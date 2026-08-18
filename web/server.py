r"""语音助手后端服务（FastAPI）。

整合 STT/LLM/TTS/工具调用/唤醒词全部能力，提供网页前端 API。

启动：
  cd D:\dsh\voice-assistant
  $env:PATH = '.venv\Lib\site-packages\torch\lib;' + $env:PATH
  .venv\Scripts\python web\server.py

访问：http://127.0.0.1:8000
"""
import asyncio
import concurrent.futures
import json
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

# 项目根目录 + web 目录入 sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

app = FastAPI(title="本地语音助手")

# CORS：允许 vite dev server（5173）跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局模型单例（懒加载，显存管理）
_llm = None
_stt = None
_tts = None
_llm_lock = threading.Lock()


def get_llm():
    global _llm
    if _llm is None:
        with _llm_lock:
            if _llm is None:
                from voice_assistant.llm import ChatModel

                _llm = ChatModel()
    return _llm


def get_stt():
    global _stt
    if _stt is None:
        from voice_assistant.stt import Recognizer

        _stt = Recognizer()
    return _stt


def unload_models_except(keep: str = ""):
    """显存管理：卸载不需要的模型（STT/LLM 不能同时驻留）。"""
    global _llm, _stt
    import gc
    import torch

    unloaded = False
    if keep != "llm" and _llm is not None:
        _llm = None
        import voice_assistant.llm as llm_mod

        llm_mod._inst = None
        unloaded = True
    if keep != "stt" and _stt is not None:
        _stt = None
        import voice_assistant.stt as stt_mod

        stt_mod._inst = None
        unloaded = True
    if not unloaded:
        # 无卸载动作：跳过 synchronize/empty_cache（LLM 驻留时开销大）
        return
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.synchronize()
        for _ in range(3):
            torch.cuda.empty_cache()
        gc.collect()


# 预热管理器（后台线程预热 LLM，启动即触发）
import prewarm as prewarm_mod

_prewarm = prewarm_mod.PrewarmManager(get_llm_fn=get_llm, unload_fn=unload_models_except)
prewarm_mod._manager = _prewarm


_chat_lock = threading.Lock()

# 工具触发关键词：命中才启用工具（避免每次带 tools 导致生成慢 4 倍）
_TOOL_KEYWORDS = ["天气", "气温", "温度", "下雨", "下雪", "搜索", "查一下", "新闻", "热点",
                  "提醒", "闹钟", "定时", "分钟后", "几点", "百度", "谷歌", "查询"]


def _need_tools(text: str) -> bool:
    return any(kw in text for kw in _TOOL_KEYWORDS)


def chat_with_tools(text: str) -> dict:
    """文字对话（含工具调用），返回 {reply, tool_calls, history_len}。

    全局锁：LLM 实例单线程推理。
    工具策略（transformers 5.15 的原生 tools 生成有性能 bug）：
      1. 命中工具关键词时，先直接执行对应工具（正则解析城市等参数）
      2. 把工具结果注入上下文，让 LLM 组织自然回复（不带 tools 参数，生成快）
    """
    from voice_assistant.tools.registry import execute_tool, get_tool_schemas

    with _chat_lock:
        print(f"[chat] 进入 chat_with_tools: {text[:20]}")
        unload_models_except(keep="llm")
        chat = get_llm()
        print("[chat] LLM 就绪")

        if not _need_tools(text):
            print("[chat] 普通对话，开始生成...")
            reply = chat.chat(text, stream=False)
            print(f"[chat] 普通对话完成: {reply[:20]}")
            return {"reply": reply, "tool_calls": [], "history_len": len(chat.history)}

        # 简单规则：识别城市（天气）并直接执行
        tool_log = []
        tool_result = None
        tool_name = None
        tool_args = None
        import re

        # 天气：匹配"X市/X/地"天气
        m = re.search(r"([\u4e00-\u9fff]{1,6}?(?:市)?)(?:今天|明天|后天)?天气", text)
        if m:
            city = m.group(1).replace("市", "")
            if city:
                tool_name = "get_weather"
                tool_args = {"city": city}
                tool_result = execute_tool(tool_name, tool_args)
                tool_log.append({"name": tool_name, "arguments": tool_args, "result": tool_result[:200]})

        # 搜索：匹配"搜索X"/"查一下X"
        if tool_result is None:
            m = re.search(r"(?:搜索|查一下|查找)\s*(.+)", text)
            if m:
                query = m.group(1).strip()
                tool_name = "web_search"
                tool_args = {"query": query}
                tool_result = execute_tool(tool_name, tool_args)
                tool_log.append({"name": tool_name, "arguments": tool_args, "result": tool_result[:200]})

        # 提醒：匹配"X分钟后提醒我Y"
        if tool_result is None:
            m = re.search(r"(\d+)\s*分钟后\s*(?:提醒我)?\s*(.+)", text)
            if m:
                minutes = float(m.group(1))
                content = m.group(2).strip() or "提醒"
                tool_name = "set_reminder"
                tool_args = {"minutes": minutes, "text": content}
                tool_result = execute_tool(tool_name, tool_args)
                tool_log.append({"name": tool_name, "arguments": tool_args, "result": tool_result[:200]})

        if tool_result is not None:
            # 工具结果注入，LLM 组织自然回复（不带 tools 参数，生成快）
            prompt = f"用户问：{text}\n\n工具结果：{tool_result}\n请用自然的中文口语化回复用户，直接给出答案。"
            reply = chat.chat(prompt, stream=False)
            return {"reply": reply, "tool_calls": tool_log, "history_len": len(chat.history)}

        # 未匹配到具体工具：走普通对话
        reply = chat.chat(text, stream=False)
        return {"reply": reply, "tool_calls": [], "history_len": len(chat.history)}


@app.get("/api/health")
def health():
    import torch

    return {
        "status": "ok",
        "cuda": torch.cuda.is_available(),
        "gpu_mem_gb": round(torch.cuda.memory_allocated() / 1e9, 2) if torch.cuda.is_available() else 0,
        "prewarm": _prewarm.to_dict(),
    }


@app.get("/api/prewarm")
def prewarm_status():
    """查询预热状态。"""
    return _prewarm.to_dict()


@app.post("/api/prewarm")
def prewarm_start():
    """手动触发预热（幂等）。"""
    _prewarm.start(background=True)
    return _prewarm.to_dict()


_tts_lock = threading.Lock()
_tts_ready = False  # 后台 TTS 是否已产出最新 mp3


def synthesize_reply_async(reply: str) -> str:
    """后台异步合成 TTS（不阻塞对话响应）。

    立即返回 /media/tts_output.mp3 URL；后台线程合成，完成后置 _tts_ready。
    前端播放时若文件未就绪（旧文件），延迟重试即可。
    """
    global _tts_ready
    _tts_ready = False

    def _run():
        global _tts_ready
        if not _tts_lock.acquire(timeout=3):
            return
        try:
            import asyncio
            import edge_tts

            media_dir = ROOT / "web" / "media"
            media_dir.mkdir(parents=True, exist_ok=True)
            mp3_path = media_dir / "tts_output.mp3"

            async def _synth():
                tts = edge_tts.Communicate(reply, voice="zh-CN-XiaoxiaoNeural")
                await asyncio.wait_for(tts.save(str(mp3_path)), timeout=8)

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_synth())
                if mp3_path.exists() and mp3_path.stat().st_size > 1000:
                    _tts_ready = True
                    print("[tts] 后台 TTS 完成")
            except Exception as e:
                print(f"[tts] edge-tts 失败: {e}")
            finally:
                loop.close()
        finally:
            _tts_lock.release()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return "/media/tts_output.mp3"


def synthesize_reply(reply: str) -> str | None:
    """兼容旧接口：同步合成（保留，用于需要立即可用的场景）。"""
    return synthesize_reply_async(reply)


# 专用推理线程池（LLM 重活在此执行，避免阻塞事件循环/默认池问题）
import concurrent.futures

_infer_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="infer")


@app.post("/api/chat")
async def api_chat(body: dict):
    """文字对话。body: {text: str, reset: bool}

    async + 专用线程池：LLM 重活放独立线程，不阻塞事件循环。
    """
    try:
        text = body.get("text", "").strip()
        if body.get("reset"):
            chat = get_llm()
            chat.reset()
            return {"reply": "已重置对话。", "tool_calls": []}
        if not text:
            return JSONResponse({"error": "文本为空"}, status_code=400)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(_infer_pool, chat_with_tools, text)
        # 后台异步 TTS（不阻塞响应）
        result["tts_url"] = synthesize_reply_async(result["reply"])
        return result
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/audio")
async def api_audio(file: UploadFile = File(...)):
    """语音对话：上传 wav → STT → LLM → TTS。

    返回 {user_text, reply, tts_wav_url}
    """
    try:
        # 保存上传音频
        data = await file.read()
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=str(ROOT / "output"))
        tmp.write(data)
        tmp.close()
        wav_path = tmp.name

        # 重活（STT+LLM+TTS）放专用线程池，不阻塞事件循环
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(_infer_pool, _process_audio_pipeline, wav_path)
        return result
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


def _process_audio_pipeline(wav_path: str) -> dict:
    """音频全链路处理（在线程池中执行）。"""
    # STT（卸载 LLM 腾显存）
    unload_models_except(keep="stt")
    stt = get_stt()
    from voice_assistant.stt import load_wav_as_float

    audio, sr = load_wav_as_float(wav_path)
    user_text = stt.transcribe((audio, sr))
    if not user_text:
        raise RuntimeError("未识别到内容")

    # 显式释放 STT 局部引用（否则 LLM 加载显存不足）
    del stt, audio
    import gc as _gc
    import torch as _torch

    _gc.collect()
    _torch.cuda.synchronize()
    _torch.cuda.empty_cache()

    # LLM 对话（含工具）
    result = chat_with_tools(user_text)

    # TTS——生成回复语音（edge-tts 在线，无需卸载 LLM）
    tts_url = synthesize_reply(result["reply"])

    return {
        "user_text": user_text,
        "reply": result["reply"],
        "tool_calls": result["tool_calls"],
        "tts_url": tts_url,
    }


@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    """WebSocket 流式对话（文字 + 工具）。"""
    await websocket.accept()
    try:
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)
            if data.get("type") == "reset":
                chat = get_llm()
                chat.reset()
                await websocket.send_json({"type": "reply", "text": "已重置对话。"})
                continue
            text = data.get("text", "")
            if not text:
                continue
            # 加载 LLM
            unload_models_except(keep="llm")
            chat = get_llm()
            from voice_assistant.tools.registry import execute_tool, get_tool_schemas

            tools = get_tool_schemas()
            tool_log = []

            def logging_executor(name, arguments):
                result = execute_tool(name, arguments)
                tool_log.append({"name": name, "arguments": arguments, "result": result[:200]})
                return result

            reply = chat.chat_with_tools(text, tools=tools, tool_executor=logging_executor, stream=False)
            await websocket.send_json({"type": "reply", "text": reply, "tool_calls": tool_log})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        traceback.print_exc()
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass


# 静态资源：优先 Vite 构建产物（webapp/dist），否则旧版 web/static
STATIC_DIR = ROOT / "web" / "static"
VITE_DIST = ROOT / "webapp" / "dist"
MEDIA_DIR = ROOT / "web" / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")


def _serve_index():
    if VITE_DIST.exists() and (VITE_DIST / "index.html").exists():
        return FileResponse(str(VITE_DIST / "index.html"))
    return FileResponse(str(STATIC_DIR / "index.html"))


if VITE_DIST.exists() and (VITE_DIST / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(VITE_DIST / "assets")), name="vite-assets")


@app.get("/")
def index():
    return _serve_index()


@app.get("/static/{path:path}")
def static_files(path: str):
    f = STATIC_DIR / path
    if f.exists() and f.is_file():
        return FileResponse(str(f))
    return JSONResponse({"error": "not found"}, status_code=404)


@app.get("/{path:path}")
def spa_fallback(path: str):
    """SPA 路由回退（Vite 构建模式）。"""
    if path.startswith("api/") or path.startswith("ws/"):
        return JSONResponse({"error": "not found"}, status_code=404)
    if VITE_DIST.exists() and (VITE_DIST / "index.html").exists():
        f = VITE_DIST / path
        if path and f.exists() and f.is_file():
            return FileResponse(str(f))
        return _serve_index()
    # 非 Vite 模式：回退旧静态页（避免 404 干扰 API）
    return JSONResponse({"error": "not found"}, status_code=404)


@app.on_event("startup")
def _auto_prewarm():
    """服务启动后自动后台预热 LLM（uvicorn 任意方式启动都触发）。"""
    try:
        _prewarm.start(background=True)
        print("[prewarm] LLM 预热已在后台启动")
    except Exception as e:
        print(f"[prewarm] 预热启动失败: {e}")


def main():
    """入口：python web/server.py 启动。"""
    import uvicorn

    print("=" * 50)
    print("本地语音助手 Web 服务")
    print(f"访问: http://127.0.0.1:8000")
    print("=" * 50)

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()

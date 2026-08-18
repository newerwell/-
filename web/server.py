r"""语音助手后端服务（FastAPI）。

整合 STT/LLM/TTS/工具调用/唤醒词全部能力，提供网页前端 API。

启动：
  cd D:\dsh\voice-assistant
  $env:PATH = '.venv\Lib\site-packages\torch\lib;' + $env:PATH
  .venv\Scripts\python web\server.py

访问：http://127.0.0.1:8000
"""
import json
import sys
import tempfile
import time
import traceback
from pathlib import Path

# 项目根目录入 sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

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


def get_llm():
    global _llm
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

    if keep != "llm" and _llm is not None:
        _llm = None
        import voice_assistant.llm as llm_mod

        llm_mod._inst = None
    if keep != "stt" and _stt is not None:
        _stt = None
        import voice_assistant.stt as stt_mod

        stt_mod._inst = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.synchronize()
        for _ in range(3):
            torch.cuda.empty_cache()
        gc.collect()


def chat_with_tools(text: str) -> dict:
    """文字对话（含工具调用），返回 {reply, tool_calls, history_len}。"""
    from voice_assistant.tools.registry import execute_tool, get_tool_schemas

    unload_models_except(keep="llm")
    chat = get_llm()
    tools = get_tool_schemas()

    # 记录工具调用
    tool_log = []
    original_exec = execute_tool

    def logging_executor(name, arguments):
        result = original_exec(name, arguments)
        tool_log.append({"name": name, "arguments": arguments, "result": result[:200]})
        return result

    reply = chat.chat_with_tools(text, tools=tools, tool_executor=logging_executor, stream=False)
    return {"reply": reply, "tool_calls": tool_log, "history_len": len(chat.history)}


@app.get("/api/health")
def health():
    import torch

    return {
        "status": "ok",
        "cuda": torch.cuda.is_available(),
        "gpu_mem_gb": round(torch.cuda.memory_allocated() / 1e9, 2) if torch.cuda.is_available() else 0,
    }


def synthesize_reply(reply: str) -> str | None:
    """合成回复语音，返回可访问的 URL 或 None。

    优先 edge-tts（联网、沙箱可用），SAPI 兜底。
    """
    try:
        import asyncio
        import edge_tts
        import threading

        media_dir = ROOT / "web" / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        mp3_path = media_dir / "tts_output.mp3"

        result_holder = {}

        def _run_synth():
            async def _synth():
                tts = edge_tts.Communicate(reply, voice="zh-CN-XiaoxiaoNeural")
                await tts.save(str(mp3_path))

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_synth())
                result_holder["ok"] = True
            finally:
                loop.close()

        # FastAPI 事件循环内不能 asyncio.run，用独立线程
        t = threading.Thread(target=_run_synth, daemon=True)
        t.start()
        t.join(timeout=60)
        if result_holder.get("ok") and mp3_path.exists() and mp3_path.stat().st_size > 1000:
            return "/media/tts_output.mp3"
        print("[tts] edge-tts 未产出文件")
    except Exception as tts_e:
        print(f"[tts] edge-tts 失败: {tts_e}")
    # 兜底：SAPI（本地）
    try:
        from voice_assistant.tts import Synthesizer

        synth = Synthesizer()
        tts_path = synth.synthesize(reply)
        if tts_path:
            media_dir = ROOT / "web" / "media"
            media_dir.mkdir(parents=True, exist_ok=True)
            import shutil

            shutil.copy2(tts_path, media_dir / "tts_output.wav")
            return "/media/tts_output.wav"
    except Exception as sapi_e:
        print(f"[tts] SAPI 也失败: {sapi_e}")
    return None


@app.post("/api/chat")
async def api_chat(body: dict):
    """文字对话。body: {text: str, reset: bool}"""
    try:
        text = body.get("text", "").strip()
        if body.get("reset"):
            chat = get_llm()
            chat.reset()
            return {"reply": "已重置对话。", "tool_calls": []}
        if not text:
            return JSONResponse({"error": "文本为空"}, status_code=400)
        result = chat_with_tools(text)
        # 生成回复语音
        unload_models_except(keep="")
        result["tts_url"] = synthesize_reply(result["reply"])
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

        # STT（卸载 LLM 腾显存）
        unload_models_except(keep="stt")
        stt = get_stt()
        from voice_assistant.stt import load_wav_as_float

        audio, sr = load_wav_as_float(wav_path)
        user_text = stt.transcribe((audio, sr))
        if not user_text:
            return JSONResponse({"error": "未识别到内容", "user_text": ""}, status_code=400)

        # 显式释放 STT 局部引用（否则 LLM 加载显存不足）
        del stt, audio
        import gc as _gc
        import torch as _torch

        _gc.collect()
        _torch.cuda.synchronize()
        _torch.cuda.empty_cache()

        # LLM 对话（含工具）
        result = chat_with_tools(user_text)

        # TTS——生成回复语音
        unload_models_except(keep="")
        tts_url = synthesize_reply(result["reply"])

        return {
            "user_text": user_text,
            "reply": result["reply"],
            "tool_calls": result["tool_calls"],
            "tts_url": tts_url,
        }
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


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


def main():
    """入口：uvicorn 启动。"""
    import uvicorn

    print("=" * 50)
    print("本地语音助手 Web 服务")
    print(f"访问: http://127.0.0.1:8000")
    print("=" * 50)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()

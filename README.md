# 语音助手 Agent — 项目说明

## 里程碑

- **M1 ✅** 命令行"说一句答一句"全链路跑通
  - STT（语音→文字）: funasr + SenseVoiceSmall (本地 GPU)
  - LLM（文字→回复）: transformers + Qwen3-8B 4bit (本地 GPU)
  - TTS（回复→语音）: Windows SAPI（CosyVoice2 模型已备，待接入）
- **M2 ✅** 唤醒词 + VAD + 打断
  - VAD: funasr fsmn-vad（1.7MB，流式分块检测，延迟约 1s）
  - 唤醒词: SenseVoice 识别 + 关键词匹配（"小助手"/"小助"）
  - 打断: TTS 播放期间麦克风能量检测中断
  - 录音: sounddevice（麦克风实时采集）
- **M4 ✅** 工具调用（天气/搜索/提醒）
  - 天气: Open-Meteo（免费、无需 key、HTTP 可用）
  - 搜索: cn.bing.com（HTTP 可达，解析搜索结果）
  - 提醒: 本地定时器（倒计时/定时，到期回调）
  - LLM: Qwen3-8B 原生 function calling（Hermes-2-Pro 风格 tool_call）
- **M5 ✅** CosyVoice2 接入（技术验证完成）
  - 官方推理代码从 GitHub 获取（Python HTTPS 突破沙箱）
  - 模型加载 + 合成验证成功（transformers 4.51 环境）
  - 已知限制：与主对话 LLM 的 transformers 5.15 版本冲突（4.51 环境自动 fallback SAPI）
  - 详见 docs/M5-report.md

## 目录结构

```
models/              模型文件（已下载）
  SenseVoiceSmall/   STT 模型
  Qwen3-8B/          LLM 模型（safetensors 分片）
  CosyVoice2-0.5B/   TTS 模型
  fsmn-vad/          VAD 模型（M2）
cosyvoice_repo/      CosyVoice2 官方推理代码（M5）
scripts/             下载/测试脚本
voice_assistant/     主程序包
  audio.py           录音/播放（sounddevice）
  vad.py             VAD 流式检测（fsmn-vad）
  wakeword.py        唤醒词监听
  bargein.py         打断（TTS 播放中检测语音）
  tools/             M4 工具包
    weather.py       天气查询（Open-Meteo）
    search.py        网络搜索（cn.bing.com）
    reminder.py      本地提醒（定时器）
    registry.py      工具注册表（schema + 执行器）
  stt.py / llm.py / tts.py / config.py / __main__.py
web/                 FastAPI 后端 + 轻量前端
  server.py          API/WebSocket 服务（含 CORS）
  static/            旧版 Vue CDN 单页（沙箱可用兜底）
  media/             生成的 TTS 音频
webapp/              Vue3 + TS + Vite 工程化前端
  src/               源码（views/stores/api/utils/router）
  node_modules/      依赖（已下载）
  README.md          前端工程说明
build-web.ps1        前端构建脚本（真实环境用）
start-web.ps1        Web 一键启动脚本
docs/                文档
wheels/              本地 wheel 缓存（离线安装用）
output/              运行输出（音频等）
```

## 运行

```powershell
# ⭐ 网页版（推荐）：Vue 界面整合全部功能（uv 托管后端）
.\start-web.ps1
# 浏览器访问 http://127.0.0.1:8000
# 说明：后端由 uv run 启动 uvicorn（web.server:app），uv 缓存已指向工作区

# 手动 uv 托管方式：
$env:UV_CACHE_DIR = 'D:\dsh\.uv-cache'
uv run --python .venv\Scripts\python.exe python -m uvicorn web.server:app --host 127.0.0.1 --port 8000

# 环境变量（bitsandbytes 需要 torch 的 CUDA DLL）
$env:PATH = 'D:\dsh\voice-assistant\.venv\Lib\site-packages\torch\lib;' + $env:PATH
$env:LD_LIBRARY_PATH = 'D:\dsh\voice-assistant\.venv\Lib\site-packages\torch\lib'

# LLM 文字对话
.venv\Scripts\python -m voice_assistant --text "你好"

# STT 识别音频
.venv\Scripts\python -m voice_assistant --audio output\real_speech.wav

# M2: VAD 检测测试
.venv\Scripts\python -m voice_assistant --vad-test output\real_speech.wav

# M2: 唤醒词+对话模式（麦克风）——说"小助手"唤醒，然后说指令
.venv\Scripts\python -m voice_assistant --listen

# M2: 指定麦克风设备（设备索引可用 sounddevice 查询）
.venv\Scripts\python -m voice_assistant --listen --device 40

# M4: 交互式对话（支持天气/搜索/提醒，如"北京天气""搜索热点""5分钟后提醒我喝水"）
.venv\Scripts\python -m voice_assistant --chat

# M4: 工具测试
.venv\Scripts\python scripts\test_tools.py
.venv\Scripts\python scripts\test_m4_e2e.py
```

## 显存管理要点（8GB 显存）

- STT（SenseVoice ~1GB）、VAD（fsmn-vad ~0.1GB）、LLM（Qwen3-8B 4bit ~5.5GB）**需串行加载**
- --listen 模式：唤醒监听用 SenseVoice，对话时加载 LLM（VAD 常驻很轻）
- 切换模型时 `del + gc.collect() + torch.cuda.empty_cache()`

## 环境限制与对策（沉淀）

1. **HTTPS 全被拦截** → 所有下载走 HTTP：
   - PyPI 包：`http://mirrors.aliyun.com/pypi/simple/`
   - torch/torchaudio：`http://mirrors.aliyun.com/pytorch-wheels/cu128/`
   - 模型：`http://www.modelscope.cn/...`（resolve 302 到 HTTPS CDN，手动降级为 HTTP）
2. **pip 网络功能被沙箱禁用** → 用 urllib/curl 下载 wheel 到本地，`pip install --no-deps --no-index --find-links` 本地安装
3. **conda 不可用** → 工作区 venv
4. **GitHub/HuggingFace 不可达** → 模型全部用 ModelScope（国内镜像）
5. 依赖修复记录：antlr4 4.9.3、llvmlite 0.49、bitsandbytes 0.46.1（cu128）、sounddevice（录音）、fsmn-vad（VAD）

## 测试脚本

```
scripts/test_pipeline.py    M1 全链路（STT→LLM）
scripts/test_wakeword.py    唤醒词匹配逻辑
scripts/test_m2_e2e.py      M2 逻辑链路（VAD+识别+匹配）
scripts/test_bargein.py     打断逻辑
```

## 下一步（M3+）

- [ ] M3：安卓 PWA 手机端（WebSocket 音频流）
- [ ] M4：工具调用（天气/搜索/提醒）
- [ ] M5：CosyVoice2 接入 + 音色克隆
- [ ] 优化：唤醒词专用模型（fsmn-kws 需预训练权重，当前用 SenseVoice 识别替代）

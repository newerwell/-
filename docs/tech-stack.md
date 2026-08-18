# 语音助手 Agent — 技术栈清单

> 整理日期：2026-08-18
> 项目位置：`D:\dsh\voice-assistant`

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────┐
│  前端（两层，均可运行）                                        │
│  ├─ webapp/    Vue 3 + TS + Vite 工程化前端（推荐）            │
│  └─ web/static 轻量 Vue CDN 单页（沙箱兜底）                   │
├─────────────────────────────────────────────────────────────┤
│  后端  FastAPI（uv 托管 uvicorn）                              │
│  ├─ REST API      /api/chat /api/audio /api/health            │
│  ├─ WebSocket     /ws/chat（流式预留）                         │
│  └─ 静态托管      前端产物 + /media 音频                        │
├─────────────────────────────────────────────────────────────┤
│  能力层（voice_assistant/ 包）                                 │
│  ├─ STT     funasr + SenseVoiceSmall（GPU）                    │
│  ├─ LLM     transformers + Qwen3-8B 4bit（GPU）               │
│  ├─ TTS     edge-tts 在线 / SAPI 本地 / CosyVoice2（备用）     │
│  ├─ VAD     funasr fsmn-vad（流式）                            │
│  ├─ 唤醒词   SenseVoice 识别 + 关键词匹配                       │
│  └─ 工具     天气(Open-Meteo) / 搜索(cn.bing) / 提醒(本地)      │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、前端技术栈

### 主前端（webapp/，Vue 3 工程化）

| 技术 | 版本 | 用途 |
|---|---|---|
| **Vue 3** | 3.5.41 | 组合式 API + `<script setup>` |
| **TypeScript** | 5.9.3 | 类型安全（vue-tsc 检查） |
| **Vite** | 8.2.1 | 构建工具（rolldown 引擎） |
| **Vue Router** | 4.6.4 | 页面路由（对话/工具/关于） |
| **Pinia** | 3.0.4 | 状态管理（chat store） |
| **Element Plus** | 2.14.4 | UI 组件库 + 中文 locale |
| **@element-plus/icons-vue** | 2.3.2 | 图标 |
| **Axios** | 1.19.0 | HTTP 请求（API 层） |
| **vue-tsc** | 3.3.10 | .vue 类型检查 |
| **sass** | 1.102.0 | 样式预处理 |

### 轻量前端（web/static，沙箱兜底）
| 技术 | 说明 |
|---|---|
| Vue 3 全局版 | 本地 CDN 文件（无构建，直接可用） |
| 原生 JS + MediaRecorder | 录音 → AudioContext 转 WAV |

---

## 三、后端技术栈

| 技术 | 版本 | 用途 |
|---|---|---|
| **FastAPI** | 0.141.1 | Web 框架（REST + WebSocket） |
| **Uvicorn** | 0.52.3 | ASGI 服务器 |
| **uv** | 0.11.27 | 项目/进程管理（uv run 托管） |
| **pydantic** | 2.13.4 | 数据校验 |
| **python-multipart** | - | 文件上传解析 |
| **CORS** | - | 跨域（允许 vite dev 5173） |

---

## 四、AI/音频能力栈

### STT（语音识别）
| 技术 | 版本 | 说明 |
|---|---|---|
| **funasr** | 1.4.2 | 阿里达摩院 ASR 框架 |
| **SenseVoiceSmall** | 936MB | 中文识别模型（GPU） |

### LLM（对话）
| 技术 | 版本 | 说明 |
|---|---|---|
| **transformers** | 5.15.0 | 模型加载/推理（Qwen3 原生 function calling） |
| **Qwen3-8B** | 16.4GB | 主对话模型（4bit 量化） |
| **bitsandbytes** | 0.46.1 | 4bit 量化（NF4 + 双量化） |
| **accelerate** | 1.14.0 | device_map 自动分配 |

### TTS（语音合成）
| 技术 | 版本 | 说明 |
|---|---|---|
| **edge-tts** | 7.2.8 | 微软在线 TTS（zh-CN-XiaoxiaoNeural，主用） |
| **pyttsx3** | - | Windows SAPI 本地兜底 |
| **CosyVoice2-0.5B** | 3.1GB | 高质量本地 TTS（需 transformers 4.51，备用） |
| **cosyvoice_repo** | - | 官方推理代码（GitHub 获取） |
| **hyperpyyaml / matcha / diffusers** | - | CosyVoice2 推理依赖 |

### VAD / 唤醒
| 技术 | 版本 | 说明 |
|---|---|---|
| **funasr fsmn-vad** | 1.7MB | 流式语音活动检测 |
| **sounddevice** | 0.5.5 | 麦克风录音（PortAudio） |

---

## 五、工具调用（M4）

| 工具 | 数据源 | 说明 |
|---|---|---|
| 天气 | Open-Meteo | 免费、无需 key、HTTP 可用 |
| 搜索 | cn.bing.com | HTML 解析搜索结果 |
| 提醒 | 本地定时器 | 倒计时/定时，线程触发 |
| 调用机制 | Qwen3 function calling | Hermes-2-Pro 风格 `<tool_call>` |

---

## 六、依赖支撑库

| 库 | 版本 | 用途 |
|---|---|---|
| **torch** | 2.10.0+cu128 | CUDA 深度学习框架 |
| **torchaudio** | 2.10.0+cu128 | 音频处理（kaldi fbank 等） |
| **numpy** | 2.5.2 | 数值计算 |
| **scipy** | 1.18.0 | 信号处理/WAV |
| **soundfile** | 0.14.0 | WAV 读写（libsndfile） |
| **librosa** | 1.0.0 | 音频分析 |
| **onnxruntime** | 1.28.0 | ONNX 推理（campplus/speech_tokenizer） |
| **modelscope** | 1.39.1 | 模型下载（国内镜像） |
| **sherpa-onnx** | 1.13.5 | ONNX 语音库（VAD/KWS 备用） |
| **websockets** | 17.0.1 | WebSocket 协议 |
| **aiohttp** | 3.14.3 | edge-tts 依赖（异步 HTTP） |

---

## 七、工具链与环境

| 工具 | 版本 | 用途 |
|---|---|---|
| **Windows** | 10/11 | 运行平台（RTX 4060 8GB） |
| **Python** | 3.12 | 后端语言（.venv 虚拟环境） |
| **uv** | 0.11.27 | 项目托管（uv run uvicorn） |
| **Node.js** | 24.16.0 | 前端构建/类型检查 |
| **npm** | 11.13.0 | 前端依赖（真实环境） |
| **git** | 2.54.0 | 版本管理 |
| **Vue 前端** | - | webapp/ 工程化 + web/ 轻量 |

---

## 八、模型资产清单（~26.4 GB）

| 模型 | 大小 | 用途 |
|---|---|---|
| SenseVoiceSmall | 0.9 GB | STT 中文识别 |
| Qwen3-8B | 16.4 GB | 主对话 LLM |
| Qwen2-0.5B-base | 1.0 GB | CosyVoice2 LLM 基础（权重被覆盖） |
| CosyVoice2-0.5B | 3.1 GB | 高质量 TTS |
| fsmn-vad | 1.7 MB | VAD 检测 |
| Qwen3-8B-GGUF | 5.0 GB | llama.cpp 备用（未启用） |

---

## 九、环境限制与对策（沉淀）

| 限制 | 对策 |
|---|---|
| HTTPS（shell curl）被拦 | Python urllib HTTPS 可用（GitHub/registry 下载） |
| npm/pnpm 子进程受限 | Python 手动下载依赖闭包到 node_modules |
| 沙箱无 node spawn | vite 构建需真实环境（tsc/vue-tsc 可离线验证） |
| pip 网络下载受限 | wheel 下载到本地 + `pip install --no-index` |
| 8GB 显存 | STT/LLM 串行加载 + 显存主动释放 |
| SAPI COM 沙箱禁用 | edge-tts 在线 TTS 替代 |

---

## 十、运行方式速查

```powershell
# Web 版（uv 托管后端）
.\start-web.ps1                     # http://127.0.0.1:8000

# 前端开发（真实环境）
.\build-web.ps1 -Dev                # http://127.0.0.1:5173

# 命令行
.venv\Scripts\python -m voice_assistant --chat    # 文字对话
.venv\Scripts\python -m voice_assistant --listen  # 唤醒词语音对话
```

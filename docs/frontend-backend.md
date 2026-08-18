# 语音助手 — 前端与后端关系说明

> 整理日期：2026-08-18
> 核心原则：**前端只负责展示与采集，后端统一承载 AI 能力**（STT/LLM/TTS/工具全在 Python 侧）。

---

## 一、总体架构图

```
┌──────────────────── 浏览器（前端） ────────────────────┐
│                                                       │
│  webapp/  Vue3 + TS + Vite（推荐）                     │
│  ┌──────────────┐   ┌──────────────┐   ┌───────────┐  │
│  │ ChatView     │   │ ToolsView    │   │ AboutView │  │
│  │ (对话页)      │   │ (工具介绍)    │   │ (关于)     │  │
│  └──────┬───────┘   └──────────────┘   └───────────┘  │
│         │ 路由 (Vue Router)                            │
│  ┌──────▼───────────────┐                             │
│  │ Pinia store (chat)   │ ← 状态管理                   │
│  │ messages / busy/health│                             │
│  └──────┬───────────────┘                             │
│         │ Axios / WebSocket                            │
│  ┌──────▼───────┐  ┌──────────────────┐               │
│  │ api/index.ts │  │ utils/audio.ts   │               │
│  │ (HTTP 封装)   │  │ (录音→WAV 转换)   │               │
│  └──────┬───────┘  └──────────────────┘               │
└─────────┼──────────────────────────────────────────────┘
          │ HTTP: /api/*  |  WS: /ws/chat  |  静态: / /media
          ▼
┌────────────────── FastAPI 后端（uv 托管 uvicorn） ──────────┐
│  web/server.py                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ /api/health  │  │ /api/chat    │  │ /api/audio       │  │
│  │ 健康检查      │  │ 文字对话      │  │ 语音对话          │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                   │            │
│  ┌──────▼─────────────────▼───────────────────▼─────────┐  │
│  │ 能力层 voice_assistant/（显存串行管理）                 │  │
│  │  STT: funasr+SenseVoice   LLM: Qwen3-8B 4bit         │  │
│  │  TTS: edge-tts / SAPI / CosyVoice2                   │  │
│  │  工具: 天气/搜索/提醒 (Qwen3 function calling)          │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## 二、前后端分工

| 职责 | 前端（浏览器） | 后端（Python） |
|---|---|---|
| 对话逻辑 | 展示消息气泡、管理输入 | 调 LLM 生成回复、工具调用 |
| 语音识别 | 录音 + 转 WAV（`utils/audio.ts`） | STT 识别文字（SenseVoice） |
| 语音合成 | 播放返回的 mp3/wav | TTS 合成（edge-tts 等） |
| 工具调用 | 展示工具卡片（名称/参数/结果） | 执行工具（天气/搜索/提醒） |
| 状态 | Pinia 管理（busy/health/消息） | 模型显存管理（串行加载） |
| 数据 | 无持久化（纯展示） | 对话历史（chat.history） |

---

## 三、接口协议（前后端契约）

### REST API（Axios 调用）

| 方法 | 路径 | 请求 | 响应 |
|---|---|---|---|
| GET | `/api/health` | - | `{status, cuda, gpu_mem_gb}` |
| POST | `/api/chat` | `{text}` | `{reply, tool_calls[], tts_url?}` |
| POST | `/api/audio` | multipart `file=*.wav` | `{user_text, reply, tool_calls[], tts_url?}` |
| POST | `/api/chat` | `{text:"", reset:true}` | `{reply:"已重置对话"}` |

### WebSocket（预留）
| 路径 | 消息 |
|---|---|
| `/ws/chat` | 入：`{type:"chat", text}`；出：`{type:"reply"/"tool"/"error"}` |

### 静态资源
| 路径 | 说明 |
|---|---|
| `/` | 前端首页（Vite 产物 `webapp/dist` 优先，否则旧版 `web/static`） |
| `/assets/*` | Vite 构建资源（存在 dist 时挂载） |
| `/media/*` | TTS 生成的音频（mp3/wav） |
| `/static/*` | 旧版轻量前端资源 |

---

## 四、两种前端形态（同一后端）

| | **webapp/（推荐，工程化）** | **web/static（兜底）** |
|---|---|---|
| 技术 | Vue3 + TS + Vite + Router + Pinia + Element Plus + Axios | Vue3 全局版 + 原生 JS |
| 定位 | 正式产品界面 | 沙箱/无构建环境快速可用 |
| 构建 | `build-web.ps1` → `webapp/dist` | 无需构建（CDN 本地文件） |
| 后端托管 | 自动检测 dist → SPA 路由回退 | `/static/` 直出 |
| 开发 | `build-web.ps1 -Dev`（vite dev 5173，代理到后端） | 直接 `start-web.ps1` |

**切换逻辑**（server.py）：
```
if webapp/dist/index.html 存在:
    首页 → dist/index.html（SPA 路由回退到它）
else:
    首页 → web/static/index.html（旧版）
```

---

## 五、开发时的联通方式

### 生产/单服务（最简单）
```
.\start-web.ps1            # 后端启动，托管前端产物
浏览器 → http://127.0.0.1:8000   （前后端同源，无跨域）
```

### 开发模式（前后端分离，热更新）
```
终端1: .\start-web.ps1                     # 后端 8000
终端2: .\build-web.ps1 -Dev                # vite dev 5173
浏览器 → http://127.0.0.1:5173
```
vite 代理（`vite.config.ts`）：
```
/api   → http://127.0.0.1:8000
/media → http://127.0.0.1:8000
/ws    → ws://127.0.0.1:8000
```
后端已开 CORS 允许 5173（双保险）。

---

## 六、数据流示例

### 文字对话（含工具）
```
用户输入 → ChatView → store.sendText() → Axios POST /api/chat
  → 后端: LLM 思考 → 工具调用(天气/搜索) → 执行 → 生成回复
  → 后端: edge-tts 合成 mp3 → 返回 {reply, tool_calls, tts_url}
→ 前端: 渲染回复 + 工具卡片 + 播放语音
```

### 语音对话
```
点击麦克风 → MediaRecorder 录音 → utils/audio.ts 转 16k WAV
  → FormData POST /api/audio
  → 后端: STT 识别 → LLM 回复 → TTS 合成 → 返回
→ 前端: 显示"🎤 你说：xxx" + 回复 + 播放语音
```

### 显存协作（后端内部）
```
语音流程: 加载 STT(1GB) → 识别完释放 → 加载 LLM(6GB) → 回复 → 释放
8GB 显存限制下 STT/LLM 严格串行（unload_models_except 管理）
```

---

## 七、前后端文件对应关系

| 前端文件 | 后端对应 |
|---|---|
| `webapp/src/api/index.ts` | `web/server.py` 的 `/api/*` 路由 |
| `webapp/src/stores/chat.ts` | 无（后端无状态，历史在 LLM 内） |
| `webapp/src/utils/audio.ts` | `web/server.py` 的 `/api/audio`（接收 WAV） |
| `webapp/src/views/ChatView.vue` | `/api/chat` + `/api/audio` |
| `webapp/src/views/ToolsView.vue` | 展示（工具定义在后端 `tools/registry.py`） |
| `webapp/src/App.vue`（header） | `/api/health` |
| 播放 TTS | `/media/tts_output.mp3` |

---

## 八、要点总结

1. **前端零 AI 依赖**：模型/推理/工具全在后端，前端只做展示与采集
2. **接口稳定**：`/api/chat`、`/api/audio` 两个核心接口承载全部对话能力
3. **双前端同后端**：工程化（webapp）与轻量（web/static）可无缝切换
4. **开发/生产两模式**：vite 代理（分离）或后端托管（同源）
5. **音频链路闭环**：录音→WAV→后端识别→回复→TTS→前端播放

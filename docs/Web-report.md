# 语音助手 Agent — Web 前端完成报告

> 日期：2026-08-17
> 状态：✅ Vue 前端 + Python 后端服务已跑通

## 成果

**网页界面整合全部功能**：文字对话（含天气/搜索/提醒工具）、语音对话（录音→识别→回复）、TTS 播放。

## 架构

```
浏览器（Vue 3 单页）          Python 后端（FastAPI）
┌──────────────────┐        ┌──────────────────────────┐
│ index.html       │  HTTP  │ server.py                │
│ app.js (Vue 3)   │ ─────► │ GET  /           页面     │
│ 对话气泡界面      │        │ POST /api/chat   文字对话 │
│ 麦克风录音按钮    │  HTTP  │ POST /api/audio  语音对话 │
│ TTS 播放         │ ◄───── │ WS   /ws/chat    流式对话 │
└──────────────────┘        │ 集成: STT/LLM/TTS/工具   │
                            └──────────────────────────┘
```

## 技术选型

- **前端**：Vue 3 全局版（CDN 本地文件，无需 Node/npm 构建——沙箱 npm 不可用）
- **后端**：FastAPI + uvicorn（PyPI 本地 wheel 安装）
- **通信**：REST API（文字/音频）+ WebSocket（流式预留）

## 文件结构

```
web/
  server.py              FastAPI 后端（模型管理/API/WebSocket）
  static/
    index.html           Vue 模板 + 样式
    app.js               Vue 应用逻辑（对话/录音/TTS）
    vendor/
      vue.global.prod.js Vue 3 本地文件
  media/                 运行生成的 TTS 音频
start-web.ps1            一键启动脚本
```

## 功能验证

| 功能 | 结果 |
|---|---|
| `/api/health` | ✅ cuda=true |
| 页面 + 静态资源 | ✅ 200 |
| 文字对话 + 天气工具 | ✅ "北京今天阴天...记得带伞"（工具调用成功） |
| 语音对话（STT→LLM） | ✅ 识别达摩院广告 → 合理回复 |
| 重置对话 | ✅ |
| TTS 播放 | ✅ edge-tts（mp3，沙箱可用） |

## 修复记录（2026-08-17）

1. **语音输入格式错误**（"file does not start with RIFF id"）：
   - 根因：MediaRecorder 默认输出 webm/opus，不是 WAV
   - 修复：前端 `blobToWav16k()` 用 AudioContext 解码 → 重采样 16k → 编码标准 WAV
2. **回答要有语音**：
   - 新增 **edge-tts**（微软免费在线 TTS，zh-CN-XiaoxiaoNeural）
   - 文字对话 + 语音对话都返回 `tts_url`（mp3）
   - edge-tts 在 FastAPI 事件循环内不能 `asyncio.run`，用独立线程 + 新事件循环
3. **界面显示识别文本**：
   - 语音输入后显示 "🎤 你说：<识别内容>"

## 显存管理（关键）

8GB 显存限制下 STT（~1GB）与 LLM（~6GB）**必须串行**：
- `unload_models_except()` 卸载另一模型（置 None + 单例清空 + gc + empty_cache×3 + synchronize）
- STT 用完显式 `del` 局部引用（否则 LLM 加载失败）
- TTS 失败不影响文字回复（catch 继续）

## 运行方式

```powershell
# 一键启动（自动设置环境变量）
.\start-web.ps1

# 或手动
$env:PATH = '.venv\Lib\site-packages\torch\lib;' + $env:PATH
.venv\Scripts\python web\server.py

# 浏览器访问
http://127.0.0.1:8000
```

## 已知限制

1. **沙箱内 SAPI 不可用**（COM 限制）——用户真实环境可正常 TTS
2. **npm/node 沙箱不可用**——Vue 用本地 CDN 文件（无构建步骤，反而更简单）
3. **首次对话加载 LLM 约 20-30s**，之后每轮 10-20s
4. WebSocket 已实现但前端暂用 REST（流式体验可后续切换）

## 下一步（可选）

- [ ] WebSocket 流式回复（打字机效果）
- [ ] 唤醒词网页集成（浏览器持续监听）
- [ ] CosyVoice2 独立 venv（网页用高质量 TTS）

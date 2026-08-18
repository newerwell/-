# 语音助手前端工程（Vue 3 + TypeScript + Vite）

工程化前端，整合语音助手全部能力（对话/语音/工具）。

## 技术栈

- **Vue 3** + **TypeScript**（组合式 API，`<script setup>`）
- **Vite 8**（构建工具，rolldown 引擎）
- **Vue Router 4**（页面路由：对话/工具/关于）
- **Pinia 3**（状态管理：chat store）
- **Element Plus 2**（UI 组件库）
- **Axios**（HTTP 请求，`src/api/index.ts`）

## 目录结构

```
webapp/
  index.html            Vite 入口
  package.json          依赖清单
  vite.config.ts        Vite 配置（dev 代理到 FastAPI 8000）
  tsconfig.json         TS 配置
  src/
    main.ts             应用入口（Element Plus + Pinia + Router）
    App.vue             布局（侧边栏 + 主区）
    env.d.ts            Vue SFC 类型声明
    router/index.ts     路由
    stores/chat.ts      Pinia store（消息/健康/发送）
    api/index.ts        Axios API 层
    utils/audio.ts      录音转 WAV 工具
    views/
      ChatView.vue      对话页（文字 + 语音 + TTS 播放 + 工具卡片）
      ToolsView.vue     工具介绍页
      AboutView.vue     关于页
```

## 运行

> ⚠️ 沙箱内 node 子进程受限，构建需在真实环境执行。
> ⚠️ PowerShell 脚本（build-web.ps1 / start-web.ps1）为纯 ASCII，避免 GBK 编码解析问题。

### 开发模式（热更新）

```powershell
# 1. 启动后端（8000）
cd D:\dsh\voice-assistant
.\start-web.ps1

# 2. 新终端启动前端 dev server（5173）
.\build-web.ps1 -Dev
# 浏览器访问 http://127.0.0.1:5173
```

### 生产模式（构建 + 后端托管）

```powershell
# 1. 构建
.\build-web.ps1

# 2. 启动后端（自动托管 webapp/dist）
.\start-web.ps1
# 浏览器访问 http://127.0.0.1:8000
```

## API 对接

前端通过 Axios 调用后端（dev 模式走 vite 代理）：
- `GET /api/health` — 健康检查
- `POST /api/chat` — 文字对话（返回 reply + tool_calls + tts_url）
- `POST /api/audio` — 语音对话（上传 wav，返回 user_text + reply + tts_url）
- `WS /ws/chat` — WebSocket 流式对话（预留）

## 说明

- 依赖已手动下载到 `node_modules/`（沙箱 npm 不可用），真实环境建议 `npm install` 刷新
- 构建产物 `dist/` 由后端 FastAPI 自动托管

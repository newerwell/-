# 语音助手 Agent — M2 完成报告

> 日期：2026-08-16
> 状态：✅ M2 "唤醒词 + VAD + 打断"已完成

## 能力与实现

### 1. VAD（语音活动检测）
- **模型**：funasr `fsmn-vad`（1.7MB，ModelScope 下载）
- **流式检测**：100ms 分块喂入，模型内部 200ms 窗口 + 150ms 起止阈值
- **延迟**：约 1s（实测：语音起点 610ms 在第 1000ms 块输出）
- **关键参数**：`chunk_size=200, is_streaming_input=True`（否则模型按整段处理导致延迟=整段时长）
- **文件**：`voice_assistant/vad.py`

### 2. 唤醒词
- **方案**：SenseVoice 识别句子 + 关键词匹配（"小助手"/"小助"/"你好小助"）
- **说明**：funasr `fsmn-kws` 专用唤醒模型在 ModelScope 无预训练权重，
  用 SenseVoice 识别替代（准确但较重，后续可换专用模型）
- **文件**：`voice_assistant/wakeword.py`

### 3. 打断（Barge-in）
- **方案**：TTS 播放期间后台线程持续麦克风采集 + RMS 能量检测
  （0.4s 持续超阈值即判定用户插话），置位 stop_event 中断播放
- **文件**：`voice_assistant/bargein.py`

### 4. 录音
- **依赖**：sounddevice（PyPI 镜像下载，Windows wheel 自带 PortAudio）
- **设备**：系统有多个麦克风（MCHOSE V9 PRO、HD Audio 等），可 `--device` 指定
- **文件**：`voice_assistant/audio.py`

## 测试结果

| 测试 | 结果 |
|---|---|
| VAD 整段检测（real_speech.wav） | ✅ 语音段 (610, 5530) |
| VAD 流式分块（200ms 块） | ✅ 语音开始/结束事件正确 |
| VAD 实时麦克风（4s 监听） | ✅ 40 块，安静环境 0 活跃 |
| 唤醒词匹配（7 组用例） | ✅ 全部通过 |
| M2 逻辑链路（VAD+识别+匹配） | ✅ 完整通过 |
| 打断逻辑（高能量触发/安静不触发） | ✅ 通过 |
| 监听模式启动/停止 | ✅ 无崩溃 |

## 运行方式

```powershell
# VAD 检测测试
.venv\Scripts\python -m voice_assistant --vad-test output\real_speech.wav

# 唤醒词+对话模式（说"小助手"唤醒，然后说指令；说"退出"结束）
.venv\Scripts\python -m voice_assistant --listen

# 指定麦克风
.venv\Scripts\python -m voice_assistant --listen --device 40
```

## 已知限制

1. **唤醒词依赖 SenseVoice**（~1GB 显存），常驻监听时占用较高；
   后续可换 fsmn-kws 专用模型（需权重）或 sherpa-onnx KWS（模型在 GitHub 被拦）
2. **打断用能量检测**（简单可靠），可能对环境噪声敏感；可调 `energy_threshold`
3. **fsmn-vad 延迟约 1s**：句子"开始"事件有约 1s 延迟，对话体验稍慢，
   但打断场景（检测到语音即停）可接受

## 下一步

- [ ] M3：安卓 PWA 手机端（WebSocket 音频流）
- [ ] M4：工具调用（天气/搜索/提醒）
- [ ] M5：CosyVoice2 接入 + 音色克隆
- [ ] 优化：fsmn-kws 专用唤醒模型 / sherpa-onnx KWS

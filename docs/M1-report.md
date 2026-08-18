# 语音助手 Agent — M1 完成报告

> 日期：2026-08-16
> 状态：✅ M1 "说一句答一句"全链路已跑通

## 已验证的成果

**全链路测试（真实中文语音）：**
```
输入语音: 欢迎大家来体验达摩院推出的语音识别模型。
[stt] 识别: 欢迎大家来体验达摩院推出的语音识别模型。   (2.9s)
[llm] 回复: 欢迎体验达摩院语音模型！您的声音就是最动听的指令～ (38.5s)
```

**单点测试：**
- STT：SenseVoice 识别真实中文语音，结果 100% 正确
- LLM：Qwen3-8B 4bit 对话自然流畅（已关闭思考模式）
- TTS：M1 用 Windows SAPI（系统中文语音 Huihui/Yaoyao 已确认存在）；
  CosyVoice2-0.5B 模型已下载（3.1GB），推理代码待接入

## 模型清单（全部本地）

| 模型 | 用途 | 大小 | 位置 |
|---|---|---|---|
| SenseVoiceSmall | STT 语音识别 | 936MB | models/SenseVoiceSmall |
| Qwen3-8B（原版） | LLM 对话 | 13.25GB | models/Qwen3-8B |
| CosyVoice2-0.5B | TTS（预留） | 3.1GB | models/CosyVoice2-0.5B |
| Qwen3-8B Q4_K_M GGUF | LLM 备用（llama.cpp 路线） | 5GB | models/Qwen3-8B-GGUF |

## 运行方式

```powershell
# 环境变量（bitsandbytes 需要 torch 的 CUDA DLL）
$env:PATH = 'D:\dsh\voice-assistant\.venv\Lib\site-packages\torch\lib;' + $env:PATH
$env:LD_LIBRARY_PATH = 'D:\dsh\voice-assistant\.venv\Lib\site-packages\torch\lib'

# 文字对话（测试 LLM）
.venv\Scripts\python -m voice_assistant --text "你好"

# 音频识别（测试 STT）
.venv\Scripts\python -m voice_assistant --audio output\real_speech.wav

# 完整链路（音频进，回复出）
.venv\Scripts\python scripts\test_pipeline.py

# 交互式聊天
.venv\Scripts\python -m voice_assistant --chat
```

## 显存管理要点（8GB 显存）

- STT 和 LLM **必须串行加载**（SenseVoice ~1GB + Qwen3-8B 4bit ~5.5GB > 8GB）
- 切换模型时 `del + gc.collect() + torch.cuda.empty_cache()`
- 跑模型前关闭壁纸引擎、MuMu 模拟器等 GPU 应用

## 环境限制与对策（沉淀）

1. **HTTPS 全被拦截** → 所有下载走 HTTP：
   - PyPI 包：`http://mirrors.aliyun.com/pypi/simple/`
   - torch/torchaudio：`http://mirrors.aliyun.com/pytorch-wheels/cu128/`
   - 模型：`http://www.modelscope.cn/...`（resolve 302 到 HTTPS CDN，手动降级为 HTTP）
2. **pip 网络功能被沙箱禁用** → 用 urllib/curl 下载 wheel 到本地，`pip install --no-deps --no-index --find-links` 本地安装
3. **conda 不可用** → 工作区 venv
4. **GitHub/HuggingFace 不可达** → 模型全部用 ModelScope（国内镜像）
5. 依赖修复记录：antlr4 4.9.3（omegaconf 需要）、torchcodec（跳过，用 wave 模块读音频）、llvmlite 0.49、soundfile DLL（绕开，用 wave）、bitsandbytes 0.46.1（cu128 支持）

## 下一步（M2+）

- [ ] M2：唤醒词（openWakeWord）+ VAD + 打断
- [ ] M3：安卓 PWA 手机端（WebSocket 音频流）
- [ ] M4：工具调用（天气/搜索/提醒）
- [ ] M5：CosyVoice2 接入（需推理代码）+ 音色克隆
- [ ] 优化：Qwen3 生成速度（当前 38s，含首次加载 20s+；预热后约 15-20s）

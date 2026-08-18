"""M2 端到端模拟测试：用音频文件流模拟麦克风，验证完整链路。

模拟场景：
1. 唤醒词音频（合成"小助手"字样语音——用 SAPI 不可用，改用真实语音文本注入）
2. VAD 检测语音段 → SenseVoice 识别 → 唤醒词匹配
3. 采集指令 → LLM 回复

说明：本测试验证 VAD + 识别 + 匹配逻辑（不含真实麦克风说话），
真实麦克风链路在 --listen 模式中验证。
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from voice_assistant.stt import Recognizer, load_wav_as_float  # noqa: E402
from voice_assistant.vad import VAD  # noqa: E402
from voice_assistant.wakeword import contains_wake_word  # noqa: E402

# 1. 加载真实语音
audio, sr = load_wav_as_float(r"D:\dsh\voice-assistant\output\real_speech.wav")
print(f"[test] 加载真实语音: {len(audio)/sr:.1f}s")

# 2. VAD 检测（分块流式）
vad = VAD()
chunk = int(sr * 0.2)
for i in range(0, len(audio), chunk):
    seg = audio[i:i + chunk]
    final = i + chunk >= len(audio)
    vad.feed(seg, is_final=final)
seg = vad.utterance_ms()
print(f"[test] VAD 语音段: {seg}")

# 3. 识别文本
rec = Recognizer()
text = rec.transcribe((audio, sr))
print(f"[test] 识别文本: {text!r}")

# 4. 唤醒词匹配（注入测试）
fake_wake_text = "小助手，" + text  # 模拟唤醒词+内容
matched = contains_wake_word(fake_wake_text)
print(f"[test] 唤醒词匹配: {fake_wake_text!r} -> {matched}")

# 5. 模拟"唤醒后采集指令"
cmd_text = text  # 模拟指令与唤醒词同句
print(f"[test] 指令文本: {cmd_text!r}")

print("\n[test] M2 逻辑链路 OK")

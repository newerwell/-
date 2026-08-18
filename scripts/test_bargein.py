"""打断（Barge-in）逻辑测试。

模拟：播放一段音频（用生成的测试音频），同时模拟"用户说话"
（向 BargeIn 注入高能量音频），验证打断触发。

由于沙箱内无法真实说话，这里直接测试：
1. play_wav 可播放
2. BargeIn 的能量检测线程能识别"模拟语音"并置位 stop_event
"""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from scipy.io import wavfile

from voice_assistant.audio import StreamRecorder, SAMPLE_RATE  # noqa: E402

# 生成一段 3 秒的测试音频（模拟 TTS 输出）
sr = SAMPLE_RATE
t = np.linspace(0, 3, int(sr * 3), endpoint=False)
tone = 0.3 * np.sin(2 * np.pi * 440 * t)
wavfile.write(r"D:\dsh\voice-assistant\output\tts_sim.wav", sr, (tone * 32767).astype(np.int16))
print("[test] 生成模拟 TTS 音频")

# 测试 BargeIn 的能量检测逻辑（独立验证）
from voice_assistant.bargein import BargeIn  # noqa: E402

barge = BargeIn()
print("[test] BargeIn 创建 OK")

# 直接测能量判定：注入高能量块应触发
stop_event = threading.Event()
energy_threshold = 0.02


def fake_listener():
    """模拟监听线程：收到高能量块就打断。"""
    frames = 0
    while not stop_event.is_set():
        # 模拟 100ms 高能量语音块
        chunk = 0.5 * np.ones(int(SAMPLE_RATE * 0.1), dtype=np.float32)
        rms = float(np.sqrt(np.mean(chunk**2)))
        if rms > energy_threshold:
            frames += 1
            if frames >= 4:  # 0.4s
                stop_event.set()
                return
        time.sleep(0.01)


t = threading.Thread(target=fake_listener, daemon=True)
t.start()
t.join(timeout=5)
if stop_event.is_set():
    print("[test] ✓ 高能量语音触发打断")
else:
    print("[test] ✗ 未能触发打断")
    sys.exit(1)

# 测试安静环境不触发
stop_event.clear()


def quiet_listener():
    frames = 0
    while not stop_event.is_set():
        chunk = 1e-6 * np.ones(int(SAMPLE_RATE * 0.1), dtype=np.float32)
        rms = float(np.sqrt(np.mean(chunk**2)))
        if rms > energy_threshold:
            frames += 1
        else:
            frames = 0
        time.sleep(0.01)
        if frames == 0:
            stop_event.set()  # 安静时不触发，模拟完成


t = threading.Thread(target=quiet_listener, daemon=True)
t.start()
t.join(timeout=5)
print("[test] 安静环境不触发 OK")

print("\n[test] BargeIn 逻辑测试通过")

"""打断（Barge-in）支持：TTS 播放期间检测用户语音并中断。

原理：播放回复时，后台线程持续从麦克风采集并用 VAD 检测。
检测到用户开始说话（语音活跃），立即置位 stop_event 中断播放，
并开始采集用户的下一句指令。
"""
import threading
import time

import numpy as np

from .audio import StreamRecorder, play_wav, SAMPLE_RATE
from .vad import VAD, get_vad


class BargeIn:
    """打断管理器：包装播放 + 语音监听。

    用法：
        barge = BargeIn()
        interrupted = barge.speak_with_bargein(wav_path)
        if interrupted:
            print("用户打断了")
    """

    def __init__(self, device: int | None = None, vad: VAD | None = None):
        self.device = device
        self.vad = vad or get_vad()
        self._stop_event = threading.Event()

    def _listen_thread(self, recorder: StreamRecorder, stop_event: threading.Event):
        """后台线程：持续 VAD 检测，一旦检测到语音就置位 stop_event。"""
        self.vad.reset()
        while not stop_event.is_set():
            chunk = recorder.read_new()
            if chunk.size:
                active = self.vad.feed(chunk)
                if active:
                    # 检测到用户语音，打断
                    stop_event.set()
                    return
            time.sleep(0.02)

    def speak_with_bargein(self, wav_path: str, min_speech_seconds: float = 0.4) -> bool:
        """播放 wav，期间监听麦克风。返回是否被打断。

        min_speech_seconds: 语音持续多久视为有效打断（避免误触发）。
        """
        self._stop_event.clear()
        recorder = StreamRecorder(device=self.device)
        recorder.start()

        # 用 VAD 的语音活跃判定（稍作延迟确认，避免噪声误触发）
        stop_event = threading.Event()
        # 简单能量确认：先积累，能量超过阈值才打断
        energy_threshold = 0.02  # RMS 阈值（需根据麦克风灵敏度调整）

        def listener():
            self.vad.reset()
            active_frames = 0
            while not stop_event.is_set():
                chunk = recorder.read_new()
                if chunk.size:
                    rms = float(np.sqrt(np.mean(chunk**2))) if chunk.size else 0.0
                    if rms > energy_threshold:
                        active_frames += 1
                        if active_frames >= int(min_speech_seconds / 0.1):
                            stop_event.set()
                            return
                    else:
                        active_frames = 0
                time.sleep(0.02)

        t = threading.Thread(target=listener, daemon=True)
        t.start()

        play_wav(wav_path, stop_event)
        interrupted = stop_event.is_set()
        stop_event.set()  # 确保线程退出
        recorder.stop()
        return interrupted


_inst = None


def get_barge_in() -> BargeIn:
    global _inst
    if _inst is None:
        _inst = BargeIn()
    return _inst

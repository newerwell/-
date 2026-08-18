"""唤醒词监听与语音采集。

架构（M2 版）：
- 持续监听：StreamRecorder 采集麦克风 → VAD 分块检测
- 唤醒词检测：SenseVoice 识别句子 + 关键词匹配（"小助手"等）
- 触发后：采集用户完整指令（VAD 判定句子结束）

注意显存：唤醒监听用 SenseVoice（约 1GB），LLM 需串行加载。
"""
import threading
import time

import numpy as np

from .audio import StreamRecorder, record_seconds, SAMPLE_RATE
from .config import (
    LISTEN_TIMEOUT,
    MAX_UTTERANCE_SECONDS,
    VAD_CHUNK_SECONDS,
    VAD_SILENCE_MS,
    WAKE_WORDS,
)
from .stt import Recognizer, get_recognizer
from .vad import VAD, get_vad


def contains_wake_word(text: str, wake_words: list[str] | None = None) -> str | None:
    """检查文本是否包含唤醒词，返回命中的唤醒词。"""
    if not text:
        return None
    for w in (wake_words or WAKE_WORDS):
        if w in text:
            return w
    return None


class WakeListener:
    """唤醒词监听器：持续听麦克风，检测唤醒词后返回采集到的指令语音。

    用法：
        listener = WakeListener()
        result = listener.listen_once()  # 阻塞直到唤醒+指令说完
        if result is not None:
            audio, text = result  # 指令音频 + 识别文本
    """

    def __init__(
        self,
        device: int | None = None,
        wake_words: list[str] | None = None,
        vad: VAD | None = None,
        recognizer: Recognizer | None = None,
    ):
        self.device = device
        self.wake_words = wake_words or WAKE_WORDS
        self.vad = vad or get_vad()
        self.recognizer = recognizer or get_recognizer()
        self.sr = SAMPLE_RATE
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def _capture_utterance(self, recorder: StreamRecorder, timeout: float) -> np.ndarray | None:
        """VAD 采集一句话（唤醒词后的指令）。返回音频数组；超时返回 None。"""
        self.vad.reset()
        buffer = np.zeros(0, dtype=np.float32)
        deadline = time.time() + timeout
        while time.time() < deadline:
            chunk = recorder.read_new()
            if chunk.size:
                buffer = np.concatenate([buffer, chunk])
                self.vad.feed(chunk)
            if self.vad.sentence_complete():
                break
            time.sleep(0.02)
        if not self.vad.has_speech():
            return None
        return buffer

    def listen_once(self, max_wait: float = 300.0) -> tuple[np.ndarray, str] | None:
        """监听一轮：等待唤醒词 → 采集指令 → 返回 (指令音频, 指令文本)。

        max_wait: 总等待上限（秒）。
        """
        recorder = StreamRecorder(device=self.device)
        recorder.start()
        try:
            deadline = time.time() + max_wait
            wake_text = None
            while time.time() < deadline:
                if self._stop_event.is_set():
                    return None
                # 采集一段语音（VAD 句子结束）
                self.vad.reset()
                buffer = np.zeros(0, dtype=np.float32)
                speech_started = False
                while True:
                    chunk = recorder.read_new()
                    if chunk.size:
                        buffer = np.concatenate([buffer, chunk])
                        active = self.vad.feed(chunk)
                        if active:
                            speech_started = True
                    if self.vad.sentence_complete():
                        break
                    if self._stop_event.is_set():
                        return None
                    # 如果一直没语音，超时
                    if not speech_started and time.time() > deadline:
                        return None
                    time.sleep(0.02)

                if buffer.size == 0:
                    continue
                # 识别这句话
                text = self.recognizer.transcribe((buffer, self.sr))
                print(f"[wake] 听到: {text!r}")
                matched = contains_wake_word(text, self.wake_words)
                if matched:
                    print(f"[wake] ✓ 唤醒词命中: {matched}")
                    # 采集后续指令
                    cmd = self._capture_utterance(recorder, LISTEN_TIMEOUT)
                    if cmd is None:
                        print("[wake] 未等到指令（超时）")
                        return None
                    cmd_text = self.recognizer.transcribe((cmd, self.sr))
                    print(f"[wake] 指令: {cmd_text!r}")
                    return (cmd, cmd_text)
                # 未命中唤醒词，继续监听
        finally:
            recorder.stop()
        return None


_inst = None


def get_wake_listener() -> WakeListener:
    global _inst
    if _inst is None:
        _inst = WakeListener()
    return _inst

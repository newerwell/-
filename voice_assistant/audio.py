"""录音/播放/音频基础工具（sounddevice）。

提供：
- 枚举并选择输入设备
- 阻塞式录音（指定时长）
- 回调式持续录音（供 VAD 流式消费）
- 播放 wav 文件（供 TTS 输出，支持中断）
"""
import threading
import time

import numpy as np
import sounddevice as sd

from .config import SAMPLE_RATE


def list_input_devices():
    """列出所有输入设备（麦克风）。"""
    devices = sd.query_devices()
    result = []
    for i, d in enumerate(devices):
        if d["max_input_channels"] > 0:
            result.append((i, d["name"]))
    return result


def pick_default_input():
    """返回默认输入设备索引。"""
    idx = sd.default.device[0]
    if idx is None:
        # 选第一个输入设备
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                idx = i
                break
    return idx


def record_seconds(duration: float, device: int | None = None, sr: int = SAMPLE_RATE) -> np.ndarray:
    """阻塞式录音，返回 float32 单声道数组（shape: (n,)）。"""
    if device is None:
        device = pick_default_input()
    rec = sd.rec(int(duration * sr), samplerate=sr, channels=1, dtype="float32", device=device)
    sd.wait()
    return rec[:, 0]


class StreamRecorder:
    """回调式录音器：持续采集音频到环形缓冲，供 VAD 流式消费。

    用法：
        rec = StreamRecorder()
        rec.start()
        while True:
            chunk = rec.read_new()  # 取出新音频（可能为空）
            ...
        rec.stop()
    """

    def __init__(self, device: int | None = None, sr: int = SAMPLE_RATE, chunk_seconds: float = 0.1):
        self.device = device if device is not None else pick_default_input()
        self.sr = sr
        self.chunk_seconds = chunk_seconds
        self._buffer = np.zeros(0, dtype=np.float32)
        self._lock = threading.Lock()
        self._stream = None
        self._pos = 0

    def _callback(self, indata, frames, time_info, status):
        with self._lock:
            self._buffer = np.concatenate([self._buffer, indata[:, 0]])

    def start(self):
        self._stream = sd.InputStream(
            samplerate=self.sr,
            channels=1,
            dtype="float32",
            device=self.device,
            blocksize=int(self.sr * self.chunk_seconds),
            callback=self._callback,
        )
        self._stream.start()

    def read_new(self) -> np.ndarray:
        """返回自上次读取以来的全部新音频（消费式）。"""
        with self._lock:
            new = self._buffer[self._pos:]
            self._pos = len(self._buffer)
            return new

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None


def play_wav(path: str, stop_event: threading.Event | None = None) -> None:
    """播放 wav 文件（16k/任意采样率）。可通过 stop_event 中断。

    返回时若 stop_event 被置位，表示被中断。
    """
    import wave

    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        raw = w.readframes(w.getnframes())
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        data = data.reshape(-1, ch)[:, 0]
    if sr != SAMPLE_RATE:
        idx = np.round(np.linspace(0, len(data) - 1, int(len(data) * SAMPLE_RATE / sr))).astype(int)
        data = data[idx]

    # 用 OutputStream 逐块播放，支持中断
    block = int(SAMPLE_RATE * 0.1)
    with sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        for i in range(0, len(data), block):
            if stop_event is not None and stop_event.is_set():
                return
            seg = data[i:i + block]
            stream.write(seg)

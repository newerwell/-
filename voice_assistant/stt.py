"""语音识别（STT）：funasr + SenseVoiceSmall。

音频输入支持：wav 文件路径 或 (numpy array, sample_rate) 元组。
"""
import wave
from pathlib import Path

import numpy as np
from funasr import AutoModel

from .config import STT_MODEL_DIR, DEVICE


def load_wav_as_float(path: str, target_sr: int = 16000) -> tuple[np.ndarray, int]:
    """读取 wav 文件为 float32 数组（16k）。"""
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        ch = w.getnchannels()
        raw = w.readframes(n)
    data = np.frombuffer(raw, dtype=np.int16)
    if ch > 1:
        data = data.reshape(-1, ch)[:, 0]
    audio = data.astype(np.float32) / 32768.0
    if sr != target_sr:
        # 简单线性重采样
        idx = np.round(np.linspace(0, len(audio) - 1, int(len(audio) * target_sr / sr))).astype(int)
        audio = audio[idx]
        sr = target_sr
    return audio, sr


class Recognizer:
    """SenseVoice 中文语音识别。"""

    def __init__(self, model_dir: str = STT_MODEL_DIR, device: str = DEVICE):
        print(f"[stt] loading SenseVoice from {model_dir} ...")
        self.model = AutoModel(
            model=model_dir,
            device=device,
            disable_update=True,
            disable_pbar=True,
        )
        print("[stt] ready")

    def transcribe(self, audio_path: str | tuple[np.ndarray, int]) -> str:
        """识别音频，返回文字。"""
        if isinstance(audio_path, tuple):
            audio, sr = audio_path
            res = self.model.generate(
                input=audio, language="zh", use_itn=True, batch_size_s=60, fs=sr
            )
        else:
            res = self.model.generate(
                input=audio_path, language="zh", use_itn=True, batch_size_s=60
            )
        text = ""
        if res and isinstance(res, list) and len(res) > 0:
            raw = res[0].get("text", "") or ""
            # 去除 SenseVoice 的特殊标记（<|zh|> 等）
            import re
            text = re.sub(r"<\|[^|]+\|>", "", raw).strip()
        return text


_inst = None


def get_recognizer() -> Recognizer:
    global _inst
    if _inst is None:
        _inst = Recognizer()
    return _inst

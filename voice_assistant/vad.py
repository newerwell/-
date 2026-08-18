"""语音活动检测（VAD）：funasr fsmn-vad 流式分块检测。

核心能力：
1. 流式检测：逐块喂入音频，实时判断语音开始/结束（延迟约 1s）
2. 语音段统计：汇总语音区间，判断一句话的开始/结束
3. 打断支持：暴露 `speech_active` 供打断逻辑轮询

注意：fsmn-vad 流式模式需要传 chunk_size=200, is_streaming_input=True，
否则模型会把输入当整段处理导致延迟等于整段时长。
"""
import numpy as np
from funasr import AutoModel

from .config import (
    DEVICE,
    VAD_MODEL_DIR,
    VAD_CHUNK_SECONDS,
    VAD_MIN_SPEECH_MS,
    VAD_SILENCE_MS,
)


class VAD:
    """fsmn-vad 流式语音活动检测器。

    用法（配合 StreamRecorder）：
        vad = VAD()
        while True:
            chunk = recorder.read_new()
            if chunk.size == 0:
                continue
            active = vad.feed(chunk)
            if vad.sentence_complete():
                break
    """

    def __init__(self, model_dir: str = VAD_MODEL_DIR, device: str = DEVICE):
        self.sr = 16000
        print(f"[vad] loading fsmn-vad from {model_dir} ...")
        self._model = AutoModel(
            model=model_dir,
            device=device,
            disable_update=True,
            disable_pbar=True,
        )
        self.reset()
        print("[vad] ready")

    def reset(self):
        """重置状态（新一句话）。"""
        self._cache: dict = {}
        self._speech_segments: list[tuple[int, int]] = []
        self._speech_active = False
        self._last_speech_end_ms: int | None = None
        self._total_ms = 0
        self._sentence_start_ms: int | None = None

    def feed(self, audio: np.ndarray, is_final: bool = False) -> bool:
        """喂入一段音频（float32 16k），返回当前是否处于语音中。

        fsmn-vad 流式检测：约 1s 延迟输出语音开始/结束事件。
        """
        if audio.size == 0:
            return self._speech_active
        res = self._model.generate(
            input=audio,
            fs=self.sr,
            cache=self._cache,
            is_final=is_final,
            chunk_size=200,
            is_streaming_input=True,
        )
        # 解析检测到的语音段（-1 表示边界未确定）
        seg_ms: list[tuple[int, int]] = []
        if res and isinstance(res, list) and res[0].get("value"):
            seg_ms = [tuple(int(x) for x in seg) for seg in res[0]["value"]]

        chunk_ms = int(len(audio) / self.sr * 1000)
        self._total_ms += chunk_ms

        for s, e in seg_ms:
            # 记录有效语音段
            if e < 0:  # 语音开始（结束未知）
                if self._speech_segments and self._speech_segments[-1][1] < 0:
                    continue
                self._speech_segments.append((s, e))
                self._sentence_start_ms = s
                self._speech_active = True
            elif s < 0:  # 语音结束（开始未知，用前一段起点）
                if self._speech_segments and self._speech_segments[-1][1] < 0:
                    prev_s, _ = self._speech_segments[-1]
                    self._speech_segments[-1] = (prev_s, e)
                    self._last_speech_end_ms = e
                else:
                    self._speech_segments.append((self._total_ms - chunk_ms, e))
                    self._last_speech_end_ms = e
                self._speech_active = False
            else:  # 完整段
                self._speech_segments.append((s, e))
                self._last_speech_end_ms = e
                self._sentence_start_ms = s

        # 自动判定句子结束：语音已结束且静音超时
        if self._last_speech_end_ms is not None and not self._speech_active:
            if self._total_ms - self._last_speech_end_ms >= VAD_SILENCE_MS:
                pass  # sentence_complete() 会返回 True

        return self._speech_active

    @property
    def speech_active(self) -> bool:
        """当前是否处于语音活动状态（供打断轮询）。"""
        return self._speech_active

    def has_speech(self) -> bool:
        """本轮是否检测到过任何语音。"""
        return len(self._speech_segments) > 0

    def sentence_complete(self) -> bool:
        """是否已采集完一句话（语音结束 + 静音超时）。"""
        if self._last_speech_end_ms is None:
            return False
        if self._speech_active:
            return False
        return self._total_ms - self._last_speech_end_ms >= VAD_SILENCE_MS

    def utterance_ms(self) -> tuple[int, int] | None:
        """当前累计语音段的 (start_ms, end_ms)。"""
        if not self._speech_segments:
            return None
        start = min(s for s, _ in self._speech_segments if s >= 0)
        ends = [e for _, e in self._speech_segments if e > 0]
        end = max(ends) if ends else None
        return (start, end)


_inst = None


def get_vad() -> VAD:
    global _inst
    if _inst is None:
        _inst = VAD()
    return _inst

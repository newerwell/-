"""模型预热（Prewarm）。

启动时后台线程预热模型，避免首次对话等待 20-30s。

策略（8GB 显存限制）：
- LLM（Qwen3-8B 4bit，~6GB）：启动即预热并**驻留**，文字对话秒回
- STT（SenseVoice，~1GB）：与 LLM 冲突，保持懒加载（语音输入时才加载）
- TTS（edge-tts 在线）：无本地模型，无需预热

API：
  GET  /api/prewarm  查询预热状态
  POST /api/prewarm  手动触发预热
"""
import threading
import time
from enum import Enum
from typing import Optional


class PrewarmStatus(str, Enum):
    IDLE = "idle"        # 未预热
    RUNNING = "running"  # 预热中
    READY = "ready"      # 已就绪
    FAILED = "failed"    # 失败


class PrewarmManager:
    def __init__(self, get_llm_fn, unload_fn=None):
        self._get_llm = get_llm_fn
        self._unload = unload_fn
        self._status: PrewarmStatus = PrewarmStatus.IDLE
        self._error: Optional[str] = None
        self._started_at: Optional[float] = None
        self._finished_at: Optional[float] = None
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    @property
    def status(self) -> PrewarmStatus:
        with self._lock:
            return self._status

    @property
    def error(self) -> Optional[str]:
        with self._lock:
            return self._error

    @property
    def duration(self) -> Optional[float]:
        """预热耗时（秒）。"""
        if self._started_at is None:
            return None
        end = self._finished_at if self._finished_at is not None else time.time()
        return round(end - self._started_at, 1)

    def start(self, background: bool = True):
        """开始预热（幂等：已在运行或就绪则跳过）。"""
        with self._lock:
            if self._status in (PrewarmStatus.RUNNING, PrewarmStatus.READY):
                return
            self._status = PrewarmStatus.RUNNING
            self._error = None
            self._started_at = time.time()
            self._finished_at = None
        if background:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        else:
            self._run()

    def _run(self):
        try:
            print("[prewarm] 开始预热 LLM ...")
            # 预热 = 加载模型（不释放，保持驻留）
            # 不做验证推理（避免与用户对话并发冲突，且省时）
            self._get_llm()
            with self._lock:
                self._status = PrewarmStatus.READY
                self._finished_at = time.time()
            print(f"[prewarm] 完成，耗时 {self.duration}s")
        except Exception as e:
            print(f"[prewarm] 预热失败: {e}")
            import traceback

            traceback.print_exc()
            with self._lock:
                self._status = PrewarmStatus.FAILED
                self._error = str(e)
                self._finished_at = time.time()

    def reset(self):
        """重置（如显存不足被卸载后）。"""
        with self._lock:
            if self._status == PrewarmStatus.READY:
                self._status = PrewarmStatus.IDLE
                self._started_at = None
                self._finished_at = None

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "error": self.error,
            "duration_s": self.duration,
        }


# 全局实例（由 server.py 注入依赖）
_manager: Optional[PrewarmManager] = None


def get_manager() -> PrewarmManager:
    return _manager

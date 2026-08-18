"""提醒工具：本地定时提醒。

支持：
- 倒计时提醒（X 分钟后）
- 定时提醒（HH:MM）
- 提醒到期时触发回调（播报）

线程安全：提醒线程 daemon，到期后自动移除。
"""
import threading
import time
from datetime import datetime


class ReminderManager:
    """提醒管理器。"""

    def __init__(self, on_trigger=None):
        """
        on_trigger: 回调函数，接收 (reminder_text, scheduled_time)。
        """
        self._reminders: dict[int, dict] = {}
        self._lock = threading.Lock()
        self._next_id = 1
        self.on_trigger = on_trigger
        self._checker = threading.Thread(target=self._run, daemon=True)
        self._checker.start()

    def _run(self):
        while True:
            now = time.time()
            due = []
            with self._lock:
                for rid, r in self._reminders.items():
                    if now >= r["due_at"]:
                        due.append((rid, r["text"], r["due_at"]))
                for rid, _, _ in due:
                    self._reminders.pop(rid, None)
            for rid, text, due_at in due:
                if self.on_trigger:
                    try:
                        self.on_trigger(text, due_at)
                    except Exception as e:
                        print(f"[reminder] 触发回调失败: {e}")
            time.sleep(1)

    def add_after(self, minutes: float, text: str) -> int:
        """X 分钟后提醒。返回提醒 ID。"""
        rid = self._next_id
        self._next_id += 1
        with self._lock:
            self._reminders[rid] = {
                "text": text,
                "due_at": time.time() + minutes * 60,
            }
        return rid

    def add_at(self, hour: int, minute: int, text: str) -> int:
        """在每天 HH:MM 提醒（下次到达该时间）。返回提醒 ID。"""
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            # 已过今天，安排到明天
            from datetime import timedelta

            target = target + timedelta(days=1)
        rid = self._next_id
        self._next_id += 1
        with self._lock:
            self._reminders[rid] = {
                "text": text,
                "due_at": target.timestamp(),
            }
        return rid

    def list_reminders(self) -> list[dict]:
        """列出所有待触发的提醒。"""
        with self._lock:
            out = []
            now = time.time()
            for rid, r in self._reminders.items():
                out.append(
                    {
                        "id": rid,
                        "text": r["text"],
                        "due_at": r["due_at"],
                        "in_seconds": int(r["due_at"] - now),
                    }
                )
            return sorted(out, key=lambda x: x["in_seconds"])

    def cancel(self, rid: int) -> bool:
        """取消提醒。"""
        with self._lock:
            return self._reminders.pop(rid, None) is not None

    def count(self) -> int:
        with self._lock:
            return len(self._reminders)


def parse_reminder_input(text: str) -> tuple[float, str] | tuple[int, int, str] | None:
    """解析用户提醒指令。

    支持：
    - "5分钟后提醒我喝水" → (5.0, "喝水")
    - "下午3点提醒我开会" / "15:00提醒我开会" → (15, 0, "开会")
    返回 (minutes, text) 或 (hour, minute, text) 或 None。
    """
    import re

    # 倒计时：N分钟后/小时
    m = re.search(r"(\d+)\s*分钟(?:后)?", text)
    if m:
        minutes = float(m.group(1))
        content = text.replace(m.group(0), "").strip()
        content = content.replace("提醒我", "").replace("提醒", "").strip()
        if not content:
            content = "提醒"
        return (minutes, content)

    # 定时：HH:MM 或 下午X点 / X点
    m = re.search(r"(\d{1,2})[:：](\d{2})", text)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        content = re.sub(r"\d{1,2}[:：]\d{2}", "", text).strip()
        content = content.replace("提醒我", "").replace("提醒", "").strip()
        if not content:
            content = "提醒"
        return (hour, minute, content)

    # 中文时间：X点
    m = re.search(r"(上午|下午|中午|晚上)?\s*(\d{1,2})\s*点", text)
    if m:
        period, hour = m.group(1), int(m.group(2))
        if period == "下午" or period == "晚上" or period == "中午" and hour < 12:
            if period == "中午" and hour == 12:
                hour = 12
            elif hour < 12 and period != "中午":
                hour += 12
        content = re.sub(r"(上午|下午|中午|晚上)?\s*\d{1,2}\s*点", "", text).strip()
        content = content.replace("提醒我", "").replace("提醒", "").strip()
        if not content:
            content = "提醒"
        return (hour, 0, content)

    return None


def get_reminder_tool_schema() -> dict:
    """LLM 工具调用 schema。"""
    return {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "设置一个提醒。支持倒计时（X分钟后）或定时（几点几分）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes": {"type": "number", "description": "多少分钟后提醒（与定时二选一）"},
                    "hour": {"type": "integer", "description": "定时提醒的小时（0-23，与分钟数二选一）"},
                    "minute": {"type": "integer", "description": "定时提醒的分钟（0-59）"},
                    "text": {"type": "string", "description": "提醒内容，如：喝水、开会"},
                },
                "required": ["text"],
            },
        },
    }

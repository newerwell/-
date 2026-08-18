"""工具注册表：统一管理 M4 工具（schema + 执行器）。

新增工具步骤：
1. 在 tools/ 下实现工具函数
2. 在 _TOOLS 注册 (name -> {schema, executor})
"""
from . import reminder, search, weather


def _default_reminder_trigger(text: str, due_at: float):
    from datetime import datetime

    t = datetime.fromtimestamp(due_at).strftime("%H:%M")
    print(f"\n[提醒] ⏰ {t}：{text}")


# 提醒管理器（全局单例，on_trigger 默认打印）
_reminder_mgr = reminder.ReminderManager(on_trigger=_default_reminder_trigger)


def _exec_weather(args: dict) -> str:
    return weather.get_weather(str(args.get("city", "")).strip())


def _exec_search(args: dict) -> str:
    return search.search(str(args.get("query", "")).strip(), num=5)


def _exec_reminder(args: dict) -> str:
    minutes = args.get("minutes")
    hour = args.get("hour")
    minute = args.get("minute")
    text = str(args.get("text", "提醒")).strip()
    if minutes is not None:
        rid = _reminder_mgr.add_after(float(minutes), text)
        return f"已设置提醒：{minutes}分钟后提醒你「{text}」（编号{rid}）"
    if hour is not None:
        rid = _reminder_mgr.add_at(int(hour), int(minute or 0), text)
        return f"已设置提醒：每天{int(hour):02d}:{int(minute or 0):02d}提醒你「{text}」（编号{rid}）"
    return "提醒设置失败：请提供 minutes（分钟）或 hour/minute（定时）。"


_TOOLS: dict[str, dict] = {
    "get_weather": {
        "schema": weather.get_weather_tool_schema(),
        "executor": _exec_weather,
    },
    "web_search": {
        "schema": search.get_search_tool_schema(),
        "executor": _exec_search,
    },
    "set_reminder": {
        "schema": reminder.get_reminder_tool_schema(),
        "executor": _exec_reminder,
    },
}


def get_tool_schemas() -> list[dict]:
    """所有工具的 OpenAI 风格 schema。"""
    return [t["schema"] for t in _TOOLS.values()]


def execute_tool(name: str, arguments: dict) -> str:
    """执行工具，返回结果文本。"""
    tool = _TOOLS.get(name)
    if tool is None:
        return f"未知工具：{name}"
    return tool["executor"](arguments)


def get_reminder_manager():
    """供外部访问提醒管理器（如 CLI 展示）。"""
    return _reminder_mgr

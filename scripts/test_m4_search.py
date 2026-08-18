"""M4 端到端测试 2：搜索 + 提醒工具调用。

验证：
1. LLM 识别"搜索"意图 → 调用 web_search
2. 提醒管理器到期触发回调
"""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from voice_assistant.llm import ChatModel  # noqa: E402
from voice_assistant.tools.registry import (
    execute_tool,
    get_tool_schemas,
    get_reminder_manager,
)  # noqa: E402

# 先测提醒管理器触发
triggered = threading.Event()
trigger_text = []


def on_trigger(text, due_at):
    trigger_text.append(text)
    triggered.set()


mgr = get_reminder_manager()
old_trigger = mgr.on_trigger
mgr.on_trigger = on_trigger
mgr.add_after(0.05, "测试提醒")
print("[m4] 等待提醒触发...")
ok = triggered.wait(timeout=5)
mgr.on_trigger = old_trigger
print(f"[m4] 提醒触发: {'OK' if ok else 'FAIL'} text={trigger_text}")

t0 = time.time()
chat = ChatModel()
tools = get_tool_schemas()
chat.reset()
q = "帮我搜索一下今天的新闻热点"
print(f"\n[m4] 用户: {q}")
reply = chat.chat_with_tools(q, tools=tools, tool_executor=execute_tool)
print(f"[m4] 助手: {reply}")
print(f"[m4] 用时 {(time.time()-t0):.1f}s")
print(f"[m4] 含搜索工具调用: {any(m.get('role')=='tool' for m in chat.history)}")
print("\n[m4] 测试 2 完成")

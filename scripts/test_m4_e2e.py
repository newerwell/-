"""M4 端到端测试：LLM 工具调用（真实模型 + 真实工具）。

验证：
1. LLM 识别"北京天气"→ 调用 get_weather
2. 执行工具 → 回填结果 → LLM 生成最终回复
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from voice_assistant.llm import ChatModel  # noqa: E402
from voice_assistant.tools.registry import execute_tool, get_tool_schemas  # noqa: E402

t0 = time.time()
chat = ChatModel()
print(f"[m4] LLM 加载完成 {(time.time()-t0):.1f}s")

tools = get_tool_schemas()
test_queries = [
    "北京今天天气怎么样？",
]

for q in test_queries:
    chat.reset()
    print(f"\n[m4] 用户: {q}")
    reply = chat.chat_with_tools(q, tools=tools, tool_executor=execute_tool)
    print(f"[m4] 助手: {reply}")
    print(f"[m4] 用时 {(time.time()-t0):.1f}s")
    print(f"[m4] 历史消息数: {len(chat.history)}")
    print(f"[m4] 含工具结果: {any(m.get('role')=='tool' for m in chat.history)}")

print("\n[m4] 端到端测试完成")

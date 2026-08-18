"""测试 ChatModel.parse_tool_calls 与工具注册表。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from voice_assistant.llm import ChatModel  # noqa: E402
from voice_assistant.tools.registry import execute_tool, get_tool_schemas  # noqa: E402

print("=== parse_tool_calls 测试 ===")
samples = [
    '<tool_call>\n{"name": "get_weather", "arguments": {"city": "北京"}}\n</tool_call>',
    '<tool_call>{"name":"web_search","arguments":"{\\"query\\": \\"热点\\"}"}</tool_call>',
    '好的，我来查一下天气。<tool_call>{"name":"get_weather","arguments":{"city":"上海"}}</tool_call>',
    '今天天气不错，不需要查。',
    '<tool_call>{"name":"set_reminder","arguments":{"minutes":5,"text":"喝水"}}</tool_call>',
]
expected = [
    [{"name": "get_weather", "arguments": {"city": "北京"}}],
    [{"name": "web_search", "arguments": {"query": "热点"}}],
    [{"name": "get_weather", "arguments": {"city": "上海"}}],
    [],
    [{"name": "set_reminder", "arguments": {"minutes": 5, "text": "喝水"}}],
]
all_ok = True
for i, (s, exp) in enumerate(zip(samples, expected)):
    got = ChatModel.parse_tool_calls(s)
    ok = got == exp
    all_ok = all_ok and ok
    print(f"  {'OK ' if ok else 'FAIL'} sample{i}: {got}")
print(f"  parse_tool_calls: {'全部通过' if all_ok else '有失败'}")

print("\n=== 工具注册表测试 ===")
print("schemas:", [s["function"]["name"] for s in get_tool_schemas()])
print("weather 执行:", execute_tool("get_weather", {"city": "北京"})[:60], "...")
print("search 执行:", execute_tool("web_search", {"query": "今日新闻"})[:60], "...")
print("reminder 执行:", execute_tool("set_reminder", {"minutes": 1, "text": "测试"}))
print("未知工具:", execute_tool("nope", {}))

print("\n" + ("全部通过" if all_ok else "有失败项"))
sys.exit(0 if all_ok else 1)

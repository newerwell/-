"""唤醒词逻辑离线测试：不依赖真实麦克风。

流程：
1. 用真实语音识别文本（real_speech.wav → "欢迎大家来体验达摩院推出的语音识别模型"）
2. 检查 contains_wake_word 的匹配逻辑（模拟"小助手"被识别到的情况）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from voice_assistant.wakeword import contains_wake_word  # noqa: E402

# 模拟各种识别结果
cases = [
    ("小助手", "小助手", True),
    ("你好小助手", "小助手", True),
    ("小助", "小助", True),
    ("欢迎大家来体验达摩院推出的语音识别模型", None, False),
    ("", None, False),
    ("小助手，今天天气怎么样", "小助手", True),
    ("嘿小助，帮我定个闹钟", "小助", True),
]

print("=== 唤醒词匹配测试 ===")
all_ok = True
for text, expect_wake, expect_hit in cases:
    matched = contains_wake_word(text)
    hit = matched is not None
    ok = (hit == expect_hit) and (matched == expect_wake)
    all_ok = all_ok and ok
    print(f"  {'OK ' if ok else 'FAIL'} {text!r} -> {matched!r} (expect {expect_wake!r})")

print(f"\n{'全部通过' if all_ok else '有失败项'}")
sys.exit(0 if all_ok else 1)

"""语音助手命令行入口。

用法：
  python -m voice_assistant --text "你好"        # LLM 文字对话
  python -m voice_assistant --audio x.wav         # STT + LLM（音频进，文字出）
  python -m voice_assistant --tts "你好"          # TTS 朗读（SAPI）
  python -m voice_assistant --chat                # 交互式聊天（文字）
  python -m voice_assistant --pipeline x.wav      # STT+LLM+TTS 全链路
  python -m voice_assistant --listen              # M2：唤醒词+对话（麦克风）
  python -m voice_assistant --vad-test x.wav      # M2：测试 VAD 检测
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser(description="本地语音助手（M1 对话链路 + M2 唤醒/VAD/打断）")
    ap.add_argument("--text", type=str, help="输入文字（LLM 对话）")
    ap.add_argument("--audio", type=str, help="输入音频路径（STT 识别）")
    ap.add_argument("--tts", type=str, help="要合成的文字（TTS 输出）")
    ap.add_argument("--pipeline", type=str, help="音频路径：STT→LLM→TTS 全链路")
    ap.add_argument("--chat", action="store_true", help="交互式对话模式（文字）")
    ap.add_argument("--listen", action="store_true", help="M2: 唤醒词+对话模式（麦克风）")
    ap.add_argument("--vad-test", type=str, help="M2: 测试 VAD 检测指定音频")
    ap.add_argument("--device", type=int, default=None, help="麦克风设备索引")
    ap.add_argument("--stream", action="store_true", help="LLM 流式输出")
    ap.add_argument("--reset", action="store_true", help="重置对话历史")
    args = ap.parse_args()

    t0 = time.time()

    # --- M2: VAD 检测测试 ---
    if args.vad_test:
        from .vad import VAD
        from .stt import load_wav_as_float
        vad = VAD()
        audio, sr = load_wav_as_float(args.vad_test)
        # 分块喂入
        chunk = int(sr * 0.2)
        events = []
        for i in range(0, len(audio), chunk):
            seg = audio[i:i + chunk]
            final = i + chunk >= len(audio)
            active = vad.feed(seg, is_final=final)
            events.append((round(i / sr * 1000), active))
        seg = vad.utterance_ms()
        print(f"[vad-test] {args.vad_test}")
        print(f"[vad-test] 检测到语音段: {seg}")
        print(f"[vad-test] 语音活跃块数: {sum(1 for _, a in events if a)}/{len(events)}")
        return

    # --- M2: 唤醒词+对话模式 ---
    if args.listen:
        from .wakeword import WakeListener
        from .llm import get_chat_model
        from .tts import get_synthesizer
        from .bargein import get_barge_in
        from .tools.registry import execute_tool, get_tool_schemas

        listener = WakeListener(device=args.device)
        chat = None
        tools = get_tool_schemas()
        print("=== 语音助手（唤醒词模式，支持天气/搜索/提醒）===")
        print(f"唤醒词: {'/'.join(listener.wake_words)}，说'退出'结束")
        try:
            while True:
                print("\n[listen] 等待唤醒词...")
                result = listener.listen_once(max_wait=600)
                if result is None:
                    print("[listen] 超时或停止，退出")
                    break
                cmd_audio, cmd_text = result
                if not cmd_text:
                    print("[listen] 未识别到指令")
                    continue
                if cmd_text in ("退出", "结束", "再见"):
                    print("[listen] 再见！")
                    break
                # 加载 LLM 对话（首次）
                if chat is None:
                    chat = get_chat_model()
                reply = chat.chat_with_tools(cmd_text, tools=tools, tool_executor=execute_tool, stream=False)
                print(f"[assistant] {reply}")
                # TTS 朗读（SAPI）+ 打断监听
                synth = get_synthesizer()
                synth.synthesize(reply)
        except KeyboardInterrupt:
            print("\n[listen] 已停止")
        return

    # --- 仅 TTS ---
    if args.tts:
        from .tts import get_synthesizer
        synth = get_synthesizer()
        out = synth.synthesize(args.tts)
        print(f"[ok] TTS 输出: {out} ({(time.time()-t0):.1f}s)")
        return

    # --- 加载 LLM（对话核心）---
    from .llm import get_chat_model
    chat = get_chat_model()
    if args.reset:
        chat.reset()

    # --- 仅文字对话 ---
    if args.text:
        print(f"[user] {args.text}")
        reply = chat.chat(args.text, stream=args.stream)
        print(f"\n[assistant] {reply}")
        return

    # --- STT ---
    if args.audio or args.pipeline:
        from .stt import get_recognizer
        rec = get_recognizer()
        audio_path = args.audio or args.pipeline
        print(f"[stt] 识别 {audio_path} ...")
        user_text = rec.transcribe(audio_path)
        print(f"[stt] -> {user_text}")
        if not user_text:
            print("[!] 未识别到内容")
            return
        if args.audio:
            reply = chat.chat(user_text, stream=args.stream)
            print(f"[assistant] {reply}")
            return

    # --- 全链路：STT + LLM + TTS ---
    if args.pipeline:
        from .tts import get_synthesizer
        reply = chat.chat(user_text, stream=False)
        print(f"[assistant] {reply}")
        synth = get_synthesizer()
        out = synth.synthesize(reply)
        print(f"[ok] 回复音频: {out} (总耗时 {(time.time()-t0):.1f}s)")
        return

    # --- 交互式聊天（文字，支持工具）---
    if args.chat:
        from .tools.registry import execute_tool, get_tool_schemas
        tools = get_tool_schemas()
        print("=== 语音助手（文字模式，支持天气/搜索/提醒），输入 exit 退出 ===")
        while True:
            try:
                user = input("\n你: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if user.lower() in ("exit", "quit", "退出"):
                break
            if not user:
                continue
            reply = chat.chat_with_tools(user, tools=tools, tool_executor=execute_tool, stream=args.stream)
            print(f"助手: {reply}")
        return

    ap.print_help()


if __name__ == "__main__":
    main()

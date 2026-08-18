"""诊断：LLM token 生成质量。"""
import sys
import time

sys.path.insert(0, r"D:\dsh\voice-assistant\cosyvoice_repo")
sys.path.insert(0, r"D:\dsh\voice-assistant")

import numpy as np  # noqa: E402
import torch  # noqa: E402


def main():
    t0 = time.time()
    from cosyvoice.cli.cosyvoice import CosyVoice2

    cv = CosyVoice2(r"D:\dsh\voice-assistant\models\CosyVoice2-0.5B")
    print(f"[diag] loaded {(time.time()-t0):.1f}s")

    model_input = cv.frontend.frontend_zero_shot(
        "你好。",
        "欢迎大家来体验达摩院推出的语音识别模型。",
        r"D:\dsh\voice-assistant\output\real_speech.wav",
        24000, "",
    )

    # 直接调 LLM inference，收集 token
    device = cv.model.device
    tokens = []
    t1 = time.time()
    gen = cv.model.llm.inference(
        text=model_input["text"].to(device),
        text_len=model_input["text_len"].to(device),
        prompt_text=model_input["prompt_text"].to(device),
        prompt_text_len=model_input["prompt_text_len"].to(device),
        prompt_speech_token=model_input["llm_prompt_speech_token"].to(device),
        prompt_speech_token_len=model_input["llm_prompt_speech_token_len"].to(device),
        embedding=model_input["llm_embedding"].to(device),
        uuid="diag2",
    )
    for t in gen:
        if hasattr(t, "item"):
            tokens.append(int(t.item()))
        elif isinstance(t, (list, tuple)):
            tokens.extend(int(x) for x in t)
        else:
            tokens.append(int(t))
    print(f"[diag] LLM token 数: {len(tokens)} ({(time.time()-t1):.1f}s)")
    if tokens:
        print(f"[diag] range: [{min(tokens)}, {max(tokens)}] unique: {len(set(tokens))}")
        print(f"[diag] 前 40: {tokens[:40]}")
        # 检查重复度（退化指标）
        if len(tokens) > 10:
            repeats = sum(1 for i in range(1, len(tokens)) if tokens[i] == tokens[i-1])
            print(f"[diag] 相邻重复: {repeats}/{len(tokens)}")
        # 检查是否都是 prompt 里的 token（复制 prompt）
        prompt_toks = set(model_input["llm_prompt_speech_token"][0].cpu().tolist())
        copied = sum(1 for t in tokens if t in prompt_toks)
        print(f"[diag] 与 prompt token 相同的: {copied}/{len(tokens)}")


if __name__ == "__main__":
    main()

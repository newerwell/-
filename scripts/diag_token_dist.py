"""对比 LLM 生成 token 与 prompt token 的分布。"""
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
    device = cv.model.device

    prompt_toks = model_input["llm_prompt_speech_token"][0].cpu().tolist()
    print(f"[diag] prompt token: {len(prompt_toks)} 个")
    print(f"[diag] prompt token 分布: min={min(prompt_toks)} max={max(prompt_toks)} unique={len(set(prompt_toks))}")

    # 多轮生成收集 token
    all_gen = []
    for trial in range(3):
        tokens = []
        gen = cv.model.llm.inference(
            text=model_input["text"].to(device),
            text_len=model_input["text_len"].to(device),
            prompt_text=model_input["prompt_text"].to(device),
            prompt_text_len=model_input["prompt_text_len"].to(device),
            prompt_speech_token=model_input["llm_prompt_speech_token"].to(device),
            prompt_speech_token_len=model_input["llm_prompt_speech_token_len"].to(device),
            embedding=model_input["llm_embedding"].to(device),
            uuid=f"dist{trial}",
        )
        for t in gen:
            if hasattr(t, "item"):
                tokens.append(int(t.item()))
            elif isinstance(t, (list, tuple)):
                tokens.extend(int(x) for x in t)
            else:
                tokens.append(int(t))
        all_gen.extend(tokens)
        print(f"[diag] trial{trial}: {len(tokens)} tokens")

    if all_gen:
        print(f"[diag] 生成 token: {len(all_gen)} 个")
        print(f"[diag] 生成分布: min={min(all_gen)} max={max(all_gen)} unique={len(set(all_gen))}")
        # 直方图对比（分成 10 桶）
        hist_p = np.histogram(prompt_toks, bins=10, range=(0, 6600))[0]
        hist_g = np.histogram(all_gen, bins=10, range=(0, 6600))[0]
        print(f"[diag] prompt 直方图: {hist_p}")
        print(f"[diag] 生成 直方图: {hist_g}")
        # 检查生成 token 是否全是特定小范围
        print(f"[diag] 生成 token 前 50: {all_gen[:50]}")


if __name__ == "__main__":
    main()

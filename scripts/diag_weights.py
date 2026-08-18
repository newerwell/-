"""关键诊断：检查 LLM token 分布与 speech_embedding 权重健康度。

如果 speech_embedding 权重异常（如全 0 或 NaN），LLM 生成的 token 会退化。
"""
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

    llm = cv.model.llm
    # 检查关键权重（Qwen2LM 结构：speech_embedding/llm_embedding/llm_decoder + llm.model.model.embed_tokens）
    print("\n[diag] LLM 权重健康检查:")
    for name in ["speech_embedding", "llm_embedding", "llm_decoder"]:
        w = getattr(llm, name, None)
        if w is not None and hasattr(w, "weight"):
            wt = w.weight
            print(f"  {name}: shape={wt.shape} dtype={wt.dtype} "
                  f"nan={torch.isnan(wt).any().item()} range=[{wt.min():.3f},{wt.max():.3f}]")
        else:
            print(f"  {name}: {type(w).__name__}")

    # Qwen2 embed_tokens
    emb = llm.llm.model.model.embed_tokens.weight
    print(f"  qwen2.embed_tokens: shape={emb.shape} dtype={emb.dtype} nan={torch.isnan(emb).any().item()}")

    # 检查 Qwen2 部分
    qw = llm.llm.model
    print(f"\n[diag] Qwen2 dtype: {next(qw.parameters()).dtype}")
    # 生成 token 分布测试（多次）
    model_input = cv.frontend.frontend_zero_shot(
        "你好。",
        "欢迎大家来体验达摩院推出的语音识别模型。",
        r"D:\dsh\voice-assistant\output\real_speech.wav",
        24000, "",
    )
    device = cv.model.device

    for trial in range(2):
        tokens = []
        gen = llm.inference(
            text=model_input["text"].to(device),
            text_len=model_input["text_len"].to(device),
            prompt_text=model_input["prompt_text"].to(device),
            prompt_text_len=model_input["prompt_text_len"].to(device),
            prompt_speech_token=model_input["llm_prompt_speech_token"].to(device),
            prompt_speech_token_len=model_input["llm_prompt_speech_token_len"].to(device),
            embedding=model_input["llm_embedding"].to(device),
            uuid=f"diag{trial}",
        )
        for t in gen:
            if hasattr(t, "item"):
                tokens.append(int(t.item()))
            elif isinstance(t, (list, tuple)):
                tokens.extend(int(x) for x in t)
            else:
                tokens.append(int(t))
        print(f"\n[diag] trial{trial}: {len(tokens)} tokens")
        print(f"  range: [{min(tokens) if tokens else '?'}, {max(tokens) if tokens else '?'}]")
        print(f"  unique: {len(set(tokens))}")
        # 检查 token 是否集中在极值（异常信号）
        if tokens:
            high = sum(1 for t in tokens if t > 6000)
            low = sum(1 for t in tokens if t < 500)
            print(f"  >6000: {high}, <500: {low}")


if __name__ == "__main__":
    main()

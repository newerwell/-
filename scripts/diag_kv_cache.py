"""检查 Qwen2Encoder.forward_one_step 的 KV cache 行为。

对比：首次 forward 的 logits vs 用 cache 逐 token 的 logits（应一致）。
"""
import sys
import time

sys.path.insert(0, r"D:\dsh\voice-assistant\cosyvoice_repo")
sys.path.insert(0, r"D:\dsh\voice-assistant")

import torch  # noqa: E402


def main():
    t0 = time.time()
    from cosyvoice.cli.cosyvoice import CosyVoice2

    cv = CosyVoice2(r"D:\dsh\voice-assistant\models\CosyVoice2-0.5B")
    print(f"[diag] loaded {(time.time()-t0):.1f}s")

    device = cv.model.device
    enc = cv.model.llm.llm  # Qwen2Encoder
    llm = cv.model.llm

    # 构造一个小的 lm_input（模拟 inference 的初始输入）
    model_input = cv.frontend.frontend_zero_shot(
        "你好。",
        "欢迎大家来体验达摩院推出的语音识别模型。",
        r"D:\dsh\voice-assistant\output\real_speech.wav",
        24000, "",
    )
    text = torch.concat([model_input["prompt_text"], model_input["text"]], dim=1)
    text_len = model_input["text_len"] + model_input["prompt_text_len"]
    text_emb = llm.llm.model.model.embed_tokens(text)
    sos_emb = llm.llm_embedding.weight[llm.sos].reshape(1, 1, -1)
    task_id_emb = llm.llm_embedding.weight[llm.task_id].reshape(1, 1, -1)
    prompt_speech_token_emb = llm.speech_embedding(model_input["llm_prompt_speech_token"])
    lm_input = torch.concat([sos_emb, text_emb, task_id_emb, prompt_speech_token_emb], dim=1)
    print(f"[diag] lm_input: {lm_input.shape}")

    # 方式1：一次性 forward 所有
    masks_full = ~torch.zeros(1, lm_input.shape[1], dtype=torch.bool)
    y_full, _ = enc.forward(lm_input, torch.tensor([lm_input.shape[1]]).to(device))
    logp_full = llm.llm_decoder(y_full[:, -1]).log_softmax(dim=-1)
    print(f"[diag] full forward last logits top5: {logp_full.topk(5).indices[0].tolist()}")

    # 方式2：forward_one_step 单步
    y1, cache = enc.forward_one_step(
        lm_input,
        masks=torch.tril(torch.ones((1, lm_input.shape[1], lm_input.shape[1]), device=device)).to(torch.bool),
        cache=None,
    )
    logp1 = llm.llm_decoder(y1[:, -1]).log_softmax(dim=-1)
    print(f"[diag] one_step last logits top5: {logp1.topk(5).indices[0].tolist()}")

    # 对比两个 top 是否一致
    same = logp_full.topk(5).indices[0].tolist() == logp1.topk(5).indices[0].tolist()
    print(f"[diag] top5 一致: {same}")
    # 计算分布差异
    diff = (logp_full - logp1).abs().mean().item()
    print(f"[diag] logits 平均差异: {diff:.6f}")

    # 测试第二步（cache 扩展）
    next_emb = llm.speech_embedding.weight[logp1.topk(1).indices[0].item()].reshape(1, 1, -1)
    masks2 = torch.tril(torch.ones((1, lm_input.shape[1] + 1, lm_input.shape[1] + 1), device=device)).to(torch.bool)
    y2, cache2 = enc.forward_one_step(next_emb, masks=masks2, cache=cache)
    print(f"[diag] step2 logits top5: {llm.llm_decoder(y2[:, -1]).log_softmax(dim=-1).topk(5).indices[0].tolist()}")


if __name__ == "__main__":
    main()

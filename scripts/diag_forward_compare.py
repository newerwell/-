"""测试：用完整 forward 替代 forward_one_step 生成 token。

如果 LLM 生成内容变对，说明 forward_one_step 的 cache 与 5.15 不兼容。
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
    llm = cv.model.llm

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

    # 方式A：forward_one_step（当前实现）
    min_len = int((text_len - model_input["prompt_text_len"]) * 2)
    max_len = int((text_len - model_input["prompt_text_len"]) * 20)
    print(f"[diag] min_len={min_len}, max_len={max_len}")

    tokens_a = []
    cache = None
    cur = lm_input
    seq_len = lm_input.shape[1]
    for i in range(min(max_len, 60)):
        masks = torch.tril(torch.ones((1, cur.shape[1], cur.shape[1]), device=device)).to(torch.bool)
        y, cache = llm.llm.forward_one_step(cur, masks=masks, cache=cache)
        logp = llm.llm_decoder(y[:, -1]).log_softmax(dim=-1)
        top_ids = llm.sampling_ids(logp.squeeze(0), tokens_a, 25, ignore_eos=True if i < min_len else False)
        if top_ids in llm.stop_token_ids:
            break
        tokens_a.append(int(top_ids))
        cur = llm.speech_embedding.weight[top_ids].reshape(1, 1, -1)
    print(f"[diag] forward_one_step tokens: {len(tokens_a)}: {tokens_a[:30]}")

    # 方式B：完整 forward（每次重算全量）
    tokens_b = []
    cur_full = lm_input
    for i in range(min(max_len, 60)):
        y, _ = llm.llm.forward(cur_full, torch.tensor([cur_full.shape[1]]).to(device))
        logp = llm.llm_decoder(y[:, -1]).log_softmax(dim=-1)
        top_ids = llm.sampling_ids(logp.squeeze(0), tokens_b, 25, ignore_eos=True if i < min_len else False)
        if top_ids in llm.stop_token_ids:
            break
        tokens_b.append(int(top_ids))
        cur_full = torch.concat([cur_full, llm.speech_embedding.weight[top_ids].reshape(1, 1, -1)], dim=1)
    print(f"[diag] 完整 forward tokens: {len(tokens_b)}: {tokens_b[:30]}")
    print(f"[diag] 两种方式一致: {tokens_a == tokens_b}")


if __name__ == "__main__":
    main()

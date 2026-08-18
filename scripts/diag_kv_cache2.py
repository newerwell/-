"""精确测试 KV cache：不同输入 token 应产生不同输出。"""
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
    enc = cv.model.llm.llm
    llm = cv.model.llm

    model_input = cv.frontend.frontend_zero_shot(
        "你好。",
        "欢迎大家来体验达摩院推出的语音识别模型。",
        r"D:\dsh\voice-assistant\output\real_speech.wav",
        24000, "",
    )
    text = torch.concat([model_input["prompt_text"], model_input["text"]], dim=1)
    text_emb = llm.llm.model.model.embed_tokens(text)
    sos_emb = llm.llm_embedding.weight[llm.sos].reshape(1, 1, -1)
    task_id_emb = llm.llm_embedding.weight[llm.task_id].reshape(1, 1, -1)
    prompt_speech_token_emb = llm.speech_embedding(model_input["llm_prompt_speech_token"])
    lm_input = torch.concat([sos_emb, text_emb, task_id_emb, prompt_speech_token_emb], dim=1)
    seq_len = lm_input.shape[1]

    def make_mask(n):
        return torch.tril(torch.ones((1, n, n), device=device)).to(torch.bool)

    # step1
    y1, cache = enc.forward_one_step(lm_input, masks=make_mask(seq_len), cache=None)
    logp1 = llm.llm_decoder(y1[:, -1]).log_softmax(dim=-1)
    t1 = logp1.topk(1).indices[0].item()
    print(f"[diag] step1 top1: {t1}")

    # step2 with token A
    embA = llm.speech_embedding.weight[100].reshape(1, 1, -1)
    yA, _ = enc.forward_one_step(embA, masks=make_mask(seq_len + 1), cache=cache)
    logpA = llm.llm_decoder(yA[:, -1]).log_softmax(dim=-1)
    topA = logpA.topk(3).indices[0].tolist()
    print(f"[diag] step2 (input=100) top3: {topA}")

    # step2 with token B（重新开始 cache）
    y1b, cacheB = enc.forward_one_step(lm_input, masks=make_mask(seq_len), cache=None)
    embB = llm.speech_embedding.weight[5000].reshape(1, 1, -1)
    yB, _ = enc.forward_one_step(embB, masks=make_mask(seq_len + 1), cache=cacheB)
    logpB = llm.llm_decoder(yB[:, -1]).log_softmax(dim=-1)
    topB = logpB.topk(3).indices[0].tolist()
    print(f"[diag] step2 (input=5000) top3: {topB}")

    # 如果 A/B 的 top3 差异大，说明 cache 正确；如果相同，cache 有问题
    print(f"[diag] 输入不同输出不同: {topA != topB}")

    # 参考：不用 cache，全量算 step2
    lm_input2 = torch.concat([lm_input, embA], dim=1)
    y_full, _ = enc.forward(lm_input2, torch.tensor([lm_input2.shape[1]]).to(device))
    logp_full = llm.llm_decoder(y_full[:, -1]).log_softmax(dim=-1)
    print(f"[diag] 全量 step2 (input=100) top3: {logp_full.topk(3).indices[0].tolist()}")
    print(f"[diag] cache vs 全量一致: {logp_full.topk(3).indices[0].tolist() == topA}")


if __name__ == "__main__":
    main()

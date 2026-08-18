"""对比 transformers 5.15 原生 Qwen2 generate 与 CosyVoice 逐 token 生成。

如果原生 generate 输出"像 prompt 延续"，说明是 LLM 权重/采样问题；
如果原生 generate 输出正常而 CosyVoice 输出乱，说明 forward_one_step 调用有问题。
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
    qwen = llm.llm.model  # Qwen2ForCausalLM

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
    print(f"[diag] lm_input: {lm_input.shape}")

    # 用原生 generate（inputs_embeds 模式）
    print("[diag] 原生 generate 5 步...")
    with torch.no_grad():
        out = qwen.generate(
            inputs_embeds=lm_input,
            max_new_tokens=5,
            do_sample=True,
            top_k=25,
            top_p=0.8,
            temperature=1.0,
        )
    print(f"[diag] 原生 generate 输出 token: {out[0][-5:].tolist()}")

    # 对比：CosyVoice forward_one_step 第一步
    masks = torch.tril(torch.ones((1, lm_input.shape[1], lm_input.shape[1]), device=device)).to(torch.bool)
    y, cache = llm.llm.forward_one_step(lm_input, masks=masks, cache=None)
    logp = llm.llm_decoder(y[:, -1]).log_softmax(dim=-1)
    top5 = logp.topk(5).indices[0].tolist()
    print(f"[diag] forward_one_step top5: {top5}")

    # 原生 generate 首 token 的 logits
    with torch.no_grad():
        logits = qwen(inputs_embeds=lm_input, use_cache=False).logits[0, -1]
    gen_logp = logits.log_softmax(dim=-1)
    print(f"[diag] 原生首 token top5: {gen_logp.topk(5).indices.tolist()}")


if __name__ == "__main__":
    main()

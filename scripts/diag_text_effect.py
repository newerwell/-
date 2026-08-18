"""测试 text 输入是否影响 LLM 生成。

如果 text 没生效，有无 text 的生成 token 应相似（LLM 纯模仿 prompt）。
"""
import sys
import time

sys.path.insert(0, r"D:\dsh\voice-assistant\cosyvoice_repo")
sys.path.insert(0, r"D:\dsh\voice-assistant")

import torch  # noqa: E402


def run_llm(cv, model_input, device, uuid, use_text=True):
    llm = cv.model.llm
    text = torch.concat([model_input["prompt_text"], model_input["text"]], dim=1) if use_text else model_input["prompt_text"]
    text_len = (model_input["text_len"] + model_input["prompt_text_len"]) if use_text else model_input["prompt_text_len"]
    text_emb = llm.llm.model.model.embed_tokens(text)
    sos_emb = llm.llm_embedding.weight[llm.sos].reshape(1, 1, -1)
    task_id_emb = llm.llm_embedding.weight[llm.task_id].reshape(1, 1, -1)
    prompt_speech_token_emb = llm.speech_embedding(model_input["llm_prompt_speech_token"])
    lm_input = torch.concat([sos_emb, text_emb, task_id_emb, prompt_speech_token_emb], dim=1)

    min_len = int((text_len - model_input["prompt_text_len"]) * 2)
    max_len = int((text_len - model_input["prompt_text_len"]) * 20)
    tokens = []
    cache = None
    cur = lm_input
    for i in range(max_len):
        masks = torch.tril(torch.ones((1, cur.shape[1], cur.shape[1]), device=device)).to(torch.bool)
        y, cache = llm.llm.forward_one_step(cur, masks=masks, cache=cache)
        logp = llm.llm_decoder(y[:, -1]).log_softmax(dim=-1)
        top_ids = llm.sampling_ids(logp.squeeze(0), tokens, 25, ignore_eos=True if i < min_len else False)
        if top_ids in llm.stop_token_ids:
            break
        tokens.append(int(top_ids))
        cur = llm.speech_embedding.weight[top_ids].reshape(1, 1, -1)
    return tokens


def main():
    t0 = time.time()
    from cosyvoice.cli.cosyvoice import CosyVoice2

    cv = CosyVoice2(r"D:\dsh\voice-assistant\models\CosyVoice2-0.5B")
    print(f"[diag] loaded {(time.time()-t0):.1f}s")

    device = cv.model.device
    model_input = cv.frontend.frontend_zero_shot(
        "你好。",
        "欢迎大家来体验达摩院推出的语音识别模型。",
        r"D:\dsh\voice-assistant\output\real_speech.wav",
        24000, "",
    )

    # 有 text
    t_with = run_llm(cv, model_input, device, "with", use_text=True)
    print(f"[diag] 有 text ({len(t_with)}): {t_with[:25]}")

    # 无 text（只 prompt）
    t_without = run_llm(cv, model_input, device, "without", use_text=False)
    print(f"[diag] 无 text ({len(t_without)}): {t_without[:25]}")

    # 对比首 token
    print(f"[diag] 首 token: 有text={t_with[0] if t_with else '?'}, 无text={t_without[0] if t_without else '?'}")


if __name__ == "__main__":
    main()

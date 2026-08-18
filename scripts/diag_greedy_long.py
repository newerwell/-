"""贪心采样 + 更大 max_token_text_ratio 测试完整合成。"""
import sys
import time

sys.path.insert(0, r"D:\dsh\voice-assistant\cosyvoice_repo")
sys.path.insert(0, r"D:\dsh\voice-assistant")

import numpy as np  # noqa: E402
import torch  # noqa: E402
import wave  # noqa: E402


def main():
    t0 = time.time()
    from cosyvoice.cli.cosyvoice import CosyVoice2

    cv = CosyVoice2(r"D:\dsh\voice-assistant\models\CosyVoice2-0.5B")
    print(f"[diag] loaded {(time.time()-t0):.1f}s")

    device = cv.model.device
    llm = cv.model.llm

    model_input = cv.frontend.frontend_zero_shot(
        "今天天气真好。",
        "欢迎大家来体验达摩院推出的语音识别模型。",
        r"D:\dsh\voice-assistant\output\real_speech.wav",
        24000, "",
    )

    # 贪心 + 更大 max_ratio（默认 20，改 30）
    tokens = []
    gen = llm.inference(
        text=model_input["text"].to(device),
        text_len=model_input["text_len"].to(device),
        prompt_text=model_input["prompt_text"].to(device),
        prompt_text_len=model_input["prompt_text_len"].to(device),
        prompt_speech_token=model_input["llm_prompt_speech_token"].to(device),
        prompt_speech_token_len=model_input["llm_prompt_speech_token_len"].to(device),
        embedding=model_input["llm_embedding"].to(device),
        sampling=1,
        max_token_text_ratio=30,
        min_token_text_ratio=10,
        uuid="greedy_long",
    )
    for t in gen:
        if hasattr(t, "item"):
            tokens.append(int(t.item()))
        elif isinstance(t, (list, tuple)):
            tokens.extend(int(x) for x in t)
        else:
            tokens.append(int(t))
    print(f"[diag] tokens: {len(tokens)}: {tokens[:30]}")

    if len(tokens) < 5:
        print("[diag] token 太少")
        return

    token = torch.tensor([tokens], dtype=torch.int32).to(device)
    tts_mel, _ = cv.model.flow.inference(
        token=token,
        token_len=torch.tensor([token.shape[1]], dtype=torch.int32).to(device),
        prompt_token=model_input["flow_prompt_speech_token"].to(device),
        prompt_token_len=torch.tensor([model_input["flow_prompt_speech_token_len"].item()], dtype=torch.int32).to(device),
        prompt_feat=model_input["prompt_speech_feat"].to(device),
        prompt_feat_len=torch.tensor([model_input["prompt_speech_feat_len"].item()], dtype=torch.int32).to(device),
        embedding=model_input["flow_embedding"].to(device),
        streaming=False,
        finalize=True,
    )
    speech, _ = cv.model.hift.inference(
        speech_feat=tts_mel,
        cache_source=torch.zeros(1, 1, 0).to(device),
    )
    sp = speech[0].cpu().numpy()
    print(f"[diag] speech: {sp.shape[0]/24000:.1f}s")

    pcm = (np.clip(sp, -1, 1) * 32767).astype(np.int16)
    with wave.open(r"D:\dsh\voice-assistant\output\cosyvoice_greedy_long.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm.tobytes())
    print("[diag] saved greedy_long.wav")


if __name__ == "__main__":
    main()

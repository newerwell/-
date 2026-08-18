"""最终验证：cross_lingual + 贪心采样，多次测试稳定性。"""
import sys
import time

sys.path.insert(0, r"D:\dsh\voice-assistant\cosyvoice_repo")
sys.path.insert(0, r"D:\dsh\voice-assistant")

import numpy as np  # noqa: E402
import torch  # noqa: E402
import wave  # noqa: E402


def synthesize_greedy(cv, text, prompt_wav):
    """cross_lingual 前端 + 贪心 LLM + flow + hift。"""
    device = cv.model.device
    llm = cv.model.llm
    model_input = cv.frontend.frontend_cross_lingual(text, prompt_wav, 24000, '')

    tokens = []
    # cross_lingual 模式：prompt 相关输入用空张量
    empty_i32 = torch.zeros(1, 0, dtype=torch.int32).to(device)
    empty_len = torch.tensor([0], dtype=torch.int32).to(device)
    gen = llm.inference(
        text=model_input["text"].to(device),
        text_len=model_input["text_len"].to(device),
        prompt_text=empty_i32,
        prompt_text_len=empty_len,
        prompt_speech_token=empty_i32,
        prompt_speech_token_len=empty_len,
        embedding=model_input["llm_embedding"].to(device),
        sampling=1,
        uuid=f"final{time.time()}",
    )
    for t in gen:
        if hasattr(t, "item"):
            tokens.append(int(t.item()))
        elif isinstance(t, (list, tuple)):
            tokens.extend(int(x) for x in t)
        else:
            tokens.append(int(t))
    if len(tokens) < 5:
        return None
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
    return speech[0].cpu().numpy()


def main():
    t0 = time.time()
    from cosyvoice.cli.cosyvoice import CosyVoice2

    cv = CosyVoice2(r"D:\dsh\voice-assistant\models\CosyVoice2-0.5B")
    print(f"[tts] loaded {(time.time()-t0):.1f}s")

    texts = [
        "今天天气真好。",
        "你好，很高兴认识你。",
    ]
    for i, text in enumerate(texts):
        sp = synthesize_greedy(cv, text, r"D:\dsh\voice-assistant\output\prompt_1s.wav")
        if sp is None:
            print(f"[tts] {text}: 无输出")
            continue
        print(f"[tts] {text}: {sp.shape[0]/24000:.1f}s RMS={np.sqrt(np.mean(sp**2)):.3f}")
        pcm = (np.clip(sp, -1, 1) * 32767).astype(np.int16)
        with wave.open(rf"D:\dsh\voice-assistant\output\cosyvoice_final_{i}.wav", "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm.tobytes())
        print(f"[tts] saved final_{i}.wav")

    print(f"\n[tts] 总计 {(time.time()-t0):.1f}s")


if __name__ == "__main__":
    main()

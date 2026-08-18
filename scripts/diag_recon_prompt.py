"""用 prompt token 重新合成 prompt 语音（验证 flow+hift 端到端）。

如果 flow+hift 正常，用 prompt 的 token 合成的语音应接近原 prompt 音频。
"""
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

    model_input = cv.frontend.frontend_zero_shot(
        "你好。",
        "欢迎大家来体验达摩院推出的语音识别模型。",
        r"D:\dsh\voice-assistant\output\real_speech.wav",
        24000, "",
    )
    device = cv.model.device

    # 用 prompt 前半 token 作为"新 token"，后半作为 prompt
    prompt_token = model_input["flow_prompt_speech_token"].to(device)
    prompt_feat = model_input["prompt_speech_feat"].to(device)
    embedding = model_input["flow_embedding"].to(device)
    split = prompt_token.shape[1] // 2
    new_token = prompt_token[:, split:]
    new_prompt_token = prompt_token[:, :split]
    new_prompt_feat = prompt_feat[:, :split * 2]

    print(f"[diag] new_token: {new_token.shape}, prompt: {new_prompt_token.shape}, feat: {new_prompt_feat.shape}")

    tts_mel, _ = cv.model.flow.inference(
        token=new_token,
        token_len=torch.tensor([new_token.shape[1]], dtype=torch.int32).to(device),
        prompt_token=new_prompt_token,
        prompt_token_len=torch.tensor([new_prompt_token.shape[1]], dtype=torch.int32).to(device),
        prompt_feat=new_prompt_feat,
        prompt_feat_len=torch.tensor([new_prompt_feat.shape[1]], dtype=torch.int32).to(device),
        embedding=embedding,
        streaming=False,
        finalize=True,
    )
    print(f"[diag] flow mel: {tts_mel.shape}")

    # hift 合成
    speech, _ = cv.model.hift.inference(
        speech_feat=tts_mel,
        cache_source=torch.zeros(1, 1, 0).to(device),
    )
    sp = speech[0].cpu().numpy()
    print(f"[diag] speech: {sp.shape} ({sp.shape[0]/24000:.1f}s) RMS={np.sqrt(np.mean(sp**2)):.3f}")

    # 保存
    pcm = (np.clip(sp, -1, 1) * 32767).astype(np.int16)
    with wave.open(r"D:\dsh\voice-assistant\output\cosyvoice_recon_prompt.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm.tobytes())
    print("[diag] saved recon_prompt.wav (应该还原 prompt 后一半语音)")


if __name__ == "__main__":
    main()

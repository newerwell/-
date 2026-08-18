"""诊断：flow 输出的 mel 质量。"""
import sys
import time

sys.path.insert(0, r"D:\dsh\voice-assistant\cosyvoice_repo")
sys.path.insert(0, r"D:\dsh\voice-assistant")

import numpy as np  # noqa: E402


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

    # LLM 生成 token
    tokens = []
    gen = cv.model.llm.inference(
        text=model_input["text"].to(device),
        text_len=model_input["text_len"].to(device),
        prompt_text=model_input["prompt_text"].to(device),
        prompt_text_len=model_input["prompt_text_len"].to(device),
        prompt_speech_token=model_input["llm_prompt_speech_token"].to(device),
        prompt_speech_token_len=model_input["llm_prompt_speech_token_len"].to(device),
        embedding=model_input["llm_embedding"].to(device),
        uuid="diag3",
    )
    for t in gen:
        if hasattr(t, "item"):
            tokens.append(int(t.item()))
        elif isinstance(t, (list, tuple)):
            tokens.extend(int(x) for x in t)
        else:
            tokens.append(int(t))
    print(f"[diag] LLM tokens: {len(tokens)}")

    import torch

    token = torch.tensor([tokens], dtype=torch.int32).to(device)
    # 调 flow.inference
    t1 = time.time()
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
    print(f"[diag] flow mel shape: {tts_mel.shape} ({(time.time()-t1):.1f}s)")
    mel = tts_mel[0].cpu().numpy()
    print(f"[diag] mel range: [{mel.min():.3f}, {mel.max():.3f}] mean: {mel.mean():.3f}")
    # 分帧能量
    frame = 24
    energies = [np.sqrt(np.mean(mel[:, i:i+frame]**2)) for i in range(0, mel.shape[1], frame)]
    print(f"[diag] 帧能量: min {min(energies):.4f} max {max(energies):.4f} mean {np.mean(energies):.4f}")
    print(f"[diag] 高能量帧: {sum(1 for e in energies if e > np.mean(energies))}/{len(energies)}")

    # hift 合成
    t2 = time.time()
    speech, source = cv.model.hift.inference(speech_feat=tts_mel, cache_source=torch.zeros(1, 1, 0).to(device))
    print(f"[diag] hift speech shape: {speech.shape} ({(time.time()-t2):.1f}s)")
    sp = speech[0].cpu().numpy()
    print(f"[diag] speech range: [{sp.min():.3f}, {sp.max():.3f}] RMS: {np.sqrt(np.mean(sp**2)):.4f}")


if __name__ == "__main__":
    main()

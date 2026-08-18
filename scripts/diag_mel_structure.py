"""诊断：对比 prompt mel 与生成 mel 的频谱结构。"""
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

    model_input = cv.frontend.frontend_zero_shot(
        "你好。",
        "欢迎大家来体验达摩院推出的语音识别模型。",
        r"D:\dsh\voice-assistant\output\real_speech.wav",
        24000, "",
    )
    device = cv.model.device
    prompt_feat = model_input["prompt_speech_feat"][0].cpu().numpy()
    print(f"[diag] prompt_feat: {prompt_feat.shape}")

    # 看 prompt mel 的频谱轮廓（每帧全频带能量随时间变化）
    frame_energy = np.sqrt(np.mean(prompt_feat**2, axis=0))
    print(f"[diag] prompt 帧能量 (前30): {np.round(frame_energy[:30], 3)}")
    print(f"[diag] prompt 帧能量 std: {np.std(frame_energy):.4f} (变化大=真实语音)")

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
        uuid="diag4",
    )
    for t in gen:
        if hasattr(t, "item"):
            tokens.append(int(t.item()))
        elif isinstance(t, (list, tuple)):
            tokens.extend(int(x) for x in t)
        else:
            tokens.append(int(t))
    print(f"[diag] LLM tokens: {len(tokens)}")

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
    gen_mel = tts_mel[0].cpu().numpy()
    print(f"[diag] 生成 mel: {gen_mel.shape}")
    # 只看新生成部分（去掉 prompt 部分 276 帧）
    new_mel = gen_mel[:, 276:]
    fe = np.sqrt(np.mean(new_mel**2, axis=0))
    print(f"[diag] 新 mel 帧能量: {np.round(fe, 3)}")
    print(f"[diag] 新 mel 帧能量 std: {np.std(fe):.4f}")

    # 检查新 mel 与 prompt mel 的差异（频谱相似性）
    # 计算新 mel 的频带分布
    band_energy = np.sqrt(np.mean(new_mel**2, axis=1))
    pb = np.sqrt(np.mean(prompt_feat**2, axis=1))
    print(f"[diag] 新 mel 频带能量前8: {np.round(band_energy[:8], 3)}")
    print(f"[diag] prompt 频带能量前8: {np.round(pb[:8], 3)}")


if __name__ == "__main__":
    main()

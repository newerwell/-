"""诊断：检查 prompt_feat 与完整 tts 输出。"""
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

    # 检查 prompt 各组件统计
    model_input = cv.frontend.frontend_zero_shot(
        "你好。",
        "欢迎大家来体验达摩院推出的语音识别模型。",
        r"D:\dsh\voice-assistant\output\real_speech.wav",
        24000, "",
    )
    feat = model_input["prompt_speech_feat"][0].cpu().numpy()
    print(f"[diag] prompt_feat shape: {feat.shape}")
    print(f"[diag] prompt_feat range: [{feat.min():.3f}, {feat.max():.3f}] mean: {feat.mean():.3f}")
    # 分帧能量
    frame = 24
    energies = [np.sqrt(np.mean(feat[:, i:i+frame]**2)) for i in range(0, feat.shape[1], frame)]
    print(f"[diag] prompt 帧能量: min {min(energies):.4f} max {max(energies):.4f}")

    # 完整 tts 流程（不走 inference_zero_shot 的循环，直接看 tts）
    print("\n[diag] 完整 tts() 调用...")
    t1 = time.time()
    out = cv.model.tts(
        text=model_input["text"],
        text_len=model_input["text_len"],
        llm_embedding=model_input["llm_embedding"],
        flow_embedding=model_input["flow_embedding"],
        prompt_text=model_input["prompt_text"],
        prompt_text_len=model_input["prompt_text_len"],
        llm_prompt_speech_token=model_input["llm_prompt_speech_token"],
        llm_prompt_speech_token_len=model_input["llm_prompt_speech_token_len"],
        flow_prompt_speech_token=model_input["flow_prompt_speech_token"],
        flow_prompt_speech_token_len=model_input["flow_prompt_speech_token_len"],
        prompt_speech_feat=model_input["prompt_speech_feat"],
        prompt_speech_feat_len=model_input["prompt_speech_feat_len"],
        stream=False,
        speed=1.0,
    )
    for o in out:
        s = o["tts_speech"][0].cpu().numpy()
        print(f"[diag] tts speech: {s.shape} ({(time.time()-t1):.1f}s)")
        print(f"[diag] range: [{s.min():.3f}, {s.max():.3f}] RMS: {np.sqrt(np.mean(s**2)):.4f}")
        # 保存
        import wave

        pcm = (np.clip(s, -1, 1) * 32767).astype(np.int16)
        with wave.open(r"D:\dsh\voice-assistant\output\cosyvoice_tts.wav", "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm.tobytes())
        print("[diag] saved")


if __name__ == "__main__":
    main()

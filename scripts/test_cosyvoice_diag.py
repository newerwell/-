"""诊断 CosyVoice2 合成：检查各阶段输出与音频质量。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, r"D:\dsh\voice-assistant\cosyvoice_repo")

import numpy as np  # noqa: E402


def main():
    t0 = time.time()
    from cosyvoice.cli.cosyvoice import CosyVoice2

    cv = CosyVoice2(r"D:\dsh\voice-assistant\models\CosyVoice2-0.5B")
    print(f"[tts] loaded {(time.time()-t0):.1f}s")

    # 用更短的文本测试
    text = "你好，今天天气不错。"
    prompt_wav = r"D:\dsh\voice-assistant\output\real_speech.wav"
    prompt_text = "欢迎大家来体验达摩院推出的语音识别模型。"

    for output in cv.inference_zero_shot(
        tts_text=text,
        prompt_text=prompt_text,
        prompt_wav=prompt_wav,
        stream=False,
        speed=1.0,
    ):
        speech = output["tts_speech"].numpy()
        print(f"[tts] shape: {speech.shape}, len: {speech.shape[1]/24000:.2f}s")
        print(f"[tts] value range: [{speech.min():.3f}, {speech.max():.3f}]")
        rms = np.sqrt(np.mean(speech**2))
        print(f"[tts] RMS: {rms:.4f}")
        # 分帧能量看是否有明显语音段
        frame = 2400  # 100ms
        energies = [np.sqrt(np.mean(speech[i:i+frame]**2)) for i in range(0, len(speech), frame)]
        active = sum(1 for e in energies if e > 0.01 * rms if rms > 0)
        print(f"[tts] 活跃帧: {active}/{len(energies)}")
        print(f"[tts] 零交叉率: {np.mean(np.abs(np.diff(speech)) > 0.01):.3f}")

        # 保存
        import wave

        pcm = (np.clip(speech, -1, 1) * 32767).astype(np.int16)
        with wave.open(r"D:\dsh\voice-assistant\output\cosyvoice_diag.wav", "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm.tobytes())
        print("[tts] saved cosyvoice_diag.wav")


if __name__ == "__main__":
    main()

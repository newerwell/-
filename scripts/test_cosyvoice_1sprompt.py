"""用 1 秒短 prompt 测试 CosyVoice2（减少 prompt 干扰）。"""
import sys
import time

sys.path.insert(0, r"D:\dsh\voice-assistant\cosyvoice_repo")
sys.path.insert(0, r"D:\dsh\voice-assistant")

import numpy as np  # noqa: E402
import wave  # noqa: E402


def main():
    t0 = time.time()
    from cosyvoice.cli.cosyvoice import CosyVoice2

    cv = CosyVoice2(r"D:\dsh\voice-assistant\models\CosyVoice2-0.5B")
    print(f"[tts] loaded {(time.time()-t0):.1f}s")

    # 从 real_speech 截取前 1 秒做 prompt
    import librosa

    y, sr = librosa.load(r"D:\dsh\voice-assistant\output\real_speech.wav", sr=16000)
    short = y[:16000]
    import soundfile as sf

    sf.write(r"D:\dsh\voice-assistant\output\prompt_1s.wav", short, 16000)

    prompt_text = "欢迎大家来体验达摩院"
    text = "你好，我是小助手。"

    for output in cv.inference_zero_shot(
        tts_text=text,
        prompt_text=prompt_text,
        prompt_wav=r"D:\dsh\voice-assistant\output\prompt_1s.wav",
        stream=False,
        speed=1.0,
    ):
        s = output["tts_speech"][0].numpy()
        print(f"[tts] 1s prompt 输出: {s.shape[0]/24000:.1f}s RMS={np.sqrt(np.mean(s**2)):.3f}")
        pcm = (np.clip(s, -1, 1) * 32767).astype(np.int16)
        with wave.open(r"D:\dsh\voice-assistant\output\cosyvoice_1sprompt.wav", "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm.tobytes())
        print("[tts] saved 1sprompt.wav")

    print(f"\n[tts] 总计 {(time.time()-t0):.1f}s")


if __name__ == "__main__":
    main()

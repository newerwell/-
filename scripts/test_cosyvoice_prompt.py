"""测试 CosyVoice2 不同 prompt 与指令模式。"""
import sys
import time

sys.path.insert(0, r"D:\dsh\voice-assistant\cosyvoice_repo")
sys.path.insert(0, r"D:\dsh\voice-assistant")

import numpy as np  # noqa: E402
import wave  # noqa: E402


def save_wav(path, speech_np, sr=24000):
    pcm = (np.clip(speech_np, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main():
    t0 = time.time()
    from cosyvoice.cli.cosyvoice import CosyVoice2

    cv = CosyVoice2(r"D:\dsh\voice-assistant\models\CosyVoice2-0.5B")
    print(f"[tts] loaded {(time.time()-t0):.1f}s")

    # 1. 最短 prompt 测试：用 1 秒音频做 prompt
    # 从 real_speech.wav 截取前 1 秒
    import torchaudio

    # 生成一个 1 秒的干净 prompt（用 scipy 生成简单音调不合适，直接截取）
    import librosa

    y, sr = librosa.load(r"D:\dsh\voice-assistant\output\real_speech.wav", sr=16000)
    short = y[:16000]
    # 保存为临时 prompt
    import soundfile as sf

    sf.write(r"D:\dsh\voice-assistant\output\prompt_1s.wav", short, 16000)

    text = "你好，我是小助手。"
    for name, prompt_wav, prompt_text in [
        ("1s_prompt", r"D:\dsh\voice-assistant\output\prompt_1s.wav", "欢迎大家来体验达摩院推出的语音识别模型"),
    ]:
        print(f"\n[tts] 测试 {name} ...")
        try:
            for output in cv.inference_zero_shot(
                tts_text=text,
                prompt_text=prompt_text,
                prompt_wav=prompt_wav,
                stream=False,
                speed=1.0,
            ):
                s = output["tts_speech"][0].numpy()
                print(f"[tts] {name}: {s.shape[1]/24000:.1f}s RMS={np.sqrt(np.mean(s**2)):.3f}")
                save_wav(rf"D:\dsh\voice-assistant\output\cosyvoice_{name}.wav", s)
        except Exception as e:
            print(f"[tts] {name} FAIL: {e}")

    print(f"\n[tts] 总计 {(time.time()-t0):.1f}s")


if __name__ == "__main__":
    main()

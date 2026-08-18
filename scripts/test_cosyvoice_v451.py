"""transformers 4.51.3 下完整测试 CosyVoice2 多文本合成。"""
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

    texts = [
        "大家好，我是你的语音助手。",
        "今天天气真不错，适合出去走走。",
    ]
    for i, text in enumerate(texts):
        print(f"\n[tts] 文本{i}: {text}")
        for output in cv.inference_zero_shot(
            tts_text=text,
            prompt_text="欢迎大家来体验达摩院推出的语音识别模型。",
            prompt_wav=r"D:\dsh\voice-assistant\output\real_speech.wav",
            stream=False,
            speed=1.0,
        ):
            s = output["tts_speech"][0].numpy()
            print(f"[tts] 输出: {s.shape[0]/24000:.1f}s RMS={np.sqrt(np.mean(s**2)):.3f}")
            pcm = (np.clip(s, -1, 1) * 32767).astype(np.int16)
            with wave.open(rf"D:\dsh\voice-assistant\output\cosyvoice_v451_{i}.wav", "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(24000)
                w.writeframes(pcm.tobytes())
            print(f"[tts] saved v451_{i}.wav")

    print(f"\n[tts] 总计 {(time.time()-t0):.1f}s")


if __name__ == "__main__":
    main()

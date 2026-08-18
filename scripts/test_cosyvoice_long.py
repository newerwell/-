"""用更长文本测试 CosyVoice2 合成质量。"""
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

    # 更长文本，多次尝试
    texts = [
        "大家好，我是你的语音助手，很高兴认识你。",
        "北京今天天气晴朗，气温二十五度，适合出门散步。",
    ]
    prompt_wav = r"D:\dsh\voice-assistant\output\real_speech.wav"
    prompt_text = "欢迎大家来体验达摩院推出的语音识别模型。"

    for i, text in enumerate(texts):
        print(f"\n[tts] 文本{i}: {text}")
        try:
            got = False
            for output in cv.inference_zero_shot(
                tts_text=text,
                prompt_text=prompt_text,
                prompt_wav=prompt_wav,
                stream=False,
                speed=1.0,
            ):
                s = output["tts_speech"][0].numpy()
                dur = s.shape[0] / 24000
                rms = np.sqrt(np.mean(s**2))
                print(f"[tts] 输出: {dur:.1f}s RMS={rms:.3f}")
                # 谐波检查：计算频谱峰值（语音有谐波结构）
                from numpy.fft import rfft

                seg = s[int(0.2*24000):int(0.4*24000)] if len(s) > 0.5*24000 else s[:9600]
                spec = np.abs(rfft(seg * np.hanning(len(seg))))
                # 检查 100-500Hz 基频区是否有能量
                f0_band = spec[100:500]
                print(f"[tts] 基频带能量: {np.mean(f0_band):.2f} (语音应>1)")
                pcm = (np.clip(s, -1, 1) * 32767).astype(np.int16)
                with wave.open(rf"D:\dsh\voice-assistant\output\cosyvoice_long{i}.wav", "wb") as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(24000)
                    w.writeframes(pcm.tobytes())
                print(f"[tts] saved long{i}.wav")
                got = True
            if not got:
                print("[tts] 无输出")
        except Exception as e:
            print(f"[tts] FAIL: {type(e).__name__}: {e}")

    print(f"\n[tts] 总计 {(time.time()-t0):.1f}s")


if __name__ == "__main__":
    main()

"""CosyVoice2 合成测试：生成中文语音并保存 wav。

零样本模式：需要 prompt_text + prompt_wav（参考语音）。
这里先用一个合成/下载的参考音频，或尝试无参考路径。
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, r"D:\dsh\voice-assistant\cosyvoice_repo")

import numpy as np  # noqa: E402
from scipy.io import wavfile  # noqa: E402

MODEL_DIR = r"D:\dsh\voice-assistant\models\CosyVoice2-0.5B"
OUT = r"D:\dsh\voice-assistant\output\cosyvoice_test.wav"


def main():
    t0 = time.time()
    from cosyvoice.cli.cosyvoice import CosyVoice2

    cv = CosyVoice2(MODEL_DIR, load_jit=False, load_trt=False, fp16=False)
    print(f"[tts] 模型加载完成 {(time.time()-t0):.1f}s")

    text = "大家好，我是你的语音助手，很高兴认识你！"
    print(f"[tts] 合成: {text}")

    # CosyVoice2 需要参考音频做零样本；尝试用 real_speech.wav 作为 prompt
    prompt_wav = r"D:\dsh\voice-assistant\output\real_speech.wav"
    prompt_text = "欢迎大家来体验达摩院推出的语音识别模型。"

    t1 = time.time()
    try:
        for output in cv.inference_zero_shot(
            tts_text=text,
            prompt_text=prompt_text,
            prompt_wav=prompt_wav,
            stream=False,
            speed=1.0,
        ):
            speech = output["tts_speech"]
            print(f"[tts] 生成语音长度: {speech.shape[1]/24000:.1f}s ({(time.time()-t1):.1f}s)")
            data = speech.numpy()
            if data.ndim > 1:
                data = data.squeeze()
            data = np.clip(data, -1.0, 1.0)
            pcm = (data * 32767).astype(np.int16)
            import wave

            with wave.open(OUT, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(24000)
                w.writeframes(pcm.tobytes())
            print(f"[tts] 已保存: {OUT} ({Path(OUT).stat().st_size/1024:.0f} KB)")
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise

    print(f"[tts] 总计 {(time.time()-t0):.1f}s")


if __name__ == "__main__":
    main()

"""语音合成（TTS）。

M5：优先 CosyVoice2-0.5B（本地 GPU 高质量），SAPI 兜底。

CosyVoice2 依赖 transformers 4.51.3（已绕过版本检查），
用 cross_lingual 模式 + 贪心采样提升内容准确度。
"""
import time
from pathlib import Path

from .config import OUTPUT_DIR


class Synthesizer:
    """统一 TTS 接口：优先 CosyVoice2，降级 SAPI。"""

    def __init__(self, prompt_wav: str = ""):
        self._cv = None
        self._sapi = None
        self._mode = None
        self.prompt_wav = prompt_wav or str(Path(__file__).resolve().parent.parent / "output" / "prompt_1s.wav")
        self._init_cosyvoice()

    def _init_cosyvoice(self):
        try:
            import transformers

            # CosyVoice2 的 LLM 依赖 transformers 4.51.x（5.15 下内容生成错误）
            ver = transformers.__version__
            if not ver.startswith("4.51"):
                print(f"[tts] transformers {ver} 不兼容 CosyVoice2（需要 4.51.x），使用 SAPI 兜底")
                self._mode = "sapi"
                return

            import sys

            # 确保 cosyvoice_repo 可导入（含官方推理代码）
            repo = Path(__file__).resolve().parent.parent / "cosyvoice_repo"
            if str(repo) not in sys.path:
                sys.path.insert(0, str(repo))

            from .config import TTS_MODEL_DIR, DEVICE

            print(f"[tts] loading CosyVoice2 from {TTS_MODEL_DIR} ...")
            t0 = time.time()
            from cosyvoice.cli.cosyvoice import CosyVoice2

            self._cv = CosyVoice2(TTS_MODEL_DIR, load_jit=False, load_trt=False, fp16=False)
            self._mode = "cosyvoice"
            print(f"[tts] CosyVoice2 ready in {time.time()-t0:.1f}s")
        except Exception as e:
            print(f"[tts] CosyVoice2 unavailable ({e}); will use SAPI fallback")
            self._mode = "sapi"

    def _init_sapi(self):
        if self._sapi is None:
            import pyttsx3

            self._sapi = pyttsx3.init()
            for v in self._sapi.getProperty("voices"):
                if "ZH" in v.id.upper() or "Huihui" in v.name or "Yaoyao" in v.name:
                    self._sapi.setProperty("voice", v.id)
                    break
            self._sapi.setProperty("rate", 180)

    def synthesize(self, text: str, out_path: str | None = None, prompt_speech: str | None = None) -> str:
        """合成语音，返回 wav 文件路径。

        CosyVoice2：cross_lingual 模式（贪心采样）。
        SAPI：实时朗读（返回空字符串）。
        """
        if self._mode == "cosyvoice":
            return self._synthesize_cosyvoice(text, out_path, prompt_speech)
        self._init_sapi()
        print(f"[tts] (SAPI) 朗读: {text}")
        self._sapi.say(text)
        self._sapi.runAndWait()
        return ""

    def _synthesize_cosyvoice(self, text, out_path, prompt_speech):
        import torch

        cv = self._cv
        device = cv.model.device
        llm = cv.model.llm
        prompt_wav = prompt_speech or self.prompt_wav
        prompt_text = "欢迎大家来体验达摩院"  # 与 prompt_1s.wav 内容对应

        # zero_shot 模式：有 prompt 文本上下文，生成更稳定
        model_input = cv.frontend.frontend_zero_shot(text, prompt_text, prompt_wav, 24000, "")
        if "text" not in model_input or model_input["text"].shape[1] == 0:
            raise RuntimeError("文本编码失败")

        # LLM 贪心采样生成 speech token
        tokens = []
        gen = llm.inference(
            text=model_input["text"].to(device),
            text_len=model_input["text_len"].to(device),
            prompt_text=model_input["prompt_text"].to(device),
            prompt_text_len=model_input["prompt_text_len"].to(device),
            prompt_speech_token=model_input["llm_prompt_speech_token"].to(device),
            prompt_speech_token_len=model_input["llm_prompt_speech_token_len"].to(device),
            embedding=model_input["llm_embedding"].to(device),
            sampling=1,  # 贪心，提升内容准确度
            uuid=f"tts{time.time()}",
        )
        for t in gen:
            if hasattr(t, "item"):
                tokens.append(int(t.item()))
            elif isinstance(t, (list, tuple)):
                tokens.extend(int(x) for x in t)
            else:
                tokens.append(int(t))
        if len(tokens) < 5:
            raise RuntimeError(f"LLM 生成 token 过少: {len(tokens)}")

        # flow + hift 合成
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
        speech, _ = cv.model.hift.inference(
            speech_feat=tts_mel,
            cache_source=torch.zeros(1, 1, 0).to(device),
        )
        sp = speech[0].cpu().numpy()

        import numpy as np
        import wave

        if out_path is None:
            out_path = str(OUTPUT_DIR / "tts_output.wav")
        pcm = (np.clip(sp, -1, 1) * 32767).astype(np.int16)
        with wave.open(out_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm.tobytes())
        return out_path


_inst = None


def get_synthesizer() -> Synthesizer:
    global _inst
    if _inst is None:
        _inst = Synthesizer()
    return _inst

"""诊断 CosyVoice2：检查 LLM token 输出与 prompt 处理。"""
import sys
import time

sys.path.insert(0, r"D:\dsh\voice-assistant\cosyvoice_repo")
sys.path.insert(0, r"D:\dsh\voice-assistant")

import numpy as np  # noqa: E402


def main():
    t0 = time.time()
    from cosyvoice.cli.cosyvoice import CosyVoice2

    cv = CosyVoice2(r"D:\dsh\voice-assistant\models\CosyVoice2-0.5B")
    print(f"[tts] loaded {(time.time()-t0):.1f}s")

    # 用 frontend 手动构造输入，检查各组件
    text = "你好，今天天气不错。"
    prompt_wav = r"D:\dsh\voice-assistant\output\real_speech.wav"
    prompt_text = "欢迎大家来体验达摩院推出的语音识别模型。"

    model_input = cv.frontend.frontend_zero_shot(text, prompt_text, prompt_wav, 24000, '')
    for k, v in model_input.items():
        if hasattr(v, "shape"):
            print(f"[diag] {k}: shape={v.shape} dtype={v.dtype}")
        else:
            print(f"[diag] {k}: {v}")

    # 手动调用 llm 推理
    print("\n[diag] 调用 LLM 推理...")
    t1 = time.time()
    llm_input = {k: model_input[k] for k in model_input if k.startswith(("text", "prompt", "llm"))}
    llm_input.pop("prompt_speech_feat", None)
    llm_input.pop("prompt_speech_feat_len", None)
    llm_input.pop("flow_embedding", None)
    llm_input.pop("llm_embedding", None)
    # 修正：llm_embedding 需要
    llm_input["llm_embedding"] = model_input["llm_embedding"]

    token_generator = cv.model.llm.inference(
        text=model_input["text"],
        text_len=model_input["text_len"],
        prompt_text=model_input["prompt_text"],
        prompt_text_len=model_input["prompt_text_len"],
        prompt_speech_token=model_input["llm_prompt_speech_token"],
        prompt_speech_token_len=model_input["llm_prompt_speech_token_len"],
        embedding=model_input["llm_embedding"],
        uuid="diag",
    )
    # 收集 token
    all_tokens = []
    for t in token_generator:
        all_tokens.extend(t)
    print(f"[diag] LLM token 数: {len(all_tokens)} ({(time.time()-t1):.1f}s)")
    print(f"[diag] token 范围: [{min(all_tokens)}, {max(all_tokens)}]")
    uniq = len(set(all_tokens))
    print(f"[diag] 唯一 token 数: {uniq}")
    print(f"[diag] 前 30: {all_tokens[:30]}")


if __name__ == "__main__":
    main()

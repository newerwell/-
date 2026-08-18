"""验证 speech_tokenizer：解码 prompt token 应还原接近原语音。

如果 speech_tokenizer_v2.onnx 工作正常，从 prompt 提取的 token 应能解码回语音。
这验证 token 空间是否正确。
"""
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

    # 1. 从 prompt 提取 speech token
    tok, tok_len = cv.frontend._extract_speech_token(r"D:\dsh\voice-assistant\output\real_speech.wav")
    print(f"[diag] prompt speech token: {tok.shape} len={tok_len}")

    # 2. 检查 speech_tokenizer onnx 的输入输出
    sess = cv.frontend.speech_tokenizer_session
    print(f"[diag] speech_tokenizer inputs: {[i.name for i in sess.get_inputs()]}")
    print(f"[diag] speech_tokenizer outputs: {[o.name for o in sess.get_outputs()]}")

    # 3. 检查 campplus 输出维度（spk embedding 应 192 维）
    sess2 = cv.frontend.campplus_session
    print(f"[diag] campplus outputs: {[o.name for o in sess2.get_outputs()]}")

    # 4. 用 LLM 生成 token 并与 prompt token 对比分布
    model_input = cv.frontend.frontend_zero_shot(
        "你好。",
        "欢迎大家来体验达摩院推出的语音识别模型。",
        r"D:\dsh\voice-assistant\output\real_speech.wav",
        24000, "",
    )
    print(f"[diag] llm_embedding shape: {model_input['llm_embedding'].shape}")

    # 检查 speech_embedding 权重的取值（如果全 0 或 NaN，token 映射就错）
    se = cv.model.llm.speech_embedding.weight
    print(f"[diag] speech_embedding: shape={se.shape} nan={torch.isnan(se).any().item()} range=[{se.min():.3f},{se.max():.3f}]")
    # 检查 prompt token 索引处的 embedding 是否非零
    pt = model_input["llm_prompt_speech_token"][0]
    emb = se[pt]
    print(f"[diag] prompt token embedding: mean_abs={emb.abs().mean():.4f}")

    # 5. 检查 flow 的 input_embedding（token→flow 空间）
    fe = cv.model.flow.input_embedding.weight
    print(f"[diag] flow input_embedding: shape={fe.shape} nan={torch.isnan(fe).any().item()}")

    # 6. LLM decoder 输出维度检查（应 6561+3=6564）
    ld = cv.model.llm.llm_decoder
    print(f"[diag] llm_decoder: {ld.weight.shape} (期望 [6564, 896])")


if __name__ == "__main__":
    main()

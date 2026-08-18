"""检查 flow encoder 输出形状（h 是否包含 prompt）。"""
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

    model_input = cv.frontend.frontend_zero_shot(
        "你好。",
        "欢迎大家来体验达摩院推出的语音识别模型。",
        r"D:\dsh\voice-assistant\output\real_speech.wav",
        24000, "",
    )
    device = cv.model.device
    flow = cv.model.flow

    prompt_token = model_input["flow_prompt_speech_token"].to(device)
    prompt_feat = model_input["prompt_speech_feat"].to(device)
    embedding = model_input["flow_embedding"].to(device)
    print(f"[diag] prompt_token: {prompt_token.shape}")
    print(f"[diag] prompt_feat: {prompt_feat.shape}")

    # 手动复现 flow.inference 的 encoder 部分
    token = torch.tensor([[1, 2, 3, 4]], dtype=torch.int32).to(device)  # 模拟新 token
    token_len = torch.tensor([4], dtype=torch.int32).to(device)
    prompt_token_len = torch.tensor([prompt_token.shape[1]], dtype=torch.int32).to(device)

    cat_token = torch.concat([prompt_token, token], dim=1)
    cat_len = prompt_token_len + token_len
    print(f"[diag] 拼接后 token: {cat_token.shape}, len: {cat_len}")

    mask = (~make_pad_mask(cat_len)).unsqueeze(-1).to(embedding)
    emb = flow.input_embedding(torch.clamp(cat_token, min=0)) * mask
    print(f"[diag] embedding: {emb.shape}")

    h, h_lengths = flow.encoder(emb, cat_len, streaming=False)
    print(f"[diag] encoder h: {h.shape}, h_lengths: {h_lengths}")

    mel_len1, mel_len2 = prompt_feat.shape[1], h.shape[1] - prompt_feat.shape[1]
    print(f"[diag] mel_len1(prompt): {mel_len1}, mel_len2(new): {mel_len2}")


if __name__ == "__main__":
    from cosyvoice.utils.mask import make_pad_mask

    main()

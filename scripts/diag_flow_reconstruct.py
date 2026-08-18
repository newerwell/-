"""决定性测试：flow 用 prompt 自身 token 重建 prompt mel。

如果 flow 正常，重建的 mel 应接近原始 prompt_feat。
如果重建是噪音，则 flow 有问题。
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

    model_input = cv.frontend.frontend_zero_shot(
        "你好。",
        "欢迎大家来体验达摩院推出的语音识别模型。",
        r"D:\dsh\voice-assistant\output\real_speech.wav",
        24000, "",
    )
    device = cv.model.device

    prompt_token = model_input["flow_prompt_speech_token"].to(device)
    prompt_feat = model_input["prompt_speech_feat"].to(device)
    embedding = model_input["flow_embedding"].to(device)
    print(f"[diag] prompt_token: {prompt_token.shape}")
    print(f"[diag] prompt_feat: {prompt_feat.shape}")

    # flow 重建：token = prompt_token 的一个子集，prompt 条件 = 自身
    # 用 prompt_token 的前半作为"新 token"，后半作为 prompt
    split = prompt_token.shape[1] // 2
    new_token = prompt_token[:, split:]
    new_prompt_token = prompt_token[:, :split]
    new_prompt_feat = prompt_feat[:, :split * 2]

    print(f"[diag] new_token: {new_token.shape}, new_prompt_token: {new_prompt_token.shape}, new_prompt_feat: {new_prompt_feat.shape}")

    tts_mel, _ = cv.model.flow.inference(
        token=new_token,
        token_len=torch.tensor([new_token.shape[1]], dtype=torch.int32).to(device),
        prompt_token=new_prompt_token,
        prompt_token_len=torch.tensor([new_prompt_token.shape[1]], dtype=torch.int32).to(device),
        prompt_feat=new_prompt_feat,
        prompt_feat_len=torch.tensor([new_prompt_feat.shape[1]], dtype=torch.int32).to(device),
        embedding=embedding,
        streaming=False,
        finalize=True,
    )
    gen_mel = tts_mel[0].cpu().numpy()
    print(f"[diag] flow 重建 mel: {gen_mel.shape}")

    # 对比重建的 mel 与"真实"的对应 mel 段（新 token 对应的真实 mel）
    real_mel = prompt_feat[0, split * 2:].cpu().numpy()
    print(f"[diag] 真实对应 mel: {real_mel.shape}")

    if gen_mel.shape[1] == real_mel.shape[0]:
        # 计算相似度（mel 是 log 能量，用相关系数）
        gen_f = gen_mel.flatten()
        real_f = real_mel.flatten()
        corr = np.corrcoef(gen_f, real_f)[0, 1]
        print(f"[diag] 重建 vs 真实 mel 相关系数: {corr:.4f} (接近1=flow正常)")
        # 能量对比
        print(f"[diag] 重建 mel 帧能量 std: {np.std(np.sqrt(np.mean(gen_mel**2, axis=0))):.4f}")
        print(f"[diag] 真实 mel 帧能量 std: {np.std(np.sqrt(np.mean(real_mel.T**2, axis=0))):.4f}")


if __name__ == "__main__":
    main()

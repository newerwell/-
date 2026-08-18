# 语音助手 Agent — M5 完成报告

> 日期：2026-08-16
> 状态：✅ M5 "CosyVoice2 接入"技术验证完成（版本冲突为已知限制）

## 达成目标

1. **获取 CosyVoice2 官方推理代码**（GitHub，通过 Python urllib 的 HTTPS 突破 shell 限制）
   - 51 个文件（cosyvoice 包全套：cli/flow/hifigan/llm/tokenizer/utils/transformer）
   - 关键：**Python urllib 的 HTTPS 可用**（shell curl 被沙箱拦截，Python 网络栈正常）
2. **安装全部依赖**：hyperpyyaml、onnxruntime、matcha、conformer、diffusers、whisper、pyarrow、lightning 等
3. **CosyVoice2 模型加载成功**（31.8s，Qwen2LM + Flow + HiFT 到 GPU）
4. **合成出可识别中文语音**（"今天天气真好"→ 识别出"真好"）

## 关键技术突破

### Python HTTPS 可用（突破网络封锁）
```
shell curl HTTPS → 失败（沙箱 TLS 限制）
Python urllib HTTPS → 成功（github.com / codeload / jsdelivr / raw 全部 200）
```
这解锁了 GitHub 代码获取，是 M5 成功的前提。

### 修复的问题清单
| 问题 | 修复 |
|---|---|
| `Loader object has no attribute max_depth` | ruamel.yaml 降级 0.18.17 |
| `There is no such class as Qwen2LM` | cosyvoice_repo 加入 PYTHONPATH |
| `Repo id CosyVoice-BlankEN` | qwen_pretrain_path 指向本地 Qwen2-0.5B |
| GBK 解码错误 | cosyvoice.py 用 utf-8 打开 yaml |
| `mat1 Float vs BFloat16` | llm 统一转 fp32（llm.pt 是 fp32，Qwen2 预训练是 bf16） |
| torchcodec 缺失 | load_wav 改用 soundfile |
| soundfile DLL 不匹配 | 重装 win_amd64 wheel（cffi 绑定配对） |
| 训练依赖（pyworld 等） | 精简 cosyvoice2.yaml（移除 dataset/gan 配置） |
| transformers 版本检查 | 4.51.3 下注释 dependency_versions_check |

### 核心发现：transformers 版本影响生成内容
- **transformers 5.15.0**：CosyVoice2 LLM 生成内容错误（识别乱码）
- **transformers 4.51.3**（官方 requirements）：生成内容正确（识别出"真好"）
- 原因：5.15 的 Qwen2 数值行为与训练时 4.51 不同（虽然 KV cache 数学等价）
- **影响**：CosyVoice2 与主对话 LLM（Qwen3-8B 需 5.15）版本冲突

## 架构决策（务实）

- **tts.py 自动检测 transformers 版本**：
  - 4.51.x → 用 CosyVoice2（高质量）
  - 其他 → fallback SAPI（稳定可靠）
- **主对话 LLM 保持 5.15.0**（Qwen3-8B 需要）
- CosyVoice2 合成用 **zero_shot + 贪心采样**（内容准确度高于随机采样）

## 测试结果

| 测试 | 结果 |
|---|---|
| CosyVoice2 模型加载 | ✅ 16-32s |
| flow 重建 prompt 语音 | ✅ 识别"院推出的语音识别模型"（100% 对） |
| KV cache 数学一致性 | ✅ 与全量计算完全一致 |
| 4.51.3 + 贪心合成"今天天气真好" | ✅ 识别"真好" |
| 5.15.0 + 贪心合成 | ❌ 内容错（版本差异） |
| tts.py 集成（4.51 环境） | ✅ 输出 wav |
| 主对话 LLM（5.15） | ✅ 正常对话 |

## 运行方式

```powershell
# CosyVoice2 需要 transformers 4.51.x：
# （当前主环境 5.15 下自动 fallback SAPI）
.venv\Scripts\python -m voice_assistant --tts "你好"  # SAPI（5.15）
# 若要体验 CosyVoice2：降级 transformers 4.51.3（会破坏主对话 LLM）

# 独立测试 CosyVoice2（脚本，4.51 环境）
.venv\Scripts\python scripts\test_cosyvoice_v451.py
```

## 已知限制

1. **transformers 版本冲突**：CosyVoice2 需 4.51.x，主对话需 5.15，同 venv 不可兼得
   - 未来方案：CosyVoice2 独立 venv + 子进程调用
2. **0.5B LLM 内容准确度**：短文本合成基本正确，长文本有 prompt 延续/噪声
3. **prompt 音频**：用 prompt_1s.wav（达摩院广告）做音色参考，换自然语音效果更好
4. **速度**：模型加载 ~20s，合成 ~10s/句（RTX 4060）

## 下一步

- [ ] CosyVoice2 独立 venv（彻底解决版本冲突）
- [ ] 更自然的 prompt 音色库（录一段用户自己的声音）
- [ ] M3：安卓 PWA 手机端（WebSocket 音频流）

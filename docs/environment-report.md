# 语音助手 Agent — 环境检测报告

> 检测时间：2026-08-16
> 目的：确认"全本地离线 + 中文 + RTX 4060"方案的硬件/软件前提

## 硬件

| 项目 | 结果 | 说明 |
|---|---|---|
| GPU | NVIDIA GeForce RTX 4060 Laptop, 8GB 显存 | 驱动 591.74，支持 CUDA 13.1 |
| GPU 当前占用 | ~2.6GB（桌面程序：QQ/Edge/壁纸引擎/模拟器等） | 跑模型前建议关闭壁纸引擎、MuMu 模拟器 |
| 可用显存 | ~5.5GB | 决定 LLM 需用 4bit 量化 |
| CPU / 内存 | （未详细检测） | — |
| 磁盘 C: | 剩余 381.2 GB / 总 953.2 GB | 充足 |
| 磁盘 D: | 剩余 442.5 GB / 总 953.9 GB | 充足，模型建议放 D 盘 |

## 软件

| 项目 | 结果 | 说明 |
|---|---|---|
| Python | 3.12.7（D:\adconda） | conda 24.11.3，pip 24.2 |
| Git | 2.54.0 | ✅ |
| PyTorch（基础环境） | 2.12.1 **+cpu** | ⚠️ CPU 版，**CUDA 不可用，需重装** |
| CUDA 版 PyTorch | 安装到独立环境 `voice-assistant`（cu128 wheel） | ✅ 完成 |

## ⚠️ 网络环境（重要发现）

本机沙箱/网络环境**拦截 HTTPS 出站**（TCP 443 可连通但 TLS 握手失败），**只允许 HTTP 明文**。
- ❌ `https://pypi.org`、`https://download.pytorch.org`、清华 TUNA、阿里云 HTTPS 均失败
- ✅ `http://mirrors.aliyun.com/pypi/simple/` 可用（实测 391KB/s 索引页 / 8.7MB/s 大文件）
- ✅ `http://mirrors.aliyun.com/pytorch-wheels/cu128/` 可用（torch 2.10.0+cu128 等）
- 系统配置了代理 `127.0.0.1:7897` 但未运行（Clash 类，ProxyEnable=0）
- pip 访问 HTTPS 索引时会**长时间卡死**（CPU 100%）；且 pip 网络下载写临时目录被沙箱拒绝 → **必须 curl/urllib 下载 wheel 到本地，再 pip 本地安装**
- 包名注意：阿里云 simple 索引对下划线包名（如 typing_extensions）返回 404，需用连字符（typing-extensions）

## ✅ 实际安装结果（已全部验证）

| 组件 | 版本 | 状态 |
|---|---|---|
| venv | D:\dsh\voice-assistant\.venv (python 3.12.7) | ✅ |
| pip | 24.2（从基础环境复制） | ✅ |
| torch | 2.10.0+cu128 | ✅ CUDA available: True |
| GPU 识别 | NVIDIA GeForce RTX 4060 Laptop GPU | ✅ |
| CUDA runtime | 12.8（cublas/cudnn/cufft 等 2.5GB DLL 已打包在 wheel 内） | ✅ |
| numpy | 2.5.2 | ✅ |
| 其他依赖 | filelock, typing_extensions, sympy 1.14, networkx 3.6, jinja2 3.1, fsspec, setuptools, mpmath, markupsafe | ✅ |

**验证命令**（输出应为 True）：
```powershell
& D:\dsh\voice-assistant\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available())"
```

**踩坑记录**：
1. conda 无法创建环境（沙箱禁止写 D:\adconda\envs）→ 用 venv 替代
2. venv ensurepip 失败 → 从基础环境复制 pip
3. HTTPS 全被拦截 → 用阿里云 HTTP 镜像
4. pip 下载写临时目录被拒 → 用 urllib 下载 wheel，pip 本地安装
5. sympy 1.14 与 mpmath 1.4.1 冲突 → pip 用 --no-deps

## 安装步骤（可复现）

```powershell
python -m venv --without-pip D:\dsh\voice-assistant\.venv
Copy-Item D:\adconda\Lib\site-packages\pip D:\dsh\voice-assistant\.venv\Lib\site-packages\ -Recurse
Copy-Item D:\adconda\Lib\site-packages\pip-24.2.dist-info D:\dsh\voice-assistant\.venv\Lib\site-packages\ -Recurse
# 下载 wheel（脚本见 scripts\download_wheels.ps1 / download_deps.py / download_numpy.py）
# 本地安装：
.venv\Scripts\python -m pip install --no-deps --no-index --find-links wheels\deps <pkg...>
.venv\Scripts\python -m pip install --no-deps wheels\torch-2.10.0+cu128-cp312-cp312-win_amd64.whl
```

## 方案约束（由环境决定）

- LLM 选型上限：**Qwen3-8B 4bit 量化（~5GB 显存）**；升级 14B 需 6bit 量化并关闭其他 GPU 应用
- 全链路模型：openWakeWord（唤醒）+ SenseVoice（STT）+ Qwen3-8B（LLM）+ sherpa-onnx TTS（首版）
- 所有模型均可装入 D 盘（剩余 442GB）

## 待办

- [x] 验证 CUDA 版 torch 安装成功（`torch.cuda.is_available()` = True）— **2026-08-16 完成**
- [ ] 下载模型（总量约 10~12GB）：SenseVoice / Qwen3-8B / 唤醒词 / TTS
- [ ] 搭建 M1：命令行"说一句答一句"全链路

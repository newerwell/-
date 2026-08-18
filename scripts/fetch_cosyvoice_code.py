"""Download CosyVoice inference code from GitHub (Python HTTPS works).

只下载推理所需的核心代码：
- cosyvoice/ 整个包（cli/model/flow/hifigan/tokenizer 等）
- requirements.txt
- 用 codeload tarball 一次拿全，解压后保留 cosyvoice 包
"""
import io
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

OUT = Path(r"D:\dsh\voice-assistant\cosyvoice_repo")
OUT.mkdir(parents=True, exist_ok=True)

url = "https://codeload.github.com/FunAudioLLM/CosyVoice/tar.gz/refs/heads/main"
print(f"downloading {url} ...")
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=600) as resp:
    data = resp.read()
print(f"  got {len(data)/1e6:.1f} MB")

# 解压
import tarfile as tf

tf_io = io.BytesIO(data)
with tarfile.open(fileobj=tf_io, mode="r:gz") as tar:
    names = tar.getnames()
    print(f"  archive entries: {len(names)}")
    # 提取到临时目录
    tmp = OUT / "_raw"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    tar.extractall(tmp)

# 找到顶层目录
tops = [p for p in tmp.iterdir() if p.is_dir()]
print("  top dirs:", [p.name for p in tops])
src = tops[0]
print("  source root:", src)

# 复制 cosyvoice 包
dst_pkg = OUT / "cosyvoice"
if dst_pkg.exists():
    shutil.rmtree(dst_pkg)
shutil.copytree(src / "cosyvoice", dst_pkg)

# 复制 requirements
req_src = src / "requirements.txt"
if req_src.exists():
    shutil.copy2(req_src, OUT / "requirements.txt")
    print("  requirements.txt copied")

# 清理
shutil.rmtree(tmp)
print("\n=== done ===")
n = sum(1 for _ in dst_pkg.rglob("*") if _.is_file())
print(f"cosyvoice package files: {n}")

"""Download complete CosyVoice inference code via jsdelivr CDN (fast).

覆盖 cosyvoice 包全部 .py 文件 + requirements + tokenizer assets。
"""
import json
import time
import urllib.request
from pathlib import Path

# 1. 从 GitHub API 拿完整文件树
API = "https://api.github.com/repos/FunAudioLLM/CosyVoice/git/trees/main?recursive=1"
req = urllib.request.Request(API, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=60) as resp:
    tree = json.loads(resp.read())["tree"]

# 保留 cosyvoice/ 下的所有文件 + requirements.txt + setup.py
keep_prefixes = ("cosyvoice/",)
files = []
for t in tree:
    if t["type"] != "blob":
        continue
    p = t["path"]
    if p.startswith(keep_prefixes) or p in ("requirements.txt",):
        files.append(p)
print(f"total files to fetch: {len(files)}")

OUT = Path(r"D:\dsh\voice-assistant\cosyvoice_repo")
ok, fail = 0, 0
for i, f in enumerate(files):
    dest = OUT / f
    if dest.exists() and dest.stat().st_size > 100:
        ok += 1
        continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://cdn.jsdelivr.net/gh/FunAudioLLM/CosyVoice@main/{f}"
    got = False
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            dest.write_bytes(data)
            ok += 1
            got = True
            break
        except Exception as e:
            time.sleep(2)
    if not got:
        fail += 1
        print(f"FAIL {f}")
    if (i + 1) % 25 == 0:
        print(f"  progress {i+1}/{len(files)}")

print(f"\n=== done: {ok} ok, {fail} fail ===")

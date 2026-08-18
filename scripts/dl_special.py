"""Download bitsandbytes 0.43.0 win_amd64 + sherpa-onnx-core wheels."""
import re
import urllib.request
from pathlib import Path

MIRROR = "http://mirrors.aliyun.com/pypi"
OUT = Path(r"D:\dsh\voice-assistant\wheels\closure")
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "curl/8.0"}


def fetch(url: str, timeout=300) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_latest(pkg: str, needle: str):
    html = fetch(f"{MIRROR}/simple/{pkg}/", 60).decode("utf-8", "ignore")
    for m in re.finditer(r'href="([^"]+\.whl)(?:[#"]|$)', html):
        url = m.group(1)
        if needle in url:
            rel = url.replace("../../", "", 1)
            fname = url.rstrip("/").rsplit("/", 1)[-1]
            return fname, f"{MIRROR}/{rel}"
    return None


# bitsandbytes 0.43.0 win_amd64
found = None
html = fetch(f"{MIRROR}/simple/bitsandbytes/", 60).decode("utf-8", "ignore")
for m in re.finditer(r'href="([^"]+\.whl)(?:[#"]|$)', html):
    url = m.group(1)
    if "0.43.0" in url and "win_amd64" in url:
        rel = url.replace("../../", "", 1)
        fname = url.rstrip("/").rsplit("/", 1)[-1]
        found = (fname, f"{MIRROR}/{rel}")
        break
if found:
    fname, url = found
    dest = OUT / fname
    if not dest.exists():
        data = fetch(url)
        dest.write_bytes(data)
        print(f"OK bitsandbytes: {fname} {len(data)/1e6:.1f} MB")
    else:
        print(f"EXISTS {fname}")
else:
    print("no bitsandbytes 0.43.0 win wheel")

# sherpa-onnx-core any win wheel
got = get_latest("sherpa-onnx-core", "win_amd64")
if got:
    fname, url = got
    dest = OUT / fname
    if not dest.exists():
        data = fetch(url, 600)
        dest.write_bytes(data)
        print(f"OK sherpa-onnx-core: {fname} {len(data)/1e6:.1f} MB")
    else:
        print(f"EXISTS {fname}")
else:
    print("no sherpa-onnx-core win wheel found")

"""Download numpy cp312 win_amd64 wheel from Aliyun HTTP mirror."""
import re
import urllib.request
from pathlib import Path

MIRROR = "http://mirrors.aliyun.com/pypi"
OUT = Path(r"D:\dsh\voice-assistant\wheels\deps")
OUT.mkdir(parents=True, exist_ok=True)


def fetch(url: str, timeout=300) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


html = fetch(f"{MIRROR}/simple/numpy/", 60).decode("utf-8", "ignore")
rows = []
for m in re.finditer(r'href="([^"]+\.whl)(?:[#"]|$)', html):
    url = m.group(1)
    if "cp312-cp312-win_amd64" not in url:
        continue
    fname = url.rstrip("/").rsplit("/", 1)[-1]
    m2 = re.match(r"^[^-]+-([0-9][^-]*)-", fname)
    ver = m2.group(1) if m2 else ""
    if re.search(r"[a-zA-Z]", ver.split("+")[0]):
        continue  # pre-release
    nums = tuple(int(x) for x in re.findall(r"\d+", ver))
    rows.append((nums, fname, url))

rows.sort(key=lambda r: r[0], reverse=True)
nums, fname, url = rows[0]
rel = url.replace("../../", "", 1)
dest = OUT / fname
if not dest.exists():
    data = fetch(f"{MIRROR}/{rel}")
    dest.write_bytes(data)
print(f"numpy: {fname}  {dest.stat().st_size/1024/1024:.1f} MB")

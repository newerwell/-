"""Download latest compatible wheels for torch deps from Aliyun HTTP mirror. v3
Fixes: version comparison bug + typing-extensions dash naming.
"""
import re
import urllib.request
from pathlib import Path

MIRROR = "http://mirrors.aliyun.com/pypi"
OUT = Path(r"D:\dsh\voice-assistant\wheels\deps")
OUT.mkdir(parents=True, exist_ok=True)

# index name (dash form) -> version floor
REQUIREMENTS = {
    "filelock": None,
    "typing-extensions": "4.10.0",
    "sympy": "1.13.3",
    "networkx": "2.5.1",
    "jinja2": None,
    "fsspec": "0.8.5",
    "setuptools": None,
    "mpmath": None,
    "markupsafe": None,
}


def parse_version(v: str):
    v = v.split("+")[0]
    nums = tuple(int(x) for x in re.findall(r"\d+", v))
    suffix = re.sub(r"[\d.]+", "", v)
    return (nums, suffix)


def version_ge(v: str, floor) -> bool:
    if floor is None:
        return True
    return parse_version(v) >= parse_version(floor)


def fetch(url: str, timeout=60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def pick_wheel(pkg: str):
    html = fetch(f"{MIRROR}/simple/{pkg}/").decode("utf-8", "ignore")
    candidates = []
    for m in re.finditer(r'href="([^"]+\.whl)(?:[#"]|$)', html):
        url = m.group(1)
        fname = url.rstrip("/").rsplit("/", 1)[-1]
        m2 = re.match(r"^[^-]+-([0-9][^-]*)-([^.]+)\.whl$", fname)
        if not m2:
            continue
        ver, tag = m2.group(1), m2.group(2)
        if re.search(r"[a-zA-Z]", ver.split("+")[0]):
            continue  # pre-release
        if not ("py3-none-any" in tag or "cp312-cp312-win_amd64" in tag):
            continue
        if not version_ge(ver, REQUIREMENTS.get(pkg)):
            continue
        candidates.append((parse_version(ver), fname, url))
    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0], reverse=True)
    _, fname, url = candidates[0]
    rel = url.replace("../../", "", 1)
    return fname, f"{MIRROR}/{rel}"


for pkg in REQUIREMENTS:
    for attempt in range(2):
        try:
            got = pick_wheel(pkg)
            if not got:
                print(f"SKIP  {pkg}: no qualifying wheel")
                break
            fname, url = got
            dest = OUT / fname
            if dest.exists():
                print(f"EXISTS {fname}")
                break
            data = fetch(url, timeout=180)
            dest.write_bytes(data)
            print(f"OK    {fname}  {len(data)/1024:.0f} KB")
            break
        except Exception as e:
            print(f"RETRY {pkg} ({attempt+1}): {e}")
            if attempt == 1:
                print(f"FAIL  {pkg}: {e}")

print("\n=== final listing ===")
for f in sorted(OUT.iterdir()):
    print(f"{f.name}  {f.stat().st_size/1024:.0f} KB")

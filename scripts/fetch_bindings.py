"""下载特定版本的 npm 包到 node_modules（处理 scoped 包）。"""
import io
import json
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

nm = Path(r"D:\dsh\voice-assistant\webapp\node_modules")

SPECS = [
    "@rolldown/binding-win32-x64-msvc@1.2.1",
    "@oxc-project/runtime@0.144.0",
    "lightningcss-win32-x64-msvc@1.33.0",
]


def fetch(spec: str):
    if "@" in spec[1:]:
        name, ver = spec.rsplit("@", 1)
    else:
        name, ver = spec, "latest"
    url = f"https://registry.npmmirror.com/{name.replace('@', '%40').replace('/', '%2F')}/{ver}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    meta = json.loads(urllib.request.urlopen(req, timeout=30).read())
    version = meta["version"]
    if name.startswith("@"):
        s, p = name.split("/")
        dest = nm / s / p
    else:
        dest = nm / name
    if dest.exists() and (dest / "package.json").exists():
        print("exists", name, version)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tarball = meta["dist"]["tarball"]
    req = urllib.request.Request(tarball, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=180).read()
    tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
    tmp = dest.parent / f".tmp_{name.replace('/', '_')}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    for member in tf.getmembers():
        parts = member.name.split("/", 1)
        if len(parts) < 2:
            continue
        target = tmp / parts[1]
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
        elif member.isfile():
            target.parent.mkdir(parents=True, exist_ok=True)
            with tf.extractfile(member) as s, open(target, "wb") as o:
                shutil.copyfileobj(s, o)
    shutil.move(str(tmp), str(dest))
    print("OK", name, version)


for s in SPECS:
    try:
        fetch(s)
    except Exception as e:
        print("FAIL", s, e)

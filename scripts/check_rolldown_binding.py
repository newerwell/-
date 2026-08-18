"""下载 rolldown 平台绑定（win32-x64-msvc）。"""
import io
import json
import shutil
import tarfile
import urllib.request
from pathlib import Path

nm = Path(r"D:\dsh\voice-assistant\webapp\node_modules")

# 检查 rolldown 需要哪些 binding
for pkg in ["@rolldown/binding-win32-x64-msvc", "@oxc-project/runtime"]:
    url = f"https://registry.npmmirror.com/{pkg.replace('@', '%40').replace('/', '%2F')}/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        meta = json.loads(urllib.request.urlopen(req, timeout=30).read())
        print(pkg, meta["version"], meta["dist"]["tarball"])
    except Exception as e:
        print(pkg, "FAIL:", e)

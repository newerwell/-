"""递归下载 npm 依赖闭包到 node_modules（沙箱 npm 不可用，用 Python HTTPS）。

解析每个包的 package.json dependencies，递归下载到平铺 node_modules。
仅处理 dependencies（运行时）+ 指定的 devDeps。
"""
import io
import json
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

REGISTRY = "https://registry.npmmirror.com"

# 顶层包：名字 -> 期望版本(可选)
ROOT_PACKAGES = {
    "vue": "3.5.41",
    "vue-router": "4",
    "pinia": "3",
    "element-plus": "2",
    "@element-plus/icons-vue": "2",
    "axios": "1",
    "vite": "8.2.1",
    "@vitejs/plugin-vue": "6",
    "typescript": "5",
    "vue-tsc": "3",
    "esbuild": "0.28.2",
    "@esbuild/win32-x64": "0.28.2",
    "rollup": "4",
    "sass": "1",
}

# 已下载缓存
_downloaded: dict[str, str] = {}  # name -> version
_queue: list[tuple[str, str]] = []  # (name, version_spec)


def resolve_meta(name: str, ver_spec: str) -> dict:
    """获取包元数据（解析版本）。"""
    url = f"{REGISTRY}/{name}/{ver_spec}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    meta = json.loads(urllib.request.urlopen(req, timeout=30).read())
    return meta


def extract_package(name: str, version: str, tarball: str, node_modules: Path) -> bool:
    if name in _downloaded:
        return True
    dest = (node_modules / name) if not name.startswith("@") else (node_modules / Path(*name.split("/")))
    if dest.exists() and (dest / "package.json").exists():
        try:
            meta = json.loads((dest / "package.json").read_text(encoding="utf-8"))
            if meta.get("version") == version:
                _downloaded[name] = version
                return True
        except Exception:
            pass
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(tarball, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=180).read()
        tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
        tmp = dest.parent / f".{name.replace('/', '_')}_tmp"
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        for member in tf.getmembers():
            parts = member.name.split("/", 1)
            if len(parts) < 2:
                continue
            rel = parts[1]
            target = tmp / rel
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with tf.extractfile(member) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(tmp), str(dest))
        _downloaded[name] = version
        return True
    except Exception as e:
        print(f"  DOWNLOAD FAIL {name}@{version}: {e}")
        return False


def process_queue(node_modules: Path, seen: set):
    """处理队列，递归解析 deps。"""
    while _queue:
        name, ver_spec = _queue.pop(0)
        key = f"{name}@{ver_spec}"
        if key in seen:
            continue
        seen.add(key)
        try:
            meta = resolve_meta(name, ver_spec)
        except Exception as e:
            print(f"  META FAIL {key}: {e}")
            continue
        version = meta["version"]
        if not extract_package(name, version, meta["dist"]["tarball"], node_modules):
            continue
        print(f"  OK {name}@{version}")
        # 解析其 dependencies（跳过 optional/peer 的复杂处理，尽量装）
        pkg_json = meta.get("dependencies") or {}
        for dep, dep_ver in pkg_json.items():
            # 清理版本号（去 ^ ~ >= 等）
            dv = dep_ver.strip()
            dv = dv.lstrip("^~>=<").split(" ")[0].split("||")[0]
            if not dv or dv == "*":
                dv = "latest"
            _queue.append((dep, dv))


def main():
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "node_modules").resolve()
    target.mkdir(parents=True, exist_ok=True)
    print(f"递归下载依赖闭包到 {target}")

    seen: set = set()
    for name, ver in ROOT_PACKAGES.items():
        _queue.append((name, ver))
    process_queue(target, seen)

    print(f"\n=== 完成: {len(_downloaded)} 个包 ===")


if __name__ == "__main__":
    main()

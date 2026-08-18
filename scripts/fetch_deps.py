"""Recursive dependency wheel downloader from Aliyun HTTP mirror (sandbox-safe).

Downloads a package and its full dependency closure as wheels into a local dir,
so pip can install purely from disk (pip network path is blocked by sandbox).

Usage: python fetch_deps.py <pkg1> [pkg2 ...]
Output: D:\dsh\voice-assistant\wheels\closure\
"""
import html
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

MIRROR = "http://mirrors.aliyun.com/pypi"
OUT = Path(r"D:\dsh\voice-assistant\wheels\closure")
OUT.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "curl/8.0"}
MAX_DEPTH = 6


def fetch(url: str, timeout=120) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def norm_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def version_key(v: str):
    """PEP440-ish sort key. Strips suffix letters; compares numerically."""
    v = v.split("+")[0]
    nums = [int(x) for x in re.findall(r"\d+", v)]
    suffix = re.sub(r"[\d.]+", "", v)
    return (nums, suffix)


def satisfies(version: str, spec: str) -> bool:
    """Check version against a simple spec like >=1.0,<2.0 (only >,>=,<,<=,==)."""
    spec = spec.strip()
    if not spec:
        return True
    for clause in spec.split(","):
        clause = clause.strip()
        m = re.match(r"^(>=|<=|>|<|==|!=)\s*v?([0-9][0-9a-zA-Z.\-]*)$", clause)
        if not m:
            return True  # ignore complex clauses
        op, req = m.group(1), m.group(2)
        k, rk = version_key(version), version_key(req)
        if op == ">=" and not (k >= rk):
            return False
        if op == "<=" and not (k <= rk):
            return False
        if op == ">" and not (k > rk):
            return False
        if op == "<" and not (k < rk):
            return False
        if op == "==" and k[0] != rk[0]:
            return False
        if op == "!=" and k == rk:
            return False
    return True


def find_wheel(pkg: str, spec: str):
    """Return (fname, full_url) of best wheel for pkg satisfying spec."""
    pkg_norm = norm_name(pkg)
    html_text = fetch(f"{MIRROR}/simple/{pkg_norm}/", 60).decode("utf-8", "ignore")
    best = None
    for m in re.finditer(r'href="([^"]+\.whl)(?:[#"]|$)', html_text):
        url = html.unescape(m.group(1))
        fname = url.rstrip("/").rsplit("/", 1)[-1]
        m2 = re.match(r"^[^-]+-([0-9][^-]*)-(.+)\.whl$", fname)
        if not m2:
            continue
        ver, tag = m2.group(1), m2.group(2)
        if re.search(r"[a-zA-Z]", ver.split("+")[0]):
            continue  # pre-release
        # platform filter:
        #  - pure python: py3-none-any / py2.py3-none-any / py2-none-any
        #  - win_amd64 with python tag compatible with 3.12
        #    (cp312, cp312-abi3, cp37-abi3, py2.py3, py3, abi3)
        py_tag = tag.split("-")[0]
        is_pure = "none-any" in tag and py_tag in ("py3", "py2.py3", "py2")
        is_win = "win_amd64" in tag and (
            "cp312" in py_tag
            or "abi3" in tag
            or py_tag.startswith("py2.py3")
            or py_tag.startswith("py3")
            or py_tag.startswith("py2")
        )
        if not (is_pure or is_win):
            continue
        if not satisfies(ver, spec):
            continue
        rel = url.replace("../../", "", 1)
        cand = (version_key(ver), fname, f"{MIRROR}/{rel}")
        if best is None or cand[0] > best[0]:
            best = cand
    return best


def deps_of(wheel_path: Path):
    """Read Requires-Dist from wheel METADATA -> list of (name, spec)."""
    deps = []
    try:
        with zipfile.ZipFile(wheel_path) as z:
            meta_name = [n for n in z.namelist() if n.endswith(".dist-info/METADATA")]
            if not meta_name:
                return deps
            text = z.read(meta_name[0]).decode("utf-8", "ignore")
    except Exception:
        return deps
    for line in text.splitlines():
        if not line.startswith("Requires-Dist:"):
            continue
        spec = line[len("Requires-Dist:"):].strip()
        if "extra ==" in spec or "extra==" in spec:
            continue  # skip optional extras
        # strip environment markers
        m = re.match(r"^([^;]+?)\s*(?:;.*)?$", spec)
        if not m:
            continue
        req = m.group(1).strip()
        m2 = re.match(r"^([A-Za-z0-9_.\-]+)\s*(.*)$", req)
        if not m2:
            continue
        deps.append((m2.group(1), m2.group(2).strip()))
    return deps


def main():
    queue = list(sys.argv[1:])  # (name) items
    # queue entries: dicts handled below
    pending = [(n, "", 0) for n in queue]
    seen = set()
    while pending:
        name, spec, depth = pending.pop(0)
        key = norm_name(name)
        if key in seen or depth > MAX_DEPTH:
            continue
        # already have any wheel for this name? check dir
        existing = [f for f in OUT.iterdir() if norm_name(f.name.rsplit("-", 2)[0]) == key]
        if existing:
            seen.add(key)
            continue
        try:
            got = find_wheel(name, spec)
        except Exception as e:
            print(f"ERR  {name}: {e}")
            continue
        if not got:
            print(f"SKIP {name} ({spec or 'any'}): no wheel")
            seen.add(key)
            continue
        _, fname, url = got
        dest = OUT / fname
        if not dest.exists():
            print(f"GET  {fname} ...")
            try:
                data = fetch(url, timeout=600)
                dest.write_bytes(data)
            except Exception as e:
                print(f"ERR  {fname}: {e}")
                seen.add(key)
                continue
        seen.add(key)
        for dep_name, dep_spec in deps_of(dest):
            if norm_name(dep_name) not in seen:
                pending.append((dep_name, dep_spec, depth + 1))
    print(f"\n=== {len(seen)} packages in {OUT} ===")


if __name__ == "__main__":
    main()

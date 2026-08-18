"""Download Qwen3-8B original safetensors model from ModelScope (HTTP downgrade)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from ms_download import download_model_file  # noqa: E402

BASE = "http://www.modelscope.cn/models/Qwen/Qwen3-8B/resolve/master"
OUT = Path(r"D:\dsh\voice-assistant\models\Qwen3-8B")
OUT.mkdir(parents=True, exist_ok=True)

FILES = [
    "config.json",
    "generation_config.json",
    "model.safetensors.index.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "model-00001-of-00005.safetensors",
    "model-00002-of-00005.safetensors",
    "model-00003-of-00005.safetensors",
    "model-00004-of-00005.safetensors",
    "model-00005-of-00005.safetensors",
]

for fname in FILES:
    dest = OUT / fname
    # skip small files that already exist (>=1KB) and big shards (>= 1GB)
    if dest.exists():
        sz = dest.stat().st_size
        need = 1_000_000_000 if fname.endswith(".safetensors") else 1000
        if sz >= need:
            print(f"EXISTS {fname} ({sz/1e9:.2f} GB)" if sz > 1e8 else f"EXISTS {fname}")
            continue
    print(f"downloading {fname} ...")
    try:
        n = download_model_file(f"{BASE}/{fname}", dest, timeout=3600)
        print(f"  OK {n/1e9:.2f} GB")
    except Exception as e:
        print(f"  FAIL: {e}")

print("\n=== done ===")
total = 0
for f in sorted(OUT.iterdir()):
    sz = f.stat().st_size
    total += sz
    print(f"{f.name}  {sz/1e9:.2f} GB")
print(f"TOTAL: {total/1e9:.2f} GB")

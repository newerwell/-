"""Download Qwen2-0.5B minimal files (config + tokenizer) for CosyVoice2 LLM init."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ms_download import download_model_file  # noqa: E402

BASE = "http://www.modelscope.cn/models/Qwen/Qwen2-0.5B/resolve/master"
OUT = Path(r"D:\dsh\voice-assistant\models\Qwen2-0.5B-base")
OUT.mkdir(parents=True, exist_ok=True)

FILES = [
    "config.json",
    "generation_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
]

for fname in FILES:
    dest = OUT / fname
    if dest.exists() and dest.stat().st_size > 100:
        print(f"EXISTS {fname}")
        continue
    print(f"downloading {fname} ...")
    try:
        n = download_model_file(f"{BASE}/{fname}", dest, timeout=600)
        print(f"  OK {n/1e6:.1f} MB")
    except Exception as e:
        print(f"  FAIL: {e}")
print("done")

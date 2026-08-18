"""Verify and repair Qwen3-8B shards: re-download any shard whose size
doesn't match the expected size from ModelScope API."""
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ms_download import download_model_file  # noqa: E402

MODEL = "Qwen/Qwen3-8B"
OUT = Path(r"D:\dsh\voice-assistant\models\Qwen3-8B")
BASE = f"http://www.modelscope.cn/models/{MODEL}/resolve/master"

# expected sizes (bytes) from ModelScope repo listing
EXPECTED = {
    "model-00001-of-00005.safetensors": 3996250744,
    "model-00002-of-00005.safetensors": 3993160032,
    "model-00003-of-00005.safetensors": 3959604768,
    "model-00004-of-00005.safetensors": 3187841392,
    "model-00005-of-00005.safetensors": 1244659840,
    "tokenizer.json": 11422654,
    "vocab.json": 2776833,
    "merges.txt": 1671853,
}

for fname, expected in EXPECTED.items():
    dest = OUT / fname
    if dest.exists() and dest.stat().st_size == expected:
        print(f"OK   {fname} ({expected/1e9:.2f} GB)")
        continue
    if dest.exists():
        print(f"BAD  {fname}: has {dest.stat().st_size} bytes, expected {expected} -> re-download")
    else:
        print(f"MISS {fname}: re-download")
    try:
        n = download_model_file(f"{BASE}/{fname}", dest, timeout=3600)
        ok = "OK" if dest.stat().st_size == expected else "SIZE MISMATCH"
        print(f"  -> {ok} {dest.stat().st_size} bytes")
    except Exception as e:
        print(f"  FAIL: {e}")

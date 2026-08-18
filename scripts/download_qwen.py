"""Download Qwen3-8B-Q4_K_M.gguf from ModelScope (with https->http downgrade)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from ms_download import download_model_file  # noqa: E402

URL = "http://www.modelscope.cn/models/Qwen/Qwen3-8B-GGUF/resolve/master/Qwen3-8B-Q4_K_M.gguf"
OUT = Path(r"D:\dsh\voice-assistant\models\Qwen3-8B-GGUF\Qwen3-8B-Q4_K_M.gguf")
OUT.parent.mkdir(parents=True, exist_ok=True)

if OUT.exists() and OUT.stat().st_size > 4_000_000_000:
    print(f"already complete: {OUT.stat().st_size/1e9:.2f} GB")
    raise SystemExit

print(f"downloading Qwen3-8B-Q4_K_M.gguf ...")
try:
    n = download_model_file(URL, OUT, timeout=1800)
    print(f"done: {n/1e9:.2f} GB")
except Exception as e:
    print(f"FAIL: {e}")

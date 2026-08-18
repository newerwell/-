"""Download fsmn-vad model from ModelScope (HTTP downgrade)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ms_download import download_model_file  # noqa: E402

BASE = "http://www.modelscope.cn/models/iic/speech_fsmn_vad_zh-cn-16k-common-pytorch/resolve/master"
OUT = Path(r"D:\dsh\voice-assistant\models\fsmn-vad")
OUT.mkdir(parents=True, exist_ok=True)

FILES = ["am.mvn", "config.yaml", "configuration.json", "model.pt", "README.md"]

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

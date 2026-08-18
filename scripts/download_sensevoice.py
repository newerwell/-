"""Download SenseVoiceSmall model files from ModelScope (with https->http downgrade)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from ms_download import download_model_file  # noqa: E402

BASE = "http://www.modelscope.cn/models/iic/SenseVoiceSmall/resolve/master"
OUT = Path(r"D:\dsh\voice-assistant\models\SenseVoiceSmall")
OUT.mkdir(parents=True, exist_ok=True)

FILES = [
    "am.mvn",
    "chn_jpn_yue_eng_ko_spectok.bpe.model",
    "config.yaml",
    "configuration.json",
    "model.pt",
    "tokens.json",
]

for fname in FILES:
    dest = OUT / fname
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"EXISTS {fname} ({dest.stat().st_size/1e6:.1f} MB)")
        continue
    print(f"downloading {fname} ...")
    try:
        n = download_model_file(f"{BASE}/{fname}", dest)
        print(f"  OK {n/1e6:.1f} MB")
    except Exception as e:
        print(f"  FAIL: {e}")

print("\n=== done ===")
for f in sorted(OUT.iterdir()):
    print(f"{f.name}  {f.stat().st_size/1e6:.1f} MB")

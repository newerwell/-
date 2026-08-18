"""Download CosyVoice2-0.5B TTS model from ModelScope (HTTP downgrade).
Only downloads files needed for zero-shot TTS inference:
- llm.pt (Qwen2-0.5B LLM, 2GB)
- flow.pt (flow matching, 450MB)
- hift.pt (HiFiGAN vocoder, 83MB)
- speech_tokenizer_v2.onnx (496MB)
- campplus.onnx (speaker encoder, 28MB)
- cosyvoice2.yaml (config)
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from ms_download import download_model_file  # noqa: E402

BASE = "http://www.modelscope.cn/models/iic/CosyVoice2-0.5B/resolve/master"
OUT = Path(r"D:\dsh\voice-assistant\models\CosyVoice2-0.5B")
OUT.mkdir(parents=True, exist_ok=True)

FILES = [
    "llm.pt",
    "flow.pt",
    "hift.pt",
    "speech_tokenizer_v2.onnx",
    "campplus.onnx",
    "cosyvoice2.yaml",
]

for fname in FILES:
    dest = OUT / fname
    need = 50_000_000 if fname.endswith((".pt", ".onnx")) else 1000
    if dest.exists() and dest.stat().st_size >= need:
        print(f"EXISTS {fname} ({dest.stat().st_size/1e9:.2f} GB)")
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

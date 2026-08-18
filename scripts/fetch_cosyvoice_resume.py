"""Download remaining CosyVoice files (resume)."""
import time
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/FunAudioLLM/CosyVoice/main"
OUT = Path(r"D:\dsh\voice-assistant\cosyvoice_repo")

FILES = [
    "cosyvoice/__init__.py",
    "cosyvoice/cli/__init__.py",
    "cosyvoice/cli/frontend.py",
    "cosyvoice/flow/__init__.py",
    "cosyvoice/flow/DiT/__init__.py",
    "cosyvoice/flow/length_regulator.py",
    "cosyvoice/hifigan/__init__.py",
    "cosyvoice/hifigan/discriminator.py",
    "cosyvoice/hifigan/f0_predictor.py",
    "cosyvoice/hifigan/generator.py",
    "cosyvoice/hifigan/hifigan.py",
    "cosyvoice/tokenizer/__init__.py",
    "cosyvoice/tokenizer/tokenizer.py",
    "cosyvoice/tokenizer/assets/multilingual_zh_ja_yue_char_del.tiktoken",
    "requirements.txt",
]

for f in FILES:
    dest = OUT / f
    if dest.exists() and dest.stat().st_size > 100:
        print(f"EXISTS {f}")
        continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BASE}/{f}"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = resp.read()
            dest.write_bytes(data)
            print(f"OK   {f} ({len(data)} B)")
            break
        except Exception as e:
            print(f"try{attempt} FAIL {f}: {type(e).__name__}")
            time.sleep(2)
    else:
        print(f"GIVEUP {f}")
print("=== batch done ===")

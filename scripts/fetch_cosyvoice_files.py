"""Download CosyVoice inference core files individually from raw.githubusercontent.com."""
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/FunAudioLLM/CosyVoice/main"
OUT = Path(r"D:\dsh\voice-assistant\cosyvoice_repo")

FILES = [
    "cosyvoice/__init__.py",
    "cosyvoice/cli/__init__.py",
    "cosyvoice/cli/cosyvoice.py",
    "cosyvoice/cli/frontend.py",
    "cosyvoice/cli/model.py",
    "cosyvoice/flow/__init__.py",
    "cosyvoice/flow/DiT/__init__.py",
    "cosyvoice/flow/DiT/dit.py",
    "cosyvoice/flow/DiT/modules.py",
    "cosyvoice/flow/decoder.py",
    "cosyvoice/flow/flow.py",
    "cosyvoice/flow/flow_matching.py",
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

ok, fail = 0, 0
for f in FILES:
    dest = OUT / f
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BASE}/{f}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        dest.write_bytes(data)
        print(f"OK   {f} ({len(data)} B)")
        ok += 1
    except Exception as e:
        print(f"FAIL {f}: {e}")
        fail += 1

print(f"\n=== done: {ok} ok, {fail} fail ===")

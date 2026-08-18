import re
from pathlib import Path

ep = Path(r"D:\dsh\voice-assistant\webapp\node_modules\element-plus")
hits = set()
for f in list(ep.rglob("*.mjs"))[:3000]:
    try:
        txt = f.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for m in re.finditer(r'from ["\'](@popperjs[^"\']+)["\']', txt):
        hits.add(m.group(1))
    for m in re.finditer(r'import ["\'](@popperjs[^"\']+)["\']', txt):
        hits.add(m.group(1))
print("popper imports:", hits if hits else "none")

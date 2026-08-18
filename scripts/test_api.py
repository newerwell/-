import json
import time
import urllib.request

for text in ["你好", "北京天气怎么样", "搜索今天的新闻"]:
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/chat", data=body,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=40)
        d = json.loads(resp.read())
        tools = [t["name"] for t in d.get("tool_calls", [])]
        print(f"{text}: {time.time()-t0:.1f}s -> {d['reply'][:40]} tools={tools}")
    except Exception as e:
        print(f"{text}: 失败 ({time.time()-t0:.1f}s): {e}")

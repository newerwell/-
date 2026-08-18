import json
import time
import urllib.request
import uuid

boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
wav = open(r"D:\dsh\voice-assistant\output\real_speech.wav", "rb").read()
body = b""
body += (
    f"--{boundary}\r\n"
    'Content-Disposition: form-data; name="file"; filename="voice.wav"\r\n'
    "Content-Type: audio/wav\r\n\r\n"
).encode()
body += wav + b"\r\n"
body += f"--{boundary}--\r\n".encode()

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/audio",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
)
t0 = time.time()
try:
    resp = urllib.request.urlopen(req, timeout=60)
    d = json.loads(resp.read())
    print(f"语音对话: {time.time()-t0:.1f}s")
    print("user_text:", d["user_text"][:40])
    print("reply:", d["reply"][:40])
except Exception as e:
    print(f"语音对话失败 ({time.time()-t0:.1f}s): {e}")

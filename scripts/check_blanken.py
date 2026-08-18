import json
import urllib.request

url = "http://www.modelscope.cn/api/v1/models/iic/CosyVoice2-0.5B/repo/files?Revision=master"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
data = json.loads(urllib.request.urlopen(req, timeout=30).read())
for f in data["Data"]["Files"]:
    if "BlankEN" in f["Path"]:
        print(f["Path"], f["Size"], "bytes")

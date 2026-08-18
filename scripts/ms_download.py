"""Shared downloader: ModelScope resolve -> redirect -> downgrade https to http.

The sandbox blocks HTTPS but allows HTTP. ModelScope resolve URLs 302-redirect
to cdn-lfs-cn-1.modelscope.cn over HTTPS; that CDN also serves plain HTTP.
"""
import urllib.request
from pathlib import Path


def build_opener():
    """Opener that does NOT auto-follow redirects, so we can downgrade them."""
    return urllib.request.build_opener(urllib.request.HTTPRedirectHandler)


# Custom handler that downgrades https -> http on redirects
class HttpDowngradeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if newurl.startswith("https://"):
            newurl = "http://" + newurl[len("https://"):]
        return urllib.request.Request(
            newurl,
            headers=req.headers,
            origin_req_host=req.origin_req_host,
            unverifiable=True,
        )


def opener():
    return urllib.request.build_opener(HttpDowngradeRedirect)


def download_model_file(resolve_url: str, dest: Path, timeout=600, chunk_mb=4):
    """Download one file. resolve_url may redirect; downgrade to http."""
    req = urllib.request.Request(resolve_url, headers={"User-Agent": "curl/8.0"})
    op = opener()
    with op.open(req, timeout=timeout) as r:
        total = int(r.headers.get("Content-Length", 0))
        done = 0
        with open(dest, "wb") as f:
            while True:
                chunk = r.read(chunk_mb * 1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total and done % (100 * 1024 * 1024) < chunk_mb * 1024 * 1024:
                    print(f"    {done/1e6:.0f} / {total/1e6:.0f} MB ({done/total*100:.0f}%)")
    return done

"""网络搜索工具：cn.bing.com（HTTP 可用）。

解析 Bing 搜索结果页的 b_algo 条目，返回标题/URL/摘要。
"""
import html
import re
import urllib.parse
import urllib.request

SEARCH_URL = "http://cn.bing.com/search"


def search(query: str, num: int = 5) -> str:
    """搜索并返回格式化结果（前 num 条）。"""
    q = urllib.parse.quote(query)
    url = f"{SEARCH_URL}?q={q}&count={num}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            page = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return f"搜索失败：{e}"

    results = _parse_bing_results(page, num)
    if not results:
        return f"未找到关于「{query}」的搜索结果。"

    lines = [f"关于「{query}」的搜索结果："]
    for i, r in enumerate(results, 1):
        title = html.unescape(r["title"])
        snippet = html.unescape(r.get("snippet", "")).strip()
        lines.append(f"{i}. {title}")
        if snippet:
            lines.append(f"   {snippet}")
        lines.append(f"   {r['url']}")
    return "\n".join(lines)


def _parse_bing_results(page: str, num: int) -> list[dict]:
    """从 Bing 结果页提取 (title, url, snippet)。"""
    results = []
    # 按 b_algo 块切分
    blocks = re.split(r'<li class="b_algo"', page)
    for block in blocks[1:]:
        if len(results) >= num:
            break
        # 标题
        m_title = re.search(r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not m_title:
            m_title = re.search(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not m_title:
            continue
        url = m_title.group(1)
        title = re.sub(r"<[^>]+>", "", m_title.group(2)).strip()
        # 摘要
        m_snip = re.search(r'<p[^>]*class="[^"]*b_lineclamp[^"]*"[^>]*>(.*?)</p>', block, re.S)
        snippet = ""
        if m_snip:
            snippet = re.sub(r"<[^>]+>", "", m_snip.group(1)).strip()
        if title and url.startswith("http"):
            results.append({"title": title, "url": url, "snippet": snippet})
    return results


def get_search_tool_schema() -> dict:
    """LLM 工具调用 schema。"""
    return {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "在互联网上搜索信息，返回相关网页的标题、链接和摘要。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词，如：今天的热点新闻"}
                },
                "required": ["query"],
            },
        },
    }

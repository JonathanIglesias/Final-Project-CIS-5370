import requests
from bs4 import BeautifulSoup
from pathlib import Path
import json, re
from urllib.parse import urljoin, urlparse
from src.crawler import fetchHTML

def load_sources(path="sources.json"):
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(text)

def host(url: str) -> str:
    return urlparse(url).netloc.lower()

def isAllowed(cfg: dict, url: str) -> bool:
    return host(url) == cfg["domain"]

def isArticle(cfg: dict, url: str) -> bool:
    pat = cfg.get("article_regex")
    return bool(pat and re.search(pat, url))

def iterSitemap(sitemap_url: str, limit: int = 50):
    """Yield article URLs from a sitemap (stop at `limit`)."""
    r = requests.get(sitemap_url, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml-xml")
    for loc in soup.select("url > loc"):
        url = loc.get_text(strip=True)
        if url and "/202" in url:
            yield url
            limit -= 1
            if limit <= 0:
                break

def extractLabel(label_url: str, limit: int = 50):
    """Yield article URLs listed on the label page (pagination optional)."""
    r = requests.get(label_url, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    # Inspect the page to choose a selector; start with generic links:
    for a in soup.select("a[href]"):
        href = a["href"]
        if href.startswith("https://thehackernews.com/") and "/202" in href:
            yield href
            limit -= 1
            if limit <= 0:
                break

def fromSeed(session, seed_url: str, limit: int = 50, same_host: str | None = None):
    status, body = fetchHTML(session, seed_url)
    if not body:
        return []

    urls, seen = [], set()
    is_xml = seed_url.lower().endswith((".xml", ".xml.gz"))
    soup = BeautifulSoup(body, "lxml-xml" if is_xml else "lxml")

    if is_xml:
        for loc in soup.select("url > loc, sitemap > loc"):
            u = (loc.get_text() or "").strip()
            if not u: 
                continue
            if same_host and urlparse(u).netloc.lower() != same_host:
                continue
            if u in seen: 
                continue
            seen.add(u); urls.append(u)
            if len(urls) >= limit: break
    else:
        for a in soup.select("a[href]"):
            href = urljoin(seed_url, a["href"])
            if href.startswith(("mailto:", "javascript:")):
                continue
            href = href.split("#", 1)[0]                 
            if same_host and urlparse(href).netloc.lower() != same_host:
                continue
            if href in seen: 
                continue
            seen.add(href); urls.append(href)
            if len(urls) >= limit: break
    return urls
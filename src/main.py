from pathlib import Path
from src.crawler import fetchHTML, createSession, extract, canFetch, today, append
from src.seeds import load_sources, isAllowed, isArticle, fromSeed
from urllib.parse import urlparse
from src.db import upsert_article

SOURCES = load_sources("../data/source.json")

def host(u: str) -> str:
    return urlparse(u).netloc.lower()

if __name__ == '__main__':
    print("Start")
    USER_AGENT = "WebCrawler (Jonathan Iglesias; FIU; for academic research)"

    session = createSession(USER_AGENT)
    outPath = Path("../data/outputs.json")
    seenPath = Path("../data/seen_urls.txt")
    seen = set(seenPath.read_text().splitlines()) if seenPath.exists() else set()
    for cfg in SOURCES:
        robots_url = f"https://{cfg['domain']}/robots.txt"
        for seed in cfg["seeds"]:
            for url in fromSeed(session, seed, limit=50, same_host=cfg["domain"]):
                # 1) same-domain gate MUST be here
                if not isAllowed(cfg, url):
                    continue
                # 2) Article filter
                if not isArticle(cfg, url):
                    continue
                # 3) robots per-URL
                if not canFetch(robots_url, USER_AGENT, url):
                    continue
                # 4) FETCH inside the URL loop
                status, html = fetchHTML(session, url)
                if status != 200 or not html:
                    continue
                extracted = extract(html)
                record = {
                    "url": url,
                    "source": host(url),
                    "fetched_at": today(),
                    "http_status": status,
                    "title": extracted.get("title"),
                    "text": extracted.get("text"),
                    "raw_html": html
                    }

                #This is optional if you want to have a copy as a json file
                append(record, outPath)
                _ = upsert_article(record)
        
    print("done")
    
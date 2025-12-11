import time, random, requests
from urllib import robotparser
import json
from pathlib import Path
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from readability import Document

RETRY_STATUSES = {429, 500, 502, 503, 504}

def canFetch(url: str, agent: str, target: str) -> bool:
    rp = robotparser.RobotFileParser()
    rp.set_url(url)
    rp.read()
    return rp.can_fetch(agent, target)

def createSession(user_agent: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s

def fetchHTML(session: requests.Session, url: str, max_retries: int = 3, timeout: int = 15):
    attempt = 0
    backoff = 1.0
    while True:
        # Polite pause
        timeOff(random.uniform(0.5, 1.5))
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True)
            status = response.status_code
            # Content check
            ctype = (response.headers.get("Content-Type") or "").lower()
            if "text/html" not in ctype:
                return status, None
            # If success normalize encoding and return
            if 200 <= status < 300:
                if not response.encoding:
                    response.encoding = response.apparent_encoding or "utf-8"
                html = response.text
                # Optional size guard
                if len(html) > 4_000_000:
                    return status, None
                return status, html
            # if is not a 2xx state, deciding whether to retry
            if status in RETRY_STATUSES and attempt < max_retries:
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    timeOff(float(retry_after))
                else:
                    timeOff(backoff)
                    backoff *= 2
                attempt += 1
                continue
            # non-retryable status or out of retries
            return status, None
        except (requests.Timeout, requests.ConnectionError):
            if attempt < max_retries:
                timeOff(backoff)
                backoff *= 2
                attempt += 1
                continue
            return None, None
        # In case it detects other requests errors
        except requests.RequestException:
            return None, None
        
def timeOff(seconds: float):
    time.sleep(seconds + random.uniform(0.0, 0.3))
    
def today() -> str:
    return datetime.now(timezone.utc).isoformat()

def append(record: dict, path: Path):
    if path.exists():
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    else:
        with path.open("w", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
def seen(url: str, seen_path: Path):
    with seen_path.open("a", encoding="utf-8") as f:
        f.write(url + "\n")
        
def extract(html: str) -> dict:
    doc = Document(html)
    title = doc.short_title()
    content_html = doc.summary()
    soup = BeautifulSoup(content_html, "lxml")
    text = soup.get_text(" ", strip=True)
    return {"title": title, "text": text}
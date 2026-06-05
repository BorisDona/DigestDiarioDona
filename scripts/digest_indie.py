#!/usr/bin/env python3
"""Digest diario de videojuegos indie."""
import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "-4832705898"
NEWSAPI_KEY = os.environ["NEWSAPI_KEY"]

QUERIES = [
    "indie game announcement",
    "Kickstarter game",
    "Steam Next Fest",
    "indie game devlog",
    "indie game release",
    "small studio game",
]

GOOD_KEYWORDS = ["indie", "Kickstarter", "Steam", "demo", "release", "announce", "launch",
                 "studio", "developer", "showcase", "festival", "early access", "alpha", "beta"]

def fetch_news(query, page_size=15):
    yesterday = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "from": yesterday,
        "pageSize": page_size,
        "apiKey": NEWSAPI_KEY,
    }
    url = "https://newsapi.org/v2/everything?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read())
            return data.get("articles", []) if data.get("status") == "ok" else []
    except Exception as e:
        print(f"[ERR] {query}: {e}", file=sys.stderr)
        return []

def filter_indie(articles, seen_urls):
    """Filtra priorizando contenido indie."""
    bad_sources = {"TMZ", "RadarOnline", "Daily Mail"}
    out = []
    for a in articles:
        url = a.get("url", "")
        title = (a.get("title") or "").strip()
        desc = (a.get("description") or "").strip()
        source = a.get("source", {}).get("name", "") or ""
        if not url or url in seen_urls:
            continue
        if not title or title == "[Removed]":
            continue
        if len(desc) < 30:
            continue
        if any(b in source for b in bad_sources):
            continue
        # Priorizar si tiene keywords indie
        text = (title + " " + desc).lower()
        score = sum(1 for k in GOOD_KEYWORDS if k.lower() in text)
        a["_score"] = score
        seen_urls.add(url)
        out.append(a)
    # Ordenar por score
    out.sort(key=lambda x: x.get("_score", 0), reverse=True)
    return out

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def main():
    seen = set()
    candidates = []
    # Acumula candidatos de varios queries
    for q in QUERIES:
        if len(candidates) >= 20:
            break
        raw = fetch_news(q, page_size=15)
        candidates.extend(filter_indie(raw, seen))

    # Tomar los 5 mejores
    top5 = candidates[:5]

    if not top5:
        text = "🎮 <b>DIGEST INDIE</b>\n\nNo se encontraron noticias hoy. 😔"
    else:
        lines = ["🎮 <b>DIGEST VIDEOJUEGOS INDIE</b>\n"]
        for i, a in enumerate(top5, 1):
            title = a.get("title", "").strip()
            source = a.get("source", {}).get("name", "")
            url = a.get("url", "")
            lines.append(f"<b>{i}. {title}</b>")
            lines.append(f"<i>{source}</i>")
            lines.append(url)
            lines.append("")
        text = "\n".join(lines)

    send_telegram(text)
    print(f"[OK] Digest indie enviado con {len(top5)} noticias")

if __name__ == "__main__":
    main()

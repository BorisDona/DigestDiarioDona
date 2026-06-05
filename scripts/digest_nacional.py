#!/usr/bin/env python3
"""Digest diario de noticias nacionales de Chile."""
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
    "Chile política",
    "Chile economía",
    "Chile sociedad",
    "Santiago Chile",
    "Congreso Chile",
]

def fetch_news(query, page_size=10):
    """Consulta NewsAPI con un query dado."""
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    params = {
        "q": query,
        "language": "es",
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

def filter_quality(articles, seen_urls):
    """Filtra: sin duplicados, descripción decente, excluye fuentes de mala calidad."""
    bad_sources = {"Hola", "Mundodeportivo.com", "Marca.com", "AS", "EL MUNDO"}
    out = []
    for a in articles:
        url = a.get("url", "")
        title = (a.get("title") or "").strip()
        desc = (a.get("description") or "").strip()
        if not url or url in seen_urls:
            continue
        if not title or title == "[Removed]":
            continue
        if len(desc) < 30:
            continue
        if any(b in (a.get("source", {}).get("name", "") or "") for b in bad_sources):
            continue
        seen_urls.add(url)
        out.append(a)
    return out

def send_telegram(text):
    """Envía mensaje a Telegram."""
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
    articles = []
    # Acumula hasta juntar 5 noticias de calidad
    for q in QUERIES:
        if len(articles) >= 5:
            break
        raw = fetch_news(q, page_size=10)
        filtered = filter_quality(raw, seen)
        for a in filtered:
            if len(articles) >= 5:
                break
            articles.append(a)

    # Si no juntamos 5, segundo intento con queries más amplios
    if len(articles) < 5:
        for q in ["Chile", "Santiago", "Región Metropolitana", "Chile gobierno"]:
            if len(articles) >= 5:
                break
            raw = fetch_news(q, page_size=15)
            filtered = filter_quality(raw, seen)
            for a in filtered:
                if len(articles) >= 5:
                    break
                articles.append(a)

    if not articles:
        text = "🇨🇱 <b>DIGEST NACIONAL — Chile</b>\n\nNo se encontraron noticias hoy. 😔"
    else:
        lines = ["🇨🇱 <b>DIGEST NACIONAL — Chile</b>\n"]
        for i, a in enumerate(articles[:5], 1):
            title = a.get("title", "").strip()
            source = a.get("source", {}).get("name", "")
            url = a.get("url", "")
            lines.append(f"<b>{i}. {title}</b>")
            lines.append(f"<i>{source}</i>")
            lines.append(url)
            lines.append("")
        text = "\n".join(lines)

    send_telegram(text)
    print(f"[OK] Digest nacional enviado con {len(articles)} noticias")

if __name__ == "__main__":
    main()

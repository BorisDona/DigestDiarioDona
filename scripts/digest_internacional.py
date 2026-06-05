#!/usr/bin/env python3
"""Digest diario internacional: 3 LATAM + 2 fuera de LATAM."""
import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "-4832705898"
NEWSAPI_KEY = os.environ["NEWSAPI_KEY"]

# 5 países LATAM principales a rotar (3 por día)
LATAM_POOL = [
    ("Argentina", "Argentina política OR Argentina economía OR Buenos Aires"),
    ("México", "México política OR México economía OR Ciudad de México"),
    ("Colombia", "Colombia política OR Colombia economía OR Bogotá"),
    ("Perú", "Perú política OR Lima OR Perú economía"),
    ("Brasil", "Brasil política OR Brasilia OR São Paulo"),
    ("Bolivia", "Bolivia política OR La Paz"),
    ("Uruguay", "Uruguay política OR Montevideo"),
    ("Ecuador", "Ecuador política OR Quito"),
    ("Venezuela", "Venezuela política OR Caracas"),
    ("Paraguay", "Paraguay política OR Asunción"),
]

# 5 regiones fuera de LATAM (2 por día)
NON_LATAM_POOL = [
    ("Europa", "Europe politics OR European Union OR Brussels OR Berlin OR Paris OR Madrid"),
    ("Asia", "Asia politics OR Tokyo OR Beijing OR Seoul OR New Delhi"),
    ("África", "Africa politics OR Nairobi OR Lagos OR Cairo OR Johannesburg"),
    ("Medio Oriente", "Middle East politics OR Israel OR Iran OR Saudi Arabia"),
    ("Estados Unidos", "United States politics OR Washington OR New York OR White House"),
]

def pick_today_pools():
    """Rota los pools según el día del año."""
    day_of_year = datetime.utcnow().timetuple().tm_yday
    # 3 LATAM en orden rotativo
    latam_today = []
    for i in range(3):
        idx = (day_of_year + i * 3) % len(LATAM_POOL)
        country, query = LATAM_POOL[idx]
        if country not in [c for c, _ in latam_today]:
            latam_today.append((country, query))
        else:
            # si se repite, agarra el siguiente
            for j in range(len(LATAM_POOL)):
                idx2 = (idx + j + 1) % len(LATAM_POOL)
                if LATAM_POOL[idx2][0] not in [c for c, _ in latam_today]:
                    latam_today.append(LATAM_POOL[idx2])
                    break
    # 2 fuera de LATAM
    non_latam_today = []
    for i in range(2):
        idx = (day_of_year * 2 + i * 5) % len(NON_LATAM_POOL)
        non_latam_today.append(NON_LATAM_POOL[idx])
    return latam_today, non_latam_pools_clean(non_latam_today)

def non_latam_pools_clean(lst):
    out = []
    for region, q in lst:
        if region not in [r for r, _ in out]:
            out.append((region, q))
    return out

def fetch_news(query, page_size=10):
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
    bad_sources = {"Hola", "Mundodeportivo.com", "Marca.com"}
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

def get_articles(query, target_count, seen):
    """Trae artículos hasta juntar target_count."""
    out = []
    raw = fetch_news(query, page_size=20)
    filtered = filter_quality(raw, seen)
    for a in filtered:
        if len(out) >= target_count:
            break
        out.append(a)
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
    latam_today, non_latam_today = pick_today_pools()
    seen = set()
    sections = []

    # LATAM
    sections.append("🌎 <b>LATINOAMÉRICA</b>\n")
    for i, (country, query) in enumerate(latam_today, 1):
        arts = get_articles(query, 1, seen)
        if arts:
            a = arts[0]
            sections.append(f"<b>{country}.</b> <b>{a.get('title','').strip()}</b>")
            sections.append(f"<i>{a.get('source',{}).get('name','')}</i>")
            sections.append(a.get("url",""))
            sections.append("")

    # Fuera de LATAM
    sections.append("🌐 <b>RESTO DEL MUNDO</b>\n")
    for region, query in non_latam_today:
        arts = get_articles(query, 1, seen)
        if arts:
            a = arts[0]
            sections.append(f"<b>{region}.</b> <b>{a.get('title','').strip()}</b>")
            sections.append(f"<i>{a.get('source',{}).get('name','')}</i>")
            sections.append(a.get("url",""))
            sections.append("")

    header = "🌍 <b>DIGEST INTERNACIONAL</b>\n"
    text = header + "\n" + "\n".join(sections)
    send_telegram(text)
    total = sum(1 for line in sections if line.startswith("<b>") and not line.startswith("<b>LATAM") and not line.startswith("<b>RESTO"))
    print(f"[OK] Digest internacional enviado")

if __name__ == "__main__":
    main()

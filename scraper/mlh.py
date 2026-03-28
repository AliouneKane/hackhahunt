"""
scraper/mlh.py — Scraper pour mlh.io (saison 2026)
Le site MLH utilise du rendu côté client pour les saisons futures,
mais la page 2026 est rendue côté serveur avec Tailwind CSS.
Structure réelle : <a class="... group ..."> avec <h4> pour le titre.
"""
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://mlh.io/seasons/2026/events"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}


def scrape_mlh() -> list:
    print("  [MLH] Scraping en cours...")
    try:
        resp = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [MLH] Erreur réseau : {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # MLH 2026 uses Tailwind: each event is an <a class="... group ..."> tag
    events = soup.select("a.group")

    hackathons = []

    for event in events:
        try:
            # Titre dans un <h4>
            title_el = event.select_one("h4")
            title = title_el.get_text(strip=True) if title_el else None
            if not title:
                continue

            # URL (le lien est la carte elle-même)
            url = event.get("href", BASE_URL)
            if url and not url.startswith("http"):
                url = "https://mlh.io" + url

            # Date et lieu : deux <span> successifs après les icônes
            spans = event.select("span")
            # Filtrer les spans qui ont du vrai texte (pas juste des SVG)
            text_spans = [s.get_text(strip=True) for s in spans if s.get_text(strip=True)]

            deadline = text_spans[0] if len(text_spans) > 0 else ""
            location = text_spans[1] if len(text_spans) > 1 else "En ligne"
            event_type = text_spans[2] if len(text_spans) > 2 else "Virtual"

            # Format basé sur le span "In-Person" / "Virtual"
            fmt = "online"
            if "in-person" in event_type.lower():
                fmt = "in-person"
            elif "hybrid" in event_type.lower():
                fmt = "hybrid"

            hackathons.append({
                "source": "mlh",
                "title": title,
                "url": url,
                "theme": "Hackathon universitaire — toutes technologies",
                "format": fmt,
                "location": location,
                "prize_raw": "",
                "prize_min_fcfa": 0,
                "prize_1st": "",
                "prize_2nd": "",
                "prize_3rd": "",
                "deadline": deadline,
                "language": "en",
            })
        except Exception as e:
            print(f"  [MLH] Erreur parsing : {e}")
            continue

    print(f"  [MLH] {len(hackathons)} hackathons collectés")
    return hackathons

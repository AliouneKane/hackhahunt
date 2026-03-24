import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.hackmakers.com/hackathons"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}


def scrape_hackmakers() -> list:
    """Scrape les hackathons sur Hackmakers"""
    hackathons = []

    print("  [Hackmakers] Scraping en cours...")
    try:
        resp = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [Hackmakers] Erreur : {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select(".hackathon-card, .event-card, article, [class*='hackathon']")

    for card in cards:
        try:
            title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
            title = title_el.get_text(strip=True) if title_el else None
            if not title:
                continue

            link_el = card.select_one("a[href]")
            url = link_el["href"] if link_el else BASE_URL
            if url and not url.startswith("http"):
                url = "https://www.hackmakers.com" + url

            desc_el = card.select_one("p, [class*='desc'], [class*='summary']")
            theme = desc_el.get_text(strip=True)[:200] if desc_el else ""

            date_el = card.select_one("time, [class*='date'], [class*='deadline']")
            deadline = date_el.get_text(strip=True) if date_el else ""

            prize_el = card.select_one("[class*='prize'], [class*='award'], [class*='reward']")
            prize_text = prize_el.get_text(strip=True) if prize_el else ""

            loc_el = card.select_one("[class*='location'], [class*='where']")
            location = loc_el.get_text(strip=True) if loc_el else "En ligne"

            fmt = "online"
            if any(w in location.lower() for w in ["in-person", "hybrid", "présentiel"]):
                fmt = "hybrid"

            hackathons.append({
                "source": "hackmakers",
                "title": title,
                "url": url,
                "theme": theme,
                "format": fmt,
                "location": location,
                "prize_raw": prize_text,
                "prize_min_fcfa": 0,
                "prize_1st": prize_text,
                "prize_2nd": "",
                "prize_3rd": "",
                "deadline": deadline,
                "language": "en",
            })
        except Exception as e:
            print(f"  [Hackmakers] Erreur parsing : {e}")
            continue

    print(f"  [Hackmakers] {len(hackathons)} hackathons collectés")
    return hackathons

import requests
from bs4 import BeautifulSoup
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

KEYWORDS = [
    "hackathon africa",
    "hackathon data science",
    "hackathon senegal",
    "hackathon west africa",
    "data challenge africa",
    "hackathon fintech africa",
    "hackathon IA afrique",
]

def scrape_eventbrite() -> list:
    print("  [Eventbrite] Scraping en cours...")
    hackathons = []
    seen_urls = set()

    for keyword in KEYWORDS:
        try:
            url = f"https://www.eventbrite.com/d/online/{keyword.replace(' ', '-')}/"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("[data-testid='event-card'], .search-event-card, article")

            for card in cards:
                try:
                    title_el = card.select_one("h2, h3, [class*='title'], [class*='name']")
                    title = title_el.get_text(strip=True) if title_el else None
                    if not title:
                        continue

                    link_el = card.select_one("a[href]")
                    card_url = link_el["href"] if link_el else None
                    if card_url and not card_url.startswith("http"):
                        card_url = "https://www.eventbrite.com" + card_url
                    if not card_url or card_url in seen_urls:
                        continue
                    seen_urls.add(card_url)

                    if not any(w in title.lower() for w in ["hack", "challenge", "data", "innov", "compétition"]):
                        continue

                    date_el = card.select_one("time, [class*='date'], [class*='when']")
                    deadline = date_el.get_text(strip=True) if date_el else ""

                    loc_el = card.select_one("[class*='location'], [class*='where']")
                    location = loc_el.get_text(strip=True) if loc_el else "En ligne"

                    hackathons.append({
                        "source": "eventbrite",
                        "title": title,
                        "url": card_url,
                        "theme": f"Trouvé via recherche : {keyword}",
                        "format": "online" if "online" in location.lower() else "hybrid",
                        "location": location,
                        "prize_raw": "",
                        "prize_min_fcfa": 0,
                        "prize_1st": "",
                        "prize_2nd": "",
                        "prize_3rd": "",
                        "deadline": deadline,
                        "language": "fr/en",
                    })
                except Exception:
                    continue

            time.sleep(2)

        except Exception as e:
            print(f"  [Eventbrite] Erreur '{keyword}' : {e}")
            continue

    print(f"  [Eventbrite] {len(hackathons)} événements collectés")
    return hackathons

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

# ── ChallengeData (ENS Paris) ─────────────────────────────────────────────────
def scrape_challengedata() -> list:
    print("  [ChallengeData] Scraping en cours...")
    url = "https://challengedata.ens.fr/challenges/active"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [ChallengeData] Erreur : {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select(".challenge, .challenge-card, article, [class*='challenge']")
    hackathons = []

    for card in cards:
        try:
            title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
            title = title_el.get_text(strip=True) if title_el else None
            if not title:
                continue

            link_el = card.select_one("a[href]")
            card_url = link_el["href"] if link_el else url
            if card_url and not card_url.startswith("http"):
                card_url = "https://challengedata.ens.fr" + card_url

            desc_el = card.select_one("p, [class*='desc'], [class*='summary']")
            theme = desc_el.get_text(strip=True)[:200] if desc_el else "Compétition data science"

            hackathons.append({
                "source": "challengedata",
                "title": title,
                "url": card_url,
                "theme": theme,
                "format": "online",
                "location": "En ligne — France / International",
                "prize_raw": "",
                "prize_min_fcfa": 0,
                "prize_1st": "",
                "prize_2nd": "",
                "prize_3rd": "",
                "deadline": "",
                "language": "fr",
            })
        except Exception as e:
            print(f"  [ChallengeData] Erreur parsing : {e}")
            continue

    print(f"  [ChallengeData] {len(hackathons)} challenges collectés")
    return hackathons


# ── Challengerocket ───────────────────────────────────────────────────────────
def scrape_challengerocket() -> list:
    print("  [Challengerocket] Scraping en cours...")
    url = "https://challengerocket.com/hackathons.html"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [Challengerocket] Erreur : {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select(".challenge-item, .hackathon-item, article, [class*='challenge']")
    hackathons = []

    for card in cards:
        try:
            title_el = card.select_one("h2, h3, h4, .title")
            title = title_el.get_text(strip=True) if title_el else None
            if not title:
                continue

            link_el = card.select_one("a[href]")
            card_url = link_el["href"] if link_el else url
            if card_url and not card_url.startswith("http"):
                card_url = "https://challengerocket.com" + card_url

            desc_el = card.select_one("p, [class*='desc']")
            theme = desc_el.get_text(strip=True)[:200] if desc_el else ""

            date_el = card.select_one("time, [class*='date']")
            deadline = date_el.get_text(strip=True) if date_el else ""

            hackathons.append({
                "source": "challengerocket",
                "title": title,
                "url": card_url,
                "theme": theme,
                "format": "online",
                "location": "En ligne — International",
                "prize_raw": "",
                "prize_min_fcfa": 0,
                "prize_1st": "",
                "prize_2nd": "",
                "prize_3rd": "",
                "deadline": deadline,
                "language": "fr/en",
            })
        except Exception as e:
            print(f"  [Challengerocket] Erreur parsing : {e}")
            continue

    print(f"  [Challengerocket] {len(hackathons)} challenges collectés")
    return hackathons

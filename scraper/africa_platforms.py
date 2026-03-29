import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

# ── A2SV Hacks ────────────────────────────────────────────────────────────────
def scrape_a2sv() -> list:
    print("  [A2SV] Scraping en cours...")
    urls = ["https://hackathon.a2sv.org", "https://hacks.a2sv.org"]
    hackathons = []

    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            title_el = soup.select_one("h1, h2, .title, [class*='title']")
            title = title_el.get_text(strip=True) if title_el else "A2SV Hackathon for Africa"

            desc_el = soup.select_one("p, .description, [class*='desc']")
            theme = desc_el.get_text(strip=True)[:200] if desc_el else "Intelligence artificielle — Afrique"

            date_el = soup.select_one("time, [class*='date'], [class*='deadline']")
            deadline = date_el.get_text(strip=True) if date_el else ""

            prize_el = soup.select_one("[class*='prize'], [class*='award']")
            prize_text = prize_el.get_text(strip=True) if prize_el else ""

            hackathons.append({
                "source": "a2sv",
                "title": title,
                "url": url,
                "theme": theme,
                "format": "hybrid",
                "location": "En ligne + finale en Afrique",
                "prize_raw": prize_text,
                "prize_min_fcfa": 0,
                "prize_1st": prize_text,
                "prize_2nd": "",
                "prize_3rd": "",
                "deadline": deadline,
                "language": "en",
            })
            break
        except Exception as e:
            print(f"  [A2SV] Erreur {url} : {e}")
            continue

    print(f"  [A2SV] {len(hackathons)} hackathons collectés")
    return hackathons


# ── Geekulcha ─────────────────────────────────────────────────────────────────
def scrape_geekulcha() -> list:
    print("  [Geekulcha] Scraping en cours...")
    url = "https://www.geekulcha.dev/events"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [Geekulcha] Erreur : {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select(".event, .event-card, article, [class*='event']")
    hackathons = []

    for card in cards:
        try:
            title_el = card.select_one("h2, h3, h4, .title")
            title = title_el.get_text(strip=True) if title_el else None
            if not title:
                continue

            # Filtrer uniquement les hackathons
            if not any(w in title.lower() for w in ["hack", "data", "code", "challenge", "innov"]):
                continue

            link_el = card.select_one("a[href]")
            card_url = link_el["href"] if link_el else url
            if card_url and not card_url.startswith("http"):
                card_url = "https://www.geekulcha.dev" + card_url

            desc_el = card.select_one("p, [class*='desc']")
            theme = desc_el.get_text(strip=True)[:200] if desc_el else "Tech & Innovation — Afrique"

            date_el = card.select_one("time, [class*='date']")
            deadline = date_el.get_text(strip=True) if date_el else ""

            loc_el = card.select_one("[class*='location'], [class*='venue']")
            location = loc_el.get_text(strip=True) if loc_el else "Afrique du Sud / Virtual"

            hackathons.append({
                "source": "geekulcha",
                "title": title,
                "url": card_url,
                "theme": theme,
                "format": "hybrid",
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
            print(f"  [Geekulcha] Erreur parsing : {e}")
            continue

    print(f"  [Geekulcha] {len(hackathons)} événements collectés")
    return hackathons


# ── Opportunities for Africans ────────────────────────────────────────────────
def scrape_opportunities_africa() -> list:
    print("  [OpportunitiesAfrica] Scraping en cours...")
    url = "https://www.opportunitiesforafricans.com/?s=hackathon"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [OpportunitiesAfrica] Erreur : {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select("article, .post, [class*='post']")
    hackathons = []

    for card in cards:
        try:
            title_el = card.select_one("h2, h3, .entry-title, [class*='title']")
            title = title_el.get_text(strip=True) if title_el else None
            if not title:
                continue
            if not any(w in title.lower() for w in ["hackathon", "challenge", "competition", "data"]):
                continue

            link_el = card.select_one("a[href]")
            card_url = link_el["href"] if link_el else url
            if card_url and not card_url.startswith("http"):
                card_url = "https://www.opportunitiesforafricans.com" + card_url

            desc_el = card.select_one("p, .entry-summary, [class*='excerpt']")
            theme = desc_el.get_text(strip=True)[:200] if desc_el else "Opportunité Afrique"

            date_el = card.select_one("time, .entry-date, [class*='date']")
            deadline = date_el.get_text(strip=True) if date_el else ""

            hackathons.append({
                "source": "opportunities_africa",
                "title": title,
                "url": card_url,
                "theme": theme,
                "format": "online",
                "location": "Afrique",
                "prize_raw": "",
                "prize_min_fcfa": 0,
                "prize_1st": "",
                "prize_2nd": "",
                "prize_3rd": "",
                "deadline": deadline,
                "language": "fr/en",
            })
        except Exception as e:
            print(f"  [OpportunitiesAfrica] Erreur parsing : {e}")
            continue

    print(f"  [OpportunitiesAfrica] {len(hackathons)} opportunités collectées")
    return hackathons

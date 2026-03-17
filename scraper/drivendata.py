import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "https://www.drivendata.org/competitions/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}


def scrape_drivendata() -> list:
    """Scrape les compétitions actives sur DrivenData"""
    hackathons = []

    print("  [DrivenData] Scraping en cours...")
    try:
        resp = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [DrivenData] Erreur : {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select(".competition-tile, .challenge-card, [class*='competition']")

    for card in cards:
        hack = _parse_card(card)
        if hack:
            hackathons.append(hack)

    print(f"  [DrivenData] {len(hackathons)} compétitions collectées")
    return hackathons


def _parse_card(card) -> dict | None:
    try:
        title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
        title = title_el.get_text(strip=True) if title_el else None
        if not title:
            return None

        link_el = card.select_one("a[href]")
        url = link_el["href"] if link_el else None
        if not url:
            return None
        if not url.startswith("http"):
            url = "https://www.drivendata.org" + url

        prize_el = card.select_one("[class*='prize'], [class*='award'], [class*='reward']")
        prize_text = prize_el.get_text(strip=True) if prize_el else ""

        desc_el = card.select_one("p, [class*='desc'], [class*='description']")
        theme = desc_el.get_text(strip=True)[:200] if desc_el else ""

        deadline_el = card.select_one("time, [class*='date'], [class*='deadline'], [class*='closes']")
        deadline = ""
        if deadline_el:
            deadline = deadline_el.get("datetime") or deadline_el.get_text(strip=True)

        return {
            "source": "drivendata",
            "title": title,
            "url": url,
            "theme": theme,
            "format": "online",  # DrivenData = toujours en ligne
            "location": "En ligne — International",
            "prize_raw": prize_text,
            "prize_min_fcfa": _extract_min_fcfa(prize_text),
            "prize_1st": _extract_prize_rank(prize_text, 1),
            "prize_2nd": _extract_prize_rank(prize_text, 2),
            "prize_3rd": _extract_prize_rank(prize_text, 3),
            "deadline": deadline,
            "language": "en",
        }
    except Exception as e:
        print(f"  [DrivenData] Erreur parsing : {e}")
        return None


def _extract_min_fcfa(prize_text: str) -> int:
    if not prize_text:
        return 0
    amounts = re.findall(r"\$\s?([\d,]+)", prize_text)
    if not amounts:
        return 0
    values = [int(a.replace(",", "")) for a in amounts]
    return int(min(values) * 655)


def _extract_prize_rank(prize_text: str, rank: int) -> str:
    if not prize_text:
        return ""
    amounts = re.findall(r"\$\s?([\d,]+)", prize_text)
    if len(amounts) >= rank:
        usd = int(amounts[rank - 1].replace(",", ""))
        return f"${usd:,} (~{usd * 655:,} FCFA)"
    return ""

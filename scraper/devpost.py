import requests
from bs4 import BeautifulSoup
import time
import re

BASE_URL = "https://devpost.com/hackathons"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

def scrape_devpost(pages: int = 5) -> list:
    """Scrape les hackathons sur Devpost — retourne une liste de dicts bruts"""
    hackathons = []

    for page in range(1, pages + 1):
        url = f"{BASE_URL}?page={page}&order_by=deadline"
        print(f"  [Devpost] Page {page}...")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [Devpost] Erreur page {page} : {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("article.hackathon-tile, div.hackathon-tile, li.hackathon")

        if not cards:
            # Essai avec un sélecteur alternatif
            cards = soup.select("[class*='hackathon']")

        if not cards:
            print(f"  [Devpost] Aucune carte trouvée page {page}, arrêt.")
            break

        for card in cards:
            hack = _parse_card(card)
            if hack:
                hackathons.append(hack)

        time.sleep(2)  # pause pour ne pas surcharger le serveur

    print(f"  [Devpost] {len(hackathons)} hackathons collectés")
    return hackathons


def _parse_card(card) -> dict | None:
    """Extrait les données d'une carte hackathon Devpost"""
    try:
        # Titre
        title_el = card.select_one("h2, h3, .title, [class*='title']")
        title = title_el.get_text(strip=True) if title_el else None
        if not title:
            return None

        # URL
        link_el = card.select_one("a[href*='devpost.com'], a[href]")
        url = link_el["href"] if link_el else None
        if not url:
            return None
        if not url.startswith("http"):
            url = "https://devpost.com" + url

        # Prix
        prize_text = ""
        prize_el = card.select_one("[class*='prize'], [class*='Prize']")
        if prize_el:
            prize_text = prize_el.get_text(strip=True)

        # Dates
        deadline = ""
        date_el = card.select_one("time, [class*='date'], [class*='deadline']")
        if date_el:
            deadline = date_el.get("datetime") or date_el.get_text(strip=True)

        # Format (en ligne ou présentiel)
        location = ""
        loc_el = card.select_one("[class*='location'], [class*='where']")
        if loc_el:
            location = loc_el.get_text(strip=True)

        # Thème / description
        theme = ""
        desc_el = card.select_one("p, [class*='desc'], [class*='tagline']")
        if desc_el:
            theme = desc_el.get_text(strip=True)[:200]

        return {
            "source": "devpost",
            "title": title,
            "url": url,
            "theme": theme,
            "format": _detect_format(location + " " + title + " " + theme),
            "location": location,
            "prize_raw": prize_text,
            "prize_min_fcfa": _extract_min_prize_fcfa(prize_text),
            "prize_1st": _extract_prize_rank(prize_text, 1),
            "prize_2nd": _extract_prize_rank(prize_text, 2),
            "prize_3rd": _extract_prize_rank(prize_text, 3),
            "deadline": deadline,
            "language": _detect_language(title + " " + theme),
        }
    except Exception as e:
        print(f"  [Devpost] Erreur parsing carte : {e}")
        return None


def _detect_format(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ["online", "virtual", "en ligne", "remote"]):
        if any(w in text_lower for w in ["in-person", "final", "finale", "présentiel"]):
            return "hybrid"
        return "online"
    if any(w in text_lower for w in ["in-person", "présentiel", "on-site"]):
        return "in-person"
    return "online"  # défaut : en ligne


def _detect_language(text: str) -> str:
    text_lower = text.lower()
    has_fr = any(w in text_lower for w in ["français", "french", "francophone", "en français"])
    has_en = any(w in text_lower for w in ["english", "anglais"])
    if has_fr and has_en:
        return "fr/en"
    if has_fr:
        return "fr"
    return "en"  # défaut


def _extract_min_prize_fcfa(prize_text: str) -> int:
    """Extrait le montant minimum (3e prix) et le convertit en FCFA — 1 USD ≈ 655 FCFA"""
    if not prize_text:
        return 0
    amounts = re.findall(r"\$\s?([\d,]+)", prize_text)
    if not amounts:
        return 0
    values = [int(a.replace(",", "")) for a in amounts]
    min_val = min(values)
    return int(min_val * 655)


def _extract_prize_rank(prize_text: str, rank: int) -> str:
    if not prize_text:
        return ""
    amounts = re.findall(r"\$\s?([\d,]+)", prize_text)
    if len(amounts) >= rank:
        usd = int(amounts[rank - 1].replace(",", ""))
        fcfa = usd * 655
        return f"${usd:,} (~{fcfa:,} FCFA)"
    return ""
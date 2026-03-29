"""
scraper/devpost.py — Scraper Devpost via API JSON officielle
Plus fiable que le scraping HTML (site dynamique React).
API endpoint: https://devpost.com/api/hackathons
"""
import requests
import re
from typing import Optional

BASE_API = "https://devpost.com/api/hackathons"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def scrape_devpost(pages: int = 5) -> list:
    """Scrape les hackathons sur Devpost via l'API JSON officielle"""
    hackathons = []
    for page in range(1, pages + 1):
        print(f"  [Devpost] Page {page}...")
        try:
            resp = requests.get(
                BASE_API,
                params={"order_by": "deadline", "status[]": ["upcoming", "open"], "page": page},
                headers=HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  [Devpost] Erreur page {page} : {e}")
            break

        items = data.get("hackathons", [])
        if not items:
            print(f"  [Devpost] Page {page} vide, arrêt.")
            break

        for item in items:
            hack = _parse_item(item)
            if hack:
                hackathons.append(hack)

    print(f"  [Devpost] {len(hackathons)} hackathons collectés")
    return hackathons


def _parse_item(item: dict) -> Optional[dict]:
    try:
        title = item.get("title", "").strip()
        if not title:
            return None

        url = item.get("url", "")
        if not url:
            return None
        # L'API Devpost peut retourner des URLs relatives (/d/online/hackathon/...)
        if url and not url.startswith("http"):
            url = "https://devpost.com" + url

        # Localisation et format
        location_info = item.get("displayed_location", {})
        location = location_info.get("location", "Online")
        location_icon = location_info.get("icon", "globe")
        fmt = "online" if location_icon == "globe" else "in-person"

        # Date (submission_period_dates)
        deadline = item.get("submission_period_dates", "") or item.get("time_left_to_submission", "")

        # Thème depuis les tags
        themes = item.get("themes", [])
        theme = ", ".join(t.get("name", "") for t in themes if t.get("name"))

        # Prix (strip HTML du prize_amount)
        prize_raw = item.get("prize_amount", "")
        prize_clean = re.sub(r"<[^>]+>", "", prize_raw).strip()  # retirer HTML
        prize_counts = item.get("prizes_counts", {})
        prize_text = prize_clean if prize_clean not in ("$0", "0", "") else ""

        return {
            "source": "devpost",
            "title": title,
            "url": url,
            "theme": theme,
            "format": fmt,
            "location": location,
            "prize_raw": prize_text,
            "prize_min_fcfa": _extract_min_prize_fcfa(prize_text),
            "prize_1st": prize_text if prize_text else "",
            "prize_2nd": "",
            "prize_3rd": "",
            "deadline": deadline,
            "language": _detect_language(title + " " + theme),
        }
    except Exception as e:
        print(f"  [Devpost] Erreur parsing item : {e}")
        return None


def _detect_format(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ["online", "virtual", "en ligne", "remote"]):
        if any(w in text_lower for w in ["in-person", "final", "finale", "présentiel"]):
            return "hybrid"
        return "online"
    if any(w in text_lower for w in ["in-person", "présentiel", "on-site"]):
        return "in-person"
    return "online"


def _detect_language(text: str) -> str:
    text_lower = text.lower()
    has_fr = any(w in text_lower for w in ["français", "french", "francophone", "en français"])
    has_en = any(w in text_lower for w in ["english", "anglais"])
    if has_fr and has_en:
        return "fr/en"
    if has_fr:
        return "fr"
    return "en"


def _extract_min_prize_fcfa(prize_text: str) -> int:
    if not prize_text:
        return 0
    amounts = re.findall(r"\$\s?([\d,]+)", prize_text)
    if not amounts:
        return 0
    values = [int(a.replace(",", "")) for a in amounts]
    return int(min(values) * 655)
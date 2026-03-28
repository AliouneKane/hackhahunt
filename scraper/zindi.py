"""
scraper/zindi.py — Scraper Zindi Africa via API JSON officielle
Plus fiable que le HTML (site dynamique).
API endpoint: https://api.zindi.africa/v1/competitions
"""
import requests
import re
from typing import Optional

API_URL = "https://api.zindi.africa/v1/competitions"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def scrape_zindi() -> list:
    """Scrape les compétitions actives sur Zindi Africa via l'API JSON"""
    hackathons = []
    print("  [Zindi] Scraping en cours...")

    seen_ids = set()
    for status in ["active", "upcoming"]:
        try:
            resp = requests.get(API_URL, params={"status": status}, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  [Zindi] Erreur ({status}) : {e}")
            continue

        competitions = data.get("data", [])
        for comp in competitions:
            hack = _parse_comp(comp)
            if hack and hack["url"] not in seen_ids:
                seen_ids.add(hack["url"])
                hackathons.append(hack)


    print(f"  [Zindi] {len(hackathons)} compétitions collectées")
    return hackathons


def _parse_comp(comp: dict) -> Optional[dict]:
    try:
        title = comp.get("title", "").strip()
        if not title:
            return None

        comp_id = comp.get("id", "")
        url = f"https://zindi.africa/competitions/{comp_id}" if comp_id else None
        if not url:
            return None

        reward = comp.get("reward", "") or ""
        deadline = comp.get("end_time", "") or ""
        # Simplifier la date ISO en format lisible
        if "T" in deadline:
            deadline = deadline.split("T")[0]

        prize_text = reward.strip() if reward else ""
        prize_min = _extract_min_fcfa(prize_text)

        kind = comp.get("kind", "competition")
        theme = f"Compétition IA/Data — Afrique ({kind})"

        return {
            "source": "zindi",
            "title": title,
            "url": url,
            "theme": theme,
            "format": "online",  # Zindi = toujours en ligne
            "location": "En ligne — Afrique",
            "prize_raw": prize_text,
            "prize_min_fcfa": prize_min,
            "prize_1st": prize_text,
            "prize_2nd": "",
            "prize_3rd": "",
            "deadline": deadline,
            "language": "en",
        }
    except Exception as e:
        print(f"  [Zindi] Erreur parsing : {e}")
        return None


def _extract_min_fcfa(prize_text: str) -> int:
    if not prize_text:
        return 0
    amounts = re.findall(r"\$\s*([\d,]+)", prize_text)
    if not amounts:
        fcfa_amounts = re.findall(r"([\d,]+)\s*(?:FCFA|XOF)", prize_text)
        if fcfa_amounts:
            return int(fcfa_amounts[-1].replace(",", ""))
        return 0
    values = [int(a.replace(",", "")) for a in amounts]
    return int(min(values) * 655)
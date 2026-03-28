import requests
import time

BASE_URL = "https://www.kaggle.com/api/v1/competitions/list"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

def scrape_kaggle() -> list:
    print("  [Kaggle] Scraping en cours...")
    hackathons = []

    try:
        resp = requests.get(
            BASE_URL,
            headers=HEADERS,
            params={"sortBy": "latestDeadline", "pageSize": 50, "category": "featured"},
            timeout=15
        )
        resp.raise_for_status()
        competitions = resp.json()
    except Exception as e:
        print(f"  [Kaggle] Erreur API : {e}")
        return []

    for comp in competitions:
        try:
            title = comp.get("title") or comp.get("name", "")
            if not title:
                continue

            url = f"https://www.kaggle.com/c/{comp.get('ref', '')}"
            deadline = comp.get("deadline", "")
            prize_usd = comp.get("reward", 0) or 0
            desc = comp.get("description", "")[:200]
            category = comp.get("category", "")

            # Convertir prize en FCFA
            try:
                prize_int = int(str(prize_usd).replace("$", "").replace(",", "").strip()) if prize_usd else 0
            except:
                prize_int = 0

            prize_fcfa = prize_int * 655
            prize_str = f"${prize_int:,} (~{prize_fcfa:,} FCFA)" if prize_int > 0 else ""

            hackathons.append({
                "source": "kaggle",
                "title": title,
                "url": url,
                "theme": desc or category,
                "format": "online",
                "location": "En ligne — International",
                "prize_raw": str(prize_usd),
                "prize_min_fcfa": prize_fcfa,
                "prize_1st": prize_str,
                "prize_2nd": "",
                "prize_3rd": "",
                "deadline": str(deadline)[:10] if deadline else "",
                "language": "en",
            })
        except Exception as e:
            print(f"  [Kaggle] Erreur parsing : {e}")
            continue

    print(f"  [Kaggle] {len(hackathons)} compétitions collectées")
    return hackathons

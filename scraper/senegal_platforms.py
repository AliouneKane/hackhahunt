"""
senegal_platforms.py — Recherche DuckDuckGo de hackathons au Sénégal
Méthode simple, gratuite, sans CAPTCHA.
Filtre automatiquement les résultats dont la date est dépassée.
"""

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

# Requêtes dynamiques : l'année courante est injectée automatiquement
def _build_queries() -> list:
    year = datetime.now().year
    return [
        f"hackathon sénégal {year} {year + 1}",
        f"hackathon dakar {year} {year + 1}",
        f"challenge innovation sénégal {year}",
        f"compétition data science sénégal {year}",
        f"hackathon afrique de l'ouest {year}",
        f"concours tech dakar {year}",
    ]

# Domaines à ignorer
SKIP_DOMAINS = [
    "youtube.com", "wikipedia.org", "facebook.com", "twitter.com",
    "x.com", "linkedin.com", "instagram.com", "tiktok.com",
    "pinterest.com", "reddit.com",
]

# Mots-clés pour filtrer les résultats pertinents
RELEVANT_WORDS = [
    "hackathon", "hack", "challenge", "compétition", "competition",
    "concours", "data", "innov", "coding", "code", "tech",
]


def _extract_deadline(text: str) -> str:
    """Essaie d'extraire une date depuis le titre + snippet.
    Retourne une chaîne lisible ou '' si rien trouvé."""
    import dateparser

    # 1. Chercher des patterns de date explicites (ex: "15 mars 2026", "March 15, 2026")
    date_patterns = [
        r'\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}',
        r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}',
        r'\d{1,2}/\d{1,2}/\d{4}',
        r'\d{4}-\d{2}-\d{2}',
        r'\d{1,2}\s+(?:jan|fév|mar|avr|mai|jun|jul|aoû|sep|oct|nov|déc)\.?\s+\d{4}',
    ]

    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parsed = dateparser.parse(match.group(), settings={"PREFER_DAY_OF_MONTH": "last"})
            if parsed:
                return parsed.strftime("%d %B %Y")

    return ""


def _is_past_event(title: str, snippet: str) -> bool:
    """Détecte si un résultat est clairement un événement passé."""
    now = datetime.now()
    current_year = now.year
    text = (title + " " + snippet).lower()

    # Si le texte mentionne uniquement des années passées et aucune année courante/future
    years_found = [int(y) for y in re.findall(r'\b(20\d{2})\b', text)]
    if years_found:
        max_year = max(years_found)
        if max_year < current_year:
            return True

    # Mots-clés indiquant un événement terminé
    past_markers = ["résultats", "gagnants", "winners", "recap", "retour sur",
                    "was held", "a eu lieu", "s'est tenu", "édition précédente"]
    if any(m in text for m in past_markers):
        # Sauf si une année future est aussi mentionnée
        if not any(y >= current_year for y in years_found):
            return True

    # Essayer dateparser sur le texte pour trouver une date explicite
    import dateparser
    date_patterns = [
        r'\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}',
        r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}',
        r'\d{1,2}/\d{1,2}/\d{4}',
        r'\d{4}-\d{2}-\d{2}',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parsed = dateparser.parse(match.group(), settings={"PREFER_DAY_OF_MONTH": "last"})
            if parsed and parsed.replace(tzinfo=None) < now:
                return True

    return False


def scrape_google_senegal() -> list:
    """Recherche DuckDuckGo pour trouver des hackathons au Sénégal."""
    print("  [GoogleSenegal] Scraping en cours...")
    hackathons = []
    seen_urls = set()
    skipped_past = 0

    for query in _build_queries():
        try:
            resp = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=HEADERS,
                timeout=15,
            )
            if resp.status_code != 200:
                print(f"  [GoogleSenegal] Status {resp.status_code} pour '{query}'")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            results = soup.select(".result")

            for result in results:
                try:
                    link_el = result.select_one("a.result__a")
                    if not link_el:
                        continue

                    title = link_el.get_text(strip=True)
                    result_url = link_el.get("href", "")

                    # DuckDuckGo encapsule parfois l'URL dans un redirect
                    if "uddg=" in result_url:
                        from urllib.parse import unquote, parse_qs, urlparse
                        parsed = urlparse(result_url)
                        qs = parse_qs(parsed.query)
                        result_url = unquote(qs.get("uddg", [result_url])[0])

                    if not result_url.startswith("http"):
                        continue
                    if any(d in result_url for d in SKIP_DOMAINS):
                        continue
                    if result_url in seen_urls:
                        continue
                    seen_urls.add(result_url)

                    if not title:
                        continue

                    # Filtrer : garder ce qui ressemble à un hackathon
                    title_lower = title.lower()
                    if not any(w in title_lower for w in RELEVANT_WORDS):
                        continue

                    # Snippet
                    desc_el = result.select_one(".result__snippet")
                    snippet = desc_el.get_text(strip=True)[:200] if desc_el else ""

                    # ── Filtre date : rejeter les événements passés ──
                    if _is_past_event(title, snippet):
                        skipped_past += 1
                        continue

                    # Extraire une deadline si possible
                    deadline = _extract_deadline(title + " " + snippet)

                    theme = snippet if snippet else f"Trouvé via recherche : {query}"

                    # Deviner format
                    all_text = (title + " " + theme).lower()
                    if any(w in all_text for w in ["en ligne", "online", "virtual", "remote"]):
                        fmt = "online"
                    elif any(w in all_text for w in ["hybride", "hybrid"]):
                        fmt = "hybrid"
                    else:
                        fmt = "hybrid"

                    lang = "fr" if any(w in all_text for w in ["sénégal", "dakar", "concours", "compétition"]) else "fr/en"

                    hackathons.append({
                        "source": "google_senegal",
                        "title": title,
                        "url": result_url,
                        "theme": theme,
                        "format": fmt,
                        "location": "Sénégal",
                        "prize_raw": "",
                        "prize_min_fcfa": 0,
                        "prize_1st": "",
                        "prize_2nd": "",
                        "prize_3rd": "",
                        "deadline": deadline,
                        "language": lang,
                    })
                except Exception:
                    continue

            time.sleep(3)

        except Exception as e:
            print(f"  [GoogleSenegal] Erreur '{query}' : {e}")
            continue

    print(f"  [GoogleSenegal] {len(hackathons)} résultats collectés, {skipped_past} expirés ignorés")
    return hackathons

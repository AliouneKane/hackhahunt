#!/usr/bin/env python3
"""
scraper_cron.py — Script autonome de scraping (sans Discord, sans asyncio).
Lance tous les scrapers, filtre, insère en DB.
À exécuter via LaunchAgent toutes les 6h — complètement indépendant du bot.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

import requests
import database as db
from datetime import datetime


def discord_log(message: str):
    token = os.getenv("DISCORD_TOKEN")
    channel_id = os.getenv("BOT_LOGS_CHANNEL_ID")
    if not token or not channel_id:
        return
    try:
        requests.post(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers={"Authorization": f"Bot {token}", "Content-Type": "application/json"},
            json={"content": message},
            timeout=10,
        )
    except Exception:
        pass
from scraper.devpost import scrape_devpost
from scraper.zindi import scrape_zindi
from scraper.mlh import scrape_mlh
from scraper.kaggle import scrape_kaggle
from scraper.hackmakers import scrape_hackmakers
from scraper.french_platforms import scrape_challengedata, scrape_challengerocket
from scraper.africa_platforms import (
    scrape_a2sv,
    scrape_geekulcha,
    scrape_opportunities_africa,
)
from scraper.eventbrite import scrape_eventbrite
from scraper.drivendata import scrape_drivendata
from scraper.senegal_platforms import scrape_google_senegal
from scraper.scorer import filter_and_score

SCRAPERS = [
    {"fn": lambda: scrape_devpost(pages=5), "name": "Devpost"},
    {"fn": scrape_zindi, "name": "Zindi"},
    {"fn": scrape_mlh, "name": "MLH"},
    {"fn": scrape_kaggle, "name": "Kaggle"},
    {"fn": scrape_hackmakers, "name": "Hackmakers"},
    {"fn": scrape_challengedata, "name": "ChallengeData"},
    {"fn": scrape_challengerocket, "name": "Challengerocket"},
    {"fn": scrape_a2sv, "name": "A2SV"},
    {"fn": scrape_geekulcha, "name": "Geekulcha"},
    {"fn": scrape_opportunities_africa, "name": "OpportunitiesAfrica"},
    {"fn": scrape_eventbrite, "name": "Eventbrite"},
    {"fn": scrape_drivendata, "name": "DrivenData"},
    {"fn": scrape_google_senegal, "name": "GoogleSenegal"},
]


def _is_deadline_expired(deadline_str) -> bool:
    if not deadline_str:
        return False
    import re
    from datetime import datetime as dt

    now = dt.now()
    d = deadline_str.replace("byOFA", "").lower().replace("ended", "").strip()
    if not d or d in ("ended", "terminé", "closed", "over"):
        return True
    if " - " in d:
        d = d.split(" - ")[-1].strip()
    elif "-" in d and not deadline_str.startswith("202"):
        d = d.split("-")[-1].strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", d)
    if m:
        try:
            return dt(int(m.group(1)), int(m.group(2)), int(m.group(3))) < now
        except ValueError:
            pass
    import dateparser
    parsed = dateparser.parse(
        d, settings={"STRICT_PARSING": False, "PREFER_DAY_OF_MONTH": "last"}
    )
    if parsed:
        return parsed.replace(tzinfo=None) < now
    return False


def run():
    start = datetime.now()
    print(f"[{start:%Y-%m-%d %H:%M}] ── Scraping démarré ──")
    discord_log(f"🔍 **Le bot est en train de parcourir les 13 plateformes** à la recherche de nouveaux hackathons ({start:%d/%m/%Y à %H:%M}). Cette étape prend 1 à 2 minutes, ne t'inquiète pas si tu ne vois rien pendant ce temps.")

    db.init_db()

    all_raw = []
    errors = []
    for scraper in SCRAPERS:
        try:
            results = scraper["fn"]()
            all_raw.extend(results)
            status = "✅" if results else "❌"
            print(f"  {status} {scraper['name']}: {len(results)}")
        except Exception as e:
            print(f"  ❌ {scraper['name']}: {e}")
            errors.append(scraper["name"])

    print(f"{len(all_raw)} hackathons bruts collectés")

    filtered = filter_and_score(all_raw)
    print(f"{len(filtered)} hackathons retenus après scoring")

    new_inserts = 0
    expired_skipped = 0
    for hack in filtered:
        if _is_deadline_expired(hack.get("deadline")):
            expired_skipped += 1
            continue
        hack_id = db.insert_hackathon(hack)
        if hack_id is not None:
            new_inserts += 1

    elapsed = (datetime.now() - start).total_seconds()
    print(
        f"[{datetime.now():%Y-%m-%d %H:%M}] ── Terminé en {elapsed:.0f}s : "
        f"{new_inserts} nouveaux, {expired_skipped} expirés ignorés ──"
    )

    if new_inserts > 0:
        summary = f"✅ **Le bot a fini de scraper les 13 plateformes** ({elapsed:.0f}s). Il a trouvé **{new_inserts} nouveau(x) hackathon(s)** et les a ajoutés à la file — il est maintenant en train de les poster dans #hackathons un par un, toutes les 5 minutes."
    else:
        summary = f"✅ **Le bot a fini de scraper les 13 plateformes** ({elapsed:.0f}s). Aucun nouveau hackathon trouvé — tout ce qui est disponible est déjà dans la base. Prochain scraping dans 30 minutes."
    if errors:
        summary += f"\n⚠️ Ces plateformes n'ont pas répondu et ont été ignorées cette fois : {', '.join(errors)}."
    discord_log(summary)


if __name__ == "__main__":
    run()

"""
scraper/runner.py — Orchestrateur principal du scraping
Lance tous les scrapers, score les résultats et les poste sur Discord.
"""
import discord
import asyncio
import os
import database as db

from scraper.devpost import scrape_devpost
from scraper.zindi import scrape_zindi
from scraper.mlh import scrape_mlh
from scraper.kaggle import scrape_kaggle
from scraper.hackmakers import scrape_hackmakers
from scraper.french_platforms import scrape_challengedata, scrape_challengerocket
from scraper.africa_platforms import scrape_a2sv, scrape_geekulcha, scrape_opportunities_africa
from scraper.eventbrite import scrape_eventbrite
from scraper.drivendata import scrape_drivendata
from scraper.scorer import filter_and_score

HACKATHON_CHANNEL_ID = int(os.getenv("HACKATHON_CHANNEL_ID", "0"))

LEVEL_COLORS = {
    "Débutant":      0x1D9E75,
    "Intermédiaire": 0x185FA5,
    "Avancé":        0xBA7517,
    "Recherche":     0xA32D2D,
}

LEVEL_DESCRIPTIONS = {
    "Débutant":      "Aucun prérequis technique fort. Idéal pour une 1ère expérience.",
    "Intermédiaire": "Python / R recommandé. Niveau L3 / 1ère année ENSAE.",
    "Avancé":        "Deep learning, NLP ou économétrie avancée. Niveau 2e–3e année ENSAE.",
    "Recherche":     "Travaux académiques attendus. Jury de chercheurs.",
}

SCRAPERS = [
    {"fn": lambda: scrape_devpost(pages=5), "name": "Devpost"},
    {"fn": scrape_zindi,                    "name": "Zindi"},
    {"fn": scrape_mlh,                      "name": "MLH"},
    {"fn": scrape_kaggle,                   "name": "Kaggle"},
    {"fn": scrape_hackmakers,               "name": "Hackmakers"},
    {"fn": scrape_challengedata,            "name": "ChallengeData"},
    {"fn": scrape_challengerocket,          "name": "Challengerocket"},
    {"fn": scrape_a2sv,                     "name": "A2SV"},
    {"fn": scrape_geekulcha,                "name": "Geekulcha"},
    {"fn": scrape_opportunities_africa,     "name": "OpportunitiesAfrica"},
    {"fn": scrape_eventbrite,               "name": "Eventbrite"},
    {"fn": scrape_drivendata,               "name": "DrivenData"},
]


async def run_all_scrapers(bot: discord.Client):
    print("Démarrage du scraping — 12 sources...")
    all_raw = []
    source_stats = {}

    for scraper in SCRAPERS:
        try:
            results = scraper["fn"]()
            source_stats[scraper['name']] = len(results)
            all_raw.extend(results)
        except Exception as e:
            print(f"  [{scraper['name']}] Erreur inattendue : {e}")
            source_stats[scraper['name']] = 0

    print(f"{len(all_raw)} hackathons bruts collectés")
    for name, count in source_stats.items():
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {name}: {count}")

    filtered = filter_and_score(all_raw)
    print(f"{len(filtered)} hackathons retenus après scoring")

    channel = bot.get_channel(HACKATHON_CHANNEL_ID)
    if not channel:
        print(f"Canal introuvable (ID: {HACKATHON_CHANNEL_ID})")
        return 0

    posted = 0
    for hack in filtered:
        hack_id = db.insert_hackathon(hack)
        if hack_id is None:
            continue

        embed = build_embed(hack)
        try:
            msg = await channel.send(embed=embed)
            await msg.add_reaction("👍")
            await msg.add_reaction("❌")
            db.update_message_id(hack_id, str(msg.id))
            posted += 1
            await asyncio.sleep(1)
        except Exception as e:
            print(f"  Erreur envoi Discord : {e}")

    print(f"{posted} nouveaux hackathons postés sur Discord")
    return posted


def build_embed(hack: dict) -> discord.Embed:
    level = hack.get("level", "Intermédiaire")
    color = LEVEL_COLORS.get(level, 0x534AB7)
    score = hack.get("score", 0)

    source_label = hack.get("source", "").capitalize()
    title = f"{hack['title']} — {source_label}"

    embed = discord.Embed(title=title, url=hack.get("url", ""), color=color)

    if hack.get("theme"):
        embed.add_field(name="Thème", value=hack["theme"][:200], inline=False)

    fmt_map = {
        "online":    "100% en ligne",
        "hybrid":    "En ligne + finale en présentiel",
        "in-person": "Présentiel uniquement",
    }
    fmt_label = fmt_map.get(hack.get("format", "online"), hack.get("format", ""))
    location = hack.get("location", "")
    embed.add_field(
        name="Format",
        value=fmt_label + (f" — {location}" if location else ""),
        inline=True
    )

    lang_map = {"fr": "Français", "en": "Anglais", "fr/en": "Français / Anglais"}
    embed.add_field(
        name="Langue",
        value=lang_map.get(hack.get("language", "en"), "Anglais"),
        inline=True
    )

    if hack.get("deadline"):
        embed.add_field(name="Deadline", value=hack["deadline"], inline=True)

    prizes = []
    if hack.get("prize_1st"):
        prizes.append(f"1er : {hack['prize_1st']}")
    if hack.get("prize_2nd"):
        prizes.append(f"2e : {hack['prize_2nd']}")
    if hack.get("prize_3rd"):
        prizes.append(f"3e : {hack['prize_3rd']}")

    prize_text = " · ".join(prizes)
    if not prize_text and hack.get("prize_raw"):
        prize_text = hack["prize_raw"]
    
    if prize_text:
        embed.add_field(name="Prix à gagner", value=prize_text[:1024], inline=False)
        
    embed.add_field(name="Taille d'équipe", value="Généralement 1 à 4 personnes", inline=True)

    level_desc = LEVEL_DESCRIPTIONS.get(level, "")
    embed.add_field(name=f"Niveau : {level}", value=level_desc, inline=False)

    score_bar = "█" * score + "░" * (10 - score)
    embed.set_footer(
        text=f"Score Hackahunt : {score}/10  {score_bar}  · Clique 👍 si tu es intéressé(e)"
    )
    return embed

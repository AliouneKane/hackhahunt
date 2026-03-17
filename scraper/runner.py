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
from scraper.drivendata import scrape_drivendata
from scraper.scorer import filter_and_score

HACKATHON_CHANNEL_ID = int(os.getenv("HACKATHON_CHANNEL_ID", "0"))

# Couleur par niveau
LEVEL_COLORS = {
    "Débutant":      0x1D9E75,  # vert
    "Intermédiaire": 0x185FA5,  # bleu
    "Avancé":        0xBA7517,  # amber
    "Recherche":     0xA32D2D,  # rouge
}

LEVEL_DESCRIPTIONS = {
    "Débutant":      "Aucun prérequis technique fort. Idéal pour une 1ère expérience.",
    "Intermédiaire": "Python / R recommandé. Niveau L3 / 1ère année ENSAE.",
    "Avancé":        "Deep learning, NLP ou économétrie avancée. Niveau 2e–3e année ENSAE.",
    "Recherche":     "Travaux académiques attendus. Jury de chercheurs.",
}


async def run_all_scrapers(bot: discord.Client):
    """Lance tous les scrapers et poste les nouveaux hackathons sur Discord"""
    print("🔍 Démarrage du scraping...")

    all_raw = []

    # Devpost
    devpost_results = scrape_devpost(pages=5)
    all_raw.extend(devpost_results)

    # Zindi
    zindi_results = scrape_zindi()
    all_raw.extend(zindi_results)

    # DrivenData
    driven_results = scrape_drivendata()
    all_raw.extend(driven_results)

    print(f"📦 {len(all_raw)} hackathons bruts collectés au total")

    # Scoring + filtrage
    filtered = filter_and_score(all_raw)
    print(f"✅ {len(filtered)} hackathons retenus après scoring")

    # Poster sur Discord
    channel = bot.get_channel(HACKATHON_CHANNEL_ID)
    if not channel:
        print(f"❌ Canal introuvable (ID: {HACKATHON_CHANNEL_ID})")
        return

    posted = 0
    for hack in filtered:
        # Vérifier si déjà en base (URL unique)
        hack_id = db.insert_hackathon(hack)
        if hack_id is None:
            continue  # Déjà posté

        # Construire l'embed Discord
        embed = build_embed(hack)

        try:
            msg = await channel.send(embed=embed)
            await msg.add_reaction("👍")
            await msg.add_reaction("❌")
            db.update_message_id(hack_id, str(msg.id))
            posted += 1
            await asyncio.sleep(1)  # Éviter le rate limit Discord
        except Exception as e:
            print(f"  ❌ Erreur envoi Discord : {e}")

    print(f"📣 {posted} nouveaux hackathons postés sur Discord")
    return posted


def build_embed(hack: dict) -> discord.Embed:
    """Construit l'embed Discord pour un hackathon"""
    level = hack.get("level", "Intermédiaire")
    color = LEVEL_COLORS.get(level, 0x534AB7)
    score = hack.get("score", 0)

    # Titre avec source
    source_label = hack.get("source", "").capitalize()
    title = f"{hack['title']} — {source_label}"

    embed = discord.Embed(title=title, url=hack.get("url", ""), color=color)

    # Thème
    if hack.get("theme"):
        embed.add_field(name="Thème", value=hack["theme"][:200], inline=False)

    # Format + localisation
    fmt_map = {
        "online": "100% en ligne",
        "hybrid": "En ligne + finale en présentiel",
        "in-person": "Présentiel uniquement",
    }
    fmt_label = fmt_map.get(hack.get("format", "online"), hack.get("format", ""))
    location = hack.get("location", "")
    location_str = f"{fmt_label}" + (f" — {location}" if location else "")
    embed.add_field(name="Format", value=location_str, inline=True)

    # Langue
    lang_map = {"fr": "Français", "en": "Anglais", "fr/en": "Français / Anglais"}
    embed.add_field(
        name="Langue",
        value=lang_map.get(hack.get("language", "en"), "Anglais"),
        inline=True
    )

    # Deadline
    if hack.get("deadline"):
        embed.add_field(name="Deadline", value=hack["deadline"], inline=True)

    # Prix
    prizes = []
    if hack.get("prize_1st"):
        prizes.append(f"1er : {hack['prize_1st']}")
    if hack.get("prize_2nd"):
        prizes.append(f"2e : {hack['prize_2nd']}")
    if hack.get("prize_3rd"):
        prizes.append(f"3e : {hack['prize_3rd']}")
    if prizes:
        embed.add_field(name="Prix", value=" · ".join(prizes), inline=False)

    # Niveau de difficulté
    level_desc = LEVEL_DESCRIPTIONS.get(level, "")
    embed.add_field(
        name=f"Niveau : {level}",
        value=level_desc,
        inline=False
    )

    # Footer avec score
    score_bar = "█" * score + "░" * (10 - score)
    embed.set_footer(text=f"Score Hackahunt : {score}/10  {score_bar}  · Clique 👍 si tu es intéressé(e)")

    return embed
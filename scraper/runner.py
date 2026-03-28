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
ARCHIVES_CHANNEL_ID = int(os.getenv("ARCHIVES_CHANNEL_ID", "0"))
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

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

    new_inserts = 0
    for hack in filtered:
        # Seuls les hacks n'existant pas encore seront ajoutés (id is not None)
        hack_id = db.insert_hackathon(hack)
        if hack_id is not None:
            new_inserts += 1

    print(f"Scraping fini : {new_inserts} nouveaux hackathons insérés en base (en attente de post).")
    return new_inserts


async def post_pending_hackathons(bot: discord.Client, limit: int = 10):
    """Poste une poignée de hackathons encore non publiés pour éviter de spammer."""
    channel = bot.get_channel(HACKATHON_CHANNEL_ID)
    if not channel:
        print(f"Canal introuvable (ID: {HACKATHON_CHANNEL_ID})")
        return 0

    import dateparser
    from datetime import datetime
    
    now = datetime.now()
    posted = 0
    total_posted = 0
    
    print(f"🚀 Publication de hackathons (Objectif: {limit})...")
    
    while total_posted < limit:
        # Fetching remaining amount to reach limit
        pending = db.get_unposted_hackathons(limit=min(10, limit - total_posted))
        if not pending:
            break

        for hack in pending:
            deadline_str = hack.get("deadline")
            expired = False
            
            if deadline_str:
                d_clean = deadline_str.replace("byOFA", "").strip()
                if " - " in d_clean:
                    d_clean = d_clean.split(" - ")[-1].strip()
                elif "-" in d_clean and not deadline_str.startswith("202"):
                    # If it's a range like Mar 21-28, 2026, we try to preserve year if needed, 
                    # but simple split is a best effort.
                    d_clean = d_clean.split("-")[-1].strip()
                
                parsed_date = dateparser.parse(d_clean, settings={'STRICT_PARSING': False})
                if parsed_date:
                    parsed_date = parsed_date.replace(tzinfo=None)
                    if parsed_date < now:
                        expired = True

            if expired:
                print(f"🗑️ Hackathon expiré supprimé : '{hack['title']}' (Deadline: {deadline_str})")
                db.delete_hackathon(hack["id"])
                continue

            embed = build_embed(hack)
            try:
                msg = await channel.send(embed=embed)
                await msg.add_reaction("👍")
                await msg.add_reaction("❌")
                db.update_message_id(hack["id"], str(msg.id))
                total_posted += 1
                await asyncio.sleep(2)
            except Exception as e:
                print(f"  Erreur envoi Discord : {e}")
                
            if total_posted >= limit:
                break
                
    print(f"{total_posted} nouveaux hackathons postés sur Discord ce tour-ci !")
    return total_posted


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


async def archive_expired_hackathons(bot: discord.Client, guild: discord.Guild = None):
    """Vérifie les hackathons publiés. Si la deadline est passée, les déplace dans l'archive."""
    
    # Nettoyage des IDs (gestion des espaces invisibles dans le .env)
    h_str = str(os.getenv("HACKATHON_CHANNEL_ID", "0")).strip()
    a_str = str(os.getenv("ARCHIVES_CHANNEL_ID", "0")).strip()
    
    h_id = int(h_str) if h_str.isdigit() else 0
    a_id = int(a_str) if a_str.isdigit() else 0

    hack_channel = None
    arch_channel = None

    if h_id != 0:
        hack_channel = bot.get_channel(h_id)
        if not hack_channel:
            try:
                hack_channel = await bot.fetch_channel(h_id)
            except:
                print(f"⚠️ [Archive] Impossible de fetch HACKATHON_CHANNEL_ID: {h_id}")
    
    if a_id != 0:
        arch_channel = bot.get_channel(a_id)
        if not arch_channel:
            try:
                arch_channel = await bot.fetch_channel(a_id)
                print(f"  [Archive] Canal Archives trouvé par fetch (ID: {a_id})")
            except Exception as e:
                print(f"  [Archive] Erreur fetch arch_channel (ID {a_id}) : {e}")
    else:
        print("  [Archive] ARCHIVES_CHANNEL_ID est à 0 dans le .env !")
    
    if not hack_channel or not arch_channel:
        print(f"❌ [Archive] Canal manquant. Hack: {hack_channel}, Arch: {arch_channel}")
        return None
        
    posted_hacks = db.get_posted_hackathons()
    if not posted_hacks:
        print("Aucun hackathon publié en base de données.")
        return 0
        
    import dateparser
    from datetime import datetime
    now = datetime.now()
    archived_count = 0
    
    for hack in posted_hacks:
        deadline_str = hack.get("deadline")
        expired = False
        
        if deadline_str:
            d_clean = deadline_str.replace("byOFA", "").lower().replace("ended", "").strip()
            if " - " in d_clean:
                d_clean = d_clean.split(" - ")[-1].strip()
            elif "-" in d_clean and not deadline_str.startswith("202"):
                d_clean = d_clean.split("-")[-1].strip()
            
            parsed_date = dateparser.parse(d_clean, settings={'STRICT_PARSING': False})
            if parsed_date:
                parsed_date = parsed_date.replace(tzinfo=None)
                if parsed_date < now:
                    expired = True

        if expired:
            print(f"📦 Archivage de : {hack['title']}")
            try:
                # 1. Tenter de supprimer l'ancien message
                msg_id_str = hack.get("discord_message_id", "").strip()
                if msg_id_str and msg_id_str.isdigit():
                    try:
                        old_msg = await hack_channel.fetch_message(int(msg_id_str))
                        await old_msg.delete()
                    except discord.NotFound:
                        pass # Le message était peut-être déjà supprimé
                    except Exception as msg_ex:
                        print(f"Impossible de supprimer le vieux message: {msg_ex}")
                        pass
                        
                # 2. Poster dans les archives
                embed = build_embed(hack)
                embed.color = discord.Color.dark_grey() # Griser l'archive
                embed.set_footer(text=f"Score: {hack.get('score', 0)}/10 · Hackathon Terminé / Archivé")
                
                await arch_channel.send(content="**[ARCHIVE]**", embed=embed)
                
                # 3. Mettre à jour en BDD
                db.archive_hackathon(hack["id"])
                archived_count += 1
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Erreur lors de l'archivage de {hack['title']} : {e}")

    if archived_count > 0:
        print(f"✅ {archived_count} hackathons ont été archivés.")
    else:
        print("Aucun hackathon n'avait expiré.")
    
    return archived_count

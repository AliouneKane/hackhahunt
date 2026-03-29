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


async def _find_channel(bot, channel_id: int, guild=None):
    """Trouve un canal Discord par ID. Priorise le guild s'il est fourni."""
    if channel_id == 0:
        print(f"  [_find_channel] ID = 0, ignoré.")
        return None

    # 1. Si on a un guild, chercher directement dedans
    if guild:
        ch = guild.get_channel(channel_id)
        if ch:
            return ch
        # Forcer un fetch des canaux du guild (contourne le cache)
        try:
            channels = await guild.fetch_channels()
            for c in channels:
                if c.id == channel_id:
                    return c
        except Exception as e:
            print(f"  [_find_channel] guild.fetch_channels() échoué : {e}")

    # 2. Cache global du bot
    ch = bot.get_channel(channel_id)
    if ch:
        return ch

    # 3. Fetch direct par API Discord
    try:
        return await bot.fetch_channel(channel_id)
    except Exception as e:
        print(f"  [_find_channel] bot.fetch_channel({channel_id}) échoué : {e}")

    # 4. Dernier recours : parcourir tous les guilds connus
    for g in bot.guilds:
        if guild and g.id == guild.id:
            continue  # déjà testé
        ch = g.get_channel(channel_id)
        if ch:
            return ch

    print(f"  [_find_channel] Aucune stratégie n'a trouvé le canal {channel_id}")
    return None


async def _get_channel_titles(channel, limit: int = 200) -> set:
    """Récupère les titres des embeds déjà postés dans un canal."""
    titles = set()
    try:
        async for msg in channel.history(limit=limit):
            for embed in msg.embeds:
                if embed.title:
                    # Le titre dans build_embed est "Titre — Source", on prend la partie avant " — "
                    clean = embed.title.split(" — ")[0].strip().lower()
                    titles.add(clean)
    except Exception as e:
        print(f"⚠️ Impossible de lire l'historique du canal : {e}")
    return titles

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
    from dotenv import load_dotenv
    load_dotenv(override=True)
    global HACKATHON_CHANNEL_ID, ARCHIVES_CHANNEL_ID
    HACKATHON_CHANNEL_ID = int(os.getenv("HACKATHON_CHANNEL_ID", "0"))
    ARCHIVES_CHANNEL_ID = int(os.getenv("ARCHIVES_CHANNEL_ID", "0"))

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

    new_inserts = 0
    for hack in filtered:
        # Seuls les hacks n'existant pas encore seront ajoutés (id is not None)
        hack_id = db.insert_hackathon(hack)
        if hack_id is not None:
            new_inserts += 1

    print(f"Scraping fini : {new_inserts} nouveaux hackathons insérés en base (en attente de post).")
    return new_inserts


async def post_pending_hackathons(bot: discord.Client, limit: int = 10, guild=None):
    """Poste une poignée de hackathons encore non publiés pour éviter de spammer."""
    from dotenv import load_dotenv
    load_dotenv(override=True)
    global HACKATHON_CHANNEL_ID
    HACKATHON_CHANNEL_ID = int(os.getenv("HACKATHON_CHANNEL_ID", "0"))

    if not guild and bot.guilds:
        g_id = int(str(os.getenv("GUILD_ID", "0")).strip() or "0")
        guild = discord.utils.get(bot.guilds, id=g_id) or (bot.guilds[0] if bot.guilds else None)

    channel = await _find_channel(bot, HACKATHON_CHANNEL_ID, guild=guild)
    if not channel:
        print(f"Canal introuvable (ID: {HACKATHON_CHANNEL_ID})")
        return 0

    import dateparser
    from datetime import datetime

    now = datetime.now()
    total_posted = 0

    # Scanner les titres déjà présents dans le canal pour éviter les doublons
    existing_titles = await _get_channel_titles(channel)
    print(f"🔍 {len(existing_titles)} titres déjà présents dans le canal.")
    print(f"🚀 Publication de hackathons (Objectif: {limit})...")

    while total_posted < limit:
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

            # Anti-doublon : vérifier si ce titre est déjà dans le canal
            title_clean = hack.get("title", "").strip().lower()
            if title_clean in existing_titles:
                print(f"⏭️ Doublon ignoré (déjà dans le canal) : '{hack['title']}'")
                db.update_message_id(hack["id"], "duplicate_skipped")
                continue

            embed = build_embed(hack)
            try:
                msg = await channel.send(embed=embed)
                db.update_message_id(hack["id"], str(msg.id))
                existing_titles.add(title_clean)  # Ajouter au set pour ce cycle
                total_posted += 1
                try:
                    await msg.add_reaction("👍")
                    await msg.add_reaction("❌")
                except Exception:
                    pass
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
    from dotenv import load_dotenv
    load_dotenv(override=True)

    h_id = int(str(os.getenv("HACKATHON_CHANNEL_ID", "0")).strip() or "0")
    a_id = int(str(os.getenv("ARCHIVES_CHANNEL_ID", "0")).strip() or "0")

    # Récupérer le guild si non fourni
    if not guild and bot.guilds:
        g_id = int(str(os.getenv("GUILD_ID", "0")).strip() or "0")
        guild = discord.utils.get(bot.guilds, id=g_id) or (bot.guilds[0] if bot.guilds else None)

    print(f"[Archive] Recherche canaux — Guild: {guild} | Hack ID: {h_id} | Arch ID: {a_id}")
    hack_channel = await _find_channel(bot, h_id, guild=guild)
    arch_channel = await _find_channel(bot, a_id, guild=guild)

    errors = []
    if not hack_channel:
        errors.append(f"HACKATHON_CHANNEL_ID={h_id} introuvable")
    if not arch_channel:
        errors.append(f"ARCHIVES_CHANNEL_ID={a_id} introuvable")

    if errors:
        print(f"❌ [Archive] {' | '.join(errors)}")
        return {"error": " ; ".join(errors)}
        
    import dateparser
    from datetime import datetime
    now = datetime.now()
    archived_count = 0

    def _is_expired(deadline_str):
        if not deadline_str:
            return False
        d = deadline_str.replace("byOFA", "").lower().replace("ended", "").strip()
        if " - " in d:
            d = d.split(" - ")[-1].strip()
        elif "-" in d and not deadline_str.startswith("202"):
            d = d.split("-")[-1].strip()
        parsed = dateparser.parse(d, settings={'STRICT_PARSING': False, 'PREFER_DAY_OF_MONTH': 'last'})
        if parsed:
            return parsed.replace(tzinfo=None) < now
        return False

    # ── Méthode 1 : via la base de données (hackathons avec discord_message_id) ──
    posted_hacks = db.get_posted_hackathons()
    print(f"[Archive] {len(posted_hacks)} hackathon(s) trouvés en base avec message_id.")

    for hack in posted_hacks:
        if not _is_expired(hack.get("deadline")):
            continue
        print(f"📦 [DB] Archivage de : {hack['title']}")
        try:
            msg_id_str = hack.get("discord_message_id", "").strip()
            if msg_id_str and msg_id_str.isdigit():
                try:
                    old_msg = await hack_channel.fetch_message(int(msg_id_str))
                    await old_msg.delete()
                except discord.NotFound:
                    pass
                except Exception as e:
                    print(f"  Impossible de supprimer le message: {e}")

            archive_embed = build_embed(hack)
            archive_embed.color = discord.Color.dark_grey()
            archive_embed.set_footer(text=f"Score: {hack.get('score', 0)}/10 · Hackathon Terminé / Archivé")
            await arch_channel.send(content="**[ARCHIVE]**", embed=archive_embed)
            db.archive_hackathon(hack["id"])
            archived_count += 1
            await asyncio.sleep(1)
        except Exception as e:
            print(f"  Erreur archivage DB {hack['title']} : {e}")

    # ── Méthode 2 : scan direct du canal (rattrape les messages non trackés en base) ──
    print(f"[Archive] Scan de l'historique du canal #{hack_channel.name}...")
    already_archived_msg_ids = set()

    try:
        async for msg in hack_channel.history(limit=500):
            if msg.author.id != bot.user.id:
                continue
            if not msg.embeds:
                continue

            embed = msg.embeds[0]

            # Extraire la deadline depuis les fields de l'embed
            deadline_str = None
            for field in embed.fields:
                if field.name and "deadline" in field.name.lower():
                    deadline_str = field.value
                    break

            if not _is_expired(deadline_str):
                continue

            title = embed.title or "Inconnu"
            print(f"📦 [SCAN] Archivage de : {title} (msg {msg.id})")

            try:
                # Construire un embed archive depuis l'embed existant
                archive_embed = discord.Embed(
                    title=embed.title,
                    url=embed.url,
                    color=discord.Color.dark_grey(),
                    description=embed.description
                )
                for field in embed.fields:
                    archive_embed.add_field(name=field.name, value=field.value, inline=field.inline)
                archive_embed.set_footer(text="Hackathon Terminé / Archivé")

                await arch_channel.send(content="**[ARCHIVE]**", embed=archive_embed)
                await msg.delete()

                # Mettre à jour la base si on trouve le hackathon par titre
                title_clean = title.split(" — ")[0].strip()
                conn = __import__('sqlite3').connect(db.DB_PATH)
                row = conn.execute(
                    "SELECT id FROM hackathons WHERE LOWER(TRIM(title)) = LOWER(?) AND status = 'active'",
                    (title_clean,)
                ).fetchone()
                if row:
                    db.archive_hackathon(row[0])
                conn.close()

                archived_count += 1
                await asyncio.sleep(1)
            except Exception as e:
                print(f"  Erreur archivage SCAN {title} : {e}")

    except Exception as e:
        print(f"[Archive] Erreur lors du scan du canal : {e}")

    print(f"✅ {archived_count} hackathon(s) archivé(s) au total.")
    return archived_count

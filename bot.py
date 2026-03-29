import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import asyncio
import database as db

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
intents.members = True
intents.reactions = True
intents.presences = True

bot = commands.Bot(command_prefix="/", intents=intents)

# ── Chargement des cogs ──────────────────────────────────────────────────────
async def load_cogs():
    await bot.load_extension("cogs.matchmaking")
    await bot.load_extension("cogs.teams")
    print("✅ Cogs chargés")

# ── Événements ───────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"🤖 {bot.user} est en ligne !")
    print(f"📡 Connecté au serveur : {GUILD_ID}")
    try:
        synced = await bot.tree.sync()
        print(f"⚡ {len(synced)} commandes slash synchronisées")
    except Exception as e:
        print(f"❌ Erreur sync commandes : {e}")
    db.init_db()
    scraping_task.start()
    post_pending_task.start()
    archive_expired_task.start()

@tasks.loop(hours=6)
async def scraping_task():
    """Scraping automatique toutes les 6h"""
    from scraper.runner import run_all_scrapers
    await run_all_scrapers(bot)

@tasks.loop(hours=1)
async def post_pending_task():
    """Poste 10 hackathons par heure pour éviter le spam."""
    from scraper.runner import post_pending_hackathons
    await post_pending_hackathons(bot, limit=10)

@tasks.loop(hours=12)
async def archive_expired_task():
    """Archive les hackathons expirés une fois par jour."""
    from scraper.runner import archive_expired_hackathons
    await archive_expired_hackathons(bot)

@scraping_task.before_loop
@post_pending_task.before_loop
@archive_expired_task.before_loop
async def before_tasks():
    await bot.wait_until_ready()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"❌ Erreur commande : {error}")

# ── Commandes slash de base ──────────────────────────────────────────────────
@bot.tree.command(name="ping", description="Vérifie que le bot est en ligne")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(
        f"🏓 Pong ! Latence : **{latency}ms**", ephemeral=True
    )

@bot.tree.command(name="aide", description="Liste des commandes disponibles")
async def aide(interaction: discord.Interaction):
    embed = discord.Embed(
        title="HackahuntBot — Commandes",
        color=0x534AB7
    )
    embed.add_field(
        name="Hackathons",
        value="`/scrape` — Lance un scraping manuel\n`/hackathons` — Liste les hackathons actifs",
        inline=False
    )
    embed.add_field(
        name="Équipes",
        value="`/team @pseudo` — Propose une équipe à quelqu'un\n`/monequipe` — Voir ton équipe actuelle",
        inline=False
    )
    embed.add_field(
        name="Général",
        value="`/ping` — Vérifie la latence\n`/aide` — Cette aide",
        inline=False
    )
    embed.set_footer(text="HackahuntBot • ENSAE")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="scrape", description="Lance un scraping manuel des hackathons (admin uniquement)")
@discord.app_commands.default_permissions(administrator=True)
async def scrape(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    from scraper.runner import run_all_scrapers, post_pending_hackathons
    
    saved = await run_all_scrapers(bot)
    
    # On force la publication de la 1ère dizaine immédiatement en manuel
    posted = await post_pending_hackathons(bot, limit=10)
    
    await interaction.followup.send(
        f"✅ Scraping terminé ! **{saved}** nouveau(x) hackathon(s) trouvés en base.\n"
        f"**{posted}** annoncés immédiatement. Le reste sera diffusé à raison de 10 toutes les heures.",
        ephemeral=True
    )

@bot.tree.command(name="archive_now", description="Force manuellement la vérification et l'archivage des hackathons expirés (admin)")
@discord.app_commands.default_permissions(administrator=True)
async def archive_now(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    from scraper.runner import archive_expired_hackathons
    count = await archive_expired_hackathons(bot, guild=interaction.guild)
    
    if count is None:
        await interaction.followup.send("❌ Erreur : Impossible de trouver les canaux (Assurez-vous que les IDs `HACKATHON_CHANNEL_ID` et `ARCHIVES_CHANNEL_ID` sont valides).", ephemeral=True)
    elif count == 0:
        await interaction.followup.send("✅ Vérification terminée. **0** hackathon n'a eu besoin d'être archivé (tous sont encore encore valides ou la base est vide).", ephemeral=True)
    else:
        await interaction.followup.send(f"✅ Action terminée ! **{count}** hackathon(s) expiré(s) ont été déplacés dans les archives.", ephemeral=True)

@bot.tree.command(name="stats", description="Affiche le nombre de hackathons en attente, postés et archivés")
async def stats(interaction: discord.Interaction):
    s = db.get_stats()
    embed = discord.Embed(title="Statistiques — Base de données", color=0x534AB7)
    embed.add_field(
        name="État actuel",
        value=(
            f"En attente de post : **{s['total_pending']}**\n"
            f"Postés (actifs)    : **{s['total_posted']}**\n"
            f"Archivés (total)   : **{s['total_archived']}**"
        ),
        inline=False
    )
    from datetime import datetime
    embed.set_footer(text=f"Total actifs en base : {s['total_active']} · {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="post_now", description="Pousse des hackathons non postés vers le canal immédiatement (admin)")
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(limite="Nombre de hackathons à poster (défaut: 10)")
async def post_now(interaction: discord.Interaction, limite: int = 10):
    await interaction.response.defer(ephemeral=True)
    from scraper.runner import post_pending_hackathons
    posted = await post_pending_hackathons(bot, limit=limite)
    if posted == 0:
        pending = db.get_stats()["total_pending"]
        if pending == 0:
            await interaction.followup.send("✅ Aucun hackathon en attente dans la base.", ephemeral=True)
        else:
            await interaction.followup.send(f"⚠️ {pending} hackathon(s) en base mais aucun posté (canal introuvable ou tous expirés).", ephemeral=True)
    else:
        await interaction.followup.send(f"✅ **{posted}** hackathon(s) postés dans le canal.", ephemeral=True)


@bot.tree.command(name="bilan", description="Résumé des actions du bot depuis le début de la journée")
async def bilan(interaction: discord.Interaction):
    from datetime import datetime
    s = db.get_stats()
    embed = discord.Embed(
        title=f"Bilan du jour — {datetime.now().strftime('%d/%m/%Y')}",
        color=0x1D9E75
    )
    embed.add_field(
        name="Aujourd'hui",
        value=(
            f"Hackathons scrapés  : **{s['scraped_today']}**\n"
            f"Hackathons postés   : **{s['posted_today']}**\n"
            f"Hackathons archivés : **{s['archived_today']}**"
        ),
        inline=False
    )
    embed.add_field(
        name="Totaux en base",
        value=(
            f"En attente de post : **{s['total_pending']}**\n"
            f"Postés et actifs   : **{s['total_posted']}**\n"
            f"Archivés           : **{s['total_archived']}**"
        ),
        inline=False
    )
    embed.set_footer(text=f"Généré à {datetime.now().strftime('%H:%M:%S')}")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="test_archive", description="Crée un hackathon de test et l'archive automatiquement après N minutes (admin)")
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(minutes="Délai avant archivage (défaut: 2 minutes)")
async def test_archive(interaction: discord.Interaction, minutes: int = 5):
    """Insère un hackathon fictif, le poste, puis l'archive quand la deadline arrive."""
    await interaction.response.defer(ephemeral=True)

    import os
    from datetime import datetime, timedelta
    from scraper.runner import build_embed

    h_id_str = str(os.getenv("HACKATHON_CHANNEL_ID", "0")).strip()
    if not h_id_str.isdigit() or int(h_id_str) == 0:
        await interaction.followup.send("❌ `HACKATHON_CHANNEL_ID` invalide dans le .env.", ephemeral=True)
        return

    hack_channel = bot.get_channel(int(h_id_str)) or await bot.fetch_channel(int(h_id_str))
    if not hack_channel:
        await interaction.followup.send("❌ Impossible d'accéder au canal hackathons.", ephemeral=True)
        return

    # Deadline = maintenant + N minutes (format ISO lisible par dateparser)
    deadline_dt = datetime.now() + timedelta(minutes=minutes)
    deadline_str = deadline_dt.strftime("%Y-%m-%d %H:%M:%S")

    test_hack = {
        "title": f"[TEST] Hackathon Fictif",
        "url": f"https://example.com/test-hackathon-{int(datetime.now().timestamp())}",
        "source": "test",
        "theme": "Intelligence Artificielle, Data Science",
        "format": "online",
        "location": "",
        "prize_1st": "500 000 FCFA",
        "prize_2nd": "200 000 FCFA",
        "prize_3rd": None,
        "prize_min_fcfa": 500000,
        "language": "fr",
        "deadline": deadline_str,
        "duration": None,
        "level": "Intermédiaire",
        "score": 7,
    }

    hack_id = db.insert_hackathon(test_hack)
    if not hack_id:
        await interaction.followup.send("❌ Impossible d'insérer le hackathon test (URL déjà existante ?).", ephemeral=True)
        return

    # Poster l'embed dans le canal hackathons
    test_hack["id"] = hack_id
    embed = build_embed(test_hack)
    embed.description = f"⚠️ **Hackathon de test** — sera archivé dans **{minutes} minute(s)**."
    msg = await hack_channel.send(embed=embed)
    await msg.add_reaction("👍")

    # Sauvegarder le message ID en base
    db.update_message_id(hack_id, str(msg.id))

    await interaction.followup.send(
        f"✅ Hackathon de test créé (ID `{hack_id}`) et posté dans <#{h_id_str}>.\n"
        f"⏳ Archivage automatique dans **{minutes} minute(s)** (`{deadline_str}`).",
        ephemeral=True
    )

    # Tâche asynchrone : attendre la deadline puis archiver
    async def _auto_archive():
        from scraper.runner import archive_expired_hackathons
        wait_seconds = (deadline_dt - datetime.now()).total_seconds()
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds + 2)  # +2s de marge
        count = await archive_expired_hackathons(bot)
        print(f"[test_archive] Archivage automatique déclenché → {count} hackathon(s) archivé(s).")

    asyncio.create_task(_auto_archive())


@bot.tree.command(name="diagnose", description="Diagnostique la configuration du bot et des canaux")
async def diagnose(interaction: discord.Interaction):
    """Vérifie la config et les accès aux salons."""
    import os
    await interaction.response.defer(ephemeral=True)
    
    h_id_str = os.getenv("HACKATHON_CHANNEL_ID")
    a_id_str = os.getenv("ARCHIVES_CHANNEL_ID")
    
    h_channel = bot.get_channel(int(h_id_str.strip())) if h_id_str and h_id_str.strip().isdigit() else None
    a_channel = bot.get_channel(int(a_id_str.strip())) if a_id_str and a_id_str.strip().isdigit() else None
    
    report = f"🔍 **Diagnostic du Bot** :\n"
    report += f"- `HACKATHON_CHANNEL_ID`: `{h_id_str}` (Trouvé: {'✅' if h_channel else '❌'})\n"
    report += f"- `ARCHIVES_CHANNEL_ID`: `{a_id_str}` (Trouvé: {'✅' if a_channel else '❌'})\n"
    
    if h_channel:
        report += f"- Salon Hack: `#{h_channel.name}`\n"
    if a_channel:
        report += f"- Salon Arch: `#{a_channel.name}`\n"
        
    if not h_channel or not a_channel:
        report += "\n⚠️ **Conseil** : Si un salon est marqué ❌, vérifie l'ID et assure-toi que le bot a la permission 'Voir le salon' dessus."
        
    await interaction.followup.send(report)

# ── Lancement ────────────────────────────────────────────────────────────────
async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
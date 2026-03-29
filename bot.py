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
async def _send_welcome(user) -> bool:
    """Envoie les messages de bienvenue en MP. Retourne True si envoyé avec succès."""

    # ── Message 1 : Bienvenue + Règles ──
    m1 = discord.Embed(
        title="",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "# 👋 Bienvenue sur HackaHunt !\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Salut **{user.display_name}** !\n\n"
            "HackaHunt est une communauté où l'on découvre "
            "ensemble des **hackathons** et où l'on forme des "
            "**équipes** pour participer et gagner."
        ),
        color=0x534AB7,
    )
    m1.add_field(
        name="📜 Règles du serveur",
        value=(
            "```\n"
            "1. Respecte les autres membres\n"
            "   Zéro tolérance pour le harcèlement,\n"
            "   les insultes ou la discrimination.\n\n"
            "2. Reste dans le bon salon\n"
            "   #entraide → questions techniques\n"
            "   #général  → discussions libres\n"
            "   #hackathons → annonces du bot uniquement\n\n"
            "3. Pas de spam\n"
            "   Pas de liens non sollicités ni de pub.\n\n"
            "4. Active tes MP\n"
            "   Indispensable pour recevoir les matchs\n"
            "   et les rappels de deadline.\n\n"
            "5. Besoin d'aide ?\n"
            "   Contacte un @Admin ou @Modérateur.\n"
            "```"
        ),
        inline=False,
    )
    m1.set_footer(text="Merci de lire ces règles avant de participer !")

    # ── Message 2 : Les salons ──
    m2 = discord.Embed(
        title="🗂️ Les salons du serveur",
        description="Voici où aller et quoi faire dans chaque salon.",
        color=0x1D9E75,
    )
    m2.add_field(
        name="📣 #hackathons",
        value=(
            "Le bot y poste des hackathons **toutes les heures**.\n"
            "Thème, prix, deadline, score de qualité /10.\n"
            "→ Clique **👍** pour montrer ton intérêt."
        ),
        inline=False,
    )
    m2.add_field(
        name="💬 #général",
        value="Discussion libre. Présente-toi, papote, partage.",
        inline=False,
    )
    m2.add_field(
        name="🛠️ #entraide",
        value="Questions techniques, bugs, projets — les membres s'entraident ici.",
        inline=False,
    )
    m2.add_field(
        name="📁 #archives",
        value="Les hackathons expirés y sont déplacés automatiquement.",
        inline=False,
    )
    m2.add_field(
        name="🔒 Salons d'équipe (privés)",
        value="Créés automatiquement quand tu formes une équipe. Retrouve-les avec `/monequipe`.",
        inline=False,
    )

    # ── Message 3 : Comment ça marche ──
    m3 = discord.Embed(
        title="🚀 Comment ça marche",
        description="Le parcours en 3 étapes pour participer à un hackathon.",
        color=0xBA7517,
    )
    m3.add_field(
        name="① Explore",
        value="Va dans **#hackathons** et repère ceux qui te plaisent.",
        inline=False,
    )
    m3.add_field(
        name="② Clique 👍",
        value="Le bot te contacte en MP avec la liste des membres intéressés.",
        inline=False,
    )
    m3.add_field(
        name="③ Forme ton équipe",
        value=(
            "Choisis un coéquipier → **match mutuel** → "
            "le bot crée un **salon privé** pour vous.\n\n"
            "Rappels automatiques : **J-7, J-3, J-1** avant la deadline."
        ),
        inline=False,
    )
    m3.add_field(
        name="⚡ Commandes utiles",
        value=(
            "`/aide` — Liste des commandes\n"
            "`/monequipe` — Ton équipe en cours\n"
            "`/team @pseudo` — Proposer une équipe\n"
            "`/stats` — Hackathons en base\n"
            "`/ping` — Le bot est en ligne ?"
        ),
        inline=False,
    )
    m3.set_footer(
        text="HackaHunt surveille 12 plateformes en permanence. Bonne chance !"
    )

    try:
        await user.send(embed=m1)
        await asyncio.sleep(1)
        await user.send(embed=m2)
        await asyncio.sleep(1)
        await user.send(embed=m3)
        return True
    except discord.Forbidden:
        return False


@bot.event
async def on_member_join(member: discord.Member):
    """Envoie le message de bienvenue quand un nouveau membre rejoint le serveur"""
    if db.is_welcomed(str(member.id)):
        return
    sent = await _send_welcome(member)
    if sent:
        db.mark_welcomed(str(member.id))


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

    # Lancer les tâches planifiées (seulement si pas déjà en cours — on_ready peut se déclencher plusieurs fois)
    if not scraping_task.is_running():
        scraping_task.start()
    if not post_pending_task.is_running():
        post_pending_task.start()
    if not archive_expired_task.is_running():
        archive_expired_task.start()

    # Exécution immédiate au démarrage (utile sur Railway où la DB est souvent vide)
    print("🚀 Exécution initiale des tâches au démarrage...")
    asyncio.create_task(_initial_run())


async def _initial_run():
    """Scrape et poste immédiatement au démarrage du bot."""
    try:
        await bot.wait_until_ready()
        from scraper.runner import run_all_scrapers, post_pending_hackathons

        stats = db.get_stats()
        print(
            f"📊 État initial DB : {stats['total_pending']} en attente, {stats['total_posted']} postés, {stats['total_archived']} archivés"
        )

        # Si la DB est vide (cas Railway après redéploiement), lancer un scraping d'abord
        if stats["total_pending"] == 0 and stats["total_posted"] == 0:
            print("🔄 Base vide — lancement d'un scraping initial...")
            saved = await run_all_scrapers(bot)
            print(f"📥 Scraping initial terminé : {saved} nouveaux hackathons")

        # Poster les hackathons en attente immédiatement
        guild = discord.utils.get(bot.guilds, id=GUILD_ID)
        if guild:
            posted = await post_pending_hackathons(bot, limit=10, guild=guild)
            print(f"✅ Initial run terminé : {posted} hackathon(s) posté(s)")
        else:
            print(
                f"❌ Guild {GUILD_ID} introuvable au démarrage. Guilds disponibles : {[g.id for g in bot.guilds]}"
            )
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution initiale : {e}")
        import traceback

        traceback.print_exc()


@tasks.loop(hours=6)
async def scraping_task():
    """Scraping automatique toutes les 6h"""
    try:
        from scraper.runner import run_all_scrapers

        print("⏰ [scraping_task] Début du scraping automatique...")
        saved = await run_all_scrapers(bot)
        print(f"⏰ [scraping_task] Terminé : {saved} nouveaux hackathons")
    except Exception as e:
        print(f"❌ [scraping_task] Erreur : {e}")
        import traceback

        traceback.print_exc()


@tasks.loop(hours=1)
async def post_pending_task():
    """Poste 10 hackathons par heure pour éviter le spam."""
    try:
        from scraper.runner import post_pending_hackathons

        print("⏰ [post_pending_task] Vérification des hackathons en attente...")
        guild = discord.utils.get(bot.guilds, id=GUILD_ID)
        if not guild:
            print(f"❌ [post_pending_task] Guild {GUILD_ID} introuvable")
            return
        posted = await post_pending_hackathons(bot, limit=10, guild=guild)
        print(f"⏰ [post_pending_task] Terminé : {posted} hackathon(s) posté(s)")
    except Exception as e:
        print(f"❌ [post_pending_task] Erreur : {e}")
        import traceback

        traceback.print_exc()


@tasks.loop(hours=12)
async def archive_expired_task():
    """Archive les hackathons expirés toutes les 12h."""
    try:
        from scraper.runner import archive_expired_hackathons

        print("⏰ [archive_expired_task] Vérification des hackathons expirés...")
        guild = discord.utils.get(bot.guilds, id=GUILD_ID)
        if not guild:
            print(f"❌ [archive_expired_task] Guild {GUILD_ID} introuvable")
            return
        count = await archive_expired_hackathons(bot, guild=guild)
        print(f"⏰ [archive_expired_task] Terminé : {count} hackathon(s) archivé(s)")
    except Exception as e:
        print(f"❌ [archive_expired_task] Erreur : {e}")
        import traceback

        traceback.print_exc()


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
    embed = discord.Embed(title="HackahuntBot — Commandes", color=0x534AB7)
    embed.add_field(
        name="Hackathons",
        value="`/scrape` — Lance un scraping manuel\n`/hackathons` — Liste les hackathons actifs",
        inline=False,
    )
    embed.add_field(
        name="Équipes",
        value="`/team @pseudo` — Propose une équipe à quelqu'un\n`/monequipe` — Voir ton équipe actuelle",
        inline=False,
    )
    embed.add_field(
        name="Général",
        value="`/ping` — Vérifie la latence\n`/aide` — Cette aide",
        inline=False,
    )
    embed.set_footer(text="HackahuntBot • ENSAE")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(
    name="scrape",
    description="Lance un scraping manuel des hackathons (admin uniquement)",
)
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
        ephemeral=True,
    )


@bot.tree.command(
    name="archive_now",
    description="Force manuellement la vérification et l'archivage des hackathons expirés (admin)",
)
@discord.app_commands.default_permissions(administrator=True)
async def archive_now(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    from scraper.runner import archive_expired_hackathons

    result = await archive_expired_hackathons(bot, guild=interaction.guild)

    if isinstance(result, dict) and "error" in result:
        await interaction.followup.send(
            f"❌ Erreur canal : {result['error']}\n\n"
            f"**Debug** : Guild = `{interaction.guild.name}` (`{interaction.guild.id}`)\n"
            f"Canaux visibles par le bot : {len(interaction.guild.channels)}",
            ephemeral=True,
        )
    elif result == 0:
        await interaction.followup.send(
            "✅ Vérification terminée. **0** hackathon n'a eu besoin d'être archivé.",
            ephemeral=True,
        )
    else:
        await interaction.followup.send(
            f"✅ Action terminée ! **{result}** hackathon(s) expiré(s) ont été déplacés dans les archives.",
            ephemeral=True,
        )


@bot.tree.command(
    name="stats",
    description="Affiche le nombre de hackathons en attente, postés et archivés",
)
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
        inline=False,
    )
    from datetime import datetime

    embed.set_footer(
        text=f"Total actifs en base : {s['total_active']} · {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(
    name="post_now",
    description="Pousse des hackathons non postés vers le canal immédiatement (admin)",
)
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(limite="Nombre de hackathons à poster (défaut: 10)")
async def post_now(interaction: discord.Interaction, limite: int = 10):
    await interaction.response.defer(ephemeral=True)
    from scraper.runner import post_pending_hackathons

    posted = await post_pending_hackathons(bot, limit=limite, guild=interaction.guild)
    if posted == 0:
        pending = db.get_stats()["total_pending"]
        if pending == 0:
            await interaction.followup.send(
                "✅ Aucun hackathon en attente dans la base.", ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"⚠️ {pending} hackathon(s) en base mais aucun posté (canal introuvable ou tous expirés).",
                ephemeral=True,
            )
    else:
        await interaction.followup.send(
            f"✅ **{posted}** hackathon(s) postés dans le canal.", ephemeral=True
        )


@bot.tree.command(
    name="bilan", description="Résumé des actions du bot depuis le début de la journée"
)
async def bilan(interaction: discord.Interaction):
    from datetime import datetime

    s = db.get_stats()
    embed = discord.Embed(
        title=f"Bilan du jour — {datetime.now().strftime('%d/%m/%Y')}", color=0x1D9E75
    )
    embed.add_field(
        name="Aujourd'hui",
        value=(
            f"Hackathons scrapés  : **{s['scraped_today']}**\n"
            f"Hackathons postés   : **{s['posted_today']}**\n"
            f"Hackathons archivés : **{s['archived_today']}**"
        ),
        inline=False,
    )
    embed.add_field(
        name="Totaux en base",
        value=(
            f"En attente de post : **{s['total_pending']}**\n"
            f"Postés et actifs   : **{s['total_posted']}**\n"
            f"Archivés           : **{s['total_archived']}**"
        ),
        inline=False,
    )
    embed.set_footer(text=f"Généré à {datetime.now().strftime('%H:%M:%S')}")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="test_archive",
    description="Crée un hackathon de test et l'archive automatiquement après N minutes (admin)",
)
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
        await interaction.followup.send(
            "❌ `HACKATHON_CHANNEL_ID` invalide dans le .env.", ephemeral=True
        )
        return

    hack_channel = bot.get_channel(int(h_id_str)) or await bot.fetch_channel(
        int(h_id_str)
    )
    if not hack_channel:
        await interaction.followup.send(
            "❌ Impossible d'accéder au canal hackathons.", ephemeral=True
        )
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
        await interaction.followup.send(
            "❌ Impossible d'insérer le hackathon test (URL déjà existante ?).",
            ephemeral=True,
        )
        return

    # Poster l'embed dans le canal hackathons
    test_hack["id"] = hack_id
    embed = build_embed(test_hack)
    embed.description = (
        f"⚠️ **Hackathon de test** — sera archivé dans **{minutes} minute(s)**."
    )
    msg = await hack_channel.send(embed=embed)
    await msg.add_reaction("👍")

    # Sauvegarder le message ID en base
    db.update_message_id(hack_id, str(msg.id))

    await interaction.followup.send(
        f"✅ Hackathon de test créé (ID `{hack_id}`) et posté dans <#{h_id_str}>.\n"
        f"⏳ Archivage automatique dans **{minutes} minute(s)** (`{deadline_str}`).",
        ephemeral=True,
    )

    # Tâche asynchrone : attendre la deadline puis archiver
    async def _auto_archive():
        from scraper.runner import archive_expired_hackathons

        wait_seconds = (deadline_dt - datetime.now()).total_seconds()
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds + 2)  # +2s de marge
        count = await archive_expired_hackathons(bot)
        print(
            f"[test_archive] Archivage automatique déclenché → {count} hackathon(s) archivé(s)."
        )

    asyncio.create_task(_auto_archive())


@bot.tree.command(
    name="diagnose", description="Diagnostique la configuration du bot et des canaux"
)
async def diagnose(interaction: discord.Interaction):
    """Vérifie la config et les accès aux salons."""
    import os

    await interaction.response.defer(ephemeral=True)

    h_id_str = os.getenv("HACKATHON_CHANNEL_ID")
    a_id_str = os.getenv("ARCHIVES_CHANNEL_ID")

    h_channel = (
        bot.get_channel(int(h_id_str.strip()))
        if h_id_str and h_id_str.strip().isdigit()
        else None
    )
    a_channel = (
        bot.get_channel(int(a_id_str.strip()))
        if a_id_str and a_id_str.strip().isdigit()
        else None
    )

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


@bot.tree.command(
    name="welcome_all",
    description="Envoie le message de bienvenue à tous les membres qui ne l'ont jamais reçu (admin)",
)
@discord.app_commands.default_permissions(administrator=True)
async def welcome_all(interaction: discord.Interaction):
    """Envoie le welcome en MP à tous les membres existants qui ne l'ont pas encore eu."""
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    if not guild:
        await interaction.followup.send(
            "❌ Impossible de trouver le serveur.", ephemeral=True
        )
        return

    # Récupérer les IDs déjà welcomés
    already_welcomed = set(db.get_not_welcomed_user_ids())

    sent = 0
    skipped = 0
    failed = 0

    for member in guild.members:
        if member.bot:
            continue
        if str(member.id) in already_welcomed:
            skipped += 1
            continue

        ok = await _send_welcome(member)
        if ok:
            db.mark_welcomed(str(member.id))
            sent += 1
        else:
            failed += 1

        await asyncio.sleep(1.5)  # éviter le rate limit Discord

    await interaction.followup.send(
        f"✅ Terminé !\n"
        f"- **{sent}** membre(s) welcomé(s)\n"
        f"- **{skipped}** déjà welcomé(s) (ignoré)\n"
        f"- **{failed}** échec(s) (MP désactivés)",
        ephemeral=True,
    )


# ── Lancement ────────────────────────────────────────────────────────────────
async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import asyncio
import concurrent.futures
from datetime import datetime
import database as db

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix="/", intents=intents)


# ── Chargement des cogs ──────────────────────────────────────────────────────
async def load_cogs():
    await bot.load_extension("cogs.matchmaking")
    await bot.load_extension("cogs.teams")
    print("✅ Cogs chargés")


# ── Bienvenue ─────────────────────────────────────────────────────────────────
async def _send_welcome(user) -> bool:
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
    m2.add_field(name="💬 #général", value="Discussion libre. Présente-toi, papote, partage.", inline=False)
    m2.add_field(name="🛠️ #entraide", value="Questions techniques, bugs, projets — les membres s'entraident ici.", inline=False)
    m2.add_field(name="📁 #archives", value="Les hackathons expirés y sont déplacés automatiquement.", inline=False)

    m3 = discord.Embed(
        title="🚀 Comment ça marche",
        description="Le parcours en 3 étapes pour participer à un hackathon.",
        color=0xBA7517,
    )
    m3.add_field(name="① Explore", value="Va dans **#hackathons** et repère ceux qui te plaisent.", inline=False)
    m3.add_field(name="② Clique 👍", value="Le bot te contacte en MP avec la liste des membres intéressés.", inline=False)
    m3.add_field(
        name="③ Forme ton équipe",
        value=(
            "Choisis un coéquipier → **match mutuel** → "
            "le bot crée un **salon privé** pour vous.\n\n"
            "Rappels automatiques : **J-7, J-3, J-1** avant la deadline."
        ),
        inline=False,
    )
    m3.set_footer(text="HackaHunt surveille 12 plateformes en permanence. Bonne chance !")

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
    if await asyncio.to_thread(db.is_welcomed, str(member.id)):
        return
    sent = await _send_welcome(member)
    if sent:
        await asyncio.to_thread(db.mark_welcomed, str(member.id))


_bot_initialized = False


@bot.event
async def on_ready():
    global _bot_initialized
    print(f"🤖 {bot.user} est en ligne ! (latence: {round(bot.latency*1000)}ms)")
    if _bot_initialized:
        return
    _bot_initialized = True

    try:
        synced = await bot.tree.sync()
        print(f"⚡ {len(synced)} commandes slash synchronisées")
    except Exception as e:
        print(f"❌ Erreur sync commandes : {e}")

    await asyncio.to_thread(db.init_db)
    post_pending_task.start()
    archive_expired_task.start()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"❌ Erreur commande : {error}")


# ── Tâches planifiées ─────────────────────────────────────────────────────────
@tasks.loop(minutes=5)
async def post_pending_task():
    try:
        from scraper.runner import post_pending_hackathons

        print("⏰ [post_pending_task] Vérification des hackathons en attente...")
        guild = discord.utils.get(bot.guilds, id=GUILD_ID)
        if not guild:
            return
        posted = await post_pending_hackathons(bot, limit=1, guild=guild)
        stats = await asyncio.to_thread(db.get_stats)
        print(f"⏰ [post_pending_task] Terminé : {posted} posté(s), {stats['total_pending']} en attente")
    except Exception as e:
        print(f"❌ [post_pending_task] Erreur : {e}")


@tasks.loop(hours=12)
async def archive_expired_task():
    try:
        from scraper.runner import archive_expired_hackathons

        print("⏰ [archive_expired_task] Vérification des hackathons expirés...")
        guild = discord.utils.get(bot.guilds, id=GUILD_ID)
        if not guild:
            return
        count = await archive_expired_hackathons(bot, guild=guild)
        print(f"⏰ [archive_expired_task] Terminé : {count} hackathon(s) archivé(s)")
    except Exception as e:
        print(f"❌ [archive_expired_task] Erreur : {e}")


@post_pending_task.before_loop
async def before_post_pending():
    await bot.wait_until_ready()
    await asyncio.sleep(10)


@archive_expired_task.before_loop
async def before_archive():
    await bot.wait_until_ready()
    await asyncio.sleep(20)


# ── Lancement ─────────────────────────────────────────────────────────────────
async def main():
    loop = asyncio.get_running_loop()
    loop.set_default_executor(
        concurrent.futures.ThreadPoolExecutor(
            max_workers=50, thread_name_prefix="asyncio-default"
        )
    )
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())

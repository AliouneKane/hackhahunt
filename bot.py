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

@tasks.loop(hours=6)
async def scraping_task():
    """Scraping automatique toutes les 6h"""
    from scraper.runner import run_all_scrapers
    await run_all_scrapers(bot)

@scraping_task.before_loop
async def before_scraping():
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
    from scraper.runner import run_all_scrapers
    posted = await run_all_scrapers(bot)
    await interaction.followup.send(
        f"✅ Scraping terminé ! **{posted or 0}** nouveau(x) hackathon(s) posté(s).",
        ephemeral=True
    )

# ── Lancement ────────────────────────────────────────────────────────────────
async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
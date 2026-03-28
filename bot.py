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
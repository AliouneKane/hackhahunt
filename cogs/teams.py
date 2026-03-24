import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import database as db
import os

GUILD_ID = int(os.getenv("GUILD_ID", "0"))
ARCHIVES_CHANNEL_ID = int(os.getenv("ARCHIVES_CHANNEL_ID", "0"))

class Teams(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.check_deadlines.start()

    def cog_unload(self):
        self.check_deadlines.cancel()

    async def create_team_channel(self, guild: discord.Guild, hackathon: dict, member_ids: list):
        """Crée un canal privé pour l'équipe et envoie les modalités"""

        # Trouver ou créer la catégorie "Équipes"
        category = discord.utils.get(guild.categories, name="Équipes")
        if not category:
            category = await guild.create_category("Équipes")

        # Nom du canal : team-{titre-hackathon-court}
        hack_slug = hackathon["title"][:20].lower().replace(" ", "-").replace("_", "-")
        hack_slug = "".join(c for c in hack_slug if c.isalnum() or c == "-")
        channel_name = f"team-{hack_slug}"

        # Permissions : visible uniquement par les membres de l'équipe
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        members = []
        for uid in member_ids:
            member = guild.get_member(uid)
            if member:
                overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                members.append(member)

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Équipe pour {hackathon['title']} | Deadline : {hackathon.get('deadline', 'N/A')}"
        )

        # Enregistrer l'équipe en base
        team_id = db.create_team(
            hackathon["id"],
            [str(uid) for uid in member_ids],
            str(channel.id),
            channel_name
        )

        # Message de bienvenue + modalités
        membres_mention = " ".join([m.mention for m in members])
        embed = discord.Embed(
            title=f"Équipe formée — {hackathon['title']}",
            description=f"Félicitations {membres_mention} ! Vous êtes maintenant une équipe.",
            color=0x534AB7
        )
        embed.add_field(name="Hackathon", value=hackathon["title"], inline=True)
        embed.add_field(name="Niveau", value=hackathon.get("level", "N/A"), inline=True)
        embed.add_field(name="Score Hackahunt", value=f"{hackathon.get('score', '?')}/10", inline=True)

        if hackathon.get("url"):
            embed.add_field(name="Lien d'inscription", value=hackathon["url"], inline=False)
        if hackathon.get("deadline"):
            embed.add_field(name="Deadline inscription", value=hackathon["deadline"], inline=True)
        if hackathon.get("prize_1st"):
            prizes = f"1er : {hackathon['prize_1st']}"
            if hackathon.get("prize_2nd"):
                prizes += f" · 2e : {hackathon['prize_2nd']}"
            if hackathon.get("prize_3rd"):
                prizes += f" · 3e : {hackathon['prize_3rd']}"
            embed.add_field(name="Prix", value=prizes, inline=False)

        embed.set_footer(text="Rappels automatiques J-7, J-3, J-1 avant la deadline • Bon courage !")

        msg = await channel.send(embed=embed)
        await msg.pin()

        # Notifier chaque membre
        for member in members:
            try:
                await member.send(
                    f"Match trouvé ! Votre canal d'équipe est prêt : {channel.mention}\n"
                    f"Hackathon : **{hackathon['title']}**"
                )
            except discord.Forbidden:
                pass

        return channel

    async def create_looking_for_team_channel(self, guild: discord.Guild, hackathon: dict, user: discord.Member):
        """Crée ou utilise un canal #cherche-équipe pour un hackathon"""

        category = discord.utils.get(guild.categories, name="Équipes")
        if not category:
            category = await guild.create_category("Équipes")

        hack_slug = hackathon["title"][:15].lower().replace(" ", "-")
        hack_slug = "".join(c for c in hack_slug if c.isalnum() or c == "-")
        channel_name = f"cherche-equipe-{hack_slug}"

        # Réutiliser le canal s'il existe déjà
        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            await existing.set_permissions(user, read_messages=True, send_messages=True)
            await existing.send(
                f"{user.mention} cherche également une équipe pour **{hackathon['title']}** !"
            )
            return existing

        # Créer le canal visible par tous les membres intéressés
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Cherche équipe pour {hackathon['title']} | Deadline : {hackathon.get('deadline', 'N/A')}"
        )

        embed = discord.Embed(
            title=f"Cherche équipe — {hackathon['title']}",
            description=f"{user.mention} cherche des coéquipiers pour ce hackathon.\n\nSi tu es intéressé(e), rejoins la discussion ici !",
            color=0xBA7517
        )
        if hackathon.get("deadline"):
            embed.add_field(name="Deadline", value=hackathon["deadline"])
        embed.set_footer(text="Canal archivé automatiquement après la deadline d'inscription")
        await channel.send(embed=embed)

        return channel

    @tasks.loop(hours=12)
    async def check_deadlines(self):
        """Vérifie les deadlines et envoie des rappels"""
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        hackathons = db.get_active_hackathons()
        now = datetime.now()

        for hack in hackathons:
            if not hack.get("deadline"):
                continue
            try:
                deadline = datetime.fromisoformat(hack["deadline"])
            except (ValueError, TypeError):
                continue

            delta = deadline - now
            days_left = delta.days

            if days_left < 0:
                # Deadline dépassée → archivage
                await self._archive_hackathon(guild, hack)
            elif days_left in [7, 3, 1]:
                # Rappel avant deadline
                conn = db.get_connection()
                teams = conn.execute(
                    "SELECT * FROM teams WHERE hackathon_id = ? AND status = 'active'",
                    (hack["id"],)
                ).fetchall()
                conn.close()

                for team in teams:
                    channel = guild.get_channel(int(team["channel_id"]))
                    if channel:
                        await channel.send(
                            f"⏰ **Rappel** — Plus que **{days_left} jour(s)** avant la deadline d'inscription pour **{hack['title']}** !\n"
                            f"Lien : {hack.get('url', 'N/A')}"
                        )

    async def _archive_hackathon(self, guild: discord.Guild, hack: dict):
        """Archive un hackathon expiré : poste dans #archives et marque en base."""
        archives_channel = guild.get_channel(ARCHIVES_CHANNEL_ID)
        if not archives_channel:
            print(f"  [Archive] Canal archives introuvable (ID: {ARCHIVES_CHANNEL_ID})")
            return

        embed = discord.Embed(
            title=f"📁 Hackathon archivé — {hack['title']}",
            description=(
                f"La deadline d'inscription pour ce hackathon est **passée**.\n"
                f"Il a été archivé automatiquement."
            ),
            color=0x808080
        )
        if hack.get("url"):
            embed.add_field(name="Lien", value=hack["url"], inline=False)
        if hack.get("deadline"):
            embed.add_field(name="Deadline était", value=hack["deadline"], inline=True)
        if hack.get("source"):
            embed.add_field(name="Source", value=hack["source"].capitalize(), inline=True)
        if hack.get("score"):
            embed.add_field(name="Score Hackahunt", value=f"{hack['score']}/10", inline=True)
        embed.set_footer(text="Hackahunt • Archivage automatique")

        await archives_channel.send(embed=embed)

        # Marquer le hackathon comme archivé en base
        conn = db.get_connection()
        conn.execute(
            "UPDATE hackathons SET status = 'archived' WHERE id = ?",
            (hack["id"],)
        )
        # Marquer les équipes associées comme terminées
        conn.execute(
            "UPDATE teams SET status = 'archived' WHERE hackathon_id = ?",
            (hack["id"],)
        )
        conn.commit()
        conn.close()

        print(f"  [Archive] '{hack['title']}' archivé.")

    @check_deadlines.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    @discord.app_commands.command(name="monequipe", description="Voir ton équipe actuelle")
    async def monequipe(self, interaction: discord.Interaction):
        conn = db.get_connection()
        row = conn.execute("""
            SELECT t.*, h.title as hack_title FROM teams t
            JOIN team_members tm ON t.id = tm.team_id
            JOIN hackathons h ON t.hackathon_id = h.id
            WHERE tm.discord_user_id = ? AND t.status = 'active'
            ORDER BY t.created_at DESC LIMIT 1
        """, (str(interaction.user.id),)).fetchone()
        conn.close()

        if not row:
            await interaction.response.send_message(
                "Tu n'as pas encore d'équipe active. Clique sur 👍 sous un hackathon pour commencer !",
                ephemeral=True
            )
            return

        team = dict(row)
        channel = interaction.guild.get_channel(int(team["channel_id"]))
        members_ids = db.get_team_members(team["id"])
        members_mentions = [f"<@{uid}>" for uid in members_ids]

        embed = discord.Embed(
            title=f"Ton équipe — {team['hack_title']}",
            color=0x534AB7
        )
        embed.add_field(name="Canal", value=channel.mention if channel else "Introuvable", inline=True)
        embed.add_field(name="Membres", value=" · ".join(members_mentions), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Teams(bot))

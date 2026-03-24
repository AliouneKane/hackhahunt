import discord
from discord.ext import commands
from discord import ui
import database as db
import os

MATCHMAKING_CHANNEL_ID = int(os.getenv("MATCHMAKING_CHANNEL_ID", "0"))

class TeamSelectView(ui.View):
    """Boutons de sélection de coéquipiers envoyés en MP"""

    def __init__(self, hackathon: dict, interested_users: list, sender_id: str):
        super().__init__(timeout=86400)  # 24h
        self.hackathon = hackathon
        self.sender_id = sender_id

        for user in interested_users:
            if user["discord_user_id"] == sender_id:
                continue
            btn = ui.Button(
                label=f"@{user['discord_username']}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"vote_{hackathon['id']}_{user['discord_user_id']}"
            )
            btn.callback = self.make_callback(user)
            self.add_item(btn)

        skip_btn = ui.Button(label="Choisir plus tard", style=discord.ButtonStyle.gray)
        skip_btn.callback = self.skip_callback
        self.add_item(skip_btn)

    def make_callback(self, target_user: dict):
        async def callback(interaction: discord.Interaction):
            target_id = target_user["discord_user_id"]
            hackathon_id = self.hackathon["id"]

            db.add_vote(hackathon_id, str(interaction.user.id), target_id)

            # Vérifier match mutuel
            if db.check_mutual_match(hackathon_id, str(interaction.user.id), target_id):
                guild = interaction.guild or interaction.client.get_guild(int(os.getenv("GUILD_ID")))
                cog = interaction.client.get_cog("Teams")
                if cog and guild:
                    await cog.create_team_channel(
                        guild, self.hackathon,
                        [interaction.user.id, int(target_id)]
                    )
                await interaction.response.send_message(
                    f"Match avec **@{target_user['discord_username']}** ! Un canal privé vient d'être créé pour votre équipe.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"Vote enregistré pour **@{target_user['discord_username']}**. En attente de sa réponse...",
                    ephemeral=True
                )
        return callback

    async def skip_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Pas de problème ! Tu peux choisir plus tard avec `/team @pseudo`.",
            ephemeral=True
        )


class JoinTeamView(ui.View):
    """Boutons proposés quand une équipe ouverte existe"""

    def __init__(self, hackathon: dict, open_team: dict):
        super().__init__(timeout=86400)
        self.hackathon = hackathon
        self.open_team = open_team

        join_btn = ui.Button(label=f"Rejoindre {open_team['channel_name']}", style=discord.ButtonStyle.success)
        join_btn.callback = self.join_callback
        self.add_item(join_btn)

        skip_btn = ui.Button(label="Non merci", style=discord.ButtonStyle.gray)
        skip_btn.callback = self.skip_callback
        self.add_item(skip_btn)

    async def join_callback(self, interaction: discord.Interaction):
        guild = interaction.client.get_guild(int(os.getenv("GUILD_ID")))
        channel = guild.get_channel(int(self.open_team["channel_id"]))
        if channel:
            await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
            # Ajouter le membre à l'équipe en base
            conn = db.get_connection()
            conn.execute(
                "INSERT OR IGNORE INTO team_members (team_id, discord_user_id) VALUES (?, ?)",
                (self.open_team["id"], str(interaction.user.id))
            )
            conn.commit()
            conn.close()

            await channel.send(f"**{interaction.user.display_name}** a rejoint l'équipe !")
            await interaction.response.send_message(
                f"Tu as rejoint **{self.open_team['channel_name']}** ! Retrouve tes coéquipiers dans {channel.mention}.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Erreur : canal introuvable.", ephemeral=True)

    async def skip_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "D'accord ! Un canal #cherche-équipe va être créé pour toi.",
            ephemeral=True
        )


class Matchmaking(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) != "👍":
            return

        hackathon = db.get_hackathon_by_message(str(payload.message_id))
        if not hackathon:
            return

        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if not member:
            return

        db.add_interest(hackathon["id"], str(payload.user_id), member.display_name)
        interested = db.get_interested_users(hackathon["id"])

        others = [u for u in interested if u["discord_user_id"] != str(payload.user_id)]

        if not others:
            await member.send(
                f"Tu es le premier à t'intéresser à **{hackathon['title']}** ! "
                f"D'autres membres recevront ta candidature dès qu'ils seront intéressés."
            )
            return

        # Construire la liste des intéressés
        liste = "\n".join([f"— {u['discord_username']} · <@{u['discord_user_id']}>" for u in others])
        embed = discord.Embed(
            title=f"Intéressés pour {hackathon['title']}",
            description=f"**{len(others)} membre(s) intéressé(s) :**\n{liste}\n\nAvec qui veux-tu faire équipe ?",
            color=0x534AB7
        )

        view = TeamSelectView(hackathon, interested, str(payload.user_id))
        try:
            await member.send(embed=embed, view=view)
        except discord.Forbidden:
            pass  # MP désactivés

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "👍":
            return
        hackathon = db.get_hackathon_by_message(str(payload.message_id))
        if hackathon:
            db.remove_interest(hackathon["id"], str(payload.user_id))

    @discord.app_commands.command(name="team", description="Propose une équipe à un membre")
    async def team_cmd(self, interaction: discord.Interaction, membre: discord.Member):
        if membre.id == interaction.user.id:
            await interaction.response.send_message("Tu ne peux pas te choisir toi-même !", ephemeral=True)
            return

        # Trouver le hackathon commun le plus récent
        conn = db.get_connection()
        row = conn.execute("""
            SELECT h.* FROM hackathons h
            JOIN interests i1 ON h.id = i1.hackathon_id AND i1.discord_user_id = ?
            JOIN interests i2 ON h.id = i2.hackathon_id AND i2.discord_user_id = ?
            WHERE h.status = 'active'
            ORDER BY h.score DESC LIMIT 1
        """, (str(interaction.user.id), str(membre.id))).fetchone()
        conn.close()

        if not row:
            await interaction.response.send_message(
                f"Vous n'êtes pas tous les deux intéressés par le même hackathon actif.",
                ephemeral=True
            )
            return

        hackathon = dict(row)
        db.add_vote(hackathon["id"], str(interaction.user.id), str(membre.id))

        if db.check_mutual_match(hackathon["id"], str(interaction.user.id), str(membre.id)):
            cog = self.bot.get_cog("Teams")
            guild = interaction.guild
            if cog and guild:
                await cog.create_team_channel(guild, hackathon, [interaction.user.id, membre.id])
            await interaction.response.send_message(
                f"Match avec {membre.mention} ! Canal d'équipe créé.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Proposition envoyée à {membre.mention} ! En attente de sa confirmation.",
                ephemeral=True
            )
            try:
                embed = discord.Embed(
                    title="Proposition d'équipe",
                    description=f"**{interaction.user.display_name}** veut faire équipe avec toi pour **{hackathon['title']}** !",
                    color=0x1D9E75
                )
                view = TeamSelectView(hackathon, [{"discord_user_id": str(interaction.user.id), "discord_username": interaction.user.display_name}], str(membre.id))
                await membre.send(embed=embed, view=view)
            except discord.Forbidden:
                pass


async def setup(bot):
    await bot.add_cog(Matchmaking(bot))

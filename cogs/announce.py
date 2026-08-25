import discord
from discord.ext import commands
from discord import app_commands


# =========================================================
# CONFIGURATION
# =========================================================

# Change these if your moderator role has a different name
MODERATOR_ROLE_NAMES = [
    "Moderator",
    "Moderators",
    "Mod",
]


# =========================================================
# ANNOUNCEMENT COG
# =========================================================

class Announce(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =====================================================
    # /ANNOUNCE
    # =====================================================

    @app_commands.command(
        name="announce",
        description="Send an announcement to a server channel."
    )
    @app_commands.describe(
        channel="The channel where the announcement should be sent",
        message="The announcement message"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def announce(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str
    ):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )
            return

        # Defer because sending the announcement may take a moment
        await interaction.response.defer(ephemeral=True)

        # =================================================
        # FIND ONLINE MODERATORS
        # =================================================

        online_moderators = []

        for member in guild.members:

            # Ignore bots
            if member.bot:
                continue

            # Check if member has a moderator role
            is_moderator = any(
                role.name in MODERATOR_ROLE_NAMES
                for role in member.roles
            )

            if not is_moderator:
                continue

            # Check online status
            if member.status in [
                discord.Status.online,
                discord.Status.idle,
                discord.Status.dnd
            ]:
                online_moderators.append(member)

        # =================================================
        # MODERATOR DISPLAY
        # =================================================

        if online_moderators:

            moderator_mentions = []

            for moderator in online_moderators:
                moderator_mentions.append(
                    f"• {moderator.mention}"
                )

            moderator_text = "\n".join(moderator_mentions)

            help_text = (
                "Need help? Our moderators are currently available:\n\n"
                f"{moderator_text}"
            )

        else:

            help_text = (
                "Need help?\n"
                "There are currently no moderators online. "
                "Please leave a message and someone will help you "
                "as soon as possible."
            )

        # =================================================
        # CREATE ANNOUNCEMENT EMBED
        # =================================================

        embed = discord.Embed(
            title="📢 Server Announcement",
            description=message,
            color=discord.Color.blurple()
        )

        # Server icon
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # =================================================
        # SERVER INFORMATION
        # =================================================

        embed.add_field(
            name="🏠 Server",
            value=guild.name,
            inline=True
        )

        embed.add_field(
            name="👥 Members",
            value=str(guild.member_count),
            inline=True
        )

        embed.add_field(
            name="📢 Posted In",
            value=channel.mention,
            inline=True
        )

        # =================================================
        # HELP / MODERATOR SECTION
        # =================================================

        embed.add_field(
            name="🛡️ Need Help?",
            value=help_text,
            inline=False
        )

        # =================================================
        # FOOTER
        # =================================================

        embed.set_footer(
            text=f"{guild.name} • Official Announcement",
            icon_url=guild.icon.url if guild.icon else None
        )

        # =================================================
        # SEND ANNOUNCEMENT
        # =================================================

        try:

            await channel.send(
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    users=True,
                    roles=False,
                    everyone=False
                )
            )

            await interaction.followup.send(
                f"✅ Announcement successfully sent to {channel.mention}.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.followup.send(
                f"❌ I don't have permission to send messages in "
                f"{channel.mention}.",
                ephemeral=True
            )

        except discord.HTTPException as e:

            await interaction.followup.send(
                f"❌ Discord returned an error: `{e}`",
                ephemeral=True
            )

    # =====================================================
    # ERROR HANDLER
    # =====================================================

    @announce.error
    async def announce_error(
        self,
        interaction: discord.Interaction,
        error
    ):

        if isinstance(error, app_commands.errors.MissingPermissions):

            message = (
                "❌ You need **Administrator** permission "
                "to use `/announce`."
            )

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    message,
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    message,
                    ephemeral=True
                )

        elif isinstance(error, app_commands.errors.CommandInvokeError):

            original = error.original

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ An error occurred: `{original}`",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ An error occurred: `{original}`",
                    ephemeral=True
                )


# =========================================================
# SETUP
# =========================================================

async def setup(bot):
    await bot.add_cog(Announce(bot))

import discord
from discord.ext import commands
from discord import app_commands
import json
import os


# =========================================================
# CONFIGURATION FILE
# =========================================================

CONFIG_FILE = "welcome_config.json"


def load_config():
    """Load saved welcome channel settings."""
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_config(config):
    """Save welcome channel settings."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


# =========================================================
# WELCOME COG
# =========================================================

class Welcome(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()

    # =====================================================
    # /SETUPWELCOME
    # =====================================================

    @app_commands.command(
        name="setupwelcome",
        description="Set up the welcome message channel."
    )
    @app_commands.describe(
        channel="Select the channel for welcome messages."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setupwelcome(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )
            return

        # Save channel for this server
        self.config[str(guild.id)] = {
            "channel_id": channel.id
        }

        save_config(self.config)

        # =================================================
        # CREATE PREVIEW
        # =================================================

        embed = self.create_welcome_embed(
            guild=guild,
            member=interaction.user
        )

        # Send confirmation
        await interaction.response.send_message(
            f"✅ Welcome system has been set up in {channel.mention}.",
            ephemeral=True
        )

        # Send preview to selected channel
        try:

            await channel.send(
                embed=embed
            )

        except discord.Forbidden:

            await interaction.followup.send(
                f"⚠️ I saved the channel, but I don't have permission "
                f"to send messages in {channel.mention}.",
                ephemeral=True
            )

        except discord.HTTPException as e:

            await interaction.followup.send(
                f"❌ Discord returned an error: `{e}`",
                ephemeral=True
            )

    # =====================================================
    # CREATE WELCOME EMBED
    # =====================================================

    def create_welcome_embed(
        self,
        guild: discord.Guild,
        member: discord.Member
    ):

        # -------------------------------------------------
        # Automatically detect server information
        # -------------------------------------------------

        server_name = guild.name
        server_icon = guild.icon.url if guild.icon else None

        # -------------------------------------------------
        # Find general channel automatically
        # -------------------------------------------------

        general_channel = self.get_general_channel(guild)

        if general_channel:
            general_text = (
                f"Start in {general_channel.mention} and say hi!"
            )
        else:
            general_text = (
                "Take a look around and say hi to the community!"
            )

        # -------------------------------------------------
        # Create embed
        # -------------------------------------------------

        embed = discord.Embed(
            title=f"👋 Welcome to {server_name}!",
            description=(
                f"**We're glad you're here, {member.mention}!**\n\n"
                "🎮 **Gaming chats**\n"
                "🔥 **Live streams**\n"
                "🏆 **Events**\n\n"
                f"{general_text}"
            ),
            color=discord.Color.blurple()
        )

        # -------------------------------------------------
        # Member profile picture
        # -------------------------------------------------

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        # -------------------------------------------------
        # Member information
        # -------------------------------------------------

        embed.add_field(
            name="👤 New Member",
            value=(
                f"{member.mention}\n"
                f"`{member.name}`"
            ),
            inline=True
        )

        # -------------------------------------------------
        # Join time
        # -------------------------------------------------

        if member.joined_at:

            joined_timestamp = int(
                member.joined_at.timestamp()
            )

            joined_text = (
                f"<t:{joined_timestamp}:R>"
            )

        else:

            joined_text = "Just now"

        embed.add_field(
            name="📅 Joined",
            value=joined_text,
            inline=True
        )

        # -------------------------------------------------
        # Total members
        # -------------------------------------------------

        embed.add_field(
            name="👥 Members",
            value=f"**{guild.member_count:,}**",
            inline=True
        )

        # -------------------------------------------------
        # Community information
        # -------------------------------------------------

        embed.add_field(
            name="🎮 Community",
            value=(
                "Welcome to the community!\n"
                "Please make sure to read the rules "
                "and enjoy your time here."
            ),
            inline=False
        )

        # -------------------------------------------------
        # Footer
        # -------------------------------------------------

        embed.set_footer(
            text=f"{server_name} • Welcome to the community",
            icon_url=server_icon
        )

        return embed

    # =====================================================
    # FIND GENERAL CHANNEL
    # =====================================================

    def get_general_channel(self, guild):

        # Look for general-chat
        for channel in guild.text_channels:

            if channel.name.lower() == "general-chat":
                return channel

        # Look for general
        for channel in guild.text_channels:

            if channel.name.lower() == "general":
                return channel

        return None

    # =====================================================
    # MEMBER JOIN EVENT
    # =====================================================

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member
    ):

        # Don't welcome bots
        if member.bot:
            return

        guild = member.guild

        # -------------------------------------------------
        # Check configuration
        # -------------------------------------------------

        guild_config = self.config.get(
            str(guild.id)
        )

        if not guild_config:
            return

        channel_id = guild_config.get(
            "channel_id"
        )

        if not channel_id:
            return

        # -------------------------------------------------
        # Find welcome channel
        # -------------------------------------------------

        channel = guild.get_channel(
            channel_id
        )

        if channel is None:

            print(
                f"⚠️ Welcome channel no longer exists "
                f"in {guild.name}"
            )

            return

        # -------------------------------------------------
        # Create welcome embed
        # -------------------------------------------------

        embed = self.create_welcome_embed(
            guild=guild,
            member=member
        )

        # -------------------------------------------------
        # Send welcome message
        # -------------------------------------------------

        try:

            await channel.send(
                content=f"👋 Welcome {member.mention}!",
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    users=True
                )
            )

            print(
                f"✅ Welcome message sent for "
                f"{member} in {guild.name}"
            )

        except discord.Forbidden:

            print(
                f"❌ No permission to send welcome message "
                f"in #{channel.name}"
            )

        except discord.HTTPException as e:

            print(
                f"❌ Discord error while sending welcome: {e}"
            )

    # =====================================================
    # /WELCOME STATUS
    # =====================================================

    @app_commands.command(
        name="welcomestatus",
        description="Check the current welcome system settings."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def welcomestatus(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

            return

        guild_config = self.config.get(
            str(guild.id)
        )

        # Not configured
        if not guild_config:

            await interaction.response.send_message(
                "❌ Welcome system is not configured.\n\n"
                "Use `/setupwelcome` to set it up.",
                ephemeral=True
            )

            return

        channel_id = guild_config.get(
            "channel_id"
        )

        channel = guild.get_channel(
            channel_id
        )

        # Channel deleted
        if channel is None:

            await interaction.response.send_message(
                "⚠️ The configured welcome channel no longer exists.\n\n"
                "Please run `/setupwelcome` again.",
                ephemeral=True
            )

            return

        # Everything OK
        await interaction.response.send_message(
            f"✅ **Welcome System Active**\n\n"
            f"📢 Channel: {channel.mention}\n"
            f"👥 Server: **{guild.name}**\n"
            f"👤 Members: **{guild.member_count:,}**",
            ephemeral=True
        )

    # =====================================================
    # /DISABLEWELCOME
    # =====================================================

    @app_commands.command(
        name="disablewelcome",
        description="Disable the welcome message system."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def disablewelcome(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

            return

        guild_id = str(guild.id)

        if guild_id not in self.config:

            await interaction.response.send_message(
                "❌ Welcome system is already disabled.",
                ephemeral=True
            )

            return

        # Remove server configuration
        del self.config[guild_id]

        save_config(self.config)

        await interaction.response.send_message(
            "✅ Welcome messages have been disabled.",
            ephemeral=True
        )

    # =====================================================
    # ERROR HANDLER
    # =====================================================

    @setupwelcome.error
    async def setupwelcome_error(
        self,
        interaction: discord.Interaction,
        error
    ):

        if isinstance(
            error,
            app_commands.errors.MissingPermissions
        ):

            message = (
                "❌ You need **Administrator** permission "
                "to use `/setupwelcome`."
            )

            if interaction.response.is_done():

                await interaction.followup.send(
                    message,
                    ephemeral=True
                )

            else:

                await interaction.response.send_message(
                    message,
                    ephemeral=True
                )

    @welcomestatus.error
    async def welcomestatus_error(
        self,
        interaction: discord.Interaction,
        error
    ):

        if isinstance(
            error,
            app_commands.errors.MissingPermissions
        ):

            await interaction.response.send_message(
                "❌ You need **Administrator** permission.",
                ephemeral=True
            )

    @disablewelcome.error
    async def disablewelcome_error(
        self,
        interaction: discord.Interaction,
        error
    ):

        if isinstance(
            error,
            app_commands.errors.MissingPermissions
        ):

            await interaction.response.send_message(
                "❌ You need **Administrator** permission.",
                ephemeral=True
            )


# =========================================================
# COG SETUP
# =========================================================

async def setup(bot):
    await bot.add_cog(Welcome(bot))

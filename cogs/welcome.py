import discord
from discord.ext import commands
from discord import app_commands
import json
import os


# =========================================================
# CONFIGURATION
# =========================================================

CONFIG_FILE = "welcome_config.json"

# Moderator role names
# Add your actual moderator role name here if different.
MODERATOR_ROLE_NAMES = [
    "MODERATOR",
    "Moderators",
    "Mod",
]


# =========================================================
# LOAD / SAVE CONFIGURATION
# =========================================================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


# =========================================================
# RULES BUTTON
# =========================================================

class RulesView(discord.ui.View):

    def __init__(self, rules_url):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="📖 Read the Rules",
                style=discord.ButtonStyle.link,
                url=rules_url
            )
        )


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
        channel="Select the channel where new members will be welcomed."
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

        # Save welcome channel
        self.config[str(guild.id)] = {
            "channel_id": channel.id
        }

        save_config(self.config)

        # Create preview
        embed = self.create_welcome_embed(
            guild,
            interaction.user
        )

        await interaction.response.send_message(
            f"✅ Welcome system has been set up in {channel.mention}.",
            ephemeral=True
        )

        try:
            await channel.send(
                embed=embed
            )

        except discord.Forbidden:

            await interaction.followup.send(
                f"⚠️ I saved the channel, but I cannot send "
                f"messages in {channel.mention}.",
                ephemeral=True
            )

    # =====================================================
    # PUBLIC WELCOME EMBED
    # =====================================================

    def create_welcome_embed(
        self,
        guild: discord.Guild,
        member: discord.Member
    ):

        server_name = guild.name
        server_icon = (
            guild.icon.url
            if guild.icon
            else None
        )

        general_channel = self.get_general_channel(guild)

        if general_channel:

            general_text = (
                f"Start in {general_channel.mention} "
                "and say hi!"
            )

        else:

            general_text = (
                "Take a look around and say hi "
                "to the community!"
            )

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

        # Member avatar
        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        # Member information
        embed.add_field(
            name="👤 New Member",
            value=(
                f"{member.mention}\n"
                f"`{member.name}`"
            ),
            inline=True
        )

        # Joined time
        if member.joined_at:

            timestamp = int(
                member.joined_at.timestamp()
            )

            joined_text = f"<t:{timestamp}:R>"

        else:

            joined_text = "Just now"

        embed.add_field(
            name="📅 Joined",
            value=joined_text,
            inline=True
        )

        # Total server members
        embed.add_field(
            name="👥 Members",
            value=f"**{guild.member_count:,}**",
            inline=True
        )

        # Community information
        embed.add_field(
            name="🎮 Community",
            value=(
                "Welcome to the community!\n"
                "Please make sure to read the rules "
                "and enjoy your time here."
            ),
            inline=False
        )

        # Footer
        embed.set_footer(
            text=f"{server_name} • Welcome to the community",
            icon_url=server_icon
        )

        return embed

    # =====================================================
    # PRIVATE DM TO NEW MEMBER
    # =====================================================

    async def send_welcome_dm(
        self,
        member: discord.Member
    ):

        guild = member.guild

        server_name = guild.name

        server_icon = (
            guild.icon.url
            if guild.icon
            else None
        )

        # =================================================
        # FIND RULES CHANNEL
        # =================================================

        rules_channel = self.get_rules_channel(guild)

        if rules_channel:

            rules_url = (
                f"https://discord.com/channels/"
                f"{guild.id}/"
                f"{rules_channel.id}"
            )

            rules_button = RulesView(rules_url)

            rules_text = (
                f"Please take a moment to read "
                f"the rules in {rules_channel.mention} "
                "before participating in the server."
            )

        else:

            rules_button = None

            rules_text = (
                "Please make sure you read the server "
                "rules before participating."
            )

        # =================================================
        # FIND MODERATORS
        # =================================================

        moderators = self.get_moderators(guild)

        total_moderators = len(moderators)

        # =================================================
        # MODERATOR LIST
        # =================================================

        if moderators:

            moderator_lines = []

            for moderator in moderators:

                # Status
                if moderator.status == discord.Status.online:
                    status = "🟢 Online"

                elif moderator.status == discord.Status.idle:
                    status = "🌙 Idle"

                elif moderator.status == discord.Status.dnd:
                    status = "⛔ DND"

                else:
                    status = "⚫ Offline"

                moderator_lines.append(
                    f"**{moderator.display_name}** "
                    f"{moderator.mention}\n"
                    f"{status}"
                )

            moderator_text = "\n\n".join(
                moderator_lines
            )

        else:

            moderator_text = (
                "No moderators are currently configured."
            )

        # =================================================
        # CREATE DM EMBED
        # =================================================

        embed = discord.Embed(
            title=f"👋 Welcome to {server_name}!",
            description=(
                f"Hi {member.mention}!\n\n"
                f"Welcome to **{server_name}**. "
                "We're happy to have you here!\n\n"
                "🎮 Join the gaming conversations\n"
                "🔥 Follow the live streams\n"
                "🏆 Take part in community events\n\n"
                f"📖 **Before you get started**\n"
                f"{rules_text}"
            ),
            color=discord.Color.blurple()
        )

        # Server logo
        if server_icon:
            embed.set_thumbnail(
                url=server_icon
            )

        # =================================================
        # SERVER INFORMATION
        # =================================================

        embed.add_field(
            name="🏠 Server",
            value=server_name,
            inline=True
        )

        embed.add_field(
            name="👥 Members",
            value=f"{guild.member_count:,}",
            inline=True
        )

        embed.add_field(
            name="🛡️ Moderators",
            value=f"**{total_moderators}**",
            inline=True
        )

        # =================================================
        # MODERATOR HELP
        # =================================================

        embed.add_field(
            name="🆘 Need Help?",
            value=(
                "You can reach out to one of our "
                "moderators below.\n\n"
                f"{moderator_text}"
            ),
            inline=False
        )

        # =================================================
        # FOOTER
        # =================================================

        embed.set_footer(
            text=(
                f"{server_name} • "
                f"{total_moderators} Moderators"
            ),
            icon_url=server_icon
        )

        # =================================================
        # SEND DM
        # =================================================

        try:

            if rules_button:

                await member.send(
                    embed=embed,
                    view=rules_button
                )

            else:

                await member.send(
                    embed=embed
                )

            print(
                f"✅ Welcome DM sent to "
                f"{member} in {server_name}"
            )

            return True

        except discord.Forbidden:

            print(
                f"⚠️ Could not DM {member}. "
                "Their DMs may be disabled."
            )

            return False

        except discord.HTTPException as e:

            print(
                f"❌ Discord error while DMing "
                f"{member}: {e}"
            )

            return False

    # =====================================================
    # MEMBER JOIN EVENT
    # =====================================================

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member
    ):

        # Ignore bots
        if member.bot:
            return

        guild = member.guild

        # =================================================
        # PUBLIC WELCOME
        # =================================================

        guild_config = self.config.get(
            str(guild.id)
        )

        if guild_config:

            channel_id = guild_config.get(
                "channel_id"
            )

            channel = guild.get_channel(
                channel_id
            )

            if channel:

                embed = self.create_welcome_embed(
                    guild,
                    member
                )

                try:

                    await channel.send(
                        content=f"👋 Welcome {member.mention}!",
                        embed=embed,
                        allowed_mentions=discord.AllowedMentions(
                            users=True
                        )
                    )

                    print(
                        f"✅ Public welcome sent for "
                        f"{member} in {guild.name}"
                    )

                except discord.Forbidden:

                    print(
                        f"❌ Cannot send welcome message "
                        f"in #{channel.name}"
                    )

                except discord.HTTPException as e:

                    print(
                        f"❌ Discord error: {e}"
                    )

        # =================================================
        # PRIVATE WELCOME DM
        # =================================================

        await self.send_welcome_dm(
            member
        )

    # =====================================================
    # GET MODERATORS
    # =====================================================

    def get_moderators(
        self,
        guild: discord.Guild
    ):

        moderators = []

        for member in guild.members:

            # Don't include bots
            if member.bot:
                continue

            # Check moderator roles
            is_moderator = any(
                role.name in MODERATOR_ROLE_NAMES
                for role in member.roles
            )

            if is_moderator:
                moderators.append(member)

        return moderators

    # =====================================================
    # FIND RULES CHANNEL
    # =====================================================

    def get_rules_channel(
        self,
        guild: discord.Guild
    ):

        # Discord's official rules channel
        if guild.rules_channel:
            return guild.rules_channel

        # Look for common rules channel names
        rules_names = [
            "rules",
            "server-rules",
            "rules-and-info",
            "rules-info"
        ]

        for channel in guild.text_channels:

            if channel.name.lower() in rules_names:
                return channel

        return None

    # =====================================================
    # FIND GENERAL CHANNEL
    # =====================================================

    def get_general_channel(
        self,
        guild: discord.Guild
    ):

        general_names = [
            "general-chat",
            "general"
        ]

        for channel in guild.text_channels:

            if channel.name.lower() in general_names:
                return channel

        return None

    # =====================================================
    # /WELCOME STATUS
    # =====================================================

    @app_commands.command(
        name="welcomestatus",
        description="Check the welcome system configuration."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
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

        if not guild_config:

            await interaction.response.send_message(
                "❌ Welcome system is not configured.\n\n"
                "Use `/setupwelcome` first.",
                ephemeral=True
            )

            return

        channel = guild.get_channel(
            guild_config.get("channel_id")
        )

        rules_channel = self.get_rules_channel(
            guild
        )

        moderators = self.get_moderators(
            guild
        )

        if channel:

            channel_text = channel.mention

        else:

            channel_text = "❌ Channel no longer exists"

        if rules_channel:

            rules_text = rules_channel.mention

        else:

            rules_text = "❌ Rules channel not found"

        await interaction.response.send_message(
            f"### 👋 Welcome System\n\n"
            f"📢 **Welcome Channel:** {channel_text}\n"
            f"📖 **Rules Channel:** {rules_text}\n"
            f"🛡️ **Moderators:** {len(moderators)}\n"
            f"👥 **Members:** {guild.member_count:,}",
            ephemeral=True
        )

    # =====================================================
    # /DISABLEWELCOME
    # =====================================================

    @app_commands.command(
        name="disablewelcome",
        description="Disable the welcome system."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
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

        del self.config[guild_id]

        save_config(self.config)

        await interaction.response.send_message(
            "✅ Welcome system has been disabled.",
            ephemeral=True
        )

    # =====================================================
    # ERROR HANDLERS
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
                "to use this command."
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

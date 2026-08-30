
import discord
from discord.ext import commands
from discord import app_commands

import json
import os


# =========================================================
# CONFIGURATION
# =========================================================

CONFIG_FILE = "cmd_config.json"


# =========================================================
# JSON FUNCTIONS
# =========================================================

def load_json(filename):

    if not os.path.exists(filename):
        return {}

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except (
        json.JSONDecodeError,
        FileNotFoundError
    ):

        return {}


def save_json(filename, data):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4
        )


# =========================================================
# MODERATOR ROLES
# =========================================================

MODERATOR_ROLE_NAMES = [
    "MODERATOR",
    "Moderators",
    "Mod"
]


# =========================================================
# MODERATOR CHECK
# =========================================================

def is_moderator(
    member: discord.Member
):

    if member.guild_permissions.administrator:

        return True

    return any(
        role.name in MODERATOR_ROLE_NAMES
        for role in member.roles
    )


# =========================================================
# COMMAND SYSTEM
# =========================================================

class CommandSystem(
    commands.Cog
):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        self.config = load_json(
            CONFIG_FILE
        )

    # =====================================================
    # SAVE CONFIG
    # =====================================================

    def save_config(self):

        save_json(
            CONFIG_FILE,
            self.config
        )

    # =====================================================
    # GET GUILD CONFIG
    # =====================================================

    def get_guild_config(
        self,
        guild: discord.Guild
    ):

        guild_id = str(
            guild.id
        )

        if guild_id not in self.config:

            self.config[guild_id] = {}

        return self.config[guild_id]

    # =====================================================
    # GET COMMAND CHANNEL
    # =====================================================

    def get_command_channel(
        self,
        guild: discord.Guild
    ):

        guild_config = self.config.get(
            str(guild.id),
            {}
        )

        channel_id = guild_config.get(
            "command_channel_id"
        )

        if not channel_id:

            return None

        channel = guild.get_channel(
            channel_id
        )

        if isinstance(
            channel,
            discord.TextChannel
        ):

            return channel

        return None

    # =====================================================
    # CREATE COMMAND EMBED
    # =====================================================

    def create_command_embed(
        self,
        guild: discord.Guild
    ):

        embed = discord.Embed(

            title="🤖 Bot Commands",

            description=(
                "Here is a quick overview of the "
                "commands available in this server.\n\n"
                "Use the commands according to your "
                "permissions."
            ),

            color=discord.Color.blurple()
        )

        if guild.icon:

            embed.set_thumbnail(
                url=guild.icon.url
            )

        # -------------------------------------------------
        # SUPPORT
        # -------------------------------------------------

        embed.add_field(

            name="🆘 SUPPORT",

            value=(
                "`/support`\n"
                "Submit a support request to the "
                "moderation team."
            ),

            inline=False
        )

        # -------------------------------------------------
        # SUPPORT MANAGEMENT
        # -------------------------------------------------

        embed.add_field(

            name="🎫 SUPPORT MANAGEMENT",

            value=(
                "`/closehelp <token>`\n"
                "Close an existing support ticket.\n\n"

                "`/helpstatus`\n"
                "Check the current support system "
                "configuration and active tickets."
            ),

            inline=False
        )

        # -------------------------------------------------
        # SUPPORT SETUP
        # -------------------------------------------------

        embed.add_field(

            name="⚙️ SUPPORT SETUP",

            value=(
                "`/setuphelp <channel>`\n"
                "Set the channel where support requests "
                "are posted.\n\n"

                "`/setuphelpcategory <category>`\n"
                "Set the category where private support "
                "tickets are created.\n\n"

                "`/setuphelpcounter <category>`\n"
                "Set the category where the live support "
                "ticket counter is created."
            ),

            inline=False
        )

        # -------------------------------------------------
        # COMMAND SYSTEM
        # -------------------------------------------------

        embed.add_field(

            name="🤖 COMMAND SYSTEM",

            value=(
                "`/cmd`\n"
                "Show this command list.\n\n"

                "`/cmdsetup <channel>`\n"
                "Set the channel where the command list "
                "is displayed."
            ),

            inline=False
        )

        # -------------------------------------------------
        # FOOTER
        # -------------------------------------------------

        embed.set_footer(

            text=(
                f"{guild.name} • Bot Command Center"
            ),

            icon_url=(
                guild.icon.url
                if guild.icon
                else None
            )
        )

        return embed

    # =====================================================
    # /CMDSETUP
    # =====================================================

    @app_commands.command(

        name="cmdsetup",

        description=(
            "Set the channel where the bot command list "
            "will be displayed."
        )
    )
    @app_commands.describe(

        channel=(
            "The channel where /cmd will be displayed."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def cmdsetup(

        self,

        interaction: discord.Interaction,

        channel: discord.TextChannel

    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(

                "❌ This command can only be used "
                "inside a server.",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # SAVE CHANNEL
        # -------------------------------------------------

        guild_config = self.get_guild_config(
            guild
        )

        guild_config[
            "command_channel_id"
        ] = channel.id

        self.save_config()

        # -------------------------------------------------
        # CREATE INITIAL COMMAND MESSAGE
        # -------------------------------------------------

        embed = self.create_command_embed(
            guild
        )

        try:

            message = await channel.send(
                embed=embed
            )

            guild_config[
                "command_message_id"
            ] = message.id

            self.save_config()

        except discord.Forbidden:

            await interaction.response.send_message(

                "❌ I don't have permission to send "
                f"messages in {channel.mention}.",

                ephemeral=True
            )

            return

        except discord.HTTPException:

            await interaction.response.send_message(

                "❌ Discord returned an error while "
                "creating the command panel.",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # CONFIRM
        # -------------------------------------------------

        await interaction.response.send_message(

            f"✅ **Command channel configured.**\n\n"
            f"📢 Command list: {channel.mention}\n"
            f"🆔 Message ID: `{message.id}`\n\n"
            f"Moderators can now use `/cmd` in that channel.",

            ephemeral=True
        )

    # =====================================================
    # /CMD
    # =====================================================

    @app_commands.command(

        name="cmd",

        description=(
            "Show all available bot commands."
        )
    )
    async def cmd(

        self,

        interaction: discord.Interaction

    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(

                "❌ This command can only be used "
                "inside a server.",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # CHECK MODERATOR
        # -------------------------------------------------

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(

                "❌ Only moderators can use this command.",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # GET CONFIGURED CHANNEL
        # -------------------------------------------------

        command_channel = self.get_command_channel(
            guild
        )

        if command_channel is None:

            await interaction.response.send_message(

                "❌ The command channel has not been "
                "configured yet.\n\n"
                "Ask an administrator to use "
                "`/cmdsetup #channel`.",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # CHECK CHANNEL
        # -------------------------------------------------

        if interaction.channel.id != command_channel.id:

            await interaction.response.send_message(

                f"❌ Please use `/cmd` in "
                f"{command_channel.mention}.",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # UPDATE EXISTING COMMAND MESSAGE
        # -------------------------------------------------

        guild_config = self.get_guild_config(
            guild
        )

        message_id = guild_config.get(
            "command_message_id"
        )

        embed = self.create_command_embed(
            guild
        )

        if message_id:

            try:

                message = await command_channel.fetch_message(
                    message_id
                )

                await message.edit(
                    embed=embed
                )

                await interaction.response.send_message(

                    "✅ Command list updated.",

                    ephemeral=True
                )

                return

            except discord.NotFound:

                pass

            except discord.Forbidden:

                pass

            except discord.HTTPException:

                pass

        # -------------------------------------------------
        # CREATE NEW COMMAND MESSAGE
        # -------------------------------------------------

        try:

            message = await command_channel.send(
                embed=embed
            )

            guild_config[
                "command_message_id"
            ] = message.id

            self.save_config()

            await interaction.response.send_message(

                "✅ Command list has been posted.",

                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(

                "❌ I don't have permission to send "
                f"messages in {command_channel.mention}.",

                ephemeral=True
            )

        except discord.HTTPException:

            await interaction.response.send_message(

                "❌ Discord returned an error while "
                "posting the command list.",

                ephemeral=True
            )

    # =====================================================
    # ERROR HANDLER
    # =====================================================

    @cmdsetup.error
    async def cmdsetup_error(

        self,

        interaction: discord.Interaction,

        error

    ):

        if isinstance(

            error,

            app_commands.errors.MissingPermissions

        ):

            await interaction.response.send_message(

                "❌ You need **Administrator** permission "
                "to configure the command channel.",

                ephemeral=True
            )

        else:

            await interaction.response.send_message(

                "❌ Something went wrong while configuring "
                "the command system.",

                ephemeral=True
            )


# =========================================================
# COG SETUP
# =========================================================

async def setup(bot):

    await bot.add_cog(
        CommandSystem(bot)
    )

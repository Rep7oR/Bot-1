# ============================================================
# REFRESH / CONFIGURATION READER
# File: cogs/refresh.py
#
# Reads the ACTUAL JSON configuration files used by the Cogs.
#
# It does NOT use config_manager.py.
#
# Example:
#
# voice_config.json
# welcome_config.json
# youtube_config.json
# support_config.json
# etc.
#
# /refresh
# ============================================================

import discord
from discord.ext import commands
from discord import app_commands

import os
import json
import re
from pathlib import Path
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

# Where the JSON files are located.
#
# Your current Cogs appear to use files like:
#
# voice_config.json
# youtube_config.json
# welcome_config.json
#
# which are normally in the project root.
#
CONFIG_ROOT = Path(".")


# Files that should NOT be treated as Cog configuration.
#
# Add more here if you have JSON files that are not configs.
IGNORED_JSON_FILES = {
    "package.json",
    "package-lock.json",
}


# Maximum Discord embed description length
MAX_DESCRIPTION = 4000


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def is_guild_id(value):
    """
    Check whether a string looks like a Discord guild ID.
    """

    if not isinstance(value, str):
        return False

    return value.isdigit() and len(value) >= 15


# ============================================================
# FORMAT JSON VALUES
# ============================================================

def format_value(
    value,
    guild=None,
    indent=0
):
    """
    Convert JSON values into readable Discord text.

    Also attempts to resolve:
        channel IDs
        role IDs
        category IDs
        guild IDs
    """

    spacing = " " * indent

    # --------------------------------------------------------
    # None
    # --------------------------------------------------------

    if value is None:
        return "`None`"

    # --------------------------------------------------------
    # Boolean
    # --------------------------------------------------------

    if isinstance(value, bool):

        return "✅ Enabled" if value else "❌ Disabled"

    # --------------------------------------------------------
    # Number
    # --------------------------------------------------------

    if isinstance(value, (int, float)):

        return f"`{value}`"

    # --------------------------------------------------------
    # String
    # --------------------------------------------------------

    if isinstance(value, str):

        # --------------------------------------------
        # Discord ID
        # --------------------------------------------

        if value.isdigit() and len(value) >= 15:

            if guild is not None:

                try:

                    discord_id = int(value)

                    # Channel
                    channel = guild.get_channel(
                        discord_id
                    )

                    if channel:

                        return (
                            f"{channel.mention} "
                            f"`({channel.name})`"
                        )

                    # Role
                    role = guild.get_role(
                        discord_id
                    )

                    if role:

                        return (
                            f"{role.mention} "
                            f"`({role.name})`"
                        )

                except Exception:
                    pass

            return f"`{value}`"

        # --------------------------------------------
        # Regular string
        # --------------------------------------------

        # Prevent extremely large values
        if len(value) > 1000:

            value = value[:1000] + "..."

        return f"`{value}`"

    # --------------------------------------------------------
    # List
    # --------------------------------------------------------

    if isinstance(value, list):

        if not value:

            return "`[]`"

        result = []

        for item in value[:50]:

            result.append(

                format_value(
                    item,
                    guild=guild,
                    indent=indent + 2
                )
            )

        if len(value) > 50:

            result.append(
                f"`... {len(value) - 50} more items`"
            )

        return "\n".join(
            f"{spacing}• {item}"
            for item in result
        )

    # --------------------------------------------------------
    # Dictionary
    # --------------------------------------------------------

    if isinstance(value, dict):

        if not value:

            return "`{}`"

        result = []

        for key, item in value.items():

            # ------------------------------------
            # Special handling for common IDs
            # ------------------------------------

            readable_key = str(key)

            key_lower = readable_key.lower()

            # Guild ID
            if (
                key_lower in {
                    "guild_id",
                    "server_id"
                }
                and isinstance(item, (int, str))
            ):

                guild_text = f"`{item}`"

                if guild is not None:

                    try:

                        if int(item) == guild.id:

                            guild_text = (
                                f"{guild.name} "
                                f"`({guild.id})`"
                            )

                    except Exception:
                        pass

                result.append(
                    f"{spacing}**{readable_key}:** "
                    f"{guild_text}"
                )

                continue

            # ------------------------------------
            # Regular nested value
            # ------------------------------------

            formatted = format_value(

                item,

                guild=guild,

                indent=indent + 2
            )

            result.append(

                f"{spacing}**{readable_key}:** "
                f"{formatted}"
            )

        return "\n".join(result)

    # --------------------------------------------------------
    # Unknown
    # --------------------------------------------------------

    return f"`{str(value)}`"


# ============================================================
# READ JSON FILE
# ============================================================

def read_json_file(
    filepath
):
    """
    Safely read a JSON file.
    """

    try:

        with open(
            filepath,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file), None

    except json.JSONDecodeError as error:

        return None, (
            f"Invalid JSON: {error}"
        )

    except Exception as error:

        return None, (
            f"{type(error).__name__}: {error}"
        )


# ============================================================
# FIND JSON CONFIGURATION FILES
# ============================================================

def find_json_files():

    files = []

    # --------------------------------------------------------
    # Search project root
    # --------------------------------------------------------

    for filepath in CONFIG_ROOT.glob("*.json"):

        if filepath.name in IGNORED_JSON_FILES:
            continue

        files.append(filepath)

    # --------------------------------------------------------
    # Also search cogs folder
    # --------------------------------------------------------

    cogs_folder = CONFIG_ROOT / "cogs"

    if cogs_folder.exists():

        for filepath in cogs_folder.glob("*.json"):

            if filepath.name in IGNORED_JSON_FILES:
                continue

            if filepath not in files:

                files.append(filepath)

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    files.sort(
        key=lambda path: path.name.lower()
    )

    return files


# ============================================================
# CREATE DISPLAY NAME
# ============================================================

def cog_name_from_file(
    filename
):

    name = Path(
        filename
    ).stem

    # Remove common suffix
    if name.lower().endswith("_config"):

        name = name[:-7]

    elif name.lower().endswith("config"):

        name = name[:-6]

    # Replace separators
    name = name.replace(
        "_",
        " "
    )

    name = name.replace(
        "-",
        " "
    )

    # Capitalize
    return name.title()


# ============================================================
# FIND GUILD CONFIGURATION
# ============================================================

def get_guild_data(
    data,
    guild_id
):
    """
    Try to find the configuration belonging
    to the current Discord server.

    Supports structures such as:

    {
        "123456789": {...}
    }

    or:

    {
        "guild_id": 123456789,
        ...
    }

    or:

    {
        "guilds": {
            "123456789": {...}
        }
    }
    """

    guild_id = str(guild_id)

    # --------------------------------------------------------
    # Not dictionary
    # --------------------------------------------------------

    if not isinstance(data, dict):

        return None

    # --------------------------------------------------------
    # Direct guild key
    # --------------------------------------------------------

    if guild_id in data:

        return data[guild_id]

    # --------------------------------------------------------
    # Integer guild key
    # --------------------------------------------------------

    try:

        integer_guild_id = int(guild_id)

        if integer_guild_id in data:

            return data[integer_guild_id]

    except Exception:
        pass

    # --------------------------------------------------------
    # Search common containers
    # --------------------------------------------------------

    for container_name in (
        "guilds",
        "servers",
        "configurations",
        "configs",
        "data"
    ):

        container = data.get(
            container_name
        )

        if isinstance(
            container,
            dict
        ):

            if guild_id in container:

                return container[guild_id]

    # --------------------------------------------------------
    # Check guild_id inside object
    # --------------------------------------------------------

    if (
        str(
            data.get(
                "guild_id",
                ""
            )
        ) == guild_id
    ):

        return data

    # --------------------------------------------------------
    # Check server_id
    # --------------------------------------------------------

    if (
        str(
            data.get(
                "server_id",
                ""
            )
        ) == guild_id
    ):

        return data

    # --------------------------------------------------------
    # Nothing found
    # --------------------------------------------------------

    return None


# ============================================================
# DETECT WHETHER JSON HAS GUILD CONFIGURATION
# ============================================================

def has_any_configuration(
    data
):

    if data is None:
        return False

    if isinstance(
        data,
        dict
    ):

        return len(data) > 0

    if isinstance(
        data,
        list
    ):

        return len(data) > 0

    return True


# ============================================================
# CREATE FILE SUMMARY
# ============================================================

def create_file_summary(
    filepath,
    guild
):

    filename = filepath.name

    cog_name = cog_name_from_file(
        filename
    )

    data, error = read_json_file(
        filepath
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    lines = []

    lines.append(
        f"📦 **{cog_name}**"
    )

    lines.append(
        f"📄 `{filename}`"
    )

    # --------------------------------------------------------
    # Read error
    # --------------------------------------------------------

    if error:

        lines.append(
            f"❌ **Error:** {error}"
        )

        return "\n".join(lines)

    # --------------------------------------------------------
    # Empty file
    # --------------------------------------------------------

    if not has_any_configuration(data):

        lines.append(
            "⚪ **Configuration file is empty.**"
        )

        return "\n".join(lines)

    # --------------------------------------------------------
    # Find guild configuration
    # --------------------------------------------------------

    guild_config = get_guild_data(

        data,

        guild.id
    )

    # --------------------------------------------------------
    # Guild-specific configuration
    # --------------------------------------------------------

    if guild_config is not None:

        lines.append(
            "🟢 **Guild configuration found.**"
        )

        formatted = format_value(

            guild_config,

            guild=guild
        )

        if formatted:

            lines.append(
                formatted
            )

        return "\n".join(lines)

    # --------------------------------------------------------
    # File exists but no guild-specific config
    # --------------------------------------------------------

    lines.append(
        "🟡 **Configuration file found, "
        "but no configuration for this server.**"
    )

    # --------------------------------------------------------
    # Show top-level information
    # --------------------------------------------------------

    if isinstance(
        data,
        dict
    ):

        # If the file contains guild IDs,
        # show which servers are configured.
        guild_keys = []

        for key in data.keys():

            if is_guild_id(
                str(key)
            ):

                guild_keys.append(
                    str(key)
                )

        if guild_keys:

            lines.append(
                f"🌐 **Servers configured:** "
                f"`{len(guild_keys)}`"
            )

            if str(guild.id) not in guild_keys:

                lines.append(
                    "⚠️ This server is not "
                    "present in the file."
                )

        else:

            # Show global configuration
            formatted = format_value(

                data,

                guild=guild
            )

            if formatted:

                lines.append(
                    "⚙️ **Global configuration:**"
                )

                lines.append(
                    formatted
                )

    return "\n".join(lines)


# ============================================================
# REFRESH COG
# ============================================================

class Refresh(commands.Cog):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        print(
            "🔄 Refresh configuration system loaded."
        )

    # ========================================================
    # /REFRESH
    # ========================================================

    @app_commands.command(

        name="refresh",

        description=(
            "Read and display all saved bot configurations."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def refresh(
        self,
        interaction: discord.Interaction
    ):

        # ----------------------------------------------------
        # Server only
        # ----------------------------------------------------

        if interaction.guild is None:

            await interaction.response.send_message(

                "❌ This command can only be used "
                "inside a server.",

                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # Defer
        # ----------------------------------------------------

        await interaction.response.defer(
            ephemeral=True
        )

        guild = interaction.guild

        # ----------------------------------------------------
        # Find JSON files
        # ----------------------------------------------------

        json_files = find_json_files()

        # ----------------------------------------------------
        # No files
        # ----------------------------------------------------

        if not json_files:

            await interaction.followup.send(

                "📊 **Bot Configuration Refresh**\n\n"

                "❌ No JSON configuration files "
                "were found.",

                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # Counters
        # ----------------------------------------------------

        total_files = len(
            json_files
        )

        configured = 0
        not_configured = 0
        errors = 0

        # ----------------------------------------------------
        # Generate summaries
        # ----------------------------------------------------

        summaries = []

        for filepath in json_files:

            summary = create_file_summary(

                filepath,

                guild
            )

            summaries.append(
                summary
            )

            # --------------------------------------------
            # Determine status
            # --------------------------------------------

            if "❌ **Error:**" in summary:

                errors += 1

            elif "🟢 **Guild configuration found.**" in summary:

                configured += 1

            else:

                not_configured += 1

        # ----------------------------------------------------
        # Main summary
        # ----------------------------------------------------

        overview = (

            "📊 **BOT CONFIGURATION REFRESH**\n\n"

            f"🏠 **Server:** {guild.name}\n\n"

            f"📦 **Configuration files found:** "
            f"`{total_files}`\n"

            f"🟢 **Configured for this server:** "
            f"`{configured}`\n"

            f"🟡 **Not configured for this server:** "
            f"`{not_configured}`\n"

            f"❌ **Errors:** "
            f"`{errors}`\n\n"

            "━━━━━━━━━━━━━━━━━━━━"
        )

        # ----------------------------------------------------
        # Build chunks
        # ----------------------------------------------------

        messages = []

        current = overview

        for summary in summaries:

            addition = (
                "\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                + summary
            )

            # Discord message limit
            if (
                len(current)
                + len(addition)
                > 3900
            ):

                messages.append(
                    current
                )

                current = summary

            else:

                current += addition

        if current:

            messages.append(
                current
            )

        # ----------------------------------------------------
        # Send first page
        # ----------------------------------------------------

        for index, content in enumerate(
            messages
        ):

            embed = discord.Embed(

                title=(
                    "📊 Bot Configuration Refresh"
                    if index == 0
                    else
                    f"📊 Configuration "
                    f"Page {index + 1}"
                ),

                description=content,

                color=(
                    discord.Color.green()
                    if errors == 0
                    else discord.Color.orange()
                ),

                timestamp=datetime.utcnow()
            )

            embed.set_footer(

                text=(
                    f"Page {index + 1}/{len(messages)}"
                )
            )

            await interaction.followup.send(

                embed=embed,

                ephemeral=True
            )

    # ========================================================
    # /CONFIGFILES
    # ========================================================

    @app_commands.command(

        name="configfiles",

        description=(
            "Show all configuration files detected by the bot."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def configfiles(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        files = find_json_files()

        if not files:

            await interaction.followup.send(

                "❌ No JSON configuration files found.",

                ephemeral=True
            )

            return

        text = "\n".join(

            f"📄 `{file.name}`"

            for file in files
        )

        if len(text) > 3900:

            text = text[:3900] + "\n..."

        embed = discord.Embed(

            title="📂 Configuration Files",

            description=text,

            color=discord.Color.blurple()
        )

        embed.set_footer(

            text=f"{len(files)} configuration file(s) detected."
        )

        await interaction.followup.send(

            embed=embed,

            ephemeral=True
        )

    # ========================================================
    # /CONFIGREAD
    # ========================================================

    @app_commands.command(

        name="configread",

        description=(
            "Read one specific JSON configuration file."
        )
    )
    @app_commands.describe(

        filename=(
            "Example: voice_config.json"
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def configread(
        self,
        interaction: discord.Interaction,
        filename: str
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        # ----------------------------------------------------
        # Security:
        # Prevent directory traversal
        # ----------------------------------------------------

        filename = os.path.basename(
            filename
        )

        filepath = CONFIG_ROOT / filename

        # ----------------------------------------------------
        # File doesn't exist
        # ----------------------------------------------------

        if not filepath.exists():

            await interaction.followup.send(

                f"❌ Configuration file not found:\n"
                f"`{filename}`",

                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # Read
        # ----------------------------------------------------

        summary = create_file_summary(

            filepath,

            interaction.guild
        )

        # ----------------------------------------------------
        # Too large
        # ----------------------------------------------------

        if len(summary) <= 3900:

            embed = discord.Embed(

                title=f"📄 {filename}",

                description=summary,

                color=discord.Color.blurple()
            )

            await interaction.followup.send(

                embed=embed,

                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # Split
        # ----------------------------------------------------

        chunks = []

        while summary:

            chunk = summary[:3900]

            # Try to split at newline
            newline = chunk.rfind(
                "\n"
            )

            if newline > 1000:

                chunk = chunk[:newline]

            chunks.append(
                chunk
            )

            summary = summary[
                len(chunk):
            ]

        for index, chunk in enumerate(
            chunks
        ):

            embed = discord.Embed(

                title=(
                    f"📄 {filename}"
                    if index == 0
                    else
                    f"📄 {filename} "
                    f"(Page {index + 1})"
                ),

                description=chunk,

                color=discord.Color.blurple()
            )

            await interaction.followup.send(

                embed=embed,

                ephemeral=True
            )

    # ========================================================
    # ERROR HANDLER
    # ========================================================

    @refresh.error
    async def refresh_error(
        self,
        interaction,
        error
    ):

        if isinstance(
            error,
            app_commands.errors.MissingPermissions
        ):

            message = (
                "❌ You need **Administrator** "
                "permission to use `/refresh`."
            )

        else:

            print(
                f"❌ /refresh error: {error}"
            )

            message = (
                "❌ An error occurred while "
                "reading the bot configuration."
            )

        try:

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

        except Exception:

            pass


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        Refresh(bot)
    )

    print(
        "✅ Refresh Cog loaded successfully."
    )

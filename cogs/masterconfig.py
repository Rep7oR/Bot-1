# ============================================================
# MASTER CONFIG / REFRESH SYSTEM
# ============================================================
#
# This Cog directly reads the REAL JSON configuration files
# used by your other Cogs.
#
# It does NOT depend on config_manager.py.
#
# Examples:
#
# voice_config.json
# youtube_config.json
# welcome_config.json
# support_config.json
# rules_config.json
# etc.
#
# Commands:
#
# /refresh
# /configfiles
# /configread <filename>
#
# ============================================================

import discord
from discord.ext import commands
from discord import app_commands

import json
import os
import traceback
from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# CONFIGURATION
# ============================================================

# Your Cogs currently save their JSON files in the project root.
CONFIG_ROOT = Path(".")


# JSON files which are NOT bot configuration files.
IGNORED_JSON_FILES = {
    "package.json",
    "package-lock.json",
}


# Files which should not be displayed as bot configurations.
# Add any other non-config JSON files here if necessary.
IGNORED_CONFIG_NAMES = {
    "bot_config.json",
}


# ============================================================
# JSON READER
# ============================================================

def read_json_file(filepath):
    """
    Read a JSON file safely.

    Returns:
        (data, None)
    or
        (None, error_message)
    """

    try:

        with open(
            filepath,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return data, None

    except FileNotFoundError:

        return None, "File not found."

    except json.JSONDecodeError as e:

        return None, (
            f"Invalid JSON: {e}"
        )

    except Exception as e:

        return None, (
            f"{type(e).__name__}: {e}"
        )


# ============================================================
# FIND CONFIGURATION FILES
# ============================================================

def find_config_files():

    files = []

    # --------------------------------------------------------
    # Project root
    # --------------------------------------------------------

    try:

        for filepath in CONFIG_ROOT.glob("*.json"):

            if filepath.name in IGNORED_JSON_FILES:
                continue

            if filepath.name in IGNORED_CONFIG_NAMES:
                continue

            files.append(filepath)

    except Exception as e:

        print(
            f"❌ Error scanning root JSON files: {e}"
        )

    # --------------------------------------------------------
    # Cogs folder
    # --------------------------------------------------------

    cogs_folder = CONFIG_ROOT / "cogs"

    if cogs_folder.exists():

        try:

            for filepath in cogs_folder.glob("*.json"):

                if filepath.name in IGNORED_JSON_FILES:
                    continue

                if filepath.name in IGNORED_CONFIG_NAMES:
                    continue

                if filepath not in files:

                    files.append(filepath)

        except Exception as e:

            print(
                f"❌ Error scanning Cogs JSON files: {e}"
            )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    files.sort(
        key=lambda x: x.name.lower()
    )

    return files


# ============================================================
# GET FRIENDLY NAME
# ============================================================

def get_config_name(filename):

    name = Path(
        filename
    ).stem

    # Remove common config suffixes
    suffixes = [
        "_config",
        "_data",
        "config",
        "data"
    ]

    for suffix in suffixes:

        if name.lower().endswith(
            suffix
        ):

            name = name[
                :-len(suffix)
            ]

            break

    # Replace separators
    name = name.replace(
        "_",
        " "
    )

    name = name.replace(
        "-",
        " "
    )

    return name.strip().title()


# ============================================================
# FIND GUILD CONFIGURATION
# ============================================================

def find_guild_config(
    data,
    guild_id
):
    """
    Supports multiple JSON structures.

    Structure 1:

    {
        "123456789": {
            ...
        }
    }

    Structure 2:

    {
        "guilds": {
            "123456789": {
                ...
            }
        }
    }

    Structure 3:

    {
        "guild_id": 123456789,
        ...
    }

    Structure 4:

    {
        "server_id": 123456789,
        ...
    }
    """

    if not isinstance(
        data,
        dict
    ):

        return None

    guild_id_string = str(
        guild_id
    )

    # --------------------------------------------------------
    # Direct string guild key
    # --------------------------------------------------------

    if guild_id_string in data:

        return data[
            guild_id_string
        ]

    # --------------------------------------------------------
    # Direct integer guild key
    # --------------------------------------------------------

    try:

        guild_id_integer = int(
            guild_id
        )

        if guild_id_integer in data:

            return data[
                guild_id_integer
            ]

    except Exception:

        pass

    # --------------------------------------------------------
    # Common containers
    # --------------------------------------------------------

    containers = [
        "guilds",
        "servers",
        "configurations",
        "configs",
        "data"
    ]

    for container_name in containers:

        container = data.get(
            container_name
        )

        if not isinstance(
            container,
            dict
        ):

            continue

        if guild_id_string in container:

            return container[
                guild_id_string
            ]

        try:

            guild_id_integer = int(
                guild_id
            )

            if guild_id_integer in container:

                return container[
                    guild_id_integer
                ]

        except Exception:

            pass

    # --------------------------------------------------------
    # Object containing guild_id
    # --------------------------------------------------------

    saved_guild_id = data.get(
        "guild_id"
    )

    if saved_guild_id is not None:

        if str(
            saved_guild_id
        ) == guild_id_string:

            return data

    # --------------------------------------------------------
    # Object containing server_id
    # --------------------------------------------------------

    saved_server_id = data.get(
        "server_id"
    )

    if saved_server_id is not None:

        if str(
            saved_server_id
        ) == guild_id_string:

            return data

    # --------------------------------------------------------
    # Object containing id
    # --------------------------------------------------------

    saved_id = data.get(
        "id"
    )

    if saved_id is not None:

        if str(
            saved_id
        ) == guild_id_string:

            return data

    # --------------------------------------------------------
    # Nothing found
    # --------------------------------------------------------

    return None


# ============================================================
# FORMAT VALUE
# ============================================================

def format_value(
    value,
    guild=None,
    depth=0
):
    """
    Convert JSON data to readable Discord text.

    Attempts to resolve:
        channel IDs
        role IDs
        category IDs
    """

    # --------------------------------------------------------
    # None
    # --------------------------------------------------------

    if value is None:

        return "`None`"

    # --------------------------------------------------------
    # Boolean
    # --------------------------------------------------------

    if isinstance(
        value,
        bool
    ):

        return (
            "✅ Enabled"
            if value
            else
            "❌ Disabled"
        )

    # --------------------------------------------------------
    # Number
    # --------------------------------------------------------

    if isinstance(
        value,
        (int, float)
    ):

        return f"`{value}`"

    # --------------------------------------------------------
    # String
    # --------------------------------------------------------

    if isinstance(
        value,
        str
    ):

        # --------------------------------------------
        # Possible Discord ID
        # --------------------------------------------

        if (
            value.isdigit()
            and len(value) >= 15
        ):

            if guild is not None:

                try:

                    discord_id = int(
                        value
                    )

                    # ----------------------------
                    # Channel
                    # ----------------------------

                    channel = guild.get_channel(
                        discord_id
                    )

                    if channel:

                        return (
                            f"{channel.mention} "
                            f"`({channel.name})`"
                        )

                    # ----------------------------
                    # Role
                    # ----------------------------

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

            return (
                f"`{value}`"
            )

        # --------------------------------------------
        # Normal string
        # --------------------------------------------

        if len(value) > 900:

            value = (
                value[:900]
                + "..."
            )

        return (
            f"`{value}`"
        )

    # --------------------------------------------------------
    # List
    # --------------------------------------------------------

    if isinstance(
        value,
        list
    ):

        if not value:

            return "`[]`"

        output = []

        for item in value[:30]:

            formatted = format_value(
                item,
                guild,
                depth + 1
            )

            output.append(
                f"• {formatted}"
            )

        if len(value) > 30:

            output.append(
                f"• `... "
                f"{len(value) - 30} more items`"
            )

        return "\n".join(
            output
        )

    # --------------------------------------------------------
    # Dictionary
    # --------------------------------------------------------

    if isinstance(
        value,
        dict
    ):

        if not value:

            return "`{}`"

        output = []

        for key, item in value.items():

            key_string = str(
                key
            )

            formatted = format_value(
                item,
                guild,
                depth + 1
            )

            output.append(
                f"**{key_string}:** {formatted}"
            )

        return "\n".join(
            output
        )

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    return (
        f"`{str(value)}`"
    )


# ============================================================
# CHECK SAVED DISCORD OBJECTS
# ============================================================

def check_discord_objects(
    data,
    guild
):
    """
    Recursively inspect JSON for common Discord IDs.

    Returns:

        existing
        missing
    """

    existing = []
    missing = []

    # --------------------------------------------------------
    # Recursive scanner
    # --------------------------------------------------------

    def scan(
        value,
        key_name=""
    ):

        # --------------------------------------------
        # Dictionary
        # --------------------------------------------

        if isinstance(
            value,
            dict
        ):

            for key, child in value.items():

                scan(
                    child,
                    str(key)
                )

            return

        # --------------------------------------------
        # List
        # --------------------------------------------

        if isinstance(
            value,
            list
        ):

            for child in value:

                scan(
                    child,
                    key_name
                )

            return

        # --------------------------------------------
        # Only inspect IDs
        # --------------------------------------------

        if not isinstance(
            value,
            (str, int)
        ):

            return

        try:

            value_string = str(
                value
            )

            if not (
                value_string.isdigit()
                and len(value_string) >= 15
            ):

                return

            key_lower = (
                key_name
                .lower()
            )

            # ----------------------------------------
            # Channel ID
            # ----------------------------------------

            if (
                "channel" in key_lower
                and "id" in key_lower
            ):

                channel = guild.get_channel(
                    int(value_string)
                )

                if channel:

                    existing.append(
                        f"#{channel.name}"
                    )

                else:

                    missing.append(
                        f"channel `{value_string}`"
                    )

            # ----------------------------------------
            # Role ID
            # ----------------------------------------

            elif (
                "role" in key_lower
                and "id" in key_lower
            ):

                role = guild.get_role(
                    int(value_string)
                )

                if role:

                    existing.append(
                        f"@{role.name}"
                    )

                else:

                    missing.append(
                        f"role `{value_string}`"
                    )

            # ----------------------------------------
            # Category ID
            # ----------------------------------------

            elif (
                "category" in key_lower
                and "id" in key_lower
            ):

                category = guild.get_channel(
                    int(value_string)
                )

                if category:

                    existing.append(
                        f"category: {category.name}"
                    )

                else:

                    missing.append(
                        f"category `{value_string}`"
                    )

        except Exception:

            pass

    scan(
        data
    )

    return (
        list(dict.fromkeys(existing)),
        list(dict.fromkeys(missing))
    )


# ============================================================
# MASTER CONFIG COG
# ============================================================

class Refresh(
    commands.Cog
):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        print(
            "🔄 Master configuration system loaded."
        )

    # ========================================================
    # GET COMMANDS FOR COG
    # ========================================================

    def get_commands_for_cog(
        self,
        cog
    ):

        commands_found = []

        # ----------------------------------------------------
        # Slash commands
        # ----------------------------------------------------

        try:

            for command in (
                self.bot.tree.walk_commands()
            ):

                try:

                    binding = getattr(
                        command,
                        "binding",
                        None
                    )

                    if binding is cog:

                        commands_found.append(
                            f"/{command.qualified_name}"
                        )

                except Exception:

                    pass

        except Exception:

            pass

        # ----------------------------------------------------
        # Prefix commands
        # ----------------------------------------------------

        try:

            for command in self.bot.commands:

                try:

                    command_cog = getattr(
                        command,
                        "cog",
                        None
                    )

                    if command_cog is cog:

                        commands_found.append(
                            f"!{command.name}"
                        )

                except Exception:

                    pass

        except Exception:

            pass

        return sorted(
            set(commands_found)
        )

    # ========================================================
    # READ ALL CONFIG FILES
    # ========================================================

    def read_all_config_files(
        self,
        guild
    ):

        results = []

        files = find_config_files()

        for filepath in files:

            data, error = read_json_file(
                filepath
            )

            result = {

                "filename": filepath.name,

                "name": get_config_name(
                    filepath.name
                ),

                "path": str(
                    filepath
                ),

                "data": data,

                "error": error,

                "configured": False,

                "existing": [],

                "missing": []
            }

            # ------------------------------------------------
            # Error
            # ------------------------------------------------

            if error:

                results.append(
                    result
                )

                continue

            # ------------------------------------------------
            # Find guild configuration
            # ------------------------------------------------

            guild_data = find_guild_config(

                data,

                guild.id
            )

            if guild_data is not None:

                result[
                    "configured"
                ] = True

                result[
                    "guild_data"
                ] = guild_data

                existing, missing = (
                    check_discord_objects(
                        guild_data,
                        guild
                    )
                )

                result[
                    "existing"
                ] = existing

                result[
                    "missing"
                ] = missing

            else:

                # ------------------------------------------------
                # Global config
                # ------------------------------------------------

                result[
                    "global"
                ] = data

                # If it looks like a guild-keyed
                # configuration file, don't call it global.
                if isinstance(
                    data,
                    dict
                ):

                    guild_keys = [

                        str(key)

                        for key in data.keys()

                        if str(key).isdigit()
                        and len(str(key)) >= 15
                    ]

                    if guild_keys:

                        result[
                            "configured"
                        ] = False

            results.append(
                result
            )

        return results

    # ========================================================
    # TRY COG SETUP INFORMATION
    # ========================================================

    async def get_cog_runtime_info(
        self,
        cog,
        guild
    ):

        # ----------------------------------------------------
        # get_setup_info()
        # ----------------------------------------------------

        setup_info = getattr(
            cog,
            "get_setup_info",
            None
        )

        if callable(
            setup_info
        ):

            try:

                result = await setup_info(
                    guild
                )

                if isinstance(
                    result,
                    dict
                ):

                    return result

                return {

                    "status": "✅",

                    "message": str(
                        result
                    )
                }

            except TypeError:

                try:

                    result = await setup_info()

                    if isinstance(
                        result,
                        dict
                    ):

                        return result

                    return {

                        "status": "✅",

                        "message": str(
                            result
                        )
                    }

                except Exception as e:

                    return {

                        "status": "❌",

                        "message": (
                            f"{type(e).__name__}: "
                            f"{e}"
                        )
                    }

            except Exception as e:

                print(
                    f"❌ get_setup_info error "
                    f"in {type(cog).__name__}: {e}"
                )

                return {

                    "status": "❌",

                    "message": (
                        f"{type(e).__name__}: "
                        f"{e}"
                    )
                }

        # ----------------------------------------------------
        # refresh()
        # ----------------------------------------------------

        refresh_method = getattr(
            cog,
            "refresh",
            None
        )

        if callable(
            refresh_method
        ):

            try:

                result = await refresh_method()

                if isinstance(
                    result,
                    dict
                ):

                    return result

                return {

                    "status": "✅",

                    "message": (
                        str(result)
                        if result
                        else
                        "Refresh completed."
                    )
                }

            except Exception as e:

                print(
                    f"❌ refresh() error "
                    f"in {type(cog).__name__}: {e}"
                )

                return {

                    "status": "❌",

                    "message": (
                        f"{type(e).__name__}: "
                        f"{e}"
                    )
                }

        return None

    # ========================================================
    # BUILD FILE REPORT
    # ========================================================

    def build_file_report(
        self,
        result,
        guild
    ):

        filename = result[
            "filename"
        ]

        name = result[
            "name"
        ]

        lines = []

        lines.append(
            f"📦 **{name}**"
        )

        lines.append(
            f"📄 `{filename}`"
        )

        # ----------------------------------------------------
        # Error
        # ----------------------------------------------------

        if result[
            "error"
        ]:

            lines.append(
                "❌ **JSON Error**"
            )

            lines.append(
                f"`{result['error']}`"
            )

            return "\n".join(
                lines
            )

        # ----------------------------------------------------
        # Guild configured
        # ----------------------------------------------------

        if result[
            "configured"
        ]:

            lines.append(
                "🟢 **Configured for this server**"
            )

            guild_data = result.get(
                "guild_data",
                {}
            )

            formatted = format_value(
                guild_data,
                guild
            )

            if formatted:

                lines.append(
                    formatted
                )

            # --------------------------------------------
            # Existing Discord objects
            # --------------------------------------------

            existing = result.get(
                "existing",
                []
            )

            if existing:

                lines.append(
                    "✅ **Discord objects:**"
                )

                lines.append(
                    "\n".join(
                        f"• {item}"
                        for item in existing[:15]
                    )
                )

            # --------------------------------------------
            # Missing Discord objects
            # --------------------------------------------

            missing = result.get(
                "missing",
                []
            )

            if missing:

                lines.append(
                    "⚠️ **Missing Discord objects:**"
                )

                lines.append(
                    "\n".join(
                        f"• {item}"
                        for item in missing[:15]
                    )
                )

            return "\n".join(
                lines
            )

        # ----------------------------------------------------
        # Global configuration
        # ----------------------------------------------------

        data = result.get(
            "global"
        )

        if isinstance(
            data,
            dict
        ):

            # ------------------------------------------------
            # Check if this is a guild-based file
            # ------------------------------------------------

            guild_keys = [

                str(key)

                for key in data.keys()

                if str(key).isdigit()
                and len(str(key)) >= 15
            ]

            if guild_keys:

                lines.append(
                    "🟡 **No configuration "
                    "for this server**"
                )

                lines.append(
                    f"🌐 Servers saved in file: "
                    f"`{len(guild_keys)}`"
                )

            else:

                lines.append(
                    "🔵 **Global configuration**"
                )

                formatted = format_value(
                    data,
                    guild
                )

                if formatted:

                    lines.append(
                        formatted
                    )

        else:

            lines.append(
                "🟡 **No guild-specific "
                "configuration found**"
            )

        return "\n".join(
            lines
        )

    # ========================================================
    # /REFRESH
    # ========================================================

    @app_commands.command(

        name="refresh",

        description=(
            "Read and check all saved bot configurations."
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

        print("")
        print(
            "========================================"
        )

        print(
            "       MASTER CONFIG REFRESH"
        )

        print(
            "========================================"
        )

        # ====================================================
        # READ REAL JSON FILES
        # ====================================================

        config_results = (
            self.read_all_config_files(
                guild
            )
        )

        # ====================================================
        # CHECK LOADED COGS
        # ====================================================

        cog_results = []

        for cog_name, cog in (
            self.bot.cogs.items()
        ):

            # Don't display this Cog
            if cog is self:
                continue

            if cog_name == "Refresh":
                continue

            print(
                f"🔄 Checking Cog: {cog_name}"
            )

            runtime_info = (
                await self.get_cog_runtime_info(
                    cog,
                    guild
                )
            )

            commands_list = (
                self.get_commands_for_cog(
                    cog
                )
            )

            cog_results.append({

                "name": cog_name,

                "runtime": runtime_info,

                "commands": commands_list
            })

        # ====================================================
        # STATISTICS
        # ====================================================

        total_files = len(
            config_results
        )

        configured_files = sum(

            1

            for result in config_results

            if result[
                "configured"
            ]
        )

        error_files = sum(

            1

            for result in config_results

            if result[
                "error"
            ]
        )

        total_cogs = len(
            cog_results
        )

        total_commands = sum(

            len(
                result[
                    "commands"
                ]
            )

            for result in cog_results
        )

        # ====================================================
        # OVERVIEW EMBED
        # ====================================================

        overview = discord.Embed(

            title="🔄 Master Configuration Refresh",

            description=(

                f"**Server:** {guild.name}\n\n"

                "The bot has read the actual "
                "configuration files from disk.\n\n"

                "━━━━━━━━━━━━━━━━━━━━\n\n"

                f"📄 **JSON files found:** "
                f"`{total_files}`\n"

                f"🟢 **Guild configurations found:** "
                f"`{configured_files}`\n"

                f"❌ **JSON errors:** "
                f"`{error_files}`\n\n"

                f"📦 **Loaded Cogs:** "
                f"`{total_cogs}`\n"

                f"⚙️ **Commands detected:** "
                f"`{total_commands}`"
            ),

            color=(
                discord.Color.green()
                if error_files == 0
                else discord.Color.orange()
            ),

            timestamp=datetime.now(
                timezone.utc
            )
        )

        overview.set_footer(

            text=(
                f"Requested by "
                f"{interaction.user}"
            )
        )

        await interaction.followup.send(

            embed=overview,

            ephemeral=True
        )

        # ====================================================
        # SEND JSON CONFIGURATION REPORT
        # ====================================================

        if config_results:

            current_text = (
                "📂 **SAVED JSON CONFIGURATIONS**\n\n"
            )

            page = 1

            for result in config_results:

                report = (
                    self.build_file_report(
                        result,
                        guild
                    )
                )

                addition = (
                    "\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    + report
                )

                if (
                    len(current_text)
                    + len(addition)
                    > 3900
                ):

                    embed = discord.Embed(

                        title=(
                            "📂 Saved Configuration"
                            f" — Page {page}"
                        ),

                        description=current_text,

                        color=discord.Color.blurple()
                    )

                    await interaction.followup.send(

                        embed=embed,

                        ephemeral=True
                    )

                    page += 1

                    current_text = report

                else:

                    current_text += addition

            if current_text:

                embed = discord.Embed(

                    title=(
                        "📂 Saved Configuration"
                        f" — Page {page}"
                    ),

                    description=current_text,

                    color=discord.Color.blurple()
                )

                await interaction.followup.send(

                    embed=embed,

                    ephemeral=True
                )

        # ====================================================
        # COG STATUS
        # ====================================================

        current_text = (
            "📦 **LOADED COG STATUS**\n\n"
        )

        page = 1

        for result in cog_results:

            cog_name = result[
                "name"
            ]

            runtime = result[
                "runtime"
            ]

            commands_list = result[
                "commands"
            ]

            # ------------------------------------------------
            # Runtime status
            # ------------------------------------------------

            if runtime:

                status = runtime.get(
                    "status",
                    "ℹ️"
                )

                message = runtime.get(
                    "message",
                    "No details."
                )

            else:

                status = "📄"

                message = (
                    "Configuration is read "
                    "directly from its JSON file."
                )

            # ------------------------------------------------
            # Commands
            # ------------------------------------------------

            if commands_list:

                command_text = "\n".join(

                    f"`{command}`"

                    for command in commands_list[:20]
                )

                if len(
                    commands_list
                ) > 20:

                    command_text += (
                        "\n`... more commands ...`"
                    )

            else:

                command_text = (
                    "No commands detected."
                )

            field = (

                f"{status} {message}\n\n"

                f"⚙️ **Commands:**\n"
                f"{command_text}"
            )

            addition = (

                "━━━━━━━━━━━━━━━━━━━━\n\n"

                f"📦 **{cog_name}**\n"

                f"{field}\n\n"
            )

            if (
                len(current_text)
                + len(addition)
                > 3900
            ):

                embed = discord.Embed(

                    title=(
                        "📦 Loaded Cogs"
                        f" — Page {page}"
                    ),

                    description=current_text,

                    color=discord.Color.blurple()
                )

                await interaction.followup.send(

                    embed=embed,

                    ephemeral=True
                )

                page += 1

                current_text = addition

            else:

                current_text += addition

        if current_text.strip():

            embed = discord.Embed(

                title=(
                    "📦 Loaded Cogs"
                    f" — Page {page}"
                ),

                description=current_text,

                color=discord.Color.blurple()
            )

            await interaction.followup.send(

                embed=embed,

                ephemeral=True
            )

        # ====================================================
        # FINISH
        # ====================================================

        print(
            "========================================"
        )

        print(
            "       MASTER REFRESH COMPLETE"
        )

        print(
            "========================================"
        )

    # ========================================================
    # /CONFIGFILES
    # ========================================================

    @app_commands.command(

        name="configfiles",

        description=(
            "Show all JSON configuration files found by the bot."
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

        files = find_config_files()

        if not files:

            await interaction.followup.send(

                "❌ No JSON configuration files were found.",

                ephemeral=True
            )

            return

        lines = []

        for filepath in files:

            lines.append(
                f"📄 `{filepath.name}`"
            )

        text = "\n".join(
            lines
        )

        if len(text) > 3900:

            text = (
                text[:3900]
                + "\n..."
            )

        embed = discord.Embed(

            title="📂 Bot Configuration Files",

            description=text,

            color=discord.Color.blurple()
        )

        embed.set_footer(

            text=(
                f"{len(files)} JSON file(s) detected."
            )
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
            "Read one JSON configuration file."
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
        # Security
        # ----------------------------------------------------

        filename = os.path.basename(
            filename
        )

        filepath = (
            CONFIG_ROOT
            / filename
        )

        # ----------------------------------------------------
        # File exists?
        # ----------------------------------------------------

        if not filepath.exists():

            # Check Cogs folder
            cogs_filepath = (
                CONFIG_ROOT
                / "cogs"
                / filename
            )

            if cogs_filepath.exists():

                filepath = cogs_filepath

            else:

                await interaction.followup.send(

                    "❌ Configuration file not found:\n\n"
                    f"`{filename}`",

                    ephemeral=True
                )

                return

        # ----------------------------------------------------
        # Read
        # ----------------------------------------------------

        data, error = read_json_file(
            filepath
        )

        if error:

            await interaction.followup.send(

                f"❌ Could not read `{filename}`.\n\n"
                f"`{error}`",

                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # Find guild configuration
        # ----------------------------------------------------

        guild_data = find_guild_config(

            data,

            interaction.guild.id
        )

        # ----------------------------------------------------
        # Use guild data when available
        # ----------------------------------------------------

        if guild_data is not None:

            display_data = guild_data

            title = (
                f"📄 {filename} "
                "— This Server"
            )

        else:

            display_data = data

            title = (
                f"📄 {filename}"
            )

        # ----------------------------------------------------
        # Format
        # ----------------------------------------------------

        text = format_value(

            display_data,

            interaction.guild
        )

        if not text:

            text = "`Empty configuration`"

        # ----------------------------------------------------
        # Split if needed
        # ----------------------------------------------------

        chunks = []

        while len(text) > 3900:

            chunk = text[:3900]

            split_position = chunk.rfind(
                "\n"
            )

            if split_position > 1000:

                chunk = chunk[
                    :split_position
                ]

            chunks.append(
                chunk
            )

            text = text[
                len(chunk):
            ]

        if text:

            chunks.append(
                text
            )

        # ----------------------------------------------------
        # Send
        # ----------------------------------------------------

        for index, chunk in enumerate(
            chunks
        ):

            embed = discord.Embed(

                title=(
                    title
                    if index == 0
                    else
                    f"{title} "
                    f"— Page {index + 1}"
                ),

                description=chunk,

                color=discord.Color.blurple()
            )

            await interaction.followup.send(

                embed=embed,

                ephemeral=True
            )

    # ========================================================
    # REFRESH ERROR
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

            traceback.print_exc()

            message = (

                "❌ An error occurred while "
                "refreshing the configuration.\n\n"

                f"`{type(error).__name__}: {error}`"
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

    # ========================================================
    # CONFIGFILES ERROR
    # ========================================================

    @configfiles.error
    async def configfiles_error(
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
                "permission to use `/configfiles`."
            )

        else:

            traceback.print_exc()

            message = (
                "❌ Configuration file error."
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

async def setup(
    bot
):

    await bot.add_cog(
        Refresh(bot)
    )

    print(
        "✅ Master Config Cog ready."
    )

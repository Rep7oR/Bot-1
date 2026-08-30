import discord
from discord.ext import commands, tasks
from discord import app_commands

import os
import json
import asyncio
import shutil
import traceback
from datetime import datetime, timezone


# ============================================================
# MASTER CONFIGURATION SYSTEM
# ============================================================
#
# This system DOES NOT modify your existing Cogs.
#
# It:
#
# 1. Reads the existing JSON configuration files.
# 2. Creates a master backup.
# 3. Restores missing JSON files after a restart/deployment.
# 4. Automatically backs up configuration periodically.
# 5. Provides /refresh for administrators.
# 6. Shows configuration for all Cogs.
# 7. Shows all commands detected in every Cog.
#
# ============================================================


# ============================================================
# PERSISTENT STORAGE
# ============================================================
#
# LOCAL:
#     data/
#
# RENDER:
#     Set environment variable:
#
#     BOT_PERSIST_DIR=/data
#
# Your Render Persistent Disk should be mounted at:
#
#     /data
#
# ============================================================

PERSISTENT_DIR = os.getenv(
    "BOT_PERSIST_DIR",
    "data"
)


os.makedirs(
    PERSISTENT_DIR,
    exist_ok=True
)


MASTER_FILE = os.path.join(
    PERSISTENT_DIR,
    "master_config.json"
)


# ============================================================
# EXISTING COG CONFIGURATION FILES
# ============================================================

CONFIG_FILES = {

    # --------------------------------------------------------
    # AI
    # --------------------------------------------------------

    "Auto_Reply": "ai_chat_config.json",

    # --------------------------------------------------------
    # CLAN
    # --------------------------------------------------------

    "Clan": "clan_data.json",

    # --------------------------------------------------------
    # COMMAND SYSTEM
    # --------------------------------------------------------

    "cmd": "cmd_config.json",

    # --------------------------------------------------------
    # SUPPORT / HELP
    # --------------------------------------------------------

    "help_system": "help_config.json",

    # --------------------------------------------------------
    # MODERATOR
    # --------------------------------------------------------

    "moderator_online": "moderator_online.json",

    "moderator_stats": "moderator_stats.json",

    # --------------------------------------------------------
    # MUSIC
    # --------------------------------------------------------

    "music_system": "music_config.json",

    # --------------------------------------------------------
    # VOICE
    # --------------------------------------------------------

    "voice": "voice_config.json",

    # --------------------------------------------------------
    # WELCOME
    # --------------------------------------------------------

    "welcome": "welcome_config.json",

    # --------------------------------------------------------
    # YOUTUBE
    # --------------------------------------------------------

    "youtube": "youtube_config.json",
}


# ============================================================
# COGS WITHOUT CONFIGURATION FILES
# ============================================================

NO_CONFIG_COGS = {

    "Announce",

    "Invite",

    "DMCommands",

    "RoleManager",

    "MissingSlash",

    "SlashChecker",

}


# ============================================================
# LOCK
# ============================================================

config_lock = asyncio.Lock()


# ============================================================
# JSON HELPERS
# ============================================================

def read_json(
    path
):

    if not os.path.exists(path):

        return None

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as e:

        print(
            f"❌ Failed reading {path}: {e}"
        )

        return None


# ============================================================

def write_json(
    path,
    data
):

    try:

        directory = os.path.dirname(path)

        if directory:

            os.makedirs(
                directory,
                exist_ok=True
            )

        temporary = (
            path + ".tmp"
        )

        with open(
            temporary,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        os.replace(
            temporary,
            path
        )

        return True

    except Exception as e:

        print(
            f"❌ Failed writing {path}: {e}"
        )

        return False


# ============================================================
# MASTER FILE
# ============================================================

def load_master():

    if not os.path.exists(
        MASTER_FILE
    ):

        return {
            "version": 1,
            "last_backup": None,
            "files": {}
        }

    data = read_json(
        MASTER_FILE
    )

    if not isinstance(
        data,
        dict
    ):

        return {
            "version": 1,
            "last_backup": None,
            "files": {}
        }

    data.setdefault(
        "version",
        1
    )

    data.setdefault(
        "last_backup",
        None
    )

    data.setdefault(
        "files",
        {}
    )

    return data


master_data = load_master()


# ============================================================
# GET CURRENT WORKING FILE
# ============================================================

def config_path(
    filename
):

    return os.path.join(
        os.getcwd(),
        filename
    )


# ============================================================
# BACKUP EXISTING CONFIGURATION
# ============================================================

def backup_all_configs():

    global master_data

    changed = False

    for cog_name, filename in (
        CONFIG_FILES.items()
    ):

        path = config_path(
            filename
        )

        # ----------------------------------------------------
        # File exists
        # ----------------------------------------------------

        if os.path.exists(path):

            data = read_json(
                path
            )

            if data is not None:

                master_data[
                    "files"
                ][filename] = {

                    "cog": cog_name,

                    "updated_at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),

                    "data": data
                }

                changed = True

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    master_data[
        "last_backup"
    ] = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    # --------------------------------------------------------
    # Save master file
    # --------------------------------------------------------

    if changed:

        success = write_json(
            MASTER_FILE,
            master_data
        )

        if success:

            print(
                "💾 Master configuration backup updated."
            )

    return changed


# ============================================================
# RESTORE CONFIGURATION FILES
# ============================================================

def restore_all_configs():

    global master_data

    restored = []

    files = master_data.get(
        "files",
        {}
    )

    for cog_name, filename in (
        CONFIG_FILES.items()
    ):

        target = config_path(
            filename
        )

        # ----------------------------------------------------
        # If current file already exists,
        # do NOT overwrite it.
        # ----------------------------------------------------

        if os.path.exists(target):

            continue

        # ----------------------------------------------------
        # Get backup
        # ----------------------------------------------------

        backup = files.get(
            filename
        )

        if not backup:

            continue

        data = backup.get(
            "data"
        )

        if data is None:

            continue

        # ----------------------------------------------------
        # Restore
        # ----------------------------------------------------

        if write_json(
            target,
            data
        ):

            restored.append(
                filename
            )

            print(
                f"♻️ Restored {filename}"
            )

    return restored


# ============================================================
# CHECK CONFIGURATION STATUS
# ============================================================

def configuration_status(
    filename
):

    path = config_path(
        filename
    )

    if os.path.exists(path):

        data = read_json(
            path
        )

        if data is None:

            return (
                "❌",
                "Configuration file exists but could not be read."
            )

        if isinstance(
            data,
            dict
        ):

            if not data:

                return (
                    "⚪",
                    "Configuration file is empty."
                )

            return (
                "✅",
                "Configuration saved."
            )

        return (
            "✅",
            "Configuration saved."
        )

    # --------------------------------------------------------
    # Check backup
    # --------------------------------------------------------

    if filename in master_data.get(
        "files",
        {}
    ):

        return (
            "♻️",
            "Saved backup exists; file will be restored."
        )

    return (
        "⚪",
        "Not configured."
    )


# ============================================================
# GET GUILD CONFIGURATION
# ============================================================

def extract_guild_config(
    data,
    guild_id
):

    if not isinstance(
        data,
        dict
    ):

        return None

    guild_id = str(
        guild_id
    )

    # --------------------------------------------------------
    # Normal structure:
    #
    # {
    #     "123456": {...}
    # }
    # --------------------------------------------------------

    if guild_id in data:

        return data[guild_id]

    # --------------------------------------------------------
    # Clan structure:
    #
    # {
    #     "guilds": {
    #         "123456": {...}
    #     }
    # }
    # --------------------------------------------------------

    guilds = data.get(
        "guilds"
    )

    if isinstance(
        guilds,
        dict
    ):

        if guild_id in guilds:

            return guilds[guild_id]

    return None


# ============================================================
# CHANNEL RESOLVER
# ============================================================

def resolve_channel(
    guild,
    channel_id
):

    if channel_id is None:

        return None

    try:

        return guild.get_channel(
            int(channel_id)
        )

    except Exception:

        return None


# ============================================================
# ROLE RESOLVER
# ============================================================

def resolve_role(
    guild,
    role_id
):

    if role_id is None:

        return None

    try:

        return guild.get_role(
            int(role_id)
        )

    except Exception:

        return None


# ============================================================
# CATEGORY RESOLVER
# ============================================================

def resolve_category(
    guild,
    category_id
):

    if category_id is None:

        return None

    try:

        channel = guild.get_channel(
            int(category_id)
        )

        if isinstance(
            channel,
            discord.CategoryChannel
        ):

            return channel

    except Exception:

        pass

    return None


# ============================================================
# FORMAT VALUE
# ============================================================

def format_value(
    guild,
    key,
    value
):

    key_lower = str(
        key
    ).lower()

    # --------------------------------------------------------
    # None
    # --------------------------------------------------------

    if value is None:

        return "Not configured"

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
            else "❌ Disabled"
        )

    # --------------------------------------------------------
    # Channel ID
    # --------------------------------------------------------

    if (
        "channel" in key_lower
        and "id" in key_lower
    ):

        channel = resolve_channel(
            guild,
            value
        )

        if channel:

            return channel.mention

        return (
            f"⚠️ Missing channel "
            f"`{value}`"
        )

    # --------------------------------------------------------
    # Category ID
    # --------------------------------------------------------

    if (
        "category" in key_lower
        and "id" in key_lower
    ):

        category = resolve_category(
            guild,
            value
        )

        if category:

            return f"`{category.name}`"

        return (
            f"⚠️ Missing category "
            f"`{value}`"
        )

    # --------------------------------------------------------
    # Role ID
    # --------------------------------------------------------

    if (
        "role" in key_lower
        and "id" in key_lower
    ):

        role = resolve_role(
            guild,
            value
        )

        if role:

            return role.mention

        return (
            f"⚠️ Missing role "
            f"`{value}`"
        )

    # --------------------------------------------------------
    # User/member ID
    # --------------------------------------------------------

    if (
        key_lower.endswith(
            "user_id"
        )
        or key_lower.endswith(
            "member_id"
        )
        or key_lower.endswith(
            "owner_id"
        )
    ):

        try:

            member = guild.get_member(
                int(value)
            )

            if member:

                return member.mention

        except Exception:

            pass

        return f"`{value}`"

    # --------------------------------------------------------
    # Large dictionaries
    # --------------------------------------------------------

    if isinstance(
        value,
        dict
    ):

        return "{...}"

    # --------------------------------------------------------
    # Lists
    # --------------------------------------------------------

    if isinstance(
        value,
        list
    ):

        if not value:

            return "None"

        text = ", ".join(
            str(item)
            for item in value[:10]
        )

        if len(value) > 10:

            text += (
                f" + {len(value) - 10} more"
            )

        return text

    # --------------------------------------------------------
    # Normal
    # --------------------------------------------------------

    return str(
        value
    )


# ============================================================
# FLATTEN CONFIG
# ============================================================

def flatten_config(
    guild,
    data,
    prefix=""
):

    lines = []

    if not isinstance(
        data,
        dict
    ):

        return lines

    for key, value in data.items():

        key_text = str(
            key
        ).replace(
            "_",
            " "
        ).title()

        current_key = (
            f"{prefix}.{key}"
            if prefix
            else str(key)
        )

        # ----------------------------------------------------
        # Nested dict
        # ----------------------------------------------------

        if isinstance(
            value,
            dict
        ):

            # Don't dump huge runtime collections
            if key in {
                "pending",
                "clans",
                "tickets",
                "members",
                "requests",
                "applications",
                "stats",
                "users"
            }:

                lines.append(
                    f"**{key_text}:** "
                    f"`{len(value)}` entries"
                )

                continue

            nested = flatten_config(
                guild,
                value,
                current_key
            )

            if nested:

                lines.extend(
                    nested
                )

            else:

                lines.append(
                    f"**{key_text}:** `{...}`"
                )

            continue

        # ----------------------------------------------------
        # Lists
        # ----------------------------------------------------

        if isinstance(
            value,
            list
        ):

            formatted = format_value(
                guild,
                key,
                value
            )

            lines.append(
                f"**{key_text}:** "
                f"{formatted}"
            )

            continue

        # ----------------------------------------------------
        # Normal value
        # ----------------------------------------------------

        formatted = format_value(
            guild,
            key,
            value
        )

        lines.append(
            f"**{key_text}:** "
            f"{formatted}"
        )

    return lines


# ============================================================
# COMMAND DISCOVERY
# ============================================================

def command_belongs_to_cog(
    command,
    cog
):

    try:

        binding = getattr(
            command,
            "binding",
            None
        )

        if binding is cog:

            return True

    except Exception:

        pass

    return False


# ============================================================

def get_cog_commands(
    bot,
    cog
):

    commands_found = []

    # --------------------------------------------------------
    # Slash commands
    # --------------------------------------------------------

    try:

        for command in bot.tree.walk_commands():

            if command_belongs_to_cog(
                command,
                cog
            ):

                commands_found.append(
                    "/" + command.qualified_name
                )

    except Exception:

        pass

    # --------------------------------------------------------
    # Prefix commands
    # --------------------------------------------------------

    try:

        for command in bot.commands:

            try:

                command_cog = getattr(
                    command,
                    "cog",
                    None
                )

                if command_cog is cog:

                    commands_found.append(
                        "!" + command.name
                    )

            except Exception:

                pass

    except Exception:

        pass

    return sorted(
        set(commands_found)
    )


# ============================================================
# MASTER CONFIG COG
# ============================================================

class MasterConfig(
    commands.Cog
):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        print(
            "=========================================="
        )

        print(
            "🧠 MASTER CONFIG SYSTEM"
        )

        print(
            "=========================================="
        )

        print(
            f"📁 Persistent directory: "
            f"{PERSISTENT_DIR}"
        )

        print(
            f"📄 Master file: "
            f"{MASTER_FILE}"
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Restore BEFORE other cogs use their JSON files.
        #
        # This works when masterconfig is loaded first.
        # ----------------------------------------------------

        restored = restore_all_configs()

        if restored:

            print(
                "♻️ Restored configuration files:"
            )

            for filename in restored:

                print(
                    f"   └── {filename}"
                )

        # ----------------------------------------------------
        # Start automatic backup
        # ----------------------------------------------------

        self.backup_loop.start()

        print(
            "✅ Master Config System loaded."
        )

    # ========================================================
    # UNLOAD
    # ========================================================

    def cog_unload(
        self
    ):

        self.backup_loop.cancel()

    # ========================================================
    # BACKUP LOOP
    # ========================================================

    @tasks.loop(
        seconds=15
    )
    async def backup_loop(
        self
    ):

        try:

            async with config_lock:

                backup_all_configs()

        except Exception as e:

            print(
                f"❌ Master backup error: {e}"
            )

    # ========================================================
    # LOOP READY
    # ========================================================

    @backup_loop.before_loop
    async def before_backup(
        self
    ):

        await self.bot.wait_until_ready()

    # ========================================================
    # MANUAL BACKUP
    # ========================================================

    async def backup_now(
        self
    ):

        async with config_lock:

            return backup_all_configs()

    # ========================================================
    # BUILD COG REPORT
    # ========================================================

    def build_cog_report(
        self,
        guild,
        cog_name,
        cog
    ):

        # ----------------------------------------------------
        # Commands
        # ----------------------------------------------------

        commands_found = get_cog_commands(
            self.bot,
            cog
        )

        # ----------------------------------------------------
        # Configuration file
        # ----------------------------------------------------

        filename = CONFIG_FILES.get(
            cog_name
        )

        # ----------------------------------------------------
        # Some class names may differ
        # ----------------------------------------------------

        if filename is None:

            aliases = {

                "AIChat": "ai_chat_config.json",

                "AutoReply": "ai_chat_config.json",

                "VoiceSystem": "voice_config.json",

                "Welcome": "welcome_config.json",

                "YouTubeSystem": "youtube_config.json",

                "ModeratorOnline": "moderator_online.json",

                "ModeratorStats": "moderator_stats.json",

                "MusicSystem": "music_config.json",

                "HelpSystem": "help_config.json",

                "ClanSystem": "clan_data.json",

                "CommandSystem": "cmd_config.json",

            }

            filename = aliases.get(
                cog_name
            )

        # ----------------------------------------------------
        # No configuration system
        # ----------------------------------------------------

        if filename is None:

            if cog_name in NO_CONFIG_COGS:

                return {

                    "status": "ℹ️",

                    "message": (
                        "Command-only Cog. "
                        "No persistent setup required."
                    ),

                    "config": None,

                    "commands": commands_found,

                    "filename": None
                }

            return {

                "status": "ℹ️",

                "message": (
                    "No configuration file "
                    "registered for this Cog."
                ),

                "config": None,

                "commands": commands_found,

                "filename": None
            }

        # ----------------------------------------------------
        # Read file
        # ----------------------------------------------------

        path = config_path(
            filename
        )

        data = read_json(
            path
        )

        # ----------------------------------------------------
        # File doesn't exist
        # ----------------------------------------------------

        if data is None:

            backup = master_data.get(
                "files",
                {}
            ).get(
                filename
            )

            if backup:

                data = backup.get(
                    "data"
                )

                status = "♻️"

                message = (
                    "Saved backup available."
                )

            else:

                status = "⚪"

                message = (
                    "Not configured."
                )

                data = None

        else:

            status = "✅"

            message = (
                "Configuration file found."
            )

        # ----------------------------------------------------
        # Extract this guild
        # ----------------------------------------------------

        guild_config = (
            extract_guild_config(
                data,
                guild.id
            )
            if data is not None
            else None
        )

        # ----------------------------------------------------
        # If configuration exists for this guild
        # ----------------------------------------------------

        if guild_config is not None:

            if isinstance(
                guild_config,
                dict
            ):

                if not guild_config:

                    status = "⚪"

                    message = (
                        "Guild configuration is empty."
                    )

            config_to_show = (
                guild_config
            )

        else:

            config_to_show = None

            if data is not None:

                status = "⚪"

                message = (
                    "File exists, but this "
                    "server has no saved setup."
                )

        return {

            "status": status,

            "message": message,

            "config": config_to_show,

            "commands": commands_found,

            "filename": filename
        }

    # ========================================================
    # BUILD ALL REPORTS
    # ========================================================

    def build_reports(
        self,
        guild
    ):

        reports = []

        for cog_name, cog in (
            self.bot.cogs.items()
        ):

            # Don't report ourselves
            if isinstance(
                cog,
                MasterConfig
            ):

                continue

            try:

                report = self.build_cog_report(
                    guild,
                    cog_name,
                    cog
                )

                reports.append(
                    (
                        cog_name,
                        report
                    )
                )

            except Exception as e:

                traceback.print_exc()

                reports.append(
                    (
                        cog_name,
                        {
                            "status": "❌",
                            "message": (
                                f"{type(e).__name__}: {e}"
                            ),
                            "config": None,
                            "commands": [],
                            "filename": None
                        }
                    )
                )

        return reports

    # ========================================================
    # /REFRESH
    # ========================================================

    @app_commands.command(
        name="refresh",
        description=(
            "Check all bot systems and show saved configuration."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def refresh(
        self,
        interaction: discord.Interaction
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        guild = interaction.guild

        # ----------------------------------------------------
        # First backup current configuration
        # ----------------------------------------------------

        try:

            await self.backup_now()

        except Exception as e:

            print(
                f"❌ Backup failed: {e}"
            )

        # ----------------------------------------------------
        # Reports
        # ----------------------------------------------------

        reports = self.build_reports(
            guild
        )

        # ----------------------------------------------------
        # Statistics
        # ----------------------------------------------------

        configured = 0
        warnings = 0
        errors = 0
        not_configured = 0
        info_only = 0
        command_count = 0

        for _, report in reports:

            status = report.get(
                "status"
            )

            if status == "✅":

                configured += 1

            elif status == "⚠️":

                warnings += 1

            elif status == "❌":

                errors += 1

            elif status == "⚪":

                not_configured += 1

            else:

                info_only += 1

            command_count += len(
                report.get(
                    "commands",
                    []
                )
            )

        # ----------------------------------------------------
        # Build embeds
        # ----------------------------------------------------

        embeds = []

        current = discord.Embed(

            title="🔄 BOT CONFIGURATION",

            description=(

                f"Server: **{guild.name}**\n\n"

                "Every loaded Cog was checked "
                "against its existing configuration."
            ),

            color=discord.Color.blurple()
        )

        field_count = 0

        for cog_name, report in reports:

            status = report.get(
                "status",
                "⚪"
            )

            message = report.get(
                "message",
                "No information."
            )

            config = report.get(
                "config"
            )

            commands_found = report.get(
                "commands",
                []
            )

            filename = report.get(
                "filename"
            )

            # ------------------------------------------------
            # Setup text
            # ------------------------------------------------

            if config is not None:

                config_lines = (
                    flatten_config(
                        guild,
                        config
                    )
                )

                if config_lines:

                    setup_text = (
                        "\n".join(
                            config_lines[:18]
                        )
                    )

                    if len(
                        config_lines
                    ) > 18:

                        setup_text += (
                            "\n..."
                        )

                else:

                    setup_text = (
                        "Configuration exists."
                    )

            else:

                setup_text = (
                    "No guild-specific configuration."
                )

            # ------------------------------------------------
            # File
            # ------------------------------------------------

            if filename:

                file_text = (
                    f"📄 `{filename}`"
                )

            else:

                file_text = ""

            # ------------------------------------------------
            # Commands
            # ------------------------------------------------

            if commands_found:

                command_text = (
                    " ".join(
                        f"`{command}`"
                        for command in commands_found
                    )
                )

                if len(
                    command_text
                ) > 500:

                    command_text = (
                        command_text[:500]
                        + " ..."
                    )

            else:

                command_text = (
                    "No registered commands."
                )

            # ------------------------------------------------
            # Complete field
            # ------------------------------------------------

            value = (

                f"{status} **{message}**\n"

                f"{file_text}\n\n"

                f"⚙️ **Setup:**\n"
                f"{setup_text}\n\n"

                f"🛠️ **Commands:**\n"
                f"{command_text}"
            )

            # ------------------------------------------------
            # Discord max field value
            # ------------------------------------------------

            if len(
                value
            ) > 1024:

                value = (
                    value[:1000]
                    + "\n..."
                )

            current.add_field(

                name=(
                    f"📦 {cog_name}"
                ),

                value=value,

                inline=False
            )

            field_count += 1

            # ------------------------------------------------
            # Keep under Discord field limit
            # ------------------------------------------------

            if field_count >= 20:

                embeds.append(
                    current
                )

                current = discord.Embed(

                    title=(
                        "🔄 BOT CONFIGURATION "
                        "— CONTINUED"
                    ),

                    color=discord.Color.blurple()
                )

                field_count = 0

        # ----------------------------------------------------
        # Add final embed
        # ----------------------------------------------------

        if field_count:

            embeds.append(
                current
            )

        # ====================================================
        # SUMMARY
        # ====================================================

        summary = discord.Embed(

            title="📊 REFRESH SUMMARY",

            description=(

                f"📦 **Cogs checked:** "
                f"`{len(reports)}`\n\n"

                f"✅ **Configured:** "
                f"`{configured}`\n"

                f"⚠️ **Warnings:** "
                f"`{warnings}`\n"

                f"❌ **Errors:** "
                f"`{errors}`\n"

                f"⚪ **Not configured:** "
                f"`{not_configured}`\n"

                f"ℹ️ **Command-only:** "
                f"`{info_only}`\n\n"

                f"⚙️ **Commands detected:** "
                f"`{command_count}`\n\n"

                "💾 **Configuration backup:** "
                "`Updated`"
            ),

            color=(
                discord.Color.green()
                if errors == 0
                else discord.Color.red()
            )
        )

        summary.set_footer(
            text=(
                f"Requested by "
                f"{interaction.user}"
            )
        )

        # ----------------------------------------------------
        # Send report
        # ----------------------------------------------------

        for embed in embeds:

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

        await interaction.followup.send(
            embed=summary,
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
                "❌ You need Administrator "
                "permission to use `/refresh`."
            )

        else:

            traceback.print_exc()

            message = (
                "❌ `/refresh` failed:\n"
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


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot
):

    await bot.add_cog(
        MasterConfig(bot)
    )

    print(
        "✅ Master Config Cog ready."
    )

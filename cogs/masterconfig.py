# ============================================================
# MASTER CONFIGURATION SYSTEM
# ============================================================
#
# PURPOSE:
#
# 1. Master Config loads FIRST.
# 2. Restores all saved JSON configuration files.
# 3. Other Cogs are loaded AFTER restoration.
# 4. Configuration is stored on Render Persistent Disk.
# 5. Existing JSON files are automatically discovered.
# 6. New JSON files can be detected automatically.
# 7. /refresh shows all Cogs, configurations and commands.
# 8. Configuration is backed up every 15 seconds.
#
# ============================================================

import discord
from discord.ext import commands, tasks
from discord import app_commands

import os
import json
import asyncio
import traceback
from datetime import datetime, timezone


# ============================================================
# SETTINGS
# ============================================================

# Render:
#
# BOT_PERSIST_DIR=/data
#
# Local:
#
# BOT_PERSIST_DIR=data
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
# CONFIGURATION FILES
# ============================================================
#
# These are known configuration files.
#
# The system will ALSO automatically discover other
# JSON configuration files in the project root.
#
# ============================================================

CONFIG_FILES = {

    "Auto_Reply": "ai_chat_config.json",

    "Clan": "clan_data.json",

    "cmd": "cmd_config.json",

    "help_system": "help_config.json",

    "moderator_online": "moderator_online.json",

    "moderator_stats": "moderator_stats.json",

    "music_system": "music_config.json",

    "voice": "voice_config.json",

    "welcome": "welcome_config.json",

    "youtube": "youtube_config.json",

    "rules": "rules_config.json",
}


# ============================================================
# COGS WITHOUT JSON CONFIGURATION
# ============================================================

NO_CONFIG_COGS = {

    "Announce",
    "Invite",
    "DMCommands",
    "RoleManager",
    "MissingSlash",
    "SlashChecker",
    "MasterConfig",
}


# ============================================================
# LOCK
# ============================================================

config_lock = asyncio.Lock()


# ============================================================
# TIME
# ============================================================

def utc_now():

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# JSON READ
# ============================================================

def read_json(path):

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
# JSON WRITE
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

def empty_master():

    return {

        "version": 2,

        "created_at": utc_now(),

        "last_backup": None,

        "files": {}

    }


def load_master():

    if not os.path.exists(
        MASTER_FILE
    ):

        return empty_master()

    data = read_json(
        MASTER_FILE
    )

    if not isinstance(
        data,
        dict
    ):

        return empty_master()

    data.setdefault(
        "version",
        2
    )

    data.setdefault(
        "created_at",
        utc_now()
    )

    data.setdefault(
        "last_backup",
        None
    )

    data.setdefault(
        "files",
        {}
    )

    if not isinstance(
        data["files"],
        dict
    ):

        data["files"] = {}

    return data


master_data = load_master()


# ============================================================
# FILE PATH
# ============================================================

def config_path(
    filename
):

    return os.path.join(
        os.getcwd(),
        filename
    )


# ============================================================
# PERSISTENT BACKUP PATH
# ============================================================

def persistent_config_path(
    filename
):

    return os.path.join(
        PERSISTENT_DIR,
        "configs",
        filename
    )


# ============================================================
# AUTOMATIC JSON DISCOVERY
# ============================================================

def discover_json_files():

    discovered = {}

    try:

        for filename in os.listdir(
            os.getcwd()
        ):

            if not filename.endswith(
                ".json"
            ):

                continue

            if filename.startswith(
                "."
            ):

                continue

            if filename in {
                "package.json",
                "package-lock.json",
            }:

                continue

            # Never treat master_config itself
            # as a Cog configuration file.

            if filename == "master_config.json":

                continue

            path = config_path(
                filename
            )

            if not os.path.isfile(
                path
            ):

                continue

            discovered[
                filename
            ] = filename

    except Exception as e:

        print(
            f"⚠️ JSON discovery error: {e}"
        )

    return discovered


# ============================================================
# GET ALL CONFIG FILES
# ============================================================

def get_all_config_files():

    result = {}

    # --------------------------------------------------------
    # Known files
    # --------------------------------------------------------

    for cog_name, filename in (
        CONFIG_FILES.items()
    ):

        result[
            filename
        ] = cog_name

    # --------------------------------------------------------
    # Automatically discovered files
    # --------------------------------------------------------

    discovered = discover_json_files()

    for filename in discovered:

        if filename not in result:

            result[
                filename
            ] = (
                filename
                .replace(
                    ".json",
                    ""
                )
                .replace(
                    "_",
                    " "
                )
                .title()
            )

    # --------------------------------------------------------
    # Files already stored in master backup
    #
    # This is VERY important.
    #
    # Even if the current deployment doesn't contain the
    # original JSON file yet, the master backup still knows
    # about it.
    # --------------------------------------------------------

    for filename in master_data.get(
        "files",
        {}
    ):

        if filename not in result:

            backup = master_data[
                "files"
            ].get(
                filename,
                {}
            )

            result[
                filename
            ] = backup.get(
                "cog",
                filename
            )

    return result


# ============================================================
# MIGRATE OLD LOCAL CONFIG
# ============================================================
#
# If a JSON configuration already exists locally and there
# is no persistent backup yet, save it to persistent storage.
#
# This prevents existing setups from being lost when moving
# to the new system.
#
# ============================================================

def migrate_existing_configs():

    global master_data

    changed = False

    all_files = get_all_config_files()

    for filename, cog_name in (
        all_files.items()
    ):

        local_path = config_path(
            filename
        )

        persistent_path = (
            persistent_config_path(
                filename
            )
        )

        # ----------------------------------------------------
        # Existing local file
        # ----------------------------------------------------

        if os.path.exists(
            local_path
        ):

            data = read_json(
                local_path
            )

            if data is not None:

                # Only create persistent copy if one
                # doesn't already exist.

                if not os.path.exists(
                    persistent_path
                ):

                    if write_json(
                        persistent_path,
                        data
                    ):

                        print(
                            f"📦 Migrated "
                            f"{filename} "
                            f"to persistent storage."
                        )

                        changed = True

                # Master index
                if filename not in master_data[
                    "files"
                ]:

                    master_data[
                        "files"
                    ][filename] = {

                        "cog": cog_name,

                        "updated_at": utc_now(),

                        "data": data
                    }

                    changed = True

    if changed:

        master_data[
            "last_backup"
        ] = utc_now()

        write_json(
            MASTER_FILE,
            master_data
        )


# ============================================================
# RESTORE ALL CONFIGURATIONS
# ============================================================

def restore_all_configs():

    global master_data

    restored = []

    all_files = get_all_config_files()

    # --------------------------------------------------------
    # First restore from persistent config copies
    # --------------------------------------------------------

    for filename, cog_name in (
        all_files.items()
    ):

        target = config_path(
            filename
        )

        persistent_path = (
            persistent_config_path(
                filename
            )
        )

        # ----------------------------------------------------
        # Current file already exists
        # ----------------------------------------------------

        if os.path.exists(
            target
        ):

            continue

        # ----------------------------------------------------
        # Persistent copy
        # ----------------------------------------------------

        if os.path.exists(
            persistent_path
        ):

            data = read_json(
                persistent_path
            )

            if data is not None:

                if write_json(
                    target,
                    data
                ):

                    restored.append(
                        filename
                    )

                    print(
                        f"♻️ Restored "
                        f"{filename} "
                        f"from persistent storage."
                    )

                continue

        # ----------------------------------------------------
        # Master backup
        # ----------------------------------------------------

        backup = master_data.get(
            "files",
            {}
        ).get(
            filename
        )

        if not backup:

            continue

        data = backup.get(
            "data"
        )

        if data is None:

            continue

        if write_json(
            target,
            data
        ):

            restored.append(
                filename
            )

            print(
                f"♻️ Restored "
                f"{filename} "
                f"from master backup."
            )

    return restored


# ============================================================
# BACKUP ALL CONFIGURATIONS
# ============================================================

def backup_all_configs():

    global master_data

    changed = False

    all_files = get_all_config_files()

    for filename, cog_name in (
        all_files.items()
    ):

        local_path = config_path(
            filename
        )

        persistent_path = (
            persistent_config_path(
                filename
            )
        )

        # ----------------------------------------------------
        # Local file exists
        # ----------------------------------------------------

        if os.path.exists(
            local_path
        ):

            data = read_json(
                local_path
            )

            if data is not None:

                # --------------------------------------------
                # Save persistent copy
                # --------------------------------------------

                if write_json(
                    persistent_path,
                    data
                ):

                    pass

                # --------------------------------------------
                # Save master index
                # --------------------------------------------

                previous = master_data[
                    "files"
                ].get(
                    filename
                )

                master_data[
                    "files"
                ][filename] = {

                    "cog": cog_name,

                    "updated_at": utc_now(),

                    "data": data
                }

                # Only mark changed if actual config
                # changed.

                if previous is None:

                    changed = True

                elif previous.get(
                    "data"
                ) != data:

                    changed = True

        # ----------------------------------------------------
        # Local file missing
        #
        # DO NOT delete its backup.
        #
        # This is extremely important.
        # ----------------------------------------------------

        else:

            if filename in master_data.get(
                "files",
                {}
            ):

                continue

    # --------------------------------------------------------
    # Update timestamp
    # --------------------------------------------------------

    master_data[
        "last_backup"
    ] = utc_now()

    # --------------------------------------------------------
    # Always save master file.
    #
    # This makes sure newly discovered JSON files are
    # registered even when the actual data didn't change.
    # --------------------------------------------------------

    success = write_json(
        MASTER_FILE,
        master_data
    )

    if success:

        if changed:

            print(
                "💾 Master configuration backup updated."
            )

    return success


# ============================================================
# STARTUP RESTORE
# ============================================================

def prepare_configuration():

    print(
        "=========================================="
    )

    print(
        "🧠 MASTER CONFIG STARTUP"
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

    # --------------------------------------------------------
    # Migrate existing configuration first
    # --------------------------------------------------------

    try:

        migrate_existing_configs()

    except Exception as e:

        print(
            f"⚠️ Migration error: {e}"
        )

    # --------------------------------------------------------
    # Reload master after migration
    # --------------------------------------------------------

    global master_data

    master_data = load_master()

    # --------------------------------------------------------
    # Restore
    # --------------------------------------------------------

    try:

        restored = restore_all_configs()

        if restored:

            print(
                "♻️ Configuration restored:"
            )

            for filename in restored:

                print(
                    f"   └── {filename}"
                )

        else:

            print(
                "ℹ️ No configuration files "
                "needed restoration."
            )

    except Exception as e:

        print(
            f"❌ Restore error: {e}"
        )

    print(
        "=========================================="
    )


# ============================================================
# CONFIGURATION STATUS
# ============================================================

def configuration_status(
    filename
):

    path = config_path(
        filename
    )

    if os.path.exists(
        path
    ):

        data = read_json(
            path
        )

        if data is None:

            return (
                "❌",
                "Configuration file exists "
                "but could not be read."
            )

        if isinstance(
            data,
            dict
        ) and not data:

            return (
                "⚪",
                "Configuration file is empty."
            )

        return (
            "✅",
            "Configuration saved."
        )

    # --------------------------------------------------------
    # Persistent backup
    # --------------------------------------------------------

    persistent = (
        persistent_config_path(
            filename
        )
    )

    if os.path.exists(
        persistent
    ):

        return (
            "♻️",
            "Persistent backup available."
        )

    # --------------------------------------------------------
    # Master backup
    # --------------------------------------------------------

    if filename in master_data.get(
        "files",
        {}
    ):

        return (
            "♻️",
            "Master backup available."
        )

    return (
        "⚪",
        "Not configured."
    )


# ============================================================
# GUILD CONFIG EXTRACTION
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
    # Normal:
    #
    # {
    #   "123456": {...}
    # }
    # --------------------------------------------------------

    if guild_id in data:

        return data[
            guild_id
        ]

    # --------------------------------------------------------
    # Nested guilds:
    #
    # {
    #   "guilds": {
    #       "123456": {...}
    #   }
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

            return guilds[
                guild_id
            ]

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

    if value is None:

        return "Not configured"

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
    # Channel
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
    # Category
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

            return (
                f"`{category.name}`"
            )

        return (
            f"⚠️ Missing category "
            f"`{value}`"
        )

    # --------------------------------------------------------
    # Role
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
    # User/member
    # --------------------------------------------------------

    if (
        key_lower.endswith(
            "user_id"
        )
        or
        key_lower.endswith(
            "member_id"
        )
        or
        key_lower.endswith(
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
    # Dictionaries
    # --------------------------------------------------------

    if isinstance(
        value,
        dict
    ):

        return (
            f"`{len(value)} entries`"
        )

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
        # Nested dictionaries
        # ----------------------------------------------------

        if isinstance(
            value,
            dict
        ):

            if key in {
                "pending",
                "clans",
                "tickets",
                "members",
                "requests",
                "applications",
                "stats",
                "users",
                "cache",
            }:

                lines.append(
                    f"**{key_text}:** "
                    f"`{len(value)} entries`"
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
        # Normal
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
        # CRITICAL
        #
        # Restore BEFORE the other Cogs are loaded.
        # ----------------------------------------------------

        prepare_configuration()

        # ----------------------------------------------------
        # Start backup
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
    # BEFORE BACKUP
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

        commands_found = get_cog_commands(
            self.bot,
            cog
        )

        # ----------------------------------------------------
        # Find configuration filename
        # ----------------------------------------------------

        filename = CONFIG_FILES.get(
            cog_name
        )

        # ----------------------------------------------------
        # Aliases
        # ----------------------------------------------------

        if filename is None:

            aliases = {

                "AIChat":
                    "ai_chat_config.json",

                "AutoReply":
                    "ai_chat_config.json",

                "VoiceSystem":
                    "voice_config.json",

                "Welcome":
                    "welcome_config.json",

                "YouTubeSystem":
                    "youtube_config.json",

                "ModeratorOnline":
                    "moderator_online.json",

                "ModeratorStats":
                    "moderator_stats.json",

                "MusicSystem":
                    "music_config.json",

                "HelpSystem":
                    "help_config.json",

                "ClanSystem":
                    "clan_data.json",

                "CommandSystem":
                    "cmd_config.json",

                "Rules":
                    "rules_config.json",

            }

            filename = aliases.get(
                cog_name
            )

        # ----------------------------------------------------
        # No configuration
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
        # Current file
        # ----------------------------------------------------

        path = config_path(
            filename
        )

        data = read_json(
            path
        )

        # ----------------------------------------------------
        # Current file missing
        # ----------------------------------------------------

        if data is None:

            persistent_path = (
                persistent_config_path(
                    filename
                )
            )

            persistent_data = read_json(
                persistent_path
            )

            if persistent_data is not None:

                data = persistent_data

                status = "♻️"

                message = (
                    "Persistent backup available."
                )

            else:

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
                        "Master backup available."
                    )

                else:

                    data = None

                    status = "⚪"

                    message = (
                        "Not configured."
                    )

        else:

            status = "✅"

            message = (
                "Configuration file found."
            )

        # ----------------------------------------------------
        # Extract guild
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
        # Guild configuration exists
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
    # BUILD REPORTS
    # ========================================================

    def build_reports(
        self,
        guild
    ):

        reports = []

        for cog_name, cog in (
            self.bot.cogs.items()
        ):

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
                                f"{type(e).__name__}: "
                                f"{e}"
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
            "Check all bot systems and saved configuration."
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

                "❌ This command can only be used "
                "inside a server.",

                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        guild = interaction.guild

        # ----------------------------------------------------
        # Backup first
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
        # Embeds
        # ----------------------------------------------------

        embeds = []

        current = discord.Embed(

            title="🔄 BOT CONFIGURATION",

            description=(

                f"Server: **{guild.name}**\n\n"

                "All loaded Cogs were checked "
                "against their saved configuration."
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
            # Setup
            # ------------------------------------------------

            if config is not None:

                config_lines = flatten_config(
                    guild,
                    config
                )

                if config_lines:

                    setup_text = "\n".join(
                        config_lines[:15]
                    )

                    if len(
                        config_lines
                    ) > 15:

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

                command_text = " ".join(

                    f"`{command}`"

                    for command
                    in commands_found
                )

                if len(
                    command_text
                ) > 450:

                    command_text = (
                        command_text[:450]
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
            # Discord field limit
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
            # Discord max 25 fields
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
        # Final embed
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

                "💾 **Persistent backup:** "
                "`Active`\n\n"

                f"📁 **Storage:** "
                f"`{PERSISTENT_DIR}`"
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
        # Send
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
                "❌ You need **Administrator** "
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

# ============================================================
# MASTER CONFIGURATION SYSTEM
# ============================================================
#
# PURPOSE
#
# 1. MasterConfig loads FIRST.
# 2. Persistent configuration is restored BEFORE other Cogs.
# 3. Existing JSON files are automatically discovered.
# 4. JSON files stored only in persistent storage are restored.
# 5. Persistent configuration takes priority over local JSON.
# 6. Configurations are backed up automatically.
# 7. /refresh shows all loaded Cogs.
# 8. /refresh shows saved configuration.
# 9. /refresh shows detected commands.
# 10. Empty local files cannot overwrite useful persistent data.
#
# Render:
#
# BOT_PERSIST_DIR=/data
#
# Persistent structure:
#
# /data/
#     master_config.json
#     configs/
#         welcome_config.json
#         youtube_config.json
#         clan_data.json
#         ...
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


PERSISTENT_CONFIG_DIR = os.path.join(
    PERSISTENT_DIR,
    "configs"
)

os.makedirs(
    PERSISTENT_CONFIG_DIR,
    exist_ok=True
)


# ============================================================
# KNOWN CONFIGURATION FILES
# ============================================================

CONFIG_FILES = {

    "Auto_Reply":
        "ai_chat_config.json",

    "AIChat":
        "ai_chat_config.json",

    "Clan":
        "clan_data.json",

    "ClanSystem":
        "clan_data.json",

    "cmd":
        "cmd_config.json",

    "CommandSystem":
        "cmd_config.json",

    "help_system":
        "help_config.json",

    "HelpSystem":
        "help_config.json",

    "moderator_online":
        "moderator_online.json",

    "ModeratorOnline":
        "moderator_online.json",

    "moderator_stats":
        "moderator_stats.json",

    "ModeratorStats":
        "moderator_stats.json",

    "music_system":
        "music_config.json",

    "MusicSystem":
        "music_config.json",

    "voice":
        "voice_config.json",

    "VoiceSystem":
        "voice_config.json",

    "welcome":
        "welcome_config.json",

    "Welcome":
        "welcome_config.json",

    "youtube":
        "youtube_config.json",

    "YouTubeSystem":
        "youtube_config.json",

    "rules":
        "rules_config.json",

    "Rules":
        "rules_config.json",
}


# ============================================================
# COGS THAT DO NOT NEED CONFIGURATION
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

def write_json(path, data):

    try:

        directory = os.path.dirname(path)

        if directory:

            os.makedirs(
                directory,
                exist_ok=True
            )

        temporary = path + ".tmp"

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

        "version": 3,

        "created_at":
            utc_now(),

        "last_backup":
            None,

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
        3
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
# LOCAL CONFIG PATH
# ============================================================

def config_path(filename):

    return os.path.join(
        os.getcwd(),
        filename
    )


# ============================================================
# PERSISTENT CONFIG PATH
# ============================================================

def persistent_config_path(filename):

    return os.path.join(
        PERSISTENT_CONFIG_DIR,
        filename
    )


# ============================================================
# DISCOVER LOCAL JSON FILES
# ============================================================

def discover_local_json_files():

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
                "master_config.json"
            }:
                continue

            path = config_path(
                filename
            )

            if os.path.isfile(path):

                discovered[
                    filename
                ] = filename

    except Exception as e:

        print(
            f"⚠️ Local JSON discovery error: {e}"
        )

    return discovered


# ============================================================
# DISCOVER PERSISTENT JSON FILES
# ============================================================

def discover_persistent_json_files():

    discovered = {}

    try:

        if not os.path.exists(
            PERSISTENT_CONFIG_DIR
        ):

            return discovered

        for filename in os.listdir(
            PERSISTENT_CONFIG_DIR
        ):

            if not filename.endswith(
                ".json"
            ):
                continue

            path = persistent_config_path(
                filename
            )

            if os.path.isfile(path):

                discovered[
                    filename
                ] = filename

    except Exception as e:

        print(
            f"⚠️ Persistent JSON discovery error: {e}"
        )

    return discovered


# ============================================================
# GET ALL CONFIG FILES
# ============================================================

def get_all_config_files():

    result = {}

    # --------------------------------------------------------
    # Known configuration files
    # --------------------------------------------------------

    for cog_name, filename in CONFIG_FILES.items():

        result[filename] = cog_name

    # --------------------------------------------------------
    # Local JSON files
    # --------------------------------------------------------

    for filename in discover_local_json_files():

        if filename not in result:

            result[filename] = (
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
    # Persistent JSON files
    #
    # IMPORTANT:
    #
    # Even if the JSON file disappeared from the deployment,
    # persistent storage still tells us it exists.
    # --------------------------------------------------------

    for filename in discover_persistent_json_files():

        if filename not in result:

            result[filename] = (
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
    # Master index
    # --------------------------------------------------------

    for filename, info in master_data.get(
        "files",
        {}
    ).items():

        if filename not in result:

            if isinstance(
                info,
                dict
            ):

                result[filename] = info.get(
                    "cog",
                    filename
                )

            else:

                result[filename] = filename

    return result


# ============================================================
# IS USEFUL CONFIGURATION?
# ============================================================

def has_useful_data(data):

    if data is None:
        return False

    if isinstance(
        data,
        dict
    ):

        return bool(data)

    if isinstance(
        data,
        list
    ):

        return bool(data)

    if isinstance(
        data,
        str
    ):

        return bool(data.strip())

    return True


# ============================================================
# MIGRATE OLD CONFIGURATION
# ============================================================
#
# Used when:
#
# - A local config exists
# - Persistent config does NOT exist
#
# This is important when installing this system for the first
# time with an already-configured bot.
# ============================================================

def migrate_existing_configs():

    global master_data

    changed = False

    all_files = get_all_config_files()

    for filename, cog_name in all_files.items():

        local_path = config_path(
            filename
        )

        persistent_path = persistent_config_path(
            filename
        )

        # ----------------------------------------------------
        # If persistent configuration already exists,
        # NEVER replace it with local repository data.
        # ----------------------------------------------------

        if os.path.exists(
            persistent_path
        ):

            continue

        # ----------------------------------------------------
        # Local configuration exists
        # ----------------------------------------------------

        if not os.path.exists(
            local_path
        ):

            continue

        data = read_json(
            local_path
        )

        if data is None:

            continue

        # ----------------------------------------------------
        # Save first persistent copy
        # ----------------------------------------------------

        if write_json(
            persistent_path,
            data
        ):

            print(
                f"📦 Migrated {filename} "
                f"to persistent storage."
            )

            changed = True

        # ----------------------------------------------------
        # Save master index
        # ----------------------------------------------------

        master_data[
            "files"
        ][filename] = {

            "cog":
                cog_name,

            "updated_at":
                utc_now(),

            "data":
                data

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
# RESTORE ONE CONFIGURATION
# ============================================================

def restore_one_config(
    filename,
    cog_name
):

    global master_data

    local_path = config_path(
        filename
    )

    persistent_path = persistent_config_path(
        filename
    )

    # --------------------------------------------------------
    # PRIORITY 1
    #
    # Persistent configuration
    # --------------------------------------------------------

    if os.path.exists(
        persistent_path
    ):

        persistent_data = read_json(
            persistent_path
        )

        if persistent_data is not None:

            # ALWAYS restore persistent data.
            #
            # This is the critical fix.
            #
            # We intentionally overwrite the local JSON.
            #

            if write_json(
                local_path,
                persistent_data
            ):

                master_data[
                    "files"
                ][filename] = {

                    "cog":
                        cog_name,

                    "updated_at":
                        utc_now(),

                    "data":
                        persistent_data

                }

                print(
                    f"♻️ Restored {filename} "
                    f"from persistent storage."
                )

                return True

    # --------------------------------------------------------
    # PRIORITY 2
    #
    # Master backup
    # --------------------------------------------------------

    backup = master_data.get(
        "files",
        {}
    ).get(
        filename
    )

    if isinstance(
        backup,
        dict
    ):

        backup_data = backup.get(
            "data"
        )

        if backup_data is not None:

            if write_json(
                local_path,
                backup_data
            ):

                # Also recreate persistent copy

                write_json(
                    persistent_path,
                    backup_data
                )

                print(
                    f"♻️ Restored {filename} "
                    f"from master backup."
                )

                return True

    # --------------------------------------------------------
    # PRIORITY 3
    #
    # Existing local configuration
    #
    # Only used if no persistent configuration exists.
    # --------------------------------------------------------

    if os.path.exists(
        local_path
    ):

        local_data = read_json(
            local_path
        )

        if local_data is not None:

            # Create persistent copy

            write_json(
                persistent_path,
                local_data
            )

            master_data[
                "files"
            ][filename] = {

                "cog":
                    cog_name,

                "updated_at":
                    utc_now(),

                "data":
                    local_data

            }

            print(
                f"📦 Saved existing "
                f"{filename}."
            )

            return False

    return False


# ============================================================
# RESTORE ALL CONFIGURATIONS
# ============================================================

def restore_all_configs():

    global master_data

    restored = []

    all_files = get_all_config_files()

    print(
        "------------------------------------------"
    )

    print(
        f"🔎 Checking {len(all_files)} configuration files..."
    )

    print(
        "------------------------------------------"
    )

    for filename, cog_name in all_files.items():

        try:

            restored_now = restore_one_config(
                filename,
                cog_name
            )

            if restored_now:

                restored.append(
                    filename
                )

        except Exception as e:

            print(
                f"❌ Failed restoring "
                f"{filename}: {e}"
            )

    # Save updated master index

    master_data[
        "last_backup"
    ] = utc_now()

    write_json(
        MASTER_FILE,
        master_data
    )

    return restored


# ============================================================
# BACKUP ALL CONFIGURATIONS
# ============================================================
#
# IMPORTANT:
#
# An empty local JSON file must NOT overwrite a useful
# persistent configuration.
#
# This prevents a Cog with an empty/default configuration
# from destroying saved configuration after restart.
# ============================================================

def backup_all_configs():

    global master_data

    changed = False

    all_files = get_all_config_files()

    for filename, cog_name in all_files.items():

        local_path = config_path(
            filename
        )

        persistent_path = persistent_config_path(
            filename
        )

        # ----------------------------------------------------
        # Local file exists
        # ----------------------------------------------------

        if os.path.exists(
            local_path
        ):

            local_data = read_json(
                local_path
            )

            if local_data is None:

                continue

            persistent_data = read_json(
                persistent_path
            )

            # ------------------------------------------------
            # SAFETY:
            #
            # If local is empty but persistent has real data,
            # keep the persistent configuration.
            # ------------------------------------------------

            if (
                not has_useful_data(local_data)
                and
                has_useful_data(persistent_data)
            ):

                print(
                    f"🛡️ Protected "
                    f"{filename} "
                    f"from empty overwrite."
                )

                continue

            # ------------------------------------------------
            # Save persistent copy
            # ------------------------------------------------

            if write_json(
                persistent_path,
                local_data
            ):

                pass

            # ------------------------------------------------
            # Master index
            # ------------------------------------------------

            previous = master_data[
                "files"
            ].get(
                filename
            )

            new_entry = {

                "cog":
                    cog_name,

                "updated_at":
                    utc_now(),

                "data":
                    local_data

            }

            master_data[
                "files"
            ][filename] = new_entry

            if previous is None:

                changed = True

            elif previous.get(
                "data"
            ) != local_data:

                changed = True

        # ----------------------------------------------------
        # Local file does not exist
        #
        # DO NOT delete persistent configuration.
        # ----------------------------------------------------

        else:

            persistent_data = read_json(
                persistent_path
            )

            if persistent_data is not None:

                master_data[
                    "files"
                ][filename] = {

                    "cog":
                        cog_name,

                    "updated_at":
                        utc_now(),

                    "data":
                        persistent_data

                }

                changed = True

    # --------------------------------------------------------
    # Save master index
    # --------------------------------------------------------

    master_data[
        "last_backup"
    ] = utc_now()

    success = write_json(
        MASTER_FILE,
        master_data
    )

    if success and changed:

        print(
            "💾 Master configuration backup updated."
        )

    return success


# ============================================================
# PREPARE CONFIGURATION
# ============================================================

def prepare_configuration():

    global master_data

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
        f"📁 Config directory: "
        f"{PERSISTENT_CONFIG_DIR}"
    )

    print(
        f"📄 Master file: "
        f"{MASTER_FILE}"
    )

    # --------------------------------------------------------
    # Load master
    # --------------------------------------------------------

    master_data = load_master()

    # --------------------------------------------------------
    # FIRST:
    #
    # Migrate old configurations only when no persistent
    # version exists.
    # --------------------------------------------------------

    try:

        migrate_existing_configs()

    except Exception as e:

        print(
            f"⚠️ Migration error: {e}"
        )

    # --------------------------------------------------------
    # Reload master
    # --------------------------------------------------------

    master_data = load_master()

    # --------------------------------------------------------
    # SECOND:
    #
    # Restore persistent configurations.
    #
    # Persistent configuration ALWAYS wins.
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
                "ℹ️ No files required restoration."
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

    local_path = config_path(
        filename
    )

    persistent_path = persistent_config_path(
        filename
    )

    # --------------------------------------------------------
    # Persistent configuration gets priority
    # --------------------------------------------------------

    persistent_data = read_json(
        persistent_path
    )

    if has_useful_data(
        persistent_data
    ):

        return (
            "♻️",
            "Saved configuration restored."
        )

    # --------------------------------------------------------
    # Local configuration
    # --------------------------------------------------------

    if os.path.exists(
        local_path
    ):

        data = read_json(
            local_path
        )

        if data is None:

            return (
                "❌",
                "Configuration file cannot be read."
            )

        if not has_useful_data(
            data
        ):

            return (
                "⚪",
                "Configuration file is empty."
            )

        return (
            "✅",
            "Configuration file found."
        )

    # --------------------------------------------------------
    # Master backup
    # --------------------------------------------------------

    backup = master_data.get(
        "files",
        {}
    ).get(
        filename
    )

    if isinstance(
        backup,
        dict
    ):

        if has_useful_data(
            backup.get("data")
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
# EXTRACT GUILD CONFIGURATION
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
    # Format:
    #
    # {
    #     "123456": {...}
    # }
    # --------------------------------------------------------

    if guild_id in data:

        return data[
            guild_id
        ]

    # --------------------------------------------------------
    # Format:
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

            return guilds[
                guild_id
            ]

    return None


# ============================================================
# DISCORD RESOLVERS
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
# FORMAT CONFIGURATION VALUES
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

            return (
                f"`{category.name}`"
            )

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
    # User/member/owner
    # --------------------------------------------------------

    if (
        key_lower.endswith("user_id")
        or
        key_lower.endswith("member_id")
        or
        key_lower.endswith("owner_id")
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

            # Don't dump huge member/cache dictionaries

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
                "history"

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
                    f"**{key_text}:** `{{}}`"
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
        # Normal values
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
            f"📁 Config directory: "
            f"{PERSISTENT_CONFIG_DIR}"
        )

        # ----------------------------------------------------
        # CRITICAL:
        #
        # Restore before other Cogs load.
        # ----------------------------------------------------

        prepare_configuration()

        # ----------------------------------------------------
        # Start backup loop
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
        # Find configuration file
        # ----------------------------------------------------

        filename = CONFIG_FILES.get(
            cog_name
        )

        # ----------------------------------------------------
        # Additional aliases
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
        # No configuration Cog
        # ----------------------------------------------------

        if filename is None:

            if cog_name in NO_CONFIG_COGS:

                return {

                    "status":
                        "ℹ️",

                    "message":
                        (
                            "Command-only Cog. "
                            "No persistent setup required."
                        ),

                    "config":
                        None,

                    "commands":
                        commands_found,

                    "filename":
                        None

                }

            return {

                "status":
                    "ℹ️",

                "message":
                    (
                        "No configuration file "
                        "registered for this Cog."
                    ),

                "config":
                    None,

                "commands":
                    commands_found,

                "filename":
                    None

            }

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Read persistent copy FIRST.
        # ----------------------------------------------------

        persistent_path = persistent_config_path(
            filename
        )

        persistent_data = read_json(
            persistent_path
        )

        if persistent_data is not None:

            data = persistent_data

            status = "♻️"

            message = (
                "Persistent configuration loaded."
            )

        else:

            path = config_path(
                filename
            )

            data = read_json(
                path
            )

            if data is not None:

                status = "✅"

                message = (
                    "Configuration file found."
                )

            else:

                backup = master_data.get(
                    "files",
                    {}
                ).get(
                    filename
                )

                if isinstance(
                    backup,
                    dict
                ):

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

        # ----------------------------------------------------
        # Extract server-specific configuration
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

            if (
                isinstance(
                    guild_config,
                    dict
                )
                and
                not guild_config
            ):

                status = "⚪"

                message = (
                    "Guild configuration is empty."
                )

            config_to_show = guild_config

        else:

            config_to_show = None

            if data is not None:

                status = "⚪"

                message = (
                    "File exists, but this "
                    "server has no saved setup."
                )

        return {

            "status":
                status,

            "message":
                message,

            "config":
                config_to_show,

            "commands":
                commands_found,

            "filename":
                filename

        }

    # ========================================================
    # BUILD REPORTS
    # ========================================================

    def build_reports(
        self,
        guild
    ):

        reports = []

        # ----------------------------------------------------
        # Running Cogs
        # ----------------------------------------------------

        for cog_name, cog in self.bot.cogs.items():

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

                            "status":
                                "❌",

                            "message":
                                (
                                    f"{type(e).__name__}: "
                                    f"{e}"
                                ),

                            "config":
                                None,

                            "commands":
                                [],

                            "filename":
                                None

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
        # IMPORTANT:
        #
        # Do NOT run setup commands.
        #
        # Only save/check existing configuration.
        # ----------------------------------------------------

        try:

            await self.backup_now()

        except Exception as e:

            print(
                f"❌ Backup failed: {e}"
            )

        # ----------------------------------------------------
        # Build reports
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

            if status in {
                "✅",
                "♻️"
            }:

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
            # Setup information
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
            # Discord embed field limit
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
        # Send embeds
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

async def setup(bot):

    await bot.add_cog(
        MasterConfig(bot)
    )

    print(
        "✅ Master Config Cog ready."
    )

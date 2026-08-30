# ============================================================
# MASTER CONFIGURATION SYSTEM
# SUPABASE / POSTGRESQL VERSION
# ============================================================
#
# PURPOSE:
#
# 1. MasterConfig loads FIRST.
# 2. Connects to Supabase PostgreSQL.
# 3. Restores saved JSON configuration files.
# 4. Other Cogs load AFTER restoration.
# 5. Automatically discovers JSON configuration files.
# 6. Automatically backs up JSON files to Supabase.
# 7. New JSON files are automatically detected.
# 8. /refresh shows configuration status.
# 9. /dbstatus checks the database.
# 10. /configcount shows saved configuration files.
#
# Existing Cogs do NOT need to be modified.
#
# ============================================================

import os
import json
import asyncio
import socket
import ssl
import traceback
from urllib.parse import urlsplit, unquote
from datetime import datetime, timezone

import asyncpg
import discord

from discord.ext import commands, tasks
from discord import app_commands


# ============================================================
# SETTINGS
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL")

# How often local JSON files are checked and backed up.
BACKUP_INTERVAL = 15

# Directories that should never be scanned.
SKIP_DIRECTORIES = {
    ".git",
    ".github",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".cache",
    ".pytest_cache",
}


# ============================================================
# GLOBAL LOCK
# ============================================================

config_lock = asyncio.Lock()


# ============================================================
# TIME
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# JSON HELPERS
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
            f"❌ Failed reading JSON "
            f"{path}: {e}"
        )

        return None


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
            f"❌ Failed writing JSON "
            f"{path}: {e}"
        )

        return False


# ============================================================
# FIND ALL JSON CONFIGURATION FILES
# ============================================================

def find_json_files():

    files = []

    root_directory = os.getcwd()

    for root, directories, filenames in os.walk(
        root_directory
    ):

        # Remove directories that should not be scanned.
        directories[:] = [
            directory
            for directory in directories
            if directory not in SKIP_DIRECTORIES
            and not directory.startswith(".")
        ]

        for filename in filenames:

            if not filename.lower().endswith(".json"):
                continue

            full_path = os.path.join(
                root,
                filename
            )

            relative_path = os.path.relpath(
                full_path,
                root_directory
            )

            relative_path = relative_path.replace(
                os.sep,
                "/"
            )

            # Don't backup package/config files that are
            # obviously not bot configuration.
            if relative_path.startswith(
                "package"
            ):
                continue

            if relative_path.startswith(
                "node_modules/"
            ):
                continue

            files.append(
                (
                    relative_path,
                    full_path
                )
            )

    return sorted(
        files
    )


# ============================================================
# MASTER CONFIG COG
# ============================================================

class MasterConfig(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.pool = None

        self.database_ready = False

        self.last_backup = None

        self.backup_status = (
            "Starting"
        )

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
            "💾 Storage: Supabase PostgreSQL"
        )

    # ========================================================
    # COG LOAD
    # ========================================================

    async def cog_load(self):

        print(
            "🧠 MasterConfig loading..."
        )

        if not DATABASE_URL:

            print(
                "❌ DATABASE_URL is not set."
            )

            print(
                "❌ Add DATABASE_URL to Render "
                "Environment Variables."
            )

            return

        try:

            await self.connect_database()

            if self.database_ready:

                await self.create_tables()

                # IMPORTANT:
                # Restore BEFORE other Cogs load.
                await self.restore_all_configs()

                # Start automatic backup.
                self.backup_loop.start()

                print(
                    "✅ MasterConfig database system ready."
                )

        except Exception as e:

            print(
                f"❌ MasterConfig startup error: {e}"
            )

            traceback.print_exc()

    # ========================================================
    # DATABASE CONNECTION
    # ========================================================

    async def connect_database(self):

        try:

            parsed = urlsplit(
                DATABASE_URL
            )

            if parsed.scheme not in {
                "postgresql",
                "postgres"
            }:

                raise ValueError(
                    "DATABASE_URL must start with "
                    "postgresql://"
                )

            hostname = parsed.hostname

            if not hostname:

                raise ValueError(
                    "DATABASE_URL does not contain "
                    "a database hostname."
                )

            port = parsed.port or 5432

            username = parsed.username

            if not username:

                raise ValueError(
                    "DATABASE_URL does not contain "
                    "a database username."
                )

            username = unquote(
                username
            )

            password = parsed.password

            if password is None:

                raise ValueError(
                    "DATABASE_URL does not contain "
                    "a database password."
                )

            password = unquote(
                password
            )

            database = (
                parsed.path.lstrip("/")
                or "postgres"
            )

            print(
                f"🔍 Database host: {hostname}"
            )

            print(
                f"🔍 Database port: {port}"
            )

            print(
                f"🔍 Database user: {username}"
            )

            # ------------------------------------------------
            # Resolve IPv4 manually.
            #
            # This avoids the hostname/IP parsing problem
            # that your Render log is currently showing.
            # ------------------------------------------------

            ipv4_addresses = socket.getaddrinfo(
                hostname,
                port,
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            if not ipv4_addresses:

                raise RuntimeError(
                    "Could not resolve database "
                    "hostname to IPv4."
                )

            ipv4 = ipv4_addresses[0][4][0]

            print(
                f"🌐 Resolved database IPv4: {ipv4}"
            )

            # ------------------------------------------------
            # SSL
            #
            # We connect to the resolved IPv4 address while
            # allowing TLS without hostname verification.
            # The Supabase pooler still provides encrypted
            # PostgreSQL traffic.
            # ------------------------------------------------

            ssl_context = ssl.create_default_context()

            ssl_context.check_hostname = False

            ssl_context.verify_mode = (
                ssl.CERT_NONE
            )

            # ------------------------------------------------
            # Connect
            # ------------------------------------------------

            self.pool = await asyncpg.create_pool(
                host=ipv4,
                port=port,
                user=username,
                password=password,
                database=database,
                min_size=1,
                max_size=5,
                ssl=ssl_context,
                command_timeout=30
            )

            # Test connection.

            async with self.pool.acquire() as connection:

                await connection.fetchval(
                    "SELECT 1"
                )

            self.database_ready = True

            print(
                "✅ Supabase PostgreSQL connected"
            )

        except Exception as e:

            self.database_ready = False
            self.pool = None

            print(
                f"❌ Database connection failed: {e}"
            )

            traceback.print_exc()

    # ========================================================
    # CREATE DATABASE TABLES
    # ========================================================

    async def create_tables(self):

        if not self.pool:
            return

        async with self.pool.acquire() as connection:

            await connection.execute("""
                CREATE TABLE IF NOT EXISTS bot_config_files (

                    config_path TEXT PRIMARY KEY,

                    config_data JSONB NOT NULL,

                    updated_at TIMESTAMPTZ
                    DEFAULT NOW()

                )
            """)

            await connection.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_bot_config_files_updated
                ON bot_config_files(updated_at)
            """)

        print(
            "✅ bot_config_files table ready"
        )

    # ========================================================
    # SAVE ONE CONFIGURATION FILE
    # ========================================================

    async def save_config_file(
        self,
        relative_path,
        full_path
    ):

        if not self.pool:
            return False

        data = read_json(
            full_path
        )

        if data is None:
            return False

        try:

            async with self.pool.acquire() as connection:

                await connection.execute(
                    """
                    INSERT INTO bot_config_files
                    (
                        config_path,
                        config_data,
                        updated_at
                    )

                    VALUES
                    (
                        $1,
                        $2::jsonb,
                        NOW()
                    )

                    ON CONFLICT
                    (
                        config_path
                    )

                    DO UPDATE SET

                        config_data =
                        EXCLUDED.config_data,

                        updated_at =
                        NOW()
                    """,

                    relative_path,

                    json.dumps(
                        data,
                        ensure_ascii=False
                    )
                )

            return True

        except Exception as e:

            print(
                f"❌ Failed saving "
                f"{relative_path}: {e}"
            )

            return False

    # ========================================================
    # RESTORE ONE CONFIGURATION FILE
    # ========================================================

    async def restore_config_file(
        self,
        relative_path
    ):

        if not self.pool:
            return False

        try:

            async with self.pool.acquire() as connection:

                row = await connection.fetchrow(
                    """
                    SELECT
                        config_data

                    FROM bot_config_files

                    WHERE config_path = $1
                    """,

                    relative_path
                )

            if not row:

                return False

            full_path = os.path.join(
                os.getcwd(),
                relative_path
            )

            data = row[
                "config_data"
            ]

            if write_json(
                full_path,
                data
            ):

                print(
                    f"♻️ Restored: "
                    f"{relative_path}"
                )

                return True

        except Exception as e:

            print(
                f"❌ Failed restoring "
                f"{relative_path}: {e}"
            )

        return False

    # ========================================================
    # RESTORE ALL CONFIGURATIONS
    # ========================================================

    async def restore_all_configs(self):

        if not self.pool:

            return

        print(
            "♻️ Checking saved configurations..."
        )

        try:

            async with self.pool.acquire() as connection:

                rows = await connection.fetch(
                    """
                    SELECT
                        config_path,
                        config_data

                    FROM bot_config_files
                    """
                )

            if not rows:

                print(
                    "ℹ️ No previous database "
                    "configuration found."
                )

                # First deployment:
                # Save whatever JSON files already exist.
                await self.backup_all_configs(
                    silent=False
                )

                return

            restored = 0

            for row in rows:

                relative_path = row[
                    "config_path"
                ]

                data = row[
                    "config_data"
                ]

                full_path = os.path.join(
                    os.getcwd(),
                    relative_path
                )

                if write_json(
                    full_path,
                    data
                ):

                    restored += 1

                    print(
                        f"♻️ Restored: "
                        f"{relative_path}"
                    )

            print(
                f"✅ Restored "
                f"{restored} configuration files."
            )

            # ------------------------------------------------
            # Detect new JSON files that weren't previously
            # stored in Supabase.
            # ------------------------------------------------

            existing_paths = {
                row["config_path"]
                for row in rows
            }

            local_files = find_json_files()

            new_files = 0

            for relative_path, full_path in local_files:

                if relative_path not in existing_paths:

                    if await self.save_config_file(
                        relative_path,
                        full_path
                    ):

                        new_files += 1

                        print(
                            f"🆕 New configuration saved: "
                            f"{relative_path}"
                        )

            if new_files:

                print(
                    f"✅ Added "
                    f"{new_files} new configuration files."
                )

        except Exception as e:

            print(
                f"❌ Restore error: {e}"
            )

            traceback.print_exc()

    # ========================================================
    # BACKUP ALL CONFIGURATIONS
    # ========================================================

    async def backup_all_configs(
        self,
        silent=True
    ):

        if not self.pool:

            return 0

        files = find_json_files()

        saved = 0

        for relative_path, full_path in files:

            # Skip master/config metadata files.
            if relative_path in {
                "package.json",
                "package-lock.json"
            }:

                continue

            if await self.save_config_file(
                relative_path,
                full_path
            ):

                saved += 1

                if not silent:

                    print(
                        f"💾 Saved: "
                        f"{relative_path}"
                    )

        self.last_backup = datetime.now(
            timezone.utc
        )

        self.backup_status = (
            f"{saved} files backed up"
        )

        if not silent:

            print(
                f"✅ Initial backup complete: "
                f"{saved} files."
            )

        return saved

    # ========================================================
    # AUTOMATIC BACKUP LOOP
    # ========================================================

    @tasks.loop(
        seconds=BACKUP_INTERVAL
    )
    async def backup_loop(self):

        if not self.database_ready:

            return

        try:

            async with config_lock:

                count = await self.backup_all_configs(
                    silent=True
                )

            print(
                f"💾 Automatic backup: "
                f"{count} JSON files"
            )

        except Exception as e:

            print(
                f"❌ Automatic backup error: "
                f"{e}"
            )

    # ========================================================
    # BACKUP LOOP BEFORE START
    # ========================================================

    @backup_loop.before_loop
    async def before_backup_loop(self):

        await self.bot.wait_until_ready()

    # ========================================================
    # GET ALL SAVED CONFIGS
    # ========================================================

    async def get_saved_configs(self):

        if not self.pool:

            return []

        try:

            async with self.pool.acquire() as connection:

                rows = await connection.fetch(
                    """
                    SELECT
                        config_path,
                        updated_at

                    FROM bot_config_files

                    ORDER BY config_path
                    """
                )

            return rows

        except Exception as e:

            print(
                f"❌ Failed loading config list: "
                f"{e}"
            )

            return []

    # ========================================================
    # PUBLIC API
    #
    # Other Cogs can use these later if needed.
    # ========================================================

    async def set_config(
        self,
        key,
        value
    ):

        if not self.pool:
            return False

        try:

            async with self.pool.acquire() as connection:

                await connection.execute(
                    """
                    INSERT INTO bot_config_files
                    (
                        config_path,
                        config_data,
                        updated_at
                    )

                    VALUES
                    (
                        $1,
                        $2::jsonb,
                        NOW()
                    )

                    ON CONFLICT
                    (
                        config_path
                    )

                    DO UPDATE SET

                        config_data =
                        EXCLUDED.config_data,

                        updated_at =
                        NOW()
                    """,

                    key,

                    json.dumps(
                        value,
                        ensure_ascii=False
                    )
                )

            return True

        except Exception as e:

            print(
                f"❌ set_config failed: {e}"
            )

            return False

    async def get_config(
        self,
        key,
        default=None
    ):

        if not self.pool:

            return default

        try:

            async with self.pool.acquire() as connection:

                row = await connection.fetchrow(
                    """
                    SELECT config_data

                    FROM bot_config_files

                    WHERE config_path = $1
                    """,

                    key
                )

            if not row:

                return default

            return row[
                "config_data"
            ]

        except Exception as e:

            print(
                f"❌ get_config failed: {e}"
            )

            return default

    # ========================================================
    # /DBSTATUS
    # ========================================================

    @app_commands.command(
        name="dbstatus",
        description="Check the Supabase database connection."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def dbstatus(
        self,
        interaction: discord.Interaction
    ):

        if not self.pool:

            await interaction.response.send_message(
                "🔴 **Database Offline**\n\n"
                "Supabase PostgreSQL is not connected.",
                ephemeral=True
            )

            return

        try:

            async with self.pool.acquire() as connection:

                await connection.fetchval(
                    "SELECT 1"
                )

            count = await connection.fetchval(
                """
                SELECT COUNT(*)
                FROM bot_config_files
                """
            )

            await interaction.response.send_message(
                "🟢 **Database Connected**\n\n"
                f"🗄️ Saved configuration files: "
                f"`{count}`\n"
                "💾 Automatic backup: `Active`",
                ephemeral=True
            )

        except Exception as e:

            await interaction.response.send_message(
                "🔴 **Database Error**\n\n"
                f"`{type(e).__name__}: {e}`",
                ephemeral=True
            )

    # ========================================================
    # /CONFIGCOUNT
    # ========================================================

    @app_commands.command(
        name="configcount",
        description="Show saved configuration count."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def configcount(
        self,
        interaction: discord.Interaction
    ):

        if not self.pool:

            await interaction.response.send_message(
                "🔴 Database is offline.",
                ephemeral=True
            )

            return

        try:

            async with self.pool.acquire() as connection:

                count = await connection.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM bot_config_files
                    """
                )

            await interaction.response.send_message(
                f"💾 **Saved configurations:** "
                f"`{count}`",
                ephemeral=True
            )

        except Exception as e:

            await interaction.response.send_message(
                f"❌ Error: `{e}`",
                ephemeral=True
            )

    # ========================================================
    # /BACKUP
    # ========================================================

    @app_commands.command(
        name="backup",
        description="Manually backup all bot configurations."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def backup(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        if not self.pool:

            await interaction.followup.send(
                "🔴 Database is offline.",
                ephemeral=True
            )

            return

        try:

            async with config_lock:

                count = await self.backup_all_configs(
                    silent=False
                )

            await interaction.followup.send(
                "✅ **Backup Complete**\n\n"
                f"💾 Configuration files saved: "
                f"`{count}`\n"
                "🗄️ Storage: `Supabase PostgreSQL`",
                ephemeral=True
            )

        except Exception as e:

            await interaction.followup.send(
                f"❌ Backup failed:\n`{e}`",
                ephemeral=True
            )

    # ========================================================
    # /REFRESH
    # ========================================================

    @app_commands.command(
        name="refresh",
        description="Check and display the complete bot setup."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def refresh(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        # ----------------------------------------------------
        # Database status
        # ----------------------------------------------------

        database_status = (
            "🟢 Connected"
            if self.database_ready
            else "🔴 Offline"
        )

        # ----------------------------------------------------
        # Cogs
        # ----------------------------------------------------

        cogs = list(
            self.bot.cogs.values()
        )

        # ----------------------------------------------------
        # Commands
        # ----------------------------------------------------

        slash_commands = []

        try:

            for command in self.bot.tree.walk_commands():

                slash_commands.append(
                    "/" + command.qualified_name
                )

        except Exception:

            pass

        slash_commands = sorted(
            set(slash_commands)
        )

        # ----------------------------------------------------
        # JSON files
        # ----------------------------------------------------

        local_files = find_json_files()

        saved_configs = []

        if self.pool:

            saved_configs = await self.get_saved_configs()

        saved_paths = {
            row["config_path"]
            for row in saved_configs
        }

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        configured = 0
        not_configured = 0
        warnings = 0
        command_only = 0

        cog_lines = []

        for cog in cogs:

            cog_name = cog.__class__.__name__

            # Commands belonging to cog
            cog_commands = []

            try:

                for command in self.bot.tree.walk_commands():

                    binding = getattr(
                        command,
                        "binding",
                        None
                    )

                    if binding is cog:

                        cog_commands.append(
                            "/" + command.qualified_name
                        )

            except Exception:

                pass

            cog_commands = sorted(
                set(cog_commands)
            )

            # Search matching config files.
            matching_files = []

            for relative_path, full_path in local_files:

                filename = os.path.basename(
                    relative_path
                ).lower()

                cog_lower = cog_name.lower()

                if (
                    cog_lower in filename
                    or filename.replace(
                        "_config.json",
                        ""
                    ) in cog_lower
                ):

                    matching_files.append(
                        relative_path
                    )

            if matching_files:

                configured += 1

                config_text = ", ".join(
                    f"`{path}`"
                    for path in matching_files
                )

                cog_lines.append(
                    f"📦 **{cog_name}**\n"
                    f"✅ Config: {config_text}\n"
                    f"🛠️ Commands: "
                    f"{', '.join(cog_commands) if cog_commands else 'None'}"
                )

            elif cog_commands:

                command_only += 1

                cog_lines.append(
                    f"📦 **{cog_name}**\n"
                    f"ℹ️ Command-only\n"
                    f"🛠️ Commands: "
                    f"{', '.join(cog_commands)}"
                )

            else:

                not_configured += 1

                cog_lines.append(
                    f"📦 **{cog_name}**\n"
                    f"⚪ No JSON configuration detected."
                )

        # ----------------------------------------------------
        # DATABASE WARNING
        # ----------------------------------------------------

        if not self.database_ready:

            warnings += 1

        # ----------------------------------------------------
        # Build embeds
        # ----------------------------------------------------

        embeds = []

        current = discord.Embed(
            title="🔄 BOT CONFIGURATION",
            color=discord.Color.blurple()
        )

        field_count = 0

        for line in cog_lines:

            if field_count >= 10:

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

            current.add_field(
                name="",
                value=line,
                inline=False
            )

            field_count += 1

        if field_count:

            embeds.append(
                current
            )

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        summary = discord.Embed(
            title="📊 REFRESH SUMMARY",
            description=(
                f"📦 **Cogs checked:** "
                f"`{len(cogs)}`\n\n"

                f"✅ **Configured:** "
                f"`{configured}`\n"

                f"⚠️ **Warnings:** "
                f"`{warnings}`\n"

                f"❌ **Errors:** "
                f"`0`\n"

                f"⚪ **Not configured:** "
                f"`{not_configured}`\n"

                f"ℹ️ **Command-only:** "
                f"`{command_only}`\n\n"

                f"⚙️ **Commands detected:** "
                f"`{len(slash_commands)}`\n\n"

                f"🗄️ **Database:** "
                f"`{database_status}`\n\n"

                f"💾 **Persistent backup:** "
                f"`{'Active' if self.database_ready else 'Offline'}`\n\n"

                f"📁 **JSON files detected:** "
                f"`{len(local_files)}`\n\n"

                f"☁️ **JSON files stored in Supabase:** "
                f"`{len(saved_paths)}`"
            ),
            color=(
                discord.Color.green()
                if self.database_ready
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
        # Send configuration pages
        # ----------------------------------------------------

        for embed in embeds:

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

        # ----------------------------------------------------
        # Send summary
        # ----------------------------------------------------

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

    # ========================================================
    # UNLOAD
    # ========================================================

    async def cog_unload(
        self
    ):

        print(
            "🛑 Stopping MasterConfig..."
        )

        try:

            if self.backup_loop.is_running():

                self.backup_loop.cancel()

        except Exception:

            pass

        # Final backup before shutdown.

        try:

            if self.pool:

                await self.backup_all_configs(
                    silent=False
                )

        except Exception as e:

            print(
                f"⚠️ Final backup failed: {e}"
            )

        # Close database.

        try:

            if self.pool:

                await self.pool.close()

                print(
                    "🔌 PostgreSQL connection closed"
                )

        except Exception as e:

            print(
                f"⚠️ Database close error: {e}"
            )


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
        "✅ MasterConfig cog loaded"
    )

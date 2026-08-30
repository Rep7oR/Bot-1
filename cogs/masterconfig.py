import os
import json
import asyncio
import traceback
from pathlib import Path

import asyncpg
import discord
from discord.ext import commands, tasks
from discord import app_commands


# ============================================================
# MASTER CONFIG
# Supabase PostgreSQL persistent configuration system
# ============================================================

class MasterConfig(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.pool = None
        self.database_ready = False

        self.config_dir = Path("data")
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.database_url = os.getenv("DATABASE_URL")

        if not self.database_url:
            self.database_url = os.getenv("SUPABASE_DB_URL")

        print("==========================================")
        print("🧠 MASTER CONFIG")
        print("==========================================")
        print("💾 Storage: Supabase PostgreSQL")
        print("🧠 MasterConfig loading...")

        self.backup_loop.start()

    # ========================================================
    # COG LOAD
    # ========================================================

    async def cog_load(self):

        try:
            await self.connect_database()

            if self.database_ready:

                await self.create_tables()

                # Restore saved configuration files
                # automatically when the bot starts.
                await self.restore_all_configs()

        except Exception as e:

            print(
                f"❌ MasterConfig startup error: {e}"
            )

            traceback.print_exc()

        print("📦 MasterConfig cog loaded")

    # ========================================================
    # COG UNLOAD
    # ========================================================

    async def cog_unload(self):

        self.backup_loop.cancel()

        if self.pool:

            try:
                await self.pool.close()

            except Exception:
                pass

    # ========================================================
    # DATABASE CONNECTION
    # ========================================================

    async def connect_database(self):

        if not self.database_url:

            print(
                "❌ DATABASE_URL / SUPABASE_DB_URL "
                "environment variable is missing."
            )

            return

        try:

            print("🔌 Connecting to Supabase...")

            # asyncpg can have problems with some URL formats.
            # Normalize the URL before connecting.

            database_url = self.database_url.strip()

            # Remove accidental quotes.
            if (
                database_url.startswith('"')
                and database_url.endswith('"')
            ):
                database_url = database_url[1:-1]

            if (
                database_url.startswith("'")
                and database_url.endswith("'")
            ):
                database_url = database_url[1:-1]

            # Render/Supabase environment variables sometimes
            # contain postgres:// instead of postgresql://.
            if database_url.startswith("postgres://"):

                database_url = database_url.replace(
                    "postgres://",
                    "postgresql://",
                    1
                )

            self.pool = await asyncpg.create_pool(
                dsn=database_url,
                min_size=1,
                max_size=5,
                command_timeout=30
            )

            self.database_ready = True

            print(
                "✅ Supabase PostgreSQL connected"
            )

        except Exception as e:

            self.database_ready = False

            print(
                f"❌ Database connection failed: {e}"
            )

            traceback.print_exc()

    # ========================================================
    # CREATE TABLE
    # ========================================================

    async def create_tables(self):

        if not self.pool:
            return

        async with self.pool.acquire() as connection:

            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_config_files (
                    filename TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )

        print(
            "✅ Configuration database table ready"
        )

    # ========================================================
    # FIND JSON CONFIGURATION FILES
    # ========================================================

    def get_config_files(self):

        files = []

        # Search the root directory.
        files.extend(
            Path(".").glob("*.json")
        )

        # Search data directory.
        if self.config_dir.exists():

            files.extend(
                self.config_dir.glob("*.json")
            )

        # Remove duplicates.
        unique_files = {}

        for file in files:

            try:

                unique_files[str(file.resolve())] = file

            except Exception:
                pass

        return list(unique_files.values())

    # ========================================================
    # BACKUP ALL CONFIGURATIONS
    # ========================================================

    async def backup_all_configs(self):

        if not self.pool or not self.database_ready:
            return

        files = self.get_config_files()

        if not files:
            print(
                "⚠️ No JSON configuration files found."
            )
            return

        saved = 0

        async with self.pool.acquire() as connection:

            for file in files:

                try:

                    content = file.read_text(
                        encoding="utf-8"
                    )

                    # Make sure the JSON is valid.
                    json.loads(content)

                    await connection.execute(
                        """
                        INSERT INTO bot_config_files
                        (
                            filename,
                            content,
                            updated_at
                        )
                        VALUES ($1, $2, NOW())

                        ON CONFLICT (filename)
                        DO UPDATE SET
                            content = EXCLUDED.content,
                            updated_at = NOW()
                        """,
                        str(file),
                        content
                    )

                    saved += 1

                except json.JSONDecodeError:

                    print(
                        f"⚠️ Invalid JSON skipped: {file}"
                    )

                except Exception as e:

                    print(
                        f"❌ Failed to backup {file}: {e}"
                    )

        print(
            f"☁️ Backed up {saved} configuration files"
        )

    # ========================================================
    # RESTORE ALL CONFIGURATIONS
    # ========================================================

    async def restore_all_configs(self):

        if not self.pool or not self.database_ready:

            print(
                "⚠️ Database unavailable - "
                "cannot restore configurations."
            )

            return

        print(
            "♻️ Restoring configurations..."
        )

        try:

            async with self.pool.acquire() as connection:

                rows = await connection.fetch(
                    """
                    SELECT filename, content
                    FROM bot_config_files
                    ORDER BY filename
                    """
                )

            if not rows:

                print(
                    "ℹ️ No saved configurations "
                    "found in Supabase."
                )

                return

            restored = 0

            for row in rows:

                filename = row["filename"]
                content = row["content"]

                try:

                    # Verify that the stored content
                    # is valid JSON.
                    json.loads(content)

                    file_path = Path(filename)

                    # Prevent accidental absolute-path
                    # restoration outside the project.
                    if file_path.is_absolute():

                        file_path = Path(
                            file_path.name
                        )

                    file_path.parent.mkdir(
                        parents=True,
                        exist_ok=True
                    )

                    file_path.write_text(
                        content,
                        encoding="utf-8"
                    )

                    restored += 1

                except json.JSONDecodeError:

                    print(
                        f"⚠️ Invalid saved JSON skipped: "
                        f"{filename}"
                    )

                except Exception as e:

                    print(
                        f"❌ Failed to restore "
                        f"{filename}: {e}"
                    )

            print(
                f"✅ Restored {restored} "
                f"configuration files"
            )

        except Exception as e:

            print(
                f"❌ Restore failed: {e}"
            )

            traceback.print_exc()

    # ========================================================
    # AUTOMATIC BACKUP
    # ========================================================

    @tasks.loop(seconds=30)
    async def backup_loop(self):

        if not self.database_ready:
            return

        try:

            await self.backup_all_configs()

        except Exception as e:

            print(
                f"❌ Automatic backup failed: {e}"
            )

    # ========================================================
    # BACKUP LOOP ERROR
    # ========================================================

    @backup_loop.before_loop
    async def before_backup_loop(self):

        await self.bot.wait_until_ready()

        # Give the database connection time to initialize.
        await asyncio.sleep(5)

    # ========================================================
    # /DBSTATUS
    # ========================================================

    @app_commands.command(
        name="dbstatus",
        description="Show MasterConfig database status."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def dbstatus(
        self,
        interaction: discord.Interaction
    ):

        if self.database_ready:

            status = (
                "🟢 **Database Online**\n\n"
                "☁️ Supabase PostgreSQL connected."
            )

        else:

            status = (
                "🔴 **Database Offline**\n\n"
                "Supabase PostgreSQL is not connected."
            )

        await interaction.response.send_message(
            status,
            ephemeral=True
        )

    # ========================================================
    # /CONFIGCOUNT
    # ========================================================

    @app_commands.command(
        name="configcount",
        description="Show the number of saved configurations."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def configcount(
        self,
        interaction: discord.Interaction
    ):

        if not self.pool or not self.database_ready:

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
                f"📦 **Saved Configurations:** `{count}`",
                ephemeral=True
            )

        except Exception as e:

            await interaction.response.send_message(
                f"❌ Failed to read database:\n`{e}`",
                ephemeral=True
            )

    # ========================================================
    # /BACKUP
    # ========================================================

    @app_commands.command(
        name="backup",
        description="Save all configuration files to Supabase."
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

        if not self.pool or not self.database_ready:

            await interaction.followup.send(
                "🔴 **Database is offline.**",
                ephemeral=True
            )

            return

        try:

            await self.backup_all_configs()

            async with self.pool.acquire() as connection:

                count = await connection.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM bot_config_files
                    """
                )

            await interaction.followup.send(
                "☁️ **Backup Complete**\n\n"
                f"📦 Configurations stored: `{count}`",
                ephemeral=True
            )

        except Exception as e:

            print(
                f"❌ Manual backup failed: {e}"
            )

            traceback.print_exc()

            await interaction.followup.send(
                "❌ **Backup Failed**\n\n"
                f"`{e}`",
                ephemeral=True
            )

    # ========================================================
    # /RESTORE
    # ========================================================

    @app_commands.command(
        name="restore",
        description="Restore all saved configurations from Supabase."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def restore(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        if not self.pool or not self.database_ready:

            await interaction.followup.send(
                "🔴 **Database is offline.**\n\n"
                "The bot cannot restore configurations.",
                ephemeral=True
            )

            return

        try:

            print(
                f"♻️ Manual restore requested by "
                f"{interaction.user}"
            )

            await self.restore_all_configs()

            async with self.pool.acquire() as connection:

                count = await connection.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM bot_config_files
                    """
                )

            await interaction.followup.send(
                "♻️ **Restore Complete**\n\n"
                f"☁️ Configurations in database: `{count}`\n"
                "📂 Saved JSON configuration files "
                "were restored.\n"
                "✅ Restore finished successfully.",
                ephemeral=True
            )

        except Exception as e:

            print(
                f"❌ Manual restore failed: {e}"
            )

            traceback.print_exc()

            await interaction.followup.send(
                "❌ **Restore Failed**\n\n"
                f"`{e}`",
                ephemeral=True
            )

    # ========================================================
    # /REFRESH
    # ========================================================

    @app_commands.command(
        name="refresh",
        description="Refresh and show saved configuration files."
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

        if not self.pool or not self.database_ready:

            await interaction.followup.send(
                "🔴 Database is offline.",
                ephemeral=True
            )

            return

        try:

            async with self.pool.acquire() as connection:

                rows = await connection.fetch(
                    """
                    SELECT filename, updated_at
                    FROM bot_config_files
                    ORDER BY filename
                    """
                )

            if not rows:

                await interaction.followup.send(
                    "📭 No configurations are saved.",
                    ephemeral=True
                )

                return

            lines = []

            for row in rows:

                filename = row["filename"]

                updated_at = row["updated_at"]

                lines.append(
                    f"📄 `{filename}`"
                )

            message = (
                "🧠 **MasterConfig**\n\n"
                f"📦 Saved configurations: "
                f"`{len(rows)}`\n\n"
                + "\n".join(lines)
            )

            # Discord messages cannot exceed 2000 chars.
            if len(message) > 1900:

                message = (
                    "🧠 **MasterConfig**\n\n"
                    f"📦 Saved configurations: "
                    f"`{len(rows)}`\n\n"
                )

                for row in rows:

                    line = (
                        f"📄 `{row['filename']}`\n"
                    )

                    if len(message) + len(line) >= 1900:
                        message += "..."
                        break

                    message += line

            await interaction.followup.send(
                message,
                ephemeral=True
            )

        except Exception as e:

            print(
                f"❌ Refresh failed: {e}"
            )

            traceback.print_exc()

            await interaction.followup.send(
                f"❌ Refresh failed:\n`{e}`",
                ephemeral=True
            )

    # ========================================================
    # COMMAND ERROR HANDLER
    # ========================================================

    @dbstatus.error
    @configcount.error
    @backup.error
    @restore.error
    @refresh.error
    async def command_error(
        self,
        interaction: discord.Interaction,
        error
    ):

        if isinstance(
            error,
            app_commands.errors.MissingPermissions
        ):

            message = (
                "⛔ **Administrator permission required.**"
            )

        else:

            print(
                f"❌ MasterConfig command error: {error}"
            )

            traceback.print_exc()

            message = (
                "❌ An unexpected error occurred."
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


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        MasterConfig(bot)
    )

    print(
        "🧠 Loaded FIRST: masterconfig.py"
    )

# # ============================================================
# # MASTER CONFIG
# # Supabase PostgreSQL persistent configuration system
# # ============================================================

# import os
# import json
# import asyncio
# import traceback
# from datetime import datetime, timezone

# import asyncpg
# import discord

# from discord.ext import commands, tasks
# from discord import app_commands


# # ============================================================
# # SETTINGS
# # ============================================================

# DATABASE_URL = os.getenv("DATABASE_URL")

# BACKUP_INTERVAL = 30

# SKIP_DIRECTORIES = {
#     ".git",
#     ".github",
#     ".venv",
#     "venv",
#     "__pycache__",
#     "node_modules",
#     ".cache",
#     ".pytest_cache",
# }


# # ============================================================
# # HELPERS
# # ============================================================

# def utc_now():
#     return datetime.now(timezone.utc).isoformat()


# def read_json(path):

#     try:

#         if not os.path.exists(path):
#             return None

#         with open(
#             path,
#             "r",
#             encoding="utf-8"
#         ) as file:

#             return json.load(file)

#     except Exception as e:

#         print(
#             f"❌ JSON read failed "
#             f"{path}: {e}"
#         )

#         return None


# def write_json(path, data):

#     try:

#         directory = os.path.dirname(path)

#         if directory:
#             os.makedirs(
#                 directory,
#                 exist_ok=True
#             )

#         temporary = path + ".tmp"

#         with open(
#             temporary,
#             "w",
#             encoding="utf-8"
#         ) as file:

#             json.dump(
#                 data,
#                 file,
#                 indent=4,
#                 ensure_ascii=False
#             )

#         os.replace(
#             temporary,
#             path
#         )

#         return True

#     except Exception as e:

#         print(
#             f"❌ JSON write failed "
#             f"{path}: {e}"
#         )

#         return False


# # ============================================================
# # FIND JSON FILES
# # ============================================================

# def find_json_files():

#     result = []

#     base = os.getcwd()

#     for root, dirs, files in os.walk(base):

#         dirs[:] = [
#             d for d in dirs
#             if d not in SKIP_DIRECTORIES
#             and not d.startswith(".")
#         ]

#         for filename in files:

#             if not filename.lower().endswith(".json"):
#                 continue

#             full_path = os.path.join(
#                 root,
#                 filename
#             )

#             relative_path = os.path.relpath(
#                 full_path,
#                 base
#             )

#             relative_path = relative_path.replace(
#                 os.sep,
#                 "/"
#             )

#             # Ignore package files.
#             if relative_path in {
#                 "package.json",
#                 "package-lock.json"
#             }:
#                 continue

#             result.append(
#                 (
#                     relative_path,
#                     full_path
#                 )
#             )

#     return sorted(result)


# # ============================================================
# # MASTER CONFIG COG
# # ============================================================

# class MasterConfig(commands.Cog):

#     def __init__(self, bot):

#         self.bot = bot

#         self.pool = None

#         self.database_ready = False

#         self.last_backup = None

#         self.backup_status = "Starting"

#         print(
#             "=========================================="
#         )

#         print(
#             "🧠 MASTER CONFIG"
#         )

#         print(
#             "=========================================="
#         )

#         print(
#             "💾 Storage: Supabase PostgreSQL"
#         )

#     # ========================================================
#     # LOAD
#     # ========================================================

#     async def cog_load(self):

#         print(
#             "🧠 MasterConfig loading..."
#         )

#         if not DATABASE_URL:

#             print(
#                 "❌ DATABASE_URL is missing."
#             )

#             print(
#                 "❌ Add DATABASE_URL in Render."
#             )

#             return

#         try:

#             await self.connect_database()

#             if not self.database_ready:
#                 return

#             await self.create_tables()

#             # Restore saved configuration BEFORE
#             # other cogs are loaded.
#             await self.restore_all_configs()

#             self.backup_loop.start()

#             print(
#                 "✅ MasterConfig database system ready."
#             )

#         except Exception as e:

#             print(
#                 f"❌ MasterConfig startup error: {e}"
#             )

#             traceback.print_exc()

#     # ========================================================
#     # DATABASE CONNECTION
#     # ========================================================

#     async def connect_database(self):

#         try:

#             print(
#                 "🔌 Connecting to Supabase..."
#             )

#             # ------------------------------------------------
#             # IMPORTANT
#             #
#             # Pass the COMPLETE DATABASE_URL directly.
#             #
#             # Do NOT:
#             # - resolve the hostname manually
#             # - convert it to an IP
#             # - use ipaddress.ip_address()
#             # ------------------------------------------------

#             self.pool = await asyncpg.create_pool(
#                 dsn=DATABASE_URL,
#                 min_size=1,
#                 max_size=5,
#                 command_timeout=30,
#                 ssl="require"
#             )

#             # Test connection.

#             async with self.pool.acquire() as connection:

#                 result = await connection.fetchval(
#                     "SELECT 1"
#                 )

#                 if result != 1:

#                     raise RuntimeError(
#                         "Database test query failed."
#                     )

#             self.database_ready = True

#             print(
#                 "✅ Supabase PostgreSQL connected"
#             )

#         except Exception as e:

#             self.database_ready = False

#             if self.pool:

#                 try:
#                     await self.pool.close()
#                 except Exception:
#                     pass

#             self.pool = None

#             print(
#                 f"❌ Database connection failed: {e}"
#             )

#             traceback.print_exc()

#     # ========================================================
#     # CREATE TABLE
#     # ========================================================

#     async def create_tables(self):

#         if not self.pool:
#             return

#         async with self.pool.acquire() as connection:

#             await connection.execute(
#                 """
#                 CREATE TABLE IF NOT EXISTS
#                 bot_config_files
#                 (
#                     config_path TEXT PRIMARY KEY,

#                     config_data JSONB NOT NULL,

#                     updated_at
#                     TIMESTAMPTZ
#                     DEFAULT NOW()
#                 )
#                 """
#             )

#         print(
#             "✅ bot_config_files table ready"
#         )

#     # ========================================================
#     # SAVE CONFIG
#     # ========================================================

#     async def save_config_file(
#         self,
#         relative_path,
#         full_path
#     ):

#         if not self.pool:
#             return False

#         data = read_json(
#             full_path
#         )

#         if data is None:
#             return False

#         try:

#             async with self.pool.acquire() as connection:

#                 await connection.execute(
#                     """
#                     INSERT INTO bot_config_files
#                     (
#                         config_path,
#                         config_data,
#                         updated_at
#                     )

#                     VALUES
#                     (
#                         $1,
#                         $2::jsonb,
#                         NOW()
#                     )

#                     ON CONFLICT
#                     (
#                         config_path
#                     )

#                     DO UPDATE SET

#                         config_data =
#                         EXCLUDED.config_data,

#                         updated_at =
#                         NOW()
#                     """,

#                     relative_path,

#                     json.dumps(
#                         data,
#                         ensure_ascii=False
#                     )
#                 )

#             return True

#         except Exception as e:

#             print(
#                 f"❌ Failed saving "
#                 f"{relative_path}: {e}"
#             )

#             return False

#     # ========================================================
#     # RESTORE ALL
#     # ========================================================

#     async def restore_all_configs(self):

#         if not self.pool:
#             return

#         print(
#             "♻️ Checking saved configurations..."
#         )

#         try:

#             async with self.pool.acquire() as connection:

#                 rows = await connection.fetch(
#                     """
#                     SELECT
#                         config_path,
#                         config_data

#                     FROM bot_config_files
#                     """
#                 )

#             if not rows:

#                 print(
#                     "ℹ️ No previous configurations "
#                     "found in Supabase."
#                 )

#                 print(
#                     "💾 Creating first backup..."
#                 )

#                 await self.backup_all_configs(
#                     silent=False
#                 )

#                 return

#             restored = 0

#             database_paths = set()

#             for row in rows:

#                 relative_path = row[
#                     "config_path"
#                 ]

#                 data = row[
#                     "config_data"
#                 ]

#                 database_paths.add(
#                     relative_path
#                 )

#                 full_path = os.path.join(
#                     os.getcwd(),
#                     relative_path
#                 )

#                 if write_json(
#                     full_path,
#                     data
#                 ):

#                     restored += 1

#                     print(
#                         f"♻️ Restored: "
#                         f"{relative_path}"
#                     )

#             print(
#                 f"✅ Restored "
#                 f"{restored} configuration files."
#             )

#             # ------------------------------------------------
#             # Find new local JSON files.
#             # ------------------------------------------------

#             local_files = find_json_files()

#             new_files = 0

#             for relative_path, full_path in local_files:

#                 if relative_path not in database_paths:

#                     if await self.save_config_file(
#                         relative_path,
#                         full_path
#                     ):

#                         new_files += 1

#                         print(
#                             f"🆕 New config saved: "
#                             f"{relative_path}"
#                         )

#             if new_files:

#                 print(
#                     f"✅ Added "
#                     f"{new_files} new configuration files."
#                 )

#         except Exception as e:

#             print(
#                 f"❌ Configuration restore failed: {e}"
#             )

#             traceback.print_exc()

#     # ========================================================
#     # BACKUP ALL
#     # ========================================================

#     async def backup_all_configs(
#         self,
#         silent=True
#     ):

#         if not self.pool:
#             return 0

#         files = find_json_files()

#         saved = 0

#         for relative_path, full_path in files:

#             if await self.save_config_file(
#                 relative_path,
#                 full_path
#             ):

#                 saved += 1

#                 if not silent:

#                     print(
#                         f"💾 Saved: "
#                         f"{relative_path}"
#                     )

#         self.last_backup = datetime.now(
#             timezone.utc
#         )

#         self.backup_status = (
#             f"{saved} files backed up"
#         )

#         return saved

#     # ========================================================
#     # AUTOMATIC BACKUP
#     # ========================================================

#     @tasks.loop(
#         seconds=BACKUP_INTERVAL
#     )
#     async def backup_loop(self):

#         if not self.database_ready:
#             return

#         try:

#             count = await self.backup_all_configs(
#                 silent=True
#             )

#             print(
#                 f"💾 Auto-backup: "
#                 f"{count} configuration files"
#             )

#         except Exception as e:

#             print(
#                 f"❌ Auto-backup failed: {e}"
#             )

#     @backup_loop.before_loop
#     async def before_backup_loop(self):

#         await self.bot.wait_until_ready()

#     # ========================================================
#     # /DBSTATUS
#     # ========================================================

#     @app_commands.command(
#         name="dbstatus",
#         description="Check the Supabase database."
#     )
#     @app_commands.checks.has_permissions(
#         administrator=True
#     )
#     async def dbstatus(
#         self,
#         interaction: discord.Interaction
#     ):

#         if not self.pool:

#             await interaction.response.send_message(
#                 "🔴 **Database Offline**",
#                 ephemeral=True
#             )

#             return

#         try:

#             async with self.pool.acquire() as connection:

#                 await connection.fetchval(
#                     "SELECT 1"
#                 )

#                 count = await connection.fetchval(
#                     """
#                     SELECT COUNT(*)
#                     FROM bot_config_files
#                     """
#                 )

#             await interaction.response.send_message(
#                 "🟢 **Database Connected**\n\n"
#                 f"💾 Saved configurations: `{count}`\n"
#                 "☁️ Storage: `Supabase PostgreSQL`\n"
#                 "🔄 Auto-backup: `Active`",
#                 ephemeral=True
#             )

#         except Exception as e:

#             await interaction.response.send_message(
#                 f"🔴 **Database Error**\n\n"
#                 f"`{e}`",
#                 ephemeral=True
#             )

#     # ========================================================
#     # /CONFIGCOUNT
#     # ========================================================

#     @app_commands.command(
#         name="configcount",
#         description="Show stored configuration count."
#     )
#     @app_commands.checks.has_permissions(
#         administrator=True
#     )
#     async def configcount(
#         self,
#         interaction: discord.Interaction
#     ):

#         if not self.pool:

#             await interaction.response.send_message(
#                 "🔴 Database is offline.",
#                 ephemeral=True
#             )

#             return

#         try:

#             async with self.pool.acquire() as connection:

#                 count = await connection.fetchval(
#                     """
#                     SELECT COUNT(*)
#                     FROM bot_config_files
#                     """
#                 )

#             await interaction.response.send_message(
#                 f"💾 **Stored configurations:** `{count}`",
#                 ephemeral=True
#             )

#         except Exception as e:

#             await interaction.response.send_message(
#                 f"❌ `{e}`",
#                 ephemeral=True
#             )

#     # ========================================================
#     # /BACKUP
#     # ========================================================

#     @app_commands.command(
#         name="backup",
#         description="Save all bot configuration files."
#     )
#     @app_commands.checks.has_permissions(
#         administrator=True
#     )
#     async def backup(
#         self,
#         interaction: discord.Interaction
#     ):

#         await interaction.response.defer(
#             ephemeral=True
#         )

#         if not self.pool:

#             await interaction.followup.send(
#                 "🔴 Database is offline.",
#                 ephemeral=True
#             )

#             return

#         try:

#             count = await self.backup_all_configs(
#                 silent=False
#             )

#             await interaction.followup.send(
#                 "✅ **Backup Complete**\n\n"
#                 f"💾 Saved: `{count}` configuration files\n"
#                 "☁️ Storage: `Supabase PostgreSQL`",
#                 ephemeral=True
#             )

#         except Exception as e:

#             await interaction.followup.send(
#                 f"❌ Backup failed:\n`{e}`",
#                 ephemeral=True
#             )

#     # ========================================================
#     # /REFRESH
#     # ========================================================

#     @app_commands.command(
#         name="refresh",
#         description="Show the complete bot configuration."
#     )
#     @app_commands.checks.has_permissions(
#         administrator=True
#     )
#     async def refresh(
#         self,
#         interaction: discord.Interaction
#     ):

#         await interaction.response.defer(
#             ephemeral=True
#         )

#         # ----------------------------------------------------
#         # COGS
#         # ----------------------------------------------------

#         cogs = list(
#             self.bot.cogs.values()
#         )

#         # ----------------------------------------------------
#         # COMMANDS
#         # ----------------------------------------------------

#         commands_list = []

#         try:

#             for command in self.bot.tree.walk_commands():

#                 commands_list.append(
#                     "/" + command.qualified_name
#                 )

#         except Exception:

#             pass

#         commands_list = sorted(
#             set(commands_list)
#         )

#         # ----------------------------------------------------
#         # LOCAL CONFIG FILES
#         # ----------------------------------------------------

#         local_files = find_json_files()

#         # ----------------------------------------------------
#         # DATABASE FILES
#         # ----------------------------------------------------

#         database_files = []

#         if self.pool:

#             try:

#                 async with self.pool.acquire() as connection:

#                     rows = await connection.fetch(
#                         """
#                         SELECT config_path
#                         FROM bot_config_files
#                         ORDER BY config_path
#                         """
#                     )

#                 database_files = [
#                     row["config_path"]
#                     for row in rows
#                 ]

#             except Exception:
#                 database_files = []

#         # ----------------------------------------------------
#         # COUNTS
#         # ----------------------------------------------------

#         configured = len(database_files)

#         local_count = len(local_files)

#         warnings = 0

#         if not self.database_ready:

#             warnings += 1

#         # ----------------------------------------------------
#         # SUMMARY EMBED
#         # ----------------------------------------------------

#         embed = discord.Embed(
#             title="📊 REFRESH SUMMARY",
#             color=(
#                 discord.Color.green()
#                 if self.database_ready
#                 else discord.Color.red()
#             )
#         )

#         embed.description = (
#             f"📦 **Cogs loaded:** "
#             f"`{len(cogs)}`\n\n"

#             f"⚙️ **Commands detected:** "
#             f"`{len(commands_list)}`\n\n"

#             f"💾 **Local JSON files:** "
#             f"`{local_count}`\n\n"

#             f"☁️ **Saved in Supabase:** "
#             f"`{configured}`\n\n"

#             f"🟢 **Database:** "
#             f"`{'Connected' if self.database_ready else 'Offline'}`\n\n"

#             f"🔄 **Automatic backup:** "
#             f"`{'Active' if self.database_ready else 'Offline'}`\n\n"

#             f"⚠️ **Warnings:** "
#             f"`{warnings}`"
#         )

#         embed.set_footer(
#             text=f"Requested by {interaction.user}"
#         )

#         await interaction.followup.send(
#             embed=embed,
#             ephemeral=True
#         )

#         # ----------------------------------------------------
#         # DATABASE FILE LIST
#         # ----------------------------------------------------

#         if database_files:

#             # Discord embed field limit workaround.
#             chunks = []

#             current = []

#             for path in database_files:

#                 current.append(
#                     f"☁️ `{path}`"
#                 )

#                 if len(current) >= 20:

#                     chunks.append(
#                         "\n".join(current)
#                     )

#                     current = []

#             if current:

#                 chunks.append(
#                     "\n".join(current)
#                 )

#             for index, chunk in enumerate(chunks):

#                 page = discord.Embed(
#                     title=(
#                         "☁️ SAVED CONFIGURATIONS"
#                         + (
#                             f" — {index + 1}"
#                             if len(chunks) > 1
#                             else ""
#                         )
#                     ),
#                     description=chunk,
#                     color=discord.Color.blurple()
#                 )

#                 await interaction.followup.send(
#                     embed=page,
#                     ephemeral=True
#                 )

#         else:

#             await interaction.followup.send(
#                 "⚪ No configurations are currently "
#                 "stored in Supabase.",
#                 ephemeral=True
#             )

#     # ========================================================
#     # ERROR HANDLER
#     # ========================================================

#     @dbstatus.error
#     @configcount.error
#     @backup.error
#     @refresh.error
#     async def command_error(
#         self,
#         interaction,
#         error
#     ):

#         if isinstance(
#             error,
#             app_commands.errors.MissingPermissions
#         ):

#             message = (
#                 "❌ You need **Administrator** "
#                 "permission to use this command."
#             )

#         else:

#             traceback.print_exc()

#             message = (
#                 f"❌ Error:\n`{error}`"
#             )

#         try:

#             if interaction.response.is_done():

#                 await interaction.followup.send(
#                     message,
#                     ephemeral=True
#                 )

#             else:

#                 await interaction.response.send_message(
#                     message,
#                     ephemeral=True
#                 )

#         except Exception:

#             pass

#     # ========================================================
#     # UNLOAD
#     # ========================================================

#     async def cog_unload(self):

#         print(
#             "🛑 MasterConfig shutting down..."
#         )

#         try:

#             if self.backup_loop.is_running():

#                 self.backup_loop.cancel()

#         except Exception:
#             pass

#         # Final backup.

#         try:

#             if self.pool:

#                 count = await self.backup_all_configs(
#                     silent=False
#                 )

#                 print(
#                     f"💾 Final backup: "
#                     f"{count} files"
#                 )

#         except Exception as e:

#             print(
#                 f"⚠️ Final backup failed: {e}"
#             )

#         # Close pool.

#         try:

#             if self.pool:

#                 await self.pool.close()

#                 print(
#                     "🔌 Database connection closed"
#                 )

#         except Exception as e:

#             print(
#                 f"⚠️ Database close failed: {e}"
#             )


# # ============================================================
# # SETUP
# # ============================================================

# async def setup(bot):

#     await bot.add_cog(
#         MasterConfig(bot)
#     )

#     print(
#         "📦 MasterConfig cog loaded"
#     )

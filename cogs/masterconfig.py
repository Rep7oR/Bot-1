# cogs/masterconfig.py

import os
import json
import asyncio
import asyncpg
import discord

from discord.ext import commands
from discord import app_commands


class MasterConfig(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.pool = None
        self.database_url = os.getenv("DATABASE_URL")

        print("🧠 MasterConfig loading...")

    # =========================================================
    # DATABASE CONNECTION
    # =========================================================

    async def cog_load(self):

        if not self.database_url:
            print("❌ DATABASE_URL is not set in Render.")
            return

        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5,
                command_timeout=30,
                ssl="require"
            )

            print("✅ Supabase PostgreSQL connected")

            await self.create_tables()

        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            self.pool = None

    # =========================================================
    # CREATE DATABASE TABLE
    # =========================================================

    async def create_tables(self):

        if not self.pool:
            return

        async with self.pool.acquire() as conn:

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_config (
                    guild_id BIGINT NOT NULL,
                    config_key TEXT NOT NULL,
                    config_value TEXT,
                    updated_at TIMESTAMPTZ DEFAULT NOW(),

                    PRIMARY KEY (guild_id, config_key)
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_bot_config_guild
                ON bot_config(guild_id)
            """)

        print("✅ bot_config table ready")

    # =========================================================
    # SAVE CONFIGURATION
    # =========================================================

    async def set_config(
        self,
        guild_id: int,
        key: str,
        value
    ):

        if not self.pool:
            print(
                f"⚠️ Database unavailable. "
                f"Could not save: {key}"
            )
            return False

        try:

            # Convert dictionaries/lists to JSON
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            # Convert other values to strings
            else:
                value = str(value)

            async with self.pool.acquire() as conn:

                await conn.execute("""
                    INSERT INTO bot_config
                    (
                        guild_id,
                        config_key,
                        config_value,
                        updated_at
                    )

                    VALUES ($1, $2, $3, NOW())

                    ON CONFLICT (
                        guild_id,
                        config_key
                    )

                    DO UPDATE SET
                        config_value = EXCLUDED.config_value,
                        updated_at = NOW()
                """,
                    guild_id,
                    key,
                    value
                )

            print(
                f"💾 Saved config: "
                f"{guild_id} → {key}"
            )

            return True

        except Exception as e:

            print(
                f"❌ Failed to save "
                f"{key}: {e}"
            )

            return False

    # =========================================================
    # GET CONFIGURATION
    # =========================================================

    async def get_config(
        self,
        guild_id: int,
        key: str,
        default=None
    ):

        if not self.pool:
            return default

        try:

            async with self.pool.acquire() as conn:

                row = await conn.fetchrow("""
                    SELECT config_value
                    FROM bot_config

                    WHERE guild_id = $1
                    AND config_key = $2
                """,
                    guild_id,
                    key
                )

            if not row:
                return default

            value = row["config_value"]

            # Try to decode JSON
            try:
                return json.loads(value)

            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:

            print(
                f"❌ Failed to get "
                f"{key}: {e}"
            )

            return default

    # =========================================================
    # GET ALL CONFIGURATION FOR A SERVER
    # =========================================================

    async def get_all_config(
        self,
        guild_id: int
    ):

        if not self.pool:
            return {}

        try:

            async with self.pool.acquire() as conn:

                rows = await conn.fetch("""
                    SELECT
                        config_key,
                        config_value,
                        updated_at

                    FROM bot_config

                    WHERE guild_id = $1

                    ORDER BY config_key
                """,
                    guild_id
                )

            result = {}

            for row in rows:

                value = row["config_value"]

                try:
                    value = json.loads(value)

                except (json.JSONDecodeError, TypeError):
                    pass

                result[row["config_key"]] = {
                    "value": value,
                    "updated_at": row["updated_at"]
                }

            return result

        except Exception as e:

            print(
                f"❌ Failed to load "
                f"configuration: {e}"
            )

            return {}

    # =========================================================
    # DELETE CONFIGURATION
    # =========================================================

    async def delete_config(
        self,
        guild_id: int,
        key: str
    ):

        if not self.pool:
            return False

        try:

            async with self.pool.acquire() as conn:

                await conn.execute("""
                    DELETE FROM bot_config

                    WHERE guild_id = $1
                    AND config_key = $2
                """,
                    guild_id,
                    key
                )

            print(
                f"🗑️ Deleted config: "
                f"{guild_id} → {key}"
            )

            return True

        except Exception as e:

            print(
                f"❌ Failed to delete "
                f"{key}: {e}"
            )

            return False

    # =========================================================
    # DATABASE STATUS
    # =========================================================

    @app_commands.command(
        name="dbstatus",
        description="Check the database connection."
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
                "🔴 Database is not connected.\n\n"
                "Check the `DATABASE_URL` environment "
                "variable in Render.",
                ephemeral=True
            )

            return

        try:

            async with self.pool.acquire() as conn:

                await conn.fetchval(
                    "SELECT 1"
                )

            await interaction.response.send_message(
                "🟢 **Database Connected**\n\n"
                "Supabase PostgreSQL is working correctly.",
                ephemeral=True
            )

        except Exception as e:

            await interaction.response.send_message(
                f"🔴 **Database Error**\n\n"
                f"`{e}`",
                ephemeral=True
            )

    # =========================================================
    # REFRESH COMMAND
    # =========================================================

    @app_commands.command(
        name="refresh",
        description="Show all saved bot configuration."
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

        configs = await self.get_all_config(
            interaction.guild.id
        )

        if not configs:

            embed = discord.Embed(
                title="🔄 Bot Configuration",
                description=(
                    "⚠️ No configuration has been "
                    "saved in the database yet."
                ),
                color=discord.Color.orange()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="🔄 Bot Configuration",
            description=(
                f"Saved configuration for "
                f"**{interaction.guild.name}**"
            ),
            color=discord.Color.blurple()
        )

        # =====================================================
        # BUILD CONFIGURATION LIST
        # =====================================================

        lines = []

        for key, data in configs.items():

            value = data["value"]

            # Make Discord IDs easier to read
            if isinstance(value, str) and value.isdigit():

                try:

                    numeric_id = int(value)

                    channel = interaction.guild.get_channel(
                        numeric_id
                    )

                    role = interaction.guild.get_role(
                        numeric_id
                    )

                    if channel:
                        value = (
                            f"{channel.mention} "
                            f"`{numeric_id}`"
                        )

                    elif role:
                        value = (
                            f"{role.mention} "
                            f"`{numeric_id}`"
                        )

                    else:
                        value = f"`{numeric_id}`"

                except Exception:
                    value = f"`{value}`"

            elif isinstance(value, bool):

                value = "✅ Enabled" if value else "❌ Disabled"

            elif isinstance(value, (dict, list)):

                value = json.dumps(
                    value,
                    indent=2
                )

            else:

                value = str(value)

            # Prevent Discord embed overflow
            if len(value) > 500:

                value = value[:497] + "..."

            lines.append(
                f"**{key}**\n"
                f"{value}\n"
            )

        # =====================================================
        # DISCORD EMBED LIMIT
        # =====================================================

        description = ""

        embeds = []

        for line in lines:

            if len(description) + len(line) > 3900:

                new_embed = discord.Embed(
                    title="🔄 Bot Configuration",
                    description=description,
                    color=discord.Color.blurple()
                )

                embeds.append(new_embed)

                description = ""

            description += line

        if description:

            new_embed = discord.Embed(
                title="🔄 Bot Configuration",
                description=description,
                color=discord.Color.blurple()
            )

            embeds.append(new_embed)

        # =====================================================
        # SEND EMBEDS
        # =====================================================

        for index, embed in enumerate(embeds):

            embed.set_footer(
                text=(
                    f"Configuration page "
                    f"{index + 1}/{len(embeds)}"
                )
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

    # =========================================================
    # DATABASE INFORMATION
    # =========================================================

    @app_commands.command(
        name="configcount",
        description="Show how many configurations are saved."
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
                "🔴 Database is not connected.",
                ephemeral=True
            )

            return

        try:

            async with self.pool.acquire() as conn:

                count = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM bot_config
                    WHERE guild_id = $1
                """,
                    interaction.guild.id
                )

            await interaction.response.send_message(
                f"💾 **Saved configurations:** `{count}`",
                ephemeral=True
            )

        except Exception as e:

            await interaction.response.send_message(
                f"❌ Error: `{e}`",
                ephemeral=True
            )

    # =========================================================
    # CLEANUP
    # =========================================================

    async def cog_unload(self):

        if self.pool:

            try:

                await self.pool.close()

                print(
                    "🔌 PostgreSQL connection closed"
                )

            except Exception as e:

                print(
                    f"⚠️ Database close error: {e}"
                )


# =============================================================
# SETUP
# =============================================================

async def setup(bot):

    await bot.add_cog(
        MasterConfig(bot)
    )

    print(
        "✅ MasterConfig cog loaded"
    )

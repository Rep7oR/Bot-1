import discord
from discord.ext import commands, tasks
from discord import app_commands

import json
import os


# ============================================================
# CONFIGURATION
# ============================================================

MODERATOR_ROLE_NAME = "Moderator"

DATA_FILE = "moderator_stats.json"

UPDATE_INTERVAL = 30


# ============================================================
# DATA
# ============================================================

def load_data():

    if not os.path.exists(DATA_FILE):

        return {
            "guilds": {}
        }

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            f"[MOD STATS] Failed to load data: {e}"
        )

        return {
            "guilds": {}
        }


stats_data = load_data()


def save_data():

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                stats_data,
                f,
                indent=4
            )

    except Exception as e:

        print(
            f"[MOD STATS] Failed to save data: {e}"
        )


def get_guild_data(
    guild_id: int
):

    guild_id = str(guild_id)

    if guild_id not in stats_data["guilds"]:

        stats_data["guilds"][guild_id] = {

            "ticket_channel_id": None,

            "clan_channel_id": None
        }

    return stats_data["guilds"][guild_id]


# ============================================================
# MODERATOR CHECK
# ============================================================

def is_moderator(
    member: discord.Member
):

    role = discord.utils.get(
        member.guild.roles,
        name=MODERATOR_ROLE_NAME
    )

    if role is None:

        return False

    return role in member.roles


# ============================================================
# MODERATOR STATISTICS COG
# ============================================================

class ModeratorStats(
    commands.Cog
):

    def __init__(
        self,
        bot: commands.Bot
    ):

        self.bot = bot

        self.update_channels.start()

    # ========================================================
    # CLEANUP
    # ========================================================

    def cog_unload(self):

        self.update_channels.cancel()

    # ========================================================
    # READY
    # ========================================================

    @commands.Cog.listener()
    async def on_ready(self):

        print(
            "✅ Moderator statistics system online"
        )

    # ========================================================
    # UPDATE VOICE CHANNELS
    # ========================================================

    @tasks.loop(seconds=UPDATE_INTERVAL)
    async def update_channels(self):

        for guild in self.bot.guilds:

            try:

                await self.update_guild(
                    guild
                )

            except Exception as e:

                print(
                    f"[MOD STATS] "
                    f"{guild.name}: {e}"
                )

    # ========================================================
    # WAIT UNTIL BOT READY
    # ========================================================

    @update_channels.before_loop
    async def before_update_channels(self):

        await self.bot.wait_until_ready()

    # ========================================================
    # UPDATE ONE SERVER
    # ========================================================

    async def update_guild(
        self,
        guild: discord.Guild
    ):

        guild_data = get_guild_data(
            guild.id
        )

        # ----------------------------------------------------
        # TICKETS
        # ----------------------------------------------------

        ticket_channel_id = guild_data.get(
            "ticket_channel_id"
        )

        if ticket_channel_id:

            ticket_channel = guild.get_channel(
                ticket_channel_id
            )

            if ticket_channel:

                ticket_count = await self.get_ticket_count(
                    guild
                )

                new_name = (
                    f"🎫 Tickets: {ticket_count}"
                )

                if ticket_channel.name != new_name:

                    try:

                        await ticket_channel.edit(
                            name=new_name,
                            reason=(
                                "Updating ticket statistics"
                            )
                        )

                    except discord.Forbidden:

                        print(
                            f"[MOD STATS] Cannot edit "
                            f"{ticket_channel.name}"
                        )

        # ----------------------------------------------------
        # CLAN APPLICATIONS
        # ----------------------------------------------------

        clan_channel_id = guild_data.get(
            "clan_channel_id"
        )

        if clan_channel_id:

            clan_channel = guild.get_channel(
                clan_channel_id
            )

            if clan_channel:

                clan_count = await self.get_clan_count(
                    guild
                )

                new_name = (
                    f"⚔️ Clan Applications: "
                    f"{clan_count}"
                )

                if clan_channel.name != new_name:

                    try:

                        await clan_channel.edit(
                            name=new_name,
                            reason=(
                                "Updating clan application statistics"
                            )
                        )

                    except discord.Forbidden:

                        print(
                            f"[MOD STATS] Cannot edit "
                            f"{clan_channel.name}"
                        )

    # ========================================================
    # COUNT TICKETS
    # ========================================================

    async def get_ticket_count(
        self,
        guild: discord.Guild
    ):

        count = 0

        # ----------------------------------------------------
        # OPTION 1:
        # Count channels inside a TICKETS category
        # ----------------------------------------------------

        ticket_category = discord.utils.find(
            lambda category:
                category.name.lower()
                in [
                    "tickets",
                    "ticket",
                    "support tickets"
                ],
            guild.categories
        )

        if ticket_category:

            count = len(
                ticket_category.channels
            )

        return count

    # ========================================================
    # COUNT CLAN APPLICATIONS
    # ========================================================

    async def get_clan_count(
        self,
        guild: discord.Guild
    ):

        # ----------------------------------------------------
        # Try to use the clan system's stored applications.
        # ----------------------------------------------------

        try:

            from cogs.clan_manager_cog import (
                get_guild_data
            )

            clan_data = get_guild_data(
                guild.id
            )

            return len(
                clan_data.get(
                    "pending",
                    {}
                )
            )

        except Exception:

            return 0

    # ========================================================
    # CREATE MODERATOR CATEGORY
    # ========================================================

    @app_commands.command(
        name="setupmodstats",
        description=(
            "Create the private moderator statistics system"
        )
    )
    async def setupmodstats(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This can only be used in a server.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # MODERATOR CHECK
        # ----------------------------------------------------

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(
                f"❌ You need the "
                f"**{MODERATOR_ROLE_NAME}** role.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # FIND MODERATOR ROLE
        # ----------------------------------------------------

        moderator_role = discord.utils.get(
            guild.roles,
            name=MODERATOR_ROLE_NAME
        )

        if moderator_role is None:

            await interaction.response.send_message(
                f"❌ Role **{MODERATOR_ROLE_NAME}** "
                f"does not exist.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        # ----------------------------------------------------
        # FIND / CREATE CATEGORY
        # ----------------------------------------------------

        category = discord.utils.get(
            guild.categories,
            name="MODERATOR STATS"
        )

        if category is None:

            overwrites = {

                guild.default_role:
                    discord.PermissionOverwrite(
                        view_channel=False
                    ),

                moderator_role:
                    discord.PermissionOverwrite(
                        view_channel=True,
                        connect=True,
                        speak=False
                    )
            }

            category = await guild.create_category(
                name="MODERATOR STATS",
                overwrites=overwrites,
                reason="Moderator statistics system"
            )

        else:

            await category.set_permissions(
                guild.default_role,
                view_channel=False
            )

            await category.set_permissions(
                moderator_role,
                view_channel=True
            )

        # ----------------------------------------------------
        # TICKET CHANNEL
        # ----------------------------------------------------

        ticket_channel = None

        guild_data = get_guild_data(
            guild.id
        )

        existing_ticket_id = guild_data.get(
            "ticket_channel_id"
        )

        if existing_ticket_id:

            ticket_channel = guild.get_channel(
                existing_ticket_id
            )

        if ticket_channel is None:

            ticket_channel = (
                await guild.create_voice_channel(
                    name="🎫 Tickets: 0",
                    category=category,
                    reason="Moderator ticket statistics"
                )
            )

            guild_data[
                "ticket_channel_id"
            ] = ticket_channel.id

        # ----------------------------------------------------
        # CLAN APPLICATION CHANNEL
        # ----------------------------------------------------

        clan_channel = None

        existing_clan_id = guild_data.get(
            "clan_channel_id"
        )

        if existing_clan_id:

            clan_channel = guild.get_channel(
                existing_clan_id
            )

        if clan_channel is None:

            clan_channel = (
                await guild.create_voice_channel(
                    name="⚔️ Clan Applications: 0",
                    category=category,
                    reason="Moderator clan application statistics"
                )
            )

            guild_data[
                "clan_channel_id"
            ] = clan_channel.id

        # ----------------------------------------------------
        # PERMISSIONS
        # ----------------------------------------------------

        for channel in [
            ticket_channel,
            clan_channel
        ]:

            await channel.set_permissions(
                guild.default_role,
                view_channel=False,
                connect=False
            )

            await channel.set_permissions(
                moderator_role,
                view_channel=True,
                connect=True,
                speak=False
            )

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        save_data()

        # ----------------------------------------------------
        # UPDATE COUNTS
        # ----------------------------------------------------

        await self.update_guild(
            guild
        )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        embed = discord.Embed(
            title="📊 Moderator Statistics",
            description=(
                "The private moderator statistics "
                "system has been created."
            ),
            color=discord.Color.blue()
        )

        embed.add_field(
            name="🎫 Tickets",
            value=ticket_channel.mention,
            inline=False
        )

        embed.add_field(
            name="⚔️ Clan Applications",
            value=clan_channel.mention,
            inline=False
        )

        embed.set_footer(
            text=(
                "Only members with the "
                f"{MODERATOR_ROLE_NAME} role can see these."
            )
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot: commands.Bot
):

    await bot.add_cog(
        ModeratorStats(bot)
    )

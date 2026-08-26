import discord
from discord.ext import commands, tasks
from discord import app_commands

import json
import os


# ============================================================
# CONFIGURATION
# ============================================================

MODERATOR_ROLE_NAME = "MODERATOR"

DATA_FILE = "moderator_stats.json"

# Backup check
UPDATE_INTERVAL = 15


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
# MODERATOR STATISTICS
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

        # Update immediately
        for guild in self.bot.guilds:

            try:

                await self.update_guild(
                    guild
                )

            except Exception as e:

                print(
                    f"[MOD STATS] Initial update error "
                    f"in {guild.name}: {e}"
                )

    # ========================================================
    # BACKUP LOOP
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
    # WAIT UNTIL READY
    # ========================================================

    @update_channels.before_loop
    async def before_update_channels(
        self
    ):

        await self.bot.wait_until_ready()

    # ========================================================
    # PUBLIC FUNCTION
    #
    # Other Cogs can call:
    #
    # await stats.update_guild(guild)
    #
    # ========================================================

    async def update_guild(
        self,
        guild: discord.Guild
    ):

        guild_data = get_guild_data(
            guild.id
        )

        # ====================================================
        # TICKETS
        # ====================================================

        ticket_channel_id = (
            guild_data.get(
                "ticket_channel_id"
            )
        )

        if ticket_channel_id:

            ticket_channel = guild.get_channel(
                ticket_channel_id
            )

            if ticket_channel:

                ticket_count = (
                    self.get_ticket_count(
                        guild
                    )
                )

                new_name = (
                    f"🎫 Tickets: {ticket_count}"
                )

                if (
                    ticket_channel.name
                    != new_name
                ):

                    try:

                        await ticket_channel.edit(
                            name=new_name,
                            reason=(
                                "Updating ticket count"
                            )
                        )

                    except discord.Forbidden:

                        print(
                            "[MOD STATS] "
                            "Cannot rename ticket counter"
                        )

                    except discord.HTTPException as e:

                        print(
                            f"[MOD STATS] "
                            f"Ticket counter error: {e}"
                        )

        # ====================================================
        # CLAN APPLICATIONS
        # ====================================================

        clan_channel_id = (
            guild_data.get(
                "clan_channel_id"
            )
        )

        if clan_channel_id:

            clan_channel = guild.get_channel(
                clan_channel_id
            )

            if clan_channel:

                clan_count = (
                    self.get_clan_count(
                        guild
                    )
                )

                new_name = (
                    f"⚔️ Clan Applications: "
                    f"{clan_count}"
                )

                if (
                    clan_channel.name
                    != new_name
                ):

                    try:

                        await clan_channel.edit(
                            name=new_name,
                            reason=(
                                "Updating clan application count"
                            )
                        )

                    except discord.Forbidden:

                        print(
                            "[MOD STATS] "
                            "Cannot rename clan counter"
                        )

                    except discord.HTTPException as e:

                        print(
                            f"[MOD STATS] "
                            f"Clan counter error: {e}"
                        )

    # ========================================================
    # TICKET COUNT
    # ========================================================

    def get_ticket_count(
        self,
        guild: discord.Guild
    ) -> int:

        count = 0

        # ----------------------------------------------------
        # Look for common ticket categories
        # ----------------------------------------------------

        possible_names = {

            "tickets",
            "ticket",
            "support tickets",
            "support",
            "ticket support"
        }

        for category in guild.categories:

            if (
                category.name.lower().strip()
                in possible_names
            ):

                count += len(
                    category.channels
                )

        return count

    # ========================================================
    # CLAN COUNT
    # ========================================================

    def get_clan_count(
        self,
        guild: discord.Guild
    ) -> int:

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

        except Exception as e:

            print(
                f"[MOD STATS] "
                f"Could not read clan applications: "
                f"{e}"
            )

            return 0

    # ========================================================
    # MANUAL REFRESH
    # ========================================================

    @app_commands.command(
        name="refreshmodstats",
        description=(
            "Immediately refresh moderator statistics"
        )
    )
    async def refreshmodstats(
        self,
        interaction: discord.Interaction
    ):

        if interaction.guild is None:

            return

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(
                f"❌ You need the "
                f"**{MODERATOR_ROLE_NAME}** role.",
                ephemeral=True
            )

            return

        await self.update_guild(
            interaction.guild
        )

        await interaction.response.send_message(
            "✅ Moderator statistics refreshed.",
            ephemeral=True
        )

    # ========================================================
    # SETUP MODERATOR STATISTICS
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

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(
                f"❌ You need the "
                f"**{MODERATOR_ROLE_NAME}** role.",
                ephemeral=True
            )

            return

        moderator_role = discord.utils.get(
            guild.roles,
            name=MODERATOR_ROLE_NAME
        )

        if moderator_role is None:

            await interaction.response.send_message(
                f"❌ Role **{MODERATOR_ROLE_NAME}** "
                "does not exist.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        # ====================================================
        # CATEGORY
        # ====================================================

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

            category = (
                await guild.create_category(
                    name="MODERATOR STATS",
                    overwrites=overwrites,
                    reason=(
                        "Moderator statistics system"
                    )
                )
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

        guild_data = get_guild_data(
            guild.id
        )

        # ====================================================
        # TICKET COUNTER
        # ====================================================

        ticket_channel = None

        ticket_id = guild_data.get(
            "ticket_channel_id"
        )

        if ticket_id:

            ticket_channel = guild.get_channel(
                ticket_id
            )

        if ticket_channel is None:

            ticket_channel = (
                await guild.create_voice_channel(
                    name="🎫 Tickets: 0",
                    category=category,
                    reason=(
                        "Ticket statistics counter"
                    )
                )
            )

            guild_data[
                "ticket_channel_id"
            ] = ticket_channel.id

        # ====================================================
        # CLAN COUNTER
        # ====================================================

        clan_channel = None

        clan_id = guild_data.get(
            "clan_channel_id"
        )

        if clan_id:

            clan_channel = guild.get_channel(
                clan_id
            )

        if clan_channel is None:

            clan_channel = (
                await guild.create_voice_channel(
                    name="⚔️ Clan Applications: 0",
                    category=category,
                    reason=(
                        "Clan application statistics"
                    )
                )
            )

            guild_data[
                "clan_channel_id"
            ] = clan_channel.id

        # ====================================================
        # PERMISSIONS
        # ====================================================

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
                connect=False
            )

        # ====================================================
        # SAVE
        # ====================================================

        save_data()

        # ====================================================
        # INITIAL UPDATE
        # ====================================================

        await self.update_guild(
            guild
        )

        # ====================================================
        # RESPONSE
        # ====================================================

        embed = discord.Embed(
            title="📊 Moderator Statistics",
            description=(
                "Moderator statistics have been configured."
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
                "Only moderators can see these channels."
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

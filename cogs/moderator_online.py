import discord
from discord.ext import commands, tasks
from discord import app_commands

import json
import os


# ============================================================
# CONFIGURATION
# ============================================================

MODERATOR_ROLE_NAME = "Moderator"

DATA_FILE = "moderator_online.json"

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
            f"[MOD ONLINE] Failed to load data: {e}"
        )

        return {
            "guilds": {}
        }


online_data = load_data()


def save_data():

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                online_data,
                f,
                indent=4
            )

    except Exception as e:

        print(
            f"[MOD ONLINE] Failed to save data: {e}"
        )


def get_guild_data(
    guild_id: int
):

    guild_id = str(guild_id)

    if guild_id not in online_data["guilds"]:

        online_data["guilds"][guild_id] = {
            "channel_id": None
        }

    return online_data["guilds"][guild_id]


# ============================================================
# MODERATOR CHECK
# ============================================================

def is_moderator(
    member: discord.Member
) -> bool:

    role = discord.utils.get(
        member.guild.roles,
        name=MODERATOR_ROLE_NAME
    )

    if role is None:
        return False

    return role in member.roles


# ============================================================
# MODERATOR ONLINE COG
# ============================================================

class ModeratorOnline(
    commands.Cog
):

    def __init__(
        self,
        bot: commands.Bot
    ):

        self.bot = bot

        self.update_moderator_counter.start()

    # ========================================================
    # CLEANUP
    # ========================================================

    def cog_unload(self):

        self.update_moderator_counter.cancel()

    # ========================================================
    # READY
    # ========================================================

    @commands.Cog.listener()
    async def on_ready(self):

        print(
            "✅ Moderator online counter started"
        )

    # ========================================================
    # UPDATE LOOP
    # ========================================================

    @tasks.loop(seconds=UPDATE_INTERVAL)
    async def update_moderator_counter(self):

        for guild in self.bot.guilds:

            try:

                await self.update_guild(
                    guild
                )

            except Exception as e:

                print(
                    f"[MOD ONLINE] "
                    f"{guild.name}: {e}"
                )

    # ========================================================
    # WAIT FOR BOT
    # ========================================================

    @update_moderator_counter.before_loop
    async def before_update(
        self
    ):

        await self.bot.wait_until_ready()

    # ========================================================
    # COUNT ONLINE MODERATORS
    # ========================================================

    def count_online_moderators(
        self,
        guild: discord.Guild
    ) -> int:

        moderator_role = discord.utils.get(
            guild.roles,
            name=MODERATOR_ROLE_NAME
        )

        if moderator_role is None:
            return 0

        online_count = 0

        for member in moderator_role.members:

            # Offline
            if member.status == discord.Status.offline:
                continue

            # Online / Idle / DND
            if member.status in (
                discord.Status.online,
                discord.Status.idle,
                discord.Status.dnd
            ):

                online_count += 1

        return online_count

    # ========================================================
    # UPDATE SERVER
    # ========================================================

    async def update_guild(
        self,
        guild: discord.Guild
    ):

        guild_data = get_guild_data(
            guild.id
        )

        channel_id = guild_data.get(
            "channel_id"
        )

        if not channel_id:
            return

        channel = guild.get_channel(
            channel_id
        )

        if channel is None:

            # Channel was deleted
            guild_data[
                "channel_id"
            ] = None

            save_data()

            return

        # ----------------------------------------------------
        # COUNT
        # ----------------------------------------------------

        online_count = (
            self.count_online_moderators(
                guild
            )
        )

        # ----------------------------------------------------
        # CHANNEL NAME
        # ----------------------------------------------------

        new_name = (
            f"🟢 Moderators Online: "
            f"{online_count}"
        )

        # ----------------------------------------------------
        # ONLY EDIT IF NECESSARY
        # ----------------------------------------------------

        if channel.name != new_name:

            try:

                await channel.edit(
                    name=new_name,
                    reason=(
                        "Updating live moderator count"
                    )
                )

            except discord.Forbidden:

                print(
                    f"[MOD ONLINE] Missing "
                    f"Manage Channels permission "
                    f"in {guild.name}"
                )

            except discord.HTTPException as e:

                print(
                    f"[MOD ONLINE] Discord error: {e}"
                )

    # ========================================================
    # SET MODERATOR COUNTER CHANNEL
    # ========================================================

    @app_commands.command(
        name="setmoderatorcounter",
        description=(
            "Set the public voice channel for "
            "online moderators"
        )
    )
    @app_commands.describe(
        channel=(
            "Voice channel that will display "
            "the online moderator count"
        )
    )
    async def setmoderatorcounter(
        self,
        interaction: discord.Interaction,
        channel: discord.VoiceChannel
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This command can only be used "
                "inside a server.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # MODERATOR ONLY
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
        # SAVE CHANNEL
        # ----------------------------------------------------

        guild_data = get_guild_data(
            guild.id
        )

        guild_data[
            "channel_id"
        ] = channel.id

        save_data()

        # ----------------------------------------------------
        # UPDATE IMMEDIATELY
        # ----------------------------------------------------

        online_count = (
            self.count_online_moderators(
                guild
            )
        )

        new_name = (
            f"🟢 Moderators Online: "
            f"{online_count}"
        )

        try:

            await channel.edit(
                name=new_name,
                reason=(
                    "Configured moderator "
                    "online counter"
                )
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I don't have permission to "
                "rename this channel.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # MAKE CHANNEL NON-JOINABLE
        # ----------------------------------------------------

        try:

            await channel.set_permissions(
                guild.default_role,
                connect=False,
                speak=False
            )

        except discord.Forbidden:

            pass

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        embed = discord.Embed(
            title="🟢 Moderator Counter Configured",
            description=(
                f"Live moderator count is now displayed in "
                f"{channel.mention}."
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="Current Online Moderators",
            value=str(
                online_count
            ),
            inline=True
        )

        embed.add_field(
            name="Update Frequency",
            value=f"Every {UPDATE_INTERVAL} seconds",
            inline=True
        )

        embed.set_footer(
            text="Visible to everyone"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # ========================================================
    # REMOVE COUNTER
    # ========================================================

    @app_commands.command(
        name="removemoderatorcounter",
        description=(
            "Stop using the moderator online counter"
        )
    )
    async def removemoderatorcounter(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        if guild is None:
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

        guild_data = get_guild_data(
            guild.id
        )

        guild_data[
            "channel_id"
        ] = None

        save_data()

        await interaction.response.send_message(
            "✅ Moderator online counter disabled.",
            ephemeral=True
        )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot: commands.Bot
):

    await bot.add_cog(
        ModeratorOnline(bot)
    )

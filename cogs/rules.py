# ============================================================
# RULES COG
# ============================================================
#
# Commands:
#
# /rulesetup
#     Admin selects a CATEGORY.
#     Bot creates the rules channel automatically.
#
# /rule
#     Posts / refreshes the rules message.
#
# Configuration:
#
# rules_config.json
#
# ============================================================

import discord
from discord.ext import commands
from discord import app_commands

import json
import os
import asyncio
from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# SETTINGS
# ============================================================

CONFIG_FILE = Path("rules_config.json")

RULES_CHANNEL_NAME = "📜・rules"

RULES_REACTION = "✅"

WARNING_COOLDOWN = 60


# ============================================================
# DEFAULT RULES
# ============================================================

DEFAULT_RULES = [
    "Respect all members, moderators, and staff.",
    "No spam, flooding, or unnecessary repeated messages.",
    "No harassment, threats, or abusive behavior.",
    "Use the appropriate channel for your messages.",
    "Do not share illegal, malicious, or harmful content.",
    "Do not advertise without permission from the staff.",
    "Do not impersonate other members, staff, or creators.",
    "Follow Discord's Terms of Service and Community Guidelines.",
    "Follow instructions given by the moderators.",
    "Staff may take action when necessary to keep the community safe and organized."
]


# ============================================================
# CONFIG FILE HELPERS
# ============================================================

def load_config():

    if not CONFIG_FILE.exists():

        return {}

    try:

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if not isinstance(data, dict):

            return {}

        return data

    except Exception as e:

        print(
            f"❌ Failed to read rules_config.json: {e}"
        )

        return {}


def save_config(data):

    try:

        with open(
            CONFIG_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as e:

        print(
            f"❌ Failed to save rules_config.json: {e}"
        )

        return False


# ============================================================
# RULES COG
# ============================================================

class Rules(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.warning_cooldown = {}

        print(
            "📜 Rules Cog loaded."
        )

    # ========================================================
    # GET SERVER CONFIG
    # ========================================================

    def get_guild_config(
        self,
        guild_id
    ):

        config = load_config()

        guild_id = str(
            guild_id
        )

        if guild_id not in config:

            config[guild_id] = {}

        return config, config[guild_id]

    # ========================================================
    # SAVE SERVER CONFIG
    # ========================================================

    def save_guild_config(
        self,
        guild_id,
        guild_config
    ):

        config = load_config()

        config[
            str(guild_id)
        ] = guild_config

        return save_config(
            config
        )

    # ========================================================
    # RULES EMBED
    # ========================================================

    def create_rules_embed(
        self,
        guild
    ):

        rules_text = ""

        for index, rule in enumerate(
            DEFAULT_RULES,
            start=1
        ):

            rules_text += (
                f"**{index}.** {rule}\n\n"
            )

        embed = discord.Embed(

            title="📜 SERVER RULES",

            description=rules_text,

            color=discord.Color.blurple(),

            timestamp=datetime.now(
                timezone.utc
            )
        )

        embed.add_field(

            name="✅ Rule Acknowledgement",

            value=(
                f"React with {RULES_REACTION} "
                "to this message to acknowledge "
                "that you have read and accepted "
                "the server rules.\n\n"
                "You must acknowledge the rules "
                "before participating in the server."
            ),

            inline=False
        )

        embed.set_footer(

            text=(
                f"{guild.name} • "
                "Please read before participating"
            )
        )

        return embed

    # ========================================================
    # FIND RULES CHANNEL
    # ========================================================

    async def get_saved_rules_channel(
        self,
        guild
    ):

        config, guild_config = (
            self.get_guild_config(
                guild.id
            )
        )

        channel_id = guild_config.get(
            "rules_channel_id"
        )

        if not channel_id:

            return None

        try:

            channel_id = int(
                channel_id
            )

        except Exception:

            return None

        channel = guild.get_channel(
            channel_id
        )

        if channel is not None:

            return channel

        try:

            channel = await self.bot.fetch_channel(
                channel_id
            )

            if isinstance(
                channel,
                discord.TextChannel
            ):

                if channel.guild.id == guild.id:

                    return channel

        except Exception:

            pass

        return None

    # ========================================================
    # CREATE RULES CHANNEL
    # ========================================================

    async def create_rules_channel(
        self,
        guild,
        category
    ):

        # ----------------------------------------------------
        # Check existing channel by saved config
        # ----------------------------------------------------

        existing = await self.get_saved_rules_channel(
            guild
        )

        if existing:

            return existing, False

        # ----------------------------------------------------
        # Check by name in selected category
        # ----------------------------------------------------

        for channel in category.text_channels:

            if channel.name == RULES_CHANNEL_NAME:

                return channel, False

        # ----------------------------------------------------
        # Permissions
        # ----------------------------------------------------

        overwrites = {

            guild.default_role: discord.PermissionOverwrite(

                view_channel=True,

                read_message_history=True,

                send_messages=True,

                add_reactions=True

            )
        }

        # ----------------------------------------------------
        # Create
        # ----------------------------------------------------

        try:

            channel = await guild.create_text_channel(

                RULES_CHANNEL_NAME,

                category=category,

                overwrites=overwrites,

                reason=(
                    "Rules system setup"
                )
            )

            print(
                f"✅ Created rules channel "
                f"#{channel.name} "
                f"in {category.name}"
            )

            return channel, True

        except Exception as e:

            print(
                f"❌ Failed to create rules channel: {e}"
            )

            raise

    # ========================================================
    # POST RULES
    # ========================================================

    async def post_rules(
        self,
        guild,
        channel
    ):

        config, guild_config = (
            self.get_guild_config(
                guild.id
            )
        )

        message_id = guild_config.get(
            "rules_message_id"
        )

        # ----------------------------------------------------
        # Try existing message
        # ----------------------------------------------------

        if message_id:

            try:

                message = await channel.fetch_message(
                    int(message_id)
                )

                embed = self.create_rules_embed(
                    guild
                )

                await message.edit(
                    embed=embed
                )

                # Remove old reactions
                try:

                    await message.clear_reactions()

                except Exception:

                    pass

                # Add required reaction
                try:

                    await message.add_reaction(
                        RULES_REACTION
                    )

                except Exception as e:

                    print(
                        f"⚠️ Could not add rules reaction: {e}"
                    )

                guild_config[
                    "rules_message_id"
                ] = str(
                    message.id
                )

                self.save_guild_config(

                    guild.id,

                    guild_config
                )

                return message

            except Exception:

                # Message no longer exists
                pass

        # ----------------------------------------------------
        # Send new rules message
        # ----------------------------------------------------

        embed = self.create_rules_embed(
            guild
        )

        message = await channel.send(
            embed=embed
        )

        # ----------------------------------------------------
        # Add reaction
        # ----------------------------------------------------

        try:

            await message.add_reaction(
                RULES_REACTION
            )

        except Exception as e:

            print(
                f"⚠️ Could not add reaction: {e}"
            )

        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        guild_config[
            "rules_message_id"
        ] = str(
            message.id
        )

        guild_config[
            "rules_channel_id"
        ] = str(
            channel.id
        )

        self.save_guild_config(

            guild.id,

            guild_config
        )

        print(
            f"✅ Rules message posted in "
            f"#{channel.name}"
        )

        return message

    # ========================================================
    # /RULESETUP
    # ========================================================

    @app_commands.command(

        name="rulesetup",

        description=(
            "Set up the server rules system."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def rulesetup(
        self,
        interaction: discord.Interaction
    ):

        # ----------------------------------------------------
        # Server check
        # ----------------------------------------------------

        if interaction.guild is None:

            await interaction.response.send_message(

                "❌ This command can only be used "
                "inside a server.",

                ephemeral=True
            )

            return

        guild = interaction.guild

        # ----------------------------------------------------
        # Check bot permission
        # ----------------------------------------------------

        me = guild.me

        if me is None:

            await interaction.response.send_message(

                "❌ I could not determine my permissions "
                "in this server.",

                ephemeral=True
            )

            return

        required_permissions = [

            "manage_channels",

            "send_messages",

            "embed_links",

            "add_reactions",

            "read_message_history"
        ]

        missing = []

        for permission in required_permissions:

            if not getattr(
                me.guild_permissions,
                permission,
                False
            ):

                missing.append(
                    permission.replace(
                        "_",
                        " "
                    )
                )

        if missing:

            await interaction.response.send_message(

                "❌ I am missing these permissions:\n\n"
                + "\n".join(
                    f"• `{permission}`"
                    for permission in missing
                ),

                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # Category select
        # ----------------------------------------------------

        categories = [

            category

            for category in guild.categories

            if category.permissions_for(
                me
            ).manage_channels
        ]

        if not categories:

            await interaction.response.send_message(

                "❌ No category is available where "
                "I can create channels.",

                ephemeral=True
            )

            return

        # Discord select max is 25
        categories = categories[:25]

        view = RulesCategoryView(

            self,

            guild,

            categories
        )

        embed = discord.Embed(

            title="📜 Rules Setup",

            description=(

                "Select the **category** where you "
                "want the bot to create the rules channel.\n\n"

                "You do **not** need to create the "
                "channel yourself.\n\n"

                "The bot will automatically create:\n"

                f"📜 `{RULES_CHANNEL_NAME}`\n\n"

                "and post the rules there."
            ),

            color=discord.Color.blurple()
        )

        await interaction.response.send_message(

            embed=embed,

            view=view,

            ephemeral=True
        )

    # ========================================================
    # /RULE
    # ========================================================

    @app_commands.command(

        name="rule",

        description=(
            "Post or refresh the server rules."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def rule(
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

        guild = interaction.guild

        channel = await self.get_saved_rules_channel(
            guild
        )

        if channel is None:

            await interaction.response.send_message(

                "❌ The rules system has not been "
                "configured yet.\n\n"

                "Use `/rulesetup` first.",

                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        try:

            message = await self.post_rules(

                guild,

                channel
            )

            await interaction.followup.send(

                "✅ Rules have been posted/refreshed.\n\n"
                f"📜 Channel: {channel.mention}\n"
                f"📝 Message ID: `{message.id}`",

                ephemeral=True
            )

        except Exception as e:

            print(
                f"❌ /rule error: {e}"
            )

            await interaction.followup.send(

                "❌ Failed to post the rules.\n\n"
                f"`{type(e).__name__}: {e}`",

                ephemeral=True
            )

    # ========================================================
    # MEMBER REACTION
    # ========================================================

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self,
        payload: discord.RawReactionActionEvent
    ):

        # ----------------------------------------------------
        # Ignore DMs
        # ----------------------------------------------------

        if payload.guild_id is None:

            return

        # ----------------------------------------------------
        # Check guild config
        # ----------------------------------------------------

        config, guild_config = (
            self.get_guild_config(
                payload.guild_id
            )
        )

        rules_message_id = guild_config.get(
            "rules_message_id"
        )

        if not rules_message_id:

            return

        try:

            rules_message_id = int(
                rules_message_id
            )

        except Exception:

            return

        # ----------------------------------------------------
        # Wrong message
        # ----------------------------------------------------

        if payload.message_id != rules_message_id:

            return

        # ----------------------------------------------------
        # Wrong reaction
        # ----------------------------------------------------

        if str(
            payload.emoji
        ) != RULES_REACTION:

            return

        # ----------------------------------------------------
        # Ignore bot
        # ----------------------------------------------------

        if self.bot.user:

            if payload.user_id == self.bot.user.id:

                return

        # ----------------------------------------------------
        # Member accepted
        # ----------------------------------------------------

        print(
            f"✅ User {payload.user_id} "
            f"accepted the server rules."
        )

    # ========================================================
    # CHECK MEMBER ACCEPTANCE
    # ========================================================

    async def member_accepted_rules(
        self,
        guild,
        member
    ):

        # ----------------------------------------------------
        # Config
        # ----------------------------------------------------

        config, guild_config = (
            self.get_guild_config(
                guild.id
            )
        )

        message_id = guild_config.get(
            "rules_message_id"
        )

        channel_id = guild_config.get(
            "rules_channel_id"
        )

        if not message_id or not channel_id:

            # Rules not configured
            return True

        try:

            message_id = int(
                message_id
            )

            channel_id = int(
                channel_id
            )

        except Exception:

            return True

        # ----------------------------------------------------
        # Get channel
        # ----------------------------------------------------

        channel = guild.get_channel(
            channel_id
        )

        if channel is None:

            return True

        # ----------------------------------------------------
        # Get message
        # ----------------------------------------------------

        try:

            message = await channel.fetch_message(
                message_id
            )

        except Exception:

            return True

        # ----------------------------------------------------
        # Find user's reaction
        # ----------------------------------------------------

        for reaction in message.reactions:

            if str(
                reaction.emoji
            ) != RULES_REACTION:

                continue

            try:

                async for user in reaction.users():

                    if user.id == member.id:

                        return True

            except Exception:

                # If Discord doesn't allow us to
                # inspect the reaction, don't punish
                # the member.
                return True

        return False

    # ========================================================
    # MESSAGE CHECK
    # ========================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message
    ):

        # ----------------------------------------------------
        # Ignore bots
        # ----------------------------------------------------

        if message.author.bot:

            return

        # ----------------------------------------------------
        # Ignore DMs
        # ----------------------------------------------------

        if message.guild is None:

            return

        guild = message.guild

        # ----------------------------------------------------
        # Check rules configured
        # ----------------------------------------------------

        config, guild_config = (
            self.get_guild_config(
                guild.id
            )
        )

        if not guild_config.get(
            "rules_message_id"
        ):

            return

        # ----------------------------------------------------
        # Don't warn inside rules channel
        # ----------------------------------------------------

        rules_channel_id = guild_config.get(
            "rules_channel_id"
        )

        try:

            if (
                rules_channel_id
                and
                message.channel.id
                == int(rules_channel_id)
            ):

                return

        except Exception:

            pass

        # ----------------------------------------------------
        # Admin / moderators
        # ----------------------------------------------------

        if message.author.guild_permissions.administrator:

            return

        # ----------------------------------------------------
        # Check acceptance
        # ----------------------------------------------------

        try:

            accepted = await self.member_accepted_rules(

                guild,

                message.author
            )

        except Exception as e:

            print(
                f"⚠️ Rules acceptance check failed: {e}"
            )

            return

        if accepted:

            return

        # ----------------------------------------------------
        # Cooldown
        # ----------------------------------------------------

        now = datetime.now(
            timezone.utc
        ).timestamp()

        last_warning = self.warning_cooldown.get(
            message.author.id,
            0
        )

        if (
            now - last_warning
            < WARNING_COOLDOWN
        ):

            return

        self.warning_cooldown[
            message.author.id
        ] = now

        # ----------------------------------------------------
        # Warn member
        # ----------------------------------------------------

        try:

            await message.reply(

                f"⚠️ {message.author.mention}, "
                f"please read and react with "
                f"{RULES_REACTION} to the rules "
                "before participating in the server.",

                mention_author=False,

                delete_after=15
            )

        except Exception as e:

            print(
                f"⚠️ Failed to send rules warning: {e}"
            )

    # ========================================================
    # GET SETUP INFO
    # ========================================================

    async def get_setup_info(
        self,
        guild
    ):

        config, guild_config = (
            self.get_guild_config(
                guild.id
            )
        )

        channel_id = guild_config.get(
            "rules_channel_id"
        )

        category_id = guild_config.get(
            "category_id"
        )

        message_id = guild_config.get(
            "rules_message_id"
        )

        if not channel_id:

            return {

                "status": "⚪",

                "message": (
                    "Rules system not configured."
                )
            }

        channel = guild.get_channel(
            int(channel_id)
        ) if str(channel_id).isdigit() else None

        category = guild.get_channel(
            int(category_id)
        ) if (
            category_id
            and
            str(category_id).isdigit()
        ) else None

        if channel is None:

            return {

                "status": "⚠️",

                "message": (
                    "Rules channel is missing."
                ),

                "channel_id": channel_id,

                "category_id": category_id,

                "message_id": message_id
            }

        return {

            "status": "🟢",

            "message": (
                "Rules system configured."
            ),

            "channel": channel.mention,

            "channel_id": channel_id,

            "category": (
                category.name
                if category
                else
                "Unknown category"
            ),

            "category_id": category_id,

            "message_id": message_id,

            "reaction": RULES_REACTION
        }


# ============================================================
# CATEGORY SELECT
# ============================================================

class RulesCategorySelect(
    discord.ui.Select
):

    def __init__(
        self,
        cog,
        guild,
        categories
    ):

        self.rules_cog = cog

        self.guild = guild

        options = []

        for category in categories:

            options.append(

                discord.SelectOption(

                    label=category.name[:100],

                    value=str(
                        category.id
                    ),

                    description=(
                        f"Create "
                        f"{RULES_CHANNEL_NAME} "
                        f"inside {category.name}"[:100]
                    )
                )
            )

        super().__init__(

            placeholder=(
                "Select a category..."
            ),

            min_values=1,

            max_values=1,

            options=options
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        category_id = int(
            self.values[0]
        )

        category = self.guild.get_channel(
            category_id
        )

        if not isinstance(
            category,
            discord.CategoryChannel
        ):

            await interaction.response.send_message(

                "❌ The selected category "
                "could not be found.",

                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        try:

            # ------------------------------------------------
            # Create / find channel
            # ------------------------------------------------

            channel, created = (
                await self.rules_cog.create_rules_channel(

                    self.guild,

                    category
                )
            )

            # ------------------------------------------------
            # Save category
            # ------------------------------------------------

            config, guild_config = (
                self.rules_cog.get_guild_config(

                    self.guild.id
                )
            )

            guild_config[
                "category_id"
            ] = str(
                category.id
            )

            guild_config[
                "rules_channel_id"
            ] = str(
                channel.id
            )

            guild_config[
                "rules_channel_name"
            ] = channel.name

            guild_config[
                "reaction"
            ] = RULES_REACTION

            guild_config[
                "updated_at"
            ] = datetime.now(
                timezone.utc
            ).isoformat()

            self.rules_cog.save_guild_config(

                self.guild.id,

                guild_config
            )

            # ------------------------------------------------
            # Post rules
            # ------------------------------------------------

            message = await self.rules_cog.post_rules(

                self.guild,

                channel
            )

            # ------------------------------------------------
            # Success
            # ------------------------------------------------

            embed = discord.Embed(

                title="✅ Rules System Ready",

                description=(

                    f"**Category:** {category.name}\n\n"

                    f"📜 **Rules channel:** "
                    f"{channel.mention}\n\n"

                    f"📝 **Rules message:** "
                    f"`{message.id}`\n\n"

                    f"✅ **Required reaction:** "
                    f"{RULES_REACTION}\n\n"

                    "The setup has been saved. "
                    "It will remain available after "
                    "the bot restarts."
                ),

                color=discord.Color.green()
            )

            await interaction.followup.send(

                embed=embed,

                ephemeral=True
            )

        except Exception as e:

            print(
                "❌ Rules setup failed:"
            )

            print(e)

            await interaction.followup.send(

                "❌ **Rules setup failed.**\n\n"
                f"`{type(e).__name__}: {e}`",

                ephemeral=True
            )


# ============================================================
# CATEGORY VIEW
# ============================================================

class RulesCategoryView(
    discord.ui.View
):

    def __init__(
        self,
        cog,
        guild,
        categories
    ):

        super().__init__(
            timeout=120
        )

        self.add_item(

            RulesCategorySelect(

                cog,

                guild,

                categories
            )
        )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot
):

    await bot.add_cog(
        Rules(bot)
    )

    print(
        "✅ Rules Cog ready."
    )

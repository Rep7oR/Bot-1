import discord
from discord.ext import commands
from discord import app_commands

import os
import json
import asyncio
from datetime import datetime, timezone


# ============================================================
# CONFIGURATION
# ============================================================

CONFIG_FILE = "rules_config.json"

ACCEPT_REACTION = "👍"

# Prevent the bot from warning the same member on every message
WARNING_COOLDOWN = 30


# ============================================================
# JSON HELPERS
# ============================================================

def load_config():

    if not os.path.exists(CONFIG_FILE):
        return {}

    try:

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(data, dict):
                return data

    except Exception as e:

        print(
            f"❌ Failed to load rules config: {e}"
        )

    return {}


def save_config(data):

    try:

        temp_file = CONFIG_FILE + ".tmp"

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        os.replace(
            temp_file,
            CONFIG_FILE
        )

        return True

    except Exception as e:

        print(
            f"❌ Failed to save rules config: {e}"
        )

        return False


# ============================================================
# RULES COG
# ============================================================

class Rules(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.config = load_config()

        # ----------------------------------------------------
        # Warning cooldown
        #
        # {
        #     guild_id: {
        #         user_id: timestamp
        #     }
        # }
        # ----------------------------------------------------

        self.warning_cooldowns = {}

        print(
            "📜 Rules system loaded."
        )

    # ========================================================
    # CONFIGURATION
    # ========================================================

    def get_guild_config(
        self,
        guild_id
    ):

        return self.config.get(
            str(guild_id)
        )

    # ========================================================

    def save_guild_config(
        self,
        guild_id,
        data
    ):

        self.config[
            str(guild_id)
        ] = data

        return save_config(
            self.config
        )

    # ========================================================
    # CHECK ADMIN
    # ========================================================

    def is_admin(
        self,
        member
    ):

        return (
            member
            and member.guild_permissions.administrator
        )

    # ========================================================
    # GET RULE MESSAGE
    # ========================================================

    async def get_rules_message(
        self,
        guild
    ):

        guild_config = self.get_guild_config(
            guild.id
        )

        if not guild_config:
            return None

        channel_id = guild_config.get(
            "channel_id"
        )

        message_id = guild_config.get(
            "message_id"
        )

        if not channel_id or not message_id:
            return None

        channel = guild.get_channel(
            int(channel_id)
        )

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            return None

        try:

            message = await channel.fetch_message(
                int(message_id)
            )

            return message

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):

            return None

    # ========================================================
    # CHECK REACTION
    # ========================================================

    async def member_accepted_rules(
        self,
        guild,
        member
    ):

        # ----------------------------------------------------
        # Bots are always allowed
        # ----------------------------------------------------

        if member.bot:
            return True

        message = await self.get_rules_message(
            guild
        )

        if message is None:
            return False

        # ----------------------------------------------------
        # Find the required reaction
        # ----------------------------------------------------

        required_reaction = None

        for reaction in message.reactions:

            if str(reaction.emoji) == ACCEPT_REACTION:

                required_reaction = reaction

                break

        # ----------------------------------------------------
        # No reaction exists
        # ----------------------------------------------------

        if required_reaction is None:
            return False

        # ----------------------------------------------------
        # Check whether member actually reacted
        # ----------------------------------------------------

        try:

            async for user in required_reaction.users():

                if user.id == member.id:

                    return True

        except (
            discord.Forbidden,
            discord.HTTPException
        ):

            return False

        return False

    # ========================================================
    # BUILD RULES EMBED
    # ========================================================

    def create_rules_embed(
        self,
        title,
        rules
    ):

        embed = discord.Embed(

            title=f"📜 {title}",

            description=rules,

            color=discord.Color.blurple(),

            timestamp=datetime.now(
                timezone.utc
            )
        )

        embed.add_field(

            name="⚠️ Required Action",

            value=(
                f"React with {ACCEPT_REACTION} "
                "to this message to confirm that "
                "you have read and accepted the rules."
            ),

            inline=False
        )

        embed.set_footer(

            text=(
                "You must accept the rules "
                "before participating in the server."
            )
        )

        return embed

    # ========================================================
    # RULE MODAL
    # ========================================================

    class RuleModal(
        discord.ui.Modal,
        title="Create Server Rules"
    ):

        rule_title = discord.ui.TextInput(

            label="Rules Title",

            placeholder="Example: Server Rules",

            required=True,

            max_length=100,

            style=discord.TextStyle.short
        )

        rule_content = discord.ui.TextInput(

            label="Rules",

            placeholder=(
                "Enter your server rules here..."
            ),

            required=True,

            max_length=4000,

            style=discord.TextStyle.paragraph
        )

        def __init__(
            self,
            cog,
            channel
        ):

            super().__init__()

            self.cog = cog

            self.channel = channel

        async def on_submit(
            self,
            interaction
        ):

            # ------------------------------------------------
            # Make sure channel still exists
            # ------------------------------------------------

            if not isinstance(
                self.channel,
                discord.TextChannel
            ):

                await interaction.response.send_message(

                    "❌ The selected channel is no longer available.",

                    ephemeral=True
                )

                return

            # ------------------------------------------------
            # Check bot permissions
            # ------------------------------------------------

            permissions = (
                self.channel.permissions_for(
                    interaction.guild.me
                )
            )

            if not permissions.send_messages:

                await interaction.response.send_message(

                    "❌ I cannot send messages in that channel.",

                    ephemeral=True
                )

                return

            if not permissions.embed_links:

                await interaction.response.send_message(

                    "❌ I need the **Embed Links** permission "
                    "in that channel.",

                    ephemeral=True
                )

                return

            # ------------------------------------------------
            # Create embed
            # ------------------------------------------------

            embed = self.cog.create_rules_embed(

                str(
                    self.rule_title.value
                ),

                str(
                    self.rule_content.value
                )
            )

            # ------------------------------------------------
            # Send rules
            # ------------------------------------------------

            try:

                message = await self.channel.send(
                    embed=embed
                )

            except Exception as e:

                await interaction.response.send_message(

                    f"❌ Failed to post the rules.\n"
                    f"`{type(e).__name__}: {e}`",

                    ephemeral=True
                )

                return

            # ------------------------------------------------
            # Add mandatory reaction
            # ------------------------------------------------

            try:

                await message.add_reaction(
                    ACCEPT_REACTION
                )

            except Exception as e:

                # ------------------------------------------------
                # Delete message if reaction cannot be added
                # because mandatory reaction is required.
                # ------------------------------------------------

                try:

                    await message.delete()

                except Exception:

                    pass

                await interaction.response.send_message(

                    "❌ I could not add the required "
                    f"{ACCEPT_REACTION} reaction.\n\n"
                    "Make sure I have the **Add Reactions** "
                    "permission in the selected channel.",

                    ephemeral=True
                )

                return

            # ------------------------------------------------
            # Save configuration
            # ------------------------------------------------

            config = {

                "channel_id": self.channel.id,

                "message_id": message.id,

                "title": str(
                    self.rule_title.value
                ),

                "rules": str(
                    self.rule_content.value
                ),

                "required_reaction": ACCEPT_REACTION,

                "created_by": interaction.user.id,

                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )
            }

            saved = self.cog.save_guild_config(

                interaction.guild.id,

                config
            )

            if not saved:

                await interaction.response.send_message(

                    "⚠️ Rules were posted and the reaction "
                    "was added, but I could not save the "
                    "configuration file.",

                    ephemeral=True
                )

                return

            # ------------------------------------------------
            # Success
            # ------------------------------------------------

            await interaction.response.send_message(

                "✅ **Rules posted successfully!**\n\n"

                f"📍 Channel: {self.channel.mention}\n"

                f"📝 Title: **{self.rule_title.value}**\n"

                f"👍 Required reaction: {ACCEPT_REACTION}\n\n"

                "Members must react to this rules message "
                "before participating in the server.",

                ephemeral=True
            )

    # ========================================================
    # CHANNEL SELECT VIEW
    # ========================================================

    class RuleChannelView(
        discord.ui.View
    ):

        def __init__(
            self,
            cog,
            author
        ):

            super().__init__(
                timeout=120
            )

            self.cog = cog

            self.author = author

            self.selected_channel = None

        # ----------------------------------------------------
        # Channel selector
        # ----------------------------------------------------

        channel_select = discord.ui.ChannelSelect(

            placeholder="Select the rules channel",

            channel_types=[
                discord.ChannelType.text
            ],

            min_values=1,

            max_values=1
        )

        @channel_select.callback
        async def channel_selected(
            self,
            interaction
        ):

            # ------------------------------------------------
            # Only command user
            # ------------------------------------------------

            if interaction.user.id != self.author.id:

                await interaction.response.send_message(

                    "❌ This setup menu belongs to "
                    "the administrator who opened it.",

                    ephemeral=True
                )

                return

            # ------------------------------------------------
            # Get selected channel
            # ------------------------------------------------

            channel = self.channel_select.values[0]

            if not isinstance(
                channel,
                discord.TextChannel
            ):

                await interaction.response.send_message(

                    "❌ Please select a normal text channel.",

                    ephemeral=True
                )

                return

            self.selected_channel = channel

            # ------------------------------------------------
            # Show modal
            # ------------------------------------------------

            modal = Rules.RuleModal(

                self.cog,

                channel
            )

            await interaction.response.send_modal(
                modal
            )

    # ========================================================
    # /RULE
    # ========================================================

    @app_commands.command(

        name="rule",

        description=(
            "Create and post the server rules."
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

        # ----------------------------------------------------
        # Show channel selector
        # ----------------------------------------------------

        view = self.RuleChannelView(

            self,

            interaction.user
        )

        await interaction.response.send_message(

            "📜 **Server Rules Setup**\n\n"

            "Select the **text channel** where you want "
            "the rules message to be posted.\n\n"

            f"Members will be required to react with "
            f"{ACCEPT_REACTION} to participate.",

            view=view,

            ephemeral=True
        )

    # ========================================================
    # /RULEREMOVE
    # ========================================================

    @app_commands.command(

        name="ruleremove",

        description=(
            "Remove the saved rules configuration."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def ruleremove(
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

        guild_id = str(
            interaction.guild.id
        )

        if guild_id not in self.config:

            await interaction.response.send_message(

                "⚪ No rules configuration exists "
                "for this server.",

                ephemeral=True
            )

            return

        del self.config[
            guild_id
        ]

        save_config(
            self.config
        )

        await interaction.response.send_message(

            "✅ Rules configuration removed.\n\n"

            "⚠️ The existing rules message was not deleted.",

            ephemeral=True
        )

    # ========================================================
    # /RULESTATUS
    # ========================================================

    @app_commands.command(

        name="rulestatus",

        description=(
            "Show the current rules configuration."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def rulestatus(
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

        config = self.get_guild_config(
            interaction.guild.id
        )

        if not config:

            await interaction.response.send_message(

                "⚪ Rules are not configured "
                "for this server.",

                ephemeral=True
            )

            return

        channel = interaction.guild.get_channel(

            int(
                config.get(
                    "channel_id",
                    0
                )
            )
        )

        message = await self.get_rules_message(
            interaction.guild
        )

        embed = discord.Embed(

            title="📜 Rules Configuration",

            color=discord.Color.blurple()
        )

        embed.add_field(

            name="Status",

            value=(
                "🟢 Active"
                if message
                else "🔴 Rules message not found"
            ),

            inline=False
        )

        embed.add_field(

            name="Channel",

            value=(
                channel.mention
                if channel
                else "⚠️ Channel not found"
            ),

            inline=True
        )

        embed.add_field(

            name="Required Reaction",

            value=ACCEPT_REACTION,

            inline=True
        )

        embed.add_field(

            name="Message",

            value=(
                f"[Jump to Rules Message]"
                f"({message.jump_url})"
                if message
                else "Message not found"
            ),

            inline=False
        )

        await interaction.response.send_message(

            embed=embed,

            ephemeral=True
        )

    # ========================================================
    # MESSAGE LISTENER
    # ========================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message
    ):

        # ----------------------------------------------------
        # Ignore DMs
        # ----------------------------------------------------

        if message.guild is None:
            return

        # ----------------------------------------------------
        # Ignore bots
        # ----------------------------------------------------

        if message.author.bot:
            return

        # ----------------------------------------------------
        # Ignore messages from admins
        # ----------------------------------------------------

        if (
            message.author.guild_permissions.administrator
        ):
            return

        # ----------------------------------------------------
        # Check whether rules are configured
        # ----------------------------------------------------

        config = self.get_guild_config(
            message.guild.id
        )

        if not config:
            return

        # ----------------------------------------------------
        # Check rules message
        # ----------------------------------------------------

        rules_message = await self.get_rules_message(

            message.guild
        )

        if rules_message is None:

            return

        # ----------------------------------------------------
        # If this IS the rules message channel,
        # don't warn people for talking there.
        #
        # This prevents the bot from fighting with
        # the rules channel itself.
        # ----------------------------------------------------

        if message.channel.id == rules_message.channel.id:

            return

        # ----------------------------------------------------
        # Check actual reaction
        # ----------------------------------------------------

        accepted = await self.member_accepted_rules(

            message.guild,

            message.author
        )

        if accepted:

            return

        # ----------------------------------------------------
        # Warning cooldown
        # ----------------------------------------------------

        guild_id = message.guild.id

        user_id = message.author.id

        now = asyncio.get_running_loop().time()

        guild_cooldowns = self.warning_cooldowns.setdefault(

            guild_id,

            {}
        )

        last_warning = guild_cooldowns.get(
            user_id,
            0
        )

        if (
            now - last_warning
            < WARNING_COOLDOWN
        ):

            return

        guild_cooldowns[
            user_id
        ] = now

        # ----------------------------------------------------
        # Find rules channel
        # ----------------------------------------------------

        rules_channel = rules_message.channel

        # ----------------------------------------------------
        # Warning
        # ----------------------------------------------------

        try:

            warning = await message.channel.send(

                f"⚠️ {message.author.mention} "
                "you must read and accept the server "
                f"rules before participating.\n\n"

                f"Please react with {ACCEPT_REACTION} "
                f"to the rules message in "
                f"{rules_channel.mention}.\n\n"

                f"[Go to Rules]({rules_message.jump_url})",

                delete_after=10
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):

            return

    # ========================================================
    # RAW REACTION LISTENER
    # ========================================================

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self,
        payload
    ):

        # ----------------------------------------------------
        # Ignore DMs
        # ----------------------------------------------------

        if payload.guild_id is None:
            return

        # ----------------------------------------------------
        # Ignore bot reactions
        # ----------------------------------------------------

        if payload.member and payload.member.bot:
            return

        config = self.get_guild_config(
            payload.guild_id
        )

        if not config:
            return

        # ----------------------------------------------------
        # Check message
        # ----------------------------------------------------

        rules_message_id = config.get(
            "message_id"
        )

        if not rules_message_id:
            return

        if payload.message_id != int(
            rules_message_id
        ):

            return

        # ----------------------------------------------------
        # Only 👍 counts
        # ----------------------------------------------------

        if str(
            payload.emoji
        ) != ACCEPT_REACTION:

            return

        # ----------------------------------------------------
        # Accepted
        # ----------------------------------------------------

        guild = self.bot.get_guild(
            payload.guild_id
        )

        if guild is None:
            return

        member = payload.member

        if member is None:

            try:

                member = await guild.fetch_member(
                    payload.user_id
                )

            except Exception:

                return

        # ----------------------------------------------------
        # Remove cooldown
        # ----------------------------------------------------

        guild_cooldowns = self.warning_cooldowns.get(

            payload.guild_id,

            {}
        )

        guild_cooldowns.pop(
            payload.user_id,
            None
        )

        print(

            f"📜 {member} accepted the server rules "
            f"in {guild.name}."
        )

    # ========================================================
    # RAW REACTION REMOVE
    # ========================================================

    @commands.Cog.listener()
    async def on_raw_reaction_remove(
        self,
        payload
    ):

        if payload.guild_id is None:
            return

        config = self.get_guild_config(
            payload.guild_id
        )

        if not config:
            return

        rules_message_id = config.get(
            "message_id"
        )

        if not rules_message_id:
            return

        if payload.message_id != int(
            rules_message_id
        ):

            return

        # ----------------------------------------------------
        # Only required reaction matters
        # ----------------------------------------------------

        if str(
            payload.emoji
        ) != ACCEPT_REACTION:

            return

        # ----------------------------------------------------
        # The member is automatically unaccepted because
        # we check the actual reaction every time they speak.
        # ----------------------------------------------------

        print(

            f"⚠️ User {payload.user_id} removed "
            "their rules reaction."
        )

    # ========================================================
    # ERROR HANDLER
    # ========================================================

    @rule.error
    async def rule_error(
        self,
        interaction,
        error
    ):

        if isinstance(
            error,
            app_commands.errors.MissingPermissions
        ):

            message = (
                "❌ You need Administrator permission "
                "to use `/rule`."
            )

        else:

            print(
                f"❌ /rule error: {error}"
            )

            message = (
                "❌ An error occurred while opening "
                "the rules setup."
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
        Rules(bot)
    )

    print(
        "✅ Rules Cog loaded."
    )

import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import string


# =========================================================
# CONFIGURATION
# =========================================================

CONFIG_FILE = "help_config.json"
TICKETS_FILE = "help_tickets.json"

# Moderator roles
MODERATOR_ROLE_NAMES = [
    "Moderator",
    "Moderators",
    "Mod",
]


# =========================================================
# FILE FUNCTIONS
# =========================================================

def load_json(filename):
    if not os.path.exists(filename):
        return {}

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)

    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# =========================================================
# TOKEN GENERATOR
# =========================================================

def generate_token(existing_tokens):

    while True:

        token = "H-" + "".join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=6
            )
        )

        if token not in existing_tokens:
            return token


# =========================================================
# MODERATOR CHECK
# =========================================================

def is_moderator(member: discord.Member):

    if member.guild_permissions.administrator:
        return True

    return any(
        role.name in MODERATOR_ROLE_NAMES
        for role in member.roles
    )


# =========================================================
# REPLY MODAL
# =========================================================

class ReplyModal(discord.ui.Modal):

    def __init__(self, cog, token):

        super().__init__(
            title=f"Reply to {token}"
        )

        self.cog = cog
        self.token = token

        self.message = discord.ui.TextInput(
            label="Your reply",
            placeholder="Type your response to the member...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.message)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        await self.cog.send_moderator_reply(
            interaction,
            self.token,
            str(self.message.value)
        )


# =========================================================
# REPLY BUTTON
# =========================================================

class ReplyButton(discord.ui.View):

    def __init__(self, cog, token):

        super().__init__(
            timeout=None
        )

        self.cog = cog
        self.token = token

        button = discord.ui.Button(
            label="Reply",
            emoji="↩️",
            style=discord.ButtonStyle.primary,
            custom_id=f"help_reply:{token}"
        )

        button.callback = self.reply_callback

        self.add_item(button)

    async def reply_callback(
        self,
        interaction: discord.Interaction
    ):

        # Check moderator
        if not isinstance(
            interaction.user,
            discord.Member
        ):

            await interaction.response.send_message(
                "❌ You cannot use this button here.",
                ephemeral=True
            )

            return

        if not is_moderator(interaction.user):

            await interaction.response.send_message(
                "❌ Only moderators can reply to support requests.",
                ephemeral=True
            )

            return

        # Check ticket
        ticket = self.cog.tickets.get(
            self.token
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ This support ticket no longer exists.",
                ephemeral=True
            )

            return

        if ticket.get("closed", False):

            await interaction.response.send_message(
                "❌ This support ticket is closed.",
                ephemeral=True
            )

            return

        # Open reply modal
        await interaction.response.send_modal(
            ReplyModal(
                self.cog,
                self.token
            )
        )


# =========================================================
# CLOSE BUTTON
# =========================================================

class CloseButton(discord.ui.View):

    def __init__(self, cog, token):

        super().__init__(
            timeout=None
        )

        self.cog = cog
        self.token = token

        reply_button = discord.ui.Button(
            label="Reply",
            emoji="↩️",
            style=discord.ButtonStyle.primary,
            custom_id=f"help_reply:{token}"
        )

        reply_button.callback = self.reply_callback

        close_button = discord.ui.Button(
            label="Close Ticket",
            emoji="🔒",
            style=discord.ButtonStyle.danger,
            custom_id=f"help_close:{token}"
        )

        close_button.callback = self.close_callback

        self.add_item(reply_button)
        self.add_item(close_button)

    async def reply_callback(
        self,
        interaction: discord.Interaction
    ):

        if not isinstance(
            interaction.user,
            discord.Member
        ):

            return

        if not is_moderator(interaction.user):

            await interaction.response.send_message(
                "❌ Only moderators can reply.",
                ephemeral=True
            )

            return

        ticket = self.cog.tickets.get(
            self.token
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ Ticket not found.",
                ephemeral=True
            )

            return

        if ticket.get("closed", False):

            await interaction.response.send_message(
                "❌ This ticket is already closed.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            ReplyModal(
                self.cog,
                self.token
            )
        )

    async def close_callback(
        self,
        interaction: discord.Interaction
    ):

        if not isinstance(
            interaction.user,
            discord.Member
        ):

            return

        if not is_moderator(interaction.user):

            await interaction.response.send_message(
                "❌ Only moderators can close tickets.",
                ephemeral=True
            )

            return

        ticket = self.cog.tickets.get(
            self.token
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ Ticket not found.",
                ephemeral=True
            )

            return

        ticket["closed"] = True
        ticket["closed_by"] = interaction.user.id

        self.cog.save_tickets()

        await interaction.response.send_message(
            f"🔒 Ticket **{self.token}** has been closed.",
            ephemeral=True
        )

        # Inform member
        try:

            user = await self.cog.bot.fetch_user(
                ticket["user_id"]
            )

            embed = discord.Embed(
                title="🔒 Support Ticket Closed",
                description=(
                    f"Your support ticket **{self.token}** "
                    "has been closed by the moderation team."
                ),
                color=discord.Color.red()
            )

            await user.send(
                embed=embed
            )

        except discord.HTTPException:
            pass


# =========================================================
# HELP COG
# =========================================================

class HelpSystem(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.config = load_json(
            CONFIG_FILE
        )

        self.tickets = load_json(
            TICKETS_FILE
        )

    # =====================================================
    # SAVE TICKETS
    # =====================================================

    def save_tickets(self):

        save_json(
            TICKETS_FILE,
            self.tickets
        )

    # =====================================================
    # FIND SUPPORT CHANNEL
    # =====================================================

    def get_support_channel(
        self,
        guild
    ):

        guild_config = self.config.get(
            str(guild.id)
        )

        if not guild_config:
            return None

        channel_id = guild_config.get(
            "channel_id"
        )

        if not channel_id:
            return None

        return guild.get_channel(
            channel_id
        )

    # =====================================================
    # /SETUPHELP
    # =====================================================

    @app_commands.command(
        name="setuphelp",
        description="Set the channel where support requests are sent."
    )
    @app_commands.describe(
        channel="The support channel"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def setuphelp(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

            return

        self.config[str(guild.id)] = {
            "channel_id": channel.id
        }

        save_json(
            CONFIG_FILE,
            self.config
        )

        await interaction.response.send_message(
            f"✅ Support system has been configured.\n\n"
            f"📨 Requests will be sent to {channel.mention}.",
            ephemeral=True
        )

    # =====================================================
    # /HELP
    # =====================================================

    @app_commands.command(
        name="help",
        description="Contact the moderation team for help."
    )
    @app_commands.describe(
        message="Explain what you need help with."
    )
    async def help_command(
        self,
        interaction: discord.Interaction,
        message: str
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

            return

        # -------------------------------------------------
        # Check support channel
        # -------------------------------------------------

        channel = self.get_support_channel(
            guild
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ The support system has not been configured yet.",
                ephemeral=True
            )

            return

        # -------------------------------------------------
        # Check if user already has open ticket
        # -------------------------------------------------

        for token, ticket in self.tickets.items():

            if (
                ticket.get("guild_id") == guild.id
                and ticket.get("user_id") == interaction.user.id
                and not ticket.get("closed", False)
            ):

                await interaction.response.send_message(
                    f"❌ You already have an open support ticket:\n"
                    f"🎫 **{token}**\n\n"
                    "Please continue the conversation through your "
                    "existing ticket.",
                    ephemeral=True
                )

                return

        # -------------------------------------------------
        # Generate token
        # -------------------------------------------------

        token = generate_token(
            self.tickets.keys()
        )

        # -------------------------------------------------
        # Save ticket
        # -------------------------------------------------

        self.tickets[token] = {
            "guild_id": guild.id,
            "user_id": interaction.user.id,
            "created_at": int(
                discord.utils.utcnow().timestamp()
            ),
            "closed": False
        }

        self.save_tickets()

        # -------------------------------------------------
        # Create support embed
        # -------------------------------------------------

        embed = discord.Embed(
            title="🆘 New Support Request",
            color=discord.Color.orange()
        )

        if guild.icon:

            embed.set_thumbnail(
                url=guild.icon.url
            )

        embed.add_field(
            name="🎫 Ticket",
            value=f"**{token}**",
            inline=True
        )

        embed.add_field(
            name="👤 Member",
            value=(
                f"{interaction.user.mention}\n"
                f"`{interaction.user}`"
            ),
            inline=True
        )

        embed.add_field(
            name="🏠 Server",
            value=guild.name,
            inline=True
        )

        embed.add_field(
            name="💬 Message",
            value=message,
            inline=False
        )

        embed.add_field(
            name="📌 How to respond",
            value=(
                "Click **↩️ Reply** below to send a private "
                "message directly to the member.\n\n"
                "The member can reply to the bot's DM and "
                "their response will appear here."
            ),
            inline=False
        )

        embed.set_footer(
            text=f"{guild.name} • Support System",
            icon_url=(
                guild.icon.url
                if guild.icon
                else None
            )
        )

        # -------------------------------------------------
        # Send to support channel
        # -------------------------------------------------

        try:

            support_message = await channel.send(
                embed=embed,
                view=CloseButton(
                    self,
                    token
                )
            )

            # Save support message ID
            self.tickets[token][
                "support_message_id"
            ] = support_message.id

            self.save_tickets()

        except discord.Forbidden:

            del self.tickets[token]

            self.save_tickets()

            await interaction.response.send_message(
                "❌ I don't have permission to send messages "
                "in the support channel.",
                ephemeral=True
            )

            return

        # -------------------------------------------------
        # Confirm to member
        # -------------------------------------------------

        await interaction.response.send_message(
            f"✅ Your support request has been sent to the "
            f"moderation team.\n\n"
            f"🎫 **Ticket:** `{token}`\n"
            f"📨 A moderator will reply to you through DM.",
            ephemeral=True
        )

    # =====================================================
    # MODERATOR REPLY
    # =====================================================

    async def send_moderator_reply(
        self,
        interaction,
        token,
        message
    ):

        ticket = self.tickets.get(
            token
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ Ticket not found.",
                ephemeral=True
            )

            return

        if ticket.get("closed", False):

            await interaction.response.send_message(
                "❌ This ticket is closed.",
                ephemeral=True
            )

            return

        # Get member
        try:

            member = await self.bot.fetch_user(
                ticket["user_id"]
            )

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ I couldn't find this member.",
                ephemeral=True
            )

            return

        guild = interaction.guild

        # -------------------------------------------------
        # DM Embed
        # -------------------------------------------------

        embed = discord.Embed(
            title="🛡️ Moderator Reply",
            description=message,
            color=discord.Color.blurple()
        )

        if guild and guild.icon:

            embed.set_thumbnail(
                url=guild.icon.url
            )

        embed.add_field(
            name="🎫 Ticket",
            value=f"`{token}`",
            inline=True
        )

        embed.add_field(
            name="🛡️ Moderator",
            value=interaction.user.mention,
            inline=True
        )

        embed.set_footer(
            text=f"{guild.name if guild else 'Support'} • Reply to continue"
        )

        # -------------------------------------------------
        # Send DM
        # -------------------------------------------------

        try:

            await member.send(
                embed=embed
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I couldn't send the member a DM. "
                "Their DMs may be disabled.",
                ephemeral=True
            )

            return

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ Discord rejected the DM.",
                ephemeral=True
            )

            return

        # -------------------------------------------------
        # Confirm to moderator
        # -------------------------------------------------

        await interaction.response.send_message(
            f"✅ Your reply was sent to {member.mention}.",
            ephemeral=True
        )

        # -------------------------------------------------
        # Also log reply in support channel
        # -------------------------------------------------

        channel = self.get_support_channel(
            guild
        )

        if channel:

            log_embed = discord.Embed(
                title="🛡️ Moderator Reply",
                description=message,
                color=discord.Color.green()
            )

            log_embed.add_field(
                name="🎫 Ticket",
                value=token,
                inline=True
            )

            log_embed.add_field(
                name="🛡️ Moderator",
                value=interaction.user.mention,
                inline=True
            )

            await channel.send(
                embed=log_embed
            )

    # =====================================================
    # MEMBER DM LISTENER
    # =====================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message
    ):

        # Ignore bots
        if message.author.bot:
            return

        # Only process DMs
        if message.guild is not None:
            return

        # -------------------------------------------------
        # Find user's open ticket
        # -------------------------------------------------

        active_ticket = None
        token = None

        for ticket_token, ticket in self.tickets.items():

            if (
                ticket.get("user_id") == message.author.id
                and not ticket.get("closed", False)
            ):

                active_ticket = ticket
                token = ticket_token
                break

        # No open ticket
        if active_ticket is None:
            return

        # -------------------------------------------------
        # Get guild
        # -------------------------------------------------

        guild = self.bot.get_guild(
            active_ticket["guild_id"]
        )

        if guild is None:
            return

        # -------------------------------------------------
        # Get support channel
        # -------------------------------------------------

        channel = self.get_support_channel(
            guild
        )

        if channel is None:
            return

        # -------------------------------------------------
        # Forward member message
        # -------------------------------------------------

        embed = discord.Embed(
            title="💬 Member Reply",
            description=message.content,
            color=discord.Color.blue()
        )

        embed.set_thumbnail(
            url=message.author.display_avatar.url
        )

        embed.add_field(
            name="🎫 Ticket",
            value=f"**{token}**",
            inline=True
        )

        embed.add_field(
            name="👤 Member",
            value=message.author.mention,
            inline=True
        )

        embed.set_footer(
            text=f"{guild.name} • Member Reply"
        )

        try:

            await channel.send(
                embed=embed,
                view=ReplyButton(
                    self,
                    token
                )
            )

            # Confirm to member
            await message.author.send(
                f"✅ Your message has been sent to the "
                f"moderation team.\n"
                f"🎫 Ticket: `{token}`"
            )

        except discord.HTTPException as e:

            print(
                f"❌ Failed to forward DM: {e}"
            )

    # =====================================================
    # /CLOSEHELP
    # =====================================================

    @app_commands.command(
        name="closehelp",
        description="Close an active support ticket."
    )
    @app_commands.describe(
        token="The support ticket token."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def closehelp(
        self,
        interaction: discord.Interaction,
        token: str
    ):

        token = token.upper()

        ticket = self.tickets.get(
            token
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ Ticket not found.",
                ephemeral=True
            )

            return

        if ticket.get("closed", False):

            await interaction.response.send_message(
                "❌ This ticket is already closed.",
                ephemeral=True
            )

            return

        ticket["closed"] = True
        ticket["closed_by"] = interaction.user.id

        self.save_tickets()

        # Inform member
        try:

            member = await self.bot.fetch_user(
                ticket["user_id"]
            )

            embed = discord.Embed(
                title="🔒 Support Ticket Closed",
                description=(
                    f"Your support ticket **{token}** "
                    "has been closed.\n\n"
                    "If you need further assistance, "
                    "you can create a new `/help` request."
                ),
                color=discord.Color.red()
            )

            await member.send(
                embed=embed
            )

        except discord.HTTPException:
            pass

        await interaction.response.send_message(
            f"🔒 Ticket **{token}** has been closed.",
            ephemeral=True
        )

    # =====================================================
    # SETUP ERROR
    # =====================================================

    @setuphelp.error
    async def setuphelp_error(
        self,
        interaction,
        error
    ):

        if isinstance(
            error,
            app_commands.errors.MissingPermissions
        ):

            await interaction.response.send_message(
                "❌ You need **Administrator** permission.",
                ephemeral=True
            )

    @closehelp.error
    async def closehelp_error(
        self,
        interaction,
        error
    ):

        if isinstance(
            error,
            app_commands.errors.MissingPermissions
        ):

            await interaction.response.send_message(
                "❌ You need **Administrator** permission.",
                ephemeral=True
            )


# =========================================================
# COG SETUP
# =========================================================

async def setup(bot):

    await bot.add_cog(
        HelpSystem(bot)
    )

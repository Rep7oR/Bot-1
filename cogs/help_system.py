
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

SUPPORT_COUNTER_PREFIX = "🎫 Support Tickets: "

MODERATOR_ROLE_NAMES = [
    "MODERATOR",
    "Moderators",
    "Mod",
]


# =========================================================
# JSON FUNCTIONS
# =========================================================

def load_json(filename):

    if not os.path.exists(filename):
        return {}

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        # Normal JSON object
        if isinstance(data, dict):
            return data

        # Handle JSON that was accidentally saved
        # as a string containing another JSON object
        if isinstance(data, str):

            try:

                nested_data = json.loads(data)

                if isinstance(nested_data, dict):
                    return nested_data

            except json.JSONDecodeError:
                pass

        # Config/tickets must always be dictionaries
        print(
            f"⚠️ {filename} does not contain "
            f"a valid JSON object. Using empty data."
        )

        return {}

    except (
        json.JSONDecodeError,
        FileNotFoundError,
        TypeError
    ):

        print(
            f"⚠️ Could not load {filename}. "
            f"Using empty data."
        )

        return {}


def save_json(filename, data):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4
        )


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
# SUPPORT MODAL
# =========================================================

class SupportModal(
    discord.ui.Modal,
    title="🆘 Support Request"
):

    subject = discord.ui.TextInput(

        label="Subject",

        placeholder=(
            "What do you need help with?"
        ),

        max_length=100,

        required=True
    )

    message = discord.ui.TextInput(

        label="Describe your problem",

        placeholder=(
            "Please explain your problem in detail..."
        ),

        style=discord.TextStyle.paragraph,

        max_length=1000,

        required=True
    )

    def __init__(self, cog):

        super().__init__()

        self.cog = cog

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        await self.cog.create_support_request(

            interaction,

            str(self.subject),

            str(self.message)
        )


# =========================================================
# SUPPORT SETUP VIEW
# =========================================================

class SupportSetupView(
    discord.ui.View
):

    def __init__(self, cog):

        super().__init__(
            timeout=None
        )

        self.cog = cog

    @discord.ui.button(

        label="Get Support",

        emoji="🆘",

        style=discord.ButtonStyle.primary,

        custom_id="support_open_form"
    )
    async def get_support(

        self,

        interaction: discord.Interaction,

        button: discord.ui.Button
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(

                "❌ This button can only be used "
                "inside a server.",

                ephemeral=True
            )

            return

        # ---------------------------------------------
        # CHECK SUPPORT SYSTEM
        # ---------------------------------------------

        support_channel = self.cog.get_support_channel(
            guild
        )

        if support_channel is None:

            await interaction.response.send_message(

                "❌ The support system has not been "
                "configured yet.",

                ephemeral=True
            )

            return

        # ---------------------------------------------
        # CHECK EXISTING REQUEST
        # ---------------------------------------------

        for token, ticket in self.cog.tickets.items():

            if (
                ticket.get("guild_id") == guild.id
                and ticket.get("user_id") == interaction.user.id
                and not ticket.get("closed", False)
            ):

                existing_channel = None

                channel_id = ticket.get(
                    "channel_id"
                )

                if channel_id:

                    existing_channel = guild.get_channel(
                        channel_id
                    )

                if existing_channel:

                    await interaction.response.send_message(

                        f"❌ You already have an open "
                        f"support ticket.\n\n"
                        f"🎫 **Ticket:** `{token}`\n"
                        f"📂 **Channel:** "
                        f"{existing_channel.mention}",

                        ephemeral=True
                    )

                else:

                    await interaction.response.send_message(

                        f"❌ You already have an active "
                        f"support request.\n\n"
                        f"🎫 **Ticket:** `{token}`\n\n"
                        f"Please wait for a moderator "
                        f"to open it.",

                        ephemeral=True
                    )

                return

        # ---------------------------------------------
        # OPEN FORM
        # ---------------------------------------------

        await interaction.response.send_modal(

            SupportModal(
                self.cog
            )
        )


# =========================================================
# MODERATOR SUPPORT REQUEST VIEW
# =========================================================

class TicketView(
    discord.ui.View
):

    def __init__(
        self,
        cog,
        token
    ):

        super().__init__(
            timeout=None
        )

        self.cog = cog
        self.token = token

    # =====================================================
    # OPEN TICKET
    # =====================================================

    @discord.ui.button(

        label="Open Ticket",

        emoji="🎫",

        style=discord.ButtonStyle.success,

        custom_id="support_open_ticket"
    )
    async def open_ticket(

        self,

        interaction: discord.Interaction,

        button: discord.ui.Button
    ):

        if not isinstance(
            interaction.user,
            discord.Member
        ):

            return

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(

                "❌ Only moderators can open "
                "support tickets.",

                ephemeral=True
            )

            return

        ticket = self.cog.tickets.get(
            self.token
        )

        if not ticket:

            await interaction.response.send_message(

                "❌ This ticket no longer exists.",

                ephemeral=True
            )

            return

        if ticket.get(
            "closed",
            False
        ):

            await interaction.response.send_message(

                "❌ This ticket is already closed.",

                ephemeral=True
            )

            return

        existing_channel_id = ticket.get(
            "channel_id"
        )

        if existing_channel_id:

            existing_channel = interaction.guild.get_channel(
                existing_channel_id
            )

            if existing_channel:

                await interaction.response.send_message(

                    f"⚠️ This ticket is already open:\n"
                    f"{existing_channel.mention}",

                    ephemeral=True
                )

                return

        await interaction.response.defer(
            ephemeral=True
        )

        channel = await self.cog.create_ticket_channel(

            interaction.guild,

            ticket,

            self.token,

            interaction.user
        )

        if channel is None:

            await interaction.followup.send(

                "❌ I couldn't create the private "
                "ticket channel.\n\n"
                "Please check that I have "
                "**Manage Channels** permission.",

                ephemeral=True
            )

            return

        await interaction.followup.send(

            f"🎫 **Ticket opened successfully.**\n"
            f"📂 {channel.mention}",

            ephemeral=True
        )


# =========================================================
# PRIVATE TICKET VIEW
# =========================================================

class PrivateTicketView(
    discord.ui.View
):

    def __init__(
        self,
        cog,
        token
    ):

        super().__init__(
            timeout=None
        )

        self.cog = cog
        self.token = token

    # =====================================================
    # CLOSE TICKET
    # =====================================================

    @discord.ui.button(

        label="Close Ticket",

        emoji="🔒",

        style=discord.ButtonStyle.danger,

        custom_id="support_close_ticket"
    )
    async def close_ticket_button(

        self,

        interaction: discord.Interaction,

        button: discord.ui.Button
    ):

        if not isinstance(
            interaction.user,
            discord.Member
        ):

            return

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(

                "❌ Only moderators can close "
                "this ticket.",

                ephemeral=True
            )

            return

        ticket = self.cog.tickets.get(
            self.token
        )

        if not ticket:

            await interaction.response.send_message(

                "❌ Ticket information could "
                "not be found.",

                ephemeral=True
            )

            return

        if ticket.get(
            "closed",
            False
        ):

            await interaction.response.send_message(

                "❌ This ticket is already closed.",

                ephemeral=True
            )

            return

        await interaction.response.send_message(

            "🔒 Closing ticket...",

            ephemeral=True
        )

        await self.cog.close_ticket(

            interaction.guild,

            self.token,

            interaction.user
        )


# =========================================================
# HELP SYSTEM
# =========================================================

class HelpSystem(
    commands.Cog
):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        self.config = load_json(
            CONFIG_FILE
        )

        self.tickets = load_json(
            TICKETS_FILE
        )

    # =====================================================
    # COG LOAD
    # =====================================================

    async def cog_load(self):

        # Persistent support setup button
        self.bot.add_view(
            SupportSetupView(
                self
            )
        )

        # Persistent ticket buttons
        for token, ticket in self.tickets.items():

            if ticket.get(
                "closed",
                False
            ):

                continue

            support_message_id = ticket.get(
                "support_message_id"
            )

            if support_message_id:

                self.bot.add_view(

                    TicketView(
                        self,
                        token
                    ),

                    message_id=support_message_id
                )

            channel_id = ticket.get(
                "channel_id"
            )

            if channel_id:

                self.bot.add_view(

                    PrivateTicketView(
                        self,
                        token
                    )
                )

        # Restore counters
        for guild in self.bot.guilds:

            try:

                await self.update_support_counter(
                    guild
                )

            except Exception as e:

                print(
                    f"❌ Counter restore error "
                    f"for {guild.name}: {e}"
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
    # SAVE CONFIG
    # =====================================================

    def save_config(self):

        save_json(
            CONFIG_FILE,
            self.config
        )

    # =====================================================
    # GET GUILD CONFIG
    # =====================================================

    def get_guild_config(
        self,
        guild: discord.Guild
    ):

        guild_id = str(
            guild.id
        )

        if guild_id not in self.config:

            self.config[guild_id] = {}

        return self.config[guild_id]

    # =====================================================
    # GET SUPPORT CHANNEL
    # =====================================================

    def get_support_channel(
        self,
        guild: discord.Guild
    ):

        guild_config = self.config.get(

            str(guild.id),

            {}
        )

        channel_id = guild_config.get(
            "channel_id"
        )

        if not channel_id:

            return None

        channel = guild.get_channel(
            channel_id
        )

        if isinstance(
            channel,
            discord.TextChannel
        ):

            return channel

        return None

    # =====================================================
    # GET TICKET CATEGORY
    # =====================================================

    def get_ticket_category(
        self,
        guild: discord.Guild
    ):

        guild_config = self.config.get(

            str(guild.id),

            {}
        )

        category_id = guild_config.get(
            "category_id"
        )

        if not category_id:

            return None

        category = guild.get_channel(
            category_id
        )

        if isinstance(
            category,
            discord.CategoryChannel
        ):

            return category

        return None

    # =====================================================
    # GET COUNTER CATEGORY
    # =====================================================

    def get_counter_category(
        self,
        guild: discord.Guild
    ):

        guild_config = self.config.get(

            str(guild.id),

            {}
        )

        category_id = guild_config.get(
            "counter_category_id"
        )

        if not category_id:

            return None

        category = guild.get_channel(
            category_id
        )

        if isinstance(
            category,
            discord.CategoryChannel
        ):

            return category

        return None

    # =====================================================
    # GET COUNTER CHANNEL
    # =====================================================

    def get_counter_channel(
        self,
        guild: discord.Guild
    ):

        guild_config = self.config.get(

            str(guild.id),

            {}
        )

        channel_id = guild_config.get(
            "counter_channel_id"
        )

        if not channel_id:

            return None

        channel = guild.get_channel(
            channel_id
        )

        if isinstance(
            channel,
            discord.VoiceChannel
        ):

            return channel

        return None

    # =====================================================
    # COUNT OPEN TICKETS
    # =====================================================

    def count_open_tickets(
        self,
        guild: discord.Guild
    ):

        count = 0

        for ticket in self.tickets.values():

            if (

                ticket.get("guild_id") == guild.id

                and

                not ticket.get(
                    "closed",
                    False
                )

            ):

                count += 1

        return count

    # =====================================================
    # UPDATE COUNTER
    # =====================================================

    async def update_support_counter(
        self,
        guild: discord.Guild
    ):

        category = self.get_counter_category(
            guild
        )

        if category is None:

            return

        count = self.count_open_tickets(
            guild
        )

        counter = self.get_counter_channel(
            guild
        )

        # -------------------------------------------------
        # CREATE COUNTER
        # -------------------------------------------------

        if counter is None:

            try:

                counter = await guild.create_voice_channel(

                    name=(
                        f"{SUPPORT_COUNTER_PREFIX}"
                        f"{count}"
                    ),

                    category=category,

                    reason=(
                        "Create live support "
                        "ticket counter"
                    )
                )

                guild_config = self.get_guild_config(
                    guild
                )

                guild_config[
                    "counter_channel_id"
                ] = counter.id

                self.save_config()

            except discord.Forbidden:

                print(
                    f"❌ Missing Manage Channels "
                    f"permission in {guild.name}"
                )

                return

            except discord.HTTPException as e:

                print(
                    f"❌ Counter creation failed: {e}"
                )

                return

        # -------------------------------------------------
        # MAKE SURE COUNTER IS IN CORRECT CATEGORY
        # -------------------------------------------------

        if counter.category_id != category.id:

            try:

                await counter.edit(
                    category=category
                )

            except discord.HTTPException:

                pass

        # -------------------------------------------------
        # UPDATE COUNTER NAME
        # -------------------------------------------------

        new_name = (
            f"{SUPPORT_COUNTER_PREFIX}"
            f"{count}"
        )

        if counter.name != new_name:

            try:

                await counter.edit(
                    name=new_name,
                    reason=(
                        "Update support "
                        "ticket counter"
                    )
                )

            except discord.HTTPException as e:

                print(
                    f"❌ Counter update failed: {e}"
                )

    # =====================================================
    # /SUPPORTSETUP
    # =====================================================

    @app_commands.command(

        name="supportsetup",

        description=(
            "Create the permanent support form."
        )
    )
    @app_commands.describe(

        channel=(
            "The channel where the support form "
            "will be posted."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def supportsetup(

        self,

        interaction: discord.Interaction,

        channel: discord.TextChannel

    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(

                "❌ This command can only be used "
                "inside a server.",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # SAVE SUPPORT CHANNEL
        # -------------------------------------------------

        guild_config = self.get_guild_config(
            guild
        )

        guild_config[
            "channel_id"
        ] = channel.id

        self.save_config()

        # -------------------------------------------------
        # SUPPORT FORM EMBED
        # -------------------------------------------------

        embed = discord.Embed(

            title="🆘 Need Support?",

            description=(

                "Need help from our moderation team?\n\n"

                "Click the button below to submit "
                "a support request.\n\n"

                "You **do not need to use `/support`**.\n"
                "Simply click **🆘 Get Support** and "
                "fill in the form.\n\n"

                "Your request will be sent to the "
                "moderation team."
            ),

            color=discord.Color.blurple()
        )

        if guild.icon:

            embed.set_thumbnail(
                url=guild.icon.url
            )

        embed.add_field(

            name="📋 How it works",

            value=(

                "1️⃣ Click **🆘 Get Support**\n"
                "2️⃣ Fill out the support form\n"
                "3️⃣ Submit your request\n"
                "4️⃣ Wait for a moderator to assist you"

            ),

            inline=False
        )

        embed.set_footer(

            text=(
                f"{guild.name} • Support System"
            ),

            icon_url=(

                guild.icon.url

                if guild.icon

                else None
            )
        )

        # -------------------------------------------------
        # SEND FORM
        # -------------------------------------------------

        try:

            message = await channel.send(

                embed=embed,

                view=SupportSetupView(
                    self
                )
            )

        except discord.Forbidden:

            await interaction.response.send_message(

                f"❌ I don't have permission to "
                f"send messages in {channel.mention}.",

                ephemeral=True
            )

            return

        except discord.HTTPException as e:

            await interaction.response.send_message(

                f"❌ Discord returned an error:\n"
                f"`{e}`",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # SAVE FORM MESSAGE
        # -------------------------------------------------

        guild_config[
            "support_setup_message_id"
        ] = message.id

        self.save_config()

        # -------------------------------------------------
        # CONFIRM
        # -------------------------------------------------

        await interaction.response.send_message(

            f"✅ **Support form created.**\n\n"
            f"📨 Channel: {channel.mention}\n"
            f"🆔 Message ID: `{message.id}`\n\n"
            f"Members can now click **🆘 Get Support** "
            f"without using `/support`.",

            ephemeral=True
        )

    # =====================================================
    # /SETUPHELP
    # =====================================================

    @app_commands.command(

        name="setuphelp",

        description=(
            "Set the channel where support requests "
            "are posted."
        )
    )
    @app_commands.describe(

        channel="The support request channel."
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

                "❌ This command can only be used "
                "inside a server.",

                ephemeral=True
            )

            return

        guild_config = self.get_guild_config(
            guild
        )

        guild_config[
            "channel_id"
        ] = channel.id

        self.save_config()

        await interaction.response.send_message(

            f"✅ **Support request channel configured.**\n\n"
            f"📨 {channel.mention}\n\n"
            f"Use `/supportsetup` to place the "
            f"member support form there.",

            ephemeral=True
        )

    # =====================================================
    # /SETUPHELPCATEGORY
    # =====================================================

    @app_commands.command(

        name="setuphelpcategory",

        description=(
            "Set the category where private "
            "support tickets are created."
        )
    )
    @app_commands.describe(

        category="Private ticket category."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def setuphelpcategory(

        self,

        interaction: discord.Interaction,

        category: discord.CategoryChannel

    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(

                "❌ This command can only be used "
                "inside a server.",

                ephemeral=True
            )

            return

        guild_config = self.get_guild_config(
            guild
        )

        guild_config[
            "category_id"
        ] = category.id

        self.save_config()

        await interaction.response.send_message(

            f"✅ **Private ticket category configured.**\n\n"
            f"📂 **{category.name}**",

            ephemeral=True
        )

    # =====================================================
    # /SETUPHELPCOUNTER
    # =====================================================

    @app_commands.command(

        name="setuphelpcounter",

        description=(
            "Set the category for the live "
            "support ticket counter."
        )
    )
    @app_commands.describe(

        category=(
            "Category where the support counter "
            "will be created."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def setuphelpcounter(

        self,

        interaction: discord.Interaction,

        category: discord.CategoryChannel

    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(

                "❌ This command can only be used "
                "inside a server.",

                ephemeral=True
            )

            return

        guild_config = self.get_guild_config(
            guild
        )

        guild_config[
            "counter_category_id"
        ] = category.id

        self.save_config()

        await self.update_support_counter(
            guild
        )

        counter = self.get_counter_channel(
            guild
        )

        if counter:

            await interaction.response.send_message(

                f"✅ **Support counter configured.**\n\n"
                f"📂 Category: **{category.name}**\n"
                f"🎫 Counter: {counter.mention}\n\n"
                f"The counter will automatically "
                f"update when requests are created "
                f"and closed.",

                ephemeral=True
            )

        else:

            await interaction.response.send_message(

                "⚠️ The category was saved, but I "
                "couldn't create the counter.\n\n"
                "Make sure I have **Manage Channels** "
                "permission.",

                ephemeral=True
            )

    # =====================================================
    # CREATE SUPPORT REQUEST
    # =====================================================

    async def create_support_request(

        self,

        interaction: discord.Interaction,

        subject: str,

        message: str

    ):

        guild = interaction.guild

        if guild is None:

            return

        support_channel = self.get_support_channel(
            guild
        )

        if support_channel is None:

            await interaction.response.send_message(

                "❌ The support system has not "
                "been configured yet.",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # CHECK DUPLICATE REQUEST
        # -------------------------------------------------

        for token, ticket in self.tickets.items():

            if (

                ticket.get("guild_id") == guild.id

                and

                ticket.get("user_id")
                == interaction.user.id

                and

                not ticket.get(
                    "closed",
                    False
                )

            ):

                await interaction.response.send_message(

                    f"❌ You already have an active "
                    f"support request.\n\n"
                    f"🎫 Ticket: `{token}`",

                    ephemeral=True
                )

                return

        # -------------------------------------------------
        # GENERATE TOKEN
        # -------------------------------------------------

        token = generate_token(
            self.tickets.keys()
        )

        # -------------------------------------------------
        # SAVE TICKET
        # -------------------------------------------------

        self.tickets[token] = {

            "guild_id":
                guild.id,

            "user_id":
                interaction.user.id,

            "username":
                str(interaction.user),

            "subject":
                subject,

            "message":
                message,

            "created_at":
                int(
                    discord.utils.utcnow().timestamp()
                ),

            "closed":
                False,

            "channel_id":
                None,

            "opened_by":
                None,

            "support_message_id":
                None
        }

        self.save_tickets()

        # -------------------------------------------------
        # CREATE EMBED
        # -------------------------------------------------

        embed = discord.Embed(

            title="🆘 New Support Request",

            description=(
                "A member has requested assistance."
            ),

            color=discord.Color.orange()
        )

        if guild.icon:

            embed.set_thumbnail(
                url=guild.icon.url
            )

        embed.add_field(

            name="🎫 Ticket",

            value=f"`{token}`",

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

            name="📌 Subject",

            value=subject,

            inline=False
        )

        embed.add_field(

            name="💬 Request",

            value=message,

            inline=False
        )

        embed.add_field(

            name="📌 Moderator Action",

            value=(

                "Click **🎫 Open Ticket** to create "
                "a private support channel."

            ),

            inline=False
        )

        embed.set_footer(

            text=(
                f"{guild.name} • Support System"
            ),

            icon_url=(

                guild.icon.url

                if guild.icon

                else None
            )
        )

        # -------------------------------------------------
        # SEND REQUEST
        # -------------------------------------------------

        try:

            support_message = await support_channel.send(

                embed=embed,

                view=TicketView(

                    self,

                    token
                )
            )

        except discord.Forbidden:

            del self.tickets[token]

            self.save_tickets()

            await interaction.response.send_message(

                "❌ I cannot send messages in "
                "the support channel.",

                ephemeral=True
            )

            return

        except discord.HTTPException:

            del self.tickets[token]

            self.save_tickets()

            await interaction.response.send_message(

                "❌ Discord returned an error while "
                "creating your support request.",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # SAVE MESSAGE ID
        # -------------------------------------------------

        self.tickets[token][
            "support_message_id"
        ] = support_message.id

        self.save_tickets()

        # -------------------------------------------------
        # UPDATE COUNTER
        # -------------------------------------------------

        await self.update_support_counter(
            guild
        )

        # -------------------------------------------------
        # CONFIRM TO MEMBER
        # -------------------------------------------------

        await interaction.response.send_message(

            f"✅ **Support request submitted!**\n\n"
            f"🎫 Ticket: `{token}`\n"
            f"📨 Your request has been sent to "
            f"the moderation team.\n\n"
            f"Please wait for a moderator to "
            f"open your private ticket.",

            ephemeral=True
        )

    # =====================================================
    # CREATE PRIVATE TICKET
    # =====================================================

    async def create_ticket_channel(

        self,

        guild: discord.Guild,

        ticket: dict,

        token: str,

        moderator: discord.Member

    ):

        # -------------------------------------------------
        # MEMBER
        # -------------------------------------------------

        try:

            member = guild.get_member(
                ticket["user_id"]
            )

            if member is None:

                member = await guild.fetch_member(
                    ticket["user_id"]
                )

        except discord.HTTPException:

            return None

        # -------------------------------------------------
        # CATEGORY
        # -------------------------------------------------

        category = self.get_ticket_category(
            guild
        )

        if category is None:

            return None

        # -------------------------------------------------
        # PERMISSIONS
        # -------------------------------------------------

        overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            member:
                discord.PermissionOverwrite(

                    view_channel=True,

                    send_messages=True,

                    read_message_history=True,

                    attach_files=True,

                    embed_links=True
                ),

            moderator:
                discord.PermissionOverwrite(

                    view_channel=True,

                    send_messages=True,

                    read_message_history=True,

                    manage_messages=True,

                    attach_files=True,

                    embed_links=True
                )
        }

        # -------------------------------------------------
        # MODERATOR ROLES
        # -------------------------------------------------

        for role in guild.roles:

            if role.name in MODERATOR_ROLE_NAMES:

                overwrites[role] = discord.PermissionOverwrite(

                    view_channel=True,

                    send_messages=True,

                    read_message_history=True,

                    manage_messages=True,

                    attach_files=True,

                    embed_links=True
                )

        # -------------------------------------------------
        # CREATE CHANNEL
        # -------------------------------------------------

        try:

            ticket_channel = await guild.create_text_channel(

                name=(
                    f"ticket-{token.lower()}"
                ),

                category=category,

                overwrites=overwrites,

                topic=(
                    f"Support Ticket {token} | "
                    f"Member: {member} ({member.id})"
                ),

                reason=(
                    f"Support ticket {token} "
                    f"opened by {moderator}"
                )
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):

            return None

        # -------------------------------------------------
        # SAVE CHANNEL
        # -------------------------------------------------

        ticket[
            "channel_id"
        ] = ticket_channel.id

        ticket[
            "opened_by"
        ] = moderator.id

        ticket[
            "opened_at"
        ] = int(
            discord.utils.utcnow().timestamp()
        )

        self.save_tickets()

        # -------------------------------------------------
        # TICKET EMBED
        # -------------------------------------------------

        embed = discord.Embed(

            title="🎫 Support Ticket",

            description=(

                f"Welcome {member.mention}!\n\n"

                "A moderator has opened your "
                "private support ticket.\n\n"

                "Only you and the moderation team "
                "can see this channel."
            ),

            color=discord.Color.blurple()
        )

        if guild.icon:

            embed.set_thumbnail(
                url=guild.icon.url
            )

        embed.add_field(

            name="🎫 Ticket",

            value=f"`{token}`",

            inline=True
        )

        embed.add_field(

            name="👤 Member",

            value=member.mention,

            inline=True
        )

        embed.add_field(

            name="🛡️ Moderator",

            value=moderator.mention,

            inline=True
        )

        embed.add_field(

            name="📌 Subject",

            value=ticket.get(
                "subject",
                "Support"
            ),

            inline=False
        )

        embed.add_field(

            name="💬 Original Request",

            value=ticket.get(
                "message",
                "No description"
            ),

            inline=False
        )

        embed.set_footer(

            text=(
                f"{guild.name} • Private Support"
            ),

            icon_url=(

                guild.icon.url

                if guild.icon

                else None
            )
        )

        # -------------------------------------------------
        # SEND PRIVATE TICKET
        # -------------------------------------------------

        try:

            await ticket_channel.send(

                content=(

                    f"{member.mention} "
                    f"{moderator.mention}"
                ),

                embed=embed,

                view=PrivateTicketView(

                    self,

                    token
                ),

                allowed_mentions=discord.AllowedMentions(
                    users=True
                )
            )

        except discord.HTTPException:

            try:

                await ticket_channel.delete()

            except discord.HTTPException:

                pass

            ticket[
                "channel_id"
            ] = None

            self.save_tickets()

            return None

        # -------------------------------------------------
        # MEMBER DM
        # -------------------------------------------------

        try:

            dm_embed = discord.Embed(

                title="🎫 Your Support Ticket Is Open",

                description=(

                    f"A moderator from **{guild.name}** "
                    "has opened a private support ticket.\n\n"

                    f"Ticket: `{token}`\n\n"

                    "Please continue the conversation "
                    f"in {ticket_channel.mention}."
                ),

                color=discord.Color.green()
            )

            await member.send(
                embed=dm_embed
            )

        except discord.HTTPException:

            pass

        return ticket_channel

    # =====================================================
    # CLOSE TICKET
    # =====================================================

    async def close_ticket(

        self,

        guild: discord.Guild,

        token: str,

        moderator: discord.Member

    ):

        ticket = self.tickets.get(
            token
        )

        if not ticket:

            return

        if ticket.get(
            "closed",
            False
        ):

            return

        # -------------------------------------------------
        # MARK CLOSED
        # -------------------------------------------------

        ticket[
            "closed"
        ] = True

        ticket[
            "closed_by"
        ] = moderator.id

        ticket[
            "closed_at"
        ] = int(
            discord.utils.utcnow().timestamp()
        )

        self.save_tickets()

        # -------------------------------------------------
        # UPDATE COUNTER FIRST
        # -------------------------------------------------

        await self.update_support_counter(
            guild
        )

        # -------------------------------------------------
        # GET MEMBER
        # -------------------------------------------------

        try:

            member = await self.bot.fetch_user(
                ticket["user_id"]
            )

        except discord.HTTPException:

            member = None

        # -------------------------------------------------
        # MEMBER DM
        # -------------------------------------------------

        if member:

            try:

                embed = discord.Embed(

                    title="🔒 Support Ticket Closed",

                    description=(

                        f"Your support ticket "
                        f"`{token}` in **{guild.name}** "
                        "has been closed.\n\n"

                        "If you need help again, simply "
                        "click the **🆘 Get Support** button "
                        "in the support channel."
                    ),

                    color=discord.Color.red()
                )

                await member.send(
                    embed=embed
                )

            except discord.HTTPException:

                pass

        # -------------------------------------------------
        # DELETE PRIVATE CHANNEL
        # -------------------------------------------------

        channel_id = ticket.get(
            "channel_id"
        )

        if channel_id:

            ticket_channel = guild.get_channel(
                channel_id
            )

            if ticket_channel:

                try:

                    await ticket_channel.delete(

                        reason=(

                            f"Support ticket {token} "
                            f"closed by {moderator}"
                        )
                    )

                except (
                    discord.Forbidden,
                    discord.HTTPException
                ):

                    pass

        # -------------------------------------------------
        # DELETE SUPPORT REQUEST MESSAGE
        # -------------------------------------------------

        support_channel = self.get_support_channel(
            guild
        )

        message_id = ticket.get(
            "support_message_id"
        )

        if (
            support_channel
            and message_id
        ):

            try:

                message = await support_channel.fetch_message(
                    message_id
                )

                await message.delete()

            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):

                pass

        self.save_tickets()

        # -------------------------------------------------
        # FINAL COUNTER UPDATE
        # -------------------------------------------------

        await self.update_support_counter(
            guild
        )

    # =====================================================
    # /CLOSEHELP
    # =====================================================

    @app_commands.command(

        name="closehelp",

        description="Close a support ticket."
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

        if ticket.get(
            "closed",
            False
        ):

            await interaction.response.send_message(

                "❌ This ticket is already closed.",

                ephemeral=True
            )

            return

        await interaction.response.send_message(

            f"🔒 Closing ticket `{token}`...",

            ephemeral=True
        )

        await self.close_ticket(

            interaction.guild,

            token,

            interaction.user
        )

    # =====================================================
    # /HELPSTATUS
    # =====================================================

    @app_commands.command(

        name="helpstatus",

        description=(
            "Check the support system status."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def helpstatus(

        self,

        interaction: discord.Interaction

    ):

        guild = interaction.guild

        if guild is None:

            return

        support_channel = self.get_support_channel(
            guild
        )

        category = self.get_ticket_category(
            guild
        )

        counter_category = self.get_counter_category(
            guild
        )

        counter = self.get_counter_channel(
            guild
        )

        count = self.count_open_tickets(
            guild
        )

        await interaction.response.send_message(

            f"### 🆘 Support System\n\n"

            f"📨 **Support Channel:** "
            f"{support_channel.mention if support_channel else 'Not configured'}\n"

            f"📂 **Ticket Category:** "
            f"{category.mention if category else 'Not configured'}\n"

            f"🔨 **Counter Category:** "
            f"{counter_category.mention if counter_category else 'Not configured'}\n"

            f"🎫 **Counter:** "
            f"{counter.mention if counter else 'Not created'}\n"

            f"📊 **Active Requests:** "
            f"`{count}`",

            ephemeral=True
        )

    # =====================================================
    # ERROR HANDLERS
    # =====================================================

    @supportsetup.error
    async def supportsetup_error(

        self,

        interaction,

        error
    ):

        if isinstance(

            error,

            app_commands.errors.MissingPermissions

        ):

            await interaction.response.send_message(

                "❌ You need **Administrator** "
                "permission.",

                ephemeral=True
            )

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

                "❌ You need **Administrator** "
                "permission.",

                ephemeral=True
            )

    @setuphelpcategory.error
    async def setuphelpcategory_error(

        self,

        interaction,

        error
    ):

        if isinstance(

            error,

            app_commands.errors.MissingPermissions

        ):

            await interaction.response.send_message(

                "❌ You need **Administrator** "
                "permission.",

                ephemeral=True
            )

    @setuphelpcounter.error
    async def setuphelpcounter_error(

        self,

        interaction,

        error
    ):

        if isinstance(

            error,

            app_commands.errors.MissingPermissions

        ):

            await interaction.response.send_message(

                "❌ You need **Administrator** "
                "permission.",

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

                "❌ You need **Administrator** "
                "permission.",

                ephemeral=True
            )

    @helpstatus.error
    async def helpstatus_error(

        self,

        interaction,

        error
    ):

        if isinstance(

            error,

            app_commands.errors.MissingPermissions

        ):

            await interaction.response.send_message(

                "❌ You need **Administrator** "
                "permission.",

                ephemeral=True
            )


# =========================================================
# COG SETUP
# =========================================================

async def setup(bot):

    await bot.add_cog(
        HelpSystem(bot)
    )


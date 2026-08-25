
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

# =========================================================
# ADD YOUR MODERATOR ROLE NAMES HERE
# =========================================================

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

            return json.load(f)

    except (
        json.JSONDecodeError,
        FileNotFoundError
    ):

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

    # Administrators count as moderators
    if member.guild_permissions.administrator:

        return True

    return any(
        role.name in MODERATOR_ROLE_NAMES
        for role in member.roles
    )


# =========================================================
# SUPPORT REQUEST VIEW
# =========================================================

class TicketView(discord.ui.View):

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
    # OPEN TICKET BUTTON
    # =====================================================

    @discord.ui.button(
        label="Open Ticket",
        emoji="🎫",
        style=discord.ButtonStyle.success
    )
    async def open_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        # Must be a server member
        if not isinstance(
            interaction.user,
            discord.Member
        ):

            await interaction.response.send_message(
                "❌ This button can only be used inside a server.",
                ephemeral=True
            )

            return

        # Only moderators
        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Only moderators can open support tickets.",
                ephemeral=True
            )

            return

        # Find ticket
        ticket = self.cog.tickets.get(
            self.token
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ This ticket no longer exists.",
                ephemeral=True
            )

            return

        # Already closed
        if ticket.get(
            "closed",
            False
        ):

            await interaction.response.send_message(
                "❌ This ticket is already closed.",
                ephemeral=True
            )

            return

        # Already opened
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

        # Defer
        await interaction.response.defer(
            ephemeral=True
        )

        # Create private channel
        channel = await self.cog.create_ticket_channel(
            interaction.guild,
            ticket,
            self.token,
            interaction.user
        )

        if channel is None:

            await interaction.followup.send(
                "❌ I couldn't create the private ticket channel.\n"
                "Please check that I have **Manage Channels** permission.",
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
        style=discord.ButtonStyle.danger
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

        # Only moderators
        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Only moderators can close this ticket.",
                ephemeral=True
            )

            return

        ticket = self.cog.tickets.get(
            self.token
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ Ticket information could not be found.",
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
# HELP SYSTEM COG
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
    # SAVE TICKETS
    # =====================================================

    def save_tickets(self):

        save_json(
            TICKETS_FILE,
            self.tickets
        )

    # =====================================================
    # GET SUPPORT CHANNEL
    # =====================================================

    def get_support_channel(
        self,
        guild: discord.Guild
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
    # GET TICKET CATEGORY
    # =====================================================

    def get_ticket_category(
        self,
        guild: discord.Guild
    ):

        guild_config = self.config.get(
            str(guild.id)
        )

        if not guild_config:

            return None

        category_id = guild_config.get(
            "category_id"
        )

        if not category_id:

            return None

        return guild.get_channel(
            category_id
        )

    # =====================================================
    # /SETUPHELP
    # =====================================================

    @app_commands.command(
        name="setuphelp",
        description="Set the channel where help requests are posted."
    )
    @app_commands.describe(
        channel="The support channel."
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

        guild_id = str(
            guild.id
        )

        if guild_id not in self.config:

            self.config[guild_id] = {}

        self.config[guild_id][
            "channel_id"
        ] = channel.id

        save_json(
            CONFIG_FILE,
            self.config
        )

        await interaction.response.send_message(
            f"✅ Support channel configured.\n\n"
            f"📨 Requests will be posted in {channel.mention}",
            ephemeral=True
        )

    # =====================================================
    # /SETUPHELPCATEGORY
    # =====================================================

    @app_commands.command(
        name="setuphelpcategory",
        description="Set the category where private tickets are created."
    )
    @app_commands.describe(
        category="Category for private support tickets."
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
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

            return

        guild_id = str(
            guild.id
        )

        if guild_id not in self.config:

            self.config[guild_id] = {}

        self.config[guild_id][
            "category_id"
        ] = category.id

        save_json(
            CONFIG_FILE,
            self.config
        )

        await interaction.response.send_message(
            f"✅ Private ticket category configured.\n\n"
            f"📂 **{category.name}**",
            ephemeral=True
        )

    # =====================================================
    # /HELP
    #
    # AVAILABLE TO EVERY MEMBER
    # =====================================================

    @app_commands.command(
        name="help",
        description="Request help from the moderation team."
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

        support_channel = self.get_support_channel(
            guild
        )

        # -------------------------------------------------
        # SUPPORT CHANNEL NOT CONFIGURED
        # -------------------------------------------------

        if support_channel is None:

            await interaction.response.send_message(
                "❌ The support system has not been configured yet.\n\n"
                "Please ask an administrator to use `/setuphelp`.",
                ephemeral=True
            )

            return

        # -------------------------------------------------
        # CHECK EXISTING TICKET
        # -------------------------------------------------

        for token, ticket in self.tickets.items():

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
                        f"❌ You already have an open support ticket.\n\n"
                        f"🎫 **Ticket:** `{token}`\n"
                        f"📂 **Channel:** {existing_channel.mention}",
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

            "guild_id": guild.id,

            "user_id": interaction.user.id,

            "username": str(
                interaction.user
            ),

            "message": message,

            "created_at": int(
                discord.utils.utcnow().timestamp()
            ),

            "closed": False,

            "channel_id": None,

            "opened_by": None,

            "support_message_id": None
        }

        self.save_tickets()

        # -------------------------------------------------
        # CREATE SUPPORT EMBED
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
            name="💬 Request",
            value=message,
            inline=False
        )

        embed.add_field(
            name="📌 Moderator Action",
            value=(
                "Click **🎫 Open Ticket** to create a "
                "private conversation channel.\n\n"
                "Only the requesting member and moderation "
                "team will be able to see the conversation."
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
        # SEND SUPPORT REQUEST
        # -------------------------------------------------

        try:

            support_message = await support_channel.send(
                embed=embed,
                view=TicketView(
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
                "❌ I cannot send messages in the support channel.",
                ephemeral=True
            )

            return

        except discord.HTTPException:

            del self.tickets[token]

            self.save_tickets()

            await interaction.response.send_message(
                "❌ Discord returned an error while creating "
                "your support request.",
                ephemeral=True
            )

            return

        # -------------------------------------------------
        # MEMBER CONFIRMATION
        # -------------------------------------------------

        await interaction.response.send_message(
            f"✅ **Your support request has been submitted.**\n\n"
            f"🎫 **Ticket:** `{token}`\n"
            f"🛡️ A moderator will open a private ticket "
            f"for you.",
            ephemeral=True
        )

    # =====================================================
    # CREATE PRIVATE TICKET CHANNEL
    # =====================================================

    async def create_ticket_channel(
        self,
        guild: discord.Guild,
        ticket: dict,
        token: str,
        moderator: discord.Member
    ):

        # -------------------------------------------------
        # GET MEMBER
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
        # GET CATEGORY
        # -------------------------------------------------

        category = self.get_ticket_category(
            guild
        )

        # -------------------------------------------------
        # PERMISSIONS
        # -------------------------------------------------

        overwrites = {

            # Everyone cannot see
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),

            # Member
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            ),

            # Moderator who opened it
            moderator: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                attach_files=True,
                embed_links=True
            )
        }

        # -------------------------------------------------
        # ALL MODERATOR ROLES
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

        channel_name = (
            f"ticket-{token.lower()}"
        )

        try:

            ticket_channel = await guild.create_text_channel(

                name=channel_name,

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

        except discord.Forbidden:

            return None

        except discord.HTTPException:

            return None

        # -------------------------------------------------
        # SAVE CHANNEL
        # -------------------------------------------------

        ticket["channel_id"] = (
            ticket_channel.id
        )

        ticket["opened_by"] = (
            moderator.id
        )

        ticket["opened_at"] = int(
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
                "A moderator has opened your private "
                "support ticket.\n\n"
                "Only you and the moderation team can "
                "see this channel."
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
            name="💬 Original Request",
            value=ticket["message"],
            inline=False
        )

        embed.add_field(
            name="🔒 Privacy",
            value=(
                "This is a private support conversation. "
                "Only the member and moderation team "
                "can access this channel."
            ),
            inline=False
        )

        embed.set_footer(
            text=f"{guild.name} • Private Support",
            icon_url=(
                guild.icon.url
                if guild.icon
                else None
            )
        )

        # -------------------------------------------------
        # SEND TICKET HEADER
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

                await ticket_channel.delete(
                    reason="Failed to initialize ticket"
                )

            except discord.HTTPException:

                pass

            ticket["channel_id"] = None

            self.save_tickets()

            return None

        # -------------------------------------------------
        # DM MEMBER
        # -------------------------------------------------

        try:

            dm_embed = discord.Embed(
                title="🎫 Your Support Ticket Is Open",
                description=(
                    f"A moderator from **{guild.name}** "
                    "has opened a private support ticket "
                    "for you.\n\n"
                    "Please continue the conversation in "
                    f"{ticket_channel.mention}."
                ),
                color=discord.Color.green()
            )

            if guild.icon:

                dm_embed.set_thumbnail(
                    url=guild.icon.url
                )

            dm_embed.add_field(
                name="🎫 Ticket",
                value=f"`{token}`",
                inline=True
            )

            dm_embed.add_field(
                name="🛡️ Moderator",
                value=moderator.display_name,
                inline=True
            )

            dm_embed.set_footer(
                text=f"{guild.name} • Support System",
                icon_url=(
                    guild.icon.url
                    if guild.icon
                    else None
                )
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

        ticket["closed"] = True

        ticket["closed_by"] = (
            moderator.id
        )

        ticket["closed_at"] = int(
            discord.utils.utcnow().timestamp()
        )

        self.save_tickets()

        # =================================================
        # GET MEMBER
        # =================================================

        try:

            member = await self.bot.fetch_user(
                ticket["user_id"]
            )

        except discord.HTTPException:

            member = None

        # =================================================
        # SEND CLOSURE DM
        # =================================================

        if member:

            try:

                embed = discord.Embed(
                    title="🔒 Support Ticket Closed",
                    description=(
                        f"Your support ticket **{token}** "
                        f"in **{guild.name}** has been closed.\n\n"
                        "If you need help again, use "
                        "`/help` to create a new support request."
                    ),
                    color=discord.Color.red()
                )

                if guild.icon:

                    embed.set_thumbnail(
                        url=guild.icon.url
                    )

                embed.set_footer(
                    text=f"{guild.name} • Support System",
                    icon_url=(
                        guild.icon.url
                        if guild.icon
                        else None
                    )
                )

                await member.send(
                    embed=embed
                )

            except discord.HTTPException:

                pass

        # =================================================
        # DELETE PRIVATE TICKET CHANNEL
        # =================================================

        ticket_channel_id = ticket.get(
            "channel_id"
        )

        if ticket_channel_id:

            ticket_channel = guild.get_channel(
                ticket_channel_id
            )

            if ticket_channel:

                try:

                    await ticket_channel.delete(
                        reason=(
                            f"Support ticket {token} "
                            f"closed by {moderator}"
                        )
                    )

                    print(
                        f"🗑️ Deleted private ticket channel "
                        f"for {token}"
                    )

                except discord.Forbidden:

                    print(
                        f"❌ Cannot delete ticket channel "
                        f"for {token}"
                    )

                except discord.HTTPException as e:

                    print(
                        f"❌ Error deleting ticket channel "
                        f"{token}: {e}"
                    )

        # =================================================
        # DELETE ORIGINAL SUPPORT MESSAGE
        # =================================================

        support_channel = self.get_support_channel(
            guild
        )

        support_message_id = ticket.get(
            "support_message_id"
        )

        if (
            support_channel
            and support_message_id
        ):

            try:

                support_message = (
                    await support_channel.fetch_message(
                        support_message_id
                    )
                )

                await support_message.delete()

                print(
                    f"🗑️ Deleted support request "
                    f"{token} from #{support_channel.name}"
                )

            except discord.NotFound:

                # Already deleted
                pass

            except discord.Forbidden:

                print(
                    f"❌ Cannot delete support message "
                    f"for {token}"
                )

            except discord.HTTPException as e:

                print(
                    f"❌ Error deleting support message "
                    f"{token}: {e}"
                )

        # =================================================
        # SAVE FINAL STATE
        # =================================================

        self.save_tickets()

        print(
            f"🔒 Ticket {token} completely closed "
            f"by {moderator}"
        )

    # =====================================================
    # /CLOSEHELP
    # =====================================================

    @app_commands.command(
        name="closehelp",
        description="Close a support ticket."
    )
    @app_commands.describe(
        token="The ticket token."
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
        description="Check the support system configuration."
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

            await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

            return

        guild_config = self.config.get(
            str(guild.id),
            {}
        )

        support_channel = self.get_support_channel(
            guild
        )

        category = self.get_ticket_category(
            guild
        )

        # Count open tickets
        open_tickets = 0

        for ticket in self.tickets.values():

            if (
                ticket.get("guild_id") == guild.id
                and not ticket.get("closed", False)
            ):

                open_tickets += 1

        await interaction.response.send_message(

            f"### 🆘 Support System\n\n"

            f"📨 **Support Channel:** "
            f"{support_channel.mention if support_channel else 'Not configured'}\n"

            f"📂 **Ticket Category:** "
            f"{category.mention if category else 'Not configured'}\n"

            f"🎫 **Open Tickets:** "
            f"`{open_tickets}`",

            ephemeral=True
        )

    # =====================================================
    # ERROR HANDLERS
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

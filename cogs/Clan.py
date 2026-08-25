import discord
from discord.ext import commands
from discord import app_commands, ui


# ============================================================
# CONFIGURATION
# ============================================================

# The Discord role that is allowed to approve/reject clans
MODERATOR_ROLE_NAME = "MODERATOR"

# The channel where clan applications are sent
CLAN_APPROVAL_CHANNEL_NAME = "1541901386852081815"


# ============================================================
# PENDING CLAN APPLICATIONS
# ============================================================

# Stores applications while the bot is running
pending_clans = {}


# ============================================================
# MODERATOR PERMISSION CHECK
# ============================================================

def is_moderator(member: discord.Member) -> bool:
    """
    Check whether the member has the configured Moderator role.
    """

    moderator_role = discord.utils.get(
        member.guild.roles,
        name=MODERATOR_ROLE_NAME
    )

    if moderator_role is None:
        return False

    return moderator_role in member.roles


# ============================================================
# CLAN CREATION MODAL
# ============================================================

class ClanCreateModal(ui.Modal, title="Create Your Clan"):

    clan_name = ui.TextInput(
        label="Clan Name",
        placeholder="Example: Shadow Wolves",
        required=True,
        max_length=50
    )

    category_name = ui.TextInput(
        label="Category Name",
        placeholder="Example: SHADOW WOLVES",
        required=True,
        max_length=50
    )

    text_channel_name = ui.TextInput(
        label="Clan Text Channel",
        placeholder="Example: clan-chat",
        required=True,
        max_length=50
    )

    member_role_name = ui.TextInput(
        label="Member Role",
        placeholder="Example: Shadow Wolves Member",
        required=True,
        max_length=50
    )

    leader_role_name = ui.TextInput(
        label="Leader Role",
        placeholder="Example: Shadow Wolves Leader",
        required=True,
        max_length=50
    )

    def __init__(
        self,
        setup_channel: discord.TextChannel
    ):
        super().__init__()

        self.setup_channel = setup_channel

    # ========================================================
    # FORM SUBMITTED
    # ========================================================

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ This can only be used inside a server.",
                ephemeral=True
            )
            return

        # ----------------------------------------------------
        # FIND APPROVAL CHANNEL
        # ----------------------------------------------------

        approval_channel = discord.utils.get(
            guild.text_channels,
            name=CLAN_APPROVAL_CHANNEL_NAME
        )

        if approval_channel is None:
            await interaction.response.send_message(
                f"❌ I couldn't find the approval channel "
                f"**#{CLAN_APPROVAL_CHANNEL_NAME}**.\n\n"
                f"Please create that channel first.",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        # ----------------------------------------------------
        # CLEAN INPUT
        # ----------------------------------------------------

        clan_name = self.clan_name.value.strip()

        category_name = self.category_name.value.strip()

        text_channel_name = (
            self.text_channel_name.value
            .strip()
            .lower()
            .replace(" ", "-")
        )

        member_role_name = (
            self.member_role_name.value.strip()
        )

        leader_role_name = (
            self.leader_role_name.value.strip()
        )

        # ----------------------------------------------------
        # CHECK IF USER ALREADY HAS PENDING APPLICATION
        # ----------------------------------------------------

        for application in pending_clans.values():

            if application["creator_id"] == interaction.user.id:

                await interaction.followup.send(
                    "❌ You already have a clan application "
                    "waiting for moderator approval.",
                    ephemeral=True
                )

                return

        # ----------------------------------------------------
        # CHECK DUPLICATE CATEGORY
        # ----------------------------------------------------

        existing_category = discord.utils.get(
            guild.categories,
            name=category_name
        )

        if existing_category:

            await interaction.followup.send(
                f"❌ A category named "
                f"**{category_name}** already exists.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # CHECK DUPLICATE ROLES
        # ----------------------------------------------------

        existing_member_role = discord.utils.get(
            guild.roles,
            name=member_role_name
        )

        if existing_member_role:

            await interaction.followup.send(
                f"❌ The role "
                f"**{member_role_name}** already exists.",
                ephemeral=True
            )

            return

        existing_leader_role = discord.utils.get(
            guild.roles,
            name=leader_role_name
        )

        if existing_leader_role:

            await interaction.followup.send(
                f"❌ The role "
                f"**{leader_role_name}** already exists.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # APPLICATION ID
        # ----------------------------------------------------

        application_id = (
            f"{guild.id}-"
            f"{interaction.user.id}-"
            f"{interaction.id}"
        )

        # ----------------------------------------------------
        # SAVE APPLICATION
        # ----------------------------------------------------

        pending_clans[application_id] = {

            "guild_id": guild.id,

            "creator_id": interaction.user.id,

            "creator_name": str(
                interaction.user
            ),

            "clan_name": clan_name,

            "category_name": category_name,

            "text_channel_name": text_channel_name,

            "member_role_name": member_role_name,

            "leader_role_name": leader_role_name,

            "setup_channel_id": self.setup_channel.id,

            "approval_message_id": None
        }

        # ----------------------------------------------------
        # APPLICATION EMBED
        # ----------------------------------------------------

        embed = discord.Embed(
            title="⚔️ New Clan Application",
            description=(
                "A new clan has been submitted "
                "and is waiting for moderator approval."
            ),
            color=discord.Color.orange()
        )

        embed.add_field(
            name="⚔️ Clan Name",
            value=clan_name,
            inline=True
        )

        embed.add_field(
            name="📁 Category",
            value=category_name,
            inline=True
        )

        embed.add_field(
            name="💬 Text Channel",
            value=f"#{text_channel_name}",
            inline=True
        )

        embed.add_field(
            name="👥 Member Role",
            value=member_role_name,
            inline=True
        )

        embed.add_field(
            name="👑 Leader Role",
            value=leader_role_name,
            inline=True
        )

        embed.add_field(
            name="👤 Requested By",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="📋 Status",
            value="⏳ Waiting for moderator approval",
            inline=False
        )

        embed.set_footer(
            text=f"Application ID: {application_id}"
        )

        # ----------------------------------------------------
        # SEND APPLICATION TO MODERATOR CHANNEL
        # ----------------------------------------------------

        try:

            approval_view = ClanApprovalView(
                application_id
            )

            message = await approval_channel.send(
                embed=embed,
                view=approval_view
            )

            pending_clans[
                application_id
            ]["approval_message_id"] = message.id

        except discord.Forbidden:

            pending_clans.pop(
                application_id,
                None
            )

            await interaction.followup.send(
                "❌ I don't have permission to send "
                "messages in the clan approval channel.",
                ephemeral=True
            )

            return

        except Exception as e:

            pending_clans.pop(
                application_id,
                None
            )

            print(
                f"[CLAN APPLICATION ERROR] "
                f"{type(e).__name__}: {e}"
            )

            await interaction.followup.send(
                "❌ Failed to submit your clan application.\n"
                f"Error: `{e}`",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # UPDATE TEMP CHANNEL
        # ----------------------------------------------------

        try:

            submitted_embed = discord.Embed(
                title="⏳ Clan Application Submitted",
                description=(
                    "Your clan application has been sent "
                    "to the moderators.\n\n"
                    "The clan will **not** be created until "
                    "a moderator approves it."
                ),
                color=discord.Color.orange()
            )

            submitted_embed.add_field(
                name="Clan",
                value=clan_name
            )

            submitted_embed.add_field(
                name="Status",
                value="⏳ Waiting for approval"
            )

            await self.setup_channel.send(
                embed=submitted_embed
            )

        except Exception:
            pass

        # ----------------------------------------------------
        # USER CONFIRMATION
        # ----------------------------------------------------

        await interaction.followup.send(
            "✅ Your clan application has been submitted!\n\n"
            f"Moderators will review it in "
            f"{approval_channel.mention}.\n\n"
            "The clan will be created only after approval.",
            ephemeral=True
        )


# ============================================================
# CLAN SETUP VIEW
# ============================================================

class ClanSetupView(ui.View):

    def __init__(self):
        super().__init__(
            timeout=600
        )

    @ui.button(
        label="Create Clan",
        style=discord.ButtonStyle.success,
        emoji="⚔️"
    )
    async def create_clan_button(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        if not isinstance(
            interaction.channel,
            discord.TextChannel
        ):
            await interaction.response.send_message(
                "❌ This button can only be used "
                "inside the clan setup channel.",
                ephemeral=True
            )
            return

        modal = ClanCreateModal(
            setup_channel=interaction.channel
        )

        await interaction.response.send_modal(
            modal
        )


# ============================================================
# APPROVAL VIEW
# ============================================================

class ClanApprovalView(ui.View):

    def __init__(
        self,
        application_id: str
    ):
        super().__init__(
            timeout=None
        )

        self.application_id = application_id

    # ========================================================
    # APPROVE CLAN
    # ========================================================

    @ui.button(
        label="Approve Clan",
        style=discord.ButtonStyle.success,
        emoji="✅"
    )
    async def approve_clan(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ This can only be used in a server.",
                ephemeral=True
            )
            return

        # ----------------------------------------------------
        # MODERATOR ROLE CHECK
        # ----------------------------------------------------

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(
                f"❌ You need the "
                f"**{MODERATOR_ROLE_NAME}** role "
                f"to approve clan applications.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # FIND APPLICATION
        # ----------------------------------------------------

        application = pending_clans.get(
            self.application_id
        )

        if application is None:

            await interaction.response.send_message(
                "❌ This clan application no longer exists.",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        # ----------------------------------------------------
        # CREATE CLAN
        # ----------------------------------------------------

        created_roles = []
        created_channels = []

        try:

            # =================================================
            # CREATE MEMBER ROLE
            # =================================================

            member_role = await guild.create_role(
                name=application[
                    "member_role_name"
                ],
                reason=(
                    f"Approved clan: "
                    f"{application['clan_name']}"
                )
            )

            created_roles.append(
                member_role
            )

            # =================================================
            # CREATE LEADER ROLE
            # =================================================

            leader_role = await guild.create_role(
                name=application[
                    "leader_role_name"
                ],
                reason=(
                    f"Approved clan leader role: "
                    f"{application['clan_name']}"
                )
            )

            created_roles.append(
                leader_role
            )

            # =================================================
            # CREATE MAIN CATEGORY
            # =================================================

            clan_category = await guild.create_category(
                name=application[
                    "category_name"
                ],
                reason=(
                    f"Approved clan: "
                    f"{application['clan_name']}"
                )
            )

            created_channels.append(
                clan_category
            )

            # =================================================
            # CREATE CLAN TEXT CHANNEL
            # =================================================

            clan_channel = await guild.create_text_channel(
                name=application[
                    "text_channel_name"
                ],
                category=clan_category,
                reason=(
                    f"Approved clan: "
                    f"{application['clan_name']}"
                )
            )

            created_channels.append(
                clan_channel
            )

            # =================================================
            # MAIN CLAN PERMISSIONS
            # =================================================

            await clan_channel.set_permissions(
                guild.default_role,
                view_channel=False
            )

            await clan_channel.set_permissions(
                member_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

            await clan_channel.set_permissions(
                leader_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

            # =================================================
            # LEADER CATEGORY
            # =================================================

            leader_category = await guild.create_category(
                name=(
                    f"{application['category_name']}"
                    f" - LEADERS"
                ),
                reason=(
                    f"Leader section for "
                    f"{application['clan_name']}"
                )
            )

            created_channels.append(
                leader_category
            )

            # =================================================
            # LEADER CHAT
            # =================================================

            leader_channel = await guild.create_text_channel(
                name="leader-chat",
                category=leader_category,
                reason=(
                    f"Leader chat for "
                    f"{application['clan_name']}"
                )
            )

            created_channels.append(
                leader_channel
            )

            # =================================================
            # LEADER CHAT PERMISSIONS
            # =================================================

            await leader_channel.set_permissions(
                guild.default_role,
                view_channel=False
            )

            await leader_channel.set_permissions(
                member_role,
                view_channel=False
            )

            await leader_channel.set_permissions(
                leader_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

            # =================================================
            # LEADER VOICE
            # =================================================

            leader_voice = await guild.create_voice_channel(
                name="Leader Voice",
                category=leader_category,
                reason=(
                    f"Leader voice for "
                    f"{application['clan_name']}"
                )
            )

            created_channels.append(
                leader_voice
            )

            # =================================================
            # LEADER VOICE PERMISSIONS
            # =================================================

            await leader_voice.set_permissions(
                guild.default_role,
                view_channel=False,
                connect=False
            )

            await leader_voice.set_permissions(
                member_role,
                view_channel=False,
                connect=False
            )

            await leader_voice.set_permissions(
                leader_role,
                view_channel=True,
                connect=True,
                speak=True
            )

            # =================================================
            # FIND CLAN CREATOR
            # =================================================

            creator = guild.get_member(
                application[
                    "creator_id"
                ]
            )

            # =================================================
            # GIVE LEADER ROLE
            # =================================================

            if creator:

                await creator.add_roles(
                    leader_role,
                    reason=(
                        f"Clan creator: "
                        f"{application['clan_name']}"
                    )
                )

                # Make creator explicitly able to see
                # everything even before permissions update
                await clan_channel.set_permissions(
                    creator,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

                await leader_channel.set_permissions(
                    creator,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

                await leader_voice.set_permissions(
                    creator,
                    view_channel=True,
                    connect=True,
                    speak=True
                )

            # =================================================
            # WELCOME MESSAGE
            # =================================================

            creator_mention = (
                creator.mention
                if creator
                else "Unknown"
            )

            welcome_embed = discord.Embed(
                title=(
                    f"⚔️ "
                    f"{application['clan_name']}"
                ),
                description=(
                    f"Welcome to "
                    f"**{application['clan_name']}**!\n\n"
                    f"👑 Clan Leader: "
                    f"{creator_mention}\n\n"
                    f"👥 Member Role: "
                    f"{member_role.mention}"
                ),
                color=discord.Color.green()
            )

            welcome_embed.add_field(
                name="💬 Clan Chat",
                value=clan_channel.mention,
                inline=True
            )

            welcome_embed.add_field(
                name="👑 Leader Chat",
                value=leader_channel.mention,
                inline=True
            )

            await clan_channel.send(
                embed=welcome_embed
            )

            # =================================================
            # DELETE TEMP SETUP CHANNEL
            # =================================================

            setup_channel = guild.get_channel(
                application[
                    "setup_channel_id"
                ]
            )

            if setup_channel:

                try:

                    await setup_channel.delete(
                        reason="Clan approved"
                    )

                except discord.Forbidden:
                    print(
                        "⚠️ Could not delete "
                        "temporary clan setup channel."
                    )

            # =================================================
            # UPDATE APPROVAL MESSAGE
            # =================================================

            approved_embed = discord.Embed(
                title="✅ Clan Approved",
                description=(
                    f"**{application['clan_name']}** "
                    "has been approved and created."
                ),
                color=discord.Color.green()
            )

            approved_embed.add_field(
                name="👑 Approved By",
                value=interaction.user.mention,
                inline=True
            )

            approved_embed.add_field(
                name="👤 Clan Leader",
                value=(
                    creator.mention
                    if creator
                    else "Unknown"
                ),
                inline=True
            )

            approved_embed.add_field(
                name="💬 Clan Channel",
                value=clan_channel.mention,
                inline=False
            )

            approved_embed.add_field(
                name="👑 Leader Section",
                value=leader_channel.mention,
                inline=False
            )

            approved_embed.set_footer(
                text="Clan application completed"
            )

            # Disable buttons
            for child in self.children:
                child.disabled = True

            await interaction.edit_original_response(
                embed=approved_embed,
                view=self
            )

            # ------------------------------------------------
            # NOTIFY CREATOR
            # ------------------------------------------------

            if creator:

                try:

                    await creator.send(
                        f"🎉 Your clan "
                        f"**{application['clan_name']}** "
                        f"has been **approved**!\n\n"
                        f"Your clan channel is "
                        f"{clan_channel.mention}."
                    )

                except discord.Forbidden:
                    pass

            # ------------------------------------------------
            # REMOVE APPLICATION
            # ------------------------------------------------

            pending_clans.pop(
                self.application_id,
                None
            )

        # ====================================================
        # PERMISSION ERROR
        # ====================================================

        except discord.Forbidden:

            # Try to clean up anything already created
            for channel in reversed(
                created_channels
            ):

                try:
                    await channel.delete(
                        reason="Clan creation failed"
                    )
                except Exception:
                    pass

            for role in created_roles:

                try:
                    await role.delete(
                        reason="Clan creation failed"
                    )
                except Exception:
                    pass

            await interaction.followup.send(
                "❌ I don't have enough permissions "
                "to create the clan.\n\n"
                "Make sure my bot role has:\n"
                "• Manage Roles\n"
                "• Manage Channels\n"
                "• View Channels\n"
                "• Send Messages",
                ephemeral=True
            )

        # ====================================================
        # OTHER ERROR
        # ====================================================

        except Exception as e:

            print(
                f"[CLAN APPROVAL ERROR] "
                f"{type(e).__name__}: {e}"
            )

            await interaction.followup.send(
                "❌ Something went wrong while "
                "creating the clan.\n\n"
                f"Error: `{e}`",
                ephemeral=True
            )

    # ========================================================
    # REJECT CLAN
    # ========================================================

    @ui.button(
        label="Reject Clan",
        style=discord.ButtonStyle.danger,
        emoji="❌"
    )
    async def reject_clan(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
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
                f"**{MODERATOR_ROLE_NAME}** role "
                f"to reject clan applications.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # FIND APPLICATION
        # ----------------------------------------------------

        application = pending_clans.get(
            self.application_id
        )

        if application is None:

            await interaction.response.send_message(
                "❌ This clan application no longer exists.",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        # ----------------------------------------------------
        # DELETE TEMP CHANNEL
        # ----------------------------------------------------

        setup_channel = guild.get_channel(
            application[
                "setup_channel_id"
            ]
        )

        if setup_channel:

            try:

                await setup_channel.delete(
                    reason="Clan application rejected"
                )

            except discord.Forbidden:
                pass

        # ----------------------------------------------------
        # UPDATE MODERATOR MESSAGE
        # ----------------------------------------------------

        rejected_embed = discord.Embed(
            title="❌ Clan Application Rejected",
            description=(
                f"**{application['clan_name']}** "
                "was rejected."
            ),
            color=discord.Color.red()
        )

        rejected_embed.add_field(
            name="Rejected By",
            value=interaction.user.mention,
            inline=True
        )

        rejected_embed.add_field(
            name="Applicant",
            value=f"<@{application['creator_id']}>",
            inline=True
        )

        rejected_embed.set_footer(
            text="No clan structure was created."
        )

        # Disable buttons
        for child in self.children:
            child.disabled = True

        await interaction.edit_original_response(
            embed=rejected_embed,
            view=self
        )

        # ----------------------------------------------------
        # NOTIFY USER
        # ----------------------------------------------------

        creator = guild.get_member(
            application[
                "creator_id"
            ]
        )

        if creator:

            try:

                await creator.send(
                    f"❌ Your clan application "
                    f"**{application['clan_name']}** "
                    f"was rejected by the moderators."
                )

            except discord.Forbidden:
                pass

        # ----------------------------------------------------
        # REMOVE APPLICATION
        # ----------------------------------------------------

        pending_clans.pop(
            self.application_id,
            None
        )


# ============================================================
# CLAN MANAGER COG
# ============================================================

class ClanManager(commands.Cog):

    def __init__(
        self,
        bot: commands.Bot
    ):
        self.bot = bot

    # ========================================================
    # /CREATECLAN
    # ========================================================

    @app_commands.command(
        name="createclan",
        description=(
            "Submit a new clan for moderator approval"
        )
    )
    async def createclan(
        self,
        interaction: discord.Interaction
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
        # CHECK MODERATOR ROLE EXISTS
        # ----------------------------------------------------

        moderator_role = discord.utils.get(
            guild.roles,
            name=MODERATOR_ROLE_NAME
        )

        if moderator_role is None:

            await interaction.response.send_message(
                f"❌ The moderator role "
                f"**{MODERATOR_ROLE_NAME}** "
                f"does not exist.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # FIND APPROVAL CHANNEL
        # ----------------------------------------------------

        approval_channel = discord.utils.get(
            guild.text_channels,
            name=CLAN_APPROVAL_CHANNEL_NAME
        )

        if approval_channel is None:

            await interaction.response.send_message(
                f"❌ The clan approval channel "
                f"**#{CLAN_APPROVAL_CHANNEL_NAME}** "
                f"does not exist.\n\n"
                f"Please create it first.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # CHECK EXISTING USER APPLICATION
        # ----------------------------------------------------

        for application in pending_clans.values():

            if application[
                "creator_id"
            ] == interaction.user.id:

                await interaction.response.send_message(
                    "❌ You already have a clan application "
                    "waiting for approval.",
                    ephemeral=True
                )

                return

        # ----------------------------------------------------
        # FIND / CREATE SETUP CATEGORY
        # ----------------------------------------------------

        setup_category = discord.utils.get(
            guild.categories,
            name="CLAN SETUP"
        )

        try:

            if setup_category is None:

                setup_category = (
                    await guild.create_category(
                        name="CLAN SETUP",
                        reason="Clan creation system"
                    )
                )

            # ------------------------------------------------
            # PRIVATE CHANNEL PERMISSIONS
            # ------------------------------------------------

            overwrites = {

                guild.default_role:
                    discord.PermissionOverwrite(
                        view_channel=False
                    ),

                interaction.user:
                    discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True
                    )
            }

            # ------------------------------------------------
            # CREATE TEMP CHANNEL
            # ------------------------------------------------

            username = (
                interaction.user.name
                .lower()
                .replace(" ", "-")
            )

            temp_channel = (
                await guild.create_text_channel(
                    name=f"clan-setup-{username}",
                    category=setup_category,
                    overwrites=overwrites,
                    reason="Temporary clan creation channel"
                )
            )

            # ------------------------------------------------
            # SETUP EMBED
            # ------------------------------------------------

            embed = discord.Embed(
                title="⚔️ Clan Creation",
                description=(
                    "Welcome to the clan creation system!\n\n"
                    "Click **Create Clan** below to open "
                    "the clan creation form."
                ),
                color=discord.Color.blue()
            )

            embed.add_field(
                name="📋 Clan Information",
                value=(
                    "• Clan name\n"
                    "• Category name\n"
                    "• Text channel\n"
                    "• Member role\n"
                    "• Leader role"
                ),
                inline=False
            )

            embed.add_field(
                name="⚠️ Moderator Approval",
                value=(
                    "Your clan will **not** be created "
                    "immediately.\n\n"
                    "After submitting the form, the application "
                    "will be sent to the moderators."
                ),
                inline=False
            )

            embed.add_field(
                name="👑 Leader Section",
                value=(
                    "After approval, a private leader category "
                    "with leader chat and voice will be created."
                ),
                inline=False
            )

            embed.set_footer(
                text=(
                    "This temporary channel will be deleted "
                    "after approval or rejection."
                )
            )

            # ------------------------------------------------
            # SEND SETUP MESSAGE
            # ------------------------------------------------

            await temp_channel.send(
                content=interaction.user.mention,
                embed=embed,
                view=ClanSetupView()
            )

            # ------------------------------------------------
            # RESPONSE
            # ------------------------------------------------

            await interaction.response.send_message(
                "✅ Your private clan setup channel "
                f"has been created: {temp_channel.mention}",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I don't have permission to create "
                "the clan setup channel.\n\n"
                "Give the bot **Manage Channels** permission.",
                ephemeral=True
            )

        except Exception as e:

            print(
                f"[CREATECLAN ERROR] "
                f"{type(e).__name__}: {e}"
            )

            await interaction.response.send_message(
                "❌ Failed to create the clan setup channel.\n"
                f"Error: `{e}`",
                ephemeral=True
            )


# ============================================================
# COG SETUP
# ============================================================

async def setup(
    bot: commands.Bot
):
    await bot.add_cog(
        ClanManager(bot)
    )

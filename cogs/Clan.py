import discord
from discord.ext import commands
from discord import app_commands, ui

import json
import os
import asyncio


# ============================================================
# CONFIGURATION
# ============================================================

MODERATOR_ROLE_NAME = "MODERATOR"

DATA_FILE = "clan_data.json"

CREATE_PANEL_CUSTOM_ID = "clan_create_panel"

LEADER_REFRESH_PREFIX = "clan_refresh:"
LEADER_MANAGE_PREFIX = "clan_manage:"

ROLE_MEMBER = "member"
ROLE_MODERATOR = "moderator"


# ============================================================
# DATA STORAGE
# ============================================================

data_lock = asyncio.Lock()


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

            data = json.load(f)

        if not isinstance(data, dict):
            return {"guilds": {}}

        data.setdefault(
            "guilds",
            {}
        )

        return data

    except Exception as e:

        print(
            f"❌ Failed to load clan_data.json: {e}"
        )

        return {
            "guilds": {}
        }


clan_data = load_data()


async def save_data():

    async with data_lock:

        try:

            temp_file = DATA_FILE + ".tmp"

            with open(
                temp_file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    clan_data,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

            os.replace(
                temp_file,
                DATA_FILE
            )

        except Exception as e:

            print(
                f"❌ Failed to save clan data: {e}"
            )


def get_guild_data(
    guild_id: int
):

    guild_id = str(guild_id)

    if "guilds" not in clan_data:
        clan_data["guilds"] = {}

    if guild_id not in clan_data["guilds"]:

        clan_data["guilds"][guild_id] = {
            "log_channel_id": None,
            "approval_channel_id": None,
            "create_panel_message_id": None,
            "pending": {},
            "clans": {}
        }

    guild_info = clan_data["guilds"][guild_id]

    guild_info.setdefault(
        "log_channel_id",
        None
    )

    guild_info.setdefault(
        "approval_channel_id",
        None
    )

    guild_info.setdefault(
        "create_panel_message_id",
        None
    )

    guild_info.setdefault(
        "pending",
        {}
    )

    guild_info.setdefault(
        "clans",
        {}
    )

    return guild_info


# ============================================================
# MODERATOR CHECK
# ============================================================

def is_moderator(
    member: discord.Member
) -> bool:

    if member.guild_permissions.administrator:
        return True

    role = discord.utils.get(
        member.guild.roles,
        name=MODERATOR_ROLE_NAME
    )

    if role is None:
        return False

    return role in member.roles


# ============================================================
# LOGGING
# ============================================================

async def clan_log(
    guild: discord.Guild,
    title: str,
    description: str,
    color=discord.Color.blue()
):

    guild_info = get_guild_data(
        guild.id
    )

    channel_id = guild_info.get(
        "log_channel_id"
    )

    if not channel_id:
        return

    channel = guild.get_channel(
        channel_id
    )

    if channel is None:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=discord.utils.utcnow()
    )

    try:

        await channel.send(
            embed=embed
        )

    except Exception as e:

        print(
            f"❌ Clan log error: {e}"
        )


# ============================================================
# FIND CLAN
# ============================================================

def find_clan_for_member(
    guild: discord.Guild,
    member: discord.Member
):

    guild_info = get_guild_data(
        guild.id
    )

    for clan_id, clan in guild_info[
        "clans"
    ].items():

        if clan.get(
            "owner_id"
        ) == member.id:

            return clan_id, clan

        if member.id in clan.get(
            "leaders",
            []
        ):

            return clan_id, clan

        for role_key in (
            "member_role_id",
            "leader_role_id",
            "moderator_role_id"
        ):

            role = guild.get_role(
                clan.get(role_key)
            )

            if role and role in member.roles:

                return clan_id, clan

    return None, None


# ============================================================
# CLAN MEMBER CHECK
# ============================================================

def is_clan_member(
    member: discord.Member,
    clan: dict
):

    if member.id == clan.get(
        "owner_id"
    ):

        return True

    if member.id in clan.get(
        "leaders",
        []
    ):

        return True

    for role_key in (
        "member_role_id",
        "leader_role_id",
        "moderator_role_id"
    ):

        role = member.guild.get_role(
            clan.get(role_key)
        )

        if role and role in member.roles:

            return True

    return False


# ============================================================
# CLAN MANAGEMENT CHECK
# ============================================================

def can_manage_clan(
    member: discord.Member,
    clan: dict
):

    if member.id == clan.get(
        "owner_id"
    ):

        return True

    if member.id in clan.get(
        "leaders",
        []
    ):

        return True

    leader_role = member.guild.get_role(
        clan.get(
            "leader_role_id"
        )
    )

    if leader_role and leader_role in member.roles:

        return True

    return False


# ============================================================
# GET CLAN MEMBERS
# ============================================================

def get_clan_members(
    guild: discord.Guild,
    clan: dict
):

    members = []

    owner_id = clan.get(
        "owner_id"
    )

    member_role = guild.get_role(
        clan.get(
            "member_role_id"
        )
    )

    leader_role = guild.get_role(
        clan.get(
            "leader_role_id"
        )
    )

    moderator_role = guild.get_role(
        clan.get(
            "moderator_role_id"
        )
    )

    for member in guild.members:

        if member.id == owner_id:

            members.append(
                member
            )

            continue

        if member_role and member_role in member.roles:

            members.append(
                member
            )

            continue

        if leader_role and leader_role in member.roles:

            members.append(
                member
            )

            continue

        if moderator_role and moderator_role in member.roles:

            members.append(
                member
            )

    unique = {}

    for member in members:

        unique[
            member.id
        ] = member

    return list(
        unique.values()
    )


# ============================================================
# ROLE CREATION
# ============================================================

async def get_or_create_role(
    guild: discord.Guild,
    name: str,
    reason: str
):

    role = discord.utils.get(
        guild.roles,
        name=name
    )

    if role:

        return role

    return await guild.create_role(
        name=name,
        reason=reason
    )


# ============================================================
# CREATE CLAN MODAL
# ============================================================

class ClanCreateModal(
    ui.Modal,
    title="Create Your Clan"
):

    clan_name = ui.TextInput(
        label="Clan Name",
        placeholder="Shadow Wolves",
        required=True,
        max_length=50
    )

    category_name = ui.TextInput(
        label="Clan Category",
        placeholder="SHADOW WOLVES",
        required=True,
        max_length=50
    )

    member_role_name = ui.TextInput(
        label="Clan Member Role",
        placeholder="Shadow Wolves Member",
        required=True,
        max_length=50
    )

    leader_role_name = ui.TextInput(
        label="Clan Leader Role",
        placeholder="Shadow Wolves Leader",
        required=True,
        max_length=50
    )

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

        guild_info = get_guild_data(
            guild.id
        )

        # ----------------------------------------------------
        # CHECK IF USER ALREADY OWNS A CLAN
        # ----------------------------------------------------

        for clan in guild_info[
            "clans"
        ].values():

            if clan.get(
                "owner_id"
            ) == interaction.user.id:

                await interaction.response.send_message(
                    "❌ You already own a clan.",
                    ephemeral=True
                )

                return

        # ----------------------------------------------------
        # CHECK PENDING APPLICATION
        # ----------------------------------------------------

        for application in guild_info[
            "pending"
        ].values():

            if application.get(
                "creator_id"
            ) == interaction.user.id:

                await interaction.response.send_message(
                    "❌ You already have a pending clan application.",
                    ephemeral=True
                )

                return

        clan_name = self.clan_name.value.strip()

        category_name = self.category_name.value.strip()

        member_role_name = self.member_role_name.value.strip()

        leader_role_name = self.leader_role_name.value.strip()

        # ----------------------------------------------------
        # DUPLICATE CLAN NAME
        # ----------------------------------------------------

        for clan in guild_info[
            "clans"
        ].values():

            if clan.get(
                "clan_name",
                ""
            ).lower() == clan_name.lower():

                await interaction.response.send_message(
                    "❌ A clan with this name already exists.",
                    ephemeral=True
                )

                return

        # ----------------------------------------------------
        # GET ADMIN CONFIGURED CHANNEL
        # ----------------------------------------------------

        approval_channel_id = guild_info.get(
            "approval_channel_id"
        )

        if not approval_channel_id:

            await interaction.response.send_message(
                "❌ The clan application channel has not been configured by an admin.",
                ephemeral=True
            )

            return

        approval_channel = guild.get_channel(
            approval_channel_id
        )

        if approval_channel is None:

            await interaction.response.send_message(
                "❌ The configured clan application channel no longer exists.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        # ----------------------------------------------------
        # APPLICATION ID
        # ----------------------------------------------------

        application_id = str(
            interaction.id
        )

        guild_info[
            "pending"
        ][
            application_id
        ] = {

            "application_id":
                application_id,

            "creator_id":
                interaction.user.id,

            "clan_name":
                clan_name,

            "category_name":
                category_name,

            "member_role_name":
                member_role_name,

            "leader_role_name":
                leader_role_name,

            "approval_message_id":
                None
        }

        await save_data()

        # ----------------------------------------------------
        # APPLICATION EMBED
        # ----------------------------------------------------

        embed = discord.Embed(
            title="⚔️ New Clan Application",
            description=(
                "A new clan application is waiting "
                "for moderator approval."
            ),
            color=discord.Color.orange()
        )

        embed.add_field(
            name="⚔️ Clan",
            value=clan_name,
            inline=True
        )

        embed.add_field(
            name="📁 Category",
            value=category_name,
            inline=True
        )

        embed.add_field(
            name="👤 Member Role",
            value=member_role_name,
            inline=True
        )

        embed.add_field(
            name="👑 Leader Role",
            value=leader_role_name,
            inline=True
        )

        embed.add_field(
            name="🛡️ Clan Moderator",
            value=f"{clan_name} Moderator",
            inline=True
        )

        embed.add_field(
            name="👤 Applicant",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="📋 Status",
            value="⏳ Waiting for moderator approval",
            inline=False
        )

        view = ClanApprovalView(
            application_id
        )

        try:

            message = await approval_channel.send(
                embed=embed,
                view=view
            )

            guild_info[
                "pending"
            ][
                application_id
            ][
                "approval_message_id"
            ] = message.id

            await save_data()

        except Exception as e:

            guild_info[
                "pending"
            ].pop(
                application_id,
                None
            )

            await save_data()

            await interaction.followup.send(
                f"❌ Failed to submit application.\n`{e}`",
                ephemeral=True
            )

            return

        await interaction.followup.send(
            "✅ Your clan application has been submitted for moderator approval.",
            ephemeral=True
        )


# ============================================================
# CREATE CLAN PANEL
# ============================================================

class ClanCreatePanelView(
    ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        button = discord.ui.Button(
            label="Create Clan",
            style=discord.ButtonStyle.success,
            emoji="⚔️",
            custom_id=CREATE_PANEL_CUSTOM_ID
        )

        button.callback = self.create_clan

        self.add_item(
            button
        )

    async def create_clan(
        self,
        interaction: discord.Interaction
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ This can only be used in a server.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            ClanCreateModal()
        )


# ============================================================
# APPROVAL VIEW
# ============================================================

class ClanApprovalView(
    ui.View
):

    def __init__(
        self,
        application_id: str
    ):

        super().__init__(
            timeout=None
        )

        self.application_id = application_id

        approve_button = discord.ui.Button(
            label="Approve Clan",
            style=discord.ButtonStyle.success,
            emoji="✅",
            custom_id=f"clan_approve:{application_id}"
        )

        reject_button = discord.ui.Button(
            label="Reject Clan",
            style=discord.ButtonStyle.danger,
            emoji="❌",
            custom_id=f"clan_reject:{application_id}"
        )

        approve_button.callback = self.approve

        reject_button.callback = self.reject

        self.add_item(
            approve_button
        )

        self.add_item(
            reject_button
        )

    async def approve(
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
                "❌ You need the **MODERATOR** role.",
                ephemeral=True
            )

            return

        guild_info = get_guild_data(
            guild.id
        )

        application = guild_info[
            "pending"
        ].get(
            self.application_id
        )

        if application is None:

            await interaction.response.send_message(
                "❌ This application no longer exists.",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        created_objects = []

        try:

            # ------------------------------------------------
            # CREATE ROLES
            # ------------------------------------------------

            member_role = await get_or_create_role(
                guild,
                application[
                    "member_role_name"
                ],
                "Clan member role"
            )

            leader_role = await get_or_create_role(
                guild,
                application[
                    "leader_role_name"
                ],
                "Clan leader role"
            )

            moderator_role = await get_or_create_role(
                guild,
                f"{application['clan_name']} Moderator",
                "Clan moderator role"
            )

            # ------------------------------------------------
            # MAIN CATEGORY
            # ------------------------------------------------

            category = await guild.create_category(
                name=application[
                    "category_name"
                ],
                reason="Approved clan"
            )

            created_objects.append(
                category
            )

            await category.set_permissions(
                guild.default_role,
                view_channel=False
            )

            # ------------------------------------------------
            # CLAN CHAT
            # ------------------------------------------------

            member_text = await guild.create_text_channel(
                name="clan-chat",
                category=category,
                reason="Clan member chat"
            )

            created_objects.append(
                member_text
            )

            await member_text.set_permissions(
                guild.default_role,
                view_channel=False
            )

            for role in (
                member_role,
                leader_role,
                moderator_role
            ):

                await member_text.set_permissions(
                    role,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

            # ------------------------------------------------
            # GENERAL VOICE
            # ------------------------------------------------

            general_voice = await guild.create_voice_channel(
                name="General Voice",
                category=category,
                reason="Clan general voice"
            )

            created_objects.append(
                general_voice
            )

            await general_voice.set_permissions(
                guild.default_role,
                view_channel=False,
                connect=False
            )

            for role in (
                member_role,
                leader_role,
                moderator_role
            ):

                await general_voice.set_permissions(
                    role,
                    view_channel=True,
                    connect=True,
                    speak=True
                )

            # ------------------------------------------------
            # LEADER CATEGORY
            # ------------------------------------------------

            leader_category = await guild.create_category(
                name=(
                    f"{application['category_name']} • LEADERS"
                ),
                reason="Clan leader management"
            )

            created_objects.append(
                leader_category
            )

            await leader_category.set_permissions(
                guild.default_role,
                view_channel=False
            )

            await leader_category.set_permissions(
                leader_role,
                view_channel=True
            )

            await leader_category.set_permissions(
                moderator_role,
                view_channel=True
            )

            # ------------------------------------------------
            # LEADER CHANNEL
            # ------------------------------------------------

            leader_text = await guild.create_text_channel(
                name="clan-leader",
                category=leader_category,
                reason="Clan leader management"
            )

            created_objects.append(
                leader_text
            )

            await leader_text.set_permissions(
                guild.default_role,
                view_channel=False
            )

            await leader_text.set_permissions(
                leader_role,
                view_channel=True,
                send_messages=False,
                read_message_history=True
            )

            await leader_text.set_permissions(
                moderator_role,
                view_channel=True,
                send_messages=False,
                read_message_history=True
            )

            # ------------------------------------------------
            # ADD OWNER ROLES
            # ------------------------------------------------

            creator = guild.get_member(
                application[
                    "creator_id"
                ]
            )

            if creator:

                await creator.add_roles(
                    leader_role,
                    reason="Clan creator"
                )

                await creator.add_roles(
                    member_role,
                    reason="Clan creator"
                )

            # ------------------------------------------------
            # CLAN ID
            # ------------------------------------------------

            clan_id = str(
                category.id
            )

            # ------------------------------------------------
            # SAVE CLAN
            # ------------------------------------------------

            guild_info[
                "clans"
            ][
                clan_id
            ] = {

                "clan_id":
                    clan_id,

                "clan_name":
                    application[
                        "clan_name"
                    ],

                "owner_id":
                    application[
                        "creator_id"
                    ],

                "leaders": [
                    application[
                        "creator_id"
                    ]
                ],

                "category_id":
                    category.id,

                "leader_category_id":
                    leader_category.id,

                "member_role_id":
                    member_role.id,

                "leader_role_id":
                    leader_role.id,

                "moderator_role_id":
                    moderator_role.id,

                "member_text_id":
                    member_text.id,

                "general_voice_id":
                    general_voice.id,

                "leader_text_id":
                    leader_text.id,

                "leader_voice_id":
                    None,

                "banned_members": [],

                "created_at":
                    discord.utils.utcnow().isoformat()
            }

            guild_info[
                "pending"
            ].pop(
                self.application_id,
                None
            )

            await save_data()

            # ------------------------------------------------
            # LEADER PANEL
            # ------------------------------------------------

            clan = clan_data_for_id(
                guild,
                clan_id
            )

            if clan:

                await update_leader_panel(
                    guild,
                    clan_id,
                    clan
                )

            # ------------------------------------------------
            # WELCOME
            # ------------------------------------------------

            await member_text.send(
                embed=discord.Embed(
                    title=(
                        f"⚔️ {application['clan_name']}"
                    ),
                    description=(
                        "Welcome to your clan!\n\n"
                        f"👑 Leader: "
                        f"{creator.mention if creator else 'Unknown'}\n\n"
                        "Use this channel for clan communication."
                    ),
                    color=discord.Color.green()
                )
            )

            # ------------------------------------------------
            # APPROVAL RESULT
            # ------------------------------------------------

            approved_embed = discord.Embed(
                title="✅ Clan Approved",
                description=(
                    f"**{application['clan_name']}** "
                    "has been created successfully."
                ),
                color=discord.Color.green()
            )

            approved_embed.add_field(
                name="👑 Owner",
                value=(
                    creator.mention
                    if creator
                    else "Unknown"
                ),
                inline=True
            )

            approved_embed.add_field(
                name="👥 Member Role",
                value=member_role.mention,
                inline=True
            )

            approved_embed.add_field(
                name="🛡️ Moderator Role",
                value=moderator_role.mention,
                inline=True
            )

            approved_embed.add_field(
                name="💬 Clan Chat",
                value=member_text.mention,
                inline=True
            )

            approved_embed.add_field(
                name="🔊 General Voice",
                value=general_voice.mention,
                inline=True
            )

            approved_embed.add_field(
                name="📋 Leader Panel",
                value=leader_text.mention,
                inline=True
            )

            for child in self.children:

                child.disabled = True

            await interaction.edit_original_response(
                embed=approved_embed,
                view=self
            )

            await clan_log(
                guild,
                "⚔️ Clan Created",
                (
                    f"**Clan:** {application['clan_name']}\n"
                    f"**Owner:** <@{application['creator_id']}>\n"
                    f"**Approved by:** {interaction.user.mention}"
                ),
                discord.Color.green()
            )

            # ------------------------------------------------
            # DM OWNER
            # ------------------------------------------------

            if creator:

                try:

                    await creator.send(
                        (
                            f"🎉 Your clan "
                            f"**{application['clan_name']}** "
                            "has been approved!"
                        )
                    )

                except Exception:
                    pass

        except Exception as e:

            print(
                f"❌ Clan creation error: {type(e).__name__}: {e}"
            )

            # Do not delete existing roles accidentally.
            # Delete only channels/categories created during
            # this failed attempt.

            for obj in reversed(
                created_objects
            ):

                try:

                    await obj.delete(
                        reason="Cleanup failed clan creation"
                    )

                except Exception:
                    pass

            await interaction.followup.send(
                f"❌ Clan creation failed.\n`{e}`",
                ephemeral=True
            )

    async def reject(
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
                "❌ You need the **MODERATOR** role.",
                ephemeral=True
            )

            return

        guild_info = get_guild_data(
            guild.id
        )

        application = guild_info[
            "pending"
        ].get(
            self.application_id
        )

        if application is None:

            await interaction.response.send_message(
                "❌ This application no longer exists.",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        guild_info[
            "pending"
        ].pop(
            self.application_id,
            None
        )

        await save_data()

        embed = discord.Embed(
            title="❌ Clan Rejected",
            description=(
                f"**{application['clan_name']}** "
                "was rejected."
            ),
            color=discord.Color.red()
        )

        embed.add_field(
            name="Rejected By",
            value=interaction.user.mention
        )

        for child in self.children:

            child.disabled = True

        await interaction.edit_original_response(
            embed=embed,
            view=self
        )

        await clan_log(
            guild,
            "❌ Clan Application Rejected",
            (
                f"**Clan:** {application['clan_name']}\n"
                f"**Applicant:** <@{application['creator_id']}>\n"
                f"**Rejected by:** {interaction.user.mention}"
            ),
            discord.Color.red()
        )


# ============================================================
# GET CLAN
# ============================================================

def clan_data_for_id(
    guild: discord.Guild,
    clan_id: str
):

    guild_info = get_guild_data(
        guild.id
    )

    return guild_info[
        "clans"
    ].get(
        clan_id
    )


# ============================================================
# LEADER EMBED
# ============================================================

def build_leader_embed(
    guild: discord.Guild,
    clan: dict
):

    members = get_clan_members(
        guild,
        clan
    )

    owner = guild.get_member(
        clan.get(
            "owner_id"
        )
    )

    embed = discord.Embed(
        title=(
            f"🏰 {clan.get('clan_name', 'Clan')}"
        ),
        description=(
            "Clan management panel.\n\n"
            "🔄 **Refresh Members** updates the list.\n"
            "👤 **Manage Member** allows role assignment."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👑 Owner",
        value=(
            owner.mention
            if owner
            else f"<@{clan.get('owner_id')}>"
        ),
        inline=True
    )

    embed.add_field(
        name="👥 Total Members",
        value=str(
            len(members)
        ),
        inline=True
    )

    embed.add_field(
        name="📊 Status",
        value="🟢 Active",
        inline=True
    )

    members.sort(
        key=lambda m: (
            0
            if m.id == clan.get("owner_id")
            else 1,
            m.display_name.lower()
        )
    )

    lines = []

    for member in members:

        if member.id == clan.get(
            "owner_id"
        ):

            role_text = "👑 Leader"

        else:

            moderator_role = guild.get_role(
                clan.get(
                    "moderator_role_id"
                )
            )

            leader_role = guild.get_role(
                clan.get(
                    "leader_role_id"
                )
            )

            if (
                leader_role
                and leader_role in member.roles
            ):

                role_text = "👑 Leader"

            elif (
                moderator_role
                and moderator_role in member.roles
            ):

                role_text = "🛡️ Clan Moderator"

            else:

                role_text = "👤 Clan Member"

        lines.append(
            f"{role_text} {member.mention}"
        )

    member_text = (
        "\n".join(lines)
        if lines
        else "No clan members found."
    )

    if len(member_text) > 1000:

        member_text = (
            member_text[:970]
            + "\n… and more members."
        )

    embed.add_field(
        name="👥 Members",
        value=member_text,
        inline=False
    )

    chat = guild.get_channel(
        clan.get(
            "member_text_id"
        )
    )

    voice = guild.get_channel(
        clan.get(
            "general_voice_id"
        )
    )

    embed.add_field(
        name="💬 Clan Chat",
        value=(
            chat.mention
            if chat
            else "Missing"
        ),
        inline=True
    )

    embed.add_field(
        name="🔊 Voice",
        value=(
            voice.mention
            if voice
            else "Missing"
        ),
        inline=True
    )

    return embed


# ============================================================
# LEADER PANEL
# ============================================================

class LeaderPanelView(
    ui.View
):

    def __init__(
        self,
        clan_id: str
    ):

        super().__init__(
            timeout=None
        )

        self.clan_id = str(
            clan_id
        )

        refresh_button = discord.ui.Button(
            label="Refresh Members",
            style=discord.ButtonStyle.primary,
            emoji="🔄",
            custom_id=(
                f"{LEADER_REFRESH_PREFIX}"
                f"{self.clan_id}"
            )
        )

        manage_button = discord.ui.Button(
            label="Manage Member",
            style=discord.ButtonStyle.success,
            emoji="👤",
            custom_id=(
                f"{LEADER_MANAGE_PREFIX}"
                f"{self.clan_id}"
            )
        )

        refresh_button.callback = self.refresh_members

        manage_button.callback = self.manage_member

        self.add_item(
            refresh_button
        )

        self.add_item(
            manage_button
        )

    async def get_clan(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        if guild is None:
            return None

        clan = clan_data_for_id(
            guild,
            self.clan_id
        )

        if clan is None:

            await interaction.response.send_message(
                "❌ This clan no longer exists.",
                ephemeral=True
            )

            return None

        if not can_manage_clan(
            interaction.user,
            clan
        ):

            await interaction.response.send_message(
                "❌ Only the clan leader can manage this clan.",
                ephemeral=True
            )

            return None

        return clan

    async def refresh_members(
        self,
        interaction: discord.Interaction
    ):

        clan = await self.get_clan(
            interaction
        )

        if clan is None:
            return

        await interaction.response.defer(
            ephemeral=True
        )

        embed = build_leader_embed(
            interaction.guild,
            clan
        )

        await interaction.message.edit(
            embed=embed,
            view=LeaderPanelView(
                self.clan_id
            )
        )

        await interaction.followup.send(
            "✅ Member list refreshed.",
            ephemeral=True
        )

    async def manage_member(
        self,
        interaction: discord.Interaction
    ):

        clan = await self.get_clan(
            interaction
        )

        if clan is None:
            return

        members = get_clan_members(
            interaction.guild,
            clan
        )

        members = [
            m for m in members
            if m.id != clan.get(
                "owner_id"
            )
        ]

        if not members:

            await interaction.response.send_message(
                "❌ There are no other clan members to manage.",
                ephemeral=True
            )

            return

        members = members[:25]

        await interaction.response.send_message(
            "👤 Select the member you want to manage:",
            view=MemberSelectView(
                self.clan_id,
                members
            ),
            ephemeral=True
        )


# ============================================================
# MEMBER SELECT
# ============================================================

class MemberSelect(
    ui.Select
):

    def __init__(
        self,
        clan_id: str,
        members
    ):

        self.clan_id = str(
            clan_id
        )

        options = []

        for member in members:

            options.append(
                discord.SelectOption(
                    label=member.display_name[:100],
                    value=str(member.id),
                    description=(
                        f"Manage {member.display_name}"
                    )[:100]
                )
            )

        super().__init__(
            placeholder="Select a clan member...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        clan = clan_data_for_id(
            guild,
            self.clan_id
        )

        if clan is None:

            await interaction.response.send_message(
                "❌ Clan not found.",
                ephemeral=True
            )

            return

        if not can_manage_clan(
            interaction.user,
            clan
        ):

            await interaction.response.send_message(
                "❌ You cannot manage this clan.",
                ephemeral=True
            )

            return

        member_id = int(
            self.values[0]
        )

        member = guild.get_member(
            member_id
        )

        if member is None:

            await interaction.response.send_message(
                "❌ Member not found.",
                ephemeral=True
            )

            return

        await interaction.response.edit_message(
            content=(
                f"👤 Managing **{member.display_name}**\n\n"
                "Select the role you want to give:"
            ),
            view=RoleSelectView(
                self.clan_id,
                member.id
            )
        )


class MemberSelectView(
    ui.View
):

    def __init__(
        self,
        clan_id: str,
        members
    ):

        super().__init__(
            timeout=120
        )

        self.add_item(
            MemberSelect(
                clan_id,
                members
            )
        )


# ============================================================
# ROLE SELECT
# ============================================================

class ClanRoleSelect(
    ui.Select
):

    def __init__(
        self,
        clan_id: str,
        member_id: int
    ):

        self.clan_id = str(
            clan_id
        )

        self.member_id = int(
            member_id
        )

        options = [

            discord.SelectOption(
                label="Clan Member",
                value=ROLE_MEMBER,
                emoji="👤",
                description="Give normal clan access"
            ),

            discord.SelectOption(
                label="Clan Moderator",
                value=ROLE_MODERATOR,
                emoji="🛡️",
                description="Give clan moderator access"
            )
        ]

        super().__init__(
            placeholder="Select clan role...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        clan = clan_data_for_id(
            guild,
            self.clan_id
        )

        if clan is None:

            await interaction.response.send_message(
                "❌ Clan not found.",
                ephemeral=True
            )

            return

        if not can_manage_clan(
            interaction.user,
            clan
        ):

            await interaction.response.send_message(
                "❌ You cannot manage this clan.",
                ephemeral=True
            )

            return

        member = guild.get_member(
            self.member_id
        )

        if member is None:

            await interaction.response.send_message(
                "❌ Member not found.",
                ephemeral=True
            )

            return

        if member.id == clan.get(
            "owner_id"
        ):

            await interaction.response.send_message(
                "❌ The clan owner cannot be changed here.",
                ephemeral=True
            )

            return

        member_role = guild.get_role(
            clan.get(
                "member_role_id"
            )
        )

        moderator_role = guild.get_role(
            clan.get(
                "moderator_role_id"
            )
        )

        selected = self.values[0]

        try:

            roles_to_remove = []

            if member_role:
                roles_to_remove.append(
                    member_role
                )

            if moderator_role:
                roles_to_remove.append(
                    moderator_role
                )

            if roles_to_remove:

                await member.remove_roles(
                    *roles_to_remove,
                    reason=(
                        f"Clan role update: "
                        f"{clan['clan_name']}"
                    )
                )

            if selected == ROLE_MEMBER:

                if member_role:

                    await member.add_roles(
                        member_role,
                        reason="Assigned Clan Member"
                    )

                role_text = "👤 Clan Member"

            else:

                if moderator_role:

                    await member.add_roles(
                        moderator_role,
                        reason="Assigned Clan Moderator"
                    )

                role_text = "🛡️ Clan Moderator"

            await save_data()

            await interaction.response.edit_message(
                content=(
                    f"✅ **{member.display_name}** "
                    f"is now **{role_text}**."
                ),
                view=None
            )

            await clan_log(
                guild,
                "👤 Clan Role Updated",
                (
                    f"**Clan:** {clan['clan_name']}\n"
                    f"**Member:** {member.mention}\n"
                    f"**Role:** {role_text}\n"
                    f"**By:** {interaction.user.mention}"
                )
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                (
                    "❌ I cannot manage this role.\n\n"
                    "Make sure the bot's highest role is "
                    "**above the clan roles**."
                ),
                ephemeral=True
            )

        except Exception as e:

            await interaction.response.send_message(
                f"❌ Failed to update role.\n`{e}`",
                ephemeral=True
            )


class RoleSelectView(
    ui.View
):

    def __init__(
        self,
        clan_id: str,
        member_id: int
    ):

        super().__init__(
            timeout=120
        )

        self.add_item(
            ClanRoleSelect(
                clan_id,
                member_id
            )
        )


# ============================================================
# UPDATE LEADER PANEL
# ============================================================

async def update_leader_panel(
    guild: discord.Guild,
    clan_id: str,
    clan: dict
):

    if clan is None:
        return

    channel = guild.get_channel(
        clan.get(
            "leader_text_id"
        )
    )

    if channel is None:
        return

    embed = build_leader_embed(
        guild,
        clan
    )

    view = LeaderPanelView(
        clan_id
    )

    try:

        async for message in channel.history(
            limit=50
        ):

            if (
                message.author == guild.me
                and message.embeds
                and message.embeds[0].title
                and clan.get(
                    "clan_name",
                    ""
                ) in message.embeds[0].title
            ):

                await message.edit(
                    embed=embed,
                    view=view
                )

                return

    except Exception as e:

        print(
            f"❌ Leader panel search error: {e}"
        )

    try:

        await channel.send(
            embed=embed,
            view=view
        )

    except Exception as e:

        print(
            f"❌ Leader panel create error: {e}"
        )


# ============================================================
# MODERATOR CLAN EMBED
# ============================================================

def build_moderator_clan_embed(
    guild: discord.Guild,
    clan: dict
):

    members = get_clan_members(
        guild,
        clan
    )

    owner = guild.get_member(
        clan.get(
            "owner_id"
        )
    )

    member_role = guild.get_role(
        clan.get(
            "member_role_id"
        )
    )

    leader_role = guild.get_role(
        clan.get(
            "leader_role_id"
        )
    )

    moderator_role = guild.get_role(
        clan.get(
            "moderator_role_id"
        )
    )

    category = guild.get_channel(
        clan.get(
            "category_id"
        )
    )

    leader_category = guild.get_channel(
        clan.get(
            "leader_category_id"
        )
    )

    member_text = guild.get_channel(
        clan.get(
            "member_text_id"
        )
    )

    general_voice = guild.get_channel(
        clan.get(
            "general_voice_id"
        )
    )

    leader_text = guild.get_channel(
        clan.get(
            "leader_text_id"
        )
    )

    embed = discord.Embed(
        title=(
            f"🏰 {clan.get('clan_name', 'Clan')}"
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👑 Owner",
        value=(
            owner.mention
            if owner
            else "Unknown"
        ),
        inline=True
    )

    embed.add_field(
        name="👥 Total Members",
        value=str(
            len(members)
        ),
        inline=True
    )

    roles_text = (
        f"👑 Leader: "
        f"{leader_role.mention if leader_role else 'Missing'}\n"
        f"🛡️ Moderator: "
        f"{moderator_role.mention if moderator_role else 'Missing'}\n"
        f"👤 Member: "
        f"{member_role.mention if member_role else 'Missing'}"
    )

    embed.add_field(
        name="🎭 Roles",
        value=roles_text,
        inline=False
    )

    channels_text = (
        f"📁 Category: "
        f"{category.mention if category else 'Missing'}\n"
        f"💬 Chat: "
        f"{member_text.mention if member_text else 'Missing'}\n"
        f"🔊 Voice: "
        f"{general_voice.mention if general_voice else 'Missing'}\n"
        f"👑 Leader Category: "
        f"{leader_category.mention if leader_category else 'Missing'}\n"
        f"📋 Leader Panel: "
        f"{leader_text.mention if leader_text else 'Missing'}"
    )

    embed.add_field(
        name="🔗 Channels",
        value=channels_text,
        inline=False
    )

    permissions_text = (
        "👑 **Leader**\n"
        "• Manage clan members\n"
        "• Assign Clan Moderator\n"
        "• Assign Clan Member\n"
        "• Access leader panel\n\n"
        "🛡️ **Clan Moderator**\n"
        "• Access clan channels\n"
        "• Access leader section\n\n"
        "👤 **Clan Member**\n"
        "• Access clan chat\n"
        "• Access clan voice"
    )

    embed.add_field(
        name="🔐 Permissions",
        value=permissions_text,
        inline=False
    )

    return embed


# ============================================================
# CLAN MANAGER
# ============================================================

class ClanManager(
    commands.Cog
):

    def __init__(
        self,
        bot: commands.Bot
    ):

        self.bot = bot

    # ========================================================
    # /CLANSETUP
    # ========================================================

    @app_commands.command(
        name="clansetup",
        description="Set the channel for the clan creation form"
    )
    @app_commands.describe(
        channel="Channel where the clan creation form will be posted"
    )
    async def clansetup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True
            )

            return

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "❌ Only the server administrator can use `/clansetup`.",
                ephemeral=True
            )

            return

        guild_info = get_guild_data(
            guild.id
        )

        # ----------------------------------------------------
        # SAVE CHANNEL
        # ----------------------------------------------------

        guild_info[
            "approval_channel_id"
        ] = channel.id

        # Reset old panel ID.
        # This makes the bot create the panel in the
        # newly selected channel.

        guild_info[
            "create_panel_message_id"
        ] = None

        await save_data()

        # ----------------------------------------------------
        # CREATE FORM PANEL
        # ----------------------------------------------------

        embed = discord.Embed(
            title="🏰 Create Your Clan",
            description=(
                "Want to create your own clan?\n\n"
                "Click the button below and submit "
                "your clan application.\n\n"
                "Your application will be reviewed "
                "by the moderators."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="📋 Application",
            value=(
                "• Clan name\n"
                "• Clan category\n"
                "• Clan member role\n"
                "• Clan leader role"
            ),
            inline=False
        )

        embed.set_footer(
            text="Clan Creation System"
        )

        try:

            message = await channel.send(
                embed=embed,
                view=ClanCreatePanelView()
            )

            guild_info[
                "create_panel_message_id"
            ] = message.id

            await save_data()

            await interaction.response.send_message(
                (
                    "✅ **Clan system configured!**\n\n"
                    f"📋 Form channel: {channel.mention}\n"
                    "🏰 The clan creation form has been posted."
                ),
                ephemeral=True
            )

            await clan_log(
                guild,
                "⚙️ Clan System Configured",
                (
                    f"**Application Channel:** {channel.mention}\n"
                    f"**Configured by:** {interaction.user.mention}"
                ),
                discord.Color.green()
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                (
                    "❌ I cannot send the clan form there.\n\n"
                    "Give the bot:\n"
                    "• View Channel\n"
                    "• Send Messages\n"
                    "• Embed Links"
                ),
                ephemeral=True
            )

        except Exception as e:

            await interaction.response.send_message(
                f"❌ Failed to post the clan form.\n`{e}`",
                ephemeral=True
            )

    # ========================================================
    # /CLANLOG
    # ========================================================

    @app_commands.command(
        name="clanlog",
        description="Set the clan system log channel"
    )
    @app_commands.describe(
        channel="Channel where clan logs should be sent"
    )
    async def clanlog(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Server only.",
                ephemeral=True
            )

            return

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "❌ Administrator only.",
                ephemeral=True
            )

            return

        guild_info = get_guild_data(
            interaction.guild.id
        )

        guild_info[
            "log_channel_id"
        ] = channel.id

        await save_data()

        await interaction.response.send_message(
            (
                "✅ Clan log channel saved.\n"
                f"📋 Logs: {channel.mention}"
            ),
            ephemeral=True
        )

    # ========================================================
    # /CLANS
    # ========================================================

    @app_commands.command(
        name="clans",
        description="View all server clans"
    )
    async def clans(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ Server only.",
                ephemeral=True
            )

            return

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Only moderators can use `/clans`.",
                ephemeral=True
            )

            return

        guild_info = get_guild_data(
            guild.id
        )

        clans = list(
            guild_info[
                "clans"
            ].items()
        )

        if not clans:

            await interaction.response.send_message(
                "🏰 There are currently no clans.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        embed = discord.Embed(
            title="🏰 Server Clans",
            description=(
                f"Total clans: **{len(clans)}**"
            ),
            color=discord.Color.blurple()
        )

        for index, (
            clan_id,
            clan
        ) in enumerate(
            clans
        ):

            members = get_clan_members(
                guild,
                clan
            )

            owner = guild.get_member(
                clan.get(
                    "owner_id"
                )
            )

            member_role = guild.get_role(
                clan.get(
                    "member_role_id"
                )
            )

            leader_role = guild.get_role(
                clan.get(
                    "leader_role_id"
                )
            )

            moderator_role = guild.get_role(
                clan.get(
                    "moderator_role_id"
                )
            )

            chat = guild.get_channel(
                clan.get(
                    "member_text_id"
                )
            )

            voice = guild.get_channel(
                clan.get(
                    "general_voice_id"
                )
            )

            leader_channel = guild.get_channel(
                clan.get(
                    "leader_text_id"
                )
            )

            value = (
                f"👑 **Owner:** "
                f"{owner.mention if owner else 'Unknown'}\n"
                f"👥 **Members:** {len(members)}\n\n"

                f"🎭 **Roles**\n"
                f"• Leader: "
                f"{leader_role.mention if leader_role else 'Missing'}\n"
                f"• Moderator: "
                f"{moderator_role.mention if moderator_role else 'Missing'}\n"
                f"• Member: "
                f"{member_role.mention if member_role else 'Missing'}\n\n"

                f"🔗 **Channels**\n"
                f"• Chat: "
                f"{chat.mention if chat else 'Missing'}\n"
                f"• Voice: "
                f"{voice.mention if voice else 'Missing'}\n"
                f"• Leader: "
                f"{leader_channel.mention if leader_channel else 'Missing'}"
            )

            embed.add_field(
                name=(
                    f"🏰 {clan.get('clan_name', 'Clan')}"
                ),
                value=value,
                inline=False
            )

            if index >= 24:
                break

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )

    # ========================================================
    # INITIALIZE GUILD
    # ========================================================

    async def initialize_guild(
        self,
        guild: discord.Guild
    ):

        guild_info = get_guild_data(
            guild.id
        )

        # ----------------------------------------------------
        # RESTORE CLAN APPLICATION PANEL
        # ----------------------------------------------------

        channel_id = guild_info.get(
            "approval_channel_id"
        )

        if channel_id:

            channel = guild.get_channel(
                channel_id
            )

            if channel:

                message_id = guild_info.get(
                    "create_panel_message_id"
                )

                existing_message = None

                if message_id:

                    try:

                        existing_message = (
                            await channel.fetch_message(
                                message_id
                            )
                        )

                    except Exception:

                        existing_message = None

                if existing_message:

                    try:

                        await existing_message.edit(
                            view=ClanCreatePanelView()
                        )

                        print(
                            f"✅ Restored clan form in #{channel.name}"
                        )

                    except Exception as e:

                        print(
                            f"❌ Failed to restore clan form: {e}"
                        )

                else:

                    try:

                        embed = discord.Embed(
                            title="🏰 Create Your Clan",
                            description=(
                                "Want to create your own clan?\n\n"
                                "Click the button below and submit "
                                "your clan application.\n\n"
                                "Your application will be reviewed "
                                "by the moderators."
                            ),
                            color=discord.Color.blurple()
                        )

                        embed.add_field(
                            name="📋 Application",
                            value=(
                                "• Clan name\n"
                                "• Clan category\n"
                                "• Clan member role\n"
                                "• Clan leader role"
                            ),
                            inline=False
                        )

                        message = await channel.send(
                            embed=embed,
                            view=ClanCreatePanelView()
                        )

                        guild_info[
                            "create_panel_message_id"
                        ] = message.id

                        await save_data()

                        print(
                            f"✅ Created clan form in #{channel.name}"
                        )

                    except Exception as e:

                        print(
                            f"❌ Failed to create clan form: {e}"
                        )

            else:

                print(
                    f"⚠️ Clan application channel "
                    f"{channel_id} no longer exists."
                )

        # ----------------------------------------------------
        # RESTORE APPROVAL BUTTONS
        # ----------------------------------------------------

        for application_id in guild_info[
            "pending"
        ].keys():

            try:

                self.bot.add_view(
                    ClanApprovalView(
                        application_id
                    )
                )

            except Exception as e:

                print(
                    f"❌ Failed to restore approval view: {e}"
                )

        # ----------------------------------------------------
        # RESTORE LEADER PANELS
        # ----------------------------------------------------

        for clan_id, clan in guild_info[
            "clans"
        ].items():

            try:

                self.bot.add_view(
                    LeaderPanelView(
                        clan_id
                    )
                )

                await update_leader_panel(
                    guild,
                    clan_id,
                    clan
                )

            except Exception as e:

                print(
                    f"❌ Failed to restore clan "
                    f"{clan_id}: {e}"
                )

    # ========================================================
    # READY INITIALIZATION
    # ========================================================

    async def initialize_all_guilds(
        self
    ):

        for guild in self.bot.guilds:

            try:

                await self.initialize_guild(
                    guild
                )

            except Exception as e:

                print(
                    f"❌ Clan initialization failed "
                    f"for {guild.name}: {e}"
                )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot: commands.Bot
):

    cog = ClanManager(
        bot
    )

    await bot.add_cog(
        cog
    )

    # --------------------------------------------------------
    # PERSISTENT CREATE CLAN BUTTON
    # --------------------------------------------------------

    bot.add_view(
        ClanCreatePanelView()
    )

    # --------------------------------------------------------
    # RESTORE EXISTING GUILDS
    # --------------------------------------------------------

    for guild in bot.guilds:

        try:

            await cog.initialize_guild(
                guild
            )

        except Exception as e:

            print(
                f"❌ Clan startup error "
                f"for {guild.name}: {e}"
            )

    print(
        "✅ Clan system loaded successfully."
    )
# import discord
# from discord.ext import commands
# from discord import app_commands, ui

# import json
# import os
# import asyncio
# from typing import Optional


# # ============================================================
# # CONFIGURATION
# # ============================================================

# MODERATOR_ROLE_NAME = "MODERATOR"

# DEFAULT_APPROVAL_CHANNEL_NAME = "clan-approval"

# DATA_FILE = "clan_data.json"


# # ============================================================
# # DATA STORAGE
# # ============================================================

# data_lock = asyncio.Lock()


# def load_data():

#     if not os.path.exists(DATA_FILE):

#         return {
#             "guilds": {}
#         }

#     try:

#         with open(
#             DATA_FILE,
#             "r",
#             encoding="utf-8"
#         ) as f:

#             return json.load(f)

#     except Exception as e:

#         print(
#             f"[CLAN DATA] Failed to load data: {e}"
#         )

#         return {
#             "guilds": {}
#         }


# clan_data = load_data()


# async def save_data():

#     async with data_lock:

#         try:

#             with open(
#                 DATA_FILE,
#                 "w",
#                 encoding="utf-8"
#             ) as f:

#                 json.dump(
#                     clan_data,
#                     f,
#                     indent=4
#                 )

#         except Exception as e:

#             print(
#                 f"[CLAN DATA] Failed to save: {e}"
#             )


# def get_guild_data(guild_id: int):

#     guild_id = str(guild_id)

#     if "guilds" not in clan_data:

#         clan_data["guilds"] = {}

#     if guild_id not in clan_data["guilds"]:

#         clan_data["guilds"][guild_id] = {
#             "log_channel_id": None,
#             "approval_channel_id": None,
#             "pending": {},
#             "clans": {}
#         }

#     return clan_data["guilds"][guild_id]


# # ============================================================
# # MODERATOR CHECK
# # ============================================================

# def is_moderator(
#     member: discord.Member
# ) -> bool:

#     role = discord.utils.get(
#         member.guild.roles,
#         name=MODERATOR_ROLE_NAME
#     )

#     if role is None:

#         return False

#     return role in member.roles


# # ============================================================
# # LOGGING
# # ============================================================

# async def clan_log(
#     guild: discord.Guild,
#     title: str,
#     description: str,
#     color=discord.Color.blue()
# ):

#     guild_info = get_guild_data(
#         guild.id
#     )

#     channel_id = guild_info.get(
#         "log_channel_id"
#     )

#     if not channel_id:
#         return

#     channel = guild.get_channel(
#         channel_id
#     )

#     if channel is None:
#         return

#     embed = discord.Embed(
#         title=title,
#         description=description,
#         color=color,
#         timestamp=discord.utils.utcnow()
#     )

#     embed.set_footer(
#         text="Clan System Logs"
#     )

#     try:

#         await channel.send(
#             embed=embed
#         )

#     except Exception as e:

#         print(
#             f"[CLAN LOG] {e}"
#         )


# # ============================================================
# # FIND CLAN
# # ============================================================

# def find_clan_for_member(
#     guild: discord.Guild,
#     member: discord.Member
# ):

#     guild_info = get_guild_data(
#         guild.id
#     )

#     for clan_id, clan in guild_info[
#         "clans"
#     ].items():

#         if (
#             member.id
#             == clan["owner_id"]
#         ):

#             return clan_id, clan

#         if (
#             member.id
#             in clan.get(
#                 "leaders",
#                 []
#             )
#         ):

#             return clan_id, clan

#         role = guild.get_role(
#             clan["member_role_id"]
#         )

#         leader_role = guild.get_role(
#             clan["leader_role_id"]
#         )

#         if role and role in member.roles:

#             return clan_id, clan

#         if (
#             leader_role
#             and leader_role in member.roles
#         ):

#             return clan_id, clan

#     return None, None


# def get_clan_by_category(
#     guild: discord.Guild,
#     category_id: int
# ):

#     guild_info = get_guild_data(
#         guild.id
#     )

#     for clan_id, clan in guild_info[
#         "clans"
#     ].items():

#         if (
#             clan["category_id"]
#             == category_id
#         ):

#             return clan_id, clan

#     return None, None


# # ============================================================
# # CLAN MANAGEMENT PERMISSION
# # ============================================================

# def can_manage_clan(
#     member: discord.Member,
#     clan: dict
# ) -> bool:

#     if member.id == clan["owner_id"]:

#         return True

#     if member.id in clan.get(
#         "leaders",
#         []
#     ):

#         return True

#     leader_role = member.guild.get_role(
#         clan["leader_role_id"]
#     )

#     if (
#         leader_role
#         and leader_role in member.roles
#     ):

#         return True

#     return False


# # ============================================================
# # CLAN CREATION MODAL
# # ============================================================

# class ClanCreateModal(
#     ui.Modal,
#     title="Create Your Clan"
# ):

#     clan_name = ui.TextInput(
#         label="Clan Name",
#         placeholder="Shadow Wolves",
#         required=True,
#         max_length=50
#     )

#     category_name = ui.TextInput(
#         label="Category Name",
#         placeholder="SHADOW WOLVES",
#         required=True,
#         max_length=50
#     )

#     member_role_name = ui.TextInput(
#         label="Member Role",
#         placeholder="Shadow Wolves Member",
#         required=True,
#         max_length=50
#     )

#     leader_role_name = ui.TextInput(
#         label="Leader Role",
#         placeholder="Shadow Wolves Leader",
#         required=True,
#         max_length=50
#     )

#     def __init__(
#         self,
#         setup_channel
#     ):

#         super().__init__()

#         self.setup_channel = setup_channel

#     async def on_submit(
#         self,
#         interaction: discord.Interaction
#     ):

#         guild = interaction.guild

#         if guild is None:

#             await interaction.response.send_message(
#                 "❌ This can only be used in a server.",
#                 ephemeral=True
#             )

#             return

#         guild_info = get_guild_data(
#             guild.id
#         )

#         # ----------------------------------------------------
#         # APPROVAL CHANNEL
#         # ----------------------------------------------------

#         approval_channel = None

#         approval_id = guild_info.get(
#             "approval_channel_id"
#         )

#         if approval_id:

#             approval_channel = guild.get_channel(
#                 approval_id
#             )

#         if approval_channel is None:

#             approval_channel = discord.utils.get(
#                 guild.text_channels,
#                 name=DEFAULT_APPROVAL_CHANNEL_NAME
#             )

#         if approval_channel is None:

#             await interaction.response.send_message(
#                 f"❌ I cannot find the clan approval channel.\n\n"
#                 f"Create **#{DEFAULT_APPROVAL_CHANNEL_NAME}** "
#                 f"or let the server owner configure it.",
#                 ephemeral=True
#             )

#             return

#         await interaction.response.defer(
#             ephemeral=True
#         )

#         clan_name = (
#             self.clan_name.value.strip()
#         )

#         category_name = (
#             self.category_name.value.strip()
#         )

#         member_role_name = (
#             self.member_role_name.value.strip()
#         )

#         leader_role_name = (
#             self.leader_role_name.value.strip()
#         )

#         # ----------------------------------------------------
#         # DUPLICATE CHECK
#         # ----------------------------------------------------

#         for clan in guild_info[
#             "clans"
#         ].values():

#             if (
#                 clan["clan_name"].lower()
#                 == clan_name.lower()
#             ):

#                 await interaction.followup.send(
#                     "❌ A clan with this name already exists.",
#                     ephemeral=True
#                 )

#                 return

#         # ----------------------------------------------------
#         # CREATE APPLICATION ID
#         # ----------------------------------------------------

#         application_id = str(
#             interaction.id
#         )

#         guild_info["pending"][
#             application_id
#         ] = {

#             "application_id":
#                 application_id,

#             "creator_id":
#                 interaction.user.id,

#             "clan_name":
#                 clan_name,

#             "category_name":
#                 category_name,

#             "member_role_name":
#                 member_role_name,

#             "leader_role_name":
#                 leader_role_name,

#             "setup_channel_id":
#                 self.setup_channel.id,

#             "approval_message_id":
#                 None
#         }

#         await save_data()

#         # ----------------------------------------------------
#         # APPROVAL EMBED
#         # ----------------------------------------------------

#         embed = discord.Embed(
#             title="⚔️ New Clan Application",
#             description=(
#                 "A new clan is waiting "
#                 "for moderator approval."
#             ),
#             color=discord.Color.orange()
#         )

#         embed.add_field(
#             name="⚔️ Clan",
#             value=clan_name,
#             inline=True
#         )

#         embed.add_field(
#             name="📁 Category",
#             value=category_name,
#             inline=True
#         )

#         embed.add_field(
#             name="👥 Member Role",
#             value=member_role_name,
#             inline=True
#         )

#         embed.add_field(
#             name="👑 Leader Role",
#             value=leader_role_name,
#             inline=True
#         )

#         embed.add_field(
#             name="👤 Creator",
#             value=interaction.user.mention,
#             inline=True
#         )

#         embed.add_field(
#             name="📋 Status",
#             value="⏳ Waiting for approval",
#             inline=False
#         )

#         view = ClanApprovalView(
#             application_id
#         )

#         try:

#             message = await approval_channel.send(
#                 embed=embed,
#                 view=view
#             )

#             guild_info[
#                 "pending"
#             ][
#                 application_id
#             ][
#                 "approval_message_id"
#             ] = message.id

#             await save_data()

#         except Exception as e:

#             guild_info[
#                 "pending"
#             ].pop(
#                 application_id,
#                 None
#             )

#             await save_data()

#             await interaction.followup.send(
#                 f"❌ Failed to submit application.\n"
#                 f"`{e}`",
#                 ephemeral=True
#             )

#             return

#         # ----------------------------------------------------
#         # UPDATE SETUP CHANNEL
#         # ----------------------------------------------------

#         try:

#             await self.setup_channel.send(
#                 embed=discord.Embed(
#                     title="⏳ Application Submitted",
#                     description=(
#                         "Your clan application has been "
#                         "sent to the moderators.\n\n"
#                         "The clan will only be created "
#                         "after approval."
#                     ),
#                     color=discord.Color.orange()
#                 )
#             )

#         except Exception:
#             pass

#         await interaction.followup.send(
#             "✅ Your clan application has been submitted "
#             "for moderator approval.",
#             ephemeral=True
#         )


# # ============================================================
# # SETUP VIEW
# # ============================================================

# class ClanSetupView(ui.View):

#     def __init__(self):

#         super().__init__(
#             timeout=600
#         )

#     @ui.button(
#         label="Create Clan",
#         style=discord.ButtonStyle.success,
#         emoji="⚔️"
#     )
#     async def create_button(
#         self,
#         interaction: discord.Interaction,
#         button: ui.Button
#     ):

#         if not isinstance(
#             interaction.channel,
#             discord.TextChannel
#         ):

#             return

#         await interaction.response.send_modal(
#             ClanCreateModal(
#                 interaction.channel
#             )
#         )


# # ============================================================
# # APPROVAL VIEW
# # ============================================================

# class ClanApprovalView(ui.View):

#     def __init__(
#         self,
#         application_id: str
#     ):

#         super().__init__(
#             timeout=None
#         )

#         self.application_id = (
#             application_id
#         )

#     # ========================================================
#     # APPROVE
#     # ========================================================

#     @ui.button(
#         label="Approve Clan",
#         style=discord.ButtonStyle.success,
#         emoji="✅",
#         custom_id="clan_approve"
#     )
#     async def approve(
#         self,
#         interaction: discord.Interaction,
#         button: ui.Button
#     ):

#         guild = interaction.guild

#         if guild is None:
#             return

#         if not is_moderator(
#             interaction.user
#         ):

#             await interaction.response.send_message(
#                 f"❌ You need the "
#                 f"**{MODERATOR_ROLE_NAME}** role.",
#                 ephemeral=True
#             )

#             return

#         guild_info = get_guild_data(
#             guild.id
#         )

#         application = guild_info[
#             "pending"
#         ].get(
#             self.application_id
#         )

#         if application is None:

#             await interaction.response.send_message(
#                 "❌ This application no longer exists.",
#                 ephemeral=True
#             )

#             return

#         await interaction.response.defer()

#         try:

#             # =================================================
#             # CREATE ROLES
#             # =================================================

#             member_role = await guild.create_role(
#                 name=application[
#                     "member_role_name"
#                 ],
#                 reason="Approved clan member role"
#             )

#             leader_role = await guild.create_role(
#                 name=application[
#                     "leader_role_name"
#                 ],
#                 reason="Approved clan leader role"
#             )

#             # =================================================
#             # CREATE MAIN CATEGORY
#             # =================================================

#             category = await guild.create_category(
#                 name=application[
#                     "category_name"
#                 ],
#                 reason="Approved clan"
#             )

#             # Everyone can see the CATEGORY
#             # but children control actual access.
#             await category.set_permissions(
#                 guild.default_role,
#                 view_channel=True,
#                 connect=False,
#                 send_messages=False
#             )

#             # =================================================
#             # MEMBER TEXT
#             # =================================================

#             member_text = await guild.create_text_channel(
#                 name="clan-chat",
#                 category=category,
#                 reason="Clan member chat"
#             )

#             await member_text.set_permissions(
#                 guild.default_role,
#                 view_channel=False
#             )

#             await member_text.set_permissions(
#                 member_role,
#                 view_channel=True,
#                 send_messages=True,
#                 read_message_history=True
#             )

#             await member_text.set_permissions(
#                 leader_role,
#                 view_channel=True,
#                 send_messages=True,
#                 read_message_history=True
#             )

#             # =================================================
#             # GENERAL VOICE
#             # =================================================

#             general_voice = await guild.create_voice_channel(
#                 name="General Voice",
#                 category=category,
#                 reason="Clan general voice"
#             )

#             # Everyone can see/use the general voice.
#             await general_voice.set_permissions(
#                 guild.default_role,
#                 view_channel=True,
#                 connect=True,
#                 speak=True
#             )

#             # =================================================
#             # LEADER CATEGORY
#             # =================================================

#             leader_category = await guild.create_category(
#                 name=(
#                     f"{application['category_name']}"
#                     f" • LEADERS"
#                 ),
#                 reason="Clan leadership section"
#             )

#             await leader_category.set_permissions(
#                 guild.default_role,
#                 view_channel=False
#             )

#             await leader_category.set_permissions(
#                 leader_role,
#                 view_channel=True
#             )

#             # =================================================
#             # LEADER TEXT
#             # =================================================

#             leader_text = await guild.create_text_channel(
#                 name="leader-chat",
#                 category=leader_category,
#                 reason="Clan leader chat"
#             )

#             await leader_text.set_permissions(
#                 guild.default_role,
#                 view_channel=False
#             )

#             await leader_text.set_permissions(
#                 leader_role,
#                 view_channel=True,
#                 send_messages=True,
#                 read_message_history=True
#             )

#             # =================================================
#             # LEADER VOICE
#             # =================================================

#             leader_voice = await guild.create_voice_channel(
#                 name="Leader Voice",
#                 category=leader_category,
#                 reason="Clan leader voice"
#             )

#             await leader_voice.set_permissions(
#                 guild.default_role,
#                 view_channel=False,
#                 connect=False
#             )

#             await leader_voice.set_permissions(
#                 leader_role,
#                 view_channel=True,
#                 connect=True,
#                 speak=True
#             )

#             # =================================================
#             # CREATOR
#             # =================================================

#             creator = guild.get_member(
#                 application[
#                     "creator_id"
#                 ]
#             )

#             if creator:

#                 await creator.add_roles(
#                     leader_role,
#                     reason="Clan creator"
#                 )

#             # =================================================
#             # CLAN ID
#             # =================================================

#             clan_id = str(
#                 category.id
#             )

#             # =================================================
#             # SAVE CLAN
#             # =================================================

#             guild_info[
#                 "clans"
#             ][clan_id] = {

#                 "clan_id":
#                     clan_id,

#                 "clan_name":
#                     application[
#                         "clan_name"
#                     ],

#                 "owner_id":
#                     application[
#                         "creator_id"
#                     ],

#                 "leaders": [
#                     application[
#                         "creator_id"
#                     ]
#                 ],

#                 "category_id":
#                     category.id,

#                 "leader_category_id":
#                     leader_category.id,

#                 "member_role_id":
#                     member_role.id,

#                 "leader_role_id":
#                     leader_role.id,

#                 "member_text_id":
#                     member_text.id,

#                 "general_voice_id":
#                     general_voice.id,

#                 "leader_text_id":
#                     leader_text.id,

#                 "leader_voice_id":
#                     leader_voice.id,

#                 "banned_members": [],

#                 "created_at":
#                     discord.utils.utcnow().isoformat()
#             }

#             # Remove pending application
#             guild_info[
#                 "pending"
#             ].pop(
#                 self.application_id,
#                 None
#             )

#             await save_data()

#             # =================================================
#             # WELCOME MESSAGE
#             # =================================================

#             await member_text.send(
#                 embed=discord.Embed(
#                     title=(
#                         f"⚔️ "
#                         f"{application['clan_name']}"
#                     ),
#                     description=(
#                         f"Welcome to "
#                         f"**{application['clan_name']}**!\n\n"
#                         f"👑 Leader: "
#                         f"{creator.mention if creator else 'Unknown'}\n\n"
#                         f"Use this channel for clan "
#                         f"communication."
#                     ),
#                     color=discord.Color.green()
#                 )
#             )

#             # =================================================
#             # DELETE TEMP CHANNEL
#             # =================================================

#             setup_channel = guild.get_channel(
#                 application[
#                     "setup_channel_id"
#                 ]
#             )

#             if setup_channel:

#                 try:

#                     await setup_channel.delete(
#                         reason="Clan approved"
#                     )

#                 except Exception:
#                     pass

#             # =================================================
#             # UPDATE APPLICATION
#             # =================================================

#             approved_embed = discord.Embed(
#                 title="✅ Clan Approved",
#                 description=(
#                     f"**{application['clan_name']}** "
#                     "has been created successfully."
#                 ),
#                 color=discord.Color.green()
#             )

#             approved_embed.add_field(
#                 name="👑 Owner",
#                 value=(
#                     creator.mention
#                     if creator
#                     else "Unknown"
#                 )
#             )

#             approved_embed.add_field(
#                 name="💬 Member Chat",
#                 value=member_text.mention
#             )

#             approved_embed.add_field(
#                 name="🔊 General Voice",
#                 value=general_voice.mention
#             )

#             approved_embed.add_field(
#                 name="👑 Leader Section",
#                 value=leader_category.name
#             )

#             for child in self.children:
#                 child.disabled = True

#             await interaction.edit_original_response(
#                 embed=approved_embed,
#                 view=self
#             )

#             # =================================================
#             # LOG
#             # =================================================

#             await clan_log(
#                 guild,
#                 "⚔️ Clan Created",
#                 (
#                     f"**Clan:** {application['clan_name']}\n"
#                     f"**Owner:** "
#                     f"<@{application['creator_id']}>\n"
#                     f"**Approved by:** "
#                     f"{interaction.user.mention}"
#                 ),
#                 discord.Color.green()
#             )

#             # =================================================
#             # DM OWNER
#             # =================================================

#             if creator:

#                 try:

#                     await creator.send(
#                         f"🎉 Your clan "
#                         f"**{application['clan_name']}** "
#                         "has been approved!\n\n"
#                         f"Your clan is located in "
#                         f"**{category.name}**."
#                     )

#                 except Exception:
#                     pass

#         except Exception as e:

#             print(
#                 f"[CLAN APPROVAL ERROR] "
#                 f"{type(e).__name__}: {e}"
#             )

#             await interaction.followup.send(
#                 f"❌ Clan creation failed.\n"
#                 f"`{e}`",
#                 ephemeral=True
#             )

#     # ========================================================
#     # REJECT
#     # ========================================================

#     @ui.button(
#         label="Reject Clan",
#         style=discord.ButtonStyle.danger,
#         emoji="❌",
#         custom_id="clan_reject"
#     )
#     async def reject(
#         self,
#         interaction: discord.Interaction,
#         button: ui.Button
#     ):

#         guild = interaction.guild

#         if guild is None:
#             return

#         if not is_moderator(
#             interaction.user
#         ):

#             await interaction.response.send_message(
#                 f"❌ You need the "
#                 f"**{MODERATOR_ROLE_NAME}** role.",
#                 ephemeral=True
#             )

#             return

#         guild_info = get_guild_data(
#             guild.id
#         )

#         application = guild_info[
#             "pending"
#         ].get(
#             self.application_id
#         )

#         if application is None:

#             await interaction.response.send_message(
#                 "❌ This application no longer exists.",
#                 ephemeral=True
#             )

#             return

#         await interaction.response.defer()

#         guild_info[
#             "pending"
#         ].pop(
#             self.application_id,
#             None
#         )

#         await save_data()

#         setup_channel = guild.get_channel(
#             application[
#                 "setup_channel_id"
#             ]
#         )

#         if setup_channel:

#             try:

#                 await setup_channel.delete(
#                     reason="Clan rejected"
#                 )

#             except Exception:
#                 pass

#         embed = discord.Embed(
#             title="❌ Clan Rejected",
#             description=(
#                 f"**{application['clan_name']}** "
#                 "was rejected."
#             ),
#             color=discord.Color.red()
#         )

#         embed.add_field(
#             name="Rejected By",
#             value=interaction.user.mention
#         )

#         for child in self.children:
#             child.disabled = True

#         await interaction.edit_original_response(
#             embed=embed,
#             view=self
#         )

#         await clan_log(
#             guild,
#             "❌ Clan Application Rejected",
#             (
#                 f"**Clan:** {application['clan_name']}\n"
#                 f"**Applicant:** "
#                 f"<@{application['creator_id']}>\n"
#                 f"**Rejected by:** "
#                 f"{interaction.user.mention}"
#             ),
#             discord.Color.red()
#         )


# # ============================================================
# # CLAN MANAGEMENT COG
# # ============================================================

# class ClanManager(
#     commands.Cog
# ):

#     def __init__(
#         self,
#         bot: commands.Bot
#     ):

#         self.bot = bot

#     # ========================================================
#     # /CREATECLAN
#     # ========================================================

#     @app_commands.command(
#         name="createclan",
#         description="Create a new clan application"
#     )
#     async def createclan(
#         self,
#         interaction: discord.Interaction
#     ):

#         guild = interaction.guild

#         if guild is None:
#             return

#         # Moderator role must exist
#         moderator_role = discord.utils.get(
#             guild.roles,
#             name=MODERATOR_ROLE_NAME
#         )

#         if moderator_role is None:

#             await interaction.response.send_message(
#                 f"❌ The **{MODERATOR_ROLE_NAME}** role "
#                 "does not exist.",
#                 ephemeral=True
#             )

#             return

#         guild_info = get_guild_data(
#             guild.id
#         )

#         # Only one clan/application per owner
#         for clan in guild_info[
#             "clans"
#         ].values():

#             if clan["owner_id"] == interaction.user.id:

#                 await interaction.response.send_message(
#                     "❌ You already own a clan.",
#                     ephemeral=True
#                 )

#                 return

#         for application in guild_info[
#             "pending"
#         ].values():

#             if (
#                 application["creator_id"]
#                 == interaction.user.id
#             ):

#                 await interaction.response.send_message(
#                     "❌ You already have a pending "
#                     "clan application.",
#                     ephemeral=True
#                 )

#                 return

#         # ----------------------------------------------------
#         # SETUP CATEGORY
#         # ----------------------------------------------------

#         setup_category = discord.utils.get(
#             guild.categories,
#             name="CLAN SETUP"
#         )

#         try:

#             if setup_category is None:

#                 setup_category = (
#                     await guild.create_category(
#                         name="CLAN SETUP"
#                     )
#                 )

#             overwrites = {

#                 guild.default_role:
#                     discord.PermissionOverwrite(
#                         view_channel=False
#                     ),

#                 interaction.user:
#                     discord.PermissionOverwrite(
#                         view_channel=True,
#                         send_messages=True,
#                         read_message_history=True
#                     )
#             }

#             channel_name = (
#                 f"clan-setup-"
#                 f"{interaction.user.name}"
#             ).lower()

#             setup_channel = (
#                 await guild.create_text_channel(
#                     name=channel_name,
#                     category=setup_category,
#                     overwrites=overwrites
#                 )
#             )

#             embed = discord.Embed(
#                 title="⚔️ Clan Creation",
#                 description=(
#                     "Create your clan using the button below.\n\n"
#                     "⚠️ Your clan requires moderator approval "
#                     "before it is created."
#                 ),
#                 color=discord.Color.blue()
#             )

#             embed.add_field(
#                 name="You will configure",
#                 value=(
#                     "• Clan name\n"
#                     "• Clan category\n"
#                     "• Member role\n"
#                     "• Leader role"
#                 ),
#                 inline=False
#             )

#             await setup_channel.send(
#                 content=interaction.user.mention,
#                 embed=embed,
#                 view=ClanSetupView()
#             )

#             await interaction.response.send_message(
#                 f"✅ Your private clan setup channel is "
#                 f"{setup_channel.mention}",
#                 ephemeral=True
#             )

#         except discord.Forbidden:

#             await interaction.response.send_message(
#                 "❌ I need **Manage Channels** permission.",
#                 ephemeral=True
#             )

#     # ========================================================
#     # /CLANADD
#     # ========================================================

#     @app_commands.command(
#         name="clanadd",
#         description="Add a member to your clan"
#     )
#     @app_commands.describe(
#         member="The member to add"
#     )
#     async def clanadd(
#         self,
#         interaction: discord.Interaction,
#         member: discord.Member
#     ):

#         guild = interaction.guild

#         clan_id, clan = find_clan_for_member(
#             guild,
#             interaction.user
#         )

#         if clan is None:

#             await interaction.response.send_message(
#                 "❌ You are not a clan leader.",
#                 ephemeral=True
#             )

#             return

#         if not can_manage_clan(
#             interaction.user,
#             clan
#         ):

#             await interaction.response.send_message(
#                 "❌ You cannot manage this clan.",
#                 ephemeral=True
#             )

#             return

#         if member.id in clan.get(
#             "banned_members",
#             []
#         ):

#             await interaction.response.send_message(
#                 "❌ This member is banned from your clan.",
#                 ephemeral=True
#             )

#             return

#         role = guild.get_role(
#             clan["member_role_id"]
#         )

#         if role is None:

#             await interaction.response.send_message(
#                 "❌ The clan member role no longer exists.",
#                 ephemeral=True
#             )

#             return

#         await member.add_roles(
#             role,
#             reason=(
#                 f"Added to clan "
#                 f"{clan['clan_name']} by "
#                 f"{interaction.user}"
#             )
#         )

#         await interaction.response.send_message(
#             f"✅ {member.mention} has been added "
#             f"to **{clan['clan_name']}**.",
#             ephemeral=True
#         )

#         await clan_log(
#             guild,
#             "👥 Clan Member Added",
#             (
#                 f"**Clan:** {clan['clan_name']}\n"
#                 f"**Member:** {member.mention}\n"
#                 f"**By:** {interaction.user.mention}"
#             )
#         )

#     # ========================================================
#     # /CLANREMOVE
#     # ========================================================

#     @app_commands.command(
#         name="clanremove",
#         description="Remove a member from your clan"
#     )
#     @app_commands.describe(
#         member="The member to remove"
#     )
#     async def clanremove(
#         self,
#         interaction: discord.Interaction,
#         member: discord.Member
#     ):

#         guild = interaction.guild

#         clan_id, clan = find_clan_for_member(
#             guild,
#             interaction.user
#         )

#         if clan is None or not can_manage_clan(
#             interaction.user,
#             clan
#         ):

#             await interaction.response.send_message(
#                 "❌ You cannot manage this clan.",
#                 ephemeral=True
#             )

#             return

#         role = guild.get_role(
#             clan["member_role_id"]
#         )

#         if role:

#             await member.remove_roles(
#                 role,
#                 reason=(
#                     f"Removed from clan "
#                     f"{clan['clan_name']}"
#                 )
#             )

#         leader_role = guild.get_role(
#             clan["leader_role_id"]
#         )

#         if leader_role:

#             await member.remove_roles(
#                 leader_role,
#                 reason=(
#                     f"Removed as clan leader"
#                 )
#             )

#         if member.id in clan.get(
#             "leaders",
#             []
#         ):

#             clan["leaders"].remove(
#                 member.id
#             )

#             await save_data()

#         await interaction.response.send_message(
#             f"✅ {member.mention} has been removed "
#             f"from **{clan['clan_name']}**.",
#             ephemeral=True
#         )

#         await clan_log(
#             guild,
#             "👤 Clan Member Removed",
#             (
#                 f"**Clan:** {clan['clan_name']}\n"
#                 f"**Member:** {member.mention}\n"
#                 f"**By:** {interaction.user.mention}"
#             )
#         )

#     # ========================================================
#     # /CLANANNOUNCE
#     # ========================================================

#     @app_commands.command(
#         name="clanannounce",
#         description="Send an announcement to your clan"
#     )
#     @app_commands.describe(
#         message="Announcement message"
#     )
#     async def clanannounce(
#         self,
#         interaction: discord.Interaction,
#         message: str
#     ):

#         guild = interaction.guild

#         clan_id, clan = find_clan_for_member(
#             guild,
#             interaction.user
#         )

#         if clan is None or not can_manage_clan(
#             interaction.user,
#             clan
#         ):

#             await interaction.response.send_message(
#                 "❌ You cannot manage this clan.",
#                 ephemeral=True
#             )

#             return

#         channel = guild.get_channel(
#             clan["member_text_id"]
#         )

#         if channel is None:

#             await interaction.response.send_message(
#                 "❌ Clan chat no longer exists.",
#                 ephemeral=True
#             )

#             return

#         embed = discord.Embed(
#             title="📢 Clan Announcement",
#             description=message,
#             color=discord.Color.gold()
#         )

#         embed.set_author(
#             name=interaction.user.display_name,
#             icon_url=interaction.user.display_avatar.url
#         )

#         await channel.send(
#             embed=embed
#         )

#         await interaction.response.send_message(
#             "✅ Announcement sent.",
#             ephemeral=True
#         )

#         await clan_log(
#             guild,
#             "📢 Clan Announcement",
#             (
#                 f"**Clan:** {clan['clan_name']}\n"
#                 f"**By:** {interaction.user.mention}\n"
#                 f"**Message:** {message}"
#             )
#         )

#     # ========================================================
#     # /CLANKICK
#     # ========================================================

#     @app_commands.command(
#         name="clankick",
#         description="Remove someone from your clan"
#     )
#     @app_commands.describe(
#         member="Member to kick from the clan"
#     )
#     async def clankick(
#         self,
#         interaction: discord.Interaction,
#         member: discord.Member
#     ):

#         await self.clanremove(
#             interaction,
#             member
#         )

#         await clan_log(
#             interaction.guild,
#             "👢 Clan Kick",
#             (
#                 f"**Member:** {member.mention}\n"
#                 f"**By:** {interaction.user.mention}"
#             ),
#             discord.Color.orange()
#         )

#     # ========================================================
#     # /CLANBAN
#     # ========================================================

#     @app_commands.command(
#         name="clanban",
#         description="Ban someone from your clan"
#     )
#     @app_commands.describe(
#         member="Member to ban from the clan"
#     )
#     async def clanban(
#         self,
#         interaction: discord.Interaction,
#         member: discord.Member
#     ):

#         guild = interaction.guild

#         clan_id, clan = find_clan_for_member(
#             guild,
#             interaction.user
#         )

#         if clan is None or not can_manage_clan(
#             interaction.user,
#             clan
#         ):

#             await interaction.response.send_message(
#                 "❌ You cannot manage this clan.",
#                 ephemeral=True
#             )

#             return

#         if member.id == clan["owner_id"]:

#             await interaction.response.send_message(
#                 "❌ You cannot ban the clan owner.",
#                 ephemeral=True
#             )

#             return

#         if member.id not in clan[
#             "banned_members"
#         ]:

#             clan[
#                 "banned_members"
#             ].append(
#                 member.id
#             )

#         role = guild.get_role(
#             clan["member_role_id"]
#         )

#         if role:

#             await member.remove_roles(
#                 role,
#                 reason=(
#                     f"Clan ban: "
#                     f"{clan['clan_name']}"
#                 )
#             )

#         leader_role = guild.get_role(
#             clan["leader_role_id"]
#         )

#         if leader_role:

#             await member.remove_roles(
#                 leader_role
#             )

#         if member.id in clan.get(
#             "leaders",
#             []
#         ):

#             clan["leaders"].remove(
#                 member.id
#             )

#         await save_data()

#         await interaction.response.send_message(
#             f"🔨 {member.mention} has been banned "
#             f"from **{clan['clan_name']}**.",
#             ephemeral=True
#         )

#         await clan_log(
#             guild,
#             "🔨 Clan Ban",
#             (
#                 f"**Clan:** {clan['clan_name']}\n"
#                 f"**Member:** {member.mention}\n"
#                 f"**By:** {interaction.user.mention}"
#             ),
#             discord.Color.red()
#         )

#     # ========================================================
#     # /CLANUNBAN
#     # ========================================================

#     @app_commands.command(
#         name="clanunban",
#         description="Remove a clan ban"
#     )
#     @app_commands.describe(
#         member="Member to unban"
#     )
#     async def clanunban(
#         self,
#         interaction: discord.Interaction,
#         member: discord.Member
#     ):

#         guild = interaction.guild

#         clan_id, clan = find_clan_for_member(
#             guild,
#             interaction.user
#         )

#         if clan is None or not can_manage_clan(
#             interaction.user,
#             clan
#         ):

#             await interaction.response.send_message(
#                 "❌ You cannot manage this clan.",
#                 ephemeral=True
#             )

#             return

#         if member.id in clan[
#             "banned_members"
#         ]:

#             clan[
#                 "banned_members"
#             ].remove(
#                 member.id
#             )

#             await save_data()

#         await interaction.response.send_message(
#             f"✅ {member.mention} is no longer "
#             f"banned from your clan.",
#             ephemeral=True
#         )

#         await clan_log(
#             guild,
#             "🔓 Clan Unban",
#             (
#                 f"**Clan:** {clan['clan_name']}\n"
#                 f"**Member:** {member.mention}\n"
#                 f"**By:** {interaction.user.mention}"
#             )
#         )

#     # ========================================================
#     # /CLANADDCHANNEL
#     # ========================================================

#     @app_commands.command(
#         name="clanaddchannel",
#         description="Create a channel inside your clan"
#     )
#     @app_commands.describe(
#         name="Channel name",
#         channel_type="Text or voice",
#         leaders_only="Make this channel leaders-only"
#     )
#     @app_commands.choices(
#         channel_type=[
#             app_commands.Choice(
#                 name="Text",
#                 value="text"
#             ),
#             app_commands.Choice(
#                 name="Voice",
#                 value="voice"
#             )
#         ]
#     )
#     async def clanaddchannel(
#         self,
#         interaction: discord.Interaction,
#         name: str,
#         channel_type: app_commands.Choice[str],
#         leaders_only: bool = False
#     ):

#         guild = interaction.guild

#         clan_id, clan = find_clan_for_member(
#             guild,
#             interaction.user
#         )

#         if clan is None or not can_manage_clan(
#             interaction.user,
#             clan
#         ):

#             await interaction.response.send_message(
#                 "❌ You cannot manage this clan.",
#                 ephemeral=True
#             )

#             return

#         category_id = (
#             clan["leader_category_id"]
#             if leaders_only
#             else clan["category_id"]
#         )

#         category = guild.get_channel(
#             category_id
#         )

#         if category is None:

#             await interaction.response.send_message(
#                 "❌ Clan category no longer exists.",
#                 ephemeral=True
#             )

#             return

#         try:

#             if channel_type.value == "text":

#                 channel = await guild.create_text_channel(
#                     name=name.lower().replace(
#                         " ",
#                         "-"
#                     ),
#                     category=category
#                 )

#             else:

#                 channel = await guild.create_voice_channel(
#                     name=name,
#                     category=category
#                 )

#             # ------------------------------------------------
#             # PERMISSIONS
#             # ------------------------------------------------

#             if leaders_only:

#                 await channel.set_permissions(
#                     guild.default_role,
#                     view_channel=False
#                 )

#                 leader_role = guild.get_role(
#                     clan["leader_role_id"]
#                 )

#                 if leader_role:

#                     await channel.set_permissions(
#                         leader_role,
#                         view_channel=True,
#                         send_messages=True,
#                         connect=True,
#                         speak=True,
#                         read_message_history=True
#                     )

#             else:

#                 await channel.set_permissions(
#                     guild.default_role,
#                     view_channel=False
#                 )

#                 member_role = guild.get_role(
#                     clan["member_role_id"]
#                 )

#                 leader_role = guild.get_role(
#                     clan["leader_role_id"]
#                 )

#                 if member_role:

#                     await channel.set_permissions(
#                         member_role,
#                         view_channel=True,
#                         send_messages=True,
#                         connect=True,
#                         speak=True,
#                         read_message_history=True
#                     )

#                 if leader_role:

#                     await channel.set_permissions(
#                         leader_role,
#                         view_channel=True,
#                         send_messages=True,
#                         connect=True,
#                         speak=True,
#                         read_message_history=True
#                     )

#             await interaction.response.send_message(
#                 f"✅ Created {channel.mention}.",
#                 ephemeral=True
#             )

#             await clan_log(
#                 guild,
#                 "📁 Clan Channel Created",
#                 (
#                     f"**Clan:** {clan['clan_name']}\n"
#                     f"**Channel:** {channel.mention}\n"
#                     f"**By:** {interaction.user.mention}\n"
#                     f"**Leaders only:** {leaders_only}"
#                 )
#             )

#         except Exception as e:

#             await interaction.response.send_message(
#                 f"❌ Failed to create channel.\n`{e}`",
#                 ephemeral=True
#             )

#     # ========================================================
#     # /CLANEDIT
#     # ========================================================

#     @app_commands.command(
#         name="clanedit",
#         description="Edit your clan category name"
#     )
#     @app_commands.describe(
#         new_name="New category name"
#     )
#     async def clanedit(
#         self,
#         interaction: discord.Interaction,
#         new_name: str
#     ):

#         guild = interaction.guild

#         clan_id, clan = find_clan_for_member(
#             guild,
#             interaction.user
#         )

#         if clan is None or not can_manage_clan(
#             interaction.user,
#             clan
#         ):

#             await interaction.response.send_message(
#                 "❌ You cannot manage this clan.",
#                 ephemeral=True
#             )

#             return

#         category = guild.get_channel(
#             clan["category_id"]
#         )

#         if category is None:

#             await interaction.response.send_message(
#                 "❌ Clan category no longer exists.",
#                 ephemeral=True
#             )

#             return

#         old_name = category.name

#         await category.edit(
#             name=new_name
#         )

#         clan["category_name"] = new_name

#         await save_data()

#         await interaction.response.send_message(
#             f"✅ Clan category renamed to "
#             f"**{new_name}**.",
#             ephemeral=True
#         )

#         await clan_log(
#             guild,
#             "✏️ Clan Category Edited",
#             (
#                 f"**Clan:** {clan['clan_name']}\n"
#                 f"**Old:** {old_name}\n"
#                 f"**New:** {new_name}\n"
#                 f"**By:** {interaction.user.mention}"
#             )
#         )

#     # ========================================================
#     # /SETCLANLOGS
#     # ========================================================

#     @app_commands.command(
#         name="setclanlogs",
#         description="Set the clan logging channel"
#     )
#     @app_commands.describe(
#         channel="Channel where clan logs will be sent"
#     )
#     async def setclanlogs(
#         self,
#         interaction: discord.Interaction,
#         channel: discord.TextChannel
#     ):

#         guild = interaction.guild

#         if guild is None:
#             return

#         if interaction.user.id != guild.owner_id:

#             await interaction.response.send_message(
#                 "❌ Only the server owner can configure "
#                 "the clan log channel.",
#                 ephemeral=True
#             )

#             return

#         guild_info = get_guild_data(
#             guild.id
#         )

#         guild_info[
#             "log_channel_id"
#         ] = channel.id

#         await save_data()

#         await interaction.response.send_message(
#             f"✅ Clan logs will now be sent to "
#             f"{channel.mention}.",
#             ephemeral=True
#         )

#         await clan_log(
#             guild,
#             "⚙️ Clan Logs Configured",
#             (
#                 f"Clan logging channel set to "
#                 f"{channel.mention}."
#             )
#         )

#     # ========================================================
#     # /SETCLANAPPROVAL
#     # ========================================================

#     @app_commands.command(
#         name="setclanapproval",
#         description="Set the clan approval channel"
#     )
#     @app_commands.describe(
#         channel="Channel for clan applications"
#     )
#     async def setclanapproval(
#         self,
#         interaction: discord.Interaction,
#         channel: discord.TextChannel
#     ):

#         guild = interaction.guild

#         if interaction.user.id != guild.owner_id:

#             await interaction.response.send_message(
#                 "❌ Only the server owner can configure "
#                 "the clan approval channel.",
#                 ephemeral=True
#             )

#             return

#         guild_info = get_guild_data(
#             guild.id
#         )

#         guild_info[
#             "approval_channel_id"
#         ] = channel.id

#         await save_data()

#         await interaction.response.send_message(
#             f"✅ Clan approval applications will now "
#             f"be sent to {channel.mention}.",
#             ephemeral=True
#         )

#     # ========================================================
#     # /DELETECLAN
#     # ========================================================

#     @app_commands.command(
#         name="deleteclan",
#         description="Delete an entire clan"
#     )
#     @app_commands.describe(
#         clan_name="Name of the clan to delete"
#     )
#     async def deleteclan(
#         self,
#         interaction: discord.Interaction,
#         clan_name: str
#     ):

#         guild = interaction.guild

#         if guild is None:
#             return

#         # ----------------------------------------------------
#         # MODERATOR ONLY
#         # ----------------------------------------------------

#         if not is_moderator(
#             interaction.user
#         ):

#             await interaction.response.send_message(
#                 f"❌ You need the "
#                 f"**{MODERATOR_ROLE_NAME}** role "
#                 "to delete clans.",
#                 ephemeral=True
#             )

#             return

#         guild_info = get_guild_data(
#             guild.id
#         )

#         target_id = None
#         target_clan = None

#         for clan_id, clan in guild_info[
#             "clans"
#         ].items():

#             if (
#                 clan["clan_name"].lower()
#                 == clan_name.lower()
#             ):

#                 target_id = clan_id
#                 target_clan = clan
#                 break

#         if target_clan is None:

#             await interaction.response.send_message(
#                 f"❌ Clan **{clan_name}** was not found.",
#                 ephemeral=True
#             )

#             return

#         # ----------------------------------------------------
#         # CONFIRMATION
#         # ----------------------------------------------------

#         embed = discord.Embed(
#             title="⚠️ Delete Clan?",
#             description=(
#                 f"You are about to delete "
#                 f"**{target_clan['clan_name']}**.\n\n"
#                 "This will permanently remove:\n"
#                 "• Clan category\n"
#                 "• Clan channels\n"
#                 "• Leader category\n"
#                 "• Leader channels\n"
#                 "• Member role\n"
#                 "• Leader role\n\n"
#                 "**This cannot be undone.**"
#             ),
#             color=discord.Color.red()
#         )

#         await interaction.response.send_message(
#             embed=embed,
#             view=DeleteClanView(
#                 target_id,
#                 target_clan
#             ),
#             ephemeral=True
#         )


# # ============================================================
# # DELETE VIEW
# # ============================================================

# class DeleteClanView(
#     ui.View
# ):

#     def __init__(
#         self,
#         clan_id,
#         clan
#     ):

#         super().__init__(
#             timeout=60
#         )

#         self.clan_id = clan_id
#         self.clan = clan

#     @ui.button(
#         label="Delete Clan",
#         style=discord.ButtonStyle.danger,
#         emoji="🗑️"
#     )
#     async def confirm(
#         self,
#         interaction: discord.Interaction,
#         button: ui.Button
#     ):

#         guild = interaction.guild

#         if guild is None:
#             return

#         if not is_moderator(
#             interaction.user
#         ):

#             await interaction.response.send_message(
#                 "❌ You are not a moderator.",
#                 ephemeral=True
#             )

#             return

#         await interaction.response.defer(
#             ephemeral=True
#         )

#         clan = self.clan

#         deleted = []

#         # ====================================================
#         # DELETE CHANNELS
#         # ====================================================

#         channel_ids = [

#             clan.get(
#                 "member_text_id"
#             ),

#             clan.get(
#                 "general_voice_id"
#             ),

#             clan.get(
#                 "leader_text_id"
#             ),

#             clan.get(
#                 "leader_voice_id"
#             ),

#             clan.get(
#                 "category_id"
#             ),

#             clan.get(
#                 "leader_category_id"
#             )
#         ]

#         # Delete child channels first
#         for channel_id in channel_ids:

#             if not channel_id:
#                 continue

#             channel = guild.get_channel(
#                 channel_id
#             )

#             if channel is None:
#                 continue

#             try:

#                 await channel.delete(
#                     reason=(
#                         f"Clan deleted by "
#                         f"{interaction.user}"
#                     )
#                 )

#                 deleted.append(
#                     channel.name
#                 )

#             except discord.Forbidden:

#                 print(
#                     f"[DELETE CLAN] Cannot delete "
#                     f"{channel.name}"
#                 )

#             except Exception as e:

#                 print(
#                     f"[DELETE CLAN] {e}"
#                 )

#         # ====================================================
#         # DELETE ROLES
#         # ====================================================

#         role_ids = [

#             clan.get(
#                 "member_role_id"
#             ),

#             clan.get(
#                 "leader_role_id"
#             )
#         ]

#         for role_id in role_ids:

#             if not role_id:
#                 continue

#             role = guild.get_role(
#                 role_id
#             )

#             if role is None:
#                 continue

#             try:

#                 await role.delete(
#                     reason=(
#                         f"Clan deleted by "
#                         f"{interaction.user}"
#                     )
#                 )

#             except discord.Forbidden:

#                 print(
#                     f"[DELETE CLAN] Cannot delete role "
#                     f"{role.name}"
#                 )

#         # ====================================================
#         # REMOVE DATABASE RECORD
#         # ====================================================

#         guild_info = get_guild_data(
#             guild.id
#         )

#         guild_info[
#             "clans"
#         ].pop(
#             self.clan_id,
#             None
#         )

#         await save_data()

#         # ====================================================
#         # RESPONSE
#         # ====================================================

#         embed = discord.Embed(
#             title="🗑️ Clan Deleted",
#             description=(
#                 f"**{clan['clan_name']}** "
#                 "has been deleted."
#             ),
#             color=discord.Color.red()
#         )

#         embed.add_field(
#             name="Deleted By",
#             value=interaction.user.mention
#         )

#         embed.add_field(
#             name="Channels Removed",
#             value=str(
#                 len(deleted)
#             )
#         )

#         for child in self.children:

#             child.disabled = True

#         await interaction.edit_original_response(
#             embed=embed,
#             view=self
#         )

#         await clan_log(
#             guild,
#             "🗑️ Clan Deleted",
#             (
#                 f"**Clan:** {clan['clan_name']}\n"
#                 f"**Deleted by:** "
#                 f"{interaction.user.mention}\n"
#                 f"**Channels removed:** "
#                 f"{len(deleted)}"
#             ),
#             discord.Color.red()
#         )

#         self.stop()

#     @ui.button(
#         label="Cancel",
#         style=discord.ButtonStyle.secondary,
#         emoji="↩️"
#     )
#     async def cancel(
#         self,
#         interaction: discord.Interaction,
#         button: ui.Button
#     ):

#         await interaction.response.send_message(
#             "✅ Clan deletion cancelled.",
#             ephemeral=True
#         )

#         self.stop()


# # ============================================================
# # COG SETUP
# # ============================================================

# async def setup(
#     bot: commands.Bot
# ):

#     await bot.add_cog(
#         ClanManager(bot)
#     )

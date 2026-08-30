import discord
from discord.ext import commands
from discord import app_commands, ui

import json
import os
import asyncio
from typing import Optional
from datetime import datetime, timezone


# ============================================================
# CONFIGURATION
# ============================================================

MODERATOR_ROLE_NAME = "MODERATOR"

DATA_FILE = "clan_data.json"

CREATE_PANEL_CUSTOM_ID = "clan_create_panel"

LEADER_REFRESH_PREFIX = "clan_refresh:"
LEADER_MANAGE_PREFIX = "clan_manage:"
LEADER_INVITE_PREFIX = "clan_invite:"

INVITE_ACCEPT_PREFIX = "clan_invite_accept:"
INVITE_DECLINE_PREFIX = "clan_invite_decline:"

MOD_CLAN_SELECT_PREFIX = "mod_clan_select:"
MOD_DELETE_PREFIX = "mod_clan_delete:"
MOD_WARN_PREFIX = "mod_clan_warn:"
MOD_PERMISSION_PREFIX = "mod_clan_permission:"
MOD_REFRESH_PREFIX = "mod_clan_refresh:"

ROLE_MEMBER = "member"
ROLE_MODERATOR = "moderator"


# ============================================================
# DATA LOCK
# ============================================================

data_lock = asyncio.Lock()


# ============================================================
# LOAD DATA
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

            data = json.load(f)

        if not isinstance(
            data,
            dict
        ):

            return {
                "guilds": {}
            }

        data.setdefault(
            "guilds",
            {}
        )

        return data

    except Exception as e:

        print(
            f"❌ Failed to load clan data: {e}"
        )

        return {
            "guilds": {}
        }


clan_data = load_data()


# ============================================================
# SAVE DATA
# ============================================================

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


# ============================================================
# GUILD DATA
# ============================================================

def get_guild_data(
    guild_id: int
):

    guild_id = str(
        guild_id
    )

    if "guilds" not in clan_data:

        clan_data["guilds"] = {}

    if guild_id not in clan_data["guilds"]:

        clan_data["guilds"][guild_id] = {

            "log_channel_id": None,

            "approval_channel_id": None,

            "create_panel_message_id": None,

            "pending": {},

            "invites": {},

            "clans": {}

        }

    guild_info = clan_data[
        "guilds"
    ][
        guild_id
    ]

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
        "invites",
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
):

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

    embed.set_footer(
        text="Clan System Logs"
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
                clan.get(
                    role_key
                )
            )

            if role and role in member.roles:

                return clan_id, clan

    return None, None


# ============================================================
# CLAN MEMBERS
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

        if (
            member_role
            and member_role in member.roles
        ):

            members.append(
                member
            )

            continue

        if (
            leader_role
            and leader_role in member.roles
        ):

            members.append(
                member
            )

            continue

        if (
            moderator_role
            and moderator_role in member.roles
        ):

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
            clan.get(
                role_key
            )
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

    if (
        leader_role
        and leader_role in member.roles
    ):

        return True

    return False


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
# CLAN CREATION MODAL
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
        # CHECK OWNER
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
        # CHECK PENDING
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
        # DUPLICATE CLAN
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
        # APPROVAL CHANNEL
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
        # APPLICATION
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
        # APPROVAL EMBED
        # ----------------------------------------------------

        embed = discord.Embed(

            title="⚔️ New Clan Application",

            description=(
                "A new clan application is "
                "waiting for moderator approval."
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

        approve = discord.ui.Button(

            label="Approve Clan",

            style=discord.ButtonStyle.success,

            emoji="✅",

            custom_id=(
                f"clan_approve:{application_id}"
            )

        )

        reject = discord.ui.Button(

            label="Reject Clan",

            style=discord.ButtonStyle.danger,

            emoji="❌",

            custom_id=(
                f"clan_reject:{application_id}"
            )

        )

        approve.callback = self.approve

        reject.callback = self.reject

        self.add_item(
            approve
        )

        self.add_item(
            reject
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

                "❌ You need the MODERATOR role.",

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
            # ROLES
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
                    f"{application['category_name']} "
                    f"• LEADERS"
                ),

                reason="Clan leader section"

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

                "banned_members":
                    [],

                "warnings":
                    {},

                "permissions": {

                    "moderator_manage_members":
                        False,

                    "moderator_invite":
                        False,

                    "moderator_manage_channels":
                        False

                },

                "created_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat()

            }

            guild_info[
                "pending"
            ].pop(
                self.application_id,
                None
            )

            await save_data()

            # ------------------------------------------------
            # WELCOME
            # ------------------------------------------------

            await member_text.send(

                embed=discord.Embed(

                    title=(
                        f"⚔️ "
                        f"{application['clan_name']}"
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
            # LEADER PANEL
            # ------------------------------------------------

            await update_leader_panel(

                guild,

                clan_id,

                guild_info[
                    "clans"
                ][
                    clan_id
                ]

            )

            # ------------------------------------------------
            # APPROVAL MESSAGE
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

                name="👤 Member Role",

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
                    f"**Clan:** "
                    f"{application['clan_name']}\n"

                    f"**Owner:** "
                    f"<@{application['creator_id']}>\n"

                    f"**Approved by:** "
                    f"{interaction.user.mention}"
                ),

                discord.Color.green()

            )

            # ------------------------------------------------
            # DM OWNER
            # ------------------------------------------------

            if creator:

                try:

                    await creator.send(

                        f"🎉 Your clan "
                        f"**{application['clan_name']}** "
                        "has been approved!"

                    )

                except Exception:

                    pass

        except Exception as e:

            print(
                f"❌ Clan creation error: {e}"
            )

            for obj in reversed(
                created_objects
            ):

                try:

                    await obj.delete(
                        reason="Clan creation cleanup"
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

                "❌ You need the MODERATOR role.",

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

        await interaction.response.edit_message(

            embed=embed,

            view=self

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
            f"🏰 "
            f"{clan.get('clan_name', 'Clan')}"
        ),

        description=(

            "Clan management panel.\n\n"

            "🔄 Refresh the member list.\n"

            "👤 Manage existing members.\n"

            "📨 Invite a new member."

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
                and
                leader_role in member.roles

            ):

                role_text = "👑 Leader"

            elif (

                moderator_role
                and
                moderator_role in member.roles

            ):

                role_text = "🛡️ Clan Moderator"

            else:

                role_text = "👤 Clan Member"

        lines.append(

            f"{role_text} "
            f"{member.mention}"

        )

    member_text = (

        "\n".join(lines)

        if lines

        else

        "No clan members found."

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

        invite_button = discord.ui.Button(

            label="Invite Member",

            style=discord.ButtonStyle.primary,

            emoji="📨",

            custom_id=(

                f"{LEADER_INVITE_PREFIX}"
                f"{self.clan_id}"

            )

        )

        refresh_button.callback = self.refresh_members

        manage_button.callback = self.manage_member

        invite_button.callback = self.invite_member

        self.add_item(
            refresh_button
        )

        self.add_item(
            manage_button
        )

        self.add_item(
            invite_button
        )

    async def get_clan(
        self,
        interaction
    ):

        guild = interaction.guild

        if guild is None:

            return None

        clan = get_guild_data(
            guild.id
        )[
            "clans"
        ].get(
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

                "❌ Only the clan leader can manage this panel.",

                ephemeral=True

            )

            return None

        return clan

    async def refresh_members(
        self,
        interaction
    ):

        clan = await self.get_clan(
            interaction
        )

        if clan is None:

            return

        embed = build_leader_embed(

            interaction.guild,

            clan

        )

        await interaction.response.edit_message(

            embed=embed,

            view=LeaderPanelView(
                self.clan_id
            )

        )

    async def manage_member(
        self,
        interaction
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

            m

            for m in members

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

        await interaction.response.send_message(

            "👤 Select a clan member:",

            view=MemberSelectView(

                self.clan_id,

                members[:25]

            ),

            ephemeral=True

        )

    async def invite_member(
        self,
        interaction
    ):

        clan = await self.get_clan(
            interaction
        )

        if clan is None:

            return

        await interaction.response.send_modal(

            ClanInviteModal(
                self.clan_id
            )

        )


# ============================================================
# INVITE MODAL
# ============================================================

class ClanInviteModal(
    ui.Modal,
    title="Invite Member"
):

    member_id = ui.TextInput(

        label="Member ID",

        placeholder="Enter the Discord user ID",

        required=True,

        max_length=25

    )

    def __init__(
        self,
        clan_id
    ):

        super().__init__()

        self.clan_id = str(
            clan_id
        )

    async def on_submit(
        self,
        interaction
    ):

        guild = interaction.guild

        if guild is None:

            return

        clan = get_guild_data(
            guild.id
        )[
            "clans"
        ].get(
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

                "❌ Only the clan leader can invite members.",

                ephemeral=True

            )

            return

        try:

            member_id = int(
                self.member_id.value.strip()
            )

        except ValueError:

            await interaction.response.send_message(

                "❌ Enter a valid Discord member ID.",

                ephemeral=True

            )

            return

        member = guild.get_member(
            member_id
        )

        if member is None:

            try:

                member = await guild.fetch_member(
                    member_id
                )

            except Exception:

                member = None

        if member is None:

            await interaction.response.send_message(

                "❌ I could not find that member in this server.",

                ephemeral=True

            )

            return

        if member.id == clan.get(
            "owner_id"
        ):

            await interaction.response.send_message(

                "❌ This member is already the clan owner.",

                ephemeral=True

            )

            return

        if is_clan_member(
            member,
            clan
        ):

            await interaction.response.send_message(

                "❌ This member is already in the clan.",

                ephemeral=True

            )

            return

        if member.id in clan.get(
            "banned_members",
            []
        ):

            await interaction.response.send_message(

                "❌ This member is banned from the clan.",

                ephemeral=True

            )

            return

        invite_id = str(
            discord.utils.time_snowflake(
                discord.utils.utcnow()
            )
        )

        guild_info = get_guild_data(
            guild.id
        )

        guild_info[
            "invites"
        ][
            invite_id
        ] = {

            "invite_id":
                invite_id,

            "clan_id":
                self.clan_id,

            "member_id":
                member.id,

            "invited_by":
                interaction.user.id,

            "created_at":
                discord.utils.utcnow().isoformat()

        }

        await save_data()

        embed = discord.Embed(

            title="📨 Clan Invitation",

            description=(

                f"You have been invited to join "
                f"**{clan['clan_name']}**.\n\n"

                f"👑 Leader: "
                f"<@{clan['owner_id']}>\n\n"

                "Click **Accept** to join the clan.\n"
                "Click **Decline** to reject the invitation."

            ),

            color=discord.Color.blurple()

        )

        try:

            await member.send(

                embed=embed,

                view=ClanInviteView(
                    invite_id
                )

            )

            await interaction.response.send_message(

                f"✅ Invitation sent to {member.mention}.",

                ephemeral=True

            )

        except discord.Forbidden:

            guild_info[
                "invites"
            ].pop(
                invite_id,
                None
            )

            await save_data()

            await interaction.response.send_message(

                "❌ I could not DM this member. "
                "Their DMs may be disabled.",

                ephemeral=True

            )


# ============================================================
# INVITE VIEW
# ============================================================

class ClanInviteView(
    ui.View
):

    def __init__(
        self,
        invite_id
    ):

        super().__init__(
            timeout=None
        )

        self.invite_id = str(
            invite_id
        )

        accept = discord.ui.Button(

            label="Accept",

            style=discord.ButtonStyle.success,

            emoji="✅",

            custom_id=(

                f"{INVITE_ACCEPT_PREFIX}"
                f"{self.invite_id}"

            )

        )

        decline = discord.ui.Button(

            label="Decline",

            style=discord.ButtonStyle.danger,

            emoji="❌",

            custom_id=(

                f"{INVITE_DECLINE_PREFIX}"
                f"{self.invite_id}"

            )

        )

        accept.callback = self.accept

        decline.callback = self.decline

        self.add_item(
            accept
        )

        self.add_item(
            decline
        )

    async def accept(
        self,
        interaction
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(

                "❌ This invitation must be accepted inside the server.",

                ephemeral=True

            )

            return

        guild_info = get_guild_data(
            guild.id
        )

        invite = guild_info[
            "invites"
        ].get(
            self.invite_id
        )

        if invite is None:

            await interaction.response.send_message(

                "❌ This invitation no longer exists.",

                ephemeral=True

            )

            return

        if invite[
            "member_id"
        ] != interaction.user.id:

            await interaction.response.send_message(

                "❌ This invitation belongs to another member.",

                ephemeral=True

            )

            return

        clan = guild_info[
            "clans"
        ].get(
            str(
                invite[
                    "clan_id"
                ]
            )
        )

        if clan is None:

            guild_info[
                "invites"
            ].pop(
                self.invite_id,
                None
            )

            await save_data()

            await interaction.response.send_message(

                "❌ The clan no longer exists.",

                ephemeral=True

            )

            return

        if interaction.user.id in clan.get(
            "banned_members",
            []
        ):

            await interaction.response.send_message(

                "❌ You are banned from this clan.",

                ephemeral=True

            )

            return

        member_role = guild.get_role(

            clan.get(
                "member_role_id"
            )

        )

        if member_role is None:

            await interaction.response.send_message(

                "❌ The clan member role no longer exists.",

                ephemeral=True

            )

            return

        try:

            await interaction.user.add_roles(

                member_role,

                reason=(
                    f"Accepted invitation to "
                    f"{clan['clan_name']}"
                )

            )

        except discord.Forbidden:

            await interaction.response.send_message(

                "❌ I cannot give you the clan role. "
                "The bot's role must be above the clan role.",

                ephemeral=True

            )

            return

        # ----------------------------------------------------
        # SAVE ACCEPTANCE
        # ----------------------------------------------------

        guild_info[
            "invites"
        ].pop(
            self.invite_id,
            None
        )

        await save_data()

        # ----------------------------------------------------
        # UPDATE LEADER PANEL
        # ----------------------------------------------------

        await update_leader_panel(

            guild,

            str(
                invite[
                    "clan_id"
                ]
            ),

            clan

        )

        for child in self.children:

            child.disabled = True

        await interaction.response.edit_message(

            content=(

                f"✅ You joined **{clan['clan_name']}**!\n\n"

                "The clan member role has been added."

            ),

            embed=None,

            view=self

        )

        await clan_log(

            guild,

            "📨 Clan Invitation Accepted",

            (
                f"**Clan:** {clan['clan_name']}\n"
                f"**Member:** {interaction.user.mention}\n"
                f"**Invited by:** "
                f"<@{invite['invited_by']}>"
            ),

            discord.Color.green()

        )

    async def decline(
        self,
        interaction
    ):

        guild = interaction.guild

        if guild is None:

            return

        guild_info = get_guild_data(
            guild.id
        )

        invite = guild_info[
            "invites"
        ].get(
            self.invite_id
        )

        if invite is None:

            await interaction.response.send_message(

                "❌ This invitation no longer exists.",

                ephemeral=True

            )

            return

        if invite[
            "member_id"
        ] != interaction.user.id:

            await interaction.response.send_message(

                "❌ This invitation belongs to another member.",

                ephemeral=True

            )

            return

        clan = guild_info[
            "clans"
        ].get(
            str(
                invite[
                    "clan_id"
                ]
            )
        )

        guild_info[
            "invites"
        ].pop(
            self.invite_id,
            None
        )

        await save_data()

        for child in self.children:

            child.disabled = True

        await interaction.response.edit_message(

            content=(

                f"❌ You declined the invitation"
                + (
                    f" to **{clan['clan_name']}**."
                    if clan
                    else "."
                )

            ),

            embed=None,

            view=self

        )


# ============================================================
# MEMBER SELECT
# ============================================================

class MemberSelect(
    ui.Select
):

    def __init__(
        self,
        clan_id,
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

                    value=str(
                        member.id
                    ),

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
        interaction
    ):

        guild = interaction.guild

        clan = get_guild_data(
            guild.id
        )[
            "clans"
        ].get(
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

            int(
                self.values[0]
            )

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
                "Select the role:"

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
        clan_id,
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
        clan_id,
        member_id
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

                emoji="👤"

            ),

            discord.SelectOption(

                label="Clan Moderator",

                value=ROLE_MODERATOR,

                emoji="🛡️"

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
        interaction
    ):

        guild = interaction.guild

        clan = get_guild_data(
            guild.id
        )[
            "clans"
        ].get(
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

            if member_role:

                await member.remove_roles(
                    member_role
                )

            if moderator_role:

                await member.remove_roles(
                    moderator_role
                )

            if selected == ROLE_MEMBER:

                if member_role:

                    await member.add_roles(
                        member_role
                    )

                role_text = "👤 Clan Member"

            else:

                if moderator_role:

                    await member.add_roles(
                        moderator_role
                    )

                role_text = "🛡️ Clan Moderator"

            await save_data()

            await update_leader_panel(

                guild,

                self.clan_id,

                clan

            )

            await interaction.response.edit_message(

                content=(

                    f"✅ **{member.display_name}** "
                    f"is now **{role_text}**."

                ),

                view=None

            )

        except discord.Forbidden:

            await interaction.response.send_message(

                "❌ I cannot manage the clan role. "
                "Move the bot's highest role above the clan roles.",

                ephemeral=True

            )


class RoleSelectView(
    ui.View
):

    def __init__(
        self,
        clan_id,
        member_id
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
    guild,
    clan_id,
    clan
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

                and

                message.embeds

                and

                message.embeds[0].title

                and

                clan.get(
                    "clan_name",
                    ""
                )
                in
                message.embeds[0].title

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
    guild,
    clan
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

    permissions = clan.get(
        "permissions",
        {}
    )

    embed = discord.Embed(

        title=(
            f"🏰 "
            f"{clan.get('clan_name', 'Clan')}"
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

    embed.add_field(

        name="🆔 Clan ID",

        value=f"`{clan.get('clan_id')}`",

        inline=True

    )

    embed.add_field(

        name="🎭 Roles",

        value=(

            f"👑 Leader: "
            f"{leader_role.mention if leader_role else 'Missing'}\n"

            f"🛡️ Moderator: "
            f"{moderator_role.mention if moderator_role else 'Missing'}\n"

            f"👤 Member: "
            f"{member_role.mention if member_role else 'Missing'}"

        ),

        inline=False

    )

    embed.add_field(

        name="🔗 Channels",

        value=(

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

        ),

        inline=False

    )

    embed.add_field(

        name="🔐 Moderator Permissions",

        value=(

            f"Manage Members: "
            f"{'✅' if permissions.get('moderator_manage_members') else '❌'}\n"

            f"Invite Members: "
            f"{'✅' if permissions.get('moderator_invite') else '❌'}\n"

            f"Manage Channels: "
            f"{'✅' if permissions.get('moderator_manage_channels') else '❌'}"

        ),

        inline=False

    )

    warnings = clan.get(
        "warnings",
        {}
    )

    embed.add_field(

        name="⚠️ Warnings",

        value=str(
            len(warnings)
        ),

        inline=True

    )

    return embed


# ============================================================
# MODERATOR CLAN SELECT
# ============================================================

class ModeratorClanSelect(
    ui.Select
):

    def __init__(
        self,
        clans
    ):

        options = []

        for clan_id, clan in clans[:25]:

            options.append(

                discord.SelectOption(

                    label=clan.get(
                        "clan_name",
                        "Clan"
                    )[:100],

                    value=str(
                        clan_id
                    ),

                    description=(
                        f"Owner ID: "
                        f"{clan.get('owner_id')}"
                    )[:100]

                )

            )

        super().__init__(

            placeholder="Select a clan...",

            min_values=1,

            max_values=1,

            options=options

        )

    async def callback(
        self,
        interaction
    ):

        guild = interaction.guild

        if guild is None:

            return

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(

                "❌ Moderator access required.",

                ephemeral=True

            )

            return

        clan_id = self.values[0]

        clan = get_guild_data(
            guild.id
        )[
            "clans"
        ].get(
            clan_id
        )

        if clan is None:

            await interaction.response.send_message(

                "❌ Clan not found.",

                ephemeral=True

            )

            return

        await interaction.response.edit_message(

            embed=build_moderator_clan_embed(

                guild,

                clan

            ),

            view=ModeratorClanManagementView(

                clan_id

            )

        )


class ModeratorClanSelectView(
    ui.View
):

    def __init__(
        self,
        clans
    ):

        super().__init__(
            timeout=180
        )

        self.add_item(

            ModeratorClanSelect(
                clans
            )

        )


# ============================================================
# MODERATOR MANAGEMENT VIEW
# ============================================================

class ModeratorClanManagementView(
    ui.View
):

    def __init__(
        self,
        clan_id
    ):

        super().__init__(
            timeout=180
        )

        self.clan_id = str(
            clan_id
        )

    async def check(
        self,
        interaction
    ):

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(

                "❌ Moderator access required.",

                ephemeral=True

            )

            return None

        clan = get_guild_data(
            interaction.guild.id
        )[
            "clans"
        ].get(
            self.clan_id
        )

        if clan is None:

            await interaction.response.send_message(

                "❌ Clan no longer exists.",

                ephemeral=True

            )

            return None

        return clan

    @ui.button(

        label="Delete",

        style=discord.ButtonStyle.danger,

        emoji="🗑️"

    )
    async def delete_button(
        self,
        interaction,
        button
    ):

        clan = await self.check(
            interaction
        )

        if clan is None:

            return

        await interaction.response.send_message(

            embed=discord.Embed(

                title="⚠️ Delete Clan?",

                description=(

                    f"Delete **{clan['clan_name']}**?\n\n"

                    "This will remove the clan channels, "
                    "category and clan roles."

                ),

                color=discord.Color.red()

            ),

            view=ConfirmDeleteView(

                self.clan_id

            ),

            ephemeral=True

        )

    @ui.button(

        label="Warn",

        style=discord.ButtonStyle.secondary,

        emoji="⚠️"

    )
    async def warn_button(
        self,
        interaction,
        button
    ):

        clan = await self.check(
            interaction
        )

        if clan is None:

            return

        await interaction.response.send_modal(

            ModeratorWarnModal(
                self.clan_id
            )

        )

    @ui.button(

        label="Permissions",

        style=discord.ButtonStyle.primary,

        emoji="🔐"

    )
    async def permission_button(
        self,
        interaction,
        button
    ):

        clan = await self.check(
            interaction
        )

        if clan is None:

            return

        await interaction.response.send_message(

            embed=discord.Embed(

                title="🔐 Clan Permissions",

                description=(

                    "Choose which permissions "
                    "the clan moderator role should have."

                ),

                color=discord.Color.blurple()

            ),

            view=ClanPermissionView(

                self.clan_id

            ),

            ephemeral=True

        )

    @ui.button(

        label="Refresh",

        style=discord.ButtonStyle.success,

        emoji="🔄"

    )
    async def refresh_button(
        self,
        interaction,
        button
    ):

        clan = await self.check(
            interaction
        )

        if clan is None:

            return

        await interaction.response.edit_message(

            embed=build_moderator_clan_embed(

                interaction.guild,

                clan

            ),

            view=ModeratorClanManagementView(

                self.clan_id

            )

        )


# ============================================================
# DELETE CONFIRMATION
# ============================================================

class ConfirmDeleteView(
    ui.View
):

    def __init__(
        self,
        clan_id
    ):

        super().__init__(
            timeout=60
        )

        self.clan_id = str(
            clan_id
        )

    @ui.button(

        label="Confirm Delete",

        style=discord.ButtonStyle.danger,

        emoji="🗑️"

    )
    async def confirm(
        self,
        interaction,
        button
    ):

        guild = interaction.guild

        if guild is None:

            return

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(

                "❌ Moderator access required.",

                ephemeral=True

            )

            return

        guild_info = get_guild_data(
            guild.id
        )

        clan = guild_info[
            "clans"
        ].get(
            self.clan_id
        )

        if clan is None:

            await interaction.response.send_message(

                "❌ Clan not found.",

                ephemeral=True

            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        # ----------------------------------------------------
        # REMOVE CLAN ROLES FROM MEMBERS
        # ----------------------------------------------------

        role_ids = [

            clan.get(
                "member_role_id"
            ),

            clan.get(
                "leader_role_id"
            ),

            clan.get(
                "moderator_role_id"
            )

        ]

        roles = []

        for role_id in role_ids:

            if role_id:

                role = guild.get_role(
                    role_id
                )

                if role:

                    roles.append(
                        role
                    )

        for member in guild.members:

            removable = [

                role

                for role in roles

                if role in member.roles

            ]

            if removable:

                try:

                    await member.remove_roles(

                        *removable,

                        reason=(
                            f"Clan deleted: "
                            f"{clan['clan_name']}"
                        )

                    )

                except Exception:

                    pass

        # ----------------------------------------------------
        # DELETE CHANNELS
        # ----------------------------------------------------

        channel_ids = [

            clan.get(
                "member_text_id"
            ),

            clan.get(
                "general_voice_id"
            ),

            clan.get(
                "leader_text_id"
            ),

            clan.get(
                "leader_voice_id"
            ),

            clan.get(
                "category_id"
            ),

            clan.get(
                "leader_category_id"
            )

        ]

        deleted_channels = []

        for channel_id in channel_ids:

            if not channel_id:

                continue

            channel = guild.get_channel(
                channel_id
            )

            if channel is None:

                continue

            try:

                name = channel.name

                await channel.delete(

                    reason=(
                        f"Clan deleted by "
                        f"{interaction.user}"
                    )

                )

                deleted_channels.append(
                    name
                )

            except Exception as e:

                print(
                    f"❌ Failed deleting channel: {e}"
                )

        # ----------------------------------------------------
        # DELETE ROLES
        # ----------------------------------------------------

        for role in roles:

            try:

                await role.delete(

                    reason=(
                        f"Clan deleted by "
                        f"{interaction.user}"
                    )

                )

            except Exception as e:

                print(
                    f"❌ Failed deleting role: {e}"
                )

        # ----------------------------------------------------
        # DELETE DATA
        # ----------------------------------------------------

        guild_info[
            "clans"
        ].pop(
            self.clan_id,
            None
        )

        # Remove invites belonging to this clan

        for invite_id in list(

            guild_info[
                "invites"
            ].keys()

        ):

            invite = guild_info[
                "invites"
            ][
                invite_id
            ]

            if str(
                invite.get(
                    "clan_id"
                )
            ) == self.clan_id:

                guild_info[
                    "invites"
                ].pop(
                    invite_id,
                    None
                )

        await save_data()

        await interaction.edit_original_response(

            content=(

                f"🗑️ **{clan['clan_name']}** "
                "has been deleted."

            ),

            embed=None,

            view=None

        )

        await clan_log(

            guild,

            "🗑️ Clan Deleted",

            (
                f"**Clan:** {clan['clan_name']}\n"
                f"**Deleted by:** "
                f"{interaction.user.mention}"
            ),

            discord.Color.red()

        )


# ============================================================
# WARN MODAL
# ============================================================

class ModeratorWarnModal(
    ui.Modal,
    title="Warn Clan Member"
):

    member_id = ui.TextInput(

        label="Member ID",

        placeholder="Discord user ID",

        required=True,

        max_length=25

    )

    reason = ui.TextInput(

        label="Warning Reason",

        placeholder="Reason for the warning",

        required=True,

        style=discord.TextStyle.paragraph,

        max_length=500

    )

    def __init__(
        self,
        clan_id
    ):

        super().__init__()

        self.clan_id = str(
            clan_id
        )

    async def on_submit(
        self,
        interaction
    ):

        guild = interaction.guild

        if guild is None:

            return

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(

                "❌ Moderator access required.",

                ephemeral=True

            )

            return

        guild_info = get_guild_data(
            guild.id
        )

        clan = guild_info[
            "clans"
        ].get(
            self.clan_id
        )

        if clan is None:

            await interaction.response.send_message(

                "❌ Clan not found.",

                ephemeral=True

            )

            return

        try:

            member_id = int(
                self.member_id.value.strip()
            )

        except ValueError:

            await interaction.response.send_message(

                "❌ Invalid member ID.",

                ephemeral=True

            )

            return

        member = guild.get_member(
            member_id
        )

        if member is None:

            try:

                member = await guild.fetch_member(
                    member_id
                )

            except Exception:

                member = None

        if member is None:

            await interaction.response.send_message(

                "❌ Member not found.",

                ephemeral=True

            )

            return

        warnings = clan.setdefault(
            "warnings",
            {}
        )

        user_warnings = warnings.setdefault(

            str(member.id),

            []

        )

        warning = {

            "reason":
                self.reason.value.strip(),

            "moderator_id":
                interaction.user.id,

            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat()

        }

        user_warnings.append(
            warning
        )

        await save_data()

        # ----------------------------------------------------
        # DM MEMBER
        # ----------------------------------------------------

        try:

            await member.send(

                embed=discord.Embed(

                    title="⚠️ Clan Warning",

                    description=(

                        f"You have received a warning "
                        f"in **{clan['clan_name']}**.\n\n"

                        f"**Reason:**\n"
                        f"{self.reason.value.strip()}"

                    ),

                    color=discord.Color.orange()

                )

            )

        except Exception:

            pass

        await interaction.response.send_message(

            (

                f"⚠️ {member.mention} has been warned.\n\n"

                f"**Reason:** "
                f"{self.reason.value.strip()}\n\n"

                f"**Total warnings:** "
                f"{len(user_warnings)}"

            ),

            ephemeral=True

        )

        await clan_log(

            guild,

            "⚠️ Clan Member Warned",

            (

                f"**Clan:** {clan['clan_name']}\n"
                f"**Member:** {member.mention}\n"
                f"**Moderator:** {interaction.user.mention}\n"
                f"**Reason:** {self.reason.value.strip()}"

            ),

            discord.Color.orange()

        )


# ============================================================
# PERMISSION VIEW
# ============================================================

class ClanPermissionView(
    ui.View
):

    def __init__(
        self,
        clan_id
    ):

        super().__init__(
            timeout=180
        )

        self.clan_id = str(
            clan_id
        )

    async def get_clan(
        self,
        interaction
    ):

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(

                "❌ Moderator access required.",

                ephemeral=True

            )

            return None

        return get_guild_data(
            interaction.guild.id
        )[
            "clans"
        ].get(
            self.clan_id
        )

    @ui.button(

        label="Toggle Manage Members",

        style=discord.ButtonStyle.primary,

        emoji="👥"

    )
    async def toggle_members(
        self,
        interaction,
        button
    ):

        clan = await self.get_clan(
            interaction
        )

        if clan is None:

            return

        permissions = clan.setdefault(

            "permissions",

            {}

        )

        permissions[
            "moderator_manage_members"
        ] = not permissions.get(

            "moderator_manage_members",

            False

        )

        await save_data()

        await interaction.response.edit_message(

            content=(

                "🔐 Permission updated.\n\n"

                f"Manage Members: "
                f"{'✅ Enabled' if permissions['moderator_manage_members'] else '❌ Disabled'}\n"

                f"Invite Members: "
                f"{'✅ Enabled' if permissions.get('moderator_invite') else '❌ Disabled'}\n"

                f"Manage Channels: "
                f"{'✅ Enabled' if permissions.get('moderator_manage_channels') else '❌ Disabled'}"

            ),

            view=ClanPermissionView(
                self.clan_id
            )

        )

    @ui.button(

        label="Toggle Invite",

        style=discord.ButtonStyle.success,

        emoji="📨"

    )
    async def toggle_invite(
        self,
        interaction,
        button
    ):

        clan = await self.get_clan(
            interaction
        )

        if clan is None:

            return

        permissions = clan.setdefault(

            "permissions",

            {}

        )

        permissions[
            "moderator_invite"
        ] = not permissions.get(

            "moderator_invite",

            False

        )

        await save_data()

        await interaction.response.edit_message(

            content=(

                "🔐 Permission updated.\n\n"

                f"Manage Members: "
                f"{'✅ Enabled' if permissions.get('moderator_manage_members') else '❌ Disabled'}\n"

                f"Invite Members: "
                f"{'✅ Enabled' if permissions['moderator_invite'] else '❌ Disabled'}\n"

                f"Manage Channels: "
                f"{'✅ Enabled' if permissions.get('moderator_manage_channels') else '❌ Disabled'}"

            ),

            view=ClanPermissionView(
                self.clan_id
            )

        )

    @ui.button(

        label="Toggle Channels",

        style=discord.ButtonStyle.secondary,

        emoji="📁"

    )
    async def toggle_channels(
        self,
        interaction,
        button
    ):

        clan = await self.get_clan(
            interaction
        )

        if clan is None:

            return

        permissions = clan.setdefault(

            "permissions",

            {}

        )

        permissions[
            "moderator_manage_channels"
        ] = not permissions.get(

            "moderator_manage_channels",

            False

        )

        await save_data()

        await interaction.response.edit_message(

            content=(

                "🔐 Permission updated.\n\n"

                f"Manage Members: "
                f"{'✅ Enabled' if permissions.get('moderator_manage_members') else '❌ Disabled'}\n"

                f"Invite Members: "
                f"{'✅ Enabled' if permissions.get('moderator_invite') else '❌ Disabled'}\n"

                f"Manage Channels: "
                f"{'✅ Enabled' if permissions['moderator_manage_channels'] else '❌ Disabled'}"

            ),

            view=ClanPermissionView(
                self.clan_id
            )

        )


# ============================================================
# CLAN MANAGER
# ============================================================

class ClanManager(
    commands.Cog
):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

    # ========================================================
    # /CLANSETUP
    # ========================================================

    @app_commands.command(

        name="clansetup",

        description=(
            "Set the channel for the clan creation form"
        )

    )
    @app_commands.describe(

        channel=(
            "Channel where the clan creation form "
            "will be posted"
        )

    )
    async def clansetup(
        self,
        interaction,
        channel: discord.TextChannel
    ):

        guild = interaction.guild

        if guild is None:

            return

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(

                "❌ Administrator only.",

                ephemeral=True

            )

            return

        guild_info = get_guild_data(
            guild.id
        )

        guild_info[
            "approval_channel_id"
        ] = channel.id

        guild_info[
            "create_panel_message_id"
        ] = None

        await save_data()

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

                    "✅ Clan system configured!\n\n"

                    f"📋 Form channel: "
                    f"{channel.mention}"

                ),

                ephemeral=True

            )

        except Exception as e:

            await interaction.response.send_message(

                f"❌ Failed to post clan form.\n`{e}`",

                ephemeral=True

            )

    # ========================================================
    # /CLANLOG
    # ========================================================

    @app_commands.command(

        name="clanlog",

        description="Set the clan log channel"

    )
    @app_commands.describe(

        channel="Channel for clan logs"

    )
    async def clanlog(
        self,
        interaction,
        channel: discord.TextChannel
    ):

        if interaction.guild is None:

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

            f"✅ Clan log channel saved: {channel.mention}",

            ephemeral=True

        )

    # ========================================================
    # /CLANS
    # ========================================================

    @app_commands.command(

        name="clans",

        description="View and manage all server clans"

    )
    async def clans(
        self,
        interaction
    ):

        guild = interaction.guild

        if guild is None:

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

        embed = discord.Embed(

            title="🏰 Server Clans",

            description=(

                f"Total clans: **{len(clans)}**\n\n"

                "Select a clan below to manage it."

            ),

            color=discord.Color.blurple()

        )

        for index, (
            clan_id,
            clan
        ) in enumerate(
            clans[:10]
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

            embed.add_field(

                name=(

                    f"🏰 "
                    f"{clan.get('clan_name', 'Clan')}"

                ),

                value=(

                    f"👑 Owner: "
                    f"{owner.mention if owner else 'Unknown'}\n"

                    f"👥 Members: "
                    f"{len(members)}\n"

                    f"🆔 ID: `{clan_id}`"

                ),

                inline=False

            )

        await interaction.response.send_message(

            embed=embed,

            view=ModeratorClanSelectView(
                clans
            ),

            ephemeral=True

        )

    # ========================================================
    # INITIALIZE
    # ========================================================

    async def initialize_guild(
        self,
        guild
    ):

        guild_info = get_guild_data(
            guild.id
        )

        # ----------------------------------------------------
        # RESTORE CREATE PANEL
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

                message = None

                if message_id:

                    try:

                        message = await channel.fetch_message(
                            message_id
                        )

                    except Exception:

                        message = None

                if message:

                    try:

                        await message.edit(

                            view=ClanCreatePanelView()

                        )

                    except Exception:

                        pass

                else:

                    try:

                        embed = discord.Embed(

                            title="🏰 Create Your Clan",

                            description=(

                                "Want to create your own clan?\n\n"

                                "Click the button below and submit "
                                "your clan application."

                            ),

                            color=discord.Color.blurple()

                        )

                        message = await channel.send(

                            embed=embed,

                            view=ClanCreatePanelView()

                        )

                        guild_info[
                            "create_panel_message_id"
                        ] = message.id

                        await save_data()

                    except Exception as e:

                        print(
                            f"❌ Failed restoring clan form: {e}"
                        )

        # ----------------------------------------------------
        # RESTORE PENDING APPLICATION BUTTONS
        # ----------------------------------------------------

        for application_id in list(

            guild_info[
                "pending"
            ].keys()

        ):

            try:

                self.bot.add_view(

                    ClanApprovalView(

                        application_id

                    )

                )

            except Exception as e:

                print(
                    f"❌ Failed restoring application view: {e}"
                )

        # ----------------------------------------------------
        # RESTORE INVITES
        # ----------------------------------------------------

        for invite_id in list(

            guild_info[
                "invites"
            ].keys()

        ):

            try:

                self.bot.add_view(

                    ClanInviteView(

                        invite_id

                    )

                )

            except Exception as e:

                print(
                    f"❌ Failed restoring invite view: {e}"
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

                    f"❌ Failed restoring clan "
                    f"{clan_id}: {e}"

                )

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

                    f"❌ Clan initialization "
                    f"failed for {guild.name}: {e}"

                )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot
):

    cog = ClanManager(
        bot
    )

    await bot.add_cog(
        cog
    )

    # --------------------------------------------------------
    # CREATE CLAN PANEL
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
        "✅ Updated Clan System loaded successfully."
    )

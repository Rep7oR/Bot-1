import discord
from discord.ext import commands
from discord import app_commands, ui

import asyncio
import json
import os
from typing import Optional


# ============================================================
# CONFIG
# ============================================================

MODERATOR_ROLE_NAME = "MODERATOR"

DATA_FILE = "clan_data.json"

data_lock = asyncio.Lock()


# ============================================================
# DEFAULT DATA
# ============================================================

def default_guild_data():
    return {
        "application_channel_id": None,
        "log_channel_id": None,
        "pending": {},
        "clans": {}
    }


def default_data():
    return {
        "guilds": {}
    }


# ============================================================
# SAFE DATA NORMALIZATION
# ============================================================

def normalize_data(data):

    # This is the important fix.
    # If something returns a string/list/etc.,
    # never call .setdefault() on it.

    if not isinstance(data, dict):
        data = default_data()

    guilds = data.get("guilds")

    if not isinstance(guilds, dict):
        data["guilds"] = {}
        guilds = data["guilds"]

    for guild_id in list(guilds.keys()):

        guild_data = guilds[guild_id]

        if not isinstance(guild_data, dict):
            guilds[guild_id] = default_guild_data()
            continue

        if not isinstance(
            guild_data.get("pending"),
            dict
        ):
            guild_data["pending"] = {}

        if not isinstance(
            guild_data.get("clans"),
            dict
        ):
            guild_data["clans"] = {}

        guild_data.setdefault(
            "application_channel_id",
            None
        )

        guild_data.setdefault(
            "log_channel_id",
            None
        )

    return data


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    if not os.path.exists(DATA_FILE):
        return default_data()

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return normalize_data(data)

    except Exception as error:

        print(
            f"[CLAN] Data loading failed: {error}"
        )

        return default_data()


clan_data = load_data()


# ============================================================
# SAVE DATA
# ============================================================

async def save_data():

    async with data_lock:

        try:

            global clan_data

            clan_data = normalize_data(
                clan_data
            )

            temporary_file = DATA_FILE + ".tmp"

            with open(
                temporary_file,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    clan_data,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

            os.replace(
                temporary_file,
                DATA_FILE
            )

        except Exception as error:

            print(
                f"[CLAN] Data saving failed: {error}"
            )


# ============================================================
# GET GUILD DATA
# ============================================================

def get_guild_data(
    guild_id: int
):

    global clan_data

    clan_data = normalize_data(
        clan_data
    )

    guilds = clan_data["guilds"]

    guild_id = str(guild_id)

    if guild_id not in guilds:

        guilds[guild_id] = (
            default_guild_data()
        )

    if not isinstance(
        guilds[guild_id],
        dict
    ):

        guilds[guild_id] = (
            default_guild_data()
        )

    guild_data = guilds[guild_id]

    if not isinstance(
        guild_data.get("pending"),
        dict
    ):

        guild_data["pending"] = {}

    if not isinstance(
        guild_data.get("clans"),
        dict
    ):

        guild_data["clans"] = {}

    return guild_data


# ============================================================
# DISCORD HELPERS
# ============================================================

def get_channel(
    guild: discord.Guild,
    channel_id
):

    if not channel_id:
        return None

    try:
        return guild.get_channel(
            int(channel_id)
        )
    except Exception:
        return None


def get_role(
    guild: discord.Guild,
    role_id
):

    if not role_id:
        return None

    try:
        return guild.get_role(
            int(role_id)
        )
    except Exception:
        return None


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

    return bool(
        role and role in member.roles
    )


# ============================================================
# FIND CLAN
# ============================================================

def find_clan(
    guild: discord.Guild,
    clan_id: str
):

    data = get_guild_data(
        guild.id
    )

    return data["clans"].get(
        str(clan_id)
    )


def find_member_clan(
    guild: discord.Guild,
    member: discord.Member
):

    data = get_guild_data(
        guild.id
    )

    for clan_id, clan in data[
        "clans"
    ].items():

        if int(
            clan.get("owner_id", 0)
        ) == member.id:

            return clan_id, clan

        if member.id in [
            int(x)
            for x in clan.get(
                "leaders",
                []
            )
        ]:

            return clan_id, clan

        member_role = get_role(
            guild,
            clan.get(
                "member_role_id"
            )
        )

        moderator_role = get_role(
            guild,
            clan.get(
                "clan_moderator_role_id"
            )
        )

        leader_role = get_role(
            guild,
            clan.get(
                "leader_role_id"
            )
        )

        if (
            member_role
            and member_role in member.roles
        ):
            return clan_id, clan

        if (
            moderator_role
            and moderator_role in member.roles
        ):
            return clan_id, clan

        if (
            leader_role
            and leader_role in member.roles
        ):
            return clan_id, clan

    return None, None


# ============================================================
# LEADER CHECK
# ============================================================

def is_clan_leader(
    member: discord.Member,
    clan: dict
):

    if member.guild_permissions.administrator:
        return True

    if member.id == int(
        clan.get("owner_id", 0)
    ):
        return True

    if member.id in [
        int(x)
        for x in clan.get(
            "leaders",
            []
        )
    ]:
        return True

    role = get_role(
        member.guild,
        clan.get(
            "leader_role_id"
        )
    )

    return bool(
        role and role in member.roles
    )


# ============================================================
# CLAN MODERATOR CHECK
# ============================================================

def can_manage_members(
    member: discord.Member,
    clan: dict
):

    if is_clan_leader(
        member,
        clan
    ):
        return True

    role = get_role(
        member.guild,
        clan.get(
            "clan_moderator_role_id"
        )
    )

    return bool(
        role and role in member.roles
    )


# ============================================================
# LOG
# ============================================================

async def clan_log(
    guild,
    title,
    description,
    color=discord.Color.blurple()
):

    data = get_guild_data(
        guild.id
    )

    channel = get_channel(
        guild,
        data.get(
            "log_channel_id"
        )
    )

    if not channel:
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

    except Exception:
        pass


# ============================================================
# APPLICATION FORM
# ============================================================

class ClanApplicationModal(
    ui.Modal,
    title="Create Clan Application"
):

    clan_name = ui.TextInput(
        label="Clan Name",
        placeholder="Shadow Wolves",
        max_length=50,
        required=True
    )

    category_name = ui.TextInput(
        label="Category Name",
        placeholder="SHADOW WOLVES",
        max_length=50,
        required=True
    )

    member_role_name = ui.TextInput(
        label="Member Role",
        placeholder="Shadow Wolves Member",
        max_length=50,
        required=True
    )

    leader_role_name = ui.TextInput(
        label="Leader Role",
        placeholder="Shadow Wolves Leader",
        max_length=50,
        required=True
    )

    async def on_submit(
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

        data = get_guild_data(
            guild.id
        )

        approval_channel = get_channel(
            guild,
            data.get(
                "application_channel_id"
            )
        )

        if not approval_channel:

            await interaction.response.send_message(
                "❌ The clan application channel has not been configured.",
                ephemeral=True
            )

            return

        clan_name = (
            self.clan_name.value
            .strip()
        )

        category_name = (
            self.category_name.value
            .strip()
        )

        member_role_name = (
            self.member_role_name.value
            .strip()
        )

        leader_role_name = (
            self.leader_role_name.value
            .strip()
        )

        # Duplicate check
        for clan in data[
            "clans"
        ].values():

            if str(
                clan.get(
                    "clan_name",
                    ""
                )
            ).lower() == clan_name.lower():

                await interaction.response.send_message(
                    "❌ A clan with this name already exists.",
                    ephemeral=True
                )

                return

        application_id = str(
            interaction.id
        )

        data["pending"][
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

        embed = discord.Embed(
            title="⚔️ New Clan Application",
            description=(
                "A member has submitted "
                "a clan application."
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
            name="Applicant",
            value=(
                f"{interaction.user.mention}\n"
                f"`{interaction.user.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="Status",
            value="⏳ Waiting for moderator",
            inline=False
        )

        try:

            message = await approval_channel.send(
                embed=embed,
                view=ClanApprovalView(
                    application_id
                )
            )

            data["pending"][
                application_id
            ][
                "approval_message_id"
            ] = message.id

            await save_data()

        except Exception as error:

            data["pending"].pop(
                application_id,
                None
            )

            await save_data()

            await interaction.response.send_message(
                f"❌ Failed to send application.\n`{error}`",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "✅ Your clan application has been sent to the moderators.",
            ephemeral=True
        )


# ============================================================
# APPLICATION FORM VIEW
# ============================================================

class ClanApplicationView(
    ui.View
):

    def __init__(self):
        super().__init__(
            timeout=None
        )

    @ui.button(
        label="Apply for a Clan",
        style=discord.ButtonStyle.success,
        emoji="⚔️",
        custom_id="clan_apply_button"
    )
    async def apply(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(
            ClanApplicationModal()
        )


# ============================================================
# DELETE APPLICATION MESSAGE
# ============================================================

async def delete_application_message(
    guild,
    application
):

    data = get_guild_data(
        guild.id
    )

    channel = get_channel(
        guild,
        data.get(
            "application_channel_id"
        )
    )

    message_id = application.get(
        "approval_message_id"
    )

    if not channel or not message_id:
        return

    try:

        message = await channel.fetch_message(
            int(message_id)
        )

        await message.delete()

    except Exception:
        pass


# ============================================================
# APPLICATION APPROVAL VIEW
# ============================================================

class ClanApprovalView(
    ui.View
):

    def __init__(
        self,
        application_id
    ):

        super().__init__(
            timeout=None
        )

        self.application_id = str(
            application_id
        )

    async def interaction_check(
        self,
        interaction
    ):

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ You need the MODERATOR role.",
                ephemeral=True
            )

            return False

        return True

    @ui.button(
        label="Approve",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="clan_approve_button"
    )
    async def approve(
        self,
        interaction,
        button
    ):

        guild = interaction.guild

        data = get_guild_data(
            guild.id
        )

        application = data[
            "pending"
        ].get(
            self.application_id
        )

        if not application:

            await interaction.response.send_message(
                "❌ This application no longer exists.",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        try:

            # --------------------------------------------
            # CREATE ROLES
            # --------------------------------------------

            member_role = await guild.create_role(
                name=application[
                    "member_role_name"
                ],
                reason="Clan member role"
            )

            leader_role = await guild.create_role(
                name=application[
                    "leader_role_name"
                ],
                reason="Clan leader role"
            )

            moderator_role = await guild.create_role(
                name=(
                    application[
                        "clan_name"
                    ]
                    + " Moderator"
                ),
                reason="Clan moderator role"
            )

            # --------------------------------------------
            # CREATE CATEGORY
            # --------------------------------------------

            category = await guild.create_category(
                name=application[
                    "category_name"
                ],
                reason="Clan category"
            )

            everyone = guild.default_role

            # Everyone cannot see clan
            await category.set_permissions(
                everyone,
                view_channel=False
            )

            # Members
            await category.set_permissions(
                member_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                connect=True,
                speak=True,
                stream=True
            )

            # Clan moderators
            await category.set_permissions(
                moderator_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                manage_threads=True,
                connect=True,
                speak=True,
                move_members=True,
                mute_members=True,
                deafen_members=True
            )

            # Leaders have full category management
            await category.set_permissions(
                leader_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_permissions=True,
                manage_messages=True,
                manage_threads=True,
                create_public_threads=True,
                create_private_threads=True,
                connect=True,
                speak=True,
                stream=True,
                move_members=True,
                mute_members=True,
                deafen_members=True
            )

            # --------------------------------------------
            # MEMBER CHAT
            # --------------------------------------------

            clan_chat = await guild.create_text_channel(
                name="clan-chat",
                category=category,
                reason="Clan member chat"
            )

            await clan_chat.set_permissions(
                everyone,
                view_channel=False
            )

            await clan_chat.set_permissions(
                member_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

            await clan_chat.set_permissions(
                moderator_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True
            )

            await clan_chat.set_permissions(
                leader_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_permissions=True,
                manage_messages=True,
                manage_threads=True
            )

            # --------------------------------------------
            # GENERAL VOICE
            # --------------------------------------------

            general_voice = await guild.create_voice_channel(
                name="general-voice",
                category=category,
                reason="Clan voice"
            )

            await general_voice.set_permissions(
                everyone,
                view_channel=False,
                connect=False
            )

            await general_voice.set_permissions(
                member_role,
                view_channel=True,
                connect=True,
                speak=True,
                stream=True
            )

            await general_voice.set_permissions(
                moderator_role,
                view_channel=True,
                connect=True,
                speak=True,
                move_members=True,
                mute_members=True,
                deafen_members=True
            )

            await general_voice.set_permissions(
                leader_role,
                view_channel=True,
                connect=True,
                speak=True,
                stream=True,
                move_members=True,
                mute_members=True,
                deafen_members=True,
                manage_channels=True,
                manage_permissions=True
            )

            # --------------------------------------------
            # LEADER CATEGORY
            # --------------------------------------------

            leader_category = await guild.create_category(
                name=(
                    application[
                        "category_name"
                    ]
                    + " • LEADERS"
                ),
                reason="Clan leader category"
            )

            await leader_category.set_permissions(
                everyone,
                view_channel=False
            )

            await leader_category.set_permissions(
                leader_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_permissions=True,
                manage_messages=True,
                manage_threads=True,
                connect=True,
                speak=True,
                move_members=True,
                mute_members=True,
                deafen_members=True
            )

            # --------------------------------------------
            # LEADER MANAGEMENT CHANNEL
            # --------------------------------------------

            management_channel = await guild.create_text_channel(
                name="clan-management",
                category=leader_category,
                reason="Clan leader management"
            )

            await management_channel.set_permissions(
                everyone,
                view_channel=False
            )

            await management_channel.set_permissions(
                leader_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_permissions=True,
                manage_messages=True
            )

            # --------------------------------------------
            # LEADER VOICE
            # --------------------------------------------

            leader_voice = await guild.create_voice_channel(
                name="leader-voice",
                category=leader_category,
                reason="Clan leader voice"
            )

            await leader_voice.set_permissions(
                everyone,
                view_channel=False,
                connect=False
            )

            await leader_voice.set_permissions(
                leader_role,
                view_channel=True,
                connect=True,
                speak=True,
                stream=True,
                move_members=True,
                mute_members=True,
                deafen_members=True,
                manage_channels=True,
                manage_permissions=True
            )

            # --------------------------------------------
            # CREATOR
            # --------------------------------------------

            owner = guild.get_member(
                int(
                    application[
                        "creator_id"
                    ]
                )
            )

            if owner:

                await owner.add_roles(
                    leader_role,
                    reason="Clan owner"
                )

            # --------------------------------------------
            # SAVE CLAN
            # --------------------------------------------

            clan_id = str(
                category.id
            )

            data["clans"][
                clan_id
            ] = {

                "clan_id":
                    clan_id,

                "clan_name":
                    application[
                        "clan_name"
                    ],

                "owner_id":
                    int(
                        application[
                            "creator_id"
                        ]
                    ),

                "leaders":
                    [
                        int(
                            application[
                                "creator_id"
                            ]
                        )
                    ],

                "members":
                    [
                        int(
                            application[
                                "creator_id"
                            ]
                        )
                    ],

                "category_id":
                    category.id,

                "leader_category_id":
                    leader_category.id,

                "member_role_id":
                    member_role.id,

                "leader_role_id":
                    leader_role.id,

                "clan_moderator_role_id":
                    moderator_role.id,

                "member_text_id":
                    clan_chat.id,

                "general_voice_id":
                    general_voice.id,

                "leader_channel_id":
                    management_channel.id,

                "leader_voice_id":
                    leader_voice.id,

                "warnings":
                    {},

                "banned_members":
                    [],

                "created_at":
                    discord.utils.utcnow().isoformat()
            }

            # Remove pending
            data["pending"].pop(
                self.application_id,
                None
            )

            await save_data()

            # --------------------------------------------
            # DELETE APPLICATION
            # --------------------------------------------

            await delete_application_message(
                guild,
                application
            )

            # --------------------------------------------
            # WELCOME
            # --------------------------------------------

            await clan_chat.send(
                embed=discord.Embed(
                    title=(
                        "⚔️ "
                        + application[
                            "clan_name"
                        ]
                    ),
                    description=(
                        f"Welcome to "
                        f"**{application['clan_name']}**!\n\n"
                        f"👑 Owner: "
                        f"{owner.mention if owner else 'Unknown'}\n\n"
                        "Use this channel for clan communication."
                    ),
                    color=discord.Color.green()
                )
            )

            # --------------------------------------------
            # LEADER MANAGEMENT PANEL
            # --------------------------------------------

            if owner:

                await send_leader_panel(
                    guild,
                    data["clans"][clan_id],
                    management_channel
                )

            await interaction.followup.send(
                f"✅ **{application['clan_name']}** has been approved."
            )

            await clan_log(
                guild,
                "Clan Approved",
                (
                    f"**{application['clan_name']}** "
                    f"was approved by "
                    f"{interaction.user.mention}."
                ),
                discord.Color.green()
            )

        except Exception as error:

            await interaction.followup.send(
                f"❌ Clan creation failed:\n`{error}`",
                ephemeral=True
            )

    @ui.button(
        label="Reject",
        style=discord.ButtonStyle.danger,
        emoji="❌",
        custom_id="clan_reject_button"
    )
    async def reject(
        self,
        interaction,
        button
    ):

        guild = interaction.guild

        data = get_guild_data(
            guild.id
        )

        application = data[
            "pending"
        ].get(
            self.application_id
        )

        if not application:

            await interaction.response.send_message(
                "❌ Application no longer exists.",
                ephemeral=True
            )

            return

        data["pending"].pop(
            self.application_id,
            None
        )

        await save_data()

        await delete_application_message(
            guild,
            application
        )

        await interaction.response.send_message(
            f"❌ **{application['clan_name']}** was rejected.",
            ephemeral=True
        )

        await clan_log(
            guild,
            "Clan Application Rejected",
            (
                f"**{application['clan_name']}** "
                f"was rejected by "
                f"{interaction.user.mention}."
            ),
            discord.Color.red()
        )


# ============================================================
# LEADER PANEL EMBED
# ============================================================

async def build_leader_embed(
    guild,
    clan
):

    members = []

    for member_id in clan.get(
        "members",
        []
    ):

        member = guild.get_member(
            int(member_id)
        )

        if member:
            members.append(member)

    lines = []

    for member in members:

        role = "Member"

        leader_role = get_role(
            guild,
            clan.get(
                "leader_role_id"
            )
        )

        moderator_role = get_role(
            guild,
            clan.get(
                "clan_moderator_role_id"
            )
        )

        if (
            leader_role
            and leader_role in member.roles
        ):

            role = "Leader"

        elif (
            moderator_role
            and moderator_role in member.roles
        ):

            role = "Clan Moderator"

        status = (
            "🟢"
            if member.status != discord.Status.offline
            else "⚫"
        )

        lines.append(
            f"{status} {member.mention} — **{role}**"
        )

    if not lines:
        lines = [
            "No members recorded."
        ]

    embed = discord.Embed(
        title=(
            f"⚔️ {clan['clan_name']} "
            f"— Management"
        ),
        description="\n".join(
            lines[:50]
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👥 Total Members",
        value=str(
            len(
                clan.get(
                    "members",
                    []
                )
            )
        ),
        inline=True
    )

    embed.add_field(
        name="👑 Owner",
        value=(
            f"<@{clan['owner_id']}>"
        ),
        inline=True
    )

    embed.add_field(
        name="📁 Clan Category",
        value=(
            f"<#{clan['category_id']}>"
        ),
        inline=True
    )

    embed.add_field(
        name="💬 Clan Chat",
        value=(
            f"<#{clan['member_text_id']}>"
        ),
        inline=True
    )

    embed.add_field(
        name="🎙️ Voice",
        value=(
            f"<#{clan['general_voice_id']}>"
        ),
        inline=True
    )

    embed.add_field(
        name="📋 Management",
        value=(
            f"<#{clan['leader_channel_id']}>"
        ),
        inline=True
    )

    embed.set_footer(
        text="Clan Management System"
    )

    return embed


# ============================================================
# LEADER MEMBER SELECT
# ============================================================

class ClanMemberSelect(
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

        for member in members[:25]:

            options.append(
                discord.SelectOption(
                    label=member.display_name[
                        :100
                    ],
                    value=str(
                        member.id
                    )
                )
            )

        if not options:

            options.append(
                discord.SelectOption(
                    label="No members",
                    value="0"
                )
            )

        super().__init__(
            placeholder="Select a member",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(
        self,
        interaction
    ):

        clan = find_clan(
            interaction.guild,
            self.clan_id
        )

        if not clan:

            await interaction.response.send_message(
                "❌ Clan not found.",
                ephemeral=True
            )

            return

        if not can_manage_members(
            interaction.user,
            clan
        ):

            await interaction.response.send_message(
                "❌ You cannot manage clan members.",
                ephemeral=True
            )

            return

        member_id = int(
            self.values[0]
        )

        member = interaction.guild.get_member(
            member_id
        )

        if not member:

            await interaction.response.send_message(
                "❌ Member is no longer in the server.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            f"Managing **{member.display_name}**",
            view=MemberActionsView(
                self.clan_id,
                member.id
            ),
            ephemeral=True
        )


# ============================================================
# MEMBER ACTIONS
# ============================================================

class MemberActionsView(
    ui.View
):

    def __init__(
        self,
        clan_id,
        member_id
    ):

        super().__init__(
            timeout=180
        )

        self.clan_id = str(
            clan_id
        )

        self.member_id = int(
            member_id
        )

    def get_clan(self, interaction):

        return find_clan(
            interaction.guild,
            self.clan_id
        )

    @ui.button(
        label="Warn",
        style=discord.ButtonStyle.secondary,
        emoji="⚠️"
    )
    async def warn(
        self,
        interaction,
        button
    ):

        clan = self.get_clan(
            interaction
        )

        if not clan or not can_manage_members(
            interaction.user,
            clan
        ):

            await interaction.response.send_message(
                "❌ You cannot manage this member.",
                ephemeral=True
            )

            return

        warnings = clan.setdefault(
            "warnings",
            {}
        )

        key = str(
            self.member_id
        )

        warnings[key] = (
            int(
                warnings.get(
                    key,
                    0
                )
            )
            + 1
        )

        await save_data()

        member = interaction.guild.get_member(
            self.member_id
        )

        await interaction.response.send_message(
            (
                f"⚠️ {member.mention if member else 'Member'} "
                f"has been warned.\n"
                f"Warnings: **{warnings[key]}**"
            ),
            ephemeral=True
        )

    @ui.button(
        label="Kick",
        style=discord.ButtonStyle.danger,
        emoji="👢"
    )
    async def kick(
        self,
        interaction,
        button
    ):

        clan = self.get_clan(
            interaction
        )

        if not clan or not is_clan_leader(
            interaction.user,
            clan
        ):

            await interaction.response.send_message(
                "❌ Only clan leaders can kick members.",
                ephemeral=True
            )

            return

        if self.member_id == int(
            clan["owner_id"]
        ):

            await interaction.response.send_message(
                "❌ The clan owner cannot be kicked.",
                ephemeral=True
            )

            return

        member = interaction.guild.get_member(
            self.member_id
        )

        if not member:

            await interaction.response.send_message(
                "❌ Member not found.",
                ephemeral=True
            )

            return

        roles = [

            get_role(
                interaction.guild,
                clan.get(
                    "member_role_id"
                )
            ),

            get_role(
                interaction.guild,
                clan.get(
                    "clan_moderator_role_id"
                )
            ),

            get_role(
                interaction.guild,
                clan.get(
                    "leader_role_id"
                )
            )
        ]

        try:

            for role in roles:

                if (
                    role
                    and role in member.roles
                ):

                    await member.remove_roles(
                        role,
                        reason="Kicked from clan"
                    )

        except Exception as error:

            await interaction.response.send_message(
                f"❌ Could not remove roles: `{error}`",
                ephemeral=True
            )

            return

        clan["members"] = [
            int(x)
            for x in clan.get(
                "members",
                []
            )
            if int(x) != member.id
        ]

        clan["leaders"] = [
            int(x)
            for x in clan.get(
                "leaders",
                []
            )
            if int(x) != member.id
        ]

        await save_data()

        await interaction.response.send_message(
            f"👢 {member.mention} was removed from the clan.",
            ephemeral=True
        )

    @ui.button(
        label="Clan Member",
        style=discord.ButtonStyle.success,
        emoji="👤"
    )
    async def make_member(
        self,
        interaction,
        button
    ):

        clan = self.get_clan(
            interaction
        )

        if not clan or not is_clan_leader(
            interaction.user,
            clan
        ):

            await interaction.response.send_message(
                "❌ Only leaders can change clan roles.",
                ephemeral=True
            )

            return

        member = interaction.guild.get_member(
            self.member_id
        )

        if not member:
            return

        member_role = get_role(
            interaction.guild,
            clan.get(
                "member_role_id"
            )
        )

        moderator_role = get_role(
            interaction.guild,
            clan.get(
                "clan_moderator_role_id"
            )
        )

        leader_role = get_role(
            interaction.guild,
            clan.get(
                "leader_role_id"
            )
        )

        try:

            if leader_role:
                await member.remove_roles(
                    leader_role
                )

            if moderator_role:
                await member.remove_roles(
                    moderator_role
                )

            if member_role:
                await member.add_roles(
                    member_role
                )

        except Exception as error:

            await interaction.response.send_message(
                f"❌ Role update failed: `{error}`",
                ephemeral=True
            )

            return

        clan["leaders"] = [
            int(x)
            for x in clan.get(
                "leaders",
                []
            )
            if int(x) != member.id
        ]

        if member.id not in [
            int(x)
            for x in clan.get(
                "members",
                []
            )
        ]:

            clan.setdefault(
                "members",
                []
            ).append(
                member.id
            )

        await save_data()

        await interaction.response.send_message(
            f"👤 {member.mention} is now a Clan Member.",
            ephemeral=True
        )

    @ui.button(
        label="Clan Moderator",
        style=discord.ButtonStyle.primary,
        emoji="🛡️"
    )
    async def make_moderator(
        self,
        interaction,
        button
    ):

        clan = self.get_clan(
            interaction
        )

        if not clan or not is_clan_leader(
            interaction.user,
            clan
        ):

            await interaction.response.send_message(
                "❌ Only leaders can change clan roles.",
                ephemeral=True
            )

            return

        member = interaction.guild.get_member(
            self.member_id
        )

        if not member:
            return

        member_role = get_role(
            interaction.guild,
            clan.get(
                "member_role_id"
            )
        )

        moderator_role = get_role(
            interaction.guild,
            clan.get(
                "clan_moderator_role_id"
            )
        )

        leader_role = get_role(
            interaction.guild,
            clan.get(
                "leader_role_id"
            )
        )

        try:

            if leader_role:
                await member.remove_roles(
                    leader_role
                )

            if member_role:
                await member.add_roles(
                    member_role
                )

            if moderator_role:
                await member.add_roles(
                    moderator_role
                )

        except Exception as error:

            await interaction.response.send_message(
                f"❌ Role update failed: `{error}`",
                ephemeral=True
            )

            return

        if member.id not in [
            int(x)
            for x in clan.get(
                "members",
                []
            )
        ]:

            clan.setdefault(
                "members",
                []
            ).append(
                member.id
            )

        clan["leaders"] = [
            int(x)
            for x in clan.get(
                "leaders",
                []
            )
            if int(x) != member.id
        ]

        await save_data()

        await interaction.response.send_message(
            f"🛡️ {member.mention} is now a Clan Moderator.",
            ephemeral=True
        )


# ============================================================
# LEADER MANAGEMENT VIEW
# ============================================================

class LeaderManagementView(
    ui.View
):

    def __init__(
        self,
        clan_id
    ):

        super().__init__(
            timeout=None
        )

        self.clan_id = str(
            clan_id
        )

    @ui.button(
        label="Refresh",
        style=discord.ButtonStyle.secondary,
        emoji="🔄",
        custom_id="clan_management_refresh"
    )
    async def refresh(
        self,
        interaction,
        button
    ):

        clan = find_clan(
            interaction.guild,
            self.clan_id
        )

        if not clan or not is_clan_leader(
            interaction.user,
            clan
        ):

            await interaction.response.send_message(
                "❌ You cannot manage this clan.",
                ephemeral=True
            )

            return

        embed = await build_leader_embed(
            interaction.guild,
            clan
        )

        await interaction.message.edit(
            embed=embed,
            view=LeaderManagementView(
                self.clan_id
            )
        )

        await interaction.response.send_message(
            "🔄 Member list refreshed.",
            ephemeral=True
        )

    @ui.button(
        label="Manage Member",
        style=discord.ButtonStyle.primary,
        emoji="👥",
        custom_id="clan_management_member"
    )
    async def manage(
        self,
        interaction,
        button
    ):

        clan = find_clan(
            interaction.guild,
            self.clan_id
        )

        if not clan or not can_manage_members(
            interaction.user,
            clan
        ):

            await interaction.response.send_message(
                "❌ You cannot manage members.",
                ephemeral=True
            )

            return

        members = []

        for member_id in clan.get(
            "members",
            []
        ):

            member = interaction.guild.get_member(
                int(member_id)
            )

            if member:
                members.append(
                    member
                )

        view = ui.View(
            timeout=180
        )

        view.add_item(
            ClanMemberSelect(
                self.clan_id,
                members
            )
        )

        await interaction.response.send_message(
            "Select a clan member:",
            view=view,
            ephemeral=True
        )

    @ui.button(
        label="Invite Member",
        style=discord.ButtonStyle.success,
        emoji="📨",
        custom_id="clan_management_invite"
    )
    async def invite(
        self,
        interaction,
        button
    ):

        clan = find_clan(
            interaction.guild,
            self.clan_id
        )

        if not clan or not is_clan_leader(
            interaction.user,
            clan
        ):

            await interaction.response.send_message(
                "❌ Only clan leaders can invite.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "📨 Create a clan invitation:",
            view=ClanInviteCreateView(
                self.clan_id
            ),
            ephemeral=True
        )

    @ui.button(
        label="Create Channel",
        style=discord.ButtonStyle.success,
        emoji="➕",
        custom_id="clan_management_channel"
    )
    async def create_channel(
        self,
        interaction,
        button
    ):

        clan = find_clan(
            interaction.guild,
            self.clan_id
        )

        if not clan or not is_clan_leader(
            interaction.user,
            clan
        ):

            await interaction.response.send_message(
                "❌ Only clan leaders can create channels.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            ClanChannelModal(
                self.clan_id
            )
        )


# ============================================================
# INVITE CREATION
# ============================================================

class ClanInviteCreateView(
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

    @ui.button(
        label="Create Invite",
        style=discord.ButtonStyle.success,
        emoji="📨"
    )
    async def create(
        self,
        interaction,
        button
    ):

        clan = find_clan(
            interaction.guild,
            self.clan_id
        )

        if not clan or not is_clan_leader(
            interaction.user,
            clan
        ):

            await interaction.response.send_message(
                "❌ You cannot invite members.",
                ephemeral=True
            )

            return

        channel = get_channel(
            interaction.guild,
            clan.get(
                "member_text_id"
            )
        )

        if not channel:

            await interaction.response.send_message(
                "❌ Clan chat channel not found.",
                ephemeral=True
            )

            return

        try:

            invite = await channel.create_invite(
                max_age=86400,
                max_uses=1,
                unique=True,
                reason="Clan invitation"
            )

        except Exception as error:

            await interaction.response.send_message(
                f"❌ Could not create invite: `{error}`",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            (
                f"📨 **{clan['clan_name']} invitation**\n\n"
                f"Send this to the member:\n"
                f"{invite.url}\n\n"
                "After joining the server, "
                "the member can use the **Join Clan** button."
            ),
            ephemeral=True
        )


# ============================================================
# INVITATION JOIN VIEW
# ============================================================

class ClanJoinView(
    ui.View
):

    def __init__(
        self,
        clan_id
    ):

        super().__init__(
            timeout=None
        )

        self.clan_id = str(
            clan_id
        )

    @ui.button(
        label="Join Clan",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="clan_join_button"
    )
    async def join(
        self,
        interaction,
        button
    ):

        clan = find_clan(
            interaction.guild,
            self.clan_id
        )

        if not clan:

            await interaction.response.send_message(
                "❌ Clan no longer exists.",
                ephemeral=True
            )

            return

        banned = [
            int(x)
            for x in clan.get(
                "banned_members",
                []
            )
        ]

        if interaction.user.id in banned:

            await interaction.response.send_message(
                "❌ You are banned from this clan.",
                ephemeral=True
            )

            return

        member_role = get_role(
            interaction.guild,
            clan.get(
                "member_role_id"
            )
        )

        if not member_role:

            await interaction.response.send_message(
                "❌ Clan member role no longer exists.",
                ephemeral=True
            )

            return

        try:

            await interaction.user.add_roles(
                member_role,
                reason="Accepted clan invitation"
            )

        except Exception as error:

            await interaction.response.send_message(
                f"❌ Could not give clan role: `{error}`",
                ephemeral=True
            )

            return

        members = [
            int(x)
            for x in clan.get(
                "members",
                []
            )
        ]

        if interaction.user.id not in members:

            members.append(
                interaction.user.id
            )

        clan["members"] = members

        await save_data()

        await interaction.response.send_message(
            (
                f"✅ You joined "
                f"**{clan['clan_name']}**!"
            ),
            ephemeral=True
        )


# ============================================================
# CHANNEL CREATION
# ============================================================

class ClanChannelModal(
    ui.Modal,
    title="Create Clan Channel"
):

    channel_name = ui.TextInput(
        label="Channel Name",
        placeholder="team-room",
        max_length=90,
        required=True
    )

    channel_type = ui.TextInput(
        label="Channel Type",
        placeholder="text or voice",
        max_length=10,
        required=True
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

        clan = find_clan(
            interaction.guild,
            self.clan_id
        )

        if not clan or not is_clan_leader(
            interaction.user,
            clan
        ):

            await interaction.response.send_message(
                "❌ Only clan leaders can create channels.",
                ephemeral=True
            )

            return

        category = get_channel(
            interaction.guild,
            clan.get(
                "category_id"
            )
        )

        if not isinstance(
            category,
            discord.CategoryChannel
        ):

            await interaction.response.send_message(
                "❌ Clan category not found.",
                ephemeral=True
            )

            return

        name = (
            self.channel_name.value
            .strip()
            .lower()
            .replace(" ", "-")
        )

        channel_type = (
            self.channel_type.value
            .strip()
            .lower()
        )

        try:

            if channel_type in (
                "voice",
                "vc"
            ):

                channel = await interaction.guild.create_voice_channel(
                    name=name,
                    category=category,
                    reason="Clan leader created voice channel"
                )

            elif channel_type in (
                "text",
                "chat"
            ):

                channel = await interaction.guild.create_text_channel(
                    name=name,
                    category=category,
                    reason="Clan leader created text channel"
                )

            else:

                await interaction.response.send_message(
                    "❌ Type must be `text` or `voice`.",
                    ephemeral=True
                )

                return

            everyone = interaction.guild.default_role

            member_role = get_role(
                interaction.guild,
                clan.get(
                    "member_role_id"
                )
            )

            moderator_role = get_role(
                interaction.guild,
                clan.get(
                    "clan_moderator_role_id"
                )
            )

            leader_role = get_role(
                interaction.guild,
                clan.get(
                    "leader_role_id"
                )
            )

            await channel.set_permissions(
                everyone,
                view_channel=False
            )

            if member_role:

                if isinstance(
                    channel,
                    discord.TextChannel
                ):

                    await channel.set_permissions(
                        member_role,
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True
                    )

                else:

                    await channel.set_permissions(
                        member_role,
                        view_channel=True,
                        connect=True,
                        speak=True
                    )

            if moderator_role:

                if isinstance(
                    channel,
                    discord.TextChannel
                ):

                    await channel.set_permissions(
                        moderator_role,
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_messages=True
                    )

                else:

                    await channel.set_permissions(
                        moderator_role,
                        view_channel=True,
                        connect=True,
                        speak=True,
                        move_members=True,
                        mute_members=True,
                        deafen_members=True
                    )

            if leader_role:

                await channel.set_permissions(
                    leader_role,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                    manage_permissions=True,
                    manage_messages=True,
                    manage_threads=True,
                    connect=True,
                    speak=True,
                    move_members=True,
                    mute_members=True,
                    deafen_members=True
                )

            await interaction.response.send_message(
                (
                    f"✅ Created {channel.mention}\n"
                    "You have full management permissions."
                ),
                ephemeral=True
            )

        except Exception as error:

            await interaction.response.send_message(
                f"❌ Channel creation failed:\n`{error}`",
                ephemeral=True
            )


# ============================================================
# SEND LEADER PANEL
# ============================================================

async def send_leader_panel(
    guild,
    clan,
    channel
):

    embed = await build_leader_embed(
        guild,
        clan
    )

    await channel.send(
        embed=embed,
        view=LeaderManagementView(
            clan["clan_id"]
        )
    )


# ============================================================
# MODERATOR CLAN SELECT
# ============================================================

class ClanAdminSelect(
    ui.Select
):

    def __init__(
        self,
        clans
    ):

        options = []

        for clan_id, clan in list(
            clans.items()
        )[:25]:

            options.append(
                discord.SelectOption(
                    label=str(
                        clan.get(
                            "clan_name",
                            clan_id
                        )
                    )[:100],
                    value=str(
                        clan_id
                    )
                )
            )

        if not options:

            options.append(
                discord.SelectOption(
                    label="No clans",
                    value="0"
                )
            )

        super().__init__(
            placeholder="Select a clan",
            options=options
        )

    async def callback(
        self,
        interaction
    ):

        clan = find_clan(
            interaction.guild,
            self.values[0]
        )

        if not clan:

            await interaction.response.send_message(
                "❌ Clan not found.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            embed=await build_admin_embed(
                interaction.guild,
                clan
            ),
            view=ModeratorClanView(
                clan["clan_id"]
            ),
            ephemeral=True
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
            ClanAdminSelect(
                clans
            )
        )


# ============================================================
# MODERATOR EMBED
# ============================================================

async def build_admin_embed(
    guild,
    clan
):

    embed = discord.Embed(
        title=(
            f"⚔️ {clan['clan_name']}"
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👑 Owner",
        value=(
            f"<@{clan['owner_id']}>"
        ),
        inline=True
    )

    embed.add_field(
        name="👥 Members",
        value=str(
            len(
                clan.get(
                    "members",
                    []
                )
            )
        ),
        inline=True
    )

    embed.add_field(
        name="📁 Category",
        value=(
            f"<#{clan['category_id']}>"
        ),
        inline=True
    )

    embed.add_field(
        name="💬 Clan Chat",
        value=(
            f"<#{clan['member_text_id']}>"
        ),
        inline=True
    )

    embed.add_field(
        name="🎙️ Voice",
        value=(
            f"<#{clan['general_voice_id']}>"
        ),
        inline=True
    )

    embed.add_field(
        name="📋 Leader Management",
        value=(
            f"<#{clan['leader_channel_id']}>"
        ),
        inline=True
    )

    embed.add_field(
        name="👤 Member Role",
        value=(
            f"<@&{clan['member_role_id']}>"
        ),
        inline=True
    )

    embed.add_field(
        name="🛡️ Moderator Role",
        value=(
            f"<@&{clan['clan_moderator_role_id']}>"
        ),
        inline=True
    )

    embed.add_field(
        name="👑 Leader Role",
        value=(
            f"<@&{clan['leader_role_id']}>"
        ),
        inline=True
    )

    return embed


# ============================================================
# MODERATOR CLAN ACTIONS
# ============================================================

class ModeratorClanView(
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

    @ui.button(
        label="Delete",
        style=discord.ButtonStyle.danger,
        emoji="🗑️"
    )
    async def delete(
        self,
        interaction,
        button
    ):

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Moderator only.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "⚠️ Delete this clan and its channels/roles?",
            view=ConfirmDeleteView(
                self.clan_id
            ),
            ephemeral=True
        )

    @ui.button(
        label="Warn Owner",
        style=discord.ButtonStyle.secondary,
        emoji="⚠️"
    )
    async def warn(
        self,
        interaction,
        button
    ):

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Moderator only.",
                ephemeral=True
            )

            return

        clan = find_clan(
            interaction.guild,
            self.clan_id
        )

        if not clan:
            return

        warnings = clan.setdefault(
            "warnings",
            {}
        )

        owner_id = str(
            clan["owner_id"]
        )

        warnings[owner_id] = (
            int(
                warnings.get(
                    owner_id,
                    0
                )
            )
            + 1
        )

        await save_data()

        await interaction.response.send_message(
            (
                "⚠️ Clan owner warned.\n"
                f"Warnings: **{warnings[owner_id]}**"
            ),
            ephemeral=True
        )

    @ui.button(
        label="Permissions",
        style=discord.ButtonStyle.primary,
        emoji="🔐"
    )
    async def permissions(
        self,
        interaction,
        button
    ):

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Moderator only.",
                ephemeral=True
            )

            return

        clan = find_clan(
            interaction.guild,
            self.clan_id
        )

        if not clan:
            return

        category = get_channel(
            interaction.guild,
            clan.get(
                "category_id"
            )
        )

        if not isinstance(
            category,
            discord.CategoryChannel
        ):

            await interaction.response.send_message(
                "❌ Category not found.",
                ephemeral=True
            )

            return

        member_role = get_role(
            interaction.guild,
            clan.get(
                "member_role_id"
            )
        )

        moderator_role = get_role(
            interaction.guild,
            clan.get(
                "clan_moderator_role_id"
            )
        )

        leader_role = get_role(
            interaction.guild,
            clan.get(
                "leader_role_id"
            )
        )

        await category.set_permissions(
            interaction.guild.default_role,
            view_channel=False
        )

        if member_role:

            await category.set_permissions(
                member_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                connect=True,
                speak=True
            )

        if moderator_role:

            await category.set_permissions(
                moderator_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                connect=True,
                speak=True,
                move_members=True,
                mute_members=True,
                deafen_members=True
            )

        if leader_role:

            await category.set_permissions(
                leader_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_permissions=True,
                manage_messages=True,
                manage_threads=True,
                connect=True,
                speak=True,
                move_members=True,
                mute_members=True,
                deafen_members=True
            )

        await interaction.response.send_message(
            "✅ Clan permissions reset.",
            ephemeral=True
        )


# ============================================================
# DELETE CLAN
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
        label="YES DELETE",
        style=discord.ButtonStyle.danger,
        emoji="🗑️"
    )
    async def confirm(
        self,
        interaction,
        button
    ):

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Moderator only.",
                ephemeral=True
            )

            return

        clan = find_clan(
            interaction.guild,
            self.clan_id
        )

        if not clan:

            await interaction.response.send_message(
                "❌ Clan not found.",
                ephemeral=True
            )

            return

        guild = interaction.guild

        channels = [

            clan.get(
                "member_text_id"
            ),

            clan.get(
                "general_voice_id"
            ),

            clan.get(
                "leader_channel_id"
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

        for channel_id in channels:

            channel = get_channel(
                guild,
                channel_id
            )

            if channel:

                try:

                    await channel.delete(
                        reason="Clan deleted by moderator"
                    )

                except Exception:
                    pass

        roles = [

            clan.get(
                "member_role_id"
            ),

            clan.get(
                "clan_moderator_role_id"
            ),

            clan.get(
                "leader_role_id"
            )
        ]

        for role_id in roles:

            role = get_role(
                guild,
                role_id
            )

            if role:

                try:

                    await role.delete(
                        reason="Clan deleted"
                    )

                except Exception:
                    pass

        data = get_guild_data(
            guild.id
        )

        data["clans"].pop(
            self.clan_id,
            None
        )

        await save_data()

        await interaction.response.send_message(
            f"🗑️ **{clan['clan_name']}** was deleted.",
            ephemeral=True
        )


# ============================================================
# COG
# ============================================================

class Clan(
    commands.Cog
):

    clan = app_commands.Group(
        name="clan",
        description="Clan system"
    )

    def __init__(
        self,
        bot
    ):

        self.bot = bot

    async def cog_load(
        self
    ):

        global clan_data

        clan_data = normalize_data(
            clan_data
        )

        await save_data()

        print(
            "[CLAN] Clan cog loaded."
        )

    @commands.Cog.listener()
    async def on_ready(
        self
    ):

        # Application form
        self.bot.add_view(
            ClanApplicationView()
        )

        # Restore pending approval buttons
        for guild_data in clan_data.get(
            "guilds",
            {}
        ).values():

            for application_id in guild_data.get(
                "pending",
                {}
            ).keys():

                self.bot.add_view(
                    ClanApprovalView(
                        application_id
                    )
                )

            # Restore leader panels
            for clan_id in guild_data.get(
                "clans",
                {}
            ).keys():

                self.bot.add_view(
                    LeaderManagementView(
                        clan_id
                    )
                )

        print(
            "[CLAN] Persistent views registered."
        )

    # ========================================================
    # SET APPLICATION CHANNEL
    # ========================================================

    @clan.command(
        name="setapplication",
        description="Set the clan application review channel"
    )
    @app_commands.describe(
        channel="Channel where moderators receive applications"
    )
    async def setapplication(
        self,
        interaction,
        channel: discord.TextChannel
    ):

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "❌ Administrator permission required.",
                ephemeral=True
            )

            return

        data = get_guild_data(
            interaction.guild.id
        )

        data[
            "application_channel_id"
        ] = channel.id

        await save_data()

        await interaction.response.send_message(
            (
                "✅ Clan applications will be sent to "
                f"{channel.mention}."
            ),
            ephemeral=True
        )

    # ========================================================
    # SET LOG CHANNEL
    # ========================================================

    @clan.command(
        name="setlogs",
        description="Set the clan log channel"
    )
    @app_commands.describe(
        channel="Clan log channel"
    )
    async def setlogs(
        self,
        interaction,
        channel: discord.TextChannel
    ):

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "❌ Administrator permission required.",
                ephemeral=True
            )

            return

        data = get_guild_data(
            interaction.guild.id
        )

        data[
            "log_channel_id"
        ] = channel.id

        await save_data()

        await interaction.response.send_message(
            f"✅ Clan logs set to {channel.mention}.",
            ephemeral=True
        )

    # ========================================================
    # POST APPLICATION FORM
    # ========================================================

    @clan.command(
        name="postform",
        description="Post the clan application form"
    )
    async def postform(
        self,
        interaction
    ):

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "❌ Administrator permission required.",
                ephemeral=True
            )

            return

        data = get_guild_data(
            interaction.guild.id
        )

        if not data.get(
            "application_channel_id"
        ):

            await interaction.response.send_message(
                (
                    "❌ Set the moderator application "
                    "channel first using:\n"
                    "`/clan setapplication`"
                ),
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="⚔️ Create a Clan",
            description=(
                "Want to create your own clan?\n\n"
                "Click **Apply for a Clan** below "
                "and submit your application.\n\n"
                "A moderator will review it before "
                "the clan is created."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="After approval",
            value=(
                "⚔️ Clan category\n"
                "👤 Member role\n"
                "🛡️ Clan moderator role\n"
                "👑 Leader role\n"
                "💬 Clan chat\n"
                "🎙️ Voice channel\n"
                "📋 Leader management channel\n"
                "🎙️ Leader voice channel"
            ),
            inline=False
        )

        await interaction.channel.send(
            embed=embed,
            view=ClanApplicationView()
        )

        await interaction.response.send_message(
            "✅ Clan application form posted.",
            ephemeral=True
        )

    # ========================================================
    # MODERATOR /CLANS
    # ========================================================

    @app_commands.command(
        name="clans",
        description="Open the moderator clan management panel"
    )
    async def clans(
        self,
        interaction
    ):

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ Moderator permission required.",
                ephemeral=True
            )

            return

        data = get_guild_data(
            interaction.guild.id
        )

        if not data[
            "clans"
        ]:

            await interaction.response.send_message(
                "ℹ️ No clans exist yet.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="⚔️ Clan Administration",
            description=(
                "Select a clan below to manage it."
            ),
            color=discord.Color.blurple()
        )

        for clan in list(
            data["clans"].values()
        )[:10]:

            embed.add_field(
                name=clan.get(
                    "clan_name",
                    "Unknown"
                ),
                value=(
                    f"Owner: <@{clan.get('owner_id')}>\n"
                    f"Members: "
                    f"{len(clan.get('members', []))}\n"
                    f"Category: "
                    f"<#{clan.get('category_id')}>"
                ),
                inline=False
            )

        await interaction.response.send_message(
            embed=embed,
            view=ModeratorClanSelectView(
                data["clans"]
            ),
            ephemeral=True
        )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot
):

    await bot.add_cog(
        Clan(bot)
    )

    print(
        "[CLAN] Extension loaded successfully."
    )

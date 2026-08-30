# cogs/clans.py

import discord
from discord.ext import commands
from discord import app_commands

import os
import json
import asyncio
from typing import Optional


# ============================================================
# CONFIGURATION
# ============================================================

PERSIST_DIR = os.getenv("BOT_PERSIST_DIR", "./data")

os.makedirs(PERSIST_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(PERSIST_DIR, "clans_config.json")
DATA_FILE = os.path.join(PERSIST_DIR, "clans_data.json")


# ============================================================
# DEFAULT CONFIG
# ============================================================

DEFAULT_CONFIG = {
    "application_channel_id": None,
    "clan_category_id": None,
}


# ============================================================
# FILE HELPERS
# ============================================================

def load_json(file_path, default):
    if not os.path.exists(file_path):
        return default.copy() if isinstance(default, dict) else default

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        print(f"❌ Failed reading {file_path}: {e}")
        return default.copy() if isinstance(default, dict) else default


def save_json(file_path, data):
    try:
        temp_file = file_path + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        os.replace(temp_file, file_path)

        return True

    except Exception as e:
        print(f"❌ Failed saving {file_path}: {e}")
        return False


# ============================================================
# CLAN COG
# ============================================================

class Clans(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        # Persistent configuration
        self.config = load_json(
            CONFIG_FILE,
            DEFAULT_CONFIG
        )

        # Persistent clan data
        self.data = load_json(
            DATA_FILE,
            {
                "clans": {},
                "applications": {},
                "invites": {}
            }
        )

        # Prevent simultaneous file writes
        self.lock = asyncio.Lock()

        print("✅ Clan system loaded")
        print(
            f"   Application channel: "
            f"{self.config.get('application_channel_id')}"
        )

    # ========================================================
    # SAVE CONFIG
    # ========================================================

    def save_config(self):

        save_json(
            CONFIG_FILE,
            self.config
        )

    # ========================================================
    # SAVE DATA
    # ========================================================

    def save_data(self):

        save_json(
            DATA_FILE,
            self.data
        )

    # ========================================================
    # GET CLAN
    # ========================================================

    def get_clan(self, clan_id):

        return self.data["clans"].get(str(clan_id))

    # ========================================================
    # FIND MEMBER'S CLAN
    # ========================================================

    def get_member_clan(self, guild_id, user_id):

        guild_id = str(guild_id)
        user_id = str(user_id)

        for clan_id, clan in self.data["clans"].items():

            if str(clan.get("guild_id")) != guild_id:
                continue

            if user_id == str(clan.get("owner_id")):
                return clan_id, clan

            members = clan.get("members", {})

            if user_id in members:
                return clan_id, clan

        return None, None

    # ========================================================
    # GET ROLE
    # ========================================================

    def get_role(self, guild, role_id):

        if not role_id:
            return None

        return guild.get_role(int(role_id))

    # ========================================================
    # GET CHANNEL
    # ========================================================

    def get_channel(self, guild, channel_id):

        if not channel_id:
            return None

        return guild.get_channel(int(channel_id))

    # ========================================================
    # ADMIN ONLY CHECK
    # ========================================================

    async def admin_check(self, interaction):

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "❌ Only server administrators can use this command.",
                ephemeral=True
            )

            return False

        return True

    # ========================================================
    # MODERATOR CHECK
    # ========================================================

    async def moderator_check(self, interaction):

        if interaction.user.guild_permissions.administrator:
            return True

        if interaction.user.guild_permissions.manage_guild:
            return True

        await interaction.response.send_message(
            "❌ You need Moderator permissions to use this.",
            ephemeral=True
        )

        return False

    # ========================================================
    # SET APPLICATION CHANNEL
    # ========================================================

    @app_commands.command(
        name="setclanapplicationchannel",
        description="Set the channel where clan applications are posted."
    )
    @app_commands.describe(
        channel="Channel where clan applications will appear."
    )
    async def setclanapplicationchannel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):

        if not await self.admin_check(interaction):
            return

        self.config["application_channel_id"] = channel.id

        self.save_config()

        await interaction.response.send_message(
            f"✅ Clan application channel set to {channel.mention}\n\n"
            f"All future clan applications will be sent there.",
            ephemeral=True
        )

    # ========================================================
    # SET CLAN CATEGORY
    # ========================================================

    @app_commands.command(
        name="setclancategory",
        description="Set the category where clan channels are created."
    )
    @app_commands.describe(
        category="Category where clan channels will be created."
    )
    async def setclancategory(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel
    ):

        if not await self.admin_check(interaction):
            return

        self.config["clan_category_id"] = category.id

        self.save_config()

        await interaction.response.send_message(
            f"✅ Clan category set to {category.mention}",
            ephemeral=True
        )

    # ========================================================
    # APPLICATION MODAL
    # ========================================================

    class ClanApplicationModal(discord.ui.Modal):

        def __init__(self, cog):

            super().__init__(
                title="Clan Application"
            )

            self.cog = cog

            self.clan_name = discord.ui.TextInput(
                label="Clan Name",
                placeholder="Enter your clan name",
                required=True,
                max_length=50
            )

            self.category = discord.ui.TextInput(
                label="Game / Category",
                placeholder="Example: Valorant, GTA, Minecraft",
                required=True,
                max_length=50
            )

            self.description = discord.ui.TextInput(
                label="Clan Description",
                placeholder="Tell us about the clan",
                required=True,
                style=discord.TextStyle.paragraph,
                max_length=1000
            )

            self.requirements = discord.ui.TextInput(
                label="Member Requirements",
                placeholder="What are you looking for in members?",
                required=False,
                style=discord.TextStyle.paragraph,
                max_length=1000
            )

            self.add_item(self.clan_name)
            self.add_item(self.category)
            self.add_item(self.description)
            self.add_item(self.requirements)

        async def on_submit(
            self,
            interaction: discord.Interaction
        ):

            cog = self.cog

            application_channel_id = cog.config.get(
                "application_channel_id"
            )

            if not application_channel_id:

                await interaction.response.send_message(
                    "❌ The clan application channel has not been "
                    "configured yet.\n\n"
                    "Ask an administrator to use:\n"
                    "`/setclanapplicationchannel`",
                    ephemeral=True
                )

                return

            channel = interaction.guild.get_channel(
                int(application_channel_id)
            )

            if not channel:

                await interaction.response.send_message(
                    "❌ The configured application channel "
                    "could not be found.",
                    ephemeral=True
                )

                return

            application_id = str(
                len(cog.data["applications"]) + 1
            )

            application = {
                "id": application_id,
                "guild_id": interaction.guild.id,
                "user_id": interaction.user.id,
                "clan_name": str(self.clan_name.value),
                "category": str(self.category.value),
                "description": str(self.description.value),
                "requirements": str(self.requirements.value),
                "status": "pending",
                "message_id": None
            }

            cog.data["applications"][application_id] = application

            cog.save_data()

            embed = discord.Embed(
                title="📋 New Clan Application",
                description=(
                    f"{interaction.user.mention} submitted "
                    f"a new clan application."
                ),
                color=discord.Color.blurple(),
                timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="👤 Applicant",
                value=(
                    f"{interaction.user.mention}\n"
                    f"`{interaction.user.id}`"
                ),
                inline=False
            )

            embed.add_field(
                name="🏷️ Clan Name",
                value=self.clan_name.value,
                inline=True
            )

            embed.add_field(
                name="🎮 Game / Category",
                value=self.category.value,
                inline=True
            )

            embed.add_field(
                name="📝 Description",
                value=self.description.value[:1024],
                inline=False
            )

            if self.requirements.value:

                embed.add_field(
                    name="📌 Requirements",
                    value=self.requirements.value[:1024],
                    inline=False
                )

            embed.set_footer(
                text=f"Application ID: {application_id}"
            )

            view = cog.ApplicationReviewView(
                cog,
                application_id
            )

            message = await channel.send(
                embed=embed,
                view=view
            )

            application["message_id"] = message.id

            cog.save_data()

            await interaction.response.send_message(
                "✅ Your clan application has been submitted!\n"
                f"Application ID: `{application_id}`",
                ephemeral=True
            )

    # ========================================================
    # APPLICATION BUTTON
    # ========================================================

    class ApplicationButton(discord.ui.Button):

        def __init__(self, cog):

            super().__init__(
                label="Apply for a Clan",
                emoji="📝",
                style=discord.ButtonStyle.primary,
                custom_id="clan_apply_button"
            )

            self.cog = cog

        async def callback(
            self,
            interaction: discord.Interaction
        ):

            await interaction.response.send_modal(
                self.cog.ClanApplicationModal(
                    self.cog
                )
            )

    # ========================================================
    # APPLICATION FORM VIEW
    # ========================================================

    class ApplicationFormView(discord.ui.View):

        def __init__(self, cog):

            super().__init__(
                timeout=None
            )

            self.add_item(
                cog.ApplicationButton(cog)
            )

    # ========================================================
    # POST APPLICATION FORM
    # ========================================================

    @app_commands.command(
        name="postclanform",
        description="Post the clan application form."
    )
    async def postclanform(
        self,
        interaction: discord.Interaction
    ):

        if not await self.admin_check(interaction):
            return

        channel_id = self.config.get(
            "application_channel_id"
        )

        if not channel_id:

            await interaction.response.send_message(
                "❌ Set the application channel first using:\n"
                "`/setclanapplicationchannel`",
                ephemeral=True
            )

            return

        channel = interaction.guild.get_channel(
            int(channel_id)
        )

        if not channel:

            await interaction.response.send_message(
                "❌ Application channel was not found.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="🏰 Create Your Clan",
            description=(
                "Want to create your own clan?\n\n"
                "Click the button below and submit your "
                "clan application.\n\n"
                "A moderator will review your application."
            ),
            color=discord.Color.blurple()
        )

        await channel.send(
            embed=embed,
            view=self.ApplicationFormView(self)
        )

        await interaction.response.send_message(
            f"✅ Clan application form posted in {channel.mention}",
            ephemeral=True
        )

    # ========================================================
    # APPLICATION REVIEW VIEW
    # ========================================================

    class ApplicationReviewView(discord.ui.View):

        def __init__(
            self,
            cog,
            application_id
        ):

            super().__init__(
                timeout=None
            )

            self.cog = cog
            self.application_id = application_id

        @discord.ui.button(
            label="Approve",
            emoji="✅",
            style=discord.ButtonStyle.success
        )
        async def approve(
            self,
            interaction: discord.Interaction,
            button: discord.ui.Button
        ):

            if not await self.cog.moderator_check(interaction):
                return

            application = self.cog.data[
                "applications"
            ].get(self.application_id)

            if not application:

                await interaction.response.send_message(
                    "❌ Application no longer exists.",
                    ephemeral=True
                )

                return

            if application["status"] != "pending":

                await interaction.response.send_message(
                    f"❌ Application already "
                    f"{application['status']}.",
                    ephemeral=True
                )

                return

            application["status"] = "approved"

            self.cog.save_data()

            await interaction.response.send_message(
                "✅ Application approved.",
                ephemeral=True
            )

            await self.cog.create_clan_from_application(
                interaction.guild,
                application
            )

        @discord.ui.button(
            label="Reject",
            emoji="❌",
            style=discord.ButtonStyle.danger
        )
        async def reject(
            self,
            interaction: discord.Interaction,
            button: discord.ui.Button
        ):

            if not await self.cog.moderator_check(interaction):
                return

            application = self.cog.data[
                "applications"
            ].get(self.application_id)

            if not application:
                return

            application["status"] = "rejected"

            self.cog.save_data()

            await interaction.response.send_message(
                "❌ Application rejected.",
                ephemeral=True
            )

    # ========================================================
    # CREATE CLAN
    # ========================================================

    async def create_clan_from_application(
        self,
        guild,
        application
    ):

        owner = guild.get_member(
            int(application["user_id"])
        )

        if not owner:
            return

        clan_id = str(
            max(
                [int(x) for x in self.data["clans"].keys()]
                or [0]
            ) + 1
        )

        clan_name = application["clan_name"]

        category = None

        category_id = self.config.get(
            "clan_category_id"
        )

        if category_id:

            category = guild.get_channel(
                int(category_id)
            )

        if category is None:

            category = await guild.create_category(
                "CLANS"
            )

            self.config["clan_category_id"] = category.id

            self.save_config()

        # ====================================================
        # CREATE ROLES
        # ====================================================

        leader_role = await guild.create_role(
            name=f"{clan_name} Leader",
            reason="Clan system"
        )

        moderator_role = await guild.create_role(
            name=f"{clan_name} Moderator",
            reason="Clan system"
        )

        member_role = await guild.create_role(
            name=f"{clan_name} Member",
            reason="Clan system"
        )

        # ====================================================
        # CREATE TEXT CHANNEL
        # ====================================================

        overwrites = {

            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),

            leader_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),

            moderator_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),

            member_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )
        }

        clan_channel = await guild.create_text_channel(
            f"{clan_name.lower().replace(' ', '-')}-chat",
            category=category,
            overwrites=overwrites,
            reason="Clan system"
        )

        # ====================================================
        # CREATE LEADER CHANNEL
        # ====================================================

        leader_overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            leader_role:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )
        }

        leader_channel = await guild.create_text_channel(
            f"{clan_name.lower().replace(' ', '-')}-leaders",
            category=category,
            overwrites=leader_overwrites,
            reason="Clan leader management"
        )

        # ====================================================
        # GIVE OWNER ROLE
        # ====================================================

        try:
            await owner.add_roles(
                leader_role,
                reason="Clan owner"
            )

        except Exception as e:

            print(
                f"❌ Could not give leader role: {e}"
            )

        # ====================================================
        # SAVE CLAN
        # ====================================================

        clan = {

            "id": clan_id,

            "guild_id": guild.id,

            "name": clan_name,

            "category": application["category"],

            "owner_id": owner.id,

            "leader_role_id": leader_role.id,

            "moderator_role_id": moderator_role.id,

            "member_role_id": member_role.id,

            "text_channel_id": clan_channel.id,

            "leader_channel_id": leader_channel.id,

            "members": {
                str(owner.id): "leader"
            },

            "warnings": {},

            "permissions": {

                "invite_members": True,

                "manage_members": True,

                "manage_moderators": True,

                "manage_channels": False

            }
        }

        self.data["clans"][clan_id] = clan

        self.save_data()

        # ====================================================
        # SEND LEADER PANEL
        # ====================================================

        await self.send_leader_panel(
            leader_channel,
            clan
        )

        # ====================================================
        # SEND CLAN INFO
        # ====================================================

        embed = discord.Embed(
            title=f"🏰 {clan_name}",
            description=(
                f"Clan created successfully!\n\n"
                f"👑 Leader: {owner.mention}\n"
                f"🎮 Category: {application['category']}\n"
                f"💬 Chat: {clan_channel.mention}"
            ),
            color=discord.Color.green()
        )

        await clan_channel.send(
            content=owner.mention,
            embed=embed
        )

    # ========================================================
    # LEADER PANEL
    # ========================================================

    async def send_leader_panel(
        self,
        channel,
        clan
    ):

        guild = channel.guild

        embed = discord.Embed(
            title=f"👑 {clan['name']} Leader Panel",
            description=(
                "Manage your clan members from here."
            ),
            color=discord.Color.gold()
        )

        members_text = ""

        for user_id, role in clan.get(
            "members",
            {}
        ).items():

            member = guild.get_member(
                int(user_id)
            )

            if member:

                members_text += (
                    f"{member.mention} — "
                    f"`{role}`\n"
                )

        if not members_text:
            members_text = "No members."

        embed.add_field(
            name="👥 Members",
            value=members_text[:1024],
            inline=False
        )

        embed.add_field(
            name="📊 Total Members",
            value=str(
                len(clan.get("members", {}))
            ),
            inline=True
        )

        embed.add_field(
            name="🔗 Clan Chat",
            value=(
                guild.get_channel(
                    clan["text_channel_id"]
                ).mention
                if guild.get_channel(
                    clan["text_channel_id"]
                )
                else "Missing"
            ),
            inline=True
        )

        await channel.send(
            embed=embed,
            view=self.LeaderPanelView(
                self,
                clan["id"]
            )
        )

    # ========================================================
    # LEADER PANEL VIEW
    # ========================================================

    class LeaderPanelView(discord.ui.View):

        def __init__(
            self,
            cog,
            clan_id
        ):

            super().__init__(
                timeout=None
            )

            self.cog = cog
            self.clan_id = clan_id

        @discord.ui.button(
            label="Refresh",
            emoji="🔄",
            style=discord.ButtonStyle.primary
        )
        async def refresh(
            self,
            interaction,
            button
        ):

            clan = self.cog.get_clan(
                self.clan_id
            )

            if not clan:
                await interaction.response.send_message(
                    "❌ Clan not found.",
                    ephemeral=True
                )
                return

            if interaction.user.id != int(
                clan["owner_id"]
            ):

                await interaction.response.send_message(
                    "❌ Only the clan leader can use this.",
                    ephemeral=True
                )

                return

            await interaction.response.defer()

            await self.cog.send_leader_panel(
                interaction.channel,
                clan
            )

        @discord.ui.button(
            label="Invite Member",
            emoji="➕",
            style=discord.ButtonStyle.success
        )
        async def invite(
            self,
            interaction,
            button
        ):

            clan = self.cog.get_clan(
                self.clan_id
            )

            if not clan:
                return

            if interaction.user.id != int(
                clan["owner_id"]
            ):

                await interaction.response.send_message(
                    "❌ Only the clan leader can invite members.",
                    ephemeral=True
                )

                return

            await interaction.response.send_message(
                "Use `/claninvite @member` to invite someone.",
                ephemeral=True
            )

    # ========================================================
    # CLANS COMMAND
    # ========================================================

    @app_commands.command(
        name="clans",
        description="Open the clan management panel."
    )
    async def clans(
        self,
        interaction: discord.Interaction
    ):

        if not await self.moderator_check(interaction):
            return

        embed = discord.Embed(
            title="🏰 Clan Management",
            description=(
                "All clans currently registered in this server."
            ),
            color=discord.Color.blurple()
        )

        found = False

        for clan_id, clan in self.data["clans"].items():

            if int(clan["guild_id"]) != interaction.guild.id:
                continue

            found = True

            owner = interaction.guild.get_member(
                int(clan["owner_id"])
            )

            text_channel = interaction.guild.get_channel(
                int(clan["text_channel_id"])
            )

            leader_channel = interaction.guild.get_channel(
                int(clan["leader_channel_id"])
            )

            member_count = len(
                clan.get("members", {})
            )

            value = (
                f"👑 Owner: "
                f"{owner.mention if owner else 'Unknown'}\n"
                f"👥 Members: `{member_count}`\n"
                f"💬 Chat: "
                f"{text_channel.mention if text_channel else 'Missing'}\n"
                f"👑 Leader: "
                f"{leader_channel.mention if leader_channel else 'Missing'}\n"
                f"🔗 ID: `{clan_id}`"
            )

            embed.add_field(
                name=f"🏰 {clan['name']}",
                value=value,
                inline=False
            )

        if not found:

            embed.description = "No clans found."

        await interaction.response.send_message(
            embed=embed,
            view=self.ClanModeratorView(
                self
            ),
            ephemeral=True
        )

    # ========================================================
    # MODERATOR PANEL
    # ========================================================

    class ClanModeratorView(discord.ui.View):

        def __init__(self, cog):

            super().__init__(
                timeout=180
            )

            self.cog = cog

        @discord.ui.button(
            label="Delete Clan",
            emoji="🗑️",
            style=discord.ButtonStyle.danger
        )
        async def delete(
            self,
            interaction,
            button
        ):

            if not await self.cog.moderator_check(
                interaction
            ):
                return

            await interaction.response.send_message(
                "Use `/deleteclan <clan_id>` to delete a clan.",
                ephemeral=True
            )

        @discord.ui.button(
            label="Clan Permissions",
            emoji="⚙️",
            style=discord.ButtonStyle.secondary
        )
        async def permissions(
            self,
            interaction,
            button
        ):

            await interaction.response.send_message(
                "Use `/clanpermissions <clan_id>` to manage permissions.",
                ephemeral=True
            )

    # ========================================================
    # INVITE MEMBER
    # ========================================================

    @app_commands.command(
        name="claninvite",
        description="Invite a member to your clan."
    )
    @app_commands.describe(
        member="Member you want to invite."
    )
    async def claninvite(
        self,
        interaction,
        member: discord.Member
    ):

        clan_id, clan = self.get_member_clan(
            interaction.guild.id,
            interaction.user.id
        )

        if not clan:

            await interaction.response.send_message(
                "❌ You are not part of a clan.",
                ephemeral=True
            )

            return

        role = clan["members"].get(
            str(interaction.user.id)
        )

        if role not in (
            "leader",
            "moderator"
        ):

            await interaction.response.send_message(
                "❌ You do not have permission to invite members.",
                ephemeral=True
            )

            return

        invite_id = f"{clan_id}-{member.id}"

        self.data["invites"][invite_id] = {

            "clan_id": clan_id,

            "guild_id": interaction.guild.id,

            "invited_user_id": member.id,

            "invited_by": interaction.user.id
        }

        self.save_data()

        embed = discord.Embed(
            title="🏰 Clan Invitation",
            description=(
                f"You have been invited to join "
                f"**{clan['name']}**."
            ),
            color=discord.Color.blurple()
        )

        await member.send(
            embed=embed,
            view=self.ClanInviteView(
                self,
                invite_id
            )
        )

        await interaction.response.send_message(
            f"✅ Invitation sent to {member.mention}.",
            ephemeral=True
        )

    # ========================================================
    # INVITE VIEW
    # ========================================================

    class ClanInviteView(discord.ui.View):

        def __init__(
            self,
            cog,
            invite_id
        ):

            super().__init__(
                timeout=None
            )

            self.cog = cog
            self.invite_id = invite_id

        @discord.ui.button(
            label="Confirm & Join Clan",
            emoji="✅",
            style=discord.ButtonStyle.success
        )
        async def confirm(
            self,
            interaction,
            button
        ):

            invite = self.cog.data[
                "invites"
            ].get(self.invite_id)

            if not invite:

                await interaction.response.send_message(
                    "❌ This invitation is no longer valid.",
                    ephemeral=True
                )

                return

            if interaction.user.id != int(
                invite["invited_user_id"]
            ):

                await interaction.response.send_message(
                    "❌ This invitation is not for you.",
                    ephemeral=True
                )

                return

            clan = self.cog.get_clan(
                invite["clan_id"]
            )

            if not clan:

                await interaction.response.send_message(
                    "❌ Clan no longer exists.",
                    ephemeral=True
                )

                return

            guild = self.cog.bot.get_guild(
                int(invite["guild_id"])
            )

            if not guild:

                await interaction.response.send_message(
                    "❌ Server could not be found.",
                    ephemeral=True
                )

                return

            member = guild.get_member(
                interaction.user.id
            )

            if not member:

                await interaction.response.send_message(
                    "❌ You are not in the server.",
                    ephemeral=True
                )

                return

            role = self.cog.get_role(
                guild,
                clan["member_role_id"]
            )

            if role:

                try:

                    await member.add_roles(
                        role,
                        reason="Joined clan"
                    )

                except Exception as e:

                    print(
                        f"❌ Role error: {e}"
                    )

            clan["members"][
                str(member.id)
            ] = "member"

            del self.cog.data[
                "invites"
            ][self.invite_id]

            self.cog.save_data()

            await interaction.response.send_message(
                f"✅ You joined **{clan['name']}**!",
                ephemeral=True
            )

            # Notify clan chat
            channel = guild.get_channel(
                int(clan["text_channel_id"])
            )

            if channel:

                await channel.send(
                    f"🎉 Welcome {member.mention} "
                    f"to the clan!"
                )

    # ========================================================
    # DELETE CLAN
    # ========================================================

    @app_commands.command(
        name="deleteclan",
        description="Delete a clan."
    )
    @app_commands.describe(
        clan_id="Clan ID to delete."
    )
    async def deleteclan(
        self,
        interaction,
        clan_id: str
    ):

        if not await self.moderator_check(
            interaction
        ):
            return

        clan = self.get_clan(clan_id)

        if not clan:

            await interaction.response.send_message(
                "❌ Clan not found.",
                ephemeral=True
            )

            return

        guild = interaction.guild

        channel_ids = [

            clan.get("text_channel_id"),

            clan.get("leader_channel_id")
        ]

        role_ids = [

            clan.get("leader_role_id"),

            clan.get("moderator_role_id"),

            clan.get("member_role_id")
        ]

        for channel_id in channel_ids:

            if channel_id:

                channel = guild.get_channel(
                    int(channel_id)
                )

                if channel:

                    try:
                        await channel.delete(
                            reason="Clan deleted"
                        )

                    except Exception:
                        pass

        for role_id in role_ids:

            if role_id:

                role = guild.get_role(
                    int(role_id)
                )

                if role:

                    try:
                        await role.delete(
                            reason="Clan deleted"
                        )

                    except Exception:
                        pass

        del self.data["clans"][
            str(clan_id)
        ]

        self.save_data()

        await interaction.response.send_message(
            f"🗑️ Clan `{clan_id}` deleted.",
            ephemeral=True
        )

    # ========================================================
    # WARN CLAN MEMBER
    # ========================================================

    @app_commands.command(
        name="clanwarn",
        description="Warn a member of a clan."
    )
    @app_commands.describe(
        member="Clan member.",
        reason="Reason for warning."
    )
    async def clanwarn(
        self,
        interaction,
        member: discord.Member,
        reason: str
    ):

        if not await self.moderator_check(
            interaction
        ):
            return

        clan_id, clan = self.get_member_clan(
            interaction.guild.id,
            member.id
        )

        if not clan:

            await interaction.response.send_message(
                "❌ Member is not in a clan.",
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

        user_warnings.append(
            {
                "reason": reason,
                "moderator_id": interaction.user.id
            }
        )

        self.save_data()

        await interaction.response.send_message(
            f"⚠️ {member.mention} has been warned.\n"
            f"Reason: {reason}",
            ephemeral=True
        )

    # ========================================================
    # CLAN PERMISSIONS
    # ========================================================

    @app_commands.command(
        name="clanpermissions",
        description="View clan permissions."
    )
    @app_commands.describe(
        clan_id="Clan ID."
    )
    async def clanpermissions(
        self,
        interaction,
        clan_id: str
    ):

        if not await self.moderator_check(
            interaction
        ):
            return

        clan = self.get_clan(clan_id)

        if not clan:

            await interaction.response.send_message(
                "❌ Clan not found.",
                ephemeral=True
            )

            return

        permissions = clan.get(
            "permissions",
            {}
        )

        text = ""

        for name, value in permissions.items():

            text += (
                f"**{name.replace('_', ' ').title()}**: "
                f"{'✅' if value else '❌'}\n"
            )

        embed = discord.Embed(
            title=f"⚙️ {clan['name']} Permissions",
            description=text,
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # ========================================================
    # ADD MEMBER ROLE
    # ========================================================

    @app_commands.command(
        name="clanrole",
        description="Change a clan member's role."
    )
    @app_commands.describe(
        member="Clan member.",
        role="member or moderator"
    )
    async def clanrole(
        self,
        interaction,
        member: discord.Member,
        role: str
    ):

        clan_id, clan = self.get_member_clan(
            interaction.guild.id,
            interaction.user.id
        )

        if not clan:

            await interaction.response.send_message(
                "❌ You are not in a clan.",
                ephemeral=True
            )

            return

        if interaction.user.id != int(
            clan["owner_id"]
        ):

            await interaction.response.send_message(
                "❌ Only the clan leader can change roles.",
                ephemeral=True
            )

            return

        role = role.lower()

        if role not in (
            "member",
            "moderator"
        ):

            await interaction.response.send_message(
                "❌ Role must be `member` or `moderator`.",
                ephemeral=True
            )

            return

        if str(member.id) not in clan[
            "members"
        ]:

            await interaction.response.send_message(
                "❌ This member is not in your clan.",
                ephemeral=True
            )

            return

        old_role = self.get_role(
            interaction.guild,
            clan["member_role_id"]
        )

        moderator_role = self.get_role(
            interaction.guild,
            clan["moderator_role_id"]
        )

        if old_role:

            try:
                await member.remove_roles(
                    old_role
                )
            except Exception:
                pass

        if moderator_role:

            try:
                await member.remove_roles(
                    moderator_role
                )
            except Exception:
                pass

        if role == "moderator":

            if moderator_role:

                await member.add_roles(
                    moderator_role
                )

        else:

            if old_role:

                await member.add_roles(
                    old_role
                )

        clan["members"][
            str(member.id)
        ] = role

        self.save_data()

        await interaction.response.send_message(
            f"✅ {member.mention} is now a "
            f"**clan {role}**.",
            ephemeral=True
        )

    # ========================================================
    # REFRESH CLAN PANEL
    # ========================================================

    @app_commands.command(
        name="refreshclans",
        description="Refresh clan information."
    )
    async def refreshclans(
        self,
        interaction
    ):

        if not await self.moderator_check(
            interaction
        ):
            return

        # Remove old bot panel messages if desired.
        # Instead of deleting everything, simply
        # display the current data.

        await interaction.response.send_message(
            "🔄 Clan configuration refreshed.\n\n"
            f"🏰 Total clans: "
            f"`{len(self.data['clans'])}`\n"
            f"📋 Applications: "
            f"`{len(self.data['applications'])}`\n"
            f"📨 Pending applications: "
            f"`{sum(1 for x in self.data['applications'].values() if x.get('status') == 'pending')}`",
            ephemeral=True
        )

    # ========================================================
    # RESTORE PERSISTENT VIEWS
    # ========================================================

    async def restore_views(self):

        try:

            # Main application button
            self.bot.add_view(
                self.ApplicationFormView(
                    self
                )
            )

            # Application review buttons
            for application_id in self.data[
                "applications"
            ]:

                application = self.data[
                    "applications"
                ][application_id]

                if application.get(
                    "status"
                ) == "pending":

                    self.bot.add_view(
                        self.ApplicationReviewView(
                            self,
                            application_id
                        )
                    )

            # Leader panels
            for clan_id in self.data[
                "clans"
            ]:

                self.bot.add_view(
                    self.LeaderPanelView(
                        self,
                        clan_id
                    )
                )

            # Invites
            for invite_id in self.data[
                "invites"
            ]:

                self.bot.add_view(
                    self.ClanInviteView(
                        self,
                        invite_id
                    )
                )

            print(
                "✅ Clan persistent views restored"
            )

        except Exception as e:

            print(
                f"❌ Failed restoring clan views: {e}"
            )

    # ========================================================
    # COG LOAD
    # ========================================================

    async def cog_load(self):

        await self.restore_views()

        print(
            f"🏰 Clan system ready | "
            f"{len(self.data['clans'])} clans loaded | "
            f"{len(self.data['applications'])} applications loaded"
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        Clans(bot)
    )

# ============================================================
# cogs/clans.py
# COMPLETE CLAN SYSTEM
#
# Features:
# - Admin chooses application channel
# - Admin chooses clan category
# - Members apply using a button
# - Moderators approve/reject
# - Application message auto-deletes after decision
# - Clan roles automatically created
# - Clan category permissions
# - Permanent leader management panel
# - Invite members through buttons
# - Warn members through buttons
# - Kick members through buttons
# - Promote/demote clan moderators
# - Leader creates text/voice channels through buttons
# - Leader panel survives bot restart
# - JSON persistence compatible with MasterConfig backup
# ============================================================

import discord
from discord.ext import commands
from discord import app_commands

import os
import json
import asyncio
import re
from typing import Optional


# ============================================================
# PERSISTENCE
# ============================================================

PERSIST_DIR = os.getenv(
    "BOT_PERSIST_DIR",
    "./data"
)

os.makedirs(
    PERSIST_DIR,
    exist_ok=True
)

CONFIG_FILE = os.path.join(
    PERSIST_DIR,
    "clans_config.json"
)

DATA_FILE = "clan_data.json"

data_lock = asyncio.Lock()

def load_data():
    ...
    
clan_data = load_data()
)


# ============================================================
# DEFAULT CONFIG
# ============================================================

DEFAULT_CONFIG = {
    "application_channel_id": None,
    "clan_category_id": None,
    "application_form_message_id": None
}


# ============================================================
# DEFAULT DATA
# ============================================================

DEFAULT_DATA = {
    "clans": {},
    "applications": {},
    "invites": {}
}


# ============================================================
# FILE HELPERS
# ============================================================

def load_json(
    file_path,
    default
):
    if not os.path.exists(file_path):
        return (
            default.copy()
            if isinstance(default, dict)
            else default
        )

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return data

    except Exception as e:

        print(
            f"❌ Failed reading {file_path}: {e}"
        )

        return (
            default.copy()
            if isinstance(default, dict)
            else default
        )


def save_json(
    file_path,
    data
):

    try:

        directory = os.path.dirname(
            file_path
        )

        if directory:
            os.makedirs(
                directory,
                exist_ok=True
            )

        temporary_file = (
            file_path + ".tmp"
        )

        with open(
            temporary_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        os.replace(
            temporary_file,
            file_path
        )

        return True

    except Exception as e:

        print(
            f"❌ Failed saving {file_path}: {e}"
        )

        return False


# ============================================================
# NAME CLEANER
# ============================================================

def clean_channel_name(name):

    name = name.lower().strip()

    name = re.sub(
        r"[^a-z0-9\-_ ]",
        "",
        name
    )

    name = re.sub(
        r"\s+",
        "-",
        name
    )

    name = re.sub(
        r"-+",
        "-",
        name
    )

    return name[:90] or "clan-channel"


# ============================================================
# CLAN COG
# ============================================================

class Clans(commands.Cog):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        # ----------------------------------------------------
        # Configuration
        # ----------------------------------------------------

        self.config = load_json(
            CONFIG_FILE,
            DEFAULT_CONFIG
        )

        # ----------------------------------------------------
        # Clan data
        # ----------------------------------------------------

        self.data = load_json(
            DATA_FILE,
            DEFAULT_DATA
        )

        # ----------------------------------------------------
        # Ensure missing keys exist
        # ----------------------------------------------------

        self.data.setdefault(
            "clans",
            {}
        )

        self.data.setdefault(
            "applications",
            {}
        )

        self.data.setdefault(
            "invites",
            {}
        )

        self.config.setdefault(
            "application_channel_id",
            None
        )

        self.config.setdefault(
            "clan_category_id",
            None
        )

        self.config.setdefault(
            "application_form_message_id",
            None
        )

        # ----------------------------------------------------
        # File lock
        # ----------------------------------------------------

        self.lock = asyncio.Lock()

        print(
            "=========================================="
        )

        print(
            "🏰 CLAN SYSTEM"
        )

        print(
            "=========================================="
        )

        print(
            "✅ Clan system loaded"
        )

        print(
            f"   Application channel: "
            f"{self.config.get('application_channel_id')}"
        )

        print(
            f"   Clan category: "
            f"{self.config.get('clan_category_id')}"
        )

        print(
            f"   Clans loaded: "
            f"{len(self.data['clans'])}"
        )


    # ========================================================
    # SAVE CONFIG
    # ========================================================

    def save_config(self):

        return save_json(
            CONFIG_FILE,
            self.config
        )


    # ========================================================
    # SAVE DATA
    # ========================================================

    def save_data(self):

        return save_json(
            DATA_FILE,
            self.data
        )


    # ========================================================
    # GET CLAN
    # ========================================================

    def get_clan(
        self,
        clan_id
    ):

        return self.data[
            "clans"
        ].get(
            str(clan_id)
        )


    # ========================================================
    # FIND MEMBER CLAN
    # ========================================================

    def get_member_clan(
        self,
        guild_id,
        user_id
    ):

        guild_id = str(
            guild_id
        )

        user_id = str(
            user_id
        )

        for clan_id, clan in self.data[
            "clans"
        ].items():

            if str(
                clan.get("guild_id")
            ) != guild_id:
                continue

            if str(
                clan.get("owner_id")
            ) == user_id:

                return clan_id, clan

            if user_id in clan.get(
                "members",
                {}
            ):

                return clan_id, clan

        return None, None


    # ========================================================
    # GET ROLE
    # ========================================================

    def get_role(
        self,
        guild,
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


    # ========================================================
    # GET CHANNEL
    # ========================================================

    def get_channel(
        self,
        guild,
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


    # ========================================================
    # ADMIN CHECK
    # ========================================================

    async def admin_check(
        self,
        interaction
    ):

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "❌ Only server administrators can use this.",
                ephemeral=True
            )

            return False

        return True


    # ========================================================
    # MODERATOR CHECK
    # ========================================================

    async def moderator_check(
        self,
        interaction
    ):

        permissions = (
            interaction.user.guild_permissions
        )

        if permissions.administrator:
            return True

        if permissions.manage_guild:
            return True

        await interaction.response.send_message(
            "❌ You need Moderator permissions to use this.",
            ephemeral=True
        )

        return False


    # ========================================================
    # LEADER CHECK
    # ========================================================

    def is_clan_leader(
        self,
        interaction,
        clan
    ):

        return (
            interaction.user.id
            == int(clan["owner_id"])
        )


    # ========================================================
    # CLAN MANAGEMENT PERMISSION
    # ========================================================

    def can_manage_clan(
        self,
        interaction,
        clan
    ):

        user_id = str(
            interaction.user.id
        )

        role = clan.get(
            "members",
            {}
        ).get(
            user_id
        )

        return role in (
            "leader",
            "moderator"
        )


    # ========================================================
    # NEXT CLAN ID
    # ========================================================

    def next_clan_id(self):

        existing = []

        for value in self.data[
            "clans"
        ].keys():

            try:
                existing.append(
                    int(value)
                )

            except Exception:
                pass

        return str(
            max(existing or [0]) + 1
        )


    # ========================================================
    # NEXT APPLICATION ID
    # ========================================================

    def next_application_id(self):

        existing = []

        for value in self.data[
            "applications"
        ].keys():

            try:
                existing.append(
                    int(value)
                )

            except Exception:
                pass

        return str(
            max(existing or [0]) + 1
        )


    # ========================================================
    # SET APPLICATION CHANNEL
    # ========================================================

    @app_commands.command(
        name="setclanapplicationchannel",
        description="Set the clan application channel."
    )
    @app_commands.describe(
        channel="Channel where applications will be posted."
    )
    async def setclanapplicationchannel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):

        if not await self.admin_check(
            interaction
        ):
            return

        self.config[
            "application_channel_id"
        ] = channel.id

        self.save_config()

        await interaction.response.send_message(
            f"✅ Clan application channel set to "
            f"{channel.mention}",
            ephemeral=True
        )


    # ========================================================
    # SET CLAN CATEGORY
    # ========================================================

    @app_commands.command(
        name="setclancategory",
        description="Set the category used for clan channels."
    )
    @app_commands.describe(
        category="Category where clan channels will be created."
    )
    async def setclancategory(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel
    ):

        if not await self.admin_check(
            interaction
        ):
            return

        self.config[
            "clan_category_id"
        ] = category.id

        self.save_config()

        await interaction.response.send_message(
            f"✅ Clan category set to "
            f"{category.mention}",
            ephemeral=True
        )


    # ========================================================
    # APPLICATION MODAL
    # ========================================================

    class ClanApplicationModal(
        discord.ui.Modal,
        title="Clan Application"
    ):

        def __init__(
            self,
            cog
        ):

            super().__init__()

            self.cog = cog

            self.clan_name = discord.ui.TextInput(
                label="Clan Name",
                placeholder="Enter your clan name",
                required=True,
                max_length=50
            )

            self.game = discord.ui.TextInput(
                label="Game / Category",
                placeholder="Example: Valorant, GTA, Minecraft",
                required=True,
                max_length=50
            )

            self.description = discord.ui.TextInput(
                label="Clan Description",
                placeholder="Tell us about your clan",
                required=True,
                style=discord.TextStyle.paragraph,
                max_length=1000
            )

            self.requirements = discord.ui.TextInput(
                label="Member Requirements",
                placeholder="What are you looking for?",
                required=False,
                style=discord.TextStyle.paragraph,
                max_length=1000
            )

            self.add_item(
                self.clan_name
            )

            self.add_item(
                self.game
            )

            self.add_item(
                self.description
            )

            self.add_item(
                self.requirements
            )


        async def on_submit(
            self,
            interaction: discord.Interaction
        ):

            cog = self.cog

            channel_id = cog.config.get(
                "application_channel_id"
            )

            if not channel_id:

                await interaction.response.send_message(
                    "❌ Clan applications are not configured yet.",
                    ephemeral=True
                )

                return

            channel = interaction.guild.get_channel(
                int(channel_id)
            )

            if not channel:

                await interaction.response.send_message(
                    "❌ The configured application channel "
                    "could not be found.",
                    ephemeral=True
                )

                return

            # ------------------------------------------------
            # Prevent duplicate applications
            # ------------------------------------------------

            for application in cog.data[
                "applications"
            ].values():

                if (
                    str(application.get("guild_id"))
                    == str(interaction.guild.id)
                    and str(application.get("user_id"))
                    == str(interaction.user.id)
                    and application.get("status")
                    == "pending"
                ):

                    await interaction.response.send_message(
                        "❌ You already have a pending clan application.",
                        ephemeral=True
                    )

                    return

            application_id = (
                cog.next_application_id()
            )

            application = {

                "id": application_id,

                "guild_id": interaction.guild.id,

                "user_id": interaction.user.id,

                "clan_name": str(
                    self.clan_name.value
                ),

                "category": str(
                    self.game.value
                ),

                "description": str(
                    self.description.value
                ),

                "requirements": str(
                    self.requirements.value
                ),

                "status": "pending",

                "message_id": None

            }

            cog.data[
                "applications"
            ][application_id] = application

            cog.save_data()

            # ------------------------------------------------
            # Application embed
            # ------------------------------------------------

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
                name="🏰 Clan Name",
                value=self.clan_name.value,
                inline=True
            )

            embed.add_field(
                name="🎮 Game / Category",
                value=self.game.value,
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

            # ------------------------------------------------
            # Send application
            # ------------------------------------------------

            message = await channel.send(
                embed=embed,
                view=cog.ApplicationReviewView(
                    cog,
                    application_id
                )
            )

            application[
                "message_id"
            ] = message.id

            cog.save_data()

            await interaction.response.send_message(
                "✅ Your clan application has been submitted!\n"
                "A moderator will review it.",
                ephemeral=True
            )


    # ========================================================
    # APPLICATION BUTTON
    # ========================================================

    class ApplicationButton(
        discord.ui.Button
    ):

        def __init__(
            self,
            cog
        ):

            super().__init__(
                label="Apply for a Clan",
                emoji="📝",
                style=discord.ButtonStyle.primary,
                custom_id="clan_application_button"
            )

            self.cog = cog


        async def callback(
            self,
            interaction
        ):

            await interaction.response.send_modal(
                self.cog.ClanApplicationModal(
                    self.cog
                )
            )


    # ========================================================
    # APPLICATION FORM VIEW
    # ========================================================

    class ApplicationFormView(
        discord.ui.View
    ):

        def __init__(
            self,
            cog
        ):

            super().__init__(
                timeout=None
            )

            self.add_item(
                cog.ApplicationButton(
                    cog
                )
            )


    # ========================================================
    # POST CLAN FORM
    # ========================================================

    @app_commands.command(
        name="postclanform",
        description="Post the clan application form."
    )
    async def postclanform(
        self,
        interaction
    ):

        if not await self.admin_check(
            interaction
        ):
            return

        channel_id = self.config.get(
            "application_channel_id"
        )

        if not channel_id:

            await interaction.response.send_message(
                "❌ Set the application channel first.",
                ephemeral=True
            )

            return

        channel = interaction.guild.get_channel(
            int(channel_id)
        )

        if not channel:

            await interaction.response.send_message(
                "❌ Application channel not found.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="🏰 Create Your Clan",
            description=(
                "Want to create your own clan?\n\n"
                "Click **📝 Apply for a Clan** below "
                "and fill in the application form.\n\n"
                "A moderator will review your application."
            ),
            color=discord.Color.blurple()
        )

        message = await channel.send(
            embed=embed,
            view=self.ApplicationFormView(
                self
            )
        )

        self.config[
            "application_form_message_id"
        ] = message.id

        self.save_config()

        await interaction.response.send_message(
            f"✅ Clan application form posted in "
            f"{channel.mention}",
            ephemeral=True
        )


    # ========================================================
    # DELETE APPLICATION MESSAGE
    # ========================================================

    async def delete_application_message(
        self,
        guild,
        application
    ):

        message_id = application.get(
            "message_id"
        )

        if not message_id:
            return

        channel_id = self.config.get(
            "application_channel_id"
        )

        if not channel_id:
            return

        channel = guild.get_channel(
            int(channel_id)
        )

        if not channel:
            return

        try:

            message = await channel.fetch_message(
                int(message_id)
            )

            await message.delete(
                reason="Clan application decision"
            )

        except discord.NotFound:

            pass

        except discord.Forbidden:

            print(
                "❌ Bot cannot delete clan application message."
            )

        except Exception as e:

            print(
                f"⚠️ Could not delete application message: {e}"
            )


    # ========================================================
    # APPLICATION REVIEW VIEW
    # ========================================================

    class ApplicationReviewView(
        discord.ui.View
    ):

        def __init__(
            self,
            cog,
            application_id
        ):

            super().__init__(
                timeout=None
            )

            self.cog = cog

            self.application_id = str(
                application_id
            )


        @discord.ui.button(
            label="Approve",
            emoji="✅",
            style=discord.ButtonStyle.success,
            custom_id="clan_application_approve"
        )
        async def approve(
            self,
            interaction,
            button
        ):

            if not await self.cog.moderator_check(
                interaction
            ):
                return

            application = self.cog.data[
                "applications"
            ].get(
                self.application_id
            )

            if not application:

                await interaction.response.send_message(
                    "❌ Application no longer exists.",
                    ephemeral=True
                )

                return

            if application.get(
                "status"
            ) != "pending":

                await interaction.response.send_message(
                    "❌ This application has already been processed.",
                    ephemeral=True
                )

                return

            await interaction.response.defer(
                ephemeral=True
            )

            try:

                application[
                    "status"
                ] = "approved"

                self.cog.save_data()

                clan = await self.cog.create_clan_from_application(
                    interaction.guild,
                    application
                )

                if clan is None:

                    application[
                        "status"
                    ] = "pending"

                    self.cog.save_data()

                    await interaction.followup.send(
                        "❌ The clan could not be created. "
                        "Check the bot's permissions.",
                        ephemeral=True
                    )

                    return

                # ------------------------------------------------
                # Delete application post
                # ------------------------------------------------

                await self.cog.delete_application_message(
                    interaction.guild,
                    application
                )

                await interaction.followup.send(
                    f"✅ Clan **{clan['name']}** approved and created.",
                    ephemeral=True
                )

            except Exception as e:

                application[
                    "status"
                ] = "pending"

                self.cog.save_data()

                print(
                    f"❌ Clan approval error: {e}"
                )

                await interaction.followup.send(
                    f"❌ Failed to create the clan:\n`{e}`",
                    ephemeral=True
                )


        @discord.ui.button(
            label="Reject",
            emoji="❌",
            style=discord.ButtonStyle.danger,
            custom_id="clan_application_reject"
        )
        async def reject(
            self,
            interaction,
            button
        ):

            if not await self.cog.moderator_check(
                interaction
            ):
                return

            application = self.cog.data[
                "applications"
            ].get(
                self.application_id
            )

            if not application:

                await interaction.response.send_message(
                    "❌ Application no longer exists.",
                    ephemeral=True
                )

                return

            if application.get(
                "status"
            ) != "pending":

                await interaction.response.send_message(
                    "❌ This application has already been processed.",
                    ephemeral=True
                )

                return

            application[
                "status"
            ] = "rejected"

            self.cog.save_data()

            await self.cog.delete_application_message(
                interaction.guild,
                application
            )

            await interaction.response.send_message(
                "❌ Clan application rejected and removed.",
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
            return None

        clan_id = self.next_clan_id()

        clan_name = application[
            "clan_name"
        ]

        # ----------------------------------------------------
        # Find configured category
        # ----------------------------------------------------

        category = None

        category_id = self.config.get(
            "clan_category_id"
        )

        if category_id:

            category = guild.get_channel(
                int(category_id)
            )

            if not isinstance(
                category,
                discord.CategoryChannel
            ):

                category = None

        # ----------------------------------------------------
        # Create fallback category
        # ----------------------------------------------------

        if category is None:

            category = await guild.create_category(
                "CLANS",
                reason="Clan system"
            )

            self.config[
                "clan_category_id"
            ] = category.id

            self.save_config()

        # ----------------------------------------------------
        # Create roles
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Move roles below bot role
        # ----------------------------------------------------

        try:

            bot_member = guild.me

            if bot_member:

                highest_bot_role = (
                    bot_member.top_role
                )

                target_position = max(
                    1,
                    highest_bot_role.position - 1
                )

                await guild.edit_role_positions(
                    positions={
                        leader_role: target_position
                    },
                    reason="Clan role hierarchy"
                )

                await guild.edit_role_positions(
                    positions={
                        moderator_role: max(
                            1,
                            target_position - 1
                        )
                    },
                    reason="Clan role hierarchy"
                )

                await guild.edit_role_positions(
                    positions={
                        member_role: max(
                            1,
                            target_position - 2
                        )
                    },
                    reason="Clan role hierarchy"
                )

        except Exception as e:

            print(
                f"⚠️ Could not position clan roles: {e}"
            )

        # ----------------------------------------------------
        # Clan permissions
        #
        # Leader gets management permissions inside
        # the clan channels.
        # ----------------------------------------------------

        leader_permissions = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True,
            manage_channels=True,
            manage_permissions=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True,
            use_external_emojis=True,
            use_application_commands=True,
            connect=True,
            speak=True,
            stream=True,
            move_members=True,
            mute_members=True,
            deafen_members=True
        )

        moderator_permissions = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True,
            connect=True,
            speak=True
        )

        member_permissions = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True,
            connect=True,
            speak=True
        )

        # ----------------------------------------------------
        # Create main clan text channel
        # ----------------------------------------------------

        text_overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            leader_role:
                leader_permissions,

            moderator_role:
                moderator_permissions,

            member_role:
                member_permissions
        }

        clan_text_channel = await guild.create_text_channel(
            clean_channel_name(
                f"{clan_name}-chat"
            ),
            category=category,
            overwrites=text_overwrites,
            reason="Clan system"
        )

        # ----------------------------------------------------
        # Create leader channel
        # ----------------------------------------------------

        leader_overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            leader_role:
                leader_permissions
        }

        leader_channel = await guild.create_text_channel(
            clean_channel_name(
                f"{clan_name}-leader"
            ),
            category=category,
            overwrites=leader_overwrites,
            reason="Clan leader management"
        )

        # ----------------------------------------------------
        # Give owner leader role
        # ----------------------------------------------------

        try:

            await owner.add_roles(
                leader_role,
                reason="Clan owner"
            )

        except Exception as e:

            print(
                f"❌ Could not give leader role: {e}"
            )

        # ----------------------------------------------------
        # Clan data
        # ----------------------------------------------------

        clan = {

            "id": clan_id,

            "guild_id": guild.id,

            "name": clan_name,

            "category": application[
                "category"
            ],

            "owner_id": owner.id,

            "leader_role_id": leader_role.id,

            "moderator_role_id": moderator_role.id,

            "member_role_id": member_role.id,

            "text_channel_id": clan_text_channel.id,

            "leader_channel_id": leader_channel.id,

            "members": {
                str(owner.id): "leader"
            },

            "warnings": {},

            "custom_channels": [],

            "permissions": {

                "invite_members": True,

                "manage_members": True,

                "manage_moderators": True,

                "warn_members": True,

                "kick_members": True,

                "manage_channels": True,

                "create_text_channels": True,

                "create_voice_channels": True

            }

        }

        self.data[
            "clans"
        ][clan_id] = clan

        self.save_data()

        # ----------------------------------------------------
        # Leader panel
        # ----------------------------------------------------

        await self.send_leader_panel(
            leader_channel,
            clan
        )

        # ----------------------------------------------------
        # Clan welcome
        # ----------------------------------------------------

        embed = discord.Embed(
            title=f"🏰 {clan_name}",
            description=(
                "Your clan has been created successfully!"
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="👑 Leader",
            value=owner.mention,
            inline=True
        )

        embed.add_field(
            name="🎮 Game",
            value=application[
                "category"
            ],
            inline=True
        )

        embed.add_field(
            name="👥 Members",
            value="1",
            inline=True
        )

        embed.add_field(
            name="💬 Clan Chat",
            value=clan_text_channel.mention,
            inline=False
        )

        embed.add_field(
            name="👑 Leader Management",
            value=leader_channel.mention,
            inline=False
        )

        await clan_text_channel.send(
            content=owner.mention,
            embed=embed
        )

        # ----------------------------------------------------
        # Notify owner
        # ----------------------------------------------------

        try:

            await owner.send(
                f"🏰 Your clan **{clan_name}** has been approved!\n\n"
                f"👑 Leader channel: "
                f"{leader_channel.mention}"
            )

        except Exception:

            pass

        return clan


    # ========================================================
    # BUILD LEADER PANEL EMBED
    # ========================================================

    def build_leader_embed(
        self,
        guild,
        clan
    ):

        owner = guild.get_member(
            int(clan["owner_id"])
        )

        members = clan.get(
            "members",
            {}
        )

        member_lines = []

        for user_id, role in members.items():

            member = guild.get_member(
                int(user_id)
            )

            if member:

                if role == "leader":
                    icon = "👑"

                elif role == "moderator":
                    icon = "🛡️"

                else:
                    icon = "👤"

                member_lines.append(
                    f"{icon} {member.mention} — "
                    f"`{role}`"
                )

        if not member_lines:

            member_text = "No members."

        else:

            member_text = "\n".join(
                member_lines
            )

        if len(member_text) > 1024:

            member_text = (
                member_text[:1000]
                + "\n..."
            )

        embed = discord.Embed(
            title=f"👑 {clan['name']} — Leader Panel",
            description=(
                "Manage your clan from this panel.\n"
                "No clan commands are required."
            ),
            color=discord.Color.gold()
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
            name="📊 Total Members",
            value=str(
                len(members)
            ),
            inline=True
        )

        embed.add_field(
            name="🎮 Category",
            value=clan.get(
                "category",
                "Unknown"
            ),
            inline=True
        )

        embed.add_field(
            name="👥 Members",
            value=member_text,
            inline=False
        )

        text_channel = guild.get_channel(
            int(clan["text_channel_id"])
        )

        leader_channel = guild.get_channel(
            int(clan["leader_channel_id"])
        )

        embed.add_field(
            name="💬 Clan Chat",
            value=(
                text_channel.mention
                if text_channel
                else "Missing"
            ),
            inline=True
        )

        embed.add_field(
            name="👑 Management",
            value=(
                leader_channel.mention
                if leader_channel
                else "Missing"
            ),
            inline=True
        )

        custom_channels = clan.get(
            "custom_channels",
            []
        )

        embed.add_field(
            name="📁 Custom Channels",
            value=str(
                len(custom_channels)
            ),
            inline=True
        )

        embed.set_footer(
            text=(
                "Clan Leader Panel • "
                "Use the buttons below"
            )
        )

        return embed


    # ========================================================
    # SEND LEADER PANEL
    # ========================================================

    async def send_leader_panel(
        self,
        channel,
        clan
    ):

        embed = self.build_leader_embed(
            channel.guild,
            clan
        )

        await channel.send(
            embed=embed,
            view=self.LeaderPanelView(
                self,
                clan["id"]
            )
        )


    # ========================================================
    # UPDATE LEADER PANEL
    # ========================================================

    async def update_leader_panel(
        self,
        channel,
        clan
    ):

        try:

            await channel.send(
                embed=self.build_leader_embed(
                    channel.guild,
                    clan
                ),
                view=self.LeaderPanelView(
                    self,
                    clan["id"]
                )
            )

        except Exception as e:

            print(
                f"❌ Could not refresh leader panel: {e}"
            )


    # ========================================================
    # INVITE MODAL
    # ========================================================

    class InviteMemberSelect(
        discord.ui.UserSelect
    ):

        def __init__(
            self,
            cog,
            clan_id
        ):

            super().__init__(
                placeholder="Select a member to invite",
                min_values=1,
                max_values=1,
                custom_id=(
                    f"clan_invite_select_{clan_id}"
                )
            )

            self.cog = cog
            self.clan_id = str(
                clan_id
            )


        async def callback(
            self,
            interaction
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

            if not self.cog.can_manage_clan(
                interaction,
                clan
            ):

                await interaction.response.send_message(
                    "❌ You cannot invite members.",
                    ephemeral=True
                )

                return

            member = self.values[0]

            if str(member.id) in clan.get(
                "members",
                {}
            ):

                await interaction.response.send_message(
                    "❌ This member is already in the clan.",
                    ephemeral=True
                )

                return

            invite_id = (
                f"{self.clan_id}-{member.id}-"
                f"{interaction.user.id}"
            )

            self.cog.data[
                "invites"
            ][invite_id] = {

                "clan_id": self.clan_id,

                "guild_id": interaction.guild.id,

                "invited_user_id": member.id,

                "invited_by": interaction.user.id

            }

            self.cog.save_data()

            embed = discord.Embed(
                title="🏰 Clan Invitation",
                description=(
                    f"You have been invited to join "
                    f"**{clan['name']}**."
                ),
                color=discord.Color.blurple()
            )

            embed.add_field(
                name="Invited by",
                value=interaction.user.mention,
                inline=False
            )

            try:

                await member.send(
                    embed=embed,
                    view=self.cog.ClanInviteView(
                        self.cog,
                        invite_id
                    )
                )

            except discord.Forbidden:

                del self.cog.data[
                    "invites"
                ][invite_id]

                self.cog.save_data()

                await interaction.response.send_message(
                    "❌ I cannot DM that member. "
                    "They may have DMs disabled.",
                    ephemeral=True
                )

                return

            await interaction.response.send_message(
                f"✅ Invitation sent to {member.mention}.",
                ephemeral=True
            )


    # ========================================================
    # INVITE VIEW
    # ========================================================

    class InviteSelectView(
        discord.ui.View
    ):

        def __init__(
            self,
            cog,
            clan_id
        ):

            super().__init__(
                timeout=60
            )

            self.add_item(
                cog.InviteMemberSelect(
                    cog,
                    clan_id
                )
            )


    # ========================================================
    # INVITATION CONFIRMATION
    # ========================================================

    class ClanInviteView(
        discord.ui.View
    ):

        def __init__(
            self,
            cog,
            invite_id
        ):

            super().__init__(
                timeout=None
            )

            self.cog = cog

            self.invite_id = str(
                invite_id
            )


        @discord.ui.button(
            label="Confirm & Join",
            emoji="✅",
            style=discord.ButtonStyle.success,
            custom_id="clan_invite_confirm"
        )
        async def confirm(
            self,
            interaction,
            button
        ):

            invite = self.cog.data[
                "invites"
            ].get(
                self.invite_id
            )

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
                    "❌ This clan no longer exists.",
                    ephemeral=True
                )

                return

            guild = self.cog.bot.get_guild(
                int(invite["guild_id"])
            )

            if not guild:

                await interaction.response.send_message(
                    "❌ Server not found.",
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

            if str(member.id) in clan.get(
                "members",
                {}
            ):

                await interaction.response.send_message(
                    "❌ You are already in this clan.",
                    ephemeral=True
                )

                return

            role = self.cog.get_role(
                guild,
                clan.get(
                    "member_role_id"
                )
            )

            if role:

                try:

                    await member.add_roles(
                        role,
                        reason="Joined clan"
                    )

                except Exception as e:

                    await interaction.response.send_message(
                        f"❌ I could not give you the clan role.\n"
                        f"`{e}`",
                        ephemeral=True
                    )

                    return

            clan[
                "members"
            ][
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

            # ------------------------------------------------
            # Notify clan
            # ------------------------------------------------

            channel = guild.get_channel(
                int(clan["text_channel_id"])
            )

            if channel:

                await channel.send(
                    f"🎉 Welcome {member.mention} "
                    f"to **{clan['name']}**!"
                )

            # ------------------------------------------------
            # Refresh leader panel
            # ------------------------------------------------

            leader_channel = guild.get_channel(
                int(clan["leader_channel_id"])
            )

            if leader_channel:

                await self.cog.update_leader_panel(
                    leader_channel,
                    clan
                )


        @discord.ui.button(
            label="Decline",
            emoji="❌",
            style=discord.ButtonStyle.danger,
            custom_id="clan_invite_decline"
        )
        async def decline(
            self,
            interaction,
            button
        ):

            invite = self.cog.data[
                "invites"
            ].get(
                self.invite_id
            )

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

            del self.cog.data[
                "invites"
            ][self.invite_id]

            self.cog.save_data()

            await interaction.response.send_message(
                "❌ Clan invitation declined.",
                ephemeral=True
            )


    # ========================================================
    # MEMBER SELECT
    # ========================================================

    class ClanMemberSelect(
        discord.ui.UserSelect
    ):

        def __init__(
            self,
            cog,
            clan_id,
            action
        ):

            super().__init__(
                placeholder="Select a clan member",
                min_values=1,
                max_values=1,
                custom_id=(
                    f"clan_member_select_"
                    f"{action}_"
                    f"{clan_id}"
                )
            )

            self.cog = cog
            self.clan_id = str(
                clan_id
            )
            self.action = action


        async def callback(
            self,
            interaction
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

            if not self.cog.is_clan_leader(
                interaction,
                clan
            ):

                await interaction.response.send_message(
                    "❌ Only the clan leader can do this.",
                    ephemeral=True
                )

                return

            member = self.values[0]

            if str(member.id) not in clan.get(
                "members",
                {}
            ):

                await interaction.response.send_message(
                    "❌ That member is not in your clan.",
                    ephemeral=True
                )

                return

            if member.id == int(
                clan["owner_id"]
            ):

                await interaction.response.send_message(
                    "❌ You cannot manage the clan owner.",
                    ephemeral=True
                )

                return

            if self.action == "manage":

                await interaction.response.send_message(
                    embed=self.cog.build_member_manage_embed(
                        member,
                        clan
                    ),
                    view=self.cog.MemberManageView(
                        self.cog,
                        self.clan_id,
                        member.id
                    ),
                    ephemeral=True
                )

                return

            if self.action == "warn":

                await interaction.response.send_modal(
                    self.cog.WarnModal(
                        self.cog,
                        self.clan_id,
                        member.id
                    )
                )

                return

            if self.action == "kick":

                await interaction.response.send_message(
                    f"⚠️ Are you sure you want to kick "
                    f"{member.mention}?",
                    view=self.cog.KickConfirmView(
                        self.cog,
                        self.clan_id,
                        member.id
                    ),
                    ephemeral=True
                )

                return


    # ========================================================
    # MEMBER SELECT VIEW
    # ========================================================

    class ClanMemberSelectView(
        discord.ui.View
    ):

        def __init__(
            self,
            cog,
            clan_id,
            action
        ):

            super().__init__(
                timeout=60
            )

            self.add_item(
                cog.ClanMemberSelect(
                    cog,
                    clan_id,
                    action
                )
            )


    # ========================================================
    # MEMBER MANAGEMENT EMBED
    # ========================================================

    def build_member_manage_embed(
        self,
        member,
        clan
    ):

        role = clan.get(
            "members",
            {}
        ).get(
            str(member.id),
            "member"
        )

        warning_count = len(
            clan.get(
                "warnings",
                {}
            ).get(
                str(member.id),
                []
            )
        )

        embed = discord.Embed(
            title=f"👤 Manage {member.display_name}",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Member",
            value=member.mention,
            inline=True
        )

        embed.add_field(
            name="Clan Role",
            value=role.title(),
            inline=True
        )

        embed.add_field(
            name="⚠️ Warnings",
            value=str(
                warning_count
            ),
            inline=True
        )

        return embed


    # ========================================================
    # MEMBER MANAGEMENT VIEW
    # ========================================================

    class MemberManageView(
        discord.ui.View
    ):

        def __init__(
            self,
            cog,
            clan_id,
            member_id
        ):

            super().__init__(
                timeout=120
            )

            self.cog = cog

            self.clan_id = str(
                clan_id
            )

            self.member_id = int(
                member_id
            )


        @discord.ui.button(
            label="Make Moderator",
            emoji="🛡️",
            style=discord.ButtonStyle.primary
        )
        async def moderator(
            self,
            interaction,
            button
        ):

            await self.cog.set_member_role(
                interaction,
                self.clan_id,
                self.member_id,
                "moderator"
            )


        @discord.ui.button(
            label="Make Member",
            emoji="👤",
            style=discord.ButtonStyle.secondary
        )
        async def member(
            self,
            interaction,
            button
        ):

            await self.cog.set_member_role(
                interaction,
                self.clan_id,
                self.member_id,
                "member"
            )


        @discord.ui.button(
            label="Warn",
            emoji="⚠️",
            style=discord.ButtonStyle.danger
        )
        async def warn(
            self,
            interaction,
            button
        ):

            await interaction.response.send_modal(
                self.cog.WarnModal(
                    self.cog,
                    self.clan_id,
                    self.member_id
                )
            )


        @discord.ui.button(
            label="Kick",
            emoji="👢",
            style=discord.ButtonStyle.danger
        )
        async def kick(
            self,
            interaction,
            button
        ):

            await interaction.response.send_message(
                "⚠️ Confirm removing this member?",
                view=self.cog.KickConfirmView(
                    self.cog,
                    self.clan_id,
                    self.member_id
                ),
                ephemeral=True
            )


    # ========================================================
    # SET MEMBER ROLE
    # ========================================================

    async def set_member_role(
        self,
        interaction,
        clan_id,
        member_id,
        role_type
    ):

        clan = self.get_clan(
            clan_id
        )

        if not clan:

            await interaction.response.send_message(
                "❌ Clan not found.",
                ephemeral=True
            )

            return

        if not self.is_clan_leader(
            interaction,
            clan
        ):

            await interaction.response.send_message(
                "❌ Only the clan leader can change roles.",
                ephemeral=True
            )

            return

        if str(member_id) not in clan.get(
            "members",
            {}
        ):

            await interaction.response.send_message(
                "❌ Member not found in clan.",
                ephemeral=True
            )

            return

        member = interaction.guild.get_member(
            int(member_id)
        )

        if not member:

            await interaction.response.send_message(
                "❌ Member is no longer in the server.",
                ephemeral=True
            )

            return

        member_role = self.get_role(
            interaction.guild,
            clan.get(
                "member_role_id"
            )
        )

        moderator_role = self.get_role(
            interaction.guild,
            clan.get(
                "moderator_role_id"
            )
        )

        try:

            if member_role:

                await member.remove_roles(
                    member_role,
                    reason="Clan role update"
                )

            if moderator_role:

                await member.remove_roles(
                    moderator_role,
                    reason="Clan role update"
                )

            if role_type == "moderator":

                if moderator_role:

                    await member.add_roles(
                        moderator_role,
                        reason="Promoted to clan moderator"
                    )

            else:

                if member_role:

                    await member.add_roles(
                        member_role,
                        reason="Set as clan member"
                    )

            clan[
                "members"
            ][
                str(member.id)
            ] = role_type

            self.save_data()

            await interaction.response.send_message(
                f"✅ {member.mention} is now "
                f"**Clan {role_type.title()}**.",
                ephemeral=True
            )

        except Exception as e:

            await interaction.response.send_message(
                f"❌ Could not update role:\n`{e}`",
                ephemeral=True
            )


    # ========================================================
    # WARN MODAL
    # ========================================================

    class WarnModal(
        discord.ui.Modal,
        title="Warn Clan Member"
    ):

        def __init__(
            self,
            cog,
            clan_id,
            member_id
        ):

            super().__init__()

            self.cog = cog

            self.clan_id = str(
                clan_id
            )

            self.member_id = int(
                member_id
            )

            self.reason = discord.ui.TextInput(
                label="Warning Reason",
                placeholder="Enter the reason for the warning",
                required=True,
                style=discord.TextStyle.paragraph,
                max_length=500
            )

            self.add_item(
                self.reason
            )


        async def on_submit(
            self,
            interaction
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

            if not self.cog.is_clan_leader(
                interaction,
                clan
            ):

                await interaction.response.send_message(
                    "❌ Only the clan leader can warn members.",
                    ephemeral=True
                )

                return

            warnings = clan.setdefault(
                "warnings",
                {}
            )

            user_warnings = warnings.setdefault(
                str(self.member_id),
                []
            )

            user_warnings.append(
                {
                    "reason": str(
                        self.reason.value
                    ),
                    "moderator_id": interaction.user.id
                }
            )

            self.cog.save_data()

            member = interaction.guild.get_member(
                self.member_id
            )

            await interaction.response.send_message(
                f"⚠️ {member.mention if member else 'Member'} "
                f"has received a clan warning.\n\n"
                f"**Reason:** {self.reason.value}\n"
                f"**Total warnings:** "
                f"`{len(user_warnings)}`",
                ephemeral=True
            )


    # ========================================================
    # KICK CONFIRM VIEW
    # ========================================================

    class KickConfirmView(
        discord.ui.View
    ):

        def __init__(
            self,
            cog,
            clan_id,
            member_id
        ):

            super().__init__(
                timeout=60
            )

            self.cog = cog

            self.clan_id = str(
                clan_id
            )

            self.member_id = int(
                member_id
            )


        @discord.ui.button(
            label="Confirm Kick",
            emoji="👢",
            style=discord.ButtonStyle.danger
        )
        async def confirm(
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

            if not self.cog.is_clan_leader(
                interaction,
                clan
            ):

                await interaction.response.send_message(
                    "❌ Only the clan leader can kick members.",
                    ephemeral=True
                )

                return

            if self.member_id == int(
                clan["owner_id"]
            ):

                await interaction.response.send_message(
                    "❌ You cannot kick the clan owner.",
                    ephemeral=True
                )

                return

            member = interaction.guild.get_member(
                self.member_id
            )

            member_role = self.cog.get_role(
                interaction.guild,
                clan.get(
                    "member_role_id"
                )
            )

            moderator_role = self.cog.get_role(
                interaction.guild,
                clan.get(
                    "moderator_role_id"
                )
            )

            try:

                if member:

                    if member_role:

                        await member.remove_roles(
                            member_role,
                            reason="Removed from clan"
                        )

                    if moderator_role:

                        await member.remove_roles(
                            moderator_role,
                            reason="Removed from clan"
                        )

                clan.get(
                    "members",
                    {}
                ).pop(
                    str(self.member_id),
                    None
                )

                clan.get(
                    "warnings",
                    {}
                ).pop(
                    str(self.member_id),
                    None
                )

                self.cog.save_data()

                await interaction.response.send_message(
                    f"👢 {member.mention if member else 'Member'} "
                    f"has been removed from the clan.",
                    ephemeral=True
                )

                text_channel = interaction.guild.get_channel(
                    int(clan["text_channel_id"])
                )

                if text_channel and member:

                    await text_channel.send(
                        f"👢 {member.mention} "
                        f"has been removed from the clan."
                    )

                leader_channel = interaction.guild.get_channel(
                    int(clan["leader_channel_id"])
                )

                if leader_channel:

                    await self.cog.update_leader_panel(
                        leader_channel,
                        clan
                    )

            except Exception as e:

                await interaction.response.send_message(
                    f"❌ Could not remove member:\n`{e}`",
                    ephemeral=True
                )


        @discord.ui.button(
            label="Cancel",
            emoji="❌",
            style=discord.ButtonStyle.secondary
        )
        async def cancel(
            self,
            interaction,
            button
        ):

            await interaction.response.send_message(
                "❌ Kick cancelled.",
                ephemeral=True
            )


    # ========================================================
    # CREATE CHANNEL MODAL
    # ========================================================

    class CreateChannelModal(
        discord.ui.Modal
    ):

        def __init__(
            self,
            cog,
            clan_id,
            channel_type
        ):

            super().__init__(
                title=(
                    "Create Voice Channel"
                    if channel_type == "voice"
                    else "Create Text Channel"
                )
            )

            self.cog = cog

            self.clan_id = str(
                clan_id
            )

            self.channel_type = channel_type

            self.channel_name = discord.ui.TextInput(
                label="Channel Name",
                placeholder="Example: gaming-room",
                required=True,
                max_length=50
            )

            self.add_item(
                self.channel_name
            )


        async def on_submit(
            self,
            interaction
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

            if not self.cog.is_clan_leader(
                interaction,
                clan
            ):

                await interaction.response.send_message(
                    "❌ Only the clan leader can create clan channels.",
                    ephemeral=True
                )

                return

            category = interaction.guild.get_channel(
                int(
                    self.cog.config.get(
                        "clan_category_id"
                    )
                )
            )

            if not isinstance(
                category,
                discord.CategoryChannel
            ):

                await interaction.response.send_message(
                    "❌ Clan category could not be found.",
                    ephemeral=True
                )

                return

            name = clean_channel_name(
                self.channel_name.value
            )

            # ------------------------------------------------
            # Permissions
            # ------------------------------------------------

            leader_role = self.cog.get_role(
                interaction.guild,
                clan.get(
                    "leader_role_id"
                )
            )

            moderator_role = self.cog.get_role(
                interaction.guild,
                clan.get(
                    "moderator_role_id"
                )
            )

            member_role = self.cog.get_role(
                interaction.guild,
                clan.get(
                    "member_role_id"
                )
            )

            overwrites = {

                interaction.guild.default_role:
                    discord.PermissionOverwrite(
                        view_channel=False
                    )
            }

            if leader_role:

                overwrites[
                    leader_role
                ] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_messages=True,
                    manage_channels=True,
                    manage_permissions=True,
                    connect=True,
                    speak=True,
                    move_members=True,
                    mute_members=True,
                    deafen_members=True
                )

            if moderator_role:

                overwrites[
                    moderator_role
                ] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_messages=True,
                    connect=True,
                    speak=True
                )

            if member_role:

                overwrites[
                    member_role
                ] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    connect=True,
                    speak=True
                )

            try:

                if self.channel_type == "voice":

                    new_channel = await interaction.guild.create_voice_channel(
                        name,
                        category=category,
                        overwrites=overwrites,
                        reason=f"Clan channel: {clan['name']}"
                    )

                else:

                    new_channel = await interaction.guild.create_text_channel(
                        name,
                        category=category,
                        overwrites=overwrites,
                        reason=f"Clan channel: {clan['name']}"
                    )

                clan.setdefault(
                    "custom_channels",
                    []
                ).append(
                    new_channel.id
                )

                self.cog.save_data()

                await interaction.response.send_message(
                    f"✅ Created {new_channel.mention}",
                    ephemeral=True
                )

            except Exception as e:

                await interaction.response.send_message(
                    f"❌ Could not create channel:\n`{e}`",
                    ephemeral=True
                )


    # ========================================================
    # LEADER PANEL
    # ========================================================

    class LeaderPanelView(
        discord.ui.View
    ):

        def __init__(
            self,
            cog,
            clan_id
        ):

            super().__init__(
                timeout=None
            )

            self.cog = cog

            self.clan_id = str(
                clan_id
            )


        # ----------------------------------------------------
        # Refresh
        # ----------------------------------------------------

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

            if not self.cog.is_clan_leader(
                interaction,
                clan
            ):

                await interaction.response.send_message(
                    "❌ Only the clan leader can use this panel.",
                    ephemeral=True
                )

                return

            await interaction.response.send_message(
                embed=self.cog.build_leader_embed(
                    interaction.guild,
                    clan
                ),
                view=self.cog.LeaderPanelView(
                    self.cog,
                    self.clan_id
                ),
                ephemeral=True
            )


        # ----------------------------------------------------
        # Invite
        # ----------------------------------------------------

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

                await interaction.response.send_message(
                    "❌ Clan not found.",
                    ephemeral=True
                )

                return

            if not self.cog.can_manage_clan(
                interaction,
                clan
            ):

                await interaction.response.send_message(
                    "❌ You cannot invite members.",
                    ephemeral=True
                )

                return

            await interaction.response.send_message(
                "Select the Discord member you want to invite:",
                view=self.cog.InviteSelectView(
                    self.cog,
                    self.clan_id
                ),
                ephemeral=True
            )


        # ----------------------------------------------------
        # Manage Members
        # ----------------------------------------------------

        @discord.ui.button(
            label="Manage Members",
            emoji="👥",
            style=discord.ButtonStyle.secondary
        )
        async def manage(
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

            if not self.cog.is_clan_leader(
                interaction,
                clan
            ):

                await interaction.response.send_message(
                    "❌ Only the clan leader can manage members.",
                    ephemeral=True
                )

                return

            await interaction.response.send_message(
                "Select a clan member:",
                view=self.cog.ClanMemberSelectView(
                    self.cog,
                    self.clan_id,
                    "manage"
                ),
                ephemeral=True
            )


        # ----------------------------------------------------
        # Warn
        # ----------------------------------------------------

        @discord.ui.button(
            label="Warn",
            emoji="⚠️",
            style=discord.ButtonStyle.danger
        )
        async def warn(
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

            if not self.cog.is_clan_leader(
                interaction,
                clan
            ):

                await interaction.response.send_message(
                    "❌ Only the clan leader can warn members.",
                    ephemeral=True
                )

                return

            await interaction.response.send_message(
                "Select the member you want to warn:",
                view=self.cog.ClanMemberSelectView(
                    self.cog,
                    self.clan_id,
                    "warn"
                ),
                ephemeral=True
            )


        # ----------------------------------------------------
        # Kick
        # ----------------------------------------------------

        @discord.ui.button(
            label="Kick",
            emoji="👢",
            style=discord.ButtonStyle.danger
        )
        async def kick(
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

            if not self.cog.is_clan_leader(
                interaction,
                clan
            ):

                await interaction.response.send_message(
                    "❌ Only the clan leader can kick members.",
                    ephemeral=True
                )

                return

            await interaction.response.send_message(
                "Select the member you want to kick:",
                view=self.cog.ClanMemberSelectView(
                    self.cog,
                    self.clan_id,
                    "kick"
                ),
                ephemeral=True
            )


        # ----------------------------------------------------
        # Create Text Channel
        # ----------------------------------------------------

        @discord.ui.button(
            label="Create Text",
            emoji="💬",
            style=discord.ButtonStyle.primary,
            row=1
        )
        async def create_text(
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

            if not self.cog.is_clan_leader(
                interaction,
                clan
            ):

                await interaction.response.send_message(
                    "❌ Only the clan leader can create channels.",
                    ephemeral=True
                )

                return

            await interaction.response.send_modal(
                self.cog.CreateChannelModal(
                    self.cog,
                    self.clan_id,
                    "text"
                )
            )


        # ----------------------------------------------------
        # Create Voice Channel
        # ----------------------------------------------------

        @discord.ui.button(
            label="Create Voice",
            emoji="🔊",
            style=discord.ButtonStyle.success,
            row=1
        )
        async def create_voice(
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

            if not self.cog.is_clan_leader(
                interaction,
                clan
            ):

                await interaction.response.send_message(
                    "❌ Only the clan leader can create channels.",
                    ephemeral=True
                )

                return

            await interaction.response.send_modal(
                self.cog.CreateChannelModal(
                    self.cog,
                    self.clan_id,
                    "voice"
                )
            )


    # ========================================================
    # /CLANS
    # MODERATOR MANAGEMENT
    # ========================================================

    @app_commands.command(
        name="clans",
        description="Open clan management."
    )
    async def clans(
        self,
        interaction
    ):

        if not await self.moderator_check(
            interaction
        ):
            return

        clans = []

        for clan_id, clan in self.data[
            "clans"
        ].items():

            if str(
                clan.get("guild_id")
            ) != str(
                interaction.guild.id
            ):
                continue

            clans.append(
                (
                    clan_id,
                    clan
                )
            )

        if not clans:

            await interaction.response.send_message(
                "🏰 No clans are currently registered.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="🏰 Clan Management",
            description=(
                "Select a clan below to manage it."
            ),
            color=discord.Color.blurple()
        )

        for clan_id, clan in clans:

            owner = interaction.guild.get_member(
                int(clan["owner_id"])
            )

            text_channel = interaction.guild.get_channel(
                int(clan["text_channel_id"])
            )

            leader_channel = interaction.guild.get_channel(
                int(clan["leader_channel_id"])
            )

            value = (
                f"👑 Owner: "
                f"{owner.mention if owner else 'Unknown'}\n"
                f"👥 Members: "
                f"`{len(clan.get('members', {}))}`\n"
                f"💬 Chat: "
                f"{text_channel.mention if text_channel else 'Missing'}\n"
                f"👑 Leader Panel: "
                f"{leader_channel.mention if leader_channel else 'Missing'}\n"
                f"🆔 ID: `{clan_id}`"
            )

            embed.add_field(
                name=f"🏰 {clan['name']}",
                value=value,
                inline=False
            )

        await interaction.response.send_message(
            embed=embed,
            view=self.ClanModeratorView(
                self
            ),
            ephemeral=True
        )


    # ========================================================
    # MODERATOR CLAN SELECT
    # ========================================================

    class ClanSelect(
        discord.ui.Select
    ):

        def __init__(
            self,
            cog
        ):

            self.cog = cog

            options = []

            for clan_id, clan in cog.data[
                "clans"
            ].items():

                options.append(
                    discord.SelectOption(
                        label=clan["name"][:100],
                        description=(
                            f"Clan ID: {clan_id}"
                        ),
                        value=str(
                            clan_id
                        )
                    )
                )

                if len(options) >= 25:
                    break

            super().__init__(
                placeholder="Select a clan to manage",
                min_values=1,
                max_values=1,
                options=options,
                custom_id="clan_moderator_select"
            )


        async def callback(
            self,
            interaction
        ):

            if not await self.cog.moderator_check(
                interaction
            ):
                return

            clan = self.cog.get_clan(
                self.values[0]
            )

            if not clan:

                await interaction.response.send_message(
                    "❌ Clan not found.",
                    ephemeral=True
                )

                return

            await interaction.response.send_message(
                embed=self.cog.build_moderator_embed(
                    interaction.guild,
                    clan
                ),
                view=self.cog.SelectedClanModeratorView(
                    self.cog,
                    clan["id"]
                ),
                ephemeral=True
            )


    # ========================================================
    # MODERATOR VIEW
    # ========================================================

    class ClanModeratorView(
        discord.ui.View
    ):

        def __init__(
            self,
            cog
        ):

            super().__init__(
                timeout=180
            )

            if cog.data[
                "clans"
            ]:

                self.add_item(
                    cog.ClanSelect(
                        cog
                    )
                )


    # ========================================================
    # MODERATOR EMBED
    # ========================================================

    def build_moderator_embed(
        self,
        guild,
        clan
    ):

        owner = guild.get_member(
            int(clan["owner_id"])
        )

        members = clan.get(
            "members",
            {}
        )

        moderator_count = sum(
            1
            for role in members.values()
            if role == "moderator"
        )

        embed = discord.Embed(
            title=f"🏰 {clan['name']}",
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
            name="👥 Members",
            value=str(
                len(members)
            ),
            inline=True
        )

        embed.add_field(
            name="🛡️ Clan Moderators",
            value=str(
                moderator_count
            ),
            inline=True
        )

        embed.add_field(
            name="🎮 Game",
            value=clan.get(
                "category",
                "Unknown"
            ),
            inline=True
        )

        embed.add_field(
            name="🆔 Clan ID",
            value=f"`{clan['id']}`",
            inline=True
        )

        return embed


    # ========================================================
    # SELECTED MODERATOR VIEW
    # ========================================================

    class SelectedClanModeratorView(
        discord.ui.View
    ):

        def __init__(
            self,
            cog,
            clan_id
        ):

            super().__init__(
                timeout=180
            )

            self.cog = cog

            self.clan_id = str(
                clan_id
            )


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
                "⚠️ Are you sure you want to delete this clan?",
                view=self.cog.DeleteClanConfirmView(
                    self.cog,
                    self.clan_id
                ),
                ephemeral=True
            )


        @discord.ui.button(
            label="Warn Member",
            emoji="⚠️",
            style=discord.ButtonStyle.danger
        )
        async def warn(
            self,
            interaction,
            button
        ):

            clan = self.cog.get_clan(
                self.clan_id
            )

            if not clan:
                return

            await interaction.response.send_message(
                "Select a member to warn:",
                view=self.cog.ClanMemberSelectView(
                    self.cog,
                    self.clan_id,
                    "warn"
                ),
                ephemeral=True
            )


        @discord.ui.button(
            label="Permissions",
            emoji="⚙️",
            style=discord.ButtonStyle.secondary
        )
        async def permissions(
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

            permissions = clan.get(
                "permissions",
                {}
            )

            text = "\n".join(
                f"**{name.replace('_', ' ').title()}**: "
                f"{'✅' if value else '❌'}"
                for name, value in permissions.items()
            )

            await interaction.response.send_message(
                f"⚙️ **{clan['name']} Permissions**\n\n"
                f"{text}",
                ephemeral=True
            )


    # ========================================================
    # DELETE CLAN CONFIRM
    # ========================================================

    class DeleteClanConfirmView(
        discord.ui.View
    ):

        def __init__(
            self,
            cog,
            clan_id
        ):

            super().__init__(
                timeout=60
            )

            self.cog = cog

            self.clan_id = str(
                clan_id
            )


        @discord.ui.button(
            label="Delete Clan",
            emoji="🗑️",
            style=discord.ButtonStyle.danger
        )
        async def confirm(
            self,
            interaction,
            button
        ):

            if not await self.cog.moderator_check(
                interaction
            ):
                return

            clan = self.cog.get_clan(
                self.clan_id
            )

            if not clan:

                await interaction.response.send_message(
                    "❌ Clan no longer exists.",
                    ephemeral=True
                )

                return

            guild = interaction.guild

            # ------------------------------------------------
            # Delete custom channels
            # ------------------------------------------------

            channel_ids = list(
                clan.get(
                    "custom_channels",
                    []
                )
            )

            channel_ids.extend(
                [
                    clan.get(
                        "text_channel_id"
                    ),
                    clan.get(
                        "leader_channel_id"
                    )
                ]
            )

            # Delete unique IDs only

            seen = set()

            for channel_id in channel_ids:

                if not channel_id:
                    continue

                if channel_id in seen:
                    continue

                seen.add(
                    channel_id
                )

                channel = guild.get_channel(
                    int(channel_id)
                )

                if channel:

                    try:

                        await channel.delete(
                            reason="Clan deleted"
                        )

                    except Exception as e:

                        print(
                            f"⚠️ Could not delete channel: {e}"
                        )

            # ------------------------------------------------
            # Delete roles
            # ------------------------------------------------

            role_ids = [

                clan.get(
                    "leader_role_id"
                ),

                clan.get(
                    "moderator_role_id"
                ),

                clan.get(
                    "member_role_id"
                )

            ]

            for role_id in role_ids:

                if not role_id:
                    continue

                role = guild.get_role(
                    int(role_id)
                )

                if role:

                    try:

                        await role.delete(
                            reason="Clan deleted"
                        )

                    except Exception as e:

                        print(
                            f"⚠️ Could not delete role: {e}"
                        )

            # ------------------------------------------------
            # Remove invites
            # ------------------------------------------------

            invites_to_delete = [

                invite_id
                for invite_id, invite
                in self.cog.data[
                    "invites"
                ].items()

                if str(
                    invite.get("clan_id")
                ) == self.clan_id
            ]

            for invite_id in invites_to_delete:

                del self.cog.data[
                    "invites"
                ][invite_id]

            # ------------------------------------------------
            # Delete clan
            # ------------------------------------------------

            del self.cog.data[
                "clans"
            ][self.clan_id]

            self.cog.save_data()

            await interaction.response.send_message(
                f"🗑️ Clan `{self.clan_id}` has been deleted.",
                ephemeral=True
            )


        @discord.ui.button(
            label="Cancel",
            emoji="❌",
            style=discord.ButtonStyle.secondary
        )
        async def cancel(
            self,
            interaction,
            button
        ):

            await interaction.response.send_message(
                "❌ Clan deletion cancelled.",
                ephemeral=True
            )


    # ========================================================
    # OLD COMMAND COMPATIBILITY
    #
    # These are moderator/admin commands.
    # Leaders do NOT need these.
    # ========================================================

    @app_commands.command(
        name="deleteclan",
        description="Delete a clan."
    )
    @app_commands.describe(
        clan_id="Clan ID."
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

        clan = self.get_clan(
            clan_id
        )

        if not clan:

            await interaction.response.send_message(
                "❌ Clan not found.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "⚠️ Confirm clan deletion:",
            view=self.DeleteClanConfirmView(
                self,
                clan_id
            ),
            ephemeral=True
        )


    # ========================================================
    # REFRESH CLANS
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

        await interaction.response.send_message(
            "🔄 **Clan system refreshed.**\n\n"
            f"🏰 Total clans: "
            f"`{len(self.data['clans'])}`\n"
            f"📋 Applications: "
            f"`{len(self.data['applications'])}`\n"
            f"📨 Pending applications: "
            f"`{sum(1 for x in self.data['applications'].values() if x.get('status') == 'pending')}`",
            ephemeral=True
        )


    # ========================================================
    # PERSISTENT VIEWS
    # ========================================================

    async def restore_views(
        self
    ):

        try:

            # ------------------------------------------------
            # Application form
            # ------------------------------------------------

            self.bot.add_view(
                self.ApplicationFormView(
                    self
                )
            )

            # ------------------------------------------------
            # Pending applications
            # ------------------------------------------------

            for application_id, application in self.data[
                "applications"
            ].items():

                if application.get(
                    "status"
                ) == "pending":

                    self.bot.add_view(
                        self.ApplicationReviewView(
                            self,
                            application_id
                        )
                    )

            # ------------------------------------------------
            # Leader panels
            # ------------------------------------------------

            for clan_id in self.data[
                "clans"
            ]:

                self.bot.add_view(
                    self.LeaderPanelView(
                        self,
                        clan_id
                    )
                )

            # ------------------------------------------------
            # Invitations
            # ------------------------------------------------

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

    async def cog_load(
        self
    ):

        await self.restore_views()

        print(
            "🏰 Clan system ready | "
            f"{len(self.data['clans'])} clans | "
            f"{len(self.data['applications'])} applications"
        )


    # ========================================================
    # COG UNLOAD
    # ========================================================

    async def cog_unload(
        self
    ):

        try:

            self.save_config()
            self.save_data()

            print(
                "💾 Clan configuration saved"
            )

        except Exception as e:

            print(
                f"❌ Clan save error: {e}"
            )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot
):

    await bot.add_cog(
        Clans(bot)
    )

    print(
        "📦 Clans cog loaded"
    )

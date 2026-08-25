import discord
from discord.ext import commands
from discord import app_commands

import json
import os


# =========================================================
# CONFIGURATION
# =========================================================

CONFIG_FILE = "voice_config.json"

MODERATOR_ROLE_NAMES = [
    "Moderator",
    "Moderators",
    "Mod",
]


# =========================================================
# JSON
# =========================================================

def load_config():

    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_config(config):

    with open(
        CONFIG_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            config,
            f,
            indent=4
        )


# =========================================================
# VOICE SYSTEM
# =========================================================

class VoiceSystem(commands.Cog):

    def __init__(self, bot):

        self.bot = bot
        self.config = load_config()

        # =================================================
        # TEMPORARY CHANNEL DATA
        #
        # voice_channel_id: {
        #     owner_id,
        #     guild_id,
        #     text_channel_id
        # }
        # =================================================

        self.temp_channels = {}

    # =====================================================
    # /SETUPVOICE
    # =====================================================

    @app_commands.command(
        name="setupvoice",
        description="Set up the Join-to-Create voice system."
    )
    @app_commands.describe(
        category="Category for temporary voice and text channels.",
        join_channel="Voice channel members join to create their room."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def setupvoice(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
        join_channel: discord.VoiceChannel
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

            return

        # -------------------------------------------------
        # SAVE CONFIGURATION
        # -------------------------------------------------

        self.config[str(guild.id)] = {
            "category_id": category.id,
            "join_channel_id": join_channel.id
        }

        save_config(
            self.config
        )

        # -------------------------------------------------
        # CONFIRMATION
        # -------------------------------------------------

        embed = discord.Embed(
            title="🎧 Voice System Configured",
            description=(
                "The Join-to-Create system is now active.\n\n"

                f"🎤 **Join Channel:** {join_channel.mention}\n"
                f"📂 **Category:** `{category.name}`\n\n"

                "When a member joins the Join-to-Create "
                "channel, the bot creates:\n\n"

                "🎧 A temporary voice channel\n"
                "💬 A temporary private text channel\n\n"

                "The text channel automatically follows "
                "the members inside the voice channel.\n\n"

                "When everyone leaves the voice channel, "
                "both channels are automatically deleted."
            ),
            color=discord.Color.blurple()
        )

        if guild.icon:
            embed.set_thumbnail(
                url=guild.icon.url
            )

        embed.set_footer(
            text=f"{guild.name} • Voice System",
            icon_url=(
                guild.icon.url
                if guild.icon
                else None
            )
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # =====================================================
    # VOICE STATE UPDATE
    # =====================================================

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):

        guild = member.guild

        guild_config = self.config.get(
            str(guild.id)
        )

        if not guild_config:
            return

        join_channel_id = guild_config.get(
            "join_channel_id"
        )

        category_id = guild_config.get(
            "category_id"
        )

        # =================================================
        # 1. JOIN-TO-CREATE
        # =================================================

        if (
            after.channel
            and after.channel.id == join_channel_id
        ):

            category = guild.get_channel(
                category_id
            )

            if category:

                await self.create_room(
                    member,
                    guild,
                    category
                )

        # =================================================
        # 2. JOINED AN EXISTING TEMP VOICE
        # =================================================

        if (
            after.channel
            and after.channel.id in self.temp_channels
        ):

            room = self.temp_channels[
                after.channel.id
            ]

            text_channel = guild.get_channel(
                room["text_channel_id"]
            )

            if text_channel:

                await self.add_text_access(
                    text_channel,
                    member
                )

        # =================================================
        # 3. LEFT A TEMP VOICE
        # =================================================

        if (
            before.channel
            and before.channel.id in self.temp_channels
        ):

            room = self.temp_channels[
                before.channel.id
            ]

            text_channel = guild.get_channel(
                room["text_channel_id"]
            )

            # -------------------------------------------------
            # If nobody remains, delete everything
            # -------------------------------------------------

            if len(before.channel.members) == 0:

                await self.delete_room(
                    before.channel.id,
                    guild
                )

                return

            # -------------------------------------------------
            # Otherwise remove member's text access
            # -------------------------------------------------

            if text_channel:

                # Do NOT remove moderator access.
                if not is_moderator(member):

                    try:

                        await text_channel.set_permissions(
                            member,
                            overwrite=None
                        )

                    except discord.HTTPException:
                        pass

    # =====================================================
    # CREATE ROOM
    # =====================================================

    async def create_room(
        self,
        member: discord.Member,
        guild: discord.Guild,
        category: discord.CategoryChannel
    ):

        # =================================================
        # VOICE PERMISSIONS
        # =================================================

        voice_overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=True,
                    connect=True,
                    speak=True,
                    stream=True,
                    use_voice_activation=True
                ),

            member:
                discord.PermissionOverwrite(
                    view_channel=True,
                    connect=True,
                    speak=True,
                    stream=True,
                    use_voice_activation=True,
                    manage_channels=True,
                    move_members=True,
                    mute_members=True,
                    deafen_members=True
                )
        }

        # =================================================
        # MODERATOR VOICE ACCESS
        # =================================================

        for role in guild.roles:

            if role.name in MODERATOR_ROLE_NAMES:

                voice_overwrites[role] = (
                    discord.PermissionOverwrite(
                        view_channel=True,
                        connect=True,
                        speak=True,
                        stream=True,
                        use_voice_activation=True,
                        move_members=True,
                        mute_members=True,
                        deafen_members=True
                    )
                )

        # =================================================
        # CREATE VOICE CHANNEL
        # =================================================

        try:

            voice_channel = await guild.create_voice_channel(

                name=f"{member.display_name}'s Room 🎮",

                category=category,

                overwrites=voice_overwrites,

                reason=(
                    f"Temporary voice room for "
                    f"{member}"
                )
            )

        except discord.Forbidden:

            print(
                f"❌ Cannot create voice channel "
                f"in {guild.name}"
            )

            return

        except discord.HTTPException as e:

            print(
                f"❌ Voice channel creation error: {e}"
            )

            return

        # =================================================
        # TEXT CHANNEL PERMISSIONS
        # =================================================

        text_overwrites = {

            # Nobody sees it by default
            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            # Owner
            member:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )
        }

        # =================================================
        # MODERATOR TEXT ACCESS
        # =================================================

        for role in guild.roles:

            if role.name in MODERATOR_ROLE_NAMES:

                text_overwrites[role] = (
                    discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        attach_files=True,
                        embed_links=True
                    )
                )

        # =================================================
        # CREATE TEXT CHANNEL
        # =================================================

        try:

            text_channel = await guild.create_text_channel(

                name=f"{member.display_name}-chat",

                category=category,

                overwrites=text_overwrites,

                topic=(
                    f"Temporary chat for "
                    f"{member} ({member.id})"
                ),

                reason=(
                    f"Temporary text channel for "
                    f"{member}"
                )
            )

        except discord.Forbidden:

            try:
                await voice_channel.delete(
                    reason="Could not create text channel"
                )
            except:
                pass

            print(
                f"❌ Cannot create text channel "
                f"for {member}"
            )

            return

        except discord.HTTPException:

            try:
                await voice_channel.delete(
                    reason="Could not create text channel"
                )
            except:
                pass

            return

        # =================================================
        # SAVE ROOM
        # =================================================

        self.temp_channels[
            voice_channel.id
        ] = {

            "owner_id": member.id,

            "guild_id": guild.id,

            "text_channel_id": text_channel.id
        }

        # =================================================
        # MOVE MEMBER
        # =================================================

        try:

            await member.move_to(
                voice_channel
            )

        except discord.HTTPException:
            pass

        # =================================================
        # SEND CONTROL PANEL
        # =================================================

        await self.send_control_panel(
            member,
            voice_channel,
            text_channel
        )

        print(
            f"🎧 Created temporary room for "
            f"{member.display_name}\n"
            f"   Voice: {voice_channel.name}\n"
            f"   Text: {text_channel.name}"
        )

    # =====================================================
    # ADD MEMBER TO TEXT CHANNEL
    # =====================================================

    async def add_text_access(
        self,
        text_channel: discord.TextChannel,
        member: discord.Member
    ):

        try:

            await text_channel.set_permissions(
                member,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )

        except discord.Forbidden:

            print(
                f"❌ Cannot give text access to "
                f"{member}"
            )

        except discord.HTTPException:
            pass

    # =====================================================
    # CONTROL PANEL
    # =====================================================

    async def send_control_panel(
        self,
        owner: discord.Member,
        voice_channel: discord.VoiceChannel,
        text_channel: discord.TextChannel
    ):

        guild = owner.guild

        embed = discord.Embed(
            title="🎧 Your Voice Room",
            description=(
                f"Welcome {owner.mention}!\n\n"

                f"🎤 **Voice:** "
                f"{voice_channel.mention}\n"

                f"💬 **Chat:** "
                f"{text_channel.mention}\n\n"

                "Everyone currently inside the voice "
                "channel can use this chat.\n\n"

                "Use the buttons below to manage your room."
            ),
            color=discord.Color.blurple()
        )

        if owner.display_avatar:

            embed.set_thumbnail(
                url=owner.display_avatar.url
            )

        embed.add_field(
            name="👑 Owner",
            value=owner.mention,
            inline=True
        )

        embed.add_field(
            name="👥 Limit",
            value="Unlimited",
            inline=True
        )

        embed.add_field(
            name="🔓 Status",
            value="Unlocked",
            inline=True
        )

        embed.set_footer(
            text=f"{guild.name} • Temporary Voice Room",
            icon_url=(
                guild.icon.url
                if guild.icon
                else None
            )
        )

        try:

            await text_channel.send(

                content=owner.mention,

                embed=embed,

                view=VoiceControlView(
                    self,
                    voice_channel.id,
                    owner.id
                ),

                allowed_mentions=discord.AllowedMentions(
                    users=True
                )
            )

        except discord.HTTPException as e:

            print(
                f"❌ Cannot send control panel: {e}"
            )

    # =====================================================
    # CHECK OWNER
    # =====================================================

    def is_owner(
        self,
        member: discord.Member,
        channel_id: int
    ):

        room = self.temp_channels.get(
            channel_id
        )

        if not room:
            return False

        return (
            room["owner_id"] == member.id
        )

    # =====================================================
    # RENAME
    # =====================================================

    async def rename_channel(
        self,
        interaction,
        channel,
        new_name
    ):

        if not self.is_owner(
            interaction.user,
            channel.id
        ):

            await interaction.response.send_message(
                "❌ Only the room owner can rename it.",
                ephemeral=True
            )

            return

        try:

            await channel.edit(
                name=new_name
            )

            await interaction.response.send_message(
                f"✅ Room renamed to **{new_name}**.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I cannot rename this room.",
                ephemeral=True
            )

    # =====================================================
    # LIMIT
    # =====================================================

    async def set_limit(
        self,
        interaction,
        channel,
        limit
    ):

        if not self.is_owner(
            interaction.user,
            channel.id
        ):

            await interaction.response.send_message(
                "❌ Only the room owner can change the limit.",
                ephemeral=True
            )

            return

        try:

            await channel.edit(
                user_limit=limit
            )

            display_limit = (
                "Unlimited"
                if limit == 0
                else str(limit)
            )

            await interaction.response.send_message(
                f"✅ User limit set to **{display_limit}**.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I cannot change the user limit.",
                ephemeral=True
            )

    # =====================================================
    # INVITE
    # =====================================================

    async def create_invite(
        self,
        interaction,
        channel
    ):

        if not self.is_owner(
            interaction.user,
            channel.id
        ):

            await interaction.response.send_message(
                "❌ Only the room owner can create an invite.",
                ephemeral=True
            )

            return

        try:

            invite = await channel.create_invite(
                max_age=0,
                max_uses=0,
                unique=True
            )

            await interaction.response.send_message(
                f"🔗 **Voice Room Invite**\n\n"
                f"{invite.url}",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I cannot create an invite.",
                ephemeral=True
            )

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ Discord could not create the invite.",
                ephemeral=True
            )

    # =====================================================
    # LOCK / UNLOCK
    # =====================================================

    async def toggle_lock(
        self,
        interaction,
        channel
    ):

        if not self.is_owner(
            interaction.user,
            channel.id
        ):

            await interaction.response.send_message(
                "❌ Only the room owner can lock it.",
                ephemeral=True
            )

            return

        everyone = interaction.guild.default_role

        permissions = channel.overwrites_for(
            everyone
        )

        locked = (
            permissions.connect is False
        )

        try:

            if locked:

                await channel.set_permissions(
                    everyone,
                    connect=True
                )

                await interaction.response.send_message(
                    "🔓 Voice room **unlocked**.",
                    ephemeral=True
                )

            else:

                await channel.set_permissions(
                    everyone,
                    connect=False
                )

                await channel.set_permissions(
                    interaction.user,
                    connect=True
                )

                await interaction.response.send_message(
                    "🔒 Voice room **locked**.",
                    ephemeral=True
                )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I cannot change the room permissions.",
                ephemeral=True
            )

    # =====================================================
    # DELETE ROOM
    # =====================================================

    async def delete_room(
        self,
        channel_id,
        guild
    ):

        room = self.temp_channels.get(
            channel_id
        )

        if not room:
            return

        voice_channel = guild.get_channel(
            channel_id
        )

        text_channel = guild.get_channel(
            room["text_channel_id"]
        )

        # Remove from memory immediately
        self.temp_channels.pop(
            channel_id,
            None
        )

        # -------------------------------------------------
        # DELETE TEXT CHANNEL
        # -------------------------------------------------

        if text_channel:

            try:

                await text_channel.delete(
                    reason="Temporary voice room closed"
                )

                print(
                    f"🗑️ Deleted temporary chat: "
                    f"{text_channel.name}"
                )

            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):
                pass

        # -------------------------------------------------
        # DELETE VOICE CHANNEL
        # -------------------------------------------------

        if voice_channel:

            try:

                await voice_channel.delete(
                    reason="Temporary voice room empty"
                )

                print(
                    f"🗑️ Deleted temporary voice: "
                    f"{voice_channel.name}"
                )

            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):
                pass

    # =====================================================
    # /VOICESTATUS
    # =====================================================

    @app_commands.command(
        name="voicestatus",
        description="Check the temporary voice system."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def voicestatus(
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

        config = self.config.get(
            str(guild.id)
        )

        if not config:

            await interaction.response.send_message(
                "❌ Voice system is not configured.",
                ephemeral=True
            )

            return

        join_channel = guild.get_channel(
            config.get("join_channel_id")
        )

        category = guild.get_channel(
            config.get("category_id")
        )

        active_rooms = [
            room
            for room in self.temp_channels.values()
            if room["guild_id"] == guild.id
        ]

        await interaction.response.send_message(

            f"### 🎧 Voice System\n\n"

            f"🎤 **Join Channel:** "
            f"{join_channel.mention if join_channel else 'Missing'}\n"

            f"📂 **Category:** "
            f"{category.name if category else 'Missing'}\n"

            f"🎧 **Active Rooms:** "
            f"`{len(active_rooms)}`",

            ephemeral=True
        )

    # =====================================================
    # ERROR HANDLER
    # =====================================================

    @setupvoice.error
    async def setupvoice_error(
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
# VOICE CONTROL VIEW
# =========================================================

class VoiceControlView(
    discord.ui.View
):

    def __init__(
        self,
        cog,
        channel_id,
        owner_id
    ):

        super().__init__(
            timeout=None
        )

        self.cog = cog
        self.channel_id = channel_id
        self.owner_id = owner_id

    # =====================================================
    # RENAME
    # =====================================================

    @discord.ui.button(
        label="Rename",
        emoji="✏️",
        style=discord.ButtonStyle.primary
    )
    async def rename(
        self,
        interaction,
        button
    ):

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if not channel:

            await interaction.response.send_message(
                "❌ This room no longer exists.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            RenameModal(
                self.cog,
                channel
            )
        )

    # =====================================================
    # LIMIT
    # =====================================================

    @discord.ui.button(
        label="Limit",
        emoji="👥",
        style=discord.ButtonStyle.primary
    )
    async def limit(
        self,
        interaction,
        button
    ):

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if not channel:

            await interaction.response.send_message(
                "❌ This room no longer exists.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            LimitModal(
                self.cog,
                channel
            )
        )

    # =====================================================
    # INVITE
    # =====================================================

    @discord.ui.button(
        label="Invite",
        emoji="🔗",
        style=discord.ButtonStyle.success
    )
    async def invite(
        self,
        interaction,
        button
    ):

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if not channel:

            await interaction.response.send_message(
                "❌ This room no longer exists.",
                ephemeral=True
            )

            return

        await self.cog.create_invite(
            interaction,
            channel
        )

    # =====================================================
    # LOCK
    # =====================================================

    @discord.ui.button(
        label="Lock",
        emoji="🔒",
        style=discord.ButtonStyle.secondary
    )
    async def lock(
        self,
        interaction,
        button
    ):

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if not channel:

            await interaction.response.send_message(
                "❌ This room no longer exists.",
                ephemeral=True
            )

            return

        await self.cog.toggle_lock(
            interaction,
            channel
        )

    # =====================================================
    # DELETE
    # =====================================================

    @discord.ui.button(
        label="Delete",
        emoji="🗑️",
        style=discord.ButtonStyle.danger
    )
    async def delete(
        self,
        interaction,
        button
    ):

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if not channel:

            await interaction.response.send_message(
                "❌ This room no longer exists.",
                ephemeral=True
            )

            return

        if not self.cog.is_owner(
            interaction.user,
            channel.id
        ):

            await interaction.response.send_message(
                "❌ Only the room owner can delete it.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🗑️ Deleting your room...",
            ephemeral=True
        )

        await self.cog.delete_room(
            channel.id,
            interaction.guild
        )


# =========================================================
# RENAME MODAL
# =========================================================

class RenameModal(
    discord.ui.Modal
):

    def __init__(
        self,
        cog,
        channel
    ):

        super().__init__(
            title="Rename Voice Room"
        )

        self.cog = cog
        self.channel = channel

        self.name_input = discord.ui.TextInput(
            label="New room name",
            placeholder="Gaming Room",
            max_length=100,
            required=True
        )

        self.add_item(
            self.name_input
        )

    async def on_submit(
        self,
        interaction
    ):

        await self.cog.rename_channel(
            interaction,
            self.channel,
            str(
                self.name_input.value
            )
        )


# =========================================================
# LIMIT MODAL
# =========================================================

class LimitModal(
    discord.ui.Modal
):

    def __init__(
        self,
        cog,
        channel
    ):

        super().__init__(
            title="Set User Limit"
        )

        self.cog = cog
        self.channel = channel

        self.limit_input = discord.ui.TextInput(
            label="Maximum users",
            placeholder="0 = unlimited",
            max_length=2,
            required=True
        )

        self.add_item(
            self.limit_input
        )

    async def on_submit(
        self,
        interaction
    ):

        try:

            limit = int(
                str(
                    self.limit_input.value
                )
            )

            if limit < 0 or limit > 99:

                raise ValueError

        except ValueError:

            await interaction.response.send_message(
                "❌ Enter a number from **0 to 99**.\n"
                "0 means unlimited.",
                ephemeral=True
            )

            return

        await self.cog.set_limit(
            interaction,
            self.channel,
            limit
        )


# =========================================================
# HELPER
# =========================================================

def is_moderator(
    member: discord.Member
):

    if member.guild_permissions.administrator:
        return True

    return any(
        role.name in MODERATOR_ROLE_NAMES
        for role in member.roles
    )


# =========================================================
# COG SETUP
# =========================================================

async def setup(bot):

    await bot.add_cog(
        VoiceSystem(bot)
    )

import discord
from discord.ext import commands
from discord import app_commands

import json
import os


# =========================================================
# CONFIGURATION
# =========================================================

CONFIG_FILE = "voice_config.json"


# =========================================================
# JSON FUNCTIONS
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
        # Temporary rooms
        #
        # voice_id: {
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
        category="Category where temporary rooms are created.",
        join_channel="Voice channel members join to create a room."
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
        # SAVE CONFIG
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
                "The Join-to-Create voice system is now active.\n\n"

                f"🎤 **Join Channel:** {join_channel.mention}\n"
                f"📂 **Category:** `{category.name}`\n\n"

                "When a member joins the Join-to-Create channel, "
                "the bot will automatically create:\n\n"

                "🎧 A private temporary voice channel\n"
                "💬 A private temporary control channel\n\n"

                "Both channels will automatically be deleted "
                "when the owner leaves their voice channel."
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
        # MEMBER JOINED JOIN-TO-CREATE
        # =================================================

        if (
            after.channel
            and after.channel.id == join_channel_id
        ):

            category = guild.get_channel(
                category_id
            )

            if category is None:
                return

            await self.create_room(
                member,
                guild,
                category
            )

        # =================================================
        # MEMBER LEFT A TEMP VOICE CHANNEL
        # =================================================

        if (
            before.channel
            and before.channel.id in self.temp_channels
        ):

            voice_channel = before.channel

            # -------------------------------------------------
            # Check if voice channel is empty
            # -------------------------------------------------

            if len(voice_channel.members) == 0:

                await self.delete_room(
                    voice_channel.id,
                    guild
                )

    # =====================================================
    # CREATE TEMPORARY ROOM
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

            # Everyone can see the room
            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=True,
                    connect=True,
                    speak=True,
                    stream=True,
                    use_voice_activation=True
                ),

            # Owner
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
        # CREATE VOICE CHANNEL
        # =================================================

        try:

            voice_channel = await guild.create_voice_channel(

                name=f"{member.display_name}'s Room 🎮",

                category=category,

                overwrites=voice_overwrites,

                reason=(
                    f"Temporary voice room "
                    f"for {member}"
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
                f"❌ Error creating voice channel: {e}"
            )

            return

        # =================================================
        # TEXT CHANNEL PERMISSIONS
        # =================================================

        text_overwrites = {

            # Everyone cannot see
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
        # GIVE MODERATORS ACCESS
        # =================================================

        # If your server has a Moderator role, add it here.
        moderator_role_names = [
            "Moderator",
            "Moderators",
            "Mod"
        ]

        for role in guild.roles:

            if role.name in moderator_role_names:

                text_overwrites[role] = (
                    discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        attach_files=True,
                        embed_links=True
                    )
                )

                voice_overwrites[role] = (
                    discord.PermissionOverwrite(
                        view_channel=True,
                        connect=True,
                        speak=True,
                        stream=True,
                        use_voice_activation=True
                    )
                )

        # =================================================
        # CREATE TEMPORARY TEXT CHANNEL
        # =================================================

        try:

            text_channel = await guild.create_text_channel(

                name=f"room-{member.display_name.lower()}",

                category=category,

                overwrites=text_overwrites,

                topic=(
                    f"Temporary control room for "
                    f"{member} ({member.id})"
                ),

                reason=(
                    f"Temporary control channel "
                    f"for {member}"
                )
            )

        except discord.Forbidden:

            # If text channel fails, remove voice channel
            try:
                await voice_channel.delete(
                    reason="Failed to create control channel"
                )
            except:
                pass

            print(
                f"❌ Cannot create control channel "
                f"for {member}"
            )

            return

        except discord.HTTPException:

            try:
                await voice_channel.delete(
                    reason="Failed to create control channel"
                )
            except:
                pass

            return

        # =================================================
        # SAVE ROOM DATA
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
            f"🎧 Created room for {member.display_name}\n"
            f"   Voice: {voice_channel.name}\n"
            f"   Text: {text_channel.name}"
        )

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

                f"🎤 **Voice Room:** "
                f"{voice_channel.mention}\n\n"

                "Use the buttons below to manage your "
                "temporary voice room.\n\n"

                "✏️ **Rename** — Change the room name\n"
                "👥 **Limit** — Set maximum users\n"
                "🔗 **Invite** — Create an invite\n"
                "🔒 **Lock** — Prevent new users joining\n"
                "👑 **Transfer** — Give ownership to another member\n"
                "🗑️ **Delete** — Delete your room"
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
            name="👥 User Limit",
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
                f"❌ Could not send control panel: {e}"
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
            room["owner_id"]
            == member.id
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
                "❌ Only the room owner can rename this channel.",
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
                "❌ I don't have permission to rename this room.",
                ephemeral=True
            )

    # =====================================================
    # USER LIMIT
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

            if limit == 0:

                display_limit = "Unlimited"

            else:

                display_limit = str(limit)

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
    # CREATE INVITE
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
                f"🔗 **Your voice room invite:**\n\n"
                f"{invite.url}",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I cannot create an invite for this room.",
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
                "❌ Only the room owner can lock this room.",
                ephemeral=True
            )

            return

        everyone = interaction.guild.default_role

        permissions = channel.overwrites_for(
            everyone
        )

        is_locked = (
            permissions.connect is False
        )

        try:

            if is_locked:

                await channel.set_permissions(
                    everyone,
                    connect=True
                )

                await interaction.response.send_message(
                    "🔓 Your voice room is now **unlocked**.",
                    ephemeral=True
                )

            else:

                await channel.set_permissions(
                    everyone,
                    connect=False
                )

                # Make sure owner remains connected
                await channel.set_permissions(
                    interaction.user,
                    connect=True
                )

                await interaction.response.send_message(
                    "🔒 Your voice room is now **locked**.",
                    ephemeral=True
                )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I cannot change the room permissions.",
                ephemeral=True
            )

    # =====================================================
    # TRANSFER OWNERSHIP
    # =====================================================

    async def transfer_ownership(
        self,
        interaction,
        channel,
        new_owner
    ):

        if not self.is_owner(
            interaction.user,
            channel.id
        ):

            await interaction.response.send_message(
                "❌ Only the current owner can transfer ownership.",
                ephemeral=True
            )

            return

        if new_owner.bot:

            await interaction.response.send_message(
                "❌ You cannot transfer ownership to a bot.",
                ephemeral=True
            )

            return

        old_owner = interaction.user

        # Update stored owner
        self.temp_channels[
            channel.id
        ]["owner_id"] = new_owner.id

        try:

            # Remove old owner-specific permissions
            await channel.set_permissions(
                old_owner,
                overwrite=None
            )

            # Give new owner permissions
            await channel.set_permissions(
                new_owner,
                connect=True,
                speak=True,
                stream=True,
                view_channel=True,
                use_voice_activation=True,
                manage_channels=True,
                move_members=True,
                mute_members=True,
                deafen_members=True
            )

            await interaction.response.send_message(
                f"👑 Ownership transferred to "
                f"{new_owner.mention}.",
                ephemeral=True
            )

        except discord.Forbidden:

            # Restore ownership if Discord rejects change
            self.temp_channels[
                channel.id
            ]["owner_id"] = old_owner.id

            await interaction.response.send_message(
                "❌ I couldn't transfer ownership.",
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

        text_channel_id = room.get(
            "text_channel_id"
        )

        text_channel = None

        if text_channel_id:

            text_channel = guild.get_channel(
                text_channel_id
            )

        # Remove from memory first
        self.temp_channels.pop(
            channel_id,
            None
        )

        # =================================================
        # DELETE TEXT CHANNEL
        # =================================================

        if text_channel:

            try:

                await text_channel.delete(
                    reason="Temporary voice room closed"
                )

                print(
                    f"🗑️ Deleted control channel: "
                    f"{text_channel.name}"
                )

            except discord.NotFound:

                pass

            except discord.Forbidden:

                print(
                    f"❌ Cannot delete control channel "
                    f"{text_channel.name}"
                )

            except discord.HTTPException:

                pass

        # =================================================
        # DELETE VOICE CHANNEL
        # =================================================

        if voice_channel:

            try:

                await voice_channel.delete(
                    reason="Temporary voice room empty"
                )

                print(
                    f"🗑️ Deleted voice channel: "
                    f"{voice_channel.name}"
                )

            except discord.NotFound:

                pass

            except discord.Forbidden:

                print(
                    f"❌ Cannot delete voice channel "
                    f"{voice_channel.name}"
                )

            except discord.HTTPException:

                pass

    # =====================================================
    # VOICESTATUS
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
                "❌ Voice system has not been configured.",
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
    # SETUP ERROR
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
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ This voice room no longer exists.",
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
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ This voice room no longer exists.",
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
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ This voice room no longer exists.",
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
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ This voice room no longer exists.",
                ephemeral=True
            )

            return

        await self.cog.toggle_lock(
            interaction,
            channel
        )

    # =====================================================
    # TRANSFER
    # =====================================================

    @discord.ui.button(
        label="Transfer",
        emoji="👑",
        style=discord.ButtonStyle.secondary
    )
    async def transfer(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ This voice room no longer exists.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "👑 Use `/transfer` is not enabled in this version.\n"
            "You can add a member-selection menu if required.",
            ephemeral=True
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
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ This voice room no longer exists.",
                ephemeral=True
            )

            return

        if not self.cog.is_owner(
            interaction.user,
            channel.id
        ):

            await interaction.response.send_message(
                "❌ Only the room owner can delete this room.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🗑️ Deleting your temporary room...",
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
        interaction: discord.Interaction
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
        interaction: discord.Interaction
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
                "❌ Enter a number between **0 and 99**.",
                ephemeral=True
            )

            return

        await self.cog.set_limit(
            interaction,
            self.channel,
            limit
        )


# =========================================================
# COG SETUP
# =========================================================

async def setup(bot):

    await bot.add_cog(
        VoiceSystem(bot)
    )


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

    except (
        json.JSONDecodeError,
        FileNotFoundError
    ):

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

        # Temporary voice channels
        #
        # {
        #     channel_id: {
        #         "owner_id": member_id,
        #         "guild_id": guild_id
        #     }
        # }
        #
        self.temp_channels = {}

    # =====================================================
    # /SETUPVOICE
    # =====================================================

    @app_commands.command(
        name="setupvoice",
        description="Set up the Join-to-Create voice system."
    )
    @app_commands.describe(
        category="Category where temporary voice channels will be created.",
        join_channel="Voice channel members join to create their room.",
        control_channel="Text channel for voice room controls."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def setupvoice(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
        join_channel: discord.VoiceChannel,
        control_channel: discord.TextChannel
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

            "join_channel_id": join_channel.id,

            "control_channel_id": control_channel.id
        }

        save_config(
            self.config
        )

        # -------------------------------------------------
        # SEND SETUP MESSAGE
        # -------------------------------------------------

        embed = discord.Embed(
            title="🎧 Temporary Voice Channels",
            description=(
                "Voice channel system has been configured.\n\n"

                f"🎤 **Join Channel:** "
                f"{join_channel.mention}\n"

                f"📂 **Category:** "
                f"`{category.name}`\n"

                f"⚙️ **Control Channel:** "
                f"{control_channel.mention}\n\n"

                "Members can join the configured voice channel "
                "to automatically receive their own temporary "
                "voice room."
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

        # -------------------------------------------------
        # SEND CONTROL CHANNEL MESSAGE
        # -------------------------------------------------

        try:

            setup_embed = discord.Embed(
                title="🎧 Join to Create",
                description=(
                    f"Join {join_channel.mention} to "
                    "automatically create your own temporary "
                    "voice channel.\n\n"

                    "**Available controls:**\n"
                    "✏️ Rename your room\n"
                    "👥 Set user limit\n"
                    "🔗 Create an invite\n"
                    "🔒 Lock / unlock your room\n"
                    "👑 Transfer ownership\n"
                    "🗑️ Delete your room"
                ),
                color=discord.Color.blurple()
            )

            if guild.icon:

                setup_embed.set_thumbnail(
                    url=guild.icon.url
                )

            setup_embed.set_footer(
                text=f"{guild.name} • Voice System",
                icon_url=(
                    guild.icon.url
                    if guild.icon
                    else None
                )
            )

            await control_channel.send(
                embed=setup_embed
            )

        except discord.Forbidden:

            await interaction.followup.send(
                f"⚠️ The system is configured, but I cannot "
                f"send messages in {control_channel.mention}.",
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

            # -------------------------------------------------
            # CREATE TEMPORARY VOICE CHANNEL
            # -------------------------------------------------

            overwrites = {

                # Everyone
                guild.default_role:
                    discord.PermissionOverwrite(
                        connect=True,
                        speak=True,
                        stream=True,
                        view_channel=True,
                        use_voice_activation=True
                    ),

                # Owner
                member:
                    discord.PermissionOverwrite(
                        manage_channels=True,
                        move_members=True,
                        mute_members=True,
                        deafen_members=True,
                        connect=True,
                        speak=True,
                        stream=True,
                        view_channel=True,
                        use_voice_activation=True
                    )
            }

            try:

                temp_vc = await guild.create_voice_channel(

                    name=f"{member.display_name}'s Room 🎮",

                    category=category,

                    overwrites=overwrites
                )

            except discord.Forbidden:

                print(
                    f"❌ Cannot create temporary VC "
                    f"in {guild.name}"
                )

                return

            except discord.HTTPException as e:

                print(
                    f"❌ Discord error creating VC: {e}"
                )

                return

            # -------------------------------------------------
            # SAVE TEMP CHANNEL
            # -------------------------------------------------

            self.temp_channels[
                temp_vc.id
            ] = {

                "owner_id": member.id,

                "guild_id": guild.id
            }

            # -------------------------------------------------
            # MOVE MEMBER
            # -------------------------------------------------

            try:

                await member.move_to(
                    temp_vc
                )

            except discord.HTTPException:

                pass

            print(
                f"🎧 Created temp VC "
                f"{temp_vc.name} "
                f"for {member}"
            )

            # -------------------------------------------------
            # SEND CONTROL PANEL
            # -------------------------------------------------

            await self.send_control_panel(
                member,
                temp_vc
            )

        # =================================================
        # DELETE EMPTY TEMP VC
        # =================================================

        if (
            before.channel
            and before.channel.id in self.temp_channels
        ):

            channel = before.channel

            # Wait a moment because Discord can update
            # voice membership asynchronously.
            await discord.utils.sleep_until(
                discord.utils.utcnow()
            )

            if len(channel.members) == 0:

                try:

                    channel_id = channel.id

                    await channel.delete(
                        reason="Temporary voice channel empty"
                    )

                    self.temp_channels.pop(
                        channel_id,
                        None
                    )

                    print(
                        f"🗑️ Deleted empty temp VC: "
                        f"{channel.name}"
                    )

                except discord.NotFound:

                    self.temp_channels.pop(
                        channel.id,
                        None
                    )

                except discord.Forbidden:

                    print(
                        f"❌ Cannot delete temp VC: "
                        f"{channel.name}"
                    )

                except discord.HTTPException:

                    pass

    # =====================================================
    # SEND CONTROL PANEL
    # =====================================================

    async def send_control_panel(
        self,
        owner: discord.Member,
        voice_channel: discord.VoiceChannel
    ):

        guild = owner.guild

        guild_config = self.config.get(
            str(guild.id),
            {}
        )

        control_channel_id = guild_config.get(
            "control_channel_id"
        )

        if not control_channel_id:

            return

        control_channel = guild.get_channel(
            control_channel_id
        )

        if control_channel is None:

            return

        embed = discord.Embed(
            title="🎧 Your Voice Room",
            description=(
                f"{owner.mention}, your temporary voice "
                f"channel has been created!\n\n"

                f"🎤 **Channel:** "
                f"{voice_channel.mention}\n\n"

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
            name="👥 Members",
            value="No limit",
            inline=True
        )

        embed.add_field(
            name="🔓 Status",
            value="Unlocked",
            inline=True
        )

        embed.set_footer(
            text=f"{guild.name} • Voice Room",
            icon_url=(
                guild.icon.url
                if guild.icon
                else None
            )
        )

        try:

            await control_channel.send(
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

        except discord.HTTPException:

            pass

    # =====================================================
    # CHECK OWNERSHIP
    # =====================================================

    def is_owner(
        self,
        member: discord.Member,
        channel_id: int
    ):

        channel_info = self.temp_channels.get(
            channel_id
        )

        if not channel_info:

            return False

        return (
            channel_info["owner_id"]
            == member.id
        )

    # =====================================================
    # RENAME CHANNEL
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
                "❌ Only the owner of this room can rename it.",
                ephemeral=True
            )

            return

        try:

            await channel.edit(
                name=new_name
            )

            await interaction.response.send_message(
                f"✅ Voice room renamed to **{new_name}**.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I don't have permission to rename this channel.",
                ephemeral=True
            )

    # =====================================================
    # SET USER LIMIT
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
                "❌ Only the owner can change the user limit.",
                ephemeral=True
            )

            return

        try:

            await channel.edit(
                user_limit=limit
            )

            if limit == 0:

                text = "unlimited"

            else:

                text = str(limit)

            await interaction.response.send_message(
                f"✅ User limit set to **{text}**.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I cannot change the channel limit.",
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
                "❌ Only the owner can lock this room.",
                ephemeral=True
            )

            return

        everyone = interaction.guild.default_role

        current_permissions = (
            channel.overwrites_for(
                everyone
            )
        )

        currently_locked = (
            current_permissions.connect is False
        )

        try:

            if currently_locked:

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

                # Keep owner connected
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
                "❌ I cannot change the channel permissions.",
                ephemeral=True
            )

    # =====================================================
    # DELETE VOICE CHANNEL
    # =====================================================

    async def delete_channel(
        self,
        interaction,
        channel
    ):

        if not self.is_owner(
            interaction.user,
            channel.id
        ):

            await interaction.response.send_message(
                "❌ Only the owner can delete this room.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🗑️ Deleting your voice room...",
            ephemeral=True
        )

        try:

            channel_id = channel.id

            await channel.delete(
                reason=(
                    f"Voice room deleted by "
                    f"{interaction.user}"
                )
            )

            self.temp_channels.pop(
                channel_id,
                None
            )

        except discord.HTTPException:

            pass

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
                "❌ Only the owner can create an invite.",
                ephemeral=True
            )

            return

        try:

            invite = await channel.create_invite(
                max_age=0,
                max_uses=0,
                unique=True,
                reason=(
                    f"Voice invite created by "
                    f"{interaction.user}"
                )
            )

            await interaction.response.send_message(
                f"🔗 **Your voice room invite:**\n\n"
                f"{invite.url}",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I cannot create an invite for this channel.",
                ephemeral=True
            )

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ Discord could not create the invite.",
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

        # Update owner
        self.temp_channels[
            channel.id
        ]["owner_id"] = new_owner.id

        try:

            # Remove old owner permissions
            await channel.set_permissions(
                interaction.user,
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

            await interaction.response.send_message(
                "❌ I cannot transfer ownership.",
                ephemeral=True
            )

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
                "❌ Voice system has not been configured.",
                ephemeral=True
            )

            return

        join_channel = guild.get_channel(
            config.get(
                "join_channel_id"
            )
        )

        category = guild.get_channel(
            config.get(
                "category_id"
            )
        )

        control_channel = guild.get_channel(
            config.get(
                "control_channel_id"
            )
        )

        await interaction.response.send_message(

            f"### 🎧 Voice System\n\n"

            f"🎤 **Join Channel:** "
            f"{join_channel.mention if join_channel else 'Missing'}\n"

            f"📂 **Category:** "
            f"{category.name if category else 'Missing'}\n"

            f"⚙️ **Control Channel:** "
            f"{control_channel.mention if control_channel else 'Missing'}\n"

            f"🎧 **Active Rooms:** "
            f"`{len([c for c in self.temp_channels.values() if c['guild_id'] == guild.id])}`",

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
    # USER LIMIT
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
        interaction,
        button
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
        interaction,
        button
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

        if channel is None:

            await interaction.response.send_message(
                "❌ This voice room no longer exists.",
                ephemeral=True
            )

            return

        await self.cog.delete_channel(
            interaction,
            channel
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
            label="New channel name",
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
            str(self.name_input.value)
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

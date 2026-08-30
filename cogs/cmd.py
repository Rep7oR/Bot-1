
import discord
from discord.ext import commands
from discord import app_commands

import json
import os


# =========================================================
# CONFIGURATION
# =========================================================

CONFIG_FILE = "cmd_config.json"

# Roles allowed to use /cmd
MODERATOR_ROLE_NAMES = [
    "MODERATOR",
    "Moderators",
    "Mod"
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
        ) as file:

            return json.load(file)

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
    ) as file:

        json.dump(
            data,
            file,
            indent=4
        )


# =========================================================
# MODERATOR CHECK
# =========================================================

def is_moderator(member: discord.Member):

    # Administrator always has access
    if member.guild_permissions.administrator:
        return True

    # Moderator roles
    for role in member.roles:

        if role.name in MODERATOR_ROLE_NAMES:
            return True

    return False


# =========================================================
# COMMAND SYSTEM
# =========================================================

class CommandSystem(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.config = load_json(
            CONFIG_FILE
        )

    # =====================================================
    # SAVE CONFIG
    # =====================================================

    def save_config(self):

        save_json(
            CONFIG_FILE,
            self.config
        )

    # =====================================================
    # GET GUILD CONFIG
    # =====================================================

    def get_guild_config(
        self,
        guild: discord.Guild
    ):

        guild_id = str(
            guild.id
        )

        if guild_id not in self.config:

            self.config[guild_id] = {}

        return self.config[guild_id]

    # =====================================================
    # GET CONFIGURED CHANNEL
    # =====================================================

    def get_command_channel(
        self,
        guild: discord.Guild
    ):

        guild_config = self.config.get(
            str(guild.id),
            {}
        )

        channel_id = guild_config.get(
            "command_channel_id"
        )

        if not channel_id:
            return None

        channel = guild.get_channel(
            channel_id
        )

        if isinstance(
            channel,
            discord.TextChannel
        ):

            return channel

        return None

    # =====================================================
    # CLEAN COG NAME
    # =====================================================

    def clean_cog_name(
        self,
        cog_name
    ):

        if not cog_name:
            return "Other Commands"

        name = cog_name

        # Remove common words
        replacements = [
            "Cog",
            "System",
            "Commands"
        ]

        for word in replacements:

            name = name.replace(
                word,
                ""
            )

        name = name.strip()

        if not name:
            name = cog_name

        return name.upper()

    # =====================================================
    # GET ALL APPLICATION COMMANDS
    # =====================================================

    def get_all_commands(
        self,
        guild: discord.Guild
    ):

        """
        Gets commands from every loaded Cog.

        We use the bot's registered application
        command tree rather than manually defining
        the command list.
        """

        commands_list = []

        # -------------------------------------------------
        # GET COMMANDS FROM COGS
        # -------------------------------------------------

        for cog_name, cog in self.bot.cogs.items():

            try:

                cog_commands = cog.get_app_commands()

            except AttributeError:

                continue

            for command in cog_commands:

                commands_list.append(
                    (
                        cog_name,
                        command
                    )
                )

        # -------------------------------------------------
        # REMOVE DUPLICATES
        # -------------------------------------------------

        unique = {}

        for cog_name, command in commands_list:

            key = (
                cog_name,
                command.qualified_name
            )

            unique[key] = command

        return [
            (
                cog_name,
                command
            )

            for (
                cog_name,
                command
            ) in unique.items()
        ]

    # =====================================================
    # GET SUBCOMMANDS
    # =====================================================

    def get_command_text(
        self,
        command
    ):

        """
        Converts a Discord application command
        into a readable command string.
        """

        try:

            return f"`/{command.qualified_name}`"

        except AttributeError:

            return f"`/{command.name}`"

    # =====================================================
    # CREATE COMMAND EMBEDS
    # =====================================================

    def create_command_embeds(
        self,
        guild: discord.Guild
    ):

        grouped_commands = {}

        # -------------------------------------------------
        # COLLECT COMMANDS
        # -------------------------------------------------

        for cog_name, command in self.get_all_commands(
            guild
        ):

            if cog_name not in grouped_commands:

                grouped_commands[cog_name] = []

            grouped_commands[cog_name].append(
                command
            )

        # -------------------------------------------------
        # SORT COGS
        # -------------------------------------------------

        sorted_groups = sorted(

            grouped_commands.items(),

            key=lambda item: item[0].lower()
        )

        # -------------------------------------------------
        # NO COMMANDS
        # -------------------------------------------------

        if not sorted_groups:

            embed = discord.Embed(

                title="🤖 Bot Commands",

                description=(
                    "No slash commands were found "
                    "in the loaded cogs."
                ),

                color=discord.Color.blurple()
            )

            return [embed]

        embeds = []

        current_embed = discord.Embed(

            title="🤖 Bot Commands",

            description=(
                "All available commands for this server.\n\n"
                "Commands are automatically collected "
                "from every loaded cog."
            ),

            color=discord.Color.blurple()
        )

        if guild.icon:

            current_embed.set_thumbnail(
                url=guild.icon.url
            )

        command_count = 0

        # -------------------------------------------------
        # ADD COGS
        # -------------------------------------------------

        for cog_name, commands_list in sorted_groups:

            commands_list.sort(

                key=lambda command:
                command.qualified_name.lower()
            )

            command_lines = []

            for command in commands_list:

                command_lines.append(

                    f"{self.get_command_text(command)}"
                    f" — {command.description or 'No description'}"
                )

            cog_title = self.clean_cog_name(
                cog_name
            )

            field_value = "\n".join(
                command_lines
            )

            # Discord embed field limit
            if len(field_value) > 1000:

                chunks = []

                current_chunk = ""

                for line in command_lines:

                    if (
                        len(current_chunk)
                        + len(line)
                        + 1
                        > 1000
                    ):

                        chunks.append(
                            current_chunk
                        )

                        current_chunk = line

                    else:

                        if current_chunk:

                            current_chunk += "\n"

                        current_chunk += line

                if current_chunk:

                    chunks.append(
                        current_chunk
                    )

            else:

                chunks = [
                    field_value
                ]

            for index, chunk in enumerate(
                chunks
            ):

                if index == 0:

                    field_name = (
                        f"📁 {cog_title}"
                    )

                else:

                    field_name = (
                        f"📁 {cog_title} "
                        f"(continued)"
                    )

                # -------------------------------------------------
                # EMBED FIELD LIMIT
                # -------------------------------------------------

                if (
                    len(current_embed.fields) >= 25
                    or
                    len(current_embed) + len(chunk)
                    > 5900
                ):

                    embeds.append(
                        current_embed
                    )

                    current_embed = discord.Embed(

                        title=(
                            "🤖 Bot Commands "
                            "(continued)"
                        ),

                        color=discord.Color.blurple()
                    )

                current_embed.add_field(

                    name=field_name,

                    value=chunk,

                    inline=False
                )

                command_count += len(
                    command_lines
                )

        # -------------------------------------------------
        # FOOTER
        # -------------------------------------------------

        current_embed.set_footer(

            text=(
                f"{command_count} commands • "
                f"Automatically generated from "
                f"loaded cogs"
            )
        )

        embeds.append(
            current_embed
        )

        return embeds

    # =====================================================
    # CREATE COMMAND PANEL VIEW
    # =====================================================

    def create_view(self):

        return CommandPanelView(
            self
        )

    # =====================================================
    # UPDATE COMMAND PANEL
    # =====================================================

    async def update_command_panel(
        self,
        guild: discord.Guild
    ):

        channel = self.get_command_channel(
            guild
        )

        if channel is None:

            return False

        guild_config = self.get_guild_config(
            guild
        )

        message_ids = guild_config.get(
            "command_message_ids",
            []
        )

        embeds = self.create_command_embeds(
            guild
        )

        # -------------------------------------------------
        # TRY TO EDIT EXISTING MESSAGES
        # -------------------------------------------------

        existing_messages = []

        for message_id in message_ids:

            try:

                message = await channel.fetch_message(
                    message_id
                )

                existing_messages.append(
                    message
                )

            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):

                pass

        new_message_ids = []

        # -------------------------------------------------
        # UPDATE EXISTING
        # -------------------------------------------------

        for index, embed in enumerate(
            embeds
        ):

            if index < len(
                existing_messages
            ):

                try:

                    message = existing_messages[index]

                    if index == 0:

                        await message.edit(

                            embed=embed,

                            view=self.create_view()
                        )

                    else:

                        await message.edit(

                            embed=embed,

                            view=None
                        )

                    new_message_ids.append(
                        message.id
                    )

                except discord.HTTPException:

                    pass

            else:

                try:

                    if index == 0:

                        message = await channel.send(

                            embed=embed,

                            view=self.create_view()
                        )

                    else:

                        message = await channel.send(
                            embed=embed
                        )

                    new_message_ids.append(
                        message.id
                    )

                except (
                    discord.Forbidden,
                    discord.HTTPException
                ):

                    return False

        # -------------------------------------------------
        # DELETE EXTRA OLD MESSAGES
        # -------------------------------------------------

        if len(existing_messages) > len(
            embeds
        ):

            for message in existing_messages[
                len(embeds):
            ]:

                try:

                    await message.delete()

                except (
                    discord.NotFound,
                    discord.Forbidden,
                    discord.HTTPException
                ):

                    pass

        # -------------------------------------------------
        # SAVE MESSAGE IDS
        # -------------------------------------------------

        guild_config[
            "command_message_ids"
        ] = new_message_ids

        self.save_config()

        return True

    # =====================================================
    # /CMDSETUP
    # =====================================================

    @app_commands.command(

        name="cmdsetup",

        description=(
            "Set the channel for the bot command panel."
        )
    )
    @app_commands.describe(

        channel=(
            "The channel where all bot commands "
            "will be displayed."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def cmdsetup(

        self,

        interaction: discord.Interaction,

        channel: discord.TextChannel

    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(

                "❌ This command can only be used "
                "inside a server.",

                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        # -------------------------------------------------
        # SAVE CHANNEL
        # -------------------------------------------------

        guild_config = self.get_guild_config(
            guild
        )

        guild_config[
            "command_channel_id"
        ] = channel.id

        self.save_config()

        # -------------------------------------------------
        # CREATE PANEL
        # -------------------------------------------------

        success = await self.update_command_panel(
            guild
        )

        if not success:

            await interaction.followup.send(

                "❌ I couldn't create the command "
                "panel.\n\n"
                "Please make sure I have permission "
                "to **View Channel**, **Send Messages**, "
                "and **Embed Links** in the selected "
                "channel.",

                ephemeral=True
            )

            return

        await interaction.followup.send(

            f"✅ **Command system configured!**\n\n"
            f"📢 Channel: {channel.mention}\n\n"
            f"The panel now automatically displays "
            f"commands from **all loaded cogs**.",

            ephemeral=True
        )

    # =====================================================
    # /CMD
    # =====================================================

    @app_commands.command(

        name="cmd",

        description=(
            "Display all available bot commands."
        )
    )
    async def cmd(

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

        # -------------------------------------------------
        # MODERATOR CHECK
        # -------------------------------------------------

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(

                "❌ Only moderators can use `/cmd`.",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # CHECK CHANNEL
        # -------------------------------------------------

        command_channel = self.get_command_channel(
            guild
        )

        if command_channel is None:

            await interaction.response.send_message(

                "❌ The command channel has not "
                "been configured yet.\n\n"
                "An administrator needs to run:\n"
                "`/cmdsetup #channel`",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # FORCE CORRECT CHANNEL
        # -------------------------------------------------

        if interaction.channel.id != command_channel.id:

            await interaction.response.send_message(

                f"❌ Please use `/cmd` in "
                f"{command_channel.mention}.",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # UPDATE
        # -------------------------------------------------

        await interaction.response.defer(
            ephemeral=True
        )

        success = await self.update_command_panel(
            guild
        )

        if success:

            await interaction.followup.send(

                "✅ Command list refreshed.\n\n"
                "The panel has been updated with "
                "all commands currently registered "
                "from your bot's cogs.",

                ephemeral=True
            )

        else:

            await interaction.followup.send(

                "❌ I couldn't update the command panel.",

                ephemeral=True
            )

    # =====================================================
    # ERROR HANDLER
    # =====================================================

    @cmdsetup.error
    async def cmdsetup_error(

        self,

        interaction: discord.Interaction,

        error

    ):

        if isinstance(

            error,

            app_commands.errors.MissingPermissions

        ):

            message = (
                "❌ You need **Administrator** "
                "permission to use `/cmdsetup`."
            )

        else:

            print(
                f"CMDSETUP ERROR: {error}"
            )

            message = (
                "❌ An error occurred while "
                "configuring the command system."
            )

        if interaction.response.is_done():

            await interaction.followup.send(

                message,

                ephemeral=True
            )

        else:

            await interaction.response.send_message(

                message,

                ephemeral=True
            )

    # =====================================================
    # COG LOAD
    # =====================================================

    async def cog_load(self):

        # Persistent button
        self.bot.add_view(
            CommandPanelView(
                self
            )
        )


# =========================================================
# COMMAND PANEL VIEW
# =========================================================

class CommandPanelView(
    discord.ui.View
):

    def __init__(
        self,
        cog
    ):

        super().__init__(
            timeout=None
        )

        self.cog = cog

    # =====================================================
    # REFRESH BUTTON
    # =====================================================

    @discord.ui.button(

        label="Refresh Commands",

        emoji="🔄",

        style=discord.ButtonStyle.secondary,

        custom_id="command_panel_refresh"
    )
    async def refresh(

        self,

        interaction: discord.Interaction,

        button: discord.ui.Button

    ):

        # -------------------------------------------------
        # SERVER CHECK
        # -------------------------------------------------

        if interaction.guild is None:

            await interaction.response.send_message(

                "❌ This button can only be used "
                "inside a server.",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # MODERATOR CHECK
        # -------------------------------------------------

        if not is_moderator(
            interaction.user
        ):

            await interaction.response.send_message(

                "❌ Only moderators can refresh "
                "the command list.",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # CHANNEL CHECK
        # -------------------------------------------------

        command_channel = (
            self.cog.get_command_channel(
                interaction.guild
            )
        )

        if command_channel is None:

            await interaction.response.send_message(

                "❌ The command channel is "
                "not configured.",

                ephemeral=True
            )

            return

        if (
            interaction.channel.id
            != command_channel.id
        ):

            await interaction.response.send_message(

                f"❌ Please use the command panel "
                f"in {command_channel.mention}.",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # REFRESH
        # -------------------------------------------------

        await interaction.response.defer(
            ephemeral=True
        )

        success = await self.cog.update_command_panel(
            interaction.guild
        )

        if success:

            await interaction.followup.send(

                "✅ Command list refreshed.",

                ephemeral=True
            )

        else:

            await interaction.followup.send(

                "❌ Failed to refresh the "
                "command list.",

                ephemeral=True
            )


# =========================================================
# COG SETUP
# =========================================================

async def setup(bot):

    await bot.add_cog(
        CommandSystem(bot)
    )


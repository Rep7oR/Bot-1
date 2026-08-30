
import discord
from discord.ext import commands
from discord import app_commands

import json
import os


# ============================================================
# CONFIGURATION
# ============================================================

CONFIG_FILE = "cmd_config.json"

MODERATOR_ROLE_NAMES = [
    "MODERATOR",
    "Moderators",
    "Moderator",
    "Mod"
]


# ============================================================
# JSON FUNCTIONS
# ============================================================

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

    except Exception as e:

        print(
            f"❌ Could not load {CONFIG_FILE}: {e}"
        )

        return {}


def save_config(data):

    try:

        with open(
            CONFIG_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4
            )

    except Exception as e:

        print(
            f"❌ Could not save {CONFIG_FILE}: {e}"
        )


# ============================================================
# MODERATOR CHECK
# ============================================================

def is_moderator(
    member: discord.Member
):

    if member.guild_permissions.administrator:
        return True

    for role in member.roles:

        if role.name in MODERATOR_ROLE_NAMES:
            return True

    return False


# ============================================================
# COMMAND SYSTEM
# ============================================================

class CommandSystem(commands.Cog):

    def __init__(
        self,
        bot: commands.Bot
    ):

        self.bot = bot

        self.config = load_config()

        print(
            "✅ Command System loaded."
        )

    # ========================================================
    # GET GUILD CONFIG
    # ========================================================

    def get_guild_config(
        self,
        guild_id: int
    ):

        guild_id = str(guild_id)

        if guild_id not in self.config:

            self.config[guild_id] = {}

        return self.config[guild_id]

    # ========================================================
    # GET COMMAND CHANNEL
    # ========================================================

    def get_command_channel(
        self,
        guild: discord.Guild
    ):

        guild_config = self.config.get(
            str(guild.id),
            {}
        )

        channel_id = guild_config.get(
            "channel_id"
        )

        if not channel_id:
            return None

        channel = guild.get_channel(
            int(channel_id)
        )

        if isinstance(
            channel,
            discord.TextChannel
        ):

            return channel

        return None

    # ========================================================
    # GET ALL REGISTERED COMMANDS
    # ========================================================

    def get_all_commands(self):

        """
        Gets commands directly from the bot's
        application command tree.

        This means the command panel shows commands
        that are actually registered with Discord.
        """

        try:

            return self.bot.tree.get_commands()

        except Exception as e:

            print(
                f"❌ Could not get application commands: {e}"
            )

            return []

    # ========================================================
    # GET COMMAND COG NAME
    # ========================================================

    def get_cog_name(
        self,
        command
    ):

        """
        Attempts to identify which Cog owns
        the application command.
        """

        # ----------------------------------------------------
        # Try command callback
        # ----------------------------------------------------

        callback = getattr(
            command,
            "callback",
            None
        )

        if callback:

            callback_self = getattr(
                callback,
                "__self__",
                None
            )

            if callback_self:

                cog_name = getattr(
                    callback_self,
                    "qualified_name",
                    None
                )

                if cog_name:

                    return cog_name

                cog_name = getattr(
                    callback_self,
                    "__class__",
                    type(
                        "x",
                        (),
                        {}
                    )
                ).__name__

                if cog_name:

                    return cog_name

        # ----------------------------------------------------
        # Try binding
        # ----------------------------------------------------

        binding = getattr(
            command,
            "binding",
            None
        )

        if binding:

            cog_name = getattr(
                binding,
                "qualified_name",
                None
            )

            if cog_name:

                return cog_name

            cog_name = binding.__class__.__name__

            if cog_name:

                return cog_name

        # ----------------------------------------------------
        # Fallback
        # ----------------------------------------------------

        return "Other Commands"

    # ========================================================
    # CLEAN COG NAME
    # ========================================================

    def clean_cog_name(
        self,
        name: str
    ):

        replacements = [
            "Commands",
            "Command",
            "System",
            "Manager",
            "Cog"
        ]

        cleaned = name

        for word in replacements:

            cleaned = cleaned.replace(
                word,
                ""
            )

        cleaned = cleaned.strip()

        if not cleaned:

            cleaned = name

        return cleaned.upper()

    # ========================================================
    # COMMAND DESCRIPTION
    # ========================================================

    def get_description(
        self,
        command
    ):

        description = getattr(
            command,
            "description",
            None
        )

        if not description:

            return "No description available."

        return description

    # ========================================================
    # FORMAT COMMAND
    # ========================================================

    def format_command(
        self,
        command
    ):

        try:

            command_name = command.qualified_name

        except AttributeError:

            command_name = command.name

        description = self.get_description(
            command
        )

        return (
            f"`/{command_name}`\n"
            f"↳ {description}"
        )

    # ========================================================
    # CREATE EMBEDS
    # ========================================================

    def create_embeds(
        self,
        guild: discord.Guild
    ):

        commands_list = self.get_all_commands()

        # ----------------------------------------------------
        # Remove default Discord commands that are not
        # actually application commands in this bot.
        # ----------------------------------------------------

        valid_commands = []

        for command in commands_list:

            if not isinstance(
                command,
                app_commands.Command
            ):

                continue

            valid_commands.append(
                command
            )

        # ----------------------------------------------------
        # Sort
        # ----------------------------------------------------

        valid_commands.sort(

            key=lambda command:
            command.qualified_name.lower()
        )

        # ----------------------------------------------------
        # Nothing found
        # ----------------------------------------------------

        if not valid_commands:

            embed = discord.Embed(

                title="🤖 Bot Commands",

                description=(

                    "No application commands are "
                    "currently registered.\n\n"

                    "Make sure your cogs are loaded "
                    "and your slash commands are synced."
                ),

                color=discord.Color.red()
            )

            if guild.icon:

                embed.set_thumbnail(
                    url=guild.icon.url
                )

            return [embed]

        # ----------------------------------------------------
        # GROUP COMMANDS BY COG
        # ----------------------------------------------------

        grouped = {}

        for command in valid_commands:

            cog_name = self.get_cog_name(
                command
            )

            if cog_name not in grouped:

                grouped[cog_name] = []

            grouped[cog_name].append(
                command
            )

        # ----------------------------------------------------
        # CREATE EMBEDS
        # ----------------------------------------------------

        embeds = []

        current_embed = discord.Embed(

            title="🤖 Bot Commands",

            description=(

                "All available commands for this bot.\n\n"

                "Commands are automatically collected "
                "from the bot's loaded application commands."
            ),

            color=discord.Color.blurple()
        )

        if guild.icon:

            current_embed.set_thumbnail(
                url=guild.icon.url
            )

        total_commands = 0

        field_count = 0

        # ----------------------------------------------------
        # GROUPS
        # ----------------------------------------------------

        for cog_name in sorted(
            grouped.keys(),
            key=lambda x: x.lower()
        ):

            command_lines = []

            commands_in_cog = grouped[
                cog_name
            ]

            commands_in_cog.sort(

                key=lambda command:
                command.qualified_name.lower()
            )

            for command in commands_in_cog:

                command_lines.append(

                    self.format_command(
                        command
                    )
                )

            field_value = "\n\n".join(
                command_lines
            )

            cog_title = self.clean_cog_name(
                cog_name
            )

            # ------------------------------------------------
            # Discord field limit
            # ------------------------------------------------

            if len(field_value) > 1024:

                chunks = []

                current_chunk = ""

                for line in command_lines:

                    if len(
                        current_chunk
                    ) + len(line) + 2 > 1024:

                        if current_chunk:

                            chunks.append(
                                current_chunk
                            )

                        current_chunk = line

                    else:

                        if current_chunk:

                            current_chunk += "\n\n"

                        current_chunk += line

                if current_chunk:

                    chunks.append(
                        current_chunk
                    )

            else:

                chunks = [
                    field_value
                ]

            # ------------------------------------------------
            # ADD FIELDS
            # ------------------------------------------------

            for index, chunk in enumerate(
                chunks
            ):

                if field_count >= 25:

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

                    field_count = 0

                if index == 0:

                    field_name = (
                        f"📁 {cog_title}"
                    )

                else:

                    field_name = (
                        f"📁 {cog_title} "
                        "(continued)"
                    )

                current_embed.add_field(

                    name=field_name,

                    value=chunk,

                    inline=False
                )

                field_count += 1

                total_commands += len(
                    commands_in_cog
                ) if index == 0 else 0

        # ----------------------------------------------------
        # FOOTER
        # ----------------------------------------------------

        current_embed.set_footer(

            text=(
                f"{total_commands} commands • "
                "Automatically generated"
            )
        )

        embeds.append(
            current_embed
        )

        return embeds

    # ========================================================
    # CREATE VIEW
    # ========================================================

    def create_panel_view(self):

        return CommandPanelView(
            self
        )

    # ========================================================
    # UPDATE PANEL
    # ========================================================

    async def update_panel(
        self,
        guild: discord.Guild
    ):

        channel = self.get_command_channel(
            guild
        )

        if channel is None:

            print(
                f"❌ Command channel not configured "
                f"for {guild.name}"
            )

            return False

        embeds = self.create_embeds(
            guild
        )

        guild_config = self.get_guild_config(
            guild.id
        )

        saved_message_ids = guild_config.get(
            "message_ids",
            []
        )

        existing_messages = []

        # ----------------------------------------------------
        # Fetch old messages
        # ----------------------------------------------------

        for message_id in saved_message_ids:

            try:

                message = await channel.fetch_message(
                    int(message_id)
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

        # ----------------------------------------------------
        # Edit / create
        # ----------------------------------------------------

        for index, embed in enumerate(
            embeds
        ):

            try:

                if index < len(
                    existing_messages
                ):

                    message = existing_messages[
                        index
                    ]

                    if index == 0:

                        await message.edit(

                            embed=embed,

                            view=self.create_panel_view()
                        )

                    else:

                        await message.edit(

                            embed=embed,

                            view=None
                        )

                    new_message_ids.append(
                        message.id
                    )

                else:

                    if index == 0:

                        message = await channel.send(

                            embed=embed,

                            view=self.create_panel_view()
                        )

                    else:

                        message = await channel.send(

                            embed=embed
                        )

                    new_message_ids.append(
                        message.id
                    )

            except discord.Forbidden:

                print(
                    "❌ Bot does not have permission "
                    "to send/edit messages."
                )

                return False

            except discord.HTTPException as e:

                print(
                    f"❌ Discord error updating "
                    f"command panel: {e}"
                )

                return False

        # ----------------------------------------------------
        # Delete old extra messages
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Save IDs
        # ----------------------------------------------------

        guild_config[
            "message_ids"
        ] = new_message_ids

        save_config(
            self.config
        )

        print(
            f"✅ Command panel updated "
            f"for {guild.name}"
        )

        return True

    # ========================================================
    # /CMDSETUP
    # ========================================================

    @app_commands.command(

        name="cmdsetup",

        description=(
            "Set the channel for the bot command list."
        )
    )
    @app_commands.describe(

        channel=(
            "Channel where the command list "
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

        # ----------------------------------------------------
        # SERVER CHECK
        # ----------------------------------------------------

        if interaction.guild is None:

            await interaction.response.send_message(

                "❌ This command can only be used "
                "inside a server.",

                ephemeral=True
            )

            return

        guild = interaction.guild

        # ----------------------------------------------------
        # DEFER
        # ----------------------------------------------------

        await interaction.response.defer(
            ephemeral=True
        )

        # ----------------------------------------------------
        # SAVE CHANNEL
        # ----------------------------------------------------

        guild_config = self.get_guild_config(
            guild.id
        )

        guild_config[
            "channel_id"
        ] = channel.id

        save_config(
            self.config
        )

        # ----------------------------------------------------
        # UPDATE PANEL
        # ----------------------------------------------------

        success = await self.update_panel(
            guild
        )

        if not success:

            await interaction.followup.send(

                "❌ **Command setup failed.**\n\n"

                f"I could not create the command panel "
                f"in {channel.mention}.\n\n"

                "Please check that the bot has:\n"
                "• View Channel\n"
                "• Send Messages\n"
                "• Embed Links\n"
                "• Read Message History",

                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        command_count = len(
            self.get_all_commands()
        )

        await interaction.followup.send(

            f"✅ **Command system configured!**\n\n"

            f"📢 Channel: {channel.mention}\n"
            f"🤖 Commands detected: `{command_count}`\n\n"

            "The command panel will automatically "
            "use the bot's registered slash commands.",

            ephemeral=True
        )

    # ========================================================
    # /CMD
    # ========================================================

    @app_commands.command(

        name="cmd",

        description=(
            "Refresh and display all bot commands."
        )
    )
    async def cmd(

        self,

        interaction: discord.Interaction

    ):

        # ----------------------------------------------------
        # SERVER CHECK
        # ----------------------------------------------------

        if interaction.guild is None:

            await interaction.response.send_message(

                "❌ This command can only be used "
                "inside a server.",

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

                "❌ Only moderators can use `/cmd`.",

                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # CHANNEL CHECK
        # ----------------------------------------------------

        command_channel = (
            self.get_command_channel(
                interaction.guild
            )
        )

        if command_channel is None:

            await interaction.response.send_message(

                "❌ The command system has not "
                "been configured yet.\n\n"

                "Ask an administrator to use:\n"
                "`/cmdsetup #channel`",

                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # ONLY USE IN CONFIGURED CHANNEL
        # ----------------------------------------------------

        if (
            interaction.channel.id
            != command_channel.id
        ):

            await interaction.response.send_message(

                f"❌ Please use `/cmd` in "
                f"{command_channel.mention}.",

                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # REFRESH
        # ----------------------------------------------------

        await interaction.response.defer(
            ephemeral=True
        )

        success = await self.update_panel(
            interaction.guild
        )

        if success:

            await interaction.followup.send(

                "✅ **Command list refreshed.**\n\n"
                "The panel now contains all "
                "currently registered bot commands.",

                ephemeral=True
            )

        else:

            await interaction.followup.send(

                "❌ I couldn't refresh the "
                "command panel.",

                ephemeral=True
            )

    # ========================================================
    # CMDSETUP ERROR
    # ========================================================

    @cmdsetup.error
    async def cmdsetup_error(

        self,

        interaction: discord.Interaction,

        error

    ):

        print(
            f"❌ /cmdsetup error: "
            f"{repr(error)}"
        )

        if isinstance(
            error,
            app_commands.errors.MissingPermissions
        ):

            message = (
                "❌ You need **Administrator** "
                "permission to use `/cmdsetup`."
            )

        elif isinstance(
            error,
            app_commands.errors.CommandInvokeError
        ):

            original = getattr(
                error,
                "original",
                error
            )

            message = (
                "❌ An error occurred while "
                "running `/cmdsetup`.\n\n"
                f"```{original}```"
            )

        else:

            message = (
                "❌ An error occurred while "
                "running `/cmdsetup`.\n\n"
                f"```{error}```"
            )

        try:

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

        except Exception as e:

            print(
                f"❌ Could not send error response: {e}"
            )


# ============================================================
# COMMAND PANEL VIEW
# ============================================================

class CommandPanelView(
    discord.ui.View
):

    def __init__(
        self,
        cog: CommandSystem
    ):

        super().__init__(
            timeout=None
        )

        self.cog = cog

    # ========================================================
    # REFRESH BUTTON
    # ========================================================

    @discord.ui.button(

        label="Refresh Commands",

        emoji="🔄",

        style=discord.ButtonStyle.secondary,

        custom_id="cmd_panel_refresh"
    )
    async def refresh_commands(

        self,

        interaction: discord.Interaction,

        button: discord.ui.Button

    ):

        # ----------------------------------------------------
        # SERVER CHECK
        # ----------------------------------------------------

        if interaction.guild is None:

            await interaction.response.send_message(

                "❌ This can only be used "
                "inside a server.",

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

                "❌ Only moderators can refresh "
                "the command list.",

                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # CHANNEL CHECK
        # ----------------------------------------------------

        configured_channel = (
            self.cog.get_command_channel(
                interaction.guild
            )
        )

        if configured_channel is None:

            await interaction.response.send_message(

                "❌ The command system has "
                "not been configured.",

                ephemeral=True
            )

            return

        if (
            interaction.channel.id
            != configured_channel.id
        ):

            await interaction.response.send_message(

                f"❌ Please use this button in "
                f"{configured_channel.mention}.",

                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # REFRESH
        # ----------------------------------------------------

        await interaction.response.defer(
            ephemeral=True
        )

        success = await self.cog.update_panel(
            interaction.guild
        )

        if success:

            await interaction.followup.send(

                "✅ Command list refreshed.",

                ephemeral=True
            )

        else:

            await interaction.followup.send(

                "❌ Failed to refresh "
                "the command list.",

                ephemeral=True
            )


# ============================================================
# COG SETUP
# ============================================================

async def setup(
    bot: commands.Bot
):

    await bot.add_cog(
        CommandSystem(bot)
    )


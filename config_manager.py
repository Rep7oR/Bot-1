import discord
from discord.ext import commands
from discord import app_commands

import traceback

from config_manager import config_manager


# ============================================================
# REFRESH SYSTEM
# ============================================================

class Refresh(commands.Cog):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        print(
            "🔄 Refresh System loaded."
        )

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
    # FORMAT CONFIGURATION
    # ========================================================

    def format_config(
        self,
        guild,
        config,
        indent=0
    ):

        lines = []

        if not isinstance(
            config,
            dict
        ):

            return [
                str(config)
            ]

        for key, value in config.items():

            display_key = str(
                key
            ).replace(
                "_",
                " "
            ).title()

            # ------------------------------------------------
            # Nested dictionary
            # ------------------------------------------------

            if isinstance(
                value,
                dict
            ):

                lines.append(
                    f"**{display_key}:**"
                )

                nested = (
                    self.format_config(
                        guild,
                        value,
                        indent + 1
                    )
                )

                for line in nested:

                    lines.append(
                        "  " + line
                    )

            # ------------------------------------------------
            # List
            # ------------------------------------------------

            elif isinstance(
                value,
                list
            ):

                if not value:

                    lines.append(
                        f"**{display_key}:** None"
                    )

                else:

                    lines.append(
                        f"**{display_key}:** "
                        + ", ".join(
                            str(x)
                            for x in value
                        )
                    )

            # ------------------------------------------------
            # IDs
            # ------------------------------------------------

            elif (
                "channel" in key.lower()
                and "id" in key.lower()
            ):

                channel = (
                    self.get_channel(
                        guild,
                        value
                    )
                )

                if channel:

                    value = channel.mention

                else:

                    value = (
                        f"Missing (`{value}`)"
                    )

                lines.append(
                    f"**{display_key}:** {value}"
                )

            elif (
                "role" in key.lower()
                and "id" in key.lower()
            ):

                role = (
                    self.get_role(
                        guild,
                        value
                    )
                )

                if role:

                    value = role.mention

                else:

                    value = (
                        f"Missing (`{value}`)"
                    )

                lines.append(
                    f"**{display_key}:** {value}"
                )

            # ------------------------------------------------
            # Normal value
            # ------------------------------------------------

            else:

                if isinstance(
                    value,
                    bool
                ):

                    value = (
                        "Enabled"
                        if value
                        else "Disabled"
                    )

                lines.append(
                    f"**{display_key}:** "
                    f"`{value}`"
                )

        return lines

    # ========================================================
    # GET COMMANDS FOR COG
    # ========================================================

    def get_commands_for_cog(
        self,
        cog
    ):

        commands_found = []

        # ----------------------------------------------------
        # Slash commands
        # ----------------------------------------------------

        for command in (
            self.bot.tree.walk_commands()
        ):

            try:

                binding = getattr(
                    command,
                    "binding",
                    None
                )

                if binding is cog:

                    commands_found.append(
                        f"/{command.qualified_name}"
                    )

            except Exception:

                pass

        # ----------------------------------------------------
        # Prefix commands
        # ----------------------------------------------------

        for command in self.bot.commands:

            try:

                command_cog = getattr(
                    command,
                    "cog",
                    None
                )

                if command_cog is cog:

                    commands_found.append(
                        f"!{command.name}"
                    )

            except Exception:

                pass

        return sorted(
            set(commands_found)
        )

    # ========================================================
    # CHECK DISCORD OBJECTS
    # ========================================================

    def check_config_objects(
        self,
        guild,
        config
    ):

        missing = []
        existing = []

        def check_dictionary(
            data,
            parent_key=""
        ):

            if not isinstance(
                data,
                dict
            ):

                return

            for key, value in data.items():

                key_lower = key.lower()

                # --------------------------------------------
                # Channel ID
                # --------------------------------------------

                if (
                    "channel" in key_lower
                    and key_lower.endswith("id")
                ):

                    channel = (
                        self.get_channel(
                            guild,
                            value
                        )
                    )

                    if channel:

                        existing.append(
                            f"#{channel.name}"
                        )

                    else:

                        missing.append(
                            f"channel `{value}`"
                        )

                # --------------------------------------------
                # Role ID
                # --------------------------------------------

                elif (
                    "role" in key_lower
                    and key_lower.endswith("id")
                ):

                    role = (
                        self.get_role(
                            guild,
                            value
                        )
                    )

                    if role:

                        existing.append(
                            f"@{role.name}"
                        )

                    else:

                        missing.append(
                            f"role `{value}`"
                        )

                # --------------------------------------------
                # Nested
                # --------------------------------------------

                elif isinstance(
                    value,
                    dict
                ):

                    check_dictionary(
                        value,
                        key
                    )

        check_dictionary(
            config
        )

        return (
            existing,
            missing
        )

    # ========================================================
    # REFRESH ONE COG
    # ========================================================

    async def refresh_cog(
        self,
        cog_name,
        cog,
        guild
    ):

        # ----------------------------------------------------
        # Read persistent configuration
        # ----------------------------------------------------

        saved_config = (
            config_manager.get(
                guild.id,
                cog_name
            )
        )

        # ----------------------------------------------------
        # Custom refresh method
        # ----------------------------------------------------

        refresh_method = getattr(
            cog,
            "refresh",
            None
        )

        if callable(
            refresh_method
        ):

            try:

                result = (
                    await refresh_method()
                )

                if isinstance(
                    result,
                    dict
                ):

                    return {
                        "status": result.get(
                            "status",
                            "✅"
                        ),
                        "message": result.get(
                            "message",
                            "Refresh completed."
                        ),
                        "config": saved_config
                    }

                return {
                    "status": "✅",
                    "message": (
                        str(result)
                        if result
                        else "Refresh completed."
                    ),
                    "config": saved_config
                }

            except Exception as e:

                traceback.print_exc()

                return {
                    "status": "❌",
                    "message": (
                        f"{type(e).__name__}: {e}"
                    ),
                    "config": saved_config
                }

        # ----------------------------------------------------
        # No custom refresh method
        # ----------------------------------------------------

        if saved_config:

            existing, missing = (
                self.check_config_objects(
                    guild,
                    saved_config
                )
            )

            if missing:

                message = (
                    "Saved configuration found, "
                    "but some Discord objects are missing."
                )

                status = "⚠️"

            else:

                message = (
                    "Saved configuration found "
                    "and checked."
                )

                status = "✅"

            return {
                "status": status,
                "message": message,
                "config": saved_config,
                "existing": existing,
                "missing": missing
            }

        # ----------------------------------------------------
        # No configuration
        # ----------------------------------------------------

        return {
            "status": "⚪",
            "message": (
                "No saved configuration."
            ),
            "config": {}
        }

    # ========================================================
    # /REFRESH
    # ========================================================

    @app_commands.command(
        name="refresh",
        description=(
            "Check all bot systems and saved setup."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def refresh(
        self,
        interaction: discord.Interaction
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        guild = interaction.guild

        results = []

        # ====================================================
        # CHECK EVERY COG
        # ====================================================

        for cog_name, cog in self.bot.cogs.items():

            if cog_name == "Refresh":

                continue

            print(
                f"🔄 Refreshing {cog_name}"
            )

            result = (
                await self.refresh_cog(
                    cog_name,
                    cog,
                    guild
                )
            )

            result["commands"] = (
                self.get_commands_for_cog(
                    cog
                )
            )

            results.append(
                (
                    cog_name,
                    result
                )
            )

        # ====================================================
        # BUILD REPORT
        # ====================================================

        embeds = []

        embed = discord.Embed(

            title="🔄 Bot Configuration",

            description=(
                f"Complete configuration report "
                f"for **{guild.name}**"
            ),

            color=discord.Color.blue()
        )

        field_count = 0

        successful = 0
        warnings = 0
        errors = 0
        unconfigured = 0
        command_count = 0

        for cog_name, result in results:

            status = result.get(
                "status",
                "⚪"
            )

            message = result.get(
                "message",
                ""
            )

            config = result.get(
                "config",
                {}
            )

            commands_list = result.get(
                "commands",
                []
            )

            existing = result.get(
                "existing",
                []
            )

            missing = result.get(
                "missing",
                []
            )

            # ------------------------------------------------
            # Counters
            # ------------------------------------------------

            if status == "✅":

                successful += 1

            elif status == "⚠️":

                warnings += 1

            elif status == "❌":

                errors += 1

            else:

                unconfigured += 1

            command_count += len(
                commands_list
            )

            # ------------------------------------------------
            # Configuration text
            # ------------------------------------------------

            config_lines = (
                self.format_config(
                    guild,
                    config
                )
            )

            if config_lines:

                config_text = "\n".join(
                    config_lines
                )

            else:

                config_text = (
                    "No saved setup."
                )

            # ------------------------------------------------
            # Existing objects
            # ------------------------------------------------

            if existing:

                existing_text = (
                    "\n\n"
                    "📍 **Existing:**\n"
                    + ", ".join(existing[:10])
                )

            else:

                existing_text = ""

            # ------------------------------------------------
            # Missing objects
            # ------------------------------------------------

            if missing:

                missing_text = (
                    "\n\n"
                    "⚠️ **Missing:**\n"
                    + ", ".join(missing[:10])
                )

            else:

                missing_text = ""

            # ------------------------------------------------
            # Commands
            # ------------------------------------------------

            if commands_list:

                commands_text = (
                    "\n".join(
                        f"`{x}`"
                        for x in commands_list
                    )
                )

            else:

                commands_text = (
                    "No commands."
                )

            # Keep Discord field below 1024 chars
            value = (
                f"{status} **{message}**\n\n"
                f"⚙️ **Setup:**\n"
                f"{config_text}"
                f"{existing_text}"
                f"{missing_text}\n\n"
                f"🛠️ **Commands:**\n"
                f"{commands_text}"
            )

            if len(value) > 1000:

                value = (
                    value[:970]
                    + "\n..."
                )

            embed.add_field(

                name=f"📦 {cog_name}",

                value=value,

                inline=False
            )

            field_count += 1

            # Discord maximum is 25 fields.
            # Keep room for summary.

            if field_count >= 20:

                embeds.append(
                    embed
                )

                embed = discord.Embed(

                    title=(
                        "🔄 Bot Configuration "
                        "— Continued"
                    ),

                    color=discord.Color.blue()
                )

                field_count = 0

        # ----------------------------------------------------
        # Remaining embed
        # ----------------------------------------------------

        if field_count:

            embeds.append(
                embed
            )

        # ====================================================
        # SUMMARY
        # ====================================================

        summary = discord.Embed(

            title="📊 Refresh Summary",

            description=(

                f"📦 **Cogs checked:** "
                f"`{len(results)}`\n\n"

                f"✅ **Configured:** "
                f"`{successful}`\n"

                f"⚠️ **Warnings:** "
                f"`{warnings}`\n"

                f"❌ **Errors:** "
                f"`{errors}`\n"

                f"⚪ **Not configured:** "
                f"`{unconfigured}`\n\n"

                f"⚙️ **Commands detected:** "
                f"`{command_count}`"
            ),

            color=(
                discord.Color.green()
                if errors == 0
                else discord.Color.red()
            )
        )

        summary.set_footer(
            text=(
                f"Requested by "
                f"{interaction.user}"
            )
        )

        # ====================================================
        # SEND
        # ====================================================

        for report in embeds:

            await interaction.followup.send(
                embed=report,
                ephemeral=True
            )

        await interaction.followup.send(
            embed=summary,
            ephemeral=True
        )

    # ========================================================
    # ERROR
    # ========================================================

    @refresh.error
    async def refresh_error(
        self,
        interaction,
        error
    ):

        if isinstance(
            error,
            app_commands.errors.MissingPermissions
        ):

            message = (
                "❌ You need Administrator "
                "permission to use `/refresh`."
            )

        else:

            traceback.print_exc()

            message = (
                "❌ Refresh failed:\n"
                f"`{type(error).__name__}: {error}`"
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

        except Exception:

            pass


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        Refresh(bot)
    )

    print(
        "✅ Refresh Cog ready."
    )

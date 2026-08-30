import discord
from discord.ext import commands
from discord import app_commands

import json
import os
import traceback


# ============================================================
# CONFIGURATION
# ============================================================

CONFIG_FILE = "bot_config.json"


# ============================================================
# LOAD CONFIGURATION
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
            f"❌ Config load error: {e}"
        )

        return {}


# ============================================================
# SAVE CONFIGURATION
# ============================================================

def save_config(config):

    try:

        with open(
            CONFIG_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                config,
                f,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as e:

        print(
            f"❌ Config save error: {e}"
        )

        return False


# ============================================================
# REFRESH COG
# ============================================================

class Refresh(commands.Cog):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        self.config = load_config()

        print(
            "🔄 Refresh Cog loaded."
        )

    # ========================================================
    # GET GUILD CONFIG
    # ========================================================

    def get_guild_config(
        self,
        guild_id
    ):

        guild_id = str(
            guild_id
        )

        if guild_id not in self.config:

            self.config[guild_id] = {}

        return self.config[guild_id]

    # ========================================================
    # SAVE GUILD CONFIG
    # ========================================================

    def save_guild_config(
        self,
        guild_id,
        cog_name,
        data
    ):

        guild_config = self.get_guild_config(
            guild_id
        )

        guild_config[cog_name] = data

        save_config(
            self.config
        )

    # ========================================================
    # GET CHANNEL NAME
    # ========================================================

    def channel_name(
        self,
        guild,
        channel_id
    ):

        if not channel_id:

            return "Not configured"

        try:

            channel = guild.get_channel(
                int(channel_id)
            )

            if channel:

                return channel.mention

        except Exception:

            pass

        return (
            f"Deleted/Missing "
            f"(`{channel_id}`)"
        )

    # ========================================================
    # GET ROLE NAME
    # ========================================================

    def role_name(
        self,
        guild,
        role_id
    ):

        if not role_id:

            return "Not configured"

        try:

            role = guild.get_role(
                int(role_id)
            )

            if role:

                return role.mention

        except Exception:

            pass

        return (
            f"Deleted/Missing "
            f"(`{role_id}`)"
        )

    # ========================================================
    # GET CATEGORY NAME
    # ========================================================

    def category_name(
        self,
        guild,
        category_id
    ):

        if not category_id:

            return "Not configured"

        try:

            category = guild.get_channel(
                int(category_id)
            )

            if category:

                return category.name

        except Exception:

            pass

        return (
            f"Deleted/Missing "
            f"(`{category_id}`)"
        )

    # ========================================================
    # DISCOVER COMMANDS
    # ========================================================

    def get_commands_for_cog(
        self,
        cog
    ):

        found = []

        # ----------------------------------------------------
        # SLASH COMMANDS
        # ----------------------------------------------------

        for command in self.bot.tree.walk_commands():

            try:

                binding = getattr(
                    command,
                    "binding",
                    None
                )

                if binding is cog:

                    found.append(
                        f"/{command.qualified_name}"
                    )

            except Exception:

                continue

        # ----------------------------------------------------
        # PREFIX COMMANDS
        # ----------------------------------------------------

        for command in self.bot.commands:

            try:

                command_cog = getattr(
                    command,
                    "cog",
                    None
                )

                if command_cog is cog:

                    found.append(
                        f"!{command.name}"
                    )

            except Exception:

                continue

        return sorted(
            set(found)
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
        # First preference:
        #
        # get_setup_info()
        # ----------------------------------------------------

        setup_info = getattr(
            cog,
            "get_setup_info",
            None
        )

        # ----------------------------------------------------
        # If cog provides setup information
        # ----------------------------------------------------

        if callable(
            setup_info
        ):

            try:

                result = await setup_info(
                    guild
                )

                if isinstance(
                    result,
                    dict
                ):

                    return result

                return {
                    "status": "✅",
                    "message": str(
                        result
                    )
                }

            except TypeError:

                # Some cogs may use
                # get_setup_info() without guild

                try:

                    result = await setup_info()

                    if isinstance(
                        result,
                        dict
                    ):

                        return result

                    return {
                        "status": "✅",
                        "message": str(
                            result
                        )
                    }

                except Exception as e:

                    return {
                        "status": "❌",
                        "message": (
                            f"{type(e).__name__}: {e}"
                        )
                    }

            except Exception as e:

                traceback.print_exc()

                return {
                    "status": "❌",
                    "message": (
                        f"{type(e).__name__}: {e}"
                    )
                }

        # ----------------------------------------------------
        # Second preference:
        #
        # refresh()
        # ----------------------------------------------------

        refresh_function = getattr(
            cog,
            "refresh",
            None
        )

        if callable(
            refresh_function
        ):

            try:

                result = await refresh_function()

                if isinstance(
                    result,
                    dict
                ):

                    return result

                return {
                    "status": "✅",
                    "message": (
                        str(result)
                        if result
                        else "Refresh completed."
                    )
                }

            except Exception as e:

                traceback.print_exc()

                return {
                    "status": "❌",
                    "message": (
                        f"{type(e).__name__}: {e}"
                    )
                }

        # ----------------------------------------------------
        # No setup handler
        # ----------------------------------------------------

        return {
            "status": "⚪",
            "message": (
                "No configuration reader "
                "in this Cog."
            )
        }

    # ========================================================
    # /REFRESH
    # ========================================================

    @app_commands.command(
        name="refresh",
        description=(
            "Check and display all bot configuration."
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
                "❌ This command can only be used in a server.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        guild = interaction.guild

        print("")
        print(
            "========================================"
        )
        print(
            "        MASTER CONFIG REFRESH"
        )
        print(
            "========================================"
        )

        results = []

        # ====================================================
        # CHECK EVERY LOADED COG
        # ====================================================

        for cog_name, cog in self.bot.cogs.items():

            # Don't report Refresh itself
            if cog_name == "Refresh":

                continue

            print(
                f"🔄 Checking {cog_name}"
            )

            result = await self.refresh_cog(
                cog_name,
                cog,
                guild
            )

            commands_list = (
                self.get_commands_for_cog(
                    cog
                )
            )

            result["commands"] = (
                commands_list
            )

            results.append(
                (
                    cog_name,
                    result
                )
            )

        # ====================================================
        # CREATE EMBEDS
        # ====================================================

        embeds = []

        current_embed = discord.Embed(

            title="🔄 Bot Configuration",

            description=(
                f"Configuration report for "
                f"**{guild.name}**\n\n"
                "All loaded Cog files have been checked."
            ),

            color=discord.Color.blue()
        )

        field_count = 0

        # ====================================================
        # ADD COG RESULTS
        # ====================================================

        for cog_name, result in results:

            status = result.get(
                "status",
                "⚪"
            )

            message = result.get(
                "message",
                "No information."
            )

            commands_list = result.get(
                "commands",
                []
            )

            # ------------------------------------------------
            # Commands
            # ------------------------------------------------

            if commands_list:

                command_text = "\n".join(
                    f"`{command}`"
                    for command in commands_list
                )

                if len(command_text) > 700:

                    command_text = (
                        command_text[:700]
                        + "\n`...more commands...`"
                    )

            else:

                command_text = (
                    "No commands detected."
                )

            # ------------------------------------------------
            # Field
            # ------------------------------------------------

            value = (
                f"{status} {message}\n\n"
                f"⚙️ **Commands:**\n"
                f"{command_text}"
            )

            if len(value) > 1024:

                value = (
                    value[:1020]
                    + "..."
                )

            current_embed.add_field(

                name=(
                    f"📦 {cog_name}"
                ),

                value=value,

                inline=False
            )

            field_count += 1

            # Discord embeds allow max 25 fields
            if field_count >= 20:

                embeds.append(
                    current_embed
                )

                current_embed = discord.Embed(

                    title=(
                        "🔄 Bot Configuration "
                        "— Continued"
                    ),

                    color=discord.Color.blue()
                )

                field_count = 0

        # ----------------------------------------------------
        # Add remaining embed
        # ----------------------------------------------------

        if field_count > 0:

            embeds.append(
                current_embed
            )

        # ====================================================
        # SUMMARY
        # ====================================================

        successful = sum(

            1
            for _, result in results
            if result.get(
                "status"
            ) == "✅"

        )

        failed = sum(

            1
            for _, result in results
            if result.get(
                "status"
            ) == "❌"

        )

        no_handler = sum(

            1
            for _, result in results
            if result.get(
                "status"
            ) == "⚪"

        )

        total_commands = sum(

            len(
                result.get(
                    "commands",
                    []
                )
            )

            for _, result in results

        )

        summary = discord.Embed(

            title="📊 Refresh Summary",

            description=(

                f"📦 **Cogs checked:** "
                f"`{len(results)}`\n\n"

                f"✅ **Configured/checked:** "
                f"`{successful}`\n"

                f"❌ **Errors:** "
                f"`{failed}`\n"

                f"⚪ **No setup reader:** "
                f"`{no_handler}`\n\n"

                f"⚙️ **Commands detected:** "
                f"`{total_commands}`"
            ),

            color=(
                discord.Color.green()
                if failed == 0
                else discord.Color.orange()
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

        for embed in embeds:

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

        await interaction.followup.send(
            embed=summary,
            ephemeral=True
        )

        print(
            "========================================"
        )

        print(
            "        MASTER REFRESH COMPLETE"
        )

        print(
            "========================================"
        )


    # ========================================================
    # ERROR HANDLER
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
                "❌ You need **Administrator** "
                "permission to use `/refresh`."
            )

        else:

            message = (
                "❌ Refresh error:\n"
                f"`{type(error).__name__}: {error}`"
            )

            traceback.print_exc()

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

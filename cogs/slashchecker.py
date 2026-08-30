import discord
from discord.ext import commands


class MissingSlash(commands.Cog):
    """
    Detects when a user types a registered slash command
    without the '/' and tells them the correct command.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ========================================================
    # MESSAGE LISTENER
    # ========================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message
    ):

        # ----------------------------------------------------
        # Ignore bots
        # ----------------------------------------------------

        if message.author.bot:
            return

        # ----------------------------------------------------
        # Ignore DMs
        # ----------------------------------------------------

        if message.guild is None:
            return

        content = message.content.strip()

        if not content:
            return

        # ----------------------------------------------------
        # Already has /
        # ----------------------------------------------------

        if content.startswith("/"):
            return

        # ----------------------------------------------------
        # Get first word
        #
        # Example:
        #
        # createclan
        #
        # or
        #
        # clanadd @Peter
        #
        # becomes:
        #
        # createclan
        # clanadd
        # ----------------------------------------------------

        parts = content.split()

        if not parts:
            return

        command_name = parts[0].lower()

        # Remove accidental "/" just in case
        command_name = command_name.lstrip("/")

        # ----------------------------------------------------
        # Get registered slash commands
        # ----------------------------------------------------

        commands_found = {}

        # Global commands
        for command in self.bot.tree.get_commands():

            commands_found[
                command.name.lower()
            ] = command

        # Guild-specific commands
        guild_commands = self.bot.tree.get_commands(
            guild=message.guild
        )

        for command in guild_commands:

            commands_found[
                command.name.lower()
            ] = command

        # ----------------------------------------------------
        # Check command
        # ----------------------------------------------------

        if command_name not in commands_found:
            return

        command = commands_found[
            command_name
        ]

        # ----------------------------------------------------
        # Tell user they forgot /
        # ----------------------------------------------------

        embed = discord.Embed(
            title="⚠️ Missing `/`",
            description=(
                f"You entered `{command_name}` "
                "without the `/`.\n\n"
                f"Please use **/{command.name}** "
                "from the Discord command menu."
            ),
            color=discord.Color.orange()
        )

        embed.set_footer(
            text="Use / before bot commands"
        )

        try:

            await message.reply(
                embed=embed,
                mention_author=False,
                delete_after=8
            )

        except discord.Forbidden:
            pass

        except discord.HTTPException:
            pass

        # ----------------------------------------------------
        # Delete user's incorrect command
        # ----------------------------------------------------

        try:

            await message.delete()

        except discord.Forbidden:
            pass

        except discord.HTTPException:
            pass


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot: commands.Bot
):

    await bot.add_cog(
        MissingSlash(bot)
    )

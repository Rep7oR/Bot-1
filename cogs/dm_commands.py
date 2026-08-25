import asyncio
import discord
from discord.ext import commands
from discord import app_commands


# =========================================================
# SERVER INVITE
# =========================================================

SERVER_INVITE = "https://discord.gg/XFugAbNg7M"


# =========================================================
# JOIN SERVER BUTTON
# =========================================================

class JoinServerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="Join Server",
                emoji="🔗",
                style=discord.ButtonStyle.link,
                url=SERVER_INVITE
            )
        )


# =========================================================
# DM COG
# =========================================================

class DMCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =====================================================
    # /DM
    # =====================================================

    @app_commands.command(
        name="dm",
        description="Send a private message to a server member."
    )
    @app_commands.describe(
        member="The member you want to message",
        message="The message you want to send"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def dm(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        message: str
    ):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )
            return

        # Tell admin we're processing
        await interaction.response.defer(ephemeral=True)

        try:
            embed = discord.Embed(
                title=f"📢 Message from {guild.name}",
                description=message,
                color=discord.Color.blurple()
            )

            # Server icon
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)

            # Server name
            embed.add_field(
                name="🏠 Server",
                value=guild.name,
                inline=False
            )

            # Footer
            embed.set_footer(
                text=f"{guild.name} • Official Community"
            )

            # Send DM with Join Server button
            await member.send(
                embed=embed,
                view=JoinServerView()
            )

            await interaction.followup.send(
                f"✅ Message successfully sent to {member.mention}.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ I couldn't DM {member.mention}. "
                "Their DMs may be disabled.",
                ephemeral=True
            )

        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ Discord rejected the DM: `{e}`",
                ephemeral=True
            )

    # =====================================================
    # /DMALL
    # =====================================================

    @app_commands.command(
        name="dmall",
        description="Send a private message to all server members."
    )
    @app_commands.describe(
        message="The message you want to send to all members"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def dmall(
        self,
        interaction: discord.Interaction,
        message: str
    ):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        count = 0
        failed = 0

        # Initial status
        status_message = await interaction.followup.send(
            "📨 Starting DM broadcast...\n"
            "This may take some time.",
            ephemeral=True
        )

        # Create the embed once
        embed = discord.Embed(
            title=f"📢 Message from {guild.name}",
            description=message,
            color=discord.Color.blurple()
        )

        # Server icon
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Server name
        embed.add_field(
            name="🏠 Server",
            value=guild.name,
            inline=False
        )

        # Footer
        embed.set_footer(
            text=f"{guild.name} • Official Community"
        )

        # Send to every member
        for member in guild.members:

            # Don't DM bots
            if member.bot:
                continue

            try:
                await member.send(
                    embed=embed,
                    view=JoinServerView()
                )

                count += 1

            except (discord.Forbidden, discord.HTTPException):
                failed += 1

            # Delay between DMs
            await asyncio.sleep(0.5)

        # Final result
        await status_message.edit(
            content=(
                f"✅ **DM broadcast completed**\n\n"
                f"🏠 Server: **{guild.name}**\n"
                f"📨 Successfully sent: **{count}**\n"
                f"❌ Failed: **{failed}**"
            )
        )

    # =====================================================
    # ERROR HANDLER
    # =====================================================

    @dm.error
    async def dm_error(
        self,
        interaction: discord.Interaction,
        error
    ):

        if isinstance(error, app_commands.errors.MissingPermissions):
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ You need **Administrator** permission to use this command.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ You need **Administrator** permission to use this command.",
                    ephemeral=True
                )

        elif isinstance(error, app_commands.errors.CommandInvokeError):
            original = error.original

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ An error occurred: `{original}`",
                    ephemeral=True
                )

    @dmall.error
    async def dmall_error(
        self,
        interaction: discord.Interaction,
        error
    ):

        if isinstance(error, app_commands.errors.MissingPermissions):
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ You need **Administrator** permission to use this command.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ You need **Administrator** permission to use this command.",
                    ephemeral=True
                )

        elif isinstance(error, app_commands.errors.CommandInvokeError):
            original = error.original

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ An error occurred: `{original}`",
                    ephemeral=True
                )


# =========================================================
# SETUP
# =========================================================

async def setup(bot):
    await bot.add_cog(DMCommands(bot))

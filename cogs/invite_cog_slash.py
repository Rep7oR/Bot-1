import discord
from discord.ext import commands
from discord import app_commands, ui


class InviteView(ui.View):
    """View with button to send invite link to DMs"""

    def __init__(self, invite_url: str):
        super().__init__(timeout=None)
        self.invite_url = invite_url

    @ui.button(
        label="Get Invite Link",
        style=discord.ButtonStyle.primary,
        emoji="🔗"
    )
    async def invite_button(
        self,
        interaction: discord.Interaction,
        button: ui.Button
    ):
        """Send invite link to user's DMs"""

        try:
            embed = discord.Embed(
                title="Server Invite Link",
                description=f"[Click here to join]({self.invite_url})",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="Direct Link",
                value=self.invite_url,
                inline=False
            )

            await interaction.user.send(embed=embed)

            await interaction.response.send_message(
                "✅ Invite link sent to your DMs!",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I couldn't send you a DM. "
                "Make sure your DMs are enabled!",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error sending invite: {e}",
                ephemeral=True
            )


class InviteCommand(commands.Cog):
    """Cog for posting server invite links"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="invite",
        description="Post the server invite in a selected channel"
    )
    @app_commands.describe(
        channel="The channel where the invite should be posted"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def invite(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        """Create an invite and post it in the selected channel."""

        # Check bot permissions in the selected channel
        permissions = channel.permissions_for(interaction.guild.me)

        if not permissions.create_instant_invite:
            return await interaction.response.send_message(
                f"❌ I don't have permission to create invites in "
                f"{channel.mention}.\n"
                f"Please give me the **Create Invite** permission.",
                ephemeral=True
            )

        if not permissions.send_messages:
            return await interaction.response.send_message(
                f"❌ I don't have permission to send messages in "
                f"{channel.mention}.",
                ephemeral=True
            )

        # Create invite
        try:
            invite = await channel.create_invite(
                max_age=0,
                max_uses=0,
                unique=False
            )

        except discord.Forbidden:
            return await interaction.response.send_message(
                f"❌ I couldn't create an invite for {channel.mention}.",
                ephemeral=True
            )

        except Exception as e:
            return await interaction.response.send_message(
                f"❌ Failed to create invite: `{e}`",
                ephemeral=True
            )

        # Create embed
        embed = discord.Embed(
            title=f"Invite Link | {interaction.guild.name}",
            description=(
                "Want to join the server?\n\n"
                "Click the button below and I'll send "
                "the invite link directly to your DMs."
            ),
            color=discord.Color.blue()
        )

        # Server icon
        if interaction.guild.icon:
            embed.set_thumbnail(
                url=interaction.guild.icon.url
            )

        # Server information
        embed.add_field(
            name="Server",
            value=interaction.guild.name,
            inline=True
        )

        embed.add_field(
            name="Members",
            value=str(interaction.guild.member_count),
            inline=True
        )

        embed.set_footer(
            text="Click the button to receive the invite in your DMs"
        )

        # Create button view
        view = InviteView(invite.url)

        # Post in selected channel
        try:
            await channel.send(
                embed=embed,
                view=view
            )

        except discord.Forbidden:
            return await interaction.response.send_message(
                f"❌ I couldn't post the invite in {channel.mention}.",
                ephemeral=True
            )

        # Confirm to administrator
        await interaction.response.send_message(
            f"✅ Invite posted successfully in {channel.mention}!",
            ephemeral=True
        )


# Load the Cog
async def setup(bot: commands.Bot):
    await bot.add_cog(InviteCommand(bot))

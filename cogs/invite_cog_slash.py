import discord
from discord.ext import commands
from discord import app_commands, ui


class InviteView(ui.View):
    """View with button to send invite link to DMs"""
    
    def __init__(self, invite_url: str):
        super().__init__()
        self.invite_url = invite_url
    
    @ui.button(label="Get Invite Link", style=discord.ButtonStyle.primary, emoji="🔗")
    async def invite_button(self, interaction: discord.Interaction, button: ui.Button):
        """Send invite link to user's DMs"""
        try:
            embed = discord.Embed(
                title="Server Invite Link",
                description=f"[Click here to join]({self.invite_url})",
                color=discord.Color.blue()
            )
            embed.add_field(name="Direct Link", value=self.invite_url, inline=False)
            
            await interaction.user.send(embed=embed)
            await interaction.response.send_message(
                "✅ Invite link sent to your DMs!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I couldn't send you a DM. Make sure you have DMs enabled!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error sending invite: {e}",
                ephemeral=True
            )


class InviteCommand(commands.Cog):
    """Cog for posting server invite links with buttons (slash command version)"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="post_invite", description="Post a server invite link with a button")
    @app_commands.checks.has_permissions(administrator=True)
    async def post_invite(self, interaction: discord.Interaction):
        """
        Create and post an invite link for the server with a button.
        
        Requires:
        - Administrator permission
        - Bot has "Create Invite" permission in the channel
        
        Usage: /post_invite
        """
        try:
            # Create permanent invite link
            invite = await interaction.channel.create_invite(
                max_age=0,      # Never expires
                max_uses=0,      # Unlimited uses
                unique=False     # Reuse existing invite if one exists
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ I don't have permission to create an invite in this channel. "
                "Give me the **'Create Invite'** permission.",
                ephemeral=True
            )
        except Exception as e:
            return await interaction.response.send_message(
                f"❌ Failed to create invite: {e}",
                ephemeral=True
            )
        
        # Create embed
        embed = discord.Embed(
            title=f"Invite Link | {interaction.guild.name}",
            description="Click the button below to get the invite link sent to your DMs!",
            color=discord.Color.blue()
        )
        
        # Add server icon if available
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        
        # Add server info
        embed.add_field(name="Server", value=interaction.guild.name, inline=True)
        embed.add_field(name="Members", value=interaction.guild.member_count, inline=True)
        
        # Add footer
        embed.set_footer(text="Click the button to receive the invite in your DMs")
        
        # Create view with button and send
        view = InviteView(invite.url)
        await interaction.response.send_message(embed=embed, view=view)


# Function to load the cog
async def setup(bot: commands.Bot):
    """Load this cog into the bot"""
    await bot.add_cog(InviteCommand(bot))

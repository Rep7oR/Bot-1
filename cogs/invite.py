import discord
from discord.ext import commands
from discord import app_commands


# ---------- EDIT THESE ----------
DISCORD_INVITE = "https://discord.gg/YOURINVITE"
YOUTUBE = "https://youtube.com/@YOURCHANNEL"
INSTAGRAM = "https://instagram.com/YOURPAGE"
WHATSAPP = "https://chat.whatsapp.com/YOURGROUP"
# -------------------------------


class InviteButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="Discord",
                emoji="💬",
                style=discord.ButtonStyle.link,
                url=DISCORD_INVITE,
            )
        )

        self.add_item(
            discord.ui.Button(
                label="YouTube",
                emoji="▶️",
                style=discord.ButtonStyle.link,
                url=YOUTUBE,
            )
        )

        self.add_item(
            discord.ui.Button(
                label="Instagram",
                emoji="📸",
                style=discord.ButtonStyle.link,
                url=INSTAGRAM,
            )
        )

        self.add_item(
            discord.ui.Button(
                label="WhatsApp",
                emoji="🟢",
                style=discord.ButtonStyle.link,
                url=WHATSAPP,
            )
        )


class Invite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="invite",
        description="Share all official community links."
    )
    async def invite(self, interaction: discord.Interaction):

        guild = interaction.guild

        embed = discord.Embed(
            title=f"🌟 Welcome to {guild.name}",
            description=(
                "Thanks for being part of our community!\n\n"
                "Stay connected with us on all our official platforms below."
            ),
            color=discord.Color.blurple(),
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(
            name="💬 Discord",
            value=f"[Join our Server]({DISCORD_INVITE})",
            inline=False,
        )

        embed.add_field(
            name="▶️ YouTube",
            value=f"[Subscribe to our Channel]({YOUTUBE})",
            inline=False,
        )

        embed.add_field(
            name="📸 Instagram",
            value=f"[Follow us on Instagram]({INSTAGRAM})",
            inline=False,
        )

        embed.add_field(
            name="🟢 WhatsApp",
            value=f"[Join our WhatsApp Community]({WHATSAPP})",
            inline=False,
        )

        embed.set_footer(
            text=f"{guild.name} • Official Community Links",
            icon_url=guild.icon.url if guild.icon else None,
        )

        await interaction.response.send_message(
            embed=embed,
            view=InviteButtons()
        )


async def setup(bot):
    await bot.add_cog(Invite(bot))

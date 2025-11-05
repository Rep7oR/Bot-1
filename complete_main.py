import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import requests
import asyncio
from datetime import datetime, timedelta, timezone
import random
import math
import time
from server import keep_alive
# -----------------------------
# MAIN CONFIG - EDIT BELOW
# -----------------------------


# Discord user IDs who can edit voice stats channels
PERMITTED_EDITORS = [1212318494356672536] 

# Welcome message editables
INSTAGRAM_URL = "https://instagram.com/YOUR_INSTAGRAM"
DISCORD_INVITE = "https://discord.gg/YfryXhPQSZ"
YOUTUBE_CHANNEL_ID = "UCEQl7jnnuyxPsFDQYogAsiA"  # Just for the welcome DM link button!
CHANNEL_ID = 1212317949612916798  # Channel to send notifications
VOICE_CHANNEL_ID = 1212354719272665158  # Voice channel for invite button

# ---------- Reaction Role Config ----------
REACTION_GUILD_ID = 1212317949612916796  # Your server ID
REACTION_ROLE_ID = 1403638537190117447   # Member role ID
REACTION_MESSAGE_ID = 1404554669564629063  # The rules message ID to watch
REACTION_EMOJI = "✅"  # Emoji users must react with
WELCOME_RULES_CHANNEL_ID = 1404425322442526823 # RULES Channel ID
WELCOME_CHANNEL_ID = 1405216479787614287
JOIN_TO_CREATE_CHANNEL_ID = 1434472477379137557  # Replace with your “Join to Create” channel ID
TEMP_VC_CATEGORY_ID = 1434472420277882961  # Optional: Category ID for temp VCs
USER_LIMIT = 8  # Limit per temp VC
temp_channels = {}
# -----------------------------
# DO NOT EDIT BELOW THIS LINE UNLESS CUSTOMIZING BEHAVIOR
# -----------------------------

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# In-memory caches

ROLE_GAIN_MESSAGES = [
    "🎉 Welcome aboard! You’ve just unlocked special access!",
    "🚀 You’re now officially part of the crew!",
    "🌟 Role acquired! Explore and enjoy your new powers!",
    "🔥 You made it in! Let’s have some fun!"
]
ROLE_REMOVE_MESSAGES = [
    "👋 We’ll miss you around here!",
    "😢 Farewell! Hope to see you again soon.",
    "🍂 Your journey here ends… for now.",
    "⚓ You’ve set sail for other adventures!"
]
random_welcome_messages = [
    "Welcome to the server! Get ready to have some fun!",
    "A new hero has joined the quest! Welcome!",
    "The party is growing! Welcome aboard!",
    "We're glad to have you! Feel free to say hi!",
    "Welcome! The adventure begins now!",
]
member_join_times = {}  # {member_id: datetime}
def is_member_online(guild):
    member_role = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
    if not member_role:
        return False
    for member in member_role.members:
        if member.status != discord.Status.offline:
            return True
    return False

def format_role_members(members):
    lines = []
    for member in members:
        profile_link = f"https://discord.com/users/{member.id}"
        name = member.display_name
        lines.append(f"[{name}]({profile_link})")
    return "\n".join(lines) if lines else "No members found."

class InviteView(discord.ui.View):
    def __init__(self, invite_url):
        super().__init__(timeout=None)
        self.invite_url = invite_url

    @discord.ui.button(label="📤 Send to Friends", style=discord.ButtonStyle.primary)
    async def send_invite_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "I’ve sent you a DM with the server invite link — share it with your friends!",
            ephemeral=True
        )
        try:
            await interaction.user.send(
                f"Here’s the invite link to **{interaction.guild.name}** — share it anywhere:\n{self.invite_url}"
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "I couldn’t DM you — please check your privacy settings (Allow DMs from server members).",
                ephemeral=True
            )


@bot.event
async def on_member_join(member):
    member_join_times[member.id] = datetime.utcnow()
    # Send a welcome notification to a public channel
    if not member.bot:
        channel = bot.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title=f"WELCOME TO {member.guild.name.upper()}!",
                description=random.choice(random_welcome_messages),
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Member Joined", value=f"{member.mention}", inline=False)
            embed.add_field(name="A Small Note", value="Please make sure to read the rules!", inline=False)
            
            # Create the button view
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                label="Read the Rules",
                style=discord.ButtonStyle.link,
                url=f"https://discord.com/channels/{REACTION_GUILD_ID}/{WELCOME_RULES_CHANNEL_ID}/{REACTION_MESSAGE_ID}"
            ))
            
            await channel.send(content="@everyone", embed=embed, view=view)
            
    # Send a private welcome DM to the new member (existing code)
    if member.id in member_join_times:
        del member_join_times[member.id]
    await setup_stats_voice(member.guild)
    await send_welcome_dm(member)

@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild

    # --- 1️⃣ When someone joins the Join-to-Create channel ---
    if after.channel and after.channel.id == JOIN_TO_CREATE_CHANNEL_ID:
        category = guild.get_channel(TEMP_VC_CATEGORY_ID) if TEMP_VC_CATEGORY_ID else None

        # Create a temp VC with proper permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                connect=True,
                speak=True,
                stream=True,
                view_channel=True,
                use_voice_activation=True,
            ),
            member: discord.PermissionOverwrite(
                manage_channels=True,  # can rename channel
                move_members=True,     # can kick users from VC
                mute_members=True,     # can mute
                deafen_members=True,   # can deafen
                connect=True,
                speak=True,
                stream=True,
                view_channel=True,
                use_voice_activation=True,
            ),
        }

        temp_vc = await guild.create_voice_channel(
            name=f"{member.display_name}'s Room 🎮",
            category=category,
            user_limit=USER_LIMIT,
            overwrites=overwrites,
        )

        # Move user into the new VC
        await member.move_to(temp_vc)

        # Save temp VC info
        temp_channels[temp_vc.id] = {
            "owner_id": member.id,
            "guild_id": guild.id,
        }

        print(f"🎧 Created temp VC for {member.display_name}: {temp_vc.name}")

    # --- 2️⃣ Delete empty temp VCs automatically ---
    if before.channel and before.channel.id in temp_channels:
        if len(before.channel.members) == 0:
            await before.channel.delete()
            del temp_channels[before.channel.id]
            print(f"🗑️ Deleted empty temp VC: {before.channel.name}")
@bot.event
async def on_member_remove(member):
    join_time = member_join_times.pop(member.id, None)
    if join_time:
        duration = datetime.utcnow() - join_time
        total_time = str(duration).split('.')[0]
    else:
        total_time = "Unknown"
    guild = member.guild
    role_name = "Member"
    embed = discord.Embed(
        title=f"👋 {guild.name}",
        description=random.choice(ROLE_REMOVE_MESSAGES),
        color=0xff0000
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Role Removed", value=f"**{role_name}**", inline=False)
    embed.add_field(name="Time in Server", value=total_time, inline=False)
    embed.set_footer(text="We hope to see you again!")
    try:
        await member.send(embed=embed)
    except discord.Forbidden:
        pass
    await setup_stats_voice(guild)

@bot.event
async def on_raw_reaction_add(payload):
    if (payload.message_id == REACTION_MESSAGE_ID and str(payload.emoji) == REACTION_EMOJI and payload.guild_id == REACTION_GUILD_ID):
        guild = bot.get_guild(REACTION_GUILD_ID)
        if not guild:
            return
        role = guild.get_role(REACTION_ROLE_ID)
        member = guild.get_member(payload.user_id)
        if member and role and role not in member.roles and not member.bot:
            await member.add_roles(role)
            if member.id not in member_join_times:
                member_join_times[member.id] = datetime.utcnow()
            embed = discord.Embed(
                title=f"🎉 {guild.name}",
                description=random.choice(ROLE_GAIN_MESSAGES),
                color=0x00ff00
            )
            embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
            embed.add_field(name="Role Granted", value=f"**{role.name}**", inline=False)
            embed.add_field(name="Welcome!", value="Enjoy your time here!", inline=False)
            embed.set_footer(text="Glad to have you with us!")
            try:
                await member.send(embed=embed)
            except discord.Forbidden:
                pass

@bot.event
async def on_raw_reaction_remove(payload):
    if (payload.message_id == REACTION_MESSAGE_ID and str(payload.emoji) == REACTION_EMOJI and payload.guild_id == REACTION_GUILD_ID):
        guild = bot.get_guild(REACTION_GUILD_ID)
        if not guild:
            return
        role = guild.get_role(REACTION_ROLE_ID)
        member = guild.get_member(payload.user_id)
        if member and role and role in member.roles:
            await member.remove_roles(role)
            join_time = member_join_times.get(member.id)
            if join_time:
                duration = datetime.utcnow() - join_time
                total_time = str(duration).split('.')[0]
            else:
                total_time = "Unknown"
            embed = discord.Embed(
                title=f"👋 {guild.name}",
                description="You have remove your verification from our server, Verify again to get your Member Role",
                color=0xff0000
            )
            embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
            embed.add_field(name="Role Removed", value=f"**{role.name}**", inline=False)
            try:
                await member.send(embed=embed)
            except discord.Forbidden:
                pass



active_sessions = {}
recent_starts = {}
recent_ends = {}
DEBOUNCE_SECONDS = 10
DELETE_AFTER_SECONDS = 60

@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    if after.bot:
        return
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return
    current_activities = {a.name for a in after.activities if a and a.name}
    previous_activities = {a.name for a in before.activities if a and a.name} if before else set()
    new_games = current_activities - previous_activities
    for new_game in new_games:
        if not (after.id in active_sessions and active_sessions[after.id][0] == new_game):
            await handle_game_start(after, channel, new_game)
    ended_games = previous_activities - current_activities
    for ended_game in ended_games:
        await handle_game_end(after, channel, ended_game)

async def handle_game_start(member, channel, game_name):
    now_ts = time.time()
    last_start = recent_starts.get(member.id, 0)
    if now_ts - last_start < DEBOUNCE_SECONDS:
        return
    if member.id in active_sessions and active_sessions[member.id][0] == game_name:
        return
    recent_starts[member.id] = now_ts
    embed = discord.Embed(
        title="🎮 Game Session Started",
        description=f"**{member.display_name}** is now playing",
        color=0x00ff00
    )
    embed.add_field(name="Game", value=f"**{game_name}**", inline=True)
    embed.add_field(name="Started", value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:R>", inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    msg = await channel.send(embed=embed,delete_after=DELETE_AFTER_SECONDS)
    active_sessions[member.id] = (game_name, datetime.now(timezone.utc))

async def handle_game_end(member, channel, game_name):
    now_ts = time.time()
    last_end = recent_ends.get(member.id, 0)
    if now_ts - last_end < DEBOUNCE_SECONDS:
        return
    if member.id not in active_sessions:
        return
    session_game, start_time = active_sessions[member.id]
    if session_game != game_name:
        return
    recent_ends[member.id] = now_ts
    del active_sessions[member.id]
    duration = datetime.now(timezone.utc) - start_time
    hours, remainder = divmod(duration.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    duration_str = ""
    if hours >= 1:
        duration_str += f"{int(hours)}h "
    if minutes >= 1 or hours >= 1:
        duration_str += f"{int(minutes)}m "
    duration_str += f"{int(seconds)}s"
    embed = discord.Embed(
        title="⏹️ Game Session Ended",
        description=f"**{member.display_name}** has finished playing",
        color=0xff0000
    )
    embed.add_field(name="Game", value=f"**{game_name}**", inline=True)
    embed.add_field(name="Duration", value=duration_str, inline=True)
    embed.add_field(
        name="Session Time",
        value=f"<t:{int(start_time.timestamp())}:t> → <t:{int(datetime.now(timezone.utc).timestamp())}:t>",
        inline=False
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    msg = await channel.send(embed=embed,delete_after=DELETE_AFTER_SECONDS)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use that command.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("I don't have the required permissions to do that.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"Command raised an error: {error.original}")
        raise error
    else:
        await ctx.send(f"Command error: {error}")

# ---------- CATEGORY 4: Custom Welcome DM ----------
WELCOME_MESSAGE = """Welcome to **{server}**! 🎉

This is the official Discord for **{yt_channel}**!
Check out our YouTube 👉 [YouTube]({yt_link})

Stay connected:
- Instagram: [Click Here]({insta_link})
- Discord: [Join Here]({discord_link})

Introduce yourself; we're glad you're here!
"""

async def send_welcome_dm(member):
    guild = member.guild
    main_yt_id = (list(NOTIFY_CHANNELS.keys()) or list(VIDEO_ALERT_CHANNELS.keys()) or [YOUTUBE_CHANNEL_ID])[0]
    yt_info = get_channel_info(main_yt_id) or {"title": "Our Channel", "url": "https://youtube.com/"}
    msg = WELCOME_MESSAGE.format(
        server=guild.name,
        yt_channel=yt_info['title'],
        yt_link=yt_info['url'],
        insta_link=INSTAGRAM_URL,
        discord_link=DISCORD_INVITE
    )
    embed = discord.Embed(title=f"Welcome, {member.display_name}!", description=msg, color=0x0077ff)
    embed.add_field(
        name="🔰 Verification Required",
        value="Click the button below to read the rules and verify yourself to get full access to the server!",
        inline=False
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            label="📜 VERIFY HERE TO GET MEMBER ROLE",
            style=discord.ButtonStyle.url,
            url=f"https://discord.com/channels/1212317949612916796/1404425322442526823/1404517671504052285"
        )
    )
    try:
        await member.send(embed=embed, view=view)
    except discord.Forbidden:
        print(f"Could not DM {member.name}")

# ---------- CATEGORY 5: Commands ----------
@bot.command(name="dmall")
@commands.has_permissions(administrator=True)
async def dmall(ctx, *, content):
    await ctx.send("Sending DMs... (may take a while)")
    count, fail = 0, 0
    for member in ctx.guild.members:
        if not member.bot:
            try:
                await member.send(content)
                count += 1
            except:
                fail += 1
        await asyncio.sleep(0.5)
    await ctx.send(f"✅ Dmed {count}, failed {fail}")

@bot.command(name="msg")
@commands.has_permissions(administrator=True)
async def msg(ctx, channel: discord.TextChannel, *, message):
    await channel.send(message)
    await ctx.send(f"✅ Sent message in {channel.mention}")


    


@bot.command(name="post_invite")
@commands.has_permissions(administrator=True)
async def post_invite(ctx):
    try:
        invite = await ctx.channel.create_invite(max_age=0, max_uses=0, unique=False)
    except discord.Forbidden:
        return await ctx.send("I don't have permission to create an invite in this channel. Give me 'Create Invite' permission.")
    except Exception as e:
        return await ctx.send(f"Failed to create invite: {e}")
    embed = discord.Embed(
        title=f"Invite Link | {ctx.guild.name}",
        description="Click the button below to get the invite link sent to your DMs!",
        color=discord.Color.blue()
    )
    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    view = InviteView(invite.url)
    await ctx.send(embed=embed, view=view)

# ---------- CATEGORY 6: Bot Startup ----------
@bot.event
async def on_ready():
    print(f"Bot online as {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="over the community"
        ),
        status=discord.Status.online
    )
bot.run(DISCORD_TOKEN)















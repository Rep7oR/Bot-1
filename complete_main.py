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
from discord import app_commands
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



# member_join_times = {}  # {member_id: datetime}
# def is_member_online(guild):
#     member_role = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
#     if not member_role:
#         return False
#     for member in member_role.members:
#         if member.status != discord.Status.offline:
#             return True
#     return False

# def format_role_members(members):
#     lines = []
#     for member in members:
#         profile_link = f"https://discord.com/users/{member.id}"
#         name = member.display_name
#         lines.append(f"[{name}]({profile_link})")
#     return "\n".join(lines) if lines else "No members found."


            




    

# @bot.event
# async def on_voice_state_update(member, before, after):
#     guild = member.guild

#     # --- 1️⃣ When someone joins the Join-to-Create channel ---
#     if after.channel and after.channel.id == JOIN_TO_CREATE_CHANNEL_ID:
#         category = guild.get_channel(TEMP_VC_CATEGORY_ID) if TEMP_VC_CATEGORY_ID else None

#         # Create a temp VC with proper permissions
#         overwrites = {
#             guild.default_role: discord.PermissionOverwrite(
#                 connect=True,
#                 speak=True,
#                 stream=True,
#                 view_channel=True,
#                 use_voice_activation=True,
#             ),
#             member: discord.PermissionOverwrite(
#                 manage_channels=True,  # can rename channel
#                 move_members=True,     # can kick users from VC
#                 mute_members=True,     # can mute
#                 deafen_members=True,   # can deafen
#                 connect=True,
#                 speak=True,
#                 stream=True,
#                 view_channel=True,
#                 use_voice_activation=True,
#             ),
#         }

#         temp_vc = await guild.create_voice_channel(
#             name=f"{member.display_name}'s Room 🎮",
#             category=category,
#             user_limit=USER_LIMIT,
#             overwrites=overwrites,
#         )

#         # Move user into the new VC
#         await member.move_to(temp_vc)

#         # Save temp VC info
#         temp_channels[temp_vc.id] = {
#             "owner_id": member.id,
#             "guild_id": guild.id,
#         }

#         print(f"🎧 Created temp VC for {member.display_name}: {temp_vc.name}")

#     # --- 2️⃣ Delete empty temp VCs automatically ---
#     if before.channel and before.channel.id in temp_channels:
#         if len(before.channel.members) == 0:
#             await before.channel.delete()
#             del temp_channels[before.channel.id]
#             print(f"🗑️ Deleted empty temp VC: {before.channel.name}")









    
# ============================================================
# LOAD COGS
# ============================================================

async def load_cogs():
    """
    Load all normal cogs during setup_hook.

    MasterConfig is intentionally NOT loaded here because its database
    connection/restore work can block Discord's setup_hook. It is loaded
    after Discord reaches on_ready().
    """

    cogs_folder = "./cogs"

    if not os.path.exists(cogs_folder):
        os.makedirs(cogs_folder)

    files = sorted([
        filename
        for filename in os.listdir(cogs_folder)
        if (
            filename.endswith(".py")
            and not filename.startswith("_")
        )
    ])

    master_names = {
        "masterconfig.py",
        "master_config.py",
    }

    normal_files = [
        filename
        for filename in files
        if filename.lower() not in master_names
    ]

    print("==========================================")
    print("🔧 LOADING DISCORD COGS")
    print("==========================================")
    print(f"📁 Cogs directory: {os.path.abspath(cogs_folder)}")
    print(f"📦 Found {len(files)} Python cog file(s).")

    if not normal_files:
        print("⚠️ No normal cog files were found.")

    for filename in normal_files:

        extension = f"cogs.{filename[:-3]}"

        try:
            print(f"🔄 Loading cog: {filename}")

            await bot.load_extension(extension)

            print(f"✅ Loaded cog: {filename}")

        except Exception as e:

            print(f"❌ Failed to load {filename}: {e}")
            import traceback
            traceback.print_exc()

    print("==========================================")
    print(f"📊 COG LOAD COMPLETE: {len(bot.cogs)} cog(s)")
    print("==========================================")


# ---------- BOT SETUP ----------

@bot.event
async def setup_hook():

    print("==========================================")
    print("🚀 DISCORD SETUP HOOK STARTED")
    print("==========================================")

    await load_cogs()

    # Sync commands for all normal cogs.
    try:

        synced = await bot.tree.sync()

        print(
            f"✅ Synced {len(synced)} slash commands."
        )

    except Exception as e:

        print(
            f"❌ Failed to sync slash commands: {e}"
        )

        import traceback
        traceback.print_exc()

    print("==========================================")
    print("✅ DISCORD SETUP HOOK FINISHED")
    print("==========================================")


# ---------- START WEB SERVER ----------
keep_alive()
# ---------- BOT STARTUP ----------
@bot.event
async def on_ready():

    print("==========================================")
    print(f"🤖 Bot online as {bot.user}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print(f"🌐 Guilds: {len(bot.guilds)}")
    print(f"🧩 Loaded cogs: {len(bot.cogs)}")
    print("==========================================")

    # ---------------------------------------------------------
    # Load MasterConfig AFTER Discord is fully ready.
    #
    # This prevents Supabase connection/restore work from
    # blocking setup_hook and preventing the other cogs from
    # loading.
    # ---------------------------------------------------------

    master_extension = None

    for candidate in (
        "cogs.masterconfig",
        "cogs.master_config",
    ):

        if candidate in bot.extensions:
            master_extension = candidate
            break

    if master_extension is None:

        for candidate in (
            "cogs.masterconfig",
            "cogs.master_config",
        ):

            try:

                print(
                    f"🧠 Loading MasterConfig after on_ready: "
                    f"{candidate}"
                )

                await bot.load_extension(candidate)

                master_extension = candidate

                print(
                    f"✅ MasterConfig loaded: {candidate}"
                )

                break

            except Exception as e:

                print(
                    f"⚠️ Could not load {candidate}: {e}"
                )

    # ---------------------------------------------------------
    # If MasterConfig exposes a post-ready initializer, use it.
    # ---------------------------------------------------------

    master_cog = bot.get_cog("MasterConfig")

    if master_cog:

        initialize = getattr(
            master_cog,
            "initialize_after_ready",
            None
        )

        if initialize:

            try:

                await initialize()

            except Exception as e:

                print(
                    f"❌ MasterConfig initialization failed: {e}"
                )

                import traceback
                traceback.print_exc()

        # If a standalone sync method exists, run it.
        sync_method = getattr(
            master_cog,
            "sync_all_cogs",
            None
        )

        if sync_method:

            try:

                await sync_method()

            except Exception as e:

                print(
                    f"❌ Cog restore sync failed: {e}"
                )

                import traceback
                traceback.print_exc()

    # ---------------------------------------------------------
    # Sync again after MasterConfig commands are loaded.
    # ---------------------------------------------------------

    try:

        synced = await bot.tree.sync()

        print(
            f"✅ Final slash-command sync: "
            f"{len(synced)} command(s)"
        )

    except Exception as e:

        print(
            f"❌ Final slash-command sync failed: {e}"
        )

    await bot.change_presence(

        activity=discord.Activity(

            type=discord.ActivityType.watching,

            name="Watching the community"
        ),

        status=discord.Status.online
    )

    print("==========================================")
    print("🟢 BOT STARTUP COMPLETE")
    print("==========================================")


# ---------- START BOT ----------
if not DISCORD_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing from the environment."
    )

bot.run(DISCORD_TOKEN)























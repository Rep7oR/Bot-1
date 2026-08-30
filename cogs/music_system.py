# import asyncio
# import json
# import os

# import discord
# from discord import app_commands
# from discord.ext import commands, tasks
# import yt_dlp


# # =========================================================
# # CONFIG
# # =========================================================

# CONFIG_FILE = "music_config.json"

# DEFAULT_VOLUME = 0.70

# WATCHDOG_INTERVAL = 20

# MUSIC_SOURCE = os.getenv("MALAYALAM_SOURCE", "").strip()


# # =========================================================
# # YT-DLP
# # =========================================================

# YTDL_OPTIONS = {
#     "format": "bestaudio/best",
#     "quiet": True,
#     "no_warnings": True,
#     "noplaylist": False,
#     "source_address": "0.0.0.0",
# }


# # =========================================================
# # FFMPEG
# # =========================================================

# FFMPEG_BEFORE_OPTIONS = (
#     "-reconnect 1 "
#     "-reconnect_streamed 1 "
#     "-reconnect_delay_max 5"
# )

# FFMPEG_OPTIONS = (
#     "-vn "
#     "-loglevel warning"
# )


# # =========================================================
# # CONFIG FILE FUNCTIONS
# # =========================================================

# def load_music_config():

#     if not os.path.exists(CONFIG_FILE):
#         return {}

#     try:

#         with open(
#             CONFIG_FILE,
#             "r",
#             encoding="utf-8"
#         ) as f:

#             return json.load(f)

#     except Exception as e:

#         print(
#             f"❌ Failed to load music config: {e}"
#         )

#         return {}


# def save_music_config(config):

#     try:

#         with open(
#             CONFIG_FILE,
#             "w",
#             encoding="utf-8"
#         ) as f:

#             json.dump(
#                 config,
#                 f,
#                 indent=4
#             )

#     except Exception as e:

#         print(
#             f"❌ Failed to save music config: {e}"
#         )


# # =========================================================
# # MUSIC COG
# # =========================================================

# class MusicSystem(commands.Cog):

#     def __init__(self, bot):

#         self.bot = bot

#         self.config = load_music_config()

#         self.players = {}

#         self.connecting = set()

#         self.music_watchdog.start()

#     # =====================================================
#     # COG UNLOAD
#     # =====================================================

#     def cog_unload(self):

#         self.music_watchdog.cancel()

#     # =====================================================
#     # GET PLAYER
#     # =====================================================

#     def get_player(
#         self,
#         guild_id
#     ):

#         return self.players.get(
#             guild_id
#         )

#     # =====================================================
#     # GET CONFIG
#     # =====================================================

#     def get_guild_config(
#         self,
#         guild_id
#     ):

#         return self.config.get(
#             str(guild_id)
#         )

#     # =====================================================
#     # /SETMUSIC
#     # =====================================================

#     @app_commands.command(
#         name="setmusic",
#         description="Create the 24/7 Malayalam music system."
#     )
#     @app_commands.describe(
#         category="Category where the music channels will be created."
#     )
#     @app_commands.checks.has_permissions(
#         administrator=True
#     )
#     async def setmusic(
#         self,
#         interaction: discord.Interaction,
#         category: discord.CategoryChannel
#     ):

#         guild = interaction.guild

#         if guild is None:

#             await interaction.response.send_message(
#                 "❌ This command can only be used in a server.",
#                 ephemeral=True
#             )

#             return

#         # -------------------------------------------------
#         # CHECK SOURCE
#         # -------------------------------------------------

#         if not MUSIC_SOURCE:

#             await interaction.response.send_message(

#                 "❌ `MALAYALAM_SOURCE` is not configured "
#                 "in Render Environment Variables.",

#                 ephemeral=True
#             )

#             return

#         # -------------------------------------------------
#         # CHECK EXISTING
#         # -------------------------------------------------

#         existing = self.get_guild_config(
#             guild.id
#         )

#         if existing:

#             voice = guild.get_channel(
#                 existing.get(
#                     "voice_channel_id"
#                 )
#             )

#             text = guild.get_channel(
#                 existing.get(
#                     "text_channel_id"
#                 )
#             )

#             await interaction.response.send_message(

#                 "⚠️ **Music system already exists.**\n\n"

#                 f"🎧 Voice: "
#                 f"{voice.mention if voice else 'Missing'}\n"

#                 f"💬 Controls: "
#                 f"{text.mention if text else 'Missing'}\n\n"

#                 "Use `/musicsetup remove` first.",

#                 ephemeral=True
#             )

#             return

#         await interaction.response.defer(
#             ephemeral=True
#         )

#         print("")
#         print("=" * 60)
#         print("🎵 MUSIC SETUP")
#         print("=" * 60)
#         print(f"Server: {guild.name}")
#         print(f"Category: {category.name}")

#         # =================================================
#         # VOICE PERMISSIONS
#         # =================================================

#         voice_overwrites = {

#             guild.default_role:
#                 discord.PermissionOverwrite(
#                     view_channel=True,
#                     connect=True,
#                     speak=False
#                 )
#         }

#         # =================================================
#         # CREATE VOICE
#         # =================================================

#         try:

#             voice_channel = await guild.create_voice_channel(

#                 name="Malayalam Music 🎵",

#                 category=category,

#                 overwrites=voice_overwrites,

#                 reason="24/7 Malayalam Music"
#             )

#             print(
#                 f"✅ Voice created: "
#                 f"{voice_channel.name}"
#             )

#         except Exception as e:

#             print(
#                 f"❌ Voice channel error: "
#                 f"{type(e).__name__}: {e}"
#             )

#             await interaction.followup.send(

#                 f"❌ Could not create music voice channel.\n\n"
#                 f"`{type(e).__name__}: {e}`",

#                 ephemeral=True
#             )

#             return

#         # =================================================
#         # TEXT PERMISSIONS
#         # =================================================

#         text_overwrites = {

#             guild.default_role:
#                 discord.PermissionOverwrite(
#                     view_channel=True,
#                     send_messages=False,
#                     read_message_history=True
#                 )
#         }

#         # =================================================
#         # CREATE CONTROL CHANNEL
#         # =================================================

#         try:

#             text_channel = await guild.create_text_channel(

#                 name="music-controls",

#                 category=category,

#                 overwrites=text_overwrites,

#                 topic="24/7 Malayalam Music Controls",

#                 reason="24/7 Malayalam Music"
#             )

#             print(
#                 f"✅ Control channel created: "
#                 f"{text_channel.name}"
#             )

#         except Exception as e:

#             print(
#                 f"❌ Text channel error: {e}"
#             )

#             try:
#                 await voice_channel.delete()
#             except:
#                 pass

#             await interaction.followup.send(

#                 f"❌ Could not create music control channel.\n\n"
#                 f"`{type(e).__name__}: {e}`",

#                 ephemeral=True
#             )

#             return

#         # =================================================
#         # SAVE CONFIG
#         # =================================================

#         self.config[
#             str(guild.id)
#         ] = {

#             "category_id":
#                 category.id,

#             "voice_channel_id":
#                 voice_channel.id,

#             "text_channel_id":
#                 text_channel.id
#         }

#         save_music_config(
#             self.config
#         )

#         # =================================================
#         # PLAYER DATA
#         # =================================================

#         self.players[
#             guild.id
#         ] = {

#             "voice_channel_id":
#                 voice_channel.id,

#             "text_channel_id":
#                 text_channel.id,

#             "message_id":
#                 None,

#             "volume":
#                 DEFAULT_VOLUME,

#             "paused":
#                 False,

#             "starting":
#                 False,

#             "title":
#                 "Connecting...",

#             "url":
#                 MUSIC_SOURCE
#         }

#         # =================================================
#         # SEND CONTROL PANEL
#         # =================================================

#         panel = await self.send_panel(
#             guild
#         )

#         if panel:

#             self.players[
#                 guild.id
#             ]["message_id"] = panel.id

#         # =================================================
#         # CONNECT
#         # =================================================

#         connected = await self.connect_to_voice(
#             guild
#         )

#         if connected:

#             await interaction.followup.send(

#                 "✅ **Malayalam Music System Started!**\n\n"

#                 f"🎧 Voice: {voice_channel.mention}\n"
#                 f"💬 Controls: {text_channel.mention}\n\n"

#                 "🎵 Music is now running.\n"
#                 "🔄 Automatic reconnection is enabled.",

#                 ephemeral=True
#             )

#         else:

#             await interaction.followup.send(

#                 "⚠️ **Music channels created, "
#                 "but voice connection failed.**\n\n"

#                 f"🎧 Voice: {voice_channel.mention}\n"
#                 f"💬 Controls: {text_channel.mention}\n\n"

#                 "The watchdog will continue trying.\n\n"

#                 "Use `/voicetest` to diagnose the voice connection.",

#                 ephemeral=True
#             )

#     # =====================================================
#     # MUSIC SETUP GROUP
#     # =====================================================

#     musicsetup = app_commands.Group(

#         name="musicsetup",

#         description="Manage the music system."
#     )

#     # =====================================================
#     # /MUSICSETUP REMOVE
#     # =====================================================

#     @musicsetup.command(
#         name="remove",
#         description="Remove the complete music system."
#     )
#     @app_commands.checks.has_permissions(
#         administrator=True
#     )
#     async def musicsetup_remove(
#         self,
#         interaction: discord.Interaction
#     ):

#         guild = interaction.guild

#         if guild is None:

#             await interaction.response.send_message(
#                 "❌ Server only.",
#                 ephemeral=True
#             )

#             return

#         await interaction.response.defer(
#             ephemeral=True
#         )

#         removed = await self.remove_system(
#             guild
#         )

#         if removed:

#             await interaction.followup.send(

#                 "🗑️ **Music System Removed**\n\n"

#                 "✅ Bot disconnected\n"
#                 "✅ Voice channel deleted\n"
#                 "✅ Control channel deleted\n"
#                 "✅ Configuration deleted\n"
#                 "✅ Player data cleared\n\n"

#                 "You can now use `/setmusic` again.",

#                 ephemeral=True
#             )

#         else:

#             await interaction.followup.send(

#                 "ℹ️ No music system was configured.",

#                 ephemeral=True
#             )

#     # =====================================================
#     # REMOVE SYSTEM
#     # =====================================================

#     async def remove_system(
#         self,
#         guild
#     ):

#         guild_id = guild.id

#         config = self.config.get(
#             str(guild_id)
#         )

#         player = self.players.get(
#             guild_id
#         )

#         if not config and not player:

#             return False

#         # -------------------------------------------------
#         # DISCONNECT
#         # -------------------------------------------------

#         voice_client = guild.voice_client

#         if voice_client:

#             try:

#                 if voice_client.is_playing():

#                     voice_client.stop()

#             except:
#                 pass

#             try:

#                 await voice_client.disconnect(
#                     force=True
#                 )

#             except Exception as e:

#                 print(
#                     f"⚠️ Disconnect error: {e}"
#                 )

#         # -------------------------------------------------
#         # CHANNEL IDS
#         # -------------------------------------------------

#         voice_id = None
#         text_id = None

#         if config:

#             voice_id = config.get(
#                 "voice_channel_id"
#             )

#             text_id = config.get(
#                 "text_channel_id"
#             )

#         if player:

#             voice_id = (
#                 voice_id
#                 or player.get(
#                     "voice_channel_id"
#                 )
#             )

#             text_id = (
#                 text_id
#                 or player.get(
#                     "text_channel_id"
#                 )
#             )

#         # -------------------------------------------------
#         # DELETE TEXT
#         # -------------------------------------------------

#         if text_id:

#             channel = guild.get_channel(
#                 text_id
#             )

#             if channel:

#                 try:

#                     await channel.delete(
#                         reason="Music system removed"
#                     )

#                     print(
#                         "🗑️ Deleted music control channel."
#                     )

#                 except Exception as e:

#                     print(
#                         f"⚠️ Text deletion error: {e}"
#                     )

#         # -------------------------------------------------
#         # DELETE VOICE
#         # -------------------------------------------------

#         if voice_id:

#             channel = guild.get_channel(
#                 voice_id
#             )

#             if channel:

#                 try:

#                     await channel.delete(
#                         reason="Music system removed"
#                     )

#                     print(
#                         "🗑️ Deleted music voice channel."
#                     )

#                 except Exception as e:

#                     print(
#                         f"⚠️ Voice deletion error: {e}"
#                     )

#         # -------------------------------------------------
#         # CLEAR DATA
#         # -------------------------------------------------

#         self.config.pop(
#             str(guild_id),
#             None
#         )

#         self.players.pop(
#             guild_id,
#             None
#         )

#         self.connecting.discard(
#             guild_id
#         )

#         save_music_config(
#             self.config
#         )

#         return True

#     # =====================================================
#     # /VOICETEST
#     # =====================================================

#     @app_commands.command(
#         name="voicetest",
#         description="Test the Discord voice connection."
#     )
#     @app_commands.checks.has_permissions(
#         administrator=True
#     )
#     async def voicetest(
#         self,
#         interaction: discord.Interaction
#     ):

#         guild = interaction.guild

#         if guild is None:

#             await interaction.response.send_message(
#                 "❌ Server only.",
#                 ephemeral=True
#             )

#             return

#         config = self.get_guild_config(
#             guild.id
#         )

#         if not config:

#             await interaction.response.send_message(

#                 "❌ Music system is not configured.\n"
#                 "Run `/setmusic` first.",

#                 ephemeral=True
#             )

#             return

#         channel = guild.get_channel(
#             config.get(
#                 "voice_channel_id"
#             )
#         )

#         if channel is None:

#             await interaction.response.send_message(

#                 "❌ Music voice channel does not exist.",

#                 ephemeral=True
#             )

#             return

#         await interaction.response.defer(
#             ephemeral=True
#         )

#         print("")
#         print("=" * 70)
#         print("🎧 VOICE CONNECTION TEST")
#         print("=" * 70)

#         print(
#             f"Server: {guild.name}"
#         )

#         print(
#             f"Guild ID: {guild.id}"
#         )

#         print(
#             f"Voice Channel: {channel.name}"
#         )

#         print(
#             f"Voice Channel ID: {channel.id}"
#         )

#         print(
#             f"discord.py: {discord.__version__}"
#         )

#         # -------------------------------------------------
#         # CHECK PYNACL
#         # -------------------------------------------------

#         try:

#             import nacl

#             print(
#                 f"✅ PyNaCl: "
#                 f"{getattr(nacl, '__version__', 'installed')}"
#             )

#         except Exception as e:

#             print(
#                 f"❌ PyNaCl: {e}"
#             )

#         # -------------------------------------------------
#         # CHECK DAVEY
#         # -------------------------------------------------

#         try:

#             import davey

#             print(
#                 f"✅ davey: "
#                 f"{getattr(davey, '__version__', 'installed')}"
#             )

#         except Exception as e:

#             print(
#                 f"❌ davey: {e}"
#             )

#         print(
#             f"Voice States Intent: "
#             f"{self.bot.intents.voice_states}"
#         )

#         try:

#             # -------------------------------------------------
#             # DISCONNECT OLD CONNECTION
#             # -------------------------------------------------

#             old_client = guild.voice_client

#             if old_client:

#                 print(
#                     "⚠️ Disconnecting old voice client..."
#                 )

#                 try:

#                     await old_client.disconnect(
#                         force=True
#                     )

#                 except:
#                     pass

#                 await asyncio.sleep(
#                     3
#                 )

#             # -------------------------------------------------
#             # CONNECT
#             # -------------------------------------------------

#             print(
#                 "🔌 Connecting..."
#             )

#             voice_client = await channel.connect(

#                 timeout=60,

#                 reconnect=True
#             )

#             print(
#                 "🟢 VOICE CONNECTION COMPLETE"
#             )

#             print(
#                 f"Connected: "
#                 f"{voice_client.is_connected()}"
#             )

#             print(
#                 f"Channel: "
#                 f"{voice_client.channel}"
#             )

#             print(
#                 f"Endpoint: "
#                 f"{voice_client.endpoint}"
#             )

#             print(
#                 f"Session ID: "
#                 f"{voice_client.session_id}"
#             )

#             print("=" * 70)

#             await interaction.followup.send(

#                 "🟢 **VOICE CONNECTION SUCCESSFUL**\n\n"

#                 f"🎧 Channel: {channel.mention}\n"
#                 f"🔌 Connected: `{voice_client.is_connected()}`\n"
#                 f"📡 Endpoint: `{voice_client.endpoint}`\n\n"

#                 "Discord voice connection is working.",

#                 ephemeral=True
#             )

#         except asyncio.TimeoutError:

#             print(
#                 "❌ VOICE CONNECTION TIMEOUT"
#             )

#             print("=" * 70)

#             await interaction.followup.send(

#                 "🔴 **Voice connection timed out.**\n\n"

#                 "Check the Render logs.",

#                 ephemeral=True
#             )

#         except discord.Forbidden as e:

#             print(
#                 f"❌ DISCORD FORBIDDEN: {e}"
#             )

#             print("=" * 70)

#             await interaction.followup.send(

#                 f"🔴 **Discord rejected the connection.**\n\n"
#                 f"`{e}`",

#                 ephemeral=True
#             )

#         except discord.ClientException as e:

#             print(
#                 f"❌ DISCORD CLIENT ERROR: {e}"
#             )

#             print("=" * 70)

#             await interaction.followup.send(

#                 f"🔴 **Discord client error.**\n\n"
#                 f"`{e}`",

#                 ephemeral=True
#             )

#         except Exception as e:

#             print(
#                 f"❌ VOICE ERROR"
#             )

#             print(
#                 f"Type: {type(e).__name__}"
#             )

#             print(
#                 f"Error: {e}"
#             )

#             print("=" * 70)

#             await interaction.followup.send(

#                 "🔴 **Voice connection failed.**\n\n"

#                 f"Type: `{type(e).__name__}`\n"
#                 f"Error: `{e}`",

#                 ephemeral=True
#             )

#     # =====================================================
#     # CONNECT TO VOICE
#     # =====================================================

#     async def connect_to_voice(
#         self,
#         guild
#     ):

#         if guild.id in self.connecting:

#             print(
#                 f"⏳ Already connecting "
#                 f"to {guild.name}"
#             )

#             return False

#         self.connecting.add(
#             guild.id
#         )

#         try:

#             player = self.players.get(
#                 guild.id
#             )

#             if not player:

#                 return False

#             channel = guild.get_channel(
#                 player[
#                     "voice_channel_id"
#                 ]
#             )

#             if not channel:

#                 print(
#                     "❌ Music voice channel missing."
#                 )

#                 return False

#             # -------------------------------------------------
#             # CHECK EXISTING
#             # -------------------------------------------------

#             voice_client = guild.voice_client

#             if voice_client:

#                 if voice_client.is_connected():

#                     if (
#                         voice_client.channel.id
#                         != channel.id
#                     ):

#                         await voice_client.move_to(
#                             channel
#                         )

#                     return True

#                 try:

#                     await voice_client.disconnect(
#                         force=True
#                     )

#                 except:
#                     pass

#                 await asyncio.sleep(
#                     2
#                 )

#             # -------------------------------------------------
#             # CONNECT
#             # -------------------------------------------------

#             print(
#                 f"🔌 Connecting to "
#                 f"{channel.name}..."
#             )

#             voice_client = await channel.connect(

#                 timeout=60,

#                 reconnect=True
#             )

#             print(
#                 f"🟢 Connected to "
#                 f"{channel.name}"
#             )

#             # -------------------------------------------------
#             # START MUSIC
#             # -------------------------------------------------

#             if (
#                 not voice_client.is_playing()
#                 and not voice_client.is_paused()
#             ):

#                 await self.start_music(
#                     guild,
#                     voice_client
#                 )

#             await self.update_panel(
#                 guild
#             )

#             return True

#         except asyncio.TimeoutError:

#             print(
#                 "❌ Voice connection timeout."
#             )

#             return False

#         except discord.Forbidden as e:

#             print(
#                 f"❌ Discord Forbidden: {e}"
#             )

#             return False

#         except discord.ClientException as e:

#             print(
#                 f"❌ Discord ClientException: {e}"
#             )

#             return False

#         except Exception as e:

#             print(
#                 f"❌ Voice connection error:"
#                 f" {type(e).__name__}: {e}"
#             )

#             return False

#         finally:

#             self.connecting.discard(
#                 guild.id
#             )

#     # =====================================================
#     # EXTRACT STREAM
#     # =====================================================

#     async def extract_stream(
#         self,
#         source
#     ):

#         loop = asyncio.get_running_loop()

#         def extract():

#             try:

#                 with yt_dlp.YoutubeDL(
#                     YTDL_OPTIONS
#                 ) as ydl:

#                     info = ydl.extract_info(
#                         source,
#                         download=False
#                     )

#                     if not info:

#                         return None

#                     # -------------------------------------------------
#                     # PLAYLIST
#                     # -------------------------------------------------

#                     if "entries" in info:

#                         entries = [
#                             item
#                             for item in info["entries"]
#                             if item
#                         ]

#                         if not entries:

#                             return None

#                         info = entries[0]

#                     return {

#                         "title":
#                             info.get(
#                                 "title",
#                                 "Malayalam Music"
#                             ),

#                         "stream_url":
#                             info.get(
#                                 "url"
#                             ),

#                         "webpage_url":
#                             info.get(
#                                 "webpage_url",
#                                 source
#                             )
#                     }

#             except Exception as e:

#                 print(
#                     f"❌ yt-dlp error:"
#                     f" {type(e).__name__}: {e}"
#                 )

#                 return None

#         return await loop.run_in_executor(
#             None,
#             extract
#         )

#     # =====================================================
#     # START MUSIC
#     # =====================================================

#     async def start_music(
#         self,
#         guild,
#         voice_client
#     ):

#         player = self.players.get(
#             guild.id
#         )

#         if not player:

#             return

#         if player.get(
#             "starting",
#             False
#         ):

#             return

#         if not voice_client.is_connected():

#             print(
#                 "❌ Cannot start music. "
#                 "Voice client is disconnected."
#             )

#             return

#         if not MUSIC_SOURCE:

#             print(
#                 "❌ MALAYALAM_SOURCE is empty."
#             )

#             return

#         player["starting"] = True

#         try:

#             print(
#                 "🔎 Getting music stream..."
#             )

#             stream = await self.extract_stream(
#                 MUSIC_SOURCE
#             )

#             if not stream:

#                 print(
#                     "❌ Could not extract stream."
#                 )

#                 player["title"] = (
#                     "Music source unavailable"
#                 )

#                 await self.update_panel(
#                     guild
#                 )

#                 return

#             stream_url = stream.get(
#                 "stream_url"
#             )

#             if not stream_url:

#                 print(
#                     "❌ No stream URL returned."
#                 )

#                 return

#             title = stream.get(
#                 "title",
#                 "Malayalam Music"
#             )

#             webpage_url = stream.get(
#                 "webpage_url",
#                 MUSIC_SOURCE
#             )

#             player["title"] = title

#             player["url"] = webpage_url

#             # -------------------------------------------------
#             # FFMPEG OPUS
#             #
#             # FFmpeg encodes the stream directly to Opus.
#             # This avoids requiring local Opus encoding
#             # from discord.py.
#             # -------------------------------------------------

#             source = discord.FFmpegOpusAudio(

#                 stream_url,

#                 before_options=
#                 FFMPEG_BEFORE_OPTIONS,

#                 options=
#                 FFMPEG_OPTIONS,

#                 bitrate=128
#             )

#             # -------------------------------------------------
#             # APPLY VOLUME
#             # -------------------------------------------------

#             source = discord.PCMVolumeTransformer(
#                 source,
#                 volume=player.get(
#                     "volume",
#                     DEFAULT_VOLUME
#                 )
#             )

#             # -------------------------------------------------
#             # CALLBACK
#             # -------------------------------------------------

#             def playback_finished(
#                 error
#             ):

#                 if error:

#                     print(
#                         f"⚠️ Playback error: {error}"
#                     )

#                 asyncio.run_coroutine_threadsafe(

#                     self.music_finished(
#                         guild.id
#                     ),

#                     self.bot.loop
#                 )

#             # -------------------------------------------------
#             # PLAY
#             # -------------------------------------------------

#             voice_client.play(

#                 source,

#                 after=playback_finished
#             )

#             player["paused"] = False

#             print(
#                 f"🎵 NOW PLAYING: {title}"
#             )

#             await self.update_panel(
#                 guild
#             )

#         except Exception as e:

#             print(
#                 f"❌ Music error:"
#                 f" {type(e).__name__}: {e}"
#             )

#             player["title"] = (
#                 "Music error - reconnecting..."
#             )

#             await self.update_panel(
#                 guild
#             )

#         finally:

#             player["starting"] = False

#     # =====================================================
#     # MUSIC FINISHED
#     # =====================================================

#     async def music_finished(
#         self,
#         guild_id
#     ):

#         await asyncio.sleep(
#             2
#         )

#         guild = self.bot.get_guild(
#             guild_id
#         )

#         if not guild:

#             return

#         player = self.players.get(
#             guild_id
#         )

#         if not player:

#             return

#         if player.get(
#             "paused",
#             False
#         ):

#             return

#         voice_client = guild.voice_client

#         if not voice_client:

#             return

#         if not voice_client.is_connected():

#             return

#         if voice_client.is_playing():

#             return

#         await self.start_music(
#             guild,
#             voice_client
#         )

#     # =====================================================
#     # WATCHDOG
#     # =====================================================

#     @tasks.loop(
#         seconds=WATCHDOG_INTERVAL
#     )
#     async def music_watchdog(
#         self
#     ):

#         for guild_id in list(
#             self.players.keys()
#         ):

#             try:

#                 guild = self.bot.get_guild(
#                     guild_id
#                 )

#                 if not guild:

#                     continue

#                 player = self.players.get(
#                     guild_id
#                 )

#                 if not player:

#                     continue

#                 voice_client = guild.voice_client

#                 # -------------------------------------------------
#                 # NOT CONNECTED
#                 # -------------------------------------------------

#                 if not voice_client:

#                     print(
#                         f"🔄 Watchdog reconnecting "
#                         f"{guild.name}"
#                     )

#                     await self.connect_to_voice(
#                         guild
#                     )

#                     continue

#                 # -------------------------------------------------
#                 # DISCONNECTED
#                 # -------------------------------------------------

#                 if not voice_client.is_connected():

#                     print(
#                         f"⚠️ Voice disconnected "
#                         f"in {guild.name}"
#                     )

#                     continue

#                 # -------------------------------------------------
#                 # MUSIC STOPPED
#                 # -------------------------------------------------

#                 if (
#                     not voice_client.is_playing()
#                     and not voice_client.is_paused()
#                     and not player.get(
#                         "starting",
#                         False
#                     )
#                 ):

#                     print(
#                         f"🔄 Restarting music "
#                         f"in {guild.name}"
#                     )

#                     await self.start_music(
#                         guild,
#                         voice_client
#                     )

#             except Exception as e:

#                 print(
#                     f"⚠️ Watchdog error:"
#                     f" {type(e).__name__}: {e}"
#                 )

#     # =====================================================
#     # WATCHDOG BEFORE LOOP
#     # =====================================================

#     @music_watchdog.before_loop
#     async def before_watchdog(
#         self
#     ):

#         await self.bot.wait_until_ready()

#         print(
#             "🎵 Music watchdog started."
#         )

#         await asyncio.sleep(
#             5
#         )

#         await self.restore_music()

#     # =====================================================
#     # RESTORE AFTER RESTART
#     # =====================================================

#     async def restore_music(
#         self
#     ):

#         if not self.config:

#             print(
#                 "ℹ️ No saved music systems."
#             )

#             return

#         print(
#             "🔄 Restoring music systems..."
#         )

#         for guild_id, config in list(
#             self.config.items()
#         ):

#             try:

#                 guild = self.bot.get_guild(
#                     int(guild_id)
#                 )

#                 if not guild:

#                     continue

#                 voice = guild.get_channel(
#                     config.get(
#                         "voice_channel_id"
#                     )
#                 )

#                 text = guild.get_channel(
#                     config.get(
#                         "text_channel_id"
#                     )
#                 )

#                 if not voice or not text:

#                     print(
#                         f"⚠️ Music channels missing "
#                         f"in {guild.name}"
#                     )

#                     continue

#                 self.players[
#                     guild.id
#                 ] = {

#                     "voice_channel_id":
#                         voice.id,

#                     "text_channel_id":
#                         text.id,

#                     "message_id":
#                         None,

#                     "volume":
#                         DEFAULT_VOLUME,

#                     "paused":
#                         False,

#                     "starting":
#                         False,

#                     "title":
#                         "Reconnecting...",

#                     "url":
#                         MUSIC_SOURCE
#                 }

#                 # -------------------------------------------------
#                 # FIND PANEL
#                 # -------------------------------------------------

#                 try:

#                     async for message in text.history(
#                         limit=30
#                     ):

#                         if (
#                             message.author.id
#                             == self.bot.user.id
#                             and message.embeds
#                         ):

#                             self.players[
#                                 guild.id
#                             ]["message_id"] = message.id

#                             break

#                 except:
#                     pass

#                 print(
#                     f"🔄 Restoring music "
#                     f"for {guild.name}"
#                 )

#                 await self.connect_to_voice(
#                     guild
#                 )

#             except Exception as e:

#                 print(
#                     f"❌ Restore error:"
#                     f" {type(e).__name__}: {e}"
#                 )

#     # =====================================================
#     # PLAYER EMBED
#     # =====================================================

#     def player_embed(
#         self,
#         guild
#     ):

#         player = self.players.get(
#             guild.id,
#             {}
#         )

#         title = player.get(
#             "title",
#             "Malayalam Music"
#         )

#         volume = int(
#             player.get(
#                 "volume",
#                 DEFAULT_VOLUME
#             ) * 100
#         )

#         voice_client = guild.voice_client

#         if player.get(
#             "paused",
#             False
#         ):

#             status = "⏸️ Paused"

#         elif (
#             voice_client
#             and voice_client.is_connected()
#             and voice_client.is_playing()
#         ):

#             status = "🟢 Playing"

#         elif (
#             voice_client
#             and voice_client.is_connected()
#         ):

#             status = "🟡 Connected"

#         else:

#             status = "🔴 Connecting..."

#         embed = discord.Embed(

#             title="🎵 MALAYALAM MUSIC",

#             description=(

#                 "━━━━━━━━━━━━━━━━━━━━\n\n"

#                 "🎶 **NOW PLAYING**\n\n"

#                 f"**{title}**\n\n"

#                 f"📻 **24/7 Malayalam Music**\n"
#                 f"🔊 **Volume:** `{volume}%`\n"
#                 f"📡 **Status:** {status}\n\n"

#                 "⏸️ Pause when you want.\n"
#                 "▶️ Resume anytime.\n"
#                 "🔊 Control the volume.\n\n"

#                 "━━━━━━━━━━━━━━━━━━━━"
#             ),

#             color=discord.Color.blurple()
#         )

#         if guild.icon:

#             embed.set_thumbnail(
#                 url=guild.icon.url
#             )

#         embed.set_footer(

#             text=(
#                 f"{guild.name} • "
#                 "24/7 Music"
#             ),

#             icon_url=(
#                 guild.icon.url
#                 if guild.icon
#                 else None
#             )
#         )

#         return embed

#     # =====================================================
#     # SEND PANEL
#     # =====================================================

#     async def send_panel(
#         self,
#         guild
#     ):

#         player = self.players.get(
#             guild.id
#         )

#         if not player:

#             return None

#         channel = guild.get_channel(
#             player[
#                 "text_channel_id"
#             ]
#         )

#         if not channel:

#             return None

#         try:

#             return await channel.send(

#                 embed=self.player_embed(
#                     guild
#                 ),

#                 view=MusicControlView(
#                     self.bot
#                 )
#             )

#         except Exception as e:

#             print(
#                 f"❌ Panel error: {e}"
#             )

#             return None

#     # =====================================================
#     # UPDATE PANEL
#     # =====================================================

#     async def update_panel(
#         self,
#         guild
#     ):

#         player = self.players.get(
#             guild.id
#         )

#         if not player:

#             return

#         channel = guild.get_channel(
#             player[
#                 "text_channel_id"
#             ]
#         )

#         if not channel:

#             return

#         message_id = player.get(
#             "message_id"
#         )

#         # -------------------------------------------------
#         # EDIT EXISTING
#         # -------------------------------------------------

#         if message_id:

#             try:

#                 message = await channel.fetch_message(
#                     message_id
#                 )

#                 await message.edit(

#                     embed=self.player_embed(
#                         guild
#                     ),

#                     view=MusicControlView(
#                         self.bot
#                     )
#                 )

#                 return

#             except:
#                 pass

#         # -------------------------------------------------
#         # CREATE NEW
#         # -------------------------------------------------

#         message = await self.send_panel(
#             guild
#         )

#         if message:

#             player[
#                 "message_id"
#             ] = message.id

#     # =====================================================
#     # CHANGE VOLUME
#     # =====================================================

#     async def change_volume(
#         self,
#         interaction,
#         amount
#     ):

#         guild = interaction.guild

#         player = self.players.get(
#             guild.id
#         )

#         if not player:

#             await interaction.response.send_message(
#                 "❌ Music system is not configured.",
#                 ephemeral=True
#             )

#             return

#         volume = player.get(
#             "volume",
#             DEFAULT_VOLUME
#         )

#         volume = max(
#             0.0,
#             min(
#                 1.0,
#                 volume + amount
#             )
#         )

#         player["volume"] = volume

#         voice_client = guild.voice_client

#         if (
#             voice_client
#             and voice_client.source
#             and isinstance(
#                 voice_client.source,
#                 discord.PCMVolumeTransformer
#             )
#         ):

#             voice_client.source.volume = volume

#         await interaction.response.send_message(

#             f"🔊 Volume: "
#             f"**{int(volume * 100)}%**",

#             ephemeral=True
#         )

#         await self.update_panel(
#             guild
#         )

#     # =====================================================
#     # PAUSE
#     # =====================================================

#     async def pause_music(
#         self,
#         interaction
#     ):

#         guild = interaction.guild

#         voice_client = guild.voice_client

#         if not voice_client:

#             await interaction.response.send_message(

#                 "❌ Bot is not connected to voice.",

#                 ephemeral=True
#             )

#             return

#         if voice_client.is_playing():

#             voice_client.pause()

#             self.players[
#                 guild.id
#             ]["paused"] = True

#             await interaction.response.send_message(
#                 "⏸️ Music paused.",
#                 ephemeral=True
#             )

#         else:

#             await interaction.response.send_message(
#                 "⚠️ Music is not playing.",
#                 ephemeral=True
#             )

#         await self.update_panel(
#             guild
#         )

#     # =====================================================
#     # RESUME
#     # =====================================================

#     async def resume_music(
#         self,
#         interaction
#     ):

#         guild = interaction.guild

#         voice_client = guild.voice_client

#         if not voice_client:

#             await interaction.response.send_message(

#                 "🔄 Reconnecting to voice...",

#                 ephemeral=True
#             )

#             connected = await self.connect_to_voice(
#                 guild
#             )

#             if not connected:

#                 await interaction.edit_original_response(

#                     content=(
#                         "❌ Could not connect to voice."
#                     )
#                 )

#                 return

#             voice_client = guild.voice_client

#         if voice_client.is_paused():

#             voice_client.resume()

#             self.players[
#                 guild.id
#             ]["paused"] = False

#             await interaction.response.send_message(
#                 "▶️ Music resumed.",
#                 ephemeral=True
#             )

#         elif voice_client.is_playing():

#             await interaction.response.send_message(
#                 "▶️ Music is already playing.",
#                 ephemeral=True
#             )

#         else:

#             self.players[
#                 guild.id
#             ]["paused"] = False

#             await self.start_music(
#                 guild,
#                 voice_client
#             )

#             await interaction.response.send_message(
#                 "▶️ Music started.",
#                 ephemeral=True
#             )

#         await self.update_panel(
#             guild
#         )

#     # =====================================================
#     # REFRESH
#     # =====================================================

#     async def refresh_music(
#         self,
#         interaction
#     ):

#         guild = interaction.guild

#         voice_client = guild.voice_client

#         if not voice_client:

#             connected = await self.connect_to_voice(
#                 guild
#             )

#             if not connected:

#                 await interaction.response.send_message(
#                     "❌ Could not connect to voice.",
#                     ephemeral=True
#                 )

#                 return

#             voice_client = guild.voice_client

#         try:

#             if voice_client.is_playing():

#                 voice_client.stop()

#         except:
#             pass

#         self.players[
#             guild.id
#         ]["paused"] = False

#         await asyncio.sleep(
#             1
#         )

#         await self.start_music(
#             guild,
#             voice_client
#         )

#         await interaction.response.send_message(
#             "🔄 Music refreshed.",
#             ephemeral=True
#         )


# # =========================================================
# # MUSIC CONTROL VIEW
# # =========================================================

# class MusicControlView(
#     discord.ui.View
# ):

#     def __init__(
#         self,
#         bot
#     ):

#         super().__init__(
#             timeout=None
#         )

#         self.bot = bot

#     # =====================================================
#     # GET COG
#     # =====================================================

#     def get_cog(self):

#         return self.bot.get_cog(
#             "MusicSystem"
#         )

#     # =====================================================
#     # VOLUME DOWN
#     # =====================================================

#     @discord.ui.button(
#         label="Volume -",
#         emoji="🔉",
#         style=discord.ButtonStyle.secondary,
#         custom_id="music_volume_down"
#     )
#     async def volume_down(
#         self,
#         interaction,
#         button
#     ):

#         cog = self.get_cog()

#         if not cog:

#             await interaction.response.send_message(
#                 "❌ Music system is loading.",
#                 ephemeral=True
#             )

#             return

#         await cog.change_volume(
#             interaction,
#             -0.10
#         )

#     # =====================================================
#     # VOLUME UP
#     # =====================================================

#     @discord.ui.button(
#         label="Volume +",
#         emoji="🔊",
#         style=discord.ButtonStyle.secondary,
#         custom_id="music_volume_up"
#     )
#     async def volume_up(
#         self,
#         interaction,
#         button
#     ):

#         cog = self.get_cog()

#         if not cog:

#             await interaction.response.send_message(
#                 "❌ Music system is loading.",
#                 ephemeral=True
#             )

#             return

#         await cog.change_volume(
#             interaction,
#             0.10
#         )

#     # =====================================================
#     # PAUSE
#     # =====================================================

#     @discord.ui.button(
#         label="Pause",
#         emoji="⏸️",
#         style=discord.ButtonStyle.primary,
#         custom_id="music_pause"
#     )
#     async def pause(
#         self,
#         interaction,
#         button
#     ):

#         cog = self.get_cog()

#         if not cog:

#             await interaction.response.send_message(
#                 "❌ Music system is loading.",
#                 ephemeral=True
#             )

#             return

#         await cog.pause_music(
#             interaction
#         )

#     # =====================================================
#     # RESUME
#     # =====================================================

#     @discord.ui.button(
#         label="Resume",
#         emoji="▶️",
#         style=discord.ButtonStyle.success,
#         custom_id="music_resume"
#     )
#     async def resume(
#         self,
#         interaction,
#         button
#     ):

#         cog = self.get_cog()

#         if not cog:

#             await interaction.response.send_message(
#                 "❌ Music system is loading.",
#                 ephemeral=True
#             )

#             return

#         await cog.resume_music(
#             interaction
#         )

#     # =====================================================
#     # REFRESH
#     # =====================================================

#     @discord.ui.button(
#         label="Refresh",
#         emoji="🔄",
#         style=discord.ButtonStyle.primary,
#         custom_id="music_refresh"
#     )
#     async def refresh(
#         self,
#         interaction,
#         button
#     ):

#         cog = self.get_cog()

#         if not cog:

#             await interaction.response.send_message(
#                 "❌ Music system is loading.",
#                 ephemeral=True
#             )

#             return

#         await cog.refresh_music(
#             interaction
#         )


# # =========================================================
# # SETUP
# # =========================================================

# async def setup(
#     bot
# ):

#     # Persistent buttons
#     bot.add_view(
#         MusicControlView(
#             bot
#         )
#     )

#     await bot.add_cog(
#         MusicSystem(
#             bot
#         )
#     )

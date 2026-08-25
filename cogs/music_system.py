import discord
from discord.ext import commands, tasks
from discord import app_commands

import asyncio
import json
import os
import yt_dlp


# =========================================================
# CONFIGURATION
# =========================================================

CONFIG_FILE = "music_config.json"

DEFAULT_VOLUME = 0.70

WATCHDOG_SECONDS = 15

# Render Environment Variable:
#
# MALAYALAM_SOURCE=your_authorized_music_stream_or_playlist
#
MALAYALAM_SOURCE = os.getenv(
    "MALAYALAM_SOURCE",
    ""
)


# =========================================================
# YT-DLP OPTIONS
# =========================================================

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "geo_bypass": True,
    "source_address": "0.0.0.0",
}


# =========================================================
# FFMPEG OPTIONS
# =========================================================

FFMPEG_BEFORE_OPTIONS = (
    "-reconnect 1 "
    "-reconnect_streamed 1 "
    "-reconnect_delay_max 5"
)

FFMPEG_OPTIONS = (
    "-vn "
    "-loglevel warning"
)


# =========================================================
# CONFIG FILE
# =========================================================

def load_config():

    if not os.path.exists(CONFIG_FILE):
        return {}

    try:

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as e:

        print(
            f"⚠️ Could not load music_config.json: {e}"
        )

        return {}


def save_config(config):

    try:

        with open(
            CONFIG_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                config,
                file,
                indent=4
            )

    except Exception as e:

        print(
            f"❌ Could not save music_config.json: {e}"
        )


# =========================================================
# MUSIC SYSTEM COG
# =========================================================

class MusicSystem(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.config = load_config()

        self.players = {}

        # Start watchdog
        self.music_watchdog.start()

    # =====================================================
    # COG UNLOAD
    # =====================================================

    def cog_unload(self):

        self.music_watchdog.cancel()

    # =====================================================
    # GET CONFIG
    # =====================================================

    def get_config(
        self,
        guild_id
    ):

        return self.config.get(
            str(guild_id)
        )

    # =====================================================
    # GET PLAYER
    # =====================================================

    def get_player(
        self,
        guild_id
    ):

        return self.players.get(
            guild_id
        )

    # =====================================================
    # /SETMUSIC
    # =====================================================

    @app_commands.command(
        name="setmusic",
        description="Create the 24/7 Malayalam music system."
    )
    @app_commands.describe(
        category="Category where the music channels will be created."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def setmusic(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

            return

        # -------------------------------------------------
        # CHECK MUSIC SOURCE
        # -------------------------------------------------

        if not MALAYALAM_SOURCE:

            await interaction.response.send_message(

                "❌ **MALAYALAM_SOURCE is not configured.**\n\n"

                "Go to:\n"
                "**Render → Environment Variables**\n\n"

                "Add:\n"
                "`MALAYALAM_SOURCE`\n\n"

                "with your authorized music/live stream source.",

                ephemeral=True
            )

            return

        # -------------------------------------------------
        # CHECK EXISTING SETUP
        # -------------------------------------------------

        existing = self.get_config(
            guild.id
        )

        if existing:

            voice = guild.get_channel(
                existing.get(
                    "voice_channel_id"
                )
            )

            text = guild.get_channel(
                existing.get(
                    "text_channel_id"
                )
            )

            await interaction.response.send_message(

                "⚠️ **Music system is already configured.**\n\n"

                f"🎧 Voice: "
                f"{voice.mention if voice else 'Missing'}\n"

                f"💬 Controls: "
                f"{text.mention if text else 'Missing'}\n\n"

                "To remove it first use:\n"
                "`/musicsetup remove`",

                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        print("")
        print("=" * 60)
        print("🎵 STARTING MUSIC SETUP")
        print("=" * 60)
        print(f"Server: {guild.name}")
        print(f"Category: {category.name}")
        print("=" * 60)

        # =================================================
        # CREATE VOICE CHANNEL
        # =================================================

        voice_overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=True,
                    connect=True,
                    speak=False
                )
        }

        try:

            voice_channel = await guild.create_voice_channel(

                name="Malayalam Music 🎵",

                category=category,

                overwrites=voice_overwrites,

                reason="24/7 Malayalam Music System"
            )

            print(
                f"✅ Created voice channel: "
                f"{voice_channel.name}"
            )

        except discord.Forbidden:

            await interaction.followup.send(

                "❌ I cannot create the music voice channel.\n\n"
                "Give the bot **Manage Channels** permission.",

                ephemeral=True
            )

            return

        except Exception as e:

            print(
                f"❌ Voice channel creation error: "
                f"{type(e).__name__}: {e}"
            )

            await interaction.followup.send(

                f"❌ Could not create voice channel.\n\n"
                f"`{type(e).__name__}: {e}`",

                ephemeral=True
            )

            return

        # =================================================
        # CREATE CONTROL CHANNEL
        # =================================================

        text_overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=False,
                    read_message_history=True
                )
        }

        try:

            text_channel = await guild.create_text_channel(

                name="music-controls",

                category=category,

                overwrites=text_overwrites,

                topic="24/7 Malayalam Music Controls",

                reason="24/7 Malayalam Music System"
            )

            print(
                f"✅ Created text channel: "
                f"{text_channel.name}"
            )

        except Exception as e:

            print(
                f"❌ Text channel creation error: {e}"
            )

            try:

                await voice_channel.delete(
                    reason="Music setup failed"
                )

            except:
                pass

            await interaction.followup.send(

                f"❌ Could not create music control channel.\n\n"
                f"`{type(e).__name__}: {e}`",

                ephemeral=True
            )

            return

        # =================================================
        # SAVE CONFIG
        # =================================================

        self.config[
            str(guild.id)
        ] = {

            "category_id":
                category.id,

            "voice_channel_id":
                voice_channel.id,

            "text_channel_id":
                text_channel.id
        }

        save_config(
            self.config
        )

        # =================================================
        # CREATE PLAYER
        # =================================================

        self.players[
            guild.id
        ] = {

            "voice_channel_id":
                voice_channel.id,

            "text_channel_id":
                text_channel.id,

            "volume":
                DEFAULT_VOLUME,

            "paused":
                False,

            "title":
                "Connecting to Malayalam Music...",

            "webpage_url":
                MALAYALAM_SOURCE,

            "message_id":
                None,

            "starting":
                False
        }

        # =================================================
        # SEND PLAYER PANEL
        # =================================================

        message = await self.send_player_panel(
            guild
        )

        if message:

            self.players[
                guild.id
            ]["message_id"] = message.id

        # =================================================
        # CONNECT TO VOICE
        # =================================================

        connected = await self.connect_music(
            guild
        )

        # =================================================
        # SUCCESS
        # =================================================

        if connected:

            await interaction.followup.send(

                "✅ **24/7 Malayalam Music System Started!**\n\n"

                f"🎧 **Voice:** {voice_channel.mention}\n"
                f"💬 **Controls:** {text_channel.mention}\n\n"

                "🎵 The bot is connected to the voice channel.\n"
                "🔄 Automatic reconnection is enabled.",

                ephemeral=True
            )

        else:

            await interaction.followup.send(

                "⚠️ **Music channels were created, "
                "but the bot could not connect to voice.**\n\n"

                f"🎧 **Voice:** {voice_channel.mention}\n"
                f"💬 **Controls:** {text_channel.mention}\n\n"

                "🔄 The watchdog will keep trying to reconnect.\n\n"

                "Run `/voicetest` to test the Discord voice connection.",

                ephemeral=True
            )

    # =====================================================
    # MUSIC SETUP GROUP
    # =====================================================

    musicsetup_group = app_commands.Group(
        name="musicsetup",
        description="Manage the music system."
    )

    # =====================================================
    # /MUSICSETUP REMOVE
    # =====================================================

    @musicsetup_group.command(
        name="remove",
        description="Remove the entire music system."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def musicsetup_remove(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        print("")
        print("=" * 60)
        print("🗑️ REMOVING MUSIC SYSTEM")
        print(f"Server: {guild.name}")
        print("=" * 60)

        removed = await self.remove_music_system(
            guild
        )

        if removed:

            await interaction.followup.send(

                "🗑️ **Music System Removed Successfully**\n\n"

                "✅ Bot disconnected from voice\n"
                "✅ Music voice channel deleted\n"
                "✅ Music control channel deleted\n"
                "✅ Music configuration deleted\n"
                "✅ Player state cleared\n\n"

                "You can now run `/setmusic` again.",

                ephemeral=True
            )

        else:

            await interaction.followup.send(

                "ℹ️ There is no music system configured "
                "for this server.",

                ephemeral=True
            )

    # =====================================================
    # REMOVE MUSIC SYSTEM
    # =====================================================

    async def remove_music_system(
        self,
        guild
    ):

        guild_id = guild.id

        config = self.config.get(
            str(guild_id)
        )

        player = self.players.get(
            guild_id
        )

        if not config and not player:

            return False

        # -------------------------------------------------
        # DISCONNECT BOT
        # -------------------------------------------------

        voice_client = guild.voice_client

        if voice_client:

            try:

                if voice_client.is_playing():

                    voice_client.stop()

            except:
                pass

            try:

                await voice_client.disconnect(
                    force=True
                )

                print(
                    "✅ Music bot disconnected."
                )

            except Exception as e:

                print(
                    f"⚠️ Disconnect error: {e}"
                )

        # -------------------------------------------------
        # FIND CHANNEL IDS
        # -------------------------------------------------

        voice_id = None
        text_id = None

        if config:

            voice_id = config.get(
                "voice_channel_id"
            )

            text_id = config.get(
                "text_channel_id"
            )

        if player:

            if voice_id is None:

                voice_id = player.get(
                    "voice_channel_id"
                )

            if text_id is None:

                text_id = player.get(
                    "text_channel_id"
                )

        # -------------------------------------------------
        # DELETE TEXT CHANNEL
        # -------------------------------------------------

        if text_id:

            text_channel = guild.get_channel(
                text_id
            )

            if text_channel:

                try:

                    await text_channel.delete(
                        reason="Music system removed"
                    )

                    print(
                        "🗑️ Deleted music control channel."
                    )

                except Exception as e:

                    print(
                        f"⚠️ Text channel delete error: {e}"
                    )

        # -------------------------------------------------
        # DELETE VOICE CHANNEL
        # -------------------------------------------------

        if voice_id:

            voice_channel = guild.get_channel(
                voice_id
            )

            if voice_channel:

                try:

                    await voice_channel.delete(
                        reason="Music system removed"
                    )

                    print(
                        "🗑️ Deleted music voice channel."
                    )

                except Exception as e:

                    print(
                        f"⚠️ Voice channel delete error: {e}"
                    )

        # -------------------------------------------------
        # DELETE CONFIG
        # -------------------------------------------------

        self.config.pop(
            str(guild_id),
            None
        )

        save_config(
            self.config
        )

        # -------------------------------------------------
        # CLEAR PLAYER
        # -------------------------------------------------

        self.players.pop(
            guild_id,
            None
        )

        print(
            "✅ Music configuration removed."
        )

        return True

    # =====================================================
    # /VOICETEST
    # =====================================================

    @app_commands.command(
        name="voicetest",
        description="Test the Discord voice connection."
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def voicetest(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This command can only be used inside a server.",
                ephemeral=True
            )

            return

        config = self.config.get(
            str(guild.id)
        )

        if not config:

            await interaction.response.send_message(

                "❌ Music system is not configured.\n\n"
                "Run `/setmusic` first.",

                ephemeral=True
            )

            return

        channel = guild.get_channel(
            config.get(
                "voice_channel_id"
            )
        )

        if channel is None:

            await interaction.response.send_message(

                "❌ The music voice channel does not exist.",

                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        print("")
        print("=" * 60)
        print("🎧 DISCORD VOICE DIAGNOSTIC")
        print("=" * 60)

        print(
            f"Guild: {guild.name}"
        )

        print(
            f"Guild ID: {guild.id}"
        )

        print(
            f"Channel: {channel.name}"
        )

        print(
            f"Channel ID: {channel.id}"
        )

        try:

            # -------------------------------------------------
            # REMOVE OLD CONNECTION
            # -------------------------------------------------

            old_vc = guild.voice_client

            if old_vc:

                print(
                    "⚠️ Existing voice client found."
                )

                try:

                    await old_vc.disconnect(
                        force=True
                    )

                except Exception as e:

                    print(
                        f"Disconnect error: {e}"
                    )

                await asyncio.sleep(
                    2
                )

            # -------------------------------------------------
            # CONNECT
            # -------------------------------------------------

            print(
                "🔌 Calling channel.connect()..."
            )

            voice_client = await channel.connect(

                timeout=60,

                reconnect=False
            )

            print(
                "✅ channel.connect() returned!"
            )

            print(
                f"Connected: "
                f"{voice_client.is_connected()}"
            )

            print(
                f"Channel: "
                f"{voice_client.channel}"
            )

            print(
                f"Endpoint: "
                f"{voice_client.endpoint}"
            )

            print(
                f"Session ID: "
                f"{'YES' if voice_client.session_id else 'NO'}"
            )

            print("=" * 60)

            await interaction.followup.send(

                "🟢 **VOICE CONNECTION SUCCESSFUL**\n\n"

                f"🎧 Channel: {channel.mention}\n"
                f"🔌 Connected: `{voice_client.is_connected()}`\n"
                f"📡 Endpoint: `{voice_client.endpoint}`\n\n"

                "Discord voice connection is working.",

                ephemeral=True
            )

        except asyncio.TimeoutError:

            print(
                "❌ VOICE CONNECTION TIMEOUT"
            )

            print("=" * 60)

            await interaction.followup.send(

                "🔴 **VOICE CONNECTION TIMEOUT**\n\n"

                "The bot has the Discord permissions, "
                "but Discord voice connection did not "
                "complete within 60 seconds.\n\n"

                "Check the Render logs.",

                ephemeral=True
            )

        except discord.Forbidden as e:

            print(
                f"❌ DISCORD FORBIDDEN: {e}"
            )

            print("=" * 60)

            await interaction.followup.send(

                "🔴 **Discord rejected the voice connection.**\n\n"

                f"`{e}`",

                ephemeral=True
            )

        except discord.ClientException as e:

            print(
                f"❌ DISCORD CLIENT ERROR: {e}"
            )

            print("=" * 60)

            await interaction.followup.send(

                "🔴 **Discord client error.**\n\n"

                f"`{e}`",

                ephemeral=True
            )

        except Exception as e:

            print(
                f"❌ VOICE ERROR TYPE: "
                f"{type(e).__name__}"
            )

            print(
                f"❌ VOICE ERROR: {e}"
            )

            print("=" * 60)

            await interaction.followup.send(

                "🔴 **Voice connection failed.**\n\n"

                f"Type: `{type(e).__name__}`\n"
                f"Error: `{e}`",

                ephemeral=True
            )

    # =====================================================
    # CONNECT MUSIC
    # =====================================================

    async def connect_music(
        self,
        guild
    ):

        player = self.players.get(
            guild.id
        )

        if not player:

            print(
                f"❌ No player data for {guild.name}"
            )

            return False

        voice_channel = guild.get_channel(
            player["voice_channel_id"]
        )

        if voice_channel is None:

            print(
                f"❌ Music voice channel not found "
                f"in {guild.name}"
            )

            return False

        print(
            f"🎧 Music voice channel found: "
            f"{voice_channel.name}"
        )

        voice_client = guild.voice_client

        # =================================================
        # EXISTING CONNECTION
        # =================================================

        if voice_client:

            if voice_client.is_connected():

                print(
                    f"✅ Already connected to "
                    f"{voice_client.channel.name}"
                )

                if (
                    voice_client.channel.id
                    != voice_channel.id
                ):

                    print(
                        f"🔄 Moving bot to "
                        f"{voice_channel.name}"
                    )

                    try:

                        await voice_client.move_to(
                            voice_channel
                        )

                    except Exception as e:

                        print(
                            f"❌ Move failed: {e}"
                        )

                        return False

            else:

                print(
                    "⚠️ Existing voice client is disconnected."
                )

                try:

                    await voice_client.disconnect(
                        force=True
                    )

                except:
                    pass

                voice_client = None

        # =================================================
        # NEW CONNECTION
        # =================================================

        if voice_client is None:

            print(
                f"🔌 Connecting to "
                f"{voice_channel.name}..."
            )

            try:

                voice_client = await voice_channel.connect(

                    timeout=60,

                    reconnect=True
                )

                print(
                    "🟢 BOT CONNECTED TO VOICE!"
                )

            except asyncio.TimeoutError:

                print(
                    "❌ VOICE CONNECTION TIMEOUT"
                )

                return False

            except discord.Forbidden as e:

                print(
                    f"❌ DISCORD FORBIDDEN: {e}"
                )

                return False

            except discord.ClientException as e:

                print(
                    f"❌ DISCORD CLIENT ERROR: {e}"
                )

                return False

            except Exception as e:

                print(
                    f"❌ VOICE CONNECTION ERROR: "
                    f"{type(e).__name__}: {e}"
                )

                return False

        # =================================================
        # VERIFY
        # =================================================

        if not voice_client.is_connected():

            print(
                "❌ Voice client is disconnected "
                "after connection."
            )

            return False

        print(
            f"🟢 Connected to "
            f"{voice_client.channel.name}"
        )

        # =================================================
        # START MUSIC
        # =================================================

        if (
            not voice_client.is_playing()
            and not voice_client.is_paused()
        ):

            await self.start_stream(
                guild,
                voice_client
            )

        await self.update_player_panel(
            guild
        )

        return True

    # =====================================================
    # EXTRACT MUSIC STREAM
    # =====================================================

    async def extract_stream(
        self,
        source
    ):

        loop = asyncio.get_running_loop()

        def extract():

            try:

                with yt_dlp.YoutubeDL(
                    YTDL_OPTIONS
                ) as ydl:

                    info = ydl.extract_info(
                        source,
                        download=False
                    )

                    if not info:

                        return None

                    # -----------------------------------------
                    # Playlist
                    # -----------------------------------------

                    if "entries" in info:

                        entries = [
                            entry
                            for entry in info["entries"]
                            if entry
                        ]

                        if not entries:

                            return None

                        info = entries[0]

                    return {

                        "title":
                            info.get(
                                "title",
                                "Malayalam Music"
                            ),

                        "stream_url":
                            info.get(
                                "url"
                            ),

                        "webpage_url":
                            info.get(
                                "webpage_url",
                                source
                            )
                    }

            except Exception as e:

                print(
                    f"❌ yt-dlp extraction error:"
                    f" {type(e).__name__}: {e}"
                )

                return None

        return await loop.run_in_executor(
            None,
            extract
        )

    # =====================================================
    # START STREAM
    # =====================================================

    async def start_stream(
        self,
        guild,
        voice_client
    ):

        player = self.players.get(
            guild.id
        )

        if not player:

            return

        if player.get(
            "starting",
            False
        ):

            return

        if not voice_client.is_connected():

            print(
                f"❌ Cannot start music because "
                f"bot is not connected."
            )

            return

        if not MALAYALAM_SOURCE:

            print(
                "❌ MALAYALAM_SOURCE is empty."
            )

            return

        player["starting"] = True

        try:

            print(
                f"🔎 Extracting music stream "
                f"for {guild.name}..."
            )

            data = await self.extract_stream(
                MALAYALAM_SOURCE
            )

            if not data:

                player["title"] = (
                    "Music source unavailable"
                )

                await self.update_player_panel(
                    guild
                )

                return

            stream_url = data.get(
                "stream_url"
            )

            if not stream_url:

                print(
                    "❌ yt-dlp returned no stream URL."
                )

                return

            title = data.get(
                "title",
                "Malayalam Music"
            )

            webpage_url = data.get(
                "webpage_url",
                MALAYALAM_SOURCE
            )

            player["title"] = title

            player["webpage_url"] = webpage_url

            player["paused"] = False

            print(
                f"🎵 Preparing FFmpeg: {title}"
            )

            # =================================================
            # FFMPEG SOURCE
            # =================================================

            ffmpeg_audio = discord.FFmpegPCMAudio(

                stream_url,

                before_options=
                FFMPEG_BEFORE_OPTIONS,

                options=
                FFMPEG_OPTIONS
            )

            audio_source = discord.PCMVolumeTransformer(

                ffmpeg_audio,

                volume=
                player.get(
                    "volume",
                    DEFAULT_VOLUME
                )
            )

            # =================================================
            # CALLBACK
            # =================================================

            def after_playing(error):

                if error:

                    print(
                        f"⚠️ Playback error: {error}"
                    )

                asyncio.run_coroutine_threadsafe(

                    self.stream_finished(
                        guild.id
                    ),

                    self.bot.loop
                )

            # =================================================
            # PLAY
            # =================================================

            voice_client.play(

                audio_source,

                after=after_playing
            )

            print(
                f"🟢 NOW PLAYING: {title}"
            )

            await self.update_player_panel(
                guild
            )

        except Exception as e:

            print(
                f"❌ STREAM/FFMPEG ERROR:"
                f" {type(e).__name__}: {e}"
            )

            player["title"] = (
                "Stream error - reconnecting..."
            )

            await self.update_player_panel(
                guild
            )

        finally:

            player["starting"] = False

    # =====================================================
    # STREAM FINISHED
    # =====================================================

    async def stream_finished(
        self,
        guild_id
    ):

        await asyncio.sleep(
            2
        )

        guild = self.bot.get_guild(
            guild_id
        )

        if not guild:

            return

        player = self.players.get(
            guild_id
        )

        if not player:

            return

        if player.get(
            "paused",
            False
        ):

            return

        voice_client = guild.voice_client

        if not voice_client:

            return

        if not voice_client.is_connected():

            return

        if voice_client.is_playing():

            return

        print(
            f"🔄 Stream ended. Refreshing "
            f"for {guild.name}"
        )

        await self.start_stream(
            guild,
            voice_client
        )

    # =====================================================
    # WATCHDOG
    # =====================================================

    @tasks.loop(
        seconds=WATCHDOG_SECONDS
    )
    async def music_watchdog(
        self
    ):

        for guild_id in list(
            self.players.keys()
        ):

            try:

                guild = self.bot.get_guild(
                    guild_id
                )

                if not guild:

                    continue

                player = self.players.get(
                    guild_id
                )

                if not player:

                    continue

                voice_client = guild.voice_client

                # -----------------------------------------
                # NO VOICE CONNECTION
                # -----------------------------------------

                if not voice_client:

                    print(
                        f"🔄 Watchdog reconnecting "
                        f"to {guild.name}"
                    )

                    await self.connect_music(
                        guild
                    )

                    continue

                # -----------------------------------------
                # DISCONNECTED
                # -----------------------------------------

                if not voice_client.is_connected():

                    print(
                        f"⚠️ Voice disconnected "
                        f"from {guild.name}"
                    )

                    try:

                        await voice_client.disconnect(
                            force=True
                        )

                    except:
                        pass

                    await asyncio.sleep(
                        2
                    )

                    await self.connect_music(
                        guild
                    )

                    continue

                # -----------------------------------------
                # CONNECTED BUT MUSIC STOPPED
                # -----------------------------------------

                if (
                    not voice_client.is_playing()
                    and not voice_client.is_paused()
                    and not player.get(
                        "starting",
                        False
                    )
                ):

                    print(
                        f"🔄 Watchdog restarting "
                        f"music in {guild.name}"
                    )

                    await self.start_stream(
                        guild,
                        voice_client
                    )

            except Exception as e:

                print(
                    f"⚠️ Watchdog error:"
                    f" {type(e).__name__}: {e}"
                )

    # =====================================================
    # WATCHDOG START
    # =====================================================

    @music_watchdog.before_loop
    async def before_watchdog(
        self
    ):

        await self.bot.wait_until_ready()

        print(
            "🎵 Music watchdog started."
        )

        await self.restore_players()

    # =====================================================
    # RESTORE AFTER RESTART
    # =====================================================

    async def restore_players(
        self
    ):

        await asyncio.sleep(
            5
        )

        if not self.config:

            print(
                "ℹ️ No saved music systems."
            )

            return

        print(
            "🔄 Restoring saved music systems..."
        )

        for guild_id, config in list(
            self.config.items()
        ):

            try:

                guild = self.bot.get_guild(
                    int(guild_id)
                )

                if not guild:

                    continue

                voice_channel = guild.get_channel(
                    config.get(
                        "voice_channel_id"
                    )
                )

                text_channel = guild.get_channel(
                    config.get(
                        "text_channel_id"
                    )
                )

                if not voice_channel:

                    print(
                        f"⚠️ Voice channel missing "
                        f"in {guild.name}"
                    )

                    continue

                if not text_channel:

                    print(
                        f"⚠️ Text channel missing "
                        f"in {guild.name}"
                    )

                    continue

                self.players[
                    guild.id
                ] = {

                    "voice_channel_id":
                        voice_channel.id,

                    "text_channel_id":
                        text_channel.id,

                    "volume":
                        DEFAULT_VOLUME,

                    "paused":
                        False,

                    "title":
                        "Reconnecting...",

                    "webpage_url":
                        MALAYALAM_SOURCE,

                    "message_id":
                        None,

                    "starting":
                        False
                }

                # -----------------------------------------
                # FIND EXISTING PANEL
                # -----------------------------------------

                try:

                    async for message in text_channel.history(
                        limit=30
                    ):

                        if (
                            message.author.id
                            == self.bot.user.id
                            and message.embeds
                        ):

                            self.players[
                                guild.id
                            ]["message_id"] = message.id

                            break

                except Exception as e:

                    print(
                        f"⚠️ Could not find old panel: {e}"
                    )

                print(
                    f"🔄 Restoring {guild.name}"
                )

                await self.connect_music(
                    guild
                )

            except Exception as e:

                print(
                    f"❌ Restore error for "
                    f"{guild_id}: "
                    f"{type(e).__name__}: {e}"
                )

    # =====================================================
    # PLAYER EMBED
    # =====================================================

    def create_player_embed(
        self,
        guild
    ):

        player = self.players.get(
            guild.id,
            {}
        )

        title = player.get(
            "title",
            "Malayalam Music"
        )

        volume = int(
            player.get(
                "volume",
                DEFAULT_VOLUME
            ) * 100
        )

        voice_client = guild.voice_client

        if player.get(
            "paused",
            False
        ):

            status = "⏸️ Paused"

        elif (
            voice_client
            and voice_client.is_connected()
            and voice_client.is_playing()
        ):

            status = "🟢 Playing"

        elif (
            voice_client
            and voice_client.is_connected()
        ):

            status = "🟡 Connected"

        else:

            status = "🔴 Disconnected"

        embed = discord.Embed(

            title="🎵 MALAYALAM MUSIC",

            description=(

                "━━━━━━━━━━━━━━━━━━━━\n\n"

                "🎶 **NOW PLAYING**\n\n"

                f"**{title}**\n\n"

                "📻 **Malayalam Music 24/7**\n"
                f"🔊 **Volume:** `{volume}%`\n"
                f"📡 **Status:** {status}\n\n"

                "🎧 Enjoy Malayalam music!\n\n"

                "━━━━━━━━━━━━━━━━━━━━"
            ),

            color=discord.Color.blurple()
        )

        if guild.icon:

            embed.set_thumbnail(
                url=guild.icon.url
            )

        embed.set_footer(

            text=(
                f"{guild.name} • "
                "24/7 Malayalam Music"
            ),

            icon_url=(
                guild.icon.url
                if guild.icon
                else None
            )
        )

        return embed

    # =====================================================
    # SEND PLAYER PANEL
    # =====================================================

    async def send_player_panel(
        self,
        guild
    ):

        player = self.players.get(
            guild.id
        )

        if not player:

            return None

        text_channel = guild.get_channel(
            player["text_channel_id"]
        )

        if not text_channel:

            return None

        try:

            message = await text_channel.send(

                embed=self.create_player_embed(
                    guild
                ),

                view=MusicControlView(
                    self.bot
                )
            )

            return message

        except Exception as e:

            print(
                f"❌ Could not send music panel: {e}"
            )

            return None

    # =====================================================
    # UPDATE PLAYER PANEL
    # =====================================================

    async def update_player_panel(
        self,
        guild
    ):

        player = self.players.get(
            guild.id
        )

        if not player:

            return

        text_channel = guild.get_channel(
            player["text_channel_id"]
        )

        if not text_channel:

            return

        message_id = player.get(
            "message_id"
        )

        # -------------------------------------------------
        # EDIT OLD MESSAGE
        # -------------------------------------------------

        if message_id:

            try:

                message = await text_channel.fetch_message(
                    message_id
                )

                await message.edit(

                    embed=self.create_player_embed(
                        guild
                    ),

                    view=MusicControlView(
                        self.bot
                    )
                )

                return

            except Exception:
                pass

        # -------------------------------------------------
        # CREATE NEW MESSAGE
        # -------------------------------------------------

        try:

            message = await text_channel.send(

                embed=self.create_player_embed(
                    guild
                ),

                view=MusicControlView(
                    self.bot
                )
            )

            player["message_id"] = message.id

        except Exception as e:

            print(
                f"❌ Could not create player panel: {e}"
            )

    # =====================================================
    # ENSURE VOICE CONNECTION
    # =====================================================

    async def ensure_connection(
        self,
        guild
    ):

        voice_client = guild.voice_client

        if (
            voice_client
            and voice_client.is_connected()
        ):

            return voice_client

        print(
            f"🔄 Button requested voice reconnect "
            f"for {guild.name}"
        )

        connected = await self.connect_music(
            guild
        )

        if not connected:

            return None

        return guild.voice_client

    # =====================================================
    # VOLUME
    # =====================================================

    async def change_volume(
        self,
        interaction,
        amount
    ):

        guild = interaction.guild

        player = self.players.get(
            guild.id
        )

        if not player:

            await interaction.response.send_message(
                "❌ Music system is not configured.",
                ephemeral=True
            )

            return

        current = player.get(
            "volume",
            DEFAULT_VOLUME
        )

        new_volume = max(
            0.0,
            min(
                1.0,
                current + amount
            )
        )

        player["volume"] = new_volume

        voice_client = guild.voice_client

        if (
            voice_client
            and voice_client.source
            and isinstance(
                voice_client.source,
                discord.PCMVolumeTransformer
            )
        ):

            voice_client.source.volume = new_volume

        await interaction.response.send_message(

            f"🔊 Volume: "
            f"**{int(new_volume * 100)}%**",

            ephemeral=True
        )

        await self.update_player_panel(
            guild
        )

    # =====================================================
    # PAUSE
    # =====================================================

    async def pause_music(
        self,
        interaction
    ):

        guild = interaction.guild

        voice_client = await self.ensure_connection(
            guild
        )

        if not voice_client:

            await interaction.response.send_message(

                "❌ I could not connect to the music "
                "voice channel.",

                ephemeral=True
            )

            return

        if voice_client.is_playing():

            voice_client.pause()

            self.players[
                guild.id
            ]["paused"] = True

            await interaction.response.send_message(
                "⏸️ Music paused.",
                ephemeral=True
            )

        elif voice_client.is_paused():

            await interaction.response.send_message(
                "⏸️ Music is already paused.",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                "⚠️ Nothing is currently playing.",
                ephemeral=True
            )

        await self.update_player_panel(
            guild
        )

    # =====================================================
    # RESUME
    # =====================================================

    async def resume_music(
        self,
        interaction
    ):

        guild = interaction.guild

        voice_client = await self.ensure_connection(
            guild
        )

        if not voice_client:

            await interaction.response.send_message(

                "❌ I could not connect to the music "
                "voice channel.",

                ephemeral=True
            )

            return

        if voice_client.is_paused():

            voice_client.resume()

            self.players[
                guild.id
            ]["paused"] = False

            await interaction.response.send_message(
                "▶️ Music resumed.",
                ephemeral=True
            )

        elif voice_client.is_playing():

            await interaction.response.send_message(
                "▶️ Music is already playing.",
                ephemeral=True
            )

        else:

            self.players[
                guild.id
            ]["paused"] = False

            await self.start_stream(
                guild,
                voice_client
            )

            await interaction.response.send_message(
                "▶️ Music started.",
                ephemeral=True
            )

        await self.update_player_panel(
            guild
        )

    # =====================================================
    # REFRESH
    # =====================================================

    async def refresh_music(
        self,
        interaction
    ):

        guild = interaction.guild

        voice_client = await self.ensure_connection(
            guild
        )

        if not voice_client:

            await interaction.response.send_message(

                "❌ I could not connect to the music "
                "voice channel.",

                ephemeral=True
            )

            return

        try:

            if voice_client.is_playing():

                voice_client.stop()

        except:
            pass

        self.players[
            guild.id
        ]["paused"] = False

        await asyncio.sleep(
            1
        )

        await self.start_stream(
            guild,
            voice_client
        )

        await interaction.response.send_message(
            "🔄 Music stream refreshed.",
            ephemeral=True
        )


# =========================================================
# CONTROL PANEL
# =========================================================

class MusicControlView(
    discord.ui.View
):

    def __init__(
        self,
        bot
    ):

        super().__init__(
            timeout=None
        )

        self.bot = bot

    # =====================================================
    # GET MUSIC COG
    # =====================================================

    def get_cog(self):

        return self.bot.get_cog(
            "MusicSystem"
        )

    # =====================================================
    # VOLUME DOWN
    # =====================================================

    @discord.ui.button(
        label="Volume -",
        emoji="🔉",
        style=discord.ButtonStyle.secondary,
        custom_id="music_volume_down"
    )
    async def volume_down(
        self,
        interaction,
        button
    ):

        cog = self.get_cog()

        if not cog:

            await interaction.response.send_message(
                "❌ Music system is still loading.",
                ephemeral=True
            )

            return

        await cog.change_volume(
            interaction,
            -0.10
        )

    # =====================================================
    # VOLUME UP
    # =====================================================

    @discord.ui.button(
        label="Volume +",
        emoji="🔊",
        style=discord.ButtonStyle.secondary,
        custom_id="music_volume_up"
    )
    async def volume_up(
        self,
        interaction,
        button
    ):

        cog = self.get_cog()

        if not cog:

            await interaction.response.send_message(
                "❌ Music system is still loading.",
                ephemeral=True
            )

            return

        await cog.change_volume(
            interaction,
            0.10
        )

    # =====================================================
    # PAUSE
    # =====================================================

    @discord.ui.button(
        label="Pause",
        emoji="⏸️",
        style=discord.ButtonStyle.primary,
        custom_id="music_pause"
    )
    async def pause(
        self,
        interaction,
        button
    ):

        cog = self.get_cog()

        if not cog:

            await interaction.response.send_message(
                "❌ Music system is still loading.",
                ephemeral=True
            )

            return

        await cog.pause_music(
            interaction
        )

    # =====================================================
    # RESUME
    # =====================================================

    @discord.ui.button(
        label="Resume",
        emoji="▶️",
        style=discord.ButtonStyle.success,
        custom_id="music_resume"
    )
    async def resume(
        self,
        interaction,
        button
    ):

        cog = self.get_cog()

        if not cog:

            await interaction.response.send_message(
                "❌ Music system is still loading.",
                ephemeral=True
            )

            return

        await cog.resume_music(
            interaction
        )

    # =====================================================
    # REFRESH
    # =====================================================

    @discord.ui.button(
        label="Refresh",
        emoji="🔄",
        style=discord.ButtonStyle.primary,
        custom_id="music_refresh"
    )
    async def refresh(
        self,
        interaction,
        button
    ):

        cog = self.get_cog()

        if not cog:

            await interaction.response.send_message(
                "❌ Music system is still loading.",
                ephemeral=True
            )

            return

        await cog.refresh_music(
            interaction
        )


# =========================================================
# COG SETUP
# =========================================================

async def setup(
    bot
):

    # Persistent control buttons
    bot.add_view(
        MusicControlView(
            bot
        )
    )

    await bot.add_cog(
        MusicSystem(
            bot
        )
    )

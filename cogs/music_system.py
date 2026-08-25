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

# Put your authorized Malayalam live stream / playlist URL
# in Render Environment Variables:
#
# MALAYALAM_SOURCE = https://....
#
MALAYALAM_SOURCE = os.getenv(
    "MALAYALAM_SOURCE",
    ""
)

DEFAULT_VOLUME = 0.70

WATCHDOG_SECONDS = 15


# =========================================================
# YT-DLP
# =========================================================

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "geo_bypass": True,
    "source_address": "0.0.0.0",
    "noplaylist": False,
}


# =========================================================
# FFMPEG
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
        ) as f:

            return json.load(f)

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
        ) as f:

            json.dump(
                config,
                f,
                indent=4
            )

    except Exception as e:

        print(
            f"❌ Could not save music config: {e}"
        )


# =========================================================
# MUSIC SYSTEM
# =========================================================

class MusicSystem(commands.Cog):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        self.config = load_config()

        # Runtime player information
        #
        # guild_id: {
        #     voice_channel_id,
        #     text_channel_id,
        #     volume,
        #     paused,
        #     title,
        #     webpage_url,
        #     message_id,
        #     starting
        # }

        self.players = {}

        # Start watchdog
        self.music_watchdog.start()

    @app_commands.command(
    name="voicetest",
    description="Test the Discord voice connection."
)
@app_commands.checks.has_permissions(administrator=True)
async def voicetest(self, interaction: discord.Interaction):

    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "❌ Server only.",
            ephemeral=True
        )
        return

    config = self.config.get(str(guild.id))

    if not config:
        await interaction.response.send_message(
            "❌ Music system is not configured. Run /setmusic first.",
            ephemeral=True
        )
        return

    channel = guild.get_channel(
        config.get("voice_channel_id")
    )

    if channel is None:
        await interaction.response.send_message(
            "❌ Music voice channel does not exist.",
            ephemeral=True
        )
        return

    await interaction.response.defer(
        ephemeral=True
    )

    print("\n" + "=" * 60)
    print("🎧 DISCORD VOICE DIAGNOSTIC")
    print("=" * 60)
    print(f"Guild: {guild.name}")
    print(f"Guild ID: {guild.id}")
    print(f"Channel: {channel.name}")
    print(f"Channel ID: {channel.id}")

    try:

        # Remove stale connection
        old_vc = guild.voice_client

        if old_vc:

            print("⚠️ Existing voice client found.")

            try:
                await old_vc.disconnect(force=True)
            except Exception as e:
                print(f"Disconnect error: {e}")

            await asyncio.sleep(2)

        print("🔌 Calling channel.connect()...")

        vc = await channel.connect(
            timeout=60,
            reconnect=False
        )

        print("✅ channel.connect() returned!")

        print(f"Connected: {vc.is_connected()}")
        print(f"Channel: {vc.channel}")

        if vc.endpoint:
            print(f"Endpoint: {vc.endpoint}")

        if vc.session_id:
            print(f"Session ID received: YES")
        else:
            print("Session ID received: NO")

        print("=" * 60)

        await interaction.followup.send(
            "🟢 **VOICE CONNECTION SUCCESSFUL**\n\n"
            f"🎧 Channel: {channel.mention}\n"
            f"🔌 Connected: `{vc.is_connected()}`\n"
            f"📡 Endpoint: `{vc.endpoint}`",
            ephemeral=True
        )

    except asyncio.TimeoutError:

        print(
            "❌ VOICE CONNECTION TIMEOUT"
        )

        print(
            "The bot could not complete the Discord "
            "voice connection within 60 seconds."
        )

        print("=" * 60)

        await interaction.followup.send(
            "🔴 **VOICE CONNECTION TIMEOUT**\n\n"
            "The bot has the Discord permissions, "
            "but it could not complete the Discord "
            "voice connection.\n\n"
            "Check the Render logs — this points to "
            "the voice/network connection rather than "
            "the music source.",
            ephemeral=True
        )

    except discord.Forbidden as e:

        print(
            f"❌ DISCORD FORBIDDEN: {e}"
        )

        print("=" * 60)

        await interaction.followup.send(
            f"🔴 **Discord rejected the voice connection**\n\n"
            f"`{e}`",
            ephemeral=True
        )

    except discord.ClientException as e:

        print(
            f"❌ DISCORD CLIENT ERROR: {e}"
        )

        print("=" * 60)

        await interaction.followup.send(
            f"🔴 **Discord client error**\n\n"
            f"`{e}`",
            ephemeral=True
        )

    except Exception as e:

        print(
            f"❌ VOICE ERROR TYPE: {type(e).__name__}"
        )

        print(
            f"❌ VOICE ERROR: {e}"
        )

        print("=" * 60)

        await interaction.followup.send(
            f"🔴 **Voice connection failed**\n\n"
            f"Type: `{type(e).__name__}`\n"
            f"Error: `{e}`",
            ephemeral=True
        )
    # =====================================================
    # COG UNLOAD
    # =====================================================

    def cog_unload(self):

        self.music_watchdog.cancel()

    # =====================================================
    # GET CONFIG
    # =====================================================

    def get_guild_config(
        self,
        guild_id
    ):

        return self.config.get(
            str(guild_id)
        )

    # =====================================================
    # /SETMUSIC
    # =====================================================

    @app_commands.command(
        name="setmusic",
        description="Set up the 24/7 Malayalam music player."
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
        # CHECK SOURCE
        # -------------------------------------------------

        if not MALAYALAM_SOURCE:

            await interaction.response.send_message(
                "❌ `MALAYALAM_SOURCE` is not configured.\n\n"
                "Add it to your Render Environment Variables.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        # -------------------------------------------------
        # CHECK EXISTING CONFIG
        # -------------------------------------------------

        old_config = self.get_guild_config(
            guild.id
        )

        if old_config:

            old_voice = guild.get_channel(
                old_config.get(
                    "voice_channel_id"
                )
            )

            old_text = guild.get_channel(
                old_config.get(
                    "text_channel_id"
                )
            )

            await interaction.followup.send(

                "⚠️ **Music system is already configured.**\n\n"

                f"🎧 Voice: "
                f"{old_voice.mention if old_voice else 'Missing'}\n"

                f"💬 Controls: "
                f"{old_text.mention if old_text else 'Missing'}",

                ephemeral=True
            )

            return

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

        except discord.Forbidden:

            await interaction.followup.send(

                "❌ I cannot create the music voice channel.\n\n"

                "Make sure the bot has:\n"
                "• Manage Channels\n"
                "• View Channels\n"
                "• Connect\n"
                "• Speak",

                ephemeral=True
            )

            return

        except Exception as e:

            print(
                f"❌ Voice channel creation error: {e}"
            )

            await interaction.followup.send(
                f"❌ Could not create voice channel.\n"
                f"`{type(e).__name__}: {e}`",
                ephemeral=True
            )

            return

        # =================================================
        # CREATE TEXT CHANNEL
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

                topic="24/7 Malayalam Music Player",

                reason="24/7 Malayalam Music Controls"
            )

        except discord.Forbidden:

            try:

                await voice_channel.delete(
                    reason="Music control channel creation failed"
                )

            except:
                pass

            await interaction.followup.send(

                "❌ I cannot create the music control channel.\n"
                "Make sure the bot has **Manage Channels**.",

                ephemeral=True
            )

            return

        except Exception as e:

            try:

                await voice_channel.delete(
                    reason="Music control channel creation failed"
                )

            except:
                pass

            await interaction.followup.send(
                f"❌ Could not create control channel.\n"
                f"`{type(e).__name__}: {e}`",
                ephemeral=True
            )

            return

        # =================================================
        # SAVE CONFIGURATION
        # =================================================

        self.config[
            str(guild.id)
        ] = {

            "category_id": category.id,

            "voice_channel_id": voice_channel.id,

            "text_channel_id": text_channel.id
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
        # CONNECT
        # =================================================

        try:

            connected = await self.connect_and_play(
                guild
            )

            if not connected:

                await interaction.followup.send(

                    "⚠️ The music channels were created, "
                    "but I could not connect to the voice channel.\n\n"

                    "Check the Render logs for the exact reason.\n\n"

                    "Make sure the bot has:\n"
                    "• View Channel\n"
                    "• Connect\n"
                    "• Speak\n"
                    "• Manage Channels",

                    ephemeral=True
                )

                return

        except Exception as e:

            print(
                f"❌ Music startup error: "
                f"{type(e).__name__}: {e}"
            )

            await interaction.followup.send(

                f"❌ Music startup failed:\n"
                f"`{type(e).__name__}: {e}`",

                ephemeral=True
            )

            return

        # =================================================
        # SUCCESS
        # =================================================

        await interaction.followup.send(

            "✅ **24/7 Malayalam Music is now active!**\n\n"

            f"🎧 **Voice:** {voice_channel.mention}\n"
            f"💬 **Controls:** {text_channel.mention}\n\n"

            "🎵 The bot will stay in the voice channel.\n"
            "🔄 The stream automatically reconnects.\n"
            "📡 The stream URL is refreshed when required.",

            ephemeral=True
        )

    # =====================================================
    # CONNECT TO VOICE
    # =====================================================

    async def connect_and_play(
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
                f"for {guild.name}"
            )

            return False

        print(
            f"🎧 Music channel found: "
            f"{voice_channel.name} "
            f"({voice_channel.id})"
        )

        voice_client = guild.voice_client

        # =================================================
        # EXISTING VOICE CLIENT
        # =================================================

        if voice_client:

            print(
                f"🔌 Existing voice client found "
                f"for {guild.name}"
            )

            if voice_client.is_connected():

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
                            f"❌ Could not move bot: {e}"
                        )

                        return False

                else:

                    print(
                        f"✅ Already connected to "
                        f"{voice_channel.name}"
                    )

            else:

                print(
                    "⚠️ Existing voice client is disconnected"
                )

                try:

                    await voice_client.disconnect(
                        force=True
                    )

                except:
                    pass

                voice_client = None

        # =================================================
        # CONNECT
        # =================================================

        if voice_client is None:

            print(
                f"🔌 Connecting to "
                f"{voice_channel.name}..."
            )

            try:

                voice_client = await voice_channel.connect(
                    timeout=30.0,
                    reconnect=True
                )

                print(
                    f"✅ Successfully connected to "
                    f"{voice_channel.name}"
                )

            except asyncio.TimeoutError:

                print(
                    f"❌ Voice connection timed out "
                    f"for {guild.name}"
                )

                return False

            except discord.ClientException as e:

                print(
                    f"❌ Discord voice client error: "
                    f"{e}"
                )

                return False

            except discord.Forbidden as e:

                print(
                    f"❌ Discord permission error: "
                    f"{e}"
                )

                return False

            except Exception as e:

                print(
                    f"❌ Voice connection failed: "
                    f"{type(e).__name__}: {e}"
                )

                return False

        # =================================================
        # VERIFY
        # =================================================

        if not voice_client.is_connected():

            print(
                "❌ Voice client is disconnected "
                "after connection attempt."
            )

            return False

        print(
            f"✅ Music bot connected to "
            f"{voice_client.channel.name}"
        )

        # =================================================
        # START MUSIC
        # =================================================

        if (
            not voice_client.is_playing()
            and not voice_client.is_paused()
        ):

            print(
                f"🎵 Starting music in "
                f"{guild.name}..."
            )

            await self.start_stream(
                guild,
                voice_client
            )

        return True

    # =====================================================
    # EXTRACT STREAM
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
                    f"❌ yt-dlp extraction error: "
                    f"{type(e).__name__}: {e}"
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

        player["starting"] = True

        try:

            # ---------------------------------------------
            # CHECK SOURCE
            # ---------------------------------------------

            if not MALAYALAM_SOURCE:

                print(
                    "❌ MALAYALAM_SOURCE is empty."
                )

                return

            print(
                f"🔎 Getting fresh music stream "
                f"for {guild.name}..."
            )

            # ---------------------------------------------
            # EXTRACT
            # ---------------------------------------------

            data = await self.extract_stream(
                MALAYALAM_SOURCE
            )

            if not data:

                print(
                    f"❌ No music stream found "
                    f"for {guild.name}"
                )

                player["title"] = (
                    "Unable to find music stream"
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
                    f"❌ Stream URL unavailable "
                    f"for {guild.name}"
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

            # ---------------------------------------------
            # FFMPEG
            # ---------------------------------------------

            print(
                f"🎵 Preparing FFmpeg for: "
                f"{title}"
            )

            ffmpeg_audio = discord.FFmpegPCMAudio(

                stream_url,

                before_options=(
                    FFMPEG_BEFORE_OPTIONS
                ),

                options=(
                    FFMPEG_OPTIONS
                )
            )

            audio_source = discord.PCMVolumeTransformer(

                ffmpeg_audio,

                volume=player.get(
                    "volume",
                    DEFAULT_VOLUME
                )
            )

            # ---------------------------------------------
            # CALLBACK
            # ---------------------------------------------

            def playback_finished(
                error
            ):

                if error:

                    print(
                        f"⚠️ Playback finished with error "
                        f"in {guild.name}: {error}"
                    )

                else:

                    print(
                        f"🎵 Playback ended in "
                        f"{guild.name}"
                    )

                future = asyncio.run_coroutine_threadsafe(

                    self.stream_finished(
                        guild.id
                    ),

                    self.bot.loop
                )

                try:

                    future.result(
                        timeout=1
                    )

                except:
                    pass

            # ---------------------------------------------
            # PLAY
            # ---------------------------------------------

            voice_client.play(
                audio_source,
                after=playback_finished
            )

            print(
                f"🟢 NOW PLAYING in "
                f"{guild.name}: {title}"
            )

            await self.update_player_panel(
                guild
            )

        except Exception as e:

            print(
                f"❌ Stream error in "
                f"{guild.name}: "
                f"{type(e).__name__}: {e}"
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
    # PLAYBACK FINISHED
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

        # Don't restart while paused
        if player.get(
            "paused",
            False
        ):

            return

        voice_client = guild.voice_client

        if not voice_client:

            return

        if voice_client.is_playing():

            return

        print(
            f"🔄 Refreshing stream for "
            f"{guild.name}"
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

                voice_channel = guild.get_channel(
                    player["voice_channel_id"]
                )

                if not voice_channel:

                    continue

                voice_client = guild.voice_client

                # -----------------------------------------
                # BOT NOT CONNECTED
                # -----------------------------------------

                if not voice_client:

                    print(
                        f"🔄 Watchdog reconnecting "
                        f"music bot to {guild.name}"
                    )

                    await self.connect_and_play(
                        guild
                    )

                    continue

                # -----------------------------------------
                # DISCONNECTED
                # -----------------------------------------

                if not voice_client.is_connected():

                    print(
                        f"⚠️ Music bot disconnected "
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

                    await self.connect_and_play(
                        guild
                    )

                    continue

                # -----------------------------------------
                # NOTHING PLAYING
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
                        f"🔄 Music stopped in "
                        f"{guild.name}, restarting..."
                    )

                    await self.start_stream(
                        guild,
                        voice_client
                    )

            except Exception as e:

                print(
                    f"⚠️ Music watchdog error: "
                    f"{type(e).__name__}: {e}"
                )

    # =====================================================
    # WATCHDOG READY
    # =====================================================

    @music_watchdog.before_loop
    async def before_music_watchdog(
        self
    ):

        await self.bot.wait_until_ready()

        print(
            "🎵 Music watchdog started."
        )

        await self.restore_players()

    # =====================================================
    # RESTORE MUSIC AFTER BOT RESTART
    # =====================================================

    async def restore_players(
        self
    ):

        await asyncio.sleep(
            5
        )

        if not self.config:

            print(
                "ℹ️ No saved music systems found."
            )

            return

        print(
            "🔄 Restoring music systems..."
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
                        f"⚠️ Music voice channel missing "
                        f"in {guild.name}"
                    )

                    continue

                if not text_channel:

                    print(
                        f"⚠️ Music text channel missing "
                        f"in {guild.name}"
                    )

                    continue

                # -----------------------------------------
                # CREATE PLAYER STATE
                # -----------------------------------------

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
                # FIND EXISTING PLAYER MESSAGE
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
                        f"⚠️ Could not find music panel: "
                        f"{e}"
                    )

                # -----------------------------------------
                # CONNECT
                # -----------------------------------------

                print(
                    f"🔄 Restoring music for "
                    f"{guild.name}"
                )

                await self.connect_and_play(
                    guild
                )

            except Exception as e:

                print(
                    f"❌ Could not restore music "
                    f"for {guild_id}: "
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

        paused = player.get(
            "paused",
            False
        )

        voice_client = guild.voice_client

        if paused:

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

                f"📻 **Source:** Malayalam Music\n"
                f"🔊 **Volume:** `{volume}%`\n"
                f"📡 **Status:** {status}\n\n"

                "🎧 Enjoy Malayalam music 24/7\n\n"

                "━━━━━━━━━━━━━━━━━━━━"
            ),

            color=discord.Color.blurple()
        )

        # -------------------------------------------------
        # Source link
        # -------------------------------------------------

        webpage_url = player.get(
            "webpage_url"
        )

        if webpage_url:

            embed.add_field(
                name="🔗 Source",
                value=f"[Open Source]({webpage_url})",
                inline=False
            )

        # -------------------------------------------------
        # Server logo
        # -------------------------------------------------

        if guild.icon:

            embed.set_thumbnail(
                url=guild.icon.url
            )

        embed.set_footer(

            text=(
                f"{guild.name} • "
                f"24/7 Malayalam Music"
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
                    self,
                    guild.id
                )
            )

            return message

        except Exception as e:

            print(
                f"❌ Could not send music panel: "
                f"{e}"
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
        # EDIT EXISTING MESSAGE
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
                        self,
                        guild.id
                    )
                )

                return

            except (
                discord.NotFound,
                discord.HTTPException
            ):

                pass

        # -------------------------------------------------
        # SEND NEW PANEL
        # -------------------------------------------------

        try:

            message = await text_channel.send(

                embed=self.create_player_embed(
                    guild
                ),

                view=MusicControlView(
                    self,
                    guild.id
                )
            )

            player["message_id"] = message.id

        except Exception as e:

            print(
                f"❌ Could not recreate panel: {e}"
            )

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

        current_volume = player.get(
            "volume",
            DEFAULT_VOLUME
        )

        new_volume = max(
            0.0,
            min(
                1.0,
                current_volume + amount
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

        percentage = int(
            new_volume * 100
        )

        await interaction.response.send_message(
            f"🔊 Volume set to **{percentage}%**.",
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

        voice_client = guild.voice_client

        if not voice_client:

            await interaction.response.send_message(
                "❌ Music bot is not connected.",
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

            await self.update_player_panel(
                guild
            )

            return

        if voice_client.is_paused():

            await interaction.response.send_message(
                "⏸️ Music is already paused.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "⚠️ Music is not currently playing.",
            ephemeral=True
        )

    # =====================================================
    # RESUME
    # =====================================================

    async def resume_music(
        self,
        interaction
    ):

        guild = interaction.guild

        voice_client = guild.voice_client

        if not voice_client:

            await interaction.response.send_message(
                "❌ Music bot is not connected.",
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

            await self.update_player_panel(
                guild
            )

            return

        if voice_client.is_playing():

            await interaction.response.send_message(
                "▶️ Music is already playing.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "⚠️ Nothing is currently playing.",
            ephemeral=True
        )

    # =====================================================
    # REFRESH STREAM
    # =====================================================

    async def restart_music(
        self,
        interaction
    ):

        guild = interaction.guild

        voice_client = guild.voice_client

        if not voice_client:

            await interaction.response.send_message(
                "❌ Music bot is not connected.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🔄 Refreshing the music stream...",
            ephemeral=True
        )

        try:

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


# =========================================================
# MUSIC CONTROL VIEW
# =========================================================

class MusicControlView(
    discord.ui.View
):

    def __init__(
        self,
        cog,
        guild_id
    ):

        super().__init__(
            timeout=None
        )

        self.cog = cog

        self.guild_id = guild_id

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

        await self.cog.change_volume(
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

        await self.cog.change_volume(
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

        await self.cog.pause_music(
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

        await self.cog.resume_music(
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

        await self.cog.restart_music(
            interaction
        )


# =========================================================
# COG SETUP
# =========================================================

async def setup(
    bot
):

    # -----------------------------------------------------
    # Persistent button view
    # -----------------------------------------------------
    #
    # This allows buttons to continue working after
    # the bot restarts.
    #
    bot.add_view(
        MusicControlView(
            None,
            0
        )
    )

    await bot.add_cog(
        MusicSystem(
            bot
        )
    )

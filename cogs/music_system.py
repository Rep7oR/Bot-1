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

# ---------------------------------------------------------
# MUSIC SOURCE
#
# Put a YouTube/live-stream/playlist URL here.
#
# IMPORTANT:
# Use a source you are authorized to stream.
# ---------------------------------------------------------

MALAYALAM_SOURCE = os.getenv(
    "MALAYALAM_SOURCE",
    ""
)

# Default volume
DEFAULT_VOLUME = 0.70

# How often the watchdog checks the player
WATCHDOG_SECONDS = 15


# =========================================================
# YT-DLP OPTIONS
# =========================================================

YTDL_OPTIONS = {

    "format": "bestaudio/best",

    "quiet": True,

    "no_warnings": True,

    "noplaylist": False,

    "extract_flat": False,

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
# LOAD / SAVE CONFIG
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

    except (
        json.JSONDecodeError,
        FileNotFoundError
    ):

        return {}


def save_config(config):

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

        # -------------------------------------------------
        # Runtime state
        # -------------------------------------------------

        self.players = {}

        # {
        #   guild_id: {
        #       "voice_channel_id": ...,
        #       "text_channel_id": ...,
        #       "volume": 0.7,
        #       "paused": False,
        #       "title": "...",
        #       "url": "..."
        #   }
        # }

        # Start watchdog
        self.music_watchdog.start()

    # =====================================================
    # CLEANUP
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

        if not MALAYALAM_SOURCE:

            await interaction.response.send_message(
                "❌ `MALAYALAM_SOURCE` is not configured.\n\n"
                "Add your authorized music/live-stream source "
                "to the environment before using `/setmusic`.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        # -------------------------------------------------
        # If already configured
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
                "⚠️ Music system is already configured.\n\n"
                f"🎧 Voice: "
                f"{old_voice.mention if old_voice else 'Missing'}\n"
                f"💬 Controls: "
                f"{old_text.mention if old_text else 'Missing'}",
                ephemeral=True
            )

            return

        # -------------------------------------------------
        # CREATE VOICE CHANNEL
        # -------------------------------------------------

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

                reason="24/7 Malayalam music system"
            )

        except discord.Forbidden:

            await interaction.followup.send(
                "❌ I cannot create the music voice channel.\n"
                "Give the bot **Manage Channels** permission.",
                ephemeral=True
            )

            return

        # -------------------------------------------------
        # CREATE TEXT CHANNEL
        # -------------------------------------------------

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

                topic=(
                    "24/7 Malayalam Music Player"
                ),

                reason="24/7 Malayalam music controls"
            )

        except discord.Forbidden:

            try:

                await voice_channel.delete(
                    reason="Music control channel creation failed"
                )

            except:
                pass

            await interaction.followup.send(
                "❌ I could not create the music control channel.",
                ephemeral=True
            )

            return

        # -------------------------------------------------
        # SAVE CONFIG
        # -------------------------------------------------

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

        # -------------------------------------------------
        # CREATE PLAYER STATE
        # -------------------------------------------------

        self.players[
            guild.id
        ] = {

            "voice_channel_id": voice_channel.id,

            "text_channel_id": text_channel.id,

            "volume": DEFAULT_VOLUME,

            "paused": False,

            "title": "Starting Malayalam Music...",

            "source_url": MALAYALAM_SOURCE,

            "message_id": None,

            "starting": False
        }

        # -------------------------------------------------
        # SEND PLAYER PANEL
        # -------------------------------------------------

        message = await self.send_player_panel(
            guild
        )

        if message:

            self.players[
                guild.id
            ]["message_id"] = message.id

        # -------------------------------------------------
        # CONNECT TO VOICE
        # -------------------------------------------------

        try:

            await self.connect_and_play(
                guild
            )

        except Exception as e:

            print(
                f"❌ Music startup error: {e}"
            )

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        await interaction.followup.send(

            f"✅ **24/7 Malayalam Music System Created**\n\n"

            f"🎧 **Voice:** {voice_channel.mention}\n"

            f"💬 **Controls:** {text_channel.mention}\n\n"

            "The bot will remain in the voice channel "
            "and automatically recover the stream if it "
            "disconnects or the stream expires.",

            ephemeral=True
        )

    # =====================================================
    # CONNECT + PLAY
    # =====================================================

    async def connect_and_play(
        self,
        guild: discord.Guild
    ):

        player = self.players.get(
            guild.id
        )

        if not player:
            return

        voice_channel = guild.get_channel(
            player["voice_channel_id"]
        )

        if not voice_channel:
            return

        # -------------------------------------------------
        # CONNECT
        # -------------------------------------------------

        voice_client = guild.voice_client

        if voice_client:

            if not voice_client.is_connected():

                try:

                    await voice_client.connect(
                        reconnect=True
                    )

                except Exception:

                    voice_client = None

            elif voice_client.channel.id != voice_channel.id:

                try:

                    await voice_client.move_to(
                        voice_channel
                    )

                except Exception:
                    pass

        if not voice_client:

            try:

                voice_client = await voice_channel.connect(
                    reconnect=True
                )

            except Exception as e:

                print(
                    f"❌ Could not connect to music VC "
                    f"{guild.name}: {e}"
                )

                return

        # -------------------------------------------------
        # DON'T RESTART IF ALREADY PLAYING
        # -------------------------------------------------

        if voice_client.is_playing():

            return

        if voice_client.is_paused():

            return

        # -------------------------------------------------
        # START STREAM
        # -------------------------------------------------

        await self.start_stream(
            guild,
            voice_client
        )

    # =====================================================
    # GET STREAM
    # =====================================================

    async def extract_stream(
        self,
        source
    ):

        loop = asyncio.get_running_loop()

        def extract():

            with yt_dlp.YoutubeDL(
                YTDL_OPTIONS
            ) as ydl:

                info = ydl.extract_info(
                    source,
                    download=False
                )

                if not info:
                    return None

                # -------------------------------------------------
                # Playlist / search results
                # -------------------------------------------------

                if "entries" in info:

                    entries = [
                        entry
                        for entry in info["entries"]
                        if entry
                    ]

                    if not entries:
                        return None

                    # Pick the first available item.
                    info = entries[0]

                return {

                    "title": info.get(
                        "title",
                        "Malayalam Music"
                    ),

                    "stream_url": info.get(
                        "url"
                    ),

                    "webpage_url": info.get(
                        "webpage_url",
                        source
                    )
                }

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

            # -------------------------------------------------
            # Extract fresh URL
            # -------------------------------------------------

            data = await self.extract_stream(
                MALAYALAM_SOURCE
            )

            if not data:

                print(
                    f"❌ No stream found for {guild.name}"
                )

                return

            stream_url = data.get(
                "stream_url"
            )

            if not stream_url:

                print(
                    f"❌ Stream URL unavailable for "
                    f"{guild.name}"
                )

                return

            title = data.get(
                "title",
                "Malayalam Music"
            )

            player["title"] = title

            player["webpage_url"] = data.get(
                "webpage_url",
                MALAYALAM_SOURCE
            )

            player["paused"] = False

            # -------------------------------------------------
            # Create FFmpeg source
            # -------------------------------------------------

            ffmpeg_source = discord.FFmpegPCMAudio(

                stream_url,

                before_options=(
                    FFMPEG_BEFORE_OPTIONS
                ),

                options=(
                    FFMPEG_OPTIONS
                )
            )

            volume_source = discord.PCMVolumeTransformer(
                ffmpeg_source,
                volume=player.get(
                    "volume",
                    DEFAULT_VOLUME
                )
            )

            # -------------------------------------------------
            # Playback callback
            # -------------------------------------------------

            def playback_finished(error):

                if error:

                    print(
                        f"⚠️ Playback error "
                        f"in {guild.name}: {error}"
                    )

                asyncio.run_coroutine_threadsafe(

                    self.stream_finished(
                        guild.id
                    ),

                    self.bot.loop
                )

            # -------------------------------------------------
            # PLAY
            # -------------------------------------------------

            voice_client.play(
                volume_source,
                after=playback_finished
            )

            print(
                f"🎵 Playing in {guild.name}: "
                f"{title}"
            )

            await self.update_player_panel(
                guild
            )

        except Exception as e:

            print(
                f"❌ Stream error in {guild.name}: {e}"
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

        await asyncio.sleep(2)

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

        # If paused, don't restart.
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

        # Refresh the stream
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
    async def music_watchdog(self):

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

                # -------------------------------------------------
                # Reconnect if disconnected
                # -------------------------------------------------

                if not voice_client:

                    print(
                        f"🔄 Reconnecting music bot "
                        f"to {guild.name}"
                    )

                    try:

                        voice_client = await voice_channel.connect(
                            reconnect=True
                        )

                    except Exception as e:

                        print(
                            f"❌ Reconnect failed: {e}"
                        )

                        continue

                elif not voice_client.is_connected():

                    try:

                        await voice_client.disconnect(
                            force=True
                        )

                    except:
                        pass

                    try:

                        voice_client = await voice_channel.connect(
                            reconnect=True
                        )

                    except:
                        continue

                # -------------------------------------------------
                # Start again if player stopped
                # -------------------------------------------------

                if (
                    not voice_client.is_playing()
                    and not voice_client.is_paused()
                    and not player.get(
                        "starting",
                        False
                    )
                ):

                    await self.start_stream(
                        guild,
                        voice_client
                    )

            except Exception as e:

                print(
                    f"⚠️ Music watchdog error: {e}"
                )

    # =====================================================
    # WATCHDOG READY
    # =====================================================

    @music_watchdog.before_loop
    async def before_music_watchdog(
        self
    ):

        await self.bot.wait_until_ready()

        # Restore configured players after bot restart
        await self.restore_players()

    # =====================================================
    # RESTORE AFTER RESTART
    # =====================================================

    async def restore_players(self):

        await asyncio.sleep(5)

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
                    continue

                if not text_channel:
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

                    "source_url":
                        MALAYALAM_SOURCE,

                    "message_id":
                        None,

                    "starting":
                        False
                }

                # Find existing panel
                try:

                    async for message in text_channel.history(
                        limit=20
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

                except Exception:
                    pass

                # Connect
                await self.connect_and_play(
                    guild
                )

            except Exception as e:

                print(
                    f"⚠️ Could not restore music "
                    f"for {guild_id}: {e}"
                )

    # =====================================================
    # PLAYER PANEL
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

        embed = self.create_player_embed(
            guild
        )

        try:

            message = await text_channel.send(

                embed=embed,

                view=MusicControlView(
                    self,
                    guild.id
                )
            )

            return message

        except discord.HTTPException as e:

            print(
                f"❌ Could not send music panel: {e}"
            )

            return None

    # =====================================================
    # CREATE EMBED
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

        if paused:

            status = "⏸️ Paused"

        else:

            voice_client = guild.voice_client

            if (
                voice_client
                and voice_client.is_playing()
            ):

                status = "🟢 Playing"

            else:

                status = "🟡 Connecting..."

        embed = discord.Embed(
            title="🎵 MALAYALAM MUSIC",
            description=(
                "━━━━━━━━━━━━━━━━━━━━\n\n"

                f"🎶 **Now Playing**\n"
                f"**{title}**\n\n"

                f"📻 **Source:** Malayalam Music\n"
                f"🔊 **Volume:** `{volume}%`\n"
                f"📡 **Status:** {status}\n\n"

                "Enjoy Malayalam music 24/7 🎧\n\n"

                "━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.blurple()
        )

        if guild.icon:

            embed.set_thumbnail(
                url=guild.icon.url
            )

        embed.set_footer(
            text=f"{guild.name} • 24/7 Music",
            icon_url=(
                guild.icon.url
                if guild.icon
                else None
            )
        )

        return embed

    # =====================================================
    # UPDATE PANEL
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
        # Edit existing panel
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
        # Create a new panel
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

        except discord.HTTPException:

            pass

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
            f"🔊 Volume: **{int(new_volume * 100)}%**",
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

        else:

            await interaction.response.send_message(
                "⚠️ Music is not currently playing.",
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

        else:

            await interaction.response.send_message(
                "⚠️ Music is not paused.",
                ephemeral=True
            )

        await self.update_player_panel(
            guild
        )

    # =====================================================
    # RESTART CURRENT STREAM
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

        await asyncio.sleep(1)

        await self.start_stream(
            guild,
            voice_client
        )

    # =====================================================
    # ERROR
    # =====================================================

    @setmusic.error
    async def setmusic_error(
        self,
        interaction,
        error
    ):

        if isinstance(
            error,
            app_commands.errors.MissingPermissions
        ):

            await interaction.response.send_message(
                "❌ You need **Administrator** permission.",
                ephemeral=True
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
    # RESTART
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

async def setup(bot):

    await bot.add_cog(
        MusicSystem(bot)
    )

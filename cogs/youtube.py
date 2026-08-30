
import discord
from discord.ext import commands, tasks
from discord import app_commands

import aiohttp
import asyncio
import json
import os
import time
from datetime import datetime, timezone


# ============================================================
# FILES
# ============================================================

CONFIG_FILE = "youtube_config.json"


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")


# ============================================================
# CONFIG
# ============================================================

UPDATE_INTERVAL_MINUTES = 5

COUNTER_SUBSCRIBERS = "👥 Subscribers: "
COUNTER_LIKES = "👍 Likes: "
COUNTER_VIDEOS = "🎬 Videos: "
COUNTER_MEMBERS = "👤 Members: "
COUNTER_MODERATORS = "🛡️ Online Mods: "
COUNTER_LIVE = "🟢 LIVE"
COUNTER_OFFLINE = "🔴 OFFLINE"

MODERATOR_ROLE_NAMES = [
    "MODERATOR",
    "Moderators",
    "Mod",
]


# ============================================================
# JSON
# ============================================================

def load_config():

    if not os.path.exists(CONFIG_FILE):
        return {}

    try:

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        # The YouTube configuration must be a dictionary.
        # Recover gracefully if it was accidentally saved
        # as a JSON string containing another JSON object.
        if isinstance(data, str):

            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = {}

        if not isinstance(data, dict):

            print(
                "⚠️ youtube_config.json has an invalid "
                "top-level format. Starting with an empty config."
            )

            return {}

        # Every guild entry must also be a dictionary.
        # Invalid guild entries are reset so commands such as
        # /youtubesetup cannot fail with string-index errors.
        cleaned = {}

        for guild_id, guild_config in data.items():

            if isinstance(guild_config, dict):
                cleaned[str(guild_id)] = guild_config

            elif isinstance(guild_config, str):

                try:
                    parsed = json.loads(guild_config)

                    if isinstance(parsed, dict):
                        cleaned[str(guild_id)] = parsed
                    else:
                        cleaned[str(guild_id)] = {}

                except json.JSONDecodeError:
                    cleaned[str(guild_id)] = {}

            else:
                cleaned[str(guild_id)] = {}

        return cleaned

    except Exception as e:

        print(
            f"❌ YouTube config load error: {e}"
        )

        return {}


def save_config(data):

    try:

        with open(
            CONFIG_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4
            )

    except Exception as e:

        print(
            f"❌ YouTube config save error: {e}"
        )


# ============================================================
# FORMAT NUMBERS
# ============================================================

def format_number(number):

    try:
        number = int(number)
    except:
        return "0"

    if number >= 1_000_000_000:

        return f"{number / 1_000_000_000:.1f}B"

    if number >= 1_000_000:

        return f"{number / 1_000_000:.1f}M"

    if number >= 1_000:

        return f"{number / 1_000:.1f}K"

    return f"{number:,}"


# ============================================================
# YOUTUBE SYSTEM
# ============================================================

class YouTubeSystem(commands.Cog):

    def __init__(
        self,
        bot: commands.Bot
    ):

        self.bot = bot

        self.config = load_config()

        self.session = None

        self.last_video_id = None

        self.last_live_id = None

        self.last_live_state = False

        # Live chat state
        self.live_chat_id = None
        self.live_chat_video_id = None
        self.live_chat_page_token = None
        self.live_chat_next_poll = 0.0

        self.youtube_update_loop.start()
        self.youtube_live_chat_loop.start()

        print(
            "✅ YouTube System loaded."
        )

    # ========================================================
    # COG UNLOAD
    # ========================================================

    def cog_unload(self):

        self.youtube_update_loop.cancel()
        self.youtube_live_chat_loop.cancel()

        if self.session:

            try:

                asyncio.create_task(
                    self.session.close()
                )

            except Exception:

                pass

    # ========================================================
    # HTTP SESSION
    # ========================================================

    async def get_session(self):

        if (
            self.session is None
            or self.session.closed
        ):

            self.session = aiohttp.ClientSession()

        return self.session

    # ========================================================
    # API CHECK
    # ========================================================

    def api_ready(self):

        return bool(
            YOUTUBE_API_KEY
            and YOUTUBE_CHANNEL_ID
        )

    # ========================================================
    # GUILD CONFIG
    # ========================================================

    def get_guild_config(
        self,
        guild_id
    ):

        guild_id = str(guild_id)

        # Make sure the top-level config is always a dictionary.
        if not isinstance(self.config, dict):
            self.config = {}

        # Create a guild entry when it does not exist.
        if guild_id not in self.config:
            self.config[guild_id] = {}

        # Repair an existing malformed guild entry.
        if not isinstance(self.config[guild_id], dict):

            old_value = self.config[guild_id]

            if isinstance(old_value, str):

                try:
                    parsed = json.loads(old_value)

                    if isinstance(parsed, dict):
                        self.config[guild_id] = parsed
                    else:
                        self.config[guild_id] = {}

                except json.JSONDecodeError:
                    self.config[guild_id] = {}

            else:
                self.config[guild_id] = {}

        return self.config[guild_id]

    # ========================================================
    # GET CHANNEL
    # ========================================================

    def get_discord_channel(
        self,
        guild,
        key
    ):

        guild_config = self.config.get(
            str(guild.id),
            {}
        )

        channel_id = guild_config.get(
            key
        )

        if not channel_id:

            return None

        return guild.get_channel(
            int(channel_id)
        )

    # ========================================================
    # YOUTUBE API REQUEST
    # ========================================================

    async def youtube_request(
        self,
        endpoint,
        params
    ):

        if not self.api_ready():

            return None

        session = await self.get_session()

        params["key"] = YOUTUBE_API_KEY

        url = (
            "https://www.googleapis.com/"
            f"youtube/v3/{endpoint}"
        )

        try:

            async with session.get(
                url,
                params=params,
                timeout=20
            ) as response:

                if response.status != 200:

                    text = await response.text()

                    print(
                        f"❌ YouTube API error "
                        f"{response.status}: {text}"
                    )

                    return None

                return await response.json()

        except asyncio.TimeoutError:

            print(
                "❌ YouTube API request timed out."
            )

            return None

        except Exception as e:

            print(
                f"❌ YouTube API request error: {e}"
            )

            return None

    # ========================================================
    # GET CHANNEL INFORMATION
    # ========================================================

    async def get_channel_data(self):

        data = await self.youtube_request(

            "channels",

            {
                "part": "snippet,statistics,contentDetails",

                "id": YOUTUBE_CHANNEL_ID
            }
        )

        if not data:

            return None

        items = data.get(
            "items",
            []
        )

        if not items:

            return None

        return items[0]

    # ========================================================
    # GET RECENT VIDEOS
    # ========================================================

    async def get_recent_videos(
        self,
        max_results=50
    ):

        channel_data = await self.get_channel_data()

        if not channel_data:

            return []

        uploads_playlist = (
            channel_data
            .get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads")
        )

        if not uploads_playlist:

            return []

        playlist_data = await self.youtube_request(

            "playlistItems",

            {
                "part": "snippet,contentDetails",

                "playlistId":
                    uploads_playlist,

                "maxResults":
                    max_results
            }
        )

        if not playlist_data:

            return []

        video_ids = []

        for item in playlist_data.get(
            "items",
            []
        ):

            video_id = (
                item
                .get("contentDetails", {})
                .get("videoId")
            )

            if video_id:

                video_ids.append(
                    video_id
                )

        if not video_ids:

            return []

        video_data = await self.youtube_request(

            "videos",

            {
                "part":
                    "snippet,statistics,liveStreamingDetails",

                "id":
                    ",".join(video_ids)
            }
        )

        if not video_data:

            return []

        return video_data.get(
            "items",
            []
        )

    # ========================================================
    # CALCULATE RECENT LIKES
    # ========================================================

    async def calculate_recent_likes(self):

        videos = await self.get_recent_videos(
            50
        )

        total_likes = 0

        for video in videos:

            statistics = video.get(
                "statistics",
                {}
            )

            likes = statistics.get(
                "likeCount"
            )

            if likes:

                try:

                    total_likes += int(
                        likes
                    )

                except:

                    pass

        return total_likes

    # ========================================================
    # GET LIVE VIDEO
    # ========================================================

    async def get_live_video(self):

        data = await self.youtube_request(

            "search",

            {
                "part":
                    "snippet",

                "channelId":
                    YOUTUBE_CHANNEL_ID,

                "eventType":
                    "live",

                "type":
                    "video",

                "maxResults":
                    1
            }
        )

        if not data:

            return None

        items = data.get(
            "items",
            []
        )

        if not items:

            return None

        video_id = items[0].get("id", {}).get("videoId")

        if not video_id:

            return None

        # The search endpoint does not provide
        # activeLiveChatId, so fetch the full video
        # resource with liveStreamingDetails.
        video_data = await self.youtube_request(

            "videos",

            {
                "part":
                    "snippet,liveStreamingDetails",

                "id":
                    video_id
            }
        )

        if not video_data:

            return None

        video_items = video_data.get(
            "items",
            []
        )

        if not video_items:

            return None

        return video_items[0]

    # ========================================================
    # GET LIVE CHAT MESSAGES
    # ========================================================

    async def get_live_chat_messages(
        self,
        live_chat_id,
        page_token=None
    ):

        params = {
            "part": "snippet",
            "liveChatId": live_chat_id,
            "maxResults": 200
        }

        if page_token:
            params["pageToken"] = page_token

        return await self.youtube_request(
            "liveChatMessages",
            params
        )

    # ========================================================
    # SEND LIVE CHAT TO DISCORD
    # ========================================================

    async def send_live_chat_messages(
        self,
        messages
    ):

        if not messages:

            return

        for guild in self.bot.guilds:

            guild_config = self.config.get(
                str(guild.id),
                {}
            )

            if not guild_config.get(
                "enabled",
                False
            ):

                continue

            channel = self.get_discord_channel(
                guild,
                "live_chat_channel_id"
            )

            if not isinstance(
                channel,
                discord.TextChannel
            ):

                continue

            for message in messages:

                snippet = message.get(
                    "snippet",
                    {}
                )

                author_details = snippet.get(
                    "authorDetails",
                    {}
                )

                # Depending on the message type,
                # YouTube may provide textMessageDetails
                # or another displayable message field.
                text_details = snippet.get(
                    "textMessageDetails",
                    {}
                )

                content = text_details.get(
                    "messageText"
                )

                if not content:
                    content = snippet.get(
                        "displayMessage"
                    )

                if not content:
                    continue

                author = author_details.get(
                    "displayName",
                    "YouTube User"
                )

                content = str(content).strip()

                if not content:
                    continue

                # Keep the message below Discord's limit.
                if len(content) > 1850:
                    content = content[:1850] + "..."

                discord_message = (
                    f"💬 **{author}:** {content}"
                )

                try:

                    await channel.send(
                        discord_message,
                        allowed_mentions=discord.AllowedMentions.none()
                    )

                except discord.Forbidden:

                    print(
                        f"❌ No permission to send "
                        f"YouTube live chat in "
                        f"{guild.name}"
                    )

                except discord.HTTPException as e:

                    print(
                        f"❌ Discord live chat error "
                        f"in {guild.name}: {e}"
                    )

    # ========================================================
    # LIVE CHAT BACKGROUND LOOP
    # ========================================================

    @tasks.loop(seconds=5)
    async def youtube_live_chat_loop(
        self
    ):

        if not self.api_ready():

            return

        now = time.monotonic()

        if now < self.live_chat_next_poll:

            return

        live_video = await self.get_live_video()

        if not live_video:

            # Reset chat state after a stream ends.
            self.live_chat_id = None
            self.live_chat_video_id = None
            self.live_chat_page_token = None
            self.live_chat_next_poll = now + 15

            return

        video_id = live_video.get(
            "id"
        )

        live_details = live_video.get(
            "liveStreamingDetails",
            {}
        )

        live_chat_id = live_details.get(
            "activeLiveChatId"
        )

        if not live_chat_id:

            # The stream can be live while chat is disabled.
            self.live_chat_id = None
            self.live_chat_video_id = video_id
            self.live_chat_page_token = None
            self.live_chat_next_poll = now + 30

            return

        # New live stream: reset the page token.
        if (
            live_chat_id
            != self.live_chat_id
            or
            video_id
            != self.live_chat_video_id
        ):

            self.live_chat_id = live_chat_id
            self.live_chat_video_id = video_id
            self.live_chat_page_token = None

        try:

            data = await self.get_live_chat_messages(
                live_chat_id,
                self.live_chat_page_token
            )

            if not data:

                self.live_chat_next_poll = (
                    time.monotonic() + 10
                )

                return

            messages = data.get(
                "items",
                []
            )

            self.live_chat_page_token = data.get(
                "nextPageToken"
            )

            polling_interval_ms = data.get(
                "pollingIntervalMillis",
                10000
            )

            try:
                polling_interval_ms = int(
                    polling_interval_ms
                )
            except (TypeError, ValueError):
                polling_interval_ms = 10000

            # Always respect YouTube's requested polling interval.
            polling_seconds = max(
                polling_interval_ms / 1000,
                5
            )

            self.live_chat_next_poll = (
                time.monotonic() + polling_seconds
            )

            await self.send_live_chat_messages(
                messages
            )

        except Exception as e:

            print(
                f"❌ YouTube live chat error: {e}"
            )

            self.live_chat_next_poll = (
                time.monotonic() + 15
            )

    @youtube_live_chat_loop.before_loop
    async def before_youtube_live_chat_loop(
        self
    ):

        await self.bot.wait_until_ready()

        print(
            "💬 YouTube live chat monitoring started."
        )

    # ========================================================
    # GET LATEST VIDEO
    # ========================================================

    async def get_latest_video(self):

        channel_data = await self.get_channel_data()

        if not channel_data:

            return None

        uploads_playlist = (
            channel_data
            .get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads")
        )

        if not uploads_playlist:

            return None

        playlist_data = await self.youtube_request(

            "playlistItems",

            {
                "part":
                    "snippet,contentDetails",

                "playlistId":
                    uploads_playlist,

                "maxResults":
                    1
            }
        )

        if not playlist_data:

            return None

        items = playlist_data.get(
            "items",
            []
        )

        if not items:

            return None

        item = items[0]

        video_id = (
            item
            .get("contentDetails", {})
            .get("videoId")
        )

        if not video_id:

            return None

        video_data = await self.youtube_request(

            "videos",

            {
                "part":
                    "snippet,statistics,liveStreamingDetails",

                "id":
                    video_id
            }
        )

        if not video_data:

            return None

        video_items = video_data.get(
            "items",
            []
        )

        if not video_items:

            return None

        return video_items[0]

    # ========================================================
    # COUNTER CATEGORY
    # ========================================================

    def get_counter_category(
        self,
        guild
    ):

        guild_config = self.config.get(
            str(guild.id),
            {}
        )

        category_id = guild_config.get(
            "counter_category_id"
        )

        if not category_id:

            return None

        category = guild.get_channel(
            int(category_id)
        )

        if isinstance(
            category,
            discord.CategoryChannel
        ):

            return category

        return None

    # ========================================================
    # MEMBER / MODERATOR COUNTS
    # ========================================================

    def count_online_moderators(self, guild):

        count = 0

        for member in guild.members:

            is_moderator = any(
                role.name in MODERATOR_ROLE_NAMES
                for role in member.roles
            )

            if not is_moderator:
                continue

            # Count members who are online, idle, or DND.
            # Offline also covers users appearing invisible.
            if member.status != discord.Status.offline:
                count += 1

        return count

    # ========================================================
    # CREATE / UPDATE COUNTER
    # ========================================================

    async def update_counter(
        self,
        guild,
        subscribers,
        likes,
        videos,
        members,
        online_moderators,
        live
    ):

        category = self.get_counter_category(
            guild
        )

        if category is None:

            return

        values = {

            "subscriber_counter_id":
                (
                    f"{COUNTER_SUBSCRIBERS}"
                    f"{format_number(subscribers)}"
                ),

            "likes_counter_id":
                (
                    f"{COUNTER_LIKES}"
                    f"{format_number(likes)}"
                ),

            "videos_counter_id":
                (
                    f"{COUNTER_VIDEOS}"
                    f"{format_number(videos)}"
                ),

            "member_counter_id":
                (
                    f"{COUNTER_MEMBERS}"
                    f"{format_number(members)}"
                ),

            "moderator_counter_id":
                (
                    f"{COUNTER_MODERATORS}"
                    f"{format_number(online_moderators)}"
                ),

            "live_counter_id":
                (
                    COUNTER_LIVE
                    if live
                    else COUNTER_OFFLINE
                )
        }

        guild_config = self.get_guild_config(
            guild.id
        )

        counter_keys = [
            "subscriber_counter_id",
            "likes_counter_id",
            "videos_counter_id",
            "member_counter_id",
            "moderator_counter_id",
            "live_counter_id"
        ]

        for key in counter_keys:

            channel_id = guild_config.get(
                key
            )

            counter = None

            if channel_id:

                counter = guild.get_channel(
                    int(channel_id)
                )

            # ------------------------------------------------
            # CREATE
            # ------------------------------------------------

            if counter is None:

                try:

                    counter = await guild.create_voice_channel(

                        name=values[key],

                        category=category,

                        reason=(
                            "YouTube statistics counter"
                        )
                    )

                    guild_config[key] = counter.id

                    save_config(
                        self.config
                    )

                except discord.Forbidden:

                    print(
                        f"❌ Cannot create YouTube "
                        f"counter in {guild.name}"
                    )

                    continue

                except discord.HTTPException as e:

                    print(
                        f"❌ YouTube counter error: {e}"
                    )

                    continue

            # ------------------------------------------------
            # CORRECT CATEGORY
            # ------------------------------------------------

            if counter.category_id != category.id:

                try:

                    await counter.edit(
                        category=category
                    )

                except:

                    pass

            # ------------------------------------------------
            # UPDATE NAME
            # ------------------------------------------------

            new_name = values[key]

            if counter.name != new_name:

                try:

                    await counter.edit(
                        name=new_name
                    )

                except discord.HTTPException:

                    pass

    # ========================================================
    # SEND NEW VIDEO NOTIFICATION
    # ========================================================

    async def send_upload_notification(
        self,
        guild,
        video
    ):

        channel = self.get_discord_channel(
            guild,
            "upload_channel_id"
        )

        if channel is None:

            return

        snippet = video.get(
            "snippet",
            {}
        )

        video_id = video.get(
            "id"
        )

        title = snippet.get(
            "title",
            "New video"
        )

        description = snippet.get(
            "description",
            ""
        )

        thumbnail = (
            snippet
            .get("thumbnails", {})
            .get("high", {})
            .get("url")
        )

        url = (
            f"https://www.youtube.com/watch?v={video_id}"
        )

        embed = discord.Embed(

            title="🎬 New YouTube Upload",

            description=(

                f"**{title}**\n\n"

                f"{description[:500]}"
                f"{'...' if len(description) > 500 else ''}\n\n"

                f"▶️ [Watch on YouTube]({url})"
            ),

            color=discord.Color.red(),

            timestamp=datetime.now(
                timezone.utc
            )
        )

        if thumbnail:

            embed.set_image(
                url=thumbnail
            )

        embed.set_footer(
            text="YouTube Upload"
        )

        try:

            await channel.send(
                embed=embed
            )

        except discord.HTTPException as e:

            print(
                f"❌ Upload notification error: {e}"
            )

    # ========================================================
    # SEND LIVE START NOTIFICATION
    # ========================================================

    async def send_live_notification(
        self,
        guild,
        video
    ):

        snippet = video.get(
            "snippet",
            {}
        )

        video_id = video.get(
            "id"
        )

        title = snippet.get(
            "title",
            "Live Stream"
        )

        thumbnail = (
            snippet
            .get("thumbnails", {})
            .get("high", {})
            .get("url")
        )

        url = (
            f"https://www.youtube.com/watch?v={video_id}"
        )

        embed = discord.Embed(

            title="🔴 WE ARE LIVE!",

            description=(

                f"**{title}**\n\n"

                "The stream is live now!\n\n"

                f"🔴 [Watch Live on YouTube]({url})"
            ),

            color=discord.Color.red(),

            timestamp=datetime.now(
                timezone.utc
            )
        )

        if thumbnail:

            embed.set_image(
                url=thumbnail
            )

        embed.set_footer(
            text="YouTube Live"
        )

        # ----------------------------------------------------
        # GENERAL NOTIFICATION
        # ----------------------------------------------------

        notification_channel = (
            self.get_discord_channel(
                guild,
                "notification_channel_id"
            )
        )

        if notification_channel:

            try:

                message = await notification_channel.send(

                    content="@everyone",

                    embed=embed,

                    allowed_mentions=discord.AllowedMentions(
                        everyone=True
                    )
                )

                # Save the live notification message ID so it
                # can be deleted automatically when the stream ends.
                guild_config = self.get_guild_config(
                    guild.id
                )

                guild_config[
                    "live_notification_message_id"
                ] = message.id

                save_config(
                    self.config
                )

            except discord.HTTPException as e:

                print(
                    f"❌ Live notification error: {e}"
                )

        # ----------------------------------------------------
        # LIVE CHAT CHANNEL
        # ----------------------------------------------------

        live_chat_channel = (
            self.get_discord_channel(
                guild,
                "live_chat_channel_id"
            )
        )

        if (
            live_chat_channel
            and live_chat_channel
            != notification_channel
        ):

            try:

                await live_chat_channel.send(
                    embed=embed
                )

            except discord.HTTPException as e:

                print(
                    f"❌ Live chat notification error: {e}"
                )

    # ========================================================
    # DELETE LIVE START NOTIFICATION
    # ========================================================

    async def delete_live_notification(
        self,
        guild
    ):

        guild_config = self.get_guild_config(
            guild.id
        )

        message_id = guild_config.get(
            "live_notification_message_id"
        )

        if not message_id:

            return

        notification_channel = (
            self.get_discord_channel(
                guild,
                "notification_channel_id"
            )
        )

        if notification_channel is None:

            guild_config.pop(
                "live_notification_message_id",
                None
            )

            save_config(
                self.config
            )

            return

        try:

            message = await notification_channel.fetch_message(
                int(message_id)
            )

            await message.delete()

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):

            pass

        # Clear the saved message ID after attempting deletion.
        guild_config.pop(
            "live_notification_message_id",
            None
        )

        save_config(
            self.config
        )

    # ========================================================
    # UPDATE EVERYTHING
    # ========================================================

    async def update_youtube(
        self
    ):

        if not self.api_ready():

            return

        channel_data = await self.get_channel_data()

        if not channel_data:

            return

        statistics = channel_data.get(
            "statistics",
            {}
        )

        subscribers = int(
            statistics.get(
                "subscriberCount",
                0
            )
        )

        videos = int(
            statistics.get(
                "videoCount",
                0
            )
        )

        # ----------------------------------------------------
        # LIKES
        # ----------------------------------------------------

        likes = await self.calculate_recent_likes()

        # ----------------------------------------------------
        # LIVE
        # ----------------------------------------------------

        live_video = await self.get_live_video()

        is_live = live_video is not None

        # ----------------------------------------------------
        # GUILDS
        # ----------------------------------------------------

        for guild in self.bot.guilds:

            guild_config = self.config.get(
                str(guild.id),
                {}
            )

            if not guild_config.get(
                "enabled",
                False
            ):

                continue

            # ------------------------------------------------
            # UPDATE COUNTERS
            # ------------------------------------------------

            members = guild.member_count or len(guild.members)
            online_moderators = self.count_online_moderators(guild)

            await self.update_counter(

                guild,

                subscribers,

                likes,

                videos,

                members,

                online_moderators,

                is_live
            )

            guild_config["last_live_state"] = is_live
            save_config(self.config)

            # ------------------------------------------------
            # CHECK LIVE START
            # ------------------------------------------------

            current_live_id = None

            if live_video:

                current_live_id = live_video.get(
                    "id"
                )

            if (
                is_live
                and
                (
                    not self.last_live_state
                    or
                    current_live_id
                    != self.last_live_id
                )
            ):

                # Remove any stale previous live notification
                # before creating the new one.
                await self.delete_live_notification(
                    guild
                )

                await self.send_live_notification(

                    guild,

                    live_video
                )

            # ------------------------------------------------
            # CHECK LIVE END
            # ------------------------------------------------

            if (
                not is_live
                and
                self.last_live_state
            ):

                # Remove the previous "WE ARE LIVE!" notification
                # automatically when the stream is no longer live.
                await self.delete_live_notification(
                    guild
                )

            # ------------------------------------------------
            # CHECK NEW UPLOAD
            # ------------------------------------------------

            latest_video = (
                await self.get_latest_video()
            )

            if latest_video:

                latest_id = latest_video.get(
                    "id"
                )

                if latest_id:

                    saved_video_id = (
                        guild_config.get(
                            "last_video_id"
                        )
                    )

                    if (
                        saved_video_id
                        and
                        latest_id != saved_video_id
                    ):

                        await self.send_upload_notification(

                            guild,

                            latest_video
                        )

                    # ------------------------------------------------
                    # Save current video
                    # ------------------------------------------------

                    guild_config[
                        "last_video_id"
                    ] = latest_id

                    save_config(
                        self.config
                    )

        # ----------------------------------------------------
        # GLOBAL LIVE STATE
        # ----------------------------------------------------

        self.last_live_state = is_live

        self.last_live_id = current_live_id

    # ========================================================
    # BACKGROUND LOOP
    # ========================================================

    @tasks.loop(
        minutes=UPDATE_INTERVAL_MINUTES
    )
    async def youtube_update_loop(
        self
    ):

        try:

            await self.update_youtube()

        except Exception as e:

            print(
                f"❌ YouTube background error: {e}"
            )

    # ========================================================
    # LOOP READY
    # ========================================================

    @youtube_update_loop.before_loop
    async def before_youtube_loop(
        self
    ):

        await self.bot.wait_until_ready()

        print(
            "📺 YouTube monitoring started."
        )

    # ========================================================
    # /YOUTUBESETUP
    # ========================================================

    @app_commands.command(

        name="youtubesetup",

        description=(
            "Configure the YouTube notification system."
        )
    )
    @app_commands.describe(

        notification_channel=(
            "Channel for @everyone YouTube notifications."
        ),

        live_chat_channel=(
            "Channel for YouTube live notifications."
        ),

        upload_channel=(
            "Channel for new YouTube uploads."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def youtubesetup(

        self,

        interaction: discord.Interaction,

        notification_channel: discord.TextChannel,

        live_chat_channel: discord.TextChannel,

        upload_channel: discord.TextChannel

    ):

        if interaction.guild is None:

            await interaction.response.send_message(

                "❌ This command can only be used "
                "inside a server.",

                ephemeral=True
            )

            return

        if not self.api_ready():

            await interaction.response.send_message(

                "❌ YouTube API is not configured.\n\n"

                "Add these to your `.env` file:\n\n"

                "`YOUTUBE_API_KEY=your_api_key`\n"
                "`YOUTUBE_CHANNEL_ID=your_channel_id`",

                ephemeral=True
            )

            return

        guild_config = self.get_guild_config(
            interaction.guild.id
        )

        guild_config[
            "enabled"
        ] = True

        guild_config[
            "notification_channel_id"
        ] = notification_channel.id

        guild_config[
            "live_chat_channel_id"
        ] = live_chat_channel.id

        guild_config[
            "upload_channel_id"
        ] = upload_channel.id

        save_config(
            self.config
        )

        await interaction.response.send_message(

            "✅ **YouTube notification system configured!**\n\n"

            f"📢 Notifications: "
            f"{notification_channel.mention}\n"

            f"🔴 Live notifications: "
            f"{live_chat_channel.mention}\n"

            f"🎬 New uploads: "
            f"{upload_channel.mention}\n\n"

            "The bot will now monitor the configured "
            "YouTube channel.\n\n"
            "💬 YouTube Live Chat will be relayed to "
            "the configured live channel when the stream "
            "is live.\n"
            "🔴 The live notification will be removed "
            "automatically when the stream ends.",

            ephemeral=True
        )

        # ----------------------------------------------------
        # Initial update
        # ----------------------------------------------------

        await self.update_youtube()

    # ========================================================
    # /YOUTUBECOUNTER
    # ========================================================

    @app_commands.command(

        name="youtubecounter",

        description=(
            "Set the category for YouTube statistics."
        )
    )
    @app_commands.describe(

        category=(
            "Category where YouTube counters "
            "will be created."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def youtubecounter(

        self,

        interaction: discord.Interaction,

        category: discord.CategoryChannel

    ):

        if interaction.guild is None:

            await interaction.response.send_message(

                "❌ This command can only be used "
                "inside a server.",

                ephemeral=True
            )

            return

        guild_config = self.get_guild_config(
            interaction.guild.id
        )

        guild_config[
            "counter_category_id"
        ] = category.id

        save_config(
            self.config
        )

        await interaction.response.send_message(

            "🔄 **Creating YouTube counters...**",

            ephemeral=True
        )

        await self.update_youtube()

        await interaction.edit_original_response(

            content=(

                "✅ **YouTube counter configured.**\n\n"

                f"📂 Category: {category.mention}\n\n"

                "The bot will automatically maintain:\n"
                "👥 Subscribers\n"
                "👍 Likes\n"
                "🎬 Videos\n"
                "🔴 Live status"
            )
        )

    # ========================================================
    # /YOUTUBEINFO
    # ========================================================

    @app_commands.command(

        name="youtubeinfo",

        description=(
            "Show the current YouTube statistics."
        )
    )
    async def youtubeinfo(

        self,

        interaction: discord.Interaction

    ):

        if interaction.guild is None:

            return

        if not self.api_ready():

            await interaction.response.send_message(

                "❌ YouTube API is not configured.",

                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        channel_data = await self.get_channel_data()

        if not channel_data:

            await interaction.followup.send(

                "❌ Could not retrieve YouTube "
                "channel information.",

                ephemeral=True
            )

            return

        statistics = channel_data.get(
            "statistics",
            {}
        )

        snippet = channel_data.get(
            "snippet",
            {}
        )

        subscribers = int(
            statistics.get(
                "subscriberCount",
                0
            )
        )

        videos = int(
            statistics.get(
                "videoCount",
                0
            )
        )

        likes = await self.calculate_recent_likes()

        live_video = await self.get_live_video()

        embed = discord.Embed(

            title="📺 YouTube Statistics",

            description=(
                f"**{snippet.get('title', 'YouTube Channel')}**"
            ),

            color=(
                discord.Color.red()
                if live_video
                else discord.Color.blurple()
            )
        )

        embed.add_field(

            name="👥 Subscribers",

            value=f"`{format_number(subscribers)}`",

            inline=True
        )

        embed.add_field(

            name="👍 Likes",

            value=(
                f"`{format_number(likes)}`\n"
                "Recent 50 videos"
            ),

            inline=True
        )

        embed.add_field(

            name="🎬 Videos",

            value=f"`{format_number(videos)}`",

            inline=True
        )

        embed.add_field(

            name="🔴 Live",

            value=(
                "`YES`"
                if live_video
                else
                "`NO`"
            ),

            inline=True
        )

        if live_video:

            live_title = (
                live_video
                .get("snippet", {})
                .get(
                    "title",
                    "Live Stream"
                )
            )

            live_id = live_video.get(
                "id"
            )

            embed.add_field(

                name="🔴 Current Stream",

                value=(

                    f"**{live_title}**\n"
                    f"https://www.youtube.com/watch?v={live_id}"
                ),

                inline=False
            )

        if snippet.get(
            "thumbnails",
            {}
        ).get(
            "high",
            {}
        ).get(
            "url"
        ):

            embed.set_thumbnail(

                url=(
                    snippet
                    ["thumbnails"]
                    ["high"]
                    ["url"]
                )
            )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )

    # ========================================================
    # /YOUTUBEREFRESH
    # ========================================================

    @app_commands.command(

        name="youtuberefresh",

        description=(
            "Immediately refresh YouTube statistics."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def youtuberefresh(

        self,

        interaction: discord.Interaction

    ):

        if interaction.guild is None:

            return

        await interaction.response.defer(
            ephemeral=True
        )

        if not self.api_ready():

            await interaction.followup.send(

                "❌ YouTube API is not configured.",

                ephemeral=True
            )

            return

        await self.update_youtube()

        await interaction.followup.send(

            "✅ YouTube statistics and live "
            "status refreshed.",

            ephemeral=True
        )

    # ========================================================
    # /YOUTUBESTATUS
    # ========================================================

    @app_commands.command(

        name="youtubestatus",

        description=(
            "Check the YouTube system configuration."
        )
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def youtubestatus(

        self,

        interaction: discord.Interaction

    ):

        if interaction.guild is None:

            return

        guild_config = self.config.get(
            str(interaction.guild.id),
            {}
        )

        notification_channel = (
            self.get_discord_channel(
                interaction.guild,
                "notification_channel_id"
            )
        )

        live_chat_channel = (
            self.get_discord_channel(
                interaction.guild,
                "live_chat_channel_id"
            )
        )

        upload_channel = (
            self.get_discord_channel(
                interaction.guild,
                "upload_channel_id"
            )
        )

        category = self.get_counter_category(
            interaction.guild
        )

        await interaction.response.send_message(

            "### 📺 YouTube System\n\n"

            f"🟢 **Enabled:** "
            f"`{guild_config.get('enabled', False)}`\n\n"

            f"📢 **Notifications:** "
            f"{notification_channel.mention if notification_channel else 'Not configured'}\n"

            f"🔴 **Live Channel:** "
            f"{live_chat_channel.mention if live_chat_channel else 'Not configured'}\n"

            f"🎬 **Upload Channel:** "
            f"{upload_channel.mention if upload_channel else 'Not configured'}\n"

            f"📊 **Counter Category:** "
            f"{category.mention if category else 'Not configured'}\n\n"

            f"👤 **Members:** `{interaction.guild.member_count or 0}`\n"
            f"🛡️ **Online Moderators:** `{self.count_online_moderators(interaction.guild)}`\n"
            f"🔴 **Live:** `{'LIVE' if guild_config.get('last_live_state', False) else 'OFFLINE'}`\n\n"

            f"🔑 **API:** "
            f"`{'Configured' if self.api_ready() else 'Not configured'}`",

            ephemeral=True
        )

    # ========================================================
    # ERROR HANDLERS
    # ========================================================

    @youtubesetup.error
    async def youtubesetup_error(
        self,
        interaction,
        error
    ):

        print(
            f"❌ /youtubesetup error: {repr(error)}"
        )

        if isinstance(
            error,
            app_commands.errors.MissingPermissions
        ):

            message = (
                "❌ You need **Administrator** "
                "permission."
            )

        else:

            message = (
                f"❌ YouTube setup error:\n"
                f"`{error}`"
            )

        if interaction.response.is_done():

            await interaction.followup.send(
                message,
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                message,
                ephemeral=True
            )

    # ========================================================
    # COG LOAD
    # ========================================================

    async def cog_load(self):

        print(
            "📺 YouTube cog initialized."
        )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot: commands.Bot
):

    await bot.add_cog(
        YouTubeSystem(bot)
    )


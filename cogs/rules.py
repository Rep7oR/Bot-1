# # ============================================================
# # RULES SYSTEM
# # File: cogs/rules.py
# # ============================================================

# import discord
# from discord.ext import commands
# from discord import app_commands

# import os
# import json
# import asyncio
# from datetime import datetime, timezone


# # ============================================================
# # SETTINGS
# # ============================================================

# CONFIG_FILE = "rules_config.json"

# # Mandatory reaction
# REQUIRED_REACTION = "👍"

# # Seconds between warnings for the same member
# WARNING_COOLDOWN = 30


# # ============================================================
# # JSON CONFIGURATION
# # ============================================================

# def load_config():

#     if not os.path.exists(CONFIG_FILE):
#         return {}

#     try:

#         with open(
#             CONFIG_FILE,
#             "r",
#             encoding="utf-8"
#         ) as file:

#             data = json.load(file)

#             if isinstance(data, dict):
#                 return data

#     except Exception as e:

#         print(
#             f"❌ Rules config load error: {e}"
#         )

#     return {}


# def save_config(data):

#     try:

#         temporary_file = CONFIG_FILE + ".tmp"

#         with open(
#             temporary_file,
#             "w",
#             encoding="utf-8"
#         ) as file:

#             json.dump(
#                 data,
#                 file,
#                 indent=4,
#                 ensure_ascii=False
#             )

#         os.replace(
#             temporary_file,
#             CONFIG_FILE
#         )

#         return True

#     except Exception as e:

#         print(
#             f"❌ Rules config save error: {e}"
#         )

#         return False


# # ============================================================
# # RULES COG
# # ============================================================

# class Rules(commands.Cog):

#     def __init__(self, bot):

#         self.bot = bot

#         # Load existing configuration
#         self.config = load_config()

#         # Warning cooldown storage
#         #
#         # {
#         #     guild_id: {
#         #         user_id: timestamp
#         #     }
#         # }
#         #
#         self.warning_cooldowns = {}

#         print("📜 Rules system loaded.")

#     # ========================================================
#     # GET GUILD CONFIG
#     # ========================================================

#     def get_guild_config(self, guild_id):

#         return self.config.get(
#             str(guild_id)
#         )

#     # ========================================================
#     # SAVE GUILD CONFIG
#     # ========================================================

#     def save_guild_config(
#         self,
#         guild_id,
#         data
#     ):

#         self.config[
#             str(guild_id)
#         ] = data

#         return save_config(
#             self.config
#         )

#     # ========================================================
#     # GET RULES MESSAGE
#     # ========================================================

#     async def get_rules_message(
#         self,
#         guild
#     ):

#         config = self.get_guild_config(
#             guild.id
#         )

#         if not config:
#             return None

#         channel_id = config.get(
#             "channel_id"
#         )

#         message_id = config.get(
#             "message_id"
#         )

#         if not channel_id or not message_id:
#             return None

#         channel = guild.get_channel(
#             int(channel_id)
#         )

#         if not isinstance(
#             channel,
#             discord.TextChannel
#         ):
#             return None

#         try:

#             message = await channel.fetch_message(
#                 int(message_id)
#             )

#             return message

#         except (
#             discord.NotFound,
#             discord.Forbidden,
#             discord.HTTPException
#         ):

#             return None

#     # ========================================================
#     # CHECK IF MEMBER ACCEPTED RULES
#     # ========================================================

#     async def member_accepted_rules(
#         self,
#         guild,
#         member
#     ):

#         # Bots are ignored
#         if member.bot:
#             return True

#         rules_message = await self.get_rules_message(
#             guild
#         )

#         if rules_message is None:
#             return False

#         # ----------------------------------------------------
#         # Find required 👍 reaction
#         # ----------------------------------------------------

#         required_reaction = None

#         for reaction in rules_message.reactions:

#             if str(
#                 reaction.emoji
#             ) == REQUIRED_REACTION:

#                 required_reaction = reaction
#                 break

#         # No 👍 reaction exists
#         if required_reaction is None:
#             return False

#         # ----------------------------------------------------
#         # Check actual Discord reaction
#         # ----------------------------------------------------

#         try:

#             async for user in required_reaction.users():

#                 if user.id == member.id:
#                     return True

#         except (
#             discord.Forbidden,
#             discord.HTTPException
#         ):

#             return False

#         return False

#     # ========================================================
#     # CREATE RULE EMBED
#     # ========================================================

#     def create_rules_embed(
#         self,
#         title,
#         rules
#     ):

#         embed = discord.Embed(

#             title=f"📜 {title}",

#             description=rules,

#             color=discord.Color.blurple(),

#             timestamp=datetime.now(
#                 timezone.utc
#             )
#         )

#         embed.add_field(

#             name="⚠️ IMPORTANT",

#             value=(

#                 f"React with {REQUIRED_REACTION} "
#                 "to this message to confirm that "
#                 "you have read and accepted the rules."
#             ),

#             inline=False
#         )

#         embed.set_footer(

#             text=(
#                 "You must accept the rules "
#                 "before participating in the server."
#             )
#         )

#         return embed

#     # ========================================================
#     # RULE CREATION MODAL
#     # ========================================================

#     class RuleModal(
#         discord.ui.Modal,
#         title="Create Server Rules"
#     ):

#         rule_title = discord.ui.TextInput(

#             label="Rules Title",

#             placeholder="Example: Server Rules",

#             required=True,

#             max_length=100,

#             style=discord.TextStyle.short
#         )

#         rule_content = discord.ui.TextInput(

#             label="Rules",

#             placeholder=(
#                 "Enter your server rules here..."
#             ),

#             required=True,

#             max_length=4000,

#             style=discord.TextStyle.paragraph
#         )

#         def __init__(
#             self,
#             cog,
#             channel
#         ):

#             super().__init__()

#             self.cog = cog

#             self.channel = channel

#         # ====================================================
#         # MODAL SUBMIT
#         # ====================================================

#         async def on_submit(
#             self,
#             interaction: discord.Interaction
#         ):

#             channel = self.channel

#             # ------------------------------------------------
#             # Check channel
#             # ------------------------------------------------

#             if not isinstance(
#                 channel,
#                 discord.TextChannel
#             ):

#                 await interaction.response.send_message(

#                     "❌ The selected channel is not "
#                     "a normal text channel.",

#                     ephemeral=True
#                 )

#                 return

#             # ------------------------------------------------
#             # Check permissions
#             # ------------------------------------------------

#             bot_member = interaction.guild.me

#             permissions = channel.permissions_for(
#                 bot_member
#             )

#             missing = []

#             if not permissions.view_channel:
#                 missing.append(
#                     "View Channel"
#                 )

#             if not permissions.send_messages:
#                 missing.append(
#                     "Send Messages"
#                 )

#             if not permissions.embed_links:
#                 missing.append(
#                     "Embed Links"
#                 )

#             if not permissions.add_reactions:
#                 missing.append(
#                     "Add Reactions"
#                 )

#             if not permissions.read_message_history:
#                 missing.append(
#                     "Read Message History"
#                 )

#             if missing:

#                 await interaction.response.send_message(

#                     "❌ I cannot use that channel.\n\n"

#                     "**Missing permissions:**\n"
#                     + "\n".join(
#                         f"• {permission}"
#                         for permission in missing
#                     ),

#                     ephemeral=True
#                 )

#                 return

#             # ------------------------------------------------
#             # Create rules embed
#             # ------------------------------------------------

#             embed = self.cog.create_rules_embed(

#                 str(
#                     self.rule_title.value
#                 ),

#                 str(
#                     self.rule_content.value
#                 )
#             )

#             # ------------------------------------------------
#             # Post rules
#             # ------------------------------------------------

#             try:

#                 rules_message = await channel.send(
#                     embed=embed
#                 )

#             except Exception as e:

#                 await interaction.response.send_message(

#                     "❌ Failed to post the rules.\n\n"
#                     f"`{type(e).__name__}: {e}`",

#                     ephemeral=True
#                 )

#                 return

#             # ------------------------------------------------
#             # Add mandatory 👍 reaction
#             # ------------------------------------------------

#             try:

#                 await rules_message.add_reaction(
#                     REQUIRED_REACTION
#                 )

#             except Exception as e:

#                 # ------------------------------------------------
#                 # Reaction is mandatory.
#                 # If bot cannot add it, delete rules message.
#                 # ------------------------------------------------

#                 try:

#                     await rules_message.delete()

#                 except Exception:

#                     pass

#                 await interaction.response.send_message(

#                     "❌ I could not add the mandatory "
#                     f"{REQUIRED_REACTION} reaction.\n\n"

#                     "Please make sure I have the "
#                     "**Add Reactions** permission "
#                     "in that channel.",

#                     ephemeral=True
#                 )

#                 return

#             # ------------------------------------------------
#             # Save configuration
#             # ------------------------------------------------

#             configuration = {

#                 "channel_id": channel.id,

#                 "message_id": rules_message.id,

#                 "title": str(
#                     self.rule_title.value
#                 ),

#                 "rules": str(
#                     self.rule_content.value
#                 ),

#                 "required_reaction": REQUIRED_REACTION,

#                 "created_by": interaction.user.id,

#                 "created_at": datetime.now(
#                     timezone.utc
#                 ).isoformat()
#             }

#             saved = self.cog.save_guild_config(

#                 interaction.guild.id,

#                 configuration
#             )

#             # ------------------------------------------------
#             # Configuration save failed
#             # ------------------------------------------------

#             if not saved:

#                 await interaction.response.send_message(

#                     "⚠️ Rules were posted successfully, "
#                     "but I could not save the configuration.\n\n"

#                     "Please check the bot's file permissions.",

#                     ephemeral=True
#                 )

#                 return

#             # ------------------------------------------------
#             # Success
#             # ------------------------------------------------

#             await interaction.response.send_message(

#                 "✅ **Server rules created successfully!**\n\n"

#                 f"📍 Channel: {channel.mention}\n"

#                 f"📜 Title: **{self.rule_title.value}**\n"

#                 f"👍 Required reaction: {REQUIRED_REACTION}\n\n"

#                 "Members must react to the rules message "
#                 "before participating in the server.",

#                 ephemeral=True
#             )

#     # ========================================================
#     # CHANNEL SELECT VIEW
#     # ========================================================

#     class RuleChannelView(
#         discord.ui.View
#     ):

#         def __init__(
#             self,
#             cog,
#             author
#         ):

#             super().__init__(
#                 timeout=120
#             )

#             self.cog = cog

#             self.author = author

#             # ------------------------------------------------
#             # IMPORTANT:
#             # Create ChannelSelect here and add it manually.
#             # ------------------------------------------------

#             self.channel_select = discord.ui.ChannelSelect(

#                 placeholder=(
#                     "📢 Select the rules text channel"
#                 ),

#                 channel_types=[
#                     discord.ChannelType.text
#                 ],

#                 min_values=1,

#                 max_values=1
#             )

#             # ------------------------------------------------
#             # Attach callback
#             # ------------------------------------------------

#             self.channel_select.callback = (
#                 self.channel_selected
#             )

#             # ------------------------------------------------
#             # Add selector to View
#             # ------------------------------------------------

#             self.add_item(
#                 self.channel_select
#             )

#         # ====================================================
#         # CHANNEL SELECTED
#         # ====================================================

#         async def channel_selected(
#             self,
#             interaction: discord.Interaction
#         ):

#             # ------------------------------------------------
#             # Only original admin
#             # ------------------------------------------------

#             if interaction.user.id != self.author.id:

#                 await interaction.response.send_message(

#                     "❌ This setup menu belongs to "
#                     "another administrator.",

#                     ephemeral=True
#                 )

#                 return

#             # ------------------------------------------------
#             # Check selection
#             # ------------------------------------------------

#             if not self.channel_select.values:

#                 await interaction.response.send_message(

#                     "❌ Please select a channel.",

#                     ephemeral=True
#                 )

#                 return

#             channel = self.channel_select.values[0]

#             # ------------------------------------------------
#             # Verify text channel
#             # ------------------------------------------------

#             if not isinstance(
#                 channel,
#                 discord.TextChannel
#             ):

#                 await interaction.response.send_message(

#                     "❌ Please select a normal "
#                     "text channel.",

#                     ephemeral=True
#                 )

#                 return

#             # ------------------------------------------------
#             # Check bot permissions
#             # ------------------------------------------------

#             bot_member = interaction.guild.me

#             permissions = channel.permissions_for(
#                 bot_member
#             )

#             missing = []

#             if not permissions.view_channel:
#                 missing.append(
#                     "View Channel"
#                 )

#             if not permissions.send_messages:
#                 missing.append(
#                     "Send Messages"
#                 )

#             if not permissions.embed_links:
#                 missing.append(
#                     "Embed Links"
#                 )

#             if not permissions.add_reactions:
#                 missing.append(
#                     "Add Reactions"
#                 )

#             if not permissions.read_message_history:
#                 missing.append(
#                     "Read Message History"
#                 )

#             if missing:

#                 await interaction.response.send_message(

#                     "❌ I cannot use that channel.\n\n"

#                     "**Missing permissions:**\n"
#                     + "\n".join(
#                         f"• {permission}"
#                         for permission in missing
#                     ),

#                     ephemeral=True
#                 )

#                 return

#             # ------------------------------------------------
#             # Open rules form
#             # ------------------------------------------------

#             modal = self.cog.RuleModal(

#                 self.cog,

#                 channel
#             )

#             await interaction.response.send_modal(
#                 modal
#             )

#     # ========================================================
#     # /RULE
#     # ========================================================

#     @app_commands.command(

#         name="rule",

#         description=(
#             "Create and post the server rules."
#         )
#     )
#     @app_commands.checks.has_permissions(
#         administrator=True
#     )
#     async def rule(
#         self,
#         interaction: discord.Interaction
#     ):

#         # ----------------------------------------------------
#         # Server only
#         # ----------------------------------------------------

#         if interaction.guild is None:

#             await interaction.response.send_message(

#                 "❌ This command can only be used "
#                 "inside a server.",

#                 ephemeral=True
#             )

#             return

#         # ----------------------------------------------------
#         # Create selector
#         # ----------------------------------------------------

#         view = self.RuleChannelView(

#             self,

#             interaction.user
#         )

#         # ----------------------------------------------------
#         # Send private setup menu
#         # ----------------------------------------------------

#         await interaction.response.send_message(

#             "📜 **Server Rules Setup**\n\n"

#             "Select the **text channel** where you "
#             "want the rules message to be posted.\n\n"

#             "After selecting the channel, a form will "
#             "open where you can enter your rules.\n\n"

#             f"Members will be required to react with "
#             f"{REQUIRED_REACTION} to participate.",

#             view=view,

#             ephemeral=True
#         )

#     # ========================================================
#     # /RULEREMOVE
#     # ========================================================

#     @app_commands.command(

#         name="ruleremove",

#         description=(
#             "Remove the saved rules configuration."
#         )
#     )
#     @app_commands.checks.has_permissions(
#         administrator=True
#     )
#     async def ruleremove(
#         self,
#         interaction: discord.Interaction
#     ):

#         if interaction.guild is None:

#             await interaction.response.send_message(

#                 "❌ This command can only be used "
#                 "inside a server.",

#                 ephemeral=True
#             )

#             return

#         guild_id = str(
#             interaction.guild.id
#         )

#         if guild_id not in self.config:

#             await interaction.response.send_message(

#                 "⚪ Rules are not configured.",

#                 ephemeral=True
#             )

#             return

#         del self.config[
#             guild_id
#         ]

#         saved = save_config(
#             self.config
#         )

#         if saved:

#             await interaction.response.send_message(

#                 "✅ Rules configuration removed.\n\n"

#                 "⚠️ The existing rules message was "
#                 "not deleted.",

#                 ephemeral=True
#             )

#         else:

#             await interaction.response.send_message(

#                 "❌ Configuration could not be saved.",

#                 ephemeral=True
#             )

#     # ========================================================
#     # /RULESTATUS
#     # ========================================================

#     @app_commands.command(

#         name="rulestatus",

#         description=(
#             "Show the current rules configuration."
#         )
#     )
#     @app_commands.checks.has_permissions(
#         administrator=True
#     )
#     async def rulestatus(
#         self,
#         interaction: discord.Interaction
#     ):

#         if interaction.guild is None:

#             await interaction.response.send_message(

#                 "❌ This command can only be used "
#                 "inside a server.",

#                 ephemeral=True
#             )

#             return

#         config = self.get_guild_config(
#             interaction.guild.id
#         )

#         if not config:

#             await interaction.response.send_message(

#                 "⚪ Rules are not configured "
#                 "for this server.",

#                 ephemeral=True
#             )

#             return

#         channel = interaction.guild.get_channel(

#             int(
#                 config.get(
#                     "channel_id",
#                     0
#                 )
#             )
#         )

#         rules_message = await self.get_rules_message(

#             interaction.guild
#         )

#         # ----------------------------------------------------
#         # Create status embed
#         # ----------------------------------------------------

#         embed = discord.Embed(

#             title="📜 Rules Status",

#             color=discord.Color.blurple(),

#             timestamp=datetime.now(
#                 timezone.utc
#             )
#         )

#         # Status
#         if rules_message:

#             embed.add_field(

#                 name="Status",

#                 value="🟢 Active",

#                 inline=False
#             )

#         else:

#             embed.add_field(

#                 name="Status",

#                 value=(
#                     "🔴 Rules message not found"
#                 ),

#                 inline=False
#             )

#         # Channel
#         embed.add_field(

#             name="Rules Channel",

#             value=(
#                 channel.mention
#                 if channel
#                 else "❌ Channel not found"
#             ),

#             inline=True
#         )

#         # Reaction
#         embed.add_field(

#             name="Required Reaction",

#             value=REQUIRED_REACTION,

#             inline=True
#         )

#         # Message
#         if rules_message:

#             embed.add_field(

#                 name="Rules Message",

#                 value=(
#                     f"[Jump to Rules Message]"
#                     f"({rules_message.jump_url})"
#                 ),

#                 inline=False
#             )

#         else:

#             embed.add_field(

#                 name="Rules Message",

#                 value="❌ Message not found",

#                 inline=False
#             )

#         # ----------------------------------------------------
#         # Send
#         # ----------------------------------------------------

#         await interaction.response.send_message(

#             embed=embed,

#             ephemeral=True
#         )

#     # ========================================================
#     # MESSAGE LISTENER
#     # ========================================================

#     @commands.Cog.listener()
#     async def on_message(
#         self,
#         message: discord.Message
#     ):

#         # ----------------------------------------------------
#         # Ignore DMs
#         # ----------------------------------------------------

#         if message.guild is None:
#             return

#         # ----------------------------------------------------
#         # Ignore bots
#         # ----------------------------------------------------

#         if message.author.bot:
#             return

#         # ----------------------------------------------------
#         # Ignore administrators
#         # ----------------------------------------------------

#         if (
#             message.author.guild_permissions.administrator
#         ):
#             return

#         # ----------------------------------------------------
#         # Get configuration
#         # ----------------------------------------------------

#         config = self.get_guild_config(

#             message.guild.id
#         )

#         if not config:
#             return

#         # ----------------------------------------------------
#         # Get rules message
#         # ----------------------------------------------------

#         rules_message = await self.get_rules_message(

#             message.guild
#         )

#         if rules_message is None:
#             return

#         # ----------------------------------------------------
#         # Don't warn inside rules channel
#         # ----------------------------------------------------

#         if (
#             message.channel.id
#             == rules_message.channel.id
#         ):

#             return

#         # ----------------------------------------------------
#         # Check actual 👍 reaction
#         # ----------------------------------------------------

#         accepted = await self.member_accepted_rules(

#             message.guild,

#             message.author
#         )

#         if accepted:
#             return

#         # ----------------------------------------------------
#         # Warning cooldown
#         # ----------------------------------------------------

#         guild_id = message.guild.id

#         user_id = message.author.id

#         current_time = (
#             asyncio.get_running_loop().time()
#         )

#         guild_cooldowns = (
#             self.warning_cooldowns.setdefault(
#                 guild_id,
#                 {}
#             )
#         )

#         last_warning = guild_cooldowns.get(
#             user_id,
#             0
#         )

#         if (
#             current_time - last_warning
#             < WARNING_COOLDOWN
#         ):

#             return

#         guild_cooldowns[
#             user_id
#         ] = current_time

#         # ----------------------------------------------------
#         # Send warning
#         # ----------------------------------------------------

#         try:

#             await message.channel.send(

#                 f"⚠️ {message.author.mention} "
#                 "you must read and accept the server "
#                 "rules before participating.\n\n"

#                 f"Please react with {REQUIRED_REACTION} "
#                 "to the rules message in "
#                 f"{rules_message.channel.mention}.\n\n"

#                 f"[📜 Go to Rules]"
#                 f"({rules_message.jump_url})",

#                 delete_after=10
#             )

#         except (
#             discord.Forbidden,
#             discord.HTTPException
#         ):

#             pass

#     # ========================================================
#     # REACTION ADDED
#     # ========================================================

#     @commands.Cog.listener()
#     async def on_raw_reaction_add(
#         self,
#         payload: discord.RawReactionActionEvent
#     ):

#         # ----------------------------------------------------
#         # Ignore DMs
#         # ----------------------------------------------------

#         if payload.guild_id is None:
#             return

#         # ----------------------------------------------------
#         # Ignore bot reactions
#         # ----------------------------------------------------

#         if payload.user_id == self.bot.user.id:
#             return

#         # ----------------------------------------------------
#         # Get config
#         # ----------------------------------------------------

#         config = self.get_guild_config(

#             payload.guild_id
#         )

#         if not config:
#             return

#         # ----------------------------------------------------
#         # Check rules message
#         # ----------------------------------------------------

#         rules_message_id = config.get(
#             "message_id"
#         )

#         if not rules_message_id:
#             return

#         if payload.message_id != int(
#             rules_message_id
#         ):

#             return

#         # ----------------------------------------------------
#         # Only 👍 is accepted
#         # ----------------------------------------------------

#         if str(
#             payload.emoji
#         ) != REQUIRED_REACTION:

#             return

#         # ----------------------------------------------------
#         # Clear warning cooldown
#         # ----------------------------------------------------

#         guild_cooldowns = (
#             self.warning_cooldowns.get(
#                 payload.guild_id,
#                 {}
#             )
#         )

#         guild_cooldowns.pop(
#             payload.user_id,
#             None
#         )

#         # ----------------------------------------------------
#         # Log
#         # ----------------------------------------------------

#         guild = self.bot.get_guild(
#             payload.guild_id
#         )

#         if guild:

#             member = guild.get_member(
#                 payload.user_id
#             )

#             if member:

#                 print(

#                     f"📜 {member} accepted "
#                     f"the rules in {guild.name}."
#                 )

#     # ========================================================
#     # REACTION REMOVED
#     # ========================================================

#     @commands.Cog.listener()
#     async def on_raw_reaction_remove(
#         self,
#         payload: discord.RawReactionActionEvent
#     ):

#         # ----------------------------------------------------
#         # Ignore DMs
#         # ----------------------------------------------------

#         if payload.guild_id is None:
#             return

#         # ----------------------------------------------------
#         # Get config
#         # ----------------------------------------------------

#         config = self.get_guild_config(

#             payload.guild_id
#         )

#         if not config:
#             return

#         rules_message_id = config.get(
#             "message_id"
#         )

#         if not rules_message_id:
#             return

#         # ----------------------------------------------------
#         # Check rules message
#         # ----------------------------------------------------

#         if payload.message_id != int(
#             rules_message_id
#         ):

#             return

#         # ----------------------------------------------------
#         # Only 👍 matters
#         # ----------------------------------------------------

#         if str(
#             payload.emoji
#         ) != REQUIRED_REACTION:

#             return

#         print(

#             f"⚠️ User {payload.user_id} "
#             "removed their rules reaction."
#         )

#     # ========================================================
#     # RULE COMMAND ERROR
#     # ========================================================

#     @rule.error
#     async def rule_error(
#         self,
#         interaction,
#         error
#     ):

#         if isinstance(
#             error,
#             app_commands.errors.MissingPermissions
#         ):

#             message = (
#                 "❌ You need **Administrator** "
#                 "permission to use `/rule`."
#             )

#         else:

#             print(
#                 f"❌ /rule error: {error}"
#             )

#             message = (
#                 "❌ An error occurred while "
#                 "opening the rules setup."
#             )

#         try:

#             if interaction.response.is_done():

#                 await interaction.followup.send(

#                     message,

#                     ephemeral=True
#                 )

#             else:

#                 await interaction.response.send_message(

#                     message,

#                     ephemeral=True
#                 )

#         except Exception:

#             pass


# # ============================================================
# # SETUP
# # ============================================================

# async def setup(bot):

#     await bot.add_cog(
#         Rules(bot)
#     )

#     print(
#         "✅ Rules Cog loaded successfully."
#     )

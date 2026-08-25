import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

class RoleManager(commands.Cog):
    """
    A Discord cog for managing member roles with slash commands.
    
    Commands:
    - /assign <member> <role> - Assign a role to a specific member
    - /assignall <role> - Assign a role to all members
    - /remove <member> <role> - Remove a role from a specific member
    - /removeall <role> - Remove a role from all members
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    # Helper function to get role from name or ID
    async def get_role(self, interaction: discord.Interaction, role_input: str) -> Optional[discord.Role]:
        """Get a role by name or ID from the guild"""
        guild = interaction.guild
        
        # Try to get role by ID
        try:
            role_id = int(role_input)
            role = guild.get_role(role_id)
            if role:
                return role
        except ValueError:
            pass
        
        # Try to get role by name
        role = discord.utils.get(guild.roles, name=role_input)
        return role
    
    # Slash command: Assign role to a specific member
    @app_commands.command(name="assign", description="Assign a role to a specific member")
    @app_commands.describe(
        member="The member to assign the role to",
        role="The role to assign (by name or ID)"
    )
    async def assign(self, interaction: discord.Interaction, member: discord.Member, role: str):
        """Assign a role to a specific member"""
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ You don't have permission to manage roles!",
                ephemeral=True
            )
            return
        
        # Get the role
        target_role = await self.get_role(interaction, role)
        if not target_role:
            await interaction.response.send_message(
                f"❌ Role '{role}' not found!",
                ephemeral=True
            )
            return
        
        # Check if bot has permission to assign this role
        if target_role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(
                f"❌ I don't have permission to assign the role '{target_role.name}' (it's above my highest role)!",
                ephemeral=True
            )
            return
        
        # Check if member already has the role
        if target_role in member.roles:
            await interaction.response.send_message(
                f"ℹ️ {member.mention} already has the role '{target_role.name}'!",
                ephemeral=True
            )
            return
        
        try:
            await member.add_roles(target_role)
            await interaction.response.send_message(
                f"✅ Successfully assigned **{target_role.name}** to {member.mention}",
                ephemeral=False
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ I don't have permission to assign roles!",
                ephemeral=True
            )
    
    # Slash command: Assign role to all members
    @app_commands.command(name="assignall", description="Assign a role to all members in the server")
    @app_commands.describe(role="The role to assign to all members (by name or ID)")
    async def assignall(self, interaction: discord.Interaction, role: str):
        """Assign a role to all members in the server"""
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ You don't have permission to manage roles!",
                ephemeral=True
            )
            return
        
        # Defer the response as this might take a while
        await interaction.response.defer()
        
        # Get the role
        target_role = await self.get_role(interaction, role)
        if not target_role:
            await interaction.followup.send(f"❌ Role '{role}' not found!")
            return
        
        # Check if bot has permission to assign this role
        if target_role.position >= interaction.guild.me.top_role.position:
            await interaction.followup.send(
                f"❌ I don't have permission to assign the role '{target_role.name}' (it's above my highest role)!"
            )
            return
        
        # Assign role to all members
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for member in interaction.guild.members:
            # Skip bot accounts
            if member.bot:
                skipped_count += 1
                continue
            
            # Skip if member already has the role
            if target_role in member.roles:
                skipped_count += 1
                continue
            
            try:
                await member.add_roles(target_role)
                success_count += 1
            except discord.Forbidden:
                failed_count += 1
            except Exception as e:
                failed_count += 1
        
        # Send summary
        summary = f"✅ **Role Assignment Complete**\n"
        summary += f"Role: **{target_role.name}**\n"
        summary += f"✓ Assigned to: {success_count} member(s)\n"
        summary += f"⊝ Skipped: {skipped_count} member(s)\n"
        if failed_count > 0:
            summary += f"✗ Failed: {failed_count} member(s)"
        
        await interaction.followup.send(summary)
    
    # Slash command: Remove role from a specific member
    @app_commands.command(name="remove", description="Remove a role from a specific member")
    @app_commands.describe(
        member="The member to remove the role from",
        role="The role to remove (by name or ID)"
    )
    async def remove(self, interaction: discord.Interaction, member: discord.Member, role: str):
        """Remove a role from a specific member"""
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ You don't have permission to manage roles!",
                ephemeral=True
            )
            return
        
        # Get the role
        target_role = await self.get_role(interaction, role)
        if not target_role:
            await interaction.response.send_message(
                f"❌ Role '{role}' not found!",
                ephemeral=True
            )
            return
        
        # Check if bot has permission to remove this role
        if target_role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(
                f"❌ I don't have permission to remove the role '{target_role.name}' (it's above my highest role)!",
                ephemeral=True
            )
            return
        
        # Check if member has the role
        if target_role not in member.roles:
            await interaction.response.send_message(
                f"ℹ️ {member.mention} doesn't have the role '{target_role.name}'!",
                ephemeral=True
            )
            return
        
        try:
            await member.remove_roles(target_role)
            await interaction.response.send_message(
                f"✅ Successfully removed **{target_role.name}** from {member.mention}",
                ephemeral=False
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ I don't have permission to remove roles!",
                ephemeral=True
            )
    
    # Slash command: Remove role from all members
    @app_commands.command(name="removeall", description="Remove a role from all members in the server")
    @app_commands.describe(role="The role to remove from all members (by name or ID)")
    async def removeall(self, interaction: discord.Interaction, role: str):
        """Remove a role from all members in the server"""
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ You don't have permission to manage roles!",
                ephemeral=True
            )
            return
        
        # Defer the response as this might take a while
        await interaction.response.defer()
        
        # Get the role
        target_role = await self.get_role(interaction, role)
        if not target_role:
            await interaction.followup.send(f"❌ Role '{role}' not found!")
            return
        
        # Check if bot has permission to remove this role
        if target_role.position >= interaction.guild.me.top_role.position:
            await interaction.followup.send(
                f"❌ I don't have permission to remove the role '{target_role.name}' (it's above my highest role)!"
            )
            return
        
        # Remove role from all members
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for member in interaction.guild.members:
            # Skip if member doesn't have the role
            if target_role not in member.roles:
                skipped_count += 1
                continue
            
            try:
                await member.remove_roles(target_role)
                success_count += 1
            except discord.Forbidden:
                failed_count += 1
            except Exception as e:
                failed_count += 1
        
        # Send summary
        summary = f"✅ **Role Removal Complete**\n"
        summary += f"Role: **{target_role.name}**\n"
        summary += f"✓ Removed from: {success_count} member(s)\n"
        summary += f"⊝ Skipped: {skipped_count} member(s)\n"
        if failed_count > 0:
            summary += f"✗ Failed: {failed_count} member(s)"
        
        await interaction.followup.send(summary)


# Function to load the cog
async def setup(bot: commands.Bot):
    """Add this cog to your bot"""
    await bot.add_cog(RoleManager(bot))

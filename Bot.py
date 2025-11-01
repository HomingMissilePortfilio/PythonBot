import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Optional


CLAN_DATA_FILE = 'clan_data.json'

class ClanManager:
    def __init__(self):
        self.clan_data = self.load_data()
    
    def load_data(self):
        """Load clan data from JSON file"""
        if os.path.exists(CLAN_DATA_FILE):
            with open(CLAN_DATA_FILE, 'r') as f:
                return json.load(f)
        return {"clans": {}, "players": {}}
    
    def save_data(self):
        """Save clan data to JSON file"""
        with open(CLAN_DATA_FILE, 'w') as f:
            json.dump(self.clan_data, f, indent=4)
    
    def create_clan(self, leader_id: int, clan_name: str):
        """Create a new clan"""
        if clan_name in self.clan_data["clans"]:
            return False, "Clan name already exists"
        
        self.clan_data["clans"][clan_name] = {
            "leader": leader_id,
            "members": [leader_id],
            "mods": [],
            "coleaders": []
        }
        
        self.clan_data["players"][str(leader_id)] = {
            "clan": clan_name,
            "role": "Leader"
        }
        
        self.save_data()
        return True, f"Clan '{clan_name}' created successfully!"
    
    def get_player_clan(self, player_id: int):
        """Get the clan a player belongs to"""
        return self.clan_data["players"].get(str(player_id), {}).get("clan")
    
    def get_player_role(self, player_id: int):
        """Get the role of a player in their clan"""
        return self.clan_data["players"].get(str(player_id), {}).get("role", "Member")
    
    def is_leader(self, player_id: int, clan_name: str):
        """Check if player is leader of the clan"""
        return self.clan_data["clans"][clan_name]["leader"] == player_id
    
    def is_coleader(self, player_id: int, clan_name: str):
        """Check if player is co-leader of the clan"""
        return player_id in self.clan_data["clans"][clan_name]["coleaders"]
    
    def is_mod(self, player_id: int, clan_name: str):
        """Check if player is mod of the clan"""
        return player_id in self.clan_data["clans"][clan_name]["mods"]
    
    def has_permission(self, player_id: int, clan_name: str, action: str):
        """Check if player has permission for an action"""
        if self.is_leader(player_id, clan_name):
            return True
        
        role = self.get_player_role(player_id)
        
        if action == "kick":
            return role in ["Leader", "Co-Leader", "Mod"]
        elif action == "invite":
            return role in ["Leader", "Co-Leader"]
        elif action == "promote_demote":
            return role in ["Leader", "Co-Leader"]
        
        return False
    
    def kick_member(self, kicker_id: int, target_name: str, clan_name: str):
        """Kick a member from the clan"""

        target_id = self.find_player_id_by_name(target_name)
        if not target_id:
            return False, "Player not found"
        
        if target_id == kicker_id:
            return False, "You cannot kick yourself"
        
        clan = self.clan_data["clans"][clan_name]
        
        # Check if target is in clan
        if target_id not in clan["members"]:
            return False, "Player is not in your clan"
        
        # Check permissions
        if not self.has_permission(kicker_id, clan_name, "kick"):
            return False, "You don't have permission to kick members"
        
        # Cannot kick leaders
        if self.is_leader(target_id, clan_name):
            return False, "You cannot kick the clan leader"
        
        # Remove from clan
        clan["members"].remove(target_id)
        if target_id in clan["mods"]:
            clan["mods"].remove(target_id)
        if target_id in clan["coleaders"]:
            clan["coleaders"].remove(target_id)
        
        # Remove from players data
        if str(target_id) in self.clan_data["players"]:
            del self.clan_data["players"][str(target_id)]
        
        self.save_data()
        return True, f"Successfully kicked {target_name} from the clan"
    
    def invite_member(self, inviter_id: int, target_name: str, clan_name: str):
        """Invite a player to the clan"""

        target_id = self.find_player_id_by_name(target_name)
        if not target_id:
            return False, "Player not found"
        
        if not self.has_permission(inviter_id, clan_name, "invite"):
            return False, "You don't have permission to invite members"
        

        if str(target_id) in self.clan_data["players"]:
            return False, "Player is already in a clan"
        
        # Add to clan
        clan = self.clan_data["clans"][clan_name]
        clan["members"].append(target_id)
        
        self.clan_data["players"][str(target_id)] = {
            "clan": clan_name,
            "role": "Member"
        }
        
        self.save_data()
        return True, f"Successfully invited {target_name} to the clan"
    
    def disband_clan(self, leader_id: int, clan_name: str):
        """Disband a clan"""
        if not self.is_leader(leader_id, clan_name):
            return False, "Only the clan leader can disband the clan"
        

        clan_members = self.clan_data["clans"][clan_name]["members"].copy()
        for member_id in clan_members:
            if str(member_id) in self.clan_data["players"]:
                del self.clan_data["players"][str(member_id)]
        

        del self.clan_data["clans"][clan_name]
        self.save_data()
        
        return True, f"Clan '{clan_name}' has been disbanded"
    
    def promote_member(self, promoter_id: int, target_name: str, clan_name: str, role: str):
        """Promote a clan member"""
        target_id = self.find_player_id_by_name(target_name)
        if not target_id:
            return False, "Player not found"
        
        if not self.has_permission(promoter_id, clan_name, "promote_demote"):
            return False, "You don't have permission to promote members"
        
        clan = self.clan_data["clans"][clan_name]
        current_role = self.get_player_role(target_id)
        
        if role == "Mod":
            if current_role != "Member":
                return False, f"Player is already {current_role}"
            clan["mods"].append(target_id)
            self.clan_data["players"][str(target_id)]["role"] = "Mod"
        
        elif role == "Co-Leader":
            if current_role == "Member":
                # Promote to Mod first, then to Co-Leader
                clan["mods"].append(target_id)
                clan["coleaders"].append(target_id)
                self.clan_data["players"][str(target_id)]["role"] = "Co-Leader"
            elif current_role == "Mod":
                clan["mods"].remove(target_id)
                clan["coleaders"].append(target_id)
                self.clan_data["players"][str(target_id)]["role"] = "Co-Leader"
            else:
                return False, f"Player is already {current_role}"
        
        self.save_data()
        return True, f"Successfully promoted {target_name} to {role}"
    
    def demote_member(self, demoter_id: int, target_name: str, clan_name: str):
        """Demote a clan member"""
        target_id = self.find_player_id_by_name(target_name)
        if not target_id:
            return False, "Player not found"
        
        if not self.has_permission(demoter_id, clan_name, "promote_demote"):
            return False, "You don't have permission to demote members"
        
        clan = self.clan_data["clans"][clan_name]
        current_role = self.get_player_role(target_id)
        
        if current_role == "Co-Leader":
            clan["coleaders"].remove(target_id)
            clan["mods"].append(target_id)
            self.clan_data["players"][str(target_id)]["role"] = "Mod"
        elif current_role == "Mod":
            clan["mods"].remove(target_id)
            self.clan_data["players"][str(target_id)]["role"] = "Member"
        else:
            return False, "Cannot demote a regular member"
        
        self.save_data()
        return True, f"Successfully demoted {target_name}"
    
    def force_kick(self, target_name: str):
        """Staff command: Force kick a player from any clan"""
        target_id = self.find_player_id_by_name(target_name)
        if not target_id:
            return False, "Player not found"
        
        if str(target_id) not in self.clan_data["players"]:
            return False, "Player is not in any clan"
        
        clan_name = self.clan_data["players"][str(target_id)]["clan"]
        clan = self.clan_data["clans"][clan_name]

        clan["members"].remove(target_id)
        if target_id in clan["mods"]:
            clan["mods"].remove(target_id)
        if target_id in clan["coleaders"]:
            clan["coleaders"].remove(target_id)
        
        del self.clan_data["players"][str(target_id)]
        self.save_data()
        
        return True, f"Force kicked {target_name} from {clan_name}"
    
    def force_join(self, target_name: str, clan_name: str):
        """Staff command: Force join a player to a clan"""
        target_id = self.find_player_id_by_name(target_name)
        if not target_id:
            return False, "Player not found"
        
        if clan_name not in self.clan_data["clans"]:
            return False, "Clan not found"
        
        if str(target_id) in self.clan_data["players"]:
            old_clan_name = self.clan_data["players"][str(target_id)]["clan"]
            old_clan = self.clan_data["clans"][old_clan_name]
            old_clan["members"].remove(target_id)
            if target_id in old_clan["mods"]:
                old_clan["mods"].remove(target_id)
            if target_id in old_clan["coleaders"]:
                old_clan["coleaders"].remove(target_id)
        
        # Add to new clan
        clan = self.clan_data["clans"][clan_name]
        clan["members"].append(target_id)
        
        self.clan_data["players"][str(target_id)] = {
            "clan": clan_name,
            "role": "Member"
        }
        
        self.save_data()
        return True, f"Force joined {target_name} to {clan_name}"
    
    def delete_clan(self, clan_name: str):
        """Staff command: Delete a clan"""
        if clan_name not in self.clan_data["clans"]:
            return False, "Clan not found"
        
        # Remove all players from this clan
        clan_members = self.clan_data["clans"][clan_name]["members"].copy()
        for member_id in clan_members:
            if str(member_id) in self.clan_data["players"]:
                del self.clan_data["players"][str(member_id)]
        
        # Remove clan
        del self.clan_data["clans"][clan_name]
        self.save_data()
        
        return True, f"Clan '{clan_name}' has been deleted"
    
    def find_player_id_by_name(self, name: str) -> int:
        """Mock function to find player ID by name"""
        return hash(name) % 1000000

class ClanBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.clan_manager = ClanManager()
    

    clan_group = app_commands.Group(name="clan", description="Clan management commands")
    
    @clan_group.command(name="create", description="Create a new clan")
    @app_commands.describe(name="Name of the clan to create")
    async def create_clan(self, interaction: discord.Interaction, name: str):
        """Create a new clan"""
        user_id = interaction.user.id
        
        # Check if user is already in a clan
        if self.clan_manager.get_player_clan(user_id):
            await interaction.response.send_message("You are already in a clan!", ephemeral=True)
            return
        
        success, message = self.clan_manager.create_clan(user_id, name)
        await interaction.response.send_message(message, ephemeral=True)
    
    @clan_group.command(name="kick", description="Kick a member from your clan")
    @app_commands.describe(player_name="Name of the player to kick")
    async def kick_member(self, interaction: discord.Interaction, player_name: str):
        """Kick a member from the clan"""
        user_id = interaction.user.id
        clan_name = self.clan_manager.get_player_clan(user_id)
        
        if not clan_name:
            await interaction.response.send_message("You are not in a clan!", ephemeral=True)
            return
        
        success, message = self.clan_manager.kick_member(user_id, player_name, clan_name)
        await interaction.response.send_message(message, ephemeral=True)
    
    @clan_group.command(name="invite", description="Invite a player to your clan")
    @app_commands.describe(player_name="Name of the player to invite")
    async def invite_member(self, interaction: discord.Interaction, player_name: str):
        """Invite a player to the clan"""
        user_id = interaction.user.id
        clan_name = self.clan_manager.get_player_clan(user_id)
        
        if not clan_name:
            await interaction.response.send_message("You are not in a clan!", ephemeral=True)
            return
        
        success, message = self.clan_manager.invite_member(user_id, player_name, clan_name)
        await interaction.response.send_message(message, ephemeral=True)
    
    @clan_group.command(name="disband", description="Disband your clan")
    async def disband_clan(self, interaction: discord.Interaction):
        """Disband your clan"""
        user_id = interaction.user.id
        clan_name = self.clan_manager.get_player_clan(user_id)
        
        if not clan_name:
            await interaction.response.send_message("You are not in a clan!", ephemeral=True)
            return
        
        success, message = self.clan_manager.disband_clan(user_id, clan_name)
        await interaction.response.send_message(message, ephemeral=True)
    
    @clan_group.command(name="promote", description="Promote a clan member")
    @app_commands.describe(
        player_name="Name of the player to promote",
        role="Role to promote to"
    )
    @app_commands.choices(role=[
        app_commands.Choice(name="Mod", value="Mod"),
        app_commands.Choice(name="Co-Leader", value="Co-Leader")
    ])
    async def promote_member(self, interaction: discord.Interaction, player_name: str, role: str):
        """Promote a clan member"""
        user_id = interaction.user.id
        clan_name = self.clan_manager.get_player_clan(user_id)
        
        if not clan_name:
            await interaction.response.send_message("You are not in a clan!", ephemeral=True)
            return
        
        success, message = self.clan_manager.promote_member(user_id, player_name, clan_name, role)
        await interaction.response.send_message(message, ephemeral=True)
    
    @clan_group.command(name="demote", description="Demote a clan member")
    @app_commands.describe(player_name="Name of the player to demote")
    async def demote_member(self, interaction: discord.Interaction, player_name: str):
        """Demote a clan member"""
        user_id = interaction.user.id
        clan_name = self.clan_manager.get_player_clan(user_id)
        
        if not clan_name:
            await interaction.response.send_message("You are not in a clan!", ephemeral=True)
            return
        
        success, message = self.clan_manager.demote_member(user_id, player_name, clan_name)
        await interaction.response.send_message(message, ephemeral=True)
    

    sclan_group = app_commands.Group(name="sclan", description="Staff clan management commands")
    
    @sclan_group.command(name="forcekick", description="Force kick a player from any clan")
    @app_commands.describe(player_name="Name of the player to force kick")
    @app_commands.default_permissions(administrator=True)
    async def force_kick(self, interaction: discord.Interaction, player_name: str):
        """Staff command: Force kick a player from any clan"""
        success, message = self.clan_manager.force_kick(player_name)
        await interaction.response.send_message(message, ephemeral=True)
    
    @sclan_group.command(name="forcejoin", description="Force join a player to a clan")
    @app_commands.describe(
        player_name="Name of the player to force join",
        clan_name="Name of the clan to join"
    )
    @app_commands.default_permissions(administrator=True)
    async def force_join(self, interaction: discord.Interaction, player_name: str, clan_name: str):
        """Staff command: Force join a player to a clan"""
        success, message = self.clan_manager.force_join(player_name, clan_name)
        await interaction.response.send_message(message, ephemeral=True)
    
    @sclan_group.command(name="delete", description="Delete a clan")
    @app_commands.describe(clan_name="Name of the clan to delete")
    @app_commands.default_permissions(administrator=True)
    async def delete_clan(self, interaction: discord.Interaction, clan_name: str):
        """Staff command: Delete a clan"""
        success, message = self.clan_manager.delete_clan(clan_name)
        await interaction.response.send_message(message, ephemeral=True)

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
    
    async def setup_hook(self):
        await self.add_cog(ClanBot(self))
        await self.tree.sync()
        print("Slash commands synced!")


if __name__ == "__main__":
    bot = Bot()
    

    BOT_TOKEN = "Not Leaking It"
    
    bot.run(BOT_TOKEN)

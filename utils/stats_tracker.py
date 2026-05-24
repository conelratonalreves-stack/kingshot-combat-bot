"""Statistics tracking for bot usage."""

import json
import os
from datetime import datetime
from typing import Dict, Set
from pathlib import Path


class StatsTracker:
    """Track bot usage statistics."""
    
    def __init__(self, stats_file: str = "data/bot_stats.json"):
        self.stats_file = Path(stats_file)
        self.stats_file.parent.mkdir(exist_ok=True)
        self.stats = self._load_stats()
    
    def _load_stats(self) -> dict:
        """Load statistics from file."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading stats: {e}")
        
        return {
            "total_commands": 0,
            "users": {},  # user_id: {name, first_seen, last_seen, command_count}
            "guilds": {},  # guild_id: {name, first_seen, last_seen, command_count}
            "commands": {},  # command_name: count
            "started_at": datetime.now().isoformat()
        }
    
    def _save_stats(self):
        """Save statistics to file."""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving stats: {e}")
    
    def track_command(self, command_name: str, user_id: int, user_name: str, 
                     guild_id: int = None, guild_name: str = None):
        """Track a command usage."""
        now = datetime.now().isoformat()
        
        # Total commands
        self.stats["total_commands"] += 1
        
        # Track user
        user_id_str = str(user_id)
        if user_id_str not in self.stats["users"]:
            self.stats["users"][user_id_str] = {
                "name": user_name,
                "first_seen": now,
                "last_seen": now,
                "command_count": 0
            }
        
        self.stats["users"][user_id_str]["name"] = user_name  # Update name
        self.stats["users"][user_id_str]["last_seen"] = now
        self.stats["users"][user_id_str]["command_count"] += 1
        
        # Track guild
        if guild_id:
            guild_id_str = str(guild_id)
            if guild_id_str not in self.stats["guilds"]:
                self.stats["guilds"][guild_id_str] = {
                    "name": guild_name or "Unknown",
                    "first_seen": now,
                    "last_seen": now,
                    "command_count": 0
                }
            
            self.stats["guilds"][guild_id_str]["name"] = guild_name or "Unknown"
            self.stats["guilds"][guild_id_str]["last_seen"] = now
            self.stats["guilds"][guild_id_str]["command_count"] += 1
        
        # Track command type
        if command_name not in self.stats["commands"]:
            self.stats["commands"][command_name] = 0
        self.stats["commands"][command_name] += 1
        
        self._save_stats()
    
    def get_stats_summary(self) -> dict:
        """Get a summary of statistics."""
        return {
            "total_commands": self.stats["total_commands"],
            "total_users": len(self.stats["users"]),
            "total_guilds": len(self.stats["guilds"]),
            "commands": self.stats["commands"],
            "started_at": self.stats.get("started_at", "Unknown")
        }
    
    def get_top_users(self, limit: int = 10) -> list:
        """Get top users by command count."""
        users = [
            {
                "id": user_id,
                "name": data["name"],
                "command_count": data["command_count"],
                "last_seen": data["last_seen"]
            }
            for user_id, data in self.stats["users"].items()
        ]
        return sorted(users, key=lambda x: x["command_count"], reverse=True)[:limit]
    
    def get_top_guilds(self, limit: int = 10) -> list:
        """Get top guilds by command count."""
        guilds = [
            {
                "id": guild_id,
                "name": data["name"],
                "command_count": data["command_count"],
                "last_seen": data["last_seen"]
            }
            for guild_id, data in self.stats["guilds"].items()
        ]
        return sorted(guilds, key=lambda x: x["command_count"], reverse=True)[:limit]
    
    def get_guild_list(self) -> list:
        """Get list of all guilds."""
        return [
            {
                "id": guild_id,
                "name": data["name"],
                "first_seen": data["first_seen"],
                "last_seen": data["last_seen"],
                "command_count": data["command_count"]
            }
            for guild_id, data in self.stats["guilds"].items()
        ]


# Global stats tracker instance
_tracker = None

def get_tracker() -> StatsTracker:
    """Get or create the global stats tracker."""
    global _tracker
    if _tracker is None:
        _tracker = StatsTracker()
    return _tracker

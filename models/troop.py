"""Troop data models for Kingshot combat calculator."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TroopStats:
    """Statistics for a specific troop type."""
    
    attack: float
    lethality: float
    defense: float
    health: float
    count: int
    troop_type: str  # "infantry", "cavalry", or "archers"
    
    def __post_init__(self):
        if self.count < 0:
            raise ValueError("Troop count cannot be negative")
        if not self.troop_type in ["infantry", "cavalry", "archers"]:
            raise ValueError(f"Invalid troop type: {self.troop_type}")
    
    def get_damage_multiplier(self):
        """Get base damage multiplier from troop count."""
        if self.count == 0:
            return 0
        return (self.count ** 0.5) * (self.attack * self.lethality) / (self.defense * self.health)


@dataclass
class TroopComposition:
    """Complete troop composition for a player or enemy."""
    
    infantry: TroopStats
    cavalry: TroopStats
    archers: TroopStats
    
    @property
    def total_troops(self) -> int:
        """Get total number of troops."""
        return self.infantry.count + self.cavalry.count + self.archers.count
    
    @property
    def infantry_ratio(self) -> float:
        """Get infantry percentage of total troops."""
        if self.total_troops == 0:
            return 0
        return self.infantry.count / self.total_troops
    
    @property
    def cavalry_ratio(self) -> float:
        """Get cavalry percentage of total troops."""
        if self.total_troops == 0:
            return 0
        return self.cavalry.count / self.total_troops
    
    @property
    def archers_ratio(self) -> float:
        """Get archers percentage of total troops."""
        if self.total_troops == 0:
            return 0
        return self.archers.count / self.total_troops
    
    def get_composition_string(self) -> str:
        """Get formatted composition string."""
        inf_pct = self.infantry_ratio * 100
        cav_pct = self.cavalry_ratio * 100
        arc_pct = self.archers_ratio * 100
        return f"Infantry: {inf_pct:.1f}% | Cavalry: {cav_pct:.1f}% | Archers: {arc_pct:.1f}%"

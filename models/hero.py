"""Hero data models for Kingshot combat calculator."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class HeroStats:
    """Statistics for a hero."""
    
    name: str
    attack: float
    lethality: float
    defense: float
    health: float
    troop_type: str  # "infantry", "cavalry", or "archers"
    
    def __post_init__(self):
        if not self.troop_type in ["infantry", "cavalry", "archers"]:
            raise ValueError(f"Invalid troop type: {self.troop_type}")


@dataclass
class JoinerHero:
    """Hero joining a rally with effect."""
    
    name: str
    effect_ops: List[int] = field(default_factory=list)
    damage_up: float = 0.0
    defense_up: float = 0.0
    opp_damage_down: float = 0.0
    hero_type: str = "damage"  # "damage", "defense", "enemy_damage_reduction"


@dataclass
class BattleHeroes:
    """Heroes participating in a battle."""
    
    main_heroes: List[HeroStats] = field(default_factory=list)  # 3 heroes max
    joiner_heroes: List[JoinerHero] = field(default_factory=list)  # 0-4 heroes
    city_buffs: dict = field(default_factory=dict)
    pet_skills: dict = field(default_factory=dict)
    _damage_boost: float = 1.0  # Override for manual SkillMod
    
    def get_total_damage_boost(self) -> float:
        """Calculate total damage boost from joiners."""
        # If manual boost set, use that
        if self._damage_boost != 1.0:
            return self._damage_boost
        if not self.joiner_heroes:
            return 1.0
        
        # Group by effect_op and sum bonuses
        effect_groups = {}
        for joiner in self.joiner_heroes:
            for effect_op in joiner.effect_ops:
                if effect_op not in effect_groups:
                    effect_groups[effect_op] = 0
                effect_groups[effect_op] += joiner.damage_up
        
        # Multiply all effect groups together
        multiplier = 1.0
        for effect_op, bonus in effect_groups.items():
            multiplier *= (1.0 + bonus)
        
        return multiplier
    
    def get_total_defense_boost(self) -> float:
        """Calculate total defense boost from joiners."""
        if not self.joiner_heroes:
            return 1.0
        
        # Group by effect_op and sum bonuses
        effect_groups = {}
        for joiner in self.joiner_heroes:
            for effect_op in joiner.effect_ops:
                if effect_op not in effect_groups:
                    effect_groups[effect_op] = 0
                effect_groups[effect_op] += joiner.defense_up
        
        # Multiply all effect groups together
        multiplier = 1.0
        for effect_op, bonus in effect_groups.items():
            multiplier *= (1.0 + bonus)
        
        return multiplier

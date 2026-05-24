"""Battle calculation and simulation models."""

from dataclasses import dataclass, field
from typing import Tuple, Dict, List, Optional
import math
from models.troop import TroopComposition, TroopStats
from models.hero import BattleHeroes


@dataclass
class BattleResult:
    """Result of a battle simulation."""
    
    attacker_wins: bool
    damage_per_turn_attacker: float
    damage_per_turn_defender: float
    turns_to_win_attacker: int
    turns_to_win_defender: int
    attacker_casualties: Dict[str, int]
    defender_casualties: Dict[str, int]
    detailed_report: str


class BattleCalculator:
    """Kingshot battle damage calculator."""
    
    @staticmethod
    def calculate_skill_mod(
        damage_up: float = 0.0,
        opp_defense_down: float = 0.0,
        opp_damage_down: float = 0.0,
        defense_up: float = 0.0
    ) -> float:
        """Calculate SkillMod for attacker or defender.
        
        SkillMod = (DamageUp × OppDefenseDown) / (OppDamageDown × DefenseUp)
        """
        numerator = (1.0 + damage_up) * (1.0 + opp_defense_down)
        denominator = (1.0 + opp_damage_down) * (1.0 + defense_up)
        
        if denominator == 0:
            return numerator
        return numerator / denominator
    
    @staticmethod
    def calculate_kills_per_troop_type(
        attacker_troops: TroopStats,
        defender_troops: TroopStats,
        attacker_skill_mod: float = 1.0
    ) -> float:
        """Calculate kills of a specific troop type.
        
        Formula: Damage = √Troops × ((100 + Attack%) × (100 + Lethality%)) 
                         / ((100 + Defense%) × (100 + Health%)) × SkillMod
        
        Percentages are bonuses: +543.5% becomes 1 + 5.435 = 6.435 multiplier
        """
        if attacker_troops.count == 0:
            return 0.0
        
        sqrt_troops = math.sqrt(attacker_troops.count)
        
        # Convert percentage bonuses to multipliers
        # +543.5% Attack means: (100 + 543.5) / 100 = 6.435
        attack_mult = (100.0 + attacker_troops.attack) / 100.0
        lethality_mult = (100.0 + attacker_troops.lethality) / 100.0
        
        # Enemy defenses reduce damage
        defense_mult = (100.0 + defender_troops.defense) / 100.0
        health_mult = (100.0 + defender_troops.health) / 100.0
        
        numerator = sqrt_troops * attack_mult * lethality_mult
        denominator = defense_mult * health_mult
        
        if denominator == 0:
            return 0.0
        
        kills = (numerator / denominator) * attacker_skill_mod
        return max(0.0, kills)
    

    @staticmethod
    def simulate_battle(
        attacker: TroopComposition,
        attacker_heroes: BattleHeroes,
        defender: TroopComposition,
        defender_heroes: BattleHeroes,
        max_turns: int = 100
    ) -> BattleResult:
        """Simulate a complete battle between two armies.
        
        Attack order: Infantry → Cavalry → Archers
        """
        # Copy initial troops
        attacker_inf = attacker.infantry.count
        attacker_cav = attacker.cavalry.count
        attacker_arc = attacker.archers.count
        
        defender_inf = defender.infantry.count
        defender_cav = defender.cavalry.count
        defender_arc = defender.archers.count
        
        attacker_initial = {
            "infantry": attacker_inf,
            "cavalry": attacker_cav,
            "archers": attacker_arc
        }
        
        defender_initial = {
            "infantry": defender_inf,
            "cavalry": defender_cav,
            "archers": defender_arc
        }
        
        # Calculate skill mods
        attacker_skill_mod = attacker_heroes.get_total_damage_boost()
        defender_skill_mod = defender_heroes.get_total_damage_boost()
        
        # Simulate turns
        for turn in range(max_turns):
            # Attacker attacks
            # Infantry attacks first
            if attacker_inf > 0 and defender_inf > 0:
                kills = BattleCalculator.calculate_kills_per_troop_type(
                    TroopStats(
                        attack=attacker.infantry.attack,
                        lethality=attacker.infantry.lethality,
                        defense=attacker.infantry.defense,
                        health=attacker.infantry.health,
                        count=attacker_inf,
                        troop_type="infantry"
                    ),
                    TroopStats(
                        attack=defender.infantry.attack,
                        lethality=defender.infantry.lethality,
                        defense=defender.infantry.defense,
                        health=defender.infantry.health,
                        count=defender_inf,
                        troop_type="infantry"
                    ),
                    attacker_skill_mod
                )
                defender_inf = max(0, defender_inf - int(kills))
            
            # Cavalry attacks
            if attacker_cav > 0 and defender_cav > 0:
                kills = BattleCalculator.calculate_kills_per_troop_type(
                    TroopStats(
                        attack=attacker.cavalry.attack,
                        lethality=attacker.cavalry.lethality,
                        defense=attacker.cavalry.defense,
                        health=attacker.cavalry.health,
                        count=attacker_cav,
                        troop_type="cavalry"
                    ),
                    TroopStats(
                        attack=defender.cavalry.attack,
                        lethality=defender.cavalry.lethality,
                        defense=defender.cavalry.defense,
                        health=defender.cavalry.health,
                        count=defender_cav,
                        troop_type="cavalry"
                    ),
                    attacker_skill_mod
                )
                defender_cav = max(0, defender_cav - int(kills))
            
            # Archers attack
            if attacker_arc > 0 and defender_arc > 0:
                kills = BattleCalculator.calculate_kills_per_troop_type(
                    TroopStats(
                        attack=attacker.archers.attack,
                        lethality=attacker.archers.lethality,
                        defense=attacker.archers.defense,
                        health=attacker.archers.health,
                        count=attacker_arc,
                        troop_type="archers"
                    ),
                    TroopStats(
                        attack=defender.archers.attack,
                        lethality=defender.archers.lethality,
                        defense=defender.archers.defense,
                        health=defender.archers.health,
                        count=defender_arc,
                        troop_type="archers"
                    ),
                    attacker_skill_mod
                )
                defender_arc = max(0, defender_arc - int(kills))
            
            # Check if defender is eliminated
            if defender_inf == 0 and defender_cav == 0 and defender_arc == 0:
                attacker_casualties = {
                    "infantry": attacker_initial["infantry"] - attacker_inf,
                    "cavalry": attacker_initial["cavalry"] - attacker_cav,
                    "archers": attacker_initial["archers"] - attacker_arc
                }
                defender_casualties = defender_initial.copy()
                
                return BattleResult(
                    attacker_wins=True,
                    damage_per_turn_attacker=0,
                    damage_per_turn_defender=0,
                    turns_to_win_attacker=turn + 1,
                    turns_to_win_defender=-1,
                    attacker_casualties=attacker_casualties,
                    defender_casualties=defender_casualties,
                    detailed_report=f"Attacker wins in {turn + 1} turns!"
                )
            
            # Defender attacks
            if defender_inf > 0 and attacker_inf > 0:
                kills = BattleCalculator.calculate_kills_per_troop_type(
                    TroopStats(
                        attack=defender.infantry.attack,
                        lethality=defender.infantry.lethality,
                        defense=defender.infantry.defense,
                        health=defender.infantry.health,
                        count=defender_inf,
                        troop_type="infantry"
                    ),
                    TroopStats(
                        attack=attacker.infantry.attack,
                        lethality=attacker.infantry.lethality,
                        defense=attacker.infantry.defense,
                        health=attacker.infantry.health,
                        count=attacker_inf,
                        troop_type="infantry"
                    ),
                    defender_skill_mod
                )
                attacker_inf = max(0, attacker_inf - int(kills))
            
            # Cavalry attacks
            if defender_cav > 0 and attacker_cav > 0:
                kills = BattleCalculator.calculate_kills_per_troop_type(
                    TroopStats(
                        attack=defender.cavalry.attack,
                        lethality=defender.cavalry.lethality,
                        defense=defender.cavalry.defense,
                        health=defender.cavalry.health,
                        count=defender_cav,
                        troop_type="cavalry"
                    ),
                    TroopStats(
                        attack=attacker.cavalry.attack,
                        lethality=attacker.cavalry.lethality,
                        defense=attacker.cavalry.defense,
                        health=attacker.cavalry.health,
                        count=attacker_cav,
                        troop_type="cavalry"
                    ),
                    defender_skill_mod
                )
                attacker_cav = max(0, attacker_cav - int(kills))
            
            # Archers attack
            if defender_arc > 0 and attacker_arc > 0:
                kills = BattleCalculator.calculate_kills_per_troop_type(
                    TroopStats(
                        attack=defender.archers.attack,
                        lethality=defender.archers.lethality,
                        defense=defender.archers.defense,
                        health=defender.archers.health,
                        count=defender_arc,
                        troop_type="archers"
                    ),
                    TroopStats(
                        attack=attacker.archers.attack,
                        lethality=attacker.archers.lethality,
                        defense=attacker.archers.defense,
                        health=attacker.archers.health,
                        count=attacker_arc,
                        troop_type="archers"
                    ),
                    defender_skill_mod
                )
                attacker_arc = max(0, attacker_arc - int(kills))
            
            # Check if attacker is eliminated
            if attacker_inf == 0 and attacker_cav == 0 and attacker_arc == 0:
                attacker_casualties = attacker_initial.copy()
                defender_casualties = {
                    "infantry": defender_initial["infantry"] - defender_inf,
                    "cavalry": defender_initial["cavalry"] - defender_cav,
                    "archers": defender_initial["archers"] - defender_arc
                }
                
                return BattleResult(
                    attacker_wins=False,
                    damage_per_turn_attacker=0,
                    damage_per_turn_defender=0,
                    turns_to_win_attacker=-1,
                    turns_to_win_defender=turn + 1,
                    attacker_casualties=attacker_casualties,
                    defender_casualties=defender_casualties,
                    detailed_report=f"Defender wins in {turn + 1} turns!"
                )
        
        # If max turns reached, return stalemate
        attacker_casualties = {
            "infantry": attacker_initial["infantry"] - attacker_inf,
            "cavalry": attacker_initial["cavalry"] - attacker_cav,
            "archers": attacker_initial["archers"] - attacker_arc
        }
        defender_casualties = {
            "infantry": defender_initial["infantry"] - defender_inf,
            "cavalry": defender_initial["cavalry"] - defender_cav,
            "archers": defender_initial["archers"] - defender_arc
        }
        
        return BattleResult(
            attacker_wins=False,
            damage_per_turn_attacker=0,
            damage_per_turn_defender=0,
            turns_to_win_attacker=-1,
            turns_to_win_defender=-1,
            attacker_casualties=attacker_casualties,
            defender_casualties=defender_casualties,
            detailed_report=f"Stalemate after {max_turns} turns"
        )

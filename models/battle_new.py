"""Battle calculation and simulation models with row-based combat."""

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
    """Kingshot battle damage calculator with row-based combat system."""
    
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
    def get_counter_bonus(attacker_type: str, defender_type: str) -> float:
        """Calculate counter bonus: Infantry > Cavalry > Archers > Infantry."""
        counters = {
            ('infantry', 'cavalry'): 1.25,
            ('cavalry', 'archers'): 1.25,
            ('archers', 'infantry'): 1.25
        }
        return counters.get((attacker_type, defender_type), 1.0)

    @staticmethod
    def get_front_line(inf_count: int, cav_count: int, arc_count: int) -> Tuple[Optional[str], int]:
        """Get the frontmost alive troop type and count (Infantry > Cavalry > Archers)."""
        if inf_count > 0:
            return ('infantry', inf_count)
        elif cav_count > 0:
            return ('cavalry', cav_count)
        elif arc_count > 0:
            return ('archers', arc_count)
        else:
            return (None, 0)

    @staticmethod
    def simulate_battle(
        attacker: TroopComposition,
        attacker_heroes: BattleHeroes,
        defender: TroopComposition,
        defender_heroes: BattleHeroes,
        max_turns: int = 100
    ) -> BattleResult:
        """Simulate a complete battle between two armies using row-based combat.
        
        All troops attack the frontmost enemy row (Infantry > Cavalry > Archers).
        Counter bonuses apply: Inf > Cav > Arc > Inf (+25% damage).
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
            # Determine front lines
            defender_front_type, defender_front_count = BattleCalculator.get_front_line(
                defender_inf, defender_cav, defender_arc
            )
            attacker_front_type, attacker_front_count = BattleCalculator.get_front_line(
                attacker_inf, attacker_cav, attacker_arc
            )
            
            # Check if battle is over
            if defender_front_type is None:
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
            
            if attacker_front_type is None:
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
            
            # Get defender front line stats
            if defender_front_type == 'infantry':
                defender_front_stats = defender.infantry
            elif defender_front_type == 'cavalry':
                defender_front_stats = defender.cavalry
            else:
                defender_front_stats = defender.archers
            
            # ATTACKER TURN: All attacker troops attack defender's front line
            total_kills_on_defender = 0
            
            # Attacker Infantry attacks defender front
            if attacker_inf > 0:
                counter_bonus = BattleCalculator.get_counter_bonus('infantry', defender_front_type)
                kills = BattleCalculator.calculate_kills_per_troop_type(
                    TroopStats(
                        attack=attacker.infantry.attack,
                        lethality=attacker.infantry.lethality,
                        defense=attacker.infantry.defense,
                        health=attacker.infantry.health,
                        count=attacker_inf,
                        troop_type='infantry'
                    ),
                    TroopStats(
                        attack=defender_front_stats.attack,
                        lethality=defender_front_stats.lethality,
                        defense=defender_front_stats.defense,
                        health=defender_front_stats.health,
                        count=defender_front_count,
                        troop_type=defender_front_type
                    ),
                    attacker_skill_mod
                ) * counter_bonus
                total_kills_on_defender += int(kills)
            
            # Attacker Cavalry attacks defender front
            if attacker_cav > 0:
                counter_bonus = BattleCalculator.get_counter_bonus('cavalry', defender_front_type)
                kills = BattleCalculator.calculate_kills_per_troop_type(
                    TroopStats(
                        attack=attacker.cavalry.attack,
                        lethality=attacker.cavalry.lethality,
                        defense=attacker.cavalry.defense,
                        health=attacker.cavalry.health,
                        count=attacker_cav,
                        troop_type='cavalry'
                    ),
                    TroopStats(
                        attack=defender_front_stats.attack,
                        lethality=defender_front_stats.lethality,
                        defense=defender_front_stats.defense,
                        health=defender_front_stats.health,
                        count=defender_front_count,
                        troop_type=defender_front_type
                    ),
                    attacker_skill_mod
                ) * counter_bonus
                total_kills_on_defender += int(kills)
            
            # Attacker Archers attack defender front
            if attacker_arc > 0:
                counter_bonus = BattleCalculator.get_counter_bonus('archers', defender_front_type)
                kills = BattleCalculator.calculate_kills_per_troop_type(
                    TroopStats(
                        attack=attacker.archers.attack,
                        lethality=attacker.archers.lethality,
                        defense=attacker.archers.defense,
                        health=attacker.archers.health,
                        count=attacker_arc,
                        troop_type='archers'
                    ),
                    TroopStats(
                        attack=defender_front_stats.attack,
                        lethality=defender_front_stats.lethality,
                        defense=defender_front_stats.defense,
                        health=defender_front_stats.health,
                        count=defender_front_count,
                        troop_type=defender_front_type
                    ),
                    attacker_skill_mod
                ) * counter_bonus
                total_kills_on_defender += int(kills)
            
            # Apply damage to defender's front line
            if defender_front_type == 'infantry':
                defender_inf = max(0, defender_inf - total_kills_on_defender)
            elif defender_front_type == 'cavalry':
                defender_cav = max(0, defender_cav - total_kills_on_defender)
            else:
                defender_arc = max(0, defender_arc - total_kills_on_defender)
            
            # Get attacker front line stats
            if attacker_front_type == 'infantry':
                attacker_front_stats = attacker.infantry
            elif attacker_front_type == 'cavalry':
                attacker_front_stats = attacker.cavalry
            else:
                attacker_front_stats = attacker.archers
            
            # DEFENDER TURN: All defender troops attack attacker's front line
            total_kills_on_attacker = 0
            
            # Defender Infantry attacks attacker front
            if defender_inf > 0:
                counter_bonus = BattleCalculator.get_counter_bonus('infantry', attacker_front_type)
                kills = BattleCalculator.calculate_kills_per_troop_type(
                    TroopStats(
                        attack=defender.infantry.attack,
                        lethality=defender.infantry.lethality,
                        defense=defender.infantry.defense,
                        health=defender.infantry.health,
                        count=defender_inf,
                        troop_type='infantry'
                    ),
                    TroopStats(
                        attack=attacker_front_stats.attack,
                        lethality=attacker_front_stats.lethality,
                        defense=attacker_front_stats.defense,
                        health=attacker_front_stats.health,
                        count=attacker_front_count,
                        troop_type=attacker_front_type
                    ),
                    defender_skill_mod
                ) * counter_bonus
                total_kills_on_attacker += int(kills)
            
            # Defender Cavalry attacks attacker front
            if defender_cav > 0:
                counter_bonus = BattleCalculator.get_counter_bonus('cavalry', attacker_front_type)
                kills = BattleCalculator.calculate_kills_per_troop_type(
                    TroopStats(
                        attack=defender.cavalry.attack,
                        lethality=defender.cavalry.lethality,
                        defense=defender.cavalry.defense,
                        health=defender.cavalry.health,
                        count=defender_cav,
                        troop_type='cavalry'
                    ),
                    TroopStats(
                        attack=attacker_front_stats.attack,
                        lethality=attacker_front_stats.lethality,
                        defense=attacker_front_stats.defense,
                        health=attacker_front_stats.health,
                        count=attacker_front_count,
                        troop_type=attacker_front_type
                    ),
                    defender_skill_mod
                ) * counter_bonus
                total_kills_on_attacker += int(kills)
            
            # Defender Archers attack attacker front
            if defender_arc > 0:
                counter_bonus = BattleCalculator.get_counter_bonus('archers', attacker_front_type)
                kills = BattleCalculator.calculate_kills_per_troop_type(
                    TroopStats(
                        attack=defender.archers.attack,
                        lethality=defender.archers.lethality,
                        defense=defender.archers.defense,
                        health=defender.archers.health,
                        count=defender_arc,
                        troop_type='archers'
                    ),
                    TroopStats(
                        attack=attacker_front_stats.attack,
                        lethality=attacker_front_stats.lethality,
                        defense=attacker_front_stats.defense,
                        health=attacker_front_stats.health,
                        count=attacker_front_count,
                        troop_type=attacker_front_type
                    ),
                    defender_skill_mod
                ) * counter_bonus
                total_kills_on_attacker += int(kills)
            
            # Apply damage to attacker's front line
            if attacker_front_type == 'infantry':
                attacker_inf = max(0, attacker_inf - total_kills_on_attacker)
            elif attacker_front_type == 'cavalry':
                attacker_cav = max(0, attacker_cav - total_kills_on_attacker)
            else:
                attacker_arc = max(0, attacker_arc - total_kills_on_attacker)
        
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

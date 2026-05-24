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
        attacker_skill_mod: float = 1.0,
        counter_bonus: float = 1.0,
        defense_bonus: float = 1.0,
        special_multiplier: float = 1.0
    ) -> float:
        """Calculate kills of a specific troop type.
        
        Formula: Damage = √Troops × ((100 + Attack%) × (100 + Lethality%)) 
                         / ((100 + Defense%) × (100 + Health%)) × SkillMod × CounterBonus / DefenseBonus × SpecialMultiplier
        
        Percentages are bonuses: +543.5% becomes 1 + 5.435 = 6.435 multiplier
        
        Args:
            counter_bonus: Type advantage bonus (1.10 for counter matchups)
            defense_bonus: Defender's defensive bonus (1.10 for Infantry vs Cavalry)
            special_multiplier: Special abilities (1.10 for Archer double attack, etc.)
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
        
        # Apply all multipliers
        kills = (numerator / denominator) * attacker_skill_mod * counter_bonus * special_multiplier / defense_bonus
        return max(0.0, kills)
    
    @staticmethod
    def get_counter_bonus(attacker_type: str, defender_type: str) -> float:
        """Calculate counter bonus damage: Infantry > Cavalry > Archers > Infantry.
        
        Official bonuses from Kingshot guides:
        - Infantry: +10% damage vs Cavalry
        - Cavalry: +10% damage vs Archers  
        - Archers: +10% damage vs Infantry
        """
        counters = {
            ('infantry', 'cavalry'): 1.10,   # Infantry deals +10% to Cavalry
            ('cavalry', 'archers'): 1.10,    # Cavalry deals +10% to Archers
            ('archers', 'infantry'): 1.10    # Archers deal +10% to Infantry
        }
        return counters.get((attacker_type, defender_type), 1.0)
    
    @staticmethod
    def get_counter_defense_bonus(defender_type: str, attacker_type: str) -> float:
        """Calculate counter defense bonus.
        
        Official bonuses:
        - Infantry: +10% defense vs Cavalry attacks
        """
        if defender_type == 'infantry' and attacker_type == 'cavalry':
            return 1.10  # Infantry takes 10% less damage from Cavalry
        return 1.0

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
        max_turns: int = 500
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
            
            # Debug first turn only
            if turn == 0:
                print(f"[BATTLE DEBUG] Turn 1:")
                print(f"  Attacker: Inf={attacker_inf} Cav={attacker_cav} Arc={attacker_arc} (Front: {attacker_front_type})")
                print(f"  Defender: Inf={defender_inf} Cav={defender_cav} Arc={defender_arc} (Front: {defender_front_type})")
            
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
                defense_bonus = BattleCalculator.get_counter_defense_bonus(defender_front_type, 'infantry')
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
                    attacker_skill_mod,
                    counter_bonus,
                    defense_bonus,
                    1.0  # No special multiplier for Infantry
                )
                total_kills_on_defender += int(kills)
            
            # Attacker Cavalry attacks defender front
            # 20% chance to ignore Infantry and attack Archers directly (Ambush ability)
            if attacker_cav > 0:
                # Determine actual target (Ambush: 20% chance to skip Infantry and hit Archers)
                actual_target_type = defender_front_type
                actual_target_stats = defender_front_stats
                actual_target_count = defender_front_count
                
                if defender_front_type == 'infantry' and defender_arc > 0:
                    # 20% of cavalry ignores infantry and hits archers
                    # Simplified: apply 20% of damage to archers, 80% to infantry front
                    
                    # 80% attacks infantry front
                    counter_bonus_inf = BattleCalculator.get_counter_bonus('cavalry', 'infantry')
                    defense_bonus_inf = BattleCalculator.get_counter_defense_bonus('infantry', 'cavalry')
                    kills_inf = BattleCalculator.calculate_kills_per_troop_type(
                        TroopStats(
                            attack=attacker.cavalry.attack,
                            lethality=attacker.cavalry.lethality,
                            defense=attacker.cavalry.defense,
                            health=attacker.cavalry.health,
                            count=attacker_cav,
                            troop_type='cavalry'
                        ),
                        TroopStats(
                            attack=defender.infantry.attack,
                            lethality=defender.infantry.lethality,
                            defense=defender.infantry.defense,
                            health=defender.infantry.health,
                            count=defender_inf,
                            troop_type='infantry'
                        ),
                        attacker_skill_mod,
                        counter_bonus_inf,
                        defense_bonus_inf,
                        0.80  # 80% normal attack
                    )
                    
                    # 20% ambushes archers
                    counter_bonus_arc = BattleCalculator.get_counter_bonus('cavalry', 'archers')
                    defense_bonus_arc = BattleCalculator.get_counter_defense_bonus('archers', 'cavalry')
                    kills_arc = BattleCalculator.calculate_kills_per_troop_type(
                        TroopStats(
                            attack=attacker.cavalry.attack,
                            lethality=attacker.cavalry.lethality,
                            defense=attacker.cavalry.defense,
                            health=attacker.cavalry.health,
                            count=attacker_cav,
                            troop_type='cavalry'
                        ),
                        TroopStats(
                            attack=defender.archers.attack,
                            lethality=defender.archers.lethality,
                            defense=defender.archers.defense,
                            health=defender.archers.health,
                            count=defender_arc,
                            troop_type='archers'
                        ),
                        attacker_skill_mod,
                        counter_bonus_arc,
                        defense_bonus_arc,
                        0.20  # 20% ambush
                    )
                    
                    # Apply split damage
                    defender_inf = max(0, defender_inf - int(kills_inf))
                    defender_arc = max(0, defender_arc - int(kills_arc))
                    
                else:
                    # Normal cavalry attack (no ambush possible)
                    counter_bonus = BattleCalculator.get_counter_bonus('cavalry', defender_front_type)
                    defense_bonus = BattleCalculator.get_counter_defense_bonus(defender_front_type, 'cavalry')
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
                            attack=actual_target_stats.attack,
                            lethality=actual_target_stats.lethality,
                            defense=actual_target_stats.defense,
                            health=actual_target_stats.health,
                            count=actual_target_count,
                            troop_type=actual_target_type
                        ),
                        attacker_skill_mod,
                        counter_bonus,
                        defense_bonus,
                        1.0
                    )
                    total_kills_on_defender += int(kills)
            
            # Attacker Archers attack defender front
            # 10% chance to attack twice (Volley ability)
            if attacker_arc > 0:
                counter_bonus = BattleCalculator.get_counter_bonus('archers', defender_front_type)
                defense_bonus = BattleCalculator.get_counter_defense_bonus(defender_front_type, 'archers')
                # Average multiplier: 90% × 1.0 + 10% × 2.0 = 1.10
                special_mult = 1.10
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
                    attacker_skill_mod,
                    counter_bonus,
                    defense_bonus,
                    special_mult  # 10% double attack
                )
                total_kills_on_defender += int(kills)
            
            # Apply damage to defender's front line
            if defender_front_type == 'infantry':
                defender_inf = max(0, defender_inf - total_kills_on_defender)
            elif defender_front_type == 'cavalry':
                defender_cav = max(0, defender_cav - total_kills_on_defender)
            else:
                defender_arc = max(0, defender_arc - total_kills_on_defender)
            
            # Debug first turn damage
            if turn == 0:
                print(f"  Attacker dealt {total_kills_on_defender} kills to defender's {defender_front_type}")
            
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
                defense_bonus = BattleCalculator.get_counter_defense_bonus(attacker_front_type, 'infantry')
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
                    defender_skill_mod,
                    counter_bonus,
                    defense_bonus,
                    1.0
                )
                total_kills_on_attacker += int(kills)
            
            # Defender Cavalry attacks attacker front  
            # 20% chance to ignore Infantry and attack Archers directly (Ambush ability)
            if defender_cav > 0:
                if attacker_front_type == 'infantry' and attacker_arc > 0:
                    # 80% attacks infantry front
                    counter_bonus_inf = BattleCalculator.get_counter_bonus('cavalry', 'infantry')
                    defense_bonus_inf = BattleCalculator.get_counter_defense_bonus('infantry', 'cavalry')
                    kills_inf = BattleCalculator.calculate_kills_per_troop_type(
                        TroopStats(
                            attack=defender.cavalry.attack,
                            lethality=defender.cavalry.lethality,
                            defense=defender.cavalry.defense,
                            health=defender.cavalry.health,
                            count=defender_cav,
                            troop_type='cavalry'
                        ),
                        TroopStats(
                            attack=attacker.infantry.attack,
                            lethality=attacker.infantry.lethality,
                            defense=attacker.infantry.defense,
                            health=attacker.infantry.health,
                            count=attacker_inf,
                            troop_type='infantry'
                        ),
                        defender_skill_mod,
                        counter_bonus_inf,
                        defense_bonus_inf,
                        0.80
                    )
                    
                    # 20% ambushes archers
                    counter_bonus_arc = BattleCalculator.get_counter_bonus('cavalry', 'archers')
                    defense_bonus_arc = BattleCalculator.get_counter_defense_bonus('archers', 'cavalry')
                    kills_arc = BattleCalculator.calculate_kills_per_troop_type(
                        TroopStats(
                            attack=defender.cavalry.attack,
                            lethality=defender.cavalry.lethality,
                            defense=defender.cavalry.defense,
                            health=defender.cavalry.health,
                            count=defender_cav,
                            troop_type='cavalry'
                        ),
                        TroopStats(
                            attack=attacker.archers.attack,
                            lethality=attacker.archers.lethality,
                            defense=attacker.archers.defense,
                            health=attacker.archers.health,
                            count=attacker_arc,
                            troop_type='archers'
                        ),
                        defender_skill_mod,
                        counter_bonus_arc,
                        defense_bonus_arc,
                        0.20
                    )
                    
                    # Apply split damage
                    attacker_inf = max(0, attacker_inf - int(kills_inf))
                    attacker_arc = max(0, attacker_arc - int(kills_arc))
                    
                else:
                    # Normal cavalry attack
                    counter_bonus = BattleCalculator.get_counter_bonus('cavalry', attacker_front_type)
                    defense_bonus = BattleCalculator.get_counter_defense_bonus(attacker_front_type, 'cavalry')
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
                        defender_skill_mod,
                        counter_bonus,
                        defense_bonus,
                        1.0
                    )
                    total_kills_on_attacker += int(kills)
            
            # Defender Archers attack attacker front
            # 10% chance to attack twice (Volley ability)
            if defender_arc > 0:
                counter_bonus = BattleCalculator.get_counter_bonus('archers', attacker_front_type)
                defense_bonus = BattleCalculator.get_counter_defense_bonus(attacker_front_type, 'archers')
                special_mult = 1.10  # 10% double attack average
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
                    defender_skill_mod,
                    counter_bonus,
                    defense_bonus,
                    special_mult
                )
                total_kills_on_attacker += int(kills)
            
            # Apply damage to attacker's front line
            if attacker_front_type == 'infantry':
                attacker_inf = max(0, attacker_inf - total_kills_on_attacker)
            elif attacker_front_type == 'cavalry':
                attacker_cav = max(0, attacker_cav - total_kills_on_attacker)
            else:
                attacker_arc = max(0, attacker_arc - total_kills_on_attacker)
            
            # Debug first turn damage
            if turn == 0:
                print(f"  Defender dealt {total_kills_on_attacker} kills to attacker's {attacker_front_type}")
                print(f"  Net advantage: Attacker {total_kills_on_defender - total_kills_on_attacker:+d} kills/turn")
        
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

"""Battle calculation logic and composition optimizer."""

import json
import os
from typing import Tuple, List
import itertools
from models.troop import TroopComposition, TroopStats
from models.hero import BattleHeroes, HeroStats, JoinerHero
from models.battle import BattleCalculator, BattleResult
from utils.validators import validate_formation


class CompositionOptimizer:
    """Optimize troop composition for maximum damage."""
    
    def __init__(self):
        """Load heroes data."""
        self.heroes_db = {}
        self._load_heroes()
    
    def _load_heroes(self):
        """Load hero data from JSON."""
        try:
            with open('data/heroes.json', 'r') as f:
                self.heroes_db = json.load(f)
        except FileNotFoundError:
            print("Warning: heroes.json not found")
    
    def find_optimal_composition(
        self,
        available_troops: dict,
        enemy_composition: TroopComposition,
        enemy_heroes: BattleHeroes,
        player_heroes: BattleHeroes
    ) -> dict:
        """Find the optimal troop composition to maximize damage.
        
        Args:
            available_troops: dict with 'infantry', 'cavalry', 'archers' counts
            enemy_composition: TroopComposition of enemy
            enemy_heroes: BattleHeroes of enemy
            player_heroes: BattleHeroes of player
        
        Returns:
            dict with optimal composition and damage estimate
        """
        best_composition = None
        best_damage = -1
        all_results = []
        
        # Test different compositions at 5% intervals
        steps = 5  # Test every 5%
        for inf_pct in range(5, 96, steps):
            for cav_pct in range(5, 96 - inf_pct, steps):
                arc_pct = 100 - inf_pct - cav_pct
                
                if arc_pct < 5:
                    continue
                
                # Create composition
                total_troops = sum(available_troops.values())
                composition = TroopComposition(
                    infantry=TroopStats(
                        attack=100,
                        lethality=20,
                        defense=80,
                        health=150,
                        count=int(total_troops * inf_pct / 100),
                        troop_type="infantry"
                    ),
                    cavalry=TroopStats(
                        attack=120,
                        lethality=25,
                        defense=70,
                        health=120,
                        count=int(total_troops * cav_pct / 100),
                        troop_type="cavalry"
                    ),
                    archers=TroopStats(
                        attack=150,
                        lethality=35,
                        defense=50,
                        health=90,
                        count=int(total_troops * arc_pct / 100),
                        troop_type="archers"
                    )
                )
                
                # Simulate battle
                result = BattleCalculator.simulate_battle(
                    composition,
                    player_heroes,
                    enemy_composition,
                    enemy_heroes
                )
                
                # Track if this is a win
                all_results.append({
                    "infantry_pct": inf_pct,
                    "cavalry_pct": cav_pct,
                    "archers_pct": arc_pct,
                    "win": result.attacker_wins,
                    "turns_to_win": result.turns_to_win_attacker,
                    "casualties": result.attacker_casualties
                })
                
                # Prefer wins, then prefer fewer casualties
                if result.attacker_wins:
                    total_casualties = sum(result.attacker_casualties.values())
                    if total_casualties < best_damage or best_damage == -1:
                        best_composition = {
                            "infantry": inf_pct,
                            "cavalry": cav_pct,
                            "archers": arc_pct
                        }
                        best_damage = total_casualties
        
        return {
            "optimal_composition": best_composition,
            "all_results": all_results,
            "can_win": best_composition is not None
        }
    
    def estimate_battles_needed(
        self,
        player_composition: TroopComposition,
        player_heroes: BattleHeroes,
        enemy_composition: TroopComposition,
        enemy_heroes: BattleHeroes,
        player_troop_recovery: bool = False
    ) -> dict:
        """Estimate how many battles are needed to defeat an enemy.
        
        Args:
            player_composition: Composition to attack with
            player_heroes: Heroes in the attack
            enemy_composition: Enemy composition
            enemy_heroes: Enemy heroes
            player_troop_recovery: Whether player recovers troops between attacks
        
        Returns:
            dict with number of battles needed or win status
        """
        battles_needed = 0
        current_enemy = TroopComposition(
            infantry=TroopStats(
                attack=enemy_composition.infantry.attack,
                lethality=enemy_composition.infantry.lethality,
                defense=enemy_composition.infantry.defense,
                health=enemy_composition.infantry.health,
                count=enemy_composition.infantry.count,
                troop_type="infantry"
            ),
            cavalry=TroopStats(
                attack=enemy_composition.cavalry.attack,
                lethality=enemy_composition.cavalry.lethality,
                defense=enemy_composition.cavalry.defense,
                health=enemy_composition.cavalry.health,
                count=enemy_composition.cavalry.count,
                troop_type="cavalry"
            ),
            archers=TroopStats(
                attack=enemy_composition.archers.attack,
                lethality=enemy_composition.archers.lethality,
                defense=enemy_composition.archers.defense,
                health=enemy_composition.archers.health,
                count=enemy_composition.archers.count,
                troop_type="archers"
            )
        )
        
        max_battles = 100
        
        for battle_num in range(1, max_battles + 1):
            result = BattleCalculator.simulate_battle(
                player_composition,
                player_heroes,
                current_enemy,
                enemy_heroes
            )
            
            if result.attacker_wins:
                return {
                    "can_win": True,
                    "battles_needed": battle_num,
                    "final_result": result
                }
            
            # Reduce enemy troops based on casualities
            current_enemy.infantry.count = max(0, 
                current_enemy.infantry.count - result.defender_casualties["infantry"]
            )
            current_enemy.cavalry.count = max(0,
                current_enemy.cavalry.count - result.defender_casualties["cavalry"]
            )
            current_enemy.archers.count = max(0,
                current_enemy.archers.count - result.defender_casualties["archers"]
            )
            
            # If enemy is defeated
            if (current_enemy.infantry.count == 0 and 
                current_enemy.cavalry.count == 0 and 
                current_enemy.archers.count == 0):
                return {
                    "can_win": True,
                    "battles_needed": battle_num,
                    "final_result": result
                }
        
        return {
            "can_win": False,
            "battles_needed": -1,
            "reason": "Enemy too strong (would need >100 battles)"
        }


async def setup(bot):
    """Setup function for Discord.py extension loading.
    
    This is required by Discord.py but battle_calculator is a utility module,
    not a Cog, so we don't actually add anything.
    """
    pass

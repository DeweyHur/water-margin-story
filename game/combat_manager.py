"""Combat manager — siege battles, field battles (pure game logic, no UI)."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional

from models.army import Army, ArmyStatus, UnitType
from models.hero import Hero
from models.town import Town

if TYPE_CHECKING:
    from models.game_state import GameState


# ──────────────────────────────────────────────────────────────────────────────
# Result / round dataclasses
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class BattleResult:
    winner: str                  # faction id
    attacker_losses: int
    defender_losses: int
    wall_damage: int = 0
    turns_fought: int = 1
    narrative: list[str] = None   # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.narrative is None:
            self.narrative = []


@dataclass
class BattleRoundData:
    """Snapshot of one combat round passed to UI callbacks."""
    round_num: int
    phase: str                      # "bombardment" | "assault" | "field"
    att_troops_before: int
    att_troops_after: int
    att_morale_before: int
    att_morale_after: int
    att_max_troops: int
    def_troops_before: int
    def_troops_after: int
    def_morale_before: int
    def_morale_after: int
    def_max_troops: int
    wall_hp_before: int
    wall_hp_after: int
    max_wall_hp: int
    events: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# CombatManager
# ──────────────────────────────────────────────────────────────────────────────

class CombatManager:
    """Handles army-level battles (pure logic — no UI/printing)."""

    def __init__(self, state: "GameState") -> None:
        self.state = state

    # ------------------------------------------------------------------ siege

    def siege_battle(
        self,
        attacker: Army,
        defender: Army,
        town: Town,
        attacker_general: Optional[Hero] = None,
        defender_general: Optional[Hero] = None,
        on_round: Optional[Callable[["BattleRoundData"], None]] = None,
    ) -> BattleResult:
        """
        Multi-phase siege: bombardment → assault.
        Calls on_round(BattleRoundData) after each phase for UI display/animation.
        """
        narrative: list[str] = []
        total_att_loss = 0
        total_def_loss = 0
        total_wall_dmg = 0
        phase_num = 0

        # ── Phase 1: Bombardment (투석기 포격) ──────────────────────────────
        if attacker.catapults > 0 or attacker.siege_towers > 0:
            phase_num += 1
            att_before = attacker.troops
            def_before = defender.troops
            wall_before = town.wall_hp
            att_mor_before = attacker.morale
            def_mor_before = defender.morale
            events: list[str] = []

            wall_dmg = int(attacker.siege_power * random.uniform(0.6, 1.4) / 10)
            wall_dmg = max(5, min(wall_dmg, town.wall_hp // 2))
            town.wall_hp = max(0, town.wall_hp - wall_dmg)
            total_wall_dmg += wall_dmg

            msg = f"💣 투석기 {attacker.catapults}문 포격! 성벽 -{wall_dmg} HP"
            events.append(msg)
            narrative.append(msg)

            if on_round:
                on_round(BattleRoundData(
                    round_num=phase_num,
                    phase="bombardment",
                    att_troops_before=att_before,
                    att_troops_after=attacker.troops,
                    att_morale_before=att_mor_before,
                    att_morale_after=attacker.morale,
                    att_max_troops=attacker.max_troops,
                    def_troops_before=def_before,
                    def_troops_after=defender.troops,
                    def_morale_before=def_mor_before,
                    def_morale_after=defender.morale,
                    def_max_troops=defender.max_troops,
                    wall_hp_before=wall_before,
                    wall_hp_after=town.wall_hp,
                    max_wall_hp=town.max_wall_hp,
                    events=events,
                ))

        # ── Phase 2: Main Assault (전면 돌격) ─────────────────────────────
        max_rounds = 5
        for rnd in range(1, max_rounds + 1):
            if not attacker.is_active() or not defender.is_active():
                break

            phase_num += 1
            att_before = attacker.troops
            def_before = defender.troops
            wall_before = town.wall_hp
            att_mor_before = attacker.morale
            def_mor_before = defender.morale
            events = []

            wall_bonus = 1.0 + town.wall_integrity() * 0.5
            att_power = attacker.combat_power * random.uniform(0.8, 1.2)
            def_power = defender.combat_power * wall_bonus * random.uniform(0.8, 1.2)

            if attacker_general:
                att_power *= 1.0 + attacker_general.strength * 0.05
            if defender_general:
                def_power *= 1.0 + defender_general.strength * 0.05

            att_loss = max(10, int(def_power * random.uniform(0.05, 0.12)))
            def_loss = max(5, int(att_power * random.uniform(0.04, 0.10)))

            attacker.apply_casualties(att_loss)
            defender.apply_casualties(def_loss)
            attacker.suffer_morale_loss(random.randint(2, 6))
            defender.suffer_morale_loss(random.randint(1, 4))
            total_att_loss += att_loss
            total_def_loss += def_loss

            round_msg = (
                f"공격군 -{att_loss:,}명 (사기 {attacker.morale}) / "
                f"수비군 -{def_loss:,}명 (사기 {defender.morale}) / "
                f"성벽 {town.wall_hp}HP"
            )
            events.append(round_msg)
            narrative.append(round_msg)

            if on_round:
                on_round(BattleRoundData(
                    round_num=rnd,
                    phase="assault",
                    att_troops_before=att_before,
                    att_troops_after=attacker.troops,
                    att_morale_before=att_mor_before,
                    att_morale_after=attacker.morale,
                    att_max_troops=attacker.max_troops,
                    def_troops_before=def_before,
                    def_troops_after=defender.troops,
                    def_morale_before=def_mor_before,
                    def_morale_after=defender.morale,
                    def_max_troops=defender.max_troops,
                    wall_hp_before=wall_before,
                    wall_hp_after=town.wall_hp,
                    max_wall_hp=town.max_wall_hp,
                    events=events,
                ))

        # ── Determine winner ────────────────────────────────────────────────
        att_broken = not attacker.is_active()
        def_broken = not defender.is_active()

        if def_broken and not att_broken:
            winner = attacker.faction_id
            town.controlled_by_faction = attacker.faction_id
            town.garrison_strength = max(1, attacker.troops // 1000)
        elif att_broken:
            winner = defender.faction_id
        else:
            winner = defender.faction_id  # defender holds by default if inconclusive

        return BattleResult(
            winner=winner,
            attacker_losses=total_att_loss,
            defender_losses=total_def_loss,
            wall_damage=total_wall_dmg,
            turns_fought=phase_num,
            narrative=narrative,
        )

    # ------------------------------------------------------------------ field

    def field_battle(
        self,
        attacker: Army,
        defender: Army,
        attacker_general: Optional[Hero] = None,
        defender_general: Optional[Hero] = None,
        allow_flanking: bool = True,
        on_round: Optional[Callable[["BattleRoundData"], None]] = None,
    ) -> BattleResult:
        """
        Open-field battle with flanking manoeuvres and cavalry charges.
        Calls on_round(BattleRoundData) after each round for UI display.
        """
        narrative: list[str] = []
        total_att_loss = 0
        total_def_loss = 0

        for rnd in range(1, 7):
            if not attacker.is_active() or not defender.is_active():
                break

            att_before = attacker.troops
            def_before = defender.troops
            att_mor_before = attacker.morale
            def_mor_before = defender.morale
            events: list[str] = []

            att_power = attacker.combat_power * random.uniform(0.85, 1.15)
            def_power = defender.combat_power * random.uniform(0.85, 1.15)

            if attacker_general:
                att_power *= 1.0 + attacker_general.strength * 0.04 + attacker_general.intelligence * 0.02
            if defender_general:
                def_power *= 1.0 + defender_general.strength * 0.04 + defender_general.intelligence * 0.02

            # Cavalry charge bonus (first round)
            if rnd == 1 and attacker.unit_type == UnitType.CAVALRY:
                att_power *= 1.5
                events.append(f"🐴 {attacker.name} 기병 돌격! 전투력 +50%")
            elif rnd == 1 and defender.unit_type == UnitType.CAVALRY:
                def_power *= 1.5
                events.append(f"🐴 {defender.name} 기병 반격 돌격! 전투력 +50%")

            # Flanking (rounds 2-3 only if attacker is cavalry)
            if allow_flanking and rnd in (2, 3) and attacker.unit_type == UnitType.CAVALRY:
                if random.random() < 0.35:
                    flank_bonus = random.uniform(0.2, 0.5)
                    att_power *= 1.0 + flank_bonus
                    events.append(f"⚡ 측면 기습 성공! 추가 피해 +{int(flank_bonus * 100)}%")

            att_loss = max(5, int(def_power * random.uniform(0.04, 0.10)))
            def_loss = max(5, int(att_power * random.uniform(0.04, 0.10)))

            if defender.unit_type == UnitType.ARCHER and attacker.unit_type == UnitType.CAVALRY:
                att_loss = int(att_loss * 1.3)
                events.append(f"🏹 {defender.name} 궁병이 기병에 집중 사격!")

            attacker.apply_casualties(att_loss)
            defender.apply_casualties(def_loss)
            attacker.suffer_morale_loss(random.randint(1, 5))
            defender.suffer_morale_loss(random.randint(1, 5))
            total_att_loss += att_loss
            total_def_loss += def_loss

            rnd_msg = (
                f"{attacker.name} -{att_loss:,}명 [{attacker.morale}%사기] | "
                f"{defender.name} -{def_loss:,}명 [{defender.morale}%사기]"
            )
            events.append(rnd_msg)
            narrative.append(rnd_msg)

            if on_round:
                on_round(BattleRoundData(
                    round_num=rnd,
                    phase="field",
                    att_troops_before=att_before,
                    att_troops_after=attacker.troops,
                    att_morale_before=att_mor_before,
                    att_morale_after=attacker.morale,
                    att_max_troops=attacker.max_troops,
                    def_troops_before=def_before,
                    def_troops_after=defender.troops,
                    def_morale_before=def_mor_before,
                    def_morale_after=defender.morale,
                    def_max_troops=defender.max_troops,
                    wall_hp_before=0,
                    wall_hp_after=0,
                    max_wall_hp=0,
                    events=events,
                ))

        att_broken = not attacker.is_active()
        def_broken = not defender.is_active()

        if def_broken and not att_broken:
            winner = attacker.faction_id
        elif att_broken and not def_broken:
            winner = defender.faction_id
        elif att_broken and def_broken:
            winner = defender.faction_id
        else:
            winner = attacker.faction_id if attacker.troops >= defender.troops else defender.faction_id

        return BattleResult(
            winner=winner,
            attacker_losses=total_att_loss,
            defender_losses=total_def_loss,
            turns_fought=6,
            narrative=narrative,
        )

    # ------------------------------------------------------------------ hero duel

    def hero_duel(
        self,
        hero_a: Hero,
        hero_b: Hero,
        on_round: Optional[Callable[[dict], None]] = None,
    ) -> Hero:
        """
        One-on-one duel between two generals.
        Calls on_round(dict) with round data for UI display.
        Returns the victor.
        """
        hp_a = hero_a.hp
        hp_b = hero_b.hp

        for rnd in range(1, 10):
            if hp_a <= 0 or hp_b <= 0:
                break

            dmg_a = max(1, int(hero_a.strength * random.uniform(0.8, 1.2)) - hero_b.agility // 3)
            dmg_b = max(1, int(hero_b.strength * random.uniform(0.8, 1.2)) - hero_a.agility // 3)

            crit_msg = None
            if hero_a.intelligence > hero_b.intelligence and random.random() < 0.2:
                dmg_a = int(dmg_a * 1.5)
                crit_msg = f"✨ {hero_a.name_ko} 비기 발동! 피해 ×1.5"

            hp_a -= dmg_b
            hp_b -= dmg_a

            if on_round:
                on_round({
                    "round": rnd,
                    "hp_a": max(0, hp_a), "hp_b": max(0, hp_b),
                    "max_hp_a": hero_a.max_hp, "max_hp_b": hero_b.max_hp,
                    "dmg_a": dmg_a, "dmg_b": dmg_b,
                    "crit_msg": crit_msg,
                })

        victor = hero_a if hp_a > hp_b else hero_b

        hero_a.hp = max(1, hp_a)
        hero_b.hp = max(1, hp_b)
        if hp_a <= 0:
            hero_a.hp = max(1, hero_a.hp // 2)
        if hp_b <= 0:
            hero_b.hp = max(1, hero_b.hp // 2)

        return victor

    # ------------------------------------------------------------------ quick combat (legacy hero vs enemies)

    def resolve_combat(self, attacker: Hero, defense: int) -> bool:
        """
        Simple hero vs. garrison combat (legacy interface for TurnManager).
        Returns True if attacker wins.
        """
        att = attacker.strength + random.randint(1, 6)
        defs = defense + random.randint(1, 6)
        won = att > defs
        if won:
            attacker.hp = max(1, attacker.hp - random.randint(5, 15))
        else:
            attacker.hp = max(1, attacker.hp - random.randint(20, 40))
        return won

    def resolve_siege(self, hero: Hero, town: Town) -> BattleResult:
        """
        AI-facing siege wrapper: hero + town 으로 Army를 임시 생성해
        siege_battle를 호출하고 도시 점령 여부를 갱신한다.
        """
        attacker = Army(
            id=f"army_{hero.id}",
            name=f"{hero.name_ko}의 군대",
            faction_id=hero.faction_id,
            general_id=hero.id,
            troops=max(1, hero.current_army),
            max_troops=max(1, hero.current_army),
            morale=80,
        )
        garrison = max(100, town.garrison_strength * 100)
        defender = Army(
            id=f"garrison_{town.id}",
            name=f"{town.name_ko} 수비군",
            faction_id=town.controlled_by_faction or "neutral",
            troops=garrison,
            max_troops=garrison,
            morale=70,
        )
        result = self.siege_battle(attacker, defender, town,
                                   attacker_general=hero)
        # 승리 시 영웅 병력 갱신
        hero.current_army = max(0, attacker.troops)
        return result
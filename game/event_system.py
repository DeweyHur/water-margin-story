"""Event system — fires dynasty timeline events and random town events."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

from models import GameState, GameEvent, EventType


class EventSystem:
    def __init__(self, state: GameState) -> None:
        self.state = state
        self._config_dir = Path(__file__).parent.parent / "config"
        self._events_config = self._load_events()

    def _load_events(self) -> dict:
        with open(self._config_dir / "events.yaml", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # ------------------------------------------------------------------
    # Dynasty timeline events (scripted)
    # ------------------------------------------------------------------

    def fire_dynasty_events(self) -> None:
        for de in self._events_config.get("dynasty_events", []):
            if de["turn"] == self.state.turn:
                self.state.dynasty_stability += de.get("stability_delta", 0)
                self.state.dynasty_stability = max(0, self.state.dynasty_stability)
                event = GameEvent(
                    type=EventType.DYNASTY_CRISIS,
                    message=de["message"],
                )
                self.state.log_event(event)

    # ------------------------------------------------------------------
    # Random events per town per turn
    # ------------------------------------------------------------------

    def fire_random_events(self) -> None:
        for re in self._events_config.get("random_events", []):
            prob = re.get("probability", 0.1)
            if random.random() > prob:
                continue

            trigger = re.get("trigger", "any_town")
            town_id = self._pick_town(trigger)
            if not town_id:
                continue

            effect = re.get("effect", {})
            self._apply_effect(effect, town_id)

            event = GameEvent(
                type=self._map_event_type(effect.get("type", "")),
                target_id=town_id,
                message=re.get("message", ""),
            )
            self.state.log_event(event)

    def _pick_town(self, trigger: str) -> str | None:
        if trigger == "any_town":
            return random.choice(list(self.state.towns.keys()))
        elif trigger in self.state.towns:
            return trigger
        return None

    def _apply_effect(self, effect: dict, town_id: str) -> None:
        etype = effect.get("type", "")
        town = self.state.towns.get(town_id)
        if not town:
            return
        if etype == "clue" and town:
            town.clue_level = min(5, town.clue_level + effect.get("clue_delta", 1))
        elif etype == "dynasty_stability":
            self.state.dynasty_stability = max(
                0,
                self.state.dynasty_stability + effect.get("stability_delta", 0),
            )
        elif etype == "garrison_reduced" and town:
            town.garrison_strength = max(
                0, town.garrison_strength + effect.get("garrison_delta", -1)
            )
        elif etype == "heal":
            # Heal heroes present in the town
            for hero in self.state.heroes.values():
                if hero.current_town == town_id:
                    hero.hp = min(hero.max_hp, hero.hp + effect.get("hp_delta", 20))
        elif etype == "combat":
            # Apply minor HP loss to heroes in battle
            for hero in self.state.heroes.values():
                if hero.current_town == town_id:
                    damage = effect.get("enemy_strength", 2) * 3
                    hero.hp = max(1, hero.hp - damage)

    @staticmethod
    def _map_event_type(effect_type: str) -> EventType:
        mapping = {
            "combat": EventType.COMBAT,
            "clue": EventType.INVESTIGATION,
            "dynasty_stability": EventType.DYNASTY_CRISIS,
            "heal": EventType.ENCOUNTER,
            "garrison_reduced": EventType.ENCOUNTER,
        }
        return mapping.get(effect_type, EventType.ENCOUNTER)

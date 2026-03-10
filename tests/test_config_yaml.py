"""Tests for YAML config files — catches malformed YAML before the game even starts."""
import yaml
import pytest
from pathlib import Path

CONFIG = Path(__file__).parent.parent / "config"


def _load(filename: str) -> dict:
    with open(CONFIG / filename, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Parse sanity ────────────────────────────────────────────────────────────

def test_towns_yaml_parses():
    """towns.yaml must parse without ScannerError (regression: admin_level merged onto same line)."""
    data = _load("towns.yaml")
    assert "towns" in data
    assert len(data["towns"]) > 0


def test_scenarios_yaml_parses():
    data = _load("scenarios.yaml")
    assert "scenarios" in data
    assert len(data["scenarios"]) == 4


def test_heroes_yaml_parses():
    data = _load("heroes.yaml")
    assert "heroes" in data
    assert len(data["heroes"]) > 0


def test_factions_yaml_parses():
    data = _load("factions.yaml")
    assert "factions" in data


# ── Town field integrity ────────────────────────────────────────────────────

def test_all_towns_have_required_fields():
    data = _load("towns.yaml")
    required = {"id", "name_ko", "town_type"}
    for town in data["towns"]:
        missing = required - town.keys()
        assert not missing, f"Town {town.get('id', '?')} missing fields: {missing}"


def test_town_admin_level_in_range():
    data = _load("towns.yaml")
    for town in data["towns"]:
        adm = town.get("admin_level", 3)  # default is 3
        assert 1 <= adm <= 10, (
            f"Town {town['id']!r} has admin_level={adm} out of range [1,10]"
        )


def test_no_field_merges_on_same_line():
    """Regression: multi_replace once collapsed max_wall_hp and admin_level onto one line."""
    raw = (CONFIG / "towns.yaml").read_text(encoding="utf-8")
    for i, line in enumerate(raw.splitlines(), start=1):
        # A line with two 'key: value' pairs is a symptom of the merge bug
        colon_count = line.count(": ")
        # Lines like '    adjacent: [a, b]' are fine (one mapping, list value)
        # Lines like '    max_wall_hp: 110    admin_level: 6' are broken
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Multiple YAML keys on one line means at least two occurrences of /\w+: /
        import re
        keys = re.findall(r'\b\w+\s*:', line)
        assert len(keys) <= 1, (
            f"towns.yaml line {i} appears to have multiple YAML keys on one line: {line!r}"
        )


# ── Scenario hero_armies ────────────────────────────────────────────────────

def test_all_scenarios_have_hero_armies():
    data = _load("scenarios.yaml")
    for s in data["scenarios"]:
        assert "hero_armies" in s, f"Scenario {s['id']} is missing hero_armies"
        assert isinstance(s["hero_armies"], dict), f"Scenario {s['id']} hero_armies is not a dict"
        assert len(s["hero_armies"]) > 0, f"Scenario {s['id']} hero_armies is empty"


def test_gao_qiu_always_has_army():
    data = _load("scenarios.yaml")
    for s in data["scenarios"]:
        armies = s.get("hero_armies", {})
        assert "gao_qiu" in armies, f"Scenario {s['id']}: gao_qiu has no starting army"
        assert armies["gao_qiu"] > 0, f"Scenario {s['id']}: gao_qiu army must be > 0"


def test_hero_armies_are_non_negative():
    data = _load("scenarios.yaml")
    for s in data["scenarios"]:
        for hero_id, size in s.get("hero_armies", {}).items():
            assert size >= 0, (
                f"Scenario {s['id']}: {hero_id} army={size} is negative"
            )


def test_scenario_army_scales_with_year():
    """Later scenarios should have a larger total army count (story progression)."""
    data = _load("scenarios.yaml")
    scenarios = data["scenarios"]
    totals = [sum(s["hero_armies"].values()) for s in scenarios]
    # Each scenario's total should be >= the previous one
    for i in range(1, len(totals)):
        assert totals[i] >= totals[i - 1], (
            f"Scenario {i+1} total armies ({totals[i]}) < scenario {i} ({totals[i-1]})"
        )


def test_towns_key_adjacency_expectations():
    data = _load("towns.yaml")
    towns = {t["id"]: t for t in data["towns"]}

    daming_adj = set(towns["daming"].get("adjacent", []))
    taiyuan_adj = set(towns["taiyuan"].get("adjacent", []))
    liangshan_adj = set(towns["liangshan"].get("adjacent", []))
    bianjing_adj = set(towns["bianjing"].get("adjacent", []))

    assert "taiyuan" not in daming_adj
    assert "daming" not in taiyuan_adj
    assert "bianjing" in liangshan_adj
    assert "liangshan" in bianjing_adj

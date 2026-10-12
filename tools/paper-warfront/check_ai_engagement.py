"""Native Godot checks and provenance for the engagement decision revision."""
import hashlib
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/core-alignment-rc7/engagement-regression"
ENGINE = ROOT / ".tools/godot/Godot_v4.7.2-stable_win64_console.exe"
TESTS = [
    ("test_unit_order_equivalence.gd", "UNIT_ORDER_EQUIVALENCE", 1200),
    ("test_axis_target_boundaries.gd", "AXIS_TARGET_BOUNDARIES", 20),
    ("test_campaign_routes.gd", "CAMPAIGN_ROUTES", 103595),
    ("test_story_objective_binding.gd", "STORY_OBJECTIVES", 1610),
    ("test_leap_blocker_phase.gd", "LEAP_BLOCKER_PHASE", 1200),
    ("test_road_target_equivalence.gd", "ROAD_TARGET_EQUIVALENCE", 58576),
    ("test_marching_query_equivalence.gd", "MARCHING_QUERY_EQUIVALENCE", 13600),
    ("test_stalled_front_recruitment.gd", "STALLED_FRONT_RECRUITMENT", 48),
    ("test_unit_fielding_roles.gd", "UNIT_FIELDING_ROLES", 48),
    ("test_paid_fielding_pipeline.gd", "PAID_FIELDING_PIPELINE", 102),
    ("test_ai_bootstrap_investments.gd", "AI_BOOTSTRAP_INVESTMENTS", 32),
    ("test_ai_economy_bootstrap.gd", "AI_ECONOMY_BOOTSTRAP", 68),
    ("test_ai_income_staging.gd", "AI_INCOME_STAGING", 72),
    ("test_ai_contact_funding.gd", "AI_CONTACT_FUNDING", 70),
    ("test_hammer_screen_reach.gd", "HAMMER_SCREEN_REACH", 16),
    ("test_ai_budget_recovery.gd", "AI_BUDGET_RECOVERY", 61),
    ("test_ai_budget_planner.gd", "AI_BUDGET_PLANNER", 246),
    ("test_paid_opening.gd", "PAID_OPENING", 200),
    ("test_healing_events.gd", "HEALING_EVENTS", 40),
    ("test_premium_reach.gd", "PREMIUM_REACH", 16),
    ("test_demand_deployment.gd", "DEMAND_DEPLOYMENT", 28),
    ("test_demand_research.gd", "DEMAND_RESEARCH", 22),
    ("test_recruitment_diagnostics.gd", "RECRUITMENT_DIAGNOSTICS", 92),
    ("test_visible_counter_deployment.gd", "VISIBLE_COUNTER_DEPLOYMENT", 28),
    ("test_context_research.gd", "CONTEXT_RESEARCH", 29),
    ("test_role_deployment.gd", "ROLE_DEPLOYMENT", 30),
    ("test_sequential_purchase_window.gd", "SEQUENTIAL_PURCHASE_WINDOW", 22),
    ("test_sequential_build_reserve.gd", "SEQUENTIAL_BUILD_RESERVE", 8),
    ("test_deployment_group.gd", "DEPLOYMENT_GROUP", 22),
    ("test_sequential_formation_cash.gd", "SEQUENTIAL_FORMATION_CASH", 32),
    ("test_sequential_deployment.gd", "SEQUENTIAL_DEPLOYMENT", 22),
    ("test_research_wave_budget.gd", "RESEARCH_WAVE_BUDGET", 10),
    ("test_deployment_screen.gd", "DEPLOYMENT_SCREEN", 4),
    ("test_research_screen_budget.gd", "RESEARCH_SCREEN_BUDGET", 12),
    ("test_area_field_aim.gd", "AREA_FIELD_AIM", 28),
    ("test_first_investment.gd", "FIRST_INVESTMENT", 40),
    ("test_staged_deployment.gd", "STAGED_DEPLOYMENT", 18),
    ("test_funded_deployment.gd", "FUNDED_DEPLOYMENT", 22),
    ("test_research_arrival.gd", "RESEARCH_ARRIVAL", 14),
    ("test_network_commands.gd", "NETWORK_COMMANDS", 12),
    ("test_queue_snapshot.gd", "QUEUE_SNAPSHOT", 22),
    ("test_spawn_camp_recruitment.gd", "SPAWN_CAMP_RECRUITMENT", 14),
    ("test_mine_pressure_boundaries.gd", "MINE_PRESSURE_BOUNDARIES", 14),
    ("test_ai_research_deployment.gd", "AI_RESEARCH_DEPLOYMENT", 18),
    ("test_recruitment_readiness.gd", "RECRUITMENT_READINESS", 54),
    ("test_research_mana_feedback.gd", "RESEARCH_MANA_FEEDBACK", 43),
    ("test_economy_alarm.gd", "ECONOMY_ALARM", 24),
    ("test_ai_economic_counterplay.gd", "AI_ECONOMIC_COUNTERPLAY", 9),
    ("test_firing_visibility.gd", "FIRING_VISIBILITY", 21),
    ("test_target_search_equivalence.gd", "TARGET_SEARCH_EQUIVALENCE", 1441),
    ("test_ranged_formation.gd", "RANGED_FORMATION", 62),
    ("probe_mixed_ranged_formation.gd", "MIXED_RANGED_FORMATION", 192),
    ("test_movement_phase_fairness.gd", "MOVEMENT_PHASE_FAIRNESS", 18),
    ("test_simultaneous_combat.gd", "SIMULTANEOUS_COMBAT", 90),
    ("test_core_visibility.gd", "CORE_VISIBILITY", 14),
    ("test_fog_presentation.gd", "FOG_PRESENTATION", 1124),
    ("test_observer_camera.gd", "OBSERVER_CAMERA", 82),
    ("test_core_spell_windows.gd", "CORE_SPELL_WINDOWS", 8),
    ("test_core_progression.gd", "CORE_PROGRESSION", 195),
    ("test_core_economy_sources.gd", "CORE_ECONOMY_SOURCES", 44),
    ("test_faction_spell_kits.gd", "FACTION_SPELL_KITS", 168),
    ("test_visibility_graph_equivalence.gd", "VISIBILITY_GRAPH_EQUIVALENCE", 1932),
    ("test_combat_ownership.gd", "OWNERSHIP", 154),
    ("test_worker_actions.gd", "WORKERS", 121),
    ("test_frame_contracts.gd", "FRAME_CONTRACTS", 3263),
    ("test_ai_structure_memory.gd", "AI_STRUCTURE_MEMORY", 19),
    ("test_cleanse_recovery.gd", "CLEANSE_RECOVERY", 6),
    ("test_world_combat.gd", "CURRENT_WORLD_COMBAT", 370),
    ("test_ai_engagement_tactics.gd", "AI_ENGAGEMENT_TACTICS", 21),
    ("test_leap_spacing.gd", "LEAP_SPACING", 8),
    ("test_ai_spell_budget.gd", "AI_SPELL_BUDGET", 258),
    ("test_ai_route_defense.gd", "AI_ROUTE_DEFENSE", 26),
    ("test_core_ai_decisions.gd", "CORE_AI_DECISIONS", 8),
    ("test_ai_investment.gd", "AI_INVESTMENT", 8),
    ("test_ai_opening_composition.gd", "AI_OPENING_COMPOSITION", 4),
    ("test_ai_random_streams.gd", "AI_RANDOM_STREAMS", 20),
    ("test_campaign_director.gd", "CAMPAIGN_DIRECTOR", 4200),
    ("test_theatre_decisions.gd", "THEATRE_DECISIONS", 45),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def experimental_policy_fields(data):
    """Reject active trial policies, including future ones, as formal match evidence."""
    selectors = {"experimental_paid_opening_side": "experimental_ai_paid_opening",
                 "experimental_ai_budget_planner_side": "experimental_ai_budget_planner"}
    return {key: value for key, value in data.items()
            if key.startswith("experimental_") and value
            and not (key in selectors and not data.get(selectors[key], False))
            and key not in {"experimental_map_removed_edges", "experimental_map_sha256"}}


def main():
    global QA
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=QA)
    parser.add_argument("--project", type=Path, default=ROOT / "game", help="Native source project to validate; reports bind its actual inputs.")
    parser.add_argument("--matchups", nargs="+", default=["faction-focused-front-saving137.json", "faction-focused-short271.json", "faction-focused-long271.json"])
    parser.add_argument("--indices", default="6,8,9,60,80,90")
    parser.add_argument("--allow-experimental-map", action="store_true")
    parser.add_argument("--mechanisms-only", action="store_true", help="Run all controlled mechanism tests without asserting paid matchup provenance.")
    args = parser.parse_args()
    QA = args.output.resolve()
    project = args.project.resolve()
    def input_path(relative):
        return project / relative.removeprefix("game/") if relative.startswith("game/") else ROOT / relative
    QA.mkdir(parents=True, exist_ok=True)
    report = {
        "scope": "Controlled native CPU decision checks; not faction balance, rendering, human usability or Android hardware evidence.",
        "inputs": {}, "tests": [], "matchups": [],
    }
    report["mechanisms_only"] = args.mechanisms_only
    report["source_project"] = project.as_posix()
    for relative in ["game/scripts/tactical_ai.gd", "game/scripts/battle_sim.gd", "game/scripts/battle_command_rules.gd", "game/scripts/ui_battle_sheets.gd",
                     "game/scripts/unit_abilities.gd", "game/data/balance-prototype.json",
                     "game/scripts/battle_visibility.gd", "game/scripts/theatre_fog.gd", "game/scripts/map_runtime.gd",
                     "game/scripts/manual_spell_rules.gd", "game/scripts/unit_frame_player.gd",
                     "game/data/unit-frames.json", "game/data/unit-actions.json",
                     "game/data/maps.json", "game/data/technology.json",
                     "tools/paper-warfront/check_ai_engagement.py", "game/tests/reference_target_search.gd",
                     "game/scripts/main.gd", "game/scripts/audio_controller.gd", "game/scripts/battle_view.gd",
                     "game/scripts/local_duel.gd", "game/scripts/lan_session.gd", "game/scripts/network_commands.gd", "game/scripts/match_projection.gd",
                     "game/scripts/data_store.gd", "game/scripts/recruitment_readiness.gd", "game/scripts/ai_budget_planner.gd", "game/scripts/mobile_ui.gd"]:
        report["inputs"][relative] = sha(input_path(relative))
    for filename, marker, expected in TESTS:
        command = [str(ENGINE), "--headless", "--path", str(project),
                   "--script", "res://tests/" + filename]
        if marker == "THEATRE_DECISIONS":
            command.extend(["--", str(QA / "theatre-current.json")])
        if marker == "CURRENT_WORLD_COMBAT":
            command.extend(["--", "--output", str(QA / "world-combat-current.json")])
        if marker == "SIMULTANEOUS_COMBAT":
            command.extend(["--", "--output", str(QA / "simultaneous-combat-current.json")])
        if marker == "OWNERSHIP":
            command.extend(["--", "--output", str(QA / "ownership-current.json")])
        if marker == "FRAME_CONTRACTS":
            command.extend(["--", "--report", str(QA / "frame-contracts-current.json")])
        run = subprocess.run(
            command, cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace", timeout=180 if filename=="test_ai_budget_planner.gd" else 120,
        )
        output = run.stdout + run.stderr
        (QA / (filename + ".log")).write_text(output, encoding="utf-8")
        count = re.search(re.escape(marker) + r"[: ]+([0-9]+)", output)
        actual = int(count.group(1)) if count else 0
        terminal_ok = "failures=[]" in output
        if marker in {"OWNERSHIP", "WORKERS"}:
            terminal_ok = " / 0 failures" in output
        if marker == "FRAME_CONTRACTS":
            terminal_ok = "checks failures []" in output
        if marker == "VISIBILITY_GRAPH_EQUIVALENCE":
            terminal_ok = "failures=0" in output
        if marker == "THEATRE_DECISIONS":
            lines = [line for line in output.splitlines() if line.startswith(marker + " ")]
            terminal = json.loads(lines[-1].split(" ", 1)[1]) if lines else {}
            actual = terminal.get("checks", 0)
            terminal_ok = terminal.get("passed") is True and terminal.get("failures") == 0
        passed = (run.returncode == 0 and actual == expected and terminal_ok
                  and "SCRIPT ERROR" not in output and "ERROR:" not in output)
        report["tests"].append({"script": filename, "sha256": sha(project / "tests" / filename),
                                "checks": actual,
                                "exit": run.returncode, "passed": passed})
    indices = {int(value) for value in args.indices.split(",")}
    for filename in ([] if args.mechanisms_only else args.matchups):
        path = QA.parent / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        trial_policies = experimental_policy_fields(data)
        current = (not trial_policies
                   and {"res://scripts/battle_sim.gd", "res://scripts/unit_abilities.gd", "res://scripts/tactical_ai.gd"}.issubset(data["inputs"])
                   and (not data.get("experimental_map_removed_edges") or args.allow_experimental_map)
                   and all(sha(project / key.removeprefix("res://")) == value
                           for key, value in data["inputs"].items()))
        complete = {row["index"] for row in data["records"]} == indices and len(data["records"]) == len(indices)
        report["matchups"].append({"file": filename, "sha256": sha(path),
                                  "current_inputs": current, "complete": complete,
                                  "map": data["map"], "seed": data["seed"],
                                  "experimental_policy_fields": trial_policies,
                                  "experimental_map_removed_edges": data.get("experimental_map_removed_edges", []),
                                  "experimental_map_sha256": data.get("experimental_map_sha256"),
                                  "records": [{"index": row["index"], "west": row["west"],
                                               "east": row["east"], "winner": row["winner"],
                                               "time": row["time"], "sides": row["sides"]}
                                              for row in data["records"]]})
    report["source_unchanged"] = all(sha(input_path(key)) == value for key, value in report["inputs"].items())
    report["passed"] = (report["source_unchanged"] and all(row["passed"] for row in report["tests"])
                        and all(row["current_inputs"] and row["complete"] for row in report["matchups"]))
    (QA / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "checks": sum(row["checks"] for row in report["tests"]),
                      "completed_observations": sum(len(row["records"]) for row in report["matchups"]) }))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

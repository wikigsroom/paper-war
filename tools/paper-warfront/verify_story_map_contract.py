"""Validate the single-player map/story contract for 纸上兵戈.

This is a data-contract gate, not a gameplay or human narrative review.  It
keeps map geometry, authored story, battle configuration, narrative geography
and campaign routing bound to the same stable level ids.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None


def fingerprint(value: Any) -> str:
    """Stable comparison key for authored prose or structured scene data."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    data = root / "game" / "data"
    files = {
        "maps": data / "maps.json",
        "story": data / "story.json",
        "campaign": data / "campaign.json",
        "flow": data / "campaign-flow.json",
        "narrative": data / "campaign-narrative.json",
    }
    checks: list[str] = []
    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        (checks if condition else failures).append(message)

    try:
        loaded = {name: read_json(path) for name, path in files.items()}
    except Exception as exc:  # pragma: no cover - diagnostic path
        failures.append(f"unable to read campaign data: {exc}")
        result = {"passed": False, "checks": checks, "failures": failures}
        target = args.output or (root / "output" / "qa" / "paper-warfront" / "story-map-contract.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    maps = loaded["maps"].get("maps", [])
    facts = loaded["story"].get("facts", [])
    levels = loaded["campaign"].get("levels", [])
    flow_nodes = loaded["flow"].get("nodes", {})
    profiles = loaded["narrative"].get("profiles", {})

    map_by_id = {entry.get("id"): entry for entry in maps}
    fact_by_id = {entry.get("id"): entry for entry in facts}
    level_by_id = {entry.get("id"): entry for entry in levels}
    map_ids = set(map_by_id)
    level_ids = set(level_by_id)
    fact_ids = set(fact_by_id)
    flow_ids = set(flow_nodes)
    story_ids = {entry.get("map") for entry in facts}
    level_map_ids = {entry.get("map") for entry in levels}
    narrative_map_ids = {entry.get("map") for entry in profiles.values()}
    forked_geometry_maps = 0
    unequal_route_length_maps = 0

    check(len(maps) == 200, f"exactly 200 authored maps ({len(maps)})")
    check(len(facts) == len(maps), f"one story fact per map ({len(facts)}/{len(maps)})")
    check(len(levels) == len(maps), f"one battle level per map ({len(levels)}/{len(maps)})")
    check(len(flow_nodes) == len(levels), f"one routing node per level ({len(flow_nodes)}/{len(levels)})")
    check(len(profiles) == len(levels), f"one narrative profile per level ({len(profiles)}/{len(levels)})")
    check(len(map_ids) == len(maps), "map ids are unique")
    check(len(level_ids) == len(levels), "campaign level ids are unique")
    check(map_ids == story_ids, "every map id is referenced by exactly one story fact")
    check(map_ids == level_map_ids, "every map id is referenced by exactly one playable level")
    check(map_ids == narrative_map_ids, "every map id is referenced by narrative geography")
    check(level_ids == flow_ids, "campaign levels and routing nodes share stable ids")

    # A non-empty field alone is too weak for a story map contract.  These
    # authored fields must remain map-specific so adding a level cannot silently
    # copy one generic briefing/result scene across the campaign.  Objective
    # tips and win-kind labels are intentionally allowed to repeat because they
    # are mechanical guidance, not the scene's authored identity.
    for field, entries, label in [
        ("story_before", facts, "story before scenes"),
        ("story_after", facts, "story after scenes"),
        ("line", facts, "story lines"),
        ("evidence_name", list(profiles.values()), "evidence names"),
        ("title", levels, "campaign titles"),
    ]:
        unique = len({fingerprint(entry.get(field)) for entry in entries})
        check(unique == len(entries), f"{label} are map-specific ({unique}/{len(entries)} unique)")

    for map_id, map_entry in map_by_id.items():
        check(bool(map_id), "every map has a stable id")
        check(nonempty(map_entry.get("nodes")) and nonempty(map_entry.get("edges")), f"{map_id}: authored nodes and edges")
        check(nonempty(map_entry.get("objective_anchor")), f"{map_id}: objective anchor")
        check(nonempty(map_entry.get("route_lengths")), f"{map_id}: route length contract")
        check(nonempty(map_entry.get("design_card")), f"{map_id}: design card")
        edge_ids = {edge.get("id") for edge in map_entry.get("edges", [])}
        anchor_edge = map_entry.get("objective_anchor", {}).get("edge")
        check(anchor_edge in edge_ids, f"{map_id}: map objective anchor edge exists")
        outgoing = Counter(edge.get("from") for edge in map_entry.get("edges", []))
        actual_forks = sum(1 for count in outgoing.values() if count > 1)
        forked_geometry_maps += int(actual_forks > 0)
        route_lengths = map_entry.get("route_lengths", {})
        unequal_route_length_maps += int(abs(float(route_lengths.get("longest", 0.0)) - float(route_lengths.get("shortest", 0.0))) > 0.001)
        check(int(map_entry.get("presentation", {}).get("forks", -1)) == actual_forks, f"{map_id}: presentation fork count matches geometry")

    for level_id, level in level_by_id.items():
        map_id = level.get("map")
        fact = fact_by_id.get(level_id)
        map_entry = map_by_id.get(map_id)
        check(fact is not None, f"{level_id}: story fact exists")
        check(map_entry is not None, f"{level_id}: map exists")
        for field in ("story_before", "story_after", "line", "tip", "win", "objective_anchor", "story_flag"):
            check(nonempty(level.get(field)), f"{level_id}: level.{field} is authored")
        if fact is not None:
            for field in ("story_before", "story_after", "line", "tip", "win", "objective_anchor", "story_flag"):
                check(nonempty(fact.get(field)), f"{level_id}: story.{field} is authored")
        if map_entry is not None:
            check(level.get("objective_anchor", {}).get("edge") in {e.get("id") for e in map_entry.get("edges", [])}, f"{level_id}: level anchor is on map geometry")
        # The profile value carries the display id ``narrative.<level>``;
        # the dictionary key intentionally stays equal to the campaign id so
        # joins remain stable across the runtime data files.
        profile = profiles.get(level_id)
        check(profile is not None, f"{level_id}: narrative profile exists")
        if profile is not None and map_entry is not None:
            check(profile.get("map") == map_id, f"{level_id}: narrative profile binds its map")
            check(nonempty(profile.get("goal")) and nonempty(profile.get("geography_reason")), f"{level_id}: narrative goal and geography reason")
            edge_ids = {edge.get("id") for edge in map_entry.get("edges", [])}
            check(set(profile.get("roads", [])) <= edge_ids, f"{level_id}: narrative roads exist on map")
            check(profile.get("objective_anchor", {}).get("edge") in edge_ids, f"{level_id}: narrative anchor is on map")

    indegree = {node_id: 0 for node_id in flow_ids}
    branch_nodes = 0
    for node_id, node in flow_nodes.items():
        successors = list(node.get("successors", []))
        if len(successors) > 1:
            branch_nodes += 1
        for target in successors + list(node.get("unlock_any", [])) + list(node.get("unlock_all", [])):
            check(target in flow_ids, f"{node_id}: route dependency {target} exists")
        for target in successors:
            if target in indegree:
                indegree[target] += 1
    merge_nodes = sum(1 for count in indegree.values() if count > 1)
    check(branch_nodes > 0, f"campaign graph has authored branching ({branch_nodes} branch nodes)")
    check(merge_nodes > 0, f"campaign graph has authored convergence ({merge_nodes} merge nodes)")
    check(nonempty(loaded["flow"].get("root")) and loaded["flow"].get("root") in flow_ids, "campaign root is playable")
    check(nonempty(loaded["flow"].get("finale")) and loaded["flow"].get("finale") in flow_ids, "campaign finale is playable")

    chapter_entries = loaded["story"].get("chapters", [])
    flow_chapters = loaded["flow"].get("chapters", [])
    check(len(chapter_entries) == 10, f"story has ten chapters ({len(chapter_entries)})")
    check(len(flow_chapters) == 10, f"routing has ten chapters ({len(flow_chapters)})")
    chapter_pages: set[str] = set()
    for chapter in flow_chapters:
        for layer in chapter.get("layers", []):
            for page in layer.get("pages", []):
                chapter_pages.add(page)
                check(page in flow_ids, f"chapter layer page {page} exists")
    check(chapter_pages == flow_ids, "chapter layers cover every authored level")

    result = {
        "passed": not failures,
        "contract": "single_player_map_story_v1",
        "version": loaded["maps"].get("schema_version"),
        "maps": len(maps),
        "chapters": len(chapter_entries),
        "branch_nodes": branch_nodes,
        "merge_nodes": merge_nodes,
        "forked_geometry_maps": forked_geometry_maps,
        "unequal_route_length_maps": unequal_route_length_maps,
        "map_specific_fields": {
            "story_before": len({fingerprint(entry.get("story_before")) for entry in facts}),
            "story_after": len({fingerprint(entry.get("story_after")) for entry in facts}),
            "story_line": len({fingerprint(entry.get("line")) for entry in facts}),
            "evidence_name": len({fingerprint(entry.get("evidence_name")) for entry in profiles.values()}),
            "campaign_title": len({fingerprint(entry.get("title")) for entry in levels}),
        },
        "checks": len(checks),
        "failures": failures,
        "input_sha256": {name: sha256(path) for name, path in files.items()},
        "scope": "Data binding only: map geometry, story text, objectives, narrative geography and campaign routing. Does not claim human narrative review or completed battle balance.",
    }
    target = args.output or (root / "output" / "qa" / "paper-warfront" / "story-map-contract.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

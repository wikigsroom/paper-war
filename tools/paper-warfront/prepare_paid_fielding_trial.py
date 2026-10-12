"""Freeze paid first-recruit trials against the verified rc23 gameplay inputs."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/paid-fielding-rc24"
ap = argparse.ArgumentParser()
ap.add_argument("--policy", choices=["commit-r1", "early-r2"], required=True)
args = ap.parse_args()
baseline = QA / "rc23-control-runtime"
target = QA / (args.policy + "-runtime")
assert not target.exists(), "Do not overwrite a frozen trial"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
shipping = read(ROOT / "release/3.0.0-rc23-preview/build-manifest.json")
for folder, pattern in [("scripts", "*.gd"), ("data", "*.json")]:
    (target / folder).mkdir(parents=True)
    for path in sorted((baseline / folder).glob(pattern)):
        assert sha(path) == shipping["source_inputs"][f"game/{folder}/{path.name}"]
        shutil.copy2(path, target / folder / path.name)
(target / "tests").mkdir()
shutil.copy2(baseline / "project.godot", target / "project.godot")
shutil.copy2(baseline / "snapshot.json", target / "snapshot.json")
source = (baseline / "scripts/tactical_ai.gd").read_text(encoding="utf-8")
prior = (ROOT / "output/qa/godot/ai-redemption-rc23/paid-grant-r6-runtime/scripts/tactical_ai.gd").read_text(encoding="utf-8")


def replace(old, new):
    global source
    assert source.count(old) == 1, old[:150]
    source = source.replace(old, new)


replace('\tif front_broken:p.ai_research=""\n', '\tif front_broken:p.ai_research=""\n'
    '\tvar grant_trial: bool=sim.config.get("experimental_ai_grant_redemption",false) and int(sim.config.get("experimental_ai_grant_redemption_side",side))==side\n'
    '\tvar grant_goal: String=paid_grant_target(sim,side) if grant_trial else ""\n'
    '\tvar grant_ready: bool=grant_goal!="" and paid_grant_formation(sim,side,grant_goal,allies,threatened,front_broken)\n'
    '\tif grant_goal!="":p.ai_research=""\n')
replace('\tvar deployment_pending: bool=', '\tvar deployment_pending: bool=grant_goal!="" or ')
replace('\tif required_facility==0 and not phase.is_empty()', '\tif grant_goal=="" and required_facility==0 and not phase.is_empty()')
replace('\tinvestment_reserve=maxf(investment_reserve,required_facility)\n',
    '\tinvestment_reserve=maxf(investment_reserve,required_facility)\n'
    '\tif grant_ready:investment_reserve=maxf(investment_reserve,float(sim.db.balance.units[grant_goal].gold))\n')
replace('\tif (not paid_opening or workers>=3 or threatened) and', '\tif (grant_goal=="" or threatened) and (not paid_opening or workers>=3 or threatened) and')
replace('\tvar safe_investment: bool=planned_unit==""', '\tvar safe_investment: bool=grant_goal=="" and planned_unit==""')
replace('\t\t\t\tif sim.request(side,"research",{"id":p.ai_research}).ok:\n',
    '\t\t\t\tif sim.request(side,"research",{"id":p.ai_research}).ok:\n'
    '\t\t\t\t\tif grant_trial and sim.db.balance.units.has(selected.grant) and not sim.db.balance.units[selected.grant].get("economy",false):\n'
    '\t\t\t\t\t\tp["ai_grant_goal"]=selected.grant;grant_goal=str(selected.grant)\n'
    '\t\t\t\t\t\tgrant_ready=paid_grant_formation(sim,side,grant_goal,allies,threatened,front_broken)\n')
replace('\t\tvar deployment_cash: float=p.gold\n', '\t\tif grant_ready:best=grant_goal if p.unlocked.has(grant_goal) else ""\n'
    '\t\tvar deployment_cash: float=p.gold\n')
replace('\t\t\tif best!="":recruitment_result=sim.request(side,"recruit",{"id":best})\n',
    '\t\t\tif best!="":\n'
    '\t\t\t\trecruitment_result=sim.request(side,"recruit",{"id":best})\n'
    '\t\t\t\tif grant_trial and best==grant_goal and recruitment_result.ok:\n'
    '\t\t\t\t\tp["ai_grant_goal"]="";p["ai_grant_first_ordered"]=true\n')
replace('\t\t\ttrace["counter_eligible"]=visible_counter_deployment_target(sim,side,allies,enemies)\n',
    '\t\t\ttrace["counter_eligible"]=visible_counter_deployment_target(sim,side,allies,enemies)\n'
    '\t\t\ttrace["grant_goal"]=grant_goal;trace["grant_ready"]=grant_ready\n')
helpers = prior[prior.index('static func paid_grant_target'):prior.index('# An opt-in paid start window.')]
replace('# An opt-in paid start window.', helpers + '# An opt-in paid start window.')

if args.policy == "early-r2":
    replace('\tvar tower_cost: float=',
        '\t# Prefer one paid advanced role before an optional opening watchpost.\n'
        '\t# Mandatory mana facilities and visible emergency defense retain priority.\n'
        '\tif grant_trial and not p.get("ai_grant_first_ordered",false) and grant_goal=="" and p.ai_research=="" and p.research.is_empty() and sim.time>=float(p.ai_research_at) and combat>=2 and sim.population(side,true,true)>=mini(3,desired_workers) and not threatened and not front_broken and (not resource_build or unbuilt_facility_reserve(sim,side)==0):\n'
        '\t\tvar first_offer: Dictionary=first_grant_offer(sim,side,phase,allies,enemies)\n'
        '\t\tif not first_offer.is_empty():p.ai_research=first_offer.id;p.ai_build_reserve=0.0\n'
        '\tvar tower_cost: float=')
    replace('\tif sim.population(side,true,true)>=mini(3,desired_workers) and not demand_pending',
        '\tif (not grant_trial or p.ai_research=="") and sim.population(side,true,true)>=mini(3,desired_workers) and not demand_pending')
    replace('choose_paid_research(sim,side,candidates,phase,allies,enemies) if paid_opening else choose_research',
        'choose_paid_research(sim,side,candidates,phase,allies,enemies) if paid_opening or grant_trial else choose_research')
    replace('static func paid_grant_target',
        'static func first_grant_offer(sim,side: int,phase: Dictionary,allies: Array,enemies: Array) -> Dictionary:\n'
        '\tvar p: Dictionary=sim.players[side]\n'
        '\tvar candidates: Array=[]\n'
        '\tfor node in sim.db.technology.nodes:\n'
        '\t\tif node.faction!=p.faction or p.studied.has(node.id) or not sim.db.balance.units.has(node.grant):continue\n'
        '\t\tif not p.roster.has(node.grant) or p.unlocked.has(node.grant):continue\n'
        '\t\tif node.requires.all(func(id):return p.studied.has(id)):candidates.append(node)\n'
        '\treturn choose_paid_research(sim,side,candidates,phase,allies,enemies) if not candidates.is_empty() else {}\n\n'
        'static func paid_grant_target')

(target / "scripts/tactical_ai.gd").write_text(source, encoding="utf-8")
probe = (baseline / "tests/probe_faction_matchups.gd").read_text(encoding="utf-8")
anchor = '\treport["experimental_ai_budget_planner"]=args.has("--budget-planner-trial")\n'
assert probe.count(anchor) == 1
probe = probe.replace(anchor, anchor + '\treport["experimental_ai_grant_redemption"]=args.has("--grant-redemption-side")\n'
    '\treport["experimental_ai_grant_redemption_side"]=int(args[args.find("--grant-redemption-side")+1]) if args.has("--grant-redemption-side") else -1\n')
anchor = '\t\tbattle.config["observe_ai_budget"]=args.has("--budget-decision-trace")\n'
assert probe.count(anchor) == 1
probe = probe.replace(anchor, anchor + '\t\tif args.has("--grant-redemption-side"):\n'
    '\t\t\tbattle.config["experimental_ai_grant_redemption"]=true\n'
    '\t\t\tbattle.config["experimental_ai_grant_redemption_side"]=int(args[args.find("--grant-redemption-side")+1])\n')
(target / "tests/probe_faction_matchups.gd").write_text(probe, encoding="utf-8")
diff = QA / (args.policy + ".diff")
diff.write_text(''.join(difflib.unified_diff(
    (baseline / "scripts/tactical_ai.gd").read_text(encoding="utf-8").splitlines(keepends=True), source.splitlines(keepends=True),
    fromfile="rc23/tactical_ai.gd", tofile=args.policy + "/tactical_ai.gd")), encoding="utf-8")
(target / "candidate.json").write_text(json.dumps({
    "policy": args.policy, "baseline_version": shipping["version"], "shipping_source_changed": False,
    "native_engine": "Godot 4.7.2", "prices_times_roads_fog_unchanged": True,
    "generation_tool_sha256": sha(Path(__file__)), "diff_sha256": sha(diff),
}, indent=2), encoding="utf-8")
print("Frozen trial prepared:", args.policy)

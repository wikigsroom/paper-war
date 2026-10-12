"""Load actual EXE's embedded pack with native Godot and external test harnesses."""
import hashlib,json,re,subprocess,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];VERSION=os.environ.get("PAPER_RELEASE_VERSION","3.0.0-rc10-preview")
QA=ROOT/os.environ.get("PAPER_QA_DIR","output/qa/godot/core-alignment-rc10")/"windows-logic";QA.mkdir(parents=True,exist_ok=True)
EXE=ROOT/f"release/{VERSION}/windows/PaperWarfront.exe"
ENGINE=ROOT/".tools/godot/Godot_v4.7.2-stable_win64_console.exe"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(filename,extra=()):
    source=ROOT/"game/tests"/filename
    timeout_seconds=180 if filename=="test_ai_budget_planner.gd" else 90
    result=subprocess.run([str(ENGINE),"--headless","--main-pack",str(EXE),"--script",str(source),"--",*map(str,extra)],cwd=ROOT,capture_output=True,encoding="utf-8",errors="replace",timeout=timeout_seconds)
    log=result.stdout+result.stderr;(QA/(filename+".log")).write_text(log,encoding="utf-8")
    assert result.returncode==0 and "SCRIPT ERROR" not in log and "ERROR:" not in log,log[-2000:]
    return log
run("packaged_runtime_origin.gd",("--output",QA/"origin.json"))
origin=json.loads((QA/"origin.json").read_text(encoding="utf-8"))
assert origin["source_gameplay_files_absent"] and origin["version"]==VERSION
apk=json.loads((QA.parent/"apk-logic/report.json").read_text(encoding="utf-8"))
assert all(apk["extracted_inputs"][p.removeprefix("res://")]==h for p,h in origin["inputs"].items()),"Embedded EXE logic/data must match actual APK bytes"
tests=[]
cases=[("test_research_mana_feedback.gd","RESEARCH_MANA_FEEDBACK",43),("probe_mixed_ranged_formation.gd","MIXED_RANGED_FORMATION",192)]
if "scripts/recruitment_readiness.gdc" in apk["extracted_inputs"]:
    cases.extend([("test_recruitment_readiness.gd","RECRUITMENT_READINESS",54),("test_mine_pressure_boundaries.gd","MINE_PRESSURE_BOUNDARIES",14),("test_spawn_camp_recruitment.gd","SPAWN_CAMP_RECRUITMENT",14)])
if int(re.search(r"-rc(\d+)",VERSION).group(1))>=12:
    investment_checks=40 if int(re.search(r"-rc(\d+)",VERSION).group(1))>=13 else 28
    cases.extend([("test_first_investment.gd","FIRST_INVESTMENT",investment_checks),("test_queue_snapshot.gd","QUEUE_SNAPSHOT",22),("test_network_commands.gd","NETWORK_COMMANDS",12)])
if int(re.search(r"-rc(\d+)",VERSION).group(1))>=13:
    cases.append(("test_area_field_aim.gd","AREA_FIELD_AIM",28))
if int(re.search(r"-rc(\d+)",VERSION).group(1))>=14:
    cases.append(("test_premium_reach.gd","PREMIUM_REACH",16))
if int(re.search(r"-rc(\d+)",VERSION).group(1))>=15:
    cases.extend([("test_healing_events.gd","HEALING_EVENTS",40),("test_ai_budget_planner.gd","AI_BUDGET_PLANNER",246)])
if int(re.search(r"-rc(\d+)",VERSION).group(1))>=16:
    recovery_checks=61 if int(re.search(r"-rc(\d+)",VERSION).group(1))>=17 else 39
    cases.append(("test_ai_budget_recovery.gd","AI_BUDGET_RECOVERY",recovery_checks))
if int(re.search(r"-rc(\d+)",VERSION).group(1))>=17:
    cases.append(("test_hammer_screen_reach.gd","HAMMER_SCREEN_REACH",16))
if int(re.search(r"-rc(\d+)",VERSION).group(1))>=20:
    cases.extend([("test_ai_spell_budget.gd","AI_SPELL_BUDGET",258),("test_ai_income_staging.gd","AI_INCOME_STAGING",72),("test_ai_contact_funding.gd","AI_CONTACT_FUNDING",70)])
if int(re.search(r"-rc(\d+)",VERSION).group(1))>=21:
    cases.append(("test_fog_presentation.gd","FOG_PRESENTATION",1124))
if int(re.search(r"-rc(\d+)",VERSION).group(1))>=22:
    cases.append(("test_observer_camera.gd","OBSERVER_CAMERA",82))
if int(re.search(r"-rc(\d+)",VERSION).group(1))>=23:
    cases.append(("test_ai_economy_bootstrap.gd","AI_ECONOMY_BOOTSTRAP",68))
    cases.extend([("test_ai_bootstrap_investments.gd","AI_BOOTSTRAP_INVESTMENTS",32),("test_core_ai_decisions.gd","CORE_AI_DECISIONS",8),("test_ai_investment.gd","AI_INVESTMENT",8),("test_ai_route_defense.gd","AI_ROUTE_DEFENSE",26)])
if int(re.search(r"-rc(\d+)",VERSION).group(1))>=24:
    cases.extend([("test_paid_fielding_pipeline.gd","PAID_FIELDING_PIPELINE",102),("test_unit_fielding_roles.gd","UNIT_FIELDING_ROLES",48)])
if int(re.search(r"-rc(\d+)",VERSION).group(1))>=25:
    cases.append(("test_stalled_front_recruitment.gd","STALLED_FRONT_RECRUITMENT",48))
if int(re.search(r"-rc(\d+)",VERSION).group(1))>=26:
    cases.extend([("test_road_target_equivalence.gd","ROAD_TARGET_EQUIVALENCE",58576),
                  ("test_marching_query_equivalence.gd","MARCHING_QUERY_EQUIVALENCE",13600),
                  ("test_target_search_equivalence.gd","TARGET_SEARCH_EQUIVALENCE",1441),
                  ("test_frame_contracts.gd","FRAME_CONTRACTS",3263)])
if int(re.search(r"-rc(\d+)",VERSION).group(1))>=27:
    cases.extend([("test_campaign_routes.gd","CAMPAIGN_ROUTES",103595),
                  ("test_leap_blocker_phase.gd","LEAP_BLOCKER_PHASE",1200)])
if int(re.search(r"-rc(\d+)",VERSION).group(1))>=28:
    cases.extend([("test_unit_order_equivalence.gd","UNIT_ORDER_EQUIVALENCE",1200),
                  ("test_axis_target_boundaries.gd","AXIS_TARGET_BOUNDARIES",20)])
if int(re.search(r'-rc(\d+)',VERSION).group(1))>=29:
    cases.append(('test_story_objective_binding.gd','STORY_OBJECTIVES',1616))
if int(re.search(r'-rc(\d+)',VERSION).group(1))>=37:
    cases.extend([('test_distinct_factions.gd','DISTINCT_FACTIONS',3109),('test_unit_actions.gd','UNIT_ACTIONS',4751)])
for filename,marker,expected in cases:
    log=run(filename);count=re.search(re.escape(marker)+r"[: ]+([0-9]+)",log)
    terminal_ok="checks failures []" in log if marker=="FRAME_CONTRACTS" else "failures=[]" in log
    assert count and int(count.group(1))==expected and terminal_ok,log[-2000:]
    tests.append({"test":filename,"test_harness_sha256":sha(ROOT/"game/tests"/filename),"checks":expected,"passed":True})
    print(filename,"EXE embedded pack passed",flush=True)
report={"version":VERSION,"passed":True,"executable_sha256":sha(EXE),"origin":origin,"tests":tests,"scope":"Native Godot loads actual Windows EXE embedded pack; external source harnesses exercise embedded compiled gameplay with no workspace gameplay source present. Origin bytecode/data matches actual APK. Separate six actual EXE launches prove executable startup/UI. Not external script dispatch by PaperWarfront.exe or Android hardware."}
(QA/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

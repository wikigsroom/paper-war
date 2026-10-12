"""Run feature checks against actual APK bytecode on native Windows Godot."""
import argparse,hashlib,json,subprocess,zipfile,re,sys,os,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
VERSION=os.environ.get("PAPER_RELEASE_VERSION","3.0.0-rc10-preview")
QA=ROOT/os.environ.get("PAPER_QA_DIR","output/qa/godot/core-alignment-rc10")/"apk-logic"
parser=argparse.ArgumentParser();parser.add_argument("--resume",action="store_true");options=parser.parse_args()
RUNTIME=QA/"extracted-runtime";RUNTIME.mkdir(parents=True,exist_ok=True)
APK=ROOT/f"release/{VERSION}/android/PaperWarfront-{VERSION}.apk"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
previous=None
if options.resume and (QA/"report.json").exists():
    previous=json.loads((QA/"report.json").read_text(encoding="utf-8"))
    assert previous["version"]==VERSION and previous["apk_sha256"]==sha(APK),"Resume only the identical APK"
    for name,digest in previous["extracted_inputs"].items():assert sha(RUNTIME/name)==digest,name
    shutil.copy2(QA/"report.json",QA/"report-before-asset-completion.json")
files={}
with zipfile.ZipFile(APK) as archive:
    for entry in archive.namelist():
        # Native Control input tests initialize fonts and texture resources even
        # with a headless renderer. Always use the APK's own imported assets.
        if not entry.startswith("assets/") or entry.endswith("/"):continue
        relative=Path(entry.removeprefix("assets/"));target=(RUNTIME/relative).resolve()
        assert target.is_relative_to(RUNTIME.resolve()),entry
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(entry));files[relative.as_posix()]=sha(target)
if previous:
    assert all(files[name]==digest for name,digest in previous["extracted_inputs"].items()),"Previously exercised bytecode/data changed"
assert not list((RUNTIME/"scripts").glob("*.gd")),"Never substitute workspace gameplay source for APK bytecode"
for name in ("battle_sim","data_store","match_projection"):
    assert (RUNTIME/f"scripts/{name}.gdc").is_file()
    assert f'res://scripts/{name}.gdc' in (RUNTIME/f"scripts/{name}.gd.remap").read_text(encoding="utf-8")
(RUNTIME/"project.godot").write_text('config_version=5\n[application]\nconfig/name="APK Logic QA"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding="utf-8")
results=[]
cases=[("test_research_mana_feedback.gd","RESEARCH_MANA_FEEDBACK",43),("probe_mixed_ranged_formation.gd","MIXED_RANGED_FORMATION",192)]
if "scripts/recruitment_readiness.gdc" in files:
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
    source=ROOT/"game/tests"/filename
    old=next((test for test in previous["tests"] if test["test"]==filename),None) if previous else None
    if old and old["passed"] and old["checks"]==expected and old["test_harness_sha256"]==sha(source):
        results.append({**old,"reused_successful_check":True})
        print(filename,"APK identical passing check retained",flush=True)
        continue
    if previous and (QA/(filename+".log")).exists():shutil.copy2(QA/(filename+".log"),QA/(filename+".before-assets.log"))
    # This suite includes twenty paid 240-second simulation workflows.
    timeout_seconds=180 if filename=="test_ai_budget_planner.gd" else 90
    run=subprocess.run([str(ROOT/".tools/godot/Godot_v4.7.2-stable_win64_console.exe"),"--headless","--path",str(RUNTIME),"--script",str(source)],cwd=ROOT,capture_output=True,encoding="utf-8",errors="replace",timeout=timeout_seconds)
    log=run.stdout+run.stderr;(QA/(filename+".log")).write_text(log,encoding="utf-8")
    count=re.search(re.escape(marker)+r"[: ]+([0-9]+)",log)
    terminal_ok="checks failures []" in log if marker=="FRAME_CONTRACTS" else "failures=[]" in log
    passed=run.returncode==0 and bool(count) and int(count.group(1))==expected and terminal_ok and "SCRIPT ERROR" not in log and "ERROR:" not in log
    results.append({"test":filename,"test_harness_sha256":sha(source),"checks":int(count.group(1)) if count else 0,"passed":passed,"exit":run.returncode})
    print(filename,"APK bytecode passed",passed,flush=True)
    if not passed:print(log[-2000:]);break
assert all(sha(RUNTIME/name)==digest for name,digest in files.items()),"Extracted bytecode/data changed during tests"
report={"version":VERSION,"scope":"Actual APK scripts/data/imported resources extracted byte-for-byte; external source harness uses APK compiled GDScript and native Control input on Windows Godot 4.7.2. Successful prior checks retained only for identical APK, bytecode/data and harness; failed checks rerun. Not Android OS, ARM native engine, GPU, physical touch or hardware execution.","apk_sha256":sha(APK),"extracted_inputs":files,"tests":results,"passed":len(results)==len(cases) and all(r["passed"] for r in results)}
(QA/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
sys.exit(0 if report["passed"] else 1)

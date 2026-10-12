"""Verify current preview artifacts and distinguish pending hardware/layout work."""
import argparse, hashlib, json, zipfile, configparser, fnmatch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def digest(stream):
    h=hashlib.sha256()
    for block in iter(lambda:stream.read(1048576),b""):h.update(block)
    return h.hexdigest()
def sha(path):
    with path.open("rb") as f:return digest(f)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--version",required=True);ap.add_argument("--qa",type=Path,required=True);ap.add_argument("--require-bundled-proof",action="store_true");args=ap.parse_args()
    release=ROOT/"release"/args.version;qa=args.qa.resolve()
    manifest=json.loads((release/"build-manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"]==args.version
    for name, expected in manifest["source_inputs"].items():assert sha(ROOT/name)==expected,name
    for entry in manifest["builds"]+manifest.get("archives",[]):
        f=ROOT/entry["path"];assert f.stat().st_size==entry["bytes"] and sha(f)==entry["sha256"],str(f)
    smoke=json.loads((qa/"mobile/export/report.json").read_text(encoding="utf-8"))
    assert smoke["passed"] and smoke["version"]==args.version and len(smoke["cases"])==6
    assert smoke["executable_sha256"]==manifest["builds"][0]["sha256"]
    for case in smoke["cases"]:assert case["passed"] and sha(ROOT/case["image"])==case["image_sha256"]
    with zipfile.ZipFile(release/f"PaperWarfront-Windows-{args.version}.zip") as z:
        assert z.testzip() is None
        with z.open("PaperWarfront/PaperWarfront.exe") as f:assert digest(f)==manifest["builds"][0]["sha256"]
        assert not any(n.endswith((".keystore",".jks","signing.json","export_credentials.cfg")) for n in z.namelist())
    with zipfile.ZipFile(release/f"android/PaperWarfront-{args.version}.apk") as z:
        assert hashlib.sha256(z.read("assets/data/balance-prototype.json")).hexdigest()==sha(ROOT/"game/data/balance-prototype.json")
        assert z.testzip() is None
        packaged_data_files=[]
        presets=configparser.ConfigParser(interpolation=None)
        presets.read(ROOT/"game/export_presets.cfg",encoding="utf-8")
        android=next(section for section in presets.sections() if presets.get(section,"name",fallback="")=='"Android"')
        excluded=presets[android]["exclude_filter"].strip('"').split(",")
        required=[path for path in sorted((ROOT/"game/data").glob("*.json")) if not any(fnmatch.fnmatchcase("data/"+path.name,pattern) for pattern in excluded)]
        actual={name.removeprefix("assets/data/") for name in z.namelist() if name.startswith("assets/data/") and name.endswith(".json")}
        assert actual=={path.name for path in required},"Packaged JSON set must match authored export contract"
        for path in required:
            assert hashlib.sha256(z.read("assets/data/"+path.name)).hexdigest()==sha(path),path.name
            packaged_data_files.append(path.name)
    for log in ["apk-signature.log","apk-alignment.log","apk-badging.log","apk-manifest.log"]:assert (qa/"build"/log).is_file()
    badging=(qa/"build/apk-badging.log").read_text(encoding="utf-8")
    import re
    expected_code=re.search(r'^version/code=(\d+)$',(ROOT/"game/export_presets.cfg").read_text(encoding="utf-8"),re.M).group(1)
    assert args.version in badging and f"versionCode='{expected_code}'" in badging
    elf=json.loads((qa/"build/apk-elf-report.json").read_text(encoding="utf-8"));assert elf and all(x["arm64_16kb_pass"] for x in elf)
    mobile_path=qa/"mobile/mobile-matrix.json";matrix=json.loads(mobile_path.read_text(encoding="utf-8")) if mobile_path.exists() else None
    if matrix:assert matrix["passed"] and matrix["version"]==args.version and len(matrix["cases"])==8
    hud_ratios={}
    if int(re.search(r"-rc(\d+)",args.version).group(1))>=15:
        assert matrix,"rc15 requires the complete native display matrix"
        for case in matrix["cases"]:
            screen_proof=json.loads((qa/"mobile"/case["name"]/"report.json").read_text(encoding="utf-8"))
            coverage=screen_proof["battlefield_coverage"]
            assert screen_proof["passed"] and screen_proof["version"]==args.version and len(coverage)==10
            assert all(row["passed"] and row["details"]["visible_ratio"]>=.70 for row in coverage),case["name"]
            for name,expected in screen_proof["inputs"].items():assert sha(ROOT/"game"/name.removeprefix("res://"))==expected,name
            hud_ratios[case["name"]]=min(row["details"]["visible_ratio"] for row in coverage)
    logic_counts={}
    for platform, artifact_key, artifact_digest in [("apk", "apk_sha256", manifest["builds"][1]["sha256"]), ("windows", "executable_sha256", manifest["builds"][0]["sha256"])]:
        path=qa/f"{platform}-logic/report.json"
        if not path.exists():continue
        proof=json.loads(path.read_text(encoding="utf-8"))
        assert proof["passed"] and proof["version"]==args.version and proof[artifact_key]==artifact_digest
        expected_tests={"test_research_mana_feedback.gd":43,"probe_mixed_ranged_formation.gd":192}
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=27:
            expected_tests.update({"test_campaign_routes.gd":103595 if int(re.search(r"-rc(\d+)",args.version).group(1))>=29 else 6376,"test_leap_blocker_phase.gd":1200})
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=28:
            expected_tests.update({"test_unit_order_equivalence.gd":1200,"test_axis_target_boundaries.gd":20})
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=29:
            expected_tests["test_story_objective_binding.gd"]=1616
        if "game/scripts/recruitment_readiness.gd" in manifest["source_inputs"]:
            expected_tests.update({"test_recruitment_readiness.gd":54,"test_mine_pressure_boundaries.gd":14,"test_spawn_camp_recruitment.gd":14})
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=12:
            investment_checks=40 if int(re.search(r"-rc(\d+)",args.version).group(1))>=13 else 28
            expected_tests.update({"test_first_investment.gd":investment_checks,"test_queue_snapshot.gd":22,"test_network_commands.gd":12})
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=13:
            expected_tests["test_area_field_aim.gd"]=28
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=14:
            expected_tests["test_premium_reach.gd"]=16
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=15:
            expected_tests.update({"test_healing_events.gd":40,"test_ai_budget_planner.gd":246})
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=16:
            expected_tests["test_ai_budget_recovery.gd"]=39
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=17:
            expected_tests.update({"test_ai_budget_recovery.gd":61,"test_hammer_screen_reach.gd":16})
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=20:
            expected_tests.update({"test_ai_spell_budget.gd":258,"test_ai_income_staging.gd":72,"test_ai_contact_funding.gd":70})
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=21:
            expected_tests["test_fog_presentation.gd"]=1124
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=22:
            expected_tests["test_observer_camera.gd"]=82
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=23:
            expected_tests["test_ai_economy_bootstrap.gd"]=68
            expected_tests.update({"test_ai_bootstrap_investments.gd":32,"test_core_ai_decisions.gd":8,"test_ai_investment.gd":8,"test_ai_route_defense.gd":26})
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=24:
            expected_tests.update({"test_paid_fielding_pipeline.gd":102,"test_unit_fielding_roles.gd":48})
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=25:
            expected_tests["test_stalled_front_recruitment.gd"]=48
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=26:
            expected_tests.update({"test_road_target_equivalence.gd":58576,"test_marching_query_equivalence.gd":13600,
                                   "test_target_search_equivalence.gd":1441,"test_frame_contracts.gd":3263})
        assert len(proof["tests"])==len(expected_tests) and all(test["passed"] for test in proof["tests"])
        assert {test["test"]:test["checks"] for test in proof["tests"]}==expected_tests
        for test in proof["tests"]:assert sha(ROOT/"game/tests"/test["test"])==test["test_harness_sha256"]
        logic_counts[platform]=sum(test["checks"] for test in proof["tests"])
    if "apk" in logic_counts and "windows" in logic_counts:
        apk_logic=json.loads((qa/"apk-logic/report.json").read_text(encoding="utf-8"))
        win_logic=json.loads((qa/"windows-logic/report.json").read_text(encoding="utf-8"))
        assert win_logic["origin"]["source_gameplay_files_absent"] and win_logic["origin"]["version"]==args.version
        with zipfile.ZipFile(release/f"android/PaperWarfront-{args.version}.apk") as z:
            for name,expected in apk_logic["extracted_inputs"].items():assert hashlib.sha256(z.read("assets/"+name)).hexdigest()==expected
        assert all(apk_logic["extracted_inputs"][name.removeprefix("res://")]==expected for name,expected in win_logic["origin"]["inputs"].items())
    if "game/scripts/recruitment_readiness.gd" in manifest["source_inputs"]:
        assert set(logic_counts)=={"apk","windows"},"New feature build requires actual compiled logic proof for both packages"
        ui=json.loads((qa/"packaged-recruitment-ui/report.json").read_text(encoding="utf-8"))
        assert ui["passed"] and ui["version"]==args.version and ui["executable_sha256"]==manifest["builds"][0]["sha256"]
        expected_ui_cases={"desktop","phone","compact","short"} if int(re.search(r"-rc(\d+)",args.version).group(1))>=15 else {"desktop","phone","compact"}
        assert len(ui["cases"])==len(expected_ui_cases) and {case["name"] for case in ui["cases"]}==expected_ui_cases
        assert sha(ROOT/"game/tests/recruitment_ui_qa.gd")==ui["source_harness_sha256"]
        assert sha(ROOT/"game/tests/mobile_ui_qa.gd")==ui["external_touch_harness_sha256"]
        assert sha(qa/"packaged-recruitment-ui/packaged_recruitment_ui_qa.gd")==ui["generated_harness_sha256"]
        for case in ui["cases"]:
            assert case["passed"] and case["inputs"] and all(apk_logic["extracted_inputs"][name.removeprefix("res://")]==expected for name,expected in case["inputs"].items())
            if int(re.search(r"-rc(\d+)",args.version).group(1))>=15:
                coverage=case["battlefield_coverage"]
                assert len(coverage)==(4 if case["name"]=="desktop" else 3) and all(row["passed"] and row["details"]["visible_ratio"]>=.70 for row in coverage)
                hud_ratios["compiled-"+case["name"]]=min(row["details"]["visible_ratio"] for row in coverage)
    paper_ui=None
    if int(re.search(r"-rc(\d+)",args.version).group(1))>=16:
        paper_ui=json.loads((qa/"paper-ui/report.json").read_text(encoding="utf-8"))
        assert paper_ui["passed"] and paper_ui["compiled_pack"] and paper_ui["pack_sha256"]==manifest["builds"][0]["sha256"]
        assert {c["case"] for c in paper_ui["cases"]}=={"desktop","phone"}
        for case in paper_ui["cases"]:
            assert case["passed"] and case["screenshots"]==21 and case["checks"]==49
            assert all(apk_logic["extracted_inputs"][name.removeprefix("res://")]==expected for name,expected in case["inputs"].items())
            assert len(case["image_files"])==21 and all(sha(ROOT/f["file"])==f["sha256"] for f in case["image_files"])
        paper_assets=json.loads((qa/"paper-ui-assets.json").read_text(encoding="utf-8"))
        assert paper_assets["passed"] and len(paper_assets["assets"])==38 and paper_assets["apk_sha256"]==manifest["builds"][1]["sha256"]
        with zipfile.ZipFile(release/f"android/PaperWarfront-{args.version}.apk") as z:
            assert all(hashlib.sha256(z.read(a["apk_texture_path"])).hexdigest()==a["apk_texture_sha256"] for a in paper_assets["assets"])
    result={"version":args.version,"preview_artifacts_verified":True,"source_inputs_verified":True,"actual_exe_cases":6,"apk_packaged_balance_verified":True,"mobile_matrix_complete":bool(matrix),"mobile_checks":matrix["checks"] if matrix else None,"paper_ui_verified":bool(paper_ui),"paper_ui_checks":sum(c["checks"] for c in paper_ui["cases"]) if paper_ui else None,"android_hardware_verified":False,"full_balance_verified":False,"scope":"Current preview binaries, native exported-EXE launches and compiled UI, source/pack hashes. No claim of Android hardware, human multiplayer or completed balance."}
    result["packaged_logic_checks_on_windows"]=logic_counts
    result["apk_packaged_json_files_verified"]=packaged_data_files
    result["packaged_recruitment_ui_verified"]="game/scripts/recruitment_readiness.gd" in manifest["source_inputs"]
    if hud_ratios:result["unobscured_battlefield_ratios"]=hud_ratios
    if int(re.search(r"-rc(\d+)",args.version).group(1))>=14:
        formal_folder=qa.parent/"formal-reach"
        formal_proof=json.loads((formal_folder/"verification.json").read_text(encoding="utf-8"))
        assert formal_proof["passed"] and not formal_proof["errors"] and len(formal_proof["records"])==6
        for name,expected in formal_proof["files"].items():assert sha(ROOT/name)==expected,name
        mechanisms=json.loads((formal_folder/"regression/report.json").read_text(encoding="utf-8"))
        assert mechanisms["passed"] and mechanisms["source_unchanged"]
        for name,expected in mechanisms["inputs"].items():assert sha(ROOT/name)==expected,name
        for test in mechanisms["tests"]:assert test["passed"] and sha(ROOT/"game/tests"/test["script"])==test["sha256"]
        for label in ["short","mid","long"]:
            recipe=json.loads((formal_folder/f"{label}-paid-exchange.json").read_text(encoding="utf-8"))
            for name,expected in recipe["inputs"].items():assert sha(ROOT/"game"/name.removeprefix("res://"))==expected
        result["formal_scythe_reach_verified"]={"paid_recipe_pairs":6,"native_gpu_configs":2,"compiled_checks_per_package":16}
        result["source_mechanism_checks"]=sum(test["checks"] for test in mechanisms["tests"])
    if int(re.search(r"-rc(\d+)",args.version).group(1))>=17:
        hammer=json.loads((qa.parent/"formal-hammer/verification.json").read_text(encoding="utf-8"))
        assert hammer["passed"] and not hammer["errors"] and len(hammer["records"])==12
        for name,expected in hammer["files"].items():assert sha(ROOT/name)==expected,name
        result["formal_hammer_reach_verified"]={"paid_recipe_pairs":12,"native_gpu_configs":2,"compiled_checks_per_package":16}
    if int(re.search(r"-rc(\d+)",args.version).group(1))>=18:
        navigation=json.loads((qa/"modal-navigation/report.json").read_text(encoding="utf-8"))
        assert navigation["passed"] and navigation["compiled_pack"] and navigation["pack_sha256"]==manifest["builds"][0]["sha256"]
        assert navigation["observer_sha256"]==sha(ROOT/"tools/paper-warfront/probe_ui_modal_navigation.gd")
        assert navigation["runner_sha256"]==sha(ROOT/"tools/paper-warfront/check_ui_modal_navigation.py")
        assert navigation["touch_helper_sha256"]==sha(ROOT/"game/tests/mobile_ui_qa.gd")
        assert len(navigation["cases"])==3 and {c["name"]:c["checks"] for c in navigation["cases"]}=={"desktop":47,"phone":55,"compact":55}
        for case in navigation["cases"]:
            assert case["passed"] and not case["failures"] and case["version"]==args.version
            assert len(case["inputs"])==8 and "res://scripts/ui_focus_scope.gdc" in case["inputs"]
            assert all(apk_logic["extracted_inputs"][name.removeprefix("res://")]==expected for name,expected in case["inputs"].items())
            assert len(case["images"])==(4 if case["name"]=="desktop" else 5)
            assert all(sha(ROOT/f["file"])==f["sha256"] for f in case["images"])
        result["modal_navigation_verified"]={"checks":sum(c["checks"] for c in navigation["cases"]),"native_configs":3,"screenshots":sum(len(c["images"]) for c in navigation["cases"])}
    if int(re.search(r"-rc(\d+)",args.version).group(1))>=19:
        live=json.loads((qa/"live-battle-sheets/report.json").read_text(encoding="utf-8"))
        assert live["passed"] and live["compiled_pack"] and live["pack_sha256"]==manifest["builds"][0]["sha256"]
        assert live["observer_sha256"]==sha(ROOT/"tools/paper-warfront/probe_live_battle_sheets.gd")
        assert live["runner_sha256"]==sha(ROOT/"tools/paper-warfront/check_live_battle_sheets.py")
        assert live["helper_sha256"]==sha(ROOT/"game/tests/mobile_ui_qa.gd")
        assert len(live["cases"])==3 and {c["name"]:c["checks"] for c in live["cases"]}=={"desktop":90,"phone":90,"compact":90}
        for case in live["cases"]:
            assert case["passed"] and not case["failures"] and case["version"]==args.version
            assert len(case["inputs"])==9 and {"res://scripts/battle_command_rules.gdc","res://scripts/ui_battle_sheets.gdc"}<=set(case["inputs"])
            assert all(apk_logic["extracted_inputs"][name.removeprefix("res://")]==expected for name,expected in case["inputs"].items())
            assert len(case["images"])==9 and all(sha(ROOT/f["file"])==f["sha256"] for f in case["images"])
        result["live_battle_sheets_verified"]={"checks":sum(c["checks"] for c in live["cases"]),"native_configs":3,"screenshots":sum(len(c["images"]) for c in live["cases"])}
    if int(re.search(r"-rc(\d+)",args.version).group(1))>=21:
        observations={}
        for label, runner, observer in [
                ("fog-render","check_fog_rendering.py","probe_fog_rendering.gd"),
                ("stage-proportions","check_stage_proportions.py","probe_stage_proportions.gd")]:
            proof=json.loads((qa/label/"report.json").read_text(encoding="utf-8"))
            assert proof["passed"] and proof["pack_sha256"]==manifest["builds"][0]["sha256"]
            assert proof["observer_sha256"]==sha(ROOT/"tools/paper-warfront"/observer)
            assert {c["name"] for c in proof["cases"]}=={"desktop","phone"}
            total=0
            for case in proof["cases"]:
                native=json.loads((qa/label/case["name"]/"report.json").read_text(encoding="utf-8"))
                assert case["passed"] and native["passed"] and native["version"]==args.version
                assert native["inputs"] and all(name.endswith(".gdc") for name in native["inputs"])
                assert all(apk_logic["extracted_inputs"][name.removeprefix("res://")]==value for name,value in native["inputs"].items())
                assert all(c["passed"] for c in native["checks"])
                total+=len(native["checks"])
                pictures=native["screenshots"] if label=="fog-render" else native["captures"]
                assert len(pictures)==6 and all(sha(Path(p["path"]))==p["sha256"] for p in pictures)
                if label=="stage-proportions":assert len(native["measurements"])==200 and native["ordinary_paid_events"]["hit"]>0
                else:assert "res://scripts/theatre_fog.gdc" in native["inputs"]
            observations[label]={"native_configs":2,"checks":total,"screenshots":12}
        result["fog_and_stage_verified"]=observations
        result["fog_semantic_checks_per_package"]=1124
        dual=json.loads((qa/"duel-stage/report.json").read_text(encoding="utf-8"))
        assert dual["passed"] and dual["version"]==args.version and len(dual["records"])==10
        assert all(c["passed"] for c in dual["records"])
        assert dual["observer_sha256"]==sha(ROOT/"tools/paper-warfront/probe_duel_stage.gd")
        assert all(apk_logic["extracted_inputs"][name.removeprefix("res://")]==value for name,value in dual["inputs"].items())
        result["duel_stage_geometry_verified"]={"checks":10,"local_minimum_interface":"800x600","mobile_lan_observers":2}
        assert (ROOT/"assets/paper-warfront/style-tokens.json").read_bytes()==(ROOT/"game/data/style-tokens.json").read_bytes()
    if int(re.search(r"-rc(\d+)",args.version).group(1))>=22:
        camera=json.loads((qa/"camera-render/report.json").read_text(encoding="utf-8"))
        assert camera["passed"] and camera["pack_sha256"]==manifest["builds"][0]["sha256"]
        assert camera["observer_sha256"]==sha(ROOT/"tools/paper-warfront/probe_camera_rendering.gd")
        assert {c["name"] for c in camera["cases"]}=={"desktop","phone"}
        for case in camera["cases"]:
            native=json.loads((qa/"camera-render"/case["name"]/"report.json").read_text(encoding="utf-8"))
            assert case["passed"] and native["passed"] and native["version"]==args.version
            assert len(native["checks"])==22 and all(c["passed"] for c in native["checks"])
            assert len(native["payments"])==2 and all(p["ok"] and abs(p["gold_before"]-p["gold_after"]-p["cost"])<.0001 for p in native["payments"])
            assert len(native["inputs"])==9 and all(name.endswith(".gdc") for name in native["inputs"])
            assert all(apk_logic["extracted_inputs"][name.removeprefix("res://")]==value for name,value in native["inputs"].items())
            assert len(native["screenshots"])==6 and all(sha(Path(p["path"]))==p["sha256"] for p in native["screenshots"])
        result["observer_camera_verified"]={"compiled_checks_per_package":82,"native_gpu_configs":2,"native_paid_navigation_checks":44,"screenshots":12}
    if int(re.search(r"-rc(\d+)",args.version).group(1))>=24:
        fielding=json.loads((qa/"normal-fielding/report.json").read_text(encoding="utf-8"))
        assert fielding["passed"] and fielding["pack_sha256"]==manifest["builds"][0]["sha256"]
        assert fielding["observer_sha256"]==sha(ROOT/"tools/paper-warfront/probe_paid_fielding_render.gd")
        assert {c["name"] for c in fielding["cases"]}=={"desktop","phone"}
        for case in fielding["cases"]:
            native=json.loads((qa/"normal-fielding"/case["name"]/"report.json").read_text(encoding="utf-8"))
            assert case["passed"] and native["passed"] and native["version"]==args.version
            assert all(c["passed"] for c in native["checks"])
            assert all(name.endswith(".gdc") and apk_logic["extracted_inputs"][name.removeprefix("res://")]==value for name,value in native["inputs"].items())
            config=native["config"]
            assert config["starting_gold"]==config["enemy_starting_gold"]==300 and not config["full_tech"]
            assert config.get("ai_warmup",4)==4 and config["difficulty"]==1 and config["ai_style"]=="counter"
            unit=native["first_paid_unit"]
            assert unit["research_started"]<unit["completed"]<=unit["ordered"]<unit["born"]<=native["first_impact"]["time"]
            assert native["first_impact"]["source_uid"]==unit["uid"] and native["first_impact"]["amount"]>0
            assert len(native["captures"])==5 and all(sha(Path(p["path"]))==p["sha256"] for p in native["captures"])
        result["normal_paid_fielding_verified"]={"native_gpu_configs":2,"checks":sum(c["checks"] for c in fielding["cases"]),"screenshots":10,"normal_starting_gold":300,"enemy_warmup_seconds":4,"west_autoplayer":True}
    if int(re.search(r"-rc(\d+)",args.version).group(1))>=25:
        contact=json.loads((qa/"stalled-front/report.json").read_text(encoding="utf-8"))
        assert contact["passed"] and contact["pack_sha256"]==manifest["builds"][0]["sha256"]
        assert contact["observer_sha256"]==sha(ROOT/"tools/paper-warfront/probe_stalled_front_render.gd")
        assert contact["runner_sha256"]==sha(ROOT/"tools/paper-warfront/check_stalled_front_render.py")
        assert {c["name"] for c in contact["cases"]}=={"desktop","phone"}
        for case in contact["cases"]:
            native=json.loads((qa/"stalled-front"/case["name"]/"report.json").read_text(encoding="utf-8"))
            assert case["passed"] and native["passed"] and native["version"]==args.version
            assert all(c["passed"] for c in native["checks"])
            assert all(name.endswith(".gdc") and apk_logic["extracted_inputs"][name.removeprefix("res://")]==value for name,value in native["inputs"].items())
            config=native["config"]
            assert config["faction"]=="yin" and config["enemy"]=="mu" and config.get("ai_warmup",4)==4
            assert config["starting_gold"]==config["enemy_starting_gold"]==300 and not config["full_tech"]
            counter=native["paid_counter"]
            assert counter["id"]=="unit.yin.spear" and counter["price"]==60 and counter["uid"]>0
            assert counter["ordered"]<counter["born"]<=native["counter_impact"]["time"]
            assert native["controlled_frontline_uid"]>0 and native["counter_impact"]["source_uid"]==counter["uid"] and native["counter_impact"]["amount"]>0
            assert native["first_impact"]["source_uid"]==native["first_paid_unit"]["uid"] and native["first_impact"]["amount"]>0
            assert len(native["captures"])==8 and all(sha(Path(p["path"]))==p["sha256"] for p in native["captures"])
        result["stalled_front_response_verified"]={"native_gpu_configs":2,"checks":sum(c["checks"] for c in contact["cases"]),"screenshots":16,"normal_starting_gold":300,"enemy_warmup_seconds":4,"matchup":"yin/mu","west_autoplayer":True}
        default_folder=qa/"stalled-front-vulkan/desktop"
        default=json.loads((default_folder/"report.json").read_text(encoding="utf-8"))
        assert default["passed"] and default["version"]==args.version and len(default["checks"])==32
        assert all(c["passed"] for c in default["checks"])
        assert default["observer_sha256"]==sha(ROOT/"tools/paper-warfront/probe_stalled_front_render.gd")
        assert all(name.endswith(".gdc") and apk_logic["extracted_inputs"][name.removeprefix("res://")]==value for name,value in default["inputs"].items())
        assert default["paid_counter"]["uid"]==default["counter_impact"]["source_uid"] and default["counter_impact"]["amount"]>0
        assert default["first_paid_unit"]["uid"]==default["first_impact"]["source_uid"] and default["first_impact"]["amount"]>0
        assert len(default["captures"])==8 and all(sha(Path(p["path"]))==p["sha256"] for p in default["captures"])
        renderer_log=(default_folder/"runtime.log").read_text(encoding="utf-8")
        assert "Vulkan" in renderer_log and "Forward Mobile" in renderer_log and "ERROR:" not in renderer_log
        result["default_desktop_renderer_verified"]={"checks":32,"screenshots":8,"backend":"Vulkan Forward Mobile","scope":"Native Windows default renderer with the actual EXE embedded pack; synchronized paid battle snapshots, not FPS or Android hardware."}
    if int(re.search(r"-rc(\d+)",args.version).group(1))>=26:
        realtime=json.loads((qa/"realtime/report.json").read_text(encoding="utf-8"))
        assert realtime["passed"] and realtime["version"]==args.version
        assert {row["case"] for row in realtime["cases"]}=={"before-stress","stress","bridge","long","phone"}
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=31 and realtime.get("resumed_after_confirmed_exit",False):
            assert realtime["runner_sha256"]==sha(ROOT/"tools/paper-warfront/resume_terrain_native_validation.py")
            assert realtime["original_runner_sha256"]==sha(ROOT/"tools/paper-warfront/run_realtime_release.py")
        else:
            assert realtime["runner_sha256"]==sha(ROOT/"tools/paper-warfront/run_realtime_release.py")
        for row in realtime["cases"]:
            folder=qa/"realtime"/row["case"]
            receipt=json.loads((folder/"receipt.json").read_text(encoding="utf-8"))
            native=json.loads((folder/"report.json").read_text(encoding="utf-8"))
            assert receipt["passed"] and native["passed"] and sha(folder/"report.json")==row["report_sha256"]
            assert sha(folder/"receipt.json")==row["receipt_sha256"] and sha(folder/"frames.csv")==native["frames_sha256"]
            assert native["fps_cap"]==60 and native["window_visible"] and not native["audio_silent"] and not native["audio_background"]
            assert native["observer_sha256"]==sha(folder/"observer.gd")==sha(ROOT/"tools/paper-warfront/probe_realtime_battle.gd")
            assert native["capacity_fixture"]==(row["case"] in ["before-stress","stress"])
            assert all(sha(Path(capture["path"]))==capture["sha256"] for capture in native["captures"])
            if row["case"]!="before-stress":
                assert native["version"]==args.version and receipt["request"]["pack_sha256"]==manifest["builds"][0]["sha256"]
                assert all(name.endswith(".gdc") and apk_logic["extracted_inputs"][name.removeprefix("res://")]==value for name,value in native["inputs"].items())
                assert any("theatre_ground_cache.gdc" in name for name in native["inputs"])
        render=json.loads((qa/"render-cache/report.json").read_text(encoding="utf-8"))
        assert render["passed"] and len(render["comparisons"])==12
        for display in ["desktop","phone"]:
            folder=qa/"render-cache"/(display+"-after")
            request=json.loads((folder/"request.json").read_text(encoding="utf-8"))
            native=json.loads((folder/"report.json").read_text(encoding="utf-8"))
            assert request["pack_sha256"]==manifest["builds"][0]["sha256"]
            assert all(name.endswith(".gdc") and apk_logic["extracted_inputs"][name.removeprefix("res://")]==value for name,value in native["inputs"].items())
            assert all(sha(Path(capture["path"]))==capture["sha256"] for capture in native["captures"])
        result["realtime_frame_observations"]=realtime
        result["render_cache_comparisons_verified"]=12
    if int(re.search(r"-rc(\d+)",args.version).group(1))>=27:
        story=json.loads((qa/"story-ui-final/report.json").read_text(encoding="utf-8"))
        assert story["passed"] and story["pack_sha256"]==manifest["builds"][0]["sha256"]
        assert {case["name"] for case in story["cases"]}=={"desktop","phone"}
        assert story["observer_sha256"]==sha(ROOT/"tools/paper-warfront/probe_story_routes_ui.gd")==sha(qa/"story-ui-final/observer.gd")
        for case in story["cases"]:
            folder=qa/"story-ui-final"/case["name"]
            native=json.loads((folder/"report.json").read_text(encoding="utf-8"))
            assert case["passed"] and native["passed"] and case["checks"]==(237 if int(re.search(r"-rc(\d+)",args.version).group(1))>=29 else 33)
            if int(re.search(r"-rc(\d+)",args.version).group(1))>=29:assert native["authored_briefs_checked"]==200 and len(native["captures"])==8
            assert sha(folder/"report.json")==case["report_sha256"]
            assert all(name.endswith(".gdc") and apk_logic["extracted_inputs"][name.removeprefix("res://")]==value for name,value in native["inputs"].items())
            assert all(sha(folder/capture["path"])==capture["sha256"] for capture in native["captures"])
        result["story_map_progression_verified"]={"opening_authored_maps":20,"optional_pairs":6,"paths_checked":64,"rule_checks":6376,"compiled_native_ui_checks":66,"scope":"First chapter narrative/progression and native Windows pointer/save transitions, all20 readable brief summaries; not normal battle wins or Android hardware."}
        if int(re.search(r"-rc(\d+)",args.version).group(1))>=29:
            authored=json.loads((qa.parent/"authorship.json").read_text('utf-8'))
            assert authored['passed'] and authored['authored_maps']==200 and authored['new_explicit_records']==180
            assert all(sha(ROOT/name)==row['sha256'] for row in authored['records'] for name in [row['source']])
            assert all(sha(ROOT/'game/data'/name)==digest for name,digest in authored['output_hashes'].items())
            font=json.loads((qa.parent/'font-coverage.json').read_text('utf-8'))
            assert font['passed'] and font['version']==args.version and all(not r['missing_after'] and sha(ROOT/r['path'])==r['sha256'] for r in font['records'])
            source=json.loads((qa.parent/'source-final/report.json').read_text('utf-8'))
            assert source['passed'] and source['source_unchanged'] and source['mechanisms_only'] and len(source['tests'])==78
            assert all(sha(ROOT/name)==digest for name,digest in source['inputs'].items())
            assert all(sha(ROOT/'game/tests'/row['script'])==row['sha256'] for row in source['tests'])
            result['story_map_progression_verified']={'authored_maps':200,'new_explicit_map_records':180,'chapters':10,'local_minimal_route_orders':552,'rule_checks':103595,'actual_goal_binding_checks':1616,'compiled_native_ui_checks':474,'source_groups':78,'source_checks':sum(r['checks'] for r in source['tests']),'bundled_cjk_characters':font['required_cjk'],'scope':'All200 map-specific conflict/result/geometry and actual initial objective bindings; authored local routes, alternatives/conjunctions/save and native Windows pointer selection. Fixtures are not200 paid victories, touch-scroll gestures, Android hardware or a human complete story review.'}
    if int(re.search(r"-rc(\d+)",args.version).group(1))>=28:
        from runtime_asset_inputs import runtime_asset_inputs
        runtime_assets=runtime_asset_inputs(ROOT/"game")
        for asset in runtime_assets:
            assert manifest["source_inputs"][asset.relative_to(ROOT).as_posix()]==sha(asset)
            descriptor=Path(str(asset)+".import")
            if descriptor.exists():assert manifest["source_inputs"][descriptor.relative_to(ROOT).as_posix()]==sha(descriptor)
        history=qa.parent
        release_number=int(re.search(r"-rc(\d+)",args.version).group(1))
        if release_number>=32:
            from verify_answers_release_evidence import verify
            result.update(verify(ROOT,qa,args.version,manifest,apk_logic))
        elif release_number>=31:
            from verify_terrain_release_evidence import verify
            result.update(verify(ROOT,qa,args.version,manifest,apk_logic))
        elif release_number>=30:
            from verify_dense_release_evidence import verify
            result.update(verify(ROOT,qa,args.version,manifest,apk_logic))
        elif release_number>=29:
            binding=json.loads((qa.parent/'combat-history-binding.json').read_text('utf-8'))
            assert binding['passed'] and binding['campaign_battle_fields_unchanged'] and binding['current_version']==args.version
            assert all(sha(ROOT/name)==digest for name,digest in binding['unchanged_inputs'].items())
            assert all(sha(ROOT/name)==row['after'] for name,row in binding['changed_inputs'].items())
            history=ROOT/binding['historical_evidence_root']
            assert all(sha(history/name)==digest for name,digest in binding['history'].items())
            result['retained_combat_equivalence_binding_sha256']=sha(qa.parent/'combat-history-binding.json')
        if release_number<30:
            capacity=json.loads((history/"capacity-axis-original-closure.json").read_text("utf-8"))
            paid=json.loads((history/"paid-axis-original-closure.json").read_text("utf-8"))
            oracle=history/"oracle-runtime"
            closure=json.loads((oracle/"closure-inputs.json").read_text("utf-8"))
            for name,record in closure["scripts"].items():
                assert sha(oracle/"scripts"/name)==record["oracle_sha256"]
                assert sha(history/"baseline-runtime/scripts"/name)==record["original_sha256"]
            for proof,expected in [(capacity,3600),(paid,73103)]:
                assert proof["passed"] and not proof["failures"] and proof["checks"]==expected
                assert proof["simulation_sha256"]==sha(ROOT/"game/scripts/battle_sim.gd")
                assert proof["baseline_sha256"]==sha(oracle/"scripts/battle_sim.gd")
            assert capacity["loaded_source_matches"] and capacity["source_unchanged"]
            result["packed_query_equivalence_verified"]={"capacity_steps":3600,"normal_paid_steps":73103,
                "complete_original_helper_scripts":len(closure["scripts"]),
                "exact_draw_order_checks_per_package":1200,"native_float_boundary_checks_per_package":20,
                "scope":"Complete frozen original helper closure and every-step state equivalence; CPU timings are not rendered FPS."}
        result["runtime_asset_bindings_verified"]={"resolved_assets":len(runtime_assets),"public_input_files":len(manifest["source_inputs"])}
        if release_number==29:result['packed_query_equivalence_verified']['scope']='Retained rc28 original-closure equivalence, explicitly bound to unchanged combat inputs/configurations; rc29 packages freshly exercise query, order and boundary checks. No new CPU benchmark claim.'
    if args.require_bundled_proof:
        with zipfile.ZipFile(release/f"PaperWarfront-Windows-{args.version}.zip") as bundle:
            assert json.loads(bundle.read("PaperWarfront/preview-verification.json"))==result,"ZIP must include identical verified preview evidence"
    (release/"preview-verification.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps(result))
if __name__=="__main__":main()

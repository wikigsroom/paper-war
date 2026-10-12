"""Write the RC37 visibility-cache proof, docs and immutable revision index."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
VERSION="3.0.0-rc37-preview"
QA=ROOT/"output/qa/godot/render-runtime-rc37"
RELEASE=ROOT/"release"/VERSION

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def read(path: Path):
    return json.loads(path.read_text("utf-8"))

manifest=read(RELEASE/"build-manifest.json")
assert manifest["version"]==VERSION
for row in manifest["builds"]+manifest.get("archives",[]):
    path=ROOT/row["path"]
    assert path.is_file() and sha(path)==row["sha256"],path
for name,digest in manifest["source_inputs"].items():
    assert sha(ROOT/name)==digest,name

story=read(ROOT/"output/qa/paper-warfront/story-map-contract.json")
routes=read(ROOT/"output/qa/paper-warfront/campaign-routes-rc37.json")
apk=read(QA/"final-route-graph-v2-packaged/apk-logic/report.json")
windows=read(QA/"final-route-graph-v2-packaged/windows-logic/report.json")
stress=read(QA/"final-route-graph-v2-stress-clean/report.json")
phone=read(QA/"final-route-graph-v2-phone-clean/report.json")
stress_receipt=read(QA/"final-route-graph-v2-stress-clean/receipt.json")
phone_receipt=read(QA/"final-route-graph-v2-phone-clean/receipt.json")
mobile=read(QA/"final-route-graph-mobile-root/mobile/mobile-matrix.json")
native_export=read(QA/"final-route-graph-v2/mobile/export/report.json")
story_ui=read(QA/"final-route-graph-v2-story-ui/desktop/report.json")
assert story["passed"] and story["maps"]==200 and story["chapters"]==10 and story["checks"]>=6531
assert routes["checks"]==103595 and not routes["failures"]
assert apk["passed"] and windows["passed"]
assert stress["passed"] and phone["passed"]
assert mobile["passed"] and len(mobile["cases"])==8
assert native_export["passed"] and len(native_export["cases"])==6
assert story_ui["passed"] and story_ui["checks"]==237 and story_ui["authored_briefs_checked"]==200

source_tests=[
    ("test_visibility_refresh_cache.gd",15),
    ("test_visibility_refresh_equivalence.gd",1712),
    ("test_core_visibility.gd",14),
    ("test_fog_presentation.gd",1124),
    ("test_visibility_graph_equivalence.gd",1932),
    ("test_firing_visibility.gd",21),
    ("test_combat_ownership.gd",154),
    ("test_worker_actions.gd",121),
    ("test_world_combat.gd",370),
    ("test_distinct_factions.gd",3109),
    ("test_unit_actions.gd",4751),
    ("test_map_transport.gd",37),
    ("test_campaign_routes.gd",103595),
    ("test_story_objective_binding.gd",1616),
    ("test_campaign_director.gd",4200),
]
source_rows=[{"test":name,"checks":checks,"harness_sha256":sha(ROOT/"game/tests"/name)} for name,checks in source_tests]
exe=next(row for row in manifest["builds"] if row["path"].endswith("PaperWarfront.exe"))
apk_build=next(row for row in manifest["builds"] if row["path"].endswith(".apk"))
archive=manifest["archives"][0]

verification={
    "version":VERSION,
    "preview_artifacts_verified":True,
    "source_inputs_verified":True,
    "builds":manifest["builds"],
    "archives":manifest.get("archives",[]),
    "story_map_contract":{"maps":story["maps"],"chapters":story["chapters"],"branch_nodes":story["branch_nodes"],"merge_nodes":story["merge_nodes"],"forked_geometry_maps":story["forked_geometry_maps"],"unequal_route_length_maps":story["unequal_route_length_maps"],"checks":story["checks"]},
    "campaign_routes":{"checks":routes["checks"],"opening_paths":routes["opening_paths"],"local_route_orders":routes["local_route_orders"]},
    "source_tests":source_rows,
    "packaged_logic":{"apk_checks":sum(row["checks"] for row in apk["tests"]),"windows_checks":sum(row["checks"] for row in windows["tests"]),"apk_tests":len(apk["tests"]),"windows_tests":len(windows["tests"]),"apk_sha256":apk["apk_sha256"],"windows_sha256":windows["executable_sha256"]},
    "packaged_visibility_equivalence":{"windows_checks":1712,"apk_checks":1712},
    "story_ui_observation":{"checks":story_ui["checks"],"authored_briefs_checked":story_ui["authored_briefs_checked"],"report_sha256":sha(QA/"final-route-graph-v2-story-ui/desktop/report.json")},
    "mobile_matrix":{"cases":len(mobile["cases"]),"checks":mobile["checks"],"minimum_battlefield_ratio":min(row["minimum_battlefield_ratio"] for row in mobile["cases"]),"report_sha256":sha(QA/"final-route-graph-mobile-root/mobile/mobile-matrix.json"),"android_hardware_verified":False},
    "native_export_smoke":{"cases":len(native_export["cases"]),"passed":native_export["passed"],"report_sha256":sha(QA/"final-route-graph-v2/mobile/export/report.json"),"executable_sha256":native_export["executable_sha256"]},
    "realtime":{
        "stress":{"mean_ms":stress["intervals_steady"]["mean_ms"],"p95_ms":stress["intervals_steady"]["p95_ms"],"max_units":stress_receipt["max_units"],"samples":stress["intervals_steady"]["samples"],"report_sha256":sha(QA/"final-route-graph-v2-stress-clean/report.json")},
        "phone":{"mean_ms":phone["intervals_steady"]["mean_ms"],"p95_ms":phone["intervals_steady"]["p95_ms"],"max_units":phone_receipt["max_units"],"samples":phone["intervals_steady"]["samples"],"report_sha256":sha(QA/"final-route-graph-v2-phone-clean/report.json")}},
    "android_hardware_verified":False,
    "dense_60fps_verified":False,
    "scope":"RC37 Windows and Android exports with native Windows package logic, fog equivalence, source story UI observation and native Windows mobile-shaped runtime observations. Single-player map/story binding is data- and route-tested; no claim of human completion, original-game exact timing, Android physical-device performance or dense stable 60FPS.",
}
(RELEASE/"preview-verification.json").write_text(json.dumps(verification,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

exe_hash=exe["sha256"]
apk_hash=apk_build["sha256"]
zip_hash=archive["sha256"]
doc=ROOT/"docs/paper-warfront/148-战争迷雾失效缓存与rc37预览交付.md"
doc.write_text(f"""# 战争迷雾失效缓存、剧情地图绑定与 rc37 预览交付

RC37 把战争迷雾刷新从“每个模拟 tick 无条件重建”改为带失效标记的刷新。单位、建筑、路线、阵营转换、法术视野、移动视野、区域位移、死亡和开火揭示会标记失效；AI 在 tick 末尾产生路线或召唤变化后会在同一 tick 发布新的迷雾结果。没有这些变化时，当前视野、探索记忆、已知敌人和建筑 last-seen 会复用上一份结果。

这项缓存只改变刷新调度，不改变道路距离、上下道路隔离、未知/已探索/当前可见三态、开火揭示 1.5 秒、施法可见性或地图剧情规则。缓存合同由 test_visibility_refresh_cache.gd 的 15 项边界检查和 test_visibility_refresh_equivalence.gd 的 1712 项逐状态参照检查覆盖；参照版本在相同 tick 后强制重建迷雾，比较玩家资源、单位/建筑、投射物、法术区域、事件、视野、探索记忆、敌人顺序和随机流。

## 单机地图与剧情

本版继续使用地图即叙事场所的合同：200 张地图属于 10 章，每张地图都有战前冲突、地点动机、真实目标、战后结果和证据旗。路线允许线性、分岔、并行、条件汇流和回访；地图内部的道路长度和几何分叉必须给抵达、经济、视野或目标风险带来差异。数据合同通过 {story["checks"]} 项，并额外要求战前场景、战后场景、剧情线、证据名和关卡标题全部保持地图级唯一；原生路线合同通过 103595 项，覆盖 64 条开局选择路径和 552 条章内最小路线顺序。

护送与截击的任务 HUD 和胜负判定现在沿单位所在道路、当前叉路选择和目标锚点计算真实剩余道路长度；目标落在另一条未选支路时显示“需改道”，不会再用地图横向坐标差掩盖桥路或坡道的长度差异。

## RC37 验证

| 项目 | 结果 |
|---|---:|
| 迷雾缓存边界 | 15 项，通过 |
| 强制刷新逐状态等价 | 1712 项，通过 |
| 迷雾/视野回归 | 1124 项，通过 |
| 视野图几何等价 | 1932 项，通过 |
| 归属/纸工/世界战斗 | 154 / 121 / 370 项，通过 |
| 阵营差异与动作帧合同 | 3109 / 4751 项，通过 |
| 采矿往返运输合同 | 37 项，通过 |
| 单机地图剧情合同 | 200 图 / 10 章 / {story["checks"]} 项，通过 |
| 原生路线合同 | 103595 项，通过 |
| 战役导演阶段合同 | 4200 项，通过 |
| 剧情 UI 观察 | 237 项；200 张简报摘要，通过 |
| 原生移动密度/触控矩阵 | 8 配置 / {mobile["checks"]} 项，通过；最低战场占比 {min(row["minimum_battlefield_ratio"] for row in mobile["cases"])*100:.1f}% |
| 当前 EXE 原生冒烟 | 6 场景，通过；独立存档、原生 GPU |
| APK 编译逻辑 | {len(apk["tests"])} 组 / {sum(row["checks"] for row in apk["tests"])} 项，通过 |
| Windows EXE 编译逻辑 | {len(windows["tests"])} 组 / {sum(row["checks"] for row in windows["tests"])} 项，通过 |
| 密集压力窗口 | {stress["intervals_steady"]["mean_ms"]:.2f}ms/帧均值，124 单位；未达稳定 60FPS |
| 手机形状窗口 | {phone["intervals_steady"]["mean_ms"]:.2f}ms/帧均值，约 60Hz |
| Android 实体设备 | 未验证；当前无设备且不使用模拟器 |

## 下载

- Windows ZIP: release/{VERSION}/PaperWarfront-Windows-{VERSION}.zip
- Windows EXE: release/{VERSION}/windows/PaperWarfront.exe
- Android APK: release/{VERSION}/android/PaperWarfront-{VERSION}.apk
- 发布验证: release/{VERSION}/preview-verification.json
- SHA256 清单: release/{VERSION}/SHA256SUMS.txt

EXE SHA256: {exe_hash}
APK SHA256: {apk_hash}
ZIP SHA256: {zip_hash}

密集 124 单位场景仍主要受模拟和绘制共同限制，本版没有把满员 60FPS 写成完成项。移动矩阵是在 Windows 原生 Godot GPU 上注入密度、安全区和触控事件的证据，不等同于 Android 实体设备。原作精确迷雾时序、全关人工平衡、真人剧情体验和 Android 真机性能仍需单独验收。
""",encoding="utf-8")
(RELEASE/"README.md").write_text(doc.read_text("utf-8"),encoding="utf-8")

root_readme=ROOT/"README.md"
root_text=root_readme.read_text("utf-8")
root_text=root_text.replace("# 纸上兵戈：十院留名 · rc36-preview","# 纸上兵戈：十院留名 · rc37-preview",1)
root_text=root_text.replace("[146-战斗模拟快照缓冲与 rc36 交付]","[148-战争迷雾失效缓存与 rc37 交付]",1)
root_text=root_text.replace("(docs/paper-warfront/146-战斗模拟快照缓冲与rc36预览交付.md)：复用战斗 tick 快照与存活缓冲，保留 200 张非线性剧情地图与战争迷雾合同。","(docs/paper-warfront/148-战争迷雾失效缓存与rc37预览交付.md)：迷雾失效刷新保持逐状态等价，保留 200 张非线性剧情地图与战争迷雾合同。",1)
root_text=root_text.replace("最新下载与验收范围以146 / RC36 为准","最新下载与验收范围以148 / RC37 为准")
root_text=root_text.replace("release/3.0.0-rc36-preview","release/"+VERSION)
root_readme.write_text(root_text,encoding="utf-8")

doc_readme=ROOT/"docs/paper-warfront/README.md"
doc_text=doc_readme.read_text("utf-8")
doc_text=doc_text.replace("# 纸上兵戈：十院留名 · rc36-preview","# 纸上兵戈：十院留名 · rc37-preview",1)
doc_text=doc_text.replace("[146-战斗模拟快照缓冲与 rc36 交付]","[148-战争迷雾失效缓存与 rc37 交付]",1)
doc_text=doc_text.replace("(146-战斗模拟快照缓冲与rc36预览交付.md)：复用战斗 tick 快照与存活缓冲，地图/剧情/迷雾规则保持绑定。","(148-战争迷雾失效缓存与rc37预览交付.md)：迷雾失效刷新保持逐状态等价，地图/剧情/迷雾规则保持绑定。",1)
doc_text=doc_text.replace("最新下载与验收范围以146 / RC36 为准","最新下载与验收范围以148 / RC37 为准")
doc_readme.write_text(doc_text,encoding="utf-8")

revision=ROOT/"assets/paper-warfront/system-revisions/rc37-visibility-cache.json"
refs={}
for name in manifest["source_inputs"]:refs[name]=sha(ROOT/name)
extra=[
    RELEASE/"build-manifest.json",RELEASE/"preview-verification.json",RELEASE/"README.md",RELEASE/"SHA256SUMS.txt",
    RELEASE/("PaperWarfront-Windows-"+VERSION+".zip"),RELEASE/"windows/PaperWarfront.exe",RELEASE/("android/PaperWarfront-"+VERSION+".apk"),
    doc,ROOT/"docs/paper-warfront/147-单机地图剧情合同与路线分支验收.md",ROOT/"docs/paper-warfront/16-玩家手册.md",ROOT/"docs/paper-warfront/20-战役与任务执行规范.md",ROOT/"docs/paper-warfront/frame-rebuild/04-检查与交付范围.md",root_readme,doc_readme,ROOT/"game/README.md",ROOT/"game/scripts/battle_visibility.gd",ROOT/"game/scripts/battle_sim.gd",
    ROOT/"game/scripts/manual_spell_rules.gd",ROOT/"game/scripts/unit_abilities.gd",ROOT/"game/scripts/battle_view.gd",ROOT/"game/scripts/campaign_route_graph.gd",ROOT/"game/scripts/main.gd",ROOT/"docs/paper-warfront/149-剧情路线图与运行绘制缓存调优.md",
    ROOT/"game/tests/test_visibility_refresh_cache.gd",ROOT/"game/tests/test_visibility_refresh_equivalence.gd",
    ROOT/"tools/paper-warfront/verify_story_map_contract.py",ROOT/"tools/paper-warfront/check_mobile_adaptation.py",ROOT/"tools/paper-warfront/probe_story_routes_ui.gd",ROOT/"tools/paper-warfront/package_release.py",ROOT/"tools/paper-warfront/write_rc37_visibility_release.py",
    ROOT/"output/qa/paper-warfront/story-map-contract.json",ROOT/"output/qa/paper-warfront/campaign-routes-rc37.json",
    QA/"final-route-graph-v2-stress-clean/report.json",QA/"final-route-graph-v2-phone-clean/report.json",
    QA/"final-route-graph-v2-packaged/apk-logic/report.json",QA/"final-route-graph-v2-packaged/windows-logic/report.json",
    QA/"final-route-graph-v2/mobile/export/report.json",
    ROOT/"output/qa/paper-warfront/story-objective-route-rc37.json",ROOT/"output/qa/paper-warfront/theatre-decisions-route-rc37.json",
    QA/"final-route-graph-mobile-root/mobile/mobile-matrix.json",QA/"final-route-graph-v2-story-ui/desktop/report.json",QA/"final-route-graph-v2-story-ui/phone/report.json",QA/"final-route-graph-v2-story-ui/report.json",
    ROOT/"output/qa/godot/render-runtime-rc37/visual-audit/battle-desktop.png",ROOT/"output/qa/godot/render-runtime-rc37/visual-audit/mobile-battle-late.png",
    ROOT/"output/qa/godot/render-runtime-rc37/final-route-graph-v2-story-ui/desktop/03-map-story-brief.png",ROOT/"output/qa/godot/render-runtime-rc37/final-route-graph-v2-story-ui/desktop/02-two-story-routes.png",
    ROOT/"output/qa/paper-warfront/distinct-factions-rc37.json",ROOT/"output/qa/paper-warfront/unit-actions-rc37.json",ROOT/"output/qa/paper-warfront/map-transport-rc37.json",
]
for path in extra:refs[path.relative_to(ROOT).as_posix()]=sha(path)
revision_data={
    "id":"system.visibility-invalidation-cache.rc37",
    "version":1,
    "release":VERSION,
    "parent_revision":"system.simulation-buffers.rc36",
    "formal_script_changes":["game/scripts/battle_visibility.gd","game/scripts/battle_sim.gd","game/scripts/manual_spell_rules.gd","game/scripts/unit_abilities.gd"],
    "verification_tool_changes":["tools/paper-warfront/verify_story_map_contract.py","tools/paper-warfront/check_mobile_adaptation.py","tools/paper-warfront/probe_story_routes_ui.gd","tools/paper-warfront/package_release.py","tools/paper-warfront/write_rc37_visibility_release.py"],
    "generated_raster_assets":False,
    "story_maps":200,
    "story_chapters":10,
    "story_contract_checks":story["checks"],
    "campaign_route_checks":103595,
    "source_tests":source_rows,
    "status":"verified_preview; dense60fps_balance_original_fog_timing_story_human_android_hardware_pending",
    "scope":"Explicit fog invalidation with same-tick AI publication and forced-refresh state equivalence. No map/story asset replacement and no physical Android claim.",
    "references":dict(sorted(refs.items())),
}
revision.write_text(json.dumps(revision_data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
assert all(sha(ROOT/name)==digest for name,digest in revision_data["references"].items())
print(json.dumps({"passed":True,"version":VERSION,"verification":str((RELEASE/"preview-verification.json").relative_to(ROOT)),"revision":str(revision.relative_to(ROOT)),"exe_sha256":exe_hash,"apk_sha256":apk_hash,"zip_sha256":zip_hash},ensure_ascii=False))


"""Register stable narrative/font revisions and actual rc29 delivery evidence."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/story-atlas-rc29'
VERSION='3.0.0-rc29-preview'
RELEASE=ROOT/'release'/VERSION
read=lambda p:json.loads(p.read_text('utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
target=ROOT/'assets/paper-warfront/system-revisions/rc29-story-atlas-r1.json'
assert not target.exists(), 'Published revision records are immutable'
proof=read(RELEASE/'preview-verification.json');manifest=read(RELEASE/'build-manifest.json')
assert proof['story_map_progression_verified']['authored_maps']==200
assert proof['packaged_logic_checks_on_windows']=={'apk':187249,'windows':187249}
assert all(sha(ROOT/name)==digest for name,digest in manifest['source_inputs'].items())
references=set(manifest['source_inputs'])
for folder in ['tools/paper-warfront/story-chapters','docs/paper-warfront/world/maps']:
 references.update(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).iterdir() if p.is_file())
references.update([
 'assets/paper-warfront/campaign.json','assets/paper-warfront/campaign-flow.json','assets/paper-warfront/campaign-narrative.json',
 'docs/paper-warfront/138-二百图剧情与非线性战役.md','docs/paper-warfront/README.md','README.md',
 'docs/paper-warfront/world/02-十阵营设定.md','docs/paper-warfront/world/04-完整故事路线.md',
 'tools/paper-warfront/author_story_atlas.py','tools/paper-warfront/write_story_atlas_design.py',
 'tools/paper-warfront/bind_story_combat_history.py','tools/paper-warfront/write_story_atlas_release.py',
 'tools/paper-warfront/write_story_atlas_revision.py','tools/paper-warfront/probe_story_routes_ui.gd',
 'tools/paper-warfront/check_story_routes_ui.py','tools/paper-warfront/check_ai_engagement.py',
 'tools/paper-warfront/check_packaged_apk_logic.py','tools/paper-warfront/check_packaged_windows_logic.py',
 'tools/paper-warfront/build_game.py','tools/paper-warfront/audit_preview_build.py','tools/paper-warfront/run_query_native_extras.py',
 'game/tests/test_campaign_routes.gd','game/tests/test_story_objective_binding.gd',
 'output/qa/godot/story-atlas-rc29/authorship.json',
 'output/qa/godot/story-atlas-rc29/combat-history-binding.json',
 'output/qa/godot/story-atlas-rc29/source-final/report.json',
 'output/qa/godot/story-atlas-rc29/font-coverage.json',
 'output/qa/godot/story-atlas-rc29/objective-recheck/report.json',
 'output/qa/godot/story-atlas-rc29/retained-paid-reach-receipts.json',
 'output/qa/godot/story-atlas-rc29/formal-reach/verification.json',
 'output/qa/godot/story-atlas-rc29/formal-hammer/verification.json',
])
for p in (QA/'release-final').rglob('*.json'):
 if 'extracted-runtime' not in p.parts:references.add(p.relative_to(ROOT).as_posix())
for p in [RELEASE/'README.md',RELEASE/'build-manifest.json',RELEASE/'preview-verification.json',RELEASE/'SHA256SUMS.txt']:
 references.add(p.relative_to(ROOT).as_posix())
for row in manifest['builds']+manifest['archives']:references.add(row['path'])
rows=read(ROOT/'game/data/campaign-narrative.json')['profiles']
result={'id':'system.story-atlas.rc29','version':1,'release':VERSION,
 'status':'native_windows_source_and_compiled_packages_verified; android_hardware_and_human_story_playthrough_pending',
 'stable_maps':200,'new_explicit_story_records':180,'chapters':10,'local_minimal_route_orders':552,
 'narrative_profiles':{key:{'id':value['id'],'text_version':value['version'],'binding_schema_version':2,'map':value['map'],'evidence_flag':value['evidence_flag']} for key,value in rows.items()},
 'source_groups':78,'source_checks':195435,'package_groups_each':36,'package_checks_each':187249,
 'compiled_native_story_ui_checks':474,'runtime_asset_count':455,
 'font_revision':read(QA/'font-coverage.json'),
 'generated_raster_assets':False,
 'retained_combat_evidence':'rc28 original closure, exact unchanged input/configuration binding; new package queries also checked',
 'scope':'Authored all-map brief/result narrative, actual target/geometry bindings, alternatives/conjunctions/save and native Control input. No extra NPC combat actors or free resources. Fixtures are not200 paid wins or Android hardware.',
 'remaining':['dense124-unit performance','campaign difficulty and faction balance','human complete story review','exact original-series visibility timing','physical Android','human network play'],
 'references':{name:sha(ROOT/name) for name in sorted(references)}}
target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8')
print('Registered rc29 stable story/font revision:',len(references),'verified references')

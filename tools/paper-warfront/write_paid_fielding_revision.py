"""Bind normal paid-unit deployment to frozen cohorts and the final RC24 packages."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/paid-fielding-rc24'
RELEASE=ROOT/'release/3.0.0-rc24-preview'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

manifest=read(RELEASE/'build-manifest.json')
proof=read(RELEASE/'preview-verification.json')
prior=read(ROOT/'release/3.0.0-rc23-preview/build-manifest.json')
assert manifest['version']==proof['version']=='3.0.0-rc24-preview'
assert proof['preview_artifacts_verified'] and proof['source_inputs_verified']
assert not proof['android_hardware_verified'] and not proof['full_balance_verified']
assert all(sha(ROOT/name)==digest for name,digest in manifest['source_inputs'].items())
assert manifest['source_inputs'].keys()==prior['source_inputs'].keys()
changed=sorted(name for name,value in manifest['source_inputs'].items() if prior['source_inputs'][name]!=value)
assert changed==['game/export_presets.cfg','game/project.godot','game/scripts/tactical_ai.gd']
ai_hash=sha(ROOT/'game/scripts/tactical_ai.gd')
assert ai_hash==sha(QA/'formal-default-runtime/scripts/tactical_ai.gd')
assert read(QA/'formal-default-runtime/candidate.json')['current_ai_source_sha256']==ai_hash

mechanisms=read(QA/'formal-reach/regression/report.json')
assert mechanisms['passed'] and mechanisms['source_unchanged'] and len(mechanisms['tests'])==70
assert sum(t['checks'] for t in mechanisms['tests'])==15586
assert all(sha(ROOT/name)==digest for name,digest in mechanisms['inputs'].items())
package_checks={}
for name in ['windows','apk']:
    report=read(QA/f'release/{name}-logic/report.json')
    assert report['passed'] and len(report['tests'])==26
    assert sum(t['checks'] for t in report['tests'])==2696
    package_checks[name]={'groups':26,'checks':2696}

compiled=read(QA/'release/apk-logic/report.json')['extracted_inputs']
old_compiled=read(ROOT/'output/qa/godot/ai-redemption-rc23/release-final/apk-logic/report.json')['extracted_inputs']
assert compiled.keys()==old_compiled.keys()
compiled_changes=sorted(name for name,value in compiled.items() if old_compiled[name]!=value)
assert compiled_changes==['.godot/uid_cache.bin','assets.sparsepck','project.binary','scripts/tactical_ai.gdc']

references=[
    'README.md','docs/paper-warfront/README.md',
    'docs/paper-warfront/133-研究后付费部署闭环与rc24交付.md',
    'docs/paper-warfront/11-Godot架构与数据契约.md','docs/paper-warfront/16-玩家手册.md',
    'game/tests/test_paid_fielding_pipeline.gd','game/tests/test_unit_fielding_roles.gd',
    'tools/paper-warfront/observe_paid_fielding.py','tools/paper-warfront/compare_default_fielding.py',
    'tools/paper-warfront/compare_paid_fielding.py','tools/paper-warfront/probe_paid_fielding_render.gd',
    'tools/paper-warfront/check_paid_fielding_render.py','tools/paper-warfront/write_paid_fielding_revision.py',
    'tools/paper-warfront/run_preview_checks.py','tools/paper-warfront/audit_preview_build.py',
    'assets/paper-warfront/style-tokens.json','assets/paper-warfront/ui/paper-ui.json',
    'assets/paper-warfront/presentation-revisions/rc21-fog-stage-r1.json',
    'assets/paper-warfront/presentation-revisions/rc22-observer-camera-r1.json',
    'assets/paper-warfront/system-revisions/rc23-ai-economy-bootstrap-r1.json',
    'release/3.0.0-rc24-preview/README.md','release/3.0.0-rc24-preview/build-manifest.json',
    'release/3.0.0-rc24-preview/preview-verification.json',
]
comparisons={}
for filename in ['compare-default-mid137.json','compare-default300-mid137.json',
                 'compare-default-short271.json','compare-default-long419.json']:
    item=read(QA/filename)
    assert item['passed'] and not item['balance_accepted']
    assert item['side_participations']==item['pairs']*2
    for entry in item['inputs'].values():
        path=Path(entry['path']);assert sha(path)==entry['sha256']
        cohort=read(path);runtime=Path(cohort['runtime'])
        assert cohort['passed'] and all(sha(runtime/name)==digest for name,digest in cohort['runtime_inputs'].items())
        for batch in cohort['batches']:assert sha(path.parent/batch['file'])==batch['sha256']
        references.append(path.relative_to(ROOT).as_posix())
    comparisons[filename]={k:item[k] for k in ['pairs','side_participations','map','seed','stock','duration','totals','outcomes','factions']}
    references.append((QA/filename).relative_to(ROOT).as_posix())
assert sum(c['pairs'] for c in comparisons.values())==220

negative=read(QA/'release/paid-fielding-render/desktop/report.json')
assert not negative['passed'] and abs(negative['time']-240)<.001
assert negative['first_paid_unit']['uid']>0 and not negative['first_impact']
assert negative['observer_sha256']==sha(QA/'normal-entry-yin-mu-harness-r1.gd')
assert all(sha(Path(c['path']))==c['sha256'] for c in negative['captures'])
fielding=read(QA/'release/normal-fielding/report.json')
assert fielding['passed'] and fielding['pack_sha256']==manifest['builds'][0]['sha256']
assert fielding['observer_sha256']==sha(ROOT/'tools/paper-warfront/probe_paid_fielding_render.gd')
assert sum(c['checks'] for c in fielding['cases'])==50
for case in fielding['cases']:
    native=read(QA/f"release/normal-fielding/{case['name']}/report.json")
    assert native['passed'] and native['config'].get('ai_warmup',4)==4
    assert all(compiled[name.removeprefix('res://')]==value for name,value in native['inputs'].items())
    assert all(sha(Path(c['path']))==c['sha256'] for c in native['captures'])
    references.extend((QA/f"release/normal-fielding/{case['name']}"/n).relative_to(ROOT).as_posix() for n in ['report.json','runtime.log'])
    references.extend(Path(c['path']).relative_to(ROOT).as_posix() for c in native['captures'])

for name in ['formal-default-runtime/candidate.json','formal-reach/regression/report.json',
             'formal-reach/verification.json','formal-hammer/verification.json',
             'working-regression-r3/report.json','compare-roles-r3-mid137-disabled-normalized.json',
             'release/normal-fielding/report.json','release/paid-fielding-render/desktop/report.json',
             'normal-entry-yin-mu-harness-r1.gd','release/windows-logic/report.json',
             'release/apk-logic/report.json','release/mobile/mobile-matrix.json',
             'release/stage-proportions/report.json','release/fog-render/report.json',
             'release/camera-render/report.json','release/paper-ui-assets.json','release/runner-report.json']:
    references.append((QA/name).relative_to(ROOT).as_posix())
for item in manifest['builds']+manifest['archives']:
    path=ROOT/item['path'];assert path.stat().st_size==item['bytes'] and sha(path)==item['sha256']
with zipfile.ZipFile(ROOT/manifest['archives'][0]['path']) as archive:
    assert archive.testzip() is None
    assert read(RELEASE/'preview-verification.json')==json.loads(archive.read('PaperWarfront/preview-verification.json'))
    bundled_manifest=json.loads(archive.read('PaperWarfront/build-manifest.json'))
    assert 'archives' not in bundled_manifest and bundled_manifest['builds']==manifest['builds']

ui=read(ROOT/'assets/paper-warfront/ui/paper-ui.json');style=read(ROOT/'assets/paper-warfront/style-tokens.json')
assert len(ui['assets'])==38 and ui['model']=='gpt-image-2.5'
record={
    'revision':'rc24-ai-paid-fielding-r1','rule_id':'ai.common.unit.first-paid-order',
    'version':manifest['version'],'status':'verified-preview','source':'game/scripts/tactical_ai.gd',
    'source_sha256':ai_hash,'frozen_default_ai_equals_formal_source':True,
    'changed_public_inputs_since_rc23':changed,'changed_extracted_apk_inputs_since_rc23':compiled_changes,
    'unchanged_extracted_apk_inputs_since_rc23':len(compiled)-len(compiled_changes),
    'normal_paid_fielding_enabled_on_both_sides':True,'budget_planner_r12_enabled_by_default':False,
    'new_raster_generation':False,'style_tokens_version':style['version'],
    'reused_ui_asset_version':ui['version'],'reused_ui_assets':38,'reused_ui_generation_model':ui['model'],
    'reused_presentation_revisions':['rc21-fog-stage-r1','rc22-observer-camera-r1'],
    'source_mechanism_checks':{'groups':70,'checks':15586},'packaged_logic_checks_on_windows':package_checks,
    'paired_both_side_observations':comparisons,'paired_conditions':220,'paired_complete_runs':440,
    'paired_scope':'Native Windows CPU; both complete AI sides with zero warmup, formal fees, 240s ceiling. Faction totals count actual side participations; cohorts do not prove menu warmup, human gameplay or full balance.',
    'normal_entry_gpu':proof['normal_paid_fielding_verified'],
    'retained_normal_entry_counterexample':{'faction':'yin','enemy':'mu','map':'map.01.04','seed':137,'duration':240,
        'research_and_first_paid_production':True,'first_unit_direct_damage':False,
        'legacy_height_field_is_ui_units_not_physical_pixels':True},
    'advanced_first_deployment_gap_remaining':True,'economy_and_faction_regressions_remaining':True,
    'android_hardware_verified':False,'full_balance_verified':False,'original_game_numeric_equivalence_verified':False,
    'files':{name:sha(ROOT/name) for name in sorted(set(references))},
    'builds_and_archives':manifest['builds']+manifest['archives'],
}
target=ROOT/'assets/paper-warfront/system-revisions/rc24-ai-paid-fielding-r1.json'
target.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert all(sha(ROOT/name)==digest for name,digest in record['files'].items())
print(f"RC24 revision verified: {len(record['files'])} references; 220 paired conditions; 440 runs; retained negative evidence.")

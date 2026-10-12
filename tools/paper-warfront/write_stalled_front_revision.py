"""Bind the reviewed control-lock policy to RC25 source, cohorts and final packages."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/fielding-contact-rc25'
RELEASE=ROOT/'release/3.0.0-rc25-preview'
REVISION='rc25-ai-stalled-front-r2'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

manifest=read(RELEASE/'build-manifest.json');proof=read(RELEASE/'preview-verification.json')
prior=read(ROOT/'release/3.0.0-rc24-preview/build-manifest.json')
assert manifest['version']==proof['version']=='3.0.0-rc25-preview'
assert proof['preview_artifacts_verified'] and proof['source_inputs_verified']
assert not proof['android_hardware_verified'] and not proof['full_balance_verified']
assert all(sha(ROOT/name)==digest for name,digest in manifest['source_inputs'].items())
assert manifest['source_inputs'].keys()==prior['source_inputs'].keys()
changed=sorted(k for k,v in manifest['source_inputs'].items() if prior['source_inputs'][k]!=v)
assert changed==['game/export_presets.cfg','game/project.godot','game/scripts/tactical_ai.gd']
assert sha(ROOT/'game/scripts/tactical_ai.gd')==sha(QA/'ranged-r5-runtime/scripts/tactical_ai.gd')
assert read(QA/'ranged-r5-runtime/candidate.json')['ai_sha256']==sha(ROOT/'game/scripts/tactical_ai.gd')
regression=read(QA/'formal-reach/regression/report.json')
assert regression['passed'] and regression['source_unchanged'] and len(regression['tests'])==71
assert sum(t['checks'] for t in regression['tests'])==15634
assert all(sha(ROOT/name)==digest for name,digest in regression['inputs'].items())
for platform in ['apk','windows']:
    item=read(QA/f'release/{platform}-logic/report.json')
    assert item['passed'] and len(item['tests'])==27 and sum(t['checks'] for t in item['tests'])==2744

references=[
    'README.md','docs/paper-warfront/README.md','docs/paper-warfront/134-受控前排反制与科技收益复核.md',
    'docs/paper-warfront/11-Godot架构与数据契约.md','docs/paper-warfront/16-玩家手册.md',
    'game/tests/test_stalled_front_recruitment.gd','tools/paper-warfront/test_stalled_front_recruitment.gd',
    'tools/paper-warfront/prepare_stalled_front_trial.py','tools/paper-warfront/prepare_contact_counter_trial.py',
    'tools/paper-warfront/compare_contact_counter.py','tools/paper-warfront/observe_contact_traces.py',
    'tools/paper-warfront/probe_fielding_contact.gd','tools/paper-warfront/observe_paid_fielding.py',
    'tools/paper-warfront/probe_stalled_front_render.gd','tools/paper-warfront/check_stalled_front_render.py',
    'tools/paper-warfront/write_stalled_front_revision.py','tools/paper-warfront/audit_preview_build.py',
    'tools/paper-warfront/check_ai_engagement.py','tools/paper-warfront/check_packaged_apk_logic.py',
    'tools/paper-warfront/check_packaged_windows_logic.py','assets/paper-warfront/style-tokens.json',
    'assets/paper-warfront/ui/paper-ui.json','assets/paper-warfront/presentation-revisions/rc21-fog-stage-r1.json',
    'assets/paper-warfront/presentation-revisions/rc22-observer-camera-r1.json',
    'release/3.0.0-rc25-preview/README.md','release/3.0.0-rc25-preview/build-manifest.json',
    'release/3.0.0-rc25-preview/preview-verification.json',
]
comparisons={}
for policy,filename in [('retained-unadopted-r3','compare-r3-matrix300-mid137.json'),
                        ('r5-stock160','compare-r5-matrix160-mid137.json'),('r5-stock300','compare-r5-matrix300-mid137.json')]:
    item=read(QA/filename)
    assert item['passed'] and item['paired_conditions']==100 and item['runtime_changed_inputs']==['scripts/tactical_ai.gd']
    assert all(sha(Path(ref['path']))==ref['sha256'] for ref in item['references'].values())
    comparisons[policy]={k:item[k] for k in ['paired_conditions','conditions','control','candidate','houses','outcome_changes']}
    references.append((QA/filename).relative_to(ROOT).as_posix())
    references.extend(Path(ref['path']).relative_to(ROOT).as_posix() for ref in item['references'].values())

for policy in ['ranged-r1','ranged-r2','ranged-r3','ranged-r4','ranged-r5']:
    item=read(QA/(policy+'-runtime/candidate.json'))
    assert item['ai_sha256']==sha(QA/(policy+'-runtime/scripts/tactical_ai.gd'))
    assert item['diff_sha256']==sha(QA/(policy+'.diff'))
    generator=(QA/'generator-r1-r2.py') if policy in ['ranged-r1','ranged-r2'] else ((QA/'generator-r3.py') if policy=='ranged-r3' else ROOT/'tools/paper-warfront/prepare_stalled_front_trial.py')
    assert item['generator_sha256']==sha(generator)
    references.extend((QA/n).relative_to(ROOT).as_posix() for n in [policy+'-runtime/candidate.json',policy+'-runtime/scripts/tactical_ai.gd',policy+'.diff'])
    references.append(generator.relative_to(ROOT).as_posix())

normal_review=read(QA/'normal-trace-review.json')
assert normal_review['passed'] and normal_review['disabled_r3_full_gameplay_trace_equal']
assert sum(bool(row['changed_fields']) for row in normal_review['short_long'])==1
for name,digest in normal_review['inputs'].items():
    assert sha(QA/name)==digest
    references.append((QA/name).relative_to(ROOT).as_posix())
for case in ['desktop','phone']:
    path=QA/f'release/stalled-front/{case}/report.json';native=read(path)
    assert native['passed'] and len(native['checks'])==32 and len(native['captures'])==8
    assert native['paid_counter']['price']==60 and native['counter_impact']['amount']>0 and native['first_impact']['amount']>0
    compiled=read(QA/'release/apk-logic/report.json')['extracted_inputs']
    assert all(compiled[name.removeprefix('res://')]==digest for name,digest in native['inputs'].items())
    references.append(path.relative_to(ROOT).as_posix())
    for shot in native['captures']:
        assert sha(Path(shot['path']))==shot['sha256']
        references.append(Path(shot['path']).relative_to(ROOT).as_posix())
for name in ['normal-trace-review.json','baseline.json','observer-r1-shared-status.gd','observer-v2.gd','observer-v3.gd',
             'r3-protected-boundaries/report.json','r4-pilot300-mid137/report.json','r5-pilot300-mid137/report.json',
             'r5-menu/report.json','r5-menu/observer.gd','r5-menu-seeds/report.json','r5-short-long/report.json',
             'r5-short-long/observer.gd','formal-reach/regression/report.json','formal-reach/verification.json',
             'formal-hammer/verification.json','formal-recipe-runner.json','release/runner-report.json',
             'release/stalled-front/report.json','release/normal-fielding/report.json','release/windows-logic/report.json',
             'release/apk-logic/report.json','release/mobile/mobile-matrix.json','release/paper-ui-assets.json',
             'release/stage-proportions/report.json','release/fog-render/report.json','release/camera-render/report.json']:
    references.append((QA/name).relative_to(ROOT).as_posix())
for name in ['report.json','runtime.log']:
    references.append((QA/'release/stalled-front-vulkan/desktop'/name).relative_to(ROOT).as_posix())
for shot in read(QA/'release/stalled-front-vulkan/desktop/report.json')['captures']:
    assert sha(Path(shot['path']))==shot['sha256']
    references.append(Path(shot['path']).relative_to(ROOT).as_posix())
for artifact in manifest['builds']+manifest['archives']:
    path=ROOT/artifact['path'];assert path.stat().st_size==artifact['bytes'] and sha(path)==artifact['sha256']
with zipfile.ZipFile(ROOT/manifest['archives'][0]['path']) as archive:
    assert archive.testzip() is None
    assert json.loads(archive.read('PaperWarfront/preview-verification.json'))==proof
    bundled=json.loads(archive.read('PaperWarfront/build-manifest.json'))
    assert 'archives' not in bundled and bundled['builds']==manifest['builds']
ui=read(ROOT/'assets/paper-warfront/ui/paper-ui.json')
assert len(ui['assets'])==38 and ui['model']=='gpt-image-2.5'
previous=ROOT/'assets/paper-warfront/system-revisions/rc25-ai-stalled-front-r1.json'
previous_record=read(previous)
assert sha(QA/'README-before-current-scope-fix.md')==previous_record['files']['README.md']
assert sha(QA/'write_stalled_front_revision-r1.py')==previous_record['files']['tools/paper-warfront/write_stalled_front_revision.py']
references.extend([previous.relative_to(ROOT).as_posix(),(QA/'README-before-current-scope-fix.md').relative_to(ROOT).as_posix(),(QA/'write_stalled_front_revision-r1.py').relative_to(ROOT).as_posix()])
record={'revision':REVISION,'supersedes':'rc25-ai-stalled-front-r1','revision_note':'Corrected the current README tail, which had retained an unlabelled rc24 no-hit claim. Original README and writer bytes archived by exact prior digests; binaries and gameplay are unchanged.',
    'rule_id':'ai.common.front.control-counter','status':'verified-preview',
    'version':manifest['version'],'source':'game/scripts/tactical_ai.gd','source_sha256':sha(ROOT/'game/scripts/tactical_ai.gd'),
    'exact_frozen_r5_equals_formal_source':True,'changed_public_inputs_since_rc24':changed,
    'normal_policy_enabled_on_both_sides':True,'budget_planner_r12_enabled_by_default':False,
    'new_raster_generation':False,'reused_ui_assets':38,'reused_ui_version':ui['version'],'reused_ui_model':ui['model'],
    'reused_presentation_revisions':['rc21-fog-stage-r1','rc22-observer-camera-r1'],
    'mechanism_checks':{'groups':71,'checks':15634},'compiled_checks_per_package_on_windows':{'groups':27,'checks':2744},
    'comparisons':comparisons,'adopted_policy_paired_conditions':200,'adopted_policy_complete_runs':400,
    'paired_scope':'Native CPU normal-AI zero-warmup stock160/300 comparisons. Two side participations per match; outcome, economy and research regressions retained. Comparison passed means provenance, not balance acceptance.',
    'normal_stalled_entry_gpu':proof['stalled_front_response_verified'],
    'default_windows_renderer':proof['default_desktop_renderer_verified'],
    'normal_menu_seed_scope':'Three same-map CPU seed conditions,300 gold and4s warmup, first guard0 to41 positive hits and victory near206s. Actual exported GPU observer stops at first guard impact near147.55s; it does not prove the full victory.',
    'advanced_first_deployment_gap_remaining':True,'economy_and_faction_regressions_remaining':True,
    'android_hardware_verified':False,'full_balance_verified':False,'original_game_numeric_equivalence_verified':False,
    'files':{name:sha(ROOT/name) for name in sorted(set(references))},'builds_and_archives':manifest['builds']+manifest['archives']}
target=ROOT/'assets/paper-warfront/system-revisions'/f'{REVISION}.json'
assert not target.exists(), 'Never overwrite a delivered revision'
target.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n','utf-8')
assert all(sha(ROOT/name)==digest for name,digest in record['files'].items())
print('RC25 revision verified:',len(record['files']),'references;200 adopted paired conditions;400 runs;negative trials retained.')

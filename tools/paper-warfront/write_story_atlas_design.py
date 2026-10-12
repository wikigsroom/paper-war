"""Publish map-bound narrative design without claiming a candidate is released."""
from pathlib import Path
import hashlib,json,shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/story-atlas-rc29'
read=lambda p:json.loads(p.read_text('utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
campaign=read(ROOT/'game/data/campaign.json')['levels']
flow=read(ROOT/'game/data/campaign-flow.json')
narrative=read(ROOT/'game/data/campaign-narrative.json')['profiles']
story=read(ROOT/'game/data/story.json')
by_id={v['id']:v for v in campaign}
world=ROOT/'docs/paper-warfront/world'
archive=QA/'pre-map-document-update'
assert not archive.exists(), 'Freeze map documents before updating them'
archive.mkdir()
shutil.copytree(world/'maps',archive/'maps')
text=['# 十院逐图故事与章内行动图',
 '200张单机地图各有战前冲突、叙事目标、实际地理动机、战后结果与稳定证据标志。剧情文本只在战前纸页与结果纸页演出；NPC对话与十院会盟不是额外生成的战斗单位。真正胜利条件仍由模拟器判断。',
 '本次为rc29候选的设计来源，发布验收记录另见正式交付文档。章内行动图决定何时可进入某图；战场道路图决定进入后如何自动行军、探视、采金和接援，二者独立。单路用于长接援、运输与截止线，双路用于护矿、绕阵与汇流，均不强制增加岔路。',
 '“或”允许择一路推进并回访其余纸页；“和”要求列出的关卡全部真实通关，可任选先后。证据只随本人实际完成关卡记录，跳过的支线不自动给星、资源或证据。旧线性存档保留已完成历史，schema3保留实际完成集合。',
 '| 章 | 地区 | 最短实际通关数 | 本章最短路线与调查顺序数 | 行动设计 |',
 '|---|---|---:|---:|---|']
for c in flow['chapters']:
 s=story['chapters'][c['index']]
 text.append(f"| {c['index']+1:02} | {s['title'].split('：')[0]} | {c['minimum_actual_clears']} | {len(c['minimal_routes'])} | {c['summary']} |")
for c in flow['chapters']:
 ci=c['index'];s=story['chapters'][ci]
 text += ['',f"## {ci+1:02} · {s['title']}",'',s['synopsis'],'',f"章内推进：{c['summary']}",'','```mermaid','flowchart LR']
 for i in range(ci*20,ci*20+20):
  level=campaign[i];n=i%20+1;text.append(f'  p{n:02}["{n:02} {narrative[level["id"]]["title"]}"]')
 for i in range(ci*20,ci*20+20):
  level=campaign[i];node=flow['nodes'][level['id']]
  required=node['unlock_all'];alternatives=node['unlock_any']
  if len(required+alternatives)>1:
   join=f'j{i%20+1:02}';label='全部留证' if required else '择一留证'
   text.append(f'  {join}{{"{label}"}}')
   for parent in required+alternatives:text.append(f'  p{by_id[parent]["index"]%20+1:02} --> {join}')
   text.append(f'  {join} --> p{i%20+1:02}')
  elif len(required+alternatives)==1:
   parent=(required+alternatives)[0]
   if by_id[parent]['index']//20==ci:text.append(f'  p{by_id[parent]["index"]%20+1:02} --> p{i%20+1:02}')
 text+=['```','','| 图 | 实际目标 | 叙事目标 | 地理动机 | 本图证物 |','|---|---|---|---|---|']
 for i in range(ci*20,ci*20+20):
  level=campaign[i];beat=narrative[level['id']]
  text.append(f"| [{i+1:03} · {beat['title']}](maps/{level['map']}.md) | {level['win']} | {beat['goal']} | {beat['geography_reason']} | {beat['evidence_name']} |")
 text+=['','章节结果：'+s['ending']]
text+=['','## 结局','',story['ending'],'','552种是各章最短路线及必须并行调查的先后顺序之和，不是所有跨章组合、回访顺序、正常战斗胜利或真人完整体验的统计。']
(world/'04-完整故事路线.md').write_text('\n\n'.join(text)+'\n','utf-8')
for level in campaign:
 path=world/'maps'/f"{level['map']}.md";assert path.exists(),path
 old=path.read_text('utf-8').split('\n## 逐图剧情与行动前置')[0]
 beat=narrative[level['id']];node=flow['nodes'][level['id']]
 requirement='起点'
 if node['unlock_all']:requirement='全部完成：'+'、'.join(by_id[p]['title'] for p in node['unlock_all'])
 if node['unlock_any']:requirement='择一完成：'+'、'.join(by_id[p]['title'] for p in node['unlock_any'])
 before='\n\n'.join('**'+line['speaker']+'**：'+line['text'] for line in level['story_before'])
 after='\n\n'.join('**'+line['speaker']+'**：'+line['text'] for line in level['story_after'])
 appended=f'''\n## 逐图剧情与行动前置

剧情标题：{level['title']}。稳定关卡ID：`{level['id']}`；地图ID保持`{level['map']}`。

行动前置：{requirement}。章节行动图和本图道路图分别管理。

叙事目标：{beat['goal']}

实际地理动机：{beat['geography_reason']}

### 战前

{before}

### 战后

{after}

### 运行绑定

本图留证：{beat['evidence_name']}；实际通关后记录`{beat['evidence_flag']}`。跳过本图不产生该证据，重访不减少已有星数。

实际目标绑定：`{json.dumps(beat['objective_binding'],ensure_ascii=False)}`。道路引用：`{', '.join(beat['roads'])}`。保护关使用已存在的指定前哨，护送与拦截必须对应原目标UID；叙事中的查验、送信与会盟是纸页对话，不额外授予战斗资源或生成未实现的NPC。
'''
 path.write_text(old+appended,'utf-8')
path=world/'02-十阵营设定.md';body=path.read_text('utf-8')
body=body.replace('每阵营40个可招募作战兵，工人与临时召唤另计。数值与能力设计属于本作，不声称是原作规则。','当前正式运行每阵营6种作战兵，各自有机制、剪影和动作设计，另有运金纸工与临时召物。旧40种模板不作为当前招募规模。数值与能力设计属于本作，不声称是原作规则；实际定义以`game/data/balance-prototype.json`为准。')
path.write_text(body,'utf-8')
(QA/'design-documents.json').write_text(json.dumps({'passed':True,'map_documents':200,'world_story_sha256':sha(world/'04-完整故事路线.md'),'map_document_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted((world/'maps').glob('*.md'))},'scope':'Runtime-authored dialogue, graph and actual goal binding published in design documents. Not a release-validation or human review result.'},ensure_ascii=False,indent=2)+'\n','utf-8')
print('Map story documentation updated:200 stable map pages and10 authored chapter graphs')

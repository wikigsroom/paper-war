"""Publish the reviewed RC34 release note after all native evidence is complete."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/render-runtime-rc34"
FINAL=QA/"release-final"
VERSION="3.0.0-rc34-preview"
RELEASE=ROOT/"release"/VERSION
DOC=ROOT/"docs/paper-warfront/144-战争迷雾可见性缓存与rc34预览交付.md"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text("utf-8"))
assert not DOC.exists() and not (RELEASE/"README.md").exists()
validation=read(FINAL/"validation-report.json")
assert validation["passed"] and validation["version"]==VERSION
manifest=read(RELEASE/"build-manifest.json")
assert manifest["version"]==VERSION and len(manifest["source_inputs"])==1194
assert all(sha(ROOT/n)==digest for n,digest in manifest["source_inputs"].items())
for platform in ["windows","apk"]:
    primary=read(FINAL/(platform+"-logic/report.json"))
    assert primary["passed"] and sum(r["checks"] for r in primary["tests"])==187249
    for prefix,count in [("dense",102920),("terrain",5873),("phase",461238)]:
        report=read(FINAL/(prefix+"-"+platform+"/report.json"));assert report["passed"] and report["checks"]==count
pixels=read(FINAL/"visibility-render/report.json")
assert pixels["passed"] and len(pixels["comparisons"])==42 and all(r["max_channel_delta"]==0 for r in pixels["comparisons"])
frames=read(FINAL/"realtime/report.json");assert frames["passed"] and frames["version"]==VERSION
natural=read(QA/"visibility-r4d-natural-observation.json");assert natural["passed"] and len(natural["cases"])==4
base=[r for r in natural["cases"] if r["label"]=="baseline"];candidate=[r for r in natural["cases"] if r["label"]=="candidate"]
assert max(r["draw_mean_ms"] for r in candidate)<min(r["draw_mean_ms"] for r in base)
correction=read(QA/"visibility-r4d-correction.json");assert correction["passed"]
story=read(QA/"authorship.json");assert story["passed"] and story["authored_maps"]==200
exe_hash,apk_hash=(r["sha256"] for r in manifest["builds"])
fps_table="\n".join(f"| {r['case']} | {r['max_units']} | {r['fps_from_mean_interval']:.2f} | {r['p95_frame_ms']:.3f} |" for r in frames["cases"])
candidate_table="\n".join(f"| {r['order']} | {r['label']} | {r['fps']:.2f} | {r['draw_mean_ms']:.3f} | {r['p95_frame_ms']:.3f} |" for r in natural["cases"])
text=f'''# 战争迷雾可见性缓存、单机剧情地图与rc34预览交付

本次 RC34 修复了战斗视图侧可见性查询缓存的生命周期。地图切换、战争迷雾 revision 更新或观察阵营切换时，路标和分岔查询都会重新取值；缓存不会把上一张地图或上一轮雾幕的坐标结果带到当前战场。模拟规则、地图几何、单位动作、AI、剧情数据和素材没有被这次修复改变。

## 单机地图必须承载剧情

十章200张单机地图继续遵守“地图即叙事场所”的设计合同。每张地图均绑定稳定的地图ID、战前冲突、地点动机、真实胜利目标、战后结果和独立证据旗；`campaign.json`负责实际对战与对白，`campaign-flow.json`负责章节推进，`campaign-narrative.json`负责故事与道路/目标绑定。当前作者档案已核验200张地图，其中后续180张也有独立剧情记录。

地图结构按冲突选型，不强制线性：可以是单路压迫、分岔后汇流、并行调查后合印、可回访支线或章节内择一。战役推进图和一场战斗里的道路图独立；道路的长度、桥口、矿点、汇流、保护对象和未知区域必须改变自动行军、运金风险、视野或任务窗口。剧情文字不会绕过战争迷雾泄露实时敌情，未走支线也不会凭空获得证据。

第一章已有六组择一路线并在事实齐备后汇合，后续章节使用并行调查、条件汇流和回访组合。单机“继续”只推荐当前真正可行动的剧情页，不假定下一张图必然是唯一线性后继。失败不推进；重访保留最高星级与已取得证据。

## RC34 可见性修复证据

| 范围 | 结果 |
|---|---:|
| R4d 源码回归 | 78组 / 195435项，通过 |
| R4d 固定姿态画面对照 | 42组，像素差0 |
| 紧凑移动路线/分岔矩阵 | 通过，恢复路牌可见矩形 |
| Windows/APK基础逻辑 | 各36组 / 187249项，通过 |
| 密集、地形、阶段编译检查 | 各102920、5873、461238项，通过 |
| 200图剧情作者记录 | 200张，通过 |

R4d 的四次串行自然压力窗口如下；124单位压力夹具用于观察渲染开销，不等同正常付费平衡，也不代表Android硬件FPS。

| 顺序 | 输入 | FPS | 绘制CPU均值 | P95帧间隔 |
|---:|---|---:|---:|---:|
{candidate_table}

实际导出程序帧率：

| 场景 | 峰值单位 | 平均FPS | P95帧间隔 |
|---|---:|---:|---:|
{fps_table}

战争迷雾仍统一约束战场、小地图、AI、施法和路标；镜头移动不揭示敌人，上下道路独立侦察。折纸UI与动作图集沿用已核验的Sub2/gpt-image-2.5素材，本次没有生成新位图。

## 已知范围

持续满员60FPS、全阵营/全关人工平衡、原作精确视野时序、真人完整剧情体验、Android实体设备与真人联机仍待完成；本机没有可用Android手机，也未使用模拟器。Windows和Android包已由Godot 4.7.2原生工具导出，Android仅完成Windows原生APK资源/字节码检查。

## 下载

- [Windows ZIP](../../release/{VERSION}/PaperWarfront-Windows-{VERSION}.zip)
- [Windows EXE](../../release/{VERSION}/windows/PaperWarfront.exe)
- [Android APK](../../release/{VERSION}/android/PaperWarfront-{VERSION}.apk)
- [发布验证](../../release/{VERSION}/preview-verification.json)
- [SHA256清单](../../release/{VERSION}/SHA256SUMS.txt)

EXE SHA256：`{exe_hash}`  
APK SHA256：`{apk_hash}`
'''
DOC.write_text(text,"utf-8")
(RELEASE/"README.md").write_text(text,encoding="utf-8")
backup=QA/"pre-publication-r4d";assert not backup.exists()
for name in ["README.md","docs/paper-warfront/README.md"]:
    src=ROOT/name;dst=backup/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    old=src.read_text("utf-8")
    entry="[144-战争迷雾可见性缓存、单机剧情地图与rc34交付](144-战争迷雾可见性缓存与rc34预览交付.md)：R4d按地图/迷雾revision修复路标缓存，42组画面对照像素差0；十章200张单机地图逐图绑定剧情，路线按冲突选型，可线性、分岔、汇流或回访。"
    if name=="docs/paper-warfront/README.md":
        src.write_text(old.replace(old.splitlines()[0],"# 纸上兵戈：十院留名 · rc34-preview",1).replace("\n\n", "\n\n"+entry+"\n\n",1),"utf-8")
    else:
        src.write_text("# 纸上兵戈：十院留名 · rc34-preview\n\n"+entry.replace("](144-", "](docs/paper-warfront/144-")+"\n\n"+old.lstrip("# 纸上兵戈：十院留名 · rc33-preview\n"),"utf-8")
files=[DOC,RELEASE/"README.md",ROOT/"README.md",ROOT/"docs/paper-warfront/README.md"]
(QA/"publication.json").write_text(json.dumps({"passed":True,"version":VERSION,"files":{p.relative_to(ROOT).as_posix():sha(p) for p in files},"scope":"Published after R4d source/pixel/mobile correction and fresh native package validation. 200-map single-player narrative and non-linear route contract retained. Hardware Android and human balance/story review remain pending."},ensure_ascii=False,indent=2)+"\n","utf-8")
print(json.dumps({"passed":True,"doc":DOC.relative_to(ROOT).as_posix(),"exe_sha256":exe_hash,"apk_sha256":apk_hash}))

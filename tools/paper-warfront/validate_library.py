"""Validate real asset outputs and cross-reference the original game data."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import array
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
LIB=ROOT/"assets/paper-warfront"
REPORT=ROOT/"docs/paper-warfront/素材库检查报告.md"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def acyclic(nodes,parent_key):
    lookup={node["id"]:node for node in nodes}
    visiting,visited=set(),set()
    def visit(key):
        if key in visiting:
            raise ValueError("Cycle: "+key)
        if key in visited:
            return
        visiting.add(key)
        parents=lookup[key].get(parent_key,[])
        if isinstance(parents,str):
            parents=[] if parents=="root" else [parents]
        for parent in parents:
            if parent not in lookup:
                raise ValueError("Missing parent: "+parent)
            visit(parent)
        visiting.remove(key)
        visited.add(key)
    for key in lookup:
        visit(key)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    errors,warnings,checks=[],[],[]
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    if not REPORT.exists():
        REPORT.write_text("# 素材库检查报告\n",encoding="utf-8")
    registry=read_json(LIB/"library-manifest.json")
    records=registry["assets"]
    ids={r["id"] for r in records}
    if len(ids)!=len(records):
        errors.append("Duplicate asset IDs")
    images,portraits,sounds,rigs=0,0,0,0
    for record in records:
        try:
            if not re.fullmatch(r"[a-z][a-z0-9]*(?:\.[a-z0-9-]+)+",record["id"]):
                raise ValueError("Invalid stable ID")
            path=(ROOT/record["asset_path"]).resolve()
            if not path.is_relative_to(LIB.resolve()):
                raise ValueError("Asset path escaped its library")
            if not path.is_file():
                raise ValueError("Missing asset file")
            if record["category"]=="audio":
                sounds+=1
                with wave.open(str(path),"rb") as sound:
                    assert sound.getnchannels()==1 and sound.getsampwidth()==2 and sound.getframerate()==44100
                    assert abs(sound.getnframes()/44100-record["duration"])<1/44100
                    samples=array.array("h",sound.readframes(sound.getnframes()))
                if sys.byteorder!="little":
                    samples.byteswap()
                assert max(abs(s) for s in samples)<32767
                assert abs(samples[0])<32 and abs(samples[-1])<32
            else:
                images+=1
                with Image.open(path) as image:
                    image.load()
                    assert image.format=="PNG"
                    assert image.size==(record["export_info"]["width"],record["export_info"]["height"])
                    if record["category"] not in ("texture","background"):
                        assert image.mode=="RGBA" and image.getchannel("A").getextrema()[0]==0
                        assert image.getchannel("A").getbbox()
                        box=record["export_info"]["content_box"]
                        assert 0<=box[0]<box[2]<=image.width and 0<=box[1]<box[3]<=image.height
                        assert image.getchannel("A").crop((0,0,image.width,1)).getextrema()[1]==0
                    else:
                        assert image.mode=="RGB"
                assert hashlib.sha256(path.read_bytes()).hexdigest()==record["export_info"]["sha256"]
                source=ROOT/record["source_path"]
                with Image.open(source) as original:
                    original.load()
                    left,top,right,bottom=record["export_info"]["source_crop"]
                    assert 0<=left<right<=original.width and 0<=top<bottom<=original.height
                if record.get("qa",{}).get("cell_border_touch") and not record["qa"].get("cell_boundary_review"):
                    warnings.append(record["id"]+"：源格边界需要视觉确认")
            if record.get("portrait_path"):
                portraits+=1
                with Image.open(ROOT/record["portrait_path"]) as portrait:
                    portrait.load()
                    assert portrait.size==(192,192) and portrait.mode=="RGBA"
            if record.get("rig_path"):
                rigs+=1
                rig=read_json(ROOT/record["rig_path"])
                assert rig["id"]==record["id"]
                assert len({p["id"] for p in rig["parts"]})==len(rig["parts"])
                acyclic(rig["parts"],"parent")
                for part in rig["parts"]:
                    assert len(part["pivot"])==3
                    if "polygon" in part:
                        polygon=part["polygon"]
                        assert len(polygon)>=3
                        area=sum(polygon[i][0]*polygon[(i+1)%len(polygon)][1]-polygon[(i+1)%len(polygon)][0]*polygon[i][1] for i in range(len(polygon)))
                        assert abs(area)>.0001
        except Exception as error:
            errors.append(record["id"]+": "+str(error or type(error).__name__))
    checks.append(f"{images}张基础PNG、{portraits}张头像、{sounds}个WAV和{rigs}份rig蓝图逐项校验")

    try:
        balance=read_json(LIB/"balance-prototype.json")
        technology=read_json(LIB/"technology.json")
        unit_ids={r["id"] for r in records if r["category"]=="unit"}
        spell_ids={r["id"] for r in records if r["category"]=="spell"}
        assert set(balance["units"])==unit_ids
        assert set(balance["spells"])==spell_ids
        assert set(balance["buildings"]).issubset(ids)
        for unit in balance["units"].values():
            if unit.get("summons"):
                assert unit["summons"] in unit_ids
        for spell in balance["spells"].values():
            if spell.get("summons"):
                assert spell["summons"] in unit_ids
        workers=[balance["units"][f"unit.{faction}.worker"] for faction in ("yin","mo","deng")]
        assert workers[0]==workers[1]==workers[2]
        nodes=technology["nodes"]
        assert len(nodes)==len({n["id"] for n in nodes})
        acyclic(nodes,"requires")
        node_by_id={n["id"]:n for n in nodes}
        grants=set()
        for node in nodes:
            assert node["grant"] in ids or node["grant"] in balance["upgrades"]
            assert node["grant"] not in grants
            grants.add(node["grant"])
            assert node["gold"]>0 and node["seconds"]>=0
            assert all(node_by_id[parent]["faction"]==node["faction"] for parent in node["requires"])
        unlocked={key for values in technology["starting_unlocked"].values() for key in values}
        assert unlocked.issubset(ids)
        required={key for key,unit in balance["units"].items() if unit.get("manual_recruit",True)}|spell_ids
        assert required.issubset(grants|unlocked)
        checks.append(f"17单位、15法术、7建筑数据覆盖；{len(nodes)}个科技节点无环、授予有效、可招募内容可解锁；三工人经济一致")
    except Exception as error:
        errors.append("Rules/technology: "+str(error or type(error).__name__))

    plan=read_json(ROOT/"output/imagegen/paper-warfront/jobs.json")
    assigned=[]
    for job in plan["jobs"]:
        try:
            assert (ROOT/job["prompt_path"]).is_file()
            with Image.open(ROOT/job["source_path"]) as source:
                source.verify()
            assert len(job["asset_ids"])<=job["grid"][0]*job["grid"][1]
            assigned+=job["asset_ids"]
        except Exception as error:
            errors.append(job["id"]+": "+str(error or type(error).__name__))
    assert len(assigned)==len(set(assigned))
    if set(assigned)!={r["id"] for r in records if r["category"]!="audio"}:
        errors.append("Generation jobs do not cover every image definition exactly once")
    checks.append(f"{len(plan['jobs'])}个生成任务、提示词与源图有效，图片定义映射完整")

    linked=0
    for doc in [*ROOT.joinpath("docs/paper-warfront").glob("*.md"),LIB/"README.md",ROOT/"tools/paper-warfront/README.md",ROOT/"docs/游戏方向提案-五选一.md",ROOT/"README.md",ROOT/"release/README.md"]:
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)",doc.read_text(encoding="utf-8")):
            if target.startswith(("https:","http:","#")):
                continue
            target=target.split("#")[0].strip("<>")
            if not (doc.parent/target).resolve().is_file():
                errors.append(str(doc.relative_to(ROOT))+": missing link "+target)
            linked+=1
    checks.append(f"{linked}个本地文档/素材链接检查")

    gallery=(LIB/"gallery.html").read_text(encoding="utf-8")
    script=re.search(r"<script>([\s\S]*?)</script>",gallery).group(1)
    node=shutil.which("node")
    if node:
        with tempfile.TemporaryDirectory(prefix="paper-warfront-js-") as temp:
            path=Path(temp)/"gallery.js"
            path.write_text(script,encoding="utf-8")
            result=subprocess.run([node,"--check",str(path)],capture_output=True,text=True)
            if result.returncode:
                errors.append("Gallery JavaScript: "+result.stderr)
            else:
                checks.append("离线浏览页JavaScript语法检查通过；未在浏览器中宣称交互验收")
    else:
        warnings.append("Node不可用，离线浏览页JavaScript语法未额外检查")
    runtime=read_json(LIB/"runtime-manifest.json")
    if set(runtime["assets"])!=ids:
        errors.append("Runtime manifest ID coverage differs")
    for record in records:
        if runtime["assets"][record["id"]]["status"]!=record["status"]:
            errors.append("Runtime manifest status out of sync: "+record["id"])

    statuses=Counter(r["status"] for r in records)
    report=["# 素材库检查报告","",f"检查时间：{datetime.now(timezone.utc).isoformat()}。工具：`validate_library.py`。","",f"结论：{'技术检查通过' if not errors else '存在检查失败'}；{len(errors)}项错误，{len(warnings)}项待确认。","",f"登记{len(records)}项，实际{images+portraits}张加工图片、{sounds}个原型WAV、{rigs}份厚片蓝图；图片源任务{len(plan['jobs'])}项。","","## 已检查","",*["- "+check for check in checks],"","## 素材状态","",*[f"- {status}: {count}" for status,count in sorted(statuses.items())],"","## 待确认与限制","","- 所有资产的游戏内加载、动画、密集点选与性能仍待可玩切片验证。","- 20个SFX和3个节奏草稿完成格式/波形校验，听感、循环和混音待试听及游戏验证。","- 纸材并未承诺无缝平铺；整身PNG不是已经拆好的关节分件。",*["- "+warning for warning in warnings]]
    report[report.index("## 待确认与限制")+2:]=[
        "- 本报告检查源图、原型WAV、历史厚片蓝图及本地链接；当前Godot使用另行加工的纸偶分件。",
        "- Godot运行库的116项绑定、53分件、正式配乐与字库已完成独立校验，见 [运行资源报告](../../output/qa/godot/runtime-assets-report.json)。",
        "- Windows实际程序的菜单、战场、动画和十五法术画面及合法通关记录见 [运行验收与交付报告](15-运行验收与交付报告.md)。",
        "- Android尚未真机运行；手机触控、听感、性能和长时间稳定性未实测。",
        "- 纸材未承诺无缝平铺；整身源图与运行分件保留各自加工溯源。",
        *["- "+warning for warning in warnings]
    ]
    if errors:
        report += ["","## 检查错误","",*["- "+error for error in errors]]
    REPORT.write_text("\n".join(report)+"\n",encoding="utf-8")
    print(f"Assets={len(records)}, PNG={images+portraits}, WAV={sounds}, rigs={rigs}, sources={len(plan['jobs'])}, errors={len(errors)}, warnings={len(warnings)}")
    for error in errors:
        print("ERROR: "+error)
    for warning in warnings:
        print("REVIEW: "+warning)
    sys.exit(1 if errors else 0)


if __name__=="__main__":
    main()

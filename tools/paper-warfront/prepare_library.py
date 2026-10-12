"""Prepare the asset registry, repeatable Sub2API prompts, and procedural rig data."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "paper-warfront"
OUTPUT = ROOT / "output" / "imagegen" / "paper-warfront"

STYLE = """Original Paper Warfront game art. A humorous side-scrolling army RTS depicted as articulated thick paper cutouts. Strict orthographic side elevation, fixed camera, no perspective foreshortening. Warm ivory rice paper, muted cinnabar red, warm charcoal ink, subdued jade and dull ochre gold. Broad woodblock contours, sparse delicate paper fibers, visibly thin paper edges, angular folded joints. Printed pigment is matte, never glossy or metallic. Chunky readable face and equipment, clear silhouette, no realistic human anatomy, no intricate realistic skeletons. No real franchise characters or logos. No words, captions, UI, readable lettering, watermark, photographic backdrop or tabletop photography. No light bloom, depth of field or cast shadow baked around assets. Never use purple as a base faction color: muted violet is only a small ink-magic accent. No plastic or metal toys, no soft watercolor outlines, no smooth sculpted 3D figurines. Paper thickness is a narrow edge, not a bulky solid body."""


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def asset_file(category, asset_id):
    stem = asset_id.replace(".", "-")
    folders = {"unit":"characters/cutouts", "portrait":"characters/cutouts", "spell":"ui/icons", "ui":"ui/icons", "building":"buildings/reference", "resource":"buildings/reference", "texture":"materials", "prop":"props", "fx":"fx/motifs", "background":"backgrounds", "audio":"audio/sfx"}
    return "assets/paper-warfront/" + folders[category] + "/" + stem + (".wav" if category == "audio" else ".png")


def sheet_prompt(items, grid, kind):
    cols, rows = grid
    content = []
    for index, item in enumerate(items):
        detail = item.get("visual", item.get("motif", ""))
        content.append(f"Cell {index + 1}, row {index // cols + 1}, column {index % cols + 1}: {detail}")
    if kind == "characters":
        rule = "Every cell has exactly ONE complete figure or cart, all facing RIGHT, in a neutral ready-to-animate standing pose, feet level. Entire weapon and all hands, feet and props remain inside the cell. Consistent paper illustration style and scale: workers/thralls small, heavy guards wider, giant deliberately taller. Keep a 14 percent empty margin inside every cell. No attack effects, floor, contact shadows, ground planes, scenery, pedestal or extra soldier. No silhouette overlaps or objects crossing cell boundaries."
    elif kind == "icons":
        rule = "Each cell contains exactly ONE bold flat printed-paper pictogram centered in its cell, approximately 60 percent cell width and height, intelligible at 48 pixels. At most three colors in each icon, uniform 3-pixel-equivalent strong ink stroke. No round button backing, no badge frame, no text, digits or extra decorations. Open spaces and holes show the magenta background, not white paint."
    elif kind == "textures":
        rule = "Each cell is fully filled edge to edge with its own uniformly lit flat paper material sample. Equal regular rectangular cells, no gaps, margins, frame, labels, objects or magenta backdrop. Sparse texture grain, no gradient, no vignette, no photographic highlights. Each cell is a texture surface only, not a paper sheet photographed from an angle."
    else:
        rule = "Each cell contains exactly ONE isolated orthographic side-view paper object or bounded visual motif centered, filling at most 72 percent cell width and height with a 14 percent margin. No base tile, ground line, contact shadow, scenery, text, label or object crossing cell boundaries. Large simple folded-paper panels, no complex sculpted ornament."
    backdrop = "" if kind == "textures" else "All empty space is one perfectly flat solid chroma-magenta #FF00FF color, including internal holes. This vivid magenta is ONLY the removable background. No other magenta material, gradient, checkerboard, off-white panel, cell borders or grid lines."
    return STYLE + f"\n\nA precise equal-cell sprite source sheet with {cols} columns and {rows} rows, read left-to-right then top-to-bottom. Exactly {len(items)} subjects. Grid is a mathematical layout, invisible, no dividers.\n" + rule + "\n" + backdrop + "\n\n" + "\n".join(content)


def polygon(w, h):
    return [[-w * .5, 0], [w * .5, 0], [w * .48, h * .8], [w * .28, h], [-w * .38, h * .93]]


def rig_for(unit, colors):
    common = {"id":unit["id"], "version":"0.1.0", "facing":"right", "origin":"feet-center", "axes":{"x":"battleline-right", "y":"up", "z":"toward-camera"}, "world_height":unit["height"], "paper_depth":.06 if unit["shape"] in ("heavy", "giant") else .035, "stage":"geometry-blueprint", "texture_policy":"Generated whole-body cutout is a visual reference and prototype stand-in; articulated final parts use paper-material textures and these geometry nodes.", "material_colors":colors}
    if unit["shape"] == "cart":
        common["parts"] = [
            {"id":"body","parent":"root","pivot":[0,.32,0],"polygon":polygon(1.15,.45),"material":"faction"},
            {"id":"barrel","parent":"body","pivot":[.1,.34,.03],"polygon":[[-.15,0],[.85,0],[.85,.25],[-.15,.36]],"material":"paper"},
            {"id":"wheel-back","parent":"root","pivot":[-.42,.25,.025],"primitive":"disc","radius":.26,"material":"ink"},
            {"id":"wheel-front","parent":"root","pivot":[.42,.25,.065],"primitive":"disc","radius":.26,"material":"ink"}
        ]
        common["animation_profile"] = "cart"
        return common
    width = {"broad":.65,"ranged":.48,"heavy":.87,"worker":.48,"slender":.43,"giant":.88,"fan":.62}[unit["shape"]]
    common["root_scale"] = unit["height"] / 1.8
    common["parts"] = [
        {"id":"torso","parent":"root","pivot":[0,.69,0],"polygon":polygon(width,.68),"material":"faction"},
        {"id":"head","parent":"torso","pivot":[.06,.66,.055],"polygon":polygon(.43,.39),"material":"paper"},
        {"id":"helmet","parent":"head","pivot":[0,.3,.008],"polygon":[[-.27,0],[.27,0],[.18,.15],[-.13,.2]],"material":"faction"},
        {"id":"arm-back","parent":"torso","pivot":[-.15,.54,-.03],"polygon":polygon(.19,-.4),"material":"faction"},
        {"id":"hand-back","parent":"arm-back","pivot":[0,-.36,.005],"polygon":polygon(.2,-.19),"material":"paper"},
        {"id":"leg-back","parent":"root","pivot":[-.15,.72,-.018],"polygon":polygon(.21,-.36),"material":"ink"},
        {"id":"shin-back","parent":"leg-back","pivot":[0,-.31,.006],"polygon":[[-.1,0],[.11,0],[.14,-.35],[-.16,-.35]],"material":"faction"},
        {"id":"leg-front","parent":"root","pivot":[.16,.72,.025],"polygon":polygon(.24,-.36),"material":"ink"},
        {"id":"shin-front","parent":"leg-front","pivot":[0,-.31,.006],"polygon":[[-.11,0],[.12,0],[.23,-.35],[-.13,-.35]],"material":"faction"},
        {"id":"arm-front","parent":"torso","pivot":[.2,.54,.075],"polygon":polygon(.22,-.38),"material":"faction"},
        {"id":"hand-front","parent":"arm-front","pivot":[.04,-.35,.012],"polygon":polygon(.22,-.18),"material":"paper"}
    ]
    common["equipment"] = {"weapon":unit["weapon"],"attachment":"hand-front","shield":unit.get("shield"),"construction":"extruded-paper-polygon","design_reference":asset_file(unit["id"].split(".")[0],unit["id"])}
    common["face_marks"] = {"mode":"procedural-ink-shapes","eyes":[[-.065,.22],[.065,.22]],"eyebrow_width":.065,"mouth_y":.12,"no_readable_glyphs":True}
    common["animation_profile"] = "worker" if unit["shape"] == "worker" else "biped"
    return common


def main():
    definition = json.loads((ASSETS / "library-definition.json").read_text(encoding="utf-8"))
    tokens = json.loads((ASSETS / "style-tokens.json").read_text(encoding="utf-8"))
    previous = {}
    registry_file = ASSETS / "library-manifest.json"
    if registry_file.exists():
        previous = {r["id"]:r for r in json.loads(registry_file.read_text(encoding="utf-8"))["assets"]}
    jobs, records = [], []
    categories = ["units","spells","structures","ui","textures","props","fx","backgrounds","audio"]
    for category in categories:
        for item in definition[category]:
            prefix = item["id"].split(".")[0]
            record = dict(item)
            record.update({"category":prefix,"faction":item.get("faction","common"),"asset_path":asset_file(prefix,item["id"]),"status":"design-ready","version":"0.1.0"})
            if prefix in ("unit","portrait"):
                record["portrait_path"] = "assets/paper-warfront/ui/portraits/" + item["id"].replace(".","-") + ".png"
                record["usage"] = "full-body-reference-and-prototype-cutout"
                if prefix == "unit":
                    record["rig_path"] = "assets/paper-warfront/rigs/" + item["id"].replace(".","-") + ".json"
                    faction = next(f for f in definition["factions"] if f["id"] == item["faction"])
                    write_json(ROOT / record["rig_path"], rig_for(item,{"faction":faction["color"],"paper":tokens["colors"]["paper"],"ink":tokens["colors"]["ink"],"edge":tokens["colors"]["paper_edge"]}))
            elif prefix in ("building","resource","fx"):
                record["usage"] = "visual-reference; final geometry or effect is procedural"
            else:
                record["usage"] = "runtime-candidate-after-visual-review"
            for key in ("status","export_info","qa","audio_info"):
                if key in previous.get(item["id"],{}):
                    record[key] = previous[item["id"]][key]
            records.append(record)

    def add_sheet(job_id, items, grid, kind, faction="common"):
        prompt = sheet_prompt(items,grid,kind)
        jobs.append({"id":job_id,"kind":kind,"faction":faction,"grid":grid,"asset_ids":[i["id"] for i in items],"prompt_path":"output/imagegen/paper-warfront/prompts/"+job_id+".txt","source_path":"output/imagegen/paper-warfront/sources/"+job_id+".png","requested_size":"1536x1024","chroma":kind!="textures"})
        path = ROOT / jobs[-1]["prompt_path"]
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(prompt + "\n",encoding="utf-8")

    for faction in definition["factions"]:
        add_sheet("characters-"+faction["id"],[u for u in definition["units"] if u["faction"]==faction["id"] and not u.get("source_group")],[3,2],"characters",faction["id"])
    add_sheet("characters-commanders",[u for u in definition["units"] if u.get("source_group")=="commanders-extra"],[2,1],"characters")
    add_sheet("structures",definition["structures"],[3,3],"objects")
    for faction in definition["factions"]:
        spells = [s for s in definition["spells"] if s["faction"]==faction["id"]]
        add_sheet("spells-"+faction["id"],spells,[5,1],"icons",faction["id"])
    add_sheet("ui-common",definition["ui"],[4,4],"icons")
    add_sheet("paper-materials",definition["textures"],[3,3],"textures")
    add_sheet("terrain-props",definition["props"],[3,3],"objects")
    add_sheet("fx-motifs",definition["fx"],[4,3],"objects")
    for background in definition["backgrounds"]:
        job_id=background["id"].replace(".","-")
        prompt=STYLE+"\n\nCreate ONE wide quiet scenery backdrop ONLY, no figures, buildings in foreground, HUD, road or active ground. "+background["motif"]+". The lower 30 percent is almost empty low-contrast ivory paper haze, to protect combat silhouettes that will later be rendered separately. Panoramic but flat layered side-view paper scenery. Maximum three low-contrast depth layers, edge detail subdued, use paper cutout silhouettes and sparse printed fiber. No saturated black foreground or large decorative object. Not chroma-magenta."
        jobs.append({"id":job_id,"kind":"background","grid":[1,1],"asset_ids":[background["id"]],"prompt_path":"output/imagegen/paper-warfront/prompts/"+job_id+".txt","source_path":"output/imagegen/paper-warfront/sources/"+job_id+".png","requested_size":"1536x1024","chroma":False})
        (ROOT/jobs[-1]["prompt_path"]).write_text(prompt+"\n",encoding="utf-8")
    look_prompts = {
        "look-style-board": STYLE+"\n\nOne clean art-direction reference board on warm ivory paper. Left third: three LARGE complete paper soldiers side by side, broad vermilion axe-and-square-shield soldier, skinny ink-black mask-and-hook-blade hunter, jade fan-helmet mirror-shield guard. All face right at exactly same camera angle and foot baseline; show the differences in widths and gear. Center third: enlarged paper-joint construction, shoulder hinge, folded shield edge, layered paper helmet and five simple face expressions. Right third: eight tidy solid pigment swatches and six small flat printed spell motifs. No words or labels, no battle, no UI. Sparse black ink outlines, limited thickness, not an ornate collage. The exact modelable paper shape language matters most.",
        "look-lantern-battle": STYLE+"\n\nLandscape visual target of a playable local clash on one horizontal paper road in a longer scrolling battlefield. No bases in main view, around ten LARGE soldiers, main infantry one fifth image height. Left vermilion stamp army: broad axe shields in front, paper spear throwers behind, one stamp hammer heavy. Right jade Lantern Seal Court: round mirror-shield curved-blade soldiers in front, red fire-slip shooters behind, narrow folded shadow infiltrator, thick ivory jade paper effigy further back. One selected jade front soldier has a thin pale outline and round jade protection seal; a second lighter but opaque identical soldier unfolds beside him as a temporary clone, with a small source-link pictogram. One reflected paper spear follows a short clear return arc near mirror shield. Bounded effects, no three lanes, no realistic 3D. Top edge slim ivory paper HUD: gold 240 and blue mana 75, four circular jade recruit portraits, five clearly separated spell pictograms (shield, duplicate, fire slips, anchored foot, summoned guardian), tiny blue costs and far-right tech-tree icon. Bottom thin paper battlefield-navigation line with tiny bases ONLY at ends, unit dots and current-view rectangle. Faint jade-grey mountain background. No giant center panel, no hero controls, no third resource. This is concept art, not an actual runtime screenshot."
    }
    for job_id,prompt in look_prompts.items():
        jobs.append({"id":job_id,"kind":"lookdev","grid":[1,1],"asset_ids":[],"prompt_path":"output/imagegen/paper-warfront/prompts/"+job_id+".txt","source_path":"output/imagegen/paper-warfront/sources/"+job_id+".png","requested_size":"1536x1024","chroma":False})
        (ROOT/jobs[-1]["prompt_path"]).write_text(prompt+"\n",encoding="utf-8")
    for job in jobs:
        for index,asset_id in enumerate(job["asset_ids"]):
            record=next(r for r in records if r["id"]==asset_id)
            record.update({"source_path":job["source_path"],"source_job":job["id"],"source_cell":{"column":index%job["grid"][0],"row":index//job["grid"][0],"grid":job["grid"]}})
    write_json(OUTPUT/"jobs.json",{"version":"0.1.0","skill":"sub2-image-gen","model":"gpt-image-2.5","jobs":jobs})
    write_json(registry_file,{"project":"paper-warfront","version":"0.1.0","status_model":["design-ready","source-generated","derived-candidate","visual-reviewed","runtime-verified"],"assets":records})
    write_json(ASSETS/"rigs"/"animation-profiles.json",{"version":"0.1.0","units":"degrees-and-milliseconds","profiles":{"biped":{"idle":{"period_ms":1100,"torso_bob":.025},"walk":{"period_ms":620,"leg_swing_degrees":19,"arm_swing_degrees":11},"attack":{"anticipation_ms":160,"strike_ms":80,"recovery_ms":240,"weapon_swing_degrees":65},"hit":{"duration_ms":170,"torso_rotation_degrees":-11},"cast":{"duration_ms":480,"arm_raise_degrees":-48},"death":{"duration_ms":420,"fold_rotation_degrees":78}},"worker":{"walk_period_ms":690,"mine_period_ms":750,"carry_pose_arm_degrees":-24},"cart":{"wheel_radius":.26,"recoil_distance":.08,"recoil_ms":180}}})
    print(f"Prepared {len(records)} asset definitions, {len(jobs)} generation jobs, and {sum(r['category']=='unit' for r in records)} procedural rig blueprints.")


if __name__=="__main__":
    main()

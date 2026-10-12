"""Build canonical guide boards from the reviewed generated assets and exact tokens."""
import json
from PIL import Image, ImageDraw
from export_library import LIB, ROOT, contact_sheet, font, write_json


def main():
    registry=json.loads((LIB/"library-manifest.json").read_text(encoding="utf-8"))
    records={r["id"]:r for r in registry["assets"]}
    tokens=json.loads((LIB/"style-tokens.json").read_text(encoding="utf-8"))
    board=Image.new("RGB",(1600,1060),tokens["colors"]["paper"])
    draw=ImageDraw.Draw(board)
    draw.text((36,24),"纸上兵戈 · 风格基准",font=font(42),fill=tokens["colors"]["ink"])
    draw.text((38,83),"正交侧视 / 薄纸层 / 印刷颜料 / 方、尖、扇三种阵营轮廓",font=font(19),fill=tokens["colors"]["muted_ink"])
    draw.line((36,122,1564,122),fill=tokens["colors"]["ink"],width=2)
    heroes=[("unit.yin.axe","印甲军 · 方肩方盾"),("unit.mo.blade","墨骸社 · 长肢尖面具"),("unit.deng.mirror","灯符朝 · 扇冠圆镜盾")]
    for index,(asset_id,label) in enumerate(heroes):
        x=36+index*330
        im=Image.open(ROOT/records[asset_id]["asset_path"]).convert("RGBA").resize((318,318),Image.Resampling.LANCZOS)
        board.paste(im,(x,180),im)
        draw.line((x+14,476,x+300,476),fill=tokens["colors"]["paper_edge"],width=1)
        draw.text((x+16,520),label,font=font(23),fill=tokens["colors"]["ink"])
        draw.text((x+16,557),asset_id,font=font(15),fill=tokens["colors"]["muted_ink"])
    draw.line((1040,146,1040,612),fill=tokens["colors"]["paper_edge"],width=1)
    swatches=[("paper","纸底"),("ink","墨轮廓"),("yin","印甲朱红"),("deng","灯符青色"),("gold","哑光金"),("mana","法力蓝"),("repair","补纸绿"),("poison","腐墨紫")]
    for index,(key,label) in enumerate(swatches):
        x=1070+(index%2)*242
        y=154+(index//2)*90
        draw.rectangle((x,y,x+72,y+50),fill=tokens["colors"][key],outline=tokens["colors"]["paper_edge"])
        draw.text((x+84,y),label,font=font(18),fill=tokens["colors"]["ink"])
        draw.text((x+84,y+29),tokens["colors"][key],font=font(14),fill=tokens["colors"]["muted_ink"])
    draw.text((1070,535),"普通纸厚 0.035 / 重型 0.06",font=font(18),fill=tokens["colors"]["ink"])
    draw.text((1070,570),"世界高 1.80 / 足底为根节点",font=font(18),fill=tokens["colors"]["ink"])
    draw.text((38,636),"材质基准 · 纤维轻，先读轮廓和色块",font=font(26),fill=tokens["colors"]["ink"])
    textures=[r for r in registry["assets"] if r["category"]=="texture"]
    for index,record in enumerate(textures):
        x=38+index*170
        im=Image.open(ROOT/record["asset_path"]).convert("RGB").resize((152,130),Image.Resampling.LANCZOS)
        board.paste(im,(x,688))
        draw.rectangle((x,688,x+152,818),outline=tokens["colors"]["paper_edge"],width=1)
        draw.text((x,831),record["name"],font=font(17),fill=tokens["colors"]["ink"])
    draw.line((36,880,1564,880),fill=tokens["colors"]["paper_edge"],width=1)
    draw.text((38,902),"造型：已检查源图 → 独立透明轮廓 → 厚片部件与附件",font=font(22),fill=tokens["colors"]["ink"])
    draw.text((38,943),"文字、费用、冷却、命中和归属由代码管理。整身图片是参考与原型切图。",font=font(19),fill=tokens["colors"]["muted_ink"])
    draw.text((38,996),"本板由 sub2-image-gen 生成素材与项目参数组装；用于美术生产，游戏内表现仍需验证。",font=font(16),fill=tokens["colors"]["muted_ink"])
    destination=LIB/"previews/style-guide.png"
    board.save(destination)
    portraits=[]
    for record in registry["assets"]:
        if record.get("portrait_path"):
            item=dict(record)
            item["asset_path"]=item["portrait_path"]
            portraits.append(item)
    contact_sheet(portraits,LIB/"previews/portraits.png",columns=5,cell_w=230,cell_h=240)
    write_json(LIB/"art-direction.json",{
        "version":"0.1.0",
        "canonical_references":["output/imagegen/v2/03-paper-warfront.png","assets/paper-warfront/previews/style-guide.png","assets/paper-warfront/previews/characters.png"],
        "authoritative_tokens":"assets/paper-warfront/style-tokens.json",
        "exploratory_illustrations":["output/imagegen/paper-warfront/sources/look-style-board.png","output/imagegen/paper-warfront/sources/look-lantern-battle.png"],
        "exploration_policy":"Independent concept illustrations may vary in helmet, weapon, proportions and HUD numbers. Use the checked character library, canonical assembled guide, and rule/tokens data for implementation.",
        "assembly_inputs":[records[key]["asset_path"] for key,label in heroes]+[r["asset_path"] for r in textures]
    })
    print("Canonical style guide, portrait review sheet, and art-direction reference policy saved.")


if __name__=="__main__":
    main()

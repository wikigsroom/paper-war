from pathlib import Path
from PIL import Image, ImageDraw
import json, shutil
ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT/'game'
stories = {
'yin':[
('第一道印','折斧先行，纸工归仓。','招募折斧兵，摧毁墨骸营地。先增加纸工能让后续增援更快。','mo',[],[],'stamp-plain'),
('补好这张甲','把裂缝补上，庆功宴再说。','用补纸救下前排。施法先选择法术，再点击目标；取消不会扣法力。','deng',[],[],'stamp-plain'),
('先买矛还是先买印','向前一寸，也要算好一枚金。','纸矛可在前排后持续投射。打开科技，选择雷印或加强回法。','mo',['unit.yin.spear'],['unit.mo.needle'],'stamp-plain'),
('大锤有空隙','纸再厚，也怕下错一锤。','压印锤卫能打断巨人的前摇；寒纸风为后排争取时间。','mo',['unit.yin.spear','spell.yin.lightning'],['unit.mo.needle','unit.mo.giant'],'ink-marsh'),
('攻到家门口','这一印，盖在他们门上。','解锁卷轴炮车破城。守住增援路线，再把落印送进敌阵。','deng',['unit.yin.spear','unit.yin.hammer','spell.yin.lightning','spell.yin.cold'],['unit.deng.fire','unit.deng.effigy'],'lantern-ridge')],
'mo':[
('纸也是法力','退役，只是另一种折法。','献纸以剩余生命换法力。纸工、召唤物和复制体不可献纸。','yin',[],[],'ink-marsh'),
('针墨留在纸上','让他们在同一个字里多站一会儿。','墨针持续腐蚀；墨缚禁止敌人移动和攻击。','deng',['unit.mo.needle','spell.mo.bind'],['unit.deng.fire'],'ink-marsh'),
('把他们折回来','落纸，回军。','拾纸祭司消费附近的阵亡纸标，召回纸骨兵。保护祭司的位置。','yin',['unit.mo.needle','spell.mo.bind','unit.mo.priest'],['unit.yin.spear'],'ink-marsh'),
('大纸人也会摔','给大个子留一个起手的空隙。','巨人范围重击威力大，蓄力却能被打断。用控制与墨针支援。','yin',['unit.mo.needle','unit.mo.priest','spell.mo.bind','unit.mo.giant'],['unit.yin.spear','unit.yin.hammer'],'stamp-plain'),
('这道印归我','借来一张纸，换走一支军。','夺印可以收编敌人的高价值战斗单位。为应急墨缚留一点法力。','deng',['unit.mo.needle','unit.mo.priest','unit.mo.giant','spell.mo.bind','spell.mo.poison'],['unit.deng.fire','unit.deng.effigy','spell.deng.protect'],'lantern-ridge')],
'deng':[
('先保住灯','灯一盏，军一行。','在固定建筑位建造产法纸灯。灯被摧毁，回法速度立即降低。','mo',[],[],'lantern-ridge'),
('把矛送回去','你寄来的签，请收好。','镜符刀卫可以反弹投射物一次。雷印和近战不会被反弹。','yin',['unit.deng.fire'],['unit.yin.spear','spell.yin.lightning'],'lantern-ridge'),
('同一张纸两份用','先印两份，再谈公平。','给前排护符，再复制可用兵种。复制体存在十秒，不能继续复制。','mo',['unit.deng.fire','spell.deng.clone'],['unit.mo.needle','unit.mo.priest'],'ink-marsh'),
('从这一折过去','绕过锋刃，折向空白。','折影客可有限越过前排。定字符让敌人站住，但其仍能攻击。','yin',['unit.deng.fire','unit.deng.shadow','spell.deng.clone','spell.deng.root'],['unit.yin.spear','unit.yin.hammer'],'stamp-plain'),
('印章不肯盖两次','把这场仗，折成我们的样子。','使用完整阵营组合。保护纸灯、调配火签，召出纸卫接住反扑。','mo',['unit.deng.fire','unit.deng.shadow','unit.deng.effigy','spell.deng.clone','spell.deng.root'],['unit.mo.needle','unit.mo.priest','unit.mo.giant','spell.mo.bind','spell.mo.poison'],'lantern-ridge')]
}
levels=[]
for faction, rows in stories.items():
    for n,(title,line,tip,enemy,kit,enemy_kit,map_id) in enumerate(rows):
        levels.append({'index':len(levels),'id':f'campaign.{faction}.{n+1}','title':title,'chapter':faction,'faction':faction,'enemy':enemy,'map':map_id,'line':line,'tip':tip,'tier':n+1,'difficulty':0 if n<2 else (1 if n<4 else 2),'starting_gold':260 if n<2 else 230,'enemy_starting_gold':110 if n==0 else (170 if n<4 else 230),'initial_unlocked':kit,'enemy_unlocked':enemy_kit,'ai_style':['rush','economy','counter'][n%3],'ai_army_limit':3 if n==0 else (5 if n==1 else 60),'ai_warmup':15 if n==0 else (10 if n==1 else 5),'win':'destroy_base','star_time':320 if n<3 else 420})
challenges=[
('守住薄纸城','yin','mo','stamp-plain','基地坚持 150 秒。科技完整开放；对手拥有公开的 420 起始金币。','survive',150),
('精准补纸','yin','deng','stamp-plain','获胜并施放至少三次补纸，获得额外星章。','destroy_base',0),
('折断巨人前摇','yin','mo','ink-marsh','对方巨人已解锁；锤卫和寒纸风能够打断与拖慢。','destroy_base',0),
('祭司争纸标','mo','yin','ink-marsh','完整科技开局；围绕祭司的阵亡纸标争夺战。','destroy_base',0),
('把火签寄回去','deng','yin','lantern-ridge','对方纸矛和炮车已解锁。镜符反弹一次，护符保住前排。','destroy_base',0),
('灯下反扑','deng','mo','lantern-ridge','建造至少一盏纸灯并获胜，获得额外星章。','destroy_base',0)]
out=[]
for i,(title,f,e,m,tip,win,dur) in enumerate(challenges):
    out.append({'index':i,'id':f'challenge.{i+1}','title':title,'faction':f,'enemy':e,'map':m,'tip':tip,'line':'纸有千折，兵有千法。','tier':5,'difficulty':1,'starting_gold':360,'enemy_starting_gold':420,'full_tech':True,'ai_style':'counter','win':win,'duration':dur,'star_time':360})
(GAME/'data/campaign.json').write_text(json.dumps({'version':'1.0.0','levels':levels,'challenges':out},ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copy2(ROOT/'output/imagegen/v2/03-paper-warfront.png', GAME/'assets/keyart.png')
# Launcher emblem assembled from generated paper shield, with original paper frame.
canvas=Image.new('RGBA',(512,512),'#343332')
draw=ImageDraw.Draw(canvas)
draw.rounded_rectangle((22,22,490,490),radius=62,fill='#e8deca',outline='#b74532',width=15)
draw.polygon([(256,69),(435,130),(413,366),(256,455),(99,366),(77,130)],fill='#b74532',outline='#343332',width=7)
unit=Image.open(GAME/'assets/ui/portraits/unit-yin-axe.png').convert('RGBA').resize((352,352),Image.Resampling.LANCZOS)
canvas.alpha_composite(unit,(80,83))
canvas.save(GAME/'assets/icon.png')
print('Prepared 15 campaign missions, 6 challenges, launcher icon')

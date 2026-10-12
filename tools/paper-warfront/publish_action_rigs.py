"""rc4: authored joint masks for all role masters + bespoke core silhouettes.

This processes the already approved Sub2/gpt-image-2.5 cutouts. It does not
generate new illustrations or claim 412 independently painted characters.
The source cutout and portrait stay intact; runtime limbs/tools are separate.
"""
from pathlib import Path
import json, hashlib, math, io
from PIL import Image, ImageDraw, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'game'
OUT = GAME / 'assets/animation/actions-rc4'

def read(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def poly(*p): return list(p)

# Reviewed against normalized 512px sources. Shoulder/elbow/grip are actual
# source coordinates, NOT the canvas centre. Tool masks omit the face/torso.
# (shoulder, elbow, grip, weapon polygon, tip).
R = {
 'vanguard': ((209,290),(159,317),(118,340),poly((35,188),(107,180),(172,358),(108,399),(43,314)),(70,217)),
 'javelin': ((200,338),(222,350),(258,356),poly((28,340),(357,337),(381,321),(404,333),(411,330),(481,354),(412,382),(391,374),(379,425),(338,435),(322,411),(349,373),(28,377)),(475,355)),
 'crusher': ((227,303),(153,278),(194,214),poly((35,36),(213,37),(219,147),(260,183),(263,221),(205,220),(197,238),(51,241),(34,198)),(132,125)),
 'artillery': ((280,252),(325,210),(350,204),poly((265,199),(417,113),(480,140),(480,281),(299,320)),(465,200)),
 'raider': ((268,350),(313,379),(360,390),poly((354,382),(403,331),(441,280),(469,355),(427,429),(373,427)),(451,320)),
 'poisoner': ((233,328),(275,329),(286,301),poly((272,286),(485,280),(485,316),(273,317)),(475,298)),
 'necromancer': ((292,341),(327,350),(359,332),poly((341,132),(480,107),(494,233),(421,278),(391,475),(350,469),(378,242),(353,216)),(431,175)),
 'colossus': ((363,280),(383,316),(418,358),poly((350,263),(416,264),(485,301),(490,387),(470,424),(405,435),(340,384),(337,336)),(475,358)),
 'mirror': ((254,304),(291,327),(338,338),poly((319,330),(350,295),(380,300),(473,222),(489,232),(486,293),(463,317),(380,351),(354,371),(321,368)),(472,240)),
 'repeater': ((203,296),(261,310),(300,306),poly((194,274),(477,242),(482,321),(245,344),(200,320)),(470,281)),
 'assassin': ((303,352),(333,368),(375,374),poly((373,353),(423,342),(471,306),(472,335),(432,390),(377,396)),(465,319)),
 'guard': ((149,270),(121,330),(104,364),poly((49,355),(122,342),(160,325),(314,254),(354,289),(354,346),(324,371),(165,397),(155,421),(124,418),(120,384),(49,392)),(337,294)),
 'engineer': ((244,299),(277,334),(306,341),poly((277,326),(335,290),(358,194),(405,181),(437,195),(402,239),(437,253),(456,220),(472,270),(416,310),(344,370),(303,380),(285,359)),(455,255)),
 'archer': ((302,311),(350,306),(394,300),poly((329,15),(402,61),(461,174),(433,297),(449,387),(398,490),(363,483),(374,423),(385,332),(389,239),(376,170),(327,72)),(440,285)),
 'harrier': ((331,302),(349,330),(378,358),poly((357,363),(381,342),(398,333),(441,190),(452,201),(464,267),(445,319),(410,348),(403,373),(382,397),(359,381)),(442,205)),
 'executioner': ((174,326),(204,363),(240,378),poly((215,359),(331,300),(343,283),(363,278),(389,249),(393,207),(351,139),(399,136),(451,167),(486,219),(489,283),(476,329),(438,367),(399,382),(400,421),(399,456),(342,456),(343,405),(351,389),(346,353),(243,398),(216,394)),(471,253)),
 'siege': ((211,177),(298,177),(365,177),poly((40,112),(480,109),(480,206),(41,203)),(474,155)),
 'medic': ((281,303),(313,322),(341,300),poly((299,56),(362,52),(405,115),(453,90),(468,136),(493,154),(482,179),(403,209),(416,254),(400,294),(356,259),(351,307),(339,472),(311,478),(316,387),(330,281),(316,235),(308,189),(299,139)),(381,125)),
 'shield': ((312,258),(344,277),(365,233),poly((347,216),(373,163),(450,83),(462,133),(410,200),(373,247)),(452,100)),
 'warden': ((317,310),(329,302),(351,285),poly((325,287),(337,259),(337,183),(329,151),(330,117),(342,80),(358,53),(390,38),(408,94),(441,93),(464,133),(437,176),(471,225),(471,247),(446,264),(463,303),(474,347),(444,342),(422,304),(414,260),(402,209),(390,213),(375,203),(355,186),(346,285),(345,467),(326,473)),(368,127)),
 'mortar': ((275,302),(302,255),(332,211),poly((225,145),(306,26),(376,25),(471,107),(452,213),(375,282),(279,293)),(402,107)),
 'berserker': ((290,322),(327,347),(360,342),poly((345,335),(368,260),(399,230),(473,278),(472,327),(417,378),(370,375)),(433,288)),
 'leech': ((238,342),(238,366),(267,369),poly((247,346),(339,319),(421,246),(465,175),(480,199),(472,281),(429,328),(341,360),(269,390),(245,385)),(469,185)),
 'oracle': ((311,292),(330,297),(342,290),poly((294,165),(408,158),(478,192),(485,285),(484,358),(343,399),(299,311)),(430,238)),
 'banner': ((273,354),(306,368),(344,342),poly((92,122),(240,87),(345,99),(378,78),(408,39),(429,53),(423,101),(402,110),(373,278),(355,474),(324,477),(331,283),(92,279),(156,206)),(410,67)),
 'burner': ((269,330),(298,331),(315,296),poly((285,343),(291,274),(278,246),(258,200),(255,156),(287,110),(288,46),(312,74),(369,83),(372,129),(389,128),(394,173),(391,194),(377,220),(359,251),(338,290),(329,350)),(327,160)),
 'caravan': ((277,315),(321,334),(341,315),poly((324,108),(391,80),(415,129),(387,202),(366,308),(361,456),(331,459),(342,214)),(377,151)),
 'chain': ((241,295),(196,289),(149,256),poly((35,256),(76,250),(85,290),(68,347),(145,365),(194,416),(165,462),(74,477),(21,406),(34,335),(50,300)),(107,420)),
 'cleaver': ((171,276),(196,321),(268,321),poly((242,309),(300,243),(434,124),(464,146),(493,263),(309,340),(246,351)),(460,185)),
 'demolisher': ((247,313),(278,351),(327,335),poly((290,281),(325,234),(398,214),(449,245),(468,318),(423,369),(338,384),(293,335)),(385,298)),
 'drummer': ((302,258),(339,237),(373,216),poly((362,239),(365,199),(370,155),(361,125),(382,113),(407,128),(402,152),(388,169),(387,228)),(386,132)),
 'duelist': ((245,321),(321,299),(352,293),poly((331,285),(350,262),(478,242),(481,257),(354,316),(331,311)),(479,248)),
 'illusionist': ((273,280),(306,259),(328,235),poly((273,182),(313,126),(354,101),(399,119),(445,159),(467,204),(452,254),(344,272)),(424,183)),
 'lancer': ((121,280),(144,313),(162,332),poly((29,392),(358,114),(375,89),(475,37),(481,55),(407,133),(428,220),(360,279),(351,162),(49,411)),(476,46)),
 'phoenix': ((217,215),(179,210),(141,237),poly((30,60),(119,105),(204,149),(249,200),(230,242),(192,285),(132,322),(68,344),(19,298),(49,217),(81,197),(20,179)),(49,102)),
 'pike': ((236,320),(262,321),(281,313),poly((257,9),(305,9),(389,226),(308,239),(302,480),(267,480)),(281,60)),
 'saboteur': ((306,346),(329,361),(352,356),poly((336,346),(403,291),(473,256),(458,294),(409,357),(354,380)),(464,267)),
 'scribe': ((301,310),(323,297),(335,284),poly((328,335),(357,271),(390,195),(398,154),(417,103),(482,51),(483,111),(459,166),(409,198),(407,228),(421,280),(434,313),(418,342),(393,339),(385,290),(378,249),(348,344)),(459,95)),
 'sniper': ((218,318),(274,329),(314,302),poly((201,279),(250,266),(475,276),(479,318),(316,326),(208,332)),(477,296)),
 'summoner': ((293,327),(334,301),(354,282),poly((325,328),(331,263),(341,205),(331,157),(333,96),(361,59),(393,55),(418,82),(436,105),(437,137),(424,151),(427,167),(474,146),(482,203),(454,213),(463,261),(436,270),(420,227),(399,214),(382,225),(360,283),(341,343)),(396,112)),
}

# Core silhouettes which do NOT share the chosen role master above.
CORE = {
 'unit.ji.vanguard': ((219,311),(194,348),(151,350),poly((39,231),(112,256),(152,309),(174,319),(169,351),(153,377),(123,396),(92,351),(55,317),(35,285)),(65,252)),
 'unit.yuan.vanguard': ((221,306),(206,342),(215,369),poly((174,369),(204,332),(230,343),(245,362),(341,400),(356,452),(271,452),(225,421),(190,395)),(341,430)),
 'unit.qi.vanguard': ((325,291),(362,320),(388,320),poly((357,319),(373,274),(399,194),(456,163),(478,227),(451,268),(405,319),(426,341),(415,362),(376,346)),(466,197)),
 'unit.ji.javelin': ((207,314),(229,347),(258,342),poly((51,342),(367,316),(375,295),(403,295),(480,321),(480,338),(408,358),(383,348),(377,390),(349,404),(324,400),(339,357),(60,366)),(474,324)),
 'unit.qi.javelin': ((218,322),(246,336),(277,333),poly((24,338),(349,306),(362,278),(478,291),(487,299),(478,319),(403,344),(377,344),(365,407),(350,428),(309,405),(319,348),(54,366)),(477,302)),
 'unit.shuang.javelin': ((224,329),(252,343),(276,341),poly((24,339),(347,323),(353,311),(372,307),(480,320),(488,329),(465,339),(393,355),(360,350),(359,386),(340,427),(315,421),(306,405),(318,359),(39,369)),(479,328)),
 'unit.mu.guard': ((307,316),(340,338),(389,338),poly((359,340),(363,273),(390,252),(402,171),(451,132),(483,195),(426,294),(434,321),(417,351),(395,387),(369,377)),(457,180)),
 'unit.mu.poisoner': ((232,296),(262,310),(282,288),poly((269,270),(480,272),(480,305),(269,306)),(474,288)),
 'unit.bai.mirror': ((331,291),(369,318),(388,304),poly((366,313),(383,281),(473,187),(489,193),(484,242),(463,268),(407,314),(391,339)),(474,213)),
 'unit.bai.repeater': ((205,353),(266,347),(309,331),poly((234,302),(476,268),(480,345),(333,366),(238,353)),(471,300)),
 'unit.jin.archer': ((287,287),(331,282),(384,274),poly((287,32),(343,32),(386,131),(426,234),(429,304),(407,346),(413,420),(412,478),(350,479),(332,443),(347,368),(353,313),(350,239),(333,168),(285,106)),(458,254)),
 'unit.shuang.warden': ((288,284),(322,316),(350,279),poly((335,50),(444,12),(484,107),(437,165),(371,215),(374,469),(341,472),(349,185),(370,118)),(421,91)),
 'unit.mu.colossus': ((358,287),(383,319),(421,362),poly((344,270),(431,266),(489,303),(490,405),(441,438),(369,430),(332,363)),(472,362)),
 'unit.bai.colossus': ((354,284),(381,321),(421,365),poly((343,265),(431,266),(490,316),(488,409),(443,438),(370,429),(331,365)),(475,364)),
}

BACK = {
 'drummer': ((211,281),(230,311),(258,317),poly((251,310),(299,302),(314,292),(339,292),(350,307),(350,329),(336,343),(310,333),(301,325),(252,327)),(321,316)),
 'raider': ((172,325),(127,317),(81,323),poly((33,307),(54,261),(71,275),(85,305),(93,341),(66,354),(24,336)),(37,306)),
 'berserker': ((205,316),(178,349),(151,349),poly((33,278),(82,232),(129,256),(165,321),(148,365),(85,373),(32,329)),(51,290)),
 'colossus': ((148,262),(116,311),(157,347),poly((60,243),(157,239),(225,278),(240,312),(225,399),(207,434),(88,445),(39,411),(26,345),(26,281)),(47,345)),
 'phoenix': ((239,217),(201,270),(150,297),poly((33,359),(96,316),(177,275),(224,271),(225,323),(185,362),(94,415),(42,410)),(57,402)),
}

GESTURE = {
 'vanguard':'slash','raider':'dual_slash','berserker':'dual_axe','guard':'guard_slash','mirror':'reflect_slash',
 'shield':'shield_thrust','harrier':'hook','executioner':'reap','leech':'crescent','cleaver':'cleave','duelist':'fence',
 'assassin':'ambush','saboteur':'stab','phoenix':'wing_strike','crusher':'hammer','colossus':'punch','demolisher':'bomb_bash',
 'lancer':'lance','pike':'pike','warden':'staff_push','siege':'ram','artillery':'cannon','mortar':'mortar',
 'javelin':'throw','archer':'bow','sniper':'sniper','repeater':'repeater','poisoner':'blowpipe','caravan':'lantern_cast',
 'chain':'chain_cast','burner':'fire_cast','drummer':'drum','banner':'banner_bash','medic':'heal_cast',
 'necromancer':'soul_cast','oracle':'orb_cast','scribe':'brush_cast','summoner':'summon_cast','illusionist':'fan_cast','engineer':'wrench'}
PROJECTILE = {'javelin':'spear','archer':'arrow','sniper':'bolt','repeater':'bolt','poisoner':'needle',
 'artillery':'cannon','mortar':'mortar','caravan':'seal','chain':'chain','burner':'fire','drummer':'sound',
 'engineer':'gear','medic':'leaf','necromancer':'soul','oracle':'orb','scribe':'ink','summoner':'paper','illusionist':'fan'}

# Face/helmet pixels belong to the torso even when an occluded painted handle
# crosses them. Keep facial expressions intact through every tool transform.
HEAD={
 'vanguard':(279,302,64,150),'javelin':(218,334,61,135),'crusher':(327,327,78,89),
 'raider':(284,345,65,148),'poisoner':(237,293,57,127),'necromancer':(284,346,61,166),
 'colossus':(286,252,73,109),'mirror':(252,262,68,136),'repeater':(235,281,61,112),
 'assassin':(328,347,55,166),'guard':(252,238,62,129),'engineer':(237,276,100,47),
 'archer':(289,286,52,144),'harrier':(313,287,74,135),'executioner':(236,310,59,131),
 'medic':(237,277,59,120),'shield':(283,282,55,103),'warden':(256,282,58,91),
 'berserker':(270,324,63,107),'leech':(271,260,70,118),'oracle':(259,277,57,121),
 'banner':(284,337,62,244),'burner':(252,325,51,192),'caravan':(264,315,61,152),
 'chain':(298,309,62,151),'cleaver':(240,266,66,125),'demolisher':(235,311,61,132),
 'drummer':(270,292,57,135),'duelist':(248,310,57,109),'illusionist':(246,288,57,100),
 'lancer':(215,263,40,143),'pike':(206,300,54,158),'saboteur':(305,348,56,160),
 'scribe':(259,263,60,90),'sniper':(254,320,48,208),'summoner':(263,289,70,165)}
CORE_HEAD={'unit.mu.guard':(291,299,68,150),'unit.bai.mirror':(269,262,64,175),
 'unit.qi.vanguard':(250,286,72,137),'unit.yuan.vanguard':(317,295,85,160),
 'unit.ji.javelin':(249,316,67,176),'unit.qi.javelin':(240,308,61,146),
 'unit.shuang.javelin':(235,323,62,182),'unit.jin.archer':(266,286,83,70)}
BEHIND_SHIELD={'unit.bai.mirror','unit.qi.vanguard'}
COMPONENT_CACHE={}
WHEELS={'artillery':[(211,383,92),(332,417,58)],'siege':[(154,393,76),(350,403,73)]}
CORE_WHEELS={'unit.ji.artillery':[(211,380,79),(345,402,72)],'unit.yuan.artillery':[(205,383,87),(334,401,73)],'unit.jin.artillery':[(210,390,83),(348,402,71)]}

def clean_fragments(image):
    alpha=image.getchannel('A');key=hashlib.sha256(alpha.tobytes()).hexdigest()
    if key not in COMPONENT_CACHE:
        size=256;data=bytearray(alpha.resize((size,size),Image.Resampling.NEAREST).point(lambda x:255 if x>24 else 0).tobytes())
        remove=bytearray(size*size)
        for first,value in enumerate(data):
            if not value:continue
            data[first]=0;stack=[first];seen=[];area=0
            while stack:
                at=stack.pop();area+=1
                if area<=96:seen.append(at)
                y,x=divmod(at,size)
                for dy in (-1,0,1):
                    yy=y+dy
                    if not 0<=yy<size:continue
                    for dx in (-1,0,1):
                        xx=x+dx
                        if not 0<=xx<size:continue
                        nxt=yy*size+xx
                        if data[nxt]:data[nxt]=0;stack.append(nxt)
            if area<96:
                for at in seen:remove[at]=255
        COMPONENT_CACHE[key]=Image.frombytes('L',(size,size),bytes(remove)).resize((512,512),Image.Resampling.NEAREST).filter(ImageFilter.MaxFilter(3))
    image.putalpha(ImageChops.subtract(alpha,COMPONENT_CACHE[key]));return image

def mask(points):
    m=Image.new('L',(512,512));ImageDraw.Draw(m).polygon(points,fill=255);return m

def arm_masks(config,width=27):
    shoulder,elbow,grip,polygon,tip=config
    tool=mask(polygon).filter(ImageFilter.MaxFilter(13))
    upper=Image.new('L',(512,512));d=ImageDraw.Draw(upper);d.line([shoulder,elbow],fill=255,width=width)
    fore=Image.new('L',(512,512));d=ImageDraw.Draw(fore);d.line([elbow,grip],fill=255,width=width)
    for m,pts in [(upper,[shoulder,elbow]),(fore,[elbow,grip])]:
        d=ImageDraw.Draw(m)
        for x,y in pts:d.ellipse((x-width/2,y-width/2,x+width/2,y+width/2),fill=255)
    # The front forearm occludes the upper-arm overlap, and the tool occludes both.
    upper=ImageChops.subtract(upper,ImageChops.lighter(tool,fore));fore=ImageChops.subtract(fore,tool)
    return upper,fore,tool

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    a=read(GAME/'data/assets.json');b=read(GAME/'data/balance-prototype.json');f=read(GAME/'data/factions.json')['factions']
    baseline=read(ROOT/'assets/paper-warfront/animation/rig-baseline-rc3.json')
    core={uid for x in f for uid in x['core_roster']};donors={}
    for x in f:
        for uid in x['core_roster']:donors.setdefault(b['units'][uid]['role'],uid)
    master_roles={p.stem for p in (ROOT/'output/imagegen/paper-warfront/theatre-v3/role-families/masters').glob('*.png')}
    alias={'unit.mo.thrall':'unit.mo.raider','unit.deng.guardian':'unit.deng.guard'}
    rows=[];profiles={}
    for uid,definition in b['units'].items():
        fa=next(x for x in f if x['id']==uid.split('.')[1])
        src=alias.get(uid,uid);role=b['units'][src].get('role','worker') or 'worker'
        meta=a['assets'][uid];old=baseline[uid];image=Image.open(GAME/meta['path'].removeprefix('res://')).convert('RGBA')
        profile={'front_behind_body':src in BEHIND_SHIELD,'id':uid,'role':role,'gesture':GESTURE.get(role,'wrench' if role=='engineer' else 'worker'),
                 'projectile':PROJECTILE.get(role,''),'windup':definition['windup'],
                 'recovery':round(min(.48,max(.16,float(definition.get('attack_interval',1))*.27)),3),
                 'attack_interval':definition['attack_interval'],'source_art':meta['path'],
                 'variant':('summoned_alias' if uid in alias else 'bespoke_core' if uid in core else 'role_palette'),
                 'states':['idle','walk','windup','attack','hurt','bound','death','special']}
        if role=='worker':
            profile.update(gesture='worker',states=['idle','walk','mine','load','unload','queue','hurt','bound','death'],rig='rc2-pickaxe',motion='rc4-service-time')
            profiles[uid]=profile;meta['action_profile']=uid;continue
        config=CORE.get(src,R[role]);width=76 if role=='crusher' else 72 if role=='colossus' else 38
        front=arm_masks(config,width)
        second=BACK.get(role);back=arm_masks(second,width) if second else None
        if role in HEAD:
            cx,cy,rad,top=CORE_HEAD.get(src,HEAD[role])
            protect=Image.new('L',(512,512));ImageDraw.Draw(protect).rectangle((cx-rad,top,cx+rad,cy),fill=255)
            front=tuple(ImageChops.subtract(m,protect) for m in front)
            if back:back=tuple(ImageChops.subtract(m,protect) for m in back)
        erased=Image.new('L',(512,512))
        for m in ([front[2]] if src in BEHIND_SHIELD else list(front))+(list(back) if back else []):erased=ImageChops.lighter(erased,m)
        if src=='unit.bai.repeater':
            # Printed in-flight bolts in this source are replaced by the actual
            # individually delayed missiles, not left hanging beside the gun.
            fake=Image.new('L',(512,512));ImageDraw.Draw(fake).rectangle((353,395,492,445),fill=255)
            erased=ImageChops.lighter(erased,fake)
        bow=None
        if role=='archer':
            bow={'top':[344,125],'bottom':[374,447],'old_nock':[255,286],'nock_y':286}
            if src=='unit.jin.archer':bow={'top':[291,89],'bottom':[351,418],'old_nock':[209,264],'nock_y':257}
            strings=Image.new('L',(512,512));d=ImageDraw.Draw(strings)
            d.line([tuple(bow['top']),tuple(bow['old_nock']),tuple(bow['bottom'])],fill=255,width=5)
            # Narrow median repair of the painted string inside opaque paper;
            # transparent spans are removed. The live string is drawn by Godot.
            opaque=image.getchannel('A').filter(ImageFilter.MinFilter(9)).point(lambda x:255 if x>180 else 0)
            repair=ImageChops.multiply(strings,opaque)
            rgb=image.convert('RGB');rgb=Image.composite(rgb.filter(ImageFilter.MedianFilter(11)),rgb,repair)
            rgb=rgb.convert('RGBA');rgb.putalpha(ImageChops.subtract(image.getchannel('A'),ImageChops.subtract(strings,opaque)));image=rgb
            arrow=Image.new('L',(512,512));d=ImageDraw.Draw(arrow)
            d.line([tuple(bow['old_nock']),(476,bow['nock_y'])],fill=255,width=12)
            d.polygon([(415,bow['nock_y']-23),(485,bow['nock_y']),(415,bow['nock_y']+23)],fill=255)
            arrow=ImageChops.subtract(arrow,protect);erased=ImageChops.lighter(erased,arrow)
        wheel_masks={};wheel_points=CORE_WHEELS.get(src,WHEELS.get(role,[]))
        if old.get('cart'):
            union=Image.new('L',(512,512))
            for label,(x,y,radius) in zip(['wheel-back','wheel-front'],wheel_points):
                m=Image.new('L',(512,512));ImageDraw.Draw(m).ellipse((x-radius,y-radius,x+radius,y+radius),fill=255)
                wheel_masks[label]=m;union=ImageChops.lighter(union,m)
            wheel_masks['body']=ImageChops.invert(union)
        # Preserve rc2 wheel/leg anchors. No old weapon pixels may survive in legs.
        parts={};records=[]
        def save(label,im):
            path=OUT/(uid.replace('.','-')+'-'+label+'.png')
            buffer=io.BytesIO();im.save(buffer,format='PNG',compress_level=6)
            blob=buffer.getvalue()
            if not path.exists() or path.read_bytes()!=blob:path.write_bytes(blob)
            parts[label]='res://'+path.relative_to(GAME).as_posix()
            records.append({'part':label,'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'alpha_pixels':sum(im.getchannel('A').histogram()[17:])})
        for label,path in old['parts'].items():
            original=Image.open(GAME/path.removeprefix('res://')).convert('RGBA');im=image.copy()
            if old.get('cart'):
                original=image.copy();original.putalpha(ImageChops.multiply(image.getchannel('A'),wheel_masks.get(label,Image.new('L',(512,512)))))
            im.putalpha(ImageChops.darker(original.getchannel('A'),image.getchannel('A')))
            im.putalpha(ImageChops.subtract(im.getchannel('A'),erased))
            if label=='body' and role not in ['artillery','mortar','siege','phoenix']:
                # Restore the torso hidden behind a painted shaft/arm. Keep the
                # original silhouette and limit underpaint to erased interior.
                torso=Image.new('L',(512,512));d=ImageDraw.Draw(torso)
                cx=(old['foot'][0]+config[0][0])*.5;sy=config[0][1]
                d.ellipse((cx-42,sy-16,cx+42,old['hip']+12),fill=255)
                patch=Image.new('RGBA',(512,512),'#'+fa['color'].lstrip('#'));pd=ImageDraw.Draw(patch)
                pd.line((cx,sy+10,cx-3,old['hip']+3),fill=(242,218,176,135),width=4)
                patch.putalpha(ImageChops.multiply(ImageChops.multiply(torso,erased),original.getchannel('A')))
                im=Image.alpha_composite(patch,im)
            if src=='unit.yuan.vanguard' and label in ['leg-back','leg-front']:
                # The original broad blade covered the legs. Rebuild the hidden
                # paper armour beneath it so moving the blade exposes legs.
                hidden=Image.new('RGBA',(512,512));hd=ImageDraw.Draw(hidden)
                points=[(220,358),(248,378),(218,423),(203,464),(162,467),(155,446),(180,407),(188,374)] if label=='leg-back' else [(311,355),(351,367),(350,413),(376,460),(341,468),(315,424),(299,384)]
                hd.polygon(points,fill=(84,112,151,255));hd.line(points+[points[0]],fill=(43,36,47,255),width=5)
                fold=[(211,375),(201,407),(179,448)] if label=='leg-back' else [(329,375),(332,407),(355,448)]
                hd.line(fold,fill=(174,191,205,255),width=4)
                im=Image.alpha_composite(hidden,im)
            if label in ['body','leg-back','leg-front']:im=clean_fragments(im)
            save(label,im)
        for prefix,conf,ms in [('front',config,front)]+([('back',second,back)] if back else []):
            for label,m in zip(['upper','fore','tool'],ms):
                im=image.copy();im.putalpha(ImageChops.multiply(image.getchannel('A'),m))
                if label!='tool':
                    if src in BEHIND_SHIELD:im.putalpha(Image.new('L',(512,512)))
                    im=clean_fragments(im)
                if label=='tool' and role=='lancer':
                    # Source pole is occluded by the original head/hand. A
                    # paper/wood underlayer joins that gap after articulation.
                    pole=Image.new('RGBA',(512,512));pd=ImageDraw.Draw(pole)
                    pd.line([(43,398),(407,112)],fill=(49,31,36,255),width=10)
                    pd.line([(43,398),(407,112)],fill=(138,103,71,255),width=5)
                    im=Image.alpha_composite(pole,im)
                # Painted tool layers can include the source hand. Fill hidden
                # joint segments beneath them so a bent elbow cannot open a gap.
                # This is native paper geometry, not a generated bitmap claim.
                if label in ['upper','fore'] and role not in ['artillery','mortar','siege','phoenix']:
                    under=Image.new('RGBA',(512,512));d=ImageDraw.Draw(under)
                    aa,bb=(conf[0],conf[1]) if label=='upper' else (conf[1],conf[2])
                    cloth=(195,179,142) if role=='colossus' else tuple(int(fa['color'].lstrip('#')[i:i+2],16) for i in (0,2,4))
                    d.line([aa,bb],fill=(58,39,42,255),width=23)
                    d.line([aa,bb],fill=cloth+(255,),width=17)
                    for point in [aa,bb]:
                        x,y=point;d.ellipse((x-10,y-10,x+10,y+10),fill=(58,39,42,255))
                        d.ellipse((x-7,y-7,x+7,y+7),fill=cloth+(255,))
                    d.line([aa,bb],fill=(236,213,168,110),width=3)
                    im=Image.alpha_composite(under,im)
                # The bow's nocked arrow becomes a runtime draw, not a painted
                # arrow remaining in the hand while the fired arrow flies.
                if role=='archer' and label=='tool':
                    im.putalpha(ImageChops.subtract(im.getchannel('A'),arrow))
                save(prefix+'-'+label,im)
        updated=dict(old,parts=parts,action_version=4)
        if old.get('cart'):
            updated['fixed_mount']=not bool(wheel_points)
            for label,(x,y,radius) in zip(['wheel-back','wheel-front'],wheel_points):updated[label+'_pivot']=[x,y]
        updated['joints']={'front':dict(zip(['shoulder','elbow','grip','mask','tip'],config))}
        if bow:updated['bow']=bow
        if second:updated['joints']['back']=dict(zip(['shoulder','elbow','grip','mask','tip'],second))
        profile['rig']='articulated-tools-v4';profile['parts']=len(parts)
        updated['gesture']=profile['gesture'];meta['animation']=updated;meta['action_profile']=uid
        rows.append({'id':uid,'role':role,'source':meta['path'],'source_sha256':sha(GAME/meta['path'].removeprefix('res://')),
                     'method':'authored source-alpha joint masks; native paper joint/torso underpaint; bow painted-string median repair; separate shoulder/elbow/grip transforms',
                     'mask_donor':src if src in core else ('role.'+role if role in master_roles else donors[role]),
                     'joints':updated['joints'],'parts':records})
        profiles[uid]=profile
    write(GAME/'data/unit-actions.json',{'version':'3.0.0-rc4','profiles':profiles,'roles':GESTURE,'projectiles':PROJECTILE})
    write(GAME/'data/action-rig-provenance.json',{'version':'3.0.0-rc4','source_model':'gpt-image-2.5 via user sub2-image-gen',
       'processor':'tools/paper-warfront/publish_action_rigs.py','processor_sha256':sha(Path(__file__)),
       'notes':'Runtime derivative masks, not newly generated illustrations. Worker rigs retained from rc2. Source cutouts/portraits unchanged.', 'records':rows})
    a['version']='3.0.0-rc4';write(GAME/'data/assets.json',a)
    write(ROOT/'assets/paper-warfront/animation/unit-actions.json',{'version':'3.0.0-rc4','profiles':profiles})
    print(json.dumps({'profiles':len(profiles),'roles':len(GESTURE)+1,'articulated':len(rows),'parts':sum(len(r['parts']) for r in rows)}))

if __name__=='__main__':main()

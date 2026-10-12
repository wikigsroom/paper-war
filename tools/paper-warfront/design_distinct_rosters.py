"""Authored six-unit faction kits and whole-frame art briefs. No palette clones."""
from pathlib import Path
import json
from prepare_frame_pilots import BASE
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/imagegen/paper-warfront/frame-rebuild'
CAT=ROOT/'assets/paper-warfront/frame-rebuild'

# Stable IDs are retained, but names, equipment and actual combat kits are authored
# per faction. Stats still come from the earlier balance baseline until publication.
# Fields below have real handlers in BattleSim / UnitAbilities, not cosmetic tags.
KITS={
 'yin':[
 ('axe','镇印刀盾卫','Broad square red lamellar infantry, huge rectangular seal shield and short heavy cleaver; disciplined planted stance','slash',{'physical_damage_multiplier':.78},'举方盾列阵，物理减伤22%；怕绕过盾面的法术。'),
 ('spear','穿封投矛手','Imperial red tabard scout, long seal-tagged throwing spear and a quiver of folded spears, no shield','throw',{'armor_break_seconds':3.5,'armor_break_amount':.18},'投矛撕开封甲，3.5秒内目标受到的物理伤害提高18%。'),
 ('hammer','压印重锤卫','Huge squat seal-press executioner, both hands on an oversized square stamp hammer, heavy rectangular shoulders','hammer',{'range':1.25,'stun_seconds':.55,'radius':.85},'隔着前排落印重砸，范围打断；长前摇可被控制。'),
 ('cannon','落印攻城台','A low red rolling seal-printing press, broad square platen raised on two rails, NO generic cannon barrel','stamp_machine',{'building_multiplier':2.6,'root_seconds':.4,'projectile_style':'seal'},'飞印优先拆城，命中短暂定身；低移速需要护送。'),
 ('banner','督印旗官','Tall rectangular imperial banner, stern red-clad officer with a command baton and marching orders scroll','banner',{'aura_damage':.18,'aura_radius':3.0},'旗旁军队增伤18%，列阵集中有收益，也容易被范围攻击。'),
 ('guard','护仓签盾兵','Short broad worker escort in layered red envelope armor, oversized ribbed signing-board tower shield, small baton','shield',{'worker_guard_radius':2.8,'worker_guard_reduction':.35},'护仓而非追击，附近运金纸工受到伤害减少35%。')],
 'mo':[
 ('blade','撕页猎骨者','Lean ragged violet bone-paper stalker, skull mask, two uneven torn-paper sickles and long hunched spine','dual_slash',{'leap_max_distance':2.5,'leap_cooldown':5.0,'lifesteal':.12},'短距扑击并吸血，靠活体冲阵；与纸骨召唤群互相掩护。'),
 ('needle','腐墨骨针师','Tiny stooped old-paper witch with a long hollow bone blowpipe, fungus-filled ink pouch and ragged hood','blowpipe',{'poison_damage_per_second':4.0,'poison_stack_limit':3,'projectile_style':'needle'},'骨针腐墨叠三层，净化和短时爆发能够反制。'),
 ('priest','拾纸招魂祭司','Ragged violet skull-hood necromancer with crooked skull staff, torn scrolls and skeletal hands','ritual',{'summons':'unit.mo.thrall','corpse_range':3.5,'max_owned_thralls':3,'summon_interval':4.5},'消耗真实战斗残页招魂；没有遗骸时无法凭空出兵。'),
 ('giant','缝骨纸骸兽','Asymmetric lumbering beast made of stitched old bone-paper scraps, hunched rib cage and massive unequal fists','punch',{'death_burst_damage':32,'death_burst_radius':1.4,'radius':1.1},'慢速范围拳击，倒下散出骨片；怕被长距离拉扯。'),
 ('leech','缠魂割纸客','Thin spectral paper reaper in a long perforated violet veil, hooked bone scythe and hanging soul strips','reap',{'lifesteal':.38,'magic_damage':True},'高吸血法术近战，生命低且难以摸到后排。'),
 ('warden','墨缚钉魂者','Low spider-like paper shaman wrapped in black ink threads, a bundle of bone pins in both hands, no conventional armor','pin_cast',{'root_seconds':1.2,'silence_seconds':.9,'projectile_style':'needle'},'骨钉缚魂并封口，主要克制支援施法兵。')],
 'deng':[
 ('mirror','转灯映符卫','Turquoise lamp guardian with a round rotating bronze mirror, curling talismans and a folded ceremonial hat','mirror',{'reflection_cooldown':2.8},'圆镜反射纸质飞弹，直伤法术和近战不受影响。'),
 ('fire','连签燃灯者','Teal-robed lantern handler with a long vertical paper lantern and two flame talisman strips between fingers','talisman',{'burst_count':2,'burn_damage_per_second':2.5,'projectile_style':'fire'},'两连火签点燃，签纸补充期间脆弱。'),
 ('shadow','折影越阵客','Extremely low folded teal origami ninja, split triangular cape, two short paper daggers and talisman eye mask','stab',{'crossing_max_distance':3.6,'crossing_cooldown':6.0,'support_multiplier':1.5},'折入敌阵跨过前排，专打支援兵；定身可阻断越阵。'),
 ('effigy','灯腹护符俑','Tall hollow turquoise paper shrine effigy with a glowing lantern in its belly and wide flat talisman arms','shield',{'physical_damage_multiplier':.75,'ward_aura':.25,'aura_radius':2.8},'灯腹结界保护附近友军抵抗法术，怕物理攻城。'),
 ('summoner','折符纸匠','Small teal craftswoman carrying a tray of folded talisman dolls, sleeves folded into sharp triangles','paper_fold',{'auto_guardian_seconds':9,'ability_interval':5.5},'现场折出最多两名有时限的护符纸卫。'),
 ('illusionist','叠灯复影师','Tall ceremonial teal magician with three nested paper lamps and a folding fan of duplicate silhouettes','fan',{'auto_clone_seconds':7,'ability_interval':8.0},'复制附近真实小型盟友，复制体有时限，巨兵不能复制。')],
 'ji':[
 ('vanguard','发条铆甲拳兵','Compact brass-and-brown paper automaton, cylindrical spring torso, piston punch gauntlet, tiny squared head','punch',{'third_hit_stun':.45},'连续第三次命中铆钉震击；稳定贴身才能完成连段。'),
 ('javelin','折簧钉枪手','Workshop mechanic with large folded nail-gun, exposed spring magazine, asymmetric leather apron and goggles','crossbow',{'burst_count':2,'reload_every':3,'reload_seconds':1.25,'projectile_style':'bolt'},'三轮钉枪后必须装填；持续压制与装填窗口均真实存在。'),
 ('engineer','旋齿修械匠','Short workshop engineer with giant articulated wrench, gear backpack and mismatched brass goggles','wrench',{'repair_building':24,'repair_interval':3.4,'repair_radius':3.5},'修理实际受损设施，离开施工与前哨阵地便失去价值。'),
 ('artillery','折簧重弩车','A wide low wheeled spring ballista with a folding paper bow, visible winch and a single large gear, NO cannon','ballista',{'building_multiplier':2.2,'reload_every':1,'reload_seconds':.5,'projectile_style':'bolt','radius':.25},'绞盘展开后射重弩拆城，每发回卷装填。'),
 ('demolisher','解构折雷机','Walking round folded brass mine with little mechanical feet, an engineer seat and a demolition probe','bomb',{'construction_multiplier':3.2,'disable_facility_seconds':2.5},'对未完成建筑拆解增伤，并使非基地设施短暂停机。'),
 ('guard','齿盾维修偶','Bulky squat paper robot with a circular rotating gear shield and drill hand, broad barrel waist','shield',{'workshop_bonus':.35,'physical_damage_multiplier':.82},'驻在己方设施旁攻击提高35%，离开阵地缺乏机动。')],
 'yuan':[
 ('vanguard','纸翼突枪客','Slim blue feather-paper courier with huge folded kite wings and a forward long lance, no heavy shield','lance',{'charge_distance':3,'charge_multiplier':1.65},'实际移动积攒冲势，下一枪增伤；定身与拥堵会破坏节奏。'),
 ('archer','回风游弓手','Blue bird-hood archer, long curved feather bow, flowing split-tail cape and light sandal feet','bow',{'skirmish_retreat':.85,'retreat_seconds':.34,'projectile_style':'arrow'},'射箭后沿当前道路后撤，近身与封路可以抓住。'),
 ('harrier','牵线钩翼兵','Winged blue rope runner with a long hooked kite line, feather headpiece and an extremely stretched low stance','hook',{'on_hit_slow':1.4,'pull_distance':.55},'钩线牵近同路目标并缓行，改变真实站位。'),
 ('artillery','风筝投弹架','A light blue twin-wing kite launcher on three thin legs and tiny wheels, hanging folded diamond bomb packets','kite_launcher',{'burst_count':3,'radius':.45,'projectile_style':'kite'},'分次送出三枚风筝弹包，轻巧但没有传统炮车护甲。'),
 ('lancer','长尾纸骑','A blue courier riding a long-tail angular folded paper horse, long thin jousting pole and streaming wing ribbons','lance',{'junction_haste_seconds':4.0,'anti_fast_multiplier':1.5},'过路口加速截击快速单位，长距离增援更有优势。'),
 ('caravan','顺风递纸车','A delicate blue sail-assisted two-wheel messenger cart, open letter satchels and feather vanes, no weapon barrel','sail',{'aura_speed':.23,'aura_radius':3.2},'顺风旗给附近作战部队加速，脆弱的运输支援。')],
 'qi':[
 ('vanguard','守契雇佣卫','Stocky gold-contract mercenary, round coin shield, quilted bill armor, coin-plated short blade and mustache','slash',{'treasury_damage_per_100':.06,'treasury_bonus_cap':.24},'保留金库提高伤害，上限24%；存钱与增兵形成取舍。'),
 ('javelin','掷契金签客','Gold trader with wide-brim ledger hat, brass coin pouch and a fan of rectangular throwing contract tokens','throw',{'burst_count':2,'bounty_gold':5,'projectile_style':'coin'},'双投契签，击杀真实敌兵收取赏金；不奖励召唤物。'),
 ('executioner','断契追债镰','Tall gold debt collector, enormous crescent contract-cutting scythe, long black-gold cape and ledger belt','reap',{'range':1.25,'execute_threshold':.38,'execute_multiplier':1.75,'bounty_gold':7},'长镰隔前排收割残血赚赏金；满血重甲能扛第一轮。'),
 ('siege','金库撞票车','Huge armored rolling golden strongbox, a long horizontal stamping ram, bill scrolls coiled around its wheels','ram',{'building_multiplier':3.2,'physical_damage_multiplier':.8},'近身撞城而非远程炮击，票甲能扛物理却怕控制。'),
 ('caravan','护票押运司','A golden walking banker with tall sealed ledger backpack, long rolled payment scroll and umbrella-like coin shield','ledger',{'delivery_aura':2,'aura_radius':3.2},'护送附近纸工每次归仓多得2金，必须实际往返才能赚取。'),
 ('sniper','悬赏契弩客','Lanky gold bounty hunter behind an oversized heavy contract crossbow, a rolled wanted poster tied to the stock','crossbow',{'support_priority':True,'support_multiplier':1.7,'bounty_gold':6,'projectile_style':'bolt'},'慢速重弩优先支援单位，长装填使近战突击有效。')],
 'mu':[
 ('guard','根藤护仓卫','A small living wooden fiber stump with root feet, a huge layered leaf shield and vine tendril arm, not a human recolor','root_bash',{'worker_guard_radius':3.0,'worker_guard_reduction':.28,'regeneration':2.5},'根藤护仓并自愈，阻断自然修复的腐墨是克星。'),
 ('poisoner','孢籽吹叶灵','Tiny mushroom-headed forest paper sprite with leaf ears, seed-pod blowpipe and a round spore backpack','blowpipe',{'poison_damage_per_second':3.0,'root_after_hits':3,'root_seconds_on_combo':1.1,'projectile_style':'seed'},'三颗命中同一敌人的孢籽长出缠根，带持续腐蚀。'),
 ('medic','花冠补叶师','Flower-crowned gentle paper gardener, huge blossom staff, leaf-layered skirt and a medicine basket','heal',{'heal_amount':23,'heal_interval':3.0,'heal_radius':3.2,'cleanse_on_heal':True},'补叶同时清除腐墨与燃烧，需保护脆弱的花冠师。'),
 ('colossus','盘根古纸树','An enormous angular living tree made of layered green fiber paper, branch horns, root legs, both arms are thick knotty wood','root_bash',{'regeneration':4.0,'radius':1.35,'root_seconds':.4},'树根重砸短暂缠住敌群，缓慢推进，需要治疗配合。'),
 ('warden','织藤结网者','Long thin praying-mantis-like leaf spirit, four folded vine limbs and a woven seed web held between hands','vine_cast',{'root_seconds':1.5,'on_hit_slow':1.8,'projectile_style':'leaf'},'远程织藤固定敌人，定身不禁止对方攻击。'),
 ('phoenix','返叶萤蛾','A large luminous green leaf moth with broad veined paper wings, hanging pollen sac and curled antennae, no humanoid soldier','wing',{'heal_death_burst':65,'heal_death_radius':3.0,'projectile_style':'leaf'},'萤蛾阵亡散出补叶粉治疗附近盟友，治疗不会产生伤害。')],
 'shuang':[
 ('shield','规尺雪盾卫','Square ice-blue paper bailiff, huge caliper-shaped shield, geometric snow helmet and straight ruler blade','shield',{'physical_damage_multiplier':.70,'retaliation_damage':5,'retaliation_interval':.7},'扛物理并对近战反震，远程攻击不会触发反震。'),
 ('javelin','霜楔掷裁者','White-blue folded-paper judge, long triangular frost wedges instead of spears, severe tall angular hood','throw',{'freeze_after_hits':3,'freeze_seconds':.8,'on_hit_slow':.7,'projectile_style':'frost'},'三枚霜楔命中同一敌人冻结，成功控制才获得法力。'),
 ('warden','钉页定身司','Tall snow-white archivist with a giant stapling staff and a hanging book spine, long folded coat','staple',{'root_seconds':1.25},'近身钉页定身，适合把目标留给抛雪车。'),
 ('mortar','压雪折页车','Low blue-white mechanical stapler sled with a concave snow scoop and thick folded paper runners, not a generic cannon cart','mortar',{'controlled_multiplier':1.45,'radius':1.2,'projectile_style':'snow','reflectable':False},'高弧雪页对被控制目标增伤45%，慢出手可被突袭。'),
 ('scribe','冻墨封言吏','Tiny ice-blue calligrapher with oversized frost ruler and a dry frozen ink brush, square hanging book sleeves','brush',{'silence_seconds':1.5,'on_hit_slow':.8,'projectile_style':'ink'},'冻墨封言并缓行，主要克制主动支援能力。'),
 ('oracle','寒页裁决官','Tall faceless snow-paper tribunal spirit, floating open law book and long geometric ice-page staff','orb',{'chain_targets':2,'chain_radius':1.7,'on_hit_slow':1.2,'magic_damage':True},'寒页裁决跳向第二个敌人，密集阵型更易受控。')],
 'jin':[
 ('berserker','半燃双刃徒','Bare-armed charcoal-paper exile with scorched jagged hair, two uneven ember blades and torn glowing cloth, not armored infantry','dual_slash',{'enrage_threshold':.35,'enrage_multiplier':1.7},'残血双刃加伤，抢先爆发或控制能阻止反扑。'),
 ('archer','炭弓余火猎','Hooded orange ash-paper hunter, charred asymmetrical branch bow and ember-tipped arrows, long torn scarf','bow',{'burn_damage_per_second':3.0,'projectile_style':'fire_arrow'},'炭弓命中持续燃烧，净化与压近可以反制。'),
 ('leech','取火钩魂客','Charcoal-masked slim exile, a long hooked fire-curved blade and a small furnace carried at the waist','hook',{'lifesteal_on_burning':.40,'burn_damage_per_second':2.0},'只从已燃烧目标吸血，需要余火猎和喷签师铺火。'),
 ('artillery','陶灰投火炉','A squat orange clay-paper kiln on broad scorched wheels, a rear chimney and hinged bowl catapult, no cannon barrel','mortar',{'burn_damage_per_second':4.0,'radius':1.0,'projectile_style':'fire_pot'},'投出余火壶点燃敌群，炉车前摇长且容易被绕后。'),
 ('burner','灰风喷签师','Hunched charcoal-paper bellows operator with a giant folded leather bellows, soot mask and burning talisman hopper','bellows',{'burst_count':3,'chain_targets':2,'chain_radius':.8,'burn_damage_per_second':2.0,'projectile_style':'fire'},'近程三段灰风扫群，火线短，需要前排保住喷签口。'),
 ('demolisher','裂火抱壶者','A frantic small ash-paper exile hugging a huge cracked glowing fire pot, stubby bare feet and scorched headband','bomb',{'death_burst_damage':62,'death_burst_radius':1.5,'building_multiplier':1.5},'抱壶突入，阵亡引爆敌方；不会误伤己方纸工。')],
 'bai':[
 ('mirror','空框映界卫','An eerie ivory faceless guard with an empty rectangular frame shield, a hole cut through the torso and thin violet seams','frame_guard',{'spell_absorb_interval':5.0,'magic_damage_multiplier':.65,'physical_damage_multiplier':1.1},'每5秒抹去一次敌方法术伤害，物理攻击穿透空框。'),
 ('repeater','镂字连签弩','White masked scribe with a punched-letter mechanical crossbow, floating cutout letters and a long perforated coat','crossbow',{'burst_count':3,'dispel_on_attack':True,'projectile_style':'glyph'},'首发删去敌人护符与强化再三连击，自己非常怕近战。'),
 ('oracle','删行执笔人','Very tall faceless ivory paper editor, huge thin eraser-quill staff and a rectangular blank page instead of face','brush',{'magic_damage':True,'silence_seconds':.8,'kill_mana':5,'projectile_style':'ink'},'删行法术封口，击杀真实敌兵返法，无法从召唤物刷取。'),
 ('colossus','页界折兽','Enormous horizontal ivory origami fox-dragon, four angular folded legs, long blank paper muzzle and layered fan tail; NOT humanoid golem','beast',{'magic_damage':True,'magic_damage_multiplier':.45,'physical_damage_multiplier':1.18,'radius':1.0,'projectile_style':'page_breath'},'折兽展开页界喷息，抗法术却怕物理围攻。'),
 ('illusionist','留白消矢师','Floating ivory folded-book spirit inside a white circular paper aperture, small faceless head and a fan eraser','erase',{'erase_projectiles_radius':2.0,'erase_interval':3.8},'周期抹除附近敌方飞弹，不消除直伤法术，沉默可封住。'),
 ('scribe','覆写禁印官','Ivory archivist carrying an oversized delete-stamp cylinder and a black-violet narrow ledger, rigid vertical long coat','stamp_cast',{'silence_seconds':2.0,'support_multiplier':1.5,'support_priority':True,'projectile_style':'seal'},'覆写印优先封锁支援兵，逼对方用前排掩护。')]
}

ATTACK={
 'slash':'Brace or step forward, lift cleaver/blade, twist torso into a clear downward-forward slash on frame 4, follow through and recover. Keep blade held in the hand.',
 'dual_slash':'Both elbows bend, alternate the two blades with a full torso turn and low knee bend; frame 4 is a strong crossing slash, blades remain correctly in the hands.',
 'throw':'Draw the throwing object back beside the head, rotate shoulders, extend the throwing arm decisively on frame 4. The held throwing object MUST disappear in frame 4 and 5, because the real engine spawns a separate projectile. Frame 6 reaches for the next object. No painted flying projectile.',
 'hammer':'Both hands grip the oversized hammer. Bend knees under its weight, raise it fully overhead in frame 3, slam forward/down in frame 4, crouch in the follow-through, recover. Whole torso and elbows change shape.',
 'bow':'Use BOTH hands: front hand holds bow upright, back hand pulls visible bowstring and arrow to cheek in frames 2 and 3. Frame 4 releases: EMPTY bow and string snaps forward, back hand recoils. No arrow remains nocked in frames 4 and 5. Frame 6 reaches for a new arrow. No painted flying arrow.',
 'crossbow':'Raise and aim the distinctive crossbow or nail gun using BOTH hands, brace on frame 3, trigger release on frame 4 with a small muzzle recoil and EMPTY bolt rail, step back on frame 5, then open or reload the mechanism. Do not paint flying bolts.',
 'blowpipe':'Hold the pipe with both hands, bring it to lips, inhale, blow on frame 4 while cheeks and torso visibly tense, recoil, breathe and recover. The actual engine draws the dart separately.',
 'punch':'Bend knees, coil a huge arm back, rotate the ribcage, punch forward on frame 4, opposite arm guards, then recoil and step back. Re-draw the elbows and hands instead of rotating a rigid arm.',
 'shield':'Set feet apart, bring distinctive shield or talisman arms forward to cover body, brace, bash forward on frame 4 with a bent knee and torso lean, recoil and reset.',
 'reap':'Grip the long hooked scythe with both hands, lift over shoulder, rotate waist, sweep a low crescent on frame 4, strong follow-through, recover.',
 'lance':'Brace a long forward lance, coil rear leg, extend in a decisive forward thrust on frame 4, lean into the strike with rear leg stretched, pull lance back. Horse riders stay mounted and horse bends knees.',
 'hook':'Swing the hook or taut kite line back, step with a low knee bend, cast the hooked line forward on frame 4, visibly pull backwards on frame 5 and recover. No painted flying object.',
 'mortar':'Brace the distinctive sled or kiln, scoop or arm the hinged launching bowl, raise to high angle in frame 3, EMPTY launcher releases on frame 4, whole chassis recoils on frame 5, reload frame 6. The engine draws the separate shell.',
 'ballista':'Set wheels, mechanically crank winch and pull the huge bowstring in frames 2 and 3, release with EMPTY rail on frame 4, spring limbs recoil in frame 5, reset winch. No painted flying bolt.',
 'ram':'Bring the rolling strongbox backwards, preload the ram, lunge forward with the piston fully extended on frame 4, compress axle springs and wheels, withdraw ram frame 6.',
 'wing':'Flap BOTH wings with flexible folded membranes, rise slightly, curl body, strike or release pollen on frame 4, sweep wings down in frame 5, recover. Same scale and cell ground anchor.',
 'root_bash':'Twist flexible vine and wooden limbs, root feet spread, coil upper body, slam thick branch arms forward/down on frame 4, leaves and joints bend with momentum, recover.',
 'beast':'The four-legged paper beast opens its muzzle and spreads layered neck pages in anticipation, lunges head and breathes forward on frame 4, neck and back curve, then folds pages and recovers. Never turn a standing humanoid around a pivot.',
}

def action_text(gesture):
    return ATTACK.get(gesture,'Bend knees and twist the torso, raise the distinctive implement in the correct hand grip, gather intent in frame 3, extend or sweep it decisively forward on frame 4 to release a real engine spell, recoil in frame 5, recover frame 6. Keep identity and equipment coherent; no painted flying effect.')

def main():
    OUT.mkdir(parents=True,exist_ok=True);CAT.mkdir(parents=True,exist_ok=True)
    assets=json.loads((ROOT/'game/data/assets.json').read_text(encoding='utf-8'))['assets']
    factions=json.loads((ROOT/'game/data/factions.json').read_text(encoding='utf-8'))['factions']
    factionmap={f['id']:f for f in factions};records=[]
    for faction,rows in KITS.items():
        for tail,name,design,gesture,mechanics,hint in rows:
            uid=f'unit.{faction}.{tail}';stem=uid.replace('.','-')
            source='game/'+assets[uid]['path'].removeprefix('res://')
            special='Use a secondary action that visibly communicates this actual kit: '+hint+'. Show deliberate equipment handling or faction ritual, then return to ready. No scenery or extra standing characters.'
            brief=BASE.replace('DESIGN_DESCRIPTION',design+'. Character must clearly belong to '+factionmap[faction]['name']+' ('+factionmap[faction]['motif']+'). A distinct body silhouette, not another army soldier recolored.').replace('ATTACK_DESCRIPTION',action_text(gesture)).replace('SPECIAL_DESCRIPTION',special)
            pilot=OUT/(stem+'.prompt.txt')
            # The two inspected pilot sheets preserve their exact generation prompt.
            if not (OUT/(stem+'-raw.png')).exists():pilot.write_text(brief,encoding='utf-8')
            records.append({'id':uid,'faction':faction,'name':name,'gesture':gesture,'design':design,'attack_description':action_text(gesture),'hint':hint,'mechanics':mechanics,'source':source,'prompt':pilot.relative_to(ROOT).as_posix(),'raw':(OUT/(stem+'-raw.png')).relative_to(ROOT).as_posix(),'layout':[6,6],'states':['idle','walk','attack','hurt','death','special'],'status':'candidate-unreviewed','model':'gpt-image-2.5'})
        f=factionmap[faction];uid=f'unit.{faction}.worker';stem=uid.replace('.','-')
        worker_design={
          'yin':'Disciplined red seal-office porter, boxy lacquer backpack, square stamp helmet, short iron pick.',
          'mo':'Hunched ragged old-paper bone scavenger, skull hood, crooked bone pick and tied torn-paper basket.',
          'deng':'Small turquoise lantern porter, folded ceremonial hat, dangling lamp and talisman-labeled gold basket.',
          'ji':'Brass workshop mining automaton with telescopic legs, a geared pick and cylindrical ore backpack.',
          'yuan':'Light blue kite-wing messenger miner, feather hood and long letter satchel, a delicate hooked pick.',
          'qi':'Gold-contract merchant porter with fat ledger sack, round coin-trimmed cap and a wide coin shovel.',
          'mu':'Tiny living leaf-and-mushroom gardener, root feet, seed basket and wooden leaf-shaped digging tool.',
          'shuang':'White-blue archival worker, ruler-shaped pick, rigid rectangular ore box and snow-paper hood.',
          'jin':'Ash-paper miner in charcoal mask with a soot-black pick, patched pot backpack and torn orange wrap.',
          'bai':'Small faceless ivory folded-paper clerk with a rectangular empty-frame basket and a narrow erase-pick.'}[faction]
        prompt=BASE.replace('DESIGN_DESCRIPTION',worker_design+' Same paper art style; this is an economy worker, no combat shield or gun.').replace('ATTACK_DESCRIPTION','This row is MINING, not combat: plant feet, lift pick or digging tool with BOTH elbows bent, reach high in frame 3, strike down toward the right ground at frame 4, lift from ground in frame 5, return frame 6. Show tool changing grip and torso bending. No walking while mining.').replace('SPECIAL_DESCRIPTION','Unload a gold bag: crouch, grip the backpack or ore box, lower it in front of body, pour distinct little folded gold pieces down, close bag, lift it back to ready. No scenery.').replace('ROW 4, six frames: receive a hit','ROW 4, six frames: receive a hit')
        (OUT/(stem+'.prompt.txt')).write_text(prompt,encoding='utf-8')
        records.append({'id':uid,'faction':faction,'name':f['prefix']+'运金纸工','gesture':'mine','design':worker_design,'attack_description':'Real planted-foot pickaxe cycle, frame 4 strikes.','hint':'矿口采金，实际归仓入账；非战斗单位。','mechanics':{'economy':True},'source':'game/'+assets[uid]['path'].removeprefix('res://'),'prompt':(OUT/(stem+'.prompt.txt')).relative_to(ROOT).as_posix(),'raw':(OUT/(stem+'-raw.png')).relative_to(ROOT).as_posix(),'layout':[6,6],'states':['idle','walk','mine','hurt','death','unload'],'status':'candidate-unreviewed','model':'gpt-image-2.5'})
    for uid,donor,design in [('unit.mo.thrall','unit.mo.blade','A very small ragged old-paper skeleton with bone limbs and a broken blade, empty skull face and no cloth armor.'),('unit.deng.guardian','unit.deng.effigy','A small turquoise folded talisman doll with a squared lamp belly, short arms, tiny paper spear and faceless blank mask.')]:
        stem=uid.replace('.','-');prompt=BASE.replace('DESIGN_DESCRIPTION',design).replace('ATTACK_DESCRIPTION',action_text('slash')).replace('SPECIAL_DESCRIPTION','Fold arms over the small body, crouch and brace against incoming attacks, then stand again.')
        (OUT/(stem+'.prompt.txt')).write_text(prompt,encoding='utf-8')
        records.append({'id':uid,'faction':uid.split('.')[1],'name':'纸骨兵' if 'thrall' in uid else '护符纸卫','gesture':'slash','design':design,'attack_description':action_text('slash'),'hint':'有来源与寿命限制的召唤物，不能招募或复制。','mechanics':{'summoned':True},'source':'game/'+assets[uid]['path'].removeprefix('res://'),'prompt':(OUT/(stem+'.prompt.txt')).relative_to(ROOT).as_posix(),'raw':(OUT/(stem+'-raw.png')).relative_to(ROOT).as_posix(),'layout':[6,6],'states':['idle','walk','attack','hurt','death','special'],'status':'candidate-unreviewed','model':'gpt-image-2.5'})
    doc={'version':'frame-rebuild-1','policy':'six distinct combat units per faction; 10 distinct economy workers and two summons; legacy palette rosters retired with stable-ID migration','units':records}
    (CAT/'unit-briefs.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Authored 60 combat kits, ten workers and two summons; no runtime bindings changed.')

if __name__=='__main__':main()

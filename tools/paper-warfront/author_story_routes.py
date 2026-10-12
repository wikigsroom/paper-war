"""Authored opening chapter: geography, story stakes, evidence and optional routes."""
from pathlib import Path
import hashlib, json, shutil
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/capacity-performance-rc27'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf-8')

# No template-generated dialogue. Each row follows this map's actual objective.
BEATS=[
 ('归金坡的封条','赤砚','旧军令把矿村列为叛军。第一车金刚到城门，追捕队就沿归金坡压来；工人身上只有工钱，没有兵器。',
  '矿村纸工','山口一封，我们的薪册和村人的名字就都成了禁物。先打开通往城门的路，账册才有地方存。',
  '解除封路军营，保住矿村与纸城的联络。','坡道把近矿和家门连在一起，敌军推进会直接威胁回款。',
  '封路营退了。矿村交出两条线索：外矿的账页，以及前哨匠保存的旧印拓片。赤砚决定先取其中一条，再去岔口。','矿村出入册'),
 ('外矿的空名册','赤砚','被宣布废弃的外矿仍在供军，薪册上的名字却全被刮空。我们把这一批金送回城，也把账页带回去。',
  '矿村纸工','近洞排队太久；外矿运程更长，也离敌哨更近。多一个工人得有护卫跟上。',
  '用实际归仓的金车证明外矿仍在生产。','近矿容量与外矿往返形成经济取舍；采到金还不算送达。',
  '金车在城门过秤，账页上的产量与军营收据吻合。所谓废矿一直在给封路军供钱；岔口的命令来历值得查。','外矿过秤账'),
 ('前哨匠的拓片','赤砚','前哨匠认出封条上的王印缺了一角。敌军要拆掉他留样的塔，我们得守到他把两枚印拓完。',
  '前哨匠','原印在塔里，别把守城当成守塔。援兵走完这段坡以前，请替我挡住第一轮。',
  '保护指定前哨直到鉴印完成。','目标位于前沿坡道；守在纸城会留下增援空档。',
  '两份拓片叠在一起，缺角的位置对不上。前哨匠交出旧印样本，赤砚有了检查岔口封令的依据。','前哨双印拓片'),
 ('封令的岔口','赤砚','无论账页还是拓片，都指向岔口的封令营。敌阵压在主路上，旧纸桥还通向它后方的汇口。',
  '引路纸工','桥是早年绕开征税哨修的，绕得远。主路快，桥路慢；进了路段的兵不会听口令瞬间换道。',
  '突破封令营，取回命令签发记录。','实际桥路绕开主路阵地并在同一节点汇流；高低路保持各自视野。',
  '岔口营里没有王印，只有批量盖好的空白封令。账车线和一名逃出的录令员，都可能解释这些命令从何而来。','岔口签发记录'),
 ('账车留下的水印','赤砚','录令营的金币从旧金车线汇入。继续护住运输，让账车按时进城，才能对照收据上的水印。',
  '过秤吏','数量要看真正运到城里的金，不能只看矿袋。军费与村人的工钱印着同一个水印。',
  '完成归仓目标，追查军费和工钱的共同来源。','金车必须沿长运输线真实回城，护矿投入会与招募争预算。',
  '回城金袋里找到同厂纸签。被抹名的矿村和封令营使用同一套账纸，前哨外矿的仓库有这批纸的旧库存。','金车水印'),
 ('录令员走过接力岗','赤砚','录令员带着一张没盖完的空令逃了出来。让他活着越过交接岗；他的原稿不能由后来人补写。',
  '录令员','追兵会从路旁入口赶来。先清岗口，或者留下接力防护，但请别让我独自走进下一段路。',
  '护送唯一携证者到真实交接位置。','路段和伏兵入口拉开护卫到达窗口，护送者需先铺好接力。',
  '录令员在交接岗交出空令原稿，背面的纸厂标记指向前哨外矿。他没有为任何一院认罪，只要求保留自己的证词。','空令原稿'),
 ('哨线之间的纸仓','赤砚','前哨外矿的旧仓存着空令用纸。敌军守住两哨之间的矿埠，我们必须夺开通路，才能查封仓里的原料。',
  '仓库匠','外矿有尽头。抢到的金得及时换成护卫，等它枯竭才补兵，就来不及守这座仓。',
  '夺回旧仓，核实命令用纸的来源。','有限外矿位于哨线之间，收入兑现与前线抵达形成争夺窗口。',
  '仓封写着停供，出库页却从未中断。长援岭的守军调令与桥矿的发运簿提供了两条追查路线。','旧仓出库页'),
 ('长援岭等来的回信','赤砚','守军回信说援兵正在长岭另一头。我们只能守住这里，等回信原件送达，证明撤防令是后来补上的。',
  '哨兵','下一批还在坡上。眼前的塔、控制法术和纸城生命，就是接住他们的时间。',
  '守住纸城到等待期结束，保全调令原件。','长坡延长援军运输；不能用瞬间出兵替代前后波衔接。',
  '守军带回原信，撤防的时辰与伪令对不上。矿路的封锁是有人蓄意制造；护运队可以据此通过交接岗。','守军回信'),
 ('桥矿的双份发运簿','赤砚','桥矿把货送到两个汇口，一份记供军，一份记废矿。夺回对岸发运营，才能把两本簿子放在同一张桌上。',
  '桥矿纸工','走桥能护我们的金车，走主路能先抢汇口。两路的敌情要分别探，下面看见的兵不等于上面也看见。',
  '突破发运营，取得两路发运记录。','桥矿在独立桥边，护运与主路抢汇流需要不同路线承诺。',
  '两本簿子的批号完全相同，签名却被改成不同院的人。赤砚命护运队带走这些页，交给仍未受封令影响的查验者。','桥矿双簿'),
 ('把原页交到人手里','赤砚','已经取回的原页不能留在军营。携证者要把它交到查验岗；矿车仍在走，我们得留一支护卫照看回款。',
  '携证者','我带的是原页，不是替谁定罪的判书。让我走到收件岗，你们还要靠矿线撑起下一批援兵。',
  '护送原页到查验岗，保持携证者存活。','护送锚点与经济线共享防守预算，军团需衔接沿路护卫。',
  '查验者收到原页，查出灯台在为印机蓄力，而覆写巨兵正被派去毁矿册。赤砚可以先断灯，或先拦巨兵。','查验收件签'),
 ('灯台长坡的夜班','赤砚','长坡另一头的灯台整夜不灭。它给复制印机供法力；我们先拆开守营，就能让下一批伪令停在纸上。',
  '灯台学徒','重兵来得慢，快兵或法术能争到停机窗口。后营的灯位和前线护卫，也在争同一笔金。',
  '突破灯台守营，取得供能记录。','长援军路与法力设施形成投资时差，没有额外高地伤害。',
  '灯台的供能页记下了每次印机开动的时辰。三矿工钱在同一时辰被抹名，接下来要把他们的薪册运回来。','灯台供能页'),
 ('越矿线以前','赤砚','覆写巨兵朝归金矿走来。它一旦越过矿线，留在洞口的旧薪册就会被毁；击倒别处的城营救不了这些页。',
  '矿册保管员','请在标出的边界前拦住它。控制只能争时间，最后仍得有伤害让它停下来。',
  '在巨兵跨过指定矿线之前击倒它。','移动巨兵与失败锚点构成实际截止；越线后同帧死亡也无法撤销失败。',
  '巨兵在矿线前停下，保管员保住了旧薪册。上面的三矿批次可以与伪令时辰交叉核对。','未覆写薪册'),
 ('三矿仍有姓名','赤砚','三处矿埠的工人拿出同一批薪册。把该付的金运回城过账，便能让原先被刮掉的名字重新有可核验的工钱。',
  '矿村纸工','三处矿的周转不同。别把所有人都塞进窄洞，纸城收下的每一车才记进这次核对。',
  '完成真实归仓，建立三矿薪资对照。','三个矿点的容量、服务与往返时间决定工人分配。',
  '薪册和收件签合上，伪令与真实工钱不再混在一起。另一具巨像正携印逃走，原印则被送到鉴印台。','三矿核对册'),
 ('追印的岔路','赤砚','第二具巨像带着覆写印记走主路。援兵可从桥边绕来，但我们必须在它触到矿线以前集中拦下。',
  '引路纸工','切桥只能改变后续部队的抵达路线。已经进主路的前排要争时间，不能等桥队凭空出现。',
  '拦截携印巨像，保住覆写印记作检验。','主路移动目标与长桥援军在汇口相遇，绕行收益取决于抵达时间。',
  '覆写印记被封在纸匣里，它的缺角与空令边缘一致。携证者可以带这份实物去双路渡复核。','巨像覆写印记'),
 ('护印台上的旧刻痕','赤砚','原印就在鉴印塔里。撑到匠人完成检验，才能分清磨损旧刻痕与后来补上的复制缺角。',
  '鉴印匠','外矿与塔位都靠前。金能补下一批兵，塔若先倒，旧刻痕就再也对不上了。',
  '保护指定鉴印塔，完成原印检验。','保护塔靠近外矿，护工与守塔的时间和金币相互牵制。',
  '匠人记下旧刻痕，证明封令并非由原印签出。携证者带着检验页，可以去双路渡找到伪令追捕队。','原印检验页'),
 ('双路渡的证人','赤砚','携证者要从双路渡把检验物带回。追捕队第一次开始怀疑封令；让原物到场，比在岔口喊话更有用。',
  '携证者','主路和纸桥都能到交接点。请先替我探路，再决定下一批护卫去哪边，别把未知处当成空路。',
  '护送检验物到渡口交接锚点。','真实双路与汇流点允许选择护送路线，视野与护卫抵达分别决定风险。',
  '检验物在渡口当面对上封令。追捕队交出高折原的印机位置；赤砚决定夺下机器，找出真正改写命令的人。','渡口当面核验'),
 ('高折原的印机','赤砚','伪令队把印机藏在层叠纸坡后。那不是新的王印，是把旧命令反复改写的机器。打通守营，才能取下它的母版。',
  '前哨匠','两段坡折拉开了前后队伍。先到的兵要有支援接上，别让整笔预算死在最后一段坡上。',
  '突破印机守营，取得伪令母版。','双折坡改变军团衔接和运输耗时，地形轮廓需清晰可辨。',
  '印机母版写着归一令，却没有任何一院的见证。要带它出疆，还得保全检验灯阵的副本，或守住撤离时的城门。','伪令母版'),
 ('围灯阵的副本','赤砚','原版只有一份，不能冒险全押在渡口。守住检验灯阵，让匠人抄成不会改写的见证副本，再去合印门。',
  '灯阵匠','指定塔在主路，矿线在纸桥。守护副本与护运要分配路线，桥上通了不等于主路塔安全。',
  '保护灯阵指定前哨到副本完成。','桥矿与主路保护塔处于不同道路，防守任务不能用全局横坐标合并。',
  '见证副本完成，灯阵停下改写功能，只留下照读原页的光。赤砚可以带副本通过合印门，把它交给墨归。','不可覆写副本'),
 ('反攻页的城门','赤砚','旧部奉伪令回来索印。我们守住撤离城门，等载着证人原物的最后一队离开；不必替一张假令杀尽所有旧友。',
  '撤离哨兵','晚到敌军换了入口。看住矿路与纸城，前线推进得再远，也不能让城门先落。',
  '守住纸城直到撤离完成。','后段敌入口改变回防压力，前推与守矿需依据实际已知敌情。',
  '最后一队从城门离开，旧部亲眼看见原物与伪令的差别。撤离签为赤砚打开合印门的会盟通路。','证人撤离签'),
 ('合印门不再封名','赤砚','母版已经取回，保全原物的路线也已走通。合印门仍奉归一令封锁十院来往；我们打通这道门，把证据交给墨归共同见证。',
  '墨归','我来收的是能被大家检验的旧页，不是哪一院写好的罪名。纸桥与矿线都要有人护，别让证据变成新的封令。',
  '打通合印门，完成第一章的交证会盟。','收官汇流、桥路护矿与攻城投入共同决定突破窗口。',
  '赤砚交出伪令母版和已保全的见证，墨归接过第一片祖印。矿路重新通行；未查完的支线仍可回访，追查转向墨骸社的旧纸回廊。','第一片祖印见证'),
]
PARENTS={1:[],2:[1],3:[1],4:[2,3],5:[4],6:[4],7:[5,6],8:[7],9:[7],10:[8,9],11:[10],12:[10],13:[11,12],14:[13],15:[13],16:[14,15],17:[16],18:[17],19:[17],20:[18,19]}
def main():
 archive=QA/'pre-story-change'
 assert not archive.exists(), 'Freeze once, do not overwrite archived inputs'
 archive.mkdir(parents=True)
 manifest=read(ROOT/'release/3.0.0-rc26-preview/build-manifest.json')
 for rel,digest in manifest['source_inputs'].items():assert sha(ROOT/rel)==digest,rel
 shutil.copytree(ROOT/'game/scripts',archive/'game/scripts')
 shutil.copytree(ROOT/'game/data',archive/'game/data')
 shutil.copytree(ROOT/'game/assets/fonts',archive/'game/assets/fonts')
 shutil.copytree(ROOT/'game/tests',archive/'game/tests')
 shutil.copytree(ROOT/'docs/paper-warfront',archive/'docs/paper-warfront')
 shutil.copyfile(ROOT/'README.md',archive/'README.md')
 for rel in ['game/project.godot','game/export_presets.cfg','assets/paper-warfront/campaign.json']:
  target=archive/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,target)
 write(archive/'inputs.json',{'source_manifest':manifest,'snapshots':{p.relative_to(archive).as_posix():sha(p) for p in sorted(archive.rglob('*')) if p.is_file()}})
 campaign=read(ROOT/'game/data/campaign.json');maps=read(ROOT/'game/data/maps.json');by_map={m['id']:m for m in maps['maps']}
 profiles={};flow={}
 for i,level in enumerate(campaign['levels']):
  if i<20:parents=[campaign['levels'][p-1]['id'] for p in PARENTS[i+1]]
  else:parents=[campaign['levels'][i-1]['id']]
  flow[level['id']]={'index':i,'chapter':i//20,'unlock_any':parents,'successors':[]}
  if i>=20:continue
  title,hero,before,npc,place,goal,reason,after,evidence=BEATS[i]
  level['title']='朱印疆·'+title;level['line']=before
  level['story_before']=[{'speaker':hero,'text':before},{'speaker':npc,'text':place}]
  level['story_after']=[{'speaker':hero,'text':after}]
  profiles[level['id']]={'id':'narrative.'+level['id'],'version':1,'map':level['map'],'objective':level['win'],'title':title,'goal':goal,'geography_reason':reason,'evidence_name':evidence,'evidence_flag':level['story_flag'],'roads':[e['id'] for e in by_map[level['map']]['edges']],'objective_anchor':level['objective_anchor'],'status':'authored_runtime_text_and_progression_pending_native_review'}
 for id,row in flow.items():
  for parent in row['unlock_any']:flow[parent]['successors'].append(id)
 routing={'schema_version':1,'revision':'rc27-opening-story-routes-r1','scope':'Opening20 missions: six optional pairs with convergence. Remaining180 retain their existing authored causal order. Spatial branches remain independent of chapter unlocking.', 'root':campaign['levels'][0]['id'],'finale':campaign['levels'][-1]['id'],'nodes':flow}
 narrative={'schema_version':1,'revision':'rc27-opening-map-narrative-r1','profiles':profiles,'constraints':{'story_required_on_every_single_player_map':True,'topology_follows_story_and_play':True,'linear_required':False,'all_maps_must_branch':False,'no_spoiler_from_unvisited_branch':True,'no_free_resources_for_story_flags':True}}
 # Runtime data and design sources have the same stable IDs and exact bytes.
 for name,data in [('campaign.json',campaign),('campaign-flow.json',routing),('campaign-narrative.json',narrative)]:
  write(ROOT/'game/data'/name,data);write(ROOT/'assets/paper-warfront'/name,data)
 # Adopt the independently verified leap correction, not the diagnostic wrappers.
 shutil.copyfile(QA/'blocker-correction-runtime/scripts/battle_sim.gd',ROOT/'game/scripts/battle_sim.gd')
 print('Authored20 opening map stories,200 progression records; six optional pairs. Old maps/combat parameters retained.')
if __name__=='__main__':main()

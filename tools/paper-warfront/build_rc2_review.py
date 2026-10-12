"""Native screenshot comparison and offline review; no browser invocation."""
from pathlib import Path
import html,json
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/rc2'
ASSET=ROOT/'assets/paper-warfront'

def main():
    font=ImageFont.truetype(str(ROOT/'game/assets/fonts/NotoSansSC.ttf'),28)
    small=ImageFont.truetype(str(ROOT/'game/assets/fonts/NotoSansSC.ttf'),19)
    pairs=[('rc1 · 原菜单',ROOT/'output/qa/godot/v3-ui-final-desktop/01-menu.png'),('rc2 · 新版原生菜单',QA/'export/menu.png'),('rc1 · 原地面与战场',ROOT/'output/qa/godot/v3/export/battle.png'),('rc2 · 纸层地形与桥梁',QA/'export/battle.png')]
    board=Image.new('RGB',(1600,1076),'#f6edda');draw=ImageDraw.Draw(board)
    for i,(label,path) in enumerate(pairs):
        x=(i%2)*800;y=(i//2)*516
        draw.text((x+20,y+10),label,font=font,fill='#24343c')
        im=Image.open(path).convert('RGB');im.thumbnail((792,450));board.paste(im,(x+4,y+58))
    draw.text((20,1044),'原生运行截图；战場为导出EXE的演示场景，判定规则另有回归报告。',font=small,fill='#615b50')
    board.save(QA/'before-after.jpg',quality=95)
    labels={f['id']:f['name'] for f in json.loads((ROOT/'game/data/factions.json').read_text(encoding='utf-8'))['factions']}
    worker_cards=''.join(f'<figure class="worker"><img class="phase-image" src="../../output/qa/godot/rc2/native-final/{f}-mine-56.png" data-faction="{f}" alt="{name}真实采矿姿态" loading="lazy"><figcaption>{name} · 自身地区的实际工作状态</figcaption></figure>' for f,name in labels.items())
    def card(src,label):return f'<figure><a href="{src}"><img src="{src}" alt="{label}" loading="lazy"></a><figcaption>{label}</figcaption></figure>'
    native=[('export/menu.png','导出EXE · 桌面菜单'),('native-final/brief.png','战前军令与实际地图'),('ui-desktop/09-research.png','原生科技状态'),('ui-mobile/01-menu.png','横屏移动菜单布局'),('ui-mobile/07-mobile-units.png','横屏军阵操作'),('ui-mobile/07-mobile-spells.png','横屏法术操作')]
    ui_cards=''.join(card('../../output/qa/godot/rc2/'+p,l) for p,l in native)
    maps=''.join(card('../../output/qa/godot/rc2/native-final/map-'+id+'.png',name) for id,name in [('map.01.01','归金坡'),('map.01.07','前哨外矿'),('map.01.11','灯台长坡'),('map.01.04','纸桥岔口'),('map.01.12','矿线阻击'),('map.01.06','守签接力')])
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>纸上兵戈 · rc2原生画面与动作</title><style>
    @font-face{font-family:Paper;src:url('../../game/assets/fonts/NotoSansSC.ttf')}*{box-sizing:border-box}body{margin:0;background:#f6edda;color:#24343c;font-family:Paper,system-ui,sans-serif;line-height:1.7}main{max-width:1440px;margin:auto;padding:32px}h1{font-size:clamp(28px,4vw,46px);margin:0 0 10px}h2{font-size:28px;margin:44px 0 14px}p{max-width:1100px}a{color:#31747c}nav{display:flex;gap:22px;flex-wrap:wrap;margin:18px 0 28px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}figure{margin:0;background:#fff8e9;border:1px solid #c4b294;border-radius:5px;overflow:hidden}figure img{display:block;width:100%;height:auto}figcaption{padding:12px 16px}video{display:block;width:100%;background:#24343c;border:1px solid #c4b294;border-radius:5px}.controls{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}button{font:inherit;min-height:48px;padding:9px 24px;background:#fff8e9;border:1px solid #978b73;border-radius:4px;color:#24343c;cursor:pointer}button[aria-pressed=true]{background:#a83c35;color:#fff8e9}button:focus-visible,a:focus-visible{outline:3px solid #31747c;outline-offset:3px}.note{color:#615b50;font-size:16px}@media(max-width:800px){main{padding:20px}.grid{grid-template-columns:1fr}}
    </style><main><h1>纸上兵戈 · 3.0.0-rc2</h1><p>友军判定、十院采矿、厚纸地图与原生UI的实际运行画面。这里用于审阅素材和动作，游戏界面本身仍由Godot Control实现。</p><nav><a href="../../release/3.0.0-rc2/README.md">Windows／Android发布</a><a href="../../docs/paper-warfront/fixes-rc2/README.md">修复与制作约束</a><a href="../../output/qa/godot/rc2/validation-index.json">证据索引</a></nav>
    <h2>前后视觉</h2>'''+card('../../output/qa/godot/rc2/before-after.jpg','rc1与rc2原生截图；战场时间与预算不同，不能用图片证明伤害规则。')+'''
    <h2>采矿动作</h2><p>实际排队、独立举镐／落镐／回收、装袋与卸货。等待者不占服务槽、不挥镐。录像为13秒、15fps离线取帧、静音，不代表实时性能或声音体验。</p><video controls preload="metadata" poster="../../output/qa/godot/rc2/native-final/yin-mine-56.png" src="../../output/qa/godot/rc2/mining-replay.mp4"></video>
    <div class="controls" aria-label="采矿相位"><button data-phase="30" aria-pressed="false">举镐</button><button data-phase="56" aria-pressed="true">落镐</button><button data-phase="79" aria-pressed="false">回收</button></div><div class="grid">'''+worker_cards+'''</div>
    <h2>菜单与战斗UI</h2><p>桌面与横屏移动布局都有原生输入检查。移动截图是在Windows上启用移动布局，未连接Android真机。法术与结果页面包含受控夹具；正常预算对战另列。</p><div class="grid">'''+ui_cards+'''</div>
    <h2>六张基准地图</h2><p>坡面、路缘和桥梁来自实际路径图。截图中付费招募由正常命令完成，非凭空放兵。</p><div class="grid">'''+maps+'''</div>
    <h2>普通预算完整对战片段</h2><p>纸桥95.717秒结束、玩家AI胜利。视频截取14–24秒与40–50秒，15fps、静音，中间有剪切；不能替代人工玩法、音效或手机性能验收。</p><video controls preload="metadata" poster="../../output/qa/godot/rc2/native-play/battle-022.png" src="../../output/qa/godot/rc2/native-play/battle-replay.mp4"></video>
    <p class="note">两张新地形母图通过Sub2／gpt-image-2.5生成，五种材质与十院镐臂的来源和派生散列在 <a href="../../game/data/rc2-art-provenance.json">增量来源表</a>。程序、资源和报告输入散列由发布审计核对。</p></main>
    <script>for(const button of document.querySelectorAll('[data-phase]'))button.addEventListener('click',()=>{for(const b of document.querySelectorAll('[data-phase]'))b.setAttribute('aria-pressed',String(b===button));for(const image of document.querySelectorAll('.phase-image'))image.src='../../output/qa/godot/rc2/native-final/'+image.dataset.faction+'-mine-'+button.dataset.phase+'.png';});</script></html>'''
    (ASSET/'rc2-review.html').write_text(page,encoding='utf-8')
    print('Native comparison and offline review published.')

if __name__=='__main__':main()

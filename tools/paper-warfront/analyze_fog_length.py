"""Native-probe-derived map/time audit; proposed sight values are never original-game facts."""
from pathlib import Path
import json,csv,math,statistics,sys
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/fog-length-rc6'
def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def paths(definition,start,goal):
    edges={}
    for e in definition['edges']:
        pts=e['points'];length=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))
        edges.setdefault(e['from'],[]).append((e['to'],length))
    def walk(node,seen):
        if node==goal:return [0.0]
        return [length+tail for nxt,length in edges.get(node,[]) if nxt not in seen for tail in walk(nxt,seen|{nxt})]
    return walk(start,{start})
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    native=read('output/qa/godot/fog-length-rc6/native-map-engagement.json')
    maps={m['id']:m for m in read('game/data/maps.json')['maps']}
    levels={l['map']:l for l in read('game/data/campaign.json')['levels']}
    assets=read('game/data/assets.json')['assets'];factions={f['id']:f for f in read('game/data/factions.json')['factions']}
    rows=[]
    for row in native['maps']:
        m=maps[row['id']];routes=paths(m,m['bases'][0]['node'],m['bases'][1]['node'])
        assert routes and abs(min(routes)-row['shortest_road'])<.001
        level=levels[row['id']]
        tallest=max([310.0]+[float(assets[id]['world_height'])*78*1.35 for side in ['faction','enemy'] for id in factions[level[side]]['default_roster']])
        ys=[p[1] for e in m['edges'] for p in e['points']];terrain=max(max(ys),0)-min(min(ys),0);terrain=max(1,terrain)
        # Matches 1280x720 / density 2 / no insets / 8 dp gutter and fit_stage.
        scale=min(.4,164/(tallest+terrain*48),140/(176+terrain*48))
        width=640/scale/78
        result={**row,'longest_road':max(routes),'route_count':len(routes),'road_in_desktop_screens':row['shortest_road']/(1600/78),'phone_world_width':width,'road_in_phone_screens':row['shortest_road']/width,'midfield_reinforcement_axe_seconds':2+row['shortest_road']/(2*1.342),'midfield_reinforcement_cannon_seconds':2+row['shortest_road']/(2*.6588)}
        rows.append(result)
    keys=['canvas_length','base_horizontal','shortest_road','longest_road','road_in_desktop_screens','phone_world_width','road_in_phone_screens','midfield_reinforcement_axe_seconds','midfield_reinforcement_cannon_seconds']
    summary={'maps':len(rows),'ranges':{k:{'min':min(r[k] for r in rows),'median':statistics.median(r[k] for r in rows),'max':max(r[k] for r in rows)} for k in keys},'first_release_seconds':{'min':min(r['baseline_axe']['first_release_seconds'] for r in rows),'median':statistics.median(r['baseline_axe']['first_release_seconds'] for r in rows),'max':max(r['baseline_axe']['first_release_seconds'] for r in rows)},'scope':native['scope'],'phone_scope':'Formula-derived 1280x720 density 2, no insets, default faction rosters; not native capture for all maps. Full viewport width includes safe gutters.','original_game_measurement':False,'rows':rows,'representatives':native['representatives']}
    (QA/'length-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    with (QA/'map-lengths.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['id','name',*keys,'first_release_seconds']);writer.writeheader()
        for row in rows:writer.writerow({**{k:row[k] for k in ['id','name',*keys]},'first_release_seconds':row['baseline_axe']['first_release_seconds']})
    chart(summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ['rows','representatives']},ensure_ascii=False,indent=2))
def chart(summary):
    image=Image.new('RGB',(1400,780),'#f2eddf');draw=ImageDraw.Draw(image)
    font_path=ROOT/'.tools/fonts/NotoSansSC.full.ttf'
    def font(size):
        result=ImageFont.truetype(str(font_path),size)
        result.set_variation_by_axes([600])
        return result
    def text(x,y,value,size=22,color='#283d3b'):draw.text((x,y),value,font=font(size),fill=color)
    text(36,22,'rc6：路长改变接敌与增援，镜头宽度不等于视野',32)
    text(36,78,'200 图已测；下表为六类基准图。首发时间：两侧同兵、空场、2 秒后出生。',21)
    text(36,130,'地图 / 基地间最短路',22);text(770,130,'首次攻击释放（秒）',22)
    text(770,163,'近战',19,'#a75a3b');text(930,163,'远程',19,'#418783');text(1090,163,'攻城',19,'#7d7794')
    rows={r['id']:r for r in summary['rows']}
    for i,rep in enumerate(sorted(summary['representatives'],key=lambda r:r['archetype'])):
        y=210+i*68;r=rows[rep['id']]
        text(36,y,rep['archetype']+' '+r['name'],21)
        draw.rounded_rectangle((300,y+10,300+r['shortest_road']*6,y+30),radius=5,fill='#ac8d68')
        text(650,y,f"{r['shortest_road']:.2f}",21)
        for x,id in [(770,'unit.yin.axe'),(930,'unit.yin.spear'),(1090,'unit.yin.cannon')]:text(x,y,f"{rep['pairs'][id]['first_release_seconds']:.2f}",23)
    text(36,655,'没有迷雾：可提前查看敌军 → 长路只是延迟；存在视野限制：长路也可能隐藏部署。',23)
    text(36,705,'受控原生模拟；不是普通付费对战、原版长度测量，也不是 Android 真机证据。',19,'#74685a')
    image.save(QA/'length-comparison.png')
if __name__=='__main__':main()

"""Chinese silhouette constraints and exact current six-unit statistics."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
SHAPES={
 'yin':['方印重甲、宽刀配竖印盾，扎实双足','轻甲长缨、细长投矛与明显空手释放','圆背重甲配大方印锤，两手举锤压地','方印轨架与四轮车，抬轨、落印、塌架','直立大背旗、指挥短杖，旗面构成长轮廓','低重心签盾、短棍和仓门形竖盾'],
 'mo':['鸟喙骨面、骨刺背与双弯刃，疾步俯冲','孢囊骨背、短管骨针器，吹刺收腹','长垂破布、兽骨法杖，举骨与折身引魂','粗背缝骨兽、巨大骨拳，双足兽体重击','空心破罩袍、垂骸镰，低伏伸镰取魂','多足纸蛛、骨手长肢，爬行与抬臂束魂'],
 'deng':['扇折尖帽、提灯圆镜，镜面朝敌倾斜','垂签长袍、燃签法杖，签面指向释放点','尖角折帽、短身纸匕，低伏跨步刺击','中空灯腹、宽符臂盾，壳体倾倒而非人形倒地','短身折纸匠、纸偶托盘，双手折符托起','灯串长杖、双扇符，展开叠影而非斩击'],
 'ji':['无肉身发条偶、双铆拳、圆轴关节，拳体伸缩','短身钉枪手、弹匣与方枪口，扣机和空轨','重护目镜修械匠、大开口齿扳手，举械与旋齿','低矮绞盘弩车、四轮和展开弩臂，轨道发射与回卷','厚桶身折雷机、钻枪臂，推进解构','宽圆齿盾偶、螺旋钻臂，机械转身而非套人形腿'],
 'yuan':['鸟面尖喙、薄羽翼和突枪，长低姿态','高纸翼弓手、长弓尾羽，侧步拉弦与射后撤步','小型钩翼跑者、卷线钩，低身牵线且完整身体占格','开放风筝架、薄帆与支腿轮，帆形压缩展开','纸马四足、长尾骑手与平举长枪，四足奔行','有帆轮车、纸翼递送者，展开风帆与推轮'],
 'qi':['短粗金契雇佣卫、票孔刀和币盾','币沿宽帽、长票包，举金签再空手投出','长罩袍、细长契镰，账页配重与低身追割','票箱金库撞车、硬票轨与轮，机械直线撞击','金票护运司、卷票号角与币盾，背弓票箱','宽帽披风、悬赏契弩和票币配件，扣机与换票'],
 'mu':['根节矮卫、叶盾与缠藤臂，根足前推','蘑菇冠短身叶灵、孢籽吹管，管口明确','花冠细身补叶师、花杖，花枝举起与修补','粗树干古树、盘根双足和双木拳，体干压缩挥击','长叶肢螳形结网者、薄藤网，长足步态和抛网','带叶脉翅的蛾形体、灯腹和触须，扇翅与萤叶散开'],
 'shuang':['低重心规尺盾卫、硬尺边与雪盾','三角折帽、霜楔纸刀，抬手后空手投出','长规尺、钉页器和直垂制服，抬臂钉页','压雪双轮车、抬管与雪页槽，加载、空膛出手','方尺帽、卷墨笔，笔尖指向封言目标','折页高冠、浮雪页和裁决尺，页签组合施法'],
 'jin':['半燃罩衣、双炭刃与长破边，双刀旋身','焦边兜帽、炭弓和余火箭，拉弦与空弓释放','瘦长破罩衣、火钩镰，低身勾取和收肘','陶灰炉车、排烟管和投火碗，炉架装填与碎倒','炭背喷签者、风箱喷口，挤压风箱与回收','厚焦身抱壶者、裂纹陶壶，抱壶推进及裂火倒地'],
 'bai':['空框面罩、矩形界框盾，框面保持通透','镂字面具、签弩和浮页背，连续扣机与换签','细身长纸笔、刀裁衣边，真正握笔书删','四足页界兽、折扇尾和页嘴，四足压步与吐页','圆形镂孔盘体、薄刃翅，空孔旋面与消矢','叠页长身、卷页筒与禁印镜口，筒口对准施法']
}

def main():
    briefs=json.loads((ROOT/'assets/paper-warfront/frame-rebuild/unit-briefs.json').read_text(encoding='utf-8'))['units']
    units=json.loads((ROOT/'game/data/balance-prototype.json').read_text(encoding='utf-8'))['units']
    factions=json.loads((ROOT/'game/data/factions.json').read_text(encoding='utf-8'))['factions']
    lines=['# 阵营轮廓与执行参数 · 3.0.0-rc5','',
      '造型规格与运行参数一一对应。下表来自当前 balance-prototype；命中、碰撞和弹丸仍由模拟执行。单次伤害为未叠加增益和护甲前的基础量，射程与移速为地图世界单位，前摇为秒。射程不是图片武器的像素长度。',
      '', '所有角色共享纸纤维、墨线、暖侧光与厚纸边阴影；跨阵营禁止共享整身轮廓再改色。不同物种、载具和机关可以采用各自的比例。左右仅镜像完整绘制帧，攻击不能靠固定肢体旋转。', '']
    for faction in factions:
        fid=faction['id'];rows=[r for r in briefs if r['faction']==fid and not units[r['id']].get('economy') and not units[r['id']].get('summoned')]
        assert len(rows)==len(SHAPES[fid])==6
        lines += ['## '+faction['name'],'', '| 单位 | 独立轮廓与动作要求 | 费用 / 生命 | 伤害 / 射程 / 移速 / 前摇 | 实际机制与边界 |','| --- | --- | --- | --- | --- |']
        for row,shape in zip(rows,SHAPES[fid]):
            d=units[row['id']]
            values=' / '.join(f'{d[k]:g}' for k in ['damage','range','speed','windup'])
            lines.append(f"| {row['name']} · {row['id']} | {shape} | {d['gold']:g} 金 / {d['hp']:g} | {values} | {row['hint']} |")
        lines += ['', '本局从六兵种中带 2–4 种，金币与法力的取舍、护矿、阵地和路线决定组合时机。用攻击前摇、真实装填、控制、净化与兵种提示中的反制窗口选择出手；纸工独立占生产项，不挤占作战编组。', '']
    lines += ['## 生成、加工与复核边界','',
      '源板与提示词保留于 v2，素材 ID 不改名。生成图先检查是否有完整身体、正确行数和武器；共享尺度加工保留跨格的完整肢体，只按明确身体核拆开细桥连接。缺少人物或宽重叠遮挡的图集重新生成，不能复制一帧或变形顶替。', '',
      'frame-adjustments.json 记录 32 个释放点、压雪车独立飞行雪球的清除和重弩跟随帧的突出弩矢清除。透明像素清理不决定攻击是否命中。实际飞行物由模拟产生。重弩在独立六帧装填中恢复弹药。', '',
      '原生全帧截图与 visual-review.json 记录当前复核；CSV 的 native-reviewed 仅对应这些相同输入。归一化文件里的 candidate 是加工阶段标签，最终视觉接收由独立验收记录决定。退役模板和失败尝试是历史资料，不能当作当前可用兵种。', '',
      '[主规范](README.md) · [当前 72 个单位表](../../../assets/paper-warfront/frame-rebuild/roster.csv) · [原生素材库](../../../assets/paper-warfront/frame-rebuild-review.html)']
    (ROOT/'docs/paper-warfront/frame-rebuild/05-阵营轮廓与执行参数.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Chinese anatomy/action constraints and current numeric parameters written for 60 units')

if __name__=='__main__':main()

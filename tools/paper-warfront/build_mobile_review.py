"""Compose an offline review from verified native screenshots, never mockups."""
from pathlib import Path
import html,json,shutil,sys
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/mobile-rc3'
GALLERY=ROOT/'assets/paper-warfront/mobile-rc3-review.html'

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    matrix=json.loads((QA/'mobile-matrix.json').read_text(encoding='utf-8'));assert matrix['passed']
    smoke=json.loads((QA/'export/report.json').read_text(encoding='utf-8'));assert smoke['passed']
    shutil.copy2(QA/'export/mobile-phone.png',QA/'after-hud.png')
    # The game's subset only carries in-game glyphs. Editorial captions use
    # the installed system font; no font is copied into the deliverable.
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24)
    small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
    contact=Image.new('RGB',(1480,525),'#f5edd9');d=ImageDraw.Draw(contact)
    for i,(name,title) in enumerate([('before-hud.png','修复前 · 桌面画布缩放'),('after-hud.png','修复后 · 密度布局与 48dp 触控')]):
        x=16+i*740;d.text((x,14),title,font=font,fill='#243438')
        with Image.open(QA/name) as im:
            assert im.size==(1280,720);im=im.convert('RGB');im.thumbnail((724,408));contact.paste(im,(x,60))
    d.text((16,485),'原生游戏画面 · 同为 1280×720、density=2 · 演示对局，不是 Android 真机画面',font=small,fill='#54534d')
    contact.save(QA/'before-after.jpg',quality=92)
    def figure(path,title):
        return f'<figure><img loading="lazy" src="../../output/qa/godot/mobile-rc3/{path}" alt="{html.escape(title)}"><figcaption>{html.escape(title)}</figcaption></figure>'
    labels={'compact-16x9':'小屏手机','phone-16x9':'常规手机','phone-high-density':'高密度手机','phone-notch':'左侧挖孔','phone-reverse-notch':'右侧挖孔','tablet-4x3':'4:3 平板','tablet-16x10':'16:10 平板','portrait-recovery':'竖屏恢复'}
    options=''.join(f'<option value="{c["name"]}">{labels[c["name"]]} · {c["physical_resolution"]}</option>' for c in matrix['cases'])
    sections=[]
    shots=[('01-menu','主菜单'),('04-brief','战前简报 · 底部动作固定'),('06-HUD-yin','法术 HUD · 十院受控输入夹具'),('07-settings','音量与显示 · 原生触摸滑杆'),('08-defeat','失败结算与重新部署')]
    for i,c in enumerate(matrix['cases']):
        figures=''.join(figure(c['name']+'/'+name+'.png',caption) for name,caption in shots)
        if c['name']=='portrait-recovery':figures+=figure(c['name']+'/00-portrait-guard.png','竖屏提示 · 横屏恢复后继续操作')
        sections.append(f'<section class="case" data-case="{c["name"]}" {"hidden" if i else ""}><h2>{labels[c["name"]]}</h2><p>请求尺寸 {c["physical_resolution"]} · density {c["density"]} · 安全边距 px {c["safe_insets_px"]} · {c["checks"]:,} 项通过</p><div class="grid">{figures}</div></section>')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>纸上兵戈 · 移动端原生评审</title>
<style>body{margin:0;background:#f5eddc;color:#263a40;font-family:"Microsoft YaHei",system-ui,sans-serif;line-height:1.6}main{max-width:1440px;margin:auto;padding:24px}h1{font-family:serif;font-size:32px;margin-bottom:4px}h2{font-size:24px}p{max-width:1000px}a{color:#1d717c}img,video{display:block;width:100%;height:auto;background:#eadfc6;border-radius:4px}figure{margin:0;background:#fffaef;border:1px solid #bca88a;padding:12px}figcaption{padding-top:8px;font-size:15px}section{margin:32px 0}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}select{min-height:48px;width:min(100%,420px);padding:8px;font:inherit;background:#fff9ed;border:1px solid #867c68;border-radius:4px}select:focus-visible{outline:3px solid #327e88}video{max-width:1280px}small{color:#5a625e}[hidden]{display:none!important}@media(max-width:900px){.grid{grid-template-columns:1fr}main{padding:16px}h1{font-size:26px}}</style>
<main><h1>纸上兵戈 · 移动端原生评审</h1><p>3.0.0-rc3 · 手机、挖孔屏、平板与触摸交互</p><p>以下为 Windows 原生 Godot 的游戏截图，注入手机密度与安全区，使用 ScreenTouch／ScreenDrag 检查触摸逻辑。Android 真机尚未连接。</p>
<p><a href="../../docs/paper-warfront/mobile-rc3/README.md">修复与验证文档</a> · <a href="../../release/3.0.0-rc3/README.md">Windows / Android 下载</a> · <a href="../../output/qa/godot/mobile-rc3/mobile-matrix.json">八配置检查矩阵</a></p>
<section><h2>同尺寸修复对照</h2><img src="../../output/qa/godot/mobile-rc3/before-after.jpg" alt="原生移动布局修复前后对照"><p><small>修复后画面来自最终导出的 Windows EXE；演示场景使用全科技配置。</small></p></section>
<section><h2>普通预算对战</h2><video controls playsinline preload="none" poster="../../output/qa/godot/mobile-rc3/native-play/battle-022.png" src="../../output/qa/godot/mobile-rc3/native-play/mobile-play.mp4"></video><p><small>原生付费指令与双方 AI。静音离线 15fps 节选，14–24 秒和 40–50 秒之间有明确跳切；不作为设备实时帧率证明。</small></p></section>
<label for="device">选择检查配置</label><br><select id="device">OPTIONS</select>SECTIONS
<p><small>各配置先完成指定尺寸的全部菜单、HUD 与 200 张地图锚点检查，再检查旋转恢复。受控法术截图用于检查 UI 和输入，不代表正常关卡开局。</small></p></main>
<script>const chooser=document.querySelector('#device');chooser.addEventListener('change',()=>{for(const section of document.querySelectorAll('.case'))section.hidden=section.dataset.case!==chooser.value;});</script></html>'''
    GALLERY.write_text(page.replace('OPTIONS',options).replace('SECTIONS',''.join(sections)),encoding='utf-8')
    print('Native mobile contact sheet and offline review written')

if __name__=='__main__':main()

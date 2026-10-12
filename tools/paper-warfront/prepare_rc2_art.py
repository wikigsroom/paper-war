"""Non-destructive worker articulation and generated terrain material publishing."""
from pathlib import Path
import json
import hashlib
from PIL import Image, ImageDraw, ImageChops, ImageOps

ROOT=Path(__file__).resolve().parents[2]
GAME=ROOT/'game'
OUT=ROOT/'output/imagegen/paper-warfront/rc2'
POLYGONS={
 'yin':([(310,302),(345,268),(372,199),(459,183),(486,328),(350,385),(313,346)],(318,305)),
 'mo':([(326,325),(350,300),(387,248),(478,248),(508,370),(363,409),(321,369)],(326,329)),
 'deng':([(328,292),(365,287),(382,248),(399,214),(482,217),(506,338),(361,391),(328,334)],(335,297)),
 'ji':([(318,308),(358,317),(385,308),(409,255),(492,249),(510,374),(352,407),(320,365)],(324,325)),
 'yuan':([(335,306),(363,307),(393,278),(419,254),(500,259),(506,366),(400,402),(331,362)],(345,318)),
 'qi':([(301,325),(329,339),(366,300),(384,265),(456,273),(496,386),(350,419),(301,372)],(307,338)),
 'mu':([(321,299),(351,315),(380,271),(400,215),(484,226),(499,334),(388,393),(325,369)],(330,315)),
 'shuang':([(316,304),(353,291),(376,218),(452,208),(503,328),(364,396),(312,364)],(324,313)),
 'jin':([(313,320),(353,331),(401,280),(423,244),(490,271),(504,399),(359,413),(313,371)],(325,333)),
 'bai':([(315,294),(351,295),(390,243),(423,205),(490,211),(509,344),(371,397),(313,345)],(328,305)),
}
PICK_HEADS={
 'yin':[(302,211),(335,198),(457,200),(477,319),(434,321),(403,258),(349,228)],
 'mo':[(370,260),(420,253),(493,283),(505,369),(468,349),(427,294),(383,288)],
 'deng':[(366,239),(409,215),(484,241),(501,338),(473,322),(440,276),(391,254)],
 'ji':[(370,267),(430,248),(487,263),(505,367),(480,355),(454,289),(388,286)],
 'yuan':[(378,270),(430,252),(487,270),(509,365),(476,356),(450,301),(398,293)],
 'qi':[(312,293),(329,272),(419,284),(470,309),(491,385),(458,369),(428,330),(359,309)],
 'mu':[(349,240),(392,212),(450,217),(493,271),(497,332),(464,306),(426,251),(367,254)],
 'shuang':[(350,227),(390,211),(458,223),(500,282),(507,329),(479,310),(427,248),(370,252)],
 'jin':[(378,270),(399,245),(447,253),(491,285),(505,393),(470,377),(449,305),(405,288)],
 'bai':[(367,220),(416,204),(483,216),(508,282),(510,345),(478,320),(443,253),(383,246)],
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf-8')
def run():
 assets=read(GAME/'data/assets.json')
 records=[]
 for f,(points,pivot) in POLYGONS.items():
  id='unit.'+f+'.worker';meta=assets['assets'][id];anim=meta['animation']
  source=GAME/meta['path'].removeprefix('res://')
  old_body=GAME/'assets/animation'/('unit-'+f+'-worker-body.png')
  original=Image.open(old_body).convert('RGBA')
  mask=Image.new('L',original.size);ImageDraw.Draw(mask).polygon(points,fill=255)
  ImageDraw.Draw(mask).polygon(PICK_HEADS[f],fill=255)
  arm=original.copy();arm.putalpha(ImageChops.multiply(original.getchannel('A'),mask))
  body=original.copy();body.putalpha(ImageChops.multiply(original.getchannel('A'),ImageChops.invert(mask)))
  directory=GAME/'assets/animation/rc2';directory.mkdir(parents=True,exist_ok=True)
  arm_path=directory/('unit-'+f+'-worker-arm-pick.png');body_path=directory/('unit-'+f+'-worker-body-work.png')
  arm.save(arm_path);body.save(body_path)
  anim['parts']['body']='res://'+body_path.relative_to(GAME).as_posix()
  anim['parts']['arm-pick']='res://'+arm_path.relative_to(GAME).as_posix()
  anim['arm-pick_pivot']=list(pivot)
  anim['work_rig_version']='rc2';meta['version']='3.0.0-rc2'
  # This segmentation preserves the existing generated design; no hand-painted
  # substitute bitmap or provider/model change is introduced.
  records.append({'id':id,'source':source.relative_to(ROOT).as_posix(),'source_sha256':sha(source),'method':'authored-arm-mask-from-existing-sub2-silhouette','mask_polygon':points,'pick_head_mask':PICK_HEADS[f],'pivot':pivot,'derived':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in [body_path,arm_path]]})
 texture_source=OUT/'terrain-fiber.png'
 if texture_source.exists():
  target=GAME/'assets/environment/rc2/terrain-fiber.png';target.parent.mkdir(parents=True,exist_ok=True)
  grain=ImageOps.autocontrast(ImageOps.grayscale(Image.open(texture_source))).point(lambda v:226+int(v*29/255))
  grain.convert('RGB').resize((512,512),Image.Resampling.LANCZOS).save(target,optimize=True)
  assets['assets']['material.common.earth']={'path':'res://'+target.relative_to(GAME).as_posix(),'kind':'material','version':'3.0.0-rc2','source':texture_source.relative_to(ROOT).as_posix()}
  records.append({'id':'material.common.earth','source':texture_source.relative_to(ROOT).as_posix(),'source_sha256':sha(texture_source),'model':'gpt-image-2.5','skill':'sub2-image-gen','prompt':(OUT/'terrain-fiber.prompt.txt').relative_to(ROOT).as_posix(),'method':'grayscale-autocontrast-luminance226-255-RGB-downsample-512','derived':[{'path':target.relative_to(ROOT).as_posix(),'sha256':sha(target)}]})
 atlas_path=OUT/'terrain-edge-atlas.png'
 if atlas_path.exists():
  atlas=Image.open(atlas_path).convert('RGBA')
  for i,name in enumerate(['grass','slate','forest','ice']):
   tile=atlas.crop(((i%2)*768,(i//2)*512,(i%2+1)*768,(i//2+1)*512))
   bounds=tile.getchannel('A').point(lambda v:255 if v>128 else 0).getbbox()
   # Trim end caps before repetition; the original paper edge is untouched.
   crop=(bounds[0]+38,bounds[1]-3,bounds[2]-38,bounds[3]+3)
   tile=tile.crop(crop);factor=512/tile.width
   tile=tile.resize((512,round(tile.height*factor)),Image.Resampling.LANCZOS)
   target=GAME/'assets/environment/rc2'/('terrain-edge-'+name+'.png');tile.save(target,optimize=True)
   walk=[229,231,165,163][i];walk=round((walk-crop[1])*factor)
   id='material.common.edge.'+name
   assets['assets'][id]={'path':'res://'+target.relative_to(GAME).as_posix(),'kind':'material','version':'3.0.0-rc2','walk_y':walk,'source':atlas_path.relative_to(ROOT).as_posix()}
   records.append({'id':id,'source':atlas_path.relative_to(ROOT).as_posix(),'source_sha256':sha(atlas_path),'model':'gpt-image-2.5','skill':'sub2-image-gen','prompt':(OUT/'terrain-edge-atlas.prompt.txt').relative_to(ROOT).as_posix(),'quadrant':i,'crop':crop,'walk_y':walk,'method':'native-alpha-crop-discard-endcaps-Lanczos-512','derived':[{'path':target.relative_to(ROOT).as_posix(),'sha256':sha(target)}]})
 assets['version']='3.0.0-rc2';write(GAME/'data/assets.json',assets)
 write(GAME/'data/rc2-art-provenance.json',{'version':'3.0.0-rc2','records':records})
 sheet=Image.new('RGBA',(2560,1024),(246,237,218,255))
 for i,f in enumerate(POLYGONS):
  for col,part in enumerate(['body','arm-pick']):
   p=GAME/assets['assets']['unit.'+f+'.worker']['animation']['parts'][part].removeprefix('res://')
   im=Image.open(p);im.thumbnail((250,450));sheet.alpha_composite(im,((i%5)*512+col*250,(i//5)*512))
 ImageDraw.Draw(sheet).text((8,1000),'rc2 worker body + independently articulated original pickaxe arm',fill='#24343c')
 OUT.mkdir(parents=True,exist_ok=True);sheet.convert('RGB').resize((1536,614)).save(OUT/'worker-rig-review.jpg',quality=92)
 print('Published',len(POLYGONS),'worker rigs and',len(records)-len(POLYGONS),'terrain materials; hashes recorded.')
if __name__=='__main__':run()

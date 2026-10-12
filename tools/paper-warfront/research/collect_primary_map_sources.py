"""Collect public primary-source metadata. No browser or full-article republication."""
import concurrent.futures
import hashlib
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/research/swords-and-soldiers-map/recheck-20261008'
SOURCES=[
 ('R01','https://joostdevblog.blogspot.com/2010/12/designing-levels-without-tools.html'),
 ('R02','https://joostdevblog.blogspot.com/2014/07/evolving-level-art-from-swords-soldiers.html'),
 ('R03','https://www.nintendo.com/en-gb/Games/WiiWare/Swords-Soldiers-286811.html'),
 ('R04','https://steamcommunity.com/stats/63500/achievements/?l=english'),
 ('R05','https://joostdevblog.blogspot.com/2011/01/ai-in-swords-soldiers-part-2.html'),
]

class ArticleMetadata(HTMLParser):
 def __init__(self):super().__init__();self.images=[];self.links=[];self.title=[];self.in_title=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='title':self.in_title=True
  if tag=='img' and a.get('src'):self.images.append({'url':a['src'],'alt':a.get('alt','')})
  if tag=='a' and a.get('href'):self.links.append(a['href'])
 def handle_endtag(self,tag):
  if tag=='title':self.in_title=False
 def handle_data(self,text):
  if self.in_title:self.title.append(text)

def fetch(item):
 key,url=item;record={'id':key,'url':url,'retrieved':'2026-10-08'}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
  with urllib.request.urlopen(req,timeout=20) as response:
   raw=response.read();record.update(http_status=response.status,final_url=response.url,content_sha256=hashlib.sha256(raw).hexdigest())
  text=raw.decode('utf-8','replace');all_meta=ArticleMetadata();all_meta.feed(text)
  record['title']=''.join(all_meta.title).strip()
  if 'joostdevblog' in url:
   begin=text.find("<div class='post-body");end=text.find("<div class='post-footer",begin)
   text=text[begin:end] if begin>=0 and end>begin else text
  meta=ArticleMetadata();meta.feed(text)
  if key=='R03':meta.images=[i for i in meta.images if re.search(r'(sus_content|sas_General|sas_Giant)',i['url'],re.I)]
  record['article_images']=meta.images[:24]
  record['image_links']=[i for i in meta.links if re.search(r'\.(jpg|png)(\?|$)',i,re.I)][:24]
  if key=='R04':
   # Short, isolated official condition strings selected for verification.
   conditions=re.findall(r'<h5>(.*?)</h5>',text,re.S)
   conditions=[re.sub('<[^>]+>','',s).strip() for s in conditions]
   record['map_achievement_conditions']=[s for s in conditions if re.search('goldmine|tower|Viking campaign|Chinese campaign|Aztec campaign',s,re.I)]
  record['status']='retrieved'
 except Exception as e:record.update(status='unavailable',error=str(e))
 return record

if __name__=='__main__':
 sys.stdout.reconfigure(encoding='utf-8');OUT.mkdir(parents=True,exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(fetch,SOURCES))
 (OUT/'primary-source-metadata.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 for r in records:print(json.dumps({'id':r['id'],'status':r['status'],'images':len(r.get('article_images',[])),'conditions':len(r.get('map_achievement_conditions',[]))},ensure_ascii=False))

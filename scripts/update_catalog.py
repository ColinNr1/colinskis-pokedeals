#!/usr/bin/env python3
import json, re, time
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'data'/'catalog.json'
UA='ColinskisPokeDeals/1.0 (+GitHub Pages price monitor)'
TIMEOUT=25
session=requests.Session(); session.headers.update({'User-Agent':UA,'Accept-Language':'en-GB,en;q=0.9'})
PRICE_RE=re.compile(r'(?:€\s*([0-9][0-9.,]*)|(?:EUR|Euro)\s*([0-9][0-9.,]*))',re.I)
OUT_WORDS=('out of stock','sold out','currently unavailable','unavailable')
IN_WORDS=('in stock','add to cart','add to basket','available')
def norm(s): return re.sub(r'[^a-z0-9]+',' ',(s or '').lower()).strip()
def tokens(name):
 skip={'pokemon','tcg','ex','the','pack','box','collection','booster'}
 return [t for t in norm(name).split() if len(t)>2 and t not in skip]
def parse_price(s):
 s=s.replace(' ','').replace(',','.')
 if s.count('.')>1:
  p=s.split('.'); s=''.join(p[:-1])+'.'+p[-1]
 try:return float(s)
 except:return None
def get_page(url):
 r=session.get(url,timeout=TIMEOUT,allow_redirects=True); r.raise_for_status(); return r.text,r.url
def find_near_text(text,name):
 nt=norm(text); toks=tokens(name)
 if not toks:return None
 for a in sorted(toks,key=len,reverse=True):
  start=0
  while True:
   i=nt.find(a,start)
   if i<0:break
   w=nt[max(0,i-850):min(len(nt),i+1400)]
   if sum(1 for t in toks if t in w)/max(1,len(toks))>=.55:return w
   start=i+len(a)
 return None
def inspect_listing(listing,product_name):
 url=listing.get('url','')
 if not url:return {'status':'no_url'}
 try:html,final=get_page(url)
 except Exception as e:return {'status':'fetch_error','error':str(e)[:180]}
 text=' '.join(BeautifulSoup(html,'html.parser').stripped_strings); near=find_near_text(text,product_name)
 if not near:return {'status':'not_matched','final_url':final}
 exactish=urlparse(final).path.count('/')>=3 and not any(x in urlparse(final).path.lower() for x in ('category','collections','shop'))
 lower=near.lower(); stock='unknown'
 if any(w in lower for w in IN_WORDS):stock='in_stock'
 if any(w in lower for w in OUT_WORDS) and exactish:stock='out_of_stock'
 candidates=[]
 for m in PRICE_RE.finditer(near):
  val=parse_price(m.group(1) or m.group(2))
  if val and .5<=val<=5000:candidates.append(val)
 old=float(listing.get('price',0) or 0); price=None
 if candidates:
  price=min(candidates,key=lambda x:abs(x-old)) if old else min(candidates)
  if old and not (old*.45<=price<=old*2.25):price=None
 return {'status':'ok','stock':stock,'price':price,'final_url':final,'exactish':exactish}
def refresh_group(items,key='listings'):
 changes=[]; checks=0
 for item in items:
  kept=[]
  for listing in item.get(key) or []:
   checks+=1; res=inspect_listing(listing,item.get('name',''))
   listing['last_checked']=datetime.now(timezone.utc).isoformat(timespec='seconds'); listing['scan_status']=res.get('status')
   if res.get('price') is not None:
    new=round(res['price'],2); old=listing.get('price')
    if old!=new:changes.append(f"{item['name']} / {listing.get('store')}: €{old} -> €{new}"); listing['price']=new
   if res.get('stock')=='out_of_stock' and res.get('exactish'):
    changes.append(f"{item['name']} / {listing.get('store')}: removed (out of stock)"); continue
   kept.append(listing); time.sleep(.15)
  item[key]=kept
 return changes,checks
def main():
 data=json.loads(CATALOG.read_text(encoding='utf-8')); all_changes=[]; total=0
 for group in ('products','preorders'):
  c,n=refresh_group(data.get(group,[])); all_changes+=c; total+=n
 data['generated_at']=datetime.now(timezone.utc).isoformat(timespec='seconds')
 data['scan_summary']={'checked_listings':total,'changes':all_changes[:100],'scanner_version':'1.0'}
 data['products']=[p for p in data.get('products',[]) if p.get('listings')]
 CATALOG.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'Checked {total} listings; {len(all_changes)} changes')
 for x in all_changes:print('-',x)
if __name__=='__main__':main()

#!/usr/bin/env python3
import json,re
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]; CAT=ROOT/'data'/'catalog.json'
COUNT_PATTERNS=[
 r'(?:contains?|includes?|with)\s+(\d{1,2})\s+(?:pokemon tcg\s+)?booster packs?',
 r'(\d{1,2})\s+(?:pokemon tcg\s+)?booster packs?\s+(?:inside|included|per box|in each)',
 r'(\d{1,2})\s+(?:packs?|boosters?)\s+per\s+(?:box|bundle)',
]
def infer_from_name(n):
 s=n.lower()
 if 'half booster box' in s:return 18,'product_type'
 if 'booster box' in s or 'display' in s:return 36,'product_type'
 if 'booster bundle' in s:return 6,'product_type'
 if '3-pack' in s or '3 pack blister' in s:return 3,'product_type'
 if 'sleeved booster' in s or re.search(r'\bbooster pack\b',s):return 1,'product_type'
 return None,None
def extract_count(text):
 t=' '.join(text.split())
 vals=[]
 for p in COUNT_PATTERNS:
  vals += [int(x) for x in re.findall(p,t,re.I) if 1<=int(x)<=72]
 return vals[0] if vals else None
def main():
 data=json.loads(CAT.read_text(encoding='utf-8')); unresolved=[]; verified=0
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage']); ctx=browser.new_context(locale='en-GB')
  for group in ('products','preorders'):
   for item in data.get(group,[]):
    name=item.get('name',''); c,src=infer_from_name(name)
    if c:
     item['pack_count']=c;item['pack_count_source']=src;verified+=1;continue
    found=None; source_url=None
    for listing in item.get('listings') or []:
     url=listing.get('url','')
     if not url.startswith('http'):continue
     page=ctx.new_page()
     try:
      page.goto(url,wait_until='domcontentloaded',timeout=16000);page.wait_for_timeout(600)
      text=BeautifulSoup(page.content(),'html.parser').get_text(' ',strip=True)
      found=extract_count(text)
      if found:source_url=page.url;break
     except Exception:pass
     finally:page.close()
    if found:
     item['pack_count']=found;item['pack_count_source']='vendor_description';item['pack_count_source_url']=source_url;verified+=1
    else:
     item.pop('pack_count',None);item['pack_count_source']='unverified';unresolved.append(name)
  ctx.close();browser.close()
 data.setdefault('scan_summary',{})['pack_counts']={'verified':verified,'unresolved':len(unresolved),'unresolved_products':unresolved}
 CAT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'Pack counts verified: {verified}; unresolved: {len(unresolved)}')
 for n in unresolved:print('UNRESOLVED:',n)
if __name__=='__main__':main()

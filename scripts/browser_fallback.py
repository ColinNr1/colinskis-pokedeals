#!/usr/bin/env python3
import json, re
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from update_catalog import find_near_text, extract_image, extract_structured_price_stock, extract_jsonld_product, PRICE_RE, parse_price, bad_image, is_direct_product_url, match_ratio, IN_WORDS, OUT_WORDS
ROOT=Path(__file__).resolve().parents[1];CATALOG=ROOT/'data'/'catalog.json'
TARGET_STATUSES={'fetch_error','not_matched','browser_not_matched','browser_timeout','browser_error'}
def clean_slug(url):
    path=urlparse(url or '').path.lower().replace('-',' ').replace('_',' ');return re.sub(r'[^a-z0-9 ]+',' ',path)
def match_evidence(soup, final_url, name, text):
    title=soup.title.get_text(' ',strip=True) if soup.title else '';h1=' '.join(x.get_text(' ',strip=True) for x in soup.find_all('h1')[:3]);slug=clean_slug(final_url);product=extract_jsonld_product(soup,name);json_name=product.get('name','') if isinstance(product,dict) else ''
    scores={'title':match_ratio(name,title),'h1':match_ratio(name,h1),'slug':match_ratio(name,slug),'jsonld':match_ratio(name,json_name)};near=find_near_text(text,name);scores['body']=1.0 if near else 0.0
    return max(scores.values())>=.62 or sum(1 for v in scores.values() if v>=.42)>=2,near,scores
def inspect_html(html, final_url, name, old_price):
    soup=BeautifulSoup(html,'html.parser');text=' '.join(soup.stripped_strings);accepted,near,scores=match_evidence(soup,final_url,name,text)
    if not accepted:return {'status':'browser_not_matched','image':extract_image(soup,final_url,name),'match_scores':scores}
    scoped=near or text[:12000];lower=scoped.lower();stock='unknown'
    if any(w in lower for w in IN_WORDS):stock='in_stock'
    if any(w in lower for w in OUT_WORDS):stock='out_of_stock'
    structured_price,structured_stock=extract_structured_price_stock(soup,name)
    if structured_stock:stock=structured_stock
    candidates=[]
    for m in PRICE_RE.finditer(scoped):
        v=parse_price(m.group(1) or m.group(2))
        if v and .5<=v<=5000:candidates.append(v)
    old=float(old_price or 0);price=None;price_source=None
    if structured_price and .5<=structured_price<=5000:price=structured_price;price_source='jsonld'
    elif candidates:
        price=min(candidates,key=lambda x:abs(x-old)) if old else min(candidates);price_source='page_context'
        if old and not (old*.45<=price<=old*2.25):price=None;price_source=None
    return {'status':'browser_ok','stock':stock,'price':price,'price_source':price_source,'image':extract_image(soup,final_url,name),'match_scores':scores}
def main():
    data=json.loads(CATALOG.read_text(encoding='utf-8'));changed=[];attempted=0;recovered=0
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--disable-dev-shm-usage','--no-sandbox']);context=browser.new_context(locale='en-GB',user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',viewport={'width':1365,'height':900})
        for group in ('products','preorders'):
            for item in data.get(group,[]):
                kept=[];best_image=None
                for listing in item.get('listings') or []:
                    if listing.get('scan_status') not in TARGET_STATUSES or not is_direct_product_url(listing.get('url','')):kept.append(listing);continue
                    attempted+=1;listing['live_verified']=False;listing['price_verified']=False;listing['stock_verified']=False;page=context.new_page()
                    try:
                        page.goto(listing['url'],wait_until='domcontentloaded',timeout=22000);page.wait_for_timeout(1600);final=page.url;res=inspect_html(page.content(),final,item.get('name',''),listing.get('price'));listing['last_checked']=datetime.now(timezone.utc).isoformat(timespec='seconds');listing['scan_status']=res['status'];listing['match_scores']=res.get('match_scores')
                        if res.get('image') and not best_image:best_image=res['image']
                        if res.get('price') is not None:
                            new=round(res['price'],2);listing['price_verified']=True;listing['price_source']=res.get('price_source')
                            if listing.get('price')!=new:changed.append(f"{item['name']} / {listing.get('store')}: €{listing.get('price')} -> €{new} (browser)")
                            listing['price']=new
                        if res.get('stock')=='in_stock':listing['stock_verified']=True
                        if res.get('stock')=='out_of_stock':changed.append(f"{item['name']} / {listing.get('store')}: removed (browser confirmed out of stock)");continue
                        listing['live_verified']=bool(res['status']=='browser_ok' and listing['price_verified'] and listing['stock_verified'])
                        if listing['live_verified']:recovered+=1
                    except PlaywrightTimeoutError:listing['scan_status']='browser_timeout'
                    except Exception as e:listing['scan_status']='browser_error';listing['browser_error']=str(e)[:160]
                    finally:page.close()
                    kept.append(listing)
                item['listings']=kept
                if best_image and bad_image(item.get('img')):item['img']=best_image;changed.append(f"{item['name']}: replaced search image with browser-verified vendor image")
        context.close();browser.close()
    statuses={};bing=0;strict_live=0
    for group in ('products','preorders'):
        for item in data.get(group,[]):
            if 'bing.net' in (item.get('img') or '').lower():bing+=1
            for listing in item.get('listings') or []:
                s=listing.get('scan_status','unknown');statuses[s]=statuses.get(s,0)+1
                if listing.get('live_verified'):strict_live+=1
    data.setdefault('scan_summary',{})['browser_fallback']={'attempted':attempted,'recovered':recovered,'statuses':statuses,'strict_live_verified':strict_live,'product_bing_images_remaining':bing,'matcher_version':'2.1-strict-live'}
    data.setdefault('scan_summary',{}).setdefault('changes',[]).extend(changed[:100]);data['products']=[p for p in data.get('products',[]) if p.get('listings')];CATALOG.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Browser fallback attempted {attempted}; recovered {recovered}; strict_live={strict_live}; bing={bing}; statuses={statuses}')
    for x in changed:print('-',x)
if __name__=='__main__':main()

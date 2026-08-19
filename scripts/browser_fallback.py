#!/usr/bin/env python3
import json, re
from pathlib import Path
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from update_catalog import (
    find_near_text, extract_image, extract_structured_price_stock,
    PRICE_RE, parse_price, bad_image, is_direct_product_url, match_ratio,
    IN_WORDS, OUT_WORDS
)

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'data'/'catalog.json'
TARGET_STATUSES={'fetch_error','not_matched'}


def inspect_html(html, final_url, name, old_price):
    soup=BeautifulSoup(html,'html.parser')
    text=' '.join(soup.stripped_strings)
    title=soup.title.get_text(' ',strip=True) if soup.title else ''
    near=find_near_text(text,name)
    if not near and match_ratio(name,title)<.35:
        return {'status':'browser_not_matched','image':extract_image(soup,final_url,name)}
    scoped=near or text[:7000]
    lower=scoped.lower()
    stock='unknown'
    if any(w in lower for w in IN_WORDS):stock='in_stock'
    if any(w in lower for w in OUT_WORDS):stock='out_of_stock'
    structured_price,structured_stock=extract_structured_price_stock(soup,name)
    if structured_stock:stock=structured_stock
    candidates=[]
    if structured_price and .5<=structured_price<=5000:candidates.append(structured_price)
    for m in PRICE_RE.finditer(scoped):
        v=parse_price(m.group(1) or m.group(2))
        if v and .5<=v<=5000:candidates.append(v)
    price=None
    old=float(old_price or 0)
    if candidates:
        price=min(candidates,key=lambda x:abs(x-old)) if old else min(candidates)
        if old and not (old*.45<=price<=old*2.25):price=None
    return {
        'status':'browser_ok','stock':stock,'price':price,
        'image':extract_image(soup,final_url,name)
    }


def main():
    data=json.loads(CATALOG.read_text(encoding='utf-8'))
    changed=[];attempted=0;recovered=0
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--disable-dev-shm-usage','--no-sandbox'])
        context=browser.new_context(
            locale='en-GB',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
            viewport={'width':1365,'height':900}
        )
        for group in ('products','preorders'):
            for item in data.get(group,[]):
                kept=[];best_image=None
                for listing in item.get('listings') or []:
                    if listing.get('scan_status') not in TARGET_STATUSES or not is_direct_product_url(listing.get('url','')):
                        kept.append(listing);continue
                    attempted+=1
                    page=context.new_page()
                    try:
                        page.goto(listing['url'],wait_until='domcontentloaded',timeout=18000)
                        page.wait_for_timeout(1200)
                        final=page.url
                        html=page.content()
                        res=inspect_html(html,final,item.get('name',''),listing.get('price'))
                        listing['last_checked']=datetime.now(timezone.utc).isoformat(timespec='seconds')
                        listing['scan_status']=res['status']
                        if res.get('image') and not best_image:best_image=res['image']
                        if res.get('price') is not None:
                            new=round(res['price'],2)
                            if listing.get('price')!=new:
                                changed.append(f"{item['name']} / {listing.get('store')}: €{listing.get('price')} -> €{new} (browser)")
                            listing['price']=new
                        if res.get('stock')=='out_of_stock':
                            changed.append(f"{item['name']} / {listing.get('store')}: removed (browser confirmed out of stock)")
                            continue
                        if res['status']=='browser_ok':recovered+=1
                    except PlaywrightTimeoutError:
                        listing['scan_status']='browser_timeout'
                    except Exception as e:
                        listing['scan_status']='browser_error'
                        listing['browser_error']=str(e)[:160]
                    finally:
                        page.close()
                    kept.append(listing)
                item['listings']=kept
                if best_image and bad_image(item.get('img')):
                    item['img']=best_image
                    changed.append(f"{item['name']}: replaced search image with browser-verified vendor image")
        context.close();browser.close()

    statuses={}
    for group in ('products','preorders'):
        for item in data.get(group,[]):
            for listing in item.get('listings') or []:
                s=listing.get('scan_status','unknown');statuses[s]=statuses.get(s,0)+1
    data.setdefault('scan_summary',{})['browser_fallback']={
        'attempted':attempted,'recovered':recovered,'statuses':statuses
    }
    data.setdefault('scan_summary',{}).setdefault('changes',[]).extend(changed[:100])
    data['products']=[p for p in data.get('products',[]) if p.get('listings')]
    CATALOG.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Browser fallback attempted {attempted}; recovered {recovered}; statuses={statuses}')
    for x in changed:print('-',x)

if __name__=='__main__':main()

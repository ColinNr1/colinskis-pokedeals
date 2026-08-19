#!/usr/bin/env python3
import json, re
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from update_catalog import (
    match_ratio, extract_image, extract_structured_price_stock,
    PRICE_RE, parse_price, IN_WORDS, OUT_WORDS, bad_image
)

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'data'/'catalog.json'


def is_product_href(href):
    p=urlparse(href or '').path.lower()
    return '/product/' in p or '/product-page/' in p or '/products/' in p


def candidate_links(html, base_url):
    soup=BeautifulSoup(html,'html.parser')
    out=[]
    seen=set()
    for a in soup.find_all('a',href=True):
        href=urljoin(base_url,a['href'])
        if not is_product_href(href) or href in seen:
            continue
        seen.add(href)
        parent=a
        for _ in range(3):
            if parent.parent is None:
                break
            parent=parent.parent
        text=' '.join(parent.stripped_strings)[:1500] or a.get_text(' ',strip=True)
        img=None
        imgtag=parent.find('img')
        if imgtag:
            img=(imgtag.get('src') or imgtag.get('data-src') or
                 imgtag.get('data-lazy-src') or imgtag.get('data-original'))
        out.append({'url':href,'text':text,'img':urljoin(base_url,img) if img else None})
    return out


def best_candidate(name,cands):
    scored=[]
    for c in cands:
        score=match_ratio(name,c['text'])
        score=max(score,match_ratio(name,urlparse(c['url']).path.replace('-',' ')))
        scored.append((score,c))
    scored.sort(key=lambda x:x[0],reverse=True)
    return scored[0] if scored and scored[0][0]>=.42 else (0,None)


def inspect_product(page,url,name,old_price):
    page.goto(url,wait_until='domcontentloaded',timeout=20000)
    page.wait_for_timeout(900)
    final=page.url
    html=page.content()
    soup=BeautifulSoup(html,'html.parser')
    text=' '.join(soup.stripped_strings)
    lower=text.lower()
    stock='unknown'
    if any(w in lower for w in IN_WORDS): stock='in_stock'
    if any(w in lower for w in OUT_WORDS): stock='out_of_stock'
    price,structured_stock=extract_structured_price_stock(soup,name)
    if structured_stock: stock=structured_stock
    candidates=[]
    if price and .5<=price<=5000: candidates.append(price)
    for m in PRICE_RE.finditer(text[:12000]):
        v=parse_price(m.group(1) or m.group(2))
        if v and .5<=v<=5000: candidates.append(v)
    old=float(old_price or 0)
    picked=None
    if candidates:
        picked=min(candidates,key=lambda x:abs(x-old)) if old else min(candidates)
        if old and not (old*.45<=picked<=old*2.25): picked=None
    return {'url':final,'stock':stock,'price':picked,'img':extract_image(soup,final,name)}


def main():
    data=json.loads(CATALOG.read_text(encoding='utf-8'))
    accessories=data.get('accessories',[])
    resolved=0; verified=0; removed=0; changes=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        ctx=browser.new_context(
            locale='en-GB',viewport={'width':1440,'height':1000},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36'
        )
        cache={}; kept=[]
        for acc in accessories:
            url=acc.get('url',''); direct=is_product_href(url); candidate_img=None
            if not direct and url:
                if url not in cache:
                    p=ctx.new_page()
                    try:
                        p.goto(url,wait_until='domcontentloaded',timeout=22000)
                        p.wait_for_timeout(1200)
                        cache[url]=candidate_links(p.content(),p.url)
                    except Exception:
                        cache[url]=[]
                    finally:
                        p.close()
                _,c=best_candidate(acc.get('name',''),cache[url])
                if c:
                    acc['url']=c['url']; url=c['url']; direct=True; candidate_img=c.get('img'); resolved+=1
                    changes.append(f"{acc['name']}: resolved direct product link")
            if direct:
                p=ctx.new_page()
                try:
                    result=inspect_product(p,url,acc.get('name',''),acc.get('price'))
                    acc['last_checked']=datetime.now(timezone.utc).isoformat(timespec='seconds')
                    acc['scan_status']='browser_ok'; acc['direct_product_url']=True
                    if result.get('stock')=='out_of_stock':
                        removed+=1; changes.append(f"{acc['name']}: removed (out of stock)"); continue
                    if result.get('price') is not None:
                        new=round(result['price'],2)
                        if acc.get('price')!=new: changes.append(f"{acc['name']}: €{acc.get('price')} -> €{new}")
                        acc['price']=new
                    image=result.get('img') or candidate_img
                    if image and (bad_image(acc.get('img')) or acc.get('img')!=image):
                        acc['img']=image; changes.append(f"{acc['name']}: installed vendor product image")
                    acc['url']=result.get('url') or url; verified+=1
                except Exception as e:
                    acc['last_checked']=datetime.now(timezone.utc).isoformat(timespec='seconds')
                    acc['scan_status']='browser_error'; acc['browser_error']=str(e)[:160]
                    if candidate_img and bad_image(acc.get('img')): acc['img']=candidate_img
                finally:
                    p.close()
            kept.append(acc)
        ctx.close(); browser.close()
    data['accessories']=kept
    bing=sum(1 for a in kept if 'bing.net' in (a.get('img') or '').lower())
    direct=sum(1 for a in kept if is_product_href(a.get('url','')))
    data.setdefault('scan_summary',{})['accessories']={
        'total':len(kept),'resolved':resolved,'verified':verified,'removed':removed,
        'direct_links':direct,'bing_images_remaining':bing
    }
    data.setdefault('scan_summary',{}).setdefault('changes',[]).extend(changes[:150])
    CATALOG.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Accessories: total={len(kept)} resolved={resolved} verified={verified} direct={direct} bing_remaining={bing}')
    for x in changes: print('-',x)

if __name__=='__main__': main()

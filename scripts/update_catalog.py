#!/usr/bin/env python3
import json, re, time
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'data'/'catalog.json'
TIMEOUT=30
session=requests.Session()
session.headers.update({
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
    'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language':'en-GB,en;q=0.9',
    'Cache-Control':'no-cache','Pragma':'no-cache',
})
PRICE_RE=re.compile(r'(?:€\s*([0-9][0-9.,]*)|(?:EUR|Euro)\s*([0-9][0-9.,]*))',re.I)
OUT_WORDS=('out of stock','sold out','currently unavailable','unavailable')
IN_WORDS=('in stock','add to cart','add to basket','available','buy now')

def norm(s):return re.sub(r'[^a-z0-9]+',' ',(s or '').lower()).strip()
def tokens(name):
    skip={'pokemon','tcg','ex','the','pack','box','collection','booster','edition','mega','evolution'}
    return [t for t in norm(name).split() if len(t)>2 and t not in skip]
def match_ratio(a,b):
    toks=tokens(a);nb=norm(b)
    return sum(1 for t in toks if t in nb)/len(toks) if toks else 0
def parse_price(s):
    s=s.replace(' ','').replace(',','.')
    if s.count('.')>1:
        p=s.split('.');s=''.join(p[:-1])+'.'+p[-1]
    try:return float(s)
    except:return None
def is_direct_product_url(url):
    if not url:return False
    p=urlparse(url).path.lower().rstrip('/')+'/'
    return ('/product/' in p or '/product-page/' in p or '/products/' in p) and not any(x in p for x in ('/product-category/','/category/','/collections/','/shop/'))
def get_page(url):
    last=None
    for attempt in range(3):
        try:
            r=session.get(url,timeout=TIMEOUT,allow_redirects=True)
            if r.status_code in (403,429,500,502,503,504):
                last=RuntimeError(f'HTTP {r.status_code}');time.sleep(1.0+attempt*1.5);continue
            r.raise_for_status();return r.text,r.url
        except Exception as e:last=e;time.sleep(.7+attempt)
    raise last or RuntimeError('fetch failed')
def find_near_text(text,name):
    nt=norm(text);toks=tokens(name)
    if not toks:return None
    for a in sorted(toks,key=len,reverse=True):
        start=0
        while True:
            i=nt.find(a,start)
            if i<0:break
            w=nt[max(0,i-1200):min(len(nt),i+2200)]
            if sum(1 for t in toks if t in w)/max(1,len(toks))>=.45:return w
            start=i+len(a)
    return None
def extract_jsonld_product(soup, product_name):
    best=None
    for tag in soup.find_all('script',attrs={'type':'application/ld+json'}):
        try:obj=json.loads(tag.string or tag.get_text() or '{}')
        except:continue
        stack=obj if isinstance(obj,list) else [obj]
        while stack:
            x=stack.pop()
            if isinstance(x,list):stack.extend(x);continue
            if not isinstance(x,dict):continue
            if isinstance(x.get('@graph'),list):stack.extend(x['@graph'])
            typ=x.get('@type')
            if typ=='Product' or (isinstance(typ,list) and 'Product' in typ):
                score=match_ratio(product_name,x.get('name',''))
                if best is None or score>best[0]:best=(score,x)
    return best[1] if best and best[0]>=.35 else None
def extract_image(soup, final_url, product_name):
    product=extract_jsonld_product(soup,product_name)
    if product:
        image=product.get('image')
        if isinstance(image,list) and image:image=image[0]
        if isinstance(image,dict):image=image.get('url') or image.get('contentUrl')
        if isinstance(image,str) and image.startswith(('http://','https://','/')):return urljoin(final_url,image)
    for attr,val in [('property','og:image'),('name','twitter:image'),('property','twitter:image')]:
        tag=soup.find('meta',attrs={attr:val})
        if tag and tag.get('content'):return urljoin(final_url,tag['content'])
    return None
def extract_structured_price_stock(soup, product_name):
    product=extract_jsonld_product(soup,product_name)
    if not product:return None,None
    offers=product.get('offers')
    if isinstance(offers,list):offers=offers[0] if offers else None
    if not isinstance(offers,dict):return None,None
    price=parse_price(str(offers.get('price',''))) if offers.get('price') is not None else None
    avail=str(offers.get('availability','')).lower();stock=None
    if 'instock' in avail:stock='in_stock'
    elif 'outofstock' in avail or 'soldout' in avail:stock='out_of_stock'
    return price,stock
def inspect_listing(listing,product_name):
    url=listing.get('url','')
    if not url:return {'status':'no_url'}
    if not is_direct_product_url(url):return {'status':'invalid_non_product_url'}
    try:html,final=get_page(url)
    except Exception as e:return {'status':'fetch_error','error':str(e)[:180]}
    if not is_direct_product_url(final):return {'status':'redirected_non_product_url','final_url':final}
    soup=BeautifulSoup(html,'html.parser');text=' '.join(soup.stripped_strings);page_title=(soup.title.get_text(' ',strip=True) if soup.title else '')
    near=find_near_text(text,product_name);title_match=match_ratio(product_name,page_title)
    if not near and title_match<.35:return {'status':'not_matched','final_url':final,'image':extract_image(soup,final,product_name)}
    scoped=near or norm(text[:6000]);lower=scoped.lower();stock='unknown'
    if any(w in lower for w in IN_WORDS):stock='in_stock'
    if any(w in lower for w in OUT_WORDS):stock='out_of_stock'
    structured_price,structured_stock=extract_structured_price_stock(soup,product_name)
    if structured_stock:stock=structured_stock
    candidates=[]
    for m in PRICE_RE.finditer(scoped):
        val=parse_price(m.group(1) or m.group(2))
        if val and .5<=val<=5000:candidates.append(val)
    old=float(listing.get('price',0) or 0);price=None;price_source=None
    if structured_price and .5<=structured_price<=5000:
        price=structured_price;price_source='jsonld'
    elif candidates:
        price=min(candidates,key=lambda x:abs(x-old)) if old else min(candidates);price_source='page_context'
        if old and not (old*.45<=price<=old*2.25):price=None;price_source=None
    return {'status':'ok','stock':stock,'price':price,'price_source':price_source,'final_url':final,'direct_url':True,'image':extract_image(soup,final,product_name)}
def bad_image(url):
    u=(url or '').lower();return (not u) or 'bing.net' in u or u.startswith('data:image/svg+xml')
def refresh_group(items,key='listings'):
    changes=[];checks=0
    for item in items:
        kept=[];best_image=None
        for listing in item.get(key) or []:
            checks+=1;listing['live_verified']=False;listing['price_verified']=False;listing['stock_verified']=False
            res=inspect_listing(listing,item.get('name',''));listing['last_checked']=datetime.now(timezone.utc).isoformat(timespec='seconds');listing['scan_status']=res.get('status');listing['direct_product_url']=is_direct_product_url(listing.get('url',''))
            if res.get('image') and not best_image:best_image=res['image']
            if res.get('price') is not None:
                new=round(res['price'],2);old=listing.get('price');listing['price_verified']=True;listing['price_source']=res.get('price_source')
                if old!=new:changes.append(f"{item['name']} / {listing.get('store')}: €{old} -> €{new}")
                listing['price']=new
            if res.get('stock')=='in_stock':listing['stock_verified']=True
            if res.get('stock')=='out_of_stock':changes.append(f"{item['name']} / {listing.get('store')}: removed (out of stock)");continue
            listing['live_verified']=bool(res.get('status')=='ok' and listing['price_verified'] and listing['stock_verified'])
            kept.append(listing);time.sleep(.12)
        item[key]=kept
        if best_image and bad_image(item.get('img')):item['img']=best_image;changes.append(f"{item['name']}: replaced placeholder/search image with vendor product image")
    return changes,checks
def validate_direct_links(data):
    invalid=[]
    for group in ('products','preorders'):
        for item in data.get(group,[]):
            for listing in item.get('listings') or []:
                if not is_direct_product_url(listing.get('url','')):invalid.append(f"{group}: {item.get('name')} / {listing.get('store')} -> {listing.get('url')}")
    if invalid:raise SystemExit('Refusing to write catalog: non-product vendor URLs remain:\n'+'\n'.join(invalid[:50]))
def main():
    data=json.loads(CATALOG.read_text(encoding='utf-8'));validate_direct_links(data);all_changes=[];total=0
    for group in ('products','preorders'):
        c,n=refresh_group(data.get(group,[]));all_changes+=c;total+=n
    data['generated_at']=datetime.now(timezone.utc).isoformat(timespec='seconds');statuses={}
    for group in ('products','preorders'):
        for item in data.get(group,[]):
            for listing in item.get('listings') or []:
                s=listing.get('scan_status','unknown');statuses[s]=statuses.get(s,0)+1
    data['scan_summary']={'checked_listings':total,'changes':all_changes[:150],'scanner_version':'1.3-strict-live-verification','statuses':statuses}
    data['products']=[p for p in data.get('products',[]) if p.get('listings')];validate_direct_links(data)
    CATALOG.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Checked {total} direct product listings; {len(all_changes)} changes; statuses={statuses}')
    for x in all_changes:print('-',x)
if __name__=='__main__':main()

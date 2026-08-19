#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data'/'catalog.json'

# Emergency denylist for listings confirmed dead/incorrect. These stay hidden even
# if a vendor error page accidentally exposes price-like or stock-like text.
DENYLIST={
    ('first-partner-s3','Gamebreaker'),
}

def main():
    data=json.loads(CAT.read_text(encoding='utf-8'))
    removed=[];kept=0
    for item in data.get('products',[]):
        live=[]
        for listing in item.get('listings') or []:
            key=(item.get('id'),listing.get('store'))
            allowed=(key not in DENYLIST and listing.get('live_verified') is True)
            if allowed:
                live.append(listing);kept+=1
            else:
                removed.append({
                    'product':item.get('name'),
                    'store':listing.get('store'),
                    'status':'denylisted' if key in DENYLIST else listing.get('scan_status'),
                    'price_verified':bool(listing.get('price_verified')),
                    'stock_verified':bool(listing.get('stock_verified')),
                    'url':listing.get('url')
                })
        item['listings']=live
    data['products']=[p for p in data.get('products',[]) if p.get('listings')]
    data.setdefault('scan_summary',{})['strict_live_qa']={
        'live_listings':kept,
        'hidden_unverified_listings':len(removed),
        'hidden':removed[:120],
        'rule':'main catalogue requires direct product match + current verified price + current in-stock evidence; confirmed dead listings are denylisted'
    }
    CAT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Strict live QA: {kept} live listings; {len(removed)} unverified/dead listings hidden')
    for x in removed:print('HIDDEN:',x['product'],'/',x['store'],x['status'])
if __name__=='__main__':main()

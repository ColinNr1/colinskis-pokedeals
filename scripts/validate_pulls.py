#!/usr/bin/env python3
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

ROOT=Path(__file__).resolve().parents[1]
PULLS=ROOT/'data'/'pulls.json'
TIMEOUT=20

def check_image(url):
    try:
        r=requests.get(url,timeout=TIMEOUT,stream=True,headers={'User-Agent':'ColinskisPokeDeals/2.0'})
        ctype=(r.headers.get('content-type') or '').lower()
        return r.status_code==200 and ctype.startswith('image/')
    except Exception:
        return False

def main():
    data=json.loads(PULLS.read_text(encoding='utf-8'))
    problems=[]; images=[]; total=0
    for set_name,item in data.get('sets',{}).items():
        cards=item.get('topCards') or []
        if not 1<=len(cards)<=5:problems.append(f'{set_name}: invalid coverage {len(cards)}')
        prices=[c.get('price7d') for c in cards]
        if any(not isinstance(p,(int,float)) or p<=0 for p in prices):problems.append(f'{set_name}: invalid price')
        if prices!=sorted(prices,reverse=True):problems.append(f'{set_name}: cards not sorted by price')
        ids=[c.get('tcgdex_id') for c in cards]
        if len(ids)!=len(set(ids)):problems.append(f'{set_name}: duplicate card id')
        for idx,c in enumerate(cards,1):
            total+=1
            if c.get('rank')!=idx:problems.append(f'{set_name}: rank mismatch at {idx}')
            if c.get('set_name') and c.get('set_name')!=set_name:problems.append(f"{set_name}: card set mismatch {c.get('set_name')}")
            img=c.get('img') or ''
            if not img.startswith('https://assets.tcgdex.net/') or not img.endswith('/high.webp'):
                problems.append(f'{set_name}: non-exact image URL for {c.get("card")}')
            else:images.append((set_name,c.get('card'),img))
        if cards and abs(item.get('price7d',0)-cards[0]['price7d'])>.001:problems.append(f'{set_name}: best pull summary mismatch')
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs={ex.submit(check_image,u):(s,c,u) for s,c,u in images}
        for fut in as_completed(futs):
            s,c,u=futs[fut]
            if not fut.result():problems.append(f'{s}: image failed for {c}: {u}')
    if problems:
        print('\n'.join('ERROR: '+p for p in problems))
        raise SystemExit(f'Pull validation failed with {len(problems)} problem(s)')
    print(f'Pull validation OK: {len(data.get("sets",{}))} sets, {total} ranked cards, {len(images)} exact images reachable')

if __name__=='__main__':main()

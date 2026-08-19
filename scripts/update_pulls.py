#!/usr/bin/env python3
import json, re, unicodedata
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus
import requests

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'data'/'catalog.json'
PULLS=ROOT/'data'/'pulls.json'
BASE='https://api.tcgdex.net/v2/en'
TIMEOUT=25
WORKERS=16
session=requests.Session()
session.headers.update({'User-Agent':'ColinskisPokeDeals/2.0','Accept':'application/json'})

# Products whose set field represents a booster expansion.
PACK_TYPES={
    'Booster Pack','Sleeved Booster','Half Booster Box','Booster Box','Booster Bundle',
    'Elite Trainer Box','3-Pack Blister','Checklane Blister','Blister'
}

ALIASES={
    # Kept explicit only where catalogue naming may differ from TCGdex naming.
    'Shrouded Fable':'Shrouded Fable',
    'Journey Together':'Journey Together',
    'Destined Rivals':'Destined Rivals',
    'Astral Radiance':'Astral Radiance',
    'Lost Origin':'Lost Origin',
    'Phantasmal Flames':'Phantasmal Flames',
    'Perfect Order':'Perfect Order',
    'Chaos Rising':'Chaos Rising',
    'Pitch Black':'Pitch Black',
    'Ascended Heroes':'Ascended Heroes',
}

def norm(s):
    s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower()
    s=s.replace('mega evolution',' ')
    return re.sub(r'[^a-z0-9]+',' ',s).strip()

def get_json(url):
    r=session.get(url,timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def image_url(base):
    if not base:return None
    return base.rstrip('/')+'/high.webp'

def cardmarket_avg7(card):
    cm=((card.get('pricing') or {}).get('cardmarket') or {})
    variants=card.get('variants') or {}
    normal=bool(variants.get('normal'))
    holo=bool(variants.get('holo'))
    # Use the price for the printing that actually exists. For holo-only chase cards,
    # holo AVG7 is the correct comparison; otherwise standard AVG7 is preferred.
    keys=['avg7-holo','avg7'] if holo and not normal else ['avg7','avg7-holo']
    for key in keys:
        v=cm.get(key)
        if isinstance(v,(int,float)) and v>0:
            return round(float(v),2),key,cm.get('updated')
    return None,None,cm.get('updated')

def fetch_card(card_id):
    try:
        c=get_json(f'{BASE}/cards/{card_id}')
        price,field,updated=cardmarket_avg7(c)
        if price is None:return None
        img=image_url(c.get('image'))
        if not img:return None
        set_obj=c.get('set') or {}
        return {
            'tcgdex_id':c.get('id'),
            'card':c.get('name'),
            'number':str(c.get('localId')),
            'rarity':c.get('rarity') or 'Unknown rarity',
            'price7d':price,
            'price_field':field,
            'pricing_updated':updated,
            'img':img,
            'set_id':set_obj.get('id'),
            'set_name':set_obj.get('name'),
            'url':'https://www.cardmarket.com/en/Pokemon/Products/Search?searchString='+quote_plus(f"{c.get('name','')} {c.get('localId','')}"),
            'data_source':f'{BASE}/cards/{card_id}'
        }
    except Exception as e:
        return {'_error':f'{card_id}: {e}'}

def find_set(set_name,sets):
    wanted=norm(ALIASES.get(set_name,set_name))
    exact=[s for s in sets if norm(s.get('name'))==wanted]
    if len(exact)==1:return exact[0]
    # Conservative fallback: require every significant token and choose unique match.
    toks=[t for t in wanted.split() if len(t)>2]
    matches=[s for s in sets if all(t in norm(s.get('name')) for t in toks)]
    return matches[0] if len(matches)==1 else None

def tracked_sets():
    cat=json.loads(CATALOG.read_text(encoding='utf-8'))
    names=[]
    for p in cat.get('products',[]):
        if p.get('type') in PACK_TYPES and p.get('set'):
            names.append(p['set'])
    # Preserve already tracked sets too, so useful older sets do not vanish just because
    # one local product temporarily sells out.
    if PULLS.exists():
        try:names += list(json.loads(PULLS.read_text(encoding='utf-8')).get('sets',{}).keys())
        except Exception:pass
    return sorted(set(names))

def rebuild_set(set_name,set_brief):
    full=get_json(f"{BASE}/sets/{set_brief['id']}")
    briefs=full.get('cards') or []
    rows=[]; errors=[]
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures={ex.submit(fetch_card,c['id']):c['id'] for c in briefs if c.get('id')}
        for fut in as_completed(futures):
            row=fut.result()
            if not row:continue
            if row.get('_error'):errors.append(row['_error']);continue
            # Reject cross-set mismatches absolutely.
            if row.get('set_id')!=set_brief['id']:continue
            rows.append(row)
    rows.sort(key=lambda x:x['price7d'],reverse=True)
    top=rows[:5]
    for i,c in enumerate(top,1):c['rank']=i
    if not top:
        return None,errors
    best=top[0]
    return {
        'card':best['card'],'number':best['number'],'rarity':best['rarity'],
        'price7d':best['price7d'],'url':best['url'],'img':best['img'],
        'topCards':top,'coverage':len(top),'set_id':set_brief['id'],
        'price_source':'TCGdex Cardmarket AVG7','image_source':'TCGdex exact card asset',
        'pricing_updated':best.get('pricing_updated'),'scan_status':'ok'
    },errors

def main():
    now=datetime.now(timezone.utc).isoformat(timespec='seconds')
    sets=get_json(f'{BASE}/sets')
    wanted=tracked_sets()
    result={'generated_at':now,'method':'Top pulls rebuilt from exact TCGdex card IDs. Prices use Cardmarket AVG7 from each exact card response; images use the exact TCGdex card asset.','sets':{},'unmatched_sets':[],'errors':[]}
    for name in wanted:
        s=find_set(name,sets)
        if not s:
            result['unmatched_sets'].append(name);continue
        try:
            item,errs=rebuild_set(name,s)
            if item:result['sets'][name]=item
            else:result['unmatched_sets'].append(name)
            result['errors'] += errs[:10]
            print(f"{name}: {item['coverage'] if item else 0} ranked pulls")
        except Exception as e:
            result['errors'].append(f'{name}: {e}')
            result['unmatched_sets'].append(name)
    PULLS.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Rebuilt {len(result['sets'])} sets; unmatched={len(result['unmatched_sets'])}; errors={len(result['errors'])}")
    if not result['sets']:
        raise SystemExit('No pull sets rebuilt')

if __name__=='__main__':main()

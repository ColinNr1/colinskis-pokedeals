#!/usr/bin/env python3
"""Enrich Top Pulls with PriceCharting raw/graded values.

Preferred production path: official PriceCharting Prices API when PRICECHARTING_TOKEN
is configured as a GitHub Actions secret. The token is never written to output.
Without a token, existing PriceCharting values are preserved and cards are marked
pending_api instead of scraping or inventing prices.
"""
import json, os, re, time
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote_plus
import requests

ROOT=Path(__file__).resolve().parents[1]
PULLS=ROOT/'data'/'pulls.json'
TOKEN=os.getenv('PRICECHARTING_TOKEN','').strip()
S=requests.Session(); S.headers.update({'User-Agent':'ColinskisPokeDeals/PriceCharting-1.0','Accept':'application/json'})

def dollars(v):
    return round(v/100,2) if isinstance(v,(int,float)) and v>0 else None

def clean_number(n):
    return re.sub(r'[^A-Za-z0-9-]','',str(n or ''))

def query(card,set_name):
    return f"{card.get('card','')} #{clean_number(card.get('number'))} Pokemon {set_name}".strip()

def api_product(q):
    r=S.get('https://www.pricecharting.com/api/product',params={'t':TOKEN,'q':q},timeout=25)
    r.raise_for_status(); data=r.json()
    if data.get('status')!='success': raise RuntimeError(data.get('error-message','PriceCharting API error'))
    return data

def plausible(pc,card,set_name):
    pn=(pc.get('product-name') or '').lower(); cn=(card.get('card') or '').lower()
    num=clean_number(card.get('number')).lower()
    if cn and cn not in pn:return False
    if num and ('#'+num not in pn and re.search(rf'\b{re.escape(num)}\b',pn) is None):return False
    console=(pc.get('console-name') or '').lower()
    # Set names normally appear in console-name for Pokemon card guides. Keep this
    # conservative; ambiguous matches are rejected rather than silently accepted.
    toks=[x for x in re.sub(r'[^a-z0-9 ]',' ',set_name.lower()).split() if len(x)>3]
    if toks and console and not all(t in console for t in toks):return False
    return True

def enrich(card,set_name):
    old=card.get('pricecharting') if isinstance(card.get('pricecharting'),dict) else {}
    q=query(card,set_name)
    if not TOKEN:
        card['pricecharting']={**old,'status':'pending_api','query':q,'search_url':'https://www.pricecharting.com/search-products?q='+quote_plus(q)+'&type=prices'}
        return False
    pc=api_product(q)
    if not plausible(pc,card,set_name):
        card['pricecharting']={**old,'status':'unmatched','query':q,'search_url':'https://www.pricecharting.com/search-products?q='+quote_plus(q)+'&type=prices'}
        return False
    card['pricecharting']={
      'status':'ok','id':str(pc.get('id')),'product_name':pc.get('product-name'),'set_name':pc.get('console-name'),
      'currency':'USD','ungraded':dollars(pc.get('loose-price')),'grade7':dollars(pc.get('cib-price')),
      'grade8':dollars(pc.get('new-price')),'grade9':dollars(pc.get('graded-price')),
      'grade9_5':dollars(pc.get('box-only-price')),'psa10':dollars(pc.get('manual-only-price')),
      'bgs10':dollars(pc.get('bgs-10-price')),'cgc10':dollars(pc.get('condition-17-price')),
      'sgc10':dollars(pc.get('condition-18-price')),'sales_volume_year':pc.get('sales-volume'),
      'url':'https://www.pricecharting.com/search-products?q='+quote_plus(q)+'&type=prices',
      'source':'PriceCharting Prices API','updated_at':datetime.now(timezone.utc).isoformat(timespec='seconds')
    }
    return True

def main():
    data=json.loads(PULLS.read_text(encoding='utf-8')); ok=0; pending=0; errors=[]
    for set_name,s in data.get('sets',{}).items():
        cards=s.get('topCards') or []
        for card in cards:
            try:
                if enrich(card,set_name):ok+=1
                else:pending+=1
            except Exception as e:
                card['pricecharting']={'status':'error','query':query(card,set_name),'error':str(e)[:180]};errors.append(f"{set_name} / {card.get('card')}: {e}")
            if TOKEN:time.sleep(1.05) # official API limit: max 1 request/second
        if cards:
            # Mirror best-card PriceCharting block for compact consumers.
            s['pricecharting']=cards[0].get('pricecharting',{})
    data['pricecharting']={'source':'PriceCharting','api_enabled':bool(TOKEN),'enriched_cards':ok,'pending_or_unmatched':pending,'errors':errors[:20],'currency':'USD','note':'Raw and graded card values. Cardmarket remains the sealed-product benchmark.'}
    PULLS.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'PriceCharting: enriched={ok}, pending/unmatched={pending}, errors={len(errors)}, api={bool(TOKEN)}')
if __name__=='__main__':main()

#!/usr/bin/env python3
import json, re
from pathlib import Path
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
PULLS=ROOT/'data'/'pulls.json'
TIMEOUT=25
session=requests.Session()
session.headers.update({
    'User-Agent':'ColinskisPokeDeals/1.1 (+GitHub Pages pull-price monitor)',
    'Accept-Language':'en-GB,en;q=0.9'
})

def parse_eur(raw):
    s=raw.strip().replace('\xa0','').replace('€','').replace(' ','')
    if ',' in s:
        s=s.replace('.','').replace(',','.')
    elif s.count('.')>1:
        parts=s.split('.')
        s=''.join(parts[:-1])+'.'+parts[-1]
    return float(s)

def fetch_7d(url):
    r=session.get(url,timeout=TIMEOUT,allow_redirects=True)
    r.raise_for_status()
    text=' '.join(BeautifulSoup(r.text,'html.parser').stripped_strings)
    for pat in (
        r'7-days average price\s*([0-9][0-9.,]*)\s*€',
        r'7-day average price\s*([0-9][0-9.,]*)\s*€',
        r'7-Tages-Durchschnitt\s*([0-9][0-9.,]*)\s*€'
    ):
        m=re.search(pat,text,re.I)
        if m:
            return parse_eur(m.group(1))
    raise ValueError('7-day average not found')

def check_card(set_name,card,changes):
    old=float(card.get('price7d') or 0)
    try:
        new=round(fetch_7d(card['url']),2)
        if old and not (old*.30 <= new <= old*3.0):
            raise ValueError(f'suspicious value {new}')
        card['last_checked']=datetime.now(timezone.utc).isoformat(timespec='seconds')
        card['scan_status']='ok'
        card.pop('scan_error',None)
        if old != new:
            changes.append(f"{set_name} / {card.get('card')}: €{old:.2f} -> €{new:.2f}")
            card['price7d']=new
    except Exception as e:
        card['last_checked']=datetime.now(timezone.utc).isoformat(timespec='seconds')
        card['scan_status']='blocked' if '403' in str(e) else 'error'
        card['scan_error']=str(e)[:180]

def main():
    data=json.loads(PULLS.read_text(encoding='utf-8'))
    changes=[]
    checked=0
    for set_name,item in data.get('sets',{}).items():
        cards=item.get('topCards') or [item]
        for card in cards:
            check_card(set_name,card,changes)
            checked+=1
        if cards:
            best=cards[0]
            for k in ('card','number','rarity','price7d','url','img','last_checked','scan_status','scan_error'):
                if k in best:
                    item[k]=best[k]
            item['coverage']=len(cards)
    data['generated_at']=datetime.now(timezone.utc).isoformat(timespec='seconds')
    data['changes']=changes[:100]
    PULLS.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Checked {checked} chase cards; {len(changes)} price changes')
    if any((c.get('scan_status')=='blocked') for item in data.get('sets',{}).values() for c in (item.get('topCards') or [item])):
        print('Cardmarket blocked one or more direct requests; previous verified prices were preserved.')

if __name__=='__main__':
    main()

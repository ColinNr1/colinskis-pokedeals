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
    'User-Agent':'ColinskisPokeDeals/1.0 (+GitHub Pages pull-price monitor)',
    'Accept-Language':'en-GB,en;q=0.9'
})

def parse_eur(raw):
    s=raw.strip().replace('\xa0','').replace('€','').replace(' ','')
    if ',' in s:
        s=s.replace('.','').replace(',','.')
    else:
        parts=s.split('.')
        if len(parts)>2:
            s=''.join(parts[:-1])+'.'+parts[-1]
    return float(s)

def fetch_7d(url):
    r=session.get(url,timeout=TIMEOUT,allow_redirects=True)
    r.raise_for_status()
    text=' '.join(BeautifulSoup(r.text,'html.parser').stripped_strings)
    patterns=[
        r'7-days average price\s*([0-9][0-9.,]*)\s*€',
        r'7-day average price\s*([0-9][0-9.,]*)\s*€',
        r'7-Tages-Durchschnitt\s*([0-9][0-9.,]*)\s*€'
    ]
    for pat in patterns:
        m=re.search(pat,text,re.I)
        if m:
            return parse_eur(m.group(1))
    raise ValueError('7-day average not found')

def main():
    data=json.loads(PULLS.read_text(encoding='utf-8'))
    changes=[]
    for set_name,item in data.get('sets',{}).items():
        old=float(item.get('price7d') or 0)
        try:
            new=round(fetch_7d(item['url']),2)
            if old and not (old*.30 <= new <= old*3.0):
                raise ValueError(f'suspicious value {new}')
            item['last_checked']=datetime.now(timezone.utc).isoformat(timespec='seconds')
            item['scan_status']='ok'
            item.pop('scan_error',None)
            if old != new:
                changes.append(f'{set_name}: €{old:.2f} -> €{new:.2f}')
                item['price7d']=new
        except Exception as e:
            item['last_checked']=datetime.now(timezone.utc).isoformat(timespec='seconds')
            item['scan_status']='error'
            item['scan_error']=str(e)[:180]
    data['generated_at']=datetime.now(timezone.utc).isoformat(timespec='seconds')
    data['changes']=changes[:100]
    PULLS.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Checked {len(data.get("sets",{}))} chase cards; {len(changes)} price changes')
    for c in changes: print('-',c)

if __name__=='__main__':
    main()

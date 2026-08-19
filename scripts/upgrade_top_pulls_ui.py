#!/usr/bin/env python3
from pathlib import Path
import re

p=Path(__file__).resolve().parents[1]/'index.html'
s=p.read_text(encoding='utf-8')
if 'class="pulls-list"' in s:
    print('Top Pulls UI already installed')
    raise SystemExit(0)

old_css=re.search(r'\.pullbox\{.*?\.pullbox a\{.*?\}',s,re.S)
if not old_css:
    raise SystemExit('pullbox CSS block not found')
new_css=""".pullbox{margin-top:10px;border:1px solid #6a5524;background:linear-gradient(135deg,#2a2413,#171a24);border-radius:12px;padding:10px;display:grid;grid-template-columns:54px 1fr auto;gap:10px;align-items:center}.pullbox>img{width:54px;height:72px;object-fit:contain;border-radius:7px;background:#f5f5f5}.pullbox .plabel{font-size:8px;color:#f3cf69;text-transform:uppercase;font-weight:900;letter-spacing:.08em}.pullbox .pname{font-size:11px;font-weight:850;margin-top:2px}.pullbox .pmeta{font-size:8px;color:#9aa9bd;margin-top:3px}.pullbox .pvalue{text-align:right}.pullbox .pvalue b{display:block;font-size:18px;color:#ffd84a}.pullbox .pvalue span{font-size:7px;color:#8fa0b6;text-transform:uppercase}.pullbox>a{grid-column:1/-1;background:#3b3016;border:1px solid #69551f;color:#f2d67b;padding:7px 9px;border-radius:8px;text-align:center;font-size:8px;font-weight:900}.pulls-list{grid-column:1/-1;margin-top:0!important;border-color:#59491f!important}.pulls-list summary{background:#211d12!important;color:#f3d475}.pullrows{padding:4px}.pullrow{display:grid;grid-template-columns:24px 40px 1fr auto;gap:8px;align-items:center;padding:7px 6px;border-bottom:1px solid #41371e}.pullrow:last-child{border-bottom:0}.pullrank{width:24px;height:24px;border-radius:50%;background:#283347;color:#c4d1e2;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:900}.pullrow:first-child .pullrank{background:#59440f;color:#ffd84a}.pullthumb{width:40px;height:54px;object-fit:contain;background:#f5f5f5;border-radius:5px}.pullinfo b{display:block;font-size:9px}.pullinfo span{display:block;font-size:7px;color:#8fa0b6;margin-top:2px}.pullprice{text-align:right}.pullprice b{display:block;color:#f6d56d;font-size:11px}.pullprice a{display:block;color:#82b8ff;font-size:7px;margin-top:2px}"""
s=s[:old_css.start()]+new_css+s[old_css.end():]

old_fn=re.search(r'function pullBox\(p\)\{.*?\n\}',s,re.S)
if not old_fn:
    raise SystemExit('pullBox function not found')
new_fn=r'''function pullBox(p){
 const x=pulls[p.set];
 if(!x||!pullEligible(p))return '';
 const cards=(x.topCards&&x.topCards.length)?x.topCards:[x];
 const best=cards[0];
 const multiple=minPrice(p)>0?best.price7d/minPrice(p):null;
 const rows=cards.map((c,i)=>`<div class="pullrow"><div class="pullrank">#${c.rank||i+1}</div><img class="pullthumb" src="${c.img||best.img}" alt="${c.card}" loading="lazy" onerror="this.style.opacity=.15"><div class="pullinfo"><b>${c.card}</b><span>${c.number||''} • ${c.rarity||'Chase card'}</span></div><div class="pullprice"><b>€${Number(c.price7d).toFixed(2)}</b><a href="${c.url}" target="_blank">Cardmarket ↗</a></div></div>`).join('');
 return `<div class="pullbox">
   <img src="${best.img}" alt="${best.card}" loading="lazy" onerror="this.style.display='none'">
   <div><div class="plabel">🏆 Best possible pull</div><div class="pname">${best.card}</div><div class="pmeta">${best.number} • ${best.rarity||'Chase card'}${multiple?` • ${multiple.toFixed(1)}× product price`:''}</div></div>
   <div class="pvalue"><span>Cardmarket 7d</span><b>€${Number(best.price7d).toFixed(2)}</b></div>
   <details class="pulls-list"><summary><span>View Top Pulls</span><span>${cards.length} card${cards.length!==1?'s':''} ▾</span></summary><div class="pullrows">${rows}</div></details>
   <a href="${best.url}" target="_blank">View #1 chase on Cardmarket ↗</a>
 </div>`;
}'''
s=s[:old_fn.start()]+new_fn+s[old_fn.end():]
s=s.replace('Best Pull layer</b><span>Top chase + 7d value','Top Pulls layer</b><span>Ranked chase cards + 7d values')
p.write_text(s,encoding='utf-8')
print('Top Pulls UI installed')

#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'index.html'
s = INDEX.read_text(encoding='utf-8')

MARKER = '/* TOP_PULLS_V2 */'
if MARKER not in s:
    extra_css = r'''
<style>
/* TOP_PULLS_V2 */
.pulls-list{grid-column:1/-1;margin-top:0!important;border-color:#59491f!important}
.pulls-list summary{background:#211d12!important;color:#f3d475}
.pullrows{padding:4px}
.pullrow{display:grid;grid-template-columns:24px 40px 1fr auto;gap:8px;align-items:center;padding:7px 6px;border-bottom:1px solid #41371e}
.pullrow:last-child{border-bottom:0}
.pullrank{width:24px;height:24px;border-radius:50%;background:#283347;color:#c4d1e2;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:900}
.pullrow:first-child .pullrank{background:#59440f;color:#ffd84a}
.pullthumb{width:40px!important;height:54px!important;object-fit:contain;background:#f5f5f5;border-radius:5px}
.pullinfo b{display:block;font-size:9px}.pullinfo span{display:block;font-size:7px;color:#8fa0b6;margin-top:2px}
.pullprice{text-align:right}.pullprice b{display:block;color:#f6d56d;font-size:11px}.pullprice a{display:block!important;background:transparent!important;border:0!important;padding:0!important;color:#82b8ff!important;font-size:7px!important;margin-top:2px!important;text-align:right!important}
</style>
'''
    s = s.replace('</head>', extra_css + '</head>', 1)

new_fn = r'''function pullBox(p){const x=pulls[p.set];if(!x||!pullEligible(p))return '';const cards=(x.topCards&&x.topCards.length)?x.topCards:[x];const best=cards[0];const multiple=minPrice(p)>0?best.price7d/minPrice(p):null;const rows=cards.map((c,i)=>`<div class="pullrow"><div class="pullrank">#${c.rank||i+1}</div><img class="pullthumb" src="${c.img||best.img}" alt="${c.card}" loading="lazy" onerror="this.style.opacity=.15"><div class="pullinfo"><b>${c.card}</b><span>${c.number||''} • ${c.rarity||'Chase card'}</span></div><div class="pullprice"><b>€${Number(c.price7d).toFixed(2)}</b><a href="${c.url}" target="_blank">Cardmarket ↗</a></div></div>`).join('');return `<div class="pullbox"><img src="${best.img}" alt="${best.card}" loading="lazy" onerror="this.style.display='none'"><div><div class="plabel">🏆 Best possible pull</div><div class="pname">${best.card}</div><div class="pmeta">${best.number} • ${best.rarity||'Chase card'}${multiple?` • ${multiple.toFixed(1)}× product price`:''}</div></div><div class="pvalue"><span>Cardmarket 7d</span><b>€${Number(best.price7d).toFixed(2)}</b></div><details class="pulls-list"><summary><span>View Top Pulls</span><span>${cards.length} cards ▾</span></summary><div class="pullrows">${rows}</div></details><a href="${best.url}" target="_blank">View #1 chase on Cardmarket ↗</a></div>`;}'''

pattern = r'function pullBox\(p\)\{.*?\}\n?function card\(p\)'
m = re.search(pattern, s, re.S)
if not m:
    raise SystemExit('Current pullBox function not found; refusing to modify index.html')
s = s[:m.start()] + new_fn + '\nfunction card(p)' + s[m.end():]
s = s.replace('<b>Best Pull layer</b><span>Top chase + 7d value</span>', '<b>Verified Top Pulls</b><span>Exact cards + Cardmarket AVG7</span>')
INDEX.write_text(s, encoding='utf-8')
print('Verified Top Pulls V2 UI installed/confirmed')

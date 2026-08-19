#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'index.html'
s=p.read_text(encoding='utf-8');changed=False
if 'budget.css' not in s:
    s=s.replace('</head>','<link rel="stylesheet" href="budget.css?v=3">\n</head>');changed=True
else:
    ns=s.replace('budget.css?v=1','budget.css?v=3').replace('budget.css?v=2','budget.css?v=3')
    if ns!=s:s=ns;changed=True
if 'budget.js' not in s:
    s=s.replace('</body>','<script src="budget.js?v=3"></script>\n</body>');changed=True
else:
    ns=s.replace('budget.js?v=1','budget.js?v=3').replace('budget.js?v=2','budget.js?v=3')
    if ns!=s:s=ns;changed=True
needle="arr=accessories;const q=document.getElementById('search').value.toLowerCase().trim(),v=document.getElementById('vendorFilter').value;"
replacement="arr=accessories.filter(a=>a.direct_product_url===true && !/bing\\.net/i.test(a.img||'') && /\\/product(?:-page)?\\/|\\/products\\//i.test(a.url||''));const q=document.getElementById('search').value.toLowerCase().trim(),v=document.getElementById('vendorFilter').value;"
if needle in s:s=s.replace(needle,replacement);changed=True
if changed:p.write_text(s,encoding='utf-8')
print('Budget Allocator V3 installed' if changed else 'Budget Allocator V3 already installed')

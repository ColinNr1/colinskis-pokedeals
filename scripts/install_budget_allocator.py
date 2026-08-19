#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'index.html'
s=p.read_text(encoding='utf-8')
changed=False
if 'budget.css' not in s:
    s=s.replace('</head>','<link rel="stylesheet" href="budget.css?v=1">\n</head>');changed=True
if 'budget.js' not in s:
    s=s.replace('</body>','<script src="budget.js?v=1"></script>\n</body>');changed=True
if changed:p.write_text(s,encoding='utf-8')
print('Budget Allocator assets installed' if changed else 'Budget Allocator already installed')
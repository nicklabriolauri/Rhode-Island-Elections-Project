#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TAG='<script src="supplemental-2026.js?v=20260910"></script>'
for name in ['index.html','running.html','ballot.html']:
    p=ROOT/name
    text=p.read_text()
    if 'supplemental-2026.js' not in text:
        text=text.replace('</body>',f'  {TAG}\n</body>')
        p.write_text(text)
        print('patched',name)
    else:
        print('already patched',name)

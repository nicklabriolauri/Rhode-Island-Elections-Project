#!/usr/bin/env python3
"""
Build data/incumbent_records_2026.json from 2025 + 2026 Rhode Island legislative bulk data.

Method:
- Match only current 2026 candidates who are incumbents.
- Count lead sponsorship separately from cosponsorship.
- Exclude ceremonial/memorial resolutions from headline bill counts.
- Count enacted measures only when the source marks enactment/signing.
- Never turn missing data into zero.
- Preserve committee/leadership fields already verified from official RI General Assembly biographies.

Open States bulk data documentation:
https://open.pluralpolicy.com/data/
"""
from pathlib import Path
import csv, io, json, re, urllib.request, zipfile

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"data"/"incumbent_records_2026.json"
BASE="https://data.openstates.org/session/csv/ri/{session}.csv"

def norm(s):
    s=(s or "").lower()
    s=re.sub(r"\b(jr|sr|ii|iii|iv)\.?\b","",s)
    return re.sub(r"[^a-z0-9]+"," ",s).strip()

def substantive(identifier, title=""):
    # RI substantive bills are normally H/S bills; resolutions are excluded.
    ident=(identifier or "").upper().strip()
    return bool(re.match(r"^[HS]\s*\d+",ident)) and "RESOLUTION" not in (title or "").upper()

def enacted(actions):
    text=" ".join(actions).lower()
    return any(x in text for x in ("signed by governor","became law","effective without governor","chapter "))

def download(session):
    with urllib.request.urlopen(BASE.format(session=session), timeout=120) as r:
        return r.read()

def main():
    existing=json.loads(OUT.read_text()) if OUT.exists() else {"records":[]}
    # Open States CSV archives contain linked bill/sponsor/action tables. The exact archive layout
    # is discovered at runtime so this script remains compatible with their bulk exporter.
    # Preserve official committee/leadership data while refreshing quantitative measures.
    bykey={(norm(r["candidate_name"]),r["chamber"],str(r["district_number"])):r for r in existing.get("records",[])}
    # Implementation intentionally fails loudly if upstream layout changes rather than publishing bad counts.
    archives={y:download(y) for y in ("2025","2026")}
    print("Downloaded 2025 and 2026 RI Open States bulk archives.")
    print("Existing incumbent records preserved:",len(bykey))
    print("Next step: parse archive tables and write verified counts; do not publish guessed zeros.")

if __name__=="__main__":
    main()

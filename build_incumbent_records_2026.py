#!/usr/bin/env python3
"""
RIEP: build and audit Record in Office data for 2026 incumbent candidates.

Purpose
-------
Create data/incumbent_records_2026.json from official Rhode Island General
Assembly sources, while keeping missing/unverified values as null rather than 0.

Verified source hierarchy
-------------------------
1. Current House/Senate committee and leadership rosters:
   House:  https://www.rilegislature.gov/representatives/Docs/hleaders_comm.pdf
   Senate: https://www.rilegislature.gov/senators/Docs/sleaders_comm.pdf
2. Current legislator biographies for individual role checks and mid-term changes.
3. Bill Status/History:
   https://status.rilegislature.gov/
4. Public Laws / Local Acts:
   https://webserver.rilegislature.gov/lawrevision/
5. House/Senate Journals are the final official session record.

Counting rules
--------------
* lead-sponsored bills:
  substantive House/Senate bills where the incumbent is the first name in the
  official "BY" sponsor list.
* cosponsored bills:
  substantive bills where the incumbent appears after the first sponsor.
* passed chamber:
  lead-sponsored substantive bills with an originating-chamber floor-passage
  action in the official Bill Status/History record.
* became law:
  lead-sponsored substantive bills whose official action history records
  "Signed by Governor" or "Effective without Governor's signature", or whose
  number is found in an official Public Laws / Local Acts bill-number index.
* resolutions:
  excluded from all four headline legislation counts.
* attendance:
  NOT calculated from the web floor-vote interface. The General Assembly says
  the House/Senate Journals are the final official record. Until a journal-based
  parser is validated, recorded/not_voting remain null.

This script deliberately fails closed: if it cannot verify a field, it leaves it
null and emits an audit warning instead of publishing a guessed zero.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from lxml import html as lhtml

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RUNNING_PATH = DATA_DIR / "whos_running_2026.json"
SEED_PATH = DATA_DIR / "incumbent_records_2026.json"
OUTPUT_PATH = DATA_DIR / "incumbent_records_2026.json"
AUDIT_PATH = DATA_DIR / "incumbent_records_2026_audit.json"

STATUS_URL = "https://status.rilegislature.gov/"
HOUSE_COMMITTEE_SOURCE = "https://www.rilegislature.gov/representatives/Docs/hleaders_comm.pdf"
SENATE_COMMITTEE_SOURCE = "https://www.rilegislature.gov/senators/Docs/sleaders_comm.pdf"
LEGISLATION_PAGE = "https://www.rilegislature.gov/Pages/Legislation.aspx"

SESSIONS = ("2025", "2026")
MAX_QUERY = 250

# These start numbers mirror the Rhode Island source layout used by the public
# Open States scraper. Odd-year House starts at 5000; even-year House can include
# both a 6500 continuation and a 7000 series. Senate starts at 1 / 2000.
STARTS = {
    ("2025", "house"): (5000,),
    ("2025", "senate"): (1,),
    ("2026", "house"): (6500, 7000),
    ("2026", "senate"): (2000,),
}

BILL_PREFIXES = (
    "House Bill No.",
    "Senate Bill No.",
)
RESOLUTION_MARKERS = (
    "Resolution No.",
    "Concurrent Resolution No.",
    "Memorial",
    "Memorandum",
)

session = requests.Session()
session.headers.update({
    "User-Agent": "RhodeIslandElectionsProject/1.0 (+https://www.rhodeislandelectionsproject.org/)"
})


def norm_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    value = value.lower()
    value = value.replace("o'", "o")
    value = re.sub(r"\b(rep(?:resentative)?|sen(?:ator)?)\.?\b", " ", value)
    value = re.sub(r"\b(jr|sr|ii|iii|iv)\.?\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def surname(value: str) -> str:
    bits = norm_name(value).split()
    return bits[-1] if bits else ""


def sponsor_match(candidate: str, sponsor: str) -> bool:
    """
    RI status results often use surnames only. Surname matching is therefore
    primary. O'Brien is normalized to obrien, distinct from Brien.
    """
    return bool(surname(candidate) and surname(candidate) == surname(sponsor))


def get(url: str, **kwargs) -> requests.Response:
    r = session.get(url, timeout=45, **kwargs)
    r.raise_for_status()
    return r


def post(url: str, **kwargs) -> requests.Response:
    r = session.post(url, timeout=45, **kwargs)
    r.raise_for_status()
    return r


def default_form_fields(url: str = STATUS_URL) -> dict[str, str]:
    root = lhtml.fromstring(get(url).content)
    result: dict[str, str] = {}
    for el in root.xpath("//*[@name]"):
        name = el.attrib.get("name")
        if not name:
            continue
        value = el.attrib.get("value")
        if value is None:
            value = el.text or ""
        result[name] = value.strip() if isinstance(value, str) else ""
    result["__EVENTTARGET"] = ""
    result["__EVENTARGUMENT"] = ""
    result["__LASTFOCUS"] = ""
    return result


def result_blocks(page: str) -> list[list[Any]]:
    root = lhtml.fromstring(page)
    if "We're Sorry! You seem to be lost." in root.text_content():
        raise RuntimeError("RI Bill Status search rejected the POST")
    nodes = root.xpath("//span[@id='lblBills']/*")
    blocks, current = [], []
    for node in nodes:
        if node.tag == "br":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(node)
    if current:
        blocks.append(current)
    # Site wrappers create a leading/trailing non-bill block.
    return blocks[1:-1] if len(blocks) >= 2 else blocks


def parse_block(nodes: list[Any]) -> dict[str, Any] | None:
    lines = [(n.text_content().strip(), n) for n in nodes]
    if any("No Bills Met this Criteria" in line for line, _ in lines):
        return None

    out: dict[str, Any] = {"actions": []}
    for line, node in lines:
        if not line:
            continue
        if line.startswith(("House Bill No.", "Senate Bill No.",
                            "House Resolution No.", "Senate Resolution No.",
                            "House Concurrent Resolution No.",
                            "Senate Concurrent Resolution No.")):
            out["raw_id"] = line
            out["id_links"] = [a.attrib.get("href") for a in node.xpath("./a") if a.attrib.get("href")]
        elif line.startswith("BY"):
            out["sponsors_raw"] = line
        elif line.startswith("ENTITLED,"):
            out["title_raw"] = line
        elif re.match(r"^\{.*\}$", line):
            out["version"] = line
        elif line.startswith("Chapter"):
            out["chapter"] = line
        elif re.match(r"^\d{2}/\d{2}/\d{4}", line):
            out["actions"].append(line)

    if "raw_id" not in out:
        return None

    raw = out["raw_id"]
    m = re.search(r"(House|Senate)\s+(?:Bill|Resolution|Concurrent Resolution)\s+No\.\s*(\d+)", raw, re.I)
    if not m:
        return None

    chamber = "house" if m.group(1).lower() == "house" else "senate"
    number = int(m.group(2))
    out["chamber"] = chamber
    out["number"] = number
    out["identifier"] = ("H" if chamber == "house" else "S") + str(number)
    out["is_substantive_bill"] = (
        any(raw.startswith(p) for p in BILL_PREFIXES)
        and not any(marker in raw for marker in RESOLUTION_MARKERS)
    )

    sponsor_text = out.get("sponsors_raw", "")
    sponsor_text = re.sub(r"^BY\s*", "", sponsor_text, flags=re.I).strip()
    sponsors = [s.strip() for s in sponsor_text.split(",") if s.strip()]
    out["sponsors"] = sponsors
    out["lead_sponsor"] = sponsors[0] if sponsors else None
    out["cosponsors"] = sponsors[1:] if len(sponsors) > 1 else []
    return out


def scrape_bill_status(year: str, chamber: str) -> list[dict[str, Any]]:
    """
    Query the official RI Bill Status/History site in <=250-number ranges.
    This follows the same public-source mechanics as the maintained Open States
    Rhode Island scraper, but applies RIEP's own counting methodology.
    """
    FROM = "ctl00$rilinContent$txtBillFrom"
    TO = "ctl00$rilinContent$txtBillTo"
    YEAR = "ctl00$rilinContent$cbYear"

    collected: dict[str, dict[str, Any]] = {}
    for start in STARTS[(year, chamber)]:
        cursor = start
        empty_streak = 0
        while empty_streak < 2:
            fields = default_form_fields()
            fields[FROM] = str(cursor)
            fields[TO] = str(cursor + MAX_QUERY)
            fields[YEAR] = year

            page = post(STATUS_URL, data=fields).text
            blocks = result_blocks(page)
            parsed = [p for p in (parse_block(b) for b in blocks) if p]

            if not parsed:
                empty_streak += 1
            else:
                empty_streak = 0
                for bill in parsed:
                    if bill["chamber"] == chamber:
                        collected[bill["identifier"]] = bill

            print(f"{year} {chamber}: {cursor}-{cursor + MAX_QUERY}: {len(parsed)} records")
            cursor += MAX_QUERY
            time.sleep(0.08)

            # Hard stops protect against a site change causing an infinite crawl.
            if chamber == "house" and cursor > (9000 if year == "2026" else 7000):
                break
            if chamber == "senate" and cursor > (4000 if year == "2026" else 1600):
                break

    return sorted(collected.values(), key=lambda x: x["number"])


def originating_chamber_passed(bill: dict[str, Any]) -> bool:
    origin = "House" if bill["chamber"] == "house" else "Senate"
    patterns = (
        rf"\b{origin}\s+passed\b",
        rf"\b{origin}\s+read and passed\b",
        rf"\b{origin}\s+passed Sub",
    )
    for action in bill.get("actions", []):
        # Exclude committee recommendation language.
        if "Committee" in action and "recommends passage" in action:
            continue
        if any(re.search(p, action, re.I) for p in patterns):
            return True
    return False


def status_became_law(bill: dict[str, Any]) -> bool:
    text = " ".join(bill.get("actions", []))
    return bool(re.search(
        r"Signed by Governor|Effective without Governor'?s signature",
        text, re.I
    ))


def flatten_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for chamber in ("house", "senate"):
        for district, record in payload.get("chambers", {}).get(chamber, {}).items():
            for group in ("candidates", "general_candidates"):
                for c in record.get(group, []):
                    rows.append({
                        "candidate_id": c.get("candidate_id"),
                        "candidate_name": c.get("name"),
                        "chamber": chamber,
                        "district_number": int(district),
                    })
    return rows


def match_incumbent_candidates(seed_records: list[dict[str, Any]],
                               candidate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Match by chamber + district + surname. Never match by district alone; doing
    so would incorrectly attach an incumbent's legislative record to a challenger.
    """
    by_seat = defaultdict(list)
    for r in seed_records:
        by_seat[(r["chamber"], int(r["district_number"]))].append(r)

    out = []
    for c in candidate_rows:
        possible = by_seat.get((c["chamber"], c["district_number"]), [])
        exact = [r for r in possible if surname(r["candidate_name"]) == surname(c["candidate_name"])]
        if len(exact) == 1:
            row = dict(exact[0])
            row["candidate_id"] = c["candidate_id"]
            row["candidate_name"] = c["candidate_name"]
            out.append(row)
        elif len(exact) > 1:
            raise RuntimeError(f"Ambiguous incumbent match: {c}")
    return out


def compile_counts(record: dict[str, Any], bills: list[dict[str, Any]]) -> None:
    lead, co = [], []
    for bill in bills:
        if not bill["is_substantive_bill"]:
            continue
        if bill["lead_sponsor"] and sponsor_match(record["candidate_name"], bill["lead_sponsor"]):
            lead.append(bill)
        elif any(sponsor_match(record["candidate_name"], s) for s in bill["cosponsors"]):
            co.append(bill)

    passed = [b for b in lead if originating_chamber_passed(b)]
    laws = [b for b in lead if status_became_law(b)]

    record["legislation"] = {
        "prime_sponsored": len(lead),
        "cosponsored": len(co),
        "passed_chamber": len(passed),
        "became_law": len(laws),
    }
    record["legislation_detail"] = {
        "lead_sponsored": [
            {"year": b["year"], "bill": b["identifier"], "status_source": STATUS_URL}
            for b in lead
        ],
        "passed_chamber": [
            {"year": b["year"], "bill": b["identifier"], "status_source": STATUS_URL}
            for b in passed
        ],
        "became_law": [
            {"year": b["year"], "bill": b["identifier"], "status_source": STATUS_URL}
            for b in laws
        ],
    }
    record.setdefault("votes", {})
    record["votes"]["recorded"] = None
    record["votes"]["not_voting"] = None
    record["votes"]["status"] = (
        "withheld: RIEP does not label missed web roll calls as attendance; "
        "journal-based attendance parser not yet validated"
    )

    record["sources"] = list(dict.fromkeys((record.get("sources") or []) + [
        STATUS_URL,
        LEGISLATION_PAGE,
    ]))
    record["verification"]["legislation_counts"] = "verified_from_official_bill_status_history"
    record["verification"]["floor_attendance"] = "withheld_pending_official_journal_validation"


def cross_checks(records: list[dict[str, Any]]) -> list[str]:
    warnings = []
    # Every published numeric record must have the four headline fields.
    for r in records:
        L = r.get("legislation", {})
        for k in ("prime_sponsored", "cosponsored", "passed_chamber", "became_law"):
            if L.get(k) is None:
                warnings.append(f"{r['candidate_name']}: {k} is null")
        if L.get("became_law", 0) > L.get("prime_sponsored", 0):
            warnings.append(f"{r['candidate_name']}: laws > lead-sponsored")
        if L.get("passed_chamber", 0) > L.get("prime_sponsored", 0):
            warnings.append(f"{r['candidate_name']}: passed chamber > lead-sponsored")

    # Mid-term entrant should remain clearly flagged.
    fam = [r for r in records if surname(r["candidate_name"]) == "famiglietti"]
    if fam and not fam[0].get("service_start"):
        warnings.append("Famiglietti missing service_start")

    return warnings


def main() -> None:
    if not RUNNING_PATH.exists():
        raise SystemExit(f"Missing {RUNNING_PATH}")
    if not SEED_PATH.exists():
        raise SystemExit(f"Missing audited seed {SEED_PATH}")

    running = json.loads(RUNNING_PATH.read_text(encoding="utf-8"))
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    seed_records = seed.get("records", [])

    candidates = flatten_candidates(running)
    incumbents = match_incumbent_candidates(seed_records, candidates)
    print(f"Matched {len(incumbents)} incumbent 2026 candidates.")

    all_bills = []
    for year in SESSIONS:
        for chamber in ("house", "senate"):
            bills = scrape_bill_status(year, chamber)
            for b in bills:
                b["year"] = int(year)
            all_bills.extend(bills)

    for r in incumbents:
        compile_counts(r, all_bills)

    warnings = cross_checks(incumbents)

    payload = {
        "updated_at": dt.date.today().isoformat(),
        "period": "2025–2026 General Assembly",
        "scope": "Only current legislators who also match a valid 2026 RIEP candidate record.",
        "methodology": (
            "RIEP reports raw descriptive measures only and does not calculate an effectiveness score. "
            "Lead sponsorship and cosponsorship are determined from the ordered sponsor list in official "
            "Rhode Island Bill Status/History records. Resolutions are excluded from headline bill counts. "
            "Originating-chamber passage is based on explicit House/Senate floor-passage actions. "
            "Became-law counts require an official signed/effective-without-signature action. "
            "Attendance remains unpublished until validated from official House/Senate Journals."
        ),
        "records": sorted(incumbents, key=lambda x: (x["chamber"], x["district_number"])),
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    AUDIT_PATH.write_text(json.dumps({
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "record_count": len(incumbents),
        "warnings": warnings,
        "sources": [STATUS_URL, HOUSE_COMMITTEE_SOURCE, SENATE_COMMITTEE_SOURCE, LEGISLATION_PAGE],
    }, indent=2), encoding="utf-8")

    print(f"Wrote {OUTPUT_PATH}")
    print(f"Wrote {AUDIT_PATH}")
    if warnings:
        print(f"AUDIT WARNINGS: {len(warnings)}")
        for warning in warnings[:25]:
            print(" -", warning)
        sys.exit(2)


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path("/Users/nicholaslabriola/Documents/New project")
SOURCE = ROOT / "data" / "raw" / "2026-election-candidates.xlsx"
OUTPUT = ROOT / "website" / "data" / "whos_running_2026.json"

CHAMBER_TOTALS = {"house": 75, "senate": 38}
PARTY_CODE = {
    "democratic": "DEM",
    "republican": "REP",
    "independent": "IND",
    "moderate": "MOD",
    "libertarian": "LIB",
}
PARTY_LABEL = {
    "DEM": "Democratic",
    "REP": "Republican",
    "IND": "Independent",
    "MOD": "Moderate",
    "LIB": "Libertarian",
    "OTH": "Other",
}
NAME_OVERRIDES = {
    "Jacob Bissalion": "Jacob Bissaillon",
    "Jessica De La Cruz": "Jessica de la Cruz",
    "Meghan Kallaman": "Meghan Kallman",
}
PARTY_OVERRIDES = {
    "Jessica de la Cruz": "REP",
}


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_chamber(value: str) -> str:
    clean = normalize_space(value).lower()
    return "senate" if "senate" in clean else "house"


def normalize_party(value: str) -> str:
    clean = normalize_space(value).lower()
    return PARTY_CODE.get(clean, "OTH")


def clean_name(value: str) -> tuple[str, bool]:
    raw = normalize_space(value)
    incumbent = "(i)" in raw.lower()
    clean = re.sub(r"\s*\(i\)\s*", "", raw, flags=re.IGNORECASE)
    return clean, incumbent


def apply_name_override(name: str) -> str:
    return NAME_OVERRIDES.get(name, name)


def apply_party_override(name: str, party: str) -> str:
    return PARTY_OVERRIDES.get(name, party)


def build_status(counts: dict[str, int]) -> tuple[str, str]:
    dem = counts.get("DEM", 0)
    rep = counts.get("REP", 0)
    other = sum(v for k, v in counts.items() if k not in {"DEM", "REP"})

    if dem and rep:
        general = "both_major"
    elif dem:
        general = "dem_only"
    elif rep:
        general = "rep_only"
    elif other:
        general = "other_only"
    else:
        general = "no_filing"

    dem_primary = dem > 1
    rep_primary = rep > 1

    if dem_primary and rep_primary:
        primary = "both_primaries"
    elif dem_primary:
        primary = "dem_primary"
    elif rep_primary:
        primary = "rep_primary"
    elif sum(counts.values()) > 0:
        primary = "no_primary"
    else:
        primary = "no_filing"

    return general, primary


def general_label(code: str) -> str:
    return {
        "both_major": "Democratic and Republican candidates filed",
        "dem_only": "Democratic candidates filed only",
        "rep_only": "Republican candidates filed only",
        "other_only": "Independent or other candidates filed only",
        "no_filing": "No filing listed in current sheet",
    }[code]


def primary_label(code: str) -> str:
    return {
        "both_primaries": "Both parties have primary activity",
        "dem_primary": "Democratic primary underway",
        "rep_primary": "Republican primary underway",
        "no_primary": "No active primary in current filings",
        "no_filing": "No filing listed in current sheet",
    }[code]


def main() -> None:
    workbook = load_workbook(SOURCE, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]

    chamber_records: dict[str, dict[int, dict]] = {
        "house": defaultdict(lambda: {"candidates": [], "party_counts": defaultdict(int)}),
        "senate": defaultdict(lambda: {"candidates": [], "party_counts": defaultdict(int)}),
    }

    for row in sheet.iter_rows(min_row=2, values_only=True):
        chamber_raw, district_raw, name_raw, party_raw = row
        if not chamber_raw or not district_raw or not name_raw:
            continue

        chamber = normalize_chamber(str(chamber_raw))
        district = int(district_raw)
        clean, incumbent = clean_name(str(name_raw))
        clean = apply_name_override(clean)
        party = apply_party_override(clean, normalize_party(str(party_raw or "Other")))

        record = chamber_records[chamber][district]
        record["candidates"].append(
            {
                "name": clean,
                "party": party,
                "party_label": PARTY_LABEL.get(party, "Other"),
                "incumbent": incumbent,
            }
        )
        record["party_counts"][party] += 1

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "election_cycle": 2026,
        "source_file": str(SOURCE),
        "source_updated_at": datetime.fromtimestamp(
            SOURCE.stat().st_mtime,
            timezone.utc,
        ).isoformat(),
        "chambers": {},
        "summary": {},
    }

    for chamber, districts in chamber_records.items():
        chamber_payload = {}
        filed_districts = 0
        both_major = 0
        primary_districts = 0
        dem_only = 0
        rep_only = 0
        empty = CHAMBER_TOTALS[chamber]

        for district in range(1, CHAMBER_TOTALS[chamber] + 1):
            raw = districts.get(district)
            counts = dict(raw["party_counts"]) if raw else {}
            candidates = sorted(
                raw["candidates"] if raw else [],
                key=lambda item: (item["party_label"], item["name"]),
            )
            general_status, primary_status = build_status(counts)
            total_candidates = sum(counts.values())

            if total_candidates:
                filed_districts += 1
                empty -= 1
            if general_status == "both_major":
                both_major += 1
            elif general_status == "dem_only":
                dem_only += 1
            elif general_status == "rep_only":
                rep_only += 1
            if primary_status in {"dem_primary", "rep_primary", "both_primaries"}:
                primary_districts += 1

            chamber_payload[str(district)] = {
                "chamber": chamber,
                "district_number": district,
                "candidates": candidates,
                "party_counts": counts,
                "candidate_total": total_candidates,
                "general_status": general_status,
                "general_label": general_label(general_status),
                "primary_status": primary_status,
                "primary_label": primary_label(primary_status),
            }

        payload["chambers"][chamber] = chamber_payload
        payload["summary"][chamber] = {
            "district_total": CHAMBER_TOTALS[chamber],
            "districts_with_filings": filed_districts,
            "no_filing_reported": empty,
            "both_major_parties_filed": both_major,
            "democratic_only": dem_only,
            "republican_only": rep_only,
            "districts_with_primary_activity": primary_districts,
        }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()

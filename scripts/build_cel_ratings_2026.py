#!/usr/bin/env python3
"""Build CEL scorecards for matching 2026 Rhode Island legislative candidates.

The Center for Effective Lawmaking publishes the source values through the API
used by its public "Find Legislators" application. This script preserves other
organizations' entries in outside_ratings_2026.json and replaces only CEL rows.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

API_BASE = "https://thelawmakers.org:3000/vis"
ORGANIZATION = "Center for Effective Lawmaking"
SOURCE_TYPE = "state legislative effectiveness score"
REPORT_URL = (
    "https://thelawmakers.org/wp-content/uploads/2026/04/"
    "Highlights-from-the-2023-2024-Rhode-Island-General-Assembly-"
    "State-Legislative-Effectiveness-Scores.pdf"
)
METHODOLOGY_URL = "https://thelawmakers.org/methodology"
GLOSSARY_URL = "https://thelawmakers.org/glossary"
LATEST_TERM = (2023, 2024)


def get_json(path: str, params: dict[str, object], retries: int = 3):
    url = f"{API_BASE}/{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "RIEP-data-builder/1.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.load(response)
        except Exception:
            if attempt + 1 == retries:
                raise
            time.sleep(1.5 * (attempt + 1))


def normalized_name(value: str) -> tuple[str, str]:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    if "," in value:
        last, given = value.split(",", 1)
        value = f"{given} {last}"
    tokens = re.findall(r"[a-z]+", value.lower())
    tokens = [t for t in tokens if t not in {"jr", "sr", "ii", "iii", "iv"}]
    return (tokens[0], tokens[-1]) if len(tokens) >= 2 else (value.lower(), value.lower())


def current_candidates(path: Path) -> dict[tuple[str, int, tuple[str, str]], str]:
    payload = json.loads(path.read_text())
    candidates = {}
    for chamber, districts in payload["chambers"].items():
        for district, race in districts.items():
            for candidate in race.get("candidates", []):
                key = chamber, int(district), normalized_name(candidate["name"])
                candidates[key] = candidate["name"]
    return candidates


def table(start: int, end: int) -> list[dict]:
    return get_json(
        "stateTable",
        {"state": "RI", "termStartYear": start, "termEndYear": end},
    )["data"]


def expectation(score: float, benchmark: float | None) -> str:
    if benchmark is None:
        return "Meets Expectations"
    if score < benchmark * 0.5:
        return "Below Expectations"
    if score <= benchmark * 1.5:
        return "Meets Expectations"
    return "Above Expectations"


def scorecard(row: dict) -> dict:
    start, end = LATEST_TERM
    result = get_json(
        "stateScorecard",
        {
            "slesId": row["slesId"],
            "termStartYear": start,
            "termEndYear": end,
            "chamber": row["chamber"],
        },
    )
    return result["data"]["overall"]


def category(overall: dict, prefix: str, label: str) -> dict:
    return {
        "label": label,
        "short": prefix.upper(),
        "introduced": overall[f"{prefix}_bill"],
        "committee_action": overall[f"{prefix}_aic"],
        "beyond_committee": overall[f"{prefix}_abc"],
        "passed_chamber": overall[f"{prefix}_pass"],
        "became_law": overall[f"{prefix}_law"],
    }


def make_entry(row: dict, candidate_name: str, overall: dict, history: list[dict]) -> dict:
    chamber = "house" if row["chamber"] == "lower" else "senate"
    chamber_title = "House" if chamber == "house" else "Senate"
    party_title = {"D": "Democrats", "R": "Republicans"}.get(row["party"], row["party"])
    categories = [
        category(overall, "c", "Commemorative"),
        category(overall, "s", "Substantive"),
        category(overall, "ss", "Substantive and significant"),
    ]
    stages = ("introduced", "committee_action", "beyond_committee", "passed_chamber", "became_law")
    bills = {stage: sum(item[stage] for item in categories) for stage in stages}
    score = float(row["sles"])
    benchmark = row.get("benchmark")
    streak = 0
    for item in history:
        if item["expectation"] != "Above Expectations":
            break
        streak += 1

    return {
        "candidate_name": candidate_name,
        "chamber": chamber,
        "district_number": int(row["district"]),
        "organization": ORGANIZATION,
        "year": "2023–2024",
        "rating": f"{score:.2f}",
        "measure": (
            "State Legislative Effectiveness Score measuring the demonstrated ability "
            "to advance sponsored bills through the legislative process, weighted by "
            "the substantive significance of the proposals."
        ),
        "source_url": REPORT_URL,
        "methodology_url": METHODOLOGY_URL,
        "source_type": SOURCE_TYPE,
        "expectation": expectation(score, benchmark),
        "comparison_group": f"{chamber_title} {party_title}",
        "party_rank": row["partyRank"],
        "party_total": row["partyTotal"],
        "benchmark": round(benchmark, 3) if benchmark is not None else None,
        "bills": bills,
        "bill_categories": categories,
        "history": [
            {"term": item["term"], "score": round(item["score"], 2), "rank": item["rank"]}
            for item in history
        ],
        "glossary_url": GLOSSARY_URL,
        "above_expectations_streak": streak,
        "note": (
            "The score is produced by the Center for Effective Lawmaking at the "
            "University of Virginia and Vanderbilt University, not by RIEP. The "
            "benchmark is the expected score for a comparable legislator based on "
            "factors including majority-party status, seniority, and committee-chair status."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, default=Path("data/whos_running_2026.json"))
    parser.add_argument("--output", type=Path, default=Path("data/outside_ratings_2026.json"))
    args = parser.parse_args()

    candidates = current_candidates(args.candidates)
    terms = get_json("stateTerms", {"state": "RI"})
    term_tables = {(t["startYear"], t["endYear"]): table(t["startYear"], t["endYear"]) for t in terms}
    latest = term_tables[LATEST_TERM]

    matches = []
    for row in latest:
        chamber = "house" if row["chamber"] == "lower" else "senate"
        key = chamber, int(row["district"]), normalized_name(row["name"])
        if key in candidates:
            matches.append((row, candidates[key]))

    def history_for(row: dict) -> list[dict]:
        identity = normalized_name(row["name"])
        items = []
        for (start, end), rows in sorted(term_tables.items(), reverse=True):
            previous = next(
                (r for r in rows if r["chamber"] == row["chamber"] and normalized_name(r["name"]) == identity),
                None,
            )
            if previous:
                items.append({
                    "term": f"{start}–{end}",
                    "score": float(previous["sles"]),
                    "rank": f"{previous['partyRank']} of {previous['partyTotal']}",
                    "expectation": expectation(float(previous["sles"]), previous.get("benchmark")),
                })
        return items

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        details = list(executor.map(lambda pair: scorecard(pair[0]), matches))

    cel_entries = [
        make_entry(row, name, overall, history_for(row))
        for (row, name), overall in zip(matches, details)
    ]
    cel_entries.sort(key=lambda item: (item["chamber"], item["district_number"], item["candidate_name"]))

    payload = json.loads(args.output.read_text())
    payload["ratings"] = [
        item for item in payload["ratings"]
        if item.get("source_type") != SOURCE_TYPE
    ] + cel_entries
    payload["updated_at"] = date.today().isoformat()
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(cel_entries)} CEL scorecards to {args.output}")


if __name__ == "__main__":
    main()

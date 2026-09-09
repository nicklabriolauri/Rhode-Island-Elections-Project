#!/usr/bin/env python3
"""
Update RIEP's 2026 Rhode Island Statewide Primary results from the
official Rhode Island Board of Elections Enhanced Voting results page.

The scraper deliberately matches the live page against RIEP's own
data/whos_running_2026.json candidate list. That makes the parser less
dependent on Enhanced Voting's internal API structure.

Official source:
https://electionresults.ri.gov/results/public/RhodeIsland/elections/RI2026StatewidePrimary
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_PATH = ROOT / "data" / "whos_running_2026.json"
OUTPUT_PATH = ROOT / "data" / "primary_results_2026.json"

RESULTS_URL = os.environ.get(
    "RI_RESULTS_URL",
    "https://electionresults.ri.gov/results/public/RhodeIsland/elections/RI2026StatewidePrimary",
)

NY = ZoneInfo("America/New_York")


def now_ny() -> datetime:
    return datetime.now(tz=NY)


def should_run() -> bool:
    if os.environ.get("FORCE_RUN") == "1":
        return True

    start_raw = os.environ.get("ELECTION_START")
    end_raw = os.environ.get("ELECTION_END")
    if not start_raw or not end_raw:
        return True

    start = datetime.fromisoformat(start_raw)
    end = datetime.fromisoformat(end_raw)
    current = datetime.now(tz=start.tzinfo)
    return start <= current <= end


def clean_name(value: str) -> str:
    value = str(value or "")
    value = value.replace("*", "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_name(value: str) -> str:
    value = clean_name(value).lower()
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    value = re.sub(r"\b(jr|sr|ii|iii|iv)\b", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def candidate_aliases(name: str) -> list[str]:
    full = normalize_name(name)
    tokens = full.split()
    aliases = {full}
    if len(tokens) >= 2:
        aliases.add(f"{tokens[0]} {tokens[-1]}")
        aliases.add(tokens[-1])
    return sorted((a for a in aliases if len(a) >= 3), key=len, reverse=True)


def derive_contested_races(payload: dict) -> list[dict]:
    races: list[dict] = []

    for chamber in ("house", "senate"):
        districts = payload.get("chambers", {}).get(chamber, {}) or {}

        for record in districts.values():
            district = record.get("district_number")
            if district is None:
                continue

            status = str(record.get("primary_status") or "").lower()
            candidates = record.get("candidates") or []

            for code, party, active_statuses in (
                ("DEM", "Democratic", {"dem_primary", "both_primaries"}),
                ("REP", "Republican", {"rep_primary", "both_primaries"}),
            ):
                party_candidates = [
                    c for c in candidates
                    if str(c.get("party") or "").upper() == code
                    and c.get("on_primary_ballot") is not False
                ]

                active = status in active_statuses or len(party_candidates) >= 2
                if not active or len(party_candidates) < 2:
                    continue

                races.append(
                    {
                        "chamber": chamber,
                        "district": int(district),
                        "party": party,
                        "party_code": code,
                        "contested": True,
                        "candidates": [
                            {
                                "name": clean_name(c.get("name")),
                                "votes": None,
                                "pct": None,
                                "advanced": False,
                            }
                            for c in party_candidates
                        ],
                    }
                )

    return races


def text_lines(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]


def parse_vote_number(value: str) -> int | None:
    value = value.strip()
    if not re.fullmatch(r"\d[\d,]*", value):
        return None
    try:
        return int(value.replace(",", ""))
    except ValueError:
        return None


def parse_candidate_from_block(block_text: str, candidate_name: str, next_names: list[str]) -> tuple[int | None, float | None]:
    """
    Enhanced Voting visually renders rows in the order:
    Candidate / party / percentage / votes.
    We locate a known RIEP candidate and inspect the lines immediately after the name.
    """
    lines = text_lines(block_text)
    aliases = candidate_aliases(candidate_name)

    start_idx = None
    for i, line in enumerate(lines):
        norm = normalize_name(line)
        if any(alias == norm or alias in norm for alias in aliases):
            start_idx = i
            break

    if start_idx is None:
        return None, None

    # Stop before another known candidate if encountered.
    stop = min(len(lines), start_idx + 10)
    other_aliases = [a for name in next_names for a in candidate_aliases(name)]

    for j in range(start_idx + 1, stop):
        norm = normalize_name(lines[j])
        if any(alias == norm or alias in norm for alias in other_aliases):
            stop = j
            break

    pct = None
    votes = None

    for line in lines[start_idx + 1:stop]:
        m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*%", line)
        if m and pct is None:
            pct = float(m.group(1))
            continue

        number = parse_vote_number(line)
        if number is not None:
            # Party labels and years are filtered by numeric-only matching; the
            # vote total is normally the first integer after the percentage.
            if votes is None:
                votes = number

    return votes, pct


def heading_score(text: str, race: dict) -> int:
    t = text.lower()
    district = str(race["district"])
    if not re.search(rf"\bdistrict\s*(?:no\.?\s*)?{re.escape(district)}\b", t):
        return -999

    score = 5

    if race["chamber"] == "house":
        if "representative" in t or "house" in t:
            score += 5
        if "senator" in t or "senate" in t:
            score -= 8
    else:
        if "senator" in t or "senate" in t:
            score += 5
        if "representative" in t or "house" in t:
            score -= 8

    if race["party_code"].lower() in t:
        score += 4
    party_word = "dem" if race["party_code"] == "DEM" else "rep"
    if party_word in t:
        score += 2

    return score


def find_race_block(page, race: dict) -> tuple[str, str] | None:
    headings = page.locator("h1, h2, h3, h4, h5")
    candidates = []

    for i in range(headings.count()):
        el = headings.nth(i)
        try:
            title = el.inner_text(timeout=1000).strip()
        except Exception:
            continue

        score = heading_score(title, race)
        if score < 5:
            continue

        # Find the smallest ancestor that contains the race's candidate names.
        block_text = ""
        for levels in range(1, 8):
            locator = el.locator("xpath=" + "/.." * levels)
            try:
                text = locator.inner_text(timeout=1000)
            except Exception:
                continue

            candidate_hits = sum(
                1 for c in race["candidates"]
                if any(alias in normalize_name(text) for alias in candidate_aliases(c["name"]))
            )

            if candidate_hits >= 2 and ("vote" in text.lower() or "%" in text):
                block_text = text
                break

        if block_text:
            candidates.append((score, title, block_text))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    _, title, block = candidates[0]
    return title, block


def parse_reporting_status(body_text: str) -> tuple[int | None, int | None, float | None]:
    """
    Enhanced Voting exposes a statewide precinct reporting block. This is not
    literally percent of ballots counted, so we store it as reporting_pct.
    """
    text = re.sub(r"\s+", " ", body_text)

    patterns = [
        r"Fully Reported\s+(\d+)\s*/\s*(\d+)",
        r"Precincts reporting.*?(\d+)\s*/\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I | re.S)
        if match:
            reporting = int(match.group(1))
            total = int(match.group(2))
            pct = round((reporting / total * 100), 1) if total else None
            return reporting, total, pct

    return None, None, None


def scrape() -> dict:
    candidates_payload = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    races = derive_contested_races(candidates_payload)

    if not races:
        raise RuntimeError("No contested races were found in data/whos_running_2026.json")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1500, "height": 1000},
            user_agent="RIEP-results-bot/1.0 (+https://www.rhodeislandelectionsproject.org/)",
        )

        try:
            page.goto(RESULTS_URL, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(8000)

            # Enhanced Voting pages auto-refresh. Give the results DOM a chance to populate.
            try:
                page.wait_for_selector("text=Candidate", timeout=30000)
            except PlaywrightTimeoutError:
                pass

            body_text = page.locator("body").inner_text(timeout=10000)
            precincts_reporting, precincts_total, reporting_pct = parse_reporting_status(body_text)

            parsed_count = 0

            for race in races:
                found = find_race_block(page, race)
                if not found:
                    race["precincts_reporting"] = precincts_reporting
                    race["precincts_total"] = precincts_total
                    race["reporting_pct"] = reporting_pct
                    continue

                _, block_text = found

                for candidate in race["candidates"]:
                    other_names = [
                        c["name"] for c in race["candidates"]
                        if c["name"] != candidate["name"]
                    ]
                    votes, pct = parse_candidate_from_block(block_text, candidate["name"], other_names)
                    candidate["votes"] = votes
                    candidate["pct"] = pct

                if any(c["votes"] is not None for c in race["candidates"]):
                    parsed_count += 1

                race["precincts_reporting"] = precincts_reporting
                race["precincts_total"] = precincts_total
                race["reporting_pct"] = reporting_pct

                # Mark a winner only after statewide precinct reporting reaches 100%.
                # RIEP is not making projections; this simply marks the top reported total.
                if reporting_pct == 100:
                    with_votes = [c for c in race["candidates"] if c["votes"] is not None]
                    if with_votes:
                        top_votes = max(c["votes"] for c in with_votes)
                        if sum(1 for c in with_votes if c["votes"] == top_votes) == 1:
                            for c in with_votes:
                                c["advanced"] = c["votes"] == top_votes

            print(f"Parsed live vote totals for {parsed_count} of {len(races)} contested races.")

        finally:
            browser.close()

    # Do not overwrite a populated file with all blanks if the live site changes.
    populated = sum(
        1 for race in races
        if any(c.get("votes") is not None for c in race.get("candidates", []))
    )

    previous = None
    if OUTPUT_PATH.exists():
        try:
            previous = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            previous = None

    previous_populated = 0
    if previous:
        previous_populated = sum(
            1 for race in previous.get("races", [])
            if any(c.get("votes") is not None for c in race.get("candidates", []))
        )

    if populated == 0 and previous_populated > 0:
        raise RuntimeError(
            "The official page returned no parseable vote totals, but the existing "
            "RIEP result file already contains votes. Refusing to overwrite it."
        )

    return {
        "election": "2026 Rhode Island Statewide Primary",
        "date": "2026-09-09",
        "source": "Rhode Island Board of Elections",
        "source_url": RESULTS_URL,
        "last_updated": now_ny().strftime("%Y-%m-%d %I:%M:%S %p %Z"),
        "status": "unofficial",
        "races": races,
    }


def main() -> int:
    if not should_run():
        print("Outside the configured election-night update window; nothing to do.")
        return 0

    if not CANDIDATE_PATH.exists():
        print(f"Missing candidate file: {CANDIDATE_PATH}", file=sys.stderr)
        return 2

    payload = scrape()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

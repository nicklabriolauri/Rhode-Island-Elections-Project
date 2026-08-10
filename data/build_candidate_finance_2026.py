from __future__ import annotations

import html
import http.cookiejar
import json
import re
import ssl
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
WEBSITE_DIR = ROOT / "website"
DATA_DIR = WEBSITE_DIR / "data"
DOCS_DIR = DATA_DIR / "finance-documents"
ROSTER_PATH = DATA_DIR / "whos_running_2026.json"
OUTPUT_PATH = DATA_DIR / "candidate_finance_2026.json"

PUBLIC_FILINGS_URL = "http://ricampaignfinance.com/RIPublic/Filings.aspx"
SECURE_BASE = "https://secure.ricampaignfinance.com"
USER_AGENT = "Mozilla/5.0"

OFFICE_CODE_BY_CHAMBER = {
    "senate": "6",
    "house": "7",
}

PARTY_SEARCH_CODE = {
    "DEM": "2",
    "REP": "5",
    "IND": "6",
}

PARTY_LABEL = {
    "DEM": "Democrat",
    "REP": "Republican",
    "IND": "Independent",
}

SOURCE_BUCKET_MAP = {
    "individuals": ("Itemized individual donors", "itemized-individual-donors"),
    "aggregate individuals": ("Small-dollar / aggregate online receipts", "small-dollar-aggregate-online-receipts"),
    "political action committees": ("PAC contributions", "pac-contributions"),
    "refund/rebate": ("Refunds / rebates", "refunds-rebates"),
    "other": ("Other reported sources", "other-reported-sources"),
}


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "candidate"


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace(".", " ").replace(",", " ").replace("'", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def format_period(start: str, end: str) -> str:
    try:
        start_dt = datetime.strptime(start, "%m/%d/%Y")
        end_dt = datetime.strptime(end, "%m/%d/%Y")
    except ValueError:
        return f"{start} to {end}"
    return f"{start_dt.strftime('%B')} {start_dt.day}, {start_dt.year} to {end_dt.strftime('%B')} {end_dt.day}, {end_dt.year}"


def format_currency(value: float) -> str:
    return "${:,.2f}".format(value)


def parse_money(value: str) -> float:
    cleaned = (value or "").replace("$", "").replace(",", "").strip()
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def clean_text(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_hidden(html_text: str, name: str) -> str:
    match = re.search(rf'name="{re.escape(name)}" id="{re.escape(name)}" value="([^"]*)"', html_text)
    return match.group(1) if match else ""


@dataclass
class CandidateSearchResult:
    name: str
    city: str
    state: str
    event_target: str


class PublicFilingsSession:
    def __init__(self) -> None:
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        self.headers = {
            "User-Agent": USER_AGENT,
            "Referer": PUBLIC_FILINGS_URL,
        }

    def fetch(self, url: str, data: dict[str, str] | None = None) -> str:
        encoded = None
        if data is not None:
            encoded = urllib.parse.urlencode(data).encode()
        request = urllib.request.Request(url, data=encoded, headers=self.headers)
        with self.opener.open(request, timeout=30) as response:
            return response.read().decode("utf-8", "ignore")

    def open_search(self) -> str:
        return self.fetch(PUBLIC_FILINGS_URL)

    def submit_search(self, base_html: str, *, last_name: str, first_name: str, office_code: str, party_code: str) -> str:
        form = {
            "__VIEWSTATE": extract_hidden(base_html, "__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": extract_hidden(base_html, "__VIEWSTATEGENERATOR"),
            "__EVENTVALIDATION": extract_hidden(base_html, "__EVENTVALIDATION"),
            "txtOrgLastName": last_name,
            "txtOrgFirstName": first_name,
            "lstOffice": office_code,
            "lstParty": party_code,
            "lstDisplayResults": "25",
            "lnkSubSearchOrg": "Search",
        }
        return self.fetch(PUBLIC_FILINGS_URL, form)

    def open_candidate(self, results_html: str, event_target: str, *, last_name: str, first_name: str, office_code: str, party_code: str) -> str:
        form = {
            "__VIEWSTATE": extract_hidden(results_html, "__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": extract_hidden(results_html, "__VIEWSTATEGENERATOR"),
            "__EVENTVALIDATION": extract_hidden(results_html, "__EVENTVALIDATION"),
            "txtOrgLastName": last_name,
            "txtOrgFirstName": first_name,
            "lstOffice": office_code,
            "lstParty": party_code,
            "lstDisplayResults": "25",
            "__EVENTTARGET": event_target,
            "__EVENTARGUMENT": "",
        }
        return self.fetch(PUBLIC_FILINGS_URL, form)


def extract_search_results(results_html: str) -> list[CandidateSearchResult]:
    rows: list[CandidateSearchResult] = []
    pattern = re.compile(
        r'<a id="dgdOrgSearchResults_ctl\d+_lnkOrgID" href="javascript:__doPostBack\(\'([^\']+)\'\,\'\'\)">(.*?)</a>'
        r".*?<td>\s*<span>\s*(.*?)\s*</span>\s*</td>"
        r".*?<td>\s*<span>\s*(.*?)\s*</span>\s*</td>"
        r".*?<td>\s*<span>\s*(.*?)\s*</span>\s*</td>",
        re.S,
    )
    for match in pattern.finditer(results_html):
        rows.append(
            CandidateSearchResult(
                event_target=match.group(1),
                name=clean_text(match.group(2)),
                city=clean_text(match.group(4)),
                state=clean_text(match.group(5)),
            )
        )
    return rows


def pick_best_search_result(results: list[CandidateSearchResult], expected_name: str) -> CandidateSearchResult | None:
    if not results:
        return None
    expected_norm = normalize_name(expected_name)
    for result in results:
        if normalize_name(result.name) == expected_norm:
            return result
    last_token = expected_norm.split()[-1] if expected_norm else ""
    for result in results:
        if last_token and last_token in normalize_name(result.name):
            return result
    return results[0]


def parse_filing_rows(candidate_html: str) -> list[dict[str, str]]:
    rows = []
    table_match = re.search(
        r'<table[^>]+id="grdSearchResults"[^>]*>(.*?)</table>',
        candidate_html,
        re.S,
    )
    if not table_match:
        return rows

    row_pattern = re.compile(
        r'<tr class="Grid(?:Alternating)?Item"[^>]*>(.*?)</tr>',
        re.S,
    )
    cell_pattern = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S)
    for match in row_pattern.finditer(table_match.group(1)):
        cells_raw = cell_pattern.findall(match.group(1))
        if len(cells_raw) < 8:
            continue
        cells = [clean_text(re.sub(r"<.*?>", " ", group)) for group in cells_raw[:8]]
        link_match = re.search(r'href="([^"]+)"', cells_raw[7])
        rows.append(
            {
                "label": cells[0],
                "period_start": cells[1],
                "period_end": cells[2],
                "due_date": cells[3],
                "status": cells[4],
                "filed_at": cells[5],
                "amended": cells[6],
                "view_href": html.unescape(link_match.group(1)) if link_match else "",
            }
        )
    return rows


def parse_public_summary(candidate_html: str) -> dict[str, float | str]:
    report_match = re.search(r'<span id="lblReportType">(.*?)</span>', candidate_html)
    balance_match = re.search(r'<span id="lblBalanceDate">(.*?)</span>', candidate_html)
    total_cash_match = re.search(r'<span id="lblTotalContributions">\$(.*?)</span>', candidate_html)
    total_exp_match = re.search(r'<span id="lblTotalExpenditures">\$(.*?)</span>', candidate_html)
    begin_match = re.search(r'<span id="lblBeginningBalance">\$(.*?)</span>', candidate_html)
    end_match = re.search(r'<span id="lblEndingBalance">\$(.*?)</span>', candidate_html)
    return {
        "report_label": clean_text(report_match.group(1)) if report_match else "",
        "balance_date": clean_text(balance_match.group(1)) if balance_match else "",
        "total_cash": parse_money(total_cash_match.group(1) if total_cash_match else ""),
        "total_liabilities": parse_money(total_exp_match.group(1) if total_exp_match else ""),
        "beginning_cash": parse_money(begin_match.group(1) if begin_match else ""),
        "ending_cash": parse_money(end_match.group(1) if end_match else ""),
    }


def fetch_html(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Referer": PUBLIC_FILINGS_URL})
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, context=context, timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


def download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Referer": url})
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, context=context, timeout=30) as response:
        destination.write_bytes(response.read())


def extract_pdf_href(secure_html: str) -> str:
    match = re.search(r'href="(https://ricampaignfinance\.com/ExportDocs/[^"]+\.pdf)"', secure_html)
    if match:
        return html.unescape(match.group(1))
    return ""


def parse_page_one_summary(pdf_path: Path) -> dict[str, float]:
    result: dict[str, float] = {}
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        if pdf.pages:
            text = pdf.pages[0].extract_text() or ""
    patterns = {
        "beginning_cash": r"Beginning Cash Balance\s+\$?\s*([\d,]+\.\d{2})",
        "ending_cash": r"(?:Ending Cash Balance|Total Fund Balance)\s+\$?\s*([\d,]+\.\d{2})",
        "money_raised": r"Total Cash\s+\$?\s*([\d,]+\.\d{2})",
        "campaign_expenses": r"Campaign Expenses\s+\$?\s*([\d,]+\.\d{2})",
        "aggregate_expenses": r"Aggregate Expenses\s+\$?\s*([\d,]+\.\d{2})",
        "individuals": r"\bIndividuals\s+([\d,]+\.\d{2})",
        "aggregate individuals": r"Aggregate\s+([\d,]+\.\d{2})",
        "political action committees": r"Political Action Committees\s+([\d,]+\.\d{2})",
        "refund/rebate": r"Refund/Rebate\s+([\d,]+\.\d{2})",
        "other": r"\bOther\s+([\d,]+\.\d{2})",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.I)
        result[key] = parse_money(match.group(1) if match else "")
    result["total_cash_available"] = result["money_raised"]
    source_total = (
        result["individuals"]
        + result["aggregate individuals"]
        + result["political action committees"]
        + result["refund/rebate"]
        + result["other"]
    )
    if source_total > 0:
        result["money_raised"] = source_total
    elif result["beginning_cash"] > 0:
        result["money_raised"] = max(result["total_cash_available"] - result["beginning_cash"], 0.0)
    result["money_spent"] = result["campaign_expenses"] + result["aggregate_expenses"]
    result["net_change"] = result["money_raised"] - result["money_spent"]
    return result


def parse_contributions(pdf_path: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    line_pattern = re.compile(
        r"^(?P<transaction>.+?)\s(?P<receipt>\d{2}/\d{2}/\d{4})(?:\s(?P<deposit>\d{2}/\d{2}/\d{4}))?\s(?P<amount>[\d,]+\.\d{2})$"
    )
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[2:]:
            text = page.extract_text() or ""
            if "SCHEDULE OF EXPENDITURES" in text:
                break
            lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]
            i = 0
            while i < len(lines):
                match = line_pattern.match(lines[i])
                if not match:
                    i += 1
                    continue

                transaction_text = match.group("transaction")
                amount = parse_money(match.group("amount"))
                donor_name = ""
                employer = ""
                description = ""

                j = i + 1
                while j < len(lines):
                    if line_pattern.match(lines[j]):
                        break
                    line = lines[j]
                    if line == "In Kind/Other Receipts Description" and j + 1 < len(lines):
                        possible = lines[j + 1]
                        if "Contributor Information" not in possible and "Prefix First Name" not in possible:
                            description = possible
                    if line.startswith("Prefix First Name MI Last Name or PAC/Party Committee Name") and j + 1 < len(lines):
                        person_line = lines[j + 1]
                        if person_line not in {"Street Address Street Address", "City State Zip City State Zip"} and not line_pattern.match(person_line):
                            if transaction_text.endswith("PAC"):
                                donor_name = person_line
                            else:
                                tokens = person_line.split()
                                if len(tokens) >= 2:
                                    donor_name = " ".join(tokens[:2])
                                    employer = " ".join(tokens[2:])
                                else:
                                    donor_name = person_line
                    j += 1

                bucket_type = "Other"
                if "PAC" in transaction_text:
                    bucket_type = "PAC"
                elif "Aggregate - Individual" in transaction_text:
                    bucket_type = "Aggregate"
                elif "Individual" in transaction_text:
                    bucket_type = "Individual"
                elif "Refund/Rebate" in transaction_text:
                    bucket_type = "Refund/Rebate"

                if not donor_name:
                    donor_name = description or bucket_type

                entries.append(
                    {
                        "donor": donor_name,
                        "amount": amount,
                        "type": bucket_type,
                        "employer": employer,
                        "description": description,
                    }
                )
                i = j
            # end while
    return entries


def build_top_donors(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for entry in entries:
        donor = clean_text(str(entry.get("donor", "")))
        if not donor or donor in {"Aggregate", "Refund/Rebate"}:
            continue
        key = (donor, str(entry.get("type", "")))
        item = grouped.setdefault(
            key,
            {
                "donor": donor,
                "amount": 0.0,
                "type": entry.get("type") or "Donor",
                "notes": "",
            },
        )
        item["amount"] = float(item["amount"]) + float(entry.get("amount", 0.0))
        if entry.get("type") == "PAC":
            item["notes"] = "Named PAC contribution listed in the filing."
        elif entry.get("employer"):
            item["notes"] = f"Employer listed as {entry['employer']}."
        elif entry.get("description"):
            item["notes"] = clean_text(str(entry["description"]))
        else:
            item["notes"] = "Named individual contribution listed in the filing."
    return sorted(grouped.values(), key=lambda item: (-float(item["amount"]), item["donor"]))[:10]


def parse_expenditures(pdf_path: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    line_pattern = re.compile(
        r"^(?:(?P<check>\d+)\s+)?(?P<expense_date>\d{2}/\d{2}/\d{4})\s(?:(?P<payment_date>\d{2}/\d{2}/\d{4})\s)?(?P<disbursement>Aggregate Expenditure|Campaign Expenditure)\s(?P<expense_type>.+?)\s\$(?P<amount>[\d,]+\.\d{2})$"
    )
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "SCHEDULE OF EXPENDITURES" not in text and not entries:
                continue
            if "SCHEDULE OF EXPENDITURES" not in text and entries is None:
                continue
            lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]
            i = 0
            while i < len(lines):
                match = line_pattern.match(lines[i])
                if not match:
                    i += 1
                    continue

                expense_type = match.group("expense_type")
                amount = parse_money(match.group("amount"))
                purpose = ""
                vendor = ""
                j = i + 1
                while j < len(lines):
                    if line_pattern.match(lines[j]):
                        break
                    if lines[j] == "Purpose of Expenditure" and j + 1 < len(lines):
                        purpose = lines[j + 1]
                    if lines[j] == "Prefix First Name MI LastName or Vendor Name Suffix" and j + 1 < len(lines):
                        possible = lines[j + 1]
                        if possible not in {"Street Address City State Zip"} and not line_pattern.match(possible):
                            vendor = possible
                    j += 1

                entries.append(
                    {
                        "expense_type": expense_type,
                        "amount": amount,
                        "purpose": purpose,
                        "vendor": vendor,
                    }
                )
                i = j
    return entries


def summarize_spending(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[str, dict[str, object]] = {}
    for entry in entries:
        expense_type = clean_text(str(entry.get("expense_type", "")))
        purpose = clean_text(str(entry.get("purpose", "")))
        vendor = clean_text(str(entry.get("vendor", "")))
        amount = float(entry.get("amount", 0.0))

        title = expense_type or "Campaign spending"
        summary = purpose or vendor or "Reported campaign expenses listed in the filing."

        item = groups.setdefault(
            title,
            {
                "title": title,
                "amount": 0.0,
                "vendors": [],
                "samples": [],
            },
        )
        item["amount"] = float(item["amount"]) + amount
        if vendor and vendor not in item["vendors"]:
            item["vendors"].append(vendor)
        if summary and summary not in item["samples"]:
            item["samples"].append(summary)

    cards = []
    for item in sorted(groups.values(), key=lambda entry: (-float(entry["amount"]), entry["title"])):
        vendors = item["vendors"][:3]
        samples = item["samples"][:2]
        if vendors:
            summary = f"Visible spending includes {', '.join(vendors)}."
        elif samples:
            summary = samples[0]
        else:
            summary = "Reported campaign expenses grouped from the filing."
        cards.append(
            {
                "title": item["title"],
                "summary": summary,
                "amount": round(float(item["amount"]), 2),
            }
        )
    return cards[:10]


def build_source_buckets(summary: dict[str, float]) -> list[dict[str, object]]:
    buckets = []
    for key in ["individuals", "aggregate individuals", "political action committees", "refund/rebate", "other"]:
        amount = round(float(summary.get(key, 0.0)), 2)
        if amount <= 0:
            continue
        label, class_name = SOURCE_BUCKET_MAP[key]
        if key == "individuals":
            description = "Named contributors reported individually in the filing."
        elif key == "aggregate individuals":
            description = "Money reported in aggregate form without individual donor names listed in the filing."
        elif key == "political action committees":
            description = "Political committees and PACs listed in the filing."
        elif key == "refund/rebate":
            description = "Small reimbursements, refunds, or rebates reported by the campaign."
        else:
            description = "Other money reported in the filing."
        buckets.append(
            {
                "label": label,
                "class_name": class_name,
                "amount": amount,
                "description": description,
            }
        )
    return buckets


def build_history_entry(label: str, row: dict[str, str], summary: dict[str, float]) -> dict[str, object]:
    net_change = round(float(summary.get("money_raised", 0.0)) - float(summary.get("money_spent", 0.0)), 2)
    note = (
        "The campaign raised more than it spent in this reporting period."
        if net_change >= 0
        else "The campaign spent more than it raised in this reporting period."
    )
    return {
        "label": label,
        "reporting_period_label": format_period(row["period_start"], row["period_end"]),
        "money_raised": round(float(summary.get("money_raised", 0.0)), 2),
        "money_spent": round(float(summary.get("money_spent", 0.0)), 2),
        "ending_cash": round(float(summary.get("ending_cash", 0.0)), 2),
        "net_change": net_change,
        "notes": note,
    }


def build_summary_intro(candidate_name: str, summary: dict[str, float]) -> str:
    ending_cash = float(summary.get("ending_cash", 0.0))
    net_change = float(summary.get("net_change", 0.0))
    if ending_cash <= 0:
        reserve_text = "This filing shows the campaign closing the period without reported cash on hand."
    elif ending_cash < 2500:
        reserve_text = "This filing shows only a limited cash reserve heading into the next stretch of the campaign."
    elif ending_cash < 20000:
        reserve_text = "This filing shows a modest cash reserve still available to the campaign."
    else:
        reserve_text = "This filing shows a campaign that still has a substantial cash reserve."
    flow_text = "it raised more during the period than it spent." if net_change >= 0 else "it spent more during the period than it raised."
    return f"{reserve_text} The report also shows that {flow_text}"


def parse_candidate_profile(candidate: dict[str, object]) -> dict[str, object] | None:
    chamber = str(candidate["chamber"])
    office_code = OFFICE_CODE_BY_CHAMBER.get(chamber)
    party_code = PARTY_SEARCH_CODE.get(str(candidate.get("party_code") or candidate.get("party") or ""))
    if not office_code or not party_code:
        return None

    name = clean_text(str(candidate["name"]))
    name_parts = name.split()
    first_name = name_parts[0]
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else name_parts[0]

    session = PublicFilingsSession()
    search_html = session.open_search()
    results_html = session.submit_search(
        search_html,
        last_name=last_name,
        first_name=first_name,
        office_code=office_code,
        party_code=party_code,
    )
    result_rows = extract_search_results(results_html)
    picked = pick_best_search_result(result_rows, name)
    if not picked:
        return None

    candidate_html = session.open_candidate(
        results_html,
        picked.event_target,
        last_name=last_name,
        first_name=first_name,
        office_code=office_code,
        party_code=party_code,
    )
    filing_rows = parse_filing_rows(candidate_html)
    public_summary = parse_public_summary(candidate_html)

    q2_row = next((row for row in filing_rows if row["label"] == "2026 On-Going Qrtly (2nd)"), None)
    if not q2_row or not q2_row["view_href"]:
        return None

    q1_row = next((row for row in filing_rows if row["label"] == "2026 On-Going Qrtly (1st)"), None)

    secure_q2_html = fetch_html(q2_row["view_href"])
    q2_pdf_href = extract_pdf_href(secure_q2_html)
    if not q2_pdf_href:
        return None

    slug = slugify(name)
    q2_pdf_path = DOCS_DIR / f"{slug}-q2-2026.pdf"
    download_file(q2_pdf_href, q2_pdf_path)

    q1_pdf_href = ""
    q1_pdf_path: Path | None = None
    if q1_row and q1_row["view_href"]:
        secure_q1_html = fetch_html(q1_row["view_href"])
        q1_pdf_href = extract_pdf_href(secure_q1_html)
        if q1_pdf_href:
            q1_pdf_path = DOCS_DIR / f"{slug}-q1-2026.pdf"
            download_file(q1_pdf_href, q1_pdf_path)

    q2_summary = parse_page_one_summary(q2_pdf_path)
    contributions = parse_contributions(q2_pdf_path)
    expenditures = parse_expenditures(q2_pdf_path)

    history = []
    if q2_row:
        history.append(build_history_entry("Q2 2026", q2_row, q2_summary))
    if q1_row and q1_pdf_path and q1_pdf_path.exists():
        q1_summary = parse_page_one_summary(q1_pdf_path)
        history.append(build_history_entry("Q1 2026", q1_row, q1_summary))

    office_sought = "State Representative" if chamber == "house" else "State Senator"
    party_code_short = str(candidate.get("party_code") or candidate.get("party") or "")

    beginning_cash = round(float(q2_summary.get("beginning_cash", public_summary.get("beginning_cash", 0.0))), 2)
    ending_cash = round(float(q2_summary.get("ending_cash", public_summary.get("ending_cash", 0.0))), 2)
    money_raised = round(float(q2_summary.get("money_raised", 0.0)), 2)
    campaign_expenses = round(float(q2_summary.get("campaign_expenses", 0.0)), 2)
    aggregate_expenses = round(float(q2_summary.get("aggregate_expenses", 0.0)), 2)
    money_spent = round(float(campaign_expenses + aggregate_expenses), 2)
    net_change = round(float(money_raised - money_spent), 2)

    profile = {
        "candidate_id": f"{chamber}-{candidate['district_number']}-{slug}",
        "slug": slug,
        "candidate_name": name,
        "chamber": chamber,
        "district_number": str(candidate["district_number"]),
        "party": party_code_short,
        "office_sought": office_sought,
        "report_label": q2_row["label"],
        "reporting_period_label": format_period(q2_row["period_start"], q2_row["period_end"]),
        "source_note": "Built from Rhode Island campaign finance filings for the 2026 second quarter.",
        "original_documents": [
            {
                "label": "Q2 2026 CF-2 report",
                "period": format_period(q2_row["period_start"], q2_row["period_end"]),
                "href": f"/data/finance-documents/{q2_pdf_path.name}",
            },
            *(
                [
                    {
                        "label": "Q1 2026 CF-2 report",
                        "period": format_period(q1_row["period_start"], q1_row["period_end"]),
                        "href": f"/data/finance-documents/{q1_pdf_path.name}",
                    }
                ]
                if q1_row and q1_pdf_path
                else []
            ),
        ],
        "beginning_cash": beginning_cash,
        "money_raised": money_raised,
        "money_spent": money_spent,
        "ending_cash": ending_cash,
        "net_change": net_change,
        "campaign_expenses": campaign_expenses,
        "aggregate_expenses": aggregate_expenses,
        "summary_intro": build_summary_intro(name, {"ending_cash": ending_cash, "net_change": net_change}),
        "filing_history": history,
        "source_buckets": build_source_buckets(q2_summary),
        "top_donors": build_top_donors(contributions),
        "spending_categories": summarize_spending(expenditures),
        "takeaways": [],
        "explainer_cards": [],
    }
    return profile


def load_roster() -> list[dict[str, object]]:
    raw = json.loads(ROSTER_PATH.read_text())
    candidates = []
    for chamber_name, chamber in raw["chambers"].items():
        for district_number, district in chamber.items():
            for candidate in district.get("candidates", []):
                if candidate.get("party") not in {"DEM", "REP", "IND"}:
                    continue
                candidates.append(
                    {
                        "name": candidate["name"],
                        "chamber": chamber_name,
                        "district_number": district_number,
                        "party_code": candidate.get("party"),
                    }
                )
    return candidates


def main() -> int:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    roster = load_roster()
    directory = []
    profiles = []

    for index, candidate in enumerate(roster, start=1):
        print(f"[{index}/{len(roster)}] {candidate['name']} ({candidate['chamber']} {candidate['district_number']})", file=sys.stderr)
        entry = {
            "candidate_name": candidate["name"],
            "slug": slugify(str(candidate["name"])),
            "candidate_id": f"{candidate['chamber']}-{candidate['district_number']}-{slugify(str(candidate['name']))}",
            "chamber": candidate["chamber"],
            "district_number": str(candidate["district_number"]),
            "party": candidate["party_code"],
            "office_sought": "State Representative" if candidate["chamber"] == "house" else "State Senator",
            "has_profile": False,
        }
        try:
            profile = parse_candidate_profile(candidate)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! failed: {exc}", file=sys.stderr)
            profile = None

        if profile:
            profiles.append(profile)
            entry["has_profile"] = True
        directory.append(entry)
        time.sleep(0.15)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cycle": "2026-q2",
        "directory": directory,
        "profiles": sorted(profiles, key=lambda item: (item["chamber"], int(item["district_number"]), item["candidate_name"])),
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {len(profiles)} profiles to {OUTPUT_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

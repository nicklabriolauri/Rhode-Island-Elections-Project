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

import pandas as pd
import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
WEBSITE_DIR = ROOT / "website"
DATA_DIR = WEBSITE_DIR / "data"
DOCS_DIR = DATA_DIR / "finance-documents"
ROSTER_PATH = DATA_DIR / "whos_running_2026.json"
OUTPUT_PATH = DATA_DIR / "candidate_finance_2026.json"
WORKBOOK_SUMMARY_PATH = Path("/Users/nicholaslabriola/Downloads/RI_2026_All_Declared_Candidates_Campaign_Finance_UPDATED_Manual_PDFs.xlsx")
WORKBOOK_DETAIL_PATH = Path("/Users/nicholaslabriola/Downloads/all_candidates_campaign_finance_Q1_Q2_2026_corrected_cash.xlsx")
LOCAL_PDF_PROFILE_OVERRIDES = {
    "house-2-christopher-r-blazejewski",
}

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
    "aggregate individuals": ("Receipts without donor names listed", "small-dollar-aggregate-online-receipts"),
    "political action committees": ("PAC contributions", "pac-contributions"),
    "refund/rebate": ("Refunds / rebates", "refunds-rebates"),
    "other": ("Other reported sources", "other-reported-sources"),
}

PARTY_DISPLAY = {
    "DEM": "Democratic",
    "REP": "Republican",
    "IND": "Independent",
}

PROFILE_SORT_KEYS = ("money_raised", "money_spent", "ending_cash")



# Q2 detail overrides extracted from allcandidatesfilingsq1q2.pdf.
# These fill only missing Top Donors, Spending Breakdown, and Funding Mix fields.
# Existing populated profile details are never overwritten.
PROFILE_DETAIL_OVERRIDES = {'house-74-alex-finkelman': {'top_donors': [{'donor': 'George Zainyeh', 'amount': 500.0, 'type': 'Individual', 'notes': 'Employer listed as Athena Solutions Group LLC.'}, {'donor': 'RI HOSPITALITY PAC', 'amount': 500.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': "PANNONE LOPES DEVEREAUX & O'GARA LLC RI STATE PAC", 'amount': 200.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'William J', 'amount': 200.0, 'type': 'Individual', 'notes': 'Employer listed as Murphy Murphy & Fay LLP.'}, {'donor': 'Peter Baptista', 'amount': 150.0, 'type': 'Individual', 'notes': 'Employer listed as Capitol Communications Group.'}, {'donor': 'CITIZENS BANK PACOM', 'amount': 125.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'REALTORS PAC OF RI', 'amount': 100.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}]}, 'house-12-arlette-hidalgo': {'top_donors': [{'donor': 'JOSE F', 'amount': 1710.0, 'type': 'Individual', 'notes': 'Employer listed as BATISTA LAW OFFICE OF JOSE F BATISTA LLC.'}, {'donor': 'VICTOR F', 'amount': 509.54, 'type': 'Individual', 'notes': 'Employer listed as CAPELLAN RI EDUCATION COLLECTIVE.'}, {'donor': 'ROSE SIEGEL', 'amount': 300.0, 'type': 'Individual', 'notes': 'Employer listed as RETIRED.'}, {'donor': 'BRANDON POTTER', 'amount': 200.0, 'type': 'Individual', 'notes': 'Employer listed as KECHES LAW GROUP.'}, {'donor': 'ARLETTE HIDALGO', 'amount': 10.0, 'type': 'Individual', 'notes': 'Employer listed as DAVID REACH ACADEMY.'}]}, 'house-57-james-mclaughlin': {'spending_categories': [{'title': 'Bank Fees', 'summary': 'Payee Information', 'amount': 24.0}]}, 'house-39-jasmin-roy': {'top_donors': [{'donor': 'RHODE ISLAND SECOND AMENDMENT PAC', 'amount': 1000.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'CHRIS STANTON', 'amount': 500.0, 'type': 'Individual', 'notes': 'Employer listed as SELF EMPLOYED.'}, {'donor': 'POLLY HOPKINS', 'amount': 370.0, 'type': 'Individual', 'notes': 'Employer listed as ELECTRIC BOAT.'}, {'donor': 'SARAH MALO', 'amount': 350.0, 'type': 'Individual', 'notes': 'Employer listed as OCEAN STATE VET SPECIALIST.'}, {'donor': 'DR STEPHEN', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as T SKOLY SELF EMPLOYED.'}, {'donor': 'THE LEAGUE OF RI BUSINESSES EXETER', 'amount': 250.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'THE LEAGUE OF RI BUSINESSES HOPKINTON', 'amount': 250.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'SYLVIA THOMPSON', 'amount': 240.15, 'type': 'Individual', 'notes': 'Employer listed as RETIRED.'}, {'donor': 'THE LEAGUE OF RI BUSINESSES RICHMOND', 'amount': 215.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'DIANNE TEFFT', 'amount': 185.0, 'type': 'Individual', 'notes': 'Employer listed as RETIRED.'}], 'spending_categories': [{'title': 'Other', 'summary': 'Visible spending includes MACYS.', 'amount': 313.0}, {'title': 'Fundraising Expenses', 'summary': 'Visible spending includes RI GOP, THE RANGE RI.', 'amount': 204.1}, {'title': 'Food, Beverages and Meals', 'summary': 'Visible spending includes AVIO, DRAGON PALACE, MIDDLE OF NOWHERE DINER.', 'amount': 147.84}, {'title': 'Donations (Political)', 'summary': 'Visible spending includes RAYMOND MCKAY, DR STEPHEN T SKOLY.', 'amount': 90.0}, {'title': 'Travel & Lodging', 'summary': 'Visible spending includes CUMBERLAND FARMS.', 'amount': 49.66}, {'title': 'Donations (All Others)', 'summary': 'Visible spending includes ST MARYS.', 'amount': 35.0}, {'title': 'Office Equipment & Supplies', 'summary': 'Visible spending includes AMAZON INTERNET.', 'amount': 34.49}, {'title': 'Gifts', 'summary': 'Visible spending includes WRISTCO AMAZON.', 'amount': 13.1}]}, 'senate-23-jessica-de-la-cruz': {'top_donors': [{'donor': 'RI BROTHERHOOD OF CORRECTIONAL OFFICERS PAC', 'amount': 1000.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'David Clauss', 'amount': 520.51, 'type': 'Individual', 'notes': 'Employer listed as MIKEL INC.'}, {'donor': 'Henry Breyer', 'amount': 520.51, 'type': 'Individual', 'notes': 'Employer listed as Max-Ord Rifles.'}, {'donor': 'Craig Mechler', 'amount': 500.0, 'type': 'Individual', 'notes': 'Employer listed as Retired.'}, {'donor': 'Christopher Gagne', 'amount': 392.21000000000004, 'type': 'Individual', 'notes': 'Employer listed as Fusion Medical.'}, {'donor': 'Kris Murphy', 'amount': 312.29999999999995, 'type': 'Individual', 'notes': 'Employer listed as QML.'}, {'donor': 'Christopher Bilotti', 'amount': 260.25, 'type': 'Individual', 'notes': 'Employer listed as The Bilotti Group, Inc..'}, {'donor': 'Roger Earle', 'amount': 260.25, 'type': 'Individual', 'notes': 'Employer listed as Retired.'}, {'donor': 'Col. Stephen', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as P. Kelley Retired.'}, {'donor': 'Joseph W', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as Walsh Self - Attorney at Law.'}]}, 'house-7-jo-ann-ryan': {'top_donors': [{'donor': 'Daniel Abram', 'amount': 2000.0, 'type': 'Individual', 'notes': 'Employer listed as Not Employed.'}, {'donor': 'JOSEPH R', 'amount': 2000.0, 'type': 'Individual', 'notes': 'Employer listed as PAOLINO PAOLINO PROPERTIES.'}, {'donor': 'Bonnie Fargnoli', 'amount': 1000.0, 'type': 'Individual', 'notes': 'Employer listed as CCRI.'}, {'donor': 'Brett Smiley', 'amount': 1000.0, 'type': 'Individual', 'notes': 'Employer listed as City of Providence.'}, {'donor': 'John Petrarca', 'amount': 1000.0, 'type': 'Individual', 'notes': 'Employer listed as Providence Auto Body.'}, {'donor': 'Karl Augenstein', 'amount': 1000.0, 'type': 'Individual', 'notes': 'Employer listed as Triggs.'}, {'donor': 'Adam Sepe', 'amount': 500.0, 'type': 'Individual', 'notes': 'Employer listed as North Eastern Tree Service.'}, {'donor': 'Anthony Simon', 'amount': 500.0, 'type': 'Individual', 'notes': 'Employer listed as Self Employed Consultant.'}, {'donor': 'Arnold B', 'amount': 500.0, 'type': 'Individual', 'notes': 'Employer listed as Chace Cornish Assoc.'}, {'donor': 'Arthur J', 'amount': 500.0, 'type': 'Individual', 'notes': 'Employer listed as Corvese Optometrist.'}]}, 'house-19-joseph-mcnamara': {'top_donors': [{'donor': 'RI ASSOCIATION OF ORAL & MAXILLOFACIAL SURGEONS PAC', 'amount': 500.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'RI DENTAL PAC', 'amount': 500.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'RI HOSPITALITY PAC', 'amount': 500.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'WARWICK FIREFIGHTER PAC 1', 'amount': 500.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'John Petrarca', 'amount': 350.0, 'type': 'Individual', 'notes': 'Employer listed as Providence Auto Body.'}, {'donor': "RI LABORER'S POLITICAL LEAGUE", 'amount': 300.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'Ronald Caniglia', 'amount': 300.0, 'type': 'Individual', 'notes': 'Employer listed as Stand Corporation.'}, {'donor': 'NEARI PACE (National Education Association of RI)', 'amount': 250.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'RI HEALTH CARE ASSOCIATION PAC', 'amount': 250.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'William Murphy', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as Murphy and Fay.'}]}, 'house-60-karen-alzate': {'top_donors': [{'donor': 'CAREPAC OF BLUE CROSS & BLUE SHIELD OF RI', 'amount': 150.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'Jean P', 'amount': 150.0, 'type': 'Individual', 'notes': 'Employer listed as Barros Unemlyed.'}, {'donor': 'Keith Hoffmann', 'amount': 150.0, 'type': 'Individual', 'notes': 'Employer listed as Unemployeed.'}, {'donor': 'RI STATE ASSOCIATION OF FIREFIGHTERS', 'amount': 150.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'steven Ceceri', 'amount': 150.0, 'type': 'Individual', 'notes': 'Employer listed as Owner-contractor.'}, {'donor': 'Carlos Vargas', 'amount': 100.0, 'type': 'Individual', 'notes': 'Employer listed as Navigant Credit Union.'}, {'donor': 'EGFFA PAC (East Greenwich Fire Fighters Association)', 'amount': 100.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'Grant Pilkington', 'amount': 100.0, 'type': 'Individual', 'notes': 'Employer listed as Advocacy Solutions.'}, {'donor': 'IBEW LOCAL 99 PAC (International Brotherhood of Electrical Workers)', 'amount': 100.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'Pedro Espinal', 'amount': 100.0, 'type': 'Individual', 'notes': 'Employer listed as councilmen.'}]}, 'house-73-marvin-abney': {'top_donors': [{'donor': 'Matthew A', 'amount': 1000.0, 'type': 'Individual', 'notes': "Employer listed as Lopes Jr Pannone Lopes Devereaux & O'Gara."}, {'donor': 'PEOPLE, RI COUNCIL 94, AFSCME AFL-CIO PAC', 'amount': 500.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'REALTORS PAC OF RI', 'amount': 300.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'CAREPAC OF BLUE CROSS & BLUE SHIELD OF RI', 'amount': 250.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'Christopher Boyle', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as Christopher Boyle, Esq..'}, {'donor': 'Leonard Lopes', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as The Victor Group.'}, {'donor': 'M. Teresa', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as Paiva Weed F/S Capitol Consulting, LLC.'}, {'donor': 'NEARI PACE (National Education Association of RI)', 'amount': 250.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'Steven VincentCeceri', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as NE Property Services Group, LLC.'}, {'donor': 'William J.', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as Murphy Murphy & Fay, LLP.'}]}, 'house-40-michael-chippendale': {'top_donors': [{'donor': 'REALTORS PAC OF RI', 'amount': 1200.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'Victor Mellor', 'amount': 1041.02, 'type': 'Individual', 'notes': 'Employer listed as American Precast Concrete.'}, {'donor': 'Committee / PAC receipts', 'amount': 800.0, 'type': 'PAC', 'notes': 'The filing shows committee or PAC receipts, but the public text does not provide readable donor names here.'}, {'donor': 'John Petrarca', 'amount': 500.0, 'type': 'Individual', 'notes': 'Employer listed as Providence Autobody.'}, {'donor': 'RHODE ISLAND ENERGY PAC (RIE PAC)', 'amount': 500.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'RI BROTHERHOOD OF CORRECTIONAL OFFICERS PAC', 'amount': 500.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'Anthony Thompson', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as Strong Tree Properties LLC.'}, {'donor': 'David Caldwell', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as Caldwell Builders.'}, {'donor': 'Nicholas Fede', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as Kingstown Liquor Mart.'}, {'donor': 'Patrick Guida', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as Esq Duffy & Sweeny.'}]}, 'house-9-santos-javier': {'top_donors': [{'donor': 'BRETT SMILEY', 'amount': 500.0, 'type': 'Individual', 'notes': 'Employer listed as CITY OF PROVIDENCE.'}, {'donor': 'COLLECTIVE POWER FOR EDUCATION PAC', 'amount': 400.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'ROSE SIEGEL', 'amount': 400.0, 'type': 'Individual', 'notes': 'Named individual contribution listed in the filing.'}, {'donor': 'FRANK CICCONE', 'amount': 300.0, 'type': 'Individual', 'notes': 'Employer listed as SENATOR.'}, {'donor': 'THE LEAGUE OF RI BUSINESSES PROVIDENCE', 'amount': 250.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'ANTHONY THOMPSON', 'amount': 150.0, 'type': 'Individual', 'notes': 'Named individual contribution listed in the filing.'}, {'donor': 'JAMES TAYLOR', 'amount': 150.0, 'type': 'Individual', 'notes': 'Named individual contribution listed in the filing.'}, {'donor': 'ADRIA PENA', 'amount': 100.0, 'type': 'Individual', 'notes': 'Named individual contribution listed in the filing.'}, {'donor': 'CAROLINA PICHARDO', 'amount': 100.0, 'type': 'Individual', 'notes': 'Named individual contribution listed in the filing.'}, {'donor': 'EDWARD COTUGNO', 'amount': 100.0, 'type': 'Individual', 'notes': 'Named individual contribution listed in the filing.'}]}, 'house-50-stephen-casey': {'top_donors': [{'donor': 'Daniel Abram', 'amount': 2000.0, 'type': 'Individual', 'notes': 'Employer listed as Self Employed.'}, {'donor': 'Douglas E', 'amount': 1500.0, 'type': 'Individual', 'notes': 'Employer listed as Lord.'}, {'donor': 'RI STATE ASSOCIATION OF FIREFIGHTERS', 'amount': 1000.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'Ralph Palumbo', 'amount': 1000.0, 'type': 'Individual', 'notes': 'Employer listed as Revity Energy.'}, {'donor': 'Stephen V', 'amount': 750.0, 'type': 'Individual', 'notes': 'Employer listed as Ceceri New England Property Services.'}, {'donor': 'Carol A', 'amount': 500.0, 'type': 'Individual', 'notes': 'Employer listed as Odonnell Emerald Reconstruction.'}, {'donor': 'IUOE LOCAL 57 (International Union of Operating Engineers)', 'amount': 500.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'JOHNSTON ASSOCIATION FIREFIGHTERS LOCAL 1950', 'amount': 500.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}, {'donor': 'Karl A', 'amount': 500.0, 'type': 'Individual', 'notes': 'Employer listed as Wadensten Vibco.'}, {'donor': 'RHODE ISLAND COALITION OF HOUSING PROVIDERS', 'amount': 500.0, 'type': 'PAC', 'notes': 'Named PAC contribution listed in the filing.'}]}, 'house-23-william-muto': {'top_donors': [{'donor': 'Friends of', 'amount': 550.0, 'type': 'Individual', 'notes': 'Employer listed as Sal DeLuise.'}, {'donor': 'John F', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as Muto.'}, {'donor': 'Peter C', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as Dorsey Jr.'}, {'donor': 'Robert Smith', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as peter pan bus lines.'}, {'donor': 'Steven V', 'amount': 250.0, 'type': 'Individual', 'notes': 'Employer listed as Ceceri.'}, {'donor': 'Earl L', 'amount': 200.0, 'type': 'Individual', 'notes': 'Employer listed as Simson.'}, {'donor': 'Joseph H', 'amount': 200.0, 'type': 'Individual', 'notes': 'Employer listed as Crowley.'}, {'donor': 'Matthew LaMountain', 'amount': 200.0, 'type': 'Individual', 'notes': 'Employer listed as Self Employeed.'}, {'donor': 'Anthony R', 'amount': 150.0, 'type': 'Individual', 'notes': 'Employer listed as Thompson.'}, {'donor': 'Dana Carlow', 'amount': 150.0, 'type': 'Individual', 'notes': 'Named individual contribution listed in the filing.'}]}}

def apply_profile_detail_overrides(profile: dict[str, object]) -> dict[str, object]:
    override = PROFILE_DETAIL_OVERRIDES.get(str(profile.get("candidate_id", "")))
    if not override:
        return profile
    for field in ("top_donors", "spending_categories", "source_buckets"):
        if not profile.get(field) and override.get(field):
            profile[field] = override[field]
    return profile


# Manual Q2 detail override for Andrew R. Dimitri (RI BOE key 9740).
# Source: 2026 Q2 CF-2 / CF-3 / CF-4 filing.
ANDREW_R_DIMITRI_DETAIL_OVERRIDE = {'source_buckets': [{'label': 'Itemized individual donors',
                     'class_name': 'itemized-individual-donors',
                     'amount': 40075.0,
                     'description': 'Named contributors reported individually in the filing.'},
                    {'label': 'PAC contributions',
                     'class_name': 'pac-contributions',
                     'amount': 8750.0,
                     'description': 'Political committees and PACs listed in the filing.'}],
 'top_donors': [{'donor': 'Thomas Badway',
                 'amount': 2000.0,
                 'type': 'Individual',
                 'notes': 'Employer listed as Law Offices of Thomas E. Badway.'},
                {'donor': 'William C. Dimitri',
                 'amount': 2000.0,
                 'type': 'Individual',
                 'notes': 'Employer listed as William C. Dimitri Law Office.'},
                {'donor': 'Gerard Disanto',
                 'amount': 2000.0,
                 'type': 'Individual',
                 'notes': 'Employer listed as Retired.'},
                {'donor': 'Anthony Minutelli Jr.',
                 'amount': 2000.0,
                 'type': 'Individual',
                 'notes': 'Employer listed as Minutelli Law Firm.'},
                {'donor': 'Johnston Association Firefighters Local 1950',
                 'amount': 1500.0,
                 'type': 'PAC',
                 'notes': 'Named PAC contribution listed in the filing.'},
                {'donor': 'Thomas G. Casale',
                 'amount': 1000.0,
                 'type': 'Individual',
                 'notes': 'Employer listed as Casale Auto Body.'},
                {'donor': 'Antonio P. Cassisi',
                 'amount': 1000.0,
                 'type': 'Individual',
                 'notes': 'Employer listed as Cassisi Construction.'},
                {'donor': 'Frank Cassisi',
                 'amount': 1000.0,
                 'type': 'Individual',
                 'notes': 'Employer listed as Cassisi Construction.'},
                {'donor': 'Eddie DiRocco',
                 'amount': 1000.0,
                 'type': 'Individual',
                 'notes': 'Employer listed as DiRocco & Sons Inc.'},
                {'donor': 'John H. Petrarca',
                 'amount': 1000.0,
                 'type': 'Individual',
                 'notes': 'Employer listed as Providence Auto Body.'}],
 'spending_categories': [{'title': 'Consultant & Professional Services',
                          'summary': 'Visible spending includes Checkmate Consulting Group, LLC.',
                          'amount': 6942.07},
                         {'title': 'Fundraising Expenses',
                          'summary': 'Visible spending includes Coast to Coast Promotional Products, Market '
                                     "Basket, and Silvio's.",
                          'amount': 4091.7},
                         {'title': 'Advertising',
                          'summary': 'Visible spending includes Warwick Beacon.',
                          'amount': 1216.32},
                         {'title': 'Donations (All Others)',
                          'summary': "Visible spending includes Johnston Little League, Slack's Reservoir "
                                     "Association, and St. Rocco's Church.",
                          'amount': 1050.0},
                         {'title': 'Donations (Political)',
                          'summary': 'Visible spending includes Friends of Lea J. Bosclair and Friends of '
                                     'Leonidas P. Raptakis.',
                          'amount': 1000.0},
                         {'title': 'Bank Fees',
                          'summary': 'Visible spending includes ActBlue.',
                          'amount': 231.46}]}

def apply_andrew_dimitri_detail_override(profile: dict[str, object]) -> dict[str, object]:
    if str(profile.get("candidate_id", "")) != "senate-25-andrew-r-dimitri":
        return profile
    profile["source_buckets"] = ANDREW_R_DIMITRI_DETAIL_OVERRIDE["source_buckets"]
    profile["top_donors"] = ANDREW_R_DIMITRI_DETAIL_OVERRIDE["top_donors"]
    profile["spending_categories"] = ANDREW_R_DIMITRI_DETAIL_OVERRIDE["spending_categories"]
    return profile


# Manual filing-detail overrides for Ana B. Quezada and Samuel W. Bell.
# Ana Quezada: Q1 2026 filing only; Q2 is past due.
# Samuel Bell: Q1 and Q2 2026 filings.
QUEZADA_BELL_PROFILE_OVERRIDES = {'senate-2-ana-b-quezada': {'report_label': 'Q1 2026 campaign finance filing',
                            'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                            'source_note': 'RI Board of Elections Q1 2026 CF-2 / CF-3 / CF-4 filing',
                            'coverage_note': 'Q1 2026 filing only. Q2 2026 report is past due and is not represented '
                                             'as a filed report.',
                            'beginning_cash': 4854.44,
                            'money_raised': 1000.0,
                            'money_spent': 3429.98,
                            'ending_cash': 2424.46,
                            'net_change': -2429.98,
                            'total_cash_receipts': 1000.0,
                            'campaign_expenses': 3168.98,
                            'aggregate_expenses': 261.0,
                            'summary_intro': 'The latest filed report available for Ana B Quezada is the Q1 2026 '
                                             'report. It shows $1,000.00 in other reported receipts, $3,429.98 in '
                                             'total spending, and $2,424.46 in cash on hand at the end of the '
                                             'period. A Q2 2026 report has not been filed and is past due.',
                            'filing_history': [{'label': 'Q1 2026',
                                                'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                'money_raised': 1000.0,
                                                'money_spent': 3429.98,
                                                'ending_cash': 2424.46,
                                                'net_change': -2429.98,
                                                'notes': 'The filing reports a $1,000 corporate check as an Other '
                                                         'Receipt, described as incorrectly deposited and to be '
                                                         'refunded. Q2 2026 is past due.'}],
                            'source_buckets': [{'label': 'Other reported sources',
                                                'class_name': 'other-reported-sources',
                                                'amount': 1000.0,
                                                'description': 'The Q1 filing reports a $1,000 Other Receipt '
                                                               'described as a corporate check that was incorrectly '
                                                               'deposited and scheduled to be refunded.'}],
                            'top_donors': [],
                            'spending_categories': [{'title': 'Donations (All Others)',
                                                     'summary': 'Visible spending includes Fundacion Global De '
                                                                'Desarollo, Assumption Church, DIHACRI, and Woman '
                                                                'Development Institute.',
                                                     'amount': 2400.0},
                                                    {'title': 'Travel & Lodging',
                                                     'summary': 'Visible spending includes travel to Washington, '
                                                                'D.C. through American Airlines, Travelocity, and a '
                                                                'Hilton Garden expense.',
                                                     'amount': 475.88},
                                                    {'title': 'Other',
                                                     'summary': 'Visible spending includes USPS postage.',
                                                     'amount': 216.0},
                                                    {'title': 'Fundraising Expenses',
                                                     'summary': 'Visible spending includes AmazonPrime supplies for '
                                                                'a fundraiser.',
                                                     'amount': 138.1},
                                                    {'title': 'Advertising',
                                                     'summary': 'Visible spending includes Friends of Pedro Espinal.',
                                                     'amount': 100.0},
                                                    {'title': 'Donations (Political)',
                                                     'summary': 'Visible spending includes Friends of Jonathan '
                                                                'Acosta.',
                                                     'amount': 100.0}]},
 'senate-5-samuel-w-bell': {'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                            'coverage_note': 'Q1 and Q2 2026 filings available. The Q2 CF-2 reports $13,159 from '
                                             'individuals and $1,000 from PACs, but the attached CF-3 contributor '
                                             'schedule does not list individual donor names.',
                            'beginning_cash': 53612.41,
                            'money_raised': 14159.0,
                            'money_spent': 4840.35,
                            'ending_cash': 62931.06,
                            'net_change': 9318.65,
                            'total_cash_receipts': 14159.0,
                            'campaign_expenses': 4840.35,
                            'aggregate_expenses': 0.0,
                            'summary_intro': "Samuel W Bell's Q2 2026 filing reports $14,159.00 in receipts, "
                                             'including $13,159.00 from individuals and $1,000.00 from PACs. The '
                                             'campaign reported $4,840.35 in campaign expenses and closed the period '
                                             'with $62,931.06 in cash on hand.',
                            'filing_history': [{'label': 'Q1 2026',
                                                'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                'money_raised': 7079.0,
                                                'money_spent': 675.11,
                                                'ending_cash': 53612.41,
                                                'net_change': 6403.89,
                                                'notes': 'Q1 reported $6,879 from individuals and $200 from PACs.'},
                                               {'label': 'Q2 2026',
                                                'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                'money_raised': 14159.0,
                                                'money_spent': 4840.35,
                                                'ending_cash': 62931.06,
                                                'net_change': 9318.65,
                                                'notes': 'Q2 reported $13,159 from individuals and $1,000 from PACs. '
                                                         'The attached CF-3 contributor schedule contains no named '
                                                         'donor entries.'}],
                            'source_buckets': [{'label': 'Itemized individual donors',
                                                'class_name': 'itemized-individual-donors',
                                                'amount': 13159.0,
                                                'description': 'The Q2 CF-2 summary reports $13,159.00 from '
                                                               'individuals. The attached CF-3 contributor schedule '
                                                               'does not display named donor entries.'},
                                               {'label': 'PAC contributions',
                                                'class_name': 'pac-contributions',
                                                'amount': 1000.0,
                                                'description': 'The Q2 CF-2 summary reports $1,000.00 from political '
                                                               'action committees. The attached CF-3 contributor '
                                                               'schedule does not display named PAC entries.'}],
                            'top_donors': [],
                            'spending_categories': [{'title': 'Bank Fees',
                                                     'summary': 'The Q2 CF-4 schedule lists an ActBlue bank-fee '
                                                                'entry of $468.77.',
                                                     'amount': 468.77},
                                                    {'title': 'Other campaign expenses not itemized on attached CF-4',
                                                     'summary': 'The Q2 CF-2 reports $4,840.35 in total campaign '
                                                                'expenses, while the attached CF-4 page itemizes '
                                                                'only the $468.77 ActBlue bank-fee entry. The '
                                                                'remainder is shown separately rather than assigned '
                                                                'to an unsupported category.',
                                                     'amount': 4371.58}]}}

def apply_quezada_bell_profile_overrides(profile: dict[str, object]) -> dict[str, object]:
    override = QUEZADA_BELL_PROFILE_OVERRIDES.get(str(profile.get("candidate_id", "")))
    if not override:
        return profile
    profile.update(override)
    return profile


# Manual follow-up overrides:
# - Samuel W. Bell latest uploaded filing (07/01/2026–08/11/2026), including named donors.
# - Andrew R. Dimitri Q1 filing added to filing history.
BELL_DIMITRI_FOLLOWUP_OVERRIDES = {'senate-25-andrew-r-dimitri': {'filing_history': [{'label': 'Q1 2026',
                                                    'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                    'money_raised': 450.0,
                                                    'money_spent': 1482.84,
                                                    'ending_cash': 9577.96,
                                                    'net_change': -1032.84,
                                                    'notes': 'Q1 receipts consisted of $450.00 in interest from '
                                                             'Washington Trust. Q1 expenses were $1,482.84.',
                                                    'source_buckets': [{'label': 'Other reported sources',
                                                                        'class_name': 'other-reported-sources',
                                                                        'amount': 450.0,
                                                                        'description': 'Interest received from '
                                                                                       'Washington Trust during Q1 '
                                                                                       '2026.'}],
                                                    'top_donors': [],
                                                    'spending_categories': [{'title': 'Consultant & Professional '
                                                                                      'Services',
                                                                             'summary': 'Visible spending includes '
                                                                                        'Checkmate Consulting Group, '
                                                                                        'LLC.',
                                                                             'amount': 1259.41},
                                                                            {'title': 'Food, Beverages and Meals',
                                                                             'summary': 'Visible spending includes '
                                                                                        'Capital Grille for a '
                                                                                        'meeting with '
                                                                                        'representatives.',
                                                                             'amount': 176.88},
                                                                            {'title': 'Fundraising Expenses',
                                                                             'summary': 'Visible spending includes '
                                                                                        'Market Basket for coffee '
                                                                                        'and pastry for a '
                                                                                        'fundraiser.',
                                                                             'amount': 44.12},
                                                                            {'title': 'Bank Fees',
                                                                             'summary': 'Visible spending includes '
                                                                                        'ActBlue.',
                                                                             'amount': 2.43}]},
                                                   {'label': 'Q2 2026',
                                                    'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                    'money_raised': 48825.0,
                                                    'money_spent': 14531.55,
                                                    'ending_cash': 43871.41,
                                                    'net_change': 34293.45,
                                                    'notes': 'The campaign raised more than it spent in this '
                                                             'reporting period.'}],
                                'coverage_note': 'Q1 and Q2 2026 filings available. The profile headline and Top '
                                                 'Donors/Funding Mix/Spending Breakdown continue to use Q2; Q1 '
                                                 'details are retained in filing history.'},
 'senate-5-samuel-w-bell': {'report_label': '2026 filing through August 11',
                            'reporting_period_label': 'July 1, 2026 to August 11, 2026',
                            'source_note': 'RI Board of Elections filing covering July 1, 2026 through August 11, '
                                           '2026',
                            'coverage_note': "The profile now uses Bell's latest uploaded filing, covering July 1 "
                                             'through August 11, 2026. Q1 and Q2 2026 remain in filing history.',
                            'beginning_cash': 62931.06,
                            'money_raised': 3668.0,
                            'money_spent': 7548.69,
                            'ending_cash': 59050.37,
                            'net_change': -3880.69,
                            'total_cash_receipts': 3668.0,
                            'campaign_expenses': 7548.69,
                            'aggregate_expenses': 0.0,
                            'summary_intro': "Samuel W Bell's latest uploaded filing covers July 1 through August "
                                             '11, 2026. It reports $3,668.00 in receipts, including $3,618.00 from '
                                             'individuals and $50.00 from a PAC. The campaign reported $7,548.69 in '
                                             'expenses and closed the period with $59,050.37 in cash on hand.',
                            'source_buckets': [{'label': 'Itemized individual donors',
                                                'class_name': 'itemized-individual-donors',
                                                'amount': 3618.0,
                                                'description': 'Named individual contributions reported in the July '
                                                               '1–August 11 filing.'},
                                               {'label': 'PAC contributions',
                                                'class_name': 'pac-contributions',
                                                'amount': 50.0,
                                                'description': 'PAC contribution reported in the July 1–August 11 '
                                                               'filing.'}],
                            'top_donors': [{'donor': 'Olin Thompson',
                                            'amount': 1000.0,
                                            'type': 'Individual',
                                            'notes': 'Named individual contribution listed in the '
                                                     '07/01/2026–08/11/2026 filing.'},
                                           {'donor': 'Anne De Groot',
                                            'amount': 500.0,
                                            'type': 'Individual',
                                            'notes': 'Employer listed as EVA Therapeutics.'},
                                           {'donor': 'Val Lawson',
                                            'amount': 500.0,
                                            'type': 'Individual',
                                            'notes': 'Employer listed as NEA RI.'},
                                           {'donor': 'Russ Mayerfeld',
                                            'amount': 250.0,
                                            'type': 'Individual',
                                            'notes': 'Named individual contribution listed in the filing.'},
                                           {'donor': 'Francis Richards',
                                            'amount': 250.0,
                                            'type': 'Individual',
                                            'notes': 'Employer listed as retired.'},
                                           {'donor': 'David Stuebe',
                                            'amount': 218.0,
                                            'type': 'Individual',
                                            'notes': 'Two contributions in the filing ($200 and $18); employer '
                                                     'listed as RPS ASA.'},
                                           {'donor': 'Daria Brashear',
                                            'amount': 100.0,
                                            'type': 'Individual',
                                            'notes': 'Employer listed as AuriStor, Inc.'},
                                           {'donor': 'John Chamblee',
                                            'amount': 100.0,
                                            'type': 'Individual',
                                            'notes': 'Employer listed as Amica Inc.'},
                                           {'donor': 'Brooke Churas',
                                            'amount': 100.0,
                                            'type': 'Individual',
                                            'notes': 'Employer listed as Sunrise Properties.'},
                                           {'donor': 'Keith Fernandes',
                                            'amount': 100.0,
                                            'type': 'Individual',
                                            'notes': 'Employer listed as self employed.'}],
                            'spending_categories': [{'title': 'Consultant & Professional Services',
                                                     'summary': 'Visible spending includes Capri Catanzaro for '
                                                                'campaign management and Oscar Pearlman for '
                                                                'canvassing.',
                                                     'amount': 5100.0},
                                                    {'title': 'Advertising',
                                                     'summary': 'Visible spending includes Signrocket yard signs.',
                                                     'amount': 1382.5},
                                                    {'title': 'Refunds/Reimbursements',
                                                     'summary': 'Visible spending includes an over-limit '
                                                                'contribution refund to Olin Thompson and smaller '
                                                                'reimbursements.',
                                                     'amount': 1066.19},
                                                    {'title': 'Other campaign expenses not itemized on attached CF-4',
                                                     'summary': 'The CF-2 reports $7,548.69 in campaign expenses. '
                                                                'The attached CF-4 pages itemize $8,148.69 in '
                                                                'positive entries, including a $1,000 contribution '
                                                                'refund; this category is not used to force a '
                                                                'reconciliation because the filing itself should be '
                                                                'preserved as reported.',
                                                     'amount': 0.0}],
                            'filing_history': [{'label': 'Q1 2026',
                                                'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                'money_raised': 7079.0,
                                                'money_spent': 675.11,
                                                'ending_cash': 53612.41,
                                                'net_change': 6403.89,
                                                'notes': 'Q1 reported $6,879 from individuals and $200 from PACs.'},
                                               {'label': 'Q2 2026',
                                                'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                'money_raised': 14159.0,
                                                'money_spent': 4840.35,
                                                'ending_cash': 62931.06,
                                                'net_change': 9318.65,
                                                'notes': 'Q2 reported $13,159 from individuals and $1,000 from PACs. '
                                                         'The attached CF-3 contributor schedule contains no named '
                                                         'donor entries.'},
                                               {'label': 'July 1–August 11, 2026',
                                                'reporting_period_label': 'July 1, 2026 to August 11, 2026',
                                                'money_raised': 3668.0,
                                                'money_spent': 7548.69,
                                                'ending_cash': 59050.37,
                                                'net_change': -3880.69,
                                                'notes': 'Latest uploaded filing; includes named donors and a $50 '
                                                         'PAC contribution.'}]}}

def apply_bell_dimitri_followup_overrides(profile: dict[str, object]) -> dict[str, object]:
    override = BELL_DIMITRI_FOLLOWUP_OVERRIDES.get(str(profile.get("candidate_id", "")))
    if not override:
        return profile
    profile.update(override)
    return profile


# Final standardized main-display override for Samuel W. Bell.
# Q2 2026 remains the headline period for comparability; later primary-period filings stay in filing history.
SAMUEL_BELL_Q2_MAIN_OVERRIDE = {'report_label': 'Q2 2026 campaign finance filing',
 'reporting_period_label': 'April 1, 2026 to June 30, 2026',
 'source_note': 'RI Board of Elections Q2 2026 CF-2 / CF-3 / CF-4 filing',
 'coverage_note': "Q2 2026 is used as the main display period for comparability across candidates. Bell's later July "
                  '1–August 11 filing is retained in filing history but does not replace the Q2 headline.',
 'beginning_cash': 53612.41,
 'money_raised': 14159.0,
 'money_spent': 4840.35,
 'ending_cash': 62931.06,
 'net_change': 9318.65,
 'total_cash_receipts': 14159.0,
 'campaign_expenses': 4371.58,
 'aggregate_expenses': 468.77,
 'summary_intro': "Samuel W Bell's Q2 2026 filing reports $14,159.00 in receipts, including $13,159.00 from "
                  'individuals and $1,000.00 from PACs. The campaign reported $4,840.35 in total spending and closed '
                  'the period with $62,931.06 in cash on hand.',
 'source_buckets': [{'label': 'Itemized individual donors',
                     'class_name': 'itemized-individual-donors',
                     'amount': 13159.0,
                     'description': "Named individual contributions reported in Bell's Q2 2026 filing."},
                    {'label': 'PAC contributions',
                     'class_name': 'pac-contributions',
                     'amount': 1000.0,
                     'description': "Political action committee contributions reported in Bell's Q2 2026 filing."}],
 'top_donors': [{'donor': 'Samuel W Bell',
                 'amount': 2000.0,
                 'type': 'Individual',
                 'notes': 'Candidate contribution listed in the Q2 filing; employer listed as Planetary Science '
                          'Institute.'},
                {'donor': 'Samantha Weiser',
                 'amount': 2000.0,
                 'type': 'Individual',
                 'notes': 'Employer listed as CreXo.'},
                {'donor': 'Daniel Abram',
                 'amount': 1950.0,
                 'type': 'Individual',
                 'notes': 'Named individual contribution listed in the Q2 filing.'},
                {'donor': 'Carolyn Weiser',
                 'amount': 1000.0,
                 'type': 'Individual',
                 'notes': 'Employer listed as Granby Public Schools.'},
                {'donor': 'Val Lawson', 'amount': 500.0, 'type': 'Individual', 'notes': 'Employer listed as NEA RI.'},
                {'donor': 'Richard St Germain',
                 'amount': 500.0,
                 'type': 'Individual',
                 'notes': 'Named individual contribution listed in the Q2 filing.'},
                {'donor': 'Brian Heller',
                 'amount': 300.0,
                 'type': 'Individual',
                 'notes': 'Named individual contribution listed in the Q2 filing.'},
                {'donor': 'Louis DiPalma',
                 'amount': 250.0,
                 'type': 'Individual',
                 'notes': 'Employer listed as Raytheon.'},
                {'donor': 'Francis Richards',
                 'amount': 250.0,
                 'type': 'Individual',
                 'notes': 'Employer listed as retired.'},
                {'donor': 'United Food & Commercial Workers Union Local 328 RI PAC',
                 'amount': 250.0,
                 'type': 'PAC',
                 'notes': 'Named PAC contribution listed in the Q2 filing.'}],
 'spending_categories': [{'title': 'Consultant & Professional Services',
                          'summary': 'Visible spending includes Capri Catanzaro for campaign management.',
                          'amount': 1800.0},
                         {'title': 'Other',
                          'summary': 'Visible spending includes Signrocket yard signs and an Elmhurst Youth Baseball '
                                     'sponsorship.',
                          'amount': 1625.0},
                         {'title': 'Advertising',
                          'summary': 'Aggregate ActBlue fees reported as advertising on the Q2 expenditure schedule.',
                          'amount': 468.77},
                         {'title': 'Donations (Political)',
                          'summary': 'Visible spending includes two contributions to Friends of Amy Santiago.',
                          'amount': 350.0},
                         {'title': 'Food, Beverages and Meals',
                          'summary': "Visible spending includes Patrick's Pub for fundraiser food.",
                          'amount': 307.2},
                         {'title': 'Refunds/Reimbursements',
                          'summary': 'Visible spending includes reimbursement to Henry Perretta for a stamp '
                                     'purchase.',
                          'amount': 289.38}],
 'filing_history': [{'label': 'Q1 2026',
                     'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                     'money_raised': 7079.0,
                     'money_spent': 675.11,
                     'ending_cash': 53612.41,
                     'net_change': 6403.89,
                     'notes': 'Q1 reported $6,879 from individuals and $200 from PACs.'},
                    {'label': 'Q2 2026',
                     'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                     'money_raised': 14159.0,
                     'money_spent': 4840.35,
                     'ending_cash': 62931.06,
                     'net_change': 9318.65,
                     'notes': 'Q2 is the standardized main display period. Named Q2 donors and detailed spending are '
                              'available.'},
                    {'label': 'July 1–August 11, 2026',
                     'reporting_period_label': 'July 1, 2026 to August 11, 2026',
                     'money_raised': 3668.0,
                     'money_spent': 7548.69,
                     'ending_cash': 59050.37,
                     'net_change': -3880.69,
                     'notes': 'Latest uploaded filing; includes named donors and a $50 PAC contribution.'}]}

def apply_samuel_bell_q2_main_override(profile: dict[str, object]) -> dict[str, object]:
    if str(profile.get("candidate_id", "")) != "senate-5-samuel-w-bell":
        return profile
    profile.update(SAMUEL_BELL_Q2_MAIN_OVERRIDE)
    return profile


# Standardized Q2 main-display overrides for William D. Connell Jr. and Tiara T. Mack.
# Source: official Rhode Island Board of Elections Q1/Q2 2026 filings.
CONNELL_MACK_Q2_OVERRIDES = {'senate-5-william-d-connell-jr': {'report_label': 'Q2 2026 campaign finance filing',
                                   'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                   'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                                   'coverage_note': 'Q2 2026 is used as the main display period for comparability '
                                                    'across candidates. Connell reported no individual or PAC '
                                                    'contributions and no expenditures in Q2; the only Q2 receipt '
                                                    'was $0.06 in interest.',
                                   'beginning_cash': 422.64,
                                   'money_raised': 0.06,
                                   'money_spent': 0.0,
                                   'ending_cash': 422.7,
                                   'net_change': 0.06,
                                   'total_cash_receipts': 0.06,
                                   'campaign_expenses': 0.0,
                                   'aggregate_expenses': 0.0,
                                   'summary_intro': "William D Connell Jr.'s Q2 2026 filing reports $0.06 in "
                                                    'interest receipts, no campaign spending, and $422.70 in cash on '
                                                    'hand at the end of the period.',
                                   'source_buckets': [{'label': 'Other reported sources',
                                                       'class_name': 'other-reported-sources',
                                                       'amount': 0.06,
                                                       'description': 'Interest received from Navigant Credit Union '
                                                                      'during Q2 2026.'}],
                                   'top_donors': [],
                                   'spending_categories': [],
                                   'filing_history': [{'label': 'Q1 2026',
                                                       'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                       'money_raised': 0.07,
                                                       'money_spent': 217.79,
                                                       'ending_cash': 422.64,
                                                       'net_change': -217.72,
                                                       'notes': 'Q1 receipts consisted of $0.07 in interest. Q1 '
                                                                'spending of $217.79 consisted of political '
                                                                'donations.'},
                                                      {'label': 'Q2 2026',
                                                       'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                       'money_raised': 0.06,
                                                       'money_spent': 0.0,
                                                       'ending_cash': 422.7,
                                                       'net_change': 0.06,
                                                       'notes': 'Q2 receipts consisted solely of $0.06 in interest; '
                                                                'no Q2 expenditures were reported.'}]},
 'senate-6-tiara-t-mack': {'report_label': 'Q2 2026 campaign finance filing',
                           'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                           'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                           'coverage_note': 'Q2 2026 is used as the main display period for comparability across '
                                            'candidates. Detailed Q2 contributors and expenditures are available.',
                           'beginning_cash': 4593.86,
                           'money_raised': 7154.01,
                           'money_spent': 4055.89,
                           'ending_cash': 7691.98,
                           'net_change': 3098.12,
                           'total_cash_receipts': 7154.01,
                           'campaign_expenses': 4055.89,
                           'aggregate_expenses': 0.0,
                           'summary_intro': "Tiara T Mack's Q2 2026 filing reports $7,154.01 in receipts, including "
                                            '$6,854.01 from individuals and $300.00 from PACs. The campaign reported '
                                            '$4,055.89 in spending and closed the period with $7,691.98 in cash on '
                                            'hand.',
                           'source_buckets': [{'label': 'Itemized individual donors',
                                               'class_name': 'itemized-individual-donors',
                                               'amount': 6854.01,
                                               'description': "Named individual contributions reported in Mack's Q2 "
                                                              '2026 filing.'},
                                              {'label': 'PAC contributions',
                                               'class_name': 'pac-contributions',
                                               'amount': 300.0,
                                               'description': 'Political action committee contributions reported in '
                                                              "Mack's Q2 2026 filing."}],
                           'top_donors': [{'donor': 'James Kingston',
                                           'amount': 1000.0,
                                           'type': 'Individual',
                                           'notes': 'Employer listed as retired.'},
                                          {'donor': 'Brett Smiley',
                                           'amount': 250.0,
                                           'type': 'Individual',
                                           'notes': 'Named individual contribution listed in the filing.'},
                                          {'donor': 'Jessie Kingston',
                                           'amount': 250.0,
                                           'type': 'Individual',
                                           'notes': 'Employer listed as Not Employed.'},
                                          {'donor': 'Richard McAuliffe',
                                           'amount': 250.0,
                                           'type': 'Individual',
                                           'notes': 'Employer listed as Mayforth Group.'},
                                          {'donor': 'Steven Ceceri',
                                           'amount': 250.0,
                                           'type': 'Individual',
                                           'notes': 'Named individual contribution listed in the filing.'},
                                          {'donor': 'Anne Belzowski',
                                           'amount': 200.0,
                                           'type': 'Individual',
                                           'notes': 'Employer listed as Physician.'},
                                          {'donor': 'Joshua Miller',
                                           'amount': 200.0,
                                           'type': 'Individual',
                                           'notes': 'Employer listed as Trinity Brewhouse.'},
                                          {'donor': 'Keith Hoffmann',
                                           'amount': 200.0,
                                           'type': 'Individual',
                                           'notes': 'Employer listed as Not Employed.'},
                                          {'donor': 'Margaret DeVos',
                                           'amount': 200.0,
                                           'type': 'Individual',
                                           'notes': 'Employer listed as SouthSide Community Landtrust.'},
                                          {'donor': 'Christopher Stark',
                                           'amount': 150.0,
                                           'type': 'Individual',
                                           'notes': 'Employer listed as RI Insurance Federation.'}],
                           'spending_categories': [{'title': 'Travel & Lodging',
                                                    'summary': 'Visible spending includes American Airlines, Amtrak, '
                                                               'Lyft.',
                                                    'amount': 1530.04},
                                                   {'title': 'Fundraising Expenses',
                                                    'summary': 'Visible spending includes Regine Printing Co Inc, '
                                                               'The Villiage PVD.',
                                                    'amount': 1413.35},
                                                   {'title': 'Office Equipment & Supplies',
                                                    'summary': 'Visible spending includes Action Network, Square '
                                                               'Space, staples.',
                                                    'amount': 518.0},
                                                   {'title': 'Donations (Political)',
                                                    'summary': 'Visible spending includes Brad Lander, Gregg Amore.',
                                                    'amount': 300.0},
                                                   {'title': 'Donations (All Others)',
                                                    'summary': 'Visible spending includes Amos House, GLBTQ '
                                                               'Defenders.',
                                                    'amount': 159.3},
                                                   {'title': 'Food, Beverages and Meals',
                                                    'summary': 'Visible spending includes Dominoes, Rise N Shine Co, '
                                                               'Wild Flower.',
                                                    'amount': 76.64},
                                                   {'title': 'Bank Fees',
                                                    'summary': 'Visible spending includes Act Blue, ActBlue.',
                                                    'amount': 58.56}],
                           'filing_history': [{'label': 'Q1 2026',
                                               'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                               'money_raised': 3460.01,
                                               'money_spent': 3645.35,
                                               'ending_cash': 4593.86,
                                               'net_change': -185.34,
                                               'notes': 'Q1 reported $3,360.01 from individuals and $100.00 from '
                                                        'PACs.'},
                                              {'label': 'Q2 2026',
                                               'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                               'money_raised': 7154.01,
                                               'money_spent': 4055.89,
                                               'ending_cash': 7691.98,
                                               'net_change': 3098.12,
                                               'notes': 'Q2 reported $6,854.01 from individuals and $300.00 from '
                                                        'PACs.'}]}}

def apply_connell_mack_q2_overrides(profile: dict[str, object]) -> dict[str, object]:
    override = CONNELL_MACK_Q2_OVERRIDES.get(str(profile.get("candidate_id", "")))
    if not override:
        return profile
    profile.update(override)
    return profile


# Standardized Q2 main-display overrides for Frank A. Ciccone, Walter S. Felag Jr., and Linda L. Ujifusa.
# Source: official Rhode Island Board of Elections Q1/Q2 2026 filings.
CICCONE_FELAG_UJIFUSA_Q2_OVERRIDES = {'senate-7-frank-a-ciccone': {'report_label': 'Q2 2026 campaign finance filing',
                              'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                              'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                              'coverage_note': 'Q2 2026 is used as the main display period for comparability across '
                                               'candidates. Detailed Q2 contributors and expenditures are available.',
                              'beginning_cash': 172099.81,
                              'money_raised': 133184.26,
                              'money_spent': 34943.66,
                              'ending_cash': 270340.41,
                              'net_change': 98240.6,
                              'total_cash_receipts': 133184.26,
                              'campaign_expenses': 34943.66,
                              'aggregate_expenses': 0.0,
                              'summary_intro': "Frank A Ciccone's Q2 2026 filing reports $133,184.26 in receipts and "
                                               '$34,943.66 in spending. The campaign closed the period with '
                                               '$270,340.41 in cash on hand.',
                              'source_buckets': [{'label': 'Itemized individual donors',
                                                  'class_name': 'itemized-individual-donors',
                                                  'amount': 107500.0,
                                                  'description': 'Named individual contributions reported in '
                                                                 "Ciccone's Q2 2026 filing."},
                                                 {'label': 'Receipts without donor names listed',
                                                  'class_name': 'small-dollar-aggregate-online-receipts',
                                                  'amount': 8400.0,
                                                  'description': 'Aggregate individual receipts reported without '
                                                                 'individual donor names.'},
                                                 {'label': 'PAC contributions',
                                                  'class_name': 'pac-contributions',
                                                  'amount': 15002.9,
                                                  'description': 'Political action committee contributions reported '
                                                                 "in Ciccone's Q2 2026 filing."},
                                                 {'label': 'Refunds / rebates',
                                                  'class_name': 'refunds-rebates',
                                                  'amount': 2281.36,
                                                  'description': 'Refund or rebate receipts reported in the Q2 '
                                                                 'filing.'}],
                              'top_donors': [{'donor': 'Joseph R. Vinagro',
                                              'amount': 3000.0,
                                              'type': 'Individual',
                                              'notes': 'Employer listed as VINAGRO JR VINAGRO.'},
                                             {'donor': 'DONNA SANTORO',
                                              'amount': 2250.0,
                                              'type': 'Individual',
                                              'notes': 'Employer listed as HOUSEWIFE.'},
                                             {'donor': 'Michael P. Petrarca',
                                              'amount': 2250.0,
                                              'type': 'Individual',
                                              'notes': 'Employer listed as PETRARCA COLLISION PROS.'},
                                             {'donor': 'Adam C. Sepe',
                                              'amount': 2000.0,
                                              'type': 'Individual',
                                              'notes': 'Employer listed as SEPE NORTH EASTERN TREE.'},
                                             {'donor': 'Angelica A. Colafrancesco',
                                              'amount': 2000.0,
                                              'type': 'Individual',
                                              'notes': 'Employer listed as COLAFRANCESCO DEAN AUTO BODY.'},
                                             {'donor': 'CARLOS A',
                                              'amount': 2000.0,
                                              'type': 'Individual',
                                              'notes': 'Employer listed as REGO REGO AUTO BODY.'},
                                             {'donor': 'CLARITZA CASALE',
                                              'amount': 2000.0,
                                              'type': 'Individual',
                                              'notes': 'Employer listed as HOUSEWIFE.'},
                                             {'donor': 'DANIEL RYAN',
                                              'amount': 2000.0,
                                              'type': 'Individual',
                                              'notes': 'Employer listed as RETIRED.'},
                                             {'donor': 'David W. Hayes',
                                              'amount': 2000.0,
                                              'type': 'Individual',
                                              'notes': 'Employer listed as HAYES D & H COLLISION SERVICE.'},
                                             {'donor': 'Gerard C. Disanto II',
                                              'amount': 2000.0,
                                              'type': 'Individual',
                                              'notes': 'Employer listed as DISANTO II SPEC SOURCE LLC.'}],
                              'spending_categories': [{'title': 'Donations (Political)',
                                                       'summary': 'Visible spending includes COMMITTEE TO ELECT LOU '
                                                                  'RAPTAKIS, CORVESE FOR REPRESENTATIVE, FRIENDS '
                                                                  'ALANA DIMARIO.',
                                                       'amount': 8400.0},
                                                      {'title': 'Fundraising Expenses',
                                                       'summary': 'Visible spending includes AURORA CIVIC '
                                                                  "ASSOCIATION, REGINE PRINTING, TOMASELLI'S.",
                                                       'amount': 8375.96},
                                                      {'title': 'Donations (All Others)',
                                                       'summary': 'Visible spending includes ACCESS POINT OF RI, '
                                                                  'AMOS HOUSE, CCRI FOUNDATION.',
                                                       'amount': 8037.16},
                                                      {'title': 'Other',
                                                       'summary': 'Visible spending includes DIGITAL OCEAN.COM, '
                                                                  'DOMAIN NAME SERVICES, GOOGLE SUITE.',
                                                       'amount': 5959.47},
                                                      {'title': 'Food, Beverages and Meals',
                                                       'summary': 'Visible spending includes AISA GRILL, BELLA VISTA '
                                                                  'RESTAURANT, CAPITAL GRILL.',
                                                       'amount': 3176.48},
                                                      {'title': 'Office Equipment & Supplies',
                                                       'summary': 'Visible spending includes AMAZON, POSTMASTER.',
                                                       'amount': 994.59}],
                              'filing_history': [{'label': 'Q1 2026',
                                                  'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                  'money_raised': 77575.25,
                                                  'money_spent': 50911.75,
                                                  'ending_cash': 172099.81,
                                                  'net_change': 26663.5,
                                                  'notes': 'Q1 reported $34,750 from itemized individuals, $20,775 '
                                                           'in aggregate individual receipts, $21,650 from PACs, and '
                                                           '$400.25 in other receipts.'},
                                                 {'label': 'Q2 2026',
                                                  'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                  'money_raised': 133184.26,
                                                  'money_spent': 34943.66,
                                                  'ending_cash': 270340.41,
                                                  'net_change': 98240.6,
                                                  'notes': 'Q2 is the standardized main display period.'}]},
 'senate-10-walter-s-felag-jr': {'report_label': 'Q2 2026 campaign finance filing',
                                 'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                 'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                                 'coverage_note': 'Q2 2026 is used as the main display period for comparability '
                                                  'across candidates. Detailed Q2 contributors and expenditures are '
                                                  'available.',
                                 'beginning_cash': 69329.83,
                                 'money_raised': 6431.74,
                                 'money_spent': 1476.88,
                                 'ending_cash': 74284.69,
                                 'net_change': 4954.86,
                                 'total_cash_receipts': 6431.74,
                                 'campaign_expenses': 379.88,
                                 'aggregate_expenses': 1097.0,
                                 'summary_intro': "Walter S Felag Jr.'s Q2 2026 filing reports $6,431.74 in total "
                                                  'receipts, including individual, aggregate individual, PAC, and '
                                                  'interest receipts. The campaign reported $1,476.88 in total '
                                                  'spending and closed with $74,284.69 in cash on hand.',
                                 'source_buckets': [{'label': 'Itemized individual donors',
                                                     'class_name': 'itemized-individual-donors',
                                                     'amount': 2000.0,
                                                     'description': 'Named individual contributions reported in '
                                                                    "Felag's Q2 filing."},
                                                    {'label': 'Receipts without donor names listed',
                                                     'class_name': 'small-dollar-aggregate-online-receipts',
                                                     'amount': 3675.0,
                                                     'description': 'Aggregate individual contributions reported '
                                                                    'without donor names.'},
                                                    {'label': 'PAC contributions',
                                                     'class_name': 'pac-contributions',
                                                     'amount': 750.0,
                                                     'description': "PAC contributions reported in Felag's Q2 "
                                                                    'filing.'},
                                                    {'label': 'Other reported sources',
                                                     'class_name': 'other-reported-sources',
                                                     'amount': 6.74,
                                                     'description': 'Interest received during Q2 2026.'}],
                                 'top_donors': [{'donor': 'Jane Costanza',
                                                 'amount': 1000.0,
                                                 'type': 'Individual',
                                                 'notes': 'Employer listed as WAKEFIELD LIQUORS.'},
                                                {'donor': 'Ali Amirsadri',
                                                 'amount': 500.0,
                                                 'type': 'Individual',
                                                 'notes': 'Employer listed as House of Liquor.'},
                                                {'donor': 'RI HOSPITALITY PAC',
                                                 'amount': 500.0,
                                                 'type': 'PAC',
                                                 'notes': 'Named PAC contribution listed in the Q2 filing.'},
                                                {'donor': 'Gayle Wolf',
                                                 'amount': 250.0,
                                                 'type': 'Individual',
                                                 'notes': 'Employer listed as Government Strategies, INC.'},
                                                {'donor': 'Joseph Walsh',
                                                 'amount': 250.0,
                                                 'type': 'Individual',
                                                 'notes': 'Employer listed as Government Strategies, INC.'},
                                                {'donor': 'RI HEALTH CARE ASSOCIATION PAC',
                                                 'amount': 250.0,
                                                 'type': 'PAC',
                                                 'notes': 'Named PAC contribution listed in the Q2 filing.'}],
                                 'spending_categories': [{'title': 'Donations (Political)',
                                                          'summary': 'Visible spending includes Friends of Greg '
                                                                     'Amore.',
                                                          'amount': 1275.0},
                                                         {'title': 'Telephone',
                                                          'summary': 'Visible spending includes Verizon.',
                                                          'amount': 129.88},
                                                         {'title': 'Office Equipment & Supplies',
                                                          'summary': 'Payee Information',
                                                          'amount': 72.0}],
                                 'filing_history': [{'label': 'Q1 2026',
                                                     'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                     'money_raised': 12407.02,
                                                     'money_spent': 3922.95,
                                                     'ending_cash': 69329.83,
                                                     'net_change': 8484.07,
                                                     'notes': 'Q1 included itemized individuals, aggregate '
                                                              'individual receipts, PAC contributions, and $7.02 in '
                                                              'interest.'},
                                                    {'label': 'Q2 2026',
                                                     'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                     'money_raised': 6431.74,
                                                     'money_spent': 1476.88,
                                                     'ending_cash': 74284.69,
                                                     'net_change': 4954.86,
                                                     'notes': 'Q2 is the standardized main display period.'}]},
 'senate-11-linda-l-ujifusa': {'report_label': 'Q2 2026 campaign finance filing',
                               'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                               'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                               'coverage_note': 'Q2 2026 is used as the main display period for comparability across '
                                                'candidates. Detailed Q2 contributors and expenditures are '
                                                'available.',
                               'beginning_cash': 2573.08,
                               'money_raised': 240.0,
                               'money_spent': 564.7,
                               'ending_cash': 2248.38,
                               'net_change': -324.7,
                               'total_cash_receipts': 240.0,
                               'campaign_expenses': 564.7,
                               'aggregate_expenses': 0.0,
                               'summary_intro': "Linda L Ujifusa's Q2 2026 filing reports $240.00 in receipts, "
                                                '$564.70 in spending, and $2,248.38 in cash on hand at the end of '
                                                'the period.',
                               'source_buckets': [{'label': 'Itemized individual donors',
                                                   'class_name': 'itemized-individual-donors',
                                                   'amount': 100.0,
                                                   'description': 'Named individual contribution reported in '
                                                                  "Ujifusa's Q2 filing."},
                                                  {'label': 'PAC contributions',
                                                   'class_name': 'pac-contributions',
                                                   'amount': 140.0,
                                                   'description': "PAC contribution reported in Ujifusa's Q2 "
                                                                  'filing.'}],
                               'top_donors': [{'donor': 'RI PRIMARY CARE PAC',
                                               'amount': 140.0,
                                               'type': 'PAC',
                                               'notes': 'Named PAC contribution listed in the Q2 filing.'},
                                              {'donor': 'Robyn Day',
                                               'amount': 100.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Invictus Therapeutics.'}],
                               'spending_categories': [{'title': 'Other',
                                                        'summary': 'Visible spending includes ActBlue, GODADDY, '
                                                                   'Google.',
                                                        'amount': 564.7}],
                               'filing_history': [{'label': 'Q1 2026',
                                                   'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                   'money_raised': 0.0,
                                                   'money_spent': 112.05,
                                                   'ending_cash': 2573.08,
                                                   'net_change': -112.05,
                                                   'notes': 'No contributions were reported in Q1; campaign expenses '
                                                            'totaled $112.05.'},
                                                  {'label': 'Q2 2026',
                                                   'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                   'money_raised': 240.0,
                                                   'money_spent': 564.7,
                                                   'ending_cash': 2248.38,
                                                   'net_change': -324.7,
                                                   'notes': 'Q2 is the standardized main display period.'}]}}

def apply_ciccone_felag_ujifusa_q2_overrides(profile: dict[str, object]) -> dict[str, object]:
    override = CICCONE_FELAG_UJIFUSA_Q2_OVERRIDES.get(str(profile.get("candidate_id", "")))
    if not override:
        return profile
    profile.update(override)
    return profile


# Standardized Q2 main-display overrides for Valarie Jean Lawson, Meghan E Kallman, and Thomas J Paolino.
LAWSON_KALLMAN_PAOLINO_Q2_OVERRIDES = {'senate-14-valarie-jean-lawson': {'report_label': 'Q2 2026 campaign finance filing',
                                   'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                   'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                                   'coverage_note': 'Q2 2026 is used as the main display period for comparability '
                                                    'across candidates. Detailed Q2 contributors are available.',
                                   'beginning_cash': 294305.53,
                                   'money_raised': 67263.98,
                                   'money_spent': 24918.9,
                                   'ending_cash': 336650.61,
                                   'net_change': 42345.08,
                                   'total_cash_receipts': 67263.98,
                                   'campaign_expenses': 24681.71,
                                   'aggregate_expenses': 237.19,
                                   'summary_intro': "Valarie Jean Lawson's Q2 2026 filing reports $67,263.98 in "
                                                    'receipts, $24,918.90 in total spending, and $336,650.61 in cash '
                                                    'on hand at the end of the period.',
                                   'source_buckets': [{'label': 'Itemized individual donors',
                                                       'class_name': 'itemized-individual-donors',
                                                       'amount': 59015.0,
                                                       'description': 'Named individual contributions reported in '
                                                                      "Lawson's Q2 2026 filing."},
                                                      {'label': 'PAC contributions',
                                                       'class_name': 'pac-contributions',
                                                       'amount': 7650.0,
                                                       'description': 'Political action committee contributions '
                                                                      "reported in Lawson's Q2 2026 filing."},
                                                      {'label': 'Other reported sources',
                                                       'class_name': 'other-reported-sources',
                                                       'amount': 598.98,
                                                       'description': "Other receipts reported in Lawson's Q2 2026 "
                                                                      'filing.'}],
                                   'top_donors': [{'donor': 'Arlene Chaplin',
                                                   'amount': 2000.0,
                                                   'type': 'Individual',
                                                   'notes': 'Employer listed as Retired.'},
                                                  {'donor': 'Jaquelin Mancini',
                                                   'amount': 2000.0,
                                                   'type': 'Individual',
                                                   'notes': 'Employer listed as RI Distributiong.'},
                                                  {'donor': 'Kenneth J. Mancini',
                                                   'amount': 2000.0,
                                                   'type': 'Individual',
                                                   'notes': 'Employer listed as Mancini Mancini Beverage.'},
                                                  {'donor': 'Wayne Chaplin',
                                                   'amount': 2000.0,
                                                   'type': 'Individual',
                                                   'notes': 'Employer listed as Retired.'},
                                                  {'donor': 'Zachary Darrow',
                                                   'amount': 2000.0,
                                                   'type': 'Individual',
                                                   'notes': 'Employer listed as Darrow Everett LLP.'},
                                                  {'donor': 'Daniel Ryan',
                                                   'amount': 1500.0,
                                                   'type': 'Individual',
                                                   'notes': 'Employer listed as Twin River Casino.'},
                                                  {'donor': 'Elizabeth Suever',
                                                   'amount': 1500.0,
                                                   'type': 'Individual',
                                                   'notes': "Employer listed as Bally's Corporation."},
                                                  {'donor': 'INTERNATIONAL UNION OF PAINTERS & ALLIED TRADES '
                                                            'POLITICAL ACTION TOGETHER POLITICAL COMMITTEE - RI',
                                                   'amount': 1500.0,
                                                   'type': 'PAC',
                                                   'notes': 'Named PAC contribution listed in the Q2 filing.'},
                                                  {'donor': 'Anthony Simon',
                                                   'amount': 1000.0,
                                                   'type': 'Individual',
                                                   'notes': 'Employer listed as Self Employed - Consultant.'},
                                                  {'donor': 'Barry Munk',
                                                   'amount': 1000.0,
                                                   'type': 'Individual',
                                                   'notes': 'Employer listed as Marquis.'}],
                                   'spending_categories': [{'title': 'Donations (Political)',
                                                            'summary': 'Visible spending includes American Airlines, '
                                                                       'Angelos, AVVIO.',
                                                            'amount': 9900.0},
                                                           {'title': 'Donations (All Others)',
                                                            'summary': 'Visible spending includes Central Falls '
                                                                       'Foundation, Fleur Providence, Friends of '
                                                                       "Townie's Athletics.",
                                                            'amount': 4667.95},
                                                           {'title': 'Food, Beverages and Meals',
                                                            'summary': 'Visible spending includes Captains Catch.',
                                                            'amount': 266.2},
                                                           {'title': 'Advertising',
                                                            'summary': 'Visible spending includes CVS.',
                                                            'amount': 200.0},
                                                           {'title': 'Other',
                                                            'summary': 'Bank Fees & EIG Constant Contacts',
                                                            'amount': 97.41},
                                                           {'title': 'Other campaign expenses not itemized in parsed '
                                                                     'schedule',
                                                            'summary': 'Amount needed to reconcile the visible '
                                                                       'expenditure categories to the CF-2 total; '
                                                                       'retained separately rather than assigned to '
                                                                       'an unsupported category.',
                                                            'amount': 9787.34}],
                                   'filing_history': [{'label': 'Q1 2026',
                                                       'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                       'money_raised': 170960.0,
                                                       'money_spent': 61801.63,
                                                       'ending_cash': 294305.53,
                                                       'net_change': 108758.37,
                                                       'notes': 'Q1 retained in filing history.'},
                                                      {'label': 'Q2 2026',
                                                       'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                       'money_raised': 67263.98,
                                                       'money_spent': 24918.9,
                                                       'ending_cash': 336650.61,
                                                       'net_change': 42345.08,
                                                       'notes': 'Q2 is the standardized main display period.'}]},
 'senate-15-meghan-e-kallman': {'report_label': 'Q2 2026 campaign finance filing',
                                'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                                'coverage_note': 'Q2 2026 is used as the main display period for comparability '
                                                 'across candidates. Detailed Q2 contributors and expenditures are '
                                                 'available.',
                                'beginning_cash': 48350.8,
                                'money_raised': 5180.0,
                                'money_spent': 2907.4,
                                'ending_cash': 50623.4,
                                'net_change': 2272.6,
                                'total_cash_receipts': 5180.0,
                                'campaign_expenses': 2907.4,
                                'aggregate_expenses': 0.0,
                                'summary_intro': "Meghan E Kallman's Q2 2026 filing reports $5,180.00 in receipts, "
                                                 '$2,907.40 in spending, and $50,623.40 in cash on hand at the end '
                                                 'of the period.',
                                'source_buckets': [{'label': 'Itemized individual donors',
                                                    'class_name': 'itemized-individual-donors',
                                                    'amount': 4005.0,
                                                    'description': 'Named individual contributions reported in '
                                                                   "Kallman's Q2 2026 filing."},
                                                   {'label': 'Receipts without donor names listed',
                                                    'class_name': 'small-dollar-aggregate-online-receipts',
                                                    'amount': 1175.0,
                                                    'description': 'Aggregate ActBlue receipts reported without '
                                                                   'individual donor names.'}],
                                'top_donors': [{'donor': 'Anne Holland',
                                                'amount': 1997.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Anne Holland Ventures.'},
                                               {'donor': 'Adam Sinel',
                                                'amount': 500.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Berger Recycling.'},
                                               {'donor': 'Camilo Viveros',
                                                'amount': 250.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as George Wiley Center.'},
                                               {'donor': 'Carolyn Betensky',
                                                'amount': 200.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as University of Rhode Island.'},
                                               {'donor': 'Elizabeth Radka',
                                                'amount': 200.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Zywave.'},
                                               {'donor': 'Karen Jo',
                                                'amount': 200.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Lee Brown University.'},
                                               {'donor': 'Zoe Gardiner',
                                                'amount': 200.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Self Employed.'},
                                               {'donor': 'Karyn Monti',
                                                'amount': 150.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Reired.'},
                                               {'donor': 'Lex Rofeberg',
                                                'amount': 108.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Institute for the next Jewish future.'},
                                               {'donor': "David O'Hara",
                                                'amount': 100.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as N/A.'}],
                                'spending_categories': [{'title': 'Consultant & Professional Services',
                                                         'summary': 'Visible spending includes Jessica Ahlquist, All '
                                                                    'The Answers Inc..',
                                                         'amount': 2458.79},
                                                        {'title': 'Refunds/Reimbursements',
                                                         'summary': 'Visible spending includes 5475494 Meghan E '
                                                                    'Kallman.',
                                                         'amount': 311.88},
                                                        {'title': 'Bank Fees',
                                                         'summary': 'Visible spending includes ActBlue.',
                                                         'amount': 118.75},
                                                        {'title': 'Advertising',
                                                         'summary': 'Visible spending includes SQUARESPACE INC.',
                                                         'amount': 8.99},
                                                        {'title': 'Other campaign expenses not itemized in parsed '
                                                                  'schedule',
                                                         'summary': 'Amount needed to reconcile the visible '
                                                                    'expenditure categories to the CF-2 total; '
                                                                    'retained separately rather than assigned to an '
                                                                    'unsupported category.',
                                                         'amount': 8.99}],
                                'filing_history': [{'label': 'Q1 2026',
                                                    'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                    'money_raised': 16449.0,
                                                    'money_spent': 1886.05,
                                                    'ending_cash': 48350.8,
                                                    'net_change': 16562.95,
                                                    'notes': 'Q1 retained in filing history.'},
                                                   {'label': 'Q2 2026',
                                                    'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                    'money_raised': 5180.0,
                                                    'money_spent': 2907.4,
                                                    'ending_cash': 50623.4,
                                                    'net_change': 2272.6,
                                                    'notes': 'Q2 is the standardized main display period.'}]},
 'senate-17-thomas-j-paolino': {'report_label': 'Q2 2026 campaign finance filing',
                                'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                                'coverage_note': 'Q2 2026 is used as the main display period for comparability. Two '
                                                 'Q2 versions were uploaded; both have identical CF-2 summary '
                                                 'totals. The more complete six-page Q2 filing was used for donor '
                                                 'and spending detail.',
                                'beginning_cash': 11318.22,
                                'money_raised': 11383.47,
                                'money_spent': 4070.62,
                                'ending_cash': 18631.07,
                                'net_change': 7312.85,
                                'total_cash_receipts': 11383.47,
                                'campaign_expenses': 4070.62,
                                'aggregate_expenses': 0.0,
                                'summary_intro': "Thomas J Paolino's Q2 2026 filing reports $11,383.47 in receipts, "
                                                 '$4,070.62 in spending, and $18,631.07 in cash on hand at the end '
                                                 'of the period.',
                                'source_buckets': [{'label': 'Itemized individual donors',
                                                    'class_name': 'itemized-individual-donors',
                                                    'amount': 3010.25,
                                                    'description': 'Named individual contributions reported in '
                                                                   "Paolino's Q2 2026 filing."},
                                                   {'label': 'Receipts without donor names listed',
                                                    'class_name': 'small-dollar-aggregate-online-receipts',
                                                    'amount': 8373.22,
                                                    'description': 'Aggregate individual receipts reported without '
                                                                   'donor names.'}],
                                'top_donors': [{'donor': 'Jessica De La Cruz',
                                                'amount': 1000.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as La Cruz.'},
                                               {'donor': 'David Ferland',
                                                'amount': 500.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Overland Supply.'},
                                               {'donor': 'Shawn Wilson',
                                                'amount': 260.25,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Retired.'},
                                               {'donor': 'Anthony Thompson',
                                                'amount': 250.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Sigil Services.'},
                                               {'donor': 'Brandon Bell',
                                                'amount': 250.0,
                                                'type': 'Individual',
                                                'notes': 'Named individual contribution listed in the Q2 filing.'},
                                               {'donor': 'Michael Kumar',
                                                'amount': 250.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as IGT.'},
                                               {'donor': 'Steven Ceceri',
                                                'amount': 250.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as New England Property Services INC.'},
                                               {'donor': 'Steven Issa',
                                                'amount': 250.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Customers Bank.'}],
                                'spending_categories': [{'title': 'Fundraising Expenses',
                                                         'summary': 'Visible spending includes Formatt Printing, '
                                                                    'Michele Fried, Andrew Kagan.',
                                                         'amount': 3445.53},
                                                        {'title': 'Advertising',
                                                         'summary': 'Visible spending includes Facebook, MailChimp.',
                                                         'amount': 550.09},
                                                        {'title': 'Donations (Political)',
                                                         'summary': 'Visible spending includes Right to Life.',
                                                         'amount': 75.0}],
                                'filing_history': [{'label': 'Q1 2026',
                                                    'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                    'money_raised': 200.0,
                                                    'money_spent': 200.0,
                                                    'ending_cash': 11318.22,
                                                    'net_change': 0.0,
                                                    'notes': 'Q1 retained in filing history.'},
                                                   {'label': 'Q2 2026',
                                                    'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                    'money_raised': 11383.47,
                                                    'money_spent': 4070.62,
                                                    'ending_cash': 18631.07,
                                                    'net_change': 7312.85,
                                                    'notes': 'Q2 is the standardized main display period; detailed '
                                                             'entries use the more complete six-page Q2 filing.'}]}}

def apply_lawson_kallman_paolino_q2_overrides(profile: dict[str, object]) -> dict[str, object]:
    override = LAWSON_KALLMAN_PAOLINO_Q2_OVERRIDES.get(str(profile.get("candidate_id", "")))
    if not override:
        return profile
    profile.update(override)
    return profile


# Standardized Q2 main-display overrides for Ryan W. Pearson, Brian J. Thompson, and Gordon E. Rogers.
PEARSON_THOMPSON_ROGERS_Q2_OVERRIDES = {'senate-19-ryan-w-pearson': {'report_label': 'Q2 2026 campaign finance filing',
                              'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                              'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                              'coverage_note': 'Q2 2026 is used as the main display period for comparability. Two Q2 '
                                               'versions were uploaded; both have the same CF-2 summary totals. The '
                                               'more complete six-page version was used for detailed contribution '
                                               'and expenditure information. A $275,000 loan repayment is reported '
                                               'separately from the $2,758.42 in campaign expenses.',
                              'beginning_cash': 345026.97,
                              'money_raised': 588.61,
                              'money_spent': 2758.42,
                              'ending_cash': 67857.16,
                              'net_change': -277169.81,
                              'total_cash_receipts': 588.61,
                              'campaign_expenses': 2758.42,
                              'aggregate_expenses': 0.0,
                              'summary_intro': "Ryan W Pearson's Q2 2026 filing reports $588.61 in cash receipts, "
                                               'consisting of a $100.00 individual contribution and $488.61 in '
                                               'interest. The campaign reported $2,758.42 in campaign expenses and '
                                               'repaid $275,000.00 in loans, closing the period with $67,857.16 in '
                                               'cash on hand.',
                              'source_buckets': [{'label': 'Itemized individual donors',
                                                  'class_name': 'itemized-individual-donors',
                                                  'amount': 100.0,
                                                  'description': 'One named individual contribution reported in '
                                                                 "Pearson's Q2 2026 filing."},
                                                 {'label': 'Other reported sources',
                                                  'class_name': 'other-reported-sources',
                                                  'amount': 488.61,
                                                  'description': 'Interest received from Citizens Bank during Q2 '
                                                                 '2026.'}],
                              'top_donors': [{'donor': 'Michael Delucia',
                                              'amount': 100.0,
                                              'type': 'Individual',
                                              'notes': 'Employer listed as Intellezy.'}],
                              'spending_categories': [{'title': 'Office Equipment & Supplies',
                                                       'summary': 'Visible spending includes Apple Store.',
                                                       'amount': 1454.92},
                                                      {'title': 'Donations (All Others)',
                                                       'summary': 'Visible spending includes Blood Cancer United, '
                                                                  'Brandon Voas, and TANK.',
                                                       'amount': 700.0},
                                                      {'title': 'Consultant & Professional Services',
                                                       'summary': 'Visible spending includes Wix.',
                                                       'amount': 319.3},
                                                      {'title': 'Donations (Political)',
                                                       'summary': 'Visible spending includes Friends of Cindy Coyne '
                                                                  'and Friends of Xay Khamsyvoravong.',
                                                       'amount': 200.0},
                                                      {'title': 'Food, Beverages and Meals',
                                                       'summary': "Visible spending includes Chelo's Waterfront.",
                                                       'amount': 84.2}],
                              'filing_history': [{'label': 'Q1 2026',
                                                  'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                  'money_raised': 275522.26,
                                                  'money_spent': 339.55,
                                                  'ending_cash': 345026.97,
                                                  'net_change': 125182.71,
                                                  'notes': 'Q1 receipts consisted of a $275,000 loan from Ryan W '
                                                           'Pearson and $522.26 in interest; $150,000 in loan '
                                                           'repayments were also reported.'},
                                                 {'label': 'Q2 2026',
                                                  'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                  'money_raised': 588.61,
                                                  'money_spent': 2758.42,
                                                  'ending_cash': 67857.16,
                                                  'net_change': -277169.81,
                                                  'notes': 'Q2 is the standardized main display period. The filing '
                                                           'also reports a $275,000 loan repayment.'}]},
 'senate-20-brian-j-thompson': {'report_label': 'Q2 2026 campaign finance filing',
                                'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                                'coverage_note': 'Q2 2026 is used as the main display period for comparability '
                                                 'across candidates. Detailed Q2 contributors and expenditures are '
                                                 'available.',
                                'beginning_cash': 22996.33,
                                'money_raised': 12600.0,
                                'money_spent': 3312.99,
                                'ending_cash': 32283.34,
                                'net_change': 9287.01,
                                'total_cash_receipts': 12600.0,
                                'campaign_expenses': 3312.99,
                                'aggregate_expenses': 0.0,
                                'summary_intro': "Brian J Thompson's Q2 2026 filing reports $12,600.00 in receipts, "
                                                 'including $10,525.00 from itemized individuals, $225.00 in '
                                                 'aggregate individual receipts, and $1,850.00 from PACs. The '
                                                 'campaign reported $3,312.99 in spending and closed with $32,283.34 '
                                                 'in cash on hand.',
                                'source_buckets': [{'label': 'Itemized individual donors',
                                                    'class_name': 'itemized-individual-donors',
                                                    'amount': 10525.0,
                                                    'description': 'Named individual contributions reported in '
                                                                   "Thompson's Q2 2026 filing."},
                                                   {'label': 'Receipts without donor names listed',
                                                    'class_name': 'small-dollar-aggregate-online-receipts',
                                                    'amount': 225.0,
                                                    'description': 'Nine $25 contributions reported in aggregate '
                                                                   'without donor names.'},
                                                   {'label': 'PAC contributions',
                                                    'class_name': 'pac-contributions',
                                                    'amount': 1850.0,
                                                    'description': 'Political action committee contributions '
                                                                   "reported in Thompson's Q2 2026 filing."}],
                                'top_donors': [{'donor': 'Mukamil Shah',
                                                'amount': 1500.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Quick Mart.'},
                                               {'donor': 'Dung Le',
                                                'amount': 1250.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Lee Convenience.'},
                                               {'donor': 'Muhammed Saeed',
                                                'amount': 1250.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Retired.'},
                                               {'donor': 'Sabir Hussain',
                                                'amount': 1000.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Retired.'},
                                               {'donor': 'John H. Petrarca',
                                                'amount': 500.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Providence Auto Body.'},
                                               {'donor': 'Steven Ceceri',
                                                'amount': 500.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as New England Property Services.'},
                                               {'donor': 'Jeffrey Lemire',
                                                'amount': 300.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Quality Precision Builders.'},
                                               {'donor': 'Michael R. St. Germain',
                                                'amount': 250.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Sierra Solutions Group.'},
                                               {'donor': 'RI Hospitality PAC',
                                                'amount': 250.0,
                                                'type': 'PAC',
                                                'notes': 'Named PAC contribution listed in the Q2 filing.'},
                                               {'donor': 'Garrett Mancieri',
                                                'amount': 200.0,
                                                'type': 'Individual',
                                                'notes': 'Employer listed as Mancieri Real Estate.'}],
                                'spending_categories': [{'title': 'Donations (All Others)',
                                                         'summary': 'Visible spending includes Blood Cancer United, '
                                                                    'George Nasuti 5K, Monique Landry, Ronald '
                                                                    'Lefort, United Veterans Council of Woonsocket, '
                                                                    'Woonsocket Cops Walk, and Woonsocket Elks 850.',
                                                         'amount': 1135.0},
                                                        {'title': 'Donations (Political)',
                                                         'summary': 'Visible spending includes Christopher '
                                                                    'Beauchamp, Friends of Gregg Amore, Daniel '
                                                                    'Gendron, Michael Kinch, and the Woonsocket '
                                                                    'Democratic City Committee.',
                                                         'amount': 1030.0},
                                                        {'title': 'Advertising',
                                                         'summary': "Visible spending includes GoDaddy, Kay's, "
                                                                    'Squarespace, WOON Radio, and Woonsocket Rotary.',
                                                         'amount': 741.72},
                                                        {'title': 'Food, Beverages and Meals',
                                                         'summary': "Visible spending includes Ciro's Tavern.",
                                                         'amount': 364.2},
                                                        {'title': 'Bank Fees',
                                                         'summary': 'Visible spending includes ActBlue and '
                                                                    'Blackstone River FCU.',
                                                         'amount': 42.07}],
                                'filing_history': [{'label': 'Q1 2026',
                                                    'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                    'money_raised': 12250.0,
                                                    'money_spent': 8694.48,
                                                    'ending_cash': 22996.33,
                                                    'net_change': 3555.52,
                                                    'notes': 'Q1 retained in filing history.'},
                                                   {'label': 'Q2 2026',
                                                    'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                    'money_raised': 12600.0,
                                                    'money_spent': 3312.99,
                                                    'ending_cash': 32283.34,
                                                    'net_change': 9287.01,
                                                    'notes': 'Q2 is the standardized main display period.'}]},
 'senate-21-gordon-e-rogers': {'report_label': 'Q2 2026 campaign finance filing',
                               'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                               'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                               'coverage_note': 'Q2 2026 is used as the main display period for comparability across '
                                                'candidates. Detailed Q2 contributors and expenditures are '
                                                'available.',
                               'beginning_cash': 28771.81,
                               'money_raised': 10615.0,
                               'money_spent': 2241.03,
                               'ending_cash': 37145.78,
                               'net_change': 8373.97,
                               'total_cash_receipts': 10615.0,
                               'campaign_expenses': 2091.43,
                               'aggregate_expenses': 149.6,
                               'summary_intro': "Gordon E Rogers's Q2 2026 filing reports $10,615.00 in receipts, "
                                                'including $5,250.00 from itemized individuals, $4,365.00 in '
                                                'aggregate receipts, and $1,000.00 from PACs. The campaign reported '
                                                '$2,241.03 in total spending and closed with $37,145.78 in cash on '
                                                'hand.',
                               'source_buckets': [{'label': 'Itemized individual donors',
                                                   'class_name': 'itemized-individual-donors',
                                                   'amount': 5250.0,
                                                   'description': 'Named individual contributions reported in '
                                                                  "Rogers's Q2 2026 filing."},
                                                  {'label': 'Receipts without donor names listed',
                                                   'class_name': 'small-dollar-aggregate-online-receipts',
                                                   'amount': 4365.0,
                                                   'description': 'Aggregate receipts reported without individual '
                                                                  'donor names.'},
                                                  {'label': 'PAC contributions',
                                                   'class_name': 'pac-contributions',
                                                   'amount': 1000.0,
                                                   'description': 'Political action committee contributions reported '
                                                                  "in Rogers's Q2 2026 filing."}],
                               'top_donors': [{'donor': 'Gregory Rice',
                                               'amount': 1000.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Nexus Property Management.'},
                                              {'donor': 'Jessica de la Cruz',
                                               'amount': 1000.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as State of Rhode Island.'},
                                              {'donor': 'Stephen Skoly',
                                               'amount': 1000.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Dr. Stephen T. Skoly Jr., DMD.'},
                                              {'donor': 'John Rocchio',
                                               'amount': 500.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as John Rocchio Corp.'},
                                              {'donor': 'Linda Young',
                                               'amount': 500.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Compassionate Care Inc.'},
                                              {'donor': 'Rhode Island Second Amendment PAC',
                                               'amount': 500.0,
                                               'type': 'PAC',
                                               'notes': 'Named PAC contribution listed in the Q2 filing.'},
                                              {'donor': 'Anthony Thompson',
                                               'amount': 250.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Strong Tree Properties, LLC.'},
                                              {'donor': 'Gun Owners PAC',
                                               'amount': 250.0,
                                               'type': 'PAC',
                                               'notes': 'Named PAC contribution listed in the Q2 filing.'},
                                              {'donor': 'Jay DeSilva',
                                               'amount': 250.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as DeSilva Excavation LLC.'},
                                              {'donor': 'Larry Torti',
                                               'amount': 250.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Larry Torti Services, Inc.'}],
                               'spending_categories': [{'title': 'Advertising',
                                                        'summary': 'Visible spending includes Amazon for costumes '
                                                                   'and float-building materials for the Ancients & '
                                                                   'Horribles Parade.',
                                                        'amount': 1005.2},
                                                       {'title': 'Fundraising Expenses',
                                                        'summary': "Visible spending includes Dan's Place plus "
                                                                   'aggregate fundraising expenses.',
                                                        'amount': 833.93},
                                                       {'title': 'Donations (Political)',
                                                        'summary': 'Visible spending includes Friends of John '
                                                                   'Loughlin plus aggregate political donations.',
                                                        'amount': 306.0},
                                                       {'title': 'Bank Fees',
                                                        'summary': 'Visible spending includes Anedot Inc.',
                                                        'amount': 70.9},
                                                       {'title': 'Consultant & Professional Services',
                                                        'summary': 'Visible spending includes Lakeside Compliance '
                                                                   'Services.',
                                                        'amount': 25.0}],
                               'filing_history': [{'label': 'Q1 2026',
                                                   'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                   'money_raised': 675.0,
                                                   'money_spent': 595.0,
                                                   'ending_cash': 28771.81,
                                                   'net_change': 80.0,
                                                   'notes': 'Q1 retained in filing history.'},
                                                  {'label': 'Q2 2026',
                                                   'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                   'money_raised': 10615.0,
                                                   'money_spent': 2241.03,
                                                   'ending_cash': 37145.78,
                                                   'net_change': 8373.97,
                                                   'notes': 'Q2 is the standardized main display period.'}]}}

def apply_pearson_thompson_rogers_q2_overrides(profile: dict[str, object]) -> dict[str, object]:
    override = PEARSON_THOMPSON_ROGERS_Q2_OVERRIDES.get(str(profile.get("candidate_id", "")))
    if not override:
        return profile
    profile.update(override)
    return profile


# Standardized Q2 main-display overrides for David P. Tikoian, Todd Patalano, and Hanna M. Gallo.
TIKOIAN_PATALANO_GALLO_Q2_OVERRIDES = {'senate-22-david-p-tikoian': {'report_label': 'Q2 2026 campaign finance filing',
                               'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                               'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                               'coverage_note': 'Q2 2026 is used as the main display period for comparability across '
                                                'candidates. Detailed Q2 contributors and expenditures are '
                                                'available.',
                               'beginning_cash': 293422.19,
                               'money_raised': 15725.0,
                               'money_spent': 2087.2,
                               'ending_cash': 307059.99,
                               'net_change': 13637.8,
                               'total_cash_receipts': 15725.0,
                               'campaign_expenses': 2087.2,
                               'aggregate_expenses': 0.0,
                               'summary_intro': "David P Tikoian's Q2 2026 filing reports $15,725.00 in receipts, "
                                                'including $12,325.00 from individuals and $3,400.00 from PACs. The '
                                                'campaign reported $2,087.20 in spending and closed with $307,059.99 '
                                                'in cash on hand.',
                               'source_buckets': [{'label': 'Itemized individual donors',
                                                   'class_name': 'itemized-individual-donors',
                                                   'amount': 12325.0,
                                                   'description': 'Named individual contributions reported in '
                                                                  "Tikoian's Q2 2026 filing."},
                                                  {'label': 'PAC contributions',
                                                   'class_name': 'pac-contributions',
                                                   'amount': 3400.0,
                                                   'description': 'Political action committee contributions reported '
                                                                  "in Tikoian's Q2 2026 filing."}],
                               'top_donors': [{'donor': 'Elizabeth Beretta Perik',
                                               'amount': 1000.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Not Employed.'},
                                              {'donor': 'John R. Koza',
                                               'amount': 1000.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as National Popular Vote.'},
                                              {'donor': 'RI Health Care Association PAC',
                                               'amount': 1000.0,
                                               'type': 'PAC',
                                               'notes': 'Named PAC contribution listed in the Q2 filing.'},
                                              {'donor': 'Adam C. Sepe',
                                               'amount': 500.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as North-Eastern Tree Service.'},
                                              {'donor': 'Anne M. Dardarian',
                                               'amount': 500.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Montgomery County Public Schools.'},
                                              {'donor': "Carol A. O'Donnell",
                                               'amount': 500.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as RI Coalition of Housing Providers.'},
                                              {'donor': 'Erica Janton',
                                               'amount': 500.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Law Office of Erica S. Janton P.C.'},
                                              {'donor': 'Kenneth J. Marandola',
                                               'amount': 500.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as KM Contracting & Real Estate.'},
                                              {'donor': 'Mark Mandell',
                                               'amount': 500.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Mandell, Boisclair & Mandell, Ltd.'},
                                              {'donor': 'Paul J. Damiano',
                                               'amount': 500.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Hilb Group.'}],
                               'spending_categories': [{'title': 'Advertising',
                                                        'summary': 'Visible spending includes Smithfield Municipal '
                                                                   'Ice Rink, The Local Insider News, LLC, and The '
                                                                   'Placemat Pro.',
                                                        'amount': 1873.0},
                                                       {'title': 'Office Equipment & Supplies',
                                                        'summary': 'Visible spending includes US Postal Service.',
                                                        'amount': 214.2}],
                               'filing_history': [{'label': 'Q1 2026',
                                                   'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                   'money_raised': 74450.0,
                                                   'money_spent': 12987.08,
                                                   'ending_cash': 293422.19,
                                                   'net_change': 61462.92,
                                                   'notes': 'Q1 retained in filing history.'},
                                                  {'label': 'Q2 2026',
                                                   'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                   'money_raised': 15725.0,
                                                   'money_spent': 2087.2,
                                                   'ending_cash': 307059.99,
                                                   'net_change': 13637.8,
                                                   'notes': 'Q2 is the standardized main display period.'}]},
 'senate-26-todd-m-patalano': {'report_label': 'Q2 2026 campaign finance filing',
                               'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                               'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                               'coverage_note': 'Q2 2026 is used as the main display period for comparability. The '
                                                'filing also reports a $4,077.00 accounts-payable repayment, shown '
                                                'separately from $1,656.60 in campaign expenses.',
                               'beginning_cash': 122835.21,
                               'money_raised': 6221.83,
                               'money_spent': 1656.6,
                               'ending_cash': 123323.44,
                               'net_change': 488.23,
                               'total_cash_receipts': 6221.83,
                               'campaign_expenses': 1656.6,
                               'aggregate_expenses': 0.0,
                               'summary_intro': "Todd Patalano's Q2 2026 filing reports $6,221.83 in cash receipts: "
                                                '$5,125.00 from individuals, $600.00 from PACs, and $496.83 in '
                                                'interest. The campaign reported $1,656.60 in campaign expenses and '
                                                'a separate $4,077.00 accounts-payable repayment, closing with '
                                                '$123,323.44 in cash on hand.',
                               'source_buckets': [{'label': 'Itemized individual donors',
                                                   'class_name': 'itemized-individual-donors',
                                                   'amount': 5125.0,
                                                   'description': 'Named individual contributions reported in '
                                                                  "Patalano's Q2 2026 filing."},
                                                  {'label': 'PAC contributions',
                                                   'class_name': 'pac-contributions',
                                                   'amount': 600.0,
                                                   'description': 'Political action committee contributions reported '
                                                                  "in Patalano's Q2 2026 filing."},
                                                  {'label': 'Other reported sources',
                                                   'class_name': 'other-reported-sources',
                                                   'amount': 496.83,
                                                   'description': 'Interest received during Q2 2026.'}],
                               'top_donors': [{'donor': 'William DeAngelus III',
                                               'amount': 2000.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Twin Oaks.'},
                                              {'donor': 'Brenda Baginski',
                                               'amount': 500.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Professional Ambulance.'},
                                              {'donor': 'Michael Pezzullo',
                                               'amount': 500.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Law Office of Michael S. Pezzullo.'},
                                              {'donor': 'John R. Koza',
                                               'amount': 250.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as National Popular Vote.'},
                                              {'donor': 'John Verdecchia',
                                               'amount': 250.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as John M. Verdecchia, Esq.'},
                                              {'donor': 'Kevin J. Hawkins',
                                               'amount': 250.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Retired.'},
                                              {'donor': 'George A. Zainyeh',
                                               'amount': 200.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Savage Law Partners, LLP.'},
                                              {'donor': "Pannone Lopes Devereaux & O'Gara LLC RI State PAC",
                                               'amount': 200.0,
                                               'type': 'PAC',
                                               'notes': 'Named PAC contribution listed in the Q2 filing.'},
                                              {'donor': 'William J. Fischer',
                                               'amount': 200.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as True North Communications, LLC.'}],
                               'spending_categories': [{'title': 'Donations (Political)',
                                                        'summary': 'Visible spending includes Committee to Elect Lou '
                                                                   'Raptakis, Friends of Anthony Melillo, and '
                                                                   'Friends of Gregg Amore.',
                                                        'amount': 950.0},
                                                       {'title': 'Donations (All Others)',
                                                        'summary': 'Visible spending includes Cranston Hall of Fame, '
                                                                   'Cranston West Little League, and RI Fraternal '
                                                                   'Order of Police.',
                                                        'amount': 680.0},
                                                       {'title': 'Bank Fees',
                                                        'summary': 'Visible spending includes Anedot, Inc.',
                                                        'amount': 26.6}],
                               'filing_history': [{'label': 'Q1 2026',
                                                   'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                   'money_raised': 29605.0,
                                                   'money_spent': 874.9,
                                                   'ending_cash': 122835.21,
                                                   'net_change': 28729.9,
                                                   'notes': 'Q1 receipts include contributions and $629.80 in '
                                                            'interest, net of a $150.00 returned contribution.'},
                                                  {'label': 'Q2 2026',
                                                   'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                   'money_raised': 6221.83,
                                                   'money_spent': 1656.6,
                                                   'ending_cash': 123323.44,
                                                   'net_change': 488.23,
                                                   'notes': 'Q2 is the standardized main display period. A $4,077.00 '
                                                            'accounts-payable repayment is reported separately.'}]},
 'senate-27-hanna-m-gallo': {'report_label': 'Q2 2026 campaign finance filing',
                             'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                             'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                             'coverage_note': 'Q2 2026 is used as the main display period for comparability across '
                                              'candidates. Aggregate individual and PAC receipts are separated from '
                                              'named contributions where the filing does not list donor names.',
                             'beginning_cash': 168217.79,
                             'money_raised': 38825.0,
                             'money_spent': 11442.74,
                             'ending_cash': 195600.05,
                             'net_change': 27382.26,
                             'total_cash_receipts': 38825.0,
                             'campaign_expenses': 9976.34,
                             'aggregate_expenses': 1466.4,
                             'summary_intro': "Hanna M Gallo's Q2 2026 filing reports $38,825.00 in receipts: "
                                              '$20,450.00 from named individuals, $10,850.00 in aggregate individual '
                                              'receipts, $4,800.00 from named PACs, and $2,725.00 in aggregate PAC '
                                              'receipts. Total spending was $11,442.74, and the campaign closed with '
                                              '$195,600.05 in cash on hand.',
                             'source_buckets': [{'label': 'Itemized individual donors',
                                                 'class_name': 'itemized-individual-donors',
                                                 'amount': 20450.0,
                                                 'description': "Named individual contributions reported in Gallo's "
                                                                'Q2 2026 filing.'},
                                                {'label': 'Receipts without donor names listed',
                                                 'class_name': 'small-dollar-aggregate-online-receipts',
                                                 'amount': 10850.0,
                                                 'description': 'Aggregate individual receipts reported without '
                                                                'donor names.'},
                                                {'label': 'PAC contributions',
                                                 'class_name': 'pac-contributions',
                                                 'amount': 4800.0,
                                                 'description': "Named PAC contributions reported in Gallo's Q2 2026 "
                                                                'filing.'},
                                                {'label': 'Aggregate PAC receipts',
                                                 'class_name': 'pac-contributions',
                                                 'amount': 2725.0,
                                                 'description': 'Aggregate PAC receipts reported without PAC '
                                                                'names.'}],
                             'top_donors': [{'donor': 'Diane Palumbo',
                                             'amount': 2000.0,
                                             'type': 'Individual',
                                             'notes': 'Employer listed as Homemaker.'},
                                            {'donor': 'Mitchel McGregor',
                                             'amount': 2000.0,
                                             'type': 'Individual',
                                             'notes': 'Employer listed as Self Employed.'},
                                            {'donor': 'Peter Salas',
                                             'amount': 2000.0,
                                             'type': 'Individual',
                                             'notes': 'Employer listed as Self Employed.'},
                                            {'donor': 'Priscilla Hatcher',
                                             'amount': 2000.0,
                                             'type': 'Individual',
                                             'notes': "Employer listed as Truluck's Restaurant Group, Inc."},
                                            {'donor': 'Vincenza Swad-White',
                                             'amount': 2000.0,
                                             'type': 'Individual',
                                             'notes': 'Employer listed as Self Employed.'},
                                            {'donor': 'Adam Sepe',
                                             'amount': 1000.0,
                                             'type': 'Individual',
                                             'notes': 'Employer listed as North Eastern Tree.'},
                                            {'donor': 'John Petrarca',
                                             'amount': 1000.0,
                                             'type': 'Individual',
                                             'notes': 'Employer listed as Providence Auto Body.'},
                                            {'donor': 'Anthony Rosciti',
                                             'amount': 500.0,
                                             'type': 'Individual',
                                             'notes': 'Named individual contribution listed in the Q2 filing.'},
                                            {'donor': 'EGFFA PAC (East Greenwich Fire Fighters Association)',
                                             'amount': 500.0,
                                             'type': 'PAC',
                                             'notes': 'Named PAC contribution listed in the Q2 filing.'}],
                             'spending_categories': [{'title': 'Advertising',
                                                      'summary': 'Visible spending includes Chris Tosto, LLC and '
                                                                 'Identifi.',
                                                      'amount': 3000.0},
                                                     {'title': 'Fundraising Expenses',
                                                      'summary': 'Visible spending includes Ballyhoo Enterprises and '
                                                                 'Circe Prime.',
                                                      'amount': 2941.57},
                                                     {'title': 'Consultant & Professional Services',
                                                      'summary': 'Reported consultant and professional-services '
                                                                 'expenses.',
                                                      'amount': 2550.0},
                                                     {'title': 'Food, Beverages and Meals',
                                                      'summary': "Visible spending includes Avvio and Iannuccilli's.",
                                                      'amount': 1464.7},
                                                     {'title': 'Office Equipment & Supplies',
                                                      'summary': 'Visible spending includes USPS.',
                                                      'amount': 780.0},
                                                     {'title': 'Bank Fees',
                                                      'summary': 'Reported bank-fee expenses.',
                                                      'amount': 256.47},
                                                     {'title': 'Donations (Political)',
                                                      'summary': 'Reported political donations.',
                                                      'amount': 250.0},
                                                     {'title': 'Donations (All Others)',
                                                      'summary': 'Reported other donations.',
                                                      'amount': 200.0}],
                             'filing_history': [{'label': 'Q1 2026',
                                                 'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                 'money_raised': 1250.0,
                                                 'money_spent': 1590.68,
                                                 'ending_cash': 168217.79,
                                                 'net_change': -340.68,
                                                 'notes': 'Q1 retained in filing history.'},
                                                {'label': 'Q2 2026',
                                                 'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                 'money_raised': 38825.0,
                                                 'money_spent': 11442.74,
                                                 'ending_cash': 195600.05,
                                                 'net_change': 27382.26,
                                                 'notes': 'Q2 is the standardized main display period.'}]}}

def apply_tikoian_patalano_gallo_q2_overrides(profile: dict[str, object]) -> dict[str, object]:
    override = TIKOIAN_PATALANO_GALLO_Q2_OVERRIDES.get(str(profile.get("candidate_id", "")))
    if not override:
        return profile
    profile.update(override)
    return profile


# Final standardized Q2 overrides for Appollonio, Vargas, LaMountain, Lauria, Pierson, and Raptakis.
# These values come from the candidates' official Rhode Island Board of Elections Q1/Q2 2026 filings.
LATEST_SENATE_Q2_OVERRIDES = {'senate-29-peter-a-appollonio-jr': {'report_label': 'Q2 2026 campaign finance filing',
                                     'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                     'source_note': 'Rhode Island Board of Elections Q1 and Q2 2026 campaign finance '
                                                    'filings',
                                     'coverage_note': 'Q2 2026 is the main display; Q1 2026 retained in filing '
                                                      'history.',
                                     'beginning_cash': 37355.9,
                                     'money_raised': 3922.95,
                                     'money_spent': 13.67,
                                     'ending_cash': 41265.18,
                                     'net_change': 3909.28,
                                     'total_cash_receipts': 3922.95,
                                     'campaign_expenses': 6.57,
                                     'aggregate_expenses': 7.1,
                                     'summary_intro': 'This filing shows the campaign ending Q2 with $41,265.18 cash '
                                                      'on hand. The campaign raised more than it spent during the '
                                                      'quarter.',
                                     'source_buckets': [{'label': 'Itemized individual donors',
                                                         'class_name': 'itemized-individual-donors',
                                                         'amount': 3022.95,
                                                         'description': 'Named individual contributions reported in '
                                                                        'the filing.'},
                                                        {'label': 'PAC contributions',
                                                         'class_name': 'pac-contributions',
                                                         'amount': 900.0,
                                                         'description': 'Political committees and PACs listed in the '
                                                                        'filing.'}],
                                     'top_donors': [{'donor': 'Bryan Monteiro',
                                                     'amount': 500,
                                                     'type': 'Individual',
                                                     'notes': 'Named individual contribution listed in the filing.'},
                                                    {'donor': 'John H Petrarca',
                                                     'amount': 500,
                                                     'type': 'Individual',
                                                     'notes': 'Named individual contribution listed in the filing.'},
                                                    {'donor': 'Valarie Lawson',
                                                     'amount': 300,
                                                     'type': 'Individual',
                                                     'notes': 'Named individual contribution listed in the filing.'},
                                                    {'donor': 'Michael Lima',
                                                     'amount': 250,
                                                     'type': 'Individual',
                                                     'notes': 'Named individual contribution listed in the filing.'},
                                                    {'donor': 'RI HOSPITALITY PAC',
                                                     'amount': 250,
                                                     'type': 'PAC',
                                                     'notes': 'Named PAC contribution listed in the filing.'},
                                                    {'donor': "RI LABORER'S POLITICAL LEAGUE",
                                                     'amount': 250,
                                                     'type': 'PAC',
                                                     'notes': 'Named PAC contribution listed in the filing.'}],
                                     'spending_categories': [{'title': 'Bank Fees',
                                                              'summary': 'ActBlue fees reported as an aggregate '
                                                                         'expenditure.',
                                                              'amount': 7.1},
                                                             {'title': 'Other',
                                                              'summary': 'ActBlue processing and contribution '
                                                                         'transaction fees.',
                                                              'amount': 6.57}],
                                     'filing_history': [{'label': 'Q1 2026',
                                                         'reporting_period_label': 'January 1, 2026 to March 31, '
                                                                                   '2026',
                                                         'money_raised': 14225.0,
                                                         'money_spent': 1319.66,
                                                         'ending_cash': 37355.9,
                                                         'net_change': 12905.34,
                                                         'notes': 'The campaign raised more than it spent in this '
                                                                  'reporting period.'},
                                                        {'label': 'Q2 2026',
                                                         'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                         'money_raised': 3922.95,
                                                         'money_spent': 13.67,
                                                         'ending_cash': 41265.18,
                                                         'net_change': 3909.28,
                                                         'notes': 'The campaign raised more than it spent in this '
                                                                  'reporting period.'}]},
 'senate-28-lammis-j-vargas': {'report_label': 'Q2 2026 campaign finance filing',
                               'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                               'source_note': 'Rhode Island Board of Elections Q1 and Q2 2026 campaign finance '
                                              'filings',
                               'coverage_note': 'Q2 2026 is the main display; Q1 2026 retained in filing history.',
                               'beginning_cash': 30304.55,
                               'money_raised': 3361.0,
                               'money_spent': 2315.5,
                               'ending_cash': 31350.05,
                               'net_change': 1045.5,
                               'total_cash_receipts': 3361.0,
                               'campaign_expenses': 2305.79,
                               'aggregate_expenses': 9.71,
                               'summary_intro': 'This filing shows the campaign ending Q2 with $31,350.05 cash on '
                                                'hand. The campaign raised more than it spent during the quarter.',
                               'source_buckets': [{'label': 'Aggregate individual contributions',
                                                   'class_name': 'aggregate-individual-donors',
                                                   'amount': 1861.0,
                                                   'description': 'Individual donations reported in aggregate for '
                                                                  'the quarter.'},
                                                  {'label': 'Itemized individual donors',
                                                   'class_name': 'itemized-individual-donors',
                                                   'amount': 150.0,
                                                   'description': 'Named individual contributions reported '
                                                                  'separately.'},
                                                  {'label': 'PAC contributions',
                                                   'class_name': 'pac-contributions',
                                                   'amount': 1350.0,
                                                   'description': 'Political committees and PACs listed in the '
                                                                  'filing.'}],
                               'top_donors': [{'donor': '(not listed)',
                                               'amount': 1861,
                                               'type': 'Aggregate - Individual',
                                               'notes': 'Aggregate individual contributions; donor names are not '
                                                        'listed in the filing.'},
                                              {'donor': 'AMALGAMATED TRANSIT UNION COPE-RHODE ISLAND',
                                               'amount': 500,
                                               'type': 'PAC',
                                               'notes': 'Named PAC contribution listed in the filing.'},
                                              {'donor': 'INTERNATIONAL UNION OF PAINTERS & ALLIED TRADES POLITICAL '
                                                        'ACTION TOGETHER POLITICAL COMMITTEE - RI',
                                               'amount': 250,
                                               'type': 'PAC',
                                               'notes': 'Named PAC contribution listed in the filing.'}],
                               'spending_categories': [{'title': 'Advertising',
                                                        'summary': 'Checkmate Consulting Group, Google Workspace and '
                                                                   'Mailchimp.',
                                                        'amount': 1505.79},
                                                       {'title': 'Consultant & Professional Services',
                                                        'summary': 'Campaign consulting payment to Mark LeBeau.',
                                                        'amount': 500.0},
                                                       {'title': 'Donations (All Others)',
                                                        'summary': 'Cranston East Little League and Cranston Hall of '
                                                                   'Fame.',
                                                        'amount': 300.0},
                                                       {'title': 'Bank Fees',
                                                        'summary': 'ActBlue fees for donations received during the '
                                                                   'quarter.',
                                                        'amount': 9.71}],
                               'filing_history': [{'label': 'Q1 2026',
                                                   'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                   'money_raised': 10837.0,
                                                   'money_spent': 2521.5,
                                                   'ending_cash': 30304.55,
                                                   'net_change': 8315.5,
                                                   'notes': 'The campaign raised more than it spent in this '
                                                            'reporting period.'},
                                                  {'label': 'Q2 2026',
                                                   'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                   'money_raised': 3361.0,
                                                   'money_spent': 2315.5,
                                                   'ending_cash': 31350.05,
                                                   'net_change': 1045.5,
                                                   'notes': 'The campaign raised more than it spent in this '
                                                            'reporting period.'}]},
 'senate-31-matthew-l-lamountain': {'report_label': 'Q2 2026 campaign finance filing',
                                    'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                    'source_note': 'Rhode Island Board of Elections Q1 and Q2 2026 campaign finance '
                                                   'filings',
                                    'coverage_note': 'Q2 2026 is the main display; Q1 2026 retained in filing '
                                                     'history.',
                                    'beginning_cash': 109568.91,
                                    'money_raised': 8750.0,
                                    'money_spent': 11578.47,
                                    'ending_cash': 106740.44,
                                    'net_change': -2828.47,
                                    'total_cash_receipts': 8750.0,
                                    'campaign_expenses': 11578.47,
                                    'aggregate_expenses': 0.0,
                                    'summary_intro': 'This filing shows the campaign ending Q2 with $106,740.44 cash '
                                                     'on hand. The campaign spent more than it raised during the '
                                                     'quarter.',
                                    'source_buckets': [{'label': 'Itemized individual donors',
                                                        'class_name': 'itemized-individual-donors',
                                                        'amount': 6375.0,
                                                        'description': 'Named individual contributions reported in '
                                                                       'the filing.'},
                                                       {'label': 'PAC contributions',
                                                        'class_name': 'pac-contributions',
                                                        'amount': 2500.0,
                                                        'description': 'Political committees and PACs listed in the '
                                                                       'filing.'},
                                                       {'label': 'Returned contributions',
                                                        'class_name': 'returned-contributions',
                                                        'amount': -125.0,
                                                        'description': 'Returned contribution reported in the '
                                                                       'filing; shown as a reduction in receipts.'}],
                                    'top_donors': [{'donor': 'John H Petrarca',
                                                    'amount': 1000,
                                                    'type': 'Individual',
                                                    'notes': 'Named individual contribution listed in the filing.'},
                                                   {'donor': 'Mark Mandell',
                                                    'amount': 500,
                                                    'type': 'Individual',
                                                    'notes': 'Named individual contribution listed in the filing.'},
                                                   {'donor': 'RI HOSPITALITY PAC',
                                                    'amount': 500,
                                                    'type': 'PAC',
                                                    'notes': 'Named PAC contribution listed in the filing.'},
                                                   {'donor': 'William J Murphy',
                                                    'amount': 350,
                                                    'type': 'Individual',
                                                    'notes': 'Named individual contribution listed in the filing.'},
                                                   {'donor': 'Anthony R Thompson',
                                                    'amount': 350,
                                                    'type': 'Individual',
                                                    'notes': 'Named individual contribution listed in the filing.'}],
                                    'spending_categories': [{'title': 'Advertising',
                                                             'summary': 'CheckMate Consulting: banner, fundraiser '
                                                                        'printing/mailing, and newsletter '
                                                                        'design/printing/mail services.',
                                                             'amount': 10246.03},
                                                            {'title': 'Donations (All Others)',
                                                             'summary': 'RI Troopers Association.',
                                                             'amount': 900.0},
                                                            {'title': 'Food, Beverages and Meals',
                                                             'summary': 'Bacaro Restaurant dinner with state '
                                                                        'senators.',
                                                             'amount': 385.76},
                                                            {'title': 'Bank Fees',
                                                             'summary': 'ActBlue and Washington Trust fees.',
                                                             'amount': 46.68}],
                                    'filing_history': [{'label': 'Q1 2026',
                                                        'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                        'money_raised': 31275.0,
                                                        'money_spent': 2080.28,
                                                        'ending_cash': 109568.91,
                                                        'net_change': 29194.72,
                                                        'notes': 'The campaign raised more than it spent in this '
                                                                 'reporting period.'},
                                                       {'label': 'Q2 2026',
                                                        'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                        'money_raised': 8750.0,
                                                        'money_spent': 11578.47,
                                                        'ending_cash': 106740.44,
                                                        'net_change': -2828.47,
                                                        'notes': 'The campaign spent more than it raised in this '
                                                                 'reporting period.'}]},
 'senate-32-pamela-j-lauria': {'report_label': 'Q2 2026 campaign finance filing',
                               'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                               'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                               'coverage_note': 'Q2 2026 is used as the main display period for comparability across '
                                                'candidates. The Q2 filing reports individual, political-party, and '
                                                'PAC receipts.',
                               'beginning_cash': 26830.84,
                               'money_raised': 6347.0,
                               'money_spent': 1675.21,
                               'ending_cash': 31502.63,
                               'net_change': 4671.79,
                               'total_cash_receipts': 6347.0,
                               'campaign_expenses': 1675.21,
                               'aggregate_expenses': 0.0,
                               'summary_intro': "Pamela J Lauria's Q2 2026 filing reports $6,347.00 in receipts, "
                                                '$1,675.21 in spending, and $31,502.63 in cash on hand at the end of '
                                                'the period.',
                               'source_buckets': [{'label': 'Itemized individual donors',
                                                   'class_name': 'itemized-individual-donors',
                                                   'amount': 4222.0,
                                                   'description': 'Named individual contributions reported in '
                                                                  "Lauria's Q2 2026 filing."},
                                                  {'label': 'PAC contributions',
                                                   'class_name': 'pac-contributions',
                                                   'amount': 1875.0,
                                                   'description': 'Political action committee contributions reported '
                                                                  "in Lauria's Q2 2026 filing."},
                                                  {'label': 'Other reported sources',
                                                   'class_name': 'other-reported-sources',
                                                   'amount': 250.0,
                                                   'description': "Political-party contribution reported in Lauria's "
                                                                  'Q2 2026 filing.'}],
                               'top_donors': [{'donor': 'Ralph Palumbo',
                                               'amount': 1000.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Revity Energy.'},
                                              {'donor': 'Val Lawson',
                                               'amount': 300.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as State of RI - Senate.'},
                                              {'donor': 'Anthony Simon',
                                               'amount': 250.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as self.'},
                                              {'donor': 'Cynthia Coyne',
                                               'amount': 250.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as retired.'},
                                              {'donor': 'East Providence Ward 4 Democratic City Committee',
                                               'amount': 250.0,
                                               'type': 'Political Party',
                                               'notes': 'Political-party contribution listed in the Q2 filing.'},
                                              {'donor': 'Nurse Practitioner of Rhode Island PAC',
                                               'amount': 250.0,
                                               'type': 'PAC',
                                               'notes': 'Named PAC contribution listed in the Q2 filing.'},
                                              {'donor': "RI Laborers' PAC",
                                               'amount': 250.0,
                                               'type': 'PAC',
                                               'notes': 'Named PAC contribution listed in the Q2 filing.'},
                                              {'donor': 'Stephen Alves',
                                               'amount': 250.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Capital Strategies LLC.'},
                                              {'donor': 'United Food & Commercial Workers Union Local 328 RI PAC',
                                               'amount': 250.0,
                                               'type': 'PAC',
                                               'notes': 'Named PAC contribution listed in the Q2 filing.'},
                                              {'donor': 'Michael Sroczynski',
                                               'amount': 200.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Hospital Association of Rhode Island.'}],
                               'spending_categories': [{'title': 'Fundraising Expenses',
                                                        'summary': 'Visible spending includes Regine Printing and '
                                                                   'USPS.',
                                                        'amount': 558.21},
                                                       {'title': 'Donations (Political)',
                                                        'summary': 'Visible spending includes Gregg Amore, Friends '
                                                                   'of Cindy Coyne, and Friends of Jason Knight.',
                                                        'amount': 550.0},
                                                       {'title': 'Food, Beverages and Meals',
                                                        'summary': "Visible spending includes Dave's Market.",
                                                        'amount': 378.09},
                                                       {'title': 'Donations (All Others)',
                                                        'summary': 'Visible spending includes Town of Barrington.',
                                                        'amount': 150.0},
                                                       {'title': 'Bank Fees',
                                                        'summary': 'Visible spending includes ActBlue and Stripe.',
                                                        'amount': 38.91}],
                               'filing_history': [{'label': 'Q1 2026',
                                                   'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                   'money_raised': 0.0,
                                                   'money_spent': 498.33,
                                                   'ending_cash': 26830.84,
                                                   'net_change': -498.33,
                                                   'notes': 'Q1 reported no receipts and $498.33 in campaign '
                                                            'expenses.'},
                                                  {'label': 'Q2 2026',
                                                   'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                   'money_raised': 6347.0,
                                                   'money_spent': 1675.21,
                                                   'ending_cash': 31502.63,
                                                   'net_change': 4671.79,
                                                   'notes': 'Q2 is the standardized main display period.'}]},
 'senate-33-james-p-pierson': {'report_label': 'Q2 2026 campaign finance filing',
                               'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                               'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 filings',
                               'coverage_note': 'Q2 2026 is used as the main display period. Pierson reported no '
                                                'receipts and no expenditures in either Q1 or Q2; the account '
                                                'remained at $6.39 cash on hand. The Q2 filing reports $465.64 in '
                                                'liabilities.',
                               'beginning_cash': 6.39,
                               'money_raised': 0.0,
                               'money_spent': 0.0,
                               'ending_cash': 6.39,
                               'net_change': 0.0,
                               'total_cash_receipts': 0.0,
                               'campaign_expenses': 0.0,
                               'aggregate_expenses': 0.0,
                               'summary_intro': "James P Pierson's Q2 2026 filing reports no receipts, no spending, "
                                                'and $6.39 in cash on hand at the end of the period.',
                               'source_buckets': [],
                               'top_donors': [],
                               'spending_categories': [],
                               'filing_history': [{'label': 'Q1 2026',
                                                   'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                   'money_raised': 0.0,
                                                   'money_spent': 0.0,
                                                   'ending_cash': 6.39,
                                                   'net_change': 0.0,
                                                   'notes': 'No receipts or expenditures were reported.'},
                                                  {'label': 'Q2 2026',
                                                   'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                   'money_raised': 0.0,
                                                   'money_spent': 0.0,
                                                   'ending_cash': 6.39,
                                                   'net_change': 0.0,
                                                   'notes': 'No receipts or expenditures were reported; Q2 is the '
                                                            'standardized main display period.'}]},
 'senate-33-leonidas-peter-raptakis': {'report_label': 'Q2 2026 campaign finance filing',
                                       'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                       'source_note': 'RI Board of Elections Q1 and Q2 2026 CF-2 / CF-3 / CF-4 '
                                                      'filings',
                                       'coverage_note': 'Q2 2026 is used as the main display period for '
                                                        'comparability across candidates. The filing reports '
                                                        '$10,462.43 in campaign expenses plus $421.49 in aggregate '
                                                        'expenses. Visible parsed expenditure categories are shown '
                                                        'separately, with the unreconciled remainder kept in a '
                                                        'neutral category.',
                                       'beginning_cash': 40242.5,
                                       'money_raised': 22275.0,
                                       'money_spent': 10883.92,
                                       'ending_cash': 51633.58,
                                       'net_change': 11391.08,
                                       'total_cash_receipts': 22275.0,
                                       'campaign_expenses': 10462.43,
                                       'aggregate_expenses': 421.49,
                                       'summary_intro': "Leonidas Peter Raptakis's Q2 2026 filing reports $22,275.00 "
                                                        'in receipts, including $20,275.00 from individuals and '
                                                        '$2,000.00 from PACs. The campaign reported $10,883.92 in '
                                                        'total spending and closed the period with $51,633.58 in '
                                                        'cash on hand.',
                                       'source_buckets': [{'label': 'Itemized individual donors',
                                                           'class_name': 'itemized-individual-donors',
                                                           'amount': 20275.0,
                                                           'description': 'Named individual contributions reported '
                                                                          "in Raptakis's Q2 2026 filing."},
                                                          {'label': 'PAC contributions',
                                                           'class_name': 'pac-contributions',
                                                           'amount': 2000.0,
                                                           'description': 'Political action committee contributions '
                                                                          "reported in Raptakis's Q2 2026 filing."}],
                                       'top_donors': [{'donor': 'Constantine Panopoulos',
                                                       'amount': 2000.0,
                                                       'type': 'Individual',
                                                       'notes': 'Employer listed as Three Plus Two Inc.'},
                                                      {'donor': 'Photis Gkionis',
                                                       'amount': 2000.0,
                                                       'type': 'Individual',
                                                       'notes': 'Employer listed as Strata Critical.'},
                                                      {'donor': 'Sundus Sultan',
                                                       'amount': 2000.0,
                                                       'type': 'Individual',
                                                       'notes': 'Employer listed as Homemaker.'},
                                                      {'donor': 'Emanuel Rouvelas',
                                                       'amount': 1000.0,
                                                       'type': 'Individual',
                                                       'notes': 'Employer listed as KL Gates.'},
                                                      {'donor': 'James Grundy',
                                                       'amount': 1000.0,
                                                       'type': 'Individual',
                                                       'notes': 'Employer listed as Atlantic Control Systems.'},
                                                      {'donor': 'Louis Katsos',
                                                       'amount': 1000.0,
                                                       'type': 'Individual',
                                                       'notes': 'Employer listed as Jekmar Associates Inc.'},
                                                      {'donor': 'Nicholas Bornozis',
                                                       'amount': 1000.0,
                                                       'type': 'Individual',
                                                       'notes': 'Employer listed as Capitol Link.'},
                                                      {'donor': 'RI Senate Leadership PAC',
                                                       'amount': 1000.0,
                                                       'type': 'PAC',
                                                       'notes': 'Named PAC contribution listed in the Q2 filing.'},
                                                      {'donor': 'Ravinder Bhalla',
                                                       'amount': 1000.0,
                                                       'type': 'Individual',
                                                       'notes': 'Employer listed as City of Hoboken.'},
                                                      {'donor': 'Tara Allen',
                                                       'amount': 1000.0,
                                                       'type': 'Individual',
                                                       'notes': 'Employer listed as Ogilvy Health.'}],
                                       'spending_categories': [{'title': 'Consultant & Professional Services',
                                                                'summary': 'Visible spending includes Greek News '
                                                                           'USA, SDR MEDIA MGT LLC, and TF Green '
                                                                           'Airport.',
                                                                'amount': 1905.0},
                                                               {'title': 'Donations (Political)',
                                                                'summary': 'Visible spending includes Ana Quezada, '
                                                                           'Sam Bell, and Constant Contact.',
                                                                'amount': 1325.0},
                                                               {'title': 'Food, Beverages and Meals',
                                                                'summary': 'Visible spending includes Safety Harbor '
                                                                           'Inn.',
                                                                'amount': 914.0},
                                                               {'title': 'Advertising',
                                                                'summary': 'Visible spending includes Providence '
                                                                           'Journal and RI Senate Open.',
                                                                'amount': 550.0},
                                                               {'title': 'Fundraising Expenses',
                                                                'summary': 'Visible spending includes ActBlue.',
                                                                'amount': 215.15},
                                                               {'title': 'Travel & Lodging',
                                                                'summary': 'Aggregate fundraising travel expenses '
                                                                           'reported in the filing.',
                                                                'amount': 206.34},
                                                               {'title': 'Donations (All Others)',
                                                                'summary': 'Visible spending includes Our Lady of '
                                                                           'Czenstochowa.',
                                                                'amount': 100.0},
                                                               {'title': 'Other campaign expenses not itemized in '
                                                                         'parsed schedule',
                                                                'summary': 'Amount needed to reconcile the visible '
                                                                           'parsed expenditure categories to the '
                                                                           'official Q2 total of $10,883.92. It is '
                                                                           'retained separately rather than assigned '
                                                                           'to an unsupported category.',
                                                                'amount': 5668.43}],
                                       'filing_history': [{'label': 'Q1 2026',
                                                           'reporting_period_label': 'January 1, 2026 to March 31, '
                                                                                     '2026',
                                                           'money_raised': 42475.0,
                                                           'money_spent': 8424.19,
                                                           'ending_cash': 40242.5,
                                                           'net_change': 34050.81,
                                                           'notes': 'Q1 reported $37,525 from individuals and $4,950 '
                                                                    'from PACs.'},
                                                          {'label': 'Q2 2026',
                                                           'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                           'money_raised': 22275.0,
                                                           'money_spent': 10883.92,
                                                           'ending_cash': 51633.58,
                                                           'net_change': 11391.08,
                                                           'notes': 'Q2 is the standardized main display period.'}]}}

def apply_latest_senate_q2_overrides(profile: dict[str, object]) -> dict[str, object]:
    override = LATEST_SENATE_Q2_OVERRIDES.get(str(profile.get("candidate_id", "")))
    if not override:
        return profile
    profile.update(override)
    return profile


# Final Q2/amended-Q2 overrides for DiMario, Valverde, Place, and Morgan.
DIMARIO_VALVERDE_PLACE_MORGAN_OVERRIDES = {'senate-36-alana-m-dimario': {'report_label': 'Amended Q2 2026 campaign finance filing',
                               'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                               'source_note': 'RI Board of Elections Q1 2026 filing and amended Q2 2026 filing '
                                              'supplied by the user',
                               'coverage_note': 'The amended Q2 filing supersedes the earlier Q2 version for the '
                                                'main display. The amendment changes reported ending cash to '
                                                '$44,045.71 and provides the detailed contribution and expenditure '
                                                'schedules.',
                               'beginning_cash': 45474.78,
                               'money_raised': 14432.0,
                               'money_spent': 15861.07,
                               'ending_cash': 44045.71,
                               'net_change': -1429.07,
                               'total_cash_receipts': 14432.0,
                               'campaign_expenses': 15861.07,
                               'aggregate_expenses': 0.0,
                               'summary_intro': "Alana M DiMario's amended Q2 2026 filing reports $14,432.00 in "
                                                'receipts, $15,861.07 in spending, and $44,045.71 in cash on hand at '
                                                'the end of the period.',
                               'source_buckets': [{'label': 'Itemized individual donors',
                                                   'class_name': 'itemized-individual-donors',
                                                   'amount': 13260.0,
                                                   'description': 'Individual contributions reported in the amended '
                                                                  'Q2 filing.'},
                                                  {'label': 'PAC contributions',
                                                   'class_name': 'pac-contributions',
                                                   'amount': 750.0,
                                                   'description': 'Political action committee contributions reported '
                                                                  'in the amended Q2 filing.'},
                                                  {'label': 'Other reported sources',
                                                   'class_name': 'other-reported-sources',
                                                   'amount': 422.0,
                                                   'description': 'Other receipt reported in the amended Q2 filing, '
                                                                  'including a conference reimbursement.'}],
                               'top_donors': [{'donor': 'Anne Hills',
                                               'amount': 2000.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Holland Anne Holland Ventures.'},
                                              {'donor': 'Ralph Palumbo',
                                               'amount': 2000.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Revity Energy.'},
                                              {'donor': 'John Cicilline',
                                               'amount': 500.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as retired.'},
                                              {'donor': 'Joshua Miller',
                                               'amount': 500.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Trinity Brewhouse.'},
                                              {'donor': 'Richard Gersten',
                                               'amount': 500.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as self-employed in commercial real '
                                                        'estate.'},
                                              {'donor': 'Sam Salganik',
                                               'amount': 500.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as RIPIN.'},
                                              {'donor': 'Council of State Governments reimbursement',
                                               'amount': 422.0,
                                               'type': 'Other',
                                               'notes': 'Delaware Housing Conference reimbursement reported in the '
                                                        'amended filing.'},
                                              {'donor': 'Margaret McDuff',
                                               'amount': 275.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as FSRI.'}],
                               'spending_categories': [{'title': 'Fundraising Expenses',
                                                        'summary': 'Visible spending includes Campaign Verify, '
                                                                   'CustomInk.com, and Amy Gabarra.',
                                                        'amount': 12217.08},
                                                       {'title': 'Advertising',
                                                        'summary': 'Visible spending includes Facebook.com, '
                                                                   'Google.com, and Mailchimp.com.',
                                                        'amount': 1209.87},
                                                       {'title': 'Food, Beverages and Meals',
                                                        'summary': "Visible spending includes Dave's Marketplace, "
                                                                   'Gooseneck Vineyards, and Joe.Coffee.',
                                                        'amount': 629.09},
                                                       {'title': 'Office Equipment & Supplies',
                                                        'summary': 'Visible spending includes Amazon.com, Canva.com, '
                                                                   'and Consignments LTD.',
                                                        'amount': 599.63},
                                                       {'title': 'Donations (All Others)',
                                                        'summary': 'Visible spending includes Planned Parenthood '
                                                                   'Votes, RI Kids Count, and RI Land Trust Council.',
                                                        'amount': 544.4},
                                                       {'title': 'Donations (Political)',
                                                        'summary': 'Visible spending includes Gregg Amore, Jack '
                                                                   'Reed, and Tyler McFeeters.',
                                                        'amount': 381.25},
                                                       {'title': 'Travel & Lodging',
                                                        'summary': 'Visible spending includes parking, Block Island '
                                                                   'Ferry, and City Parking.',
                                                        'amount': 149.77},
                                                       {'title': 'Bank Fees',
                                                        'summary': 'Visible spending includes ActBlue.com.',
                                                        'amount': 129.98}],
                               'filing_history': [{'label': 'Q1 2026',
                                                   'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                   'money_raised': 5421.0,
                                                   'money_spent': 3830.28,
                                                   'ending_cash': 45554.62,
                                                   'net_change': 1590.72,
                                                   'notes': 'Q1 reported $5,421.00 in receipts.'},
                                                  {'label': 'Q2 2026 (amended)',
                                                   'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                   'money_raised': 14432.0,
                                                   'money_spent': 15861.07,
                                                   'ending_cash': 44045.71,
                                                   'net_change': -1429.07,
                                                   'notes': 'The amended filing is used for the standardized main '
                                                            'display.'}]},
 'senate-35-bridget-g-valverde': {'report_label': 'Q2 2026 campaign finance filing',
                                  'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                  'source_note': 'RI Board of Elections Q1 and Q2 2026 filings supplied by the user',
                                  'coverage_note': 'Q2 2026 is used as the main display period.',
                                  'beginning_cash': 41189.72,
                                  'money_raised': 7844.0,
                                  'money_spent': 1085.92,
                                  'ending_cash': 47947.8,
                                  'net_change': 6758.08,
                                  'total_cash_receipts': 7844.0,
                                  'campaign_expenses': 904.19,
                                  'aggregate_expenses': 181.73,
                                  'summary_intro': "Bridget G Valverde's Q2 2026 filing reports $7,844.00 in "
                                                   'receipts, $1,085.92 in total spending, and $47,947.80 in cash on '
                                                   'hand.',
                                  'source_buckets': [{'label': 'Itemized individual donors',
                                                      'class_name': 'itemized-individual-donors',
                                                      'amount': 6894.0,
                                                      'description': 'Individual contributions reported in the Q2 '
                                                                     'filing.'},
                                                     {'label': 'PAC contributions',
                                                      'class_name': 'pac-contributions',
                                                      'amount': 950.0,
                                                      'description': 'Political action committee contributions '
                                                                     'reported in the Q2 filing.'}],
                                  'top_donors': [{'donor': 'Jessie Kingston',
                                                  'amount': 2000.0,
                                                  'type': 'Individual',
                                                  'notes': 'Employer status listed as retired/not employed.'},
                                                 {'donor': 'Anne Holland',
                                                  'amount': 1999.0,
                                                  'type': 'Individual',
                                                  'notes': 'Employer status listed as not employed.'},
                                                 {'donor': 'EGFFA PAC (East Greenwich Fire Fighters Association)',
                                                  'amount': 250.0,
                                                  'type': 'PAC',
                                                  'notes': 'Named PAC contribution listed in the filing.'},
                                                 {'donor': 'Christopher Malgieri',
                                                  'amount': 200.0,
                                                  'type': 'Individual',
                                                  'notes': 'Employer listed as Brown Medical Health Group.'},
                                                 {'donor': 'Joshua Miller',
                                                  'amount': 200.0,
                                                  'type': 'Individual',
                                                  'notes': 'Employer listed as Trinity Brewhouse.'},
                                                 {'donor': 'Leonidas Raptakis',
                                                  'amount': 200.0,
                                                  'type': 'Individual',
                                                  'notes': 'Employer listed as ANR Consulting LLC.'},
                                                 {'donor': 'William Farrell',
                                                  'amount': 200.0,
                                                  'type': 'Individual',
                                                  'notes': 'Employer listed as William A Farrell and Associates, '
                                                           'LLC.'},
                                                 {'donor': 'CarePAC of Blue Cross & Blue Shield of RI',
                                                  'amount': 150.0,
                                                  'type': 'PAC',
                                                  'notes': 'Named PAC contribution listed in the filing.'}],
                                  'spending_categories': [{'title': 'Food, Beverages and Meals',
                                                           'summary': "Visible spending includes Ogie's Trailer "
                                                                      'Park.',
                                                           'amount': 576.8},
                                                          {'title': 'Consultant & Professional Services',
                                                           'summary': 'Visible spending includes All the Answers, '
                                                                      'Inc.',
                                                           'amount': 327.39},
                                                          {'title': 'Fundraising Expenses',
                                                           'summary': 'Aggregate ActBlue fees reported for April.',
                                                           'amount': 181.73}],
                                  'filing_history': [{'label': 'Q1 2026',
                                                      'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                      'money_raised': 1440.0,
                                                      'money_spent': 984.72,
                                                      'ending_cash': 41189.72,
                                                      'net_change': 455.28,
                                                      'notes': 'Q1 reported $1,440.00 in receipts.'},
                                                     {'label': 'Q2 2026',
                                                      'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                      'money_raised': 7844.0,
                                                      'money_spent': 1085.92,
                                                      'ending_cash': 47947.8,
                                                      'net_change': 6758.08,
                                                      'notes': 'Q2 is the standardized main display period.'}]},
 'senate-38-westin-j-place': {'report_label': 'Q2 2026 campaign finance filing',
                              'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                              'source_note': 'RI Board of Elections Q1 and Q2 2026 filings supplied by the user',
                              'coverage_note': 'Q2 2026 is used as the main display period. Place reported no Q2 '
                                               'receipts or expenditures.',
                              'beginning_cash': 609.06,
                              'money_raised': 0.0,
                              'money_spent': 0.0,
                              'ending_cash': 609.06,
                              'net_change': 0.0,
                              'total_cash_receipts': 0.0,
                              'campaign_expenses': 0.0,
                              'aggregate_expenses': 0.0,
                              'summary_intro': "Westin J Place's Q2 2026 filing reports no receipts, no spending, "
                                               'and $609.06 in cash on hand.',
                              'source_buckets': [],
                              'top_donors': [],
                              'spending_categories': [],
                              'filing_history': [{'label': 'Q1 2026',
                                                  'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                  'money_raised': 47.4,
                                                  'money_spent': 0.0,
                                                  'ending_cash': 609.06,
                                                  'net_change': 47.4,
                                                  'notes': 'Q1 reported $47.40 in aggregate individual receipts and '
                                                           'no spending.'},
                                                 {'label': 'Q2 2026',
                                                  'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                  'money_raised': 0.0,
                                                  'money_spent': 0.0,
                                                  'ending_cash': 609.06,
                                                  'net_change': 0.0,
                                                  'notes': 'No receipts or expenditures were reported.'}]},
 'senate-34-elaine-j-morgan': {'report_label': 'Amended Q2 2026 campaign finance filing',
                               'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                               'source_note': 'RI Board of Elections Q1 2026 filing and amended Q2 2026 filing '
                                              'supplied by the user',
                               'coverage_note': 'The amended Q2 filing supersedes the earlier Q2 version for the '
                                                'funding mix. It reclassifies the $5,580.00 in receipts as $2,780 '
                                                'aggregate individual, $2,050 itemized individual, and $750 PAC '
                                                'contributions.',
                               'beginning_cash': 3624.35,
                               'money_raised': 5580.0,
                               'money_spent': 314.08,
                               'ending_cash': 8890.27,
                               'net_change': 5265.92,
                               'total_cash_receipts': 5580.0,
                               'campaign_expenses': 314.08,
                               'aggregate_expenses': 0.0,
                               'summary_intro': "Elaine J Morgan's amended Q2 2026 filing reports $5,580.00 in "
                                                'receipts, $314.08 in spending, and $8,890.27 in cash on hand.',
                               'source_buckets': [{'label': 'Aggregate individual contributions',
                                                   'class_name': 'aggregate-individual-contributions',
                                                   'amount': 2780.0,
                                                   'description': 'Aggregate individual contributions reported in '
                                                                  'the amended Q2 filing.'},
                                                  {'label': 'Itemized individual donors',
                                                   'class_name': 'itemized-individual-donors',
                                                   'amount': 2050.0,
                                                   'description': 'Itemized individual contributions reported in the '
                                                                  'amended Q2 filing.'},
                                                  {'label': 'PAC contributions',
                                                   'class_name': 'pac-contributions',
                                                   'amount': 750.0,
                                                   'description': 'PAC contributions reported in the amended Q2 '
                                                                  'filing.'}],
                               'top_donors': [{'donor': 'Bruce Govin',
                                               'amount': 250.0,
                                               'type': 'Individual',
                                               'notes': 'Employer listed as Arrowhead Dental Associates.'},
                                              {'donor': 'Gun Owners PAC',
                                               'amount': 250.0,
                                               'type': 'PAC',
                                               'notes': 'Named PAC contribution listed in the amended filing.'},
                                              {'donor': 'Gun Owners PAC',
                                               'amount': 200.0,
                                               'type': 'PAC',
                                               'notes': 'A separate PAC contribution listed in the amended filing.'},
                                              {'donor': 'Fundraiser donations',
                                               'amount': 200.0,
                                               'type': 'Aggregate',
                                               'notes': 'Aggregate fundraiser donations listed in the amended '
                                                        'filing.'},
                                              {'donor': 'PAC contribution',
                                               'amount': 150.0,
                                               'type': 'PAC',
                                               'notes': 'PAC contribution listed in the amended filing.'}],
                               'spending_categories': [{'title': 'Campaign Expenses',
                                                        'summary': 'The amended filing reports $314.08 in campaign '
                                                                   "expenses. The amendment's parsed expenditure "
                                                                   'schedule does not support a complete '
                                                                   'category-level allocation, so the official total '
                                                                   'is retained without guessing.',
                                                        'amount': 314.08}],
                               'filing_history': [{'label': 'Q1 2026',
                                                   'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                   'money_raised': 660.0,
                                                   'money_spent': 283.92,
                                                   'ending_cash': 3624.35,
                                                   'net_change': 376.08,
                                                   'notes': 'Q1 reported $660.00 in receipts.'},
                                                  {'label': 'Q2 2026 (amended)',
                                                   'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                   'money_raised': 5580.0,
                                                   'money_spent': 314.08,
                                                   'ending_cash': 8890.27,
                                                   'net_change': 5265.92,
                                                   'notes': 'The amended filing is used for the standardized main '
                                                            'display and corrected funding mix.'}]}}

def apply_dimario_valverde_place_morgan_overrides(profile: dict[str, object]) -> dict[str, object]:
    override = DIMARIO_VALVERDE_PLACE_MORGAN_OVERRIDES.get(str(profile.get("candidate_id", "")))
    if override:
        profile.update(override)
    return profile


# Interest-group topic classification for named donors/committees.
# Classification is conservative and based on the committee/organization name only.
INTEREST_GROUP_RULES = [('Gun Rights', ('second amendment', 'gun owners', 'rifle', 'firearms')),
 ('Public Safety',
  ('firefighter',
   'fire fighters',
   'fire fighters association',
   'police',
   'correctional',
   'law enforcement',
   'sheriff',
   'fop')),
 ('Health Care',
  ('health',
   'hospital',
   'nurse',
   'nursing',
   'medical',
   'physician',
   'dental',
   'dentist',
   'optometric',
   'carepac',
   'blue cross',
   'pharmacy')),
 ('Education', ('education', 'teacher', 'teachers', 'nea', 'school', 'university', 'college', 'faculty')),
 ('Labor / Unions',
  ('union',
   'afl-cio',
   'afscme',
   'ibew',
   'laborer',
   'laborers',
   'teamster',
   'plumber',
   'pipefitter',
   'operating engineer',
   'cope',
   'workers',
   'building trades')),
 ('Hospitality / Tourism', ('hospitality', 'hotel', 'restaurant', 'tourism', 'lodging')),
 ('Construction / Trades', ('construction', 'contractor', 'contractors', 'builders', 'building industry')),
 ('Housing / Real Estate', ('realtor', 'real estate', 'housing', 'property owners')),
 ('Energy / Utilities', ('energy', 'utility', 'utilities', 'electric', 'gas association', 'renewable')),
 ('Finance / Insurance', ('bank', 'bankers', 'insurance', 'credit union', 'financial services')),
 ('Transportation', ('transit', 'transportation', 'truck', 'railroad', 'airline')),
 ('Environment / Conservation',
  ('environment', 'environmental', 'conservation', 'clean water', 'land trust', 'climate')),
 ('Reproductive Rights / Women', ('planned parenthood', 'reproductive', 'women', 'womxn')),
 ('Business / Industry', ('business', 'chamber', 'manufactur', 'industry', 'industries', 'commerce')),
 ('Legal / Professional', ('bar association', 'attorney', 'lawyers', 'legal')),
 ('Political Party / Leadership',
  ('senate leadership',
   'democratic committee',
   'republican committee',
   'dem committee',
   'gop',
   'party committee',
   'ward committee',
   'city committee')),
 ('Advocacy / Civic', ('civic', 'advocacy', 'good government', 'community action'))]


AJELLO_GARMAN_BIAH_Q2_OVERRIDES = {'edith-h-ajello': {'report_label': '2026 On-Going Qrtly (2nd)',
                    'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                    'source_note': "Built from Edith H Ajello's Rhode Island Q1 and Q2 2026 campaign finance filings.",
                    'coverage_note': 'Detailed Q1/Q2 filing data; Q2 is the main display.',
                    'original_documents': [{'label': 'Q1 2026 CF-2 report',
                                            'period': 'January 1, 2026 to March 31, 2026',
                                            'href': '/data/finance-documents/edith-h-ajello-q1-2026.pdf'},
                                           {'label': 'Q2 2026 CF-2 report',
                                            'period': 'April 1, 2026 to June 30, 2026',
                                            'href': '/data/finance-documents/edith-h-ajello-q2-2026.pdf'}],
                    'beginning_cash': 7132.11,
                    'money_raised': 16404.58,
                    'money_spent': 0.0,
                    'ending_cash': 23536.69,
                    'net_change': 16404.58,
                    'total_cash_receipts': 16404.58,
                    'campaign_expenses': 0.0,
                    'aggregate_expenses': 0.0,
                    'summary_intro': 'This filing shows a campaign that increased its cash reserve substantially '
                                     'during the quarter. The Q2 report also lists an $8,540 account payable, which is '
                                     'a liability rather than a cash disbursement.',
                    'filing_history': [{'label': 'Q1 2026',
                                        'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                        'money_raised': 0.0,
                                        'money_spent': 150.0,
                                        'ending_cash': 7132.11,
                                        'net_change': -150.0,
                                        'notes': 'The campaign spent more than it raised in this reporting period.'},
                                       {'label': 'Q2 2026',
                                        'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                        'money_raised': 16404.58,
                                        'money_spent': 0.0,
                                        'ending_cash': 23536.69,
                                        'net_change': 16404.58,
                                        'notes': 'The campaign raised more than it spent in this reporting period.'}],
                    'source_buckets': [{'label': 'Itemized individual donors',
                                        'class_name': 'itemized-individual-donors',
                                        'amount': 5000.0,
                                        'description': 'Named individual contributors reported in the Q2 filing.'},
                                       {'label': 'Receipts without donor names listed',
                                        'class_name': 'small-dollar-aggregate-online-receipts',
                                        'amount': 5204.58,
                                        'description': 'Aggregate individual receipts reported without donor names '
                                                       'attached.'},
                                       {'label': 'PAC contributions reported in aggregate',
                                        'class_name': 'pac-contributions',
                                        'amount': 200.0,
                                        'description': 'PAC money reported in aggregate without the committee name '
                                                       'listed.'},
                                       {'label': 'Candidate loan',
                                        'class_name': 'candidate-loan',
                                        'amount': 6000.0,
                                        'description': 'Loan proceeds from Edith H Ajello to the campaign.'}],
                    'top_donors': [{'donor': 'Anne Holland',
                                    'amount': 2000.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Named contribution listed in the Q2 filing.'},
                                   {'donor': 'Helen Anthony',
                                    'amount': 500.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Named contribution listed in the Q2 filing.'},
                                   {'donor': 'Jennifer Kiddie',
                                    'amount': 500.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Named contribution listed in the Q2 filing.'},
                                   {'donor': 'Linda Kushner',
                                    'amount': 500.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Named contribution listed in the Q2 filing.'},
                                   {'donor': 'Carolyn Mark',
                                    'amount': 500.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Named contribution listed in the Q2 filing.'},
                                   {'donor': 'Ralph Palumbo',
                                    'amount': 500.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Named contribution listed in the Q2 filing.'},
                                   {'donor': 'Myrth York',
                                    'amount': 500.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Named contribution listed in the Q2 filing.'}],
                    'spending_categories': [],
                    'takeaways': [],
                    'explainer_cards': []},
 'michael-j-garman': {'report_label': '2026 On-Going Qrtly (2nd)',
                      'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                      'source_note': "Built from Michael J Garman's Rhode Island Q1 and Q2 2026 campaign finance "
                                     'filings.',
                      'coverage_note': 'Detailed Q1/Q2 filing data; Q2 is the main display.',
                      'original_documents': [{'label': 'Q1 2026 CF-2 report',
                                              'period': 'January 1, 2026 to March 31, 2026',
                                              'href': '/data/finance-documents/michael-j-garman-q1-2026.pdf'},
                                             {'label': 'Q2 2026 CF-2 report',
                                              'period': 'April 1, 2026 to June 30, 2026',
                                              'href': '/data/finance-documents/michael-j-garman-q2-2026.pdf'}],
                      'beginning_cash': 23840.41,
                      'money_raised': 1250.0,
                      'money_spent': 2476.54,
                      'ending_cash': 22613.87,
                      'net_change': -1226.54,
                      'total_cash_receipts': 1250.0,
                      'campaign_expenses': 2476.54,
                      'aggregate_expenses': 0.0,
                      'summary_intro': 'This filing shows a campaign that spent more than it raised during Q2 while '
                                       'retaining more than $22,000 in cash on hand.',
                      'filing_history': [{'label': 'Q1 2026',
                                          'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                          'money_raised': 5283.0,
                                          'money_spent': 2450.84,
                                          'ending_cash': 23840.41,
                                          'net_change': 2832.16,
                                          'notes': 'The campaign raised more than it spent in this reporting period.'},
                                         {'label': 'Q2 2026',
                                          'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                          'money_raised': 1250.0,
                                          'money_spent': 2476.54,
                                          'ending_cash': 22613.87,
                                          'net_change': -1226.54,
                                          'notes': 'The campaign spent more than it raised in this reporting period.'}],
                      'source_buckets': [{'label': 'Itemized individual donors',
                                          'class_name': 'itemized-individual-donors',
                                          'amount': 820.0,
                                          'description': 'Named individual contributors reported in the Q2 filing.'},
                                         {'label': 'Receipts without donor names listed',
                                          'class_name': 'small-dollar-aggregate-online-receipts',
                                          'amount': 430.0,
                                          'description': 'ActBlue receipts reported in aggregate without donor names '
                                                         'attached to those payout lines.'}],
                      'top_donors': [{'donor': 'Sally Shwartz',
                                      'amount': 500.0,
                                      'type': 'Individual',
                                      'interest_group': 'Individual',
                                      'notes': 'Named contribution listed in the Q2 filing.'},
                                     {'donor': 'James Silverthorn',
                                      'amount': 100.0,
                                      'type': 'Individual',
                                      'interest_group': 'Individual',
                                      'notes': 'Named contribution listed in the Q2 filing.'},
                                     {'donor': 'Angel Dean',
                                      'amount': 50.0,
                                      'type': 'Individual',
                                      'interest_group': 'Individual',
                                      'notes': 'Named contribution listed in the Q2 filing.'},
                                     {'donor': 'Spencer Dickinson',
                                      'amount': 50.0,
                                      'type': 'Individual',
                                      'interest_group': 'Individual',
                                      'notes': 'Named contribution listed in the Q2 filing.'},
                                     {'donor': 'Joshua Kennedy',
                                      'amount': 50.0,
                                      'type': 'Individual',
                                      'interest_group': 'Individual',
                                      'notes': 'Named contribution listed in the Q2 filing.'},
                                     {'donor': 'Keerthi Sampath Madapusi',
                                      'amount': 50.0,
                                      'type': 'Individual',
                                      'interest_group': 'Individual',
                                      'notes': 'Named contribution listed in the Q2 filing.'},
                                     {'donor': 'Kenny Uong',
                                      'amount': 10.0,
                                      'type': 'Individual',
                                      'interest_group': 'Individual',
                                      'notes': 'Named contribution listed in the Q2 filing.'},
                                     {'donor': 'Megan Ranney',
                                      'amount': 10.0,
                                      'type': 'Individual',
                                      'interest_group': 'Individual',
                                      'notes': 'Named contribution listed in the Q2 filing.'}],
                      'spending_categories': [{'title': 'Consultant & Professional Services',
                                               'summary': 'Campaign management payments to Joshua Stearns.',
                                               'amount': 2425.0},
                                              {'title': 'Fundraising Expenses',
                                               'summary': 'Donation-processing fees reported for ActBlue and Stripe.',
                                               'amount': 51.54}],
                      'takeaways': [],
                      'explainer_cards': []},
 'nathan-w-biah': {'report_label': '2026 On-Going Qrtly (2nd)',
                   'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                   'source_note': "Built from Nathan W Biah's Rhode Island Q1 and Q2 2026 campaign finance filings.",
                   'coverage_note': 'Detailed Q1/Q2 filing data; Q2 is the main display.',
                   'original_documents': [{'label': 'Q1 2026 CF-2 report',
                                           'period': 'January 1, 2026 to March 31, 2026',
                                           'href': '/data/finance-documents/nathan-w-biah-q1-2026.pdf'},
                                          {'label': 'Q2 2026 CF-2 report',
                                           'period': 'April 1, 2026 to June 30, 2026',
                                           'href': '/data/finance-documents/nathan-w-biah-q2-2026.pdf'}],
                   'beginning_cash': 3597.7,
                   'money_raised': 7800.0,
                   'money_spent': 2782.98,
                   'ending_cash': 8614.72,
                   'net_change': 5017.02,
                   'total_cash_receipts': 7800.0,
                   'campaign_expenses': 2782.98,
                   'aggregate_expenses': 0.0,
                   'summary_intro': 'This filing shows a campaign that raised substantially more than it spent in Q2, '
                                    'increasing cash on hand to more than $8,600.',
                   'filing_history': [{'label': 'Q1 2026',
                                       'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                       'money_raised': 0.0,
                                       'money_spent': 460.83,
                                       'ending_cash': 3597.7,
                                       'net_change': -460.83,
                                       'notes': 'The campaign spent more than it raised in this reporting period.'},
                                      {'label': 'Q2 2026',
                                       'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                       'money_raised': 7800.0,
                                       'money_spent': 2782.98,
                                       'ending_cash': 8614.72,
                                       'net_change': 5017.02,
                                       'notes': 'The campaign raised more than it spent in this reporting period.'}],
                   'source_buckets': [{'label': 'Itemized individual donors',
                                       'class_name': 'itemized-individual-donors',
                                       'amount': 5675.0,
                                       'description': 'Named individual contributors reported in the Q2 filing.'},
                                      {'label': 'PAC contributions',
                                       'class_name': 'pac-contributions',
                                       'amount': 2125.0,
                                       'description': 'Political committees and PACs listed in the Q2 filing.'}],
                   'top_donors': [{'donor': 'John H. Petrarca',
                                   'amount': 1000.0,
                                   'type': 'Individual',
                                   'interest_group': 'Individual',
                                   'notes': 'Named contribution listed in the Q2 filing.'},
                                  {'donor': 'Brett P. Smiley',
                                   'amount': 500.0,
                                   'type': 'Individual',
                                   'interest_group': 'Individual',
                                   'notes': 'Named contribution listed in the Q2 filing.'},
                                  {'donor': 'CREDIT UNION PAC OF RI',
                                   'amount': 500.0,
                                   'type': 'PAC',
                                   'interest_group': 'Labor / Unions',
                                   'notes': 'Named contribution listed in the Q2 filing.'},
                                  {'donor': 'Matthew A Lopes Jr',
                                   'amount': 250.0,
                                   'type': 'Individual',
                                   'interest_group': 'Individual',
                                   'notes': 'Named contribution listed in the Q2 filing.'},
                                  {'donor': 'RI TROOPERS ASSOCIATION PAC',
                                   'amount': 250.0,
                                   'type': 'PAC',
                                   'interest_group': 'Public Safety',
                                   'notes': 'Named contribution listed in the Q2 filing.'},
                                  {'donor': 'Muraina Akinfolarin',
                                   'amount': 200.0,
                                   'type': 'Individual',
                                   'interest_group': 'Individual',
                                   'notes': 'Named contribution listed in the Q2 filing.'},
                                  {'donor': 'Keith Hoffmann',
                                   'amount': 200.0,
                                   'type': 'Individual',
                                   'interest_group': 'Individual',
                                   'notes': 'Named contribution listed in the Q2 filing.'},
                                  {'donor': 'William J. Murphy',
                                   'amount': 200.0,
                                   'type': 'Individual',
                                   'interest_group': 'Individual',
                                   'notes': 'Named contribution listed in the Q2 filing.'},
                                  {'donor': 'Anthony Simon',
                                   'amount': 200.0,
                                   'type': 'Individual',
                                   'interest_group': 'Individual',
                                   'notes': 'Named contribution listed in the Q2 filing.'},
                                  {'donor': 'Joseph W Walsh',
                                   'amount': 200.0,
                                   'type': 'Individual',
                                   'interest_group': 'Individual',
                                   'notes': 'Named contribution listed in the Q2 filing.'},
                                  {'donor': 'RI BROTHERHOOD OF CORRECTIONAL OFFICERS PAC',
                                   'amount': 200.0,
                                   'type': 'PAC',
                                   'interest_group': 'Public Safety',
                                   'notes': 'Named contribution listed in the Q2 filing.'},
                                  {'donor': 'Zachary G Darrow',
                                   'amount': 150.0,
                                   'type': 'Individual',
                                   'interest_group': 'Individual',
                                   'notes': 'Named contribution listed in the Q2 filing.'}],
                   'spending_categories': [{'title': 'Travel & Lodging',
                                            'summary': 'Visible spending includes American Airlines, Boston Logan '
                                                       'International Airport, Lyft and Marriott.',
                                            'amount': 792.76},
                                           {'title': 'Office Equipment & Supplies',
                                            'summary': 'Visible spending includes three payments to Hanna Pro, LLC.',
                                            'amount': 750.0},
                                           {'title': 'Fundraising Expenses',
                                            'summary': "Visible spending includes Patrick's Pub.",
                                            'amount': 683.5},
                                           {'title': 'Donations (All Others)',
                                            'summary': "Visible spending includes the Providence St. Patrick's Day "
                                                       'Parade and The Wings Mentorship Through Sports.',
                                            'amount': 350.0},
                                           {'title': 'Food, Beverages and Meals',
                                            'summary': 'Visible spending includes Condesa Restaurante Mexicano and '
                                                       "Sala'o Cuban Restaurant & Bar.",
                                            'amount': 177.6},
                                           {'title': 'Bank Fees',
                                            'summary': 'Visible spending includes ActBlue and Citizens Bank.',
                                            'amount': 29.12}],
                   'takeaways': [],
                   'explainer_cards': []}}


def apply_ajello_garman_biah_q2_overrides(profile: dict[str, object]) -> dict[str, object]:
    override = AJELLO_GARMAN_BIAH_Q2_OVERRIDES.get(str(profile.get("slug", "")))
    if not override:
        return profile
    profile.update(override)
    return profile


HOUSE_4_5_6_7_9_Q2_OVERRIDES = {'rebecca-m-kislak': {'report_label': '2026 On-Going Qrtly (2nd)',
                      'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                      'source_note': "Built from Rebecca M Kislak's Rhode Island Q2 2026 campaign finance filing "
                                     'supplied by the user.',
                      'coverage_note': 'Q2 2026 is the standardized main display. No Q1 source PDF was included in '
                                       'this upload batch, so this update does not invent a Q1 filing history.',
                      'original_documents': [{'label': 'Q2 2026 CF-2 report',
                                              'period': 'April 1, 2026 to June 30, 2026',
                                              'href': '/data/finance-documents/rebecca-m-kislak-q2-2026.pdf'}],
                      'beginning_cash': 38847.94,
                      'money_raised': 7164.0,
                      'money_spent': 2650.52,
                      'ending_cash': 43361.42,
                      'net_change': 4513.48,
                      'total_cash_receipts': 7164.0,
                      'campaign_expenses': 2650.52,
                      'aggregate_expenses': 0.0,
                      'summary_intro': "Rebecca M Kislak's Q2 2026 filing reports $7,164.00 in receipts, $2,650.52 in "
                                       'campaign expenses, and $43,361.42 in cash on hand.',
                      'filing_history': [{'label': 'Q2 2026',
                                          'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                          'money_raised': 7164.0,
                                          'money_spent': 2650.52,
                                          'ending_cash': 43361.42,
                                          'net_change': 4513.48,
                                          'notes': 'Q2 is the standardized main display period.'}],
                      'source_buckets': [{'label': 'Itemized individual donors',
                                          'class_name': 'itemized-individual-donors',
                                          'amount': 6189.0,
                                          'description': 'Named individual contributions reported in Q2.'},
                                         {'label': 'PAC contributions',
                                          'class_name': 'pac-contributions',
                                          'amount': 975.0,
                                          'description': 'Political action committee contributions reported in Q2.'}],
                      'top_donors': [{'donor': 'Paula Kislak',
                                      'amount': 1000.0,
                                      'type': 'Individual',
                                      'interest_group': 'Individual',
                                      'notes': 'Employer listed as unemployed.'},
                                     {'donor': 'Michelle McGaw',
                                      'amount': 335.0,
                                      'type': 'Individual',
                                      'interest_group': 'Individual',
                                      'notes': 'Employer listed as RI General Assembly; contribution description notes '
                                               'food for a shared fundraiser.'},
                                     {'donor': 'Elliot Perlman',
                                      'amount': 250.0,
                                      'type': 'Individual',
                                      'interest_group': 'Individual',
                                      'notes': 'Employer listed as not employed.'},
                                     {'donor': 'Judith Seminoff',
                                      'amount': 250.0,
                                      'type': 'Individual',
                                      'interest_group': 'Individual',
                                      'notes': 'Employer listed as not employed.'},
                                     {'donor': 'Louis Gitlin',
                                      'amount': 250.0,
                                      'type': 'Individual',
                                      'interest_group': 'Individual',
                                      'notes': 'Employer listed as Mid City Scrap.'},
                                     {'donor': 'Karen McAninch',
                                      'amount': 200.0,
                                      'type': 'Individual',
                                      'interest_group': 'Individual',
                                      'notes': 'Employer listed as retired.'},
                                     {'donor': 'RI MEDICAL PAC',
                                      'amount': 200.0,
                                      'type': 'PAC',
                                      'interest_group': 'Health Care',
                                      'notes': 'Named contribution listed in the Q2 filing.'},
                                     {'donor': 'Renee Rulin',
                                      'amount': 200.0,
                                      'type': 'Individual',
                                      'interest_group': 'Individual',
                                      'notes': 'Employer listed as not employed.'},
                                     {'donor': 'CAREPAC OF BLUE CROSS & BLUE SHIELD OF RI',
                                      'amount': 150.0,
                                      'type': 'PAC',
                                      'interest_group': 'Health Care',
                                      'notes': 'Named contribution listed in the Q2 filing.'},
                                     {'donor': 'RI ASSOCIATION OF NURSE ANESTHETISTS PAC',
                                      'amount': 125.0,
                                      'type': 'PAC',
                                      'interest_group': 'Health Care',
                                      'notes': 'Named contribution listed in the Q2 filing.'}],
                      'spending_categories': [{'title': 'Other',
                                               'summary': 'Visible spending includes Google, MLK Elementary, and RI '
                                                          'Pride/Peachtree.',
                                               'amount': 1184.03},
                                              {'title': 'Fundraising Expenses',
                                               'summary': 'Visible spending includes The District.',
                                               'amount': 694.41},
                                              {'title': 'Advertising',
                                               'summary': 'Visible spending includes Regine Printing and USPS.',
                                               'amount': 590.36},
                                              {'title': 'Consultant & Professional Services',
                                               'summary': 'Visible spending includes Orson Boucek.',
                                               'amount': 125.0},
                                              {'title': 'Food, Beverages and Meals',
                                               'summary': 'Reported campaign expenses listed in the filing.',
                                               'amount': 56.72}],
                      'takeaways': [],
                      'explainer_cards': []},
 'anthony-j-desimone': {'report_label': '2026 On-Going Qrtly (2nd)',
                        'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                        'source_note': "Built from Anthony J DeSimone's Rhode Island Q1 and Q2 2026 campaign finance "
                                       'filings.',
                        'coverage_note': 'Detailed Q1/Q2 filing data; Q2 is the main display.',
                        'original_documents': [{'label': 'Q1 2026 CF-2 report',
                                                'period': 'January 1, 2026 to March 31, 2026',
                                                'href': '/data/finance-documents/anthony-j-desimone-q1-2026.pdf'},
                                               {'label': 'Q2 2026 CF-2 report',
                                                'period': 'April 1, 2026 to June 30, 2026',
                                                'href': '/data/finance-documents/anthony-j-desimone-q2-2026.pdf'}],
                        'beginning_cash': 40458.81,
                        'money_raised': 26050.0,
                        'money_spent': 2431.49,
                        'ending_cash': 64077.32,
                        'net_change': 23618.51,
                        'total_cash_receipts': 26050.0,
                        'campaign_expenses': 2431.49,
                        'aggregate_expenses': 0.0,
                        'summary_intro': "Anthony J DeSimone's Q2 2026 filing reports $26,050.00 in receipts, "
                                         '$2,431.49 in spending, and $64,077.32 in cash on hand.',
                        'filing_history': [{'label': 'Q1 2026',
                                            'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                            'money_raised': 0.0,
                                            'money_spent': 855.19,
                                            'ending_cash': 40458.81,
                                            'net_change': -855.19,
                                            'notes': 'The campaign spent more than it raised in this reporting '
                                                     'period.'},
                                           {'label': 'Q2 2026',
                                            'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                            'money_raised': 26050.0,
                                            'money_spent': 2431.49,
                                            'ending_cash': 64077.32,
                                            'net_change': 23618.51,
                                            'notes': 'Q2 is the standardized main display period.'}],
                        'source_buckets': [{'label': 'Itemized individual donors',
                                            'class_name': 'itemized-individual-donors',
                                            'amount': 21525.0,
                                            'description': 'Named individual contributions reported in Q2.'},
                                           {'label': 'PAC contributions',
                                            'class_name': 'pac-contributions',
                                            'amount': 4525.0,
                                            'description': 'Political action committee contributions reported in Q2.'}],
                        'top_donors': [{'donor': 'Gerard C. DiSanto II',
                                        'amount': 2000.0,
                                        'type': 'Individual',
                                        'interest_group': 'Individual',
                                        'notes': 'Employer listed as Club Desire.'},
                                       {'donor': 'Thomas E. Badway',
                                        'amount': 2000.0,
                                        'type': 'Individual',
                                        'interest_group': 'Individual',
                                        'notes': 'Employer listed as Law Offices of Thomas Badway.'},
                                       {'donor': 'John H. Petrarca',
                                        'amount': 1000.0,
                                        'type': 'Individual',
                                        'interest_group': 'Individual',
                                        'notes': 'Employer listed as Providence Auto Body.'},
                                       {'donor': 'Marisa L. Sepe',
                                        'amount': 1000.0,
                                        'type': 'Individual',
                                        'interest_group': 'Individual',
                                        'notes': 'Employer listed as North Eastern Tree Service.'},
                                       {'donor': 'Steven Vincent Ceceri',
                                        'amount': 1000.0,
                                        'type': 'Individual',
                                        'interest_group': 'Individual',
                                        'notes': 'Employer listed as New England Property Services.'},
                                       {'donor': 'Anthony M. Santoro',
                                        'amount': 500.0,
                                        'type': 'Individual',
                                        'interest_group': 'Individual',
                                        'notes': 'Employer listed as Santoro Oil.'},
                                       {'donor': 'Kenneth J. Marandola Jr.',
                                        'amount': 500.0,
                                        'type': 'Individual',
                                        'interest_group': 'Individual',
                                        'notes': 'Employer listed as KM Security Solutions, LLC.'},
                                       {'donor': 'PROVIDENCE FIREFIGHTERS LOCAL 799 IAFF (International Association of '
                                                 'Firefighters)',
                                        'amount': 500.0,
                                        'type': 'PAC',
                                        'interest_group': 'Public Safety',
                                        'notes': 'Named contribution listed in the Q2 filing.'},
                                       {'donor': 'Peter J. Petrarca',
                                        'amount': 500.0,
                                        'type': 'Individual',
                                        'interest_group': 'Individual',
                                        'notes': 'Employer listed as Petrarca & Petrarca Law Offices.'},
                                       {'donor': "RI LABORERS' PUBLIC EMPLOYEES PAC",
                                        'amount': 500.0,
                                        'type': 'PAC',
                                        'interest_group': 'Labor / Unions',
                                        'notes': 'Named contribution listed in the Q2 filing.'}],
                        'spending_categories': [{'title': 'Office Equipment & Supplies',
                                                 'summary': "Visible spending includes BJ's Wholesale Club, CVS "
                                                            'Pharmacy, and US Postmaster.',
                                                 'amount': 725.49},
                                                {'title': 'Donations (Political)',
                                                 'summary': 'Visible spending includes Friends of Greg Amore, Friends '
                                                            'of Nicholas Feola, and Friends of Shelley T. Peterson.',
                                                 'amount': 600.0},
                                                {'title': 'Food, Beverages and Meals',
                                                 'summary': "Visible spending includes Chelo's Hometown Bar & Grille, "
                                                            'Kirkbrae Country Club, and Sport and Leisure.',
                                                 'amount': 456.51},
                                                {'title': 'Donations (All Others)',
                                                 'summary': 'Visible spending includes Joseph Francis Niel Memorial '
                                                            'Golf Tournament, Mount Pleasant Little League, and St. '
                                                            "Anthony's Society.",
                                                 'amount': 397.0},
                                                {'title': 'Gifts',
                                                 'summary': 'Visible spending includes Edible.com.',
                                                 'amount': 122.34},
                                                {'title': 'Fundraising Expenses',
                                                 'summary': 'Visible spending includes Staples.',
                                                 'amount': 68.23},
                                                {'title': 'Other',
                                                 'summary': 'Visible spending includes Market Basket.',
                                                 'amount': 41.92},
                                                {'title': 'Bank Fees',
                                                 'summary': 'Visible spending includes Citizens Bank.',
                                                 'amount': 20.0}],
                        'takeaways': [],
                        'explainer_cards': []},
 'raymond-a-hull': {'report_label': '2026 On-Going Qrtly (2nd)',
                    'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                    'source_note': "Built from Raymond A Hull's Rhode Island Q1 and Q2 2026 campaign finance filings.",
                    'coverage_note': 'Detailed Q1/Q2 filing data; Q2 is the main display.',
                    'original_documents': [{'label': 'Q1 2026 CF-2 report',
                                            'period': 'January 1, 2026 to March 31, 2026',
                                            'href': '/data/finance-documents/raymond-a-hull-q1-2026.pdf'},
                                           {'label': 'Q2 2026 CF-2 report',
                                            'period': 'April 1, 2026 to June 30, 2026',
                                            'href': '/data/finance-documents/raymond-a-hull-q2-2026.pdf'}],
                    'beginning_cash': 182018.51,
                    'money_raised': 23200.0,
                    'money_spent': 4661.01,
                    'ending_cash': 200557.5,
                    'net_change': 18538.99,
                    'total_cash_receipts': 23200.0,
                    'campaign_expenses': 4661.01,
                    'aggregate_expenses': 0.0,
                    'summary_intro': "Raymond A Hull's Q2 2026 filing reports $23,200.00 in receipts, $4,661.01 in "
                                     'spending, and $200,557.50 in cash on hand.',
                    'filing_history': [{'label': 'Q1 2026',
                                        'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                        'money_raised': 1000.0,
                                        'money_spent': 1364.43,
                                        'ending_cash': 182018.51,
                                        'net_change': -364.43,
                                        'notes': 'The campaign spent more than it raised in this reporting period.'},
                                       {'label': 'Q2 2026',
                                        'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                        'money_raised': 23200.0,
                                        'money_spent': 4661.01,
                                        'ending_cash': 200557.5,
                                        'net_change': 18538.99,
                                        'notes': 'Q2 is the standardized main display period.'}],
                    'source_buckets': [{'label': 'Itemized individual donors',
                                        'class_name': 'itemized-individual-donors',
                                        'amount': 19200.0,
                                        'description': 'Named individual contributions reported in Q2.'},
                                       {'label': 'PAC contributions',
                                        'class_name': 'pac-contributions',
                                        'amount': 4000.0,
                                        'description': 'Political action committee contributions reported in Q2.'}],
                    'top_donors': [{'donor': 'Gerard C. DiSanto II',
                                    'amount': 1000.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Employer listed as Club Desire.'},
                                   {'donor': "John E. O'Rourke Jr.",
                                    'amount': 1000.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Employer listed as Sodexho.'},
                                   {'donor': 'John H. Petrarca',
                                    'amount': 1000.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Employer listed as Providence Auto Body.'},
                                   {'donor': 'Lisa M. Andoscia',
                                    'amount': 1000.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Employer listed as Rosewood Consulting.'},
                                   {'donor': "Roseann M. O'Rourke",
                                    'amount': 1000.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Employer listed as retired.'},
                                   {'donor': 'Thomas E. Badway',
                                    'amount': 500.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Employer listed as Thomas E. Badway & Associates LLC.'},
                                   {'donor': 'Albert Gianfrancesco',
                                    'amount': 400.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Employer listed as Louis Family Restaurant.'},
                                   {'donor': 'Deborah M. Dimeo',
                                    'amount': 350.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Employer listed as not employed.'},
                                   {'donor': 'AMALGAMATED TRANSIT UNION COPE-RHODE ISLAND',
                                    'amount': 300.0,
                                    'type': 'PAC',
                                    'interest_group': 'Labor / Unions',
                                    'notes': 'Named contribution listed in the Q2 filing.'},
                                   {'donor': 'Frank A. Ciccone',
                                    'amount': 300.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Employer listed as State of Rhode Island.'}],
                    'spending_categories': [{'title': 'Fundraising Expenses',
                                             'summary': "Visible spending includes BBB, LLC, Gilligan's Pub, and "
                                                        'Hopkins Press.',
                                             'amount': 2706.3},
                                            {'title': 'Donations (All Others)',
                                             'summary': "Visible spending includes Providence Permanent Firemen's "
                                                        'Relief Assoc. and Special Signal Fire Association.',
                                             'amount': 1100.0},
                                            {'title': 'Advertising',
                                             'summary': 'Visible spending includes Central High School Alumni '
                                                        'Association and The Valley Breeze.',
                                             'amount': 445.0},
                                            {'title': 'Donations (Political)',
                                             'summary': 'Visible spending includes Friends of Chris Blazejewski, '
                                                        'Friends of Jo-Ann Ryan, and Friends of Joseph Solomon Jr.',
                                             'amount': 400.0},
                                            {'title': 'Bank Fees',
                                             'summary': 'Visible spending includes ActBlue.',
                                             'amount': 9.71}],
                    'takeaways': [],
                    'explainer_cards': []},
 'amy-j-santiago': {'report_label': '2026 On-Going Qrtly (2nd)',
                    'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                    'source_note': "Built from Amy Joseph Santiago's Rhode Island Q1 and Q2 2026 campaign finance "
                                   'filings.',
                    'coverage_note': 'Detailed Q1/Q2 filing data; Q2 is the main display. Q2 includes a $300 '
                                     'returned/NSF check and $151.16 of in-kind PAC support.',
                    'original_documents': [{'label': 'Q1 2026 CF-2 report',
                                            'period': 'January 1, 2026 to March 31, 2026',
                                            'href': '/data/finance-documents/amy-j-santiago-q1-2026.pdf'},
                                           {'label': 'Q2 2026 CF-2 report',
                                            'period': 'April 1, 2026 to June 30, 2026',
                                            'href': '/data/finance-documents/amy-j-santiago-q2-2026.pdf'}],
                    'beginning_cash': 6768.65,
                    'money_raised': 2626.0,
                    'money_spent': 3577.17,
                    'ending_cash': 5517.48,
                    'net_change': -1251.17,
                    'total_cash_receipts': 2626.0,
                    'campaign_expenses': 3577.17,
                    'aggregate_expenses': 0.0,
                    'summary_intro': "Amy J Santiago's Q2 2026 filing reports $2,626.00 in gross cash receipts and "
                                     '$3,577.17 in campaign expenses. A $300 NSF/returned check reduced cash during '
                                     'the quarter, producing an ending cash balance of $5,517.48. The filing also '
                                     'reports $151.16 in in-kind support from the RI Working Families Party PAC.',
                    'filing_history': [{'label': 'Q1 2026',
                                        'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                        'money_raised': 109.0,
                                        'money_spent': 2396.32,
                                        'ending_cash': 6768.65,
                                        'net_change': -2287.32,
                                        'notes': 'The campaign spent more than it raised in this reporting period.'},
                                       {'label': 'Q2 2026',
                                        'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                        'money_raised': 2626.0,
                                        'money_spent': 3577.17,
                                        'ending_cash': 5517.48,
                                        'net_change': -1251.17,
                                        'notes': 'Gross cash receipts were $2,626.00; a separate $300 NSF/returned '
                                                 'check reduced cash during the quarter.'}],
                    'source_buckets': [{'label': 'Itemized individual donors',
                                        'class_name': 'itemized-individual-donors',
                                        'amount': 2617.0,
                                        'description': 'Gross individual contributions reported in Q2.'},
                                       {'label': 'Refunds / rebates',
                                        'class_name': 'refunds-rebates',
                                        'amount': 9.0,
                                        'description': 'Monthly service-fee waivers reported as refunds/rebates.'}],
                    'top_donors': [{'donor': 'Jonathan Hird',
                                    'amount': 600.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Two $300 contributions are listed; a separate $300 NSF/returned-check '
                                             'entry later reduced campaign cash.'},
                                   {'donor': 'Samuel Bell',
                                    'amount': 350.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Employer listed as Planetary Science Institute.'},
                                   {'donor': 'Brandon Potter',
                                    'amount': 250.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Employer listed as Keches Law Group.'},
                                   {'donor': 'Michael Miranda',
                                    'amount': 250.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Named individual contribution listed in the filing.'},
                                   {'donor': 'Paula Hudson',
                                    'amount': 250.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Employer listed as Better Lives Rhode Island.'},
                                   {'donor': 'RI WORKING FAMILIES PARTY PAC',
                                    'amount': 151.16,
                                    'type': 'PAC',
                                    'interest_group': 'Political Party / Leadership',
                                    'notes': 'In-kind staff time; not included in cash receipts.'},
                                   {'donor': 'Jacqueline E. Goldman',
                                    'amount': 100.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Named contribution listed in the Q2 filing.'},
                                   {'donor': 'Mederick Bellaire',
                                    'amount': 100.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'ActBlue contribution.'},
                                   {'donor': 'Rachel Carpenter',
                                    'amount': 100.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'ActBlue contribution.'},
                                   {'donor': 'Stewart Martin',
                                    'amount': 100.0,
                                    'type': 'Individual',
                                    'interest_group': 'Individual',
                                    'notes': 'Named contribution listed in the Q2 filing.'}],
                    'spending_categories': [{'title': 'Food, Beverages and Meals',
                                             'summary': 'Visible spending includes Patriarca Restaurant & Tortillería.',
                                             'amount': 1546.0},
                                            {'title': 'Consultant & Professional Services',
                                             'summary': 'Visible spending includes Isabel Irizarry.',
                                             'amount': 1025.0},
                                            {'title': 'Advertising',
                                             'summary': 'Visible spending includes Canva, SignRocket, and Squarespace.',
                                             'amount': 847.44},
                                            {'title': 'Fundraising Expenses',
                                             'summary': 'Visible spending includes ActBlue, Delta Wine & More, and '
                                                        'Ocean State Job Lot.',
                                             'amount': 149.73},
                                            {'title': 'Bank Fees',
                                             'summary': 'Visible spending includes Coastal1.',
                                             'amount': 9.0}],
                    'takeaways': [],
                    'explainer_cards': []},
 'christopher-l-ireland': {'report_label': '2026 On-Going Qrtly (2nd)',
                           'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                           'source_note': "Built from Christopher Leslie Ireland's Rhode Island Q1 and Q2 2026 "
                                          'campaign finance filings.',
                           'coverage_note': 'Q2 2026 is the standardized main display. No contributions were reported '
                                            'in either Q1 or Q2.',
                           'original_documents': [{'label': 'Q1 2026 CF-2 report',
                                                   'period': 'January 1, 2026 to March 31, 2026',
                                                   'href': '/data/finance-documents/christopher-l-ireland-q1-2026.pdf'},
                                                  {'label': 'Q2 2026 CF-2 report',
                                                   'period': 'April 1, 2026 to June 30, 2026',
                                                   'href': '/data/finance-documents/christopher-l-ireland-q2-2026.pdf'}],
                           'beginning_cash': 195.2,
                           'money_raised': 0.0,
                           'money_spent': 30.0,
                           'ending_cash': 165.2,
                           'net_change': -30.0,
                           'total_cash_receipts': 0.0,
                           'campaign_expenses': 30.0,
                           'aggregate_expenses': 0.0,
                           'summary_intro': "Christopher L Ireland's Q2 2026 filing reports no receipts, $30.00 in "
                                            'bank fees, and $165.20 in cash on hand.',
                           'filing_history': [{'label': 'Q1 2026',
                                               'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                               'money_raised': 0.0,
                                               'money_spent': 30.0,
                                               'ending_cash': 195.2,
                                               'net_change': -30.0,
                                               'notes': 'The campaign spent more than it raised in this reporting '
                                                        'period.'},
                                              {'label': 'Q2 2026',
                                               'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                               'money_raised': 0.0,
                                               'money_spent': 30.0,
                                               'ending_cash': 165.2,
                                               'net_change': -30.0,
                                               'notes': 'Q2 is the standardized main display period.'}],
                           'source_buckets': [],
                           'top_donors': [],
                           'spending_categories': [{'title': 'Bank Fees',
                                                    'summary': 'Three $10 monthly Santander Bank fees.',
                                                    'amount': 30.0}],
                           'takeaways': [],
                           'explainer_cards': []},
 'enrique-george-sanchez': {'report_label': '2026 On-Going Qrtly (2nd)',
                            'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                            'source_note': "Built from Enrique George Sanchez's Rhode Island Q1 and Q2 2026 campaign "
                                           'finance filings.',
                            'coverage_note': 'Detailed Q1/Q2 filing data; Q2 is the main display. The Q2 filing itself '
                                             'reports a $1,091.85 beginning balance, which does not match the '
                                             '$2,260.85 ending balance shown on the supplied Q1 filing; the source '
                                             'discrepancy is preserved rather than silently reconciled.',
                            'original_documents': [{'label': 'Q1 2026 CF-2 report',
                                                    'period': 'January 1, 2026 to March 31, 2026',
                                                    'href': '/data/finance-documents/enrique-george-sanchez-q1-2026.pdf'},
                                                   {'label': 'Q2 2026 CF-2 report',
                                                    'period': 'April 1, 2026 to June 30, 2026',
                                                    'href': '/data/finance-documents/enrique-george-sanchez-q2-2026.pdf'}],
                            'beginning_cash': 1091.85,
                            'money_raised': 295.0,
                            'money_spent': 1494.36,
                            'ending_cash': -107.51,
                            'net_change': -1199.36,
                            'total_cash_receipts': 295.0,
                            'campaign_expenses': 1494.36,
                            'aggregate_expenses': 0.0,
                            'summary_intro': "Enrique George Sanchez's Q2 2026 filing reports $295.00 in individual "
                                             'contributions and $1,494.36 in campaign expenses, ending the period with '
                                             'a reported negative cash balance of $107.51.',
                            'filing_history': [{'label': 'Q1 2026',
                                                'reporting_period_label': 'January 1, 2026 to March 31, 2026',
                                                'money_raised': 2130.0,
                                                'money_spent': 26.24,
                                                'ending_cash': 2260.85,
                                                'net_change': 2103.76,
                                                'notes': 'The campaign raised more than it spent in this reporting '
                                                         'period.'},
                                               {'label': 'Q2 2026',
                                                'reporting_period_label': 'April 1, 2026 to June 30, 2026',
                                                'money_raised': 295.0,
                                                'money_spent': 1494.36,
                                                'ending_cash': -107.51,
                                                'net_change': -1199.36,
                                                'notes': 'The Q2 filing reports a $1,091.85 beginning balance, which '
                                                         'differs from the supplied Q1 ending balance.'}],
                            'source_buckets': [{'label': 'Itemized individual donors',
                                                'class_name': 'itemized-individual-donors',
                                                'amount': 295.0,
                                                'description': 'Named individual contributions reported in Q2.'}],
                            'top_donors': [{'donor': 'Tahon Ross',
                                            'amount': 100.0,
                                            'type': 'Individual',
                                            'interest_group': 'Individual',
                                            'notes': 'Employer listed as City of Boston.'},
                                           {'donor': 'William Colwell',
                                            'amount': 100.0,
                                            'type': 'Individual',
                                            'interest_group': 'Individual',
                                            'notes': 'Employer listed as Butler Hospital.'},
                                           {'donor': 'Patrick Trentalange',
                                            'amount': 50.0,
                                            'type': 'Individual',
                                            'interest_group': 'Individual',
                                            'notes': 'Employer listed as CPUSA.'},
                                           {'donor': 'Jonathan Daly-LaBelle',
                                            'amount': 30.0,
                                            'type': 'Individual',
                                            'interest_group': 'Individual',
                                            'notes': 'Employer listed as self-employed realtor.'},
                                           {'donor': 'Gregory Greco',
                                            'amount': 15.0,
                                            'type': 'Individual',
                                            'interest_group': 'Individual',
                                            'notes': 'Employer listed as Southeastern Regional School District.'}],
                            'spending_categories': [{'title': 'Food, Beverages and Meals',
                                                     'summary': 'Visible spending includes Dunkin, El Chapin, and '
                                                                'Playa PVD.',
                                                     'amount': 724.86},
                                                    {'title': 'Consultant & Professional Services',
                                                     'summary': 'Visible spending includes Mehki Arajuao, Susana '
                                                                'Espinal, and Johan Ji.',
                                                     'amount': 675.0},
                                                    {'title': 'Fundraising Expenses',
                                                     'summary': 'Visible spending includes ActBlue.',
                                                     'amount': 59.96},
                                                    {'title': 'Travel & Lodging',
                                                     'summary': 'Visible spending includes Lyft.',
                                                     'amount': 17.99},
                                                    {'title': 'Office Equipment & Supplies',
                                                     'summary': 'Visible spending includes Staples.',
                                                     'amount': 14.55},
                                                    {'title': 'Bank Fees',
                                                     'summary': 'Visible spending includes Washington Trust.',
                                                     'amount': 2.0}],
                            'takeaways': [],
                            'explainer_cards': []}}


def apply_house_4_5_6_7_9_q2_overrides(profile: dict[str, object]) -> dict[str, object]:
    override = HOUSE_4_5_6_7_9_Q2_OVERRIDES.get(str(profile.get("slug", "")))
    if not override:
        return profile
    profile.update(override)
    return profile

def classify_interest_group(donor: dict[str, object]) -> str:
    name = str(donor.get("donor", "") or "").strip().lower()
    donor_type = str(donor.get("type", "") or "").strip().lower()

    # Do not infer an individual's policy interests from employer/occupation.
    if "individual" in donor_type and "pac" not in donor_type and "committee" not in donor_type:
        return "Individual"

    for category, keywords in INTEREST_GROUP_RULES:
        if any(keyword in name for keyword in keywords):
            return category

    if "political party" in donor_type:
        return "Political Party / Leadership"
    if any(token in donor_type for token in ("pac", "committee", "organization", "party")):
        return "Other / Unclassified"
    if "individual" in donor_type:
        return "Individual"
    return "Other / Unclassified"

def enrich_interest_groups(profile: dict[str, object]) -> dict[str, object]:
    donors = profile.get("top_donors") or []
    for donor in donors:
        if isinstance(donor, dict):
            donor["interest_group"] = classify_interest_group(donor)
    return profile

def is_searchable_named_donor(donor: dict[str, object]) -> bool:
    name = str(donor.get("donor", "") or "").strip().lower()
    donor_type = str(donor.get("type", "") or "").strip().lower()
    if not name or name in {"(not listed)", "not listed", "unknown"}:
        return False
    if "aggregate" in donor_type or "unitemized" in name or "without donor names" in name:
        return False
    return True

def build_sitewide_donor_index(profiles: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for profile in profiles:
        for donor in profile.get("top_donors") or []:
            if not isinstance(donor, dict) or not is_searchable_named_donor(donor):
                continue
            rows.append({
                "donor": str(donor.get("donor", "")),
                "amount": round(float(donor.get("amount", 0.0) or 0.0), 2),
                "type": str(donor.get("type", "Donor")),
                "interest_group": str(donor.get("interest_group") or classify_interest_group(donor)),
                "notes": str(donor.get("notes", "")),
                "candidate_id": str(profile.get("candidate_id", "")),
                "candidate_name": str(profile.get("candidate_name", "")),
                "chamber": str(profile.get("chamber", "")),
                "district_number": str(profile.get("district_number", "")),
                "party": str(profile.get("party", "")),
                "slug": str(profile.get("slug", "")),
            })
    rows.sort(key=lambda row: (
        str(row["donor"]).lower(),
        -float(row["amount"]),
        str(row["candidate_name"]).lower(),
    ))
    return rows

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


def normalize_candidate_key(value: str) -> str:
    text = normalize_name(value)
    tokens = [token for token in text.split() if token]
    suffixes = {"jr", "sr", "ii", "iii", "iv", "v"}
    stopwords = {"mr", "mrs", "ms", "miss", "dr", "hon", "rep", "sen"}
    filtered: list[str] = []
    for index, token in enumerate(tokens):
        if token in suffixes or token in stopwords:
            continue
        # Drop middle initials like "g" in "john g edwards" but keep single-token names.
        if len(token) == 1 and index not in {0, len(tokens) - 1}:
            continue
        filtered.append(token)
    return " ".join(filtered or tokens)

CASH_ON_HAND_OVERRIDES = {
    'alana dimario': 44545.71,
    'albert joseph vitali': 73.06,
    'alex finkelman': 100542.07,
    'alex marszalkowski': 17680.80,
    'allan fung': 0.00,
    'amy santiago': 5517.48,
    'ana quezada': 2424.46,
    'andrew dimitri': 43871.41,
    'angela coburn': 1245.00,
    'angela lima': 15651.70,
    'anthony desimone': 64077.32,
    'arlette hidalgo': 2946.10,
    'arthur corvese': 13247.30,
    'arthur handy': 23661.00,
    'barbara quigley': 5.00,
    'brandon potter': 35367.22,
    'brandon voas': 16189.17,
    'brian coogan': 0.00,
    'brian newberry': 15008.49,
    'brian patrick kennedy': 70908.00,
    'brian thompson': 32283.34,
    'bridget valverde': 47947.80,
    'brittany kubicek': 4018.69,
    'cameron moquin': 2260.05,
    'cameron st germain': 3402.20,
    'carlos cedeno': 0.00,
    'carol hagan mcentee': 83982.92,
    'charlene lima': 105102.91,
    'cherie cruz': 19211.54,
    'christopher blazejewski': 608809.48,
    'christopher ireland': 165.20,
    'christopher paplauskas': 28314.70,
    'colleen crudele': 0.00,
    'dana james traversie': 28022.22,
    'david bennett': 39586.69,
    'david place': 4427.49,
    'david tikoian': 307059.99,
    'dawn euer': 65049.41,
    'deborah fellela': 10139.28,
    'earl read': 33493.45,
    'edith ajello': 23536.69,
    'edward cardillo': 17788.73,
    'edward stravato': 45724.70,
    'elaine morgan': 8890.27,
    'enrique george sanchez': 1091.85,
    'evan patrick shanley': 32358.05,
    'frank ciccone': 270340.41,
    'gena felix': 5986.77,
    'george nardone': 5454.95,
    'gordon rogers': 37145.78,
    'grace diaz': 4957.20,
    'grant webber wosencroft': 3901.72,
    'hanna gallo': 195600.05,
    'jacob bissaillon': 81421.87,
    'jacquelyn baginski': 217427.77,
    'james mclaughlin': 251.19,
    'james metivier': 27812.18,
    'james pierson': 6.39,
    'james sheehan': 2706.85,
    'janie lee segui': 0.00,
    'jasmin roy': 5147.96,
    'jean barros': 50047.18,
    'jenni furtado': 10718.17,
    'jennifer nerbonne': 2239.16,
    'jennifer smith boylan': 33287.35,
    'jennifer stewart': 42203.95,
    'jessica de la cruz': 59575.12,
    'jessica drew day': 5311.61,
    'jina petrarca': 0.00,
    'jo-ann ryan': 32438.76,
    'john burke': 54855.09,
    'john douglas barr': 100.00,
    'john edwards': 75582.25,
    'john joseph lombardi': 70554.20,
    'jon brien': 25097.59,
    'jonathon acosta': 12736.97,
    'joseph depasquale': 0.00,
    'joseph hosey': 19132.25,
    'joseph mcnamara': 49932.40,
    'joshua giraldo': 28006.72,
    'june speakman': 12797.55,
    'justine caldwell': 28083.90,
    'karen alzate': 2653.17,
    'katherine sheena kazarian': 185822.87,
    'kathleen fogarty': 10721.40,
    'kevin hoyle': 66040.90,
    'kevin whalen': 0.00,
    'lammis vargas': 31350.05,
    'lauren carson': 27542.21,
    'lawrence paul almagno': 7252.61,
    'leah boisclair': 12973.79,
    'leonela felix': 9460.65,
    'leonidas peter raptakis': 51672.75,
    'linda ujifusa': 2248.38,
    'lori urso': 46854.51,
    'louis dipalma': 145709.16,
    'luis ernesto sandoval': 10.00,
    'marie hopkins': 25051.75,
    'mark mckenney': 47671.10,
    'mark mesrobian': 107311.17,
    'mark theroux': 7379.60,
    'marvin abney': 256687.46,
    'mary ann shallcross smith': 41142.61,
    'mary duffy messier': 19459.43,
    'matthew dawson': 24376.09,
    'matthew lamountain': 106740.44,
    'matthew mccoy': 500.00,
    'megan cotter': 28600.20,
    'meghan kallman': 50623.40,
    'melissa murray': 39591.88,
    'mia ackerman': 49463.38,
    'michael chippendale': 19694.29,
    'michael garman': 22613.87,
    'michael riley': 0.00,
    'michelle mcgaw': 21189.27,
    'nathan biah': 8614.72,
    'nelly burdette': 6480.27,
    'nicole jellinek': 19642.75,
    'pamela lauria': 31502.63,
    'patrick maloney': 0.00,
    'paul santucci': 34858.77,
    'peter appollonio': 41265.18,
    'ramon perez': 518.93,
    'raymond hull': 200557.50,
    'rebecca kislak': 43361.42,
    'richard fascia': 9733.56,
    'robert britto': 81025.04,
    'robert craven': 46292.98,
    'robert phillips': 15327.32,
    'ronald paul jarvais': 344.51,
    'ryan pearson': 67857.16,
    'samantha wilcox': 13314.95,
    'samuel angelo azzinaro': 19778.28,
    'samuel bell': 62931.06,
    'samuel zurier': 44505.45,
    'santos javier': 2309.77,
    'scott slater': 97505.96,
    'shaina smith': 618.56,
    'sherry roberts': 4555.21,
    'stefano famiglietti': 27049.97,
    'stephen casey': 23644.71,
    'stephen moffitt': 15.35,
    'susan ann donovan': 16224.12,
    'suzanna alba': 6218.10,
    'teresa tanzi': 6117.95,
    'terri-denise cortvriend': 25640.70,
    'thomas menec': 2710.97,
    'thomas noret': 88303.76,
    'thomas paolino': 18631.07,
    'tiara mack': 7691.98,
    'timothy howe': 14799.56,
    'tina spears': 18511.21,
    'todd patalano': 123323.44,
    'valarie jean lawson': 336650.61,
    'vanessa lopez': 9869.68,
    'veronicka vega': 5074.45,
    'victoria gu': 37897.25,
    'virginia susan sosnowski': 63996.88,
    'walter felag': 74284.69,
    'westin place': 609.06,
    'william connell': 0.00,
    'william muto': 11160.76,
    'william obrien': 50074.97,
    'zakary pereira': 0.00,
}


def apply_cash_on_hand_override(candidate_name: str, current_value: float) -> float:
    """Use the Ending Balance values from Cash_Hand_2026.xlsx for cash on hand only."""
    override = CASH_ON_HAND_OVERRIDES.get(normalize_candidate_key(candidate_name))
    return round(float(override), 2) if override is not None else round(float(current_value), 2)


def to_float(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, float):
        if value != value:
            return 0.0
        return value
    if isinstance(value, int):
        return float(value)
    cleaned = str(value).strip()
    if not cleaned or cleaned.lower() == "nan":
        return 0.0
    return parse_money(cleaned)


def clean_string(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    return clean_text(text)


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


def donor_name_looks_like_code(value: str) -> bool:
    text = clean_text(value)
    if not text:
        return False
    if len(text) < 4:
        return False
    if re.fullmatch(r"[\d,\sO-]+", text):
        return True
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if parts and all(re.fullmatch(r"[A-Z0-9]{1,6}", part) for part in parts):
        return True
    return False


def load_excel_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    frame = pd.read_excel(path, sheet_name=sheet_name)
    frame.columns = [clean_string(column) for column in frame.columns]
    return frame


def build_workbook_name_index(roster: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    index: dict[str, dict[str, object]] = {}
    for candidate in roster:
        name = str(candidate["name"])
        keys = {
            normalize_candidate_key(name),
            normalize_name(name),
        }
        for key in keys:
            if key:
                index[key] = candidate
    return index


def find_roster_candidate(name: str, roster_index: dict[str, dict[str, object]]) -> dict[str, object] | None:
    for key in (normalize_candidate_key(name), normalize_name(name)):
        if key in roster_index:
            return roster_index[key]
    return None


def workbook_candidate_id(candidate: dict[str, object]) -> str:
    return f"{candidate['chamber']}-{candidate['district_number']}-{slugify(str(candidate['name']))}"


def normalize_bucket_class(bucket: str) -> str:
    text = clean_string(bucket).lower()
    mapping = {
        "itemized individual donors": "individuals",
        "receipts without donor names listed": "aggregate individuals",
        "small-dollar / aggregate online receipts": "aggregate individuals",
        "pac contributions": "political action committees",
        "political action committees": "political action committees",
        "refunds / rebates": "refund/rebate",
        "other": "other",
        "other reported sources": "other",
        "total parsed receipts": "total",
    }
    return mapping.get(text, text)


def load_finance_workbooks(roster: list[dict[str, object]]) -> tuple[dict[str, dict[str, object]], list[dict[str, object]]]:
    roster_index = build_workbook_name_index(roster)
    discrepancies: list[dict[str, object]] = []
    candidates_by_id: dict[str, dict[str, object]] = {}

    def get_candidate_record(candidate: dict[str, object]) -> dict[str, object]:
        candidate_id = workbook_candidate_id(candidate)
        return candidates_by_id.setdefault(
            candidate_id,
            {
                "candidate": candidate,
                "summary_rows": {},
                "donors": [],
                "expenses": [],
                "receipt_totals": defaultdict(float),
                "submitted_filings": [],
                "coverage_note": "",
                "source_note": "",
            },
        )

    def ingest_summary(path: Path, source_label: str) -> None:
        frame = load_excel_sheet(path, "Candidate Summary")
        for _, row in frame.iterrows():
            name = clean_string(row.get("Candidate"))
            if not name:
                continue
            candidate = find_roster_candidate(name, roster_index)
            if not candidate:
                discrepancies.append(
                    {
                        "type": "unmatched-summary-candidate",
                        "source": source_label,
                        "candidate_name": name,
                    }
                )
                continue
            record = get_candidate_record(candidate)
            normalized_row = {column: row.get(column) for column in frame.columns}
            record["summary_rows"][source_label] = normalized_row
            record["coverage_note"] = clean_string(row.get("Data Coverage") or row.get("Source / Coverage") or row.get("Finance Status"))
            record["source_note"] = clean_string(row.get("Source / Coverage") or row.get("Source PDF") or row.get("Finance Status"))

    def ingest_donors(path: Path, source_label: str) -> None:
        frame = load_excel_sheet(path, "Donors & Receipts")
        for _, row in frame.iterrows():
            name = clean_string(row.get("Candidate"))
            if not name:
                continue
            candidate = find_roster_candidate(name, roster_index)
            if not candidate:
                continue
            record = get_candidate_record(candidate)
            donor_name = clean_string(
                row.get("Donor / Source")
                or row.get("Donor")
                or row.get("Contributor")
                or row.get("Name")
            )
            donor_type = clean_string(
                row.get("Contribution Type")
                or row.get("Type")
                or row.get("Receipt Type")
                or row.get("Category")
            )
            employer = clean_string(row.get("Employer"))
            description = clean_string(row.get("Description") or row.get("Notes"))
            amount = to_float(row.get("Amount"))
            quarter = clean_string(row.get("Quarter"))
            if amount <= 0:
                continue
            record["donors"].append(
                {
                    "donor": donor_name or donor_type or "Donor",
                    "amount": amount,
                    "type": donor_type or "Other",
                    "employer": employer,
                    "description": description,
                    "quarter": quarter,
                    "source": source_label,
                }
            )

    def ingest_expenses(path: Path, source_label: str) -> None:
        frame = load_excel_sheet(path, "Expenses")
        for _, row in frame.iterrows():
            name = clean_string(row.get("Candidate"))
            if not name:
                continue
            candidate = find_roster_candidate(name, roster_index)
            if not candidate:
                continue
            record = get_candidate_record(candidate)
            title = clean_string(row.get("Expense Type") or row.get("Category") or row.get("Purpose"))
            purpose = clean_string(row.get("Purpose") or row.get("Description"))
            vendor = clean_string(row.get("Vendor / Payee") or row.get("Vendor"))
            amount = to_float(row.get("Amount"))
            quarter = clean_string(row.get("Quarter"))
            if amount <= 0:
                continue
            record["expenses"].append(
                {
                    "expense_type": title or "Campaign spending",
                    "amount": amount,
                    "purpose": purpose,
                    "vendor": vendor,
                    "quarter": quarter,
                    "source": source_label,
                }
            )

    def ingest_receipt_totals(path: Path, source_label: str) -> None:
        frame = load_excel_sheet(path, "Receipt Category Totals")
        total_columns = (
            ("Itemized individual donors", "individuals"),
            ("Receipts without donor names listed", "aggregate individuals"),
            ("PAC contributions", "political action committees"),
            ("Refunds / rebates", "refund/rebate"),
            ("Other", "other"),
        )
        for _, row in frame.iterrows():
            name = clean_string(row.get("Candidate"))
            if not name:
                continue
            candidate = find_roster_candidate(name, roster_index)
            if not candidate:
                continue
            record = get_candidate_record(candidate)
            quarter = clean_string(row.get("Quarter"))
            if quarter != "Q2":
                continue
            for column_name, bucket in total_columns:
                amount = to_float(row.get(column_name))
                if amount > 0:
                    record["receipt_totals"][bucket] += amount

    def ingest_submitted_filings(path: Path) -> None:
        if not path.exists():
            return
        frame = load_excel_sheet(path, "Submitted Filings")
        for _, row in frame.iterrows():
            name = clean_string(row.get("Candidate"))
            if not name:
                continue
            candidate = find_roster_candidate(name, roster_index)
            if not candidate:
                continue
            record = get_candidate_record(candidate)
            quarter = clean_string(row.get("Quarter"))
            label = clean_string(row.get("Filing") or row.get("Report") or row.get("Label") or (f"{quarter} campaign finance filing" if quarter else ""))
            status = clean_string(row.get("Status") or row.get("Filing Status"))
            amended = clean_string(row.get("Amended"))
            href = clean_string(row.get("PDF Href") or row.get("Href") or row.get("Link"))
            period = clean_string(row.get("Period") or row.get("Reporting Period"))
            if not period:
                begin = clean_string(row.get("Begin"))
                end = clean_string(row.get("End"))
                if begin and end:
                    period = format_period(begin, end)
            if not label and not href and not period:
                continue
            record["submitted_filings"].append(
                {
                    "label": label or "Campaign finance filing",
                    "status": status,
                    "amended": amended,
                    "period": period,
                    "href": href,
                }
            )

    ingest_summary(WORKBOOK_SUMMARY_PATH, "manual-summary")
    ingest_donors(WORKBOOK_SUMMARY_PATH, "manual-summary")
    ingest_expenses(WORKBOOK_SUMMARY_PATH, "manual-summary")
    ingest_receipt_totals(WORKBOOK_SUMMARY_PATH, "manual-summary")
    ingest_submitted_filings(WORKBOOK_SUMMARY_PATH)

    ingest_summary(WORKBOOK_DETAIL_PATH, "manual-detail")
    ingest_donors(WORKBOOK_DETAIL_PATH, "manual-detail")
    ingest_expenses(WORKBOOK_DETAIL_PATH, "manual-detail")
    ingest_receipt_totals(WORKBOOK_DETAIL_PATH, "manual-detail")

    return candidates_by_id, discrepancies


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
        donor_type = str(entry.get("type", "") or "Donor")
        if donor_name_looks_like_code(donor):
            if donor_type == "Aggregate":
                donor = "Unitemized / aggregate receipts"
            elif donor_type == "PAC":
                donor = "Committee / PAC receipts"
            else:
                donor = "Donor names not readable in filing text"
        if not donor or donor in {"Aggregate", "Refund/Rebate"}:
            continue
        key = (donor, donor_type)
        item = grouped.setdefault(
            key,
            {
                "donor": donor,
                "amount": 0.0,
                "type": donor_type,
                "notes": "",
            },
        )
        item["amount"] = float(item["amount"]) + float(entry.get("amount", 0.0))
        if donor == "Unitemized / aggregate receipts":
            item["notes"] = "The filing reports these receipts in aggregate form without individual donor names."
        elif donor == "Committee / PAC receipts":
            item["notes"] = "The filing shows committee or PAC receipts, but the public text does not provide readable donor names here."
        elif donor == "Donor names not readable in filing text":
            item["notes"] = "The filing includes the contribution amount, but the public text does not surface a readable donor name."
        elif donor_type == "PAC":
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


def build_history_entry_from_workbook(
    label: str,
    period_start: str,
    period_end: str,
    money_raised: float,
    money_spent: float,
    ending_cash: float,
) -> dict[str, object]:
    net_change = round(float(money_raised) - float(money_spent), 2)
    note = (
        "The campaign raised more than it spent in this reporting period."
        if net_change >= 0
        else "The campaign spent more than it raised in this reporting period."
    )
    return {
        "label": label,
        "reporting_period_label": format_period(period_start, period_end),
        "money_raised": round(float(money_raised), 2),
        "money_spent": round(float(money_spent), 2),
        "ending_cash": round(float(ending_cash), 2),
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


def summary_value(row: dict[str, object], *keys: str) -> float:
    for key in keys:
        if key in row:
            value = to_float(row.get(key))
            if value or str(row.get(key)).strip():
                return value
    return 0.0


def summary_text(row: dict[str, object], *keys: str) -> str:
    for key in keys:
        value = clean_string(row.get(key))
        if value:
            return value
    return ""


def build_local_filing_row(label: str, period_start: str, period_end: str) -> dict[str, str]:
    return {
        "label": label,
        "period_start": period_start,
        "period_end": period_end,
        "due_date": "",
        "status": "Filed",
        "filed_at": "",
        "amended": "",
        "view_href": "",
    }


def build_workbook_profile(record: dict[str, object], existing_profile: dict[str, object] | None = None) -> tuple[dict[str, object] | None, list[dict[str, object]]]:
    candidate = record["candidate"]
    summary_rows = record.get("summary_rows", {})
    primary_row = summary_rows.get("manual-summary") or summary_rows.get("manual-detail")
    if not primary_row:
        return None, []

    fallback_row = summary_rows.get("manual-detail") if primary_row is summary_rows.get("manual-summary") else summary_rows.get("manual-summary")

    def get_float(*keys: str) -> float:
        value = summary_value(primary_row, *keys)
        if value == 0.0 and fallback_row:
            fallback_value = summary_value(fallback_row, *keys)
            if fallback_value:
                return fallback_value
        return value

    def get_text(*keys: str) -> str:
        value = summary_text(primary_row, *keys)
        if not value and fallback_row:
            return summary_text(fallback_row, *keys)
        return value

    website_beginning_cash = round(get_float("Website Beginning Balance"), 2)
    website_ending_cash = round(get_float("Website Ending Balance"), 2)
    website_total_cash = round(get_float("Website Total Cash"), 2)

    beginning_cash = round(get_float("Q1 Cash on Hand", "Website Beginning Balance"), 2)
    ending_cash = round(get_float("Q2 Cash on Hand", "Website Ending Balance"), 2)
    ending_cash = apply_cash_on_hand_override(str(candidate["name"]), ending_cash)
    total_cash = round(get_float("Q2 Total Cash Receipts", "Website Total Cash"), 2)

    # Prefer the public-facing website summary when it exists, because it mirrors the
    # Board of Elections summary sheet more reliably than the gross receipt subtotal
    # columns in Candidate Summary.
    if website_total_cash and website_beginning_cash:
        money_raised = round(max(website_total_cash - website_beginning_cash, 0.0), 2)
    else:
        money_raised = round(get_float("Q2 Total Cash Receipts", "Q2 Money Raised"), 2)

    if website_total_cash and website_ending_cash:
        money_spent = round(max(website_total_cash - website_ending_cash, 0.0), 2)
    else:
        money_spent = round(get_float("Q2 Spent"), 2)

    net_change = round(money_raised - money_spent, 2)

    receipt_totals = {key: round(float(value), 2) for key, value in dict(record.get("receipt_totals", {})).items() if round(float(value), 2) > 0}
    if not receipt_totals:
        bucket_pairs = [
            ("individuals", "Q2 Individuals"),
            ("aggregate individuals",),
            ("political action committees", "Q2 PAC"),
            ("refund/rebate", "Q2 Refund/Rebate"),
            ("other", "Q2 Other"),
        ]
        for bucket_keys in bucket_pairs:
            bucket = bucket_keys[0]
            source_key = bucket_keys[1] if len(bucket_keys) > 1 else None
            if source_key:
                amount = get_float(source_key)
                if amount > 0:
                    receipt_totals[bucket] = round(amount, 2)
        total_known = sum(receipt_totals.values())
        if total_cash > total_known:
            receipt_totals["aggregate individuals"] = round(receipt_totals.get("aggregate individuals", 0.0) + (total_cash - total_known), 2)

    source_buckets = build_source_buckets(receipt_totals)
    top_donors = build_top_donors(record.get("donors", []))
    spending_categories = summarize_spending(record.get("expenses", []))
    campaign_expenses = round(sum(float(item.get("amount", 0.0)) for item in record.get("expenses", [])), 2)
    aggregate_expenses = max(0.0, round(money_spent - campaign_expenses, 2))

    filing_history = [
        build_history_entry_from_workbook(
            "Q1 2026",
            "01/01/2026",
            "03/31/2026",
            get_float("Q1 Money Raised"),
            get_float("Q1 Spent"),
            get_float("Q1 Cash on Hand"),
        ),
        build_history_entry_from_workbook(
            "Q2 2026",
            "04/01/2026",
            "06/30/2026",
            money_raised,
            money_spent,
            ending_cash,
        ),
    ]

    original_documents: list[dict[str, str]] = []
    for filing in record.get("submitted_filings", []):
        href = clean_string(filing.get("href"))
        if not href:
            continue
        label = clean_string(filing.get("label")) or "Campaign finance filing"
        period = clean_string(filing.get("period")) or label
        original_documents.append(
            {
                "label": label,
                "period": period,
                "href": href,
            }
        )

    report_label = get_text("Website Summary Period End") or "Q2 2026 campaign finance filing"
    reporting_period_label = get_text("Website Summary Period End") or "April 1, 2026 to June 30, 2026"
    office = "State Representative" if candidate["chamber"] == "house" else "State Senator"
    party_code = str(candidate.get("party_code") or "")
    party = PARTY_DISPLAY.get(party_code, party_code)

    profile = {
        "candidate_id": workbook_candidate_id(candidate),
        "slug": slugify(str(candidate["name"])),
        "candidate_name": candidate["name"],
        "chamber": candidate["chamber"],
        "district_number": str(candidate["district_number"]),
        "party": party_code,
        "party_label": party,
        "office_sought": office,
        "report_label": report_label,
        "reporting_period_label": reporting_period_label,
        "source_note": record.get("source_note") or record.get("coverage_note") or "Workbook-backed finance profile built from Rhode Island campaign finance filings.",
        "coverage_note": record.get("coverage_note") or "",
        "original_documents": original_documents,
        "beginning_cash": beginning_cash,
        "money_raised": money_raised,
        "money_spent": money_spent,
        "ending_cash": ending_cash,
        "net_change": net_change,
        "total_cash_receipts": total_cash,
        "campaign_expenses": campaign_expenses,
        "aggregate_expenses": aggregate_expenses,
        "summary_intro": build_summary_intro(str(candidate["name"]), {"ending_cash": ending_cash, "net_change": net_change}),
        "filing_history": filing_history,
        "source_buckets": source_buckets,
        "top_donors": top_donors,
        "spending_categories": spending_categories,
        "takeaways": [],
        "explainer_cards": [],
    }

    discrepancies: list[dict[str, object]] = []
    if fallback_row:
        website_beginning = summary_value(primary_row, "Website Beginning Balance")
        website_ending = summary_value(primary_row, "Website Ending Balance")
        website_total_cash = summary_value(primary_row, "Website Total Cash")

        derived_summary_values = {
            "money_raised": round(max(website_total_cash - website_beginning, 0.0), 2)
            if website_total_cash or website_beginning
            else 0.0,
            "money_spent": round(max(website_total_cash - website_ending, 0.0), 2)
            if website_total_cash or website_ending
            else 0.0,
            "ending_cash": round(website_ending, 2),
        }
        detail_values = {
            "money_raised": round(summary_value(fallback_row, "Q2 Total Cash Receipts", "Q2 Money Raised"), 2),
            "money_spent": round(summary_value(fallback_row, "Q2 Spent"), 2),
            "ending_cash": round(summary_value(fallback_row, "Q2 Cash on Hand", "Website Ending Balance"), 2),
        }
        for field_name, primary_value in derived_summary_values.items():
            fallback_value = detail_values[field_name]
            if primary_value != fallback_value:
                discrepancies.append(
                    {
                        "type": "workbook-source-mismatch",
                        "candidate_id": profile["candidate_id"],
                        "candidate_name": profile["candidate_name"],
                        "field": field_name,
                        "manual_summary": primary_value,
                        "manual_detail": fallback_value,
                    }
                )

    if existing_profile:
        for field_name in ("money_raised", "money_spent", "ending_cash", "net_change"):
            old_value = round(float(existing_profile.get(field_name, 0.0)), 2)
            new_value = round(float(profile.get(field_name, 0.0)), 2)
            if old_value != new_value:
                discrepancies.append(
                    {
                        "type": "site-vs-workbook-mismatch",
                        "candidate_id": profile["candidate_id"],
                        "candidate_name": profile["candidate_name"],
                        "field": field_name,
                        "site_value": old_value,
                        "workbook_value": new_value,
                    }
                )

    return profile, discrepancies


def parse_candidate_profile(candidate: dict[str, object]) -> dict[str, object] | None:
    chamber = str(candidate["chamber"])
    office_code = OFFICE_CODE_BY_CHAMBER.get(chamber)
    party_code = PARTY_SEARCH_CODE.get(str(candidate.get("party_code") or candidate.get("party") or ""))
    if not office_code or not party_code:
        return None

    name = clean_text(str(candidate["name"]))
    slug = slugify(name)
    q2_pdf_path = DOCS_DIR / f"{slug}-q2-2026.pdf"
    q1_pdf_path = DOCS_DIR / f"{slug}-q1-2026.pdf"
    name_parts = name.split()
    first_name = name_parts[0]
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else name_parts[0]
    filing_rows: list[dict[str, str]] = []
    public_summary: dict[str, float] = {}
    q2_row: dict[str, str] | None = None
    q1_row: dict[str, str] | None = None

    try:
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
        if picked:
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
            q1_row = next((row for row in filing_rows if row["label"] == "2026 On-Going Qrtly (1st)"), None)
            if q2_row and q2_row.get("view_href"):
                secure_q2_html = fetch_html(q2_row["view_href"])
                q2_pdf_href = extract_pdf_href(secure_q2_html)
                if q2_pdf_href:
                    download_file(q2_pdf_href, q2_pdf_path)
            if q1_row and q1_row.get("view_href"):
                secure_q1_html = fetch_html(q1_row["view_href"])
                q1_pdf_href = extract_pdf_href(secure_q1_html)
                if q1_pdf_href:
                    download_file(q1_pdf_href, q1_pdf_path)
    except Exception as exc:  # noqa: BLE001
        print(f"  ! live lookup skipped for {name}: {exc}", file=sys.stderr)

    if not q2_row and q2_pdf_path.exists():
        q2_row = build_local_filing_row("2026 On-Going Qrtly (2nd)", "04/01/2026", "06/30/2026")
    if not q1_row and q1_pdf_path.exists():
        q1_row = build_local_filing_row("2026 On-Going Qrtly (1st)", "01/01/2026", "03/31/2026")
    if not q2_pdf_path.exists():
        return None
    if not q1_pdf_path.exists():
        q1_pdf_path = None

    q2_summary = parse_page_one_summary(q2_pdf_path)
    q2_summary["ending_cash"] = apply_cash_on_hand_override(name, float(q2_summary.get("ending_cash", 0.0)))
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
    existing_payload = json.loads(OUTPUT_PATH.read_text()) if OUTPUT_PATH.exists() else {}
    existing_profiles = {
        str(profile.get("candidate_id")): profile
        for profile in existing_payload.get("profiles", [])
    }
    workbook_records, workbook_discrepancies = load_finance_workbooks(roster)
    directory = []
    profiles = []
    discrepancies = list(workbook_discrepancies)

    for index, candidate in enumerate(roster, start=1):
        print(f"[{index}/{len(roster)}] {candidate['name']} ({candidate['chamber']} {candidate['district_number']})", file=sys.stderr)
        candidate_id = workbook_candidate_id(candidate)
        entry = {
            "candidate_name": candidate["name"],
            "slug": slugify(str(candidate["name"])),
            "candidate_id": candidate_id,
            "chamber": candidate["chamber"],
            "district_number": str(candidate["district_number"]),
            "party": candidate["party_code"],
            "office_sought": "State Representative" if candidate["chamber"] == "house" else "State Senator",
            "has_profile": False,
        }
        record = workbook_records.get(candidate_id)
        profile = None
        if candidate_id in LOCAL_PDF_PROFILE_OVERRIDES:
            try:
                profile = parse_candidate_profile(candidate)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! local PDF override failed: {exc}", file=sys.stderr)
                profile = None

        if profile is None and record:
            try:
                profile, profile_discrepancies = build_workbook_profile(record, existing_profiles.get(candidate_id))
                discrepancies.extend(profile_discrepancies)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! workbook build failed: {exc}", file=sys.stderr)
                profile = None
        elif profile is None and candidate_id in existing_profiles:
            profile = existing_profiles[candidate_id]

        if profile:
            profile = apply_profile_detail_overrides(profile)
            profile = apply_andrew_dimitri_detail_override(profile)
            profile = apply_quezada_bell_profile_overrides(profile)
            profile = apply_bell_dimitri_followup_overrides(profile)
            profile = apply_samuel_bell_q2_main_override(profile)
            profile = apply_connell_mack_q2_overrides(profile)
            profile = apply_ciccone_felag_ujifusa_q2_overrides(profile)
            profile = apply_lawson_kallman_paolino_q2_overrides(profile)
            profile = apply_pearson_thompson_rogers_q2_overrides(profile)
            profile = apply_tikoian_patalano_gallo_q2_overrides(profile)
            profile = apply_latest_senate_q2_overrides(profile)
            profile = apply_dimario_valverde_place_morgan_overrides(profile)
            profile = apply_ajello_garman_biah_q2_overrides(profile)
            profile = apply_house_4_5_6_7_9_q2_overrides(profile)
            profile = enrich_interest_groups(profile)
            profiles.append(profile)
            entry["has_profile"] = True
        directory.append(entry)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cycle": "2026-q2",
        "directory": directory,
        "donor_index": build_sitewide_donor_index(profiles),
        "donor_search_scope_note": "Donor search covers named donors currently listed in published campaign-finance profiles. Aggregate receipts reported without donor names cannot be searched.",
        "profiles": sorted(profiles, key=lambda item: (item["chamber"], int(item["district_number"]), item["candidate_name"])),
        "discrepancies": discrepancies,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {len(profiles)} profiles to {OUTPUT_PATH} with {len(discrepancies)} discrepancy notes", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

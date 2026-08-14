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
            profiles.append(profile)
            entry["has_profile"] = True
        directory.append(entry)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cycle": "2026-q2",
        "directory": directory,
        "profiles": sorted(profiles, key=lambda item: (item["chamber"], int(item["district_number"]), item["candidate_name"])),
        "discrepancies": discrepancies,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {len(profiles)} profiles to {OUTPUT_PATH} with {len(discrepancies)} discrepancy notes", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

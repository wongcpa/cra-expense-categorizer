"""
expense_categorizer.py
=======================
Bank Statement Expense Categorizer — CRA T2125 Mapping

Usage:
  python expense_categorizer.py

You will be prompted for:
  - Bank statement CSV file

Expected CSV columns:
  Date, Description, Debit, Credit, Balance
  (Debits are negative amounts; Credits are positive)

Test fixture: bank_statement.csv

Author: Jimmy Wong, CPA
DATA PRIVACY: All processing is local. Bank data never leaves your machine.
"""

import csv
import io
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# SECTION 1: CRA CATEGORIES & T2125 LINE MAPPING
# ---------------------------------------------------------------------------

CRA_CATEGORIES: Dict[str, Dict] = {
    "ADVERTISING":          {"t2125_line": "8520 — Advertising",                    "deductibility": 1.0,  "cra_note": "Fully deductible. Digital ads, print, signage."},
    "MEALS_ENTERTAINMENT":  {"t2125_line": "8523 — Meals and entertainment",         "deductibility": 0.5,  "cra_note": "50% deductible per ITA s.67.1. Retain receipts with business purpose."},
    "MOTOR_VEHICLE":        {"t2125_line": "9281 — Motor vehicle expenses",          "deductibility": 1.0,  "cra_note": "Deduct business-use portion only. Log km. See IT-521R."},
    "OFFICE_SUPPLIES":      {"t2125_line": "8810 — Office expenses",                 "deductibility": 1.0,  "cra_note": "Fully deductible. Small items used in the office."},
    "RENT":                 {"t2125_line": "8910 — Rent",                            "deductibility": 1.0,  "cra_note": "Business portion of rent fully deductible."},
    "TELEPHONE_INTERNET":   {"t2125_line": "9270 — Telephone and utilities",         "deductibility": 1.0,  "cra_note": "Deduct business-use portion. Personal not deductible."},
    "INSURANCE":            {"t2125_line": "8690 — Insurance",                       "deductibility": 1.0,  "cra_note": "Business insurance premiums fully deductible."},
    "PROFESSIONAL_FEES":    {"t2125_line": "8860 — Professional fees",               "deductibility": 1.0,  "cra_note": "Accounting, legal, consulting fees for business purposes."},
    "BANK_CHARGES":         {"t2125_line": "8710 — Bank charges and interest",       "deductibility": 1.0,  "cra_note": "Business account fees and loan interest deductible."},
    "SOFTWARE_SUBSCRIPTIONS":{"t2125_line":"8810 — Office expenses / 8871 — Computer","deductibility": 1.0, "cra_note": "SaaS and software subscriptions for business use."},
    "MEDICAL_SUPPLIES":     {"t2125_line": "8811 — Supplies (profession-specific)",  "deductibility": 1.0,  "cra_note": "Professional supplies (chiro: linens, oils, equipment)."},
    "CONTINUING_EDUCATION": {"t2125_line": "8560 — Training / 9270 — Other",        "deductibility": 1.0,  "cra_note": "Courses to maintain/upgrade professional skills."},
    "PAYROLL":              {"t2125_line": "9060 — Salaries and wages",              "deductibility": 1.0,  "cra_note": "Wages paid to arm's-length employees. T4 required."},
    "UTILITIES":            {"t2125_line": "9270 — Telephone and utilities",         "deductibility": 1.0,  "cra_note": "Hydro, gas, water for business premises."},
    "UNCATEGORIZED":        {"t2125_line": "— REVIEW REQUIRED —",                   "deductibility": 0.0,  "cra_note": "Could not be categorized. Manual review required."},
}

KEYWORD_RULES: List[Tuple[str, str]] = [
    (r"\b(payroll|adp|ceridian|humi|direct\s*deposit|wage|salary)\b",                            "PAYROLL"),
    (r"\b(rent|lease|landlord|property\s*mgmt|realty)\b",                                        "RENT"),
    (r"\b(intact|aviva|manulife|sunlife|desjardins|insurance|insur|premium|coverage)\b",         "INSURANCE"),
    (r"\b(cpa|accountant|lawyer|legal|notary|bookkeep|consultant|advisory)\b",                   "PROFESSIONAL_FEES"),
    (r"\b(microsoft|google\s*workspace|adobe|intuit|quickbooks|xero|freshbooks|"
     r"dropbox|slack|zoom|aws|azure|shopify|jane\s*app|janeapp|saas|subscription)\b",            "SOFTWARE_SUBSCRIPTIONS"),
    (r"\b(rogers|bell|telus|shaw|videotron|koodo|fido|virgin\s*mobile|"
     r"internet|mobile|wireless|cell\s*phone|phone\s*plan|telecom)\b",                           "TELEPHONE_INTERNET"),
    (r"\b(hydro|enbridge|atco|fortis|bc\s*hydro|ontario\s*hydro|electricity|"
     r"natural\s*gas|water\s*bill|utility|utilities)\b",                                          "UTILITIES"),
    (r"\b(medichair|health\s*craft|chiro\s*supply|linens|treatment\s*table|"
     r"medical\s*supply|clinic\s*supply|rehab\s*supply|acupuncture)\b",                          "MEDICAL_SUPPLIES"),
    (r"\b(seminar|conference|course|cce|webinar|continuing\s*ed|professional\s*dev|"
     r"cmcc|chiropractic\s*assoc|registration\s*fee|udemy|coursera|linkedin\s*learning)\b",      "CONTINUING_EDUCATION"),
    (r"\b(facebook\s*ads|google\s*ads|meta\s*ads|instagram|marketing|advertis|"
     r"flyer|brochure|signage|seo|mailchimp|yelp)\b",                                            "ADVERTISING"),
    (r"\b(restaurant|cafe|coffee|starbucks|tim\s*hortons|second\s*cup|"
     r"doordash|uber\s*eats|skip|grubhub|dining|lunch|dinner|breakfast|catering|bar|pub)\b",     "MEALS_ENTERTAINMENT"),
    (r"\b(petro\s*canada|shell|esso|husky|pioneer|gas\s*station|fuel|"
     r"parking|autopark|impark|green\s*p|car\s*wash|jiffy\s*lube|midas|"
     r"canadian\s*tire|mto|vehicle|auto)\b",                                                      "MOTOR_VEHICLE"),
    (r"\b(staples|bureau\s*en\s*gros|grand\s*&\s*toy|office\s*depot|"
     r"paper|toner|ink|printer|binder|stationery|pens|folders)\b",                               "OFFICE_SUPPLIES"),
    (r"\b(service\s*charge|bank\s*fee|nsf|wire\s*fee|interac\s*fee|"
     r"monthly\s*fee|account\s*fee|transaction\s*fee|interest\s*charged|overdraft)\b",           "BANK_CHARGES"),
]


def categorize(description: str) -> str:
    """Match description against keyword rules; return category key."""
    for pattern, category in KEYWORD_RULES:
        if re.search(pattern, description, re.IGNORECASE):
            return category
    return "UNCATEGORIZED"


# ---------------------------------------------------------------------------
# SECTION 2: FILE INPUT WITH RETRY LOGIC
# ---------------------------------------------------------------------------

EXPECTED_COLUMNS = {"Date", "Description", "Debit", "Credit", "Balance"}

def prompt_for_file(max_attempts: int = 3) -> str:
    """
    Prompt for a bank statement CSV file path.
    Re-prompts up to max_attempts times on failure.
    """
    print("\n" + "=" * 60)
    print("  CRA EXPENSE CATEGORIZER")
    print("=" * 60)
    print("\nTest fixture: bank_statement.csv")
    print("Expected columns: Date, Description, Debit, Credit, Balance")

    for attempt in range(1, max_attempts + 1):
        raw = input("\nBank statement CSV file path: ").strip()
        path = Path(raw)

        if not path.exists():
            print(f"  ERROR: File not found: '{raw}'")
        elif path.suffix.lower() != ".csv":
            print(f"  ERROR: Expected .csv file, got '{path.suffix}'")
        else:
            try:
                with open(path, newline="", encoding="utf-8-sig") as f:
                    headers = set(csv.DictReader(f).fieldnames or [])
                    missing = EXPECTED_COLUMNS - headers
                    if missing:
                        print(f"  ERROR: Missing columns: "
                              f"{', '.join(sorted(missing))}")
                        print(f"  Expected: {', '.join(sorted(EXPECTED_COLUMNS))}")
                    else:
                        return str(path)
            except Exception as e:
                print(f"  ERROR: Could not read file: {e}")

        if attempt < max_attempts:
            print(f"  Attempt {attempt}/{max_attempts}. Please try again.")

    print(f"\n  FATAL: Maximum attempts ({max_attempts}) reached. Exiting.")
    sys.exit(1)


def prompt_for_output(default: str = "categorized_expenses_cra.csv") -> str:
    raw = input(f"\nOutput CSV filename [{default}]: ").strip()
    return raw if raw else default


# ---------------------------------------------------------------------------
# SECTION 3: LOAD & PROCESS
# ---------------------------------------------------------------------------

def load_transactions(filepath: str) -> List[Dict]:
    """Parse bank CSV into expense transaction list (debits only)."""
    transactions = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            debit  = float(row.get("Debit",  0) or 0)
            credit = float(row.get("Credit", 0) or 0)
            amount = debit + credit
            if amount >= 0:
                continue  # Skip income/credits
            transactions.append({
                "date":        row["Date"].strip(),
                "description": row["Description"].strip(),
                "amount":      abs(amount),
            })
    return transactions


def generate_report(transactions: List[Dict]) -> List[Dict]:
    """Categorize transactions and return enriched list."""
    categorized = []
    for txn in transactions:
        cat      = categorize(txn["description"])
        cat_info = CRA_CATEGORIES[cat]
        categorized.append({
            **txn,
            "category":          cat,
            "t2125_line":        cat_info["t2125_line"],
            "deductibility_pct": cat_info["deductibility"] * 100,
            "deductible_amount": round(txn["amount"] * cat_info["deductibility"], 2),
        })
    return categorized


def print_report(categorized: List[Dict]) -> None:
    """Print CRA-aligned expense summary."""
    summary = defaultdict(lambda: {"total": 0.0, "deductible": 0.0, "count": 0})
    for txn in categorized:
        cat = txn["category"]
        summary[cat]["total"]      += txn["amount"]
        summary[cat]["deductible"] += txn["deductible_amount"]
        summary[cat]["count"]      += 1

    div = "=" * 78
    print(f"\n{div}")
    print("  CRA EXPENSE CATEGORIZATION REPORT — T2125 MAPPING")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(div)

    print(f"\n  TRANSACTION DETAIL")
    print("  " + "-" * 74)
    print(f"  {'Date':<12} {'Description':<30} {'Amount':>10} "
          f"{'Category':<22} {'Deductible':>10}")
    print("  " + "-" * 74)
    for txn in categorized:
        flag = " ⚠" if txn["category"] == "UNCATEGORIZED" else ""
        print(f"  {txn['date']:<12} {txn['description'][:29]:<30} "
              f"${txn['amount']:>9,.2f} {txn['category'][:21]:<22} "
              f"${txn['deductible_amount']:>9,.2f}{flag}")

    print(f"\n\n  SUMMARY BY CRA CATEGORY")
    print("  " + "-" * 74)
    print(f"  {'Category':<24} {'T2125 Line':<33} "
          f"{'Total':>10} {'Deductible':>10} {'Ded%':>6}")
    print("  " + "-" * 74)
    grand_total = grand_ded = 0.0
    for cat, data in sorted(summary.items(), key=lambda x: -x[1]["deductible"]):
        line  = CRA_CATEGORIES[cat]["t2125_line"][:32]
        ded   = CRA_CATEGORIES[cat]["deductibility"] * 100
        print(f"  {cat[:23]:<24} {line:<33} "
              f"${data['total']:>9,.2f} ${data['deductible']:>9,.2f} "
              f"{ded:>5.0f}%")
        grand_total += data["total"]
        grand_ded   += data["deductible"]
    print("  " + "-" * 74)
    print(f"  {'TOTAL':<59} ${grand_total:>9,.2f} ${grand_ded:>9,.2f}")

    uncategorized = [t for t in categorized if t["category"] == "UNCATEGORIZED"]
    if uncategorized:
        print(f"\n\n  ⚠  ITEMS REQUIRING MANUAL REVIEW ({len(uncategorized)})")
        print("  " + "-" * 50)
        for txn in uncategorized:
            print(f"  {txn['date']}  {txn['description']:<35}  "
                  f"${txn['amount']:>9,.2f}")

    print(f"\n{div}")
    print("  DISCLAIMER: Categorization tool only. Consult a CPA for T2125 filing.")
    print(div)


def export_csv(categorized: List[Dict], filepath: str) -> None:
    """Export categorized transactions to CSV."""
    if not categorized:
        return
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=categorized[0].keys())
        writer.writeheader()
        writer.writerows(categorized)
    print(f"\n  ✔ Export saved to: {filepath}")


# ---------------------------------------------------------------------------
# SECTION 4: MAIN
# ---------------------------------------------------------------------------

def main():
    input_path  = prompt_for_file()
    output_path = prompt_for_output()

    print(f"\nLoading transactions from: {input_path}")
    transactions = load_transactions(input_path)
    print(f"Processing {len(transactions)} expense transactions...")

    categorized = generate_report(transactions)
    print_report(categorized)
    export_csv(categorized, output_path)


if __name__ == "__main__":
    main()

# cra-expense-categorizer

**Automated bank statement expense categorization mapped to CRA T2125 (Statement of Business or Professional Activities).**

Built to reflect bookkeeping automation work for a Canadian sole proprietor healthcare practice. Ingests any Canadian bank CSV export, categorizes transactions using a regex keyword engine against 14 CRA expense categories, applies the 50% meals & entertainment rule (ITA s.67.1), and flags uncategorized items for CPA review.

[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE) [![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org) [![Tests: pytest](https://img.shields.io/badge/Tests-pytest-green.svg)](tests/) [![100% Local](https://img.shields.io/badge/Data%20Privacy-100%25%20Local-brightgreen.svg)](#data-privacy)

---

## Live Demo
Open `src/index.html` — drop `fixtures/bank_statement.csv` to see categorization with deductibility breakdown.

---

## Features

| Feature | Detail |
|---|---|
| 14 CRA categories | Mapped to T2125 line numbers |
| ITA s.67.1 | 50% meals & entertainment cap applied automatically |
| Canadian vendors | Rogers, Bell, Telus, Petro-Canada, Hydro One, JaneApp, Medichair, and more |
| Uncategorized flagging | Items requiring manual CPA review clearly separated |
| Filter + search | Web app allows filtering by category and keyword search |
| CSV export | Categorized transaction file for working paper documentation |

---

## Repository Structure

```
cra-expense-categorizer/
├── src/
│   ├── index.html              # Browser web app (drag & drop)
│   └── expense_categorizer.py  # Python CLI with file prompts
├── tests/
│   └── test_expense_categorizer.py  # pytest suite — categories, deductibility, CSV
├── fixtures/
│   └── bank_statement.csv      # 50 realistic Canadian transactions (Jan–Feb 2025)
├── requirements.txt
├── .gitignore
└── LICENSE
```

---

## Quick Start

**Web app:** `open src/index.html` → drop `fixtures/bank_statement.csv`.

**CLI:**
```bash
git clone https://github.com/wongcpa/cra-expense-categorizer.git
cd cra-expense-categorizer
python src/expense_categorizer.py
# Enter: fixtures/bank_statement.csv
```

**Tests:** `pip install pytest && pytest tests/ -v`

---

## CRA T2125 Categories

| Category | T2125 Line | Deductibility |
|---|---|---|
| Advertising | 8520 | 100% |
| Meals & Entertainment | 8523 | 50% (ITA s.67.1) |
| Motor Vehicle | 9281 | Business-use % |
| Office Supplies | 8810 | 100% |
| Rent | 8910 | 100% |
| Telephone & Internet | 9270 | Business-use % |
| Insurance | 8690 | 100% |
| Professional Fees | 8860 | 100% |
| Bank Charges | 8710 | 100% |
| Software/SaaS | 8810/8871 | 100% |
| Medical Supplies | 8811 | 100% |
| Continuing Education | 8560 | 100% |
| Payroll | 9060 | 100% |
| Utilities | 9270 | 100% |

---

## Input CSV Format

Standard Canadian bank export: `Date` · `Description` · `Debit` · `Credit` · `Balance`

Works with RBC, TD, BMO, Scotiabank, CIBC, and most major Canadian bank CSV exports.

---

## Data Privacy
All processing is local. Bank data never leaves your machine.

---

## Author

**Jimmy Wong, CPA (WA), CPA (Canada)**
[www.wong.cpa](https://www.wong.cpa) · [LinkedIn](https://www.linkedin.com/in/wongjimmy/) · [GitHub @wongcpa](https://github.com/wongcpa)

*Categorization assistance only. Consult a CPA for T2125/T2 filing. CRA audit requires original receipts.*

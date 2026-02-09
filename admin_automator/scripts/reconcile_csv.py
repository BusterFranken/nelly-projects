#!/usr/bin/env python3
"""reconcile_csv.py

Monthly reconciliation helper.

Inputs:
- Bank statement CSV exported by Buster (format may vary by bank).
- Ledger sheet exported as CSV or fetched via gog sheets get.

Outputs:
- JSON report with:
  - parsed bank transactions (date, description, amount, currency)
  - ledger entries (invoice_date/vendor/total)
  - unmatched transactions (suggested missing invoice tasks)

This is intentionally tolerant: it tries to infer columns by header names and common patterns.
If it cannot parse, it should fail with a clear error listing the headers found.

Usage:
  python3 reconcile_csv.py --bank bank.csv --out report.json

"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def parse_date(s: str) -> Optional[str]:
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return None


def parse_amount(s: str) -> Optional[float]:
    s = (s or "").strip()
    if not s:
        return None
    s = s.replace("€", "").replace(" ", "")
    # Handle 1.234,56 and 1234.56
    if s.count(",") == 1 and s.count(".") >= 1:
        # assume dot thousands, comma decimal
        s = s.replace(".", "").replace(",", ".")
    elif s.count(",") == 1 and s.count(".") == 0:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def infer_columns(headers: list[str]) -> dict:
    h = [norm(x) for x in headers]

    def pick(candidates: list[str]) -> Optional[int]:
        for cand in candidates:
            for i, hh in enumerate(h):
                if cand in hh:
                    return i
        return None

    col_date = pick(["date", "datum", "booking date", "transaction date", "waarde", "valuta datum"])
    col_desc = pick(["description", "omschrijving", "memo", "name", "tegenpartij", "counterparty", "payment"])
    col_amount = pick(["amount", "bedrag", "debit", "credit", "amount (eur)", "af", "bij"])
    col_currency = pick(["currency", "valuta"])

    if col_date is None or col_desc is None or col_amount is None:
        raise ValueError(
            "Could not infer required columns (date/description/amount). "
            f"Headers found: {headers}"
        )

    return {
        "date": col_date,
        "description": col_desc,
        "amount": col_amount,
        "currency": col_currency,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    bank_path = Path(args.bank)
    rows_out = []

    with bank_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = next(reader)
        cols = infer_columns(headers)

        for r in reader:
            if not r or all(not (x or "").strip() for x in r):
                continue
            d = parse_date(r[cols["date"]] if cols["date"] < len(r) else "")
            desc = (r[cols["description"]] if cols["description"] < len(r) else "").strip()
            amt = parse_amount(r[cols["amount"]] if cols["amount"] < len(r) else "")
            cur = (r[cols["currency"]] if cols["currency"] is not None and cols["currency"] < len(r) else "").strip() or None

            rows_out.append({
                "date": d,
                "description": desc,
                "amount": amt,
                "currency": cur,
                "raw": r,
            })

    report = {
        "ok": True,
        "bank": {
            "path": str(bank_path),
            "count": len(rows_out),
            "transactions": rows_out,
        },
        "note": "This script only parses the CSV. Matching against the ledger is performed by the agent using heuristics.",
    }

    Path(args.out).write_text(json.dumps(report, indent=2))
    print(json.dumps({"ok": True, "count": len(rows_out), "out": args.out}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

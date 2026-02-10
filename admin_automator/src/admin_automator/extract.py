from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable

import pdfplumber
from dateutil import parser as dtparser


@dataclass
class ExtractedFields:
    invoice_date: str | None = None
    vendor: str | None = None
    total: str | None = None
    vat_amount: str | None = None
    company_numbers: list[str] | None = None
    vat_numbers: list[str] | None = None


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extract_text_from_pdf(path: str, max_pages: int = 3) -> str:
    out: list[str] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages[:max_pages]):
            out.append(page.extract_text() or "")
    return "\n".join(out)


_VAT_RE = re.compile(r"\b([A-Z]{2}\s?\d{8,12}|VAT\s?No\.?\s*[:#]?\s*[A-Z0-9\- ]{6,})\b", re.I)
_COMPANY_RE = re.compile(
    r"\b(Chamber\s+of\s+Commerce\s*(?:No\.?|Number)?\s*[:#]?\s*\d{6,10}|KvK\s*[:#]?\s*\d{6,10}|Company\s+No\.?\s*[:#]?\s*\d{6,10})\b",
    re.I,
)

_DATE_HINT_RE = re.compile(r"\b(invoice\s+date|date\s+of\s+issue|date)\b", re.I)
_DATE_VALUE_RE = re.compile(r"\b(\d{4}[\-/]\d{1,2}[\-/]\d{1,2}|\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b")

_MONEY_RE = re.compile(r"(?:(?:EUR|€)\s*)?([0-9]{1,3}(?:[\.,][0-9]{3})*(?:[\.,][0-9]{2}))")


def _parse_decimal(amount: str) -> Decimal | None:
    a = amount.strip()
    # Convert European comma decimals into dot.
    if a.count(",") == 1 and a.count(".") >= 1:
        # assume dots are thousand separators, comma decimal
        a = a.replace(".", "").replace(",", ".")
    elif a.count(",") == 1 and a.count(".") == 0:
        a = a.replace(",", ".")

    a = re.sub(r"[^0-9\.]", "", a)
    try:
        return Decimal(a)
    except InvalidOperation:
        return None


def _pick_invoice_date(text: str) -> str | None:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # Prefer lines that mention invoice date
    for line in lines:
        if _DATE_HINT_RE.search(line):
            m = _DATE_VALUE_RE.search(line)
            if m:
                try:
                    s = m.group(1)
                    dayfirst = False if re.match(r"^\d{4}[\-/]", s) else True
                    d = dtparser.parse(s, dayfirst=dayfirst).date()
                    return d.isoformat()
                except Exception:
                    pass
    # fallback: first parseable date
    for m in _DATE_VALUE_RE.finditer(text):
        try:
            s = m.group(1)
            dayfirst = False if re.match(r"^\d{4}[\-/]", s) else True
            d = dtparser.parse(s, dayfirst=dayfirst).date()
            return d.isoformat()
        except Exception:
            continue
    return None


def _pick_total(text: str) -> str | None:
    # Heuristic: look for "total" lines, else pick max monetary value
    candidates: list[Decimal] = []
    totals: list[Decimal] = []
    for line in text.splitlines():
        mm = _MONEY_RE.findall(line)
        if not mm:
            continue
        vals = [v for v in (_parse_decimal(x) for x in mm) if v is not None]
        if not vals:
            continue
        candidates.extend(vals)
        if re.search(r"\b(total\s+due|amount\s+due|grand\s+total|total)\b", line, re.I):
            totals.extend(vals)

    if totals:
        return str(max(totals))
    if candidates:
        return str(max(candidates))
    return None


def _pick_vat_amount(text: str) -> str | None:
    for line in text.splitlines():
        if re.search(r"\bvat\b|\btax\b", line, re.I):
            mm = _MONEY_RE.findall(line)
            vals = [v for v in (_parse_decimal(x) for x in mm) if v is not None]
            if vals:
                return str(max(vals))
    return None


def extract_fields_from_text(text: str, *, vendor_hint: str | None = None) -> ExtractedFields:
    text = text or ""
    cleaned = _norm_ws(text)

    vat_numbers = sorted({ _norm_ws(m.group(1)) for m in _VAT_RE.finditer(cleaned) })
    company_numbers = sorted({ _norm_ws(m.group(1)) for m in _COMPANY_RE.finditer(cleaned) })

    invoice_date = _pick_invoice_date(text)
    total = _pick_total(text)
    vat_amount = _pick_vat_amount(text)

    vendor = vendor_hint
    if not vendor:
        # naive: take first non-empty line
        for line in text.splitlines():
            line = line.strip()
            if line and len(line) <= 80:
                vendor = line
                break

    return ExtractedFields(
        invoice_date=invoice_date,
        vendor=vendor,
        total=total,
        vat_amount=vat_amount,
        company_numbers=company_numbers or None,
        vat_numbers=vat_numbers or None,
    )


def extract_fields_from_pdf(path: str, *, vendor_hint: str | None = None) -> ExtractedFields:
    text = extract_text_from_pdf(path)
    return extract_fields_from_text(text, vendor_hint=vendor_hint)

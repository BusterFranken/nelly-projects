# TA Admin 2026 - Ledger schema

The ledger is a Google Sheet. One row per archived attachment.

## Columns (header row)
- `received_at`: ISO timestamp when the email was processed
- `invoice_date`: date on invoice/receipt (ISO YYYY-MM-DD if possible)
- `vendor`: merchant / supplier name
- `description`: best-effort short description (what was purchased)
- `category`: restaurant | travel | software | supplies | other
- `is_restaurant`: true/false
- `currency`: EUR/USD/…
- `total_gross`: total paid incl. VAT (numeric)
- `vat_rate`: e.g. 9%, 21% (string)
- `vat_amount`: VAT/BTW amount (numeric)
- `net_amount`: excl VAT (numeric, if derivable)
- `status`: ready | incomplete | missing
- `comment`: free-text notes (what’s missing / context / reconciliation notes)
- `needs_correction`: true/false (legacy boolean; keep aligned with status)
- `missing_fields`: comma-separated missing items (e.g. company_name, vat_number, vat_amount)
- `source_message_id`: Gmail messageId
- `drive_file_url`: URL to the archived file in Drive

## Special case: invoices in email body (no attachment)
- Generate a PDF from the email body ("print to PDF") and archive that PDF.
- In the ledger, set `vendor` from the email sender/company name if needed, and set `description` to reflect that it was body-rendered.

## Categorization heuristics
- Restaurant: vendor appears like a restaurant name; receipt contains keywords like "restaurant", "café", "bar", "menu", "table", or NL receipts with horeca context.
- If uncertain, set category `other` and `is_restaurant=false` and flag for review.

## Validation heuristics (NL tax authority readiness)
For non-restaurant invoices, aim to have:
- company name present (Talos Holding B.V.)
- VAT number present (one of the two)
- total amount
- VAT amount or rate

If missing: set `needs_correction=true` and list missing fields. Also append an item to the ledger sheet TODOs tab.

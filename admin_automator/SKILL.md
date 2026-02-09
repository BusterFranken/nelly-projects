---
name: admin-automator
description: Automate admin/tax document handling: when Buster forwards emails with invoice/receipt attachments, download and archive them to the shared Drive folder 'TA Admin 2026_Nelly', extract key fields (vendor, date, total, VAT), append a row to the TA Admin Google Sheet ledger, and track missing/invalid invoices. Also supports monthly bank-statement reconciliation and creating Kanban tasks under the Admin project when anything is missing or blocked.
---

# Admin Automator (TA Admin 2026)

## Canonical locations (config)
- **Drive folder (archive):** `TA Admin 2026_Nelly` (folderId discovered at runtime)
- **Ledger sheet:** `TA Admin 2026 - Ledger` (spreadsheetId stored in `references/config.json`)

Company info to validate on non-restaurant invoices:
- Company name: **Talos Holding B.V.**
- VAT numbers: **NL0058490834** or **NL860102397B01**

## Intake rule (how Buster should send)
To avoid accidentally processing random attachments, only process emails that match ALL of:
- Gmail label: **`TA/Admin`**
- From address is allowlisted (Buster): `busterfranken@gmail.com` or `busterfranken@live.nl`

(If label is missing or sender is not allowlisted, do not process automatically; ask Buster on Signal.)

## Workflow: process new receipts/invoices
1) **Find candidate emails**
   - Use `gog gmail messages search` with a strict query, e.g.:
     - `newer_than:30d has:attachment (subject:"TA:" OR subject:"ADMIN:" OR label:"TA/Admin") -label:"TA/Admin/Processed"`

2) **Download attachments locally**
   - For each message:
     - Use `gog gmail get <messageId> --json` to find attachment IDs.
     - If attachments exist: download each with `gog gmail attachment <messageId> <attachmentId> --out <path>`.
     - If **no attachments** but the email body contains an invoice/receipt (e.g. HTML invoice):
       - Fetch decoded body (use `gog gmail messages search ... --include-body --json` or `gog gmail get <messageId> --full --json` if supported).
       - Render body to a PDF (“print to PDF”) using `textutil`:
         - write body to a temp file as HTML or plain text
         - `textutil -convert pdf -output /tmp/<name>.pdf /tmp/<name>.html` (or `.txt`)
       - Treat that generated PDF as the attachment for archiving + extraction.

3) **Archive to Drive**
   - Upload each attachment to `TA Admin 2026_Nelly` via `gog drive upload ... --parent <folderId>`.
   - Record the Drive file URL.

4) **Extract fields** (best-effort)
   - If PDF contains text: use `pdftotext` (if available) or `strings`/`textutil` fallback.
   - If image/scan: use the `image` tool to OCR/extract.

   Extract and normalize:
   - `invoice_date`
   - `vendor`
   - `description` (best guess)
   - `category` (best guess: restaurant | travel | software | supplies | other)
   - `is_restaurant` (boolean)
   - `currency`
   - `total_gross`
   - `vat_rate` and/or `vat_amount` (BTW)
   - `net_amount` (if derivable)

   Derive ledger state:
   - `status`:
     - `ready` if sufficient for bookkeeping
     - `incomplete` if invoice exists but missing required fields (non-restaurant)
     - `missing` if bank reconciliation indicates an invoice is missing
   - `comment`: short explanation / next action

   Validation rules:
   - If **NOT restaurant**: check whether the invoice contains **Talos Holding B.V.** AND one of the VAT numbers.
     - If missing: set `status=incomplete`, set `needs_correction=true`, populate `missing_fields`, and set `comment`.
   - If VAT is missing but expected: set `status=incomplete` + explain in `comment`.

5) **Append to Google Sheet**
   - Append one row per attachment to the ledger sheet.
   - Columns are defined in the sheet header row.

6) **Mark processed**
   - Apply label `TA/Admin/Processed` to the thread/message so it won’t be reprocessed.

7) **If blocked / missing info**
   - Append an entry to the **TODOs tab** in the ledger Google Sheet (source of truth for quarterly batching).
   - Ping Buster on Signal with a short heads-up.
   - Create/append a Kanban task under the Admin project if:
     - an invoice is missing required fields,
     - OCR failed,
     - bank statement reconciliation reveals missing invoices.

## Monthly reconciliation
- Once per month, ask Buster (Signal) to send the month’s bank statement.
- Compare transactions to ledger entries (by date/amount/vendor fuzzy match).
- For unmatched transactions, add Kanban tasks under Admin: “Missing invoice for <vendor> <date> <amount>”.

## Bundled resources
- `references/config.json` — IDs for Drive folder + Sheet
- `references/ledger_schema.md` — column meanings + categorization heuristics
- `scripts/admin_scan.py` — scan Gmail + download/upload attachments; outputs JSON for extraction+sheet append


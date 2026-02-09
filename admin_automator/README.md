# Admin Automator (Talos Holding B.V.)

Python utilities + OpenClaw skill scaffolding for automating invoice/receipt admin.

## What it does (target)
- Find Gmail threads labeled `TA/Admin` from allowlisted sender(s)
- Download attachments (or render invoice-like email bodies to PDF)
- Upload to Drive folder `TA Admin 2026_Nelly`
- OCR locally (ocrmypdf + tesseract + poppler)
- Extract key fields and write them to the Google Sheet:
  - Spreadsheet: `TA Admin 2026 - Ledger`
  - Tabs: `Ledger`, `TODOs`
- Apply Gmail label `TA/Admin/Processed`

## Local dependencies
Install once:

```bash
brew install tesseract poppler ocrmypdf
```

## Configuration
See `admin_automator/references/config.json`.

## Status
This repo currently contains the skill + helper scripts that were first developed inside the OpenClaw workspace.
Next step is to harden into a single CLI that runs end-to-end.

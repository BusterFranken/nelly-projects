# Admin Automator

Processes Gmail messages labeled `TA/Admin` from allowlisted senders:

1. Downloads attachments (or renders the email body to PDF)
2. Runs OCR (via `ocrmypdf` + `tesseract` + `poppler`)
3. Uploads PDFs to Google Drive folder `TA Admin 2026_Nelly`
4. Extracts key invoice fields
5. Appends/updates a Google Sheet (`Ledger` + `TODOs` tabs)
6. Applies Gmail label `TA/Admin/Processed`

## Quickstart

### 1) Install system deps (macOS)

```bash
brew install tesseract poppler ocrmypdf
```

(Windows/Linux: install `tesseract-ocr`, `poppler-utils`, `ocrmypdf` via your package manager.)

### 2) Install Python package

From repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ./admin_automator
```

Optional HTML->PDF support:

```bash
pip install -e ./admin_automator[html]
```

### 3) Configure Google credentials

Create an OAuth Client ID (Desktop) in Google Cloud Console and download `credentials.json`.

Then run once:

```bash
admin-automator auth --credentials ./credentials.json
```

This creates a token file at `~/.config/admin-automator/token.json`.

### 4) Configure settings

Create `~/.config/admin-automator/config.yaml`:

```yaml
allowlisted_senders:
  - "billing@vendor.com"
  - "noreply@another.com"

gmail:
  label_inbox: "TA/Admin"
  label_processed: "TA/Admin/Processed"

drive:
  target_folder_name: "TA Admin 2026_Nelly"

sheets:
  spreadsheet_id: "<YOUR_SHEET_ID>"
  ledger_tab: "Ledger"
  todos_tab: "TODOs"

processing:
  dry_run: false
  max_messages: 25
```

### 5) Run

```bash
admin-automator run
```

To preview without modifying Gmail/Drive/Sheets:

```bash
admin-automator run --dry-run
```

## Notes

- This tool expects a `TA/Admin` Gmail label to already exist.
- If a message has no attachments, the email body is turned into a PDF.
- OCR output PDFs are uploaded; the local working directory defaults to `./.admin_automator_work`.

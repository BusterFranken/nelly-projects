from __future__ import annotations

import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path

from googleapiclient.discovery import build

from . import __version__
from .config import Settings
from .drive_client import get_or_create_folder, upload_pdf
from .extract import extract_fields_from_pdf
from .gmail_client import (
    get_message_body_text,
    get_message_full,
    get_or_create_label,
    iter_attachments,
    message_from_address,
    message_subject,
    modify_labels,
    save_attachment,
)
from .ocr import ocr_pdf
from .pdf_render import render_email_to_pdf


GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


@dataclass
class ProcessResult:
    message_id: str
    processed: bool
    reason: str | None = None


def _safe_filename(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:180] if len(name) > 180 else name


def run_once(*, settings: Settings, creds, dry_run: bool | None = None) -> list[ProcessResult]:
    dry = settings.processing.dry_run if dry_run is None else dry_run

    gmail = build("gmail", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds) if settings.sheets else None

    user_id = "me"
    label_inbox_id = get_or_create_label(gmail, user_id=user_id, label_name=settings.gmail.label_inbox)
    label_processed_id = get_or_create_label(
        gmail, user_id=user_id, label_name=settings.gmail.label_processed
    )

    folder_id = get_or_create_folder(drive, folder_name=settings.drive.target_folder_name)

    # Fetch messages labeled TA/Admin but NOT already processed
    msg_refs = gmail.users().messages().list(
        userId=user_id,
        labelIds=[label_inbox_id],
        maxResults=settings.processing.max_messages,
        q=f"-label:{settings.gmail.label_processed}",
    ).execute()

    results: list[ProcessResult] = []

    for m in msg_refs.get("messages", []) or []:
        msg_id = m["id"]
        full = get_message_full(gmail, user_id=user_id, message_id=msg_id)
        sender = message_from_address(full)
        subj = message_subject(full) or "(no subject)"

        if settings.allowlisted_senders and (sender not in [s.lower() for s in settings.allowlisted_senders]):
            results.append(ProcessResult(message_id=msg_id, processed=False, reason="sender not allowlisted"))
            continue

        workdir = Path(settings.processing.workdir)
        workdir.mkdir(parents=True, exist_ok=True)
        msg_dir = workdir / msg_id
        msg_dir.mkdir(parents=True, exist_ok=True)

        pdfs: list[Path] = []
        for att in iter_attachments(gmail, user_id=user_id, message_full=full):
            fn = _safe_filename(att.filename or "attachment")
            p = msg_dir / fn
            save_attachment(att, p)

            # If attachment is already PDF keep, else attempt to convert? (not implemented)
            mime, _ = mimetypes.guess_type(p.name)
            if (att.mime_type == "application/pdf") or (mime == "application/pdf"):
                pdfs.append(p)

        if not pdfs:
            body = get_message_body_text(full)
            rendered = msg_dir / f"{_safe_filename(subj)}.pdf"
            render_email_to_pdf(body=body, out_path=rendered, subject=subj)
            pdfs.append(rendered)

        for pdf in pdfs:
            ocr_out = msg_dir / (pdf.stem + ".ocr.pdf")
            try:
                ocr_pdf(in_path=pdf, out_path=ocr_out)
                final_pdf = ocr_out
            except Exception:
                final_pdf = pdf

            upload_name = _safe_filename(final_pdf.name)

            if dry:
                drive_meta = {"id": "DRY_RUN", "webViewLink": None, "name": upload_name}
            else:
                drive_meta = upload_pdf(
                    drive,
                    path=str(final_pdf),
                    folder_id=folder_id,
                    filename=upload_name,
                )

            fields = extract_fields_from_pdf(str(final_pdf), vendor_hint=sender)

            if sheets and settings.sheets:
                missing = [k for k in ["invoice_date", "vendor", "total"] if not getattr(fields, k)]
                if missing:
                    if not dry:
                        from .sheets_client import upsert_todo

                        upsert_todo(
                            sheets,
                            spreadsheet_id=settings.sheets.spreadsheet_id,
                            tab_name=settings.sheets.todos_tab,
                            message_id=msg_id,
                            summary=f"Missing fields: {', '.join(missing)}",
                            details=f"Subject: {subj}\nSender: {sender}\nDrive: {drive_meta.get('webViewLink')}",
                        )
                else:
                    if not dry:
                        from .sheets_client import append_row

                        append_row(
                            sheets,
                            spreadsheet_id=settings.sheets.spreadsheet_id,
                            tab_name=settings.sheets.ledger_tab,
                            values=[
                                fields.invoice_date,
                                fields.vendor,
                                fields.total,
                                fields.vat_amount,
                                "; ".join(fields.vat_numbers or []),
                                "; ".join(fields.company_numbers or []),
                                drive_meta.get("webViewLink"),
                                msg_id,
                                subj,
                                sender,
                                __version__,
                            ],
                        )

        if not dry:
            modify_labels(
                gmail,
                user_id=user_id,
                message_id=msg_id,
                add_label_ids=[label_processed_id],
            )

        results.append(ProcessResult(message_id=msg_id, processed=True, reason=None))

    return results

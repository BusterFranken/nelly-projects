from __future__ import annotations

import base64
from dataclasses import dataclass
from email.utils import parseaddr
from pathlib import Path
from typing import Iterable, Optional

from googleapiclient.discovery import Resource


@dataclass(frozen=True)
class GmailMessageRef:
    id: str
    thread_id: str | None = None


@dataclass(frozen=True)
class GmailAttachment:
    filename: str
    mime_type: str
    data: bytes


def _header(headers: list[dict], name: str) -> str | None:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value")
    return None


def get_or_create_label(service: Resource, *, user_id: str, label_name: str) -> str:
    res = service.users().labels().list(userId=user_id).execute()
    for lbl in res.get("labels", []):
        if lbl.get("name") == label_name:
            return lbl["id"]

    created = (
        service.users()
        .labels()
        .create(
            userId=user_id,
            body={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        .execute()
    )
    return created["id"]


def list_messages_with_label(
    service: Resource,
    *,
    user_id: str,
    label_id: str,
    max_results: int = 50,
) -> list[GmailMessageRef]:
    out: list[GmailMessageRef] = []
    req = service.users().messages().list(userId=user_id, labelIds=[label_id], maxResults=max_results)
    while req is not None and len(out) < max_results:
        res = req.execute()
        for m in res.get("messages", []):
            out.append(GmailMessageRef(id=m["id"], thread_id=m.get("threadId")))
            if len(out) >= max_results:
                break
        req = service.users().messages().list_next(previous_request=req, previous_response=res)
    return out


def get_message_full(service: Resource, *, user_id: str, message_id: str) -> dict:
    return (
        service.users()
        .messages()
        .get(userId=user_id, id=message_id, format="full")
        .execute()
    )


def message_from_address(message_full: dict) -> str | None:
    headers = message_full.get("payload", {}).get("headers", [])
    raw_from = _header(headers, "From")
    if not raw_from:
        return None
    _, addr = parseaddr(raw_from)
    return addr.lower() if addr else None


def message_subject(message_full: dict) -> str | None:
    headers = message_full.get("payload", {}).get("headers", [])
    return _header(headers, "Subject")


def _walk_parts(payload: dict) -> Iterable[dict]:
    stack = [payload]
    while stack:
        part = stack.pop()
        yield part
        for sub in part.get("parts", []) or []:
            stack.append(sub)


def iter_attachments(service: Resource, *, user_id: str, message_full: dict) -> Iterable[GmailAttachment]:
    payload = message_full.get("payload") or {}
    for part in _walk_parts(payload):
        filename = part.get("filename")
        body = part.get("body") or {}
        att_id = body.get("attachmentId")
        mime_type = part.get("mimeType")

        if filename and att_id:
            att = (
                service.users()
                .messages()
                .attachments()
                .get(userId=user_id, messageId=message_full["id"], id=att_id)
                .execute()
            )
            data = base64.urlsafe_b64decode(att["data"].encode("utf-8"))
            yield GmailAttachment(filename=filename, mime_type=mime_type, data=data)


def get_message_body_text(message_full: dict) -> str:
    """Best-effort plain text extraction from the message payload."""
    payload = message_full.get("payload") or {}

    # Prefer text/plain parts
    plain: list[str] = []
    html: list[str] = []

    for part in _walk_parts(payload):
        mime = (part.get("mimeType") or "").lower()
        body = part.get("body") or {}
        data = body.get("data")
        if not data:
            continue
        decoded = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")
        if mime == "text/plain":
            plain.append(decoded)
        elif mime == "text/html":
            html.append(decoded)

    if plain:
        return "\n\n".join(plain).strip()
    if html:
        # Return HTML as-is; caller can render
        return "\n\n".join(html).strip()

    snippet = message_full.get("snippet")
    return snippet or ""


def is_html_body(text: str) -> bool:
    t = text.lstrip().lower()
    return t.startswith("<!doctype html") or t.startswith("<html") or ("<body" in t and "</" in t)


def save_attachment(att: GmailAttachment, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(att.data)
    return path


def modify_labels(
    service: Resource,
    *,
    user_id: str,
    message_id: str,
    add_label_ids: list[str] | None = None,
    remove_label_ids: list[str] | None = None,
) -> None:
    body = {
        "addLabelIds": add_label_ids or [],
        "removeLabelIds": remove_label_ids or [],
    }
    service.users().messages().modify(userId=user_id, id=message_id, body=body).execute()

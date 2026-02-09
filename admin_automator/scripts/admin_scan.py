#!/usr/bin/env python3
"""admin_scan.py

Scan Gmail for TA/Admin intake messages, download attachments, upload to Drive archive,
then output a JSON manifest for downstream extraction + ledger append.

This script intentionally does NOT do OCR itself. OCR/extraction is handled by the agent
(using either local PDF text tools or the image tool), then the ledger is appended.

Usage:
  python3 admin_scan.py --since-days 30 --out manifest.json

Requires:
  - gog (authorized for gmail+drive)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def sh(cmd: list[str]) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr.strip()}")
    return p.stdout


def load_config(cfg_path: Path) -> dict:
    return json.loads(cfg_path.read_text())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "references" / "config.json"))
    ap.add_argument("--since-days", type=int, default=30)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workdir", default=str(Path.home() / ".openclaw" / "workspace" / ".admin_scan"))
    args = ap.parse_args()

    cfg = load_config(Path(args.config))
    account = cfg["account"]
    intake_label = cfg["gmailLabels"]["intake"]
    processed_label = cfg["gmailLabels"]["processed"]
    prefixes = cfg.get("intakeSubjectPrefixes", ["TA:", "ADMIN:"])

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    # Strict query: intake label OR subject prefix, must have attachment, not yet processed.
    subj_q = " OR ".join([f'subject:"{p}"' for p in prefixes])
    query = f"newer_than:{args.since_days}d has:attachment (label:\"{intake_label}\" OR ({subj_q})) -label:\"{processed_label}\""

    res = sh([
        "gog", "gmail", "messages", "search", query,
        "--account", account,
        "--json", "--max", "50",
    ])
    data = json.loads(res)
    msgs = data.get("messages") or []

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "account": account,
        "items": [],
    }

    # NOTE: We do not yet enumerate attachment IDs; gog doesn't provide a single "download all".
    # We capture message IDs; downstream agent can call gog gmail get + attachment.
    for m in msgs:
        mid = m.get("id") or m.get("messageId") or m
        if not mid:
            continue
        manifest["items"].append({
            "message_id": mid,
        })

    Path(args.out).write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"ok": True, "count": len(manifest["items"]), "out": args.out}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        raise

# NOTE (2026-02-09): Field extraction is implemented via local OCR pipeline:
# - ocrmypdf -m force --output-type pdf <in> <out>
# - pdftotext -layout <out> <txt>
# The agent parses the resulting text and fills the ledger.

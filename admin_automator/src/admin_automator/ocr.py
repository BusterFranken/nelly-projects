from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class OcrError(RuntimeError):
    pass


def ensure_ocr_dependencies() -> None:
    missing = [exe for exe in ["ocrmypdf", "tesseract"] if shutil.which(exe) is None]
    if missing:
        raise OcrError(
            "Missing OCR dependencies: "
            + ", ".join(missing)
            + ". Install with e.g. `brew install tesseract poppler ocrmypdf` (macOS)."
        )


def ocr_pdf(*, in_path: Path, out_path: Path, language: str = "eng") -> Path:
    ensure_ocr_dependencies()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # --skip-text means: if the PDF already has text, don't OCR it again.
    cmd = [
        "ocrmypdf",
        "--skip-text",
        "--force-ocr",
        "--output-type",
        "pdf",
        "-l",
        language,
        str(in_path),
        str(out_path),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise OcrError(f"ocrmypdf failed ({p.returncode}): {p.stderr.strip() or p.stdout.strip()}")
    return out_path

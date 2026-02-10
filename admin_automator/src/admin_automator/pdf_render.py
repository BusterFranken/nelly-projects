from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .gmail_client import is_html_body


def render_email_to_pdf(*, body: str, out_path: Path, subject: str | None = None) -> Path:
    """Render an email body to a PDF.

    - If optional dependency `weasyprint` is installed and body looks like HTML, render HTML.
    - Otherwise render as plain text using reportlab.
    """

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if is_html_body(body):
        try:
            from weasyprint import HTML  # type: ignore

            HTML(string=body, base_url=str(Path.cwd())).write_pdf(str(out_path))
            return out_path
        except Exception:
            # fall back to plain text
            pass

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4
    x = 40
    y = height - 40
    line_height = 14

    if subject:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, subject)
        y -= line_height * 2

    c.setFont("Helvetica", 10)
    for raw_line in body.splitlines() or [""]:
        line = raw_line.replace("\t", "    ")
        # naive wrapping
        while len(line) > 110:
            c.drawString(x, y, line[:110])
            line = line[110:]
            y -= line_height
            if y < 40:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - 40
        c.drawString(x, y, line)
        y -= line_height
        if y < 40:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - 40

    c.save()
    return out_path

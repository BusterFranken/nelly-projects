from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .config import load_settings
from .google_auth import DEFAULT_TOKEN_PATH, get_credentials
from .runner import DRIVE_SCOPES, GMAIL_SCOPES, SHEETS_SCOPES, run_once

app = typer.Typer(add_completion=False, help="Admin Automator")


@app.command()
def auth(
    credentials: Path = typer.Option(..., exists=True, help="Path to Google OAuth credentials.json"),
    token: Path = typer.Option(DEFAULT_TOKEN_PATH, help="Where to store token.json"),
):
    """Authenticate with Google and store a token file."""
    scopes = list({*GMAIL_SCOPES, *DRIVE_SCOPES, *SHEETS_SCOPES})
    get_credentials(scopes=scopes, credentials_path=credentials, token_path=token)
    typer.echo(f"Token saved to: {token}")


@app.command()
def run(
    config: Optional[Path] = typer.Option(None, help="Path to config.yaml"),
    credentials: Optional[Path] = typer.Option(None, help="Path to Google OAuth credentials.json (first run only)"),
    token: Path = typer.Option(DEFAULT_TOKEN_PATH, help="token.json path"),
    dry_run: bool = typer.Option(False, help="Don't modify Gmail/Drive/Sheets"),
):
    """Process labeled Gmail messages."""
    settings = load_settings(config)
    scopes = list({*GMAIL_SCOPES, *DRIVE_SCOPES, *SHEETS_SCOPES})
    creds = get_credentials(scopes=scopes, credentials_path=credentials, token_path=token)

    results = run_once(settings=settings, creds=creds, dry_run=dry_run)
    for r in results:
        status = "processed" if r.processed else "skipped"
        reason = f" ({r.reason})" if r.reason else ""
        typer.echo(f"{r.message_id}: {status}{reason}")


if __name__ == "__main__":
    app()

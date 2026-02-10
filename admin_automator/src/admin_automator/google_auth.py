from __future__ import annotations

from pathlib import Path
from typing import Sequence

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


DEFAULT_TOKEN_PATH = Path("~/.config/admin-automator/token.json").expanduser()


def get_credentials(
    *,
    scopes: Sequence[str],
    credentials_path: Path | None = None,
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> Credentials:
    token_path.parent.mkdir(parents=True, exist_ok=True)

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes=list(scopes))

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
        return creds

    if not credentials_path:
        raise FileNotFoundError(
            "No valid token found. Provide --credentials path to credentials.json to authenticate."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes=list(scopes))
    creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json())
    return creds

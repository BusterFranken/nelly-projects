from __future__ import annotations

from googleapiclient.discovery import Resource
from googleapiclient.http import MediaFileUpload


def find_folder_id_by_name(service: Resource, *, folder_name: str) -> str | None:
    q = (
        "mimeType='application/vnd.google-apps.folder' "
        "and trashed=false "
        f"and name='{folder_name.replace("'", "\\'")}'"
    )
    res = service.files().list(q=q, spaces="drive", fields="files(id,name)").execute()
    files = res.get("files", [])
    return files[0]["id"] if files else None


def create_folder(service: Resource, *, folder_name: str, parent_id: str | None = None) -> str:
    body: dict = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        body["parents"] = [parent_id]
    created = service.files().create(body=body, fields="id").execute()
    return created["id"]


def get_or_create_folder(service: Resource, *, folder_name: str) -> str:
    existing = find_folder_id_by_name(service, folder_name=folder_name)
    if existing:
        return existing
    return create_folder(service, folder_name=folder_name)


def upload_pdf(service: Resource, *, path: str, folder_id: str, filename: str) -> dict:
    media = MediaFileUpload(path, mimetype="application/pdf", resumable=True)
    body = {"name": filename, "parents": [folder_id]}
    created = service.files().create(body=body, media_body=media, fields="id,name,webViewLink").execute()
    return created

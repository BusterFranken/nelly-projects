from pathlib import Path

from admin_automator.config import load_settings


def test_load_settings_defaults_when_missing(tmp_path: Path):
    p = tmp_path / "missing.yaml"
    s = load_settings(p)
    assert s.gmail.label_inbox == "TA/Admin"


def test_load_settings_from_yaml(tmp_path: Path):
    p = tmp_path / "config.yaml"
    p.write_text(
        """
allowlisted_senders:
  - billing@example.com
sheets:
  spreadsheet_id: SHEET
""".lstrip()
    )
    s = load_settings(p)
    assert s.allowlisted_senders == ["billing@example.com"]
    assert s.sheets and s.sheets.spreadsheet_id == "SHEET"

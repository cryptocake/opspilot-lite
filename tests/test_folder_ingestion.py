from pathlib import Path

from sqlmodel import select

from app.ingestion.folder import ingest_folder
from app.models import AuditEvent, RequestItem


def test_ingest_folder_creates_request_and_skips_duplicates(tmp_path: Path, session):
    (tmp_path / "request.txt").write_text("Need Shopify automation", encoding="utf-8")
    first = ingest_folder(session, tmp_path)
    second = ingest_folder(session, tmp_path)
    assert len(first) == 1
    assert len(second) == 0
    assert session.exec(select(RequestItem)).one().body == "Need Shopify automation"
    assert session.exec(select(AuditEvent)).one().event_type == "request.ingested"

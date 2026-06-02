from pathlib import Path

from sqlmodel import Session, select

from app.audit import record_event
from app.models import RequestItem


def ingest_folder(session: Session, folder_path: str | Path) -> list[RequestItem]:
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Inbox folder does not exist: {folder}")
    ingested: list[RequestItem] = []
    for file_path in sorted(folder.glob("*.txt")):
        source_ref = str(file_path.resolve())
        existing = session.exec(select(RequestItem).where(RequestItem.source_ref == source_ref)).first()
        if existing:
            continue
        item = RequestItem(
            source_type="folder",
            source_ref=source_ref,
            subject=file_path.stem,
            body=file_path.read_text(encoding="utf-8").strip(),
        )
        session.add(item)
        session.flush()
        record_event(
            session,
            "request.ingested",
            f"Ingested {file_path.name}",
            request_id=item.id,
            metadata={"source_ref": source_ref},
        )
        ingested.append(item)
    session.commit()
    return ingested

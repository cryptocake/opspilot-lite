from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


def sqlite_database_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None
    raw_path = database_url.removeprefix("sqlite:///")
    if raw_path in {"", ":memory:"}:
        return None
    return Path(raw_path)


def get_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    sqlite_path = sqlite_database_path(url)
    if sqlite_path is not None:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = get_engine()


def init_db() -> None:
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

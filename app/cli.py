import argparse

from sqlmodel import Session

from app.ai.factory import get_llm_client
from app.config import get_settings
from app.db import engine, init_db, sqlite_database_path
from app.ingestion.folder import ingest_folder
from app.service import process_all_new_requests


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opspilot")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest", help="Ingest .txt requests from a folder")
    ingest.add_argument("folder")
    sub.add_parser("process", help="Process all new requests")
    reset = sub.add_parser("demo-reset", help="Remove local demo database")
    reset.add_argument("--yes", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    init_db()
    if args.command == "ingest":
        with Session(engine) as session:
            items = ingest_folder(session, args.folder)
            print(f"ingested={len(items)}")
        return 0
    if args.command == "process":
        with Session(engine) as session:
            processed = process_all_new_requests(session, get_llm_client())
            print(f"processed={len(processed)}")
        return 0
    if args.command == "demo-reset":
        if not args.yes:
            print("Refusing to reset without --yes")
            return 2
        db_path = sqlite_database_path(get_settings().database_url)
        if db_path is None:
            print("Refusing to reset a non-file SQLite database")
            return 2
        db_path.unlink(missing_ok=True)
        print(f"reset={db_path}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

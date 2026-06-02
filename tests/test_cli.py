from app.cli import build_parser, main


def test_cli_parser_accepts_ingest():
    args = build_parser().parse_args(["ingest", "examples/inbox"])
    assert args.command == "ingest"


def test_demo_reset_requires_yes(capsys):
    assert main(["demo-reset"]) == 2
    assert "Refusing" in capsys.readouterr().out

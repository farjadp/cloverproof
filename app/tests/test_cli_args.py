import pytest

from cloverproof_app import cli


def test_password_is_never_an_argument() -> None:
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "user-create",
                "--email",
                "a@b.org",
                "--org",
                "o",
                "--role",
                "staff",
                "--password",
                "x",
            ]
        )


def test_missing_database_url_is_explicit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    code = cli.main(["user-create", "--email", "a@b.org", "--org", "o", "--role", "staff"])
    assert code == 2 and "DATABASE_URL" in capsys.readouterr().err

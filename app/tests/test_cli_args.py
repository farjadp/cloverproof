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


def test_platform_role_arguments() -> None:
    parser = cli.build_parser()
    base = ["user-create", "--email", "a@b.org", "--org", "o", "--role", "staff"]
    assert parser.parse_args(base).platform_role is None
    assert parser.parse_args([*base, "--platform-role", "superadmin"]).platform_role == (
        "superadmin"
    )
    with pytest.raises(SystemExit):
        parser.parse_args([*base, "--platform-role", "staff"])
    set_role = ["user-set-platform-role", "--email", "a@b.org", "--platform-role"]
    assert parser.parse_args([*set_role, "superadmin"]).platform_role == "superadmin"
    assert parser.parse_args([*set_role, "none"]).platform_role == "none"

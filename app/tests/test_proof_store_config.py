"""PROOF_STORE selection: filesystem by default, s3 only with every BUCKET_* variable."""

from __future__ import annotations

import pytest

from cloverproof_app.config import BUCKET_VARS, ConfigError, Settings
from cloverproof_app.proof_web import store_for
from cloverproof_app.storage import FilesystemProofStore
from cloverproof_app.storage.s3 import S3ProofStore

BASE = {"DATABASE_URL": "postgresql://u@localhost/db", "SESSION_SECRET": "s" * 40}
BUCKET = {
    "BUCKET_ENDPOINT": "https://bucket.example.test",
    "BUCKET_NAME": "proofs",
    "BUCKET_REGION": "auto",
    "BUCKET_ACCESS_KEY_ID": "test-key-id",
    "BUCKET_SECRET_ACCESS_KEY": "test-secret-do-not-print",
}


def test_filesystem_is_the_default() -> None:
    settings = Settings.from_env(BASE)
    assert settings.proof_store == "filesystem"
    assert isinstance(store_for(settings), FilesystemProofStore)


def test_s3_with_all_bucket_vars() -> None:
    settings = Settings.from_env({**BASE, "PROOF_STORE": "S3", **BUCKET})
    assert settings.proof_store == "s3"
    store = store_for(settings)
    assert isinstance(store, S3ProofStore)
    assert store.bucket == "proofs"


@pytest.mark.parametrize("missing", sorted(BUCKET_VARS))
def test_s3_refused_without_every_bucket_var(missing: str) -> None:
    env = {**BASE, "PROOF_STORE": "s3", **BUCKET}
    del env[missing]
    with pytest.raises(ConfigError, match=missing):
        Settings.from_env(env)


def test_unknown_store_refused() -> None:
    with pytest.raises(ConfigError, match="PROOF_STORE"):
        Settings.from_env({**BASE, "PROOF_STORE": "railway"})


def test_endpoint_must_be_https_outside_development() -> None:
    env = {**BASE, "PROOF_STORE": "s3", **BUCKET, "BUCKET_ENDPOINT": "http://minio.local:9000"}
    assert Settings.from_env(env).bucket_endpoint.startswith("http://")  # development
    deployed = {
        **env,
        "ENV": "production",
        "ALLOWED_HOSTS": "app.example.test",
    }
    with pytest.raises(ConfigError, match="BUCKET_ENDPOINT"):
        Settings.from_env(deployed)


def test_bucket_vars_ignored_for_filesystem_and_secret_not_in_repr() -> None:
    settings = Settings.from_env({**BASE, **BUCKET})
    assert settings.proof_store == "filesystem"
    assert "test-secret-do-not-print" not in repr(settings)


def test_config_errors_never_contain_values() -> None:
    env = {**BASE, "PROOF_STORE": "s3", **BUCKET}
    del env["BUCKET_NAME"]
    with pytest.raises(ConfigError) as caught:
        Settings.from_env(env)
    assert "test-secret-do-not-print" not in str(caught.value)
    assert "test-key-id" not in str(caught.value)

"""ProofStore (filesystem): write-once keys, SHA-256 on put, safe key paths."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

import pytest

from cloverproof_app.storage import (
    DEFAULT_PROOF_STORE_DIR,
    FilesystemProofStore,
    InvalidKey,
    KeyExists,
    ProofNotFound,
    proof_key,
    store_from_env,
)

ORG = UUID("00000000-0000-4000-8000-000000000001")
REC = UUID("00000000-0000-4000-8000-000000000002")
DATA = b"%PDF-1.7 fixture bytes"
SHA = hashlib.sha256(DATA).hexdigest()


def test_put_returns_sha256_and_get_returns_same_bytes(tmp_path: Path) -> None:
    store = FilesystemProofStore(tmp_path)
    key = proof_key(ORG, REC, SHA)
    assert not store.exists(key)
    assert store.put(key, DATA) == SHA
    assert store.exists(key)
    assert store.get(key) == DATA


def test_key_format_matches_adr_0005(tmp_path: Path) -> None:
    assert proof_key(ORG, REC, SHA) == f"proof/{ORG}/{REC}/{SHA}.pdf"
    with pytest.raises(InvalidKey):
        proof_key(ORG, REC, "ABC")  # not 64 lowercase hex


def test_write_once_refuses_overwrite_and_keeps_original(tmp_path: Path) -> None:
    store = FilesystemProofStore(tmp_path)
    key = proof_key(ORG, REC, SHA)
    store.put(key, DATA)
    with pytest.raises(KeyExists):
        store.put(key, DATA)
    with pytest.raises(KeyExists):
        store.put(key, b"different bytes")
    assert store.get(key) == DATA
    assert [p.name for p in (tmp_path / "proof" / str(ORG) / str(REC)).iterdir()] == [
        f"{SHA}.pdf"
    ]  # no temp files left behind


def test_get_missing_key(tmp_path: Path) -> None:
    store = FilesystemProofStore(tmp_path)
    with pytest.raises(ProofNotFound):
        store.get(proof_key(ORG, REC, SHA))


@pytest.mark.parametrize(
    "key",
    ["", "/etc/passwd", "../x.pdf", "proof/../../x.pdf", "proof//x.pdf", "proof/x\\y.pdf",
     "proof/./x.pdf", "Proof/X.pdf", "proof/x.pdf\n"],
)  # fmt: skip
def test_unsafe_keys_are_refused(tmp_path: Path, key: str) -> None:
    store = FilesystemProofStore(tmp_path)
    with pytest.raises(InvalidKey):
        store.put(key, DATA)
    with pytest.raises(InvalidKey):
        store.get(key)
    with pytest.raises(InvalidKey):
        store.exists(key)


def test_root_from_env(tmp_path: Path) -> None:
    store = store_from_env({"PROOF_STORE_DIR": str(tmp_path / "proofs")})
    assert isinstance(store, FilesystemProofStore)
    assert store.root == (tmp_path / "proofs").resolve()
    default = store_from_env({})
    assert isinstance(default, FilesystemProofStore)
    assert default.root == Path(DEFAULT_PROOF_STORE_DIR).resolve()

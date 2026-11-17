"""Proof-PDF storage behind one interface (ADR 0005 B1).

`ProofStore`: `put(key, bytes) -> sha256`, `get(key) -> bytes`, `exists(key)`. Keys are
write-once: `put` on an existing key raises `KeyExists` and leaves the stored bytes alone.

Implementations: `FilesystemProofStore` (local dev, tests; root env `PROOF_STORE_DIR`,
default `./var/proofs`, gitignored) and `S3ProofStore` in `storage.s3` (any S3-compatible
private bucket: Railway Bucket now, a Canadian host later; ADR 0009 section 4). The app
picks one with `PROOF_STORE=filesystem|s3` (config.Settings).
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol
from uuid import UUID

DEFAULT_PROOF_STORE_DIR = "var/proofs"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
# Lowercase path segments of [a-z0-9._-], no empty / "." / ".." segments, no leading "/".
_SEGMENT = re.compile(r"^[a-z0-9_-][a-z0-9._-]*$")


class StoreError(Exception):
    """Base class for proof-store errors."""


class InvalidKey(StoreError):
    """The key is not a safe relative object key."""


class KeyExists(StoreError):
    """Write-once: the key already holds a document."""


class ProofNotFound(StoreError):
    """No object stored under this key."""


class ProofTampered(StoreError):
    """The stored bytes do not hash to the SHA-256 in their key."""


class ProofStore(Protocol):
    def put(self, key: str, data: bytes) -> str:
        """Store `data` under a new key; return its SHA-256 (lowercase hex)."""
        ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def proof_key(org_id: UUID, recommendation_id: UUID, sha256: str) -> str:
    """`proof/{org_id}/{recommendation_id}/{sha256}.pdf` (the DB checks the same format)."""
    if not _SHA256.fullmatch(sha256):
        raise InvalidKey("sha256 must be 64 lowercase hex characters")
    return f"proof/{org_id}/{recommendation_id}/{sha256}.pdf"


def check_key(key: str) -> list[str]:
    parts = key.split("/")
    if not key or not all(_SEGMENT.fullmatch(p) and p not in {".", ".."} for p in parts):
        raise InvalidKey("unsafe object key")
    return parts


class FilesystemProofStore:
    """Files under `root`, one per key. Writes are atomic and never replace a file."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = self.root.joinpath(*check_key(key))
        if not path.is_relative_to(self.root):  # defence in depth; check_key already refuses
            raise InvalidKey("unsafe object key")
        return path

    def put(self, key: str, data: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise KeyExists(key)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".part")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp, 0o440)
            try:
                os.link(tmp, path)  # atomic and fails if the key exists (no overwrite race)
            except FileExistsError as error:
                raise KeyExists(key) from error
        finally:
            Path(tmp).unlink(missing_ok=True)
        return sha256_hex(data)

    def get(self, key: str) -> bytes:
        path = self._path(key)
        try:
            return path.read_bytes()
        except FileNotFoundError as error:
            raise ProofNotFound(key) from error

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()


def filesystem_store(root: str = "") -> FilesystemProofStore:
    """The filesystem store at `root` (Settings.proof_store_dir), default ./var/proofs."""
    return FilesystemProofStore(root.strip() or DEFAULT_PROOF_STORE_DIR)


def store_from_env(environ: Mapping[str, str] | None = None) -> ProofStore:
    env = os.environ if environ is None else environ
    return filesystem_store(env.get("PROOF_STORE_DIR", ""))

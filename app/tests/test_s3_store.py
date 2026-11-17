"""S3ProofStore against a hand-written fake S3 client (no network, no moto).

The fake answers like S3: HEAD of a missing key is a bare 404, GET of a missing key is
NoSuchKey, a PUT with If-None-Match: * on an existing key is 412 PreconditionFailed.
"""

from __future__ import annotations

import hashlib
import io
from typing import Any
from uuid import UUID

import pytest
from botocore.exceptions import ClientError

from cloverproof_app.storage import (
    InvalidKey,
    KeyExists,
    ProofNotFound,
    ProofTampered,
    StoreError,
    proof_key,
)
from cloverproof_app.storage.s3 import S3ProofStore, s3_store

ORG = UUID("00000000-0000-4000-8000-000000000001")
REC = UUID("00000000-0000-4000-8000-000000000002")
DATA = b"%PDF-1.7 fixture bytes"
SHA = hashlib.sha256(DATA).hexdigest()
KEY = proof_key(ORG, REC, SHA)
BUCKET = "proofs-test"


def client_error(code: str, operation: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, operation)


class FakeS3:
    def __init__(self, *, honour_if_none_match: bool = True) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.puts: list[dict[str, Any]] = []
        self.honour_if_none_match = honour_if_none_match
        self.fail_with: str | None = None
        self.race_before_put = False  # another writer lands between head and put

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if self.fail_with:
            raise client_error(self.fail_with, "HeadObject")
        if (Bucket, Key) not in self.objects:
            raise client_error("404", "HeadObject")
        return {"ContentLength": len(self.objects[(Bucket, Key)])}

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        self.puts.append(kwargs)
        slot = (kwargs["Bucket"], kwargs["Key"])
        if self.race_before_put:
            self.objects[slot] = b"the other writer"
        if self.honour_if_none_match and kwargs.get("IfNoneMatch") == "*" and slot in self.objects:
            raise client_error("PreconditionFailed", "PutObject")
        self.objects[slot] = kwargs["Body"]
        return {}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if self.fail_with:
            raise client_error(self.fail_with, "GetObject")
        if (Bucket, Key) not in self.objects:
            raise client_error("NoSuchKey", "GetObject")
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}


@pytest.fixture
def fake() -> FakeS3:
    return FakeS3()


@pytest.fixture
def store(fake: FakeS3) -> S3ProofStore:
    return S3ProofStore(fake, BUCKET)


def test_put_get_round_trip(store: S3ProofStore, fake: FakeS3) -> None:
    assert not store.exists(KEY)
    assert store.put(KEY, DATA) == SHA
    assert store.exists(KEY)
    assert store.get(KEY) == DATA
    (put,) = fake.puts
    assert put["IfNoneMatch"] == "*"
    assert put["ContentType"] == "application/pdf"
    assert "ACL" not in put  # private: bucket default, never public-read


def test_overwrite_refused_by_head_check(store: S3ProofStore, fake: FakeS3) -> None:
    store.put(KEY, DATA)
    with pytest.raises(KeyExists):
        store.put(KEY, DATA)
    assert len(fake.puts) == 1
    assert store.get(KEY) == DATA


def test_overwrite_refused_by_conditional_put_on_race(store: S3ProofStore, fake: FakeS3) -> None:
    fake.race_before_put = True
    with pytest.raises(KeyExists):
        store.put(KEY, DATA)
    assert fake.objects[(BUCKET, KEY)] == b"the other writer"


def test_tampered_object_detected_on_get(store: S3ProofStore, fake: FakeS3) -> None:
    store.put(KEY, DATA)
    fake.objects[(BUCKET, KEY)] = DATA + b" altered"
    with pytest.raises(ProofTampered):
        store.get(KEY)


def test_put_refuses_bytes_that_do_not_match_the_key(store: S3ProofStore, fake: FakeS3) -> None:
    with pytest.raises(InvalidKey):
        store.put(KEY, b"other bytes")
    assert fake.puts == []


def test_get_missing_key(store: S3ProofStore) -> None:
    with pytest.raises(ProofNotFound):
        store.get(KEY)


@pytest.mark.parametrize(
    "key",
    ["", "../x.pdf", "proof/../../x.pdf", f"proof/{ORG}/{REC}/x.pdf",
     f"other/{ORG}/{REC}/{SHA}.pdf", f"proof/{ORG}/{REC}/{SHA}.PDF", f"proof/{ORG}/{SHA}.pdf"],
)  # fmt: skip
def test_non_proof_keys_are_refused(store: S3ProofStore, fake: FakeS3, key: str) -> None:
    for call in (lambda: store.put(key, DATA), lambda: store.get(key), lambda: store.exists(key)):
        with pytest.raises(InvalidKey):
            call()
    assert fake.puts == []


def test_other_bucket_errors_are_store_errors(store: S3ProofStore, fake: FakeS3) -> None:
    fake.fail_with = "AccessDenied"
    with pytest.raises(StoreError) as caught:
        store.get(KEY)
    assert not isinstance(caught.value, ProofNotFound)
    with pytest.raises(StoreError):
        store.exists(KEY)


def test_s3_store_builds_a_client_without_network() -> None:
    store = s3_store(
        endpoint="https://bucket.example.test",
        region="us-east-1",
        bucket=BUCKET,
        access_key_id="test-key-id",
        secret_access_key="test-secret-value",
    )
    assert store.bucket == BUCKET
    assert store.client.meta.endpoint_url == "https://bucket.example.test"  # type: ignore[attr-defined]

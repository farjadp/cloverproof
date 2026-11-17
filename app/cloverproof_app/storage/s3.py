"""S3-compatible ProofStore (ADR 0005 B1; portable per ADR 0009 section 4).

Plain S3 API through boto3, no provider-specific calls, so the same code talks to the
Railway Bucket now and to a Canadian host's bucket later. Contract (same as the
filesystem store, plus the bucket-specific parts):
- keys are proof keys only: `proof/{org_id}/{recommendation_id}/{sha256}.pdf`;
- `put` refuses bytes whose SHA-256 is not the one in the key (InvalidKey);
- write-once: `head_object` first, then `put_object` with `IfNoneMatch="*"` so a
  concurrent writer cannot replace the object either (412/409 -> KeyExists). A provider
  that ignores the header still gets the head check;
- private: no ACL is sent (bucket default, private); objects are only served through the
  app's auth-checked download route, never by public URL;
- `get` re-hashes the bytes and raises ProofTampered on a mismatch with the key.
"""

from __future__ import annotations

import re
from typing import Any, Protocol

from botocore.exceptions import ClientError

from cloverproof_app.storage import (
    InvalidKey,
    KeyExists,
    ProofNotFound,
    ProofTampered,
    StoreError,
    check_key,
    sha256_hex,
)

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
PROOF_KEY = re.compile(rf"^proof/{_UUID}/{_UUID}/(?P<sha256>[0-9a-f]{{64}})\.pdf$")
NOT_FOUND_CODES = frozenset({"404", "NoSuchKey", "NotFound"})
CONFLICT_CODES = frozenset({"412", "409", "PreconditionFailed", "ConditionalRequestConflict"})


class S3Client(Protocol):
    """The three boto3 S3 client calls the store uses (a fake implements them in tests)."""

    def head_object(self, **kwargs: Any) -> dict[str, Any]: ...

    def put_object(self, **kwargs: Any) -> dict[str, Any]: ...

    def get_object(self, **kwargs: Any) -> dict[str, Any]: ...


def _code(error: ClientError) -> str:
    return str(error.response.get("Error", {}).get("Code", ""))


def key_sha256(key: str) -> str:
    """The SHA-256 a proof key names; InvalidKey for anything that is not a proof key."""
    check_key(key)
    match = PROOF_KEY.fullmatch(key)
    if match is None:
        raise InvalidKey("not a proof key: proof/{org_id}/{recommendation_id}/{sha256}.pdf")
    return match["sha256"]


class S3ProofStore:
    def __init__(self, client: S3Client, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    def exists(self, key: str) -> bool:
        key_sha256(key)
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            if _code(error) in NOT_FOUND_CODES:
                return False
            raise StoreError(f"bucket head_object failed ({_code(error)})") from error
        return True

    def put(self, key: str, data: bytes) -> str:
        expected = key_sha256(key)
        digest = sha256_hex(data)
        if digest != expected:
            raise InvalidKey("the bytes do not hash to the SHA-256 in the key")
        if self.exists(key):
            raise KeyExists(key)
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType="application/pdf",
                IfNoneMatch="*",
            )
        except ClientError as error:
            if _code(error) in CONFLICT_CODES:
                raise KeyExists(key) from error
            raise StoreError(f"bucket put_object failed ({_code(error)})") from error
        return digest

    def get(self, key: str) -> bytes:
        expected = key_sha256(key)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            if _code(error) in NOT_FOUND_CODES:
                raise ProofNotFound(key) from error
            raise StoreError(f"bucket get_object failed ({_code(error)})") from error
        body = response["Body"]
        try:
            data = body.read()
        finally:
            body.close()
        if sha256_hex(data) != expected:
            raise ProofTampered(key)
        return data


def s3_store(
    *, endpoint: str, region: str, bucket: str, access_key_id: str, secret_access_key: str
) -> S3ProofStore:
    """An S3ProofStore on a real boto3 client. No network call until the first request."""
    import boto3  # deferred: tests and the filesystem store never load it
    from botocore.config import Config

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=5,
            read_timeout=30,
            # Portability: some S3-compatible providers reject boto3's default CRC
            # checksum headers; the app re-hashes with SHA-256 on every get instead.
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )
    return S3ProofStore(client, bucket)

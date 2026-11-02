"""Private object storage abstraction (FND-006). Originals are private; access is via short-lived
signed URLs. ``local`` backend for dev/tests; ``s3`` backend for S3/MinIO/R2 (boto3, lazy import)."""

from __future__ import annotations

import hashlib
import hmac
import time
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import quote

from app.core.config import get_settings

MAX_SIGNED_TTL = 3600


def _safe_key(key: str) -> str:
    if key.startswith("/") or ".." in key.split("/") or "\\" in key or not key:
        raise ValueError("invalid object key")
    return key


def tenant_key(merchant_id: str, *parts: str) -> str:
    """All merchant objects live under m/<merchant_id>/ so bucket policies and cleanup are tenant-scoped."""
    return _safe_key("/".join(("m", merchant_id, *parts)))


class ObjectStorage(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    def get(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def signed_get_url(self, key: str, ttl_s: int = 300) -> str: ...

    @abstractmethod
    def signed_put_url(self, key: str, content_type: str, ttl_s: int = 300) -> str: ...


class LocalStorage(ObjectStorage):
    def __init__(self, root: Path, signing_secret: str) -> None:
        self.root = root
        self._secret = signing_secret.encode()

    def _path(self, key: str) -> Path:
        p = (self.root / _safe_key(key)).resolve()
        if not str(p).startswith(str(self.root.resolve())):
            raise ValueError("invalid object key")
        return p

    def put(self, key: str, data: bytes, content_type: str) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def _sign(self, method: str, key: str, ttl_s: int) -> str:
        exp = int(time.time()) + min(ttl_s, MAX_SIGNED_TTL)
        sig = hmac.new(self._secret, f"{method}\n{key}\n{exp}".encode(), hashlib.sha256).hexdigest()
        return f"/_dev/objects/{quote(_safe_key(key))}?exp={exp}&sig={sig}&m={method}"

    def verify(self, method: str, key: str, exp: int, sig: str) -> bool:
        if exp < time.time():
            return False
        good = hmac.new(self._secret, f"{method}\n{key}\n{exp}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(good, sig)

    def signed_get_url(self, key: str, ttl_s: int = 300) -> str:
        return self._sign("GET", key, ttl_s)

    def signed_put_url(self, key: str, content_type: str, ttl_s: int = 300) -> str:
        return self._sign("PUT", key, ttl_s)


class S3Storage(ObjectStorage):
    def __init__(self) -> None:
        import boto3  # lazy: optional dependency for s3 backend

        s = get_settings()
        self.bucket = s.s3_bucket
        self._s3 = boto3.client(
            "s3",
            endpoint_url=s.s3_endpoint_url,
            region_name=s.s3_region,
            aws_access_key_id=s.s3_access_key_id.get_secret_value() if s.s3_access_key_id else None,
            aws_secret_access_key=s.s3_secret_access_key.get_secret_value()
            if s.s3_secret_access_key
            else None,
        )

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._s3.put_object(
            Bucket=self.bucket,
            Key=_safe_key(key),
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )

    def get(self, key: str) -> bytes:
        return self._s3.get_object(Bucket=self.bucket, Key=_safe_key(key))["Body"].read()

    def delete(self, key: str) -> None:
        self._s3.delete_object(Bucket=self.bucket, Key=_safe_key(key))

    def signed_get_url(self, key: str, ttl_s: int = 300) -> str:
        return self._s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": _safe_key(key)},
            ExpiresIn=min(ttl_s, MAX_SIGNED_TTL),
        )

    def signed_put_url(self, key: str, content_type: str, ttl_s: int = 300) -> str:
        return self._s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": _safe_key(key), "ContentType": content_type},
            ExpiresIn=min(ttl_s, MAX_SIGNED_TTL),
        )


def get_storage() -> ObjectStorage:
    s = get_settings()
    if s.storage_backend == "s3":
        return S3Storage()
    return LocalStorage(s.storage_local_root, s.jwt_secret.get_secret_value())

"""Envelope encryption for secrets at rest (BYOK provider keys, channel OAuth tokens).

Each secret is encrypted with a fresh 256-bit data key (AES-256-GCM); the data key is wrapped by a
key-encryption key from a ``KeyProvider``. Production uses a cloud KMS provider; the ``local``
provider exists for development/test only and is refused in production by Settings validation.
Associated data binds ciphertext to its owner (e.g. merchant id + purpose) so a blob copied to
another tenant fails to decrypt.
"""

from __future__ import annotations

import base64
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings


class KeyProvider(ABC):
    key_id: str

    @abstractmethod
    def wrap(self, data_key: bytes, aad: bytes) -> bytes: ...

    @abstractmethod
    def unwrap(self, wrapped: bytes, aad: bytes) -> bytes: ...


class LocalKeyProvider(KeyProvider):
    def __init__(self, kek: bytes, key_id: str = "local-v1") -> None:
        if len(kek) != 32:
            raise ValueError("Local KEK must be 32 bytes")
        self._aes = AESGCM(kek)
        self.key_id = key_id

    def wrap(self, data_key: bytes, aad: bytes) -> bytes:
        nonce = os.urandom(12)
        return nonce + self._aes.encrypt(nonce, data_key, aad)

    def unwrap(self, wrapped: bytes, aad: bytes) -> bytes:
        return self._aes.decrypt(wrapped[:12], wrapped[12:], aad)


class KmsKeyProvider(KeyProvider):
    """Placeholder for AWS KMS / GCP KMS. Integration needs: KMS key ARN, IAM role for API/workers.
    Tracked in docs/KNOWN_GAPS.md (SEC-KMS)."""

    def __init__(self) -> None:
        raise NotImplementedError("KMS key provider not configured; see docs/KNOWN_GAPS.md")

    def wrap(self, data_key: bytes, aad: bytes) -> bytes:  # pragma: no cover
        raise NotImplementedError

    def unwrap(self, wrapped: bytes, aad: bytes) -> bytes:  # pragma: no cover
        raise NotImplementedError


def get_key_provider() -> KeyProvider:
    s = get_settings()
    if s.kek_provider == "local":
        return LocalKeyProvider(base64.b64decode(s.local_kek_b64.get_secret_value()))
    if s.kek_provider == "kms":
        return KmsKeyProvider()
    raise ValueError(f"Unknown key provider {s.kek_provider}")


@dataclass(frozen=True)
class SealedSecret:
    blob: str  # JSON, safe to store

    @staticmethod
    def seal(plaintext: str, aad: str, provider: KeyProvider | None = None) -> SealedSecret:
        kp = provider or get_key_provider()
        dk = AESGCM.generate_key(256)
        nonce = os.urandom(12)
        ct = AESGCM(dk).encrypt(nonce, plaintext.encode(), aad.encode())
        doc = {
            "v": 1,
            "kid": kp.key_id,
            "wdk": base64.b64encode(kp.wrap(dk, aad.encode())).decode(),
            "n": base64.b64encode(nonce).decode(),
            "ct": base64.b64encode(ct).decode(),
        }
        return SealedSecret(json.dumps(doc, separators=(",", ":")))

    def open(self, aad: str, provider: KeyProvider | None = None) -> str:
        kp = provider or get_key_provider()
        doc = json.loads(self.blob)
        dk = kp.unwrap(base64.b64decode(doc["wdk"]), aad.encode())
        return (
            AESGCM(dk).decrypt(base64.b64decode(doc["n"]), base64.b64decode(doc["ct"]), aad.encode()).decode()
        )

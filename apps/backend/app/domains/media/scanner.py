"""Upload malware scanning. ``clamd`` speaks the ClamAV INSTREAM protocol over TCP; ``none`` is for
development/test only (Settings refuses it in production) and marks assets ``skipped``."""

from __future__ import annotations

import socket
import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import get_settings


@dataclass(frozen=True)
class ScanResult:
    status: str  # clean | infected | skipped | error
    signature: str | None = None


class Scanner(ABC):
    @abstractmethod
    def scan(self, data: bytes) -> ScanResult: ...


class NoopScanner(Scanner):
    def scan(self, data: bytes) -> ScanResult:
        return ScanResult("skipped")


class ClamdScanner(Scanner):
    CHUNK = 64 * 1024

    def __init__(self, host: str, port: int, timeout_s: float = 30) -> None:
        self.host, self.port, self.timeout_s = host, port, timeout_s

    def scan(self, data: bytes) -> ScanResult:
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout_s) as sock:
                sock.sendall(b"zINSTREAM\0")
                for i in range(0, len(data), self.CHUNK):
                    chunk = data[i : i + self.CHUNK]
                    sock.sendall(struct.pack("!L", len(chunk)) + chunk)
                sock.sendall(struct.pack("!L", 0))
                reply = b""
                while not reply.endswith(b"\0"):
                    part = sock.recv(4096)
                    if not part:
                        break
                    reply += part
        except OSError:
            return ScanResult("error")
        text = reply.rstrip(b"\0").decode(errors="replace")
        if text.endswith("OK"):
            return ScanResult("clean")
        if text.endswith("FOUND"):
            return ScanResult("infected", text.split(":", 1)[-1].replace("FOUND", "").strip()[:120])
        return ScanResult("error")


def get_scanner() -> Scanner:
    s = get_settings()
    if s.malware_scanner == "clamd":
        return ClamdScanner(s.clamd_host, s.clamd_port)
    return NoopScanner()

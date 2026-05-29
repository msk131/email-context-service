import base64
import os
from datetime import datetime
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core import settings

NONCE_SIZE = 12


def _encryption_key() -> bytes:
    return bytes.fromhex(settings.encryption_key_hex)


def encrypt_text(plaintext: str) -> str:
    key = _encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_text(ciphertext: str) -> str:
    key = _encryption_key()
    decoded = base64.b64decode(ciphertext.encode("utf-8"))
    nonce = decoded[:NONCE_SIZE]
    payload = decoded[NONCE_SIZE:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, payload, None).decode("utf-8")


def normalize_date_range(
    start_date: Optional[datetime], end_date: Optional[datetime]
) -> tuple[datetime, datetime]:
    boundary = end_date or start_date
    tzinfo = boundary.tzinfo if boundary and boundary.tzinfo else None
    earliest = datetime.fromtimestamp(0, tz=tzinfo)
    now = datetime.now(tz=tzinfo)
    if start_date is None:
        start_date = earliest
    if end_date is None:
        end_date = now
    if start_date > end_date:
        raise ValueError("start_date must be before end_date")
    return start_date, end_date

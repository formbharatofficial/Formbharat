"""Versioned document encryption for new uploads.

Old files have no FBDOC1 header and are read as their original bytes.
This module never rewrites an existing file. A missing or lost key cannot
be recovered. A new key does not decrypt files written with the previous
key, and those files are not re-encrypted automatically.

OCR uses a temporary plaintext file outside document storage and deletes
it afterwards. Downloads are decrypted in memory. Database backups still
contain older plaintext OCR rows. New OCR text and extracted JSON are
stored with an FBTEXT1 prefix only when a valid key is configured.
Nothing here is written to logs.
"""

import base64
import binascii
import os
import stat
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


MAGIC = b"FBDOC1"
TEXT_PREFIX = "FBTEXT1:"
_FILE_AAD = b"formbharat-document-v1"
_TEXT_AAD = b"formbharat-text-v1"
_INVALID = object()


class DocumentStorageError(Exception):
    """A safe storage error. The message never includes key material."""


def encryption_required():
    value = os.environ.get("FORMBHARAT_REQUIRE_DOCUMENT_ENCRYPTION", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _key_material():
    raw = os.environ.get("FORMBHARAT_DOCUMENT_KEY", "").strip()
    if not raw:
        return None
    try:
        if len(raw) == 64 and all(char in "0123456789abcdefABCDEF" for char in raw):
            key = bytes.fromhex(raw)
        else:
            padded = raw + ("=" * (-len(raw) % 4))
            key = base64.urlsafe_b64decode(padded.encode("ascii"))
        if len(key) != 32:
            return _INVALID
        return key
    except (binascii.Error, UnicodeError, ValueError):
        return _INVALID


def encryption_status():
    key = _key_material()
    required = encryption_required()
    if key is _INVALID:
        new_uploads = "rejected"
        reason = "The document key is not valid. New uploads are not saved."
        enabled = False
    elif key is None and required:
        new_uploads = "rejected"
        reason = (
            "Document encryption is required and the key is not available. "
            "New uploads are not saved."
        )
        enabled = False
    elif key is None:
        new_uploads = "plaintext"
        reason = (
            "No document key is configured. New uploads stay plaintext "
            "unless encryption is required. Existing files are not rewritten."
        )
        enabled = False
    else:
        new_uploads = "encrypted"
        reason = (
            "New uploads are encrypted. Existing files without the FBDOC1 "
            "header stay readable and are not rewritten. A lost key cannot "
            "be recovered, and changing the key does not decrypt older files."
        )
        enabled = True
    return {
        "enabled": enabled,
        "required": required,
        "existing_files": "unchanged",
        "new_uploads": new_uploads,
        "reason": reason,
    }


def _reject_if_unusable(key):
    if key is _INVALID:
        raise DocumentStorageError(
            "Document encryption key is not valid. The upload was not saved."
        )
    if key is None and encryption_required():
        raise DocumentStorageError(
            "Document encryption key is not available. The upload was not saved."
        )


def _encrypt(payload, key, aad):
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, payload, aad)
    return nonce + ciphertext


def _decrypt(payload, key, aad):
    if len(payload) < 13:
        raise DocumentStorageError("Stored file could not be read.")
    nonce, ciphertext = payload[:12], payload[12:]
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, aad)
    except Exception as error:
        raise DocumentStorageError("Stored file could not be read.") from error


def store_bytes(data):
    """Return bytes to write. Legacy files are never passed through here."""
    if not isinstance(data, (bytes, bytearray)):
        raise DocumentStorageError("The upload was not saved.")
    key = _key_material()
    _reject_if_unusable(key)
    if key is None:
        return bytes(data)
    return MAGIC + _encrypt(bytes(data), key, _FILE_AAD)


def read_bytes(path):
    """Read one stored file without changing it."""
    blob = Path(path).read_bytes()
    if not blob.startswith(MAGIC):
        return blob
    key = _key_material()
    if key is None or key is _INVALID:
        raise DocumentStorageError("Stored file could not be read.")
    return _decrypt(blob[len(MAGIC):], key, _FILE_AAD)


def protect_text(text):
    """Protect new OCR text. Plaintext mode returns the same text."""
    value = "" if text is None else str(text)
    key = _key_material()
    _reject_if_unusable(key)
    if key is None or value == "":
        return value
    token = base64.urlsafe_b64encode(
        _encrypt(value.encode("utf-8"), key, _TEXT_AAD)
    ).decode("ascii")
    return TEXT_PREFIX + token


def reveal_text(stored):
    """Return legacy plaintext unchanged. Unreadable ciphertext becomes empty."""
    if not isinstance(stored, str) or not stored.startswith(TEXT_PREFIX):
        return "" if stored is None else str(stored)
    key = _key_material()
    if key is None or key is _INVALID:
        return ""
    try:
        payload = base64.urlsafe_b64decode(stored[len(TEXT_PREFIX):].encode("ascii"))
        return _decrypt(payload, key, _TEXT_AAD).decode("utf-8")
    except (binascii.Error, UnicodeError, DocumentStorageError):
        return ""


def read_for_ocr(path, reader):
    """Give OCR a plaintext path, then delete any temporary file."""
    blob = Path(path).read_bytes()
    if not blob.startswith(MAGIC):
        return reader(path)
    plaintext = read_bytes(path)
    descriptor, temporary = tempfile.mkstemp(prefix="fb-ocr-")
    try:
        os.write(descriptor, plaintext)
        os.close(descriptor)
        descriptor = None
        try:
            os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        return reader(temporary)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            os.remove(temporary)
        except OSError:
            pass

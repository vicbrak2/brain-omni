"""Tests de verificación de firma HMAC-SHA256 (compartida por WhatsApp e Instagram)."""
import hashlib
import hmac

import pytest
from fastapi import HTTPException

from app.api.webhook import _verify_signature

SECRET = "test-secret-key"


def _sign(body: bytes, secret: str = SECRET) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


# ── Casos válidos ─────────────────────────────────────────────────────────────

def test_valid_signature_does_not_raise():
    body = b'{"entry": []}'
    _verify_signature(body, _sign(body), SECRET, "TEST_SECRET")


def test_valid_signature_with_binary_body():
    body = b"\x00\x01\x02\x03payload"
    _verify_signature(body, _sign(body), SECRET, "TEST_SECRET")


def test_empty_secret_skips_validation():
    """Si no hay secret configurado, no debe bloquear (modo desarrollo)."""
    _verify_signature(b"any-body", "sha256=whatever", "", "TEST_SECRET")


# ── Casos inválidos ───────────────────────────────────────────────────────────

def test_wrong_signature_raises_401():
    body = b'{"entry": []}'
    with pytest.raises(HTTPException) as exc:
        _verify_signature(body, "sha256=0badcafe", SECRET, "TEST_SECRET")
    assert exc.value.status_code == 401


def test_missing_sha256_prefix_raises_401():
    body = b'{"entry": []}'
    with pytest.raises(HTTPException) as exc:
        _verify_signature(body, "invalidsignature", SECRET, "TEST_SECRET")
    assert exc.value.status_code == 401


def test_empty_header_raises_401():
    body = b'{"entry": []}'
    with pytest.raises(HTTPException) as exc:
        _verify_signature(body, "", SECRET, "TEST_SECRET")
    assert exc.value.status_code == 401


def test_tampered_body_raises_401():
    """Una firma válida para body A no sirve para body B."""
    original = b'{"entry": []}'
    tampered = b'{"entry": [{"evil": true}]}'
    sig_for_original = _sign(original)
    with pytest.raises(HTTPException) as exc:
        _verify_signature(tampered, sig_for_original, SECRET, "TEST_SECRET")
    assert exc.value.status_code == 401

"""Small, dependency-free password and bearer-token helpers for the local MVP.

Tokens are HMAC-signed and expire. This is not a replacement for a managed
identity provider; production deployments should add key rotation and rate limits.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time

PBKDF2_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64(salt)}${_b64(derived)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_text, expected_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _unb64(salt_text), int(iterations)
        )
        return hmac.compare_digest(actual, _unb64(expected_text))
    except (ValueError, TypeError):
        return False


def _secret() -> bytes:
    value = os.getenv("FORGEMIND_AUTH_SECRET", "")
    if len(value) < 32:
        if os.getenv("APP_ENV", "development").lower() not in {"development", "test"}:
            raise RuntimeError("FORGEMIND_AUTH_SECRET must be at least 32 characters outside development")
        value = "local-development-only-change-this-secret-before-deployment"
    return value.encode("utf-8")


def create_access_token(user_id: str, organization_id: str, role: str, expires_in: int = 3600) -> str:
    payload = {
        "sub": user_id,
        "org": organization_id,
        "role": role,
        "exp": int(time.time()) + expires_in,
    }
    body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _b64(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{signature}"


def decode_access_token(token: str) -> dict | None:
    try:
        body, signature = token.split(".", 1)
        expected = _b64(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(_unb64(body))
        if not isinstance(payload, dict) or int(payload["exp"]) <= int(time.time()):
            return None
        if not all(isinstance(payload.get(key), str) and payload[key] for key in ("sub", "org", "role")):
            return None
        return payload
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

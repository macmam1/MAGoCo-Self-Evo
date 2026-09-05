"""Encrypted vault for provider API keys.

Master key resolution order:
1. MAGOCO_MASTER_KEY env var (raw string -> PBKDF2 derived, or urlsafe-b64 accepted as-is)
2. data/.master_key file (auto-created once, chmod 600)

The key file MUST never be committed (covered by .gitignore).
"""

import base64
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _master_key_b64(data_dir: str = "./data") -> bytes:
    """Always returns urlsafe-b64-encoded 32-byte key (Fernet-ready)."""
    env_key = os.environ.get("MAGOCO_MASTER_KEY")
    if env_key:
        try:
            raw = base64.urlsafe_b64decode(env_key)
            if len(raw) == 32:
                return env_key.encode()
        except Exception:
            pass
        # Derive from arbitrary string.
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b"magoco-vault", iterations=100_000)
        return base64.urlsafe_b64encode(kdf.derive(env_key.encode()))

    key_file = Path(data_dir) / ".master_key"
    if key_file.exists():
        return key_file.read_bytes().strip()

    from cryptography.fernet import Fernet
    raw_b64 = Fernet.generate_key()
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_bytes(raw_b64)
    try:
        os.chmod(key_file, 0o600)
    except Exception:
        pass
    logger.info("Generated new vault master key at %s", key_file)
    return raw_b64


def _fernet(data_dir: str = "./data"):
    from cryptography.fernet import Fernet
    return Fernet(_master_key_b64(data_dir))


def encrypt_secret(plaintext: str, data_dir: str = "./data") -> str:
    """Encrypt an API key. Returns '' for empty input."""
    if not plaintext:
        return ""
    return _fernet(data_dir).encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str, data_dir: str = "./data") -> str:
    """Decrypt an API key. Returns '' for empty input."""
    if not token:
        return ""
    return _fernet(data_dir).decrypt(token.encode()).decode()

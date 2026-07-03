"""
Standalone password hashing — PBKDF2-HMAC-SHA256, salted.
No Flask/Werkzeug dependency; uses only Python's stdlib `hashlib`/`hmac`/`secrets`.

Hash format stored in the DB: "pbkdf2:sha256:<iterations>$<salt_hex>$<hash_hex>"
(intentionally similar to Werkzeug's format for familiarity, but generated independently)
"""
import hashlib
import hmac
import secrets

_ITERATIONS = 260_000


def generate_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return f"pbkdf2:sha256:{_ITERATIONS}${salt}${derived.hex()}"


def check_password_hash(stored_hash: str, password: str) -> bool:
    try:
        algo_part, salt, hash_hex = stored_hash.split("$")
        iterations = int(algo_part.split(":")[2])
    except (ValueError, IndexError):
        return False

    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return hmac.compare_digest(derived.hex(), hash_hex)

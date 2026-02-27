import base64
import hashlib
import hmac
import os


class PasswordHasher:
    def __init__(self, iterations: int = 120_000, salt_bytes: int = 16) -> None:
        self._iterations = iterations
        self._salt_bytes = salt_bytes

    def hash(self, password: str) -> str:
        salt = os.urandom(self._salt_bytes)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, self._iterations)
        return "pbkdf2_sha256${}${}${}".format(
            self._iterations,
            base64.b64encode(salt).decode("utf-8"),
            base64.b64encode(dk).decode("utf-8"),
        )

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            alg, iterations, salt_b64, hash_b64 = password_hash.split("$", 3)
            if alg != "pbkdf2_sha256":
                return False
            iterations = int(iterations)
            salt = base64.b64decode(salt_b64.encode("utf-8"))
            expected = base64.b64decode(hash_b64.encode("utf-8"))
            dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(dk, expected)
        except Exception:
            return False

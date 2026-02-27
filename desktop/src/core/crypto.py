import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet, InvalidToken

class CryptoError(Exception):
    pass

class CryptoManager:
    ITERATIONS = 600_000
    CANARY = "vault_ok"

    def __init__(self) -> None:
        self._fernet: Fernet | None = None
        self._salt: bytes | None = None

    @staticmethod
    def generate_salt() -> bytes:
        return os.urandom(32)

    @staticmethod
    def _derive_key(password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=CryptoManager.ITERATIONS,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))

    def unlock(self, password: str, salt: bytes) -> None:
        self._salt = salt
        self._fernet = Fernet(self._derive_key(password, salt))

    def lock(self) -> None:
        self._fernet = None
        self._salt = None

    @property
    def is_unlocked(self) -> bool:
        return self._fernet is not None

    def encrypt(self, plaintext: str) -> str:
        if not self._fernet:
            raise CryptoError("Vault is locked.")
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        if not self._fernet:
            raise CryptoError("Vault is locked.")
        try:
            return self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except (InvalidToken, Exception) as exc:
            raise CryptoError("Decryption failed — wrong password or corrupted data.") from exc

    def make_canary(self) -> str:
        return self.encrypt(self.CANARY)

    def verify_canary(self, encrypted_canary: str) -> bool:
        try:
            return self.decrypt(encrypted_canary) == self.CANARY
        except CryptoError:
            return False

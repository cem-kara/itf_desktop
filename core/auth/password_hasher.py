class PasswordHasher:
    def hash(self, password: str) -> str:
        # TODO: replace with bcrypt/argon2 implementation.
        raise NotImplementedError

    def verify(self, password: str, password_hash: str) -> bool:
        # TODO: replace with bcrypt/argon2 implementation.
        raise NotImplementedError

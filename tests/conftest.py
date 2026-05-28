import os

os.environ.setdefault("ENCRYPTION_KEY_HEX", "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

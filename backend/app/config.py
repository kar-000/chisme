from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Redis — presence, pub/sub, voice state, HA coordination
    # Set to empty string to disable Redis (app falls back to in-memory only)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PRESENCE_TTL: int = 300  # seconds — key expires if heartbeat stops

    # Server identity — used to namespace Redis keys and qualify user identities.
    # Set to your public domain in production (e.g. "chisme-groupa.example.com").
    # Each independent Chisme deployment should have a unique value.
    SERVER_DOMAIN: str = "localhost"

    # Tenor GIF API (v2) — set in .env (console.cloud.google.com → enable Tenor API → create key)
    TENOR_API_KEY: str = ""
    TENOR_API_BASE: str = "https://tenor.googleapis.com/v2"
    TENOR_SEARCH_LIMIT: int = 20

    # File uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 26_214_400  # 25 MB
    ALLOWED_MIME_TYPES: list[str] = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "video/mp4",
        "video/webm",
        "application/pdf",
        "application/zip",
        "text/plain",
    ]

    # Web Push (VAPID) — generate with: npx web-push generate-vapid-keys
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_CLAIMS_EMAIL: str = "mailto:admin@localhost"

    # SMTP — optional, for operator notifications on server creation.
    # If SMTP_HOST is empty, events are logged only (visible in docker compose logs).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_TLS: bool = True
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_ADMIN_EMAIL: str = ""  # destination for operator notifications

    model_config = {"env_file": ".env"}


settings = Settings()

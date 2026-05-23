from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://mongodb:27017"
    mongodb_db: str = "ollog"
    secret_key: str
    api_token_secret: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    admin_username: str | None = None
    admin_password: str | None = None
    admin_callsign: str | None = None

    # UDP listener (v1.4)
    udp_enabled: bool = True
    udp_port: int = 2399
    udp_bind_host: str = "127.0.0.1"
    udp_operator: str | None = None

    # ACLog TCP API bridge
    aclog_enabled: bool = True
    aclog_reconnect_seconds: int = 5
    aclog_scan_seconds: int = 10

    # Backup (v1.8)
    backup_dir: str = "/app/backups"
    backup_schedule: str | None = None
    backup_s3_bucket: str | None = None
    backup_s3_prefix: str = "backups/"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()

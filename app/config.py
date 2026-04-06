from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://mongodb:27017"
    mongodb_db: str = "ollog"
    secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    admin_username: str | None = None
    admin_password: str | None = None
    admin_callsign: str | None = None

    # UDP listener (v1.4)
    udp_enabled: bool = False
    udp_port: int = 2399
    udp_bind_host: str = "127.0.0.1"
    udp_operator: str | None = None

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()

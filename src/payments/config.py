import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    DEBUG: bool = True

    APP_HOST: str = "localhost"
    APP_PORT: int = 8000

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"  # noqa: S105
    POSTGRES_DB: str = "postgres"
    POSTGRES_URL_SCHEMA: str = "postgresql+asyncpg"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    OUTBOX_SCHEDULER_INTERVAL_SECONDS: float = 1.0
    OUTBOX_SCHEDULER_BATCH_SIZE: int = 100

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            DEBUG=cls._env_bool("DEBUG", cls.DEBUG),
            APP_HOST=os.getenv("APP_HOST", cls.APP_HOST),
            APP_PORT=cls._env_int("APP_PORT", cls.APP_PORT),
            POSTGRES_HOST=os.getenv("POSTGRES_HOST", cls.POSTGRES_HOST),
            POSTGRES_PORT=cls._env_int("POSTGRES_PORT", cls.POSTGRES_PORT),
            POSTGRES_USER=os.getenv("POSTGRES_USER", cls.POSTGRES_USER),
            POSTGRES_PASSWORD=os.getenv(
                "POSTGRES_PASSWORD",
                cls.POSTGRES_PASSWORD,
            ),
            POSTGRES_DB=os.getenv("POSTGRES_DB", cls.POSTGRES_DB),
            RABBITMQ_URL=os.getenv(
                "RABBITMQ_URL",
                cls.RABBITMQ_URL,
            ),
            OUTBOX_SCHEDULER_INTERVAL_SECONDS=cls._env_float(
                "OUTBOX_SCHEDULER_INTERVAL_SECONDS",
                cls.OUTBOX_SCHEDULER_INTERVAL_SECONDS,
            ),
        )

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        value = os.getenv(name)
        if value is None:
            return default
        return int(value)

    @staticmethod
    def _env_float(name: str, default: float) -> float:
        value = os.getenv(name)
        if value is None:
            return default
        return float(value)

    @property
    def ENGINE_URL(self) -> str:  # noqa: N802
        return (
            f"{self.POSTGRES_URL_SCHEMA}://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

from .base import BaseConfig


class DevConfig(BaseConfig):
    ENV: str = "dev"
    INITIAL_CAPITAL: float = 10_000.0

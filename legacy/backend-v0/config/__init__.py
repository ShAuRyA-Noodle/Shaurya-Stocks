import os
from .dev import DevConfig
from .prod import ProdConfig


def load_config():
    env = os.getenv("ENV", "dev").lower()

    if env == "prod":
        return ProdConfig()
    elif env == "dev":
        return DevConfig()
    else:
        raise ValueError(f"Unknown ENV: {env}")


CONFIG = load_config()

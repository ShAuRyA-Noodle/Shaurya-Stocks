from dataclasses import dataclass
from pathlib import Path
import pytz


@dataclass(frozen=True)
class BaseConfig:
    # ===== PROJECT =====
    PROJECT_NAME: str = "quant-ml-trading-system"
    ENV: str = "base"

    # ===== TIME =====
    TIMEZONE = pytz.timezone("US/Eastern")

    # ===== PATHS =====
    ROOT_DIR: Path = Path(__file__).resolve().parents[1]
    BACKEND_DIR: Path = ROOT_DIR / "backend"
    DATA_DIR: Path = ROOT_DIR / "data"
    MODELS_DIR: Path = ROOT_DIR / "models"
    REPORTS_DIR: Path = ROOT_DIR / "reports"
    STATE_DIR: Path = ROOT_DIR / "state"
    LOG_DIR: Path = ROOT_DIR / "logs"

    # ===== MARKET =====
    UNIVERSE: tuple = ("AAPL", "MSFT")

    # ===== CAPITAL =====
    INITIAL_CAPITAL: float = 100_000.0
    MAX_POSITION_PCT: float = 0.10
    MAX_POSITIONS: int = 5

    # ===== COSTS =====
    TRANSACTION_COST_PCT: float = 0.001
    SLIPPAGE_PCT: float = 0.0005

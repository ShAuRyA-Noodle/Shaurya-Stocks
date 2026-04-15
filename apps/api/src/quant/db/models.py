"""
SQLAlchemy 2.0 models — the canonical data schema for the platform.

Organization:
- auth.*       — users, refresh tokens, API keys
- market.*     — tickers, universe membership (point-in-time), corporate actions
- ohlcv_daily  — daily bars (TimescaleDB hypertable) in public schema for simplicity
- ohlcv_1m     — 1-minute bars (TimescaleDB hypertable)
- feature.*    — engineered features per (date, symbol) (hypertable)
- signal.*     — model signals + SHAP attributions (hypertable)
- model.*      — model registry metadata (MLflow is authoritative; this mirrors)
- portfolio.*  — positions, trades, snapshots
- news.*       — news articles + LLM sentiment cache
- macro.*      — FRED series (hypertable)

Timescale hypertables are created in migration 001 via raw SQL (not Alembic op).
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from quant.db.base import Base


# ================================================================
# AUTH
# ================================================================
class UserRole(enum.StrEnum):
    viewer = "viewer"  # read-only signals + metrics
    trader = "trader"  # paper trading with own Alpaca keys
    admin = "admin"  # full ops access


class UserTier(enum.StrEnum):
    free = "free"
    pro = "pro"
    premium = "premium"  # live trading unlocked


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role"), default=UserRole.viewer)
    tier: Mapped[UserTier] = mapped_column(SAEnum(UserTier, name="user_tier"), default=UserTier.free)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Optional per-user Alpaca keys for pro/premium tiers (encrypted at rest in Sprint 7)
    alpaca_key_id: Mapped[str | None] = mapped_column(String(255))
    alpaca_secret_ciphertext: Mapped[str | None] = mapped_column(Text)
    alpaca_paper: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    """Opaque refresh tokens — rotated on every use."""

    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": "auth"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


# ================================================================
# MARKET / UNIVERSE
# ================================================================
class Ticker(Base):
    """Master list of tickers we ever track."""

    __tablename__ = "tickers"
    __table_args__ = {"schema": "market"}

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255))
    exchange: Mapped[str | None] = mapped_column(String(16), index=True)
    asset_class: Mapped[str] = mapped_column(String(16), default="equity")
    sector: Mapped[str | None] = mapped_column(String(64), index=True)
    industry: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(8))
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    listed_at: Mapped[date | None] = mapped_column(Date)
    delisted_at: Mapped[date | None] = mapped_column(Date)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UniverseMembership(Base):
    """Point-in-time index membership — kills survivorship bias."""

    __tablename__ = "universe_membership"
    __table_args__ = (
        UniqueConstraint("universe", "symbol", "effective_from", name="uq_universe_member"),
        Index("ix_universe_membership_lookup", "universe", "symbol", "effective_from"),
        {"schema": "market"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    universe: Mapped[str] = mapped_column(String(32), nullable=False)  # SP500, NDX100, R1000
    symbol: Mapped[str] = mapped_column(String(16), ForeignKey("market.tickers.symbol"), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)  # null = currently a member


class CorporateAction(Base):
    """Splits + dividends — used to adjust backtest prices."""

    __tablename__ = "corporate_actions"
    __table_args__ = (
        UniqueConstraint("symbol", "ex_date", "action_type", name="uq_corp_action"),
        Index("ix_corporate_actions_symbol_date", "symbol", "ex_date"),
        {"schema": "market"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), ForeignKey("market.tickers.symbol"))
    action_type: Mapped[str] = mapped_column(String(16), nullable=False)  # split, dividend
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    record_date: Mapped[date | None] = mapped_column(Date)
    pay_date: Mapped[date | None] = mapped_column(Date)
    ratio: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))  # for splits
    cash_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))  # for dividends
    currency: Mapped[str] = mapped_column(String(8), default="USD")


# ================================================================
# OHLCV — Timescale hypertables
# ================================================================
class OHLCVDaily(Base):
    """Daily bars. Hypertable on (date). Split-adjusted + dividend-adjusted."""

    __tablename__ = "ohlcv_daily"

    date: Mapped[date] = mapped_column(Date, primary_key=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), primary_key=True, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    adj_close: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    trade_count: Mapped[int | None] = mapped_column(BigInteger)
    source: Mapped[str] = mapped_column(String(32), default="polygon", nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("high >= low", name="high_gte_low"),
        CheckConstraint("volume >= 0", name="volume_nonneg"),
        Index("ix_ohlcv_daily_symbol_date", "symbol", "date"),
    )


class OHLCV1Min(Base):
    """1-minute bars. Hypertable on (ts)."""

    __tablename__ = "ohlcv_1m"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), primary_key=True, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    trade_count: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(32), default="alpaca", nullable=False)

    __table_args__ = (Index("ix_ohlcv_1m_symbol_ts", "symbol", "ts"),)


# ================================================================
# FEATURES — engineered, hypertable
# ================================================================
class Feature(Base):
    """
    Wide feature row per (date, symbol). JSONB for forward-compat —
    new features land without migrations. Hypertable on (date).
    """

    __tablename__ = "features_daily"
    __table_args__ = (
        Index("ix_features_daily_symbol_date", "symbol", "date"),
        {"schema": "feature"},
    )

    date: Mapped[date] = mapped_column(Date, primary_key=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), primary_key=True, nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(32), primary_key=True, nullable=False)

    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # e.g. {"ret_1d": 0.012, "rsi_14": 58.2, "sentiment_news_1d": 0.34, ...}

    point_in_time_safe: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ================================================================
# MODEL REGISTRY (mirrors MLflow — MLflow is authoritative)
# ================================================================
class ModelRun(Base):
    """Every trained model gets a row here + full artifacts in MLflow/MinIO."""

    __tablename__ = "model_runs"
    __table_args__ = {"schema": "model"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mlflow_run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g. "ts_xgb_AAPL"
    family: Mapped[str] = mapped_column(String(32), nullable=False)  # ts | cs | regime | meta
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    feature_set_version: Mapped[str] = mapped_column(String(32), nullable=False)
    symbols: Mapped[list[Any]] = mapped_column(JSONB, default=list)  # which symbols trained
    train_start: Mapped[date] = mapped_column(Date, nullable=False)
    train_end: Mapped[date] = mapped_column(Date, nullable=False)
    cv_scheme: Mapped[str] = mapped_column(String(64), nullable=False)  # purged_kfold, walk_forward
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    hyperparams: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ================================================================
# SIGNALS — hypertable on (date)
# ================================================================
class SignalDirection(enum.StrEnum):
    buy = "BUY"
    hold = "HOLD"
    sell = "SELL"


class Signal(Base):
    """
    Model output. One row per (date, symbol, model_run).
    SHAP attributions stored inline (JSONB) for UI consumption.
    """

    __tablename__ = "signals"
    __table_args__ = (
        Index("ix_signals_symbol_date", "symbol", "date"),
        Index("ix_signals_date_direction", "date", "direction"),
        {"schema": "signal"},
    )

    date: Mapped[date] = mapped_column(Date, primary_key=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), primary_key=True, nullable=False)
    model_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model.model_runs.id"), primary_key=True, nullable=False
    )

    direction: Mapped[SignalDirection] = mapped_column(
        SAEnum(SignalDirection, name="signal_direction"), nullable=False
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)  # 0..1
    score: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)  # raw ensemble score
    rank_in_universe: Mapped[int | None] = mapped_column(Integer)

    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    target_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    stop_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    horizon_days: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    shap_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # {"rsi_14": -0.12, ...}
    risk_level: Mapped[str | None] = mapped_column(String(16))  # LOW / MEDIUM / HIGH
    explanation: Mapped[str | None] = mapped_column(Text)  # Groq-generated plain-english

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ================================================================
# PORTFOLIO
# ================================================================
class OrderSide(enum.StrEnum):
    buy = "BUY"
    sell = "SELL"


class OrderStatus(enum.StrEnum):
    pending = "PENDING"
    submitted = "SUBMITTED"
    partial = "PARTIAL"
    filled = "FILLED"
    cancelled = "CANCELLED"
    rejected = "REJECTED"
    expired = "EXPIRED"


class Position(Base):
    """Currently-open positions (closed positions go to trades.closed_at)."""

    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_positions_user_symbol"),
        Index("ix_positions_user", "user_id"),
        {"schema": "portfolio"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE")
    )
    symbol: Mapped[str] = mapped_column(String(16), ForeignKey("market.tickers.symbol"))
    side: Mapped[OrderSide] = mapped_column(SAEnum(OrderSide, name="order_side"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    avg_entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)

    last_mark_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    last_mark_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))

    opening_signal_id: Mapped[str | None] = mapped_column(String(128))
    broker_position_id: Mapped[str | None] = mapped_column(String(128))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Trade(Base):
    """Full audit trail — every fill (both legs of a round trip)."""

    __tablename__ = "trades"
    __table_args__ = (
        Index("ix_trades_user_date", "user_id", "trade_date"),
        Index("ix_trades_symbol_date", "symbol", "trade_date"),
        {"schema": "portfolio"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE")
    )
    symbol: Mapped[str] = mapped_column(String(16), ForeignKey("market.tickers.symbol"))
    side: Mapped[OrderSide] = mapped_column(SAEnum(OrderSide, name="order_side"))
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status"), default=OrderStatus.pending
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    filled_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), default=Decimal("0"))
    limit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    fill_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    fees: Mapped[Decimal] = mapped_column(Numeric(20, 6), default=Decimal("0"))
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))

    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    signal_id_ref: Mapped[str | None] = mapped_column(String(128))  # date|symbol|model_run
    broker_order_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    client_order_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Snapshot(Base):
    """Daily end-of-day portfolio snapshot (hypertable on date)."""

    __tablename__ = "snapshots"
    __table_args__ = (
        Index("ix_snapshots_user_date", "user_id", "date"),
        {"schema": "portfolio"},
    )

    date: Mapped[date] = mapped_column(Date, primary_key=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    cash: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    positions_value: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    total_equity: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    realized_pnl_cum: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    num_positions: Mapped[int] = mapped_column(Integer, default=0)
    gross_exposure: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    net_exposure: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ================================================================
# NEWS + SENTIMENT
# ================================================================
class NewsArticle(Base):
    """News articles with LLM-scored sentiment (Groq)."""

    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(64), nullable=False)  # polygon, marketaux, newsapi, finnhub
    provider_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbols: Mapped[list[Any]] = mapped_column(JSONB, default=list)

    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))  # -1..1
    sentiment_label: Mapped[str | None] = mapped_column(String(16))  # bearish/neutral/bullish
    sentiment_model: Mapped[str | None] = mapped_column(String(64))
    sentiment_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("source", "provider_id", name="uq_news_source_providerid"),
        Index("ix_articles_published", "published_at"),
        Index("ix_articles_symbols", "symbols", postgresql_using="gin"),
        {"schema": "news"},
    )


# ================================================================
# MACRO (FRED) — hypertable on (date)
# ================================================================
class MacroSeries(Base):
    """FRED metadata per series."""

    __tablename__ = "series"
    __table_args__ = {"schema": "macro"}

    series_id: Mapped[str] = mapped_column(String(32), primary_key=True)  # VIXCLS, DGS10, ...
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    units: Mapped[str | None] = mapped_column(String(64))
    frequency: Mapped[str | None] = mapped_column(String(16))
    category: Mapped[str | None] = mapped_column(String(64))
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MacroObservation(Base):
    """FRED observations. Hypertable on (date)."""

    __tablename__ = "observations"
    __table_args__ = (
        Index("ix_macro_obs_series_date", "series_id", "date"),
        {"schema": "macro"},
    )

    date: Mapped[date] = mapped_column(Date, primary_key=True, nullable=False)
    series_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("macro.series.series_id"), primary_key=True, nullable=False
    )
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ================================================================
# Exports
# ================================================================
__all__ = [
    "CorporateAction",
    "Feature",
    "MacroObservation",
    "MacroSeries",
    "ModelRun",
    "NewsArticle",
    "OHLCV1Min",
    "OHLCVDaily",
    "OrderSide",
    "OrderStatus",
    "Position",
    "RefreshToken",
    "Signal",
    "SignalDirection",
    "Snapshot",
    "Ticker",
    "Trade",
    "UniverseMembership",
    "User",
    "UserRole",
    "UserTier",
]

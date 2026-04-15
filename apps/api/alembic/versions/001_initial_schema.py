"""initial schema — auth, market, feature, model, signal, portfolio, news, macro (+ Timescale hypertables).

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-04-15

Schemas are pre-created by `infra/postgres/init.sql`, but we idempotently
re-create them here so running migrations against a fresh DB (e.g. in CI)
still works without the init script.

Hypertables (OHLCV daily/1m, features_daily, signals, snapshots, macro.observations)
are promoted via raw SQL because Alembic's autogenerate has no concept of them.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
SCHEMAS = ("auth", "market", "feature", "model", "signal", "portfolio", "news", "macro")

USER_ROLE = sa.Enum("viewer", "trader", "admin", name="user_role")
USER_TIER = sa.Enum("free", "pro", "premium", name="user_tier")
SIGNAL_DIRECTION = sa.Enum("BUY", "HOLD", "SELL", name="signal_direction")
ORDER_SIDE = sa.Enum("BUY", "SELL", name="order_side")
ORDER_STATUS = sa.Enum(
    "PENDING",
    "SUBMITTED",
    "PARTIAL",
    "FILLED",
    "CANCELLED",
    "REJECTED",
    "EXPIRED",
    name="order_status",
)


def upgrade() -> None:
    conn = op.get_bind()

    # --- extensions + schemas (idempotent) -------------------------
    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
    conn.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    for s in SCHEMAS:
        conn.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {s}"))

    # --- enums -----------------------------------------------------
    USER_ROLE.create(conn, checkfirst=True)
    USER_TIER.create(conn, checkfirst=True)
    SIGNAL_DIRECTION.create(conn, checkfirst=True)
    ORDER_SIDE.create(conn, checkfirst=True)
    ORDER_STATUS.create(conn, checkfirst=True)

    # =============================================================
    # AUTH
    # =============================================================
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("role", USER_ROLE, nullable=False, server_default="viewer"),
        sa.Column("tier", USER_TIER, nullable=False, server_default="free"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("alpaca_key_id", sa.String(255)),
        sa.Column("alpaca_secret_ciphertext", sa.Text),
        sa.Column("alpaca_paper", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="auth",
    )
    op.create_index("ix_auth_users_email", "users", ["email"], unique=True, schema="auth")

    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="auth",
    )
    op.create_index("ix_auth_refresh_tokens_user_id", "refresh_tokens", ["user_id"], schema="auth")
    op.create_index(
        "ix_auth_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True, schema="auth"
    )

    # =============================================================
    # MARKET
    # =============================================================
    op.create_table(
        "tickers",
        sa.Column("symbol", sa.String(16), primary_key=True),
        sa.Column("name", sa.String(255)),
        sa.Column("exchange", sa.String(16)),
        sa.Column("asset_class", sa.String(16), nullable=False, server_default="equity"),
        sa.Column("sector", sa.String(64)),
        sa.Column("industry", sa.String(128)),
        sa.Column("country", sa.String(8)),
        sa.Column("currency", sa.String(8), nullable=False, server_default="USD"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("listed_at", sa.Date),
        sa.Column("delisted_at", sa.Date),
        sa.Column("metadata", postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="market",
    )
    op.create_index("ix_market_tickers_exchange", "tickers", ["exchange"], schema="market")
    op.create_index("ix_market_tickers_sector", "tickers", ["sector"], schema="market")

    op.create_table(
        "universe_membership",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("universe", sa.String(32), nullable=False),
        sa.Column("symbol", sa.String(16), sa.ForeignKey("market.tickers.symbol"), nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date),
        sa.UniqueConstraint("universe", "symbol", "effective_from", name="uq_universe_member"),
        schema="market",
    )
    op.create_index(
        "ix_universe_membership_lookup",
        "universe_membership",
        ["universe", "symbol", "effective_from"],
        schema="market",
    )

    op.create_table(
        "corporate_actions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(16), sa.ForeignKey("market.tickers.symbol")),
        sa.Column("action_type", sa.String(16), nullable=False),
        sa.Column("ex_date", sa.Date, nullable=False),
        sa.Column("record_date", sa.Date),
        sa.Column("pay_date", sa.Date),
        sa.Column("ratio", sa.Numeric(20, 10)),
        sa.Column("cash_amount", sa.Numeric(20, 10)),
        sa.Column("currency", sa.String(8), nullable=False, server_default="USD"),
        sa.UniqueConstraint("symbol", "ex_date", "action_type", name="uq_corp_action"),
        schema="market",
    )
    op.create_index(
        "ix_corporate_actions_symbol_date", "corporate_actions", ["symbol", "ex_date"], schema="market"
    )

    # =============================================================
    # OHLCV (public schema — will become hypertables)
    # =============================================================
    op.create_table(
        "ohlcv_daily",
        sa.Column("date", sa.Date, primary_key=True, nullable=False),
        sa.Column("symbol", sa.String(16), primary_key=True, nullable=False),
        sa.Column("open", sa.Numeric(20, 6), nullable=False),
        sa.Column("high", sa.Numeric(20, 6), nullable=False),
        sa.Column("low", sa.Numeric(20, 6), nullable=False),
        sa.Column("close", sa.Numeric(20, 6), nullable=False),
        sa.Column("adj_close", sa.Numeric(20, 6), nullable=False),
        sa.Column("volume", sa.BigInteger, nullable=False),
        sa.Column("vwap", sa.Numeric(20, 6)),
        sa.Column("trade_count", sa.BigInteger),
        sa.Column("source", sa.String(32), nullable=False, server_default="polygon"),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("high >= low", name="high_gte_low"),
        sa.CheckConstraint("volume >= 0", name="volume_nonneg"),
    )
    op.create_index("ix_ohlcv_daily_symbol_date", "ohlcv_daily", ["symbol", "date"])

    op.create_table(
        "ohlcv_1m",
        sa.Column("ts", sa.DateTime(timezone=True), primary_key=True, nullable=False),
        sa.Column("symbol", sa.String(16), primary_key=True, nullable=False),
        sa.Column("open", sa.Numeric(20, 6), nullable=False),
        sa.Column("high", sa.Numeric(20, 6), nullable=False),
        sa.Column("low", sa.Numeric(20, 6), nullable=False),
        sa.Column("close", sa.Numeric(20, 6), nullable=False),
        sa.Column("volume", sa.BigInteger, nullable=False),
        sa.Column("vwap", sa.Numeric(20, 6)),
        sa.Column("trade_count", sa.Integer),
        sa.Column("source", sa.String(32), nullable=False, server_default="alpaca"),
    )
    op.create_index("ix_ohlcv_1m_symbol_ts", "ohlcv_1m", ["symbol", "ts"])

    # =============================================================
    # FEATURES
    # =============================================================
    op.create_table(
        "features_daily",
        sa.Column("date", sa.Date, primary_key=True, nullable=False),
        sa.Column("symbol", sa.String(16), primary_key=True, nullable=False),
        sa.Column("feature_set_version", sa.String(32), primary_key=True, nullable=False),
        sa.Column("features", postgresql.JSONB, nullable=False),
        sa.Column("point_in_time_safe", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="feature",
    )
    op.create_index("ix_features_daily_symbol_date", "features_daily", ["symbol", "date"], schema="feature")

    # =============================================================
    # MODEL REGISTRY
    # =============================================================
    op.create_table(
        "model_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("mlflow_run_id", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("family", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("feature_set_version", sa.String(32), nullable=False),
        sa.Column("symbols", postgresql.JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("train_start", sa.Date, nullable=False),
        sa.Column("train_end", sa.Date, nullable=False),
        sa.Column("cv_scheme", sa.String(64), nullable=False),
        sa.Column("metrics", postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("hyperparams", postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="model",
    )
    op.create_index(
        "ix_model_model_runs_mlflow_run_id", "model_runs", ["mlflow_run_id"], unique=True, schema="model"
    )

    # =============================================================
    # SIGNALS
    # =============================================================
    op.create_table(
        "signals",
        sa.Column("date", sa.Date, primary_key=True, nullable=False),
        sa.Column("symbol", sa.String(16), primary_key=True, nullable=False),
        sa.Column(
            "model_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model.model_runs.id"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("direction", SIGNAL_DIRECTION, nullable=False),
        sa.Column("confidence", sa.Numeric(6, 5), nullable=False),
        sa.Column("score", sa.Numeric(10, 6), nullable=False),
        sa.Column("rank_in_universe", sa.Integer),
        sa.Column("entry_price", sa.Numeric(20, 6)),
        sa.Column("target_price", sa.Numeric(20, 6)),
        sa.Column("stop_price", sa.Numeric(20, 6)),
        sa.Column("horizon_days", sa.Integer, nullable=False, server_default="5"),
        sa.Column("shap_values", postgresql.JSONB),
        sa.Column("risk_level", sa.String(16)),
        sa.Column("explanation", sa.Text),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="signal",
    )
    op.create_index("ix_signals_symbol_date", "signals", ["symbol", "date"], schema="signal")
    op.create_index("ix_signals_date_direction", "signals", ["date", "direction"], schema="signal")

    # =============================================================
    # PORTFOLIO
    # =============================================================
    op.create_table(
        "positions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(16), sa.ForeignKey("market.tickers.symbol")),
        sa.Column("side", ORDER_SIDE, nullable=False),
        sa.Column("quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("avg_entry_price", sa.Numeric(20, 6), nullable=False),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column("last_mark_price", sa.Numeric(20, 6)),
        sa.Column("last_mark_at", sa.DateTime(timezone=True)),
        sa.Column("unrealized_pnl", sa.Numeric(20, 4), server_default="0"),
        sa.Column("opening_signal_id", sa.String(128)),
        sa.Column("broker_position_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "symbol", name="uq_positions_user_symbol"),
        schema="portfolio",
    )
    op.create_index("ix_positions_user", "positions", ["user_id"], schema="portfolio")

    op.create_table(
        "trades",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(16), sa.ForeignKey("market.tickers.symbol")),
        sa.Column("side", ORDER_SIDE, nullable=False),
        sa.Column("status", ORDER_STATUS, nullable=False, server_default="PENDING"),
        sa.Column("quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("filled_quantity", sa.Numeric(20, 6), server_default="0"),
        sa.Column("limit_price", sa.Numeric(20, 6)),
        sa.Column("fill_price", sa.Numeric(20, 6)),
        sa.Column("fees", sa.Numeric(20, 6), server_default="0"),
        sa.Column("realized_pnl", sa.Numeric(20, 4), server_default="0"),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("filled_at", sa.DateTime(timezone=True)),
        sa.Column("signal_id_ref", sa.String(128)),
        sa.Column("broker_order_id", sa.String(128), unique=True),
        sa.Column("client_order_id", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="portfolio",
    )
    op.create_index("ix_trades_user_date", "trades", ["user_id", "trade_date"], schema="portfolio")
    op.create_index("ix_trades_symbol_date", "trades", ["symbol", "trade_date"], schema="portfolio")
    op.create_index("ix_portfolio_trades_trade_date", "trades", ["trade_date"], schema="portfolio")

    op.create_table(
        "snapshots",
        sa.Column("date", sa.Date, primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("cash", sa.Numeric(20, 4), nullable=False),
        sa.Column("positions_value", sa.Numeric(20, 4), nullable=False),
        sa.Column("total_equity", sa.Numeric(20, 4), nullable=False),
        sa.Column("realized_pnl_cum", sa.Numeric(20, 4), server_default="0"),
        sa.Column("unrealized_pnl", sa.Numeric(20, 4), server_default="0"),
        sa.Column("num_positions", sa.Integer, server_default="0"),
        sa.Column("gross_exposure", sa.Numeric(20, 4), server_default="0"),
        sa.Column("net_exposure", sa.Numeric(20, 4), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="portfolio",
    )
    op.create_index("ix_snapshots_user_date", "snapshots", ["user_id", "date"], schema="portfolio")

    # =============================================================
    # NEWS
    # =============================================================
    op.create_table(
        "articles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("provider_id", sa.String(255), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbols", postgresql.JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("sentiment_score", sa.Numeric(5, 4)),
        sa.Column("sentiment_label", sa.String(16)),
        sa.Column("sentiment_model", sa.String(64)),
        sa.Column("sentiment_at", sa.DateTime(timezone=True)),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source", "provider_id", name="uq_news_source_providerid"),
        schema="news",
    )
    op.create_index("ix_articles_published", "articles", ["published_at"], schema="news")
    op.create_index("ix_articles_symbols", "articles", ["symbols"], postgresql_using="gin", schema="news")

    # =============================================================
    # MACRO
    # =============================================================
    op.create_table(
        "series",
        sa.Column("series_id", sa.String(32), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("units", sa.String(64)),
        sa.Column("frequency", sa.String(16)),
        sa.Column("category", sa.String(64)),
        sa.Column("last_updated", sa.DateTime(timezone=True)),
        schema="macro",
    )

    op.create_table(
        "observations",
        sa.Column("date", sa.Date, primary_key=True, nullable=False),
        sa.Column(
            "series_id",
            sa.String(32),
            sa.ForeignKey("macro.series.series_id"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("value", sa.Numeric(20, 6)),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="macro",
    )
    op.create_index("ix_macro_obs_series_date", "observations", ["series_id", "date"], schema="macro")

    # =============================================================
    # TIMESCALE HYPERTABLES (raw SQL — Alembic doesn't know about them)
    # create_hypertable(table, time_column, migrate_data => true)
    # =============================================================
    hypertables = [
        ("public.ohlcv_daily", "date", "7 days"),
        ("public.ohlcv_1m", "ts", "1 day"),
        ("feature.features_daily", "date", "30 days"),
        ("signal.signals", "date", "30 days"),
        ("portfolio.snapshots", "date", "30 days"),
        ("macro.observations", "date", "365 days"),
    ]
    for table, time_col, chunk in hypertables:
        conn.execute(
            sa.text(
                f"SELECT create_hypertable('{table}', '{time_col}', "
                f"chunk_time_interval => INTERVAL '{chunk}', "
                f"if_not_exists => TRUE, migrate_data => TRUE)"
            )
        )


def downgrade() -> None:
    """Drop everything. Timescale hypertables drop with their underlying tables."""
    conn = op.get_bind()

    # Drop in reverse-dependency order
    op.drop_index("ix_macro_obs_series_date", table_name="observations", schema="macro")
    op.drop_table("observations", schema="macro")
    op.drop_table("series", schema="macro")

    op.drop_index("ix_articles_symbols", table_name="articles", schema="news")
    op.drop_index("ix_articles_published", table_name="articles", schema="news")
    op.drop_table("articles", schema="news")

    op.drop_index("ix_snapshots_user_date", table_name="snapshots", schema="portfolio")
    op.drop_table("snapshots", schema="portfolio")

    op.drop_index("ix_portfolio_trades_trade_date", table_name="trades", schema="portfolio")
    op.drop_index("ix_trades_symbol_date", table_name="trades", schema="portfolio")
    op.drop_index("ix_trades_user_date", table_name="trades", schema="portfolio")
    op.drop_table("trades", schema="portfolio")

    op.drop_index("ix_positions_user", table_name="positions", schema="portfolio")
    op.drop_table("positions", schema="portfolio")

    op.drop_index("ix_signals_date_direction", table_name="signals", schema="signal")
    op.drop_index("ix_signals_symbol_date", table_name="signals", schema="signal")
    op.drop_table("signals", schema="signal")

    op.drop_index("ix_model_model_runs_mlflow_run_id", table_name="model_runs", schema="model")
    op.drop_table("model_runs", schema="model")

    op.drop_index("ix_features_daily_symbol_date", table_name="features_daily", schema="feature")
    op.drop_table("features_daily", schema="feature")

    op.drop_index("ix_ohlcv_1m_symbol_ts", table_name="ohlcv_1m")
    op.drop_table("ohlcv_1m")
    op.drop_index("ix_ohlcv_daily_symbol_date", table_name="ohlcv_daily")
    op.drop_table("ohlcv_daily")

    op.drop_index("ix_corporate_actions_symbol_date", table_name="corporate_actions", schema="market")
    op.drop_table("corporate_actions", schema="market")
    op.drop_index("ix_universe_membership_lookup", table_name="universe_membership", schema="market")
    op.drop_table("universe_membership", schema="market")
    op.drop_index("ix_market_tickers_sector", table_name="tickers", schema="market")
    op.drop_index("ix_market_tickers_exchange", table_name="tickers", schema="market")
    op.drop_table("tickers", schema="market")

    op.drop_index("ix_auth_refresh_tokens_token_hash", table_name="refresh_tokens", schema="auth")
    op.drop_index("ix_auth_refresh_tokens_user_id", table_name="refresh_tokens", schema="auth")
    op.drop_table("refresh_tokens", schema="auth")
    op.drop_index("ix_auth_users_email", table_name="users", schema="auth")
    op.drop_table("users", schema="auth")

    ORDER_STATUS.drop(conn, checkfirst=True)
    ORDER_SIDE.drop(conn, checkfirst=True)
    SIGNAL_DIRECTION.drop(conn, checkfirst=True)
    USER_TIER.drop(conn, checkfirst=True)
    USER_ROLE.drop(conn, checkfirst=True)

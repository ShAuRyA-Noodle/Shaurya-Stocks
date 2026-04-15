"""
Admin endpoints — kill switch, ops, user management.

All routes require `UserRole.admin`. No destructive operation is allowed
without an explicit request body confirming the intent.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from quant.config import settings
from quant.core.dependencies import get_current_admin, get_db
from quant.db.models import Snapshot, Trade, User
from quant.monitoring.metrics import KILL_SWITCH_STATE
from quant.risk.manager import KILL_SWITCH_KEY

router = APIRouter(prefix="/admin", tags=["admin"])


class KillSwitchIn(BaseModel):
    engaged: bool
    reason: str = Field(min_length=3, max_length=500)


class KillSwitchOut(BaseModel):
    engaged: bool
    reason: str | None
    updated_at: datetime | None


class OpsSummaryOut(BaseModel):
    users: int
    open_orders: int
    filled_today: int
    last_snapshot_at: datetime | None
    kill_switch_engaged: bool


async def _redis() -> Redis:
    return Redis.from_url(settings.redis_url)


@router.get("/kill-switch", response_model=KillSwitchOut)
async def get_kill_switch(
    _admin: User = Depends(get_current_admin),
    r: Redis = Depends(_redis),
) -> KillSwitchOut:
    try:
        v = await r.get(KILL_SWITCH_KEY)
        reason = await r.get(f"{KILL_SWITCH_KEY}:reason")
        updated = await r.get(f"{KILL_SWITCH_KEY}:at")
        engaged = bool(v) and v.decode() in ("1", "true", "on")
        KILL_SWITCH_STATE.set(1 if engaged else 0)
        return KillSwitchOut(
            engaged=engaged,
            reason=reason.decode() if reason else None,
            updated_at=datetime.fromisoformat(updated.decode()) if updated else None,
        )
    finally:
        await r.close()


@router.post("/kill-switch", response_model=KillSwitchOut)
async def set_kill_switch(
    payload: KillSwitchIn,
    admin: User = Depends(get_current_admin),
    r: Redis = Depends(_redis),
) -> KillSwitchOut:
    try:
        now = datetime.now(UTC).isoformat()
        if payload.engaged:
            await r.set(KILL_SWITCH_KEY, "1")
        else:
            await r.delete(KILL_SWITCH_KEY)
        await r.set(f"{KILL_SWITCH_KEY}:reason", f"{payload.reason} (by {admin.email})")
        await r.set(f"{KILL_SWITCH_KEY}:at", now)
        KILL_SWITCH_STATE.set(1 if payload.engaged else 0)
        return KillSwitchOut(
            engaged=payload.engaged,
            reason=f"{payload.reason} (by {admin.email})",
            updated_at=datetime.fromisoformat(now),
        )
    finally:
        await r.close()


@router.get("/ops/summary", response_model=OpsSummaryOut)
async def ops_summary(
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    r: Redis = Depends(_redis),
) -> OpsSummaryOut:
    from quant.db.models import OrderStatus

    try:
        users = int((await db.execute(select(func.count()).select_from(User))).scalar() or 0)
        open_orders = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(Trade)
                    .where(Trade.status.in_((OrderStatus.pending, OrderStatus.submitted)))
                )
            ).scalar()
            or 0
        )
        today = datetime.now(UTC).date()
        filled_today = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(Trade)
                    .where(Trade.status == OrderStatus.filled, Trade.trade_date == today)
                )
            ).scalar()
            or 0
        )
        last_snap_at = (await db.execute(select(func.max(Snapshot.created_at)))).scalar_one_or_none()

        v = await r.get(KILL_SWITCH_KEY)
        engaged = bool(v) and v.decode() in ("1", "true", "on")
        return OpsSummaryOut(
            users=users,
            open_orders=open_orders,
            filled_today=filled_today,
            last_snapshot_at=last_snap_at,
            kill_switch_engaged=engaged,
        )
    finally:
        await r.close()


@router.post("/users/{user_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: str,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    import uuid

    try:
        uid = uuid.UUID(user_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "bad user id") from e
    u = await db.get(User, uid)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    u.is_active = False
    await db.commit()

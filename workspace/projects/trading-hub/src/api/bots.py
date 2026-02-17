"""
Trading Hub — 봇 관리 라우터

POST /api/bots        — 봇 등록
GET  /api/bots        — 봇 목록
GET  /api/bots/{id}   — 봇 상세
PATCH /api/bots/{id}/start — 봇 시작
PATCH /api/bots/{id}/stop  — 봇 중지
GET  /api/bots/{id}/status — 봇 상태 조회
DELETE /api/bots/{id} — 봇 삭제
"""

import json
import logging
from typing import List

from fastapi import APIRouter, HTTPException

from src.api.security import encrypt_value  # @risk: encryption
from src.db import database as db
from src.models.base_bot import bot_manager
from src.models.sim_bot import SimBot
from src.shared.types import (
    BotConfig,
    BotCreateRequest,
    BotResponse,
    BotStatus,
    BotStatusResponse,
    ExchangeType,
    OkResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bots", tags=["bots"])


# ──────────────────────────────────────────────
# 헬퍼: DB row → BotResponse
# ──────────────────────────────────────────────

def _db_row_to_response(row: dict) -> BotResponse:
    """DB row dict를 BotResponse로 변환."""
    config_data = row.get("config", "{}")
    if isinstance(config_data, str):
        config_data = json.loads(config_data)

    return BotResponse(
        id=row["id"],
        name=row["name"],
        exchange=ExchangeType(row["exchange"]),
        type=row["type"],
        status=BotStatus(row["status"]),
        config=BotConfig(**config_data),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# ──────────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────────

@router.post("", response_model=BotResponse, status_code=201)
async def create_bot(request: BotCreateRequest) -> BotResponse:
    """봇을 등록한다."""
    # 입력 검증
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="봇 이름은 비어 있을 수 없습니다.")

    # API 키 암호화 (있는 경우)
    # @risk: encryption
    api_key_enc = None
    api_secret_enc = None
    if request.api_key:
        api_key_enc = encrypt_value(request.api_key)
    if request.api_secret:
        api_secret_enc = encrypt_value(request.api_secret)

    row = await db.create_bot(
        name=request.name.strip(),
        exchange=request.exchange.value,
        bot_type=request.type,
        config=request.config.model_dump(),
        api_key_encrypted=api_key_enc,
        api_secret_encrypted=api_secret_enc,
    )

    bot_response = _db_row_to_response(row)

    # 시뮬레이션 봇이면 BotManager에 등록
    if request.exchange == ExchangeType.simulation:
        sim_bot = SimBot(
            bot_id=bot_response.id,
            name=bot_response.name,
            config=request.config,
        )
        bot_manager.register(sim_bot)

    logger.info("Bot created: %s (%d)", bot_response.name, bot_response.id)
    return bot_response


@router.get("", response_model=List[BotResponse])
async def list_bots() -> List[BotResponse]:
    """봇 목록을 조회한다."""
    rows = await db.get_bots()
    result = []
    for row in rows:
        resp = _db_row_to_response(row)
        # BotManager에 등록된 봇이면 실시간 상태 반영
        managed = bot_manager.get(resp.id)
        if managed:
            resp.status = managed.status
        result.append(resp)
    return result


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(bot_id: int) -> BotResponse:
    """봇 상세를 조회한다."""
    if bot_id <= 0:
        raise HTTPException(status_code=400, detail="유효하지 않은 봇 ID입니다.")

    row = await db.get_bot(bot_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"봇 {bot_id}을(를) 찾을 수 없습니다.")

    resp = _db_row_to_response(row)
    managed = bot_manager.get(bot_id)
    if managed:
        resp.status = managed.status
    return resp


@router.patch("/{bot_id}/start", response_model=BotResponse)
async def start_bot(bot_id: int) -> BotResponse:
    """봇을 시작한다."""
    if bot_id <= 0:
        raise HTTPException(status_code=400, detail="유효하지 않은 봇 ID입니다.")

    row = await db.get_bot(bot_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"봇 {bot_id}을(를) 찾을 수 없습니다.")

    # BotManager에 등록되지 않은 경우 등록 시도
    managed = bot_manager.get(bot_id)
    if managed is None:
        if row["exchange"] == ExchangeType.simulation.value:
            config_data = row.get("config", "{}")
            if isinstance(config_data, str):
                config_data = json.loads(config_data)
            sim_bot = SimBot(
                bot_id=bot_id,
                name=row["name"],
                config=BotConfig(**config_data),
            )
            bot_manager.register(sim_bot)
            managed = sim_bot
        else:
            raise HTTPException(
                status_code=400,
                detail=f"거래소 '{row['exchange']}' 봇은 아직 지원하지 않습니다. simulation만 가능합니다.",
            )

    if managed.status == BotStatus.running:
        raise HTTPException(status_code=400, detail="봇이 이미 실행 중입니다.")

    try:
        await bot_manager.start_bot(bot_id)
    except Exception as e:
        await db.update_bot_status(bot_id, BotStatus.error.value)
        raise HTTPException(status_code=500, detail=f"봇 시작 실패: {str(e)}")

    await db.update_bot_status(bot_id, BotStatus.running.value)
    updated = await db.get_bot(bot_id)
    resp = _db_row_to_response(updated)
    resp.status = BotStatus.running
    logger.info("Bot started: %s (%d)", resp.name, resp.id)
    return resp


@router.patch("/{bot_id}/stop", response_model=BotResponse)
async def stop_bot(bot_id: int) -> BotResponse:
    """봇을 중지한다."""
    if bot_id <= 0:
        raise HTTPException(status_code=400, detail="유효하지 않은 봇 ID입니다.")

    row = await db.get_bot(bot_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"봇 {bot_id}을(를) 찾을 수 없습니다.")

    managed = bot_manager.get(bot_id)
    if managed is None:
        raise HTTPException(status_code=400, detail="봇이 BotManager에 등록되어 있지 않습니다.")

    if managed.status not in (BotStatus.running, BotStatus.error):
        raise HTTPException(status_code=400, detail="봇이 실행 중이 아닙니다.")

    try:
        await bot_manager.stop_bot(bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"봇 중지 실패: {str(e)}")

    await db.update_bot_status(bot_id, BotStatus.stopped.value)
    updated = await db.get_bot(bot_id)
    resp = _db_row_to_response(updated)
    resp.status = BotStatus.stopped
    logger.info("Bot stopped: %s (%d)", resp.name, resp.id)
    return resp


@router.get("/{bot_id}/status", response_model=BotStatusResponse)
async def get_bot_status(bot_id: int) -> BotStatusResponse:
    """봇 상태를 상세 조회한다."""
    if bot_id <= 0:
        raise HTTPException(status_code=400, detail="유효하지 않은 봇 ID입니다.")

    row = await db.get_bot(bot_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"봇 {bot_id}을(를) 찾을 수 없습니다.")

    managed = bot_manager.get(bot_id)
    status = BotStatus(row["status"])
    uptime = None
    last_tick = None
    error_msg = None

    if managed:
        status = managed.status
        uptime = managed.uptime_seconds
        last_tick = managed.last_tick_at
        error_msg = managed.error_message

    return BotStatusResponse(
        id=row["id"],
        name=row["name"],
        status=status,
        exchange=ExchangeType(row["exchange"]),
        uptime_seconds=uptime,
        last_tick_at=last_tick,
        error_message=error_msg,
    )


@router.delete("/{bot_id}", response_model=OkResponse)
async def delete_bot(bot_id: int) -> OkResponse:
    """봇을 삭제한다. 실행 중이면 먼저 중지."""
    if bot_id <= 0:
        raise HTTPException(status_code=400, detail="유효하지 않은 봇 ID입니다.")

    row = await db.get_bot(bot_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"봇 {bot_id}을(를) 찾을 수 없습니다.")

    # 실행 중이면 중지
    managed = bot_manager.get(bot_id)
    if managed and managed.status == BotStatus.running:
        await bot_manager.stop_bot(bot_id)

    # BotManager에서 해제
    bot_manager.unregister(bot_id)

    # DB에서 삭제
    deleted = await db.delete_bot(bot_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="봇 삭제에 실패했습니다.")

    logger.info("Bot deleted: %d", bot_id)
    return OkResponse(message=f"봇 {bot_id}이(가) 삭제되었습니다.")

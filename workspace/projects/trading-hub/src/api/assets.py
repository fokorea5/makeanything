"""
Trading Hub — 자산 라우터

GET /api/assets         — 봇별 자산 목록
GET /api/assets/summary — 전체 자산 합산
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Query

from src.db import database as db
from src.shared.types import (
    AssetResponse,
    AssetSummaryResponse,
    BotAssetSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assets", tags=["assets"])


# ──────────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────────

@router.get("", response_model=List[AssetResponse])
async def list_assets(
    bot_id: Optional[int] = Query(default=None, description="봇 ID로 필터"),
) -> List[AssetResponse]:
    """봇별 자산 목록을 조회한다."""
    rows = await db.get_assets(bot_id=bot_id)
    result = []
    for row in rows:
        result.append(
            AssetResponse(
                id=row["id"],
                bot_id=row["bot_id"],
                bot_name=row.get("bot_name"),
                currency=row["currency"],
                balance=row["balance"],
                locked=row["locked"],
                value_usd=row["value_usd"],
                updated_at=row["updated_at"],
            )
        )
    return result


@router.get("/summary", response_model=AssetSummaryResponse)
async def get_summary() -> AssetSummaryResponse:
    """전체 자산 요약을 반환한다."""
    summary = await db.get_asset_summary()
    return AssetSummaryResponse(
        total_value_usd=summary["total_value_usd"],
        bot_count=summary["bot_count"],
        assets_by_currency=summary["assets_by_currency"],
        assets_by_bot=[
            BotAssetSummary(**bot_data)
            for bot_data in summary["assets_by_bot"]
        ],
    )

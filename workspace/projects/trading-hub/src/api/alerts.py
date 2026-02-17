"""
Trading Hub — 알림 라우터

POST /api/alerts/test — 테스트 알림 전송
GET  /api/alerts      — 알림 이력 조회
텔레그램 메시지 전송 함수 포함.
"""

import logging
import os
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, Query

from src.db import database as db
from src.shared.types import (
    AlertListResponse,
    AlertResponse,
    AlertTestRequest,
    AlertType,
    OkResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# ──────────────────────────────────────────────
# 텔레그램 메시지 전송 함수
# ──────────────────────────────────────────────

def send_telegram_message(message: str) -> bool:
    """
    텔레그램으로 메시지를 전송한다.

    환경변수:
        TELEGRAM_BOT_TOKEN: BotFather에서 발급받은 토큰
        TELEGRAM_CHAT_ID:   메시지를 보낼 채팅 ID

    Returns:
        True: 전송 성공, False: 전송 실패 또는 설정 누락
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        logger.warning(
            "텔레그램 설정 누락 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID). "
            "알림이 전송되지 않습니다."
        )
        return False

    # 메시지 길이 제한 (4096자)
    if len(message) > 4096:
        message = message[:4090] + "\n..."

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("텔레그램 알림 전송 성공")
            return True
        elif response.status_code == 429:
            # Rate Limit
            retry_after = response.json().get("parameters", {}).get("retry_after", 1)
            logger.warning("텔레그램 Rate Limit. %d초 후 재시도 필요.", retry_after)
            return False
        else:
            logger.error(
                "텔레그램 전송 실패: status=%d, body=%s",
                response.status_code,
                response.text[:200],
            )
            return False
    except requests.exceptions.Timeout:
        logger.error("텔레그램 전송 타임아웃 (10초)")
        return False
    except requests.exceptions.RequestException as e:
        logger.error("텔레그램 전송 오류: %s", e)
        return False


# ──────────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────────

@router.post("/test", response_model=OkResponse)
async def send_test_alert(request: AlertTestRequest) -> OkResponse:
    """테스트 알림을 전송한다."""
    message = f"[TEST] {request.message}"

    # DB에 알림 기록 저장
    alert_row = await db.create_alert(
        alert_type=AlertType.error.value,  # test는 error 타입으로 기록
        message=message,
        bot_id=None,
        sent=False,
    )

    # 텔레그램 전송 시도
    sent = send_telegram_message(message)

    if sent:
        await db.update_alert_sent(alert_row["id"], True)
        return OkResponse(message="테스트 알림이 텔레그램으로 전송되었습니다.")
    else:
        return OkResponse(
            message="알림이 DB에 기록되었으나 텔레그램 전송에 실패했습니다. "
                    "TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID 설정을 확인하세요."
        )


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    bot_id: Optional[int] = Query(default=None, description="봇 ID로 필터"),
    type: Optional[str] = Query(default=None, description="알림 유형 (error, large_trade, daily_profit)"),
    page: int = Query(default=1, ge=1, description="페이지 번호 (1-based)"),
    size: int = Query(default=20, ge=1, le=100, description="페이지 크기"),
) -> AlertListResponse:
    """알림 이력을 조회한다."""
    # type 검증
    valid_types = {"error", "large_trade", "daily_profit"}
    if type is not None and type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"유효하지 않은 알림 유형입니다. 가능한 값: {', '.join(valid_types)}",
        )

    result = await db.get_alerts(
        bot_id=bot_id,
        alert_type=type,
        page=page,
        size=size,
    )

    items = []
    for row in result["items"]:
        items.append(
            AlertResponse(
                id=row["id"],
                bot_id=row["bot_id"],
                type=AlertType(row["type"]),
                message=row["message"],
                sent=bool(row["sent"]),
                created_at=row["created_at"],
            )
        )

    return AlertListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"],
    )

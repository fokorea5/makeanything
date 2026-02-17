"""
Trading Hub — FastAPI 앱 진입점

- FastAPI 앱 생성
- 라우터 등록 (bots, assets, trades, alerts)
- static 파일 서빙 (src/pages/, src/styles/, static/)
- startup 이벤트에서 DB 초기화
- WebSocket 엔드포인트 (/ws/status)
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# .env 파일 로드
load_dotenv(PROJECT_ROOT / ".env")

from src.api import alerts, assets, bots, trades
from src.db import database as db
from src.models.base_bot import bot_manager
from src.shared.types import BotStatus, ExchangeType, WsBotStatus, WsStatusMessage

# ──────────────────────────────────────────────
# 로깅 설정
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# WebSocket 연결 관리
# ──────────────────────────────────────────────

class ConnectionManager:
    """WebSocket 연결 풀 관리."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connected. Active: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("WebSocket disconnected. Active: %d", len(self.active_connections))

    async def broadcast(self, message: str) -> None:
        """모든 연결에 메시지 전송. 끊어진 연결은 제거."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)


ws_manager = ConnectionManager()


# ──────────────────────────────────────────────
# WebSocket push 백그라운드 태스크
# ──────────────────────────────────────────────

async def ws_push_loop() -> None:
    """3초마다 모든 봇 상태를 WebSocket으로 push한다."""
    interval = int(os.environ.get("WS_PUSH_INTERVAL", "3"))
    while True:
        try:
            if ws_manager.active_connections:
                bots_list = bot_manager.get_all()
                bot_statuses = []
                for bot in bots_list:
                    bot_statuses.append(
                        WsBotStatus(
                            bot_id=bot.bot_id,
                            name=bot.name,
                            status=bot.status,
                            exchange=ExchangeType.simulation,
                            last_tick_at=bot.last_tick_at,
                            error_message=bot.error_message,
                        )
                    )

                msg = WsStatusMessage(
                    type="status_update",
                    timestamp=datetime.utcnow(),
                    bots=bot_statuses,
                )
                await ws_manager.broadcast(msg.model_dump_json())
        except Exception as e:
            logger.error("WebSocket push error: %s", e)

        await asyncio.sleep(interval)


# ──────────────────────────────────────────────
# 앱 생명주기
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 생명주기."""
    # Startup
    logger.info("Trading Hub starting...")
    await db.init_db()
    logger.info("DB initialized")

    # WebSocket push 백그라운드 태스크 시작
    push_task = asyncio.create_task(ws_push_loop())
    logger.info("WebSocket push loop started")

    yield

    # Shutdown
    logger.info("Trading Hub shutting down...")
    push_task.cancel()
    try:
        await push_task
    except asyncio.CancelledError:
        pass
    await bot_manager.stop_all()
    logger.info("All bots stopped. Goodbye.")


# ──────────────────────────────────────────────
# FastAPI 앱 생성
# ──────────────────────────────────────────────

app = FastAPI(
    title="Trading Hub",
    description="자동매매 봇 통합 관리 대시보드",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경. 운영 시 특정 도메인으로 제한.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# 라우터 등록
# ──────────────────────────────────────────────

app.include_router(bots.router)
app.include_router(assets.router)
app.include_router(trades.router)
app.include_router(alerts.router)


# ──────────────────────────────────────────────
# 정적 파일 서빙
# ──────────────────────────────────────────────

# src/pages/ — HTML 페이지
pages_dir = PROJECT_ROOT / "src" / "pages"
if pages_dir.exists():
    app.mount("/pages", StaticFiles(directory=str(pages_dir), html=True), name="pages")

# src/styles/ — CSS
styles_dir = PROJECT_ROOT / "src" / "styles"
if styles_dir.exists():
    app.mount("/styles", StaticFiles(directory=str(styles_dir)), name="styles")

# static/ — JS 등
static_dir = PROJECT_ROOT / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ──────────────────────────────────────────────
# 루트 리다이렉트
# ──────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    """루트 → 대시보드 리다이렉트."""
    dashboard_path = pages_dir / "dashboard.html"
    if dashboard_path.exists():
        return RedirectResponse(url="/pages/dashboard.html")
    return {"message": "Trading Hub API is running. Visit /docs for API documentation."}


# ──────────────────────────────────────────────
# WebSocket 엔드포인트
# ──────────────────────────────────────────────

@app.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """
    실시간 봇 상태 WebSocket 스트림.
    - 연결 시 즉시 현재 상태 전송
    - 3초 간격으로 전체 봇 상태 push (백그라운드 태스크)
    - 봇 상태 변경 시 즉시 push
    """
    await ws_manager.connect(websocket)
    try:
        # 연결 시 즉시 현재 상태 전송
        bots_list = bot_manager.get_all()
        bot_statuses = []
        for bot in bots_list:
            bot_statuses.append(
                WsBotStatus(
                    bot_id=bot.bot_id,
                    name=bot.name,
                    status=bot.status,
                    exchange=ExchangeType.simulation,
                    last_tick_at=bot.last_tick_at,
                    error_message=bot.error_message,
                )
            )

        msg = WsStatusMessage(
            type="status_update",
            timestamp=datetime.utcnow(),
            bots=bot_statuses,
        )
        await websocket.send_text(msg.model_dump_json())

        # 클라이언트 메시지 수신 대기 (연결 유지)
        while True:
            data = await websocket.receive_text()
            # 클라이언트에서 ping 등 수신 가능
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        ws_manager.disconnect(websocket)


# ──────────────────────────────────────────────
# 서버 실행
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    logger.info("Starting Trading Hub on %s:%d", host, port)
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )

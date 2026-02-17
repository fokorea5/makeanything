"""
Polymarket Reaper Bot v1.1 -- 메인 엔트리포인트 (DESIGN.md 3.6절).

asyncio.run(main())으로 시작.
Config 로드, 로깅 설정, engine.run() 호출.
"""

from __future__ import annotations

import sys
import os
import asyncio
import logging

# 프로젝트 루트를 sys.path에 추가 (config.py import용)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from config import Config  # noqa: E402
from src.core.engine import TradingEngine  # noqa: E402


def _setup_logging(config: Config) -> None:
    """구조화된 로깅을 설정한다 (AC-37).

    로그 형식: %(asctime)s [%(levelname)s] %(name)s: %(message)s
    LOG_LEVEL 환경변수로 레벨 설정.
    """
    log_level_str = getattr(config, "LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


async def main() -> None:
    """메인 비동기 함수."""
    # Config 로드 (AC-05)
    Config.load()
    config = Config

    # 로깅 설정 (AC-37)
    _setup_logging(config)

    logger = logging.getLogger("reaper.main")
    logger.info("=" * 60)
    logger.info("Polymarket Reaper Bot v1.1 Starting")
    logger.info("=" * 60)
    logger.info("DRY_RUN: %s", getattr(config, "DRY_RUN", True))
    logger.info("FREQUENCY_MODE: %s", getattr(config, "FREQUENCY_MODE", "AUTO"))
    logger.info("LOG_LEVEL: %s", getattr(config, "LOG_LEVEL", "INFO"))

    # Trading Engine 생성 및 실행
    engine = TradingEngine(config)

    try:
        await engine.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.critical("Fatal error: %s", e, exc_info=True)
        sys.exit(1)

    logger.info("Polymarket Reaper Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())

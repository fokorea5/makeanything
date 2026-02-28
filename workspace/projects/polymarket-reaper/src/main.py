"""
Polymarket Reaper Bot v1.1 -- 메인 엔트리포인트 (DESIGN.md 3.6절).

asyncio.run(main())으로 시작.
Config 로드, 로깅 설정, engine.run() 호출.

rich가 설치되어 있으면 시작부터 로그를 파일로 보내고
터미널에는 Rich 대시보드만 표시한다.
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


def _has_rich() -> bool:
    """rich 패키지가 설치되어 있는지 확인한다."""
    try:
        import rich  # noqa: F401
        return True
    except ImportError:
        return False


def _setup_logging(config: Config, to_file: bool = False) -> None:
    """구조화된 로깅을 설정한다 (AC-37).

    Args:
        config: Config 객체.
        to_file: True이면 로그를 파일로만 출력 (대시보드 모드).
    """
    log_level_str = getattr(config, "LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handlers: list[logging.Handler] = []

    if to_file:
        # 대시보드 모드: 로그를 파일로만
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "reaper.log")
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(fmt)
        handlers.append(file_handler)
    else:
        # 일반 모드: stdout
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(fmt)
        handlers.append(stream_handler)

    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True,
    )

    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def _print_splash(config: Config) -> None:
    """터미널에 스플래시 메시지를 표시한다 (대시보드 모드)."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        console = Console()
        dry_run = getattr(config, "DRY_RUN", True)
        mode = getattr(config, "FREQUENCY_MODE", "AUTO")
        mode_tag = "[bold red]LIVE[/bold red]" if not dry_run else "[bold yellow]DRY RUN[/bold yellow]"

        splash = Text.from_markup(
            f"[bold cyan]POLYMARKET REAPER v1.1[/bold cyan]  {mode_tag}\n\n"
            f"[dim]Mode: {mode}  |  Logs: logs/reaper.log[/dim]\n"
            f"[dim]Initializing engine...[/dim]"
        )
        console.print()
        console.print(Panel(splash, style="bright_blue", expand=True))
        console.print()
    except Exception:
        print("Polymarket Reaper Bot v1.1 -- Starting...")


async def main() -> None:
    """메인 비동기 함수."""
    # Config 로드 (AC-05)
    Config.load()
    config = Config

    # rich 설치 여부에 따라 로깅 설정
    dashboard_mode = _has_rich()

    # 로깅 설정 (AC-37)
    _setup_logging(config, to_file=dashboard_mode)

    logger = logging.getLogger("reaper.main")
    logger.info("=" * 60)
    logger.info("Polymarket Reaper Bot v1.1 Starting")
    logger.info("=" * 60)
    logger.info("DRY_RUN: %s", getattr(config, "DRY_RUN", True))
    logger.info("FREQUENCY_MODE: %s", getattr(config, "FREQUENCY_MODE", "AUTO"))
    logger.info("LOG_LEVEL: %s", getattr(config, "LOG_LEVEL", "INFO"))
    logger.info("Dashboard mode: %s", dashboard_mode)

    # 대시보드 모드이면 스플래시 표시
    if dashboard_mode:
        _print_splash(config)

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

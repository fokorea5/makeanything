"""
main.py — 엔트리포인트.
CLI 인자 파싱 → 설정 로드 → TradingEngine 시작.

사용법:
    python -m src.main              # 드라이런 (기본)
    python -m src.main --live       # 실거래
    python -m src.main --help       # 도움말
    python -m src.main --cycle-interval 60 --log-level DEBUG
"""

from __future__ import annotations

import argparse
import logging
import sys

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """CLI 인자 파싱."""
    parser = argparse.ArgumentParser(
        prog="polymarket-bot",
        description=(
            "Polymarket 자동매매 트레이딩 봇.\n"
            "6개 전략 (해결 기준 아비트라지, 오라클 공포, 군중 반대,\n"
            " 연관 시장 비효율, 유동성 진공 사냥, 메타봇) + 드라이런 모드."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="실거래 모드 활성화 (기본값: 드라이런). 주의: 실제 USDC를 사용합니다.",
    )
    parser.add_argument(
        "--cycle-interval",
        type=int,
        default=None,
        metavar="SECONDS",
        help="메인 루프 주기 (초). 기본값: 환경 변수 CYCLE_INTERVAL 또는 30.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        metavar="LEVEL",
        help="로그 레벨 (DEBUG/INFO/WARNING/ERROR). 기본값: INFO.",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        metavar="PATH",
        help="SQLite DB 파일 경로. 기본값: data/polymarket_bot.db.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="polymarket-bot 1.0.0",
    )

    return parser.parse_args()


def main() -> int:
    """
    메인 함수.
    반환값: 종료 코드 (0=성공, 1=오류).
    """
    args = parse_args()

    # Config 로드
    try:
        from src.config import Config
        config = Config.from_env()
    except Exception as exc:
        print(f"설정 로드 오류: {exc}", file=sys.stderr)
        return 1

    # CLI 인자로 설정 오버라이드
    if args.live:
        config.dry_run = False
    if args.cycle_interval is not None:
        config.cycle_interval = args.cycle_interval
    if args.log_level is not None:
        config.log_level = args.log_level
    if args.db_path is not None:
        config.db_path = args.db_path

    # 실거래 경고 확인
    if not config.dry_run:
        print(
            "\n[경고] 실거래 모드가 활성화되었습니다.\n"
            "        실제 USDC가 사용됩니다. 5초 후 시작합니다.\n"
            "        중단하려면 Ctrl+C를 누르세요.\n"
        )
        import time
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            print("사용자가 취소했습니다.")
            return 0

    # 엔진 시작
    try:
        from src.engine.trading_engine import TradingEngine
        engine = TradingEngine(config)
        engine.start()
        return 0
    except KeyboardInterrupt:
        print("\n사용자가 종료했습니다.")
        return 0
    except Exception as exc:
        logger.error("엔진 시작 오류: %s", exc, exc_info=True)
        print(f"엔진 오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

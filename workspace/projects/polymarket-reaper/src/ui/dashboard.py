"""
Polymarket Reaper Bot v1.1 -- Terminal Dashboard

Rich 기반 터미널 대시보드.
엔진의 8번째 비동기 태스크로 동작하며, 15초 주기로 갱신.

표시 정보:
  - 포트폴리오 요약 (잔고, 노출, DD, P&L)
  - 보유 포지션
  - 활성 시장 현황 (Target / Hit List)
  - 최근 시그널 & 거래
  - 시스템 상태 (Governor 모드, 큐 깊이, API 상태)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.layout import Layout
from rich.live import Live

logger = logging.getLogger("reaper.ui.dashboard")

# 갱신 주기 (초)
REFRESH_INTERVAL = 15


class TerminalDashboard:
    """Rich 기반 터미널 대시보드.

    TradingEngine에서 8번째 태스크로 실행된다.
    engine의 내부 상태를 읽기 전용으로 참조하여 표시한다.
    """

    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.console = Console()
        self._running = False

    async def run(self) -> None:
        """대시보드 메인 루프. REFRESH_INTERVAL 초마다 화면 갱신."""
        self._running = True
        logger.info("Terminal Dashboard started (refresh=%ds)", REFRESH_INTERVAL)

        # 엔진 초기화 대기
        await asyncio.sleep(5)

        while self._running and getattr(self.engine, "_running", False):
            try:
                await self._refresh_cached_data()
                self._render()
            except Exception as e:
                logger.debug("Dashboard render error: %s", e)

            try:
                await asyncio.sleep(REFRESH_INTERVAL)
            except asyncio.CancelledError:
                break

        logger.info("Terminal Dashboard stopped")

    def stop(self) -> None:
        self._running = False

    # ------------------------------------------------------------------
    # 렌더링
    # ------------------------------------------------------------------

    def _render(self) -> None:
        """전체 대시보드를 한 번 렌더링한다."""
        self.console.clear()

        # 헤더
        self.console.print(self._build_header())
        self.console.print()

        # 상단: 포트폴리오 + 시스템 상태
        top_panels = [
            self._build_portfolio_panel(),
            self._build_system_panel(),
        ]
        self.console.print(Columns(top_panels, equal=True, expand=True))
        self.console.print()

        # 중단: 포지션 테이블
        self.console.print(self._build_positions_table())
        self.console.print()

        # 하단: 시장 파이프라인 + 최근 거래
        bottom_panels = [
            self._build_pipeline_panel(),
            self._build_recent_trades_panel(),
        ]
        self.console.print(Columns(bottom_panels, equal=True, expand=True))

    # ------------------------------------------------------------------
    # 헤더
    # ------------------------------------------------------------------

    def _build_header(self) -> Panel:
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        dry_run = getattr(self.engine.config, "DRY_RUN", True)
        mode_tag = "[bold red]LIVE[/bold red]" if not dry_run else "[bold yellow]DRY RUN[/bold yellow]"
        title = Text.from_markup(
            f"[bold cyan]Polymarket Reaper Bot v1.1[/bold cyan]  {mode_tag}  |  {now}"
        )
        return Panel(title, style="bright_blue", expand=True)

    # ------------------------------------------------------------------
    # 포트폴리오 패널
    # ------------------------------------------------------------------

    def _build_portfolio_panel(self) -> Panel:
        tracker = self.engine.portfolio_tracker
        if tracker is None:
            return Panel("[dim]Portfolio tracker unavailable[/dim]", title="Portfolio")

        bankroll = tracker._bankroll
        if getattr(self.engine.config, "DRY_RUN", True) and bankroll <= 0:
            bankroll = 1000.0

        peak = tracker._peak_bankroll
        if getattr(self.engine.config, "DRY_RUN", True) and peak <= 0:
            peak = 1000.0

        dd = (peak - bankroll) / peak if peak > 0 else 0.0
        dd = max(0.0, min(1.0, dd))
        daily_pnl = tracker._daily_pnl

        # 노출 계산
        positions = list(tracker._virtual_positions.values()) if getattr(
            self.engine.config, "DRY_RUN", True
        ) else list(tracker._positions.values())
        total_exposure = sum(p.size * p.current_price for p in positions)
        unrealized_pnl = sum(p.unrealized_pnl for p in positions)

        # DD 색상
        if dd < 0.03:
            dd_color = "green"
        elif dd < 0.08:
            dd_color = "yellow"
        else:
            dd_color = "red"

        # P&L 색상
        pnl_color = "green" if daily_pnl >= 0 else "red"
        upnl_color = "green" if unrealized_pnl >= 0 else "red"

        exposure_pct = (total_exposure / bankroll * 100) if bankroll > 0 else 0.0

        lines = [
            f"[bold]Bankroll:[/bold]       ${bankroll:,.2f}",
            f"[bold]Peak:[/bold]           ${peak:,.2f}",
            f"[bold]Drawdown:[/bold]       [{dd_color}]{dd:.2%}[/{dd_color}]",
            f"[bold]Exposure:[/bold]       ${total_exposure:,.2f} ({exposure_pct:.1f}%)",
            f"[bold]Daily P&L:[/bold]      [{pnl_color}]${daily_pnl:+,.2f}[/{pnl_color}]",
            f"[bold]Unrealized:[/bold]     [{upnl_color}]${unrealized_pnl:+,.2f}[/{upnl_color}]",
            f"[bold]Positions:[/bold]      {len(positions)}",
        ]
        return Panel("\n".join(lines), title="[bold]Portfolio[/bold]", border_style="green")

    # ------------------------------------------------------------------
    # 시스템 상태 패널
    # ------------------------------------------------------------------

    def _build_system_panel(self) -> Panel:
        gov = self.engine.frequency_governor
        state = gov.get_state()

        mode_display = state.current_mode.value
        if state.current_mode.value == "AUTO":
            effective = gov.get_effective_mode_name()
            mode_display = f"AUTO ({effective})"

        # 모드별 색상
        mode_colors = {"TURBO": "red", "NORMAL": "green", "STEALTH": "blue", "AUTO": "yellow"}
        effective_name = gov.get_effective_mode_name()
        mode_color = mode_colors.get(effective_name, "white")

        queue_depth = self.engine.signal_queue.qsize()
        targets = len(self.engine._target_list)
        hits = len(self.engine._hit_list)

        lines = [
            f"[bold]Mode:[/bold]           [{mode_color}]{mode_display}[/{mode_color}]",
            f"[bold]Kelly x:[/bold]        {state.kelly_multiplier:.1f}",
            f"[bold]Stage1 Cycle:[/bold]   {state.stage1_interval:.0f}s",
            f"[bold]Stage2 Cycle:[/bold]   {state.stage2_interval:.0f}s",
            f"[bold]Signal Queue:[/bold]   {queue_depth}",
            f"[bold]Target List:[/bold]    {targets} markets",
            f"[bold]Hit List:[/bold]       {hits} markets",
        ]
        return Panel("\n".join(lines), title="[bold]System[/bold]", border_style="cyan")

    # ------------------------------------------------------------------
    # 포지션 테이블
    # ------------------------------------------------------------------

    def _build_positions_table(self) -> Panel:
        tracker = self.engine.portfolio_tracker
        if tracker is None:
            return Panel("[dim]No positions[/dim]", title="Positions")

        positions = list(tracker._virtual_positions.values()) if getattr(
            self.engine.config, "DRY_RUN", True
        ) else list(tracker._positions.values())

        table = Table(expand=True, show_lines=False, pad_edge=False)
        table.add_column("Market", style="white", max_width=45, no_wrap=True)
        table.add_column("Side", style="bold", justify="center", width=5)
        table.add_column("Size", justify="right", width=10)
        table.add_column("Entry", justify="right", width=8)
        table.add_column("Current", justify="right", width=8)
        table.add_column("P&L", justify="right", width=12)

        if not positions:
            table.add_row("[dim]No open positions[/dim]", "", "", "", "", "")
        else:
            # 미실현 P&L 크기순 정렬
            sorted_pos = sorted(positions, key=lambda p: abs(p.unrealized_pnl), reverse=True)
            for pos in sorted_pos[:10]:  # 최대 10개
                question = pos.market_question or pos.condition_id[:20]
                if len(question) > 42:
                    question = question[:42] + "..."

                side_str = f"[cyan]{pos.outcome}[/cyan]"
                pnl_color = "green" if pos.unrealized_pnl >= 0 else "red"
                pnl_str = f"[{pnl_color}]${pos.unrealized_pnl:+.2f}[/{pnl_color}]"

                table.add_row(
                    question,
                    side_str,
                    f"{pos.size:.2f}",
                    f"${pos.avg_price:.3f}",
                    f"${pos.current_price:.3f}",
                    pnl_str,
                )

            if len(positions) > 10:
                table.add_row(
                    f"[dim]... +{len(positions) - 10} more[/dim]",
                    "", "", "", "", "",
                )

        return Panel(table, title="[bold]Positions[/bold]", border_style="yellow")

    # ------------------------------------------------------------------
    # 파이프라인 패널 (시장 흐름)
    # ------------------------------------------------------------------

    def _build_pipeline_panel(self) -> Panel:
        cache = self.engine.market_cache
        total_markets = 0
        if cache is not None and hasattr(cache, "_markets"):
            total_markets = len(cache._markets)

        targets = len(self.engine._target_list)
        hits = len(self.engine._hit_list)

        # 전략 상태
        s1_count = len(self.engine._stage1_strategies)
        s2_count = len(self.engine._stage2_strategies)
        s3_count = len(self.engine._stage3_strategies)
        omega_on = (
            self.engine._omega_strategy is not None
            and self.engine._omega_strategy.enabled
        )

        lines = [
            "[bold]Pipeline:[/bold]",
            f"  All Markets:     {total_markets}",
            f"  -> Stage 1:      {targets} targets",
            f"  -> Stage 2:      {hits} hits",
            f"  -> Stage 3:      WS subscribed",
            "",
            "[bold]Strategies:[/bold]",
            f"  Stage 1:  {s1_count} active",
            f"  Stage 2:  {s2_count} active",
            f"  Stage 3:  {s3_count} active",
            f"  Omega:    {'[green]ON[/green]' if omega_on else '[red]OFF[/red]'}",
        ]
        return Panel("\n".join(lines), title="[bold]Market Pipeline[/bold]", border_style="magenta")

    # ------------------------------------------------------------------
    # 최근 거래 패널
    # ------------------------------------------------------------------

    def _build_recent_trades_panel(self) -> Panel:
        db = self.engine.db_manager
        if db is None:
            return Panel("[dim]DB unavailable[/dim]", title="Recent Trades")

        # DB에서 오늘 거래 가져오기 (동기적으로 캐시 참조)
        # 비동기 호출은 렌더 루프에서 하기 어려우므로,
        # 최근 거래는 _last_trades 캐시를 통해 표시
        trades = getattr(self, "_cached_trades", [])

        table = Table(expand=True, show_lines=False, pad_edge=False)
        table.add_column("Time", width=8)
        table.add_column("Market", max_width=25, no_wrap=True)
        table.add_column("Side", justify="center", width=5)
        table.add_column("Cost", justify="right", width=10)
        table.add_column("Status", justify="center", width=8)

        if not trades:
            table.add_row("[dim]No trades yet[/dim]", "", "", "", "")
        else:
            for t in trades[:8]:
                time_str = t.get("created_at", "")
                if isinstance(time_str, str) and len(time_str) > 8:
                    time_str = time_str[11:19]  # HH:MM:SS

                market = str(t.get("condition_id", ""))[:22]
                side = t.get("side", "")
                side_color = "green" if side == "BUY" else "red"
                cost = t.get("cost_usdc", 0.0)
                status = t.get("status", "")

                status_colors = {
                    "FILLED": "green",
                    "DRY_RUN": "yellow",
                    "REJECTED": "red",
                    "PARTIAL": "cyan",
                }
                status_color = status_colors.get(status, "white")

                table.add_row(
                    time_str,
                    market,
                    f"[{side_color}]{side}[/{side_color}]",
                    f"${cost:,.2f}" if isinstance(cost, (int, float)) else str(cost),
                    f"[{status_color}]{status}[/{status_color}]",
                )

        return Panel(table, title="[bold]Recent Trades[/bold]", border_style="blue")

    # ------------------------------------------------------------------
    # 비동기 데이터 갱신 (run 루프에서 호출)
    # ------------------------------------------------------------------

    async def _refresh_cached_data(self) -> None:
        """비동기 데이터를 캐시에 갱신한다."""
        db = self.engine.db_manager
        if db is not None:
            try:
                today = datetime.utcnow().strftime("%Y-%m-%d")
                trades = await db.get_trades_for_date(today)
                # 최신순 정렬
                if trades:
                    trades = sorted(
                        trades,
                        key=lambda t: t.get("created_at", ""),
                        reverse=True,
                    )
                self._cached_trades = trades or []
            except Exception:
                pass

"""實單/模擬盤執行器：抓最新資料 -> 跑策略 -> 透過 Broker 下單。

設計成「跑一次 = 掃一輪標的」，由外部排程器 (cron / APScheduler) 在盤中或收盤後觸發，
而不是在程式內 while True，方便控制與除錯。

安全預設：dry_run=True 只印出「會下什麼單」但不真的送出，確認無誤再關閉。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from ..broker.base import Broker, Order, OrderSide
from ..data.base import DataProvider
from ..models import Action, Position
from ..strategies.base import Strategy, StrategyContext

LOT = 1000


@dataclass
class TradePlan:
    symbol: str
    action: str
    shares: int
    price: float
    reason: str
    sent: bool = False


class LiveTrader:
    def __init__(
        self,
        provider: DataProvider,
        broker: Broker,
        strategy: Strategy,
        position_budget: float = 200_000.0,
        dry_run: bool = True,
        lookback_days: int = 400,
    ):
        self.provider = provider
        self.broker = broker
        self.strategy = strategy
        self.position_budget = position_budget
        self.dry_run = dry_run
        self.lookback_days = lookback_days

    def _current_position(self, symbol: str) -> Optional[Position]:
        for p in self.broker.positions():
            if p.symbol == symbol and p.shares > 0:
                return p
        return None

    def scan(self, symbols: List[str], end: str) -> List[TradePlan]:
        """掃描標的，回傳本輪要執行的交易計畫 (並視 dry_run 決定是否真的送單)。"""
        start = (pd.Timestamp(end) - pd.Timedelta(days=self.lookback_days * 2)).strftime("%Y-%m-%d")
        bench = self.provider.benchmark(start, end)
        plans: List[TradePlan] = []

        for sym in symbols:
            df = self.provider.history(sym, start, end)
            if df.empty:
                continue
            price = float(df["close"].iloc[-1])
            pos = self._current_position(sym)
            b = bench.reindex(df.index).ffill() if bench is not None else None
            ctx = StrategyContext(
                symbol=sym,
                prices=df,
                fundamentals=self.provider.fundamentals(sym),
                benchmark=b,
                position=pos,
            )
            sig = self.strategy.evaluate(ctx)
            if not sig.is_actionable:
                continue

            if sig.action == Action.BUY and pos is None:
                lots = int((self.position_budget * sig.strength) // (price * LOT))
                shares = lots * LOT
                if shares <= 0:
                    continue
                plan = TradePlan(sym, "BUY", shares, price, sig.reason)
            elif sig.action == Action.SELL and pos is not None:
                plan = TradePlan(sym, "SELL", pos.shares, price, sig.reason)
            else:
                continue

            if not self.dry_run:
                side = OrderSide.BUY if plan.action == "BUY" else OrderSide.SELL
                self.broker.place_order(Order(plan.symbol, side, plan.shares, plan.price, plan.reason))
                plan.sent = True
            plans.append(plan)

        return plans

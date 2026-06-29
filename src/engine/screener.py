"""選股引擎：對一籃子股票跑所有策略，列出「現在每個策略各看上哪幾檔」。

只看「當下最新一根 K」的訊號 (position=None，代表找進場標的)，
不做回測、不下單，純粹幫你篩出今天值得注意的買進候選。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from ..data.base import DataProvider
from ..data.universe import NAMES
from ..models import Action
from ..strategies.base import Strategy, StrategyContext


@dataclass
class Hit:
    symbol: str
    name: str
    strategy: str
    strength: float
    reason: str


@dataclass
class ScreenResult:
    end: str
    hits: List[Hit] = field(default_factory=list)
    scanned: int = 0
    failed: List[str] = field(default_factory=list)

    def by_strategy(self) -> Dict[str, List[Hit]]:
        out: Dict[str, List[Hit]] = {}
        for h in sorted(self.hits, key=lambda x: -x.strength):
            out.setdefault(h.strategy, []).append(h)
        return out

    def by_symbol(self) -> Dict[str, List[Hit]]:
        out: Dict[str, List[Hit]] = {}
        for h in self.hits:
            out.setdefault(h.symbol, []).append(h)
        return out


class Screener:
    def __init__(self, provider: DataProvider, strategies: List[Strategy], lookback_days: int = 500):
        self.provider = provider
        self.strategies = strategies
        self.lookback_days = lookback_days

    def run(self, symbols: List[str], end: str) -> ScreenResult:
        start = (pd.Timestamp(end) - pd.Timedelta(days=self.lookback_days)).strftime("%Y-%m-%d")
        bench = self.provider.benchmark(start, end)
        result = ScreenResult(end=end)

        for sym in symbols:
            try:
                df = self.provider.history(sym, start, end)
                if df is None or df.empty:
                    result.failed.append(sym)
                    continue
                fund = self.provider.fundamentals(sym)
                b = bench.reindex(df.index).ffill() if bench is not None else None
                result.scanned += 1
                for strat in self.strategies:
                    ctx = StrategyContext(symbol=sym, prices=df, fundamentals=fund, benchmark=b, position=None)
                    sig = strat.evaluate(ctx)
                    if sig.action == Action.BUY and sig.strength > 0:
                        result.hits.append(
                            Hit(sym, NAMES.get(sym, ""), strat.name, sig.strength, sig.reason)
                        )
            except Exception as e:
                result.failed.append(f"{sym}({e})")
        return result


def format_report(res: ScreenResult) -> str:
    """純文字報表 (給終端機與 Telegram 共用)。"""
    lines = [f"📋 選股結果 @ {res.end}　掃描 {res.scanned} 檔 × 多策略"]

    by_strat = res.by_strategy()
    lines.append("\n📈 各策略的買進名單：")
    if not by_strat:
        lines.append("　(今日所有策略皆無買進訊號)")
    for strat, hits in by_strat.items():
        names = "、".join(f"{h.symbol}{h.name}" for h in hits)
        lines.append(f"　{strat:<10}: {names}")

    by_sym = res.by_symbol()
    multi = {s: hs for s, hs in by_sym.items() if len(hs) >= 2}
    if multi:
        lines.append("\n⭐ 多策略同時看好 (訊號較強)：")
        for sym, hs in sorted(multi.items(), key=lambda kv: -len(kv[1])):
            strats = "、".join(h.strategy for h in hs)
            lines.append(f"　{sym}{NAMES.get(sym,'')}　← {strats} ({len(hs)} 個策略)")

    if res.failed:
        lines.append(f"\n⚠️ 無法取得資料: {', '.join(res.failed[:10])}")
    return "\n".join(lines)

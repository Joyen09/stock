"""班傑明‧葛拉漢 (Benjamin Graham) — 價值投資之父 / 深度價值與安全邊際。

核心理念："安全邊際 (Margin of Safety)" — 用遠低於內在價值的價格買進。

經典量化條件 (源自《智慧型股票投資人》防禦型投資人準則的簡化版)：
1. 本益比 PE <= 15
2. 股價淨值比 PB <= 1.5
3. PE * PB <= 22.5 (葛拉漢數字概念)
4. 流動比率 >= 150% (財務安全)
5. 負債比 <= 60%
6. 有穩定配息

葛拉漢偏向「分散買進一籃子便宜股」，所以這裡只要多數條件成立即視為買進，
不額外要求趨勢；賣出條件為估值修復 (PE*PB 過高) 或基本面惡化。
"""
from __future__ import annotations

from ..models import Action, Signal
from .base import Strategy, StrategyContext


class GrahamStrategy(Strategy):
    name = "graham"
    requires_fundamentals = True
    min_bars = 1

    DEFAULTS = dict(
        max_pe=15.0,
        max_pb=1.5,
        max_graham_number=22.5,
        min_current_ratio=150.0,
        max_debt_ratio=60.0,
    )

    def __init__(self, **params):
        merged = {**self.DEFAULTS, **params}
        super().__init__(**merged)

    def evaluate(self, ctx: StrategyContext) -> Signal:
        if not self._ready(ctx):
            return self._hold("缺基本面資料")

        f = ctx.fundamentals
        p = self.params
        graham_num = (f.pe * f.pb) if (f.pe and f.pb) else None

        checks = {
            "PE<=15": f.pe is not None and 0 < f.pe <= p["max_pe"],
            "PB<=1.5": f.pb is not None and 0 < f.pb <= p["max_pb"],
            "PE*PB<=22.5": graham_num is not None and graham_num <= p["max_graham_number"],
            "流動比>=150%": f.current_ratio is not None and f.current_ratio >= p["min_current_ratio"],
            "負債比<=60%": f.debt_ratio is not None and f.debt_ratio <= p["max_debt_ratio"],
            "有配息": f.dividend_yield is not None and f.dividend_yield > 0,
        }
        passed = sum(checks.values())
        score = passed / len(checks)
        detail = "、".join(k for k, v in checks.items() if v) or "無"

        held = ctx.position is not None and ctx.position.shares > 0

        # 賣出：估值不再便宜 (葛拉漢數字超標) 或安全條件崩壞
        if held and (graham_num is not None and graham_num > p["max_graham_number"] * 1.5):
            return self._signal(
                Action.SELL, 1.0,
                f"估值修復 PE*PB={graham_num:.1f} 偏貴，獲利了結",
                ctx.symbol,
            )

        # 買進：多數安全邊際條件成立
        if score >= 0.8:
            return self._signal(
                Action.BUY, score,
                f"具安全邊際的便宜股 (符合: {detail})",
                ctx.symbol,
            )

        return self._hold(f"安全邊際不足 {score:.0%} (符合: {detail})")

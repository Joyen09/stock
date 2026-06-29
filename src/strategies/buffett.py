"""華倫‧巴菲特 (Warren Buffett) — 價值投資 / 護城河。

核心理念："以合理的價格買進優秀的公司，遠勝於以便宜的價格買進平庸的公司。"

選股條件 (基本面為主)：
1. 高且穩定的股東權益報酬率 ROE (>= 15%)            -> 賺錢能力強
2. 低負債比 (<= 50%)                                -> 財務穩健、有護城河
3. 合理估值：本益比不過高 (<= 22) 且毛利率佳         -> 不追高
4. 有配息 (殖利率 > 0)                               -> 真實獲利

進場再加一個技術濾網：股價站上年線 (200MA)，避免買在長空趨勢。
賣出：基本面轉差 (ROE 跌破門檻) 或股價跌破年線。
"""
from __future__ import annotations

from .. import indicators as ind
from ..models import Action, Signal
from .base import Strategy, StrategyContext


class BuffettStrategy(Strategy):
    name = "buffett"
    requires_fundamentals = True
    min_bars = 200

    DEFAULTS = dict(
        min_roe=15.0,
        max_debt_ratio=50.0,
        max_pe=22.0,
        min_gross_margin=20.0,
        ma_window=200,
    )

    def __init__(self, **params):
        merged = {**self.DEFAULTS, **params}
        super().__init__(**merged)

    def evaluate(self, ctx: StrategyContext) -> Signal:
        if not self._ready(ctx):
            return self._hold("資料不足或缺基本面")

        f = ctx.fundamentals
        p = self.params
        close = ctx.prices["close"]
        ma = ind.sma(close, p["ma_window"]).iloc[-1]
        price = close.iloc[-1]

        # --- 基本面評分 (0~1) ---
        checks = {
            "ROE>=15%": f.roe is not None and f.roe >= p["min_roe"],
            "負債比<=50%": f.debt_ratio is not None and f.debt_ratio <= p["max_debt_ratio"],
            "本益比<=22": f.pe is not None and 0 < f.pe <= p["max_pe"],
            "毛利率>=20%": f.gross_margin is not None and f.gross_margin >= p["min_gross_margin"],
            "有配息": f.dividend_yield is not None and f.dividend_yield > 0,
        }
        passed = sum(checks.values())
        score = passed / len(checks)
        detail = "、".join(k for k, v in checks.items() if v) or "無"

        above_ma = price >= ma if ma == ma else False  # ma 可能為 NaN

        # 賣出：優質條件崩壞或跌破年線
        held = ctx.position is not None and ctx.position.shares > 0
        if held and (score < 0.6 or not above_ma):
            return self._signal(
                Action.SELL, 1.0,
                f"基本面評分 {score:.0%} 或跌破年線，出場 (符合: {detail})",
                ctx.symbol,
            )

        # 買進：基本面夠優 + 股價站上年線
        if score >= 0.8 and above_ma:
            return self._signal(
                Action.BUY, score,
                f"優質公司且站上年線 (符合: {detail})",
                ctx.symbol,
            )

        return self._hold(f"基本面評分 {score:.0%}，續抱/觀望 (符合: {detail})")

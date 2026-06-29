"""傑西‧李佛摩 (Jesse Livermore) — 趨勢順勢 / 關鍵點突破。

核心理念："順著阻力最小的方向操作 (line of least resistance)"，只在趨勢明確時進場，
並嚴守停損 ("永遠不要攤平虧損")。

純技術策略 (不需基本面)：
- 進場：股價突破近 N 日 (預設 60) 的關鍵高點，且站上中期均線 (確認趨勢向上)。
- 加碼概念：訊號強度隨突破幅度提高 (這裡只輸出強度，由資金控管決定)。
- 停損：以 ATR 為基準的移動停損 (進場後跌破 entry - k*ATR)，或跌破關鍵低點。
"""
from __future__ import annotations

from .. import indicators as ind
from ..models import Action, Signal
from .base import Strategy, StrategyContext


class LivermoreStrategy(Strategy):
    name = "livermore"
    requires_fundamentals = False
    min_bars = 60

    DEFAULTS = dict(
        breakout_window=60,
        trend_ma=120,
        atr_window=14,
        atr_stop=3.0,
        exit_window=20,
    )

    def __init__(self, **params):
        merged = {**self.DEFAULTS, **params}
        super().__init__(**merged)

    def evaluate(self, ctx: StrategyContext) -> Signal:
        if not self._ready(ctx):
            return self._hold("資料不足")

        p = self.params
        df = ctx.prices
        close = df["close"]
        price = close.iloc[-1]
        atr_val = ind.atr(df, p["atr_window"]).iloc[-1]

        held = ctx.position is not None and ctx.position.shares > 0
        # --- 出場：ATR 移動停損 或 跌破近期關鍵低點 ---
        if held:
            entry = ctx.position.avg_price
            exit_low = ind.rolling_low(close, p["exit_window"]).shift(1).iloc[-1]
            if atr_val == atr_val and entry > 0 and price <= entry - p["atr_stop"] * atr_val:
                return self._signal(Action.SELL, 1.0, f"ATR 移動停損 ({p['atr_stop']}xATR)", ctx.symbol)
            if exit_low == exit_low and price < exit_low:
                return self._signal(Action.SELL, 1.0, f"跌破近 {p['exit_window']} 日關鍵低點，認賠/獲利了結", ctx.symbol)

        # --- 進場：突破關鍵高點 + 趨勢向上 ---
        prior_high = ind.rolling_high(close, p["breakout_window"]).shift(1).iloc[-1]
        trend = ind.sma(close, p["trend_ma"]).iloc[-1]
        up_trend = trend == trend and price >= trend
        breakout = prior_high == prior_high and price >= prior_high

        if breakout and up_trend:
            # 突破幅度越大、ATR 越小，訊號越強
            margin = (price - prior_high) / prior_high if prior_high else 0
            strength = min(1.0, 0.6 + margin * 20)
            return self._signal(
                Action.BUY, strength,
                f"突破近 {p['breakout_window']} 日關鍵高點且順勢 (阻力最小方向)",
                ctx.symbol,
            )

        return self._hold("未突破關鍵點或趨勢未確認")

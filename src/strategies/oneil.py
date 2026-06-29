"""威廉‧歐尼爾 (William O'Neil) — CANSLIM / 成長動能突破。

核心理念：買強勢、創新高的成長股，用相對強弱 (RS) 與量價突破進場。

本實作聚焦 CANSLIM 中可量化的價量面：
- C/A (盈餘成長)：EPS 年成長 >= 25% (有基本面時加分，沒有則略過)
- L (Leader)：相對大盤強度 RS >= 1 (近一年贏大盤)
- N (New high)：股價突破近 52 週 (250 日) 高點
- I (Supply/Demand)：突破當天成交量 > 近期均量 1.5 倍 (帶量)

賣出 (歐尼爾的鐵律「停損 7%~8%」)：
- 自買進價回落超過 8% -> 停損
- 或跌破 50 日均線 -> 趨勢轉弱
"""
from __future__ import annotations

from .. import indicators as ind
from ..models import Action, Signal
from .base import Strategy, StrategyContext


class ONeilStrategy(Strategy):
    name = "oneil"
    requires_fundamentals = False
    min_bars = 250

    DEFAULTS = dict(
        high_window=250,
        vol_window=50,
        vol_mult=1.5,
        rs_min=1.0,
        ma_exit=50,
        stop_loss=0.08,
        min_eps_growth=25.0,
    )

    def __init__(self, **params):
        merged = {**self.DEFAULTS, **params}
        super().__init__(**merged)

    def evaluate(self, ctx: StrategyContext) -> Signal:
        if not self._ready(ctx):
            return self._hold("資料不足 (需 250 根 K 棒)")

        p = self.params
        close = ctx.prices["close"]
        vol = ctx.prices["volume"]
        price = close.iloc[-1]

        held = ctx.position is not None and ctx.position.shares > 0
        # --- 出場優先 ---
        if held:
            entry = ctx.position.avg_price
            ma_exit = ind.sma(close, p["ma_exit"]).iloc[-1]
            if entry > 0 and price <= entry * (1 - p["stop_loss"]):
                return self._signal(Action.SELL, 1.0, f"停損 -{p['stop_loss']:.0%} (歐尼爾鐵律)", ctx.symbol)
            if ma_exit == ma_exit and price < ma_exit:
                return self._signal(Action.SELL, 1.0, "跌破 50 日均線，趨勢轉弱出場", ctx.symbol)

        # --- 進場條件 ---
        prior_high = ind.rolling_high(close, p["high_window"]).shift(1).iloc[-1]
        avg_vol = ind.sma(vol, p["vol_window"]).iloc[-1]
        new_high = prior_high == prior_high and price >= prior_high
        big_vol = avg_vol == avg_vol and vol.iloc[-1] >= avg_vol * p["vol_mult"]

        rs_ok = True
        rs_val = None
        if ctx.benchmark is not None and len(ctx.benchmark) == len(close):
            rs = ind.relative_strength(close, ctx.benchmark)
            rs_val = rs.iloc[-1]
            rs_ok = rs_val >= p["rs_min"]

        eps_ok = True
        if ctx.fundamentals is not None and ctx.fundamentals.eps_growth is not None:
            eps_ok = ctx.fundamentals.eps_growth >= p["min_eps_growth"]

        if new_high and big_vol and rs_ok and eps_ok:
            rs_txt = f", RS={rs_val:.2f}" if rs_val is not None else ""
            return self._signal(
                Action.BUY, 0.9,
                f"帶量突破 52 週新高{rs_txt} (CANSLIM)",
                ctx.symbol,
            )

        return self._hold("未出現帶量突破新高")

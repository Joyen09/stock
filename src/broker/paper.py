"""紙上模擬券商 (paper trading)。

在記憶體中模擬資金與持倉，套用真實台股交易成本，用於：
- 回測引擎的成交撮合
- 實單前的「模擬盤」演練 (接真實行情、假下單)
"""
from __future__ import annotations

from typing import Dict, List

from ..models import Position
from . import fees
from .base import Account, Broker, Order, OrderSide


class PaperBroker(Broker):
    def __init__(self, cash: float = 1_000_000.0, fee_discount: float = 1.0):
        self.account = Account(cash=cash)
        self.fee_discount = fee_discount
        self.history: List[Order] = []

    def place_order(self, order: Order) -> Order:
        if order.price is None:
            raise ValueError("PaperBroker 需指定價格 (撮合用)，請帶入當下成交價")
        amount = order.shares * order.price
        pos = self.account.positions.get(order.symbol, Position(order.symbol))

        if order.side == OrderSide.BUY:
            total = fees.buy_cost(amount, self.fee_discount)
            if total > self.account.cash:
                order.note += " | 資金不足，未成交"
                return order
            self.account.cash -= total
            new_shares = pos.shares + order.shares
            pos.avg_price = (pos.cost + amount) / new_shares if new_shares else 0.0
            pos.shares = new_shares
            self.account.positions[order.symbol] = pos
        else:  # SELL
            sell_shares = min(order.shares, pos.shares)
            if sell_shares <= 0:
                order.note += " | 無持倉可賣"
                return order
            proceeds = fees.sell_proceeds(sell_shares * order.price, self.fee_discount)
            self.account.cash += proceeds
            pos.shares -= sell_shares
            if pos.shares == 0:
                pos.avg_price = 0.0
            self.account.positions[order.symbol] = pos
            order.shares = sell_shares

        order.filled = True
        order.fill_price = order.price
        self.history.append(order)
        return order

    def positions(self) -> List[Position]:
        return [p for p in self.account.positions.values() if p.shares > 0]

    def cash(self) -> float:
        return self.account.cash

    def equity(self, prices: Dict[str, float]) -> float:
        """總資產 = 現金 + 持倉市值。"""
        market = sum(p.shares * prices.get(p.symbol, p.avg_price) for p in self.positions())
        return self.account.cash + market

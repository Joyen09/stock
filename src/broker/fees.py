"""台股交易成本計算。

- 手續費：成交金額 * 0.1425%，買賣都收，多數券商最低 20 元，常見折扣 (例如 2.8 折)。
- 證券交易稅：成交金額 * 0.3%，**僅賣出時收** (當沖為 0.15%)。
"""
from __future__ import annotations

BROKER_FEE_RATE = 0.001425
TAX_RATE = 0.003
MIN_FEE = 20.0


def buy_cost(amount: float, fee_discount: float = 1.0) -> float:
    """買進總成本 = 成交金額 + 手續費。"""
    fee = max(amount * BROKER_FEE_RATE * fee_discount, MIN_FEE)
    return amount + fee


def sell_proceeds(amount: float, fee_discount: float = 1.0, day_trade: bool = False) -> float:
    """賣出實得 = 成交金額 - 手續費 - 證交稅。"""
    fee = max(amount * BROKER_FEE_RATE * fee_discount, MIN_FEE)
    tax = amount * (TAX_RATE / 2 if day_trade else TAX_RATE)
    return amount - fee - tax


def round_trip_fee(amount: float, fee_discount: float = 1.0) -> float:
    """一買一賣的總交易成本 (估算)。"""
    return (buy_cost(amount, fee_discount) - amount) + (amount - sell_proceeds(amount, fee_discount))

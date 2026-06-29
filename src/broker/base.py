"""券商抽象介面。

策略產生訊號 -> Trader 換算成 Order -> Broker 送單。
PaperBroker 與真實券商 (Shioaji) 都實作同一介面，方便先模擬後實單。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from ..models import Position


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Order:
    symbol: str
    side: OrderSide
    shares: int                      # 股數 (台股 1 張 = 1000 股)
    price: Optional[float] = None    # None 代表市價
    note: str = ""
    order_id: Optional[str] = None
    filled: bool = False
    fill_price: Optional[float] = None


@dataclass
class Account:
    cash: float = 1_000_000.0
    positions: Dict[str, Position] = field(default_factory=dict)


class Broker:
    """券商介面。"""

    def place_order(self, order: Order) -> Order:
        raise NotImplementedError

    def positions(self) -> List[Position]:
        raise NotImplementedError

    def cash(self) -> float:
        raise NotImplementedError

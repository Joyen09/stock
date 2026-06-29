"""FinMind 真實台股資料來源 (免費，需在 https://finmindtrade.com 申請 token)。

需要安裝: pip install FinMind
設定 token: 環境變數 FINMIND_TOKEN，或建構時傳入 token=。

這支只負責「把 FinMind 的資料轉成框架的標準格式」，介面與 SampleDataProvider 完全相同，
所以回測 / 實單程式碼不需更動，換 provider 即可用真實資料。
"""
from __future__ import annotations

import os
from typing import List, Optional

import pandas as pd

from ..models import Fundamentals
from .base import DataProvider

TAIEX = "TAIEX"  # 加權指數代號 (FinMind TaiwanStockTotalReturnIndex / 這裡用發行量加權)


class FinMindProvider(DataProvider):
    def __init__(self, token: Optional[str] = None):
        try:
            from FinMind.data import DataLoader  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise ImportError("請先安裝 FinMind: pip install FinMind") from e
        self.api = DataLoader()
        token = token or os.getenv("FINMIND_TOKEN")
        if token:
            self.api.login_by_token(api_token=token)

    def history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        df = self.api.taiwan_stock_daily(stock_id=symbol, start_date=start, end_date=end)
        if df is None or df.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = df.rename(
            columns={
                "max": "high",
                "min": "low",
                "Trading_Volume": "volume",
                "open": "open",
                "close": "close",
            }
        )
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        return df[["open", "high", "low", "close", "volume"]]

    def fundamentals(self, symbol: str) -> Optional[Fundamentals]:
        """從 FinMind 財報 / PER 等資料表組出基本面快照。

        注意：FinMind 不同資料表更新頻率不同，這裡示範如何取 PER/PBR；
        ROE、負債比等可由 taiwan_stock_financial_statement 推算，依需求擴充。
        """
        try:
            per = self.api.taiwan_stock_per_pbr(stock_id=symbol, start_date="2020-01-01")
        except Exception:  # pragma: no cover - 網路/額度問題時回 None
            return None
        if per is None or per.empty:
            return Fundamentals(symbol=symbol)
        latest = per.sort_values("date").iloc[-1]
        return Fundamentals(
            symbol=symbol,
            pe=float(latest.get("PER")) if latest.get("PER") else None,
            pb=float(latest.get("PBR")) if latest.get("PBR") else None,
            dividend_yield=float(latest.get("dividend_yield")) if latest.get("dividend_yield") else None,
            extra={"note": "ROE/負債比等請以財報資料表補齊"},
        )

    def benchmark(self, start: str, end: str) -> Optional[pd.Series]:
        try:
            df = self.api.taiwan_stock_daily(stock_id="TAIEX", start_date=start, end_date=end)
        except Exception:  # pragma: no cover
            return None
        if df is None or df.empty:
            return None
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date").sort_index()["close"]

    def universe(self) -> List[str]:  # pragma: no cover - 依需求自訂清單
        return []

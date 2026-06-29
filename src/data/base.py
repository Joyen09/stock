"""資料來源介面。"""
from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from ..models import Fundamentals


class DataProvider:
    """資料來源抽象介面，回測與實單共用。"""

    def history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """回傳日 K 線，index 為 DatetimeIndex，欄位 open/high/low/close/volume。"""
        raise NotImplementedError

    def fundamentals(self, symbol: str) -> Optional[Fundamentals]:
        """回傳個股最新基本面，無則回 None。"""
        return None

    def benchmark(self, start: str, end: str) -> Optional[pd.Series]:
        """回傳大盤 (加權指數) 收盤價，供相對強弱用。"""
        return None

    def universe(self) -> List[str]:
        """可交易/可回測的股票代號清單。"""
        return []

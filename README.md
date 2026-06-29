# 台股名人策略交易框架 🇹🇼📈

一個可**回測 → 模擬盤 → 實單**的台股自動交易框架，內建多位投資名人的交易策略。
設計成資料來源與券商皆可抽換：**不用任何金鑰、不用連網就能跑回測**，要實單時再接上 FinMind（資料）與永豐金 Shioaji（下單）。

> ⚠️ **風險聲明**：本專案僅供程式與策略研究教學，**不構成投資建議**。回測績效不代表未來表現，自動下單請務必先用模擬帳戶充分測試，並自行承擔交易風險。

---

## 一、台股自動交易 API 一覽

自動下單一定要有「券商帳戶 + 開通 API + 憑證」。常見選擇：

| 券商 | API | 語言 | 備註 |
|------|-----|------|------|
| **永豐金證券** | **Shioaji** | Python | 最多人用、文件完整、有模擬帳戶（本專案預設整合） |
| 玉山富果 | Fugle Trade | Python/JS | 即時行情佳，REST + WebSocket |
| 富邦證券 | Fubon Neo | Python | 大券商，近年積極經營 |
| 元大 / 凱基 | 各自 API | Python | 市佔大 |

**資料來源（免費、免開戶即可回測）**：
- **FinMind**：日 K、財報、PER/PBR、三大法人等，最完整（需免費 token）。
- twstock、yfinance：日 K 為主。

本框架：**下單用 Shioaji、資料用 FinMind**，但都封裝在統一介面後，可自由替換。

---

## 二、內建名人策略

| 代號 | 名人 | 類型 | 核心邏輯 |
|------|------|------|----------|
| `buffett` | 華倫‧巴菲特 | 價值/護城河 | 高 ROE(≥15%)、低負債、合理本益比、有配息 + 站上年線 |
| `graham` | 班傑明‧葛拉漢 | 深度價值/安全邊際 | 低 PE(≤15)、低 PB(≤1.5)、葛拉漢數字 PE×PB≤22.5、財務安全 |
| `lynch` | 彼得‧林區 | 成長合理價 GARP | PEG≤1.2、EPS 成長 15~50%、營收成長 + 站上季線 |
| `oneil` | 威廉‧歐尼爾 | 動能突破 CANSLIM | 帶量突破 52 週新高、相對強弱 RS≥1、停損 8% |
| `livermore` | 傑西‧李佛摩 | 順勢趨勢 | 突破關鍵高點 + 順勢，ATR 移動停損、跌破關鍵低點出場 |

每個策略都在對應檔案開頭詳細註解其理念與條件，方便你調參或新增自己的策略
（`src/strategies/`）。

---

## 三、快速開始

```bash
# 1. 安裝核心套件（回測只需要 pandas / numpy）
pip install pandas numpy

# 2. 列出策略
python main.py list

# 3. 用內建樣本資料回測（免金鑰、免連網）
python main.py backtest --strategy buffett --trades

# 4. 指定股票與期間
python main.py backtest --strategy livermore --symbols 2330,2454 --start 2024-01-01

# 5. 模擬盤掃描訊號（dry-run，只印出會下的單，不會真的下單）
python main.py scan --strategy oneil
```

回測輸出包含：總報酬率、年化報酬(CAGR)、最大回撤、夏普值、交易次數與明細，
並已套用真實台股交易成本（手續費 0.1425%、證交稅 0.3%，可設折扣）。

---

## 四、接上真實資料（FinMind）

```bash
pip install FinMind
export FINMIND_TOKEN="你的 token"   # 申請：https://finmindtrade.com

python main.py backtest --strategy graham --source finmind --symbols 2330,2317
```

`src/data/finmind.py` 已把 FinMind 轉成框架標準格式；ROE、負債比等可依需求從財報表補齊。

---

## 五、接上實單（永豐金 Shioaji）

```bash
pip install shioaji

# 金鑰一律走環境變數，切勿寫進程式或 commit！
export SHIOAJI_API_KEY="..."
export SHIOAJI_SECRET_KEY="..."
# 實單還需憑證：
export SHIOAJI_CA_PATH="/path/to/ca.pfx"
export SHIOAJI_CA_PASSWD="..."
export SHIOAJI_PERSON_ID="身分證字號"
```

```python
from src.data.finmind import FinMindProvider
from src.broker.shioaji_broker import ShioajiBroker
from src.engine.trader import LiveTrader
from src import strategies

provider = FinMindProvider()
broker   = ShioajiBroker(simulation=True)   # ⚠️ 先用模擬盤！確認無誤再改 False
trader   = LiveTrader(provider, broker, strategies.build("oneil"),
                      position_budget=200_000, dry_run=True)  # dry_run 再保險一層

plans = trader.scan(["2330", "2454"], end="2025-12-31")
for p in plans:
    print(p)
```

確認模擬盤 + dry-run 行為正確後，再依序關閉 `dry_run`、把 `simulation` 改 `False`。
建議用系統排程（cron / APScheduler）在每日盤後觸發 `trader.scan(...)`，而非 `while True`。

---

## 六、專案結構

```
stock/
├── main.py                 # 命令列入口 (list / backtest / scan)
├── config.example.yaml     # 設定範本 (複製成 config.yaml)
├── requirements.txt
└── src/
    ├── models.py           # Signal / Fundamentals / Position 等資料模型
    ├── indicators.py       # 技術指標 (SMA/EMA/RSI/MACD/ATR/突破/相對強弱)
    ├── strategies/         # 名人策略 (buffett/graham/lynch/oneil/livermore)
    ├── data/               # 資料源 (sample 離線樣本 / finmind 真實)
    ├── broker/             # 券商 (paper 模擬 / shioaji 實單) + 台股交易成本
    └── engine/             # backtest 回測引擎 / trader 實單執行器
```

---

## 七、測試

```bash
python tests/test_strategies.py      # 內建 runner，免裝 pytest
# 或
pytest tests/
```

---

## 八、如何新增自己的策略

1. 在 `src/strategies/` 新增檔案，繼承 `Strategy`，實作 `evaluate(ctx) -> Signal`。
2. 在 `src/strategies/__init__.py` 的 `REGISTRY` 註冊名稱。
3. 即可用 `python main.py backtest --strategy <你的名稱>` 回測。

`evaluate()` 只會拿到「截至當下」的資料（引擎已切片），避免未來函數；
產生 `Signal(action, strength, reason)` 即可，下單與資金控管交給引擎處理。

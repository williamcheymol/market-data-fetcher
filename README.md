# Market Data Fetcher

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Data](https://img.shields.io/badge/source-yfinance-orange)
![Status](https://img.shields.io/badge/status-Phase%201%20complete-success)

A lightweight Python tool to pull, clean and structure historical market data via yfinance — prices, volumes, dividends — exported in formats directly usable for quant analysis and backtesting.

Built as a reusable data layer for quantitative finance projects.

---

## Key results

| Ticker | Period | Mean daily return | Annualised vol |
|--------|--------|-------------------|----------------|
| AAPL | 2020–2024 | +0.11% | ~28% |
| MSFT | 2020–2024 | +0.10% | ~26% |
| SPY | 2020–2024 | +0.06% | ~18% |

---

## Features

- Download OHLCV data for any ticker (stocks, ETFs, indices, crypto, forex)
- Automatic price adjustment for dividends and stock splits
- Multi-ticker support with graceful error handling
- Cleaning pipeline: duplicate dates, invalid prices, missing values
- Feature computation: log-returns, rolling realised volatility, cumulative returns
- CSV export ready for downstream use (backtesting, pricers, ML)
- 28 unit tests

---

## Quickstart

```bash
# Install dependencies
pip install -r requirements.txt

# Run the full pipeline (downloads AAPL, MSFT, SPY by default)
python main.py

# Run the test suite
pytest tests/ -v
```

Output CSVs are saved in `results/` — one file per ticker.

---

## Usage

```python
from fetcher.download import download_single, download_multiple
from cleaner.pipeline import clean
from features.compute import compute_all
from exporter.export import to_csv

# Single ticker
df_raw = download_single("AAPL", start="2020-01-01", end="2024-12-31")
df     = clean(df_raw)
df     = compute_all(df)
to_csv(df, "AAPL")

# Multiple tickers
data = download_multiple(["AAPL", "MSFT", "SPY"], "2020-01-01", "2024-12-31")
```

---

## Output columns

| Column | Description |
|--------|-------------|
| `open` | Opening price |
| `high` | Daily high |
| `low` | Daily low |
| `close` | Closing price (adjusted) |
| `volume` | Number of shares traded |
| `log_return` | $r_t = \log(S_t / S_{t-1})$ |
| `realised_vol` | Rolling std of log-returns × $\sqrt{252}$ (annualised) |
| `cumulative_return` | $\exp(\sum r_i) - 1$ from start date |

---

## Project structure

```
market-fetcher/
├── config.py            # Tickers, date range, rolling window
├── main.py              # Pipeline entry point
│
├── fetcher/
│   └── download.py      # yfinance download — single & multi-ticker
│
├── cleaner/
│   └── pipeline.py      # Cleaning: duplicates, invalid prices, NaN, columns
│
├── features/
│   └── compute.py       # Log-returns, realised vol, cumulative returns
│
├── exporter/
│   └── export.py        # CSV export
│
└── tests/
    ├── test_fetcher.py   # 8 tests
    ├── test_cleaner.py   # 12 tests
    └── test_features.py  # 8 tests
```

---

## Configuration (`config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DEFAULT_TICKERS` | `["AAPL", "MSFT", "SPY"]` | Tickers to download |
| `START_DATE` | `"2020-01-01"` | Start of historical window |
| `END_DATE` | `"2024-12-31"` | End of historical window |
| `ROLLING_WINDOW` | `21` | Rolling vol window (~1 month) |
| `TRADING_DAYS_PER_YEAR` | `252` | Annualisation factor |

---

## Roadmap

**Phase 1 ✓** — OHLCV download for any ticker via yfinance · Auto-adjustment for dividends & splits · Multi-ticker with graceful error handling · Cleaning pipeline (duplicates, invalid prices, NaN) · Log-returns, realised vol, cumulative returns · CSV export · 28 unit tests

**Phase 2 — next:**
- Sharpe ratio, max drawdown, and other risk metrics
- Visualisation tools

---

*Built as a reusable data layer for a quantitative finance project series.*

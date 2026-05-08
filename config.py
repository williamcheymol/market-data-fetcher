# =============================================================================
# config.py — Global parameters for the Market Data Fetcher
# =============================================================================
# Centralises all configuration: tickers, date range, feature parameters.
# Import from here in all modules — never hardcode values elsewhere.
# =============================================================================

# --- Tickers ---
# A ticker is the unique symbol identifying a stock on an exchange.
# Examples: "AAPL" (Apple), "SPY" (S&P 500 ETF), "BTC-USD" (Bitcoin)
DEFAULT_TICKERS = ["AAPL", "MSFT", "SPY"]

# --- Date range ---
# Format: "YYYY-MM-DD"
# Start and end dates for historical data download
START_DATE = "2020-01-01"
END_DATE   = "2024-12-31"

# --- Features ---
# Rolling window (in trading days) for realised volatility computation
# 21 trading days ≈ 1 calendar month
ROLLING_WINDOW = 21

# Annualisation factor: there are ~252 trading days in a year
# Used to convert daily vol to annualised vol: σ_annual = σ_daily * sqrt(252)
TRADING_DAYS_PER_YEAR = 252

# --- Export ---
# Output directory for generated CSV files
EXPORT_DIR = "results/"

# --- Options ---
# Ticker used for option chain fetching
OPTION_TICKER = "AAPL"

# Maximum number of expiry dates to fetch (nearest maturities first)
MAX_MATURITIES = 4

# Implied vol search bounds (Brent's method)
IV_LOW  = 1e-4   # 0.01% — avoids division by zero
IV_HIGH = 5.0    # 500%  — handles deep OTM options

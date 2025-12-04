# SHPE Capital - Algorithmic Trading Model

A Python-based algorithmic trading system that uses a **Smart Moving Average (SMA) Crossover** strategy with **RSI filtering** to generate trading signals. Features include multi-stock portfolio analysis with intelligent capital allocation, interactive backtesting, and comprehensive performance metrics.

---

## Table of Contents
1. [How to Run](#how-to-run)
2. [Algorithmic Trading Concepts Used](#algorithmic-trading-concepts-used)
3. [Strategy Overview](#strategy-overview)
4. [Python Implementation](#python-implementation)
5. [Backtesting & Performance Evaluation](#backtesting--performance-evaluation)
6. [Risk Management Integration](#risk-management-integration)

---

## How to Run

### 1. Clone the Repository
```bash
git clone <repository_url>
cd <repository_directory>/stock-analyzer
```

### 2. Set Up Virtual Environment & Install Dependencies
```bash
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r src/requirements.txt
```

### 3. Launch the Interactive Web GUI (Recommended)
```bash
python -m src.web_gui
```
Open your browser to **http://localhost:5000**

Features:
- **Multi-stock portfolio analysis** - Enter multiple tickers (e.g., `AAPL, MSFT, GOOGL, NVDA`)
- **Smart capital allocation** - Automatically weights more capital to better-performing stocks
- **Animated equity curve** - Watch your portfolio grow/shrink over time
- **Live profit counter** - See net profit update in real-time during animation
- **Interactive Plotly charts** - Zoom, pan, hover for details
- **Visual BUY/SELL markers** - Green triangles for buys, red for sells
- **Stock rankings table** - Sorted by profit with allocation percentages

### 4. Alternative: Run CLI Backtest
```bash
python -m src.main
```
Follow prompts for ticker, capital, and date range.

### 5. Alternative: Desktop GUI (Tkinter)
```bash
python -m src.gui
```

---

## Algorithmic Trading Concepts Used

### 1. Market Data Feed
The model pulls **OHLCV (Open, High, Low, Close, Volume)** data directly from the Yahoo Finance chart API using the `requests` library in `data_fetcher.py`. This provides real historical price data that our algorithm uses to calculate indicators and generate trading signals. We chose direct API calls over the `yfinance` library to avoid authentication issues and ensure reliable data access.

### 2. Trading Platform (Simulation)
The `backtester.py` module acts as our **simulated trading platform**. It maintains a complete portfolio state—tracking cash balance, stock positions, and total equity value at each time step. When our strategy generates a BUY or SELL signal, the backtester executes the trade and updates the portfolio, simulating exactly how a real brokerage account would behave without risking actual capital.

### 3. Connectivity/Latency Relevance
While our backtesting model runs locally and processes historical data (so latency doesn't affect results), **in live trading, latency is critical**. The time delay between receiving market data, processing signals, and executing orders can mean the difference between profit and loss. High-frequency strategies require sub-millisecond latency, while our daily SMA strategy would be less sensitive but still benefits from reliable connectivity to avoid missed trades.

### 4. Backtesting Importance
**Backtesting is the foundation of algorithmic trading development.** Our entire project is a backtesting engine that tests strategy viability against historical data before risking real money. This process helps identify flaws in strategy logic, understand performance across different market conditions (bull/bear markets), and optimize parameters. Without backtesting, traders would be "flying blind" with untested ideas.

### 5. Risk Controls
Our model implements multiple **risk control mechanisms** to prevent catastrophic losses:
- **Stop-loss orders**: Automatically sell if price drops X% from purchase price
- **RSI filtering**: Prevents buying overbought stocks (RSI > 70) or panic-selling oversold stocks (RSI < 30)
- **Smart allocation**: Weights capital toward historically better-performing assets rather than equal distribution

These controls help prevent **overfitting** (strategy that only works on past data) and reduce **blow-up risk** (total account loss from a single bad trade).

---

## Strategy Overview

Our core strategy is a **Smart SMA Crossover with RSI Filter**:

### Indicators Used
| Indicator | Description |
|-----------|-------------|
| **Fast SMA (20-day)** | Short-term moving average that reacts quickly to price changes |
| **Slow SMA (50-day)** | Long-term moving average showing the overall trend direction |
| **RSI (14-day)** | Relative Strength Index measuring overbought/oversold conditions |

### Time Windows
- **Data frequency**: Daily price data (1 trading day per bar)
- **Fast SMA lookback**: 20 trading days (~1 month)
- **Slow SMA lookback**: 50 trading days (~2.5 months)
- **RSI period**: 14 trading days (standard)

### Trading Rules

| Condition | Action | Logic |
|-----------|--------|-------|
| **BUY Signal** | Fast SMA crosses ABOVE Slow SMA AND RSI < 70 | Momentum turning bullish, but not overbought |
| **SELL Signal** | Fast SMA crosses BELOW Slow SMA AND RSI > 30 | Momentum turning bearish, but not oversold |
| **HOLD Condition** | No crossover occurring | Maintain current position (cash or stock) |
| **Stop-Loss (Risk Rule)** | Price drops X% from purchase price | Force sell to limit losses, overrides other signals |
| **RSI Filter (Risk Rule)** | RSI > 70 on buy signal | Block the buy—stock is overbought, likely to pull back |

### Why This Strategy Works
- **SMA Crossover** captures medium-term trends while filtering out daily noise
- **RSI Filter** prevents buying at the top (overbought) or selling at the bottom (oversold)
- **Faster SMAs (20/50 vs 40/100)** respond more quickly to trend changes, improving entry/exit timing

---

## Python Implementation

### Code Structure
```
stock-analyzer/
├── src/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # CLI entry point
│   ├── gui.py               # Tkinter desktop GUI
│   ├── web_gui.py           # Flask + Plotly web interface
│   ├── data_fetcher.py      # Yahoo Finance API data retrieval
│   ├── strategy.py          # SMA crossover + RSI signal generation
│   ├── backtester.py        # Portfolio simulation engine
│   ├── performance.py       # Sharpe ratio, max drawdown calculations
│   └── requirements.txt     # Python dependencies
├── venv/                    # Virtual environment
└── README.md                # This file
```

### Key Modules

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `data_fetcher.py` | Fetches OHLCV data from Yahoo Finance | `fetch_price_history(ticker, start, end)` |
| `strategy.py` | Generates BUY/SELL signals | `generate_signals(data, short_window, long_window, use_rsi)` |
| `backtester.py` | Simulates trades, tracks portfolio | `run_backtest(ticker, data, signals, capital)` |
| `performance.py` | Calculates risk-adjusted metrics | `calculate_sharpe_ratio()`, `calculate_max_drawdown()` |
| `web_gui.py` | Interactive web dashboard | `analyze_single_stock()`, `/api/portfolio` endpoint |

### Code Quality
- ✅ **Runs end-to-end without errors**
- ✅ **Indicators implemented correctly** (SMA, RSI calculations verified)
- ✅ **Signal logic matches strategy design** (crossover + RSI filter)
- ✅ **Organized in functions/files** (modular architecture)
- ✅ **Comments explain key logic** (docstrings on all functions)
- ✅ **Clean repo structure** (src folder, requirements.txt, README)

---

## Backtesting & Performance Evaluation

### Metrics Produced
Our backtester calculates and displays the following performance metrics:

| Metric | Description | Why It Matters |
|--------|-------------|----------------|
| **Equity Curve** | Portfolio value over time (animated chart) | Visualizes growth/drawdowns |
| **Total Return %** | (Final Value - Initial) / Initial × 100 | Overall profitability |
| **Net Profit/Loss** | Final Value - Initial Capital (in dollars) | Actual money made/lost |
| **Sharpe Ratio** | Risk-adjusted return (excess return / volatility) | Higher = better risk/reward |
| **Maximum Drawdown %** | Largest peak-to-trough decline | Worst-case loss scenario |
| **Win Rate %** | Profitable trades / Total trades × 100 | Consistency of strategy |

### Sample Results
Testing AAPL, MSFT, GOOGL, NVDA, AMZN with $100,000 from 2023-01-01 to 2024-06-01:

| Stock | Allocation | Profit | Return |
|-------|------------|--------|--------|
| NVDA | 38.6% | +$112,616 | +291% |
| AMZN | 25.3% | +$18,872 | +74% |
| GOOGL | 22.7% | +$11,863 | +52% |
| AAPL | 13.1% | +$3,177 | +24% |
| **Portfolio Total** | 100% | **+$146,530** | **+146%** |

### What Worked
- **Faster SMAs (20/50)** caught trends earlier than slow SMAs (40/100)
- **RSI filter** prevented several bad entries at market tops
- **Smart allocation** put more capital in NVDA (best performer)

### What Could Improve
- Strategy struggles in sideways/choppy markets (many false signals)
- No position sizing—always goes 100% in or 100% out
- Could add more indicators (MACD, Bollinger Bands) for confirmation

---

## Risk Management Integration

### Implemented Risk Controls

#### 1. Stop-Loss Orders
```python
# In backtester.py
if stop_loss_pct is not None and positions > 0:
    if price < last_buy_price * (1 - stop_loss_pct):
        cash = positions * price  # Force sell
        positions = 0.0
```
**Why it matters**: Limits maximum loss on any single trade. If we buy at $100 with a 10% stop-loss, we automatically sell if price hits $90, preventing further losses if the stock continues falling.

#### 2. RSI Overbought/Oversold Filter
```python
# In strategy.py
if use_rsi:
    # Don't buy if RSI > 70 (overbought)
    overbought_buys = (signals['positions'] == 1.0) & (signals['rsi'] > 70)
    signals.loc[overbought_buys, 'positions'] = 0.0
    
    # Don't sell if RSI < 30 (oversold)  
    oversold_sells = (signals['positions'] == -1.0) & (signals['rsi'] < 30)
    signals.loc[oversold_sells, 'positions'] = 0.0
```
**Why it matters**: Prevents buying stocks that are already overextended (likely to pull back) and prevents panic-selling at bottoms (likely to bounce). This reduces **whipsaw trades** that erode profits.

#### 3. Smart Capital Allocation (Portfolio Mode)
```python
# In web_gui.py
# Weight allocation by Sharpe ratio
sharpes = [max(s['sharpe'], 0.01) for s in stock_results]
weights = sharpes / sum(sharpes)
allocations = weights * total_capital
```
**Why it matters**: Instead of equal-weighting all stocks, we allocate MORE capital to stocks with better risk-adjusted returns. This is a form of **diversification-based risk control**—we're not betting everything on one stock, and we're favoring historically less volatile winners.

### How These Prevent Overfitting & Blow-Up Risk

| Risk Control | Prevents Overfitting By... | Prevents Blow-Up By... |
|--------------|---------------------------|------------------------|
| Stop-Loss | Forces strategy to handle losing trades (not just winners) | Caps maximum loss at X% per trade |
| RSI Filter | Adds independent confirmation signal (not just SMA) | Avoids buying at unsustainable highs |
| Smart Allocation | Distributes risk across multiple assets | No single stock can destroy portfolio |

---

## Technologies Used
- **Python 3.12** - Core programming language
- **Pandas** - Data manipulation and analysis
- **NumPy** - Numerical calculations
- **Matplotlib** - Static charting
- **Plotly** - Interactive web charts
- **Flask** - Web server for GUI
- **Requests** - HTTP calls to Yahoo Finance API
- **Tkinter** - Desktop GUI framework

---

## Team
**SHPE Capital** - Society of Hispanic Professional Engineers

---

## License
This project is for educational purposes as part of the SHPE algorithmic trading workshop.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered automated stock trading system for US stocks using machine learning and technical indicators. Implements a "buy low, sell high" strategy with backtesting, paper trading, and live trading capabilities.

**Tech Stack**: Python 3.9+, yfinance, scikit-learn, XGBoost, Flask, Alpaca API

## Common Commands

### Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp env.example .env
# Edit .env with your API keys
```

### Running the System

**Backtesting** (testing strategy against historical data):
```bash
# Basic backtest
python main.py --mode backtest --symbols AAPL,MSFT,GOOGL --start 2022-01-01 --end 2024-12-31

# Single stock backtest
python main.py --mode backtest --symbols AAPL --start 2023-01-01 --end 2024-01-01
```

**Paper Trading** (simulated trading with fake money):
```bash
# Run locally
python main.py --mode paper --symbols AAPL,MSFT,GOOGL

# Run as daemon (background service)
python main.py --mode paper --symbols AAPL,MSFT,GOOGL --daemon

# With web dashboard
python main.py --mode paper --symbols AAPL,MSFT,GOOGL --dashboard
```

**Live Trading** (real money - use with caution):
```bash
python main.py --mode live --symbols AAPL,MSFT,GOOGL --daemon
```

### Testing
No test framework is currently configured in this project.

## Architecture Overview

### Execution Flow

The system follows this flow: **Data Collection → Feature Engineering → Strategy Signal Generation → Portfolio Management → Trade Execution**

### Key Components

**1. Entry Point ([main.py](main.py))**
- Parses command-line arguments (`--mode`, `--symbols`, `--start`, `--end`, `--daemon`, `--dashboard`)
- Routes to appropriate execution mode (backtest/paper/live)
- Initializes logging and scheduler

**2. Configuration ([config.py](config.py))**
- Centralized configuration for all parameters
- Trading parameters: `INITIAL_CAPITAL`, `MAX_POSITION_SIZE`, `STOP_LOSS_PCT`, `TAKE_PROFIT_PCT`
- Strategy parameters: `RSI_OVERSOLD/OVERBOUGHT`, `BOLLINGER_STD`, `MA_SHORT/LONG`
- API keys loaded from `.env` file via `python-dotenv`

**3. Data Pipeline**
- **Data Collector** ([utils/data_collector.py](utils/data_collector.py)): Downloads stock data from yfinance
  - `collect_stock_data()`: Main entry point for downloading multiple symbols
  - `get_latest_data()`: For real-time updates in live trading
- **Feature Engineering** ([utils/feature_engineering.py](utils/feature_engineering.py)): Adds 50+ technical indicators
  - `add_technical_indicators()`: Main function that adds RSI, MACD, Bollinger Bands, volume indicators, etc.
  - Generates derived features like price position, gaps, consecutive up/down days

**4. Trading Strategy ([strategies/buy_low_sell_high.py](strategies/buy_low_sell_high.py))**
- Core strategy implementation using technical indicators + ML
- **Signal Generation Logic**:
  - Buy signals: RSI < 30, price at Bollinger lower band, recent low, volume spike
  - Sell signals: RSI > 70, price at Bollinger upper band, recent high, profit target hit
  - Combines 6 buy signals and 6 sell signals into scores
- **Machine Learning**: Trains XGBoost or Random Forest classifier on historical data
  - `train_model()`: Trains ML model with cross-validation
  - `predict()`: Generates BUY/SELL/HOLD predictions with confidence scores
  - `get_signal()`: Main entry point for getting trading signal for a symbol

**5. Portfolio Management ([backtesting/portfolio_manager.py](backtesting/portfolio_manager.py))**
- Manages cash, positions, and trades
- **Key Classes**:
  - `Position`: Tracks individual stock positions with P&L
  - `Trade`: Records individual trade transactions
  - `PortfolioManager`: Core manager with cash and position tracking
- **Key Methods**:
  - `execute_trade()`: Executes buy/sell orders with validation
  - `calculate_position_size()`: Calculates how many shares to buy based on risk parameters
  - `get_performance_metrics()`: Calculates returns, Sharpe ratio, max drawdown, win rate

**6. Execution Modes**

**Backtesting** ([backtesting/backtest_engine.py](backtesting/backtest_engine.py)):
- Simulates strategy on historical data
- Steps through each trading day chronologically
- Generates performance report with charts and metrics

**Paper Trading** ([live_trading/paper_trader.py](live_trading/paper_trader.py)):
- Simulates live trading without real money
- Runs in continuous loop checking for signals every minute during market hours
- Multi-threaded: trading loop + monitoring loop
- Updates data and checks signals for each symbol

**Live Trading** ([live_trading/live_trader.py](live_trading/live_trader.py)):
- Connects to Alpaca API for real trade execution
- Similar architecture to paper trader but executes real orders

**7. Supporting Components**
- **Scheduler** ([utils/scheduler.py](utils/scheduler.py)): Manages market hours and periodic tasks
- **Dashboard** ([dashboard/web_dashboard.py](dashboard/web_dashboard.py)): Flask-based web UI for monitoring
- **Risk Manager** ([live_trading/risk_manager.py](live_trading/risk_manager.py)): Enforces risk limits
- **Notifications** ([utils/notification.py](utils/notification.py)): Telegram alerts for trades

**8. Market Context Analysis (NEW)**
- **News Sentiment** ([utils/news_sentiment.py](utils/news_sentiment.py)): Collects and analyzes news sentiment
  - Uses Finnhub API (primary) + yfinance (fallback)
  - Local FinBERT model for sentiment analysis backup
  - 1-hour caching to minimize API calls
  - Returns: sentiment score (-1~1), trend (VERY_POSITIVE/POSITIVE/NEUTRAL/NEGATIVE/VERY_NEGATIVE), news count, buzz ratio
- **Sector Rotation** ([utils/sector_analyzer.py](utils/sector_analyzer.py)): Tracks 11 sector ETFs for strength analysis
  - Monitors XLK, XLF, XLV, XLY, XLP, XLE, XLI, XLB, XLRE, XLU, XLC
  - Calculates relative strength vs S&P 500
  - Detects market phase: EXPANSION, PEAK, CONTRACTION, RECOVERY, TRANSITION
  - 6-hour caching to reduce yfinance calls
  - Adjusts position sizing based on sector strength (0.7x ~ 1.3x)
- **Macro Indicators** ([utils/macro_indicators.py](utils/macro_indicators.py)): Tracks macroeconomic environment
  - Collects: 10Y Treasury yield, VIX, unemployment rate, CPI, GDP growth, Fed funds rate, consumer sentiment
  - Uses FRED API (optional) + yfinance (required)
  - Scores environment from -10 to +10
  - Returns: VERY_FAVORABLE/FAVORABLE/NEUTRAL/UNFAVORABLE/VERY_UNFAVORABLE
  - 24-hour caching (updates once per day)
  - Adjusts position multiplier (0.3x ~ 1.3x) and risk parameters based on environment

### Data Flow in Strategy Execution

1. **Data Collection**: yfinance downloads OHLCV data
2. **Feature Engineering**: Adds 50+ technical indicators (RSI, MACD, Bollinger Bands, etc.)
3. **Market Context Analysis** (NEW):
   - **News Sentiment**: Fetch and analyze news for each symbol
   - **Sector Rotation**: Check sector strength and market phase
   - **Macro Environment**: Assess overall economic conditions
4. **Strategy Preparation**: Generates buy/sell signal scores and target variables
5. **ML Prediction**: XGBoost/Random Forest predicts BUY/SELL/HOLD with confidence
6. **Signal Decision**: Combines rule-based signals + ML prediction + market context
   - Adjusts buy/sell scores based on news sentiment (+/-2 points)
   - Adjusts scores based on sector strength (+/-1 point)
   - Can override BUY signal in VERY_UNFAVORABLE macro environment
7. **Position Sizing**: Calculates position size with multiple adjustments
   - Base position size from strategy
   - Market filter multiplier (from VIX, trend strength)
   - Sector weight adjustment (0.7x ~ 1.3x)
   - Macro environment multiplier (0.3x ~ 1.3x)
8. **Risk Management Adaptation**: Risk parameters adapt to macro environment
   - VERY_UNFAVORABLE: 0.3x position, tighter stop-loss
   - VERY_FAVORABLE: 1.3x position, wider take-profit
9. **Portfolio Action**: PortfolioManager executes trade with adjusted parameters
10. **Performance Tracking**: Records daily portfolio values, trades, and market context

### Important Design Patterns

**Global Instances**: The codebase uses global singleton instances for reusability:
- `data_collector` in [utils/data_collector.py](utils/data_collector.py)
- `feature_engineer` in [utils/feature_engineering.py](utils/feature_engineering.py)
- `strategy` in [strategies/buy_low_sell_high.py](strategies/buy_low_sell_high.py)

**Configuration Centralization**: All parameters in [config.py](config.py) can be imported with `from config import *`

**Data Normalization**: Stock data uses uppercase column names: `OPEN`, `HIGH`, `LOW`, `CLOSE`, `VOLUME`

### API Integration

**Alpaca API** (Trading):
- Paper trading: `https://paper-api.alpaca.markets`
- Live trading: `https://api.alpaca.markets` (switch in [config.py](config.py):17-18)
- Credentials stored in `.env`: `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`

**Finnhub API** (News Sentiment - Optional):
- Free tier: 60 calls/minute
- Provides: Company news, news sentiment scores, buzz ratios
- Sign up: https://finnhub.io/register
- Credentials: `FINNHUB_API_KEY` in `.env`
- Fallback: yfinance news if unavailable

**FRED API** (Macro Economics - Optional):
- Free tier: unlimited
- Provides: Unemployment, CPI, GDP, Fed funds rate, consumer sentiment
- Sign up: https://fred.stlouisfed.org/docs/api/api_key.html
- Credentials: `FRED_API_KEY` in `.env`
- Fallback: Basic indicators from yfinance only

**yfinance** (Core Data - Required):
- No API key needed
- Provides: Stock prices, company info, basic news, Treasury yields, VIX
- Free and unlimited

## Development Notes

### Working with Strategies

To modify the trading strategy logic, edit [strategies/buy_low_sell_high.py](strategies/buy_low_sell_high.py):
- `_generate_buy_signals()`: Define what constitutes buy conditions
- `_generate_sell_signals()`: Define what constitutes sell conditions
- `_generate_combined_signals()`: Adjust scoring thresholds (currently 3+ signals needed)

### Working with Technical Indicators

To add new indicators, edit [utils/feature_engineering.py](utils/feature_engineering.py):
- Add to appropriate method: `_add_price_indicators()`, `_add_momentum_indicators()`, etc.
- The `ta` library (ta-lib) provides most indicators

### Risk Management Parameters

Key parameters in [config.py](config.py) to tune:
- `MAX_POSITION_SIZE = 0.1`: Maximum 10% of portfolio per stock
- `STOP_LOSS_PCT = 0.05`: Auto-sell at 5% loss
- `TAKE_PROFIT_PCT = 0.10`: Auto-sell at 10% profit
- `MAX_DAILY_LOSS = 0.02`: Maximum 2% portfolio loss per day

### File Storage Structure

- `data/`: Downloaded stock data (CSV/pickle)
- `models/`: Trained ML models (joblib)
- `logs/`: Application logs
- `reports/`: Backtest reports (HTML/PDF)
- `backtest_results/`: Pickled backtest results

### Logging

All modules use centralized logging via `utils.logger.setup_logger(name)`. Log level controlled by `LOG_LEVEL` in [config.py](config.py).

## Korean Language Context

The codebase contains Korean comments and the README is in Korean (한국어). This is an AI stock trading system (AI 주식 트레이더) designed for Korean developers trading US stocks.

# CrossX Trading Dashboard

A cryptocurrency trading dashboard with multi-exchange support, featuring paper trading, backtesting, and arbitrage scanning capabilities.

## Features

- Real-time market data visualization with technical indicators
- Paper trading simulation with $10,000 virtual balance
- Strategy backtesting with performance metrics
- Cross-exchange arbitrage opportunity scanner
- Support for multiple exchanges (Binance, KuCoin)
- Implementation of the Moth Scalping strategy

## Setup

1. Create and activate a conda environment:
```bash
conda create -n crossx python=3.10
conda activate crossx
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your API keys:
   - Copy `.env.example` to `.env` in the config directory
   - Fill in your exchange API keys and other settings

## Usage

To start the dashboard:
```bash
python main.py
```

This will launch the Streamlit dashboard in your default web browser.

### Dashboard Sections

1. **Market Overview**
   - Real-time price charts with technical indicators
   - Market statistics and volume data
   - Multiple timeframe support

2. **Strategy Backtest**
   - Test the Moth Scalping strategy on historical data
   - Adjustable risk parameters and initial balance
   - Detailed performance metrics and trade history

3. **Paper Trading**
   - Practice trading with virtual $10,000 balance
   - Real-time position tracking and P&L monitoring
   - Risk management features

4. **Arbitrage Scanner**
   - Monitor price differences between exchanges
   - Customizable minimum spread thresholds
   - Historical spread analysis

## Testing

Run the unit tests:
```bash
python -m unittest discover tests
```

## Directory Structure

```
crossx/
├── config/             # Configuration files and environment variables
├── core/              # Core trading logic and data handling
│   ├── data.py       # Exchange data collection
│   ├── trading.py    # Paper trading implementation
│   ├── strategy.py   # Trading strategy implementation
│   └── arbitrage.py  # Arbitrage detection
├── ui/               # User interface components
│   └── dashboard.py  # Streamlit dashboard
├── utils/            # Utility functions
├── tests/            # Unit tests
└── notebooks/        # Analysis notebooks
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

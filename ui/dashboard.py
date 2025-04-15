import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os

# Add the project root to the Python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.data import ExchangeDataCollector
from core.trading import PaperTrader
from core.strategy import Strategy
from core.arbitrage import ArbitrageDetector

# Page config
st.set_page_config(page_title="CrossX Dashboard", layout="wide")

# Initialize components
@st.cache_resource
def init_components():
    data_collector = ExchangeDataCollector()
    strategy = Strategy()
    paper_trader = PaperTrader()
    arbitrage_detector = ArbitrageDetector(data_collector)
    return data_collector, strategy, paper_trader, arbitrage_detector

data_collector, strategy, paper_trader, arbitrage_detector = init_components()

# Sidebar
st.sidebar.title("CrossX Dashboard")
selected_tab = st.sidebar.radio("Navigation", ["Market Overview", "Strategy Backtest", "Paper Trading", "Arbitrage Scanner"])

# Market Overview Tab
if selected_tab == "Market Overview":
    st.title("Market Overview")
    
    col1, col2 = st.columns(2)
    with col1:
        symbol = st.text_input("Symbol", value="BTC/USDT")
    with col2:
        exchange = st.selectbox("Exchange", ["binance", "kucoin"])
    
    timeframe = st.select_slider("Timeframe", 
                               options=['1m', '5m', '15m', '1h', '4h', '1d'],
                               value='5m')
    days = st.slider("Days of Data", min_value=1, max_value=30, value=5)
    
    if st.button("Fetch Data"):
        with st.spinner("Fetching market data..."):
            df = data_collector.get_historical_data(symbol, exchange, timeframe, days)
            if not df.empty:
                # Calculate indicators
                df = strategy.calculate_indicators(df)
                
                # Create price chart with indicators
                fig = make_subplots(rows=3, cols=1, 
                                  shared_xaxes=True,
                                  vertical_spacing=0.05,
                                  row_heights=[0.6, 0.2, 0.2])
                
                # Candlestick chart
                fig.add_trace(go.Candlestick(
                    x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name="OHLC"
                ), row=1, col=1)
                
                # Add EMAs
                fig.add_trace(go.Scatter(x=df.index, y=df['ema_8'], 
                                       name="EMA8", line=dict(color='blue')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['ema_21'], 
                                       name="EMA21", line=dict(color='orange')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['ema_55'], 
                                       name="EMA55", line=dict(color='red')), row=1, col=1)
                
                # MACD
                fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'],
                                   name="MACD Histogram"), row=2, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD_12_26_9'],
                                       name="MACD", line=dict(color='blue')), row=2, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MACDs_12_26_9'],
                                       name="Signal", line=dict(color='orange')), row=2, col=1)
                
                # RSI
                fig.add_trace(go.Scatter(x=df.index, y=df['rsi'],
                                       name="RSI", line=dict(color='purple')), row=3, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
                
                fig.update_layout(height=800)
                st.plotly_chart(fig, use_container_width=True)
                
                # Display current market stats
                ticker = data_collector.get_ticker(symbol, exchange)
                if ticker:
                    stats_col1, stats_col2, stats_col3 = st.columns(3)
                    with stats_col1:
                        st.metric("Last Price", f"${ticker['last']:.2f}")
                    with stats_col2:
                        st.metric("24h Volume", f"${ticker['quoteVolume']:.2f}")
                    with stats_col3:
                        change = ticker['percentage']
                        st.metric("24h Change", f"{change:.2f}%", 
                                 delta=f"{change:.2f}%")

# Strategy Backtest Tab
elif selected_tab == "Strategy Backtest":
    st.title("Strategy Backtest")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        symbol = st.text_input("Symbol", value="BTC/USDT")
    with col2:
        exchange = st.selectbox("Exchange", ["binance", "kucoin"])
    with col3:
        timeframe = st.select_slider("Timeframe", 
                                   options=['1m', '5m', '15m', '1h', '4h', '1d'],
                                   value='5m')
    
    risk_per_trade = st.slider("Risk per Trade (%)", 
                              min_value=0.5, max_value=5.0, value=2.0) / 100
    initial_balance = st.number_input("Initial Balance (USDT)", 
                                    min_value=100, value=10000)
    
    if st.button("Run Backtest"):
        with st.spinner("Running backtest..."):
            df = data_collector.get_historical_data(symbol, exchange, timeframe, days=30)
            if not df.empty:
                results = strategy.backtest(df, initial_balance, risk_per_trade)
                
                # Display metrics
                metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
                with metrics_col1:
                    st.metric("Total Trades", results['total_trades'])
                with metrics_col2:
                    st.metric("Win Rate", f"{results['win_rate']:.2f}%")
                with metrics_col3:
                    st.metric("Total Return", f"{results['total_return']:.2f}%")
                with metrics_col4:
                    st.metric("Max Drawdown", f"{results['max_drawdown']:.2f}%")
                
                # Plot equity curve
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    y=results['equity_curve'],
                    name="Equity Curve",
                    line=dict(color='green')
                ))
                fig.update_layout(title="Equity Curve", height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # Display trades table
                if results['trades']:
                    trades_df = pd.DataFrame(results['trades'])
                    trades_df['pnl'] = trades_df['pnl'].round(2)
                    trades_df['balance'] = trades_df['balance'].round(2)
                    st.dataframe(trades_df)

# Paper Trading Tab
elif selected_tab == "Paper Trading":
    st.title("Paper Trading")
    
    col1, col2 = st.columns(2)
    with col1:
        symbol = st.text_input("Symbol", value="BTC/USDT")
    with col2:
        exchange = st.selectbox("Exchange", ["binance", "kucoin"])
    
    # Display current position if any
    position = None
    for pos in paper_trader.open_positions.values():
        if pos.symbol == symbol:
            position = pos
            break
    
    if position:
        ticker = data_collector.get_ticker(symbol, exchange)
        if ticker:
            current_price = ticker['last']
            if position.side == 'long':
                pnl = (current_price - position.entry_price) / position.entry_price * 100
            else:
                pnl = (position.entry_price - current_price) / position.entry_price * 100
            
            pos_col1, pos_col2, pos_col3 = st.columns(3)
            with pos_col1:
                st.metric("Position Side", position.side.upper())
            with pos_col2:
                st.metric("Entry Price", f"${position.entry_price:.2f}")
            with pos_col3:
                st.metric("Unrealized P&L", f"{pnl:.2f}%", delta=f"{pnl:.2f}%")
    
    # Trading controls
    trade_col1, trade_col2 = st.columns(2)
    with trade_col1:
        if st.button("Long"):
            ticker = data_collector.get_ticker(symbol, exchange)
            if ticker:
                size = paper_trader.calculate_max_position_size(ticker['last'])
                trade = paper_trader.open_position(symbol, exchange, ticker['last'], 
                                                size, 'long')
                if trade:
                    st.success("Long position opened successfully!")
                else:
                    st.error("Failed to open position")
    
    with trade_col2:
        if st.button("Short"):
            ticker = data_collector.get_ticker(symbol, exchange)
            if ticker:
                size = paper_trader.calculate_max_position_size(ticker['last'])
                trade = paper_trader.open_position(symbol, exchange, ticker['last'], 
                                                size, 'short')
                if trade:
                    st.success("Short position opened successfully!")
                else:
                    st.error("Failed to open position")
    
    if position and st.button("Close Position"):
        ticker = data_collector.get_ticker(symbol, exchange)
        if ticker:
            trade = paper_trader.close_position(symbol, ticker['last'])
            if trade:
                st.success(f"Position closed with P&L: {trade.pnl:.2f}%")
    
    # Display account metrics
    st.subheader("Account Overview")
    metrics_col1, metrics_col2 = st.columns(2)
    with metrics_col1:
        st.metric("Current Balance", f"${paper_trader.current_balance:.2f}")
    with metrics_col2:
        pnl = (paper_trader.current_balance - paper_trader.initial_balance) / paper_trader.initial_balance * 100
        st.metric("Total P&L", f"{pnl:.2f}%", delta=f"{pnl:.2f}%")

# Arbitrage Scanner Tab
else:
    st.title("Arbitrage Scanner")
    
    col1, col2 = st.columns(2)
    with col1:
        symbols = st.multiselect("Symbols", ["BTC/USDT", "ETH/USDT", "BNB/USDT"], 
                               default=["BTC/USDT"])
    with col2:
        min_spread = st.slider("Minimum Spread (%)", 
                             min_value=0.1, max_value=5.0, value=1.0)
    
    if st.button("Scan for Opportunities"):
        exchanges = ["binance", "kucoin"]
        for symbol in symbols:
            opportunities = arbitrage_detector.find_opportunities(symbol, exchanges)
            
            if opportunities:
                st.subheader(f"Opportunities for {symbol}")
                for opp in opportunities:
                    if opp['spread_percent'] >= min_spread:
                        st.info(
                            f"Spread: {opp['spread_percent']:.2f}% | "
                            f"Buy from {opp['buy_exchange']} at ${opp['buy_price']:.2f} | "
                            f"Sell on {opp['sell_exchange']} at ${opp['sell_price']:.2f} | "
                            f"Potential profit: {opp['potential_profit_percent']:.2f}%"
                        )
            else:
                st.write(f"No opportunities found for {symbol}")
                
        # Display historical spreads
        st.subheader("Historical Spreads")
        for symbol in symbols:
            spreads_df = arbitrage_detector.get_historical_spreads(symbol, exchanges)
            if not spreads_df.empty:
                fig = go.Figure()
                for column in spreads_df.columns:
                    fig.add_trace(go.Scatter(
                        x=spreads_df.index,
                        y=spreads_df[column],
                        name=column
                    ))
                fig.update_layout(title=f"Historical Spreads - {symbol}", height=400)
                st.plotly_chart(fig, use_container_width=True)
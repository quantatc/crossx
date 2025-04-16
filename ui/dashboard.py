import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os
from streamlit_option_menu import option_menu
from streamlit_autorefresh import st_autorefresh

# Add the project root to the Python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.data import ExchangeDataCollector
from core.trading import PaperTrader
from core.strategy import Strategy
from core.arbitrage import ArbitrageDetector
from utils.symbol_manager import SymbolManager
from utils.metrics import MarketMetrics

# Page config
st.set_page_config(
    page_title="CrossX - Multi-Exchange Crypto Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add title and custom styling
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #262730;
        border-radius: 4px 4px 0px 0px;
        gap: 2px;
        padding: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1a1c24;
    }
    .dashboard-title {
        text-align: center;
        font-size: 2.5em;
        margin-bottom: 1em;
        color: #ffffff;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# Display dashboard title
st.markdown('<h1 class="dashboard-title">📊 CrossX</h1>', unsafe_allow_html=True)

# Initialize components
@st.cache_resource
def init_components():
    data_collector = ExchangeDataCollector()
    strategy = Strategy()
    paper_trader = PaperTrader()
    arbitrage_detector = ArbitrageDetector(data_collector)
    symbol_manager = SymbolManager()
    return data_collector, strategy, paper_trader, arbitrage_detector, symbol_manager

data_collector, strategy, paper_trader, arbitrage_detector, symbol_manager = init_components()

# Auto-refresh every 30 seconds
st_autorefresh(interval=30000, key="datarefresh")

# Sidebar
with st.sidebar:
    selected_tab = option_menu(
        "Navigation",
        ["Market Overview", "Trading Terminal", "Strategy Backtest", "Arbitrage Scanner"],
        icons=["graph-up", "currency-exchange", "clock-history", "arrows-angle-expand"],
        menu_icon="cast",
        default_index=0,
    )
    
    st.sidebar.markdown("### Symbol Settings")
    quote_currency = st.sidebar.selectbox("Quote Currency", ["USDT", "USD", "BTC"], index=0)
    top_coins_only = st.sidebar.checkbox("Top 100 Coins Only", value=True)
    
    exchanges = st.sidebar.multiselect(
        "Exchanges",
        ["binance", "kucoin", "okx", "bybit"],
        default=["binance", "kucoin"]
    )

# Get available symbols
@st.cache_data(ttl=3600)
def get_available_symbols(exchanges, quote_currency, top_coins_only):
    return symbol_manager.get_common_symbols(exchanges, quote_currency, top_coins_only)

symbols = get_available_symbols(exchanges, quote_currency, top_coins_only)

# Market Overview Tab
if selected_tab == "Market Overview":
    st.title("Market Overview")
    
    # Market Summary Cards
    col1, col2, col3 = st.columns(3)
    
    # Symbol Selection
    selected_symbol = st.selectbox(
        "Select Trading Pair",
        symbols,
        index=0 if "BTC/USDT" in symbols else 0
    )
    
    # Timeframe Selection
    timeframe_col1, timeframe_col2 = st.columns([3, 1])
    with timeframe_col1:
        timeframe = st.select_slider(
            "Timeframe",
            options=['1m', '5m', '15m', '1h', '4h', '1d'],
            value='5m'
        )
    with timeframe_col2:
        days = st.number_input("Days of Data", min_value=1, max_value=30, value=5)
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["Price Action", "Technical Analysis", "Exchange Comparison"])
    
    with tab1:
        with st.spinner("Loading market data..."):
            # Fetch and process data
            dfs = {}
            current_prices = {}
            for exchange in exchanges:
                df = data_collector.get_historical_data(selected_symbol, exchange, timeframe, days)
                if not df.empty:
                    dfs[exchange] = MarketMetrics.calculate_indicators(df)
                    current_prices[exchange] = df['close'].iloc[-1]
            
            if dfs:
                # Create main chart
                fig = make_subplots(
                    rows=3, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.05,
                    row_heights=[0.6, 0.2, 0.2],
                    subplot_titles=("Price", "Volume", "RSI")
                )
                
                colors = {'binance': '#F0B90B', 'kucoin': '#26A17B', 'okx': '#121212', 'bybit': '#FFD700'}
                
                for exchange, df in dfs.items():
                    # Candlestick chart
                    fig.add_trace(
                        go.Candlestick(
                            x=df.index,
                            open=df['open'],
                            high=df['high'],
                            low=df['low'],
                            close=df['close'],
                            name=f"{exchange.capitalize()} OHLC",
                            increasing_line_color=colors.get(exchange, '#26A69A'),
                            decreasing_line_color='#EF5350'
                        ),
                        row=1, col=1
                    )
                    
                    # Volume
                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=df['volume'],
                            name=f"{exchange.capitalize()} Volume",
                            marker_color=colors.get(exchange, '#888888'),
                            opacity=0.3
                        ),
                        row=2, col=1
                    )
                    
                    # RSI
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['rsi'],
                            name=f"{exchange.capitalize()} RSI",
                            line=dict(color=colors.get(exchange, '#888888'))
                        ),
                        row=3, col=1
                    )
                
                # Add RSI levels
                fig.add_hline(y=70, line_dash="dash", line_color="#ff0000", row=3, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="#00ff00", row=3, col=1)
                
                fig.update_layout(
                    height=800,
                    template="plotly_dark",
                    showlegend=True,
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01
                    ),
                    margin=dict(l=50, r=50, t=30, b=50)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Market Metrics
                for exchange, df in dfs.items():
                    metrics = MarketMetrics.calculate_metrics(df)
                    summary = MarketMetrics.get_summary_metrics(df)
                    
                    st.subheader(f"{exchange.capitalize()} Market Metrics")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Price",
                            f"${metrics['last_price']:.2f}",
                            f"{metrics['price_change_24h']:.2f}%"
                        )
                    with col2:
                        st.metric(
                            "24h Range",
                            f"${metrics['high_24h']:.2f}",
                            f"${metrics['low_24h']:.2f}"
                        )
                    with col3:
                        st.metric(
                            "24h Volume",
                            f"${metrics['volume_24h']:,.0f}"
                        )
                    with col4:
                        st.metric(
                            "Volatility",
                            f"{metrics['volatility_24h']:.2f}%"
                        )
    
    with tab2:
        if dfs:
            for exchange, df in dfs.items():
                st.subheader(f"{exchange.capitalize()} Technical Analysis")
                
                # Technical Indicators
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    rsi = df['rsi'].iloc[-1]
                    rsi_color = "🟢" if rsi < 30 else "🔴" if rsi > 70 else "⚪"
                    st.metric("RSI", f"{rsi_color} {rsi:.1f}")
                
                with col2:
                    macd = df['macd_line'].iloc[-1]
                    signal = df['macd_signal'].iloc[-1]
                    macd_color = "🟢" if macd > signal else "🔴"
                    st.metric("MACD", f"{macd_color} {macd:.2f}")
                
                with col3:
                    trend = "🟢 Bullish" if df['close'].iloc[-1] > df['sma_50'].iloc[-1] else "🔴 Bearish"
                    st.metric("Trend", trend)
                
                with col4:
                    st.metric("ATR", f"{df['atr'].iloc[-1]:.2f}")
    
    with tab3:
        if len(current_prices) > 1:
            st.subheader("Exchange Price Comparison")
            
            # Calculate arbitrage opportunities
            arb_metrics = MarketMetrics.calculate_arbitrage_metrics(current_prices)
            
            # Display opportunities
            if arb_metrics['opportunities']:
                st.warning("Arbitrage Opportunities Detected!")
                for opp in arb_metrics['opportunities']:
                    st.info(
                        f"💰 Potential {opp['spread']:.2f}% profit: "
                        f"Buy on {opp['buy_exchange']} (${opp['buy_price']:.2f}) → "
                        f"Sell on {opp['sell_exchange']} (${opp['sell_price']:.2f})"
                    )
            
            # Display price comparison matrix
            spread_df = pd.DataFrame(
                [[f"{float(arb_metrics['spreads'].get((k, ex), 0)):.2f}%" if k != ex else "-" 
                  for ex in exchanges] 
                 for k in exchanges],
                index=exchanges,
                columns=exchanges
            )
            st.dataframe(spread_df, use_container_width=True)

elif selected_tab == "Trading Terminal":
    st.title("Trading Terminal")
    
    # Layout
    left_col, right_col = st.columns([2, 1])
    
    with left_col:
        # Trading pair selection
        selected_symbol = st.selectbox("Select Trading Pair", symbols)
        selected_exchange = st.selectbox("Select Exchange", exchanges)
        
        # Fetch and display current market data
        with st.spinner("Loading market data..."):
            df = data_collector.get_historical_data(selected_symbol, selected_exchange, '1m', days=1)
            if not df.empty:
                df = MarketMetrics.calculate_indicators(df)
                
                # Price chart with indicators
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.05,
                    row_heights=[0.7, 0.3]
                )
                
                fig.add_trace(
                    go.Candlestick(
                        x=df.index,
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'],
                        name="OHLC"
                    ),
                    row=1, col=1
                )
                
                # Add EMAs
                fig.add_trace(go.Scatter(x=df.index, y=df['ema_8'], 
                    name="EMA8", line=dict(color='blue')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['ema_21'], 
                    name="EMA21", line=dict(color='orange')), row=1, col=1)
                
                # Volume bars
                colors = ['red' if row['open'] > row['close'] else 'green' 
                         for _, row in df.iterrows()]
                fig.add_trace(go.Bar(x=df.index, y=df['volume'],
                    marker_color=colors, name="Volume"), row=2, col=1)
                
                fig.update_layout(
                    height=600,
                    template="plotly_dark",
                    xaxis_rangeslider_visible=False
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    with right_col:
        st.subheader("Trading Controls")
        
        # Account Overview
        current_balance = paper_trader.current_balance
        st.metric("Available Balance", f"${current_balance:.2f}")
        
        # Position sizing
        amount = st.number_input(
            "Trade Amount (USDT)",
            min_value=10.0,
            max_value=current_balance,
            value=min(100.0, current_balance),
            step=10.0
        )
        
        # Trading buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Long 📈", type="primary"):
                ticker = data_collector.get_ticker(selected_symbol, selected_exchange)
                if ticker and ticker['last'] > 0:
                    size = amount / ticker['last']
                    trade = paper_trader.open_position(
                        selected_symbol,
                        selected_exchange,
                        ticker['last'],
                        size,
                        'long'
                    )
                    if trade:
                        st.success(f"Opened LONG position at ${ticker['last']:.2f}")
                    else:
                        st.error("Failed to open position")
        
        with col2:
            if st.button("Short 📉", type="primary"):
                ticker = data_collector.get_ticker(selected_symbol, selected_exchange)
                if ticker and ticker['last'] > 0:
                    size = amount / ticker['last']
                    trade = paper_trader.open_position(
                        selected_symbol,
                        selected_exchange,
                        ticker['last'],
                        size,
                        'short'
                    )
                    if trade:
                        st.success(f"Opened SHORT position at ${ticker['last']:.2f}")
                    else:
                        st.error("Failed to open position")
        
        with col3:
            if st.button("Close ⭕"):
                ticker = data_collector.get_ticker(selected_symbol, selected_exchange)
                if ticker:
                    trade = paper_trader.close_position(selected_symbol, ticker['last'])
                    if trade:
                        pnl_percent = (trade.pnl / amount) * 100
                        st.success(f"Closed position with P&L: ${trade.pnl:.2f} ({pnl_percent:.2f}%)")
                    else:
                        st.warning("No open position to close")
        
        # Open Positions
        st.subheader("Open Positions")
        if paper_trader.open_positions:
            for symbol, position in paper_trader.open_positions.items():
                ticker = data_collector.get_ticker(symbol, position.exchange)
                if ticker:
                    current_price = ticker['last']
                    if position.side == 'long':
                        unrealized_pnl = (current_price - position.entry_price) * position.position_size
                    else:
                        unrealized_pnl = (position.entry_price - current_price) * position.position_size
                    
                    st.info(
                        f"Symbol: {symbol}\n\n"
                        f"Side: {position.side.upper()}\n\n"
                        f"Entry: ${position.entry_price:.2f}\n\n"
                        f"Current: ${current_price:.2f}\n\n"
                        f"Unrealized P&L: ${unrealized_pnl:.2f}"
                    )
        else:
            st.info("No open positions")
        
        # Trade History
        st.subheader("Trade History")
        if paper_trader.closed_trades:
            history_df = pd.DataFrame([
                {
                    'Symbol': t.symbol,
                    'Side': t.side,
                    'Entry': t.entry_price,
                    'Exit': t.exit_price,
                    'P&L': t.pnl,
                    'Time': t.exit_time
                }
                for t in paper_trader.closed_trades
            ])
            st.dataframe(history_df, use_container_width=True)
        else:
            st.info("No trade history")

elif selected_tab == "Strategy Backtest":
    st.title("Strategy Backtest")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        backtest_symbol = st.selectbox("Select Symbol", symbols, key='backtest_symbol')
    with col2:
        backtest_exchange = st.selectbox("Select Exchange", exchanges, key='backtest_exchange')
    with col3:
        backtest_days = st.number_input("Days to Backtest", min_value=5, max_value=90, value=30)
    
    # Strategy parameters
    st.subheader("Strategy Parameters")
    param_col1, param_col2 = st.columns(2)
    
    with param_col1:
        initial_balance = st.number_input(
            "Initial Balance (USDT)",
            min_value=100.0,
            max_value=1000000.0,
            value=10000.0
        )
    with param_col2:
        risk_per_trade = st.slider(
            "Risk per Trade (%)",
            min_value=0.1,
            max_value=5.0,
            value=1.0
        ) / 100.0
    
    if st.button("Run Backtest", type="primary"):
        with st.spinner("Running backtest..."):
            # Fetch historical data
            df = data_collector.get_historical_data(
                backtest_symbol,
                backtest_exchange,
                timeframe='5m',
                days=backtest_days
            )
            
            if not df.empty:
                # Run backtest
                results = strategy.backtest(df, initial_balance, risk_per_trade)
                
                # Display results
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Total Return",
                        f"{results['total_return']:.2f}%",
                        delta=f"{results['total_return']:.2f}%"
                    )
                with col2:
                    st.metric("Win Rate", f"{results['win_rate']:.2f}%")
                with col3:
                    st.metric("Total Trades", results['total_trades'])
                with col4:
                    st.metric("Max Drawdown", f"{results['max_drawdown']:.2f}%")
                
                # Equity curve
                st.subheader("Equity Curve")
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    y=results['equity_curve'],
                    name="Portfolio Value",
                    line=dict(color='green')
                ))
                fig.update_layout(
                    template="plotly_dark",
                    height=400,
                    yaxis_title="Portfolio Value (USDT)"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Trade list
                if results['trades']:
                    st.subheader("Trade History")
                    trades_df = pd.DataFrame(results['trades'])
                    trades_df['pnl'] = trades_df['pnl'].round(2)
                    trades_df['entry_price'] = trades_df['entry_price'].round(2)
                    trades_df['exit_price'] = trades_df['exit_price'].round(2)
                    st.dataframe(trades_df, use_container_width=True)

else:  # Arbitrage Scanner
    st.title("Arbitrage Scanner")
    
    # Settings
    st.subheader("Scanner Settings")
    col1, col2 = st.columns(2)
    
    with col1:
        scan_symbols = st.multiselect(
            "Select Symbols to Scan",
            symbols,
            default=[s for s in symbols if 'BTC' in s or 'ETH' in s][:2]
        )
    
    with col2:
        min_spread = st.slider(
            "Minimum Spread (%)",
            min_value=0.1,
            max_value=5.0,
            value=0.5,
            step=0.1
        )
    
    if st.button("Scan for Opportunities", type="primary"):
        with st.spinner("Scanning exchanges..."):
            all_opportunities = []
            historical_spreads = {}
            
            for symbol in scan_symbols:
                # Get current opportunities
                opportunities = arbitrage_detector.find_opportunities(symbol, exchanges)
                all_opportunities.extend(opportunities)
                
                # Get historical spreads
                spreads_df = arbitrage_detector.get_historical_spreads(symbol, exchanges)
                if not spreads_df.empty:
                    historical_spreads[symbol] = spreads_df
            
            # Display current opportunities
            if all_opportunities:
                st.subheader("Live Arbitrage Opportunities")
                
                for opp in all_opportunities:
                    if opp['spread_percent'] >= min_spread:
                        st.success(
                            f"💰 {opp['spread_percent']:.2f}% spread on {opp['symbol']}\n\n"
                            f"Buy on {opp['buy_exchange']} at ${opp['buy_price']:.2f}\n\n"
                            f"Sell on {opp['sell_exchange']} at ${opp['sell_price']:.2f}\n\n"
                            f"Potential profit after fees: {opp['potential_profit_percent']:.2f}%"
                        )
            else:
                st.info("No arbitrage opportunities found above the minimum spread threshold")
            
            # Display historical spread analysis
            if historical_spreads:
                st.subheader("Historical Spread Analysis")
                
                for symbol, spreads_df in historical_spreads.items():
                    st.write(f"**{symbol} Spread History**")
                    
                    fig = go.Figure()
                    for col in spreads_df.columns:
                        fig.add_trace(go.Scatter(
                            x=spreads_df.index,
                            y=spreads_df[col],
                            name=col,
                            line=dict(width=1)
                        ))
                    
                    fig.update_layout(
                        template="plotly_dark",
                        height=400,
                        yaxis_title="Spread (%)",
                        showlegend=True
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Spread statistics
                    stats = pd.DataFrame({
                        'Mean Spread (%)': spreads_df.mean(),
                        'Max Spread (%)': spreads_df.max(),
                        'Min Spread (%)': spreads_df.min(),
                        'Std Dev (%)': spreads_df.std()
                    }).round(2)
                    
                    st.dataframe(stats, use_container_width=True)
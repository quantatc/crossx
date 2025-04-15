### This is the script I use to run on VPS for a simple strategy
```
from binance.client import Client
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
import pandas_ta as ta

# Load environment variables
load_dotenv()
api_key = os.getenv("api_key")
secret_key = os.getenv("secret_key")

class BinanceClient:
    def __init__(self):
        self.client = Client(api_key=api_key, api_secret=secret_key, tld="com", testnet=True)

    def get_historical_data(self, symbol, days, interval="5m"):
        now = datetime.utcnow()
        past = str(now - timedelta(days=days))
        bars = self.client.futures_historical_klines(
            symbol=symbol, interval=interval, start_str=past, limit=1000
        )
        df = pd.DataFrame(bars)
        df["Date"] = pd.to_datetime(df.iloc[:, 0], unit="ms")
        df.columns = [
            "Open Time", "Open", "High", "Low", "Close", "Volume",
            "Close Time", "Quote Asset Volume", "Number of Trades",
            "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore", "Date"
        ]
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
        df.set_index("Date", inplace=True)
        for column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        return df

class Strategy:
    def __init__(self, atr_period=16):
        self.atr_period = atr_period

    def generate_signals(self, ohlc):
        ohlc["rsi"] = ta.rsi(ohlc.Close)
        ohlc["ema50"] = ta.ema(ohlc.Close, length=50)
        ohlc["ema21"] = ta.ema(ohlc.Close, length=21)
        ohlc["ema200"] = ta.ema(ohlc.Close, length=200)
        ohlc["signal"] = np.where(
            (ohlc["ema21"] > ohlc["ema50"]) & (ohlc["ema50"] > ohlc["ema200"]) & (ohlc["rsi"] > 50),
            1,
            np.where(
                (ohlc["ema21"] < ohlc["ema50"]) & (ohlc["ema50"] < ohlc["ema200"]) & (ohlc["rsi"] < 50),
                -1,
                0
            )
        )
        return ohlc

class TradeExecutor:
    def __init__(self, client):
        self.client = client

    def place_order(self, symbol, side, position, units, stop_loss, take_profit):
        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=Client.ORDER_TYPE_MARKET,
                quantity=units,
                positionSide=position
            )
            return order
        except Exception as e:
            logging.error(f"Error placing order: {e}")
            return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    symbols = ["BTCUSDT", "ETHUSDT"]
    binance_client = BinanceClient()
    strategy = Strategy()

    for symbol in symbols:
        data = binance_client.get_historical_data(symbol, days=5)
        if data.empty:
            logging.warning(f"No data for {symbol}")
            continue
        data = strategy.generate_signals(data)
        logging.info(f"Generated signals for {symbol}")
```
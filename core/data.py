import ccxt
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
from typing import Optional, Dict

# Load environment variables
load_dotenv()

class ExchangeDataCollector:
    def __init__(self):
        self.exchanges = {}
        self.data_cache = {}
        self.ticker_cache = {}
        self.last_ticker_update = {}
    
    def _get_exchange(self, exchange_id: str) -> ccxt.Exchange:
        """Get or create exchange instance"""
        if exchange_id not in self.exchanges:
            try:
                exchange_class = getattr(ccxt, exchange_id)
                self.exchanges[exchange_id] = exchange_class({
                    'enableRateLimit': True,
                    'timeout': 30000,
                })
            except Exception as e:
                logging.error(f"Error initializing {exchange_id}: {e}")
                return None
        return self.exchanges[exchange_id]

    def get_historical_data(self, symbol: str, exchange_id: str, 
                          timeframe: str = '5m', days: int = 5) -> pd.DataFrame:
        """Fetch historical OHLCV data"""
        cache_key = f"{exchange_id}_{symbol}_{timeframe}_{days}"
        
        # Check cache (valid for 1 minute)
        if cache_key in self.data_cache:
            cache_time, df = self.data_cache[cache_key]
            if (datetime.now() - cache_time).total_seconds() < 60:
                return df

        try:
            exchange = self._get_exchange(exchange_id)
            if not exchange:
                return pd.DataFrame()

            # Calculate timeframe in milliseconds
            timeframe_ms = {
                '1m': 60000,
                '5m': 300000,
                '15m': 900000,
                '1h': 3600000,
                '4h': 14400000,
                '1d': 86400000
            }
            
            since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            # Fetch OHLCV data
            ohlcv = exchange.fetch_ohlcv(
                symbol, 
                timeframe=timeframe,
                since=since,
                limit=1000
            )
            
            if not ohlcv:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Cache the result
            self.data_cache[cache_key] = (datetime.now(), df)
            return df
            
        except Exception as e:
            logging.error(f"Error fetching data for {symbol} on {exchange_id}: {e}")
            return pd.DataFrame()

    def get_ticker(self, symbol: str, exchange_id: str) -> Optional[Dict]:
        """Get current ticker data"""
        cache_key = f"{exchange_id}_{symbol}"
        
        # Check cache (valid for 10 seconds)
        current_time = datetime.now()
        if cache_key in self.ticker_cache and cache_key in self.last_ticker_update:
            if (current_time - self.last_ticker_update[cache_key]).total_seconds() < 10:
                return self.ticker_cache[cache_key]

        try:
            exchange = self._get_exchange(exchange_id)
            if not exchange:
                return None

            ticker = exchange.fetch_ticker(symbol)
            if ticker:
                self.ticker_cache[cache_key] = ticker
                self.last_ticker_update[cache_key] = current_time
                return ticker
                
        except Exception as e:
            logging.error(f"Error fetching ticker for {symbol} on {exchange_id}: {e}")
            
        return None

    def get_orderbook(self, symbol: str, exchange_id: str, limit: int = 20) -> Optional[Dict]:
        """Get current orderbook"""
        try:
            exchange = self._get_exchange(exchange_id)
            if not exchange:
                return None

            return exchange.fetch_order_book(symbol, limit=limit)
            
        except Exception as e:
            logging.error(f"Error fetching orderbook for {symbol} on {exchange_id}: {e}")
            return None
import ccxt
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
from typing import Dict, List

# Load environment variables
load_dotenv()

class ExchangeDataCollector:
    def __init__(self):
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self.setup_exchanges()

    def setup_exchanges(self):
        """Initialize connection to multiple exchanges"""
        exchange_configs = {
            'binance': {
                'apiKey': os.getenv('BINANCE_API_KEY'),
                'secret': os.getenv('BINANCE_SECRET'),
                'enableRateLimit': True
            },
            'kucoin': {
                'apiKey': os.getenv('KUCOIN_API_KEY'),
                'secret': os.getenv('KUCOIN_SECRET'),
                'password': os.getenv('KUCOIN_PASSPHRASE'),
                'enableRateLimit': True
            }
        }
        
        for exchange_id, config in exchange_configs.items():
            try:
                exchange_class = getattr(ccxt, exchange_id)
                # If API keys are not provided, initialize exchange without authentication
                if not config['apiKey'] or config['apiKey'] == 'your_binance_api_key':
                    self.exchanges[exchange_id] = exchange_class({
                        'enableRateLimit': True
                    })
                else:
                    self.exchanges[exchange_id] = exchange_class(config)
                logging.info(f"Initialized {exchange_id} in {'authenticated' if config['apiKey'] else 'public'} mode")
            except Exception as e:
                logging.error(f"Error initializing {exchange_id}: {e}")
                # Still initialize exchange in public mode if authentication fails
                try:
                    self.exchanges[exchange_id] = exchange_class({
                        'enableRateLimit': True
                    })
                    logging.info(f"Initialized {exchange_id} in public mode after auth failure")
                except Exception as e:
                    logging.error(f"Failed to initialize {exchange_id} in public mode: {e}")

    def get_historical_data(self, symbol: str, exchange_id: str, timeframe: str = '5m', days: int = 5) -> pd.DataFrame:
        """Fetch historical OHLCV data from specified exchange"""
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                raise ValueError(f"Exchange {exchange_id} not initialized")

            since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            for column in df.columns:
                df[column] = pd.to_numeric(df[column], errors='coerce')
            return df

        except Exception as e:
            logging.error(f"Error fetching data from {exchange_id}: {e}")
            return pd.DataFrame()

    def get_ticker(self, symbol: str, exchange_id: str) -> dict:
        """Get current ticker data from specified exchange"""
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                raise ValueError(f"Exchange {exchange_id} not initialized")
            
            ticker = exchange.fetch_ticker(symbol)
            # Ensure all required fields are present
            required_fields = ['last', 'ask', 'bid', 'quoteVolume']
            for field in required_fields:
                if field not in ticker or ticker[field] is None:
                    ticker[field] = ticker.get('last', 0)
            ticker['percentage'] = ticker.get('percentage', 0)
            
            return ticker
        except Exception as e:
            logging.error(f"Error fetching ticker from {exchange_id}: {e}")
            # Return a default ticker structure with zeros
            return {
                'last': 0,
                'ask': 0,
                'bid': 0,
                'quoteVolume': 0,
                'percentage': 0
            }
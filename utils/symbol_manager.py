import ccxt
from typing import Dict, List, Set
import logging
from pycoingecko import CoinGeckoAPI
import pandas as pd
import time

class SymbolManager:
    def __init__(self):
        self.cg = CoinGeckoAPI()
        self.top_coins_cache = {}
        self.exchange_symbols_cache = {}
        self.last_update = 0
        self._load_top_coins()
    
    def _load_top_coins(self):
        """Load top 100 coins by market cap from CoinGecko"""
        # Refresh cache every hour
        current_time = time.time()
        if current_time - self.last_update < 3600 and self.top_coins_cache:
            return

        try:
            # Use USD as the base currency for market cap data
            coins = self.cg.get_coins_markets(
                vs_currency='usd',
                order='market_cap_desc',
                per_page=100,
                sparkline=False
            )
            
            # Create cache with both symbol and id for better matching
            self.top_coins_cache = {}
            for coin in coins:
                symbol = coin['symbol'].upper()
                self.top_coins_cache[symbol] = coin
                if 'id' in coin:
                    self.top_coins_cache[coin['id'].upper()] = coin
            
            self.last_update = current_time
            logging.info(f"Successfully loaded {len(coins)} top coins from CoinGecko")
            
        except Exception as e:
            logging.error(f"Error loading top coins: {e}")
            if not self.top_coins_cache:  # Only create default if empty
                self.top_coins_cache = {
                    'BTC': {'symbol': 'BTC', 'name': 'Bitcoin'},
                    'ETH': {'symbol': 'ETH', 'name': 'Ethereum'},
                }

    def get_exchange_symbols(self, exchange_id: str, quote_currency: str = 'USDT', 
                           top_coins_only: bool = False) -> List[str]:
        """Get available trading pairs for an exchange"""
        cache_key = f"{exchange_id}_{quote_currency}_{top_coins_only}"
        
        # Use cached results if available and less than 5 minutes old
        current_time = time.time()
        if cache_key in self.exchange_symbols_cache:
            cache_time, symbols = self.exchange_symbols_cache[cache_key]
            if current_time - cache_time < 300:  # 5 minutes cache
                return symbols
            
        try:
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class({'enableRateLimit': True})
            markets = exchange.load_markets()
            
            # Filter for quote currency and normalize symbols
            symbols = []
            for symbol, market in markets.items():
                if not isinstance(market, dict):
                    continue
                    
                base = market.get('base', '')
                quote = market.get('quote', '')
                
                if quote == quote_currency:
                    if top_coins_only:
                        base_upper = base.upper()
                        # Check if base currency is in top coins
                        if base_upper in self.top_coins_cache:
                            symbols.append(f"{base}/{quote}")
                    else:
                        symbols.append(f"{base}/{quote}")
            
            # Sort by volume if available
            if markets and symbols:
                volume_data = {}
                for s in symbols:
                    market = markets.get(s.replace('/', ''))
                    if market and isinstance(market, dict):
                        volume = float(market.get('info', {}).get('quoteVolume', 0))
                        volume_data[s] = volume
                
                symbols.sort(key=lambda s: volume_data.get(s, 0), reverse=True)
            
            self.exchange_symbols_cache[cache_key] = (current_time, symbols)
            return symbols
            
        except Exception as e:
            logging.error(f"Error loading symbols for {exchange_id}: {e}")
            return []

    def get_common_symbols(self, exchanges: List[str], quote_currency: str = 'USDT',
                          top_coins_only: bool = False) -> List[str]:
        """Get symbols available across all specified exchanges"""
        if not exchanges:
            return []
            
        all_symbols = [
            set(self.get_exchange_symbols(ex, quote_currency, top_coins_only))
            for ex in exchanges
        ]
        
        if not all_symbols:
            return []
            
        common_symbols = set.intersection(*all_symbols)
        
        # If using top coins, ensure they're in our cache
        if top_coins_only:
            common_symbols = {
                s for s in common_symbols
                if s.split('/')[0] in self.top_coins_cache
            }
        
        # Sort by market cap if possible
        if self.top_coins_cache:
            return sorted(
                list(common_symbols),
                key=lambda s: self.top_coins_cache.get(
                    s.split('/')[0],
                    {'market_cap': 0}
                ).get('market_cap', 0),
                reverse=True
            )
        
        return sorted(list(common_symbols))

    def get_symbol_info(self, symbol: str) -> Dict:
        """Get additional information about a symbol from CoinGecko"""
        base = symbol.split('/')[0] if '/' in symbol else symbol
        return self.top_coins_cache.get(base.upper(), {})
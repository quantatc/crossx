import pandas as pd
from typing import List, Dict
from datetime import datetime, timedelta
import logging

class ArbitrageDetector:
    def __init__(self, data_collector):
        self.data_collector = data_collector
        self.spread_cache = {}
        self.last_update = {}
        self.min_profit_threshold = 0.001  # 0.1% minimum profit after fees
        self.fee_rate = 0.001  # 0.1% fee per trade

    def find_opportunities(self, symbol: str, exchanges: List[str]) -> List[Dict]:
        """Find arbitrage opportunities for a symbol across exchanges"""
        opportunities = []
        current_prices = {}
        
        # Get current prices from all exchanges
        for exchange in exchanges:
            ticker = self.data_collector.get_ticker(symbol, exchange)
            if ticker and ticker['last']:
                current_prices[exchange] = ticker['last']
        
        if len(current_prices) < 2:
            return []

        # Compare prices between exchanges
        for i, (ex1, price1) in enumerate(current_prices.items()):
            for ex2, price2 in list(current_prices.items())[i+1:]:
                # Calculate spread percentage
                spread = ((price2 - price1) / price1) * 100
                
                # Calculate fees
                fee_cost = (price1 * self.fee_rate) + (price2 * self.fee_rate)
                profit_after_fees = abs(price2 - price1) - fee_cost
                
                # Convert to percentage
                profit_percent = (profit_after_fees / price1) * 100
                
                if profit_percent > self.min_profit_threshold:
                    if price2 > price1:
                        opportunities.append({
                            'symbol': symbol,
                            'buy_exchange': ex1,
                            'sell_exchange': ex2,
                            'buy_price': price1,
                            'sell_price': price2,
                            'spread_percent': spread,
                            'potential_profit_percent': profit_percent
                        })
                    else:
                        opportunities.append({
                            'symbol': symbol,
                            'buy_exchange': ex2,
                            'sell_exchange': ex1,
                            'buy_price': price2,
                            'sell_price': price1,
                            'spread_percent': -spread,
                            'potential_profit_percent': profit_percent
                        })

        return sorted(opportunities, key=lambda x: x['potential_profit_percent'], reverse=True)

    def get_historical_spreads(self, symbol: str, exchanges: List[str],
                             timeframe: str = '5m', days: int = 1) -> pd.DataFrame:
        """Calculate historical price spreads between exchanges"""
        dfs = {}
        
        # Get historical data from all exchanges
        for exchange in exchanges:
            df = self.data_collector.get_historical_data(symbol, exchange, timeframe, days)
            if not df.empty:
                dfs[exchange] = df

        if len(dfs) < 2:
            return pd.DataFrame()

        # Calculate spreads between exchanges
        spread_data = {}
        exchanges_list = list(dfs.keys())
        
        for i, ex1 in enumerate(exchanges_list):
            for ex2 in exchanges_list[i+1:]:
                # Resample and align timeframes
                df1 = dfs[ex1].resample(timeframe).last()
                df2 = dfs[ex2].resample(timeframe).last()
                
                # Calculate spread percentage
                common_index = df1.index.intersection(df2.index)
                if len(common_index) > 0:
                    spread = ((df2.loc[common_index, 'close'] - 
                             df1.loc[common_index, 'close']) / 
                            df1.loc[common_index, 'close'] * 100)
                    spread_data[f"{ex1}-{ex2}"] = spread

        if spread_data:
            return pd.DataFrame(spread_data)
        return pd.DataFrame()

    def get_best_execution_path(self, symbol: str, exchanges: List[str],
                              amount: float) -> Dict:
        """Find the best execution path for a given trade size"""
        orderbooks = {}
        
        # Get orderbook data from all exchanges
        for exchange in exchanges:
            ob = self.data_collector.get_orderbook(symbol, exchange)
            if ob:
                orderbooks[exchange] = ob

        if len(orderbooks) < 2:
            return {}

        best_path = {
            'buy_exchange': None,
            'sell_exchange': None,
            'expected_profit': 0,
            'execution_details': {}
        }

        # Compare liquidity and prices across exchanges
        for ex1, ob1 in orderbooks.items():
            for ex2, ob2 in orderbooks.items():
                if ex1 != ex2:
                    # Calculate effective prices including slippage
                    buy_price = self._calculate_effective_price(ob1['asks'], amount)
                    sell_price = self._calculate_effective_price(ob2['bids'], amount)
                    
                    if buy_price and sell_price:
                        # Calculate profit after fees
                        fees = (buy_price * amount * self.fee_rate +
                               sell_price * amount * self.fee_rate)
                        profit = (sell_price - buy_price) * amount - fees
                        
                        if profit > best_path['expected_profit']:
                            best_path = {
                                'buy_exchange': ex1,
                                'sell_exchange': ex2,
                                'expected_profit': profit,
                                'execution_details': {
                                    'buy_price': buy_price,
                                    'sell_price': sell_price,
                                    'amount': amount,
                                    'fees': fees,
                                    'net_profit': profit
                                }
                            }

        return best_path

    def _calculate_effective_price(self, orders: List, amount: float) -> float:
        """Calculate effective price for a given order size including slippage"""
        remaining = amount
        total_cost = 0
        
        for price, size in orders:
            if remaining <= 0:
                break
            
            executed = min(remaining, size)
            total_cost += executed * price
            remaining -= executed
            
        if remaining > 0:  # Not enough liquidity
            return None
            
        return total_cost / amount
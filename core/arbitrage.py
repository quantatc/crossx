import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class ArbitrageDetector:
    def __init__(self, data_collector):
        self.data_collector = data_collector
        self.min_profit_after_fees = 0.002  # 0.2% minimum profit after fees

    def find_opportunities(self, symbol: str, exchanges: List[str]) -> List[Dict]:
        """Find arbitrage opportunities between exchanges"""
        opportunities = []
        tickers = {}
        
        # Collect current prices from all exchanges
        for exchange in exchanges:
            ticker = self.data_collector.get_ticker(symbol, exchange)
            if ticker:
                tickers[exchange] = {
                    'ask': ticker['ask'] if 'ask' in ticker else ticker['last'],
                    'bid': ticker['bid'] if 'bid' in ticker else ticker['last'],
                    'last': ticker['last']
                }

        # Compare prices between exchanges
        for buy_exchange in exchanges:
            if buy_exchange not in tickers:
                continue
                
            for sell_exchange in exchanges:
                if sell_exchange == buy_exchange or sell_exchange not in tickers:
                    continue
                
                buy_price = tickers[buy_exchange]['ask']
                sell_price = tickers[sell_exchange]['bid']
                
                # Calculate spread and potential profit
                spread = (sell_price - buy_price) / buy_price
                spread_percent = spread * 100
                
                # Account for exchange fees (assumed 0.1% per trade)
                fees = (buy_price * 0.001) + (sell_price * 0.001)
                potential_profit = spread - (fees / buy_price)
                potential_profit_percent = potential_profit * 100
                
                if potential_profit > self.min_profit_after_fees:
                    opportunities.append({
                        'buy_exchange': buy_exchange,
                        'sell_exchange': sell_exchange,
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'spread': sell_price - buy_price,
                        'spread_percent': spread_percent,
                        'potential_profit': potential_profit,
                        'potential_profit_percent': potential_profit_percent,
                        'timestamp': datetime.now()
                    })
        
        return opportunities

    def get_historical_spreads(self, symbol: str, exchanges: List[str], 
                             days: int = 1) -> pd.DataFrame:
        """Get historical price spreads between exchanges"""
        spreads = []
        
        # Get historical data for each exchange
        exchange_data = {}
        for exchange in exchanges:
            df = self.data_collector.get_historical_data(
                symbol, exchange, timeframe='5m', days=days
            )
            if not df.empty:
                exchange_data[exchange] = df

        # Calculate spreads between exchanges
        if len(exchange_data) > 1:
            # Get common timestamps
            common_times = None
            for df in exchange_data.values():
                if common_times is None:
                    common_times = set(df.index)
                else:
                    common_times = common_times.intersection(set(df.index))

            if common_times:
                spread_data = {}
                for i, ex1 in enumerate(exchanges):
                    if ex1 not in exchange_data:
                        continue
                        
                    for ex2 in exchanges[i+1:]:
                        if ex2 not in exchange_data:
                            continue
                            
                        # Calculate spread between these exchanges
                        df1 = exchange_data[ex1]
                        df2 = exchange_data[ex2]
                        
                        spread_name = f"{ex1}-{ex2}"
                        spread_data[spread_name] = []
                        
                        for time in sorted(common_times):
                            price1 = df1.loc[time, 'close']
                            price2 = df2.loc[time, 'close']
                            spread = ((price2 - price1) / price1) * 100
                            spread_data[spread_name].append(spread)
                
                # Create DataFrame with spreads
                df_spreads = pd.DataFrame(
                    spread_data, 
                    index=sorted(common_times)
                )
                return df_spreads
        
        return pd.DataFrame()
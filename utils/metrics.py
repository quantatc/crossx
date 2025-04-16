import pandas as pd
import numpy as np
from typing import Dict, List
import pandas_ta as ta

class MarketMetrics:
    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for market analysis"""
        if df.empty:
            return df
            
        # Moving Averages
        df['sma_20'] = ta.sma(df['close'], length=20)
        df['sma_50'] = ta.sma(df['close'], length=50)
        df['sma_200'] = ta.sma(df['close'], length=200)
        
        df['ema_8'] = ta.ema(df['close'], length=8)
        df['ema_21'] = ta.ema(df['close'], length=21)
        df['ema_55'] = ta.ema(df['close'], length=55)
        
        # RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # MACD
        macd = ta.macd(df['close'])
        df['macd_line'] = macd['MACD_12_26_9']
        df['macd_signal'] = macd['MACDs_12_26_9']
        df['macd_hist'] = macd['MACDh_12_26_9']
        
        # ATR for volatility
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        return df

    @staticmethod
    def calculate_metrics(df: pd.DataFrame) -> Dict:
        """Calculate market metrics for a symbol"""
        if df.empty:
            return {
                'last_price': 0,
                'price_change_24h': 0,
                'high_24h': 0,
                'low_24h': 0,
                'volume_24h': 0,
                'volatility_24h': 0
            }
        
        # Get latest price
        last_price = df['close'].iloc[-1]
        
        # Calculate 24h change
        price_24h_ago = df['close'].iloc[-24] if len(df) >= 24 else df['close'].iloc[0]
        price_change = ((last_price - price_24h_ago) / price_24h_ago) * 100
        
        # Get 24h high and low
        high_24h = df['high'].tail(24).max()
        low_24h = df['low'].tail(24).min()
        
        # Calculate 24h volume
        volume_24h = df['volume'].tail(24).sum()
        
        # Calculate volatility (standard deviation of returns)
        returns = df['close'].pct_change().tail(24)
        volatility = returns.std() * 100  # Convert to percentage
        
        return {
            'last_price': last_price,
            'price_change_24h': price_change,
            'high_24h': high_24h,
            'low_24h': low_24h,
            'volume_24h': volume_24h,
            'volatility_24h': volatility
        }

    @staticmethod
    def get_summary_metrics(df: pd.DataFrame) -> Dict:
        """Get summary statistics for technical indicators"""
        if df.empty:
            return {}
            
        rsi = df['rsi'].iloc[-1]
        macd = df['macd_line'].iloc[-1]
        macd_signal = df['macd_signal'].iloc[-1]
        
        trend = 'bullish' if df['close'].iloc[-1] > df['sma_50'].iloc[-1] else 'bearish'
        momentum = 'positive' if rsi > 50 else 'negative'
        signal = 'buy' if macd > macd_signal else 'sell'
        
        return {
            'trend': trend,
            'momentum': momentum,
            'signal': signal,
            'rsi': rsi,
            'macd': macd,
            'macd_signal': macd_signal
        }

    @staticmethod
    def calculate_arbitrage_metrics(prices: Dict[str, float]) -> Dict:
        """Calculate arbitrage opportunities between exchanges"""
        opportunities = []
        spreads = {}
        
        exchanges = list(prices.keys())
        
        for i, ex1 in enumerate(exchanges):
            spreads[ex1] = {}
            for ex2 in exchanges[i+1:]:
                price1 = prices[ex1]
                price2 = prices[ex2]
                
                spread = ((price2 - price1) / price1) * 100
                spreads[ex1][ex2] = spread
                
                # Consider spreads above 0.5% as opportunities
                if abs(spread) > 0.5:
                    if price2 > price1:
                        opportunities.append({
                            'buy_exchange': ex1,
                            'sell_exchange': ex2,
                            'buy_price': price1,
                            'sell_price': price2,
                            'spread': spread
                        })
                    else:
                        opportunities.append({
                            'buy_exchange': ex2,
                            'sell_exchange': ex1,
                            'buy_price': price2,
                            'sell_price': price1,
                            'spread': -spread
                        })
        
        return {
            'opportunities': sorted(opportunities, key=lambda x: abs(x['spread']), reverse=True),
            'spreads': spreads
        }

    @staticmethod
    def analyze_volume_profile(df: pd.DataFrame, price_levels: int = 50) -> Dict:
        """Analyze volume distribution across price levels"""
        if df.empty:
            return {}
            
        # Calculate price range
        price_min = df['low'].min()
        price_max = df['high'].max()
        price_step = (price_max - price_min) / price_levels
        
        # Create price bins
        price_bins = np.linspace(price_min, price_max, price_levels + 1)
        
        # Calculate volume profile
        volume_profile = pd.cut(df['close'], 
                              bins=price_bins, 
                              labels=price_bins[:-1],
                              include_lowest=True)
        
        volume_by_price = df.groupby(volume_profile)['volume'].sum()
        
        # Find point of control (price level with highest volume)
        poc_price = volume_by_price.idxmax()
        poc_volume = volume_by_price.max()
        
        # Calculate value area (70% of total volume)
        total_volume = volume_by_price.sum()
        sorted_volumes = volume_by_price.sort_values(ascending=False)
        cumsum_volume = sorted_volumes.cumsum()
        value_area_threshold = total_volume * 0.7
        value_area_prices = sorted_volumes[cumsum_volume <= value_area_threshold].index
        
        return {
            'volume_profile': volume_by_price.to_dict(),
            'point_of_control': {
                'price': poc_price,
                'volume': poc_volume
            },
            'value_area': {
                'low': min(value_area_prices),
                'high': max(value_area_prices)
            }
        }
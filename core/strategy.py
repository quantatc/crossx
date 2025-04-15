import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class Strategy:
    def __init__(self, timeframe: str = '5m'):
        self.timeframe = timeframe

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for the strategy"""
        # Create a copy to avoid modifying the original dataframe
        df = df.copy()
        
        # Calculate EMAs
        df['ema_8'] = ta.ema(df['close'], length=8)
        df['ema_21'] = ta.ema(df['close'], length=21)
        df['ema_55'] = ta.ema(df['close'], length=55)
        
        # Calculate MACD
        macd = ta.macd(df['close'])
        df = pd.concat([df, macd], axis=1)
        
        # Calculate RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # Calculate Bollinger Bands
        bollinger = ta.bbands(df['close'], length=20)
        df = pd.concat([df, bollinger], axis=1)
        
        # Calculate ADX
        adx = ta.adx(df['high'], df['low'], df['close'])
        df = pd.concat([df, adx], axis=1)
        
        return df

    def check_entry_conditions(self, df: pd.DataFrame, row_idx: int) -> Tuple[bool, str]:
        """Check if entry conditions are met for the Moth Scalping strategy"""
        if row_idx < 55:  # Need enough data for indicators
            return False, ""
            
        row = df.iloc[row_idx]
        prev_row = df.iloc[row_idx - 1]
        
        # Long entry conditions
        long_conditions = [
            row['ema_8'] > row['ema_21'],  # Bullish EMA alignment
            row['ema_21'] > row['ema_55'],
            row['close'] > row['ema_8'],    # Price above EMA8
            row['MACD_12_26_9'] > row['MACDs_12_26_9'],  # MACD bullish crossover
            prev_row['MACD_12_26_9'] <= prev_row['MACDs_12_26_9'],
            row['rsi'] > 40,                # RSI conditions
            row['rsi'] < 70,
            row['ADX_14'] > 25              # Strong trend
        ]
        
        # Short entry conditions
        short_conditions = [
            row['ema_8'] < row['ema_21'],  # Bearish EMA alignment
            row['ema_21'] < row['ema_55'],
            row['close'] < row['ema_8'],    # Price below EMA8
            row['MACD_12_26_9'] < row['MACDs_12_26_9'],  # MACD bearish crossover
            prev_row['MACD_12_26_9'] >= prev_row['MACDs_12_26_9'],
            row['rsi'] < 60,                # RSI conditions
            row['rsi'] > 30,
            row['ADX_14'] > 25              # Strong trend
        ]
        
        if all(long_conditions):
            return True, "long"
        elif all(short_conditions):
            return True, "short"
            
        return False, ""

    def check_exit_conditions(self, df: pd.DataFrame, row_idx: int, 
                            entry_price: float, side: str) -> bool:
        """Check if exit conditions are met"""
        if row_idx < 1:
            return False
            
        row = df.iloc[row_idx]
        
        # Exit conditions for long positions
        if side == "long":
            # Take profit at 1.5% or stop loss at 0.5%
            current_pnl = (row['close'] - entry_price) / entry_price * 100
            if current_pnl >= 1.5 or current_pnl <= -0.5:
                return True
                
            # Exit if EMA8 crosses below EMA21
            if row['ema_8'] < row['ema_21']:
                return True
                
        # Exit conditions for short positions
        elif side == "short":
            # Take profit at 1.5% or stop loss at 0.5%
            current_pnl = (entry_price - row['close']) / entry_price * 100
            if current_pnl >= 1.5 or current_pnl <= -0.5:
                return True
                
            # Exit if EMA8 crosses above EMA21
            if row['ema_8'] > row['ema_21']:
                return True
                
        return False

    def backtest(self, df: pd.DataFrame, initial_balance: float = 10000.0, 
                 risk_per_trade: float = 0.02) -> Dict:
        """Run backtest simulation of the strategy"""
        df = self.calculate_indicators(df)
        
        balance = initial_balance
        position = None
        trades = []
        equity_curve = [initial_balance]
        
        for i in range(len(df)):
            # Check for exit if in position
            if position:
                if self.check_exit_conditions(df, i, position['entry_price'], position['side']):
                    exit_price = df.iloc[i]['close']
                    pnl = 0
                    
                    if position['side'] == 'long':
                        pnl = (exit_price - position['entry_price']) / position['entry_price']
                    else:
                        pnl = (position['entry_price'] - exit_price) / position['entry_price']
                        
                    pnl = pnl * position['size'] - (position['size'] * 0.001 * 2)  # Include 0.1% fees
                    balance += pnl
                    
                    trades.append({
                        'entry_time': df.index[position['entry_index']],
                        'exit_time': df.index[i],
                        'side': position['side'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'balance': balance
                    })
                    
                    position = None
                    equity_curve.append(balance)
                    
            # Check for entry if not in position
            else:
                should_enter, side = self.check_entry_conditions(df, i)
                if should_enter:
                    entry_price = df.iloc[i]['close']
                    position_size = balance * risk_per_trade
                    
                    position = {
                        'side': side,
                        'entry_price': entry_price,
                        'entry_index': i,
                        'size': position_size
                    }
        
        # Calculate performance metrics
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'trades': [],
                'equity_curve': equity_curve
            }
            
        wins = len([t for t in trades if t['pnl'] > 0])
        total_profit = sum([t['pnl'] for t in trades if t['pnl'] > 0])
        total_loss = abs(sum([t['pnl'] for t in trades if t['pnl'] < 0]))
        
        equity_series = pd.Series(equity_curve)
        max_drawdown = ((equity_series.cummax() - equity_series) / 
                       equity_series.cummax()).max() * 100
        
        return {
            'total_trades': len(trades),
            'win_rate': wins / len(trades) * 100,
            'profit_factor': total_profit / total_loss if total_loss > 0 else float('inf'),
            'total_return': (balance - initial_balance) / initial_balance * 100,
            'max_drawdown': max_drawdown,
            'trades': trades,
            'equity_curve': equity_curve
        }
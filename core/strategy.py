import pandas as pd
import numpy as np
from typing import Dict, List
import pandas_ta as ta

class Strategy:
    def __init__(self):
        self.atr_period = 14
        self.rsi_period = 14
        self.stop_loss_atr = 2.0
        self.take_profit_atr = 3.0

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for analysis"""
        if df.empty:
            return df
            
        # Create a copy to avoid SettingWithCopyWarning
        df = df.copy()
        
        try:
            # Moving Averages
            df['sma_20'] = ta.sma(df['close'], length=20).fillna(df['close'])
            df['sma_50'] = ta.sma(df['close'], length=50).fillna(df['close'])
            df['sma_200'] = ta.sma(df['close'], length=200).fillna(df['close'])
            
            df['ema_8'] = ta.ema(df['close'], length=8).fillna(df['close'])
            df['ema_21'] = ta.ema(df['close'], length=21).fillna(df['close'])
            df['ema_55'] = ta.ema(df['close'], length=55).fillna(df['close'])
            
            # RSI
            df['rsi'] = ta.rsi(df['close'], length=self.rsi_period).fillna(50)
            
            # MACD
            macd = ta.macd(df['close'])
            if macd is not None:
                df['macd_line'] = macd['MACD_12_26_9'].fillna(0)
                df['macd_signal'] = macd['MACDs_12_26_9'].fillna(0)
                df['macd_hist'] = macd['MACDh_12_26_9'].fillna(0)
            else:
                df['macd_line'] = 0
                df['macd_signal'] = 0
                df['macd_hist'] = 0
            
            # ATR for volatility
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.atr_period)
            df['atr'] = df['atr'].fillna(df['high'] - df['low'])
            
            # Bollinger Bands
            bb = ta.bbands(df['close'])
            if bb is not None:
                # Get the first column names that contain upper, middle, and lower
                bb_cols = bb.columns.tolist()
                upper_col = next(col for col in bb_cols if 'BBU_' in col)
                middle_col = next(col for col in bb_cols if 'BBM_' in col)
                lower_col = next(col for col in bb_cols if 'BBL_' in col)
                
                df['bb_upper'] = bb[upper_col].fillna(df['close'])
                df['bb_middle'] = bb[middle_col].fillna(df['close'])
                df['bb_lower'] = bb[lower_col].fillna(df['close'])
            else:
                df['bb_upper'] = df['close']
                df['bb_middle'] = df['close']
                df['bb_lower'] = df['close']
            
        except Exception as e:
            # If any calculation fails, set default values
            for col in ['sma_20', 'sma_50', 'sma_200', 'ema_8', 'ema_21', 'ema_55']:
                df[col] = df['close']
            
            df['rsi'] = 50
            df['atr'] = df['high'] - df['low']
            
            df['macd_line'] = 0
            df['macd_signal'] = 0
            df['macd_hist'] = 0
            
            df['bb_upper'] = df['close']
            df['bb_middle'] = df['close']
            df['bb_lower'] = df['close']
        
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals based on Moth Scalping strategy"""
        if df.empty:
            return df
            
        # Create a copy to avoid SettingWithCopyWarning
        df = df.copy()
        df = self.calculate_indicators(df)
        
        # Initialize signal column
        df['signal'] = 0
        
        # Long entry conditions with NaN handling
        long_condition = (
            (df['ema_21'] > df['ema_55']) &  # Trend filter
            (df['close'] > df['ema_21']) &    # Price above EMA21
            (df['rsi'] > 50) &                # RSI momentum
            (df['macd_line'] > df['macd_signal'])  # MACD crossover
        ).fillna(False)
        
        # Short entry conditions with NaN handling
        short_condition = (
            (df['ema_21'] < df['ema_55']) &  # Trend filter
            (df['close'] < df['ema_21']) &    # Price below EMA21
            (df['rsi'] < 50) &                # RSI momentum
            (df['macd_line'] < df['macd_signal'])  # MACD crossover
        ).fillna(False)
        
        # Set signals
        df.loc[long_condition, 'signal'] = 1
        df.loc[short_condition, 'signal'] = -1
        
        return df

    def backtest(self, df: pd.DataFrame, initial_balance: float = 10000,
                risk_per_trade: float = 0.02) -> Dict:
        """Run backtest simulation"""
        if df.empty:
            return {
                'equity_curve': [initial_balance],
                'trades': [],
                'total_return': 0,
                'win_rate': 0,
                'total_trades': 0,
                'max_drawdown': 0
            }
        
        # Create a copy to avoid SettingWithCopyWarning
        df = df.copy()
        df = self.generate_signals(df)
        
        balance = initial_balance
        position = None
        equity_curve = [initial_balance] * len(df)  # Initialize with initial balance for all points
        trades = []
        
        for i in range(1, len(df)):
            current_bar = df.iloc[i]
            prev_bar = df.iloc[i-1]
            
            # Skip if no ATR value
            if pd.isna(current_bar['atr']):
                continue
            
            # Check for position exit
            if position:
                # Calculate stop loss and take profit
                if position['side'] == 'long':
                    stop_loss = position['entry'] - (position['atr'] * self.stop_loss_atr)
                    take_profit = position['entry'] + (position['atr'] * self.take_profit_atr)
                    
                    # Check if stopped out
                    if current_bar['low'] <= stop_loss:
                        pnl = (stop_loss - position['entry']) * position['size']
                        balance += pnl
                        trades.append({
                            'entry_time': position['time'],
                            'exit_time': current_bar.name,
                            'side': position['side'],
                            'entry_price': position['entry'],
                            'exit_price': stop_loss,
                            'pnl': pnl,
                            'balance': balance
                        })
                        position = None
                    
                    # Check if take profit hit
                    elif current_bar['high'] >= take_profit:
                        pnl = (take_profit - position['entry']) * position['size']
                        balance += pnl
                        trades.append({
                            'entry_time': position['time'],
                            'exit_time': current_bar.name,
                            'side': position['side'],
                            'entry_price': position['entry'],
                            'exit_price': take_profit,
                            'pnl': pnl,
                            'balance': balance
                        })
                        position = None
                
                else:  # Short position
                    stop_loss = position['entry'] + (position['atr'] * self.stop_loss_atr)
                    take_profit = position['entry'] - (position['atr'] * self.take_profit_atr)
                    
                    # Check if stopped out
                    if current_bar['high'] >= stop_loss:
                        pnl = (position['entry'] - stop_loss) * position['size']
                        balance += pnl
                        trades.append({
                            'entry_time': position['time'],
                            'exit_time': current_bar.name,
                            'side': position['side'],
                            'entry_price': position['entry'],
                            'exit_price': stop_loss,
                            'pnl': pnl,
                            'balance': balance
                        })
                        position = None
                    
                    # Check if take profit hit
                    elif current_bar['low'] <= take_profit:
                        pnl = (position['entry'] - take_profit) * position['size']
                        balance += pnl
                        trades.append({
                            'entry_time': position['time'],
                            'exit_time': current_bar.name,
                            'side': position['side'],
                            'entry_price': position['entry'],
                            'exit_price': take_profit,
                            'pnl': pnl,
                            'balance': balance
                        })
                        position = None
            
            # Check for new position entry
            if not position and not pd.isna(current_bar['atr']):
                if current_bar['signal'] == 1:  # Long signal
                    risk_amount = balance * risk_per_trade
                    position_size = risk_amount / (current_bar['atr'] * self.stop_loss_atr)
                    position = {
                        'side': 'long',
                        'entry': current_bar['close'],
                        'time': current_bar.name,
                        'size': position_size,
                        'atr': current_bar['atr']
                    }
                
                elif current_bar['signal'] == -1:  # Short signal
                    risk_amount = balance * risk_per_trade
                    position_size = risk_amount / (current_bar['atr'] * self.stop_loss_atr)
                    position = {
                        'side': 'short',
                        'entry': current_bar['close'],
                        'time': current_bar.name,
                        'size': position_size,
                        'atr': current_bar['atr']
                    }
            
            # Update equity curve at the current position
            equity_curve[i] = balance
        
        # Close any open position at the end
        if position:
            exit_price = df['close'].iloc[-1]
            if position['side'] == 'long':
                pnl = (exit_price - position['entry']) * position['size']
            else:
                pnl = (position['entry'] - exit_price) * position['size']
            
            balance += pnl
            trades.append({
                'entry_time': position['time'],
                'exit_time': df.index[-1],
                'side': position['side'],
                'entry_price': position['entry'],
                'exit_price': exit_price,
                'pnl': pnl,
                'balance': balance
            })
            equity_curve[-1] = balance
        
        # Calculate metrics
        total_return = ((balance - initial_balance) / initial_balance) * 100
        win_trades = sum(1 for t in trades if t['pnl'] > 0)
        win_rate = (win_trades / len(trades)) * 100 if trades else 0
        
        # Calculate max drawdown
        peak = initial_balance
        max_drawdown = 0
        for value in equity_curve:
            peak = max(peak, value)
            drawdown = (peak - value) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        return {
            'equity_curve': equity_curve,
            'trades': trades,
            'total_return': total_return,
            'win_rate': win_rate,
            'total_trades': len(trades),
            'max_drawdown': max_drawdown
        }
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

@dataclass
class Trade:
    symbol: str
    exchange: str
    entry_price: float
    exit_price: Optional[float]
    position_size: float
    side: str  # 'long' or 'short'
    entry_time: datetime
    exit_time: Optional[datetime]
    pnl: Optional[float] = None
    fees: float = 0.0
    status: str = 'open'  # 'open' or 'closed'

class PaperTrader:
    def __init__(self, initial_balance: float = 10000):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.open_positions: Dict[str, Trade] = {}
        self.closed_trades: List[Trade] = []
        self.fee_rate = 0.001  # 0.1% fee per trade
        
    def calculate_max_position_size(self, price: float, risk_percent: float = 0.02) -> float:
        """Calculate maximum position size based on risk percentage"""
        return (self.current_balance * risk_percent) / price
        
    def open_position(self, symbol: str, exchange: str, price: float, 
                     size: float, side: str) -> Optional[Trade]:
        """Open a new paper trading position"""
        if symbol in self.open_positions:
            return None
            
        position_cost = price * size
        fees = position_cost * self.fee_rate
        
        if position_cost + fees > self.current_balance:
            return None
            
        trade = Trade(
            symbol=symbol,
            exchange=exchange,
            entry_price=price,
            exit_price=None,
            position_size=size,
            side=side,
            entry_time=datetime.now(),
            exit_time=None,
            fees=fees
        )
        
        self.current_balance -= (position_cost + fees)
        self.open_positions[symbol] = trade
        return trade
        
    def close_position(self, symbol: str, price: float) -> Optional[Trade]:
        """Close an existing paper trading position"""
        if symbol not in self.open_positions:
            return None
            
        trade = self.open_positions[symbol]
        position_value = price * trade.position_size
        exit_fees = position_value * self.fee_rate
        
        if trade.side == 'long':
            pnl = position_value - (trade.entry_price * trade.position_size)
        else:
            pnl = (trade.entry_price * trade.position_size) - position_value
            
        pnl -= (trade.fees + exit_fees)
        
        trade.exit_price = price
        trade.exit_time = datetime.now()
        trade.pnl = pnl
        trade.fees += exit_fees
        trade.status = 'closed'
        
        self.current_balance += position_value - exit_fees
        self.closed_trades.append(trade)
        del self.open_positions[symbol]
        
        return trade
        
    def get_trading_metrics(self) -> dict:
        """Calculate trading performance metrics"""
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_profit': 0.0,
                'total_pnl': 0.0,
                'max_drawdown': 0.0
            }
            
        total_trades = len(self.closed_trades)
        winning_trades = len([t for t in self.closed_trades if t.pnl > 0])
        total_pnl = sum(t.pnl for t in self.closed_trades)
        
        # Calculate running balance and max drawdown
        running_balance = [self.initial_balance]
        for trade in self.closed_trades:
            running_balance.append(running_balance[-1] + trade.pnl)
        running_balance = pd.Series(running_balance)
        max_drawdown = ((running_balance.cummax() - running_balance) / 
                       running_balance.cummax()).max()
        
        return {
            'total_trades': total_trades,
            'win_rate': winning_trades / total_trades,
            'avg_profit': total_pnl / total_trades,
            'total_pnl': total_pnl,
            'max_drawdown': max_drawdown
        }
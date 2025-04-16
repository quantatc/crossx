from datetime import datetime
from typing import List, Dict, Optional
import logging
from dataclasses import dataclass

@dataclass
class Position:
    symbol: str
    exchange: str
    side: str  # 'long' or 'short'
    entry_price: float
    position_size: float
    entry_time: datetime

@dataclass
class Trade:
    symbol: str
    exchange: str
    side: str
    entry_price: float
    exit_price: float
    position_size: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    fees: float

class PaperTrader:
    def __init__(self, initial_balance: float = 10000.0, fee_rate: float = 0.001):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.fee_rate = fee_rate
        self.open_positions: Dict[str, Position] = {}
        self.closed_trades: List[Trade] = []
        
    def open_position(self, symbol: str, exchange: str, price: float,
                     size: float, side: str) -> Optional[Position]:
        """Open a new position"""
        if side not in ['long', 'short']:
            logging.error(f"Invalid side: {side}")
            return None
            
        # Check if position already exists
        if symbol in self.open_positions:
            logging.error(f"Position already exists for {symbol}")
            return None
            
        # Calculate required margin
        position_value = price * size
        fees = position_value * self.fee_rate
        
        if position_value + fees > self.current_balance:
            logging.error("Insufficient balance")
            return None
            
        # Open position
        position = Position(
            symbol=symbol,
            exchange=exchange,
            side=side,
            entry_price=price,
            position_size=size,
            entry_time=datetime.now()
        )
        
        self.open_positions[symbol] = position
        self.current_balance -= fees
        
        logging.info(f"Opened {side} position for {symbol} at {price}")
        return position
        
    def close_position(self, symbol: str, price: float) -> Optional[Trade]:
        """Close an existing position"""
        position = self.open_positions.get(symbol)
        if not position:
            logging.error(f"No open position for {symbol}")
            return None
            
        # Calculate P&L
        position_value = price * position.position_size
        fees = position_value * self.fee_rate
        
        if position.side == 'long':
            pnl = (price - position.entry_price) * position.position_size
        else:  # short
            pnl = (position.entry_price - price) * position.position_size
            
        # Create trade record
        trade = Trade(
            symbol=position.symbol,
            exchange=position.exchange,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=price,
            position_size=position.position_size,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            pnl=pnl,
            fees=fees
        )
        
        # Update balance and remove position
        self.current_balance += pnl - fees
        self.closed_trades.append(trade)
        del self.open_positions[symbol]
        
        logging.info(f"Closed {position.side} position for {symbol} at {price}, PnL: {pnl:.2f}")
        return trade
        
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for a symbol"""
        return self.open_positions.get(symbol)
        
    def get_pnl_summary(self) -> Dict:
        """Get summary of trading performance"""
        total_pnl = sum(t.pnl for t in self.closed_trades)
        total_fees = sum(t.fees for t in self.closed_trades)
        win_trades = sum(1 for t in self.closed_trades if t.pnl > 0)
        
        return {
            'total_pnl': total_pnl,
            'total_fees': total_fees,
            'net_pnl': total_pnl - total_fees,
            'total_trades': len(self.closed_trades),
            'win_trades': win_trades,
            'win_rate': (win_trades / len(self.closed_trades) * 100) if self.closed_trades else 0,
            'roi': ((self.current_balance - self.initial_balance) / self.initial_balance * 100)
        }

    def calculate_metrics(self) -> Dict:
        """Calculate trading metrics"""
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'average_win': 0,
                'average_loss': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0
            }
            
        # Calculate basic metrics
        winning_trades = [t for t in self.closed_trades if t.pnl > 0]
        losing_trades = [t for t in self.closed_trades if t.pnl < 0]
        
        total_profit = sum(t.pnl for t in winning_trades)
        total_loss = abs(sum(t.pnl for t in losing_trades))
        
        # Calculate running balance and drawdown
        running_balance = [self.initial_balance]
        for trade in self.closed_trades:
            running_balance.append(running_balance[-1] + trade.pnl - trade.fees)
            
        peak_balance = self.initial_balance
        max_drawdown = 0
        
        for balance in running_balance:
            peak_balance = max(peak_balance, balance)
            drawdown = (peak_balance - balance) / peak_balance * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        return {
            'total_trades': len(self.closed_trades),
            'win_rate': (len(winning_trades) / len(self.closed_trades)) * 100,
            'profit_factor': total_profit / total_loss if total_loss > 0 else float('inf'),
            'average_win': total_profit / len(winning_trades) if winning_trades else 0,
            'average_loss': total_loss / len(losing_trades) if losing_trades else 0,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': self._calculate_sharpe_ratio(running_balance)
        }
        
    def _calculate_sharpe_ratio(self, balance_history: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if len(balance_history) < 2:
            return 0
            
        returns = [(b2 - b1) / b1 for b1, b2 in zip(balance_history[:-1], balance_history[1:])]
        if not returns:
            return 0
            
        import numpy as np
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate
        
        if len(excess_returns) < 2:
            return 0
            
        return np.sqrt(252) * (excess_returns.mean() / excess_returns.std()) if excess_returns.std() != 0 else 0
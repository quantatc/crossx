import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.strategy import Strategy

class TestStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = Strategy()
        
        # Create sample data for testing
        dates = pd.date_range(start='2025-01-01', periods=100, freq='5min')
        self.test_data = pd.DataFrame({
            'open': np.random.normal(100, 2, 100),
            'high': np.random.normal(101, 2, 100),
            'low': np.random.normal(99, 2, 100),
            'close': np.random.normal(100, 2, 100),
            'volume': np.random.normal(1000, 200, 100)
        }, index=dates)

    def test_calculate_indicators(self):
        # Test indicator calculation
        df = self.strategy.calculate_indicators(self.test_data)
        
        # Check if all required indicators are present
        required_indicators = ['ema_8', 'ema_21', 'ema_55', 'rsi', 
                             'MACD_12_26_9', 'MACDs_12_26_9', 'MACDh_12_26_9']
        for indicator in required_indicators:
            self.assertIn(indicator, df.columns)
            
        # Check if indicators have valid values
        self.assertTrue(df['ema_8'].notna().any())
        self.assertTrue(df['rsi'].between(0, 100).all())

    def test_check_entry_conditions(self):
        df = self.strategy.calculate_indicators(self.test_data)
        
        # Test entry condition check
        should_enter, side = self.strategy.check_entry_conditions(df, 60)
        self.assertIn(side, ['', 'long', 'short'])
        self.assertIsInstance(should_enter, bool)

    def test_check_exit_conditions(self):
        df = self.strategy.calculate_indicators(self.test_data)
        
        # Test exit condition check for long position
        should_exit = self.strategy.check_exit_conditions(
            df, 60, entry_price=100.0, side='long'
        )
        self.assertIsInstance(should_exit, bool)
        
        # Test exit condition check for short position
        should_exit = self.strategy.check_exit_conditions(
            df, 60, entry_price=100.0, side='short'
        )
        self.assertIsInstance(should_exit, bool)

    def test_backtest(self):
        # Test backtest functionality
        results = self.strategy.backtest(
            self.test_data, initial_balance=10000, risk_per_trade=0.02
        )
        
        # Check if backtest results contain all required metrics
        required_metrics = ['total_trades', 'win_rate', 'profit_factor', 
                          'total_return', 'max_drawdown', 'trades', 'equity_curve']
        for metric in required_metrics:
            self.assertIn(metric, results)
        
        # Check if metrics have valid values
        self.assertGreaterEqual(results['total_trades'], 0)
        self.assertGreaterEqual(results['win_rate'], 0)
        self.assertGreaterEqual(results['win_rate'], 0)
        self.assertGreaterEqual(len(results['equity_curve']), 1)

if __name__ == '__main__':
    unittest.main()
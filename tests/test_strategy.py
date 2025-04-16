import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.strategy import Strategy

class TestStrategy(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        # Create sample OHLCV data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
        self.test_data = pd.DataFrame({
            'open': np.random.normal(100, 2, 100),
            'high': np.random.normal(102, 2, 100),
            'low': np.random.normal(98, 2, 100),
            'close': np.random.normal(101, 2, 100),
            'volume': np.random.normal(1000, 200, 100)
        }, index=dates)
        
        # Ensure high is highest and low is lowest
        self.test_data['high'] = self.test_data[['open', 'high', 'low', 'close']].max(axis=1)
        self.test_data['low'] = self.test_data[['open', 'high', 'low', 'close']].min(axis=1)
        
        self.strategy = Strategy()

    def test_calculate_indicators(self):
        """Test technical indicator calculations"""
        df = self.strategy.calculate_indicators(self.test_data.copy())
        
        # Check if all indicators are present
        expected_columns = [
            'sma_20', 'sma_50', 'sma_200',
            'ema_8', 'ema_21', 'ema_55',
            'rsi', 'macd_line', 'macd_signal', 'macd_hist',
            'atr', 'bb_upper', 'bb_middle', 'bb_lower'
        ]
        
        for col in expected_columns:
            self.assertIn(col, df.columns)
            self.assertTrue(df[col].notna().any())

    def test_generate_signals(self):
        """Test trading signal generation"""
        df = self.strategy.generate_signals(self.test_data.copy())
        
        # Check if signal column exists
        self.assertIn('signal', df.columns)
        
        # Check if signals are valid (-1, 0, or 1)
        unique_signals = df['signal'].unique()
        self.assertTrue(all(s in [-1, 0, 1] for s in unique_signals))

    def test_backtest(self):
        """Test backtesting functionality"""
        initial_balance = 10000
        risk_per_trade = 0.02
        
        results = self.strategy.backtest(
            self.test_data.copy(),
            initial_balance=initial_balance,
            risk_per_trade=risk_per_trade
        )
        
        # Check if all required metrics are present
        expected_keys = [
            'equity_curve', 'trades', 'total_return',
            'win_rate', 'total_trades', 'max_drawdown'
        ]
        
        for key in expected_keys:
            self.assertIn(key, results)
        
        # Check if equity curve is valid
        self.assertEqual(len(results['equity_curve']), len(self.test_data))
        self.assertGreater(len(results['equity_curve']), 0)
        
        # Check if metrics are within reasonable ranges
        self.assertIsInstance(results['total_return'], float)
        self.assertGreaterEqual(results['win_rate'], 0)
        self.assertLessEqual(results['win_rate'], 100)
        self.assertGreaterEqual(results['max_drawdown'], 0)
        self.assertLessEqual(results['max_drawdown'], 100)

    def test_risk_management(self):
        """Test risk management rules"""
        initial_balance = 10000
        risk_per_trade = 0.02
        
        results = self.strategy.backtest(
            self.test_data.copy(),
            initial_balance=initial_balance,
            risk_per_trade=risk_per_trade
        )
        
        # Check if any trades were made
        if results['trades']:
            for trade in results['trades']:
                # Calculate risk amount for each trade
                entry_price = trade['entry_price']
                exit_price = trade['exit_price']
                max_loss = abs(trade['pnl'])
                
                # Maximum loss should not exceed risk per trade
                max_allowed_loss = initial_balance * risk_per_trade
                self.assertLessEqual(max_loss, max_allowed_loss * 1.1)  # Allow 10% margin for slippage

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Test with empty DataFrame
        empty_df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        results = self.strategy.backtest(empty_df)
        self.assertEqual(results['total_trades'], 0)
        
        # Test with single row
        single_row = self.test_data.iloc[[0]]
        results = self.strategy.backtest(single_row)
        self.assertEqual(results['total_trades'], 0)
        
        # Test with missing values
        df_with_nan = self.test_data.copy()
        df_with_nan.loc[df_with_nan.index[0], 'close'] = np.nan
        results = self.strategy.backtest(df_with_nan)
        self.assertGreaterEqual(len(results['equity_curve']), 0)

if __name__ == '__main__':
    unittest.main()
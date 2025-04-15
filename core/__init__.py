# This file makes the core directory a Python package
from .data import ExchangeDataCollector
from .trading import PaperTrader
from .strategy import Strategy
from .arbitrage import ArbitrageDetector

__all__ = ['ExchangeDataCollector', 'PaperTrader', 'Strategy', 'ArbitrageDetector']
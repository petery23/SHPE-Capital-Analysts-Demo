"""
Core backtesting engine modules.

This package contains the core functionality for:
- Data fetching from Yahoo Finance
- Trading strategy signal generation
- Portfolio backtesting simulation
- Performance metrics calculation
"""

from . import backtester, strategy, performance, data_fetcher

__all__ = ['backtester', 'strategy', 'performance', 'data_fetcher']


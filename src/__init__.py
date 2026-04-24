"""
Stock Analyzer - Portfolio Backtesting Tool

A comprehensive tool for backtesting trading strategies across multiple stocks
with smart capital allocation based on performance metrics.
"""

# Re-export main components for easy access
from . import core
from . import web
from . import cli

__all__ = ['core', 'web', 'cli']


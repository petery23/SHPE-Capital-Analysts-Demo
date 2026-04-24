"""
Interactive Web-Based Portfolio Backtesting GUI
Smart capital allocation across multiple stocks based on individual performance.

This module is maintained for backwards compatibility.
The code has been reorganized into:
- web/app.py: Flask app and routes
- web/analysis.py: Analysis and validation functions
- web/utils.py: Utility functions
- web/templates/: HTML templates
- web/static/: CSS and JavaScript files
"""

# Import everything from the modularized components for backwards compatibility
from .web import app, launch_web_gui, analyze_single_stock, validate_stock, clean_for_json, clean_list

# Re-export for backwards compatibility
__all__ = [
    'app',
    'launch_web_gui',
    'analyze_single_stock',
    'validate_stock',
    'clean_for_json',
    'clean_list',
]

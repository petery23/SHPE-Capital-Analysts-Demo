"""
Utility functions for the web GUI.
"""

import math


def clean_for_json(val):
    """Clean a value for JSON serialization (handle NaN, Infinity)."""
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return 0.0
        return val
    return val


def clean_list(lst):
    """Clean a list for JSON serialization."""
    return [clean_for_json(v) if isinstance(v, (int, float)) else v for v in lst]


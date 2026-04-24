"""
Analysis and validation functions for the web GUI.
"""

import datetime as dt

from ..core import backtester, strategy
from ..core.data_fetcher import DataFetchError, fetch_price_history
from .utils import clean_for_json, clean_list


def validate_stock(ticker, start_date, end_date):
    """
    Validate a stock and return error information if there are issues.
    Returns None if valid, or a dict with error information.
    """
    try:
        price_data = fetch_price_history(ticker, start_date, end_date)
        
        if price_data.empty:
            return {
                'ticker': ticker,
                'error': 'not_found',
                'message': f'{ticker} could not be found in the database'
            }
        
        # Check if stock has data for the full time frame
        # Account for weekends and holidays - allow up to 5 days difference
        data_start = price_data.index[0].date()
        data_end = price_data.index[-1].date()
        
        issues = []
        
        # Calculate days difference
        start_diff = (data_start - start_date).days
        end_diff = (end_date - data_end).days
        
        # Only flag if the gap is more than 5 days (to account for weekends + holidays)
        if start_diff > 5:
            issues.append({
                'type': 'partial_data',
                'message': f'{ticker} did not exist at the start date ({start_date}). Data starts from {data_start}.'
            })
        elif start_diff > 0:
            # Small gap (likely weekend/holiday) - this is fine, don't flag it
            pass
        
        if end_diff > 5:
            issues.append({
                'type': 'partial_data',
                'message': f'{ticker} data ends before the end date ({end_date}). Data ends at {data_end}.'
            })
        elif end_diff > 0:
            # Small gap (likely weekend/holiday) - this is fine, don't flag it
            pass
        
        if issues:
            return {
                'ticker': ticker,
                'error': 'partial_data',
                'issues': issues,
                'data_start': data_start.isoformat(),
                'data_end': data_end.isoformat(),
                'message': f'{ticker} does not have complete data for the specified time frame'
            }
        
        return None  # Stock is valid
        
    except DataFetchError as e:
        return {
            'ticker': ticker,
            'error': 'fetch_error',
            'message': str(e)
        }
    except Exception as e:
        return {
            'ticker': ticker,
            'error': 'unknown_error',
            'message': f'Unexpected error: {str(e)}'
        }


def analyze_single_stock(ticker, start_date, end_date, short_window, long_window, use_rsi):
    """Analyze a single stock and return results."""
    try:
        price_data = fetch_price_history(ticker, start_date, end_date)
        if price_data.empty:
            return None
            
        signals = strategy.generate_signals(
            price_data,
            short_window=short_window,
            long_window=long_window,
            use_rsi=use_rsi
        )
        
        if signals is None:
            return None
        
        # Run backtest with $10000 to get normalized metrics
        results, portfolio = backtester.run_backtest(
            ticker, price_data, signals, 10000, show_chart=False
        )
        
        # Extract data for response - clean NaN values
        dates = [d.strftime('%Y-%m-%d') for d in price_data.index]
        prices = clean_list(price_data['Adj Close'].tolist())
        short_ma = clean_list(signals['short_mavg'].tolist())
        long_ma = clean_list(signals['long_mavg'].tolist())
        portfolio_vals = clean_list(portfolio['total'].tolist())
        
        # Buy/sell signals with amounts
        buys = []
        sells = []
        buy_mask  = signals['positions'] == 1.0
        sell_mask = signals['positions'] == -1.0

        # Derive traded amounts from the actual portfolio delta on each signal day.
        # This works correctly for both graded (partial) and legacy all-in sizing.
        for idx in signals[buy_mask].index:
            price         = float(price_data.loc[idx, 'Adj Close'])
            portfolio_idx = portfolio.index.get_loc(idx)

            holdings_after  = float(portfolio.iloc[portfolio_idx]['holdings'])
            holdings_before = float(portfolio.iloc[portfolio_idx - 1]['holdings']) if portfolio_idx > 0 else 0.0

            amount_invested = max(holdings_after - holdings_before, 0.0)
            shares_bought   = amount_invested / price if price > 0 else 0.0

            buys.append({
                'date':   idx.strftime('%Y-%m-%d'),
                'price':  clean_for_json(price),
                'amount': clean_for_json(amount_invested),
                'shares': clean_for_json(shares_bought),
            })

        for idx in signals[sell_mask].index:
            price         = float(price_data.loc[idx, 'Adj Close'])
            portfolio_idx = portfolio.index.get_loc(idx)

            holdings_after  = float(portfolio.iloc[portfolio_idx]['holdings'])
            holdings_before = float(portfolio.iloc[portfolio_idx - 1]['holdings']) if portfolio_idx > 0 else 0.0

            amount_sold = max(holdings_before - holdings_after, 0.0)
            shares_sold = amount_sold / price if price > 0 else 0.0

            sells.append({
                'date':   idx.strftime('%Y-%m-%d'),
                'price':  clean_for_json(price),
                'amount': clean_for_json(amount_sold),
                'shares': clean_for_json(shares_sold),
            })
        
        # Clean sharpe ratio
        sharpe = clean_for_json(results['sharpe_ratio'])
        return_pct = clean_for_json(results['total_return_pct'])
        
        return {
            'ticker': ticker,
            'dates': dates,
            'prices': prices,
            'short_ma': short_ma,
            'long_ma': long_ma,
            'portfolio_vals': portfolio_vals,
            'buys': buys,
            'sells': sells,
            'sharpe': sharpe,
            'return_pct': return_pct,
            'final_value': clean_for_json(float(portfolio['total'].iloc[-1]))
        }
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None


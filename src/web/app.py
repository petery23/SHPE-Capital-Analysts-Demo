"""
Flask routes for the web GUI.
"""

import datetime as dt

from flask import Flask, render_template, request, jsonify
import numpy as np
import os

from ..core.data_fetcher import DataFetchError
from .analysis import analyze_single_stock, validate_stock
from .utils import clean_for_json, clean_list

# Configure Flask to use templates and static folders in src directory
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/portfolio', methods=['POST'])
def run_portfolio_analysis():
    try:
        data = request.get_json()
        
        tickers = data.get('tickers', [])
        capital = float(data.get('capital', 100000))
        start_date = dt.datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = dt.datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        short_window = data.get('short_window', 20)
        long_window = data.get('long_window', 50)
        use_rsi = data.get('use_rsi', True)
        smart_allocation = data.get('smart_allocation', True)
        
        if not tickers:
            return jsonify({'error': 'No tickers provided'}), 400
        
        if capital <= 0:
            return jsonify({'error': 'Capital must be positive'}), 400
        
        if end_date <= start_date:
            return jsonify({'error': 'End date must be after start date'}), 400
        
        skip_validation = data.get('skip_validation', False)
        
        # Validate all stocks first (unless skipping validation)
        if not skip_validation:
            validation_errors = []
            for ticker in tickers:
                error_info = validate_stock(ticker, start_date, end_date)
                if error_info:
                    validation_errors.append(error_info)
            
            # If there are validation errors, return them for user review
            if validation_errors:
                # Check if any are critical (not found) vs warnings (partial data)
                critical_errors = [e for e in validation_errors if e['error'] in ['not_found', 'fetch_error', 'unknown_error']]
                warnings = [e for e in validation_errors if e['error'] == 'partial_data']
                
                return jsonify({
                    'validation_errors': True,
                    'errors': validation_errors,
                    'critical_errors': critical_errors,
                    'warnings': warnings,
                    'can_continue': len(critical_errors) == 0  # Can continue if only warnings
                }), 200  # Return 200 so frontend can handle it
        
        # Analyze all stocks
        stock_results = []
        for ticker in tickers:
            result = analyze_single_stock(
                ticker, start_date, end_date,
                short_window, long_window, use_rsi
            )
            if result:
                stock_results.append(result)
        
        if not stock_results:
            return jsonify({'error': 'No valid data for any of the tickers'}), 400
        
        # Calculate allocation weights based on Sharpe ratio
        if smart_allocation:
            # Use Sharpe ratio for weighting (shift to positive if needed)
            sharpes = np.array([max(s['sharpe'], 0.01) for s in stock_results])
            weights = sharpes / sharpes.sum()
        else:
            # Equal allocation
            weights = np.ones(len(stock_results)) / len(stock_results)
        
        # Allocate capital
        allocations = weights * capital
        
        # Calculate actual profits with allocated capital
        stocks_output = []
        total_profit = 0
        
        # Find common date range
        all_dates = set()
        for s in stock_results:
            all_dates.update(s['dates'])
        common_dates = sorted(list(all_dates))
        
        portfolio_values = [0] * len(common_dates)
        
        for i, s in enumerate(stock_results):
            allocation = float(allocations[i])
            # Scale the portfolio values based on allocation
            scale = allocation / 10000  # Our test was with $10000
            
            scaled_vals = clean_list([v * scale for v in s['portfolio_vals']])
            profit = clean_for_json(scaled_vals[-1] - allocation if scaled_vals else 0)
            return_pct = clean_for_json((scaled_vals[-1] / allocation - 1) * 100 if allocation > 0 and scaled_vals else 0)
            
            # Add to portfolio total
            date_to_val = dict(zip(s['dates'], scaled_vals))
            for j, d in enumerate(common_dates):
                if d in date_to_val:
                    portfolio_values[j] += date_to_val[d]
                elif j > 0:
                    # Carry forward last known value for this stock
                    pass
            
            # Scale buy/sell amounts and shares to match actual allocation
            scaled_buys = []
            for buy in s.get('buys', []):
                buy_amount = (buy.get('amount') or 0) * scale
                buy_shares = (buy.get('shares') or 0) * scale
                scaled_buys.append({
                    'date': buy['date'],
                    'price': buy['price'],
                    'amount': clean_for_json(buy_amount),
                    'shares': clean_for_json(buy_shares)
                })
            
            scaled_sells = []
            for sell in s.get('sells', []):
                sell_amount = (sell.get('amount') or 0) * scale
                sell_shares = (sell.get('shares') or 0) * scale
                scaled_sells.append({
                    'date': sell['date'],
                    'price': sell['price'],
                    'amount': clean_for_json(sell_amount),
                    'shares': clean_for_json(sell_shares)
                })
            
            stocks_output.append({
                'ticker': s['ticker'],
                'allocation': clean_for_json(allocation),
                'allocation_pct': clean_for_json(float(weights[i] * 100)),
                'profit': profit,
                'return_pct': return_pct,
                'sharpe': clean_for_json(float(s['sharpe'])),
                'dates': s['dates'],
                'prices': s['prices'],
                'short_ma': s['short_ma'],
                'long_ma': s['long_ma'],
                'values': scaled_vals,
                'buys': scaled_buys,
                'sells': scaled_sells
            })
            
            total_profit += profit
        
        # Sort by profit descending
        stocks_output.sort(key=lambda x: x['profit'], reverse=True)
        
        # Calculate total return
        total_return_pct = (total_profit / capital) * 100
        
        # Clean portfolio values for JSON
        clean_portfolio_values = clean_list(portfolio_values)
        
        return jsonify({
            'stocks': stocks_output,
            'dates': common_dates,
            'portfolio_values': clean_portfolio_values,
            'total_profit': clean_for_json(total_profit),
            'total_return_pct': clean_for_json(total_return_pct),
            'total_capital': capital
        })
        
    except DataFetchError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


def launch_web_gui(debug=False, port=5000):
    """Launch the web-based GUI."""
    print(f"\n{'='*60}")
    print("  SHPE Capital - Smart Portfolio Analyzer")
    print(f"{'='*60}")
    print(f"\n  Open your browser and navigate to:")
    print(f"  >>> http://localhost:{port}")
    print(f"\n  Press Ctrl+C to stop the server")
    print(f"{'='*60}\n")
    app.run(debug=debug, port=port, threaded=True)


if __name__ == '__main__':
    launch_web_gui(debug=True)


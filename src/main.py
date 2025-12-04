import datetime
import traceback

from . import backtester, strategy
from .data_fetcher import DataFetchError, fetch_price_history

def main():
    """
    Main function to run the backtesting script from the terminal.
    """
    # --- User Input ---
    ticker = input("Enter the stock ticker to analyze (e.g., AAPL): ").upper()
    
    while True:
        try:
            initial_capital = float(input("Enter the initial capital to invest (e.g., 100000): "))
            if initial_capital <= 0:
                print("Initial capital must be a positive number.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    print(f"\n(Note: The latest available data is typically up to yesterday's market close.)")
    print(f"Today's date is: {datetime.date.today().strftime('%Y-%m-%d')}")
    while True:
        try:
            start_date_str = input("Enter the start date (YYYY-MM-DD): ")
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
            if start_date > datetime.date.today():
                print("Error: Start date cannot be in the future. Please enter a past or current date.")
                continue
            break
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")
    
    while True:
        try:
            end_date_str = input("Enter the end date (YYYY-MM-DD): ")
            end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if end_date > datetime.date.today():
                print("Warning: End date is in the future. Data will be fetched up to today's date.")
                end_date = datetime.date.today()

            if end_date <= start_date:
                print("Error: End date must be after the start date.")
                continue
            break
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")

    # --- Data Fetching ---
    print(f"\nDownloading data for {ticker} from {start_date} to {end_date}...")
    try:
        data = fetch_price_history(ticker, start_date, end_date)
    except DataFetchError as exc:
        print(f"\nData fetch error: {exc}")
        return
    except Exception:
        print(f"\n--- An Unexpected Error Occurred ---")
        print(f"An error occurred while trying to download data for '{ticker}'.")
        print("Here are the technical details:")
        traceback.print_exc()
        print("------------------------------------\n")
        return
        
    # --- Strategy and Backtesting ---
    print("Generating trading signals...")
    signals = strategy.generate_signals(data)

    if signals is None:
        print("\nBacktest could not be run due to issues with the data or strategy parameters.")
        return
    
    print("Running backtest...")
    results, portfolio = backtester.run_backtest(ticker, data, signals, initial_capital)
    
    # --- Display Results ---
    print("\n--- Backtest Results ---")
    print(f"Total Return: {results['total_return_pct']:.2f}%")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"Maximum Drawdown: {results['max_drawdown_pct']:.2f}%")
    print(f"Win Rate: {results['win_rate_pct']:.2f}%")
    print("--------------------------\n")


if __name__ == "__main__":
    main()

import numpy as np

def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
    """
    Calculates the Sharpe ratio.

    Args:
        returns (pd.Series): A pandas Series of daily returns.
        risk_free_rate (float): The annual risk-free rate.

    Returns:
        float: The annualized Sharpe ratio.
    """
    excess_returns = returns - (risk_free_rate / 252)
    sharpe_ratio = np.sqrt(252) * (excess_returns.mean() / excess_returns.std())
    return sharpe_ratio

def calculate_max_drawdown(equity_curve):
    """
    Calculates the maximum drawdown from an equity curve.

    Args:
        equity_curve (pd.Series): A pandas Series representing the portfolio's value over time.

    Returns:
        float: The maximum drawdown as a percentage.
    """
    # Calculate the running maximum
    running_max = equity_curve.cummax()
    # Calculate the drawdown
    drawdown = (equity_curve - running_max) / running_max
    max_drawdown = drawdown.min()
    return max_drawdown * 100



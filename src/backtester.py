import matplotlib.pyplot as plt
import pandas as pd

from . import performance


def run_backtest(
    ticker,
    data,
    signals,
    initial_capital=100000.0,
    stop_loss_pct=None,
    show_chart=True,
):
    """
    Runs a backtest on a given set of data and trading signals.
    """
    portfolio = pd.DataFrame(index=signals.index, columns=["holdings", "cash", "total"], dtype=float)
    portfolio[:] = 0.0

    cash = float(initial_capital)
    positions = 0.0
    last_buy_price = 0.0

    for i, idx in enumerate(signals.index):
        price = signals["Adj Close"].iloc[i]
        signal = signals["positions"].iloc[i]

        if signal == 1.0 and cash > 0:
            positions = cash / price
            cash = 0.0
            last_buy_price = price
        elif signal == -1.0 and positions > 0:
            cash = positions * price
            positions = 0.0
            last_buy_price = 0.0
        elif stop_loss_pct is not None and positions > 0:
            if price < last_buy_price * (1 - stop_loss_pct):
                cash = positions * price
                positions = 0.0
                last_buy_price = 0.0
                print(f"Stop-loss triggered on {idx.date()} at ${price:.2f}")

        holdings_value = positions * price
        total = cash + holdings_value
        portfolio.loc[idx, "holdings"] = holdings_value
        portfolio.loc[idx, "cash"] = cash
        portfolio.loc[idx, "total"] = total

    portfolio["returns"] = portfolio["total"].pct_change()

    total_return = (portfolio["total"].iloc[-1] / initial_capital - 1) * 100
    sharpe_ratio = performance.calculate_sharpe_ratio(portfolio["returns"])
    max_drawdown = performance.calculate_max_drawdown(portfolio["total"])

    if show_chart:
        plt.figure(figsize=(12, 8))
        plt.plot(portfolio["total"], label="Portfolio Value")
        plt.plot(
            signals.loc[signals.positions == 1.0].index,
            signals.short_mavg[signals.positions == 1.0],
            "^",
            markersize=10,
            color="g",
            lw=0,
            label="BUY",
        )
        plt.plot(
            signals.loc[signals.positions == -1.0].index,
            signals.short_mavg[signals.positions == -1.0],
            "v",
            markersize=10,
            color="r",
            lw=0,
            label="SELL",
        )
        plt.title(f"Equity Curve for {ticker}")
        plt.ylabel("Portfolio Value ($)")
        plt.xlabel("Date")
        plt.legend(loc="upper left")
        plt.grid(True)
        plt.show()

    trades = signals["positions"][signals["positions"] != 0]
    wins = 0
    for j in range(len(trades)):
        if trades.iloc[j] == 1.0 and j + 1 < len(trades) and trades.iloc[j + 1] == -1.0:
            buy_price = data["Adj Close"][trades.index[j]]
            sell_price = data["Adj Close"][trades.index[j + 1]]
            if sell_price > buy_price:
                wins += 1

    total_trades = len(trades) // 2
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0

    return (
        {
            "total_return_pct": total_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown_pct": max_drawdown,
            "win_rate_pct": win_rate,
        },
        portfolio,
    )

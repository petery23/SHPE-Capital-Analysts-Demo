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
    Runs a backtest with daily rebalancing toward target allocation.

    Instead of all-in / all-out flips, the backtester reads 'target_alloc'
    from the signals DataFrame (0.0–1.0) and rebalances the portfolio toward
    that target whenever the allocation tier changes by 25 percentage points
    or more. This implements gradual scaling in and out of positions.

    A 1% of portfolio minimum-trade filter prevents micro-rebalancing noise.
    Stop-loss still forces a full exit regardless of target allocation.
    """
    portfolio = pd.DataFrame(
        index=signals.index,
        columns=["holdings", "cash", "total"],
        dtype=float,
    )
    portfolio[:] = 0.0

    cash = float(initial_capital)
    shares = 0.0
    last_buy_price = 0.0
    has_target_alloc = "target_alloc" in signals.columns

    # Track last executed allocation to avoid rebalancing on tiny drift
    ALLOC_CHANGE_THRESHOLD = 0.25   # only rebalance on meaningful tier changes
    MIN_TRADE_FRACTION     = 0.01   # don't execute if trade < 1% of portfolio

    for i, idx in enumerate(signals.index):
        price = float(signals["Adj Close"].iloc[i])
        if price <= 0:
            portfolio.loc[idx] = [shares * price, cash, cash + shares * price]
            continue

        total_value = cash + shares * price

        # ── Stop-loss (always applied, overrides target allocation) ───────────
        if stop_loss_pct is not None and shares > 0 and last_buy_price > 0:
            if price < last_buy_price * (1 - stop_loss_pct):
                cash = shares * price
                shares = 0.0
                last_buy_price = 0.0
                print(f"Stop-loss triggered on {idx.date()} at ${price:.2f}")

        # ── Rebalance toward target allocation ────────────────────────────────
        if has_target_alloc:
            target_alloc = float(signals["target_alloc"].iloc[i])
            prev_alloc   = float(signals["target_alloc"].iloc[i - 1]) if i > 0 else 0.0

            # Only rebalance when the signal tier actually changes
            if abs(target_alloc - prev_alloc) >= ALLOC_CHANGE_THRESHOLD:
                total_value      = cash + shares * price
                target_holdings  = total_value * target_alloc
                current_holdings = shares * price
                delta            = target_holdings - current_holdings

                if delta > total_value * MIN_TRADE_FRACTION and cash >= delta:
                    # Scale in — buy more shares
                    shares += delta / price
                    cash   -= delta
                    if last_buy_price == 0.0:
                        last_buy_price = price

                elif delta < -total_value * MIN_TRADE_FRACTION and shares > 0:
                    # Scale out — sell some shares
                    sell_value  = min(abs(delta), shares * price)
                    shares     -= sell_value / price
                    cash       += sell_value
                    if shares < 1e-6:
                        shares         = 0.0
                        last_buy_price = 0.0
        else:
            # Fallback: legacy binary signal (all-in / all-out)
            signal = signals["positions"].iloc[i]
            if signal == 1.0 and cash > 0:
                shares         = cash / price
                cash           = 0.0
                last_buy_price = price
            elif signal == -1.0 and shares > 0:
                cash           = shares * price
                shares         = 0.0
                last_buy_price = 0.0

        holdings_value = shares * price
        total          = cash + holdings_value
        portfolio.loc[idx, "holdings"] = holdings_value
        portfolio.loc[idx, "cash"]     = cash
        portfolio.loc[idx, "total"]    = total

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
            label="BUY / ADD",
        )
        plt.plot(
            signals.loc[signals.positions == -1.0].index,
            signals.short_mavg[signals.positions == -1.0],
            "v",
            markersize=10,
            color="r",
            lw=0,
            label="SELL / TRIM",
        )
        plt.title(f"Equity Curve for {ticker}")
        plt.ylabel("Portfolio Value ($)")
        plt.xlabel("Date")
        plt.legend(loc="upper left")
        plt.grid(True)
        plt.show()

    # ── Win rate (buy→sell round trips) ──────────────────────────────────────
    trades      = signals["positions"][signals["positions"] != 0]
    wins        = 0
    total_trades = 0
    for j in range(len(trades)):
        if trades.iloc[j] == 1.0 and j + 1 < len(trades) and trades.iloc[j + 1] == -1.0:
            buy_price  = data["Adj Close"][trades.index[j]]
            sell_price = data["Adj Close"][trades.index[j + 1]]
            if sell_price > buy_price:
                wins += 1
            total_trades += 1

    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0

    return (
        {
            "total_return_pct": total_return,
            "sharpe_ratio":     sharpe_ratio,
            "max_drawdown_pct": max_drawdown,
            "win_rate_pct":     win_rate,
        },
        portfolio,
    )

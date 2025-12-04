import datetime as dt
import tkinter as tk
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from . import backtester, strategy
from .data_fetcher import DataFetchError, fetch_price_history


class BacktestApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Algo Backtester")
        self.geometry("920x720")
        self.configure(padx=16, pady=16)

        self._build_form()
        self.results_var = tk.StringVar(value="Run a backtest to see results here.")
        self.canvas_widget = None

    def _build_form(self) -> None:
        form_frame = ttk.LabelFrame(self, text="Input Parameters")
        form_frame.grid(row=0, column=0, sticky="ew")
        form_frame.columnconfigure(1, weight=1)

        ttk.Label(form_frame, text="Ticker").grid(row=0, column=0, sticky="w")
        self.ticker_entry = ttk.Entry(form_frame)
        self.ticker_entry.insert(0, "AAPL")
        self.ticker_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=4)

        ttk.Label(form_frame, text="Initial Capital ($)").grid(row=1, column=0, sticky="w")
        self.capital_entry = ttk.Entry(form_frame)
        self.capital_entry.insert(0, "10000")
        self.capital_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=4)

        ttk.Label(form_frame, text="Start Date (YYYY-MM-DD)").grid(row=2, column=0, sticky="w")
        self.start_entry = ttk.Entry(form_frame)
        self.start_entry.insert(0, "2023-01-01")
        self.start_entry.grid(row=2, column=1, sticky="ew", padx=8, pady=4)

        ttk.Label(form_frame, text="End Date (YYYY-MM-DD)").grid(row=3, column=0, sticky="w")
        self.end_entry = ttk.Entry(form_frame)
        self.end_entry.insert(0, "2024-01-01")
        self.end_entry.grid(row=3, column=1, sticky="ew", padx=8, pady=4)

        run_button = ttk.Button(form_frame, text="Run Backtest", command=self.run_backtest)
        run_button.grid(row=4, column=0, columnspan=2, pady=8)

        results_frame = ttk.LabelFrame(self, text="Performance Summary")
        results_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        results_label = ttk.Label(results_frame, textvariable=self.results_var, justify="left")
        results_label.grid(row=0, column=0, sticky="nsew")

        chart_frame = ttk.LabelFrame(self, text="Equity Curve")
        chart_frame.grid(row=2, column=0, sticky="nsew", pady=(12, 0))
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)

        self.chart_frame = chart_frame
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

    def run_backtest(self) -> None:
        ticker = self.ticker_entry.get().strip().upper()
        try:
            capital = float(self.capital_entry.get())
            if capital <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Initial capital must be a positive numeric value.")
            return

        try:
            start_date = dt.datetime.strptime(self.start_entry.get(), "%Y-%m-%d").date()
            end_date = dt.datetime.strptime(self.end_entry.get(), "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Invalid Input", "Dates must follow the YYYY-MM-DD format.")
            return

        if end_date <= start_date:
            messagebox.showerror("Invalid Input", "End date must be after the start date.")
            return

        try:
            data = fetch_price_history(ticker, start_date, end_date)
            signals = strategy.generate_signals(data)
            if signals is None:
                raise ValueError("Insufficient data for the selected range.")
            results, portfolio = backtester.run_backtest(
                ticker, data, signals, capital, show_chart=False
            )
        except DataFetchError as err:
            messagebox.showerror("Download Error", str(err))
            return
        except Exception as exc:
            messagebox.showerror("Unexpected Error", str(exc))
            return

        self.results_var.set(
            "\n".join(
                [
                    f"Ticker: {ticker}",
                    f"Initial Capital: ${capital:,.2f}",
                    f"Total Return: {results['total_return_pct']:.2f}%",
                    f"Sharpe Ratio: {results['sharpe_ratio']:.2f}",
                    f"Max Drawdown: {results['max_drawdown_pct']:.2f}%",
                    f"Win Rate: {results['win_rate_pct']:.2f}%",
                ]
            )
        )
        self._render_chart(portfolio)

    def _render_chart(self, portfolio):
        if self.canvas_widget:
            self.canvas_widget.get_tk_widget().destroy()

        fig = Figure(figsize=(6, 3), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(portfolio.index, portfolio["total"], label="Portfolio Value")
        ax.set_title("Portfolio Equity Curve")
        ax.set_xlabel("Date")
        ax.set_ylabel("Value ($)")
        ax.grid(True)
        ax.legend()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.canvas_widget = canvas


def launch_gui():
    app = BacktestApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()


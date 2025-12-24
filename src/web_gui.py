"""
Interactive Web-Based Portfolio Backtesting GUI
Smart capital allocation across multiple stocks based on individual performance.
"""

import datetime as dt
import json
import math

from flask import Flask, render_template_string, request, jsonify
import plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

from . import backtester, strategy
from .data_fetcher import DataFetchError, fetch_price_history

app = Flask(__name__)


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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SHPE Capital - Portfolio Analyzer</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        :root {
            /* SHPE UF palette */
            --navy: #001F5B;
            --blue: #0070C0;
            --baby-blue: #72A9B3;
            --red: #D33A02;
            --orange: #FD652F;
            --gray: #626366;

            /* Derived theme tokens aligned with shpeuf.com feel */
            --bg-primary: #f3f7fb;          /* very light background sections */
            --bg-secondary: var(--navy);    /* header/footer bands */
            --bg-card: #ffffff;             /* white cards like content panels */
            --bg-input: #f0f4fa;

            --accent-blue: var(--blue);
            --accent-blue-soft: #4a9bd8;
            --accent-baby: var(--baby-blue);
            --accent-green: var(--baby-blue);
            --accent-red: var(--red);
            --accent-orange: var(--orange);

            --text-primary: #0b1220;
            --text-secondary: #26314a;
            --text-muted: var(--gray);

            --border-color: #d0d8e8;
            --glow-primary: 0 0 24px rgba(0, 112, 192, 0.35);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 100vh;
            overflow: hidden;
            margin: 0;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 8px 16px;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        header {
            background: var(--orange);
            border-radius: 12px;
            padding: 8px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #ffffff;
            margin-bottom: 8px;
            flex-shrink: 0;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .logo-icon {
            width: 44px; height: 44px;
            background: linear-gradient(135deg, var(--orange), var(--red));
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            font-weight: 700;
            color: #ffffff;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }

        .logo-text h1 {
            font-size: 20px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }

        .logo-text span {
            font-size: 11px;
            color: rgba(255,255,255,0.8);
            letter-spacing: 2.2px;
            text-transform: uppercase;
        }

        .header-stats {
            display: flex;
            gap: 16px;
        }

        .header-stat {
            background: #ffffff;
            border-radius: 999px;
            padding: 6px 14px;
            text-align: center;
            min-width: 120px;
            border: 1px solid rgba(255,255,255,0.5);
        }

        .header-stat.profit {
            border-color: rgba(0, 112, 192, 0.8);
        }

        .header-stat.loss {
            border-color: rgba(211, 58, 2, 0.8);
        }

        .header-stat-label {
            font-size: 10px;
            color: rgba(0,0,0,0.65);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .header-stat-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 18px;
            font-weight: 700;
            margin-top: 2px;
        }

        .header-stat.profit .header-stat-value { color: var(--accent-blue); }
        .header-stat.loss .header-stat-value { color: var(--accent-red); }

        .main-layout {  
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 12px;
            flex: 1;
            min-height: 0;
            overflow: hidden;
        }

        .left-panel {
            display: flex;
            flex-direction: column;
            gap: 10px;
            min-height: 0;
            overflow: hidden;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 12px;
            box-shadow: 0 6px 16px rgba(0,0,0,0.06);
            flex-shrink: 0;
        }

        .card-title {
            font-size: 11px;
            font-weight: 500;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .card-title::before {
            content: '';
            width: 4px; height: 14px;
            background: linear-gradient(180deg, var(--accent-blue), var(--accent-orange));
            border-radius: 2px;
        }

        .form-group {
            margin-bottom: 8px;
        }

        .form-group label {
            display: block;
            font-size: 10px;
            color: var(--text-muted);
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .form-group input, .form-group textarea {
            width: 100%;
            padding: 8px 10px;
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-primary);
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            transition: all 0.3s ease;
        }

        .form-group textarea {
            resize: none;
            min-height: 60px;
            max-height: 60px;
        }

        .form-group input:focus, .form-group textarea:focus {
            outline: none;
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
        }

        .input-hint {
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 2px;
        }

        .help-toggle {
            background: none;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 11px;
            cursor: pointer;
            margin-bottom: 8px;
            width: 100%;
            text-align: left;
        }

        .help-toggle:hover {
            border-color: var(--accent-blue);
            color: var(--accent-blue);
        }

        .help-content {
            display: none;
            background: var(--bg-input);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 12px;
            font-size: 12px;
            line-height: 1.6;
            color: var(--text-secondary);
        }

        .help-content.show {
            display: block;
        }

        .help-content strong {
            color: var(--accent-blue);
        }

        .run-btn {
            width: 100%;
            padding: 10px;
            background: linear-gradient(135deg, var(--orange), var(--red));
            border: none;
            border-radius: 10px;
            color: #ffffff;
            font-family: 'Outfit', sans-serif;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .run-btn:hover {
            transform: translateY(-2px);
            box-shadow: var(--glow-primary);
        }

        .run-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .run-btn .spinner {
            display: none;
            width: 18px; height: 18px;
            border: 2px solid transparent;
            border-top-color: var(--bg-primary);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        .run-btn.loading .spinner { display: block; }
        .run-btn.loading .btn-text { display: none; }

        @keyframes spin { to { transform: rotate(360deg); } }

        .tuning-section {
            border-top: 1px solid var(--border-color);
            margin-top: 10px;
            padding-top: 10px;
        }

        .tuning-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }

        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 6px;
        }

        .checkbox-group input[type="checkbox"] {
            width: 18px; height: 18px;
            accent-color: var(--accent-blue);
        }

        .checkbox-group label {
            font-size: 12px;
            color: var(--text-secondary);
            cursor: pointer;
            margin: 0;
        }

        /* Right Panel */
        .right-panel {
            display: flex;
            flex-direction: column;
            gap: 12px;
            min-height: 0;
            overflow: hidden;
        }

        /* Portfolio Rankings */
        .rankings-card {
            background: #ffffff;
            display: flex;
            flex-direction: column;
            min-height: 0;
            max-height: 280px;
            overflow: hidden;
        }
        
        #rankingsContainer {
            overflow-y: auto;
            flex: 1;
            min-height: 0;
        }

        .rankings-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .stock-count {
            background: var(--orange);
            color: #ffffff;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }

        .rankings-table {
            width: 100%;
            border-collapse: collapse;
        }

        .rankings-table th {
            text-align: left;
            font-size: 10px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-color);
        }

        .rankings-table th.right { text-align: right; }

        .rankings-table td {
            padding: 8px 12px;
            border-bottom: 1px solid rgba(45, 55, 72, 0.5);
            font-size: 13px;
        }

        .rankings-table tr {
            cursor: pointer;
            transition: all 0.2s;
        }

        .rankings-table tr:hover {
            background: rgba(59, 130, 246, 0.1);
        }

        .rankings-table tr.selected {
            background: rgba(59, 130, 246, 0.2);
        }

        .rank-badge {
            width: 28px; height: 28px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 12px;
        }

        .rank-badge.gold { background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #000; }
        .rank-badge.silver { background: linear-gradient(135deg, #94a3b8, #64748b); color: #000; }
        .rank-badge.bronze { background: linear-gradient(135deg, #cd7f32, #a0522d); color: #fff; }
        .rank-badge.normal { background: var(--bg-input); color: var(--text-secondary); }

        .stock-ticker {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            color: var(--accent-blue);
        }

        .allocation-bar {
            width: 80px;
            height: 8px;
            background: var(--bg-input);
            border-radius: 4px;
            overflow: hidden;
        }

        .allocation-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
            border-radius: 4px;
        }

        .profit-cell {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            text-align: right;
        }

        .profit-cell.positive { color: var(--accent-green); }
        .profit-cell.negative { color: var(--accent-red); }

        .return-cell {
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            text-align: right;
            color: var(--text-secondary);
        }

        /* Chart Area */
        .chart-card {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
            overflow: hidden;
        }

        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .chart-tabs {
            display: flex;
            gap: 8px;
        }

        .chart-tab {
            background: #ffffff;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .chart-tab:hover {
            border-color: var(--accent-blue);
        }

        .chart-tab.active {
            background: var(--accent-blue);
            border-color: var(--accent-blue);
            color: #ffffff;
        }

        .chart-container {
            flex: 1;
            min-height: 280px;
            max-height: 400px;
        }

        .placeholder {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            min-height: 280px;
            color: var(--text-muted);
        }

        .placeholder-text {
            font-size: 18px;
            margin-bottom: 8px;
        }

        /* Animation controls */
        .anim-controls {
            display: none;
            align-items: center;
            gap: 10px;
            padding-top: 10px;
            border-top: 1px solid var(--border-color);
            margin-top: 10px;
            flex-shrink: 0;
        }

        .anim-controls.show { display: flex; }

        .anim-btn {
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 8px 14px;
            color: var(--text-primary);
            font-size: 13px;
            cursor: pointer;
        }

        .anim-btn:hover { border-color: var(--accent-blue); }
        .anim-btn.active { background: var(--accent-blue); border-color: var(--accent-blue); }

        .progress-bar {
            flex: 1;
            height: 6px;
            background: var(--bg-input);
            border-radius: 3px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-green));
            width: 0%;
            transition: width 0.1s;
        }

        .speed-control {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .speed-control label {
            font-size: 12px;
            color: var(--text-muted);
        }

        .speed-slider {
            width: 80px;
            accent-color: var(--accent-blue);
        }

        /* Toast */
        .toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            padding: 16px 32px;
            background: var(--accent-red);
            color: white;
            border-radius: 12px;
            font-weight: 500;
            opacity: 0;
            transition: all 0.3s ease;
            z-index: 1000;
        }

        .toast.show {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }

        /* Loading overlay */
        .loading-overlay {
            display: none;
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(243, 247, 251, 0.98));
            backdrop-filter: blur(8px);
            z-index: 10;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }

        .loading-overlay.show { display: flex; }

        .loading-spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(0, 112, 192, 0.1);
            border-top-color: var(--accent-blue);
            border-right-color: var(--accent-orange);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-bottom: 20px;
        }

        .loading-text {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
            margin-top: 8px;
            letter-spacing: 0.5px;
        }

        .loading-progress {
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            color: var(--accent-blue);
            margin-top: 8px;
            font-weight: 500;
        }

        /* Model modal */
        .modal-backdrop {
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.65);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 2000;
            padding: 16px;
        }
        .modal-backdrop.show { display: flex; }
        .modal {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            max-width: 960px;
            width: 100%;
            max-height: 90vh;
            padding: 24px 28px 28px;
            box-shadow: 0 18px 40px rgba(0,0,0,0.35);
            position: relative;
            display: flex;
            flex-direction: column;
        }
        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            position: sticky;
            top: 0;
            padding-bottom: 10px;
            margin-bottom: 8px;
            background: #ffffff; /* solid so title never clashes with scrolled content */
            z-index: 1;
        }
        .modal h2 {
            margin-bottom: 12px;
            font-size: 22px;
        }
        .modal h3 {
            margin-top: 18px;
            margin-bottom: 8px;
            font-size: 16px;
            color: var(--accent-blue);
        }
        .modal p, .modal li {
            color: var(--text-secondary);
            line-height: 1.6;
            font-size: 14px;
        }
        .modal ul { padding-left: 18px; margin: 8px 0; }
        .modal-content {
            overflow-y: auto;
            padding-top: 4px;
        }
        .close-btn {
            background: linear-gradient(135deg, var(--orange), var(--red));
            border: none;
            color: #ffffff;
            padding: 6px 14px;
            border-radius: 999px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            box-shadow: 0 0 12px rgba(0,0,0,0.18);
        }
        .close-btn:hover { filter: brightness(1.05); box-shadow: 0 0 16px rgba(0,0,0,0.25); }

        .error-item {
            background: #fff5f5;
            border-left: 4px solid var(--accent-red);
            padding: 12px 16px;
            margin-bottom: 12px;
            border-radius: 6px;
        }
        .error-item.warning {
            background: #fffbf0;
            border-left-color: var(--accent-orange);
        }
        .error-ticker {
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            color: var(--accent-red);
            margin-bottom: 6px;
            font-size: 14px;
        }
        .error-item.warning .error-ticker {
            color: var(--accent-orange);
        }
        .error-message {
            color: var(--text-secondary);
            font-size: 13px;
            line-height: 1.5;
        }
        .error-details {
            margin-top: 8px;
            padding-left: 16px;
        }
        .error-details li {
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }

        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 3px; }

        @media (max-width: 1100px) {
            .main-layout { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="modal-backdrop" id="modelModal">
            <div class="modal">
                <div class="modal-header">
                    <h2>How the Model Works</h2>
                    <button class="close-btn" onclick="closeModelInfo()">Close</button>
                </div>
                <div class="modal-content">
                    <p><strong>Goal:</strong> Identify trend shifts with SMA crossover, avoid overbought/oversold traps via RSI, and allocate more capital to stronger performers.</p>

                    <h3>Data</h3>
                    <ul>
                        <li>Price source: Yahoo Finance OHLCV via direct API calls.</li>
                        <li>Frequency: Daily bars for chosen date range.</li>
                    </ul>

                    <h3>Indicators & Features</h3>
                    <ul>
                        <li><strong>Fast SMA (default 20)</strong> — short-term trend.</li>
                        <li><strong>Slow SMA (default 50)</strong> — medium-term trend.</li>
                        <li><strong>RSI (14)</strong> — overbought/oversold filter (blocks buys & sells in extremes).</li>
                    </ul>

                    <h3>Signal Logic</h3>
                    <ul>
                        <li><strong>BUY:</strong> Fast SMA crosses above Slow SMA AND RSI &lt; 70.</li>
                        <li><strong>SELL:</strong> Fast SMA crosses below Slow SMA AND RSI &gt; 30.</li>
                        <li><strong>Hold:</strong> No crossover.</li>
                    </ul>

                    <h3>Backtesting Flow (per stock)</h3>
                    <ul>
                        <li>Fetch price history → compute indicators → generate signals.</li>
                        <li>Simulated trades with full capital per position (no leverage).</li>
                        <li>Outputs equity curve, profit, return %, Sharpe, max drawdown, win rate.</li>
                    </ul>

                    <h3>Portfolio Allocation</h3>
                    <ul>
                        <li><strong>Smart allocation (default):</strong> Weight by Sharpe ratio (shifted positive) so stronger/risk-adjusted performers get more capital.</li>
                        <li><strong>Equal weight:</strong> If smart allocation is disabled.</li>
                    </ul>

                    <h3>Why RSI Filter?</h3>
                    <p>Prevents buying into overbought spikes (RSI &gt; 70) and panic-selling in oversold dips (RSI &lt; 30), reducing whipsaws.</p>

                    <h3>What You Can Tune</h3>
                    <ul>
                        <li>Fast/Slow SMA windows.</li>
                        <li>RSI filter on/off.</li>
                        <li>Smart allocation on/off.</li>
                    </ul>

                    <h3>Outputs You’ll See</h3>
                    <ul>
                        <li>Animated portfolio equity curve with live profit/return.</li>
                        <li>Per-stock equity, buys/sells, SMAs, RSI filter effects.</li>
                        <li>Rankings table with allocation, profit, and return updating during animation.</li>
                    </ul>
                </div>
            </div>
        </div>
        <div class="modal-backdrop" id="warningModal" onclick="if(event.target === this) cancelAnalysis()">
            <div class="modal" style="max-width: 600px;" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h2 style="color: var(--accent-red);">⚠️ Validation Warnings</h2>
                </div>
                <div class="modal-content">
                    <p style="margin-bottom: 16px; color: var(--text-secondary);">
                        The following issues were found with the stocks you entered:
                    </p>
                    <div id="warningErrors" style="margin-bottom: 20px;"></div>
                    <div style="display: flex; gap: 12px; justify-content: flex-end; margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border-color);">
                        <button class="close-btn" onclick="cancelAnalysis()" style="background: var(--gray);">Cancel</button>
                        <button class="close-btn" id="continueBtn" onclick="continueAnalysis()">Continue Anyway</button>
                    </div>
                </div>
            </div>
        </div>
        <header>
            <div class="logo">
                <div class="logo-text">
                    <h1>SHPE Capital</h1>
                    <span>Technical Analysis Platform</span>
                </div>
            </div>
            <div class="header-stats" id="headerStats" style="display: none;">
                <div class="header-stat" id="totalProfitStat">
                    <div class="header-stat-label">Portfolio Profit</div>
                    <div class="header-stat-value" id="totalProfitValue">$0</div>
                </div>
                <div class="header-stat">
                    <div class="header-stat-label">Total Return</div>
                    <div class="header-stat-value" id="totalReturnValue" style="color: var(--text-primary);">0%</div>
                </div>
            </div>
        </header>

        <div class="main-layout">
            <div class="left-panel">
                <div class="card">
                    <div class="card-title">Portfolio Settings</div>
                    
                    <button class="help-toggle" onclick="openModelInfo()">&#9432; How does this work?</button>
                    <div class="help-content" id="helpContent">
                        <p><strong>Quick summary:</strong> SMA crossover + RSI filter, backtested per stock, weighted by Sharpe.</p>
                        <p style="margin-top: 8px;">Click the button above for the full breakdown.</p>
                    </div>

                    <form id="backtestForm">
                        <div class="form-group">
                            <label>Stock Tickers</label>
                            <textarea id="tickers" placeholder="AAPL, MSFT, GOOGL, NVDA, TSLA" required>AAPL, MSFT, GOOGL, NVDA, AMZN</textarea>
                            <div class="input-hint">Separate multiple tickers with commas</div>
                        </div>
                        <div class="form-group">
                            <label>Total Capital ($)</label>
                            <input type="number" id="capital" value="100000" min="1000" required>
                        </div>
                        <div class="form-group">
                            <label>Start Date</label>
                            <input type="date" id="startDate" value="2023-01-01" required>
                        </div>
                        <div class="form-group">
                            <label>End Date</label>
                            <input type="date" id="endDate" value="2024-06-01" required>
                        </div>

                        <div class="tuning-section">
                            <label style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; display: block;">Strategy Settings</label>
                            <div class="tuning-grid">
                                <div class="form-group" style="margin-bottom: 6px;">
                                    <label>Fast SMA</label>
                                    <input type="number" id="shortWindow" value="20" min="5" max="50">
                                </div>
                                <div class="form-group" style="margin-bottom: 6px;">
                                    <label>Slow SMA</label>
                                    <input type="number" id="longWindow" value="50" min="20" max="200">
                                </div>
                            </div>
                            <div class="checkbox-group">
                                <input type="checkbox" id="useRsi" checked>
                                <label for="useRsi">Use RSI Filter</label>
                            </div>
                            <div class="checkbox-group">
                                <input type="checkbox" id="smartAllocation" checked>
                                <label for="smartAllocation">Smart Allocation (weight by performance)</label>
                            </div>
                        </div>

                        <button type="submit" class="run-btn" id="runBtn" style="margin-top: 10px;">
                            <span class="btn-text">Analyze Portfolio</span>
                            <div class="spinner"></div>
                        </button>
                    </form>
                </div>
            </div>

            <div class="right-panel">
                <div class="card rankings-card" style="position: relative;">
                    <div class="rankings-header">
                        <div class="card-title" style="margin-bottom: 0;">Stock Rankings</div>
                        <div class="stock-count" id="stockCount">0 stocks</div>
                    </div>
                    <div id="rankingsContainer">
                        <div class="placeholder" style="min-height: 200px;">
                            <div style="font-size: 40px; opacity: 0.2; margin-bottom: 12px;">&#127942;</div>
                            <div>Stocks will be ranked by profit here</div>
                        </div>
                    </div>
                    <div class="loading-overlay" id="loadingOverlay">
                        <div class="loading-spinner"></div>
                        <div class="loading-text">Analyzing stocks...</div>
                        <div class="loading-progress" id="loadingProgress">0 / 0</div>
                    </div>
                </div>

                <div class="card chart-card">
                    <div class="chart-header">
                        <div class="card-title" style="margin-bottom: 0;">Performance Chart</div>
                        <div class="chart-tabs" id="chartTabs">
                            <button class="chart-tab active" data-view="portfolio">Portfolio</button>
                            <button class="chart-tab" data-view="individual">Individual</button>
                        </div>
                    </div>
                    <div class="chart-container" id="chartContainer">
                        <div class="placeholder">
                            <div style="font-size: 48px; opacity: 0.2; margin-bottom: 12px;">&#128200;</div>
                            <div class="placeholder-text">Run analysis to see charts</div>
                        </div>
                    </div>
                    <div class="anim-controls" id="animControls">
                        <button class="anim-btn" id="playBtn">&#9658; Play</button>
                        <button class="anim-btn" id="resetBtn">&#8634; Reset</button>
                        <button class="anim-btn" id="endBtn">&#9654;&#9654; End</button>
                        <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
                        <div class="speed-control">
                            <label>Speed</label>
                            <input type="range" class="speed-slider" id="speedSlider" min="1" max="50" value="25">
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        let portfolioData = null;
        let selectedStock = null;
        let currentView = 'portfolio';
        let animFrame = 0;
        let isPlaying = false;
        let animInterval = null;
        let pendingRequestData = null;

        function toggleHelp() {
            document.getElementById('helpContent').classList.toggle('show');
        }

        function openModelInfo() {
            const modal = document.getElementById('modelModal');
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
        }

        function closeModelInfo() {
            document.getElementById('modelModal').classList.remove('show');
            document.body.style.overflow = '';
        }

        function showWarningModal(errors, criticalErrors, warnings, canContinue) {
            const errorsContainer = document.getElementById('warningErrors');
            errorsContainer.innerHTML = '';
            
            errors.forEach(error => {
                const isWarning = error.error === 'partial_data';
                const errorDiv = document.createElement('div');
                errorDiv.className = `error-item ${isWarning ? 'warning' : ''}`;
                
                let html = `<div class="error-ticker">${error.ticker}</div>`;
                html += `<div class="error-message">${error.message}</div>`;
                
                if (error.issues && error.issues.length > 0) {
                    html += '<ul class="error-details">';
                    error.issues.forEach(issue => {
                        html += `<li>${issue.message}</li>`;
                    });
                    html += '</ul>';
                }
                
                errorDiv.innerHTML = html;
                errorsContainer.appendChild(errorDiv);
            });
            
            const continueBtn = document.getElementById('continueBtn');
            if (!canContinue) {
                continueBtn.style.display = 'none';
            } else {
                continueBtn.style.display = 'block';
            }
            
            const modal = document.getElementById('warningModal');
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
        }

        function closeWarningModal() {
            document.getElementById('warningModal').classList.remove('show');
            document.body.style.overflow = '';
        }

        function cancelAnalysis() {
            closeWarningModal();
            const runBtn = document.getElementById('runBtn');
            runBtn.classList.remove('loading');
            runBtn.disabled = false;
            document.getElementById('loadingOverlay').classList.remove('show');
            pendingRequestData = null;
        }

        async function continueAnalysis() {
            closeWarningModal();
            if (!pendingRequestData) return;
            
            // Add flag to skip validation and proceed
            pendingRequestData.skip_validation = true;
            
            const runBtn = document.getElementById('runBtn');
            const overlay = document.getElementById('loadingOverlay');
            overlay.classList.add('show');
            
            try {
                const response = await fetch('/api/portfolio', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(pendingRequestData)
                });

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.error || 'Analysis failed');
                }

                portfolioData = result;
                selectedStock = result.stocks[0]?.ticker;

                // Update header stats
                document.getElementById('headerStats').style.display = 'flex';
                const profitStat = document.getElementById('totalProfitStat');
                profitStat.className = 'header-stat ' + (result.total_profit >= 0 ? 'profit' : 'loss');
                document.getElementById('totalProfitValue').textContent = formatCurrency(result.total_profit);
                
                const retVal = document.getElementById('totalReturnValue');
                retVal.textContent = result.total_return_pct.toFixed(2) + '%';
                retVal.style.color = result.total_return_pct >= 0 ? 'var(--accent-blue)' : 'var(--accent-red)';

                // Render rankings and chart (start allocations at 0%)
                renderRankings(result.stocks, 0);
                renderPortfolioChart();

                document.getElementById('animControls').classList.add('show');

            } catch (error) {
                showToast(error.message);
            } finally {
                runBtn.classList.remove('loading');
                runBtn.disabled = false;
                overlay.classList.remove('show');
                pendingRequestData = null;
            }
        }

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 4000);
        }

        function formatCurrency(v) {
            const sign = v >= 0 ? '+' : '-';
            return sign + '$' + Math.abs(v).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }

        function renderRankings(stocks, frameIdx = null) {
            if (!stocks || stocks.length === 0) {
                document.getElementById('rankingsContainer').innerHTML = '<div class="placeholder" style="min-height:200px;"><div>No results</div></div>';
                return;
            }

            let html = '<table class="rankings-table"><thead><tr>';
            html += '<th>#</th><th>Ticker</th><th>Allocation</th><th class="right">Profit</th><th class="right">Return</th>';
            html += '</tr></thead><tbody>';

            stocks.forEach((s, i) => {
                // Default to final backtest metrics
                let profit = s.profit;
                let returnPct = s.return_pct;
                let allocPctDisplay = s.allocation_pct;

                // If we are animating and have per-stock values, compute dynamic metrics
                if (frameIdx !== null && portfolioData && Array.isArray(s.values) && s.values.length > 0) {
                    const maxIdx = s.values.length - 1;
                    let ratio;
                    if (maxIdx <= 0) {
                        ratio = 1;
                    } else if (frameIdx <= 0) {
                        ratio = 0;
                    } else {
                        ratio = Math.min(frameIdx / maxIdx, 1);
                    }
                    const idx = Math.round(ratio * maxIdx);
                    const currentVal = (s.values[idx] !== undefined ? s.values[idx] : s.allocation);
                    if (s.allocation && s.allocation > 0) {
                        profit = currentVal - s.allocation;
                        returnPct = (currentVal / s.allocation - 1) * 100;
                    } else {
                        profit = 0;
                        returnPct = 0;
                    }
                    allocPctDisplay = s.allocation_pct * ratio;
                }

                const rankClass = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : 'normal';
                const profitClass = profit >= 0 ? 'positive' : 'negative';
                const isSelected = selectedStock === s.ticker ? 'selected' : '';

                html += `<tr class="${isSelected}" onclick="selectStock('${s.ticker}')">`;
                html += `<td><div class="rank-badge ${rankClass}">${i + 1}</div></td>`;
                html += `<td class="stock-ticker">${s.ticker}</td>`;
                html += `<td><div style="display:flex;align-items:center;gap:8px;"><div class="allocation-bar"><div class="allocation-fill" style="width:${allocPctDisplay}%"></div></div><span style="font-size:12px;color:var(--text-muted)">${allocPctDisplay.toFixed(1)}%</span></div></td>`;
                html += `<td class="profit-cell ${profitClass}">${formatCurrency(profit)}</td>`;
                html += `<td class="return-cell">${returnPct.toFixed(2)}%</td>`;
                html += '</tr>';
            });

            html += '</tbody></table>';
            document.getElementById('rankingsContainer').innerHTML = html;
            document.getElementById('stockCount').textContent = stocks.length + ' stocks';
        }

        function selectStock(ticker) {
            selectedStock = ticker;
            // When selecting manually, show final metrics (no frame index)
            renderRankings(portfolioData.stocks);
            if (currentView === 'individual') {
                renderIndividualChart(ticker);
            }
        }

        function updateProfitDisplay(currentValue, capital) {
            const profit = currentValue - capital;
            const returnPct = ((currentValue / capital) - 1) * 100;
            
            const profitStat = document.getElementById('totalProfitStat');
            profitStat.className = 'header-stat ' + (profit >= 0 ? 'profit' : 'loss');
            document.getElementById('totalProfitValue').textContent = formatCurrency(profit);
            
            const retVal = document.getElementById('totalReturnValue');
            retVal.textContent = returnPct.toFixed(2) + '%';
            retVal.style.color = returnPct >= 0 ? 'var(--accent-blue)' : 'var(--accent-red)';
        }

        function renderAnimatedPortfolioChart() {
            if (!portfolioData) return;
            
            document.getElementById('chartContainer').innerHTML = '';
            document.getElementById('animControls').classList.add('show');
            
            const capital = portfolioData.total_capital;
            animFrame = 0;
            
            // Initial empty chart
            const traces = [{
                x: [],
                y: [],
                type: 'scatter',
                mode: 'lines',
                name: 'Portfolio Total',
                line: { color: '#0070C0', width: 3 },
                fill: 'tozeroy',
                fillcolor: 'rgba(0, 112, 192, 0.08)'
            }];

            const layout = {
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: '#f0f4fa',
                font: { family: 'Outfit', color: '#0b1220' },
                showlegend: true,
                legend: { orientation: 'h', y: -0.15, x: 0.5, xanchor: 'center' },
                margin: { l: 60, r: 30, t: 20, b: 60 },
                xaxis: { 
                    showgrid: true, 
                    gridcolor: '#d0d8e8',
                    range: [portfolioData.dates[0], portfolioData.dates[portfolioData.dates.length - 1]]
                },
                yaxis: { 
                    showgrid: true, 
                    gridcolor: '#d0d8e8', 
                    tickprefix: '$', 
                    tickformat: ',.0f',
                    range: [0, Math.max(...portfolioData.portfolio_values) * 1.1]
                },
                hovermode: 'x unified'
            };

            Plotly.newPlot('chartContainer', traces, layout, { responsive: true, displayModeBar: false });
            
            // Start animation after a small delay
            updateProfitDisplay(capital, capital);
            setTimeout(() => startAnimation(), 300);
        }

        function animateFrame() {
            if (!portfolioData || animFrame >= portfolioData.dates.length) {
                stopAnimation();
                return;
            }
            
            const endIdx = animFrame + 1;
            const dates = portfolioData.dates.slice(0, endIdx);
            const values = portfolioData.portfolio_values.slice(0, endIdx);
            
            // Update chart
            Plotly.update('chartContainer', {
                x: [dates],
                y: [values]
            }, {}, [0]);
            
            // Update profit display with current value
            const currentValue = values[values.length - 1] || portfolioData.total_capital;
            updateProfitDisplay(currentValue, portfolioData.total_capital);
            
            // Update per-stock rankings dynamically to match current frame (use last index we just drew)
            if (portfolioData.stocks && Array.isArray(portfolioData.stocks)) {
                renderRankings(portfolioData.stocks, endIdx - 1);
            }
            
            // Update progress bar
            const progress = (endIdx / portfolioData.dates.length) * 100;
            document.getElementById('progressFill').style.width = progress + '%';
            
            animFrame++;
        }

        function startAnimation() {
            if (isPlaying || !portfolioData) return;
            isPlaying = true;
            document.getElementById('playBtn').innerHTML = '&#10074;&#10074; Pause';
            document.getElementById('playBtn').classList.add('active');
            
            const speed = 51 - document.getElementById('speedSlider').value;
            animInterval = setInterval(animateFrame, speed * 2);
        }

        function stopAnimation() {
            isPlaying = false;
            document.getElementById('playBtn').innerHTML = '&#9658; Play';
            document.getElementById('playBtn').classList.remove('active');
            if (animInterval) {
                clearInterval(animInterval);
                animInterval = null;
            }
        }

        function resetAnimation() {
            stopAnimation();
            animFrame = 0;
            document.getElementById('progressFill').style.width = '0%';
            if (portfolioData) {
                updateProfitDisplay(portfolioData.total_capital, portfolioData.total_capital);
                Plotly.update('chartContainer', { x: [[]], y: [[]] }, {}, [0]);
                // Reset rankings to 0% allocations and zero P&L
                renderRankings(portfolioData.stocks, 0);
            }
        }

        function skipToEnd() {
            if (!portfolioData) return;
            stopAnimation();

            const lastIdx = portfolioData.dates.length - 1;
            if (lastIdx < 0) return;

            const dates = portfolioData.dates.slice();
            const values = portfolioData.portfolio_values.slice();

            Plotly.update('chartContainer', {
                x: [dates],
                y: [values]
            }, {}, [0]);

            const finalValue = values[values.length - 1] || portfolioData.total_capital;
            updateProfitDisplay(finalValue, portfolioData.total_capital);

            // Show final rankings/allocations
            renderRankings(portfolioData.stocks, null);
            document.getElementById('progressFill').style.width = '100%';
            animFrame = portfolioData.dates.length;
        }

        document.getElementById('playBtn').addEventListener('click', () => {
            if (isPlaying) stopAnimation();
            else startAnimation();
        });

        document.getElementById('resetBtn').addEventListener('click', resetAnimation);
        document.getElementById('endBtn').addEventListener('click', skipToEnd);

        document.getElementById('speedSlider').addEventListener('input', () => {
            if (isPlaying) {
                stopAnimation();
                startAnimation();
            }
        });

        function renderPortfolioChart() {
            renderAnimatedPortfolioChart();
        }

        function renderIndividualChart(ticker) {
            if (!portfolioData) return;
            const stock = portfolioData.stocks.find(s => s.ticker === ticker);
            if (!stock) return;

            document.getElementById('chartContainer').innerHTML = '';

            const traces = [
                {
                    x: stock.dates,
                    y: stock.prices,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Price',
                    line: { color: '#0070C0', width: 2 },
                    fill: 'tozeroy',
                    fillcolor: 'rgba(0, 112, 192, 0.08)'
                },
                {
                    x: stock.dates,
                    y: stock.short_ma,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Fast SMA',
                    line: { color: '#FD652F', width: 1.5, dash: 'dot' }
                },
                {
                    x: stock.dates,
                    y: stock.long_ma,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Slow SMA',
                    line: { color: '#72A9B3', width: 1.5, dash: 'dot' }
                }
            ];

            if (stock.buys.length > 0) {
                traces.push({
                    x: stock.buys.map(b => b.date),
                    y: stock.buys.map(b => b.price),
                    type: 'scatter',
                    mode: 'markers',
                    name: 'BUY',
                    marker: { symbol: 'triangle-up', size: 14, color: '#0070C0', line: { color: 'white', width: 2 } }
                });
            }

            if (stock.sells.length > 0) {
                traces.push({
                    x: stock.sells.map(s => s.date),
                    y: stock.sells.map(s => s.price),
                    type: 'scatter',
                    mode: 'markers',
                    name: 'SELL',
                    marker: { symbol: 'triangle-down', size: 14, color: '#D33A02', line: { color: 'white', width: 2 } }
                });
            }

            const layout = {
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: '#f0f4fa',
                font: { family: 'Outfit', color: '#0b1220' },
                title: { text: stock.ticker + ' - ' + (stock.profit >= 0 ? '+' : '') + '$' + stock.profit.toFixed(2), font: { size: 16 } },
                showlegend: true,
                legend: { orientation: 'h', y: -0.15 },
                margin: { l: 60, r: 30, t: 40, b: 60 },
                xaxis: { showgrid: true, gridcolor: '#d0d8e8' },
                yaxis: { showgrid: true, gridcolor: '#d0d8e8', tickprefix: '$' },
                hovermode: 'x unified'
            };

            Plotly.newPlot('chartContainer', traces, layout, { responsive: true, displayModeBar: false });
        }

        // Chart tab switching
        document.querySelectorAll('.chart-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.chart-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentView = tab.dataset.view;
                
                if (currentView === 'portfolio') {
                    renderPortfolioChart();
                } else if (selectedStock) {
                    renderIndividualChart(selectedStock);
                } else if (portfolioData && portfolioData.stocks.length > 0) {
                    selectedStock = portfolioData.stocks[0].ticker;
                    renderRankings(portfolioData.stocks);
                    renderIndividualChart(selectedStock);
                }
            });
        });

        // Form submission
        document.getElementById('backtestForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const runBtn = document.getElementById('runBtn');
            runBtn.classList.add('loading');
            runBtn.disabled = true;

            const overlay = document.getElementById('loadingOverlay');
            overlay.classList.add('show');

            const tickers = document.getElementById('tickers').value
                .split(',')
                .map(t => t.trim().toUpperCase())
                .filter(t => t.length > 0);

            document.getElementById('loadingProgress').textContent = `0 / ${tickers.length}`;

            const data = {
                tickers: tickers,
                capital: parseFloat(document.getElementById('capital').value),
                start_date: document.getElementById('startDate').value,
                end_date: document.getElementById('endDate').value,
                short_window: parseInt(document.getElementById('shortWindow').value),
                long_window: parseInt(document.getElementById('longWindow').value),
                use_rsi: document.getElementById('useRsi').checked,
                smart_allocation: document.getElementById('smartAllocation').checked
            };

            try {
                const response = await fetch('/api/portfolio', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.error || 'Analysis failed');
                }

                // Check if this is a validation error response
                if (result.validation_errors) {
                    pendingRequestData = data;
                    showWarningModal(
                        result.errors,
                        result.critical_errors,
                        result.warnings,
                        result.can_continue
                    );
                    // Don't hide loading yet - user will decide
                    return;
                }

                portfolioData = result;
                selectedStock = result.stocks[0]?.ticker;

                // Update header stats
                document.getElementById('headerStats').style.display = 'flex';
                const profitStat = document.getElementById('totalProfitStat');
                profitStat.className = 'header-stat ' + (result.total_profit >= 0 ? 'profit' : 'loss');
                document.getElementById('totalProfitValue').textContent = formatCurrency(result.total_profit);
                
                const retVal = document.getElementById('totalReturnValue');
                retVal.textContent = result.total_return_pct.toFixed(2) + '%';
                retVal.style.color = result.total_return_pct >= 0 ? 'var(--accent-blue)' : 'var(--accent-red)';

                // Render rankings and chart (start allocations at 0%)
                renderRankings(result.stocks, 0);
                renderPortfolioChart();

                document.getElementById('animControls').classList.add('show');

            } catch (error) {
                showToast(error.message);
            } finally {
                runBtn.classList.remove('loading');
                runBtn.disabled = false;
                overlay.classList.remove('show');
            }
        });
    </script>
</body>
</html>
"""


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
        
        # Buy/sell signals
        buys = []
        sells = []
        buy_mask = signals['positions'] == 1.0
        sell_mask = signals['positions'] == -1.0
        
        for idx in signals[buy_mask].index:
            buys.append({'date': idx.strftime('%Y-%m-%d'), 'price': clean_for_json(float(price_data.loc[idx, 'Adj Close']))})
        for idx in signals[sell_mask].index:
            sells.append({'date': idx.strftime('%Y-%m-%d'), 'price': clean_for_json(float(price_data.loc[idx, 'Adj Close']))})
        
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


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


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
                'buys': s['buys'],
                'sells': s['sells']
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

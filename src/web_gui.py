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
            --bg-primary: #0a0f1a;
            --bg-secondary: #111827;
            --bg-card: #1a2332;
            --bg-input: #0d1421;
            --accent-green: #00ff88;
            --accent-red: #ff4757;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
            --accent-gold: #fbbf24;
            --accent-cyan: #22d3ee;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border-color: #2d3748;
            --glow-green: 0 0 30px rgba(0, 255, 136, 0.4);
            --glow-red: 0 0 30px rgba(255, 71, 87, 0.4);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }

        body::before {
            content: '';
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: 
                radial-gradient(ellipse at 10% 10%, rgba(59, 130, 246, 0.1) 0%, transparent 40%),
                radial-gradient(ellipse at 90% 90%, rgba(139, 92, 246, 0.1) 0%, transparent 40%);
            pointer-events: none;
            z-index: -1;
        }

        .container {
            max-width: 1800px;
            margin: 0 auto;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .logo-icon {
            width: 50px; height: 50px;
            background: linear-gradient(135deg, var(--accent-green), var(--accent-blue));
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 26px;
            font-weight: 700;
            color: var(--bg-primary);
            box-shadow: 0 4px 20px rgba(0, 255, 136, 0.3);
        }

        .logo-text h1 {
            font-size: 26px;
            font-weight: 600;
            background: linear-gradient(135deg, var(--accent-green), var(--accent-blue));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .logo-text span {
            font-size: 12px;
            color: var(--text-muted);
            letter-spacing: 3px;
            text-transform: uppercase;
        }

        .header-stats {
            display: flex;
            gap: 16px;
        }

        .header-stat {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 12px 20px;
            text-align: center;
            min-width: 140px;
        }

        .header-stat.profit {
            border-color: var(--accent-green);
            background: linear-gradient(135deg, rgba(0, 255, 136, 0.1), transparent);
        }

        .header-stat.loss {
            border-color: var(--accent-red);
            background: linear-gradient(135deg, rgba(255, 71, 87, 0.1), transparent);
        }

        .header-stat-label {
            font-size: 10px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .header-stat-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 22px;
            font-weight: 700;
            margin-top: 4px;
        }

        .header-stat.profit .header-stat-value { color: var(--accent-green); }
        .header-stat.loss .header-stat-value { color: var(--accent-red); }

        .main-layout {
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 20px;
            flex: 1;
            margin-top: 20px;
            min-height: 0;
        }

        .left-panel {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 20px;
        }

        .card-title {
            font-size: 13px;
            font-weight: 500;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .card-title::before {
            content: '';
            width: 4px; height: 14px;
            background: linear-gradient(180deg, var(--accent-blue), var(--accent-purple));
            border-radius: 2px;
        }

        .form-group {
            margin-bottom: 14px;
        }

        .form-group label {
            display: block;
            font-size: 11px;
            color: var(--text-muted);
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .form-group input, .form-group textarea {
            width: 100%;
            padding: 12px 14px;
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            color: var(--text-primary);
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            transition: all 0.3s ease;
        }

        .form-group textarea {
            resize: vertical;
            min-height: 80px;
        }

        .form-group input:focus, .form-group textarea:focus {
            outline: none;
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
        }

        .input-hint {
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 4px;
        }

        .help-toggle {
            background: none;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 12px;
            cursor: pointer;
            margin-bottom: 12px;
            width: 100%;
            text-align: left;
        }

        .help-toggle:hover {
            border-color: var(--accent-blue);
            color: var(--text-primary);
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
            padding: 14px;
            background: linear-gradient(135deg, var(--accent-green), #00cc6a);
            border: none;
            border-radius: 12px;
            color: var(--bg-primary);
            font-family: 'Outfit', sans-serif;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .run-btn:hover {
            transform: translateY(-2px);
            box-shadow: var(--glow-green);
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
            margin-top: 16px;
            padding-top: 16px;
        }

        .tuning-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }

        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 10px;
        }

        .checkbox-group input[type="checkbox"] {
            width: 18px; height: 18px;
            accent-color: var(--accent-blue);
        }

        .checkbox-group label {
            font-size: 13px;
            color: var(--text-secondary);
            cursor: pointer;
            margin: 0;
        }

        /* Right Panel */
        .right-panel {
            display: flex;
            flex-direction: column;
            gap: 16px;
            min-height: 0;
        }

        /* Portfolio Rankings */
        .rankings-card {
            background: linear-gradient(135deg, var(--bg-card), #1e2d3d);
        }

        .rankings-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .stock-count {
            background: var(--accent-purple);
            color: white;
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
            padding: 12px;
            border-bottom: 1px solid rgba(45, 55, 72, 0.5);
            font-size: 14px;
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
            min-height: 400px;
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
            background: var(--bg-input);
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
            color: white;
        }

        .chart-container {
            flex: 1;
            min-height: 350px;
        }

        .placeholder {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            min-height: 350px;
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
            gap: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--border-color);
            margin-top: 12px;
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
            background: rgba(10, 15, 26, 0.9);
            z-index: 10;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border-radius: 16px;
        }

        .loading-overlay.show { display: flex; }

        .loading-text {
            font-size: 16px;
            color: var(--text-secondary);
            margin-top: 16px;
        }

        .loading-progress {
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            color: var(--accent-blue);
            margin-top: 8px;
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
        <header>
            <div class="logo">
                <div class="logo-icon">S</div>
                <div class="logo-text">
                    <h1>SHPE Capital</h1>
                    <span>Smart Portfolio Analyzer</span>
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
                    
                    <button class="help-toggle" onclick="toggleHelp()">&#9432; How does this work?</button>
                    <div class="help-content" id="helpContent">
                        <p><strong>Smart Allocation:</strong> Enter multiple stocks and the system will analyze each one, then allocate MORE capital to better-performing stocks.</p>
                        <p style="margin-top: 8px;"><strong>Strategy:</strong> Uses SMA crossover (when fast average crosses slow average = trade signal) + RSI filter to avoid bad entries.</p>
                        <p style="margin-top: 8px;"><strong>Ranking:</strong> Stocks are scored by Sharpe ratio (risk-adjusted returns) to determine allocation.</p>
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
                            <label style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; display: block;">Strategy Settings</label>
                            <div class="tuning-grid">
                                <div class="form-group" style="margin-bottom: 8px;">
                                    <label>Fast SMA</label>
                                    <input type="number" id="shortWindow" value="20" min="5" max="50">
                                </div>
                                <div class="form-group" style="margin-bottom: 8px;">
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

                        <button type="submit" class="run-btn" id="runBtn" style="margin-top: 16px;">
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
                        <div class="spinner" style="width: 40px; height: 40px; border-width: 3px; border-color: var(--accent-blue); border-top-color: transparent; display: block;"></div>
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

        function toggleHelp() {
            document.getElementById('helpContent').classList.toggle('show');
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

        function renderRankings(stocks) {
            if (!stocks || stocks.length === 0) {
                document.getElementById('rankingsContainer').innerHTML = '<div class="placeholder" style="min-height:200px;"><div>No results</div></div>';
                return;
            }

            let html = '<table class="rankings-table"><thead><tr>';
            html += '<th>#</th><th>Ticker</th><th>Allocation</th><th class="right">Profit</th><th class="right">Return</th>';
            html += '</tr></thead><tbody>';

            stocks.forEach((s, i) => {
                const rankClass = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : 'normal';
                const profitClass = s.profit >= 0 ? 'positive' : 'negative';
                const isSelected = selectedStock === s.ticker ? 'selected' : '';
                
                html += `<tr class="${isSelected}" onclick="selectStock('${s.ticker}')">`;
                html += `<td><div class="rank-badge ${rankClass}">${i + 1}</div></td>`;
                html += `<td class="stock-ticker">${s.ticker}</td>`;
                html += `<td><div style="display:flex;align-items:center;gap:8px;"><div class="allocation-bar"><div class="allocation-fill" style="width:${s.allocation_pct}%"></div></div><span style="font-size:12px;color:var(--text-muted)">${s.allocation_pct.toFixed(1)}%</span></div></td>`;
                html += `<td class="profit-cell ${profitClass}">${formatCurrency(s.profit)}</td>`;
                html += `<td class="return-cell">${s.return_pct.toFixed(2)}%</td>`;
                html += '</tr>';
            });

            html += '</tbody></table>';
            document.getElementById('rankingsContainer').innerHTML = html;
            document.getElementById('stockCount').textContent = stocks.length + ' stocks';
        }

        function selectStock(ticker) {
            selectedStock = ticker;
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
            retVal.style.color = returnPct >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
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
                line: { color: '#00ff88', width: 3 },
                fill: 'tozeroy',
                fillcolor: 'rgba(0, 255, 136, 0.1)'
            }];

            const layout = {
                template: 'plotly_dark',
                paper_bgcolor: '#1a2332',
                plot_bgcolor: '#0d1421',
                font: { family: 'Outfit', color: '#f8fafc' },
                showlegend: true,
                legend: { orientation: 'h', y: -0.15, x: 0.5, xanchor: 'center' },
                margin: { l: 60, r: 30, t: 20, b: 60 },
                xaxis: { 
                    showgrid: true, 
                    gridcolor: 'rgba(45,55,72,0.5)',
                    range: [portfolioData.dates[0], portfolioData.dates[portfolioData.dates.length - 1]]
                },
                yaxis: { 
                    showgrid: true, 
                    gridcolor: 'rgba(45,55,72,0.5)', 
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
            }
        }

        document.getElementById('playBtn').addEventListener('click', () => {
            if (isPlaying) stopAnimation();
            else startAnimation();
        });

        document.getElementById('resetBtn').addEventListener('click', resetAnimation);

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
                    line: { color: '#3b82f6', width: 2 },
                    fill: 'tozeroy',
                    fillcolor: 'rgba(59, 130, 246, 0.1)'
                },
                {
                    x: stock.dates,
                    y: stock.short_ma,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Fast SMA',
                    line: { color: '#f59e0b', width: 1.5, dash: 'dot' }
                },
                {
                    x: stock.dates,
                    y: stock.long_ma,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Slow SMA',
                    line: { color: '#8b5cf6', width: 1.5, dash: 'dot' }
                }
            ];

            if (stock.buys.length > 0) {
                traces.push({
                    x: stock.buys.map(b => b.date),
                    y: stock.buys.map(b => b.price),
                    type: 'scatter',
                    mode: 'markers',
                    name: 'BUY',
                    marker: { symbol: 'triangle-up', size: 14, color: '#00ff88', line: { color: 'white', width: 2 } }
                });
            }

            if (stock.sells.length > 0) {
                traces.push({
                    x: stock.sells.map(s => s.date),
                    y: stock.sells.map(s => s.price),
                    type: 'scatter',
                    mode: 'markers',
                    name: 'SELL',
                    marker: { symbol: 'triangle-down', size: 14, color: '#ff4757', line: { color: 'white', width: 2 } }
                });
            }

            const layout = {
                template: 'plotly_dark',
                paper_bgcolor: '#1a2332',
                plot_bgcolor: '#0d1421',
                font: { family: 'Outfit', color: '#f8fafc' },
                title: { text: stock.ticker + ' - ' + (stock.profit >= 0 ? '+' : '') + '$' + stock.profit.toFixed(2), font: { size: 16 } },
                showlegend: true,
                legend: { orientation: 'h', y: -0.15 },
                margin: { l: 60, r: 30, t: 40, b: 60 },
                xaxis: { showgrid: true, gridcolor: 'rgba(45,55,72,0.5)' },
                yaxis: { showgrid: true, gridcolor: 'rgba(45,55,72,0.5)', tickprefix: '$' },
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

                portfolioData = result;
                selectedStock = result.stocks[0]?.ticker;

                // Update header stats
                document.getElementById('headerStats').style.display = 'flex';
                const profitStat = document.getElementById('totalProfitStat');
                profitStat.className = 'header-stat ' + (result.total_profit >= 0 ? 'profit' : 'loss');
                document.getElementById('totalProfitValue').textContent = formatCurrency(result.total_profit);
                
                const retVal = document.getElementById('totalReturnValue');
                retVal.textContent = result.total_return_pct.toFixed(2) + '%';
                retVal.style.color = result.total_return_pct >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';

                // Render rankings and chart
                renderRankings(result.stocks);
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

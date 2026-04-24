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
                const headerStats = document.getElementById('headerStats');
                headerStats.classList.remove('header-stats-hidden');
                headerStats.classList.add('header-stats-visible');
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
                const buyText = stock.buys.map(b => {
                    const amount = (b.amount != null && b.amount !== undefined) ? '$' + b.amount.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : 'N/A';
                    const shares = (b.shares != null && b.shares !== undefined) ? b.shares.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : 'N/A';
                    return `BUY<br>Price: $${b.price.toFixed(2)}<br>Amount: ${amount}<br>Shares: ${shares}`;
                });
                traces.push({
                    x: stock.buys.map(b => b.date),
                    y: stock.buys.map(b => b.price),
                    text: buyText,
                    type: 'scatter',
                    mode: 'markers',
                    name: 'BUY',
                    marker: { symbol: 'triangle-up', size: 14, color: '#0070C0', line: { color: 'white', width: 2 } },
                    hovertemplate: '%{text}<extra></extra>'
                });
            }

            if (stock.sells.length > 0) {
                const sellText = stock.sells.map(s => {
                    const amount = (s.amount != null && s.amount !== undefined) ? '$' + s.amount.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : 'N/A';
                    const shares = (s.shares != null && s.shares !== undefined) ? s.shares.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : 'N/A';
                    return `SELL<br>Price: $${s.price.toFixed(2)}<br>Amount: ${amount}<br>Shares: ${shares}`;
                });
                traces.push({
                    x: stock.sells.map(s => s.date),
                    y: stock.sells.map(s => s.price),
                    text: sellText,
                    type: 'scatter',
                    mode: 'markers',
                    name: 'SELL',
                    marker: { symbol: 'triangle-down', size: 14, color: '#D33A02', line: { color: 'white', width: 2 } },
                    hovertemplate: '%{text}<extra></extra>'
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
                const headerStats = document.getElementById('headerStats');
                headerStats.classList.remove('header-stats-hidden');
                headerStats.classList.add('header-stats-visible');
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
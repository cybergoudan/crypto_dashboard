const fs = require('fs');

let html = fs.readFileSync('index.html', 'utf8');

// ==== 1. CSS ====
const cssTarget = '/* 表格行悬停效果 */';
const cssReplace = `
        /* K线周期切换栏 */
        .tf-bar {
            padding: 10px 20px;
            background: #1f2937;
            border-bottom: 1px solid var(--border-col);
            display: flex;
            gap: 10px;
        }
        .tf-btn {
            background: transparent; border: 1px solid #374151; color: #9ca3af;
            padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px;
            transition: all 0.2s;
        }
        .tf-btn:hover { background: #374151; color: #fff; }
        .tf-btn.active { background: var(--accent-blue); color: #fff; border-color: var(--accent-blue); }

        /* 表格行悬停效果 */`;
if (html.includes(cssTarget)) html = html.replace(cssTarget, cssReplace);

// ==== 2. HTML ====
const htmlTarget = '<div id="tv-chart"></div>';
const htmlReplace = `
                <div class="tf-bar">
                    <button class="tf-btn" id="tf-1m" onclick="changeTimeframe('1m')">1分钟</button>
                    <button class="tf-btn" id="tf-5m" onclick="changeTimeframe('5m')">5分钟</button>
                    <button class="tf-btn active" id="tf-15m" onclick="changeTimeframe('15m')">15分钟</button>
                    <button class="tf-btn" id="tf-1h" onclick="changeTimeframe('1h')">1小时</button>
                    <button class="tf-btn" id="tf-4h" onclick="changeTimeframe('4h')">4小时</button>
                    <button class="tf-btn" id="tf-1d" onclick="changeTimeframe('1d')">1天</button>
                    <button class="tf-btn" id="tf-1w" onclick="changeTimeframe('1w')">1周</button>
                    <button class="tf-btn" id="tf-1M" onclick="changeTimeframe('1M')">1月</button>
                </div>
                <div id="tv-chart"></div>`;
if (html.includes(htmlTarget)) html = html.replace(htmlTarget, htmlReplace);

// ==== 3. JS State ====
const stateTarget = 'let candleSeries = null;';
const stateReplace = 'let candleSeries = null;\n        let currentChartState = {};';
if (html.includes(stateTarget)) html = html.replace(stateTarget, stateReplace);

// ==== 4. JS Logic Refactor ====
const openChartStart = html.indexOf('function openChart');
const initEnd = html.indexOf('// Init');
if (openChartStart > -1 && initEnd > -1) {
    const newJsLogic = `
        function openChart(symbol, side, entryPrice, entryTimeUnix) {
            currentChartState = { symbol, side, entryPrice, entryTimeUnix, interval: '15m' };
            document.getElementById('chart-modal').style.display = 'flex';
            
            const tvContainer = document.getElementById('tv-chart');
            tvContainer.innerHTML = '';
            
            chartInstance = LightweightCharts.createChart(tvContainer, {
                width: 798,
                height: 440,
                layout: { background: { type: 'solid', color: '#1a1c23' }, textColor: '#d1d5db' },
                grid: { vertLines: { color: '#2d3748' }, horzLines: { color: '#2d3748' } },
                crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
                timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#2d3748' },
            });

            candleSeries = chartInstance.addSeries(LightweightCharts.CandlestickSeries, {
                upColor: '#22c55e', downColor: '#ef4444', borderVisible: false,
                wickUpColor: '#22c55e', wickDownColor: '#ef4444'
            });

            changeTimeframe('15m');
        }

        function changeTimeframe(interval) {
            // Update UI buttons
            document.querySelectorAll('.tf-btn').forEach(btn => btn.classList.remove('active'));
            const activeBtn = document.getElementById('tf-' + interval);
            if(activeBtn) activeBtn.classList.add('active');
            
            currentChartState.interval = interval;
            const { symbol, side, entryPrice, entryTimeUnix } = currentChartState;
            
            document.getElementById('chart-title').innerText = \`\${symbol} 现货复盘 (\${interval}线)\`;
            document.getElementById('chart-subtitle').innerText = "加载历史 K 线及计算标记位...";

            const url = \`https://api.binance.com/api/v3/klines?symbol=\${symbol}&interval=\${interval}&limit=500\`;
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 8000);

            fetch(url, { signal: controller.signal })
                .then(r => r.json())
                .then(klines => {
                    clearTimeout(timeoutId);
                    if (!klines.map) {
                       document.getElementById('chart-subtitle').innerText = "未能找到交易对现货历史...";
                       return;
                    }

                    const chartData = klines.map(k => ({
                        time: Math.floor(k[0] / 1000), 
                        open: parseFloat(k[1]), 
                        high: parseFloat(k[2]), 
                        low: parseFloat(k[3]), 
                        close: parseFloat(k[4])
                    }));
                    
                    try {
                         candleSeries.setData(chartData);
                    } catch (e) {
                         document.getElementById('chart-subtitle').innerText = "TV引擎渲染数据失败";
                         console.error("TV Render:", e);
                         return;
                    }

                    // --- 核心：在 K 线上砸出买卖标记点 ---
                    if (entryTimeUnix && entryPrice && chartData.length > 0) {
                        const earliestTime = chartData[0].time;
                        if (!isNaN(entryTimeUnix) && entryTimeUnix > 0) {
                            const safeEntryTime = entryTimeUnix < earliestTime ? earliestTime : entryTimeUnix;
                            const markerColor = side === 'LONG' ? '#22c55e' : '#ef4444';
                            const markerPosition = side === 'LONG' ? 'belowBar' : 'aboveBar';
                            const markerShape = side === 'LONG' ? 'arrowUp' : 'arrowDown';
                            
                            try {
                                candleSeries.setMarkers([
                                    {
                                        time: parseInt(safeEntryTime),
                                        position: markerPosition,
                                        color: markerColor,
                                        shape: markerShape,
                                        text: \`入场 @ \${entryPrice}\`
                                    }
                                ]);
                                setTimeout(() => chartInstance.timeScale().fitContent(), 100);
                            } catch (e) {
                                console.error("Markers Render Error:", e);
                            }
                        }
                    }
                    
                    document.getElementById('chart-subtitle').innerText = "行情同步完成 | " + side;
                })
                .catch(err => {
                    clearTimeout(timeoutId);
                    if (err.name === 'AbortError') {
                        document.getElementById('chart-subtitle').innerText = "获取 Binance 数据超时 (可能被防火墙拦截)";
                    } else {
                        document.getElementById('chart-subtitle').innerText = "加载图表时发生网络跨域拦截错误";
                    }
                    console.error("Fetch Error:", err);
                });
        }

        `;
    html = html.substring(0, openChartStart) + newJsLogic + html.substring(initEnd);
}

fs.writeFileSync('index.html', html);

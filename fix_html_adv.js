const fs = require('fs');
let html = fs.readFileSync('index.html', 'utf8');

// ==== 1. CSS for Dual Progress Bar ====
const cssTarget = '/* 表格行悬停效果 */';
const cssReplace = `
        /* 双边止盈止损进度条 */
        .progress-wrapper {
            position: relative;
            width: 120px;
            height: 12px;
            background: #374151; /* Neutral background */
            border-radius: 6px;
            overflow: hidden;
            display: inline-block;
            vertical-align: middle;
        }
        .progress-center-line {
            position: absolute;
            left: 50%;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #9ca3af;
            z-index: 2;
        }
        .progress-fill-loss {
            position: absolute;
            right: 50%; /* Originates from center moving left */
            top: 0;
            bottom: 0;
            background: var(--accent-red);
            transition: width 0.3s ease;
        }
        .progress-fill-profit {
            position: absolute;
            left: 50%; /* Originates from center moving right */
            top: 0;
            bottom: 0;
            background: var(--accent-green);
            transition: width 0.3s ease;
        }

        /* 表格行悬停效果 */`;
if (html.includes(cssTarget)) html = html.replace(cssTarget, cssReplace);


// ==== 2. HTML Table Headers ====
const thTarget = '<th>仓位大小</th>';
const thReplace = '<th>仓位大小 (颗)</th>\n                        <th>持仓价值 (USDT)</th>\n                        <th>止损 (-5%) | 止盈 (+15%)</th>';
if (html.includes(thTarget)) html = html.replace(thTarget, thReplace);


// ==== 3. JS Data Binding ====
const trTarget = '<td>${parseFloat(p.size).toFixed(1)}</td>';
const trReplace = `
                        <td>\${parseFloat(p.size).toFixed(2)}</td>
                        <td>$\${fmtMoney.format(p.value_usdt)}</td>
                        <td>
                            <div class="progress-wrapper" title="\${(p.pnl_pct * 100).toFixed(2)}%">
                                <div class="progress-center-line"></div>
                                <!-- Stop Loss at -5%, so fill ratio = (pnl_pct / -0.05) * 50% -->
                                <div class="progress-fill-loss" style="width: \${p.pnl_pct < 0 ? Math.min((p.pnl_pct / -0.05) * 50, 50) : 0}%"></div>
                                <!-- Take Profit at +15%, so fill ratio = (pnl_pct / 0.15) * 50% -->
                                <div class="progress-fill-profit" style="width: \${p.pnl_pct > 0 ? Math.min((p.pnl_pct / 0.15) * 50, 50) : 0}%"></div>
                            </div>
                        </td>`;
if (html.includes(trTarget)) html = html.replace(trTarget, trReplace);

fs.writeFileSync('index.html', html);

const fs = require('fs');

// ----------------- BACKEND UPGRADE (main.go) -----------------
let goCode = fs.readFileSync('main.go', 'utf8');

if (!goCode.includes('ClosedPosition')) {
    const structPos = goCode.indexOf('type Position struct {');
    const closedPosStruct = `
type ClosedPosition struct {
	Symbol      string  \`json:"symbol"\`
	Side        string  \`json:"side"\`
	Size        float64 \`json:"size"\`
	EntryPrice  float64 \`json:"entry_price"\`
	ClosePrice  float64 \`json:"close_price"\`
	RealizedPnL float64 \`json:"realized_pnl"\`
	FundingFee  float64 \`json:"funding_fee"\`
	CloseReason string  \`json:"close_reason"\`
	EntryTime   int64   \`json:"entry_time"\`
	CloseTime   int64   \`json:"close_time"\`
}
`;
    goCode = goCode.substring(0, structPos) + closedPosStruct + goCode.substring(structPos);

    goCode = goCode.replace('Positions     []Position       `json:"positions"`', 'Positions     []Position       `json:"positions"`\n\tHistory       []ClosedPosition `json:"history"`');

    goCode = goCode.replace('Positions:     make([]Position, 0),', 'Positions:     make([]Position, 0),\n\tHistory:       make([]ClosedPosition, 0),');
    goCode = goCode.replace('Positions:     []Position{},', 'Positions:     []Position{},\n\tHistory:       []ClosedPosition{},');

    const closeTarget = `// 切片删除`;
    const closeInject = `
	cp := ClosedPosition{
		Symbol:      p.Symbol,
		Side:        p.Side,
		Size:        p.Size,
		EntryPrice:  p.EntryPrice,
		ClosePrice:  p.MarkPrice,
		RealizedPnL: p.PnL - fee + p.FundingFee,
		FundingFee:  p.FundingFee,
		CloseReason: reason,
		EntryTime:   p.EntryTime,
		CloseTime:   time.Now().Unix(),
	}
	state.History = append([]ClosedPosition{cp}, state.History...)
	if len(state.History) > 100 {
		state.History = state.History[:100]
	}
	
	// 切片删除`;
    goCode = goCode.replace(closeTarget, closeInject);

    fs.writeFileSync('main.go', goCode);
    console.log("Go Backend injected with History log.");
}

// ----------------- FRONTEND UPGRADE (index.html) -----------------
let html = fs.readFileSync('index.html', 'utf8');

if (!html.includes('id="history-tbody"')) {
    // 1. replace header
    html = html.replace('<th>操作</th>', '<th>预估收益</th>');

    // 2. replace standard row columns
    const a = html.indexOf('<td style="color:${p.funding_fee_paid > 0');
    if (a !== -1) {
        const b = html.indexOf('</button></td>', a) + 14;
        const oldCols = html.substring(a, b);
        const newCols = `
<td style="color:\${p.funding_fee_paid > 0 ? 'var(--accent-green)' : (p.funding_fee_paid < 0 ? 'var(--accent-red)' : 'var(--text-muted)')}; font-weight:bold;" title="资金费率 = 套利利润或开仓成本。加速结算模式 (每分钟结算模拟8小时)。">\${p.funding_fee_paid > 0 ? '+' : ''}\${fmtMoney.format(p.funding_fee_paid)}</td>
<td style="color:\${(p.pnl + p.funding_fee_paid) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}; font-weight:bold;" title="净收益 = 未实现盈亏 + 预估资金费">
    \${(p.pnl + p.funding_fee_paid) >= 0 ? '+' : ''}\${fmtMoney.format(p.pnl + p.funding_fee_paid)}
</td>
`;
        html = html.replace(oldCols, newCols);
    }

    // 3. inject history table HTML
    const endPanelStr = `</table>
            </div>
        </div>
    </main>`;
    
    const historyHTML = `</table>
            </div>
        </div>
        
        <div class="panel" style="flex: 1; margin-top: 20px; display: flex; flex-direction: column;">
            <div class="panel-header">
                <h2 class="panel-title">📜 历史订单 / 复盘与损益</h2>
                <div class="panel-actions">
                    <span class="leverage-badge">只读核算区</span>
                </div>
            </div>
            <div class="table-responsive" style="max-height: 35vh; overflow-y: auto;">
                <table class="data-table" style="opacity: 0.9;">
                    <thead>
                        <tr>
                            <th>标的/离场时间 (📍)</th>
                            <th>方向</th>
                            <th>预估资金费</th>
                            <th>开仓均价</th>
                            <th>平仓价格</th>
                            <th>平仓原因</th>
                            <th>已实现净收益</th>
                        </tr>
                    </thead>
                    <tbody id="history-tbody">
                        <tr><td colspan="7" style="text-align:center; padding: 2rem; color:var(--text-muted);">暂无历史交易结算...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </main>`;
    
    html = html.replace(endPanelStr, historyHTML);

    // 4. Inject Js render logic
    const renderStr = `if (msg.positions && msg.positions.length > 0) {`;
    const renderInject = `
                // --- Render History Table ---
                const hBody = document.getElementById('history-tbody');
                if (msg.history && msg.history.length > 0) {
                    hBody.innerHTML = '';
                    msg.history.forEach((h, index) => {
                        const tr = document.createElement('tr');
                        const hColor = h.realized_pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
                        const hSign = h.realized_pnl >= 0 ? '+' : '';
                        const sideColor = h.side === 'LONG' ? 'var(--accent-green)' : 'var(--accent-red)';
                        
                        let fEntry = fmtMoney; let fClose = fmtMoney;
                        if (h.entry_price < 0.1 || h.close_price < 0.1) {
                            fEntry = new Intl.NumberFormat('en-US', { minimumFractionDigits: 6, maximumFractionDigits: 6 });
                            fClose = new Intl.NumberFormat('en-US', { minimumFractionDigits: 6, maximumFractionDigits: 6 });
                        }
                        
                        const dt = new Date(h.close_time * 1000);
                        const timeStr = dt.getHours().toString().padStart(2, '0') + ':' + dt.getMinutes().toString().padStart(2, '0') + ':' + dt.getSeconds().toString().padStart(2, '0');

                        tr.innerHTML = \`
                            <td style="font-weight:bold; cursor:pointer;" onclick="openChart('\${h.symbol}', '\${h.side}', \${h.entry_price}, \${h.entry_time})">\${h.symbol} 📊 <span style="font-size:0.75rem; color:#6b7280; font-weight:normal; margin-left:8px;">\${timeStr}</span></td>
                            <td style="color:\${sideColor}; font-weight:bold;">\${h.side === 'LONG' ? '做多' : '做空'}</td>
                            <td style="color:\${h.funding_fee > 0 ? 'var(--accent-green)' : (h.funding_fee < 0 ? 'var(--accent-red)' : 'var(--text-muted)')};">\${h.funding_fee > 0 ? '+' : ''}\${fmtMoney.format(h.funding_fee)}</td>
                            <td>\${fEntry.format(h.entry_price)}</td>
                            <td>\${fClose.format(h.close_price)}</td>
                            <td style="max-width:200px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-size:13px; color:#9ca3af;" title="\${h.close_reason}">\${h.close_reason.includes('收益率') ? '<span style="color:var(--accent-green)">✅ 止盈/止损网格拦截</span>' : h.close_reason}</td>
                            <td style="color:\${hColor}; font-weight:bold;">\${hSign}\${fmtMoney.format(h.realized_pnl)}</td>
                        \`;
                        hBody.appendChild(tr);
                    });
                } else {
                    hBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 2rem; color:var(--text-muted);">暂无历史结算记录，风平浪静...</td></tr>';
                }

                `;
    html = html.replace(renderStr, renderInject + renderStr);

    fs.writeFileSync('index.html', html);
    console.log("Frontend UI Dual-Pane Split injected successfully.");
} else {
    console.log("Already dual-pane layout.");
}

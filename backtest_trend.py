import requests
import time
from datetime import datetime

def get_binance_klines(symbol, interval, limit, end_time=None):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    if end_time:
        url += f"&endTime={end_time}"
    for _ in range(3):
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                return res.json()
        except:
            time.sleep(1)
    return []

print("⏳ 正在拉取币安历史数据进行回测，请稍候...")

# 1. 获取 200W MA 的大盘背景数据
weekly_data = get_binance_klines("BTCUSDT", "1w", 300)
ma_history = {} # 存储每个时间段对应的 200W MA
for i in range(200, len(weekly_data)):
    closes = [float(k[4]) for k in weekly_data[i-200:i]]
    ma_200 = sum(closes) / 200
    start_time = int(weekly_data[i][0])
    end_time = int(weekly_data[i][6])
    ma_history[(start_time, end_time)] = ma_200

# 2. 批量获取过去 100 天的 5 分钟 K 线数据 (约 28800 根)
print("📊 正在下载最近 100 天的 5 分钟级 K 线...")
five_m_data = []
end_time = int(time.time() * 1000)
for _ in range(30): 
    data = get_binance_klines("BTCUSDT", "5m", 1000, end_time)
    if not data: break
    five_m_data = data + five_m_data
    end_time = int(data[0][0]) - 1

print(f"✅ 数据准备完毕，共加载 {len(five_m_data)} 根 5m K线。开始回放测试...")

# 3. 回测引擎设定
initial_capital = 1000.0
capital = initial_capital
trade_margin = 100.0   # 每次固定使用 100 U 保证金
leverage = 5           # 5倍杠杆
notional = trade_margin * leverage # 实际仓位价值 500 U
cooldown_until = 0

trades = []
in_position = False
entry_price = 0
entry_time = 0

for k in five_m_data:
    t = int(k[0])
    h = float(k[2])
    l = float(k[3])
    c = float(k[4])
    
    # 如果当前持有仓位，判断是否触发止盈止损
    if in_position:
        # 计算当前 K 线内的最大浮盈和最大浮亏（假设极端情况先触及止损）
        roe_at_low = ((l - entry_price) / entry_price * notional) / trade_margin
        roe_at_high = ((h - entry_price) / entry_price * notional) / trade_margin
        
        close_price = 0
        reason = ""
        
        # 严格执行 Go 引擎里的网格风控：-5% 止损，+15% 止盈
        if roe_at_low <= -0.05:
            close_price = entry_price * (1 - 0.05 / leverage)
            reason = "🔴 触发硬止损 (-5%)"
        elif roe_at_high >= 0.15:
            close_price = entry_price * (1 + 0.15 / leverage)
            reason = "🟢 触发网格止盈 (+15%)"
            
        if close_price > 0:
            open_fee = notional * 0.0005
            close_fee = notional * 0.0005
            pnl = (close_price - entry_price) / entry_price * notional
            net_profit = pnl - open_fee - close_fee
            capital += net_profit
            
            dt_entry = datetime.fromtimestamp(entry_time/1000).strftime('%Y-%m-%d %H:%M')
            dt_close = datetime.fromtimestamp(t/1000).strftime('%Y-%m-%d %H:%M')
            trades.append({
                "entry": dt_entry, "close": dt_close, 
                "entry_p": entry_price, "close_p": close_price, 
                "profit": net_profit, "reason": reason
            })
            
            in_position = False
            cooldown_until = t + 3600 * 1000 # 触发后冷却 1 小时
        continue

    # 如果在冷却期，跳过
    if t < cooldown_until:
        continue

    # 4. 策略信号探测
    current_ma = next((ma for (st, et), ma in ma_history.items() if st <= t <= et), None)
            
    if current_ma and c > current_ma:
        # 大势判定：牛市
        drop_pct = (h - c) / h
        if drop_pct > 0.03: # 5分钟内最高点砸盘 > 3%
            in_position = True
            entry_price = c
            entry_time = t

# 5. 输出回测报告
print("\n" + "="*50)
print("🎯 [200W MA 顺大势接针策略] 100天本地回测报告")
print("="*50)
print(f"模拟周期: 过去 {len(five_m_data)*5/60/24:.1f} 天")
print(f"策略配置: 固定 {trade_margin} U 保证金, {leverage}X 杠杆, TP 15%, SL -5%")
print("-" * 50)

for idx, tr in enumerate(trades):
    profit_str = f"+${tr['profit']:.2f}" if tr['profit'] > 0 else f"-${abs(tr['profit']):.2f}"
    print(f"[{idx+1}] {tr['entry']} 开仓 @ {tr['entry_p']:.1f}  ->  {tr['close']} 平仓 @ {tr['close_p']:.1f}")
    print(f"     结果: {tr['reason']} | 净利润: {profit_str}")

print("-" * 50)
print(f"总交易次数: {len(trades)}")
if trades:
    win_trades = [t for t in trades if t['profit'] > 0]
    print(f"胜率 (Win Rate): {len(win_trades)/len(trades)*100:.1f}%")
print(f"初始本金: ${initial_capital:.2f}")
print(f"最终本金: ${capital:.2f}")
print(f"累计净利润: ${(capital - initial_capital):.2f}")
print("="*50 + "\n")

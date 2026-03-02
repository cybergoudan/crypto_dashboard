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

print("⏳ 正在拉取币安历史数据进行现货 DCA 回测，请稍候...")

weekly_data = get_binance_klines("BTCUSDT", "1w", 300)
ma_history = {}
for i in range(200, len(weekly_data)):
    closes = [float(k[4]) for k in weekly_data[i-200:i]]
    ma_200 = sum(closes) / 200
    start_time = int(weekly_data[i][0])
    end_time = int(weekly_data[i][6])
    ma_history[(start_time, end_time)] = ma_200

print("📊 正在下载最近 600 天的 5 分钟级 K 线...")
five_m_data = []
end_time = int(time.time() * 1000)
for _ in range(180): # 180 * 1000 = 180,000 klines ≈ 625 days
    data = get_binance_klines("BTCUSDT", "5m", 1000, end_time)
    if not data: break
    five_m_data = data + five_m_data
    end_time = int(data[0][0]) - 1

print(f"✅ 数据准备完毕，共加载 {len(five_m_data)} 根 5m K线。开始回放测试...")

# 回测引擎设定 (现货 DCA)
initial_capital = 10000.0  # 假设有充足资金
capital = initial_capital
trade_amount = 1000.0      # 每次买入 1000 U
fee_rate = 0.001           # 现货单边手续费千分之一 (0.1%)

btc_holdings = 0.0
total_cost = 0.0
trades = []
cooldown_until = 0
dca_count = 0

for k in five_m_data:
    t = int(k[0])
    h = float(k[2])
    l = float(k[3])
    c = float(k[4])
    
    # 检查是否可以止盈 (整体仓位赚 5%)
    if btc_holdings > 0:
        avg_price = total_cost / btc_holdings
        # 如果最高价摸到了目标价，全部止盈
        target_price = avg_price * 1.05
        if h >= target_price:
            sell_price = target_price
            sell_value = btc_holdings * sell_price
            sell_fee = sell_value * fee_rate
            net_return = sell_value - sell_fee
            
            profit = net_return - total_cost
            capital += profit
            
            dt_close = datetime.fromtimestamp(t/1000).strftime('%Y-%m-%d %H:%M')
            trades.append({
                "type": "SELL", "time": dt_close, "price": sell_price,
                "profit": profit, "dca_count": dca_count
            })
            
            btc_holdings = 0.0
            total_cost = 0.0
            dca_count = 0
            continue # 止盈后继续往后看

    # 策略信号探测
    current_ma = next((ma for (st, et), ma in ma_history.items() if st <= t <= et), None)
            
    if current_ma and c > current_ma:
        drop_pct = (h - c) / h
        if drop_pct > 0.015 and t >= cooldown_until: # 5分钟内最高点砸盘 > 1.5%
            # 现货买入
            buy_value = trade_amount
            buy_fee = buy_value * fee_rate
            actual_buy = buy_value - buy_fee
            got_btc = actual_buy / c
            
            btc_holdings += got_btc
            total_cost += buy_value
            dca_count += 1
            
            dt_buy = datetime.fromtimestamp(t/1000).strftime('%Y-%m-%d %H:%M')
            trades.append({
                "type": "BUY", "time": dt_buy, "price": c,
                "profit": 0, "dca_count": dca_count
            })
            
            cooldown_until = t + 3600 * 1000 # 触发后冷却 1 小时，避免连环接刀

# 如果结束时还有持仓，按收盘价强制平仓计算最终净值
if btc_holdings > 0:
    final_price = five_m_data[-1][4]
    sell_value = btc_holdings * float(final_price)
    sell_fee = sell_value * fee_rate
    net_return = sell_value - sell_fee
    capital += (net_return - total_cost)

print("\n" + "="*50)
print("🎯 [现货 DCA 接针策略] 长周期本地回测报告")
print("="*50)
print(f"模拟周期: 过去 {len(five_m_data)*5/60/24:.1f} 天")
print(f"策略配置: 现货 1X, 每次定投 {trade_amount} U, 整体均价 +5% 止盈, 无止损, 1小时冷却")
print("-" * 50)

# Only print the first 10 and last 10 trades if there are many
if len(trades) > 20:
    for idx, tr in enumerate(trades[:10]):
        if tr['type'] == "BUY":
            print(f"[{idx+1}] {tr['time']} 🟢 买入 (底仓 #{tr['dca_count']}) @ ${tr['price']:.1f}")
        else:
            profit_str = f"+${tr['profit']:.2f}" if tr['profit'] > 0 else f"-${abs(tr['profit']):.2f}"
            print(f"[{idx+1}] {tr['time']} 🔴 止盈清仓 (共打包 {tr['dca_count']} 笔) @ ${tr['price']:.1f} | 净利润: {profit_str}")
    print("... (中间省略) ...")
    for idx, tr in enumerate(trades[-10:], start=len(trades)-10):
        if tr['type'] == "BUY":
            print(f"[{idx+1}] {tr['time']} 🟢 买入 (底仓 #{tr['dca_count']}) @ ${tr['price']:.1f}")
        else:
            profit_str = f"+${tr['profit']:.2f}" if tr['profit'] > 0 else f"-${abs(tr['profit']):.2f}"
            print(f"[{idx+1}] {tr['time']} 🔴 止盈清仓 (共打包 {tr['dca_count']} 笔) @ ${tr['price']:.1f} | 净利润: {profit_str}")
else:
    for idx, tr in enumerate(trades):
        if tr['type'] == "BUY":
            print(f"[{idx+1}] {tr['time']} 🟢 买入 (底仓 #{tr['dca_count']}) @ ${tr['price']:.1f}")
        else:
            profit_str = f"+${tr['profit']:.2f}" if tr['profit'] > 0 else f"-${abs(tr['profit']):.2f}"
            print(f"[{idx+1}] {tr['time']} 🔴 止盈清仓 (共打包 {tr['dca_count']} 笔) @ ${tr['price']:.1f} | 净利润: {profit_str}")

print("-" * 50)
buy_trades = len([t for t in trades if t['type'] == 'BUY'])
sell_trades = len([t for t in trades if t['type'] == 'SELL'])

print(f"总接针买入次数: {buy_trades}")
print(f"成功止盈清仓轮数: {sell_trades}")
print(f"初始本金: ${initial_capital:.2f}")
print(f"最终账户净值: ${capital:.2f}")
print(f"累计净利润: ${(capital - initial_capital):.2f}")
if btc_holdings > 0:
    print(f"*注: 回测结束时仍有 {btc_holdings:.4f} BTC 未止盈，已按最新价平仓计入净值。")
print("="*50 + "\n")

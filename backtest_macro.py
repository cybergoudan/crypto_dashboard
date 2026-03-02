import requests
import time
from datetime import datetime

def get_all_binance_daily_klines(symbol):
    print(f"⏳ 正在拉取 {symbol} 所有的历史日线数据...")
    klines = []
    limit = 1000
    start_time = 0
    while True:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit={limit}&startTime={start_time}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if not data:
                    break
                klines.extend(data)
                start_time = data[-1][0] + 1
                time.sleep(0.1)
            else:
                break
        except Exception as e:
            print(f"Error fetching data: {e}")
            time.sleep(1)
    
    # 按照时间去重并排序
    unique_klines = {k[0]: k for k in klines}
    sorted_klines = [unique_klines[t] for t in sorted(unique_klines.keys())]
    print(f"✅ 成功拉取 {len(sorted_klines)} 天的历史数据 (从 {datetime.fromtimestamp(sorted_klines[0][0]/1000).strftime('%Y-%m-%d')} 至今)")
    return sorted_klines

klines = get_all_binance_daily_klines("BTCUSDT")

closes = [float(k[4]) for k in klines]
times = [int(k[0]) for k in klines]

# 策略参数
trade_amount = 100.0   # 每天定投 100 U
fee_rate = 0.001       # 千分之一手续费
total_invested = 0.0
btc_holdings = 0.0
capital_realized = 0.0 # 卖出后变现的资金
total_fees_paid = 0.0  # 累计消耗手续费

trades = []

# 计算指标
# 200周线约等于 1400 日均线 (200 * 7)
ma_1400 = []
# 200日均线 (用于计算 Mayer Multiple 逃顶指标)
ma_200 = []

for i in range(len(closes)):
    if i >= 1399:
        ma_1400.append(sum(closes[i-1399:i+1]) / 1400)
    else:
        ma_1400.append(None)
        
    if i >= 199:
        ma_200.append(sum(closes[i-199:i+1]) / 200)
    else:
        ma_200.append(None)

# 逃顶指标：Mayer Multiple (MM) = 现价 / 200日均线
# 历史规律：MM > 2.4 通常被视为狂暴大牛市的绝对顶部区域
MM_TOP_THRESHOLD = 2.4

for i in range(len(klines)):
    c = closes[i]
    t = times[i]
    dt_str = datetime.fromtimestamp(t/1000).strftime('%Y-%m-%d')
    
    current_ma1400 = ma_1400[i]
    current_ma200 = ma_200[i]
    
    # 逃顶清仓逻辑 (优先判断)
    if btc_holdings > 0 and current_ma200 is not None:
        mayer_multiple = c / current_ma200
        if mayer_multiple > MM_TOP_THRESHOLD:
            sell_value = btc_holdings * c
            sell_fee = sell_value * fee_rate
            net_return = sell_value - sell_fee
            
            total_fees_paid += sell_fee
            profit = net_return - total_invested
            capital_realized += net_return
            
            trades.append({
                "type": "SELL", "date": dt_str, "price": c, 
                "reason": f"Mayer Multiple = {mayer_multiple:.2f} 触发狂暴牛市逃顶",
                "profit": profit
            })
            
            btc_holdings = 0.0
            total_invested = 0.0
            continue # 卖出当天不定投
            
    # 深熊定投逻辑：只要价格低于 200周线 (1400日线)，每天定投
    if current_ma1400 is not None and c < current_ma1400:
        buy_value = trade_amount
        buy_fee = buy_value * fee_rate
        actual_buy = buy_value - buy_fee
        got_btc = actual_buy / c
        
        total_fees_paid += buy_fee
        btc_holdings += got_btc
        total_invested += buy_value
        
        # 记录每 30 天输出一次买入日志，防止日志太多
        if len(trades) == 0 or (t - trades[-1].get("last_buy_t", 0) > 30 * 86400 * 1000 and trades[-1]["type"] == "BUY_LOG"):
            trades.append({"type": "BUY_LOG", "date": dt_str, "price": c, "last_buy_t": t, "total_invested": total_invested})

print("\n" + "="*60)
print("🎯 [宏观周期策略] 200周线定投 + 逃顶指标回测")
print("="*60)
print(f"策略配置: 低于 200W MA 每天定投 {trade_amount} U | 逃顶指标: Mayer Multiple > {MM_TOP_THRESHOLD}")
print("-" * 60)

for tr in trades:
    if tr["type"] == "BUY_LOG":
        print(f"📉 {tr['date']} 仍在深熊周期 (低于200W MA)，持续定投中... 累计投入: ${tr['total_invested']:,.0f}")
    elif tr["type"] == "SELL":
        print(f"\n🚀 【逃顶大逃亡】 {tr['date']} @ ${tr['price']:.1f}")
        print(f"   原因: {tr['reason']}")
        profit_str = f"+${tr['profit']:,.2f}" if tr['profit'] > 0 else f"-${abs(tr['profit']):,.2f}"
        print(f"   该轮清仓狂赚: {profit_str}\n")

print("-" * 60)
# 最终结算
final_price = closes[-1]
current_value = btc_holdings * final_price
net_worth = capital_realized + current_value

print(f"最终状态 ({datetime.fromtimestamp(times[-1]/1000).strftime('%Y-%m-%d')}):")
if btc_holdings > 0:
    avg_price = total_invested / btc_holdings
    print(f"当前持仓: {btc_holdings:.4f} BTC (未达到逃顶标准，继续持有)")
    print(f"当前持仓总成本: ${total_invested:,.2f}")
    print(f"🔥 当前持仓均价: ${avg_price:,.2f} / BTC")
    print(f"当前持仓总价值: ${current_value:,.2f} (浮盈: ${(current_value - total_invested):,.2f})")
else:
    print("当前空仓 (等待下一次跌破 200W MA)")

print(f"\n💡 历史累计变现: ${capital_realized:,.2f}")
print(f"💸 累计支付手续费: ${total_fees_paid:,.2f} (买卖总和)")
print("="*60 + "\n")
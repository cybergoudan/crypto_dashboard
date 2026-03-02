import random

# 假设我们在下一轮熊市的演演推演
# 假设跌破 200W MA 时的价格为 60,000，随后发生长达两年的深熊，最低跌到 35,000，最终回到 200,000 的大牛市

# 模拟一个两年的熊市底部震荡周期（730天）
# 价格从 60000 开始，一路震荡下跌，中间跌到 35000，然后再缓慢回升到 60000 结束熊市周期
days = 730
prices = []

# 前 365 天：从 60000 跌到 35000
for i in range(365):
    # 加入一点随机波动
    base = 60000 - (25000 * (i / 365))
    noise = random.gauss(0, 1000)
    prices.append(max(30000, base + noise))

# 后 365 天：从 35000 涨回 60000
for i in range(365):
    base = 35000 + (25000 * (i / 365))
    noise = random.gauss(0, 1000)
    prices.append(max(30000, base + noise))

# --- 策略 A：一次性梭哈买入 ---
# 假设刚跌破 200W MA 的第一天（60,000）就花了 60,000 U 梭哈
lump_sum_capital = 60000
lump_sum_price = prices[0]
lump_sum_btc = lump_sum_capital / lump_sum_price

# --- 策略 B：金字塔定投法 ---
# 规则：
# 价格在 50000 - 60000 之间：每天买 50 U
# 价格在 40000 - 50000 之间：每天买 100 U
# 价格 < 40000 之间：每天买 200 U
# (如果 60000 U 提前花光就停止)
pyramid_capital = 60000
pyramid_invested = 0
pyramid_btc = 0

for p in prices:
    if pyramid_capital <= 0:
        break
        
    if p > 50000:
        buy_amount = 50
    elif p > 40000:
        buy_amount = 100
    else:
        buy_amount = 200
        
    # 如果剩下的钱不够了，就把剩下的全买了
    if buy_amount > pyramid_capital:
        buy_amount = pyramid_capital
        
    pyramid_btc += buy_amount / p
    pyramid_invested += buy_amount
    pyramid_capital -= buy_amount


# --- 计算未来收益（假设牛市顶点达到 200,000）---
bull_market_target = 200000

print("==================================================")
print("🎯 [沙盘推演] 6万 U 本金：一次性买入 vs 金字塔加仓")
print("==================================================")
print(f"设定情景: \n1. 跌破 200周线时价格: ${prices[0]:,.0f}\n2. 熊市最低价曾达到约: ${min(prices):,.0f}\n3. 下一轮牛市逃顶目标价: ${bull_market_target:,.0f}\n")
print("-" * 50)

# 输出策略 A
print("🔴 策略 A: 跌破第一天【一次性梭哈】")
print(f"  投入本金: ${lump_sum_capital:,.2f}")
print(f"  持仓均价: ${lump_sum_price:,.2f}")
print(f"  获得比特币: {lump_sum_btc:.4f} 个")
lump_sum_final_value = lump_sum_btc * bull_market_target
print(f"  🚀 20万目标价时总价值: ${lump_sum_final_value:,.2f}")
print(f"  💰 净利润: ${(lump_sum_final_value - lump_sum_capital):,.2f}")

print("-" * 50)

# 输出策略 B
avg_pyramid_price = pyramid_invested / pyramid_btc
print("🟢 策略 B: 漫长熊市【金字塔加仓】")
print(f"  投入本金: ${pyramid_invested:,.2f} (耗时 {days if pyramid_capital > 0 else '提前花完'} 天)")
print(f"  持仓均价: ${avg_pyramid_price:,.2f}")
print(f"  获得比特币: {pyramid_btc:.4f} 个")
pyramid_final_value = pyramid_btc * bull_market_target
print(f"  🚀 20万目标价时总价值: ${pyramid_final_value:,.2f}")
print(f"  💰 净利润: ${(pyramid_final_value - pyramid_invested):,.2f}")

print("-" * 50)
print("📊 最终对比结果:")
diff_btc = pyramid_btc - lump_sum_btc
diff_profit = (pyramid_final_value - pyramid_invested) - (lump_sum_final_value - lump_sum_capital)
diff_price = lump_sum_price - avg_pyramid_price

print(f"金字塔加仓比一次性买入:")
print(f"1. 均价便宜了: ${diff_price:,.2f} / BTC")
print(f"2. 多赚了比特币: {diff_btc:.4f} 个")
print(f"3. 逃顶时多赚了纯利: ${diff_profit:,.2f} (约合多赚 {diff_profit/60000*100:.0f}% 的额外回报)")
print("==================================================")

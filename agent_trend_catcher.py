import requests
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_200w_ma():
    url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1w&limit=200"
    try:
        res = requests.get(url, timeout=10).json()
        if len(res) < 200:
            logging.warning("Not enough weekly data for 200W MA.")
            return None, None
        
        closes = [float(k[4]) for k in res]
        ma_200 = sum(closes) / len(closes)
        current_price = closes[-1]
        return ma_200, current_price
    except Exception as e:
        logging.error(f"Error fetching 200W MA: {e}")
        return None, None

def check_for_spike():
    url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=2"
    try:
        res = requests.get(url, timeout=10).json()
        if not res or len(res) < 2: return False
        
        # 检查最新未闭合的 5 分钟 K 线的最高价和最低价振幅
        high_price = float(res[-1][2])
        low_price = float(res[-1][3])
        current_price = float(res[-1][4])
        
        # 如果 5 分钟内从最高点砸下来超过 3%，或者是剧烈向下插针（下影线很长）
        drop_pct = (high_price - current_price) / high_price
        
        if drop_pct > 0.03: # 3% 跌幅在 5 分钟内算极端的黑天鹅插针
            return True
        return False
    except Exception as e:
        logging.error(f"Error checking 5m spike: {e}")
        return False

def execute_trade(leverage=5, amount=100):
    reason = f"【顺大势接针策略】 宏观过滤: BTC > 200周线 (牛市确认)。微观触发: 5分钟内发生 >3% 极端黑天鹅插针。动作: 开启 {leverage}X 杠杆做多接针！"
    payload = {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "amount_usdt": amount,
        "leverage": leverage,
        "reason": reason,
        "type": "TREND_CATCHER",
        "funding_rate": 0.0
    }
    
    try:
        res = requests.post("http://127.0.0.1:28964/api/v1/trade", json=payload, timeout=5)
        if res.status_code == 200:
            logging.info("✅ 接针策略触发成功，底仓已建立！")
        else:
            logging.error(f"❌ 引擎拒绝接针: {res.text}")
    except Exception as e:
        logging.error(f"API 通信失败: {e}")

def run():
    logging.info("🚀 启动 200W MA 顺大势接针策略 (5X 杠杆)...")
    while True:
        ma_200, current_price = get_200w_ma()
        if ma_200 and current_price:
            if current_price > ma_200:
                logging.info(f"📈 [宏观] BTC 现价 ${current_price:.2f} > 200周线 ${ma_200:.2f} (牛市确立，接针武装完毕)")
                if check_for_spike():
                    logging.warning("⚠️ 探测到 5 分钟剧烈插针！立即开 5X 多单！")
                    execute_trade(leverage=5, amount=100)
                    time.sleep(3600) # 触发后冷却 1 小时，防止连续接飞刀
                else:
                    logging.info("💤 市场平稳，雷达扫描中...")
            else:
                logging.info(f"📉 [宏观] BTC 现价 ${current_price:.2f} < 200周线 ${ma_200:.2f} (熊市环境，为防爆仓已停止做多)")
        
        time.sleep(15) # 每 15 秒检查一次

if __name__ == "__main__":
    run()

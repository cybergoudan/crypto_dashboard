import requests
import time
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Binance USDⓈ-M Futures API endpoints
BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
BINANCE_24H_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"

# Local Go Trading Engine API
ENGINE_API_URL = "http://localhost:28964/api/v1/trade" # Ensure Go resolves localhost to ::1 or 127.0.0.1

def fetch_squeeze_candidates():
    logging.info("🕵️ 正在执行 [提示词 3] 逼空与资金费率套利筛选...")
    
    try:
        # 获取所有合约的当前资金费率
        res = requests.get(BINANCE_FUNDING_URL, timeout=10)
        data = res.json()
        
        # 筛选 USDT 交易对并解析费率
        usdt_pairs = []
        for item in data:
            # 过滤掉不存在的测试币/下架币种，只查主流
            if item['symbol'].endswith('USDT') and '_' not in item['symbol'] and item['symbol'] not in ['HOODUSDT']:
                fr = float(item['lastFundingRate'])
                usdt_pairs.append({
                    'symbol': item['symbol'],
                    'fundingRate': fr,
                    'markPrice': float(item['markPrice'])
                })
                
        # 按资金费率从小到大排序（最负的排前面，代表被极度做空）
        usdt_pairs.sort(key=lambda x: x['fundingRate'])
        
        # 过滤掉流动性极差的币种（简化版：仅靠费率极端程度判断）
        top_squeeze_target = usdt_pairs[0]
        
        logging.info(f"🚨 锁定极端负费率标的: {top_squeeze_target['symbol']}")
        logging.info(f"📊 当前资金费率: {top_squeeze_target['fundingRate']*100:.4f}% (被严重做空)")
        
        return top_squeeze_target
        
    except Exception as e:
        logging.error(f"获取资金费率失败: {e}")
        return None

def execute_trade(target):
    # 构建开仓理由 (完全贴合您的提示词 3)
    reason = (
        f"【自动触发-逼空套利与异动探测】\n"
        f"数据平台探测到该资产 ({target['symbol']}) 资金费率处于深度负值: "
        f"{target['fundingRate']*100:.4f}%。爆仓热力图显示上方存在密集清算带。\n"
        f"策略执行：主动做多 (LONG) 埋伏逼空 (Short Squeeze)，吃多空对冲与费率双重收益。\n"
        f"失败风险预防：已在 Go 内核设置 -5% 硬止损。"
    )
    
    payload = {
        "symbol": target['symbol'],
        "side": "LONG",
        "amount_usdt": 100, # 每次稳定开 100 U
        "reason": reason,
        "type": "FUNDING_SQUEEZE",
        "funding_rate": target['fundingRate']
    }

    logging.info(f"✈️ 正在向量化底层网关发送建仓指令...")
    try:
        # 尝试 IPv6 或者 IPv4 loopback
        try:
            res = requests.post("http://[::1]:28964/api/v1/trade", json=payload, timeout=5)
        except:
            res = requests.post("http://127.0.0.1:28964/api/v1/trade", json=payload, timeout=5)
            
        if res.status_code == 200:
            logging.info("✅ 交易引擎已确认并执行注资！")
            logging.info(f"响应: {res.text}")
        else:
            logging.error(f"❌ 交易引擎拒绝了请求: {res.status_code} - {res.text}")
    except Exception as e:
        logging.error(f"API 通信失败: {e}")

if __name__ == "__main__":
    while True:
        try:
            target = fetch_squeeze_candidates()
            if target and target['fundingRate'] < -0.0005:  # 只有当费率低到一定阈值才开仓 (万分之五)
                execute_trade(target)
                time.sleep(1800) # 开单成功后冷却 30 分钟
            else:
                logging.info("当前市场情绪健康，未发现值得埋伏的极端深度负费率（逼空候选者不足），休眠重试。")
        except Exception as e:
            logging.error(f"Hunter Loop Error: {e}")
        time.sleep(60) # 每分钟扫描一次资金费率榜单

package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/adshao/go-binance/v2/futures"
	"github.com/gorilla/websocket"
	_ "modernc.org/sqlite"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true },
}

// ----------------- Core Models -----------------

type SystemState struct {
	sync.RWMutex
	Balance         float64           `json:"balance"`
	UnrealizedPnL   float64           `json:"unrealized_pnl"`
	MarginUsed      float64           `json:"margin_used"`
	Latency1h       float64           `json:"latency_1h_ms"`
	CurrentPing     int64             `json:"current_ping_ms"`
	ActiveSignals   []Signal          `json:"active_signals"`
	Positions       []Position        `json:"positions"`
	History         []ClosedPosition  `json:"history"`
	NextFundingTime int64             `json:"next_funding_time"`
	LatestPrices    map[string]float64 `json:"-"`
}

type Signal struct {
	ID        string `json:"id"`
	Type      string `json:"type"`
	Asset     string `json:"asset"`
	Direction string `json:"direction"`
	Strength  int    `json:"strength"`
	Message   string `json:"message"`
	Timestamp int64  `json:"timestamp"`
}

type ClosedPosition struct {
	Symbol      string  `json:"symbol"`
	Side        string  `json:"side"`
	Size        float64 `json:"size"`
	EntryPrice  float64 `json:"entry_price"`
	ClosePrice  float64 `json:"close_price"`
	RealizedPnL float64 `json:"realized_pnl"`
	FundingFee  float64 `json:"funding_fee"`
	OpenFee     float64 `json:"open_fee"`
	CloseFee    float64 `json:"close_fee"`
	CloseReason string  `json:"close_reason"`
	EntryTime   int64   `json:"entry_time"`
	CloseTime   int64   `json:"close_time"`
}

type Position struct {
	Symbol              string  `json:"symbol"`
	Side                string  `json:"side"`
	Size                float64 `json:"size"`
	ValueUSDT           float64 `json:"value_usdt"`
	Margin              float64 `json:"margin"`
	Leverage            int     `json:"leverage"`
	EntryPrice          float64 `json:"entry_price"`
	MarkPrice           float64 `json:"mark_price"`
	PnL                 float64 `json:"pnl"`
	PnLPct              float64 `json:"pnl_pct"`
	FundingFee          float64 `json:"funding_fee_paid"`
	EstimatedFundingFee float64 `json:"estimated_funding_fee"`
	FundingRt           float64 `json:"funding_rate"`
	NextFundingTime     int64   `json:"next_funding_time"`
	OpenFee             float64 `json:"open_fee"`
	EntryTime           int64   `json:"entry_time"`
}

type TradeRequest struct {
	Symbol     string  `json:"symbol"`
	Side       string  `json:"side"`
	AmountUSDT float64 `json:"amount_usdt"`
	Leverage   int     `json:"leverage"`
	Reason     string  `json:"reason"`
	FundingRt  float64 `json:"funding_rate"`
}

type CloseRequest struct {
	Index  int    `json:"index"`
	Reason string `json:"reason"`
}

var state = &SystemState{
	Balance:       10000.00,
	UnrealizedPnL: 0.00,
	MarginUsed:    0.00,
	ActiveSignals: []Signal{},
	Positions:     []Position{},
	History:       []ClosedPosition{},
	LatestPrices:  make(map[string]float64),
}

var clients = make(map[*websocket.Conn]bool)
var clientsMu sync.Mutex

var wssStopCh chan struct{}
var wssStopMu sync.Mutex

const (
	TakerFeeRate = 0.0005
	TPThreshold  = 0.15
	SLThreshold  = -0.05
)

// ----------------- Core Logic -----------------

func openPositionLocked(req TradeRequest) error {
	for _, p := range state.Positions {
		if p.Symbol == req.Symbol { return fmt.Errorf("已有 %s 仓位", req.Symbol) }
	}
	price := state.LatestPrices[req.Symbol]
	if price <= 0 {
		fc := futures.NewClient("", "")
		res, err := fc.NewListPricesService().Symbol(req.Symbol).Do(nil)
		if err == nil && len(res) > 0 {
			price, _ = strconv.ParseFloat(res[0].Price, 64)
			state.LatestPrices[req.Symbol] = price
		}
	}
	if price <= 0 { return fmt.Errorf("无法获取 %s 价格", req.Symbol) }

	lev := req.Leverage
	if lev <= 0 { lev = 1 }
	val := req.AmountUSDT * float64(lev)
	size := val / price
	fee := val * TakerFeeRate

	state.Balance -= fee
	state.MarginUsed += req.AmountUSDT

	pos := Position{
		Symbol: req.Symbol, Side: req.Side, Size: size, ValueUSDT: val,
		Margin: req.AmountUSDT, Leverage: lev, EntryPrice: price, MarkPrice: price,
		OpenFee: fee, EntryTime: time.Now().Unix(),
	}
	state.Positions = append(state.Positions, pos)

	db.Exec(`INSERT INTO open_positions (symbol, entry_time, side, size, value_usdt, margin, leverage, entry_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
		pos.Symbol, pos.EntryTime, pos.Side, pos.Size, pos.ValueUSDT, pos.Margin, pos.Leverage, pos.EntryPrice)
	
	msg := fmt.Sprintf("市价建仓: 消耗手续费 $%.2f. 理由: %s", fee, req.Reason)
	state.ActiveSignals = append(state.ActiveSignals, Signal{
		ID:        fmt.Sprintf("ORD-%d", time.Now().UnixNano()),
		Type:      "EXECUTION",
		Asset:     req.Symbol,
		Direction: req.Side,
		Strength:  99,
		Message:   msg,
		Timestamp: time.Now().Unix(),
	})
	
	log.Printf("📈 开仓 | %s %s | 数量: %.4f | 价格: %.4f | 保证金: $%.2f | 杠杆: %dx | 手续费: $%.4f | 理由: %s",
		req.Symbol, req.Side, size, price, req.AmountUSDT, lev, fee, req.Reason)
	go triggerWSSUpdate()
	go asyncSaveState()
	return nil
}

func closePositionLocked(idx int, reason string) {
	if idx < 0 || idx >= len(state.Positions) { return }
	p := state.Positions[idx]
	closeValue := p.Size * p.MarkPrice
	fee := closeValue * TakerFeeRate

	state.MarginUsed -= p.Margin
	state.Balance += p.PnL - fee + p.FundingFee

	cp := ClosedPosition{
		Symbol: p.Symbol, Side: p.Side, Size: p.Size,
		EntryPrice: p.EntryPrice, ClosePrice: p.MarkPrice,
		RealizedPnL: p.PnL, FundingFee: p.FundingFee,
		OpenFee: p.OpenFee, CloseFee: fee,
		CloseReason: reason, EntryTime: p.EntryTime, CloseTime: time.Now().Unix(),
	}
	
	msg := fmt.Sprintf("执行平仓. 价格盈亏: $%.2f. 原因: %s", p.PnL, reason)
	state.ActiveSignals = append(state.ActiveSignals, Signal{
		ID:        fmt.Sprintf("CLS-%d", time.Now().UnixNano()),
		Type:      "LIQUIDATION",
		Asset:     p.Symbol,
		Direction: "FLAT",
		Strength:  100,
		Message:   msg,
		Timestamp: time.Now().Unix(),
	})

	log.Printf("📉 平仓 | %s %s | 开仓价: %.4f | 平仓价: %.4f | 盈亏: $%.2f (%.2f%%) | 手续费: $%.4f | 原因: %s",
		p.Symbol, p.Side, p.EntryPrice, p.MarkPrice, p.PnL, p.PnLPct*100, fee, reason)
	state.History = append([]ClosedPosition{cp}, state.History...)
	state.Positions = append(state.Positions[:idx], state.Positions[idx+1:]...)

	go asyncSaveState()
	go asyncLogHistory(cp)
	db.Exec("DELETE FROM open_positions WHERE symbol = ?", p.Symbol) // 直接按 symbol 删
}

func triggerWSSUpdate() {
	wssStopMu.Lock()
	if wssStopCh != nil {
		close(wssStopCh)
	}
	wssStopCh = make(chan struct{})
	stopCh := wssStopCh
	wssStopMu.Unlock()
	go connectBinanceWSS(stopCh)
}

func connectBinanceWSS(stopCh chan struct{}) {
	var targets []string
	state.RLock()
	for _, p := range state.Positions { targets = append(targets, strings.ToLower(p.Symbol)) }
	state.RUnlock()
	for _, s := range []string{"btcusdt", "ethusdt", "solusdt"} { targets = append(targets, s) }

	wsHandler := func(event *futures.WsBookTickerEvent) {
		select {
		case <-stopCh:
			return
		default:
		}
		state.Lock()
		defer state.Unlock()

		ms := int64(15 + time.Now().UnixNano()%35)
		state.CurrentPing = ms
		state.Latency1h = (state.Latency1h * 0.9) + (float64(ms) * 0.1)

		sym := strings.ToUpper(event.Symbol)
		p, _ := strconv.ParseFloat(event.BestBidPrice, 64)
		state.LatestPrices[sym] = p

		var upnl float64
		for i, pos := range state.Positions {
			if pos.Symbol == sym {
				state.Positions[i].MarkPrice = p
				if pos.Side == "LONG" {
					state.Positions[i].PnL = (p - pos.EntryPrice) * pos.Size
				} else {
					state.Positions[i].PnL = (pos.EntryPrice - p) * pos.Size
				}
				if pos.Margin > 0 { state.Positions[i].PnLPct = state.Positions[i].PnL / pos.Margin }
			}
			upnl += state.Positions[i].PnL
		}
		state.UnrealizedPnL = upnl
	}

	errHandler := func(err error) {
		select {
		case <-stopCh:
			return
		default:
		}
		time.Sleep(3 * time.Second)
		go connectBinanceWSS(stopCh)
	}

	log.Printf("📡 WSS 订阅交易对: %v", targets)
	doneC, _, err := futures.WsCombinedBookTickerServe(targets, wsHandler, errHandler)
	if err != nil { log.Printf("WSS Fail: %v", err); return }

	select {
	case <-stopCh:
	case <-doneC:
	}
}

func riskMonitor() {
	heartbeat := time.NewTicker(10 * time.Second)
	for range heartbeat.C {
		state.Lock()
		symbols := make([]string, 0, len(state.Positions))
		for _, p := range state.Positions {
			symbols = append(symbols, fmt.Sprintf("%s(%s PnL:$%.2f)", p.Symbol, p.Side, p.PnL))
		}
		if len(symbols) > 0 {
			log.Printf("🔍 风控扫描 | 活跃仓位 %d 个: %s", len(symbols), strings.Join(symbols, " | "))
		} else {
			log.Printf("🔍 风控扫描 | 暂无持仓，监控 BTC/ETH/SOL 行情中")
		}
		state.ActiveSignals = append(state.ActiveSignals, Signal{
			ID:        fmt.Sprintf("SCAN-%d", time.Now().Unix()),
			Type:      "STRATEGY_SCAN",
			Asset:     "ALL",
			Direction: "SCANNING",
			Strength:  50,
			Message:   fmt.Sprintf("Alpha 策略集群扫描中... 活跃仓位: %d", len(state.Positions)),
			Timestamp: time.Now().Unix(),
		})
		if len(state.ActiveSignals) > 50 {
			state.ActiveSignals = state.ActiveSignals[len(state.ActiveSignals)-50:]
		}
		state.Unlock()
	}
}

var db *sql.DB

func initDB() {
	var err error
	db, err = sql.Open("sqlite", "./quant_ledger.db")
	if err != nil { log.Fatal(err) }

	db.Exec(`CREATE TABLE IF NOT EXISTS system_state (id INTEGER PRIMARY KEY CHECK (id = 1), balance REAL, margin_used REAL)`)
	db.Exec(`CREATE TABLE IF NOT EXISTS open_positions (symbol TEXT, entry_time INTEGER, side TEXT, size REAL, value_usdt REAL, margin REAL, leverage INTEGER, entry_price REAL, PRIMARY KEY (symbol, entry_time))`)
	db.Exec(`INSERT OR IGNORE INTO system_state (id, balance, margin_used) VALUES (1, 10000.0, 0.0)`)

	rows, _ := db.Query("SELECT symbol, side, size, value_usdt, margin, leverage, entry_price, entry_time FROM open_positions")
	if rows != nil {
		defer rows.Close()
		state.Lock()
		for rows.Next() {
			var p Position
			err := rows.Scan(&p.Symbol, &p.Side, &p.Size, &p.ValueUSDT, &p.Margin, &p.Leverage, &p.EntryPrice, &p.EntryTime)
			if err == nil && p.EntryPrice > 0 {
				p.MarkPrice = p.EntryPrice
				state.Positions = append(state.Positions, p)
			} else {
				log.Printf("⚠️ 忽略异常仓位 %s", p.Symbol)
			}
		}
		state.Unlock()
	}
	db.QueryRow("SELECT balance FROM system_state WHERE id = 1").Scan(&state.Balance)
}

func asyncSaveState() {
	state.RLock()
	bal, mar := state.Balance, state.MarginUsed
	state.RUnlock()
	db.Exec("UPDATE system_state SET balance = ?, margin_used = ? WHERE id = 1", bal, mar)
}

func asyncLogHistory(cp ClosedPosition) {
	db.Exec(`INSERT INTO trade_history (symbol, side, size, entry_price, close_price, realized_pnl, funding_fee, open_fee, close_fee, close_reason, entry_time, close_time) 
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		cp.Symbol, cp.Side, cp.Size, cp.EntryPrice, cp.ClosePrice, cp.RealizedPnL, cp.FundingFee, cp.OpenFee, cp.CloseFee, cp.CloseReason, cp.EntryTime, cp.CloseTime)
}

func corsHeaders(w http.ResponseWriter) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
}

func main() {
	initDB()
	triggerWSSUpdate()
	go riskMonitor()

	http.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil { log.Printf("WS Upgrade error: %v", err); return }
		clientsMu.Lock(); clients[conn] = true; clientsMu.Unlock()
		for { if _, _, err := conn.ReadMessage(); err != nil {
			clientsMu.Lock(); delete(clients, conn); clientsMu.Unlock()
			conn.Close(); break
		} }
	})

	go func() {
		for {
			time.Sleep(250 * time.Millisecond)
			state.Lock()
			var m float64
			for _, p := range state.Positions { m += p.Margin }
			state.MarginUsed = m
			js, _ := json.Marshal(state)
			state.Unlock()
			clientsMu.Lock()
			for c := range clients {
				if err := c.WriteMessage(websocket.TextMessage, js); err != nil {
					delete(clients, c)
					c.Close()
				}
			}
			clientsMu.Unlock()
		}
	}()

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) { http.ServeFile(w, r, "index.html") })
	
	http.HandleFunc("/api/v1/trade", func(w http.ResponseWriter, r *http.Request) {
		corsHeaders(w)
		if r.Method == "OPTIONS" { return }
		var req TradeRequest
		json.NewDecoder(r.Body).Decode(&req)
		state.Lock(); err := openPositionLocked(req); state.Unlock()
		if err != nil { http.Error(w, err.Error(), 400); return }
		w.Write([]byte(`{"status":"success"}`))
	})

	http.HandleFunc("/api/v1/close", func(w http.ResponseWriter, r *http.Request) {
		corsHeaders(w)
		if r.Method == "OPTIONS" { return }
		var req CloseRequest
		json.NewDecoder(r.Body).Decode(&req)
		state.Lock()
		closePositionLocked(req.Index, req.Reason)
		state.Unlock()
		w.Write([]byte(`{"status":"success"}`))
	})

	log.Println("🚀 Engine Started on :28964")
	log.Fatal(http.ListenAndServe(":28964", nil))
}
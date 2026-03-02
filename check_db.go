//go:build ignore

package main

import (
	"database/sql"
	"fmt"
	"log"
	_ "modernc.org/sqlite"
)

func main() {
	db, err := sql.Open("sqlite3", "./quant_ledger.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	fmt.Println("--- 活跃仓位快照 (open_positions) ---")
	rows, err := db.Query("SELECT symbol, entry_time, estimated_funding_fee FROM open_positions")
	if err != nil {
		log.Fatal(err)
	}
	defer rows.Close()
	for rows.Next() {
		var symbol string
		var entryTime int64
		var fee float64
		rows.Scan(&symbol, &entryTime, &fee)
		fmt.Printf("Symbol: %s, EntryTime: %d, EstFee: %.4f\n", symbol, entryTime, fee)
	}

	fmt.Println("\n--- 系统状态 (system_state) ---")
	row := db.QueryRow("SELECT balance, margin_used FROM system_state WHERE id = 1")
	var bal, mar float64
	row.Scan(&bal, &mar)
	fmt.Printf("Balance: $%.2f, MarginUsed: $%.2f\n", bal, mar)
}

//go:build ignore

package main

import (
	"database/sql"
	"fmt"
	_ "modernc.org/sqlite"
)

func main() {
	db, err := sql.Open("sqlite3", "quant_ledger.db")
	if err != nil { fmt.Println(err); return }
	defer db.Close()
	
	_, err = db.Exec("DELETE FROM trade_history")
	if err != nil { fmt.Println(err); return }
	
	fmt.Println("Successfully cleared all trade history from DB")
}

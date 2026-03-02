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
	
	_, err = db.Exec("UPDATE system_state SET balance = 1000.0, margin_used = 0.0 WHERE id = 1")
	if err != nil { fmt.Println(err); return }
	
	fmt.Println("Successfully initialized balance to 1000.00 and margin_used to 0.00 in DB")
}

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
	_, err = db.Exec("UPDATE system_state SET margin_used = 0.0 WHERE id = 1")
	if err != nil { fmt.Println(err); return }
	fmt.Println("Successfully reset margin_used to 0.0 in DB")
}

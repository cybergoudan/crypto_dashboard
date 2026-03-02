#!/bin/bash
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/go_sdk/go/bin"
cd /mnt/c/Users/Administrator/Desktop/tmp/lianghua
CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -o crypto_pro_daemon_linux_amd64 .
echo "exit:$?"

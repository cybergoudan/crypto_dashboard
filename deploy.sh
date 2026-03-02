#!/bin/bash
# ============================================================
# 币安量化仪表盘 - 一键部署脚本 (Ubuntu)
# 用法: bash <(curl -fsSL https://raw.githubusercontent.com/cybergoudan/crypto_dashboard/main/deploy.sh)
# ============================================================

set -e

APP_DIR="/opt/crypto_dashboard"
SERVICE_NAME="crypto_dashboard"
BINARY="crypto_dashboard"
PORT=28964
GITHUB_RAW="https://raw.githubusercontent.com/cybergoudan/crypto_dashboard/main"

# 防止 Windows CRLF 污染变量
APP_DIR="${APP_DIR//$'\r'/}"
SERVICE_NAME="${SERVICE_NAME//$'\r'/}"
BINARY="${BINARY//$'\r'/}"
GITHUB_RAW="${GITHUB_RAW//$'\r'/}"

echo ""
echo "======================================================"
echo "  币安量化仪表盘 部署脚本"
echo "======================================================"
echo ""

# 1. 检查 root
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用 root 或 sudo 运行此脚本"
    exit 1
fi

# 2. 创建目录
echo "📁 创建应用目录 $APP_DIR ..."
mkdir -p "$APP_DIR"

# 3. 从 GitHub 下载程序文件
echo "📦 下载程序文件..."
curl -fsSL "$GITHUB_RAW/crypto_dashboard" -o "$APP_DIR/$BINARY"
curl -fsSL "$GITHUB_RAW/index.html" -o "$APP_DIR/index.html"
chmod +x "$APP_DIR/$BINARY"

# 4. 写入 systemd service
echo "⚙️  配置 systemd 服务..."
cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Crypto Quant Dashboard
After=network.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/${BINARY}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

[Install]
WantedBy=multi-user.target
EOF

# 5. 启动服务
echo "🚀 启动服务..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
sleep 2

# 6. 写入 kuiqian 快捷菜单脚本
echo "🎛️  安装 kuiqian 快捷命令..."
cat > /usr/local/bin/kuiqian <<'KUIQIAN_EOF'
#!/bin/bash

SERVICE="crypto_dashboard"
APP_DIR="/opt/crypto_dashboard"
PORT=28964

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

show_status() {
    if systemctl is-active --quiet "$SERVICE"; then
        echo -e "  状态: ${GREEN}● 运行中${NC}"
    else
        echo -e "  状态: ${RED}● 已停止${NC}"
    fi
    local pid=$(systemctl show -p MainPID --value "$SERVICE" 2>/dev/null)
    [ "$pid" != "0" ] && echo -e "  PID:  $pid"
    echo -e "  端口: :${PORT}"
}

show_menu() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "  ╔══════════════════════════════════════╗"
    echo "  ║     币安量化仪表盘  管理控制台       ║"
    echo "  ╚══════════════════════════════════════╝"
    echo -e "${NC}"
    show_status
    echo ""
    echo -e "${BOLD}  ── 服务管理 ──────────────────────────${NC}"
    echo "  [1] 启动服务"
    echo "  [2] 停止服务"
    echo "  [3] 重启服务"
    echo "  [4] 查看服务状态"
    echo ""
    echo -e "${BOLD}  ── 日志查看 ──────────────────────────${NC}"
    echo "  [5] 实时日志 (tail -f)"
    echo "  [6] 最近 100 行日志"
    echo "  [7] 今日全部日志"
    echo "  [8] 错误日志过滤"
    echo ""
    echo -e "${BOLD}  ── 数据库 ─────────────────────────────${NC}"
    echo "  [9]  查看当前仓位"
    echo "  [10] 查看余额"
    echo "  [11] 清空仓位数据"
    echo "  [12] 重置余额为 10000"
    echo ""
    echo -e "${BOLD}  ── 程序更新 ──────────────────────────${NC}"
    echo "  [13] 从 GitHub 拉取最新版并重启"
    echo ""
    echo -e "${BOLD}  ── 其他 ────────────────────────────${NC}"
    echo "  [14] 卸载（删除服务和程序）"
    echo ""
    echo "  [0]  退出"
    echo ""
    echo -n "  请输入选项: "
}

db_query() {
    python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('${APP_DIR}/quant_ledger.db')
    cur = conn.cursor()
    cur.execute(\"\"\"$1\"\"\")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    if cols: print(' | '.join(cols))
    if cols: print('-' * 60)
    for r in rows: print(' | '.join(str(x) for x in r))
    if not rows: print('(无数据)')
    conn.close()
except Exception as e:
    print('DB错误:', e)
" 2>&1
}

db_exec() {
    python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('${APP_DIR}/quant_ledger.db')
    conn.execute(\"\"\"$1\"\"\")
    conn.commit()
    print('执行成功')
    conn.close()
except Exception as e:
    print('DB错误:', e)
" 2>&1
}

GITHUB_RAW="https://raw.githubusercontent.com/cybergoudan/crypto_dashboard/main"

while true; do
    show_menu
    read -r choice
    echo ""

    case "$choice" in
        1)
            systemctl start "$SERVICE" && echo -e "${GREEN}✅ 服务已启动${NC}" || echo -e "${RED}❌ 启动失败${NC}"
            ;;
        2)
            systemctl stop "$SERVICE" && echo -e "${YELLOW}⏹  服务已停止${NC}" || echo -e "${RED}❌ 停止失败${NC}"
            ;;
        3)
            systemctl restart "$SERVICE" && echo -e "${GREEN}🔄 服务已重启${NC}" || echo -e "${RED}❌ 重启失败${NC}"
            ;;
        4)
            systemctl status "$SERVICE" --no-pager
            ;;
        5)
            echo -e "${CYAN}实时日志 (Ctrl+C 退出)...${NC}"
            journalctl -u "$SERVICE" -f
            ;;
        6)
            journalctl -u "$SERVICE" -n 100 --no-pager
            ;;
        7)
            journalctl -u "$SERVICE" --since today --no-pager
            ;;
        8)
            echo -e "${RED}错误日志:${NC}"
            journalctl -u "$SERVICE" -p err --no-pager | tail -50
            ;;
        9)
            echo "=== 当前仓位 (open_positions) ==="
            db_query "SELECT symbol, side, size, entry_price, margin, leverage FROM open_positions"
            ;;
        10)
            echo "=== 账户余额 ==="
            db_query "SELECT balance, margin_used FROM system_state WHERE id=1"
            ;;
        11)
            echo -n "  ⚠️  确认清空所有仓位数据? (yes/N): "
            read -r confirm
            if [ "$confirm" = "yes" ]; then
                db_exec "DELETE FROM open_positions"
                systemctl restart "$SERVICE"
                echo -e "${GREEN}✅ 仓位已清空，服务已重启${NC}"
            else
                echo "已取消"
            fi
            ;;
        12)
            echo -n "  ⚠️  确认重置余额为 10000? (yes/N): "
            read -r confirm
            if [ "$confirm" = "yes" ]; then
                db_exec "UPDATE system_state SET balance=10000.0, margin_used=0.0 WHERE id=1"
                systemctl restart "$SERVICE"
                echo -e "${GREEN}✅ 余额已重置，服务已重启${NC}"
            else
                echo "已取消"
            fi
            ;;
        13)
            echo -e "${CYAN}正在从 GitHub 拉取最新版...${NC}"
            systemctl stop "$SERVICE"
            curl -fsSL "$GITHUB_RAW/crypto_dashboard" -o "$APP_DIR/$SERVICE"
            curl -fsSL "$GITHUB_RAW/index.html" -o "$APP_DIR/index.html"
            chmod +x "$APP_DIR/$SERVICE"
            systemctl start "$SERVICE"
            echo -e "${GREEN}✅ 已更新并重启${NC}"
            ;;
        14)
            echo -e "${RED}⚠️  此操作将删除服务、程序目录和 kuiqian 命令${NC}"
            echo -n "  确认卸载? (yes/N): "
            read -r confirm
            if [ "$confirm" = "yes" ]; then
                systemctl stop "$SERVICE" 2>/dev/null
                systemctl disable "$SERVICE" 2>/dev/null
                rm -f /etc/systemd/system/${SERVICE}.service
                systemctl daemon-reload
                rm -rf "$APP_DIR"
                rm -f /usr/local/bin/kuiqian
                echo -e "${GREEN}✅ 卸载完成${NC}"
                exit 0
            else
                echo "已取消"
            fi
            ;;
        0)
            echo "再见 👋"
            exit 0
            ;;
        *)
            echo -e "${RED}无效选项${NC}"
            ;;
    esac

    echo ""
    echo -n "  按 Enter 继续..."
    read -r
done
KUIQIAN_EOF

chmod +x /usr/local/bin/kuiqian

# 7. 检查服务状态
echo ""
echo "======================================================"
if systemctl is-active --quiet "$SERVICE"; then
    echo -e "  ✅ 部署成功！服务运行中，端口 :${PORT}"
else
    echo -e "  ❌ 服务启动失败，请检查日志："
    echo "     journalctl -u ${SERVICE_NAME} -n 30"
fi
echo ""
echo "  输入 kuiqian 进入管理菜单"
echo "======================================================"
echo ""

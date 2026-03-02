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

# 2. 检查 python3
if ! command -v python3 &>/dev/null; then
    echo "📦 安装 python3 及依赖..."
    apt-get update -q && apt-get install -y -q python3 python3-pip
fi
pip3 install requests -q 2>/dev/null || true

# 3. 停止已有服务（防止 Text file busy）
echo "🛑 停止已有服务..."
systemctl stop crypto_squeeze crypto_trend crypto_dashboard 2>/dev/null || true
sleep 1
# 强制杀掉残留进程
pkill -f "crypto_dashboard" 2>/dev/null || true
sleep 1

# 4. 创建目录
echo "📁 创建应用目录 $APP_DIR ..."
mkdir -p "$APP_DIR"

# 5. 从 GitHub 下载程序文件
echo "📦 下载程序文件..."
curl -fsSL "$GITHUB_RAW/crypto_dashboard" -o "$APP_DIR/${BINARY}.new"
mv -f "$APP_DIR/${BINARY}.new" "$APP_DIR/$BINARY"
curl -fsSL "$GITHUB_RAW/index.html" -o "$APP_DIR/index.html"
curl -fsSL "$GITHUB_RAW/agent_trend_catcher.py" -o "$APP_DIR/agent_trend_catcher.py"
curl -fsSL "$GITHUB_RAW/agent_squeeze_hunter.py" -o "$APP_DIR/agent_squeeze_hunter.py"
chmod +x "$APP_DIR/$BINARY"

# 5. 写入主服务 systemd service
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

# 6. 写入趋势接针策略 systemd service
cat > /etc/systemd/system/crypto_trend.service <<EOF
[Unit]
Description=Crypto Trend Catcher Strategy
After=network.target crypto_dashboard.service
Requires=crypto_dashboard.service

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/python3 -u ${APP_DIR}/agent_trend_catcher.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=crypto_trend

[Install]
WantedBy=multi-user.target
EOF

# 7. 写入资金费率逼空策略 systemd service
cat > /etc/systemd/system/crypto_squeeze.service <<EOF
[Unit]
Description=Crypto Squeeze Hunter Strategy
After=network.target crypto_dashboard.service
Requires=crypto_dashboard.service

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/python3 -u ${APP_DIR}/agent_squeeze_hunter.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=crypto_squeeze

[Install]
WantedBy=multi-user.target
EOF

# 8. 启动所有服务
echo "🚀 启动服务..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME" crypto_trend crypto_squeeze
systemctl restart "$SERVICE_NAME"
sleep 2
systemctl restart crypto_trend crypto_squeeze
sleep 1

# 9. 写入 kuiqian 快捷菜单脚本
echo "🎛️  安装 kuiqian 快捷命令..."
cat > /usr/local/bin/kuiqian <<'KUIQIAN_EOF'
#!/bin/bash

SERVICE="crypto_dashboard"
SVC_TREND="crypto_trend"
SVC_SQUEEZE="crypto_squeeze"
APP_DIR="/opt/crypto_dashboard"
PORT=28964

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

svc_status() {
    local s=$1
    if systemctl is-active --quiet "$s"; then
        echo -e "${GREEN}● 运行中${NC}"
    else
        echo -e "${RED}● 已停止${NC}"
    fi
}

show_status() {
    echo -e "  仪表盘引擎:   $(svc_status $SERVICE)  端口 :${PORT}"
    echo -e "  趋势接针策略: $(svc_status $SVC_TREND)"
    echo -e "  逼空套利策略: $(svc_status $SVC_SQUEEZE)"
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
    echo "  [1] 启动全部服务"
    echo "  [2] 停止全部服务"
    echo "  [3] 重启全部服务"
    echo "  [4] 查看服务状态"
    echo ""
    echo -e "${BOLD}  ── 日志查看 ──────────────────────────${NC}"
    echo "  [5] 实时日志 - 全部 (三个服务合并)"
    echo "  [6] 实时日志 - 仪表盘引擎"
    echo "  [7] 实时日志 - 趋势接针策略"
    echo "  [8] 实时日志 - 逼空套利策略"
    echo "  [9] 最近 100 行日志 (全部)"
    echo ""
    echo -e "${BOLD}  ── 数据库 ─────────────────────────────${NC}"
    echo "  [10] 查看当前仓位"
    echo "  [11] 查看余额"
    echo "  [12] 清空仓位数据"
    echo "  [13] 重置余额为 10000"
    echo ""
    echo -e "${BOLD}  ── 程序更新 ──────────────────────────${NC}"
    echo "  [14] 从 GitHub 拉取最新版并重启"
    echo ""
    echo -e "${BOLD}  ── 其他 ────────────────────────────${NC}"
    echo "  [15] 卸载（删除所有服务和程序）"
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
            systemctl start "$SERVICE" "$SVC_TREND" "$SVC_SQUEEZE" && echo -e "${GREEN}✅ 全部服务已启动${NC}" || echo -e "${RED}❌ 启动失败${NC}"
            ;;
        2)
            systemctl stop "$SVC_TREND" "$SVC_SQUEEZE" "$SERVICE" && echo -e "${YELLOW}⏹  全部服务已停止${NC}" || echo -e "${RED}❌ 停止失败${NC}"
            ;;
        3)
            systemctl restart "$SERVICE" && sleep 1 && systemctl restart "$SVC_TREND" "$SVC_SQUEEZE" && echo -e "${GREEN}🔄 全部服务已重启${NC}" || echo -e "${RED}❌ 重启失败${NC}"
            ;;
        4)
            systemctl status "$SERVICE" "$SVC_TREND" "$SVC_SQUEEZE" --no-pager
            ;;
        5)
            echo -e "${CYAN}全部实时日志 (Ctrl+C 退出)...${NC}"
            journalctl -u "$SERVICE" -u "$SVC_TREND" -u "$SVC_SQUEEZE" -f
            ;;
        6)
            echo -e "${CYAN}仪表盘引擎日志 (Ctrl+C 退出)...${NC}"
            journalctl -u "$SERVICE" -f
            ;;
        7)
            echo -e "${CYAN}趋势接针策略日志 (Ctrl+C 退出)...${NC}"
            journalctl -u "$SVC_TREND" -f
            ;;
        8)
            echo -e "${CYAN}逼空套利策略日志 (Ctrl+C 退出)...${NC}"
            journalctl -u "$SVC_SQUEEZE" -f
            ;;
        9)
            journalctl -u "$SERVICE" -u "$SVC_TREND" -u "$SVC_SQUEEZE" -n 100 --no-pager
            ;;
        10)
            echo "=== 当前仓位 (open_positions) ==="
            db_query "SELECT symbol, side, size, entry_price, margin, leverage FROM open_positions"
            ;;
        11)
            echo "=== 账户余额 ==="
            db_query "SELECT balance, margin_used FROM system_state WHERE id=1"
            ;;
        12)
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
        13)
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
        14)
            echo -e "${CYAN}正在从 GitHub 拉取最新版...${NC}"
            systemctl stop "$SVC_TREND" "$SVC_SQUEEZE" "$SERVICE"
            curl -fsSL "$GITHUB_RAW/crypto_dashboard" -o "$APP_DIR/crypto_dashboard"
            curl -fsSL "$GITHUB_RAW/index.html" -o "$APP_DIR/index.html"
            curl -fsSL "$GITHUB_RAW/agent_trend_catcher.py" -o "$APP_DIR/agent_trend_catcher.py"
            curl -fsSL "$GITHUB_RAW/agent_squeeze_hunter.py" -o "$APP_DIR/agent_squeeze_hunter.py"
            chmod +x "$APP_DIR/crypto_dashboard"
            systemctl start "$SERVICE" && sleep 2 && systemctl start "$SVC_TREND" "$SVC_SQUEEZE"
            echo -e "${GREEN}✅ 已更新并重启全部服务${NC}"
            ;;
        15)
            echo -e "${RED}⚠️  此操作将删除所有服务、程序目录和 kuiqian 命令${NC}"
            echo -n "  确认卸载? (yes/N): "
            read -r confirm
            if [ "$confirm" = "yes" ]; then
                systemctl stop "$SVC_TREND" "$SVC_SQUEEZE" "$SERVICE" 2>/dev/null
                systemctl disable "$SVC_TREND" "$SVC_SQUEEZE" "$SERVICE" 2>/dev/null
                rm -f /etc/systemd/system/${SERVICE}.service
                rm -f /etc/systemd/system/crypto_trend.service
                rm -f /etc/systemd/system/crypto_squeeze.service
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

# 10. 检查服务状态
echo ""
echo "======================================================"
ALL_OK=true
for svc in "$SERVICE_NAME" crypto_trend crypto_squeeze; do
    if systemctl is-active --quiet "$svc"; then
        echo "  ✅ $svc 运行中"
    else
        echo "  ❌ $svc 启动失败"
        ALL_OK=false
    fi
done
echo ""
if $ALL_OK; then
    echo "  🎉 全部部署成功！仪表盘端口 :${PORT}"
else
    echo "  ⚠️  部分服务启动失败，查看日志："
    echo "     journalctl -u crypto_dashboard -u crypto_trend -u crypto_squeeze -n 30"
fi
echo ""
echo "  输入 kuiqian 进入管理菜单"
echo "======================================================"
echo ""

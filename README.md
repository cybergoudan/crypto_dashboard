# Crypto Quant Dashboard

币安合约量化仪表盘，实时行情、仓位管理、Alpha 策略信号流。

## 一键安装（Ubuntu）

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/cybergoudan/crypto_dashboard/main/deploy.sh)
```

安装完成后输入 `kuiqian` 进入管理菜单。

## 管理菜单功能

| 选项 | 功能 |
|------|------|
| 1 | 启动服务 |
| 2 | 停止服务 |
| 3 | 重启服务 |
| 4 | 服务状态详情 |
| 5 | 实时日志 (tail -f) |
| 6 | 最近 100 行日志 |
| 7 | 今日全部日志 |
| 8 | 错误日志过滤 |
| 9 | 查看当前仓位 |
| 10 | 查看余额 |
| 11 | 清空仓位数据 |
| 12 | 重置余额为 10000 |
| 13 | 上传新版本并重启 |
| 14 | 卸载（删除服务和程序） |

## 手动部署

```bash
# 下载文件
wget https://raw.githubusercontent.com/cybergoudan/crypto_dashboard/main/crypto_dashboard
wget https://raw.githubusercontent.com/cybergoudan/crypto_dashboard/main/index.html
wget https://raw.githubusercontent.com/cybergoudan/crypto_dashboard/main/deploy.sh

# 执行部署
chmod +x crypto_dashboard deploy.sh
sudo bash deploy.sh
```

## 服务信息

- 程序目录：`/opt/crypto_dashboard/`
- 端口：`:28964`
- 服务名：`crypto_dashboard`
- 管理命令：`kuiqian`

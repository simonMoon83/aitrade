#!/bin/bash

###############################################################################
# AI Stock Trader - Systemd 서비스 설정 스크립트
# 이 스크립트는 서버에서 실행됩니다
###############################################################################

set -e

echo "🔧 Systemd 서비스 설정 시작..."

# 현재 사용자
CURRENT_USER=$(whoami)
PROJECT_DIR="/home/$CURRENT_USER/aitrader"

# 색상
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Paper Trading 서비스 생성
echo -e "${YELLOW}[1/4] Paper Trading 서비스 생성...${NC}"
sudo tee /etc/systemd/system/aitrader-paper.service > /dev/null <<EOF
[Unit]
Description=AI Stock Trader - Paper Trading
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python main.py --mode paper --symbols AAPL,MSFT,GOOGL,AMZN,NVDA,META,TSLA --daemon
Restart=always
RestartSec=10
StandardOutput=append:$PROJECT_DIR/logs/paper_trading.log
StandardError=append:$PROJECT_DIR/logs/paper_trading_error.log

[Install]
WantedBy=multi-user.target
EOF

# Dashboard 서비스 생성
echo -e "${YELLOW}[2/4] Dashboard 서비스 생성...${NC}"
sudo tee /etc/systemd/system/aitrader-dashboard.service > /dev/null <<EOF
[Unit]
Description=AI Stock Trader Dashboard
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
Environment="FLASK_APP=simple_dashboard.py"
ExecStart=$PROJECT_DIR/venv/bin/python simple_dashboard.py
Restart=always
RestartSec=10
StandardOutput=append:$PROJECT_DIR/logs/dashboard.log
StandardError=append:$PROJECT_DIR/logs/dashboard_error.log

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화
echo -e "${YELLOW}[3/4] 서비스 활성화...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable aitrader-paper
sudo systemctl enable aitrader-dashboard

# 서비스 시작
echo -e "${YELLOW}[4/4] 서비스 시작...${NC}"
sudo systemctl start aitrader-paper
sudo systemctl start aitrader-dashboard

# 상태 확인
echo ""
echo -e "${GREEN}✅ 서비스 설정 완료!${NC}"
echo ""
echo "서비스 상태:"
sudo systemctl status aitrader-paper --no-pager
echo ""
sudo systemctl status aitrader-dashboard --no-pager
echo ""
echo "유용한 명령어:"
echo "  상태 확인: sudo systemctl status aitrader-paper"
echo "  로그 확인: sudo journalctl -u aitrader-paper -f"
echo "  재시작:   sudo systemctl restart aitrader-paper"
echo ""

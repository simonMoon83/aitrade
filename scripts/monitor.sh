#!/bin/bash

###############################################################################
# AI Stock Trader - 모니터링 스크립트
# 시스템 상태를 한눈에 확인
###############################################################################

# 색상
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

clear

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  AI Stock Trader 모니터링${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 현재 시간
echo -e "${YELLOW}📅 현재 시간:${NC} $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 서비스 상태
echo -e "${YELLOW}🔧 서비스 상태:${NC}"
echo "-----------------------------------"

# Paper Trading
if systemctl is-active --quiet aitrader-paper; then
    echo -e "  Paper Trading: ${GREEN}●${NC} 실행 중"
else
    echo -e "  Paper Trading: ${RED}●${NC} 중지됨"
fi

# Dashboard
if systemctl is-active --quiet aitrader-dashboard; then
    echo -e "  Dashboard:     ${GREEN}●${NC} 실행 중"
else
    echo -e "  Dashboard:     ${RED}●${NC} 중지됨"
fi
echo ""

# 시스템 리소스
echo -e "${YELLOW}💻 시스템 리소스:${NC}"
echo "-----------------------------------"

# CPU 사용률
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
echo -e "  CPU 사용률:  ${CPU_USAGE}%"

# 메모리 사용률
MEM_INFO=$(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2 }')
echo -e "  메모리:      ${MEM_INFO}"

# 디스크 사용률
DISK_USAGE=$(df -h / | awk 'NR==2{print $5}')
echo -e "  디스크:      ${DISK_USAGE}"
echo ""

# 프로세스 정보
echo -e "${YELLOW}🔍 Python 프로세스:${NC}"
echo "-----------------------------------"
ps aux | grep -E "main.py|simple_dashboard.py" | grep -v grep | awk '{printf "  PID: %-6s CPU: %-5s MEM: %-5s CMD: %s\n", $2, $3"%", $4"%", $11}'
echo ""

# 최근 로그 (에러만)
echo -e "${YELLOW}📝 최근 에러 로그 (최근 5개):${NC}"
echo "-----------------------------------"
if [ -f ~/aitrader/logs/paper_trading_error.log ]; then
    tail -5 ~/aitrader/logs/paper_trading_error.log 2>/dev/null | sed 's/^/  /' || echo "  에러 없음"
else
    echo "  로그 파일 없음"
fi
echo ""

# 네트워크 연결
echo -e "${YELLOW}🌐 네트워크 연결:${NC}"
echo "-----------------------------------"
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "알 수 없음")
echo -e "  공용 IP:     ${PUBLIC_IP}"
DASHBOARD_PORT=$(ss -tulpn 2>/dev/null | grep :5000 | wc -l)
if [ $DASHBOARD_PORT -gt 0 ]; then
    echo -e "  대시보드:    ${GREEN}포트 5000 LISTEN${NC}"
else
    echo -e "  대시보드:    ${RED}포트 5000 닫힘${NC}"
fi
echo ""

# 디스크 공간
echo -e "${YELLOW}💾 디스크 공간 (aitrader):${NC}"
echo "-----------------------------------"
if [ -d ~/aitrader ]; then
    du -sh ~/aitrader/{logs,data,reports,models} 2>/dev/null | awk '{printf "  %-15s %s\n", $2, $1}'
fi
echo ""

# 빠른 명령어
echo -e "${BLUE}빠른 명령어:${NC}"
echo "  로그 보기:     tail -f ~/aitrader/logs/paper_trading.log"
echo "  서비스 재시작: sudo systemctl restart aitrader-paper"
echo "  대시보드 접속: http://${PUBLIC_IP}:5000"
echo ""

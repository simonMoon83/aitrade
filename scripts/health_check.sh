#!/bin/bash

###############################################################################
# AI Stock Trader - 헬스 체크 스크립트
# 시스템 문제를 자동으로 감지하고 알림
###############################################################################

# 색상
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ALERT=0
PROJECT_DIR="$HOME/aitrader"

echo "🏥 AI Stock Trader 헬스 체크"
echo "================================"
echo ""

# 1. 서비스 상태 확인
echo "1. 서비스 상태 확인..."
if ! systemctl is-active --quiet aitrader-paper; then
    echo -e "  ${RED}✗${NC} Paper Trading 서비스가 중지되었습니다!"
    ALERT=1
else
    echo -e "  ${GREEN}✓${NC} Paper Trading 서비스 정상"
fi

if ! systemctl is-active --quiet aitrader-dashboard; then
    echo -e "  ${YELLOW}⚠${NC} Dashboard 서비스가 중지되었습니다"
else
    echo -e "  ${GREEN}✓${NC} Dashboard 서비스 정상"
fi
echo ""

# 2. 메모리 사용률 확인
echo "2. 메모리 사용률 확인..."
MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
if [ $MEM_USAGE -gt 90 ]; then
    echo -e "  ${RED}✗${NC} 메모리 사용률이 높습니다: ${MEM_USAGE}%"
    ALERT=1
elif [ $MEM_USAGE -gt 80 ]; then
    echo -e "  ${YELLOW}⚠${NC} 메모리 사용률: ${MEM_USAGE}%"
else
    echo -e "  ${GREEN}✓${NC} 메모리 사용률 정상: ${MEM_USAGE}%"
fi
echo ""

# 3. 디스크 공간 확인
echo "3. 디스크 공간 확인..."
DISK_USAGE=$(df -h / | awk 'NR==2{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
    echo -e "  ${RED}✗${NC} 디스크 공간이 부족합니다: ${DISK_USAGE}%"
    ALERT=1
elif [ $DISK_USAGE -gt 80 ]; then
    echo -e "  ${YELLOW}⚠${NC} 디스크 사용률: ${DISK_USAGE}%"
else
    echo -e "  ${GREEN}✓${NC} 디스크 공간 정상: ${DISK_USAGE}%"
fi
echo ""

# 4. 로그 파일 에러 확인
echo "4. 최근 에러 로그 확인..."
if [ -f "$PROJECT_DIR/logs/paper_trading_error.log" ]; then
    ERROR_COUNT=$(tail -100 "$PROJECT_DIR/logs/paper_trading_error.log" 2>/dev/null | grep -i "error\|exception\|critical" | wc -l)
    if [ $ERROR_COUNT -gt 10 ]; then
        echo -e "  ${RED}✗${NC} 최근 100줄에 ${ERROR_COUNT}개의 에러가 발견되었습니다"
        ALERT=1
        echo "    최근 에러 예시:"
        tail -100 "$PROJECT_DIR/logs/paper_trading_error.log" | grep -i "error\|exception" | tail -3 | sed 's/^/    /'
    elif [ $ERROR_COUNT -gt 0 ]; then
        echo -e "  ${YELLOW}⚠${NC} 최근 100줄에 ${ERROR_COUNT}개의 에러가 있습니다"
    else
        echo -e "  ${GREEN}✓${NC} 최근 에러 없음"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} 에러 로그 파일을 찾을 수 없습니다"
fi
echo ""

# 5. API 연결 확인
echo "5. API 연결 확인..."
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
    if [ -z "$ALPACA_API_KEY" ]; then
        echo -e "  ${RED}✗${NC} Alpaca API 키가 설정되지 않았습니다"
        ALERT=1
    else
        echo -e "  ${GREEN}✓${NC} API 키 설정됨"
    fi
else
    echo -e "  ${RED}✗${NC} .env 파일이 없습니다"
    ALERT=1
fi
echo ""

# 6. Python 프로세스 확인
echo "6. Python 프로세스 확인..."
PYTHON_PROCESSES=$(ps aux | grep -E "main.py|simple_dashboard.py" | grep -v grep | wc -l)
if [ $PYTHON_PROCESSES -eq 0 ]; then
    echo -e "  ${RED}✗${NC} Python 프로세스가 실행되고 있지 않습니다"
    ALERT=1
else
    echo -e "  ${GREEN}✓${NC} ${PYTHON_PROCESSES}개의 Python 프로세스 실행 중"
fi
echo ""

# 7. 네트워크 연결 확인
echo "7. 네트워크 연결 확인..."
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} 인터넷 연결 정상"
else
    echo -e "  ${RED}✗${NC} 인터넷 연결 불가"
    ALERT=1
fi
echo ""

# 8. 포트 확인
echo "8. 대시보드 포트 확인..."
if ss -tulpn 2>/dev/null | grep -q :5000; then
    echo -e "  ${GREEN}✓${NC} 포트 5000 활성화"
else
    echo -e "  ${YELLOW}⚠${NC} 포트 5000이 닫혀있습니다"
fi
echo ""

# 최종 결과
echo "================================"
if [ $ALERT -eq 0 ]; then
    echo -e "${GREEN}✅ 모든 검사 통과! 시스템 정상${NC}"
    exit 0
else
    echo -e "${RED}⚠️  문제가 발견되었습니다!${NC}"
    echo ""
    echo "권장 조치:"
    echo "  1. 로그 확인: tail -f $PROJECT_DIR/logs/paper_trading.log"
    echo "  2. 서비스 재시작: sudo systemctl restart aitrader-paper"
    echo "  3. 시스템 리소스: ./scripts/monitor.sh"
    exit 1
fi

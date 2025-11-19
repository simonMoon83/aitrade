#!/bin/bash

###############################################################################
# AI Stock Trader - OCI 배포 스크립트
# 이 스크립트는 서버에서 실행됩니다
###############################################################################

set -e  # 에러 발생시 중단

echo "🚀 AI Stock Trader 배포 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 프로젝트 디렉토리
PROJECT_DIR="/home/ubuntu/aitrader"
VENV_DIR="$PROJECT_DIR/venv"

# 디렉토리 이동
cd $PROJECT_DIR || exit 1

echo -e "${YELLOW}[1/7] 최신 코드 가져오기...${NC}"
git pull origin main

echo -e "${YELLOW}[2/7] 가상환경 활성화...${NC}"
source $VENV_DIR/bin/activate

echo -e "${YELLOW}[3/7] 의존성 업데이트...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${YELLOW}[4/7] 디렉토리 권한 설정...${NC}"
mkdir -p logs reports data models
chmod 755 main.py simple_dashboard.py

echo -e "${YELLOW}[5/7] .env 파일 확인...${NC}"
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env 파일이 없습니다!${NC}"
    echo "env.example을 참고하여 .env 파일을 생성하세요."
    exit 1
fi
chmod 600 .env

echo -e "${YELLOW}[6/7] 서비스 재시작...${NC}"
sudo systemctl daemon-reload
sudo systemctl restart aitrader-paper || echo -e "${YELLOW}⚠️  Paper trading 서비스를 찾을 수 없습니다${NC}"
sudo systemctl restart aitrader-dashboard || echo -e "${YELLOW}⚠️  Dashboard 서비스를 찾을 수 없습니다${NC}"

echo -e "${YELLOW}[7/7] 서비스 상태 확인...${NC}"
sleep 2
sudo systemctl status aitrader-paper --no-pager || true
sudo systemctl status aitrader-dashboard --no-pager || true

echo ""
echo -e "${GREEN}✅ 배포 완료!${NC}"
echo ""
echo "📊 대시보드: http://$(curl -s ifconfig.me):5000"
echo "📝 로그 확인: tail -f logs/paper_trading.log"
echo ""

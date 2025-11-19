#!/bin/bash

###############################################################################
# AI Stock Trader - 빠른 시작 스크립트
# 새 서버에 처음 설치할 때 사용
###############################################################################

set -e

echo "🚀 AI Stock Trader 빠른 시작..."

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 사용자 확인
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ root 사용자로 실행하지 마세요!${NC}"
    echo "일반 사용자(ubuntu)로 실행하세요."
    exit 1
fi

PROJECT_DIR="$HOME/aitrader"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  AI Stock Trader 설치 마법사${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 1. 시스템 업데이트
echo -e "${YELLOW}[1/9] 시스템 업데이트...${NC}"
sudo apt update && sudo apt upgrade -y

# 2. 필수 패키지 설치
echo -e "${YELLOW}[2/9] 필수 패키지 설치...${NC}"
sudo apt install -y software-properties-common build-essential git curl wget

# 3. Python 3.11 설치
echo -e "${YELLOW}[3/9] Python 3.11 설치...${NC}"
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# 4. 프로젝트가 없으면 생성
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}[4/9] 프로젝트 디렉토리 생성...${NC}"
    mkdir -p $PROJECT_DIR
    echo -e "${RED}⚠️  프로젝트 파일을 업로드하거나 git clone 하세요!${NC}"
    echo "   예: git clone https://github.com/YOUR_REPO/aitrader.git ~/aitrader"
else
    echo -e "${GREEN}✓ 프로젝트 디렉토리 존재${NC}"
fi

cd $PROJECT_DIR

# 5. 가상환경 생성
echo -e "${YELLOW}[5/9] Python 가상환경 생성...${NC}"
python3.11 -m venv venv
source venv/bin/activate

# 6. 의존성 설치
echo -e "${YELLOW}[6/9] Python 패키지 설치...${NC}"
pip install --upgrade pip
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
else
    echo -e "${RED}⚠️  requirements.txt를 찾을 수 없습니다${NC}"
fi

# 7. 디렉토리 생성
echo -e "${YELLOW}[7/9] 필요한 디렉토리 생성...${NC}"
mkdir -p logs reports data models archive

# 8. .env 파일 체크
echo -e "${YELLOW}[8/9] 환경 설정 파일 확인...${NC}"
if [ ! -f .env ]; then
    if [ -f env.example ]; then
        cp env.example .env
        echo -e "${YELLOW}⚠️  .env 파일을 생성했습니다. API 키를 입력하세요!${NC}"
        echo "   편집: nano .env"
    else
        echo -e "${RED}❌ env.example 파일이 없습니다!${NC}"
    fi
else
    echo -e "${GREEN}✓ .env 파일 존재${NC}"
fi

# 9. 방화벽 설정
echo -e "${YELLOW}[9/9] 방화벽 설정...${NC}"
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 5000/tcp  # Dashboard
sudo ufw --force enable

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}  설치 완료! 🎉${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${BLUE}다음 단계:${NC}"
echo ""
echo "1️⃣  API 키 설정:"
echo "   nano ~/.aitrader/.env"
echo ""
echo "2️⃣  백테스트 테스트:"
echo "   cd ~/aitrader && source venv/bin/activate"
echo "   python main.py --mode backtest --symbols AAPL,MSFT --start 2024-01-01 --end 2024-12-31"
echo ""
echo "3️⃣  서비스 설정:"
echo "   chmod +x scripts/setup_services.sh"
echo "   ./scripts/setup_services.sh"
echo ""
echo "4️⃣  대시보드 접속:"
echo "   http://$(curl -s ifconfig.me):5000"
echo ""
echo -e "${YELLOW}⚠️  보안 주의사항:${NC}"
echo "   - .env 파일 권한: chmod 600 .env"
echo "   - 방화벽에서 5000 포트는 본인 IP만 허용 권장"
echo "   - 실전 거래 전 충분한 페이퍼 트레이딩 테스트 필수!"
echo ""

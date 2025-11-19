#!/bin/bash

###############################################################################
# AI Stock Trader - 백업 스크립트
# 중요 데이터를 백업합니다
###############################################################################

set -e

# 색상
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 설정
PROJECT_DIR="$HOME/aitrader"
BACKUP_DIR="$HOME/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="aitrader_backup_$DATE.tar.gz"
RETENTION_DAYS=7

echo -e "${YELLOW}🔄 백업 시작...${NC}"

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

# 임시 디렉토리 생성
TEMP_DIR=$(mktemp -d)
TEMP_BACKUP="$TEMP_DIR/aitrader_backup"
mkdir -p $TEMP_BACKUP

cd $PROJECT_DIR

echo -e "${YELLOW}[1/5] 데이터 복사 중...${NC}"
# 중요 파일만 백업
cp -r data $TEMP_BACKUP/ 2>/dev/null || mkdir -p $TEMP_BACKUP/data
cp -r reports $TEMP_BACKUP/ 2>/dev/null || mkdir -p $TEMP_BACKUP/reports
cp -r logs $TEMP_BACKUP/ 2>/dev/null || mkdir -p $TEMP_BACKUP/logs
cp -r models $TEMP_BACKUP/ 2>/dev/null || mkdir -p $TEMP_BACKUP/models

echo -e "${YELLOW}[2/5] 설정 파일 복사 중...${NC}"
cp .env $TEMP_BACKUP/ 2>/dev/null || echo "  .env 파일 없음"
cp config.py $TEMP_BACKUP/ 2>/dev/null || echo "  config.py 없음"

echo -e "${YELLOW}[3/5] 압축 중...${NC}"
cd $TEMP_DIR
tar -czf "$BACKUP_DIR/$BACKUP_NAME" aitrader_backup/

# 백업 파일 크기 확인
BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME" | cut -f1)

echo -e "${YELLOW}[4/5] 오래된 백업 삭제 중...${NC}"
# 7일 이상 된 백업 삭제
find $BACKUP_DIR -name "aitrader_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# 백업 파일 개수
BACKUP_COUNT=$(ls -1 $BACKUP_DIR/aitrader_backup_*.tar.gz 2>/dev/null | wc -l)

echo -e "${YELLOW}[5/5] 정리 중...${NC}"
# 임시 디렉토리 삭제
rm -rf $TEMP_DIR

echo ""
echo -e "${GREEN}✅ 백업 완료!${NC}"
echo ""
echo "  백업 파일: $BACKUP_DIR/$BACKUP_NAME"
echo "  파일 크기: $BACKUP_SIZE"
echo "  총 백업 수: $BACKUP_COUNT개"
echo ""

# 백업 목록 표시
echo "최근 백업 목록:"
ls -lht $BACKUP_DIR/aitrader_backup_*.tar.gz 2>/dev/null | head -5 | awk '{printf "  %s %s  %s\n", $6, $7, $9}' || echo "  백업 없음"
echo ""

# 복원 방법 안내
echo -e "${YELLOW}복원 방법:${NC}"
echo "  tar -xzf $BACKUP_DIR/$BACKUP_NAME -C ~/"
echo ""

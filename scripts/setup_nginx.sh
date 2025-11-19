#!/bin/bash
# AI Stock Trader - Nginx 설정 추가 스크립트
# 이미 nginx가 설치된 서버에 aitrader 설정을 추가합니다.

set -e

echo "🌐 AI Stock Trader Nginx 설정 추가 시작..."

PROJECT_DIR="/home/ubuntu/aitrader"
NGINX_CONF="$PROJECT_DIR/nginx/aitrader.conf"

# 1. Nginx가 설치되어 있는지 확인
if ! command -v nginx &> /dev/null; then
    echo "❌ Nginx가 설치되어 있지 않습니다!"
    echo "다음 명령으로 설치하세요: sudo apt install -y nginx"
    exit 1
fi

echo "✅ Nginx 설치 확인됨"

# 2. 도메인 입력받기
read -p "도메인 또는 서브도메인을 입력하세요 (예: aitrader.darkhorsetip.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo "❌ 도메인을 입력해야 합니다!"
    exit 1
fi

echo "입력된 도메인: $DOMAIN"

# 3. nginx 설정 파일 복사 및 도메인 변경
echo "[1/6] Nginx 설정 파일 생성 중..."
sudo cp $NGINX_CONF /etc/nginx/sites-available/aitrader
sudo sed -i "s/aitrader.your-domain.com/$DOMAIN/g" /etc/nginx/sites-available/aitrader

# 4. 심볼릭 링크 생성
echo "[2/6] Nginx 설정 활성화 중..."
if [ -L /etc/nginx/sites-enabled/aitrader ]; then
    sudo rm /etc/nginx/sites-enabled/aitrader
fi
sudo ln -s /etc/nginx/sites-available/aitrader /etc/nginx/sites-enabled/

# 5. Nginx 설정 테스트
echo "[3/6] Nginx 설정 검증 중..."
if ! sudo nginx -t; then
    echo "❌ Nginx 설정에 오류가 있습니다!"
    echo "설정 파일 확인: sudo nano /etc/nginx/sites-available/aitrader"
    exit 1
fi

echo "✅ Nginx 설정 검증 완료"

# 6. Nginx 재시작
echo "[4/6] Nginx 재시작 중..."
sudo systemctl reload nginx

# 7. 방화벽 확인 (UFW 사용 시)
if command -v ufw &> /dev/null; then
    echo "[5/6] 방화벽 상태 확인 중..."
    sudo ufw status | grep -E "80|443" || {
        echo "⚠️  방화벽에 HTTP/HTTPS 포트가 열려있지 않습니다."
        read -p "방화벽 포트를 열까요? (y/n): " OPEN_PORTS
        if [ "$OPEN_PORTS" = "y" ]; then
            sudo ufw allow 80/tcp
            sudo ufw allow 443/tcp
            echo "✅ 방화벽 포트 80, 443 열림"
        fi
    }
else
    echo "[5/6] UFW가 설치되어 있지 않습니다. 건너뜁니다."
fi

# 8. 서비스 상태 확인
echo "[6/6] 서비스 상태 확인 중..."
echo ""
echo "📊 Nginx 상태:"
sudo systemctl status nginx --no-pager | head -n 10

echo ""
echo "📊 AI Trader 서비스 상태:"
if systemctl is-active --quiet aitrader-paper; then
    echo "✅ aitrader-paper: 실행 중"
else
    echo "⚠️  aitrader-paper: 실행 중이 아님"
    echo "   시작: sudo systemctl start aitrader-paper"
fi

if systemctl is-active --quiet aitrader-dashboard; then
    echo "✅ aitrader-dashboard: 실행 중"
else
    echo "⚠️  aitrader-dashboard: 실행 중이 아님"
    echo "   시작: sudo systemctl start aitrader-dashboard"
fi

echo ""
echo "✅ Nginx 설정 완료!"
echo ""
echo "📌 접속 정보:"
echo "   HTTP:  http://$DOMAIN"
echo "   로컬:  http://localhost:5000"
echo ""
echo "📌 SSL 인증서 발급 (선택사항):"
echo "   sudo certbot --nginx -d $DOMAIN"
echo ""
echo "📌 설정 파일 위치:"
echo "   /etc/nginx/sites-available/aitrader"
echo ""
echo "📌 로그 확인:"
echo "   sudo tail -f /var/log/nginx/aitrader_access.log"
echo "   sudo tail -f /var/log/nginx/aitrader_error.log"
echo ""

#!/bin/bash
# Let's Encrypt SSL 인증서 설정 스크립트

echo "=== SSL 인증서 설정 시작 ==="

# Certbot 설치
sudo apt install -y certbot python3-certbot-nginx

# 도메인 입력 받기
read -p "도메인을 입력하세요 (예: trader.yourdomain.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo "도메인이 입력되지 않았습니다. 스크립트를 종료합니다."
    exit 1
fi

# Nginx 설정 파일 업데이트
sudo sed -i "s/server_name your-domain.com;/server_name $DOMAIN;/" /etc/nginx/sites-available/aitrader

# SSL 인증서 발급
sudo certbot --nginx -d $DOMAIN

# 자동 갱신 설정
sudo crontab -l 2>/dev/null | { cat; echo "0 12 * * * /usr/bin/certbot renew --quiet"; } | sudo crontab -

# Nginx 재시작
sudo systemctl restart nginx

echo "=== SSL 인증서 설정 완료 ==="
echo "HTTPS 접속: https://$DOMAIN"
echo "인증서 자동 갱신이 설정되었습니다."


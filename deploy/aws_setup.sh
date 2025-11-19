#!/bin/bash
# AWS EC2 서버 설정 스크립트

echo "=== AI 주식 트레이더 서버 설정 시작 ==="

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Python 3.9 설치
sudo apt install -y python3.9 python3.9-pip python3.9-venv

# 필수 패키지 설치
sudo apt install -y nginx supervisor git curl

# 프로젝트 디렉토리 생성
sudo mkdir -p /opt/aitrader
sudo chown $USER:$USER /opt/aitrader

# 프로젝트 클론 (GitHub에서)
cd /opt/aitrader
git clone https://github.com/your-username/aitrader.git .

# Python 가상환경 생성
python3.9 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 파일 생성
cat > .env << EOF
# Alpaca API 설정
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here

# 대시보드 인증
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=your_secure_password_here

# 텔레그램 봇 (선택사항)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# 암호화 키
ENCRYPTION_KEY=your_secret_encryption_key_here
EOF

# 로그 디렉토리 생성
mkdir -p logs reports backtest_results

# Supervisor 설정
sudo tee /etc/supervisor/conf.d/aitrader.conf > /dev/null << EOF
[program:aitrader]
command=/opt/aitrader/venv/bin/python /opt/aitrader/main.py --mode paper --daemon
directory=/opt/aitrader
user=$USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/aitrader/logs/supervisor.log
environment=PATH="/opt/aitrader/venv/bin"
EOF

# Nginx 설정
sudo tee /etc/nginx/sites-available/aitrader > /dev/null << EOF
server {
    listen 80;
    server_name your-domain.com;  # 도메인이 있다면 변경

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # 정적 파일 캐싱
    location /static {
        alias /opt/aitrader/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Nginx 사이트 활성화
sudo ln -sf /etc/nginx/sites-available/aitrader /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 방화벽 설정
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw --force enable

# 서비스 시작
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start aitrader
sudo systemctl restart nginx

echo "=== 서버 설정 완료 ==="
echo "다음 단계:"
echo "1. .env 파일에 실제 API 키 입력"
echo "2. SSL 인증서 설정: sudo ./deploy/setup_ssl.sh"
echo "3. 서비스 상태 확인: sudo supervisorctl status"
echo "4. 웹 대시보드 접속: http://your-server-ip"


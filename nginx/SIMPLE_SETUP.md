# AI Trader 간단 설치 가이드 (Systemd + Nginx)

Docker 없이 **직접 실행 + 기존 Nginx 연동** 방식입니다.

## 📋 전제조건

- Ubuntu 서버 (Oracle Cloud)
- Nginx가 이미 설치되어 있음
- Python 3.9+ 설치
- darkhorsetip이 이미 실행 중

## 🚀 전체 설치 과정

### 1단계: 서버에 코드 업로드

```bash
# 서버 접속
ssh ubuntu@your-server-ip

# 코드 업로드 (Git 사용)
cd /home/ubuntu
git clone https://github.com/yourusername/aitrader.git
cd aitrader

# 또는 scp로 업로드
# 로컬에서: scp -r C:\Project\aitrader ubuntu@your-server-ip:/home/ubuntu/
```

### 2단계: 자동 설치 스크립트 실행

```bash
cd /home/ubuntu/aitrader

# 스크립트 실행 권한 부여
chmod +x scripts/*.sh

# 1. 환경 설정 (Python, 가상환경, 의존성)
./scripts/quick_start.sh
```

스크립트가 자동으로:
- ✅ 시스템 업데이트
- ✅ Python 3.11 설치
- ✅ 가상환경 생성
- ✅ 의존성 설치 (requirements.txt)
- ✅ 디렉토리 생성 (data, logs, reports, models)
- ✅ 방화벽 설정

### 3단계: API 키 설정

```bash
# .env 파일 생성
nano .env
```

**입력 내용:**
```env
# Alpaca API (Paper Trading)
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# 알림 설정 (선택)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

저장: `Ctrl+O` → `Enter` → `Ctrl+X`

### 4단계: Systemd 서비스 설치

```bash
# 서비스 등록
./scripts/setup_services.sh
```

자동으로 생성되는 서비스:
- ✅ `aitrader-paper.service` - Paper Trading 자동 실행
- ✅ `aitrader-dashboard.service` - 웹 대시보드 (포트 5000)

### 5단계: Nginx 설정 추가

#### Option A: 자동 설정

```bash
./scripts/setup_nginx.sh

# 도메인 입력 프롬프트에서:
# aitrader.darkhorsetip.com 입력
```

#### Option B: 수동 설정 (darkhorsetip 통합)

**기존 darkhorsetip nginx 설정에 추가:**

```bash
# darkhorsetip의 nginx 설정 확인
cd /home/ubuntu/darkhorsetip
ls nginx/conf.d/

# 기존 설정이 Docker Compose로 관리되는 경우:
# → 호스트 nginx 설정 파일 직접 수정
sudo nano /etc/nginx/sites-available/darkhorsetip
```

**또는 aitrader 전용 설정 파일 생성:**

```bash
# aitrader nginx 설정 복사
sudo cp /home/ubuntu/aitrader/nginx/aitrader.conf /etc/nginx/sites-available/aitrader

# 도메인 수정
sudo sed -i 's/aitrader.your-domain.com/aitrader.darkhorsetip.com/g' /etc/nginx/sites-available/aitrader

# 심볼릭 링크 생성
sudo ln -s /etc/nginx/sites-available/aitrader /etc/nginx/sites-enabled/

# 설정 검증
sudo nginx -t

# Nginx 재시작
sudo systemctl reload nginx
```

### 6단계: 서비스 시작

```bash
# 서비스 시작
sudo systemctl start aitrader-paper
sudo systemctl start aitrader-dashboard

# 자동 시작 활성화
sudo systemctl enable aitrader-paper
sudo systemctl enable aitrader-dashboard

# 상태 확인
sudo systemctl status aitrader-paper
sudo systemctl status aitrader-dashboard
```

### 7단계: 접속 확인

```
http://your-server-ip:5000
# 또는
https://aitrader.darkhorsetip.com
```

## 📊 서비스 관리 명령어

### 상태 확인
```bash
# 서비스 상태
sudo systemctl status aitrader-paper
sudo systemctl status aitrader-dashboard

# 로그 확인
tail -f ~/aitrader/logs/paper_trading.log
tail -f ~/aitrader/logs/dashboard.log

# Nginx 로그
sudo tail -f /var/log/nginx/aitrader_access.log
sudo tail -f /var/log/nginx/aitrader_error.log
```

### 서비스 제어
```bash
# 시작
sudo systemctl start aitrader-paper
sudo systemctl start aitrader-dashboard

# 중지
sudo systemctl stop aitrader-paper
sudo systemctl stop aitrader-dashboard

# 재시작
sudo systemctl restart aitrader-paper
sudo systemctl restart aitrader-dashboard

# 자동 시작 활성화/비활성화
sudo systemctl enable aitrader-paper
sudo systemctl disable aitrader-paper
```

### 실시간 모니터링
```bash
# 통합 모니터링 대시보드
~/aitrader/scripts/monitor.sh

# 헬스 체크
~/aitrader/scripts/health_check.sh
```

## 🔧 darkhorsetip Nginx와 통합

### 방법 1: 별도 설정 파일 (권장)

darkhorsetip은 Docker Compose nginx, aitrader는 호스트에서 실행:

```nginx
# /etc/nginx/sites-available/aitrader

server {
    listen 80;
    server_name aitrader.darkhorsetip.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name aitrader.darkhorsetip.com;

    ssl_certificate /etc/letsencrypt/live/darkhorsetip.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/darkhorsetip.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/aitrader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 방법 2: 통합 설정

darkhorsetip의 Docker Compose nginx 설정에 추가 - 위에서 만든 `darkhorsetip-default.conf` 참고

## 🔍 트러블슈팅

### 1. 서비스가 시작되지 않음
```bash
# 상세 로그 확인
sudo journalctl -u aitrader-dashboard -n 50 -f

# 가상환경 확인
ls -la ~/aitrader/venv/

# 수동 실행 테스트
cd ~/aitrader
source venv/bin/activate
python simple_dashboard.py
```

### 2. 포트 5000이 사용 중
```bash
# 프로세스 확인
sudo lsof -i :5000

# 프로세스 종료
sudo kill <PID>
```

### 3. Nginx 502 Bad Gateway
```bash
# aitrader 서비스 상태 확인
sudo systemctl status aitrader-dashboard

# 포트 확인
curl http://127.0.0.1:5000

# 방화벽 확인
sudo ufw status
```

### 4. 의존성 오류
```bash
cd ~/aitrader
source venv/bin/activate
pip install -r requirements.txt
```

## 📦 백업 및 유지보수

### 자동 백업
```bash
# 매일 자동 백업 (cron 설정)
crontab -e

# 추가:
0 2 * * * /home/ubuntu/aitrader/scripts/backup.sh
```

### 수동 백업
```bash
~/aitrader/scripts/backup.sh

# 백업 파일 확인
ls -lh ~/aitrader/backups/
```

### 업데이트
```bash
# Git으로 최신 코드 받기
cd ~/aitrader
git pull origin main

# 배포 스크립트 실행
./scripts/deploy.sh
```

## 🎯 최종 구조

```
Oracle Cloud Server
│
├─ darkhorsetip/ (Docker Compose)
│  ├─ MariaDB
│  ├─ WordPress
│  ├─ Nginx (Docker) → Port 80, 443
│  └─ n8n
│
├─ aitrader/ (Systemd Service)
│  ├─ aitrader-paper.service → Python 프로세스
│  └─ aitrader-dashboard.service → Flask (Port 5000)
│
└─ Nginx (Host) → /etc/nginx/sites-available/aitrader
   └─ aitrader.darkhorsetip.com → 127.0.0.1:5000
```

## ✅ 설치 체크리스트

- [ ] 서버 접속 및 코드 업로드
- [ ] `./scripts/quick_start.sh` 실행
- [ ] `.env` 파일 API 키 설정
- [ ] `./scripts/setup_services.sh` 실행
- [ ] Nginx 설정 추가
- [ ] `sudo systemctl start aitrader-*` 서비스 시작
- [ ] 브라우저에서 접속 확인
- [ ] (선택) SSL 인증서 설정
- [ ] (선택) 자동 백업 cron 설정

완료! 🎉

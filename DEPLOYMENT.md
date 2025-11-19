# AI Stock Trader 배포 가이드

Oracle Cloud 서버에 배포하는 최종 가이드입니다.

## 🏗️ 배포 구조

```
Oracle Cloud Server
│
├─ darkhorsetip/ (Docker Compose)
│  ├─ WordPress + MariaDB
│  ├─ n8n
│  └─ Nginx (Docker) ← aitrader.darkhorsetip.com도 여기서 처리
│     ├─ darkhorsetip.com → WordPress
│     ├─ n8n.darkhorsetip.com → n8n:5678
│     └─ aitrader.darkhorsetip.com → host.docker.internal:5000
│
└─ aitrader/ (Systemd Service)
   ├─ aitrader-paper.service (백그라운드 트레이딩)
   └─ aitrader-dashboard.service (Flask 대시보드 :5000)
```

## 🚀 배포 단계

### 1단계: 서버에 코드 업로드

```bash
# 서버 접속
ssh ubuntu@your-oracle-cloud-ip

# Git으로 클론
cd /home/ubuntu
git clone https://github.com/yourusername/aitrader.git
cd aitrader

# 또는 로컬에서 scp로 업로드
# scp -r C:\Project\aitrader ubuntu@server-ip:/home/ubuntu/
```

### 2단계: 자동 환경 설정

```bash
cd /home/ubuntu/aitrader

# 스크립트 실행 권한
chmod +x scripts/*.sh

# 환경 자동 설정 (Python, 가상환경, 의존성)
./scripts/quick_start.sh
```

**자동으로 설치되는 것:**
- ✅ 시스템 업데이트 (apt update & upgrade)
- ✅ Python 3.11
- ✅ 가상환경 생성 (venv/)
- ✅ 모든 의존성 설치 (requirements.txt)
- ✅ 디렉토리 생성 (data, logs, reports, models)
- ✅ 방화벽 설정 (UFW)

### 3단계: API 키 설정

```bash
nano .env
```

**입력:**
```env
# Alpaca API (Paper Trading)
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# 알림 (선택사항)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

저장: `Ctrl+O` → `Enter` → `Ctrl+X`

### 4단계: Systemd 서비스 설치

```bash
./scripts/setup_services.sh
```

**생성되는 서비스:**
- `/etc/systemd/system/aitrader-paper.service`
- `/etc/systemd/system/aitrader-dashboard.service`

### 5단계: 서비스 시작

```bash
# 서비스 시작
sudo systemctl start aitrader-paper
sudo systemctl start aitrader-dashboard

# 부팅 시 자동 시작 설정
sudo systemctl enable aitrader-paper
sudo systemctl enable aitrader-dashboard

# 상태 확인
sudo systemctl status aitrader-paper
sudo systemctl status aitrader-dashboard
```

**정상 실행 확인:**
```bash
# 포트 5000 확인
curl http://localhost:5000

# 로그 확인
tail -f ~/aitrader/logs/paper_trading.log
```

### 6단계: darkhorsetip Nginx 설정 수정

```bash
cd /home/ubuntu/darkhorsetip
nano nginx/conf.d/default.conf
```

**Part 1 수정** - HTTP 리다이렉트에 추가 (6번째 줄):
```nginx
server {
    listen 80;
    server_name darkhorsetip.com www.darkhorsetip.com n8n.darkhorsetip.com aitrader.darkhorsetip.com;
    #                                                  추가 ──────────────────┘
    return 301 https://$host$request_uri;
}
```

**Part 4 추가** - 파일 맨 끝에 추가:
```nginx
# --- Part 4: AI Stock Trader(aitrader.darkhorsetip.com) 요청 처리 ---
server {
    listen 443 ssl http2;
    server_name aitrader.darkhorsetip.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    access_log /var/log/nginx/aitrader_access.log;
    error_log /var/log/nginx/aitrader_error.log;

    client_max_body_size 10M;

    location / {
        proxy_pass http://host.docker.internal:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /health {
        proxy_pass http://host.docker.internal:5000/health;
        access_log off;
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

### 7단계: docker-compose.yml 수정

```bash
nano docker-compose.yml
```

**webserver 섹션에 `extra_hosts` 추가:**
```yaml
  webserver:
    image: nginx:1.25-alpine
    container_name: darkhorsetip-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - wp_content:/var/www/html
      - ./nginx/conf.d/default.conf:/etc/nginx/conf.d/default.conf
      - ./nginx/ssl:/etc/nginx/ssl
    extra_hosts:                          # ← 이 부분 추가!
      - "host.docker.internal:host-gateway"
    networks:
      - app-network
```

### 8단계: Nginx 재시작

```bash
cd /home/ubuntu/darkhorsetip

# Docker Compose nginx 재시작
docker-compose restart webserver

# 로그 확인
docker-compose logs -f webserver
```

### 9단계: 접속 확인 ✅

```
https://aitrader.darkhorsetip.com
```

**로그인 정보:**
- Username: `admin`
- Password: `password123`

## 📊 서비스 관리

### 상태 확인
```bash
# 서비스 상태
sudo systemctl status aitrader-paper
sudo systemctl status aitrader-dashboard

# 프로세스 확인
ps aux | grep python | grep aitrader

# 포트 확인
sudo lsof -i :5000
```

### 로그 확인
```bash
# aitrader 앱 로그
tail -f ~/aitrader/logs/paper_trading.log
tail -f ~/aitrader/logs/dashboard.log

# Systemd 로그
sudo journalctl -u aitrader-dashboard -n 50 -f

# Nginx 로그 (Docker 컨테이너 내부)
docker exec -it darkhorsetip-nginx tail -f /var/log/nginx/aitrader_access.log
docker exec -it darkhorsetip-nginx tail -f /var/log/nginx/aitrader_error.log
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
sudo systemctl restart aitrader-dashboard

# 자동 시작 활성화/비활성화
sudo systemctl enable aitrader-paper
sudo systemctl disable aitrader-paper
```

### 모니터링
```bash
# 통합 모니터링 대시보드
~/aitrader/scripts/monitor.sh

# 헬스 체크
~/aitrader/scripts/health_check.sh

# 백업
~/aitrader/scripts/backup.sh
```

## 🔍 트러블슈팅

### 1. 502 Bad Gateway

**증상:** `https://aitrader.darkhorsetip.com` 접속 시 502 오류

**원인 1:** aitrader-dashboard 서비스가 실행되지 않음
```bash
sudo systemctl status aitrader-dashboard
sudo systemctl start aitrader-dashboard
```

**원인 2:** 포트 5000이 열리지 않음
```bash
curl http://localhost:5000
# 응답 없으면 수동 실행으로 테스트
cd ~/aitrader
source venv/bin/activate
python simple_dashboard.py
```

**원인 3:** Docker에서 host.docker.internal 접근 불가
```bash
# docker-compose.yml에 extra_hosts 추가 확인
docker-compose config | grep extra_hosts

# 없으면 6-7단계 다시 수행
```

### 2. 서비스가 시작되지 않음

```bash
# 상세 로그 확인
sudo journalctl -u aitrader-dashboard -n 100 --no-pager

# 가상환경 확인
ls -la ~/aitrader/venv/bin/python

# 권한 확인
ls -la ~/aitrader/main.py
chmod +x ~/aitrader/main.py

# 수동 실행 테스트
cd ~/aitrader
source venv/bin/activate
python main.py --mode paper --symbols AAPL --daemon
```

### 3. 의존성 오류

```bash
cd ~/aitrader
source venv/bin/activate
pip install -r requirements.txt

# 특정 패키지 재설치
pip install --force-reinstall yfinance pandas
```

### 4. 포트 충돌

```bash
# 포트 5000 사용 프로세스 확인
sudo lsof -i :5000

# 프로세스 종료
sudo kill -9 <PID>
```

### 5. Nginx 로그 확인

```bash
# Docker 컨테이너 접속
docker exec -it darkhorsetip-nginx sh

# 로그 확인
tail -f /var/log/nginx/aitrader_error.log

# host.docker.internal 확인
ping host.docker.internal  # 작동 안 하면 extra_hosts 추가 필요
```

## 🔄 업데이트 및 재배포

```bash
cd ~/aitrader

# Git에서 최신 코드 받기
git pull origin main

# 자동 배포 스크립트
./scripts/deploy.sh
```

**deploy.sh가 자동으로:**
1. 최신 코드 가져오기
2. 가상환경 활성화
3. 의존성 업데이트
4. 디렉토리 권한 설정
5. .env 파일 확인
6. 서비스 재시작
7. 상태 확인

## 📦 백업 설정

### 자동 백업 (Cron)

```bash
crontab -e

# 매일 새벽 2시 백업
0 2 * * * /home/ubuntu/aitrader/scripts/backup.sh

# 매주 일요일 2시 백업
0 2 * * 0 /home/ubuntu/aitrader/scripts/backup.sh
```

### 수동 백업

```bash
~/aitrader/scripts/backup.sh

# 백업 파일 확인
ls -lh ~/aitrader/backups/
```

## ✅ 배포 체크리스트

- [ ] 서버 접속 및 코드 업로드
- [ ] `./scripts/quick_start.sh` 실행 완료
- [ ] `.env` 파일에 API 키 입력
- [ ] `./scripts/setup_services.sh` 실행 완료
- [ ] `sudo systemctl start aitrader-*` 서비스 시작
- [ ] `sudo systemctl enable aitrader-*` 자동 시작 설정
- [ ] darkhorsetip nginx 설정 수정 (Part 1, Part 4)
- [ ] docker-compose.yml에 extra_hosts 추가
- [ ] `docker-compose restart webserver` 완료
- [ ] `https://aitrader.darkhorsetip.com` 접속 확인
- [ ] 로그인 확인 (admin/password123)
- [ ] Paper trading 동작 확인
- [ ] 백업 cron 설정 (선택)

## 🎯 최종 접속 정보

- **URL:** https://aitrader.darkhorsetip.com
- **로그인:** admin / password123
- **대시보드:** 실시간 포트폴리오 + 성과 확인
- **보고서:** 백테스트 결과 확인

---

배포 완료! 🎉 성공적인 트레이딩 되세요! 📈

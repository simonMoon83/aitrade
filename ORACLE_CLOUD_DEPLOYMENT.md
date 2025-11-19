# 오라클 클라우드 배포 가이드

AI 주식 트레이더를 Oracle Cloud Infrastructure (OCI)에 배포하는 상세 가이드입니다.

## 목차
1. [사전 준비](#사전-준비)
2. [OCI 인스턴스 생성](#oci-인스턴스-생성)
3. [서버 환경 설정](#서버-환경-설정)
4. [애플리케이션 배포](#애플리케이션-배포)
5. [자동 실행 설정](#자동-실행-설정)
6. [모니터링 및 유지보수](#모니터링-및-유지보수)

---

## 사전 준비

### 1. 필요한 정보
- Oracle Cloud 계정
- Alpaca API 키 (라이브/페이퍼 트레이딩용)
- SSH 키 페어 (인스턴스 접속용)

### 2. 로컬에서 테스트
```bash
# 백테스트 실행
python main.py --mode backtest --symbols AAPL,MSFT --start 2024-01-01 --end 2024-12-31

# 페이퍼 트레이딩 테스트
python main.py --mode paper --symbols AAPL,MSFT
```

---

## OCI 인스턴스 생성

### 1. 무료 티어 인스턴스 생성

1. **OCI 콘솔 접속**
   - https://cloud.oracle.com 로그인
   - 서울 리전 선택 권장

2. **컴퓨트 인스턴스 생성**
   - Compute > Instances > Create Instance
   - 이름: `ai-trader-server`
   - 이미지: **Ubuntu 22.04** (권장)
   - Shape: **VM.Standard.A1.Flex** (무료 티어)
     - OCPU: 2개
     - Memory: 12GB
   - 또는: **VM.Standard.E2.1.Micro** (무료 티어)
     - OCPU: 1개
     - Memory: 1GB (메모리 부족 가능)

3. **네트워크 설정**
   - VCN: 기본 VCN 사용
   - 공용 IP 할당: **체크**
   - SSH 키: 기존 키 사용 또는 새로 생성

4. **보안 규칙 설정**
   ```
   Ingress Rules:
   - Port 22 (SSH): 0.0.0.0/0
   - Port 5000 (Flask): 본인 IP만 허용 (보안 권장)
   - Port 80 (HTTP): 0.0.0.0/0 (선택)
   - Port 443 (HTTPS): 0.0.0.0/0 (선택)
   ```

### 2. SSH 접속 확인
```bash
# Windows (PowerShell/CMD)
ssh -i path\to\your\key.pem ubuntu@<PUBLIC_IP>

# Linux/Mac
chmod 600 ~/path/to/key.pem
ssh -i ~/path/to/key.pem ubuntu@<PUBLIC_IP>
```

---

## 서버 환경 설정

### 1. 시스템 업데이트
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Python 3.11 설치
```bash
# Python 3.11 설치
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# pip 설치
sudo apt install -y python3-pip

# Python 3.11을 기본으로 설정 (선택)
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

### 3. 필수 패키지 설치
```bash
sudo apt install -y git build-essential libssl-dev libffi-dev
```

### 4. 방화벽 설정 (Ubuntu UFW)
```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 5000/tcp  # Flask (필요시)
sudo ufw enable
sudo ufw status
```

---

## 시간대 설정 (중요!)

### 1. 시스템 시간대 확인
```bash
# 현재 시간대 확인
date
timedatectl

# 출력 예시:
# Time zone: Etc/UTC (UTC, +0000)
```

### 2. 오라클 클라우드 시간 정책
- **기본 설정**: 모든 인스턴스는 UTC 시간대 사용
- **변경 금지**: 시간대를 변경하지 마세요 (시스템 안정성)
- **해결 방법**: 애플리케이션 레벨에서 시간대 처리

### 3. aitrader 시간 처리
본 프로젝트는 **pytz 라이브러리**를 사용하여 자동으로 시간대를 처리합니다:
- UTC → 미국 동부시간(EST/EDT) 자동 변환
- 썸머타임(Daylight Saving Time) 자동 적용
- 서버 시간대 변경 불필요

### 4. 시간 확인 방법
```bash
# 서버 시간 (UTC)
date

# Python으로 미국 동부시간 확인
python3 << EOF
import pytz
from datetime import datetime
utc_now = datetime.now(pytz.UTC)
et_now = utc_now.astimezone(pytz.timezone('US/Eastern'))
print(f"UTC: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"Eastern: {et_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"Market Status: {'Open' if 9 <= et_now.hour < 16 and et_now.weekday() < 5 else 'Closed'}")
EOF
```

### 5. 썸머타임 정보
- **EDT (Eastern Daylight Time)**: UTC-4, 3월 두 번째 일요일 ~ 11월 첫 번째 일요일
- **EST (Eastern Standard Time)**: UTC-5, 11월 첫 번째 일요일 ~ 3월 두 번째 일요일

| 기간 | 시간대 | UTC 오프셋 | 미국 장시간 (UTC) |
|------|--------|-----------|-------------------|
| 서머타임 (3~11월) | EDT | UTC-4 | 13:30 - 20:00 |
| 표준시 (11~3월) | EST | UTC-5 | 14:30 - 21:00 |

### 6. 장시간 체크 테스트
```bash
cd ~/aitrader
source venv/bin/activate

# 장시간 체크 테스트
python3 << EOF
import sys
sys.path.insert(0, '/home/ubuntu/aitrader')

from live_trading.paper_trader import PaperTrader
from config import *

trader = PaperTrader(['AAPL'], INITIAL_CAPITAL)
is_open = trader._is_market_open()
print(f"현재 미국 장 상태: {'개장' if is_open else '휴장'}")
EOF
```

---

## 애플리케이션 배포

### 1. 프로젝트 업로드

#### 옵션 A: Git 사용 (권장)
```bash
# 프로젝트를 GitHub에 푸시한 후
cd ~
git clone https://github.com/YOUR_USERNAME/aitrader.git
cd aitrader
```

#### 옵션 B: SCP로 직접 업로드
```bash
# 로컬 PC에서 실행
scp -i path\to\key.pem -r C:\Project\aitrader ubuntu@<PUBLIC_IP>:~/
```

### 2. 가상 환경 생성
```bash
cd ~/aitrader
python3.11 -m venv venv
source venv/bin/activate
```

### 3. 의존성 설치
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 환경 변수 설정
```bash
# .env 파일 생성
nano .env
```

**.env 파일 내용:**
```env
# Alpaca API
ALPACA_API_KEY=your_actual_api_key_here
ALPACA_SECRET_KEY=your_actual_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # 페이퍼 트레이딩
# ALPACA_BASE_URL=https://api.alpaca.markets      # 라이브 트레이딩

# 대시보드 인증
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=your_secure_password_here

# 텔레그램 알림 (선택)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 로깅
LOG_LEVEL=INFO
```

**저장:** `Ctrl+O` → Enter → `Ctrl+X`

### 5. 권한 설정
```bash
chmod 600 .env
mkdir -p logs reports data models
chmod 755 main.py
```

---

## 자동 실행 설정

### 1. Systemd 서비스 생성 (권장)

#### A. 페이퍼 트레이딩 서비스
```bash
sudo nano /etc/systemd/system/aitrader-paper.service
```

```ini
[Unit]
Description=AI Stock Trader - Paper Trading
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/aitrader
Environment="PATH=/home/ubuntu/aitrader/venv/bin"
ExecStart=/home/ubuntu/aitrader/venv/bin/python main.py --mode paper --symbols AAPL,MSFT,GOOGL,AMZN,NVDA,META,TSLA --daemon
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/aitrader/logs/paper_trading.log
StandardError=append:/home/ubuntu/aitrader/logs/paper_trading_error.log

[Install]
WantedBy=multi-user.target
```

#### B. 대시보드 서비스
```bash
sudo nano /etc/systemd/system/aitrader-dashboard.service
```

```ini
[Unit]
Description=AI Stock Trader Dashboard
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/aitrader
Environment="PATH=/home/ubuntu/aitrader/venv/bin"
Environment="FLASK_APP=simple_dashboard.py"
ExecStart=/home/ubuntu/aitrader/venv/bin/python simple_dashboard.py
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/aitrader/logs/dashboard.log
StandardError=append:/home/ubuntu/aitrader/logs/dashboard_error.log

[Install]
WantedBy=multi-user.target
```

### 2. 서비스 활성화 및 시작
```bash
# 서비스 리로드
sudo systemctl daemon-reload

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

### 3. 서비스 관리 명령어
```bash
# 시작
sudo systemctl start aitrader-paper

# 중지
sudo systemctl stop aitrader-paper

# 재시작
sudo systemctl restart aitrader-paper

# 로그 확인
sudo journalctl -u aitrader-paper -f

# 또는 직접 로그 파일 확인
tail -f ~/aitrader/logs/paper_trading.log
```

---

## Nginx 리버스 프록시 설정 (선택)

### 1. Nginx 설치
```bash
sudo apt install -y nginx
```

### 2. Nginx 설정
```bash
sudo nano /etc/nginx/sites-available/aitrader
```

```nginx
server {
    listen 80;
    server_name your_domain.com;  # 또는 PUBLIC_IP

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 보안 헤더
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

### 3. Nginx 활성화
```bash
sudo ln -s /etc/nginx/sites-available/aitrader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 4. 방화벽 업데이트
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

---

## SSL 인증서 설정 (선택, HTTPS)

### 1. Let's Encrypt 설치
```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 2. SSL 인증서 발급
```bash
sudo certbot --nginx -d your_domain.com
```

### 3. 자동 갱신 설정
```bash
sudo certbot renew --dry-run
```

---

## 모니터링 및 유지보수

### 1. 로그 모니터링
```bash
# 실시간 로그 확인
tail -f ~/aitrader/logs/paper_trading.log
tail -f ~/aitrader/logs/dashboard.log

# 최근 에러 확인
tail -100 ~/aitrader/logs/paper_trading_error.log

# 시스템 로그
sudo journalctl -u aitrader-paper -n 100
```

### 2. 시스템 리소스 모니터링
```bash
# CPU, 메모리 사용량
htop

# 디스크 사용량
df -h

# 네트워크 연결
sudo netstat -tulpn | grep python
```

### 3. 로그 로테이션 설정
```bash
sudo nano /etc/logrotate.d/aitrader
```

```
/home/ubuntu/aitrader/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0644 ubuntu ubuntu
}
```

### 4. 자동 백업 스크립트
```bash
nano ~/backup_aitrader.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 데이터 백업
tar -czf $BACKUP_DIR/aitrader_data_$DATE.tar.gz \
    ~/aitrader/data \
    ~/aitrader/reports \
    ~/aitrader/logs \
    ~/aitrader/.env

# 7일 이상 된 백업 삭제
find $BACKUP_DIR -name "aitrader_data_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/aitrader_data_$DATE.tar.gz"
```

```bash
chmod +x ~/backup_aitrader.sh

# 크론잡으로 매일 자정 백업
crontab -e
```

```cron
0 0 * * * /home/ubuntu/backup_aitrader.sh >> /home/ubuntu/backup.log 2>&1
```

---

## 문제 해결 (Troubleshooting)

### 1. 서비스가 시작되지 않음
```bash
# 상세 로그 확인
sudo journalctl -u aitrader-paper -xe

# 수동 실행으로 에러 확인
cd ~/aitrader
source venv/bin/activate
python main.py --mode paper --symbols AAPL
```

### 2. 메모리 부족 (1GB 인스턴스)
```bash
# 스왑 메모리 추가
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 확인
free -h
```

### 3. 포트 접근 불가
```bash
# 방화벽 확인
sudo ufw status

# OCI 보안 리스트 확인
# OCI 콘솔 > Networking > Virtual Cloud Networks > Security Lists
```

### 4. API 키 오류
```bash
# .env 파일 확인
cat ~/aitrader/.env

# 환경 변수 로드 확인
source ~/aitrader/venv/bin/activate
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('ALPACA_API_KEY'))"
```

### 5. 시간대 관련 문제
```bash
# 증상: 장시간에도 거래가 실행되지 않음

# 해결 1: pytz 설치 확인
pip list | grep pytz

# 해결 2: 수동으로 설치
pip install pytz

# 해결 3: 시간 로그 확인
tail -f ~/aitrader/logs/paper_trading.log | grep "시간 체크"

# 해결 4: 수동 테스트
python3 -c "import pytz; from datetime import datetime; et = datetime.now(pytz.UTC).astimezone(pytz.timezone('US/Eastern')); print(f'ET: {et.strftime(\"%Y-%m-%d %H:%M:%S %Z\")}')"

# 해결 5: 현재 장 상태 확인
cd ~/aitrader
source venv/bin/activate
python3 << EOF
import pytz
from datetime import datetime
et = datetime.now(pytz.UTC).astimezone(pytz.timezone('US/Eastern'))
is_market_hours = (et.hour > 9 or (et.hour == 9 and et.minute >= 30)) and et.hour < 16
is_weekday = et.weekday() < 5
print(f"현재 시각(ET): {et.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"요일: {['월','화','수','목','금','토','일'][et.weekday()]}")
print(f"장시간 여부: {is_market_hours and is_weekday}")
EOF
```

---

## 성능 최적화

### 1. Python 최적화
```bash
# PyPy 사용 (선택, 일부 라이브러리 호환성 이슈 가능)
# 더 빠른 실행 속도
sudo apt install pypy3
```

### 2. 데이터베이스 최적화
- 거래 내역이 많아지면 SQLite 대신 PostgreSQL 사용 고려

### 3. 캐싱 활성화
- Redis 설치로 API 호출 캐싱

---

## 보안 권장사항

### 1. SSH 보안 강화
```bash
sudo nano /etc/ssh/sshd_config
```

```
# 비밀번호 로그인 비활성화
PasswordAuthentication no

# 루트 로그인 비활성화
PermitRootLogin no

# 포트 변경 (선택)
Port 2222
```

```bash
sudo systemctl restart sshd
```

### 2. Fail2ban 설치
```bash
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 3. 자동 업데이트 설정
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 라이브 트레이딩 전환 (주의!)

### 실전 거래로 전환하기 전 체크리스트:

1. ✅ 페이퍼 트레이딩에서 최소 1개월 이상 테스트
2. ✅ 전략 수익률이 안정적으로 플러스
3. ✅ 모든 에러 로그 확인 및 수정
4. ✅ 자금 관리 파라미터 재확인 (config.py)
5. ✅ Stop-loss, Take-profit 설정 확인

### 라이브 전환:
```bash
# .env 파일 수정
nano ~/aitrader/.env
```

```env
# 실전 API로 변경
ALPACA_BASE_URL=https://api.alpaca.markets
```

```bash
# 서비스 재시작
sudo systemctl restart aitrader-paper
```

---

## 유용한 명령어 모음

```bash
# 프로젝트 업데이트
cd ~/aitrader && git pull && sudo systemctl restart aitrader-paper

# 로그 실시간 모니터링
tail -f ~/aitrader/logs/*.log

# 디스크 정리
sudo apt autoremove -y
sudo apt autoclean

# 시스템 상태 한눈에 보기
sudo systemctl status aitrader-*

# 긴급 중지
sudo systemctl stop aitrader-paper aitrader-dashboard
```

---

## 추가 리소스

- [Oracle Cloud 무료 티어](https://www.oracle.com/cloud/free/)
- [Alpaca API 문서](https://alpaca.markets/docs/)
- [Systemd 문서](https://www.freedesktop.org/software/systemd/man/systemd.service.html)

---

## 지원

문제가 발생하면:
1. 로그 파일 확인
2. GitHub Issues 등록
3. 커뮤니티 포럼 질문

**배포 성공을 기원합니다! 🚀**

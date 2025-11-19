# Nginx 설정 가이드

AI Stock Trader를 기존 Nginx 서버에 추가하는 방법입니다.

## 📋 전제조건

- Nginx가 이미 설치되어 있어야 합니다
- 포트 5000이 사용 가능해야 합니다
- (선택) 도메인 또는 서브도메인 설정 완료

## 🚀 빠른 설치

### 방법 1: 자동 스크립트 사용 (권장)

```bash
cd /home/ubuntu/aitrader
chmod +x scripts/setup_nginx.sh
./scripts/setup_nginx.sh
```

스크립트가 자동으로:
1. ✅ Nginx 설치 확인
2. ✅ 도메인 입력 받기
3. ✅ 설정 파일 생성 및 활성화
4. ✅ Nginx 설정 검증
5. ✅ Nginx 재시작
6. ✅ 방화벽 포트 확인

### 방법 2: 수동 설치

```bash
# 1. 설정 파일 복사
sudo cp nginx/aitrader.conf /etc/nginx/sites-available/aitrader

# 2. 도메인 수정
sudo nano /etc/nginx/sites-available/aitrader
# server_name을 실제 도메인으로 변경

# 3. 심볼릭 링크 생성
sudo ln -s /etc/nginx/sites-available/aitrader /etc/nginx/sites-enabled/

# 4. 설정 검증
sudo nginx -t

# 5. Nginx 재시작
sudo systemctl reload nginx
```

## 🌐 접속 방법

### HTTP 접속
```
http://your-domain.com
http://your-server-ip
```

### HTTPS 접속 (SSL 인증서 발급 후)
```bash
# Let's Encrypt SSL 인증서 발급
sudo certbot --nginx -d your-domain.com

# 이후 자동으로 HTTPS 설정됨
https://your-domain.com
```

## 📁 파일 구조

```
aitrader/
├── nginx/
│   ├── aitrader.conf          # Nginx 설정 파일 (sites-available에 복사)
│   ├── conf.d/                # Docker용 nginx 설정
│   │   └── default.conf
│   └── ssl/                   # Docker용 SSL 인증서
└── scripts/
    └── setup_nginx.sh         # 자동 설치 스크립트
```

## 🔧 설정 상세

### 프록시 설정
- **Dashboard**: `http://127.0.0.1:5000` → `http://your-domain.com`
- **Reports**: `/home/ubuntu/aitrader/reports/` → `http://your-domain.com/reports/`
- **Health Check**: `http://your-domain.com/health`

### 보안 헤더
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Referrer-Policy (HTTPS)

### 로그 위치
- Access log: `/var/log/nginx/aitrader_access.log`
- Error log: `/var/log/nginx/aitrader_error.log`

## 🔍 트러블슈팅

### 1. 포트 5000이 사용 중인 경우
```bash
# 포트 사용 확인
sudo lsof -i :5000

# 프로세스 종료
sudo kill <PID>
```

### 2. Nginx 설정 오류
```bash
# 설정 검증
sudo nginx -t

# 상세 로그 확인
sudo tail -f /var/log/nginx/error.log
```

### 3. 서비스가 실행되지 않는 경우
```bash
# aitrader 서비스 상태 확인
sudo systemctl status aitrader-paper
sudo systemctl status aitrader-dashboard

# 서비스 시작
sudo systemctl start aitrader-paper
sudo systemctl start aitrader-dashboard
```

### 4. 방화벽 문제
```bash
# UFW 상태 확인
sudo ufw status

# 포트 열기
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

## 🔐 SSL 인증서 설정

### Let's Encrypt (무료)
```bash
# certbot 설치 (Ubuntu)
sudo apt install -y certbot python3-certbot-nginx

# 인증서 발급 및 자동 설정
sudo certbot --nginx -d your-domain.com

# 자동 갱신 테스트
sudo certbot renew --dry-run
```

인증서가 발급되면 nginx 설정 파일의 HTTPS 섹션이 자동으로 활성화됩니다.

## 📊 모니터링

### 실시간 로그 확인
```bash
# Access log
sudo tail -f /var/log/nginx/aitrader_access.log

# Error log
sudo tail -f /var/log/nginx/aitrader_error.log
```

### Nginx 상태 확인
```bash
sudo systemctl status nginx
```

### 연결 상태 확인
```bash
sudo netstat -tulpn | grep nginx
```

## 🔄 설정 변경 후

```bash
# 설정 검증
sudo nginx -t

# 설정 다시 로드 (다운타임 없음)
sudo systemctl reload nginx

# 완전 재시작
sudo systemctl restart nginx
```

## 📌 darkhorsetip과 함께 사용

darkhorsetip과 동일한 서버에서 실행하는 경우:

```
darkhorsetip.com         → 워드프레스 (포트 80, 443)
n8n.darkhorsetip.com     → n8n 자동화 (포트 80, 443)
aitrader.darkhorsetip.com → AI Stock Trader (포트 80, 443)
                           → 백엔드: 포트 5000
```

모두 독립적으로 동작하며 서로 영향을 주지 않습니다!

# AI Trader → darkhorsetip Nginx에 추가하기

기존 darkhorsetip의 nginx 설정에 aitrader를 추가하는 가이드입니다.

## 📋 현재 구조

```
darkhorsetip/
├── docker-compose.yml
│   ├── db (MariaDB)
│   ├── wordpress
│   ├── webserver (nginx) ← 여기에 추가!
│   └── n8n
└── nginx/
    ├── conf.d/
    │   └── default.conf  ← 이 파일 수정
    └── ssl/
        ├── cert.pem
        └── key.pem
```

## 🚀 적용 방법

### 방법 1: 수동 수정 (권장)

#### 1단계: 기존 파일 백업
```bash
cd ~/darkhorsetip
cp nginx/conf.d/default.conf nginx/conf.d/default.conf.backup
```

#### 2단계: default.conf 수정
```bash
nano nginx/conf.d/default.conf
```

**수정 내용:**

**Part 1 수정** - HTTP 리다이렉트에 aitrader 추가:
```nginx
server {
    listen 80;
    server_name darkhorsetip.com www.darkhorsetip.com n8n.darkhorsetip.com aitrader.darkhorsetip.com;
    #                                                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^
    #                                                                      이 부분 추가!
    return 301 https://$host$request_uri;
}
```

**Part 4 추가** - aitrader HTTPS 설정 (파일 맨 끝에 추가):
```nginx
# --- Part 4: AI Stock Trader(aitrader.darkhorsetip.com) 요청 처리 ---
server {
    listen 443 ssl http2;
    server_name aitrader.darkhorsetip.com;

    # SSL 설정: 동일한 와일드카드 인증서(*.darkhorsetip.com) 사용
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    # 로그 설정
    access_log /var/log/nginx/aitrader_access.log;
    error_log /var/log/nginx/aitrader_error.log;

    # 보안: 큰 파일 업로드 제한
    client_max_body_size 10M;

    location / {
        # 호스트 서버의 포트 5000으로 프록시 (aitrader 대시보드)
        proxy_pass http://host.docker.internal:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 타임아웃 설정
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # 웹소켓 지원 (실시간 업데이트용)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 헬스 체크 엔드포인트
    location /health {
        proxy_pass http://host.docker.internal:5000/health;
        access_log off;
    }

    # 보안 헤더
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

#### 3단계: Docker Compose에서 host 네트워크 접근 허용

**Option A: extra_hosts 추가 (권장)**

`~/darkhorsetip/docker-compose.yml`의 webserver 섹션에 추가:

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

**Option B: network_mode 사용**

또는 간단하게 host 네트워크 사용:

```yaml
  webserver:
    image: nginx:1.25-alpine
    container_name: darkhorsetip-nginx
    restart: always
    network_mode: "host"  # ← 이렇게 변경
    volumes:
      - wp_content:/var/www/html
      - ./nginx/conf.d/default.conf:/etc/nginx/conf.d/default.conf
      - ./nginx/ssl:/etc/nginx/ssl
```

#### 4단계: Nginx 재시작
```bash
cd ~/darkhorsetip
docker-compose restart webserver

# 로그 확인
docker-compose logs -f webserver
```

#### 5단계: aitrader 서비스 시작
```bash
cd ~/aitrader

# Systemd로 시작
sudo systemctl start aitrader-paper
sudo systemctl start aitrader-dashboard

# 또는 수동 실행
python main.py --mode paper --symbols AAPL,MSFT,GOOGL --daemon
python simple_dashboard.py
```

#### 6단계: 접속 테스트
```
https://aitrader.darkhorsetip.com
```

### 방법 2: 전체 파일 교체

aitrader 프로젝트의 `nginx/darkhorsetip-default.conf` 파일을 복사:

```bash
cd ~/aitrader
cp nginx/darkhorsetip-default.conf ~/darkhorsetip/nginx/conf.d/default.conf

# Nginx 재시작
cd ~/darkhorsetip
docker-compose restart webserver
```

## 🔍 트러블슈팅

### 1. 502 Bad Gateway 오류

**원인**: aitrader 서비스(포트 5000)가 실행되지 않음

**해결**:
```bash
# 서비스 상태 확인
sudo systemctl status aitrader-dashboard

# 포트 확인
sudo lsof -i :5000

# 수동 실행 테스트
cd ~/aitrader
python simple_dashboard.py
```

### 2. host.docker.internal 연결 실패

**원인**: Docker 컨테이너가 호스트 네트워크에 접근 못함

**해결**: docker-compose.yml에 `extra_hosts` 추가 (위 3단계 참고)

### 3. SSL 인증서 오류

**원인**: 와일드카드 인증서(*.darkhorsetip.com)가 필요

**해결**:
```bash
# 와일드카드 인증서 발급 (certbot)
sudo certbot certonly --manual --preferred-challenges dns \
  -d darkhorsetip.com -d *.darkhorsetip.com
```

### 4. 로그 확인

```bash
# Nginx 컨테이너 로그
docker-compose logs -f webserver

# 컨테이너 내부 로그
docker exec -it darkhorsetip-nginx tail -f /var/log/nginx/aitrader_error.log

# aitrader 앱 로그
tail -f ~/aitrader/logs/paper_trading.log
```

## 📊 최종 구조

```
서비스                          포트                        접속 URL
───────────────────────────────────────────────────────────────────────
WordPress                       80, 443                     https://darkhorsetip.com
n8n                            5678 (내부)                  https://n8n.darkhorsetip.com
AI Stock Trader                5000 (호스트)                https://aitrader.darkhorsetip.com
```

모든 서비스가 **동일한 nginx 컨테이너**를 통해 라우팅됩니다!

## 🔐 보안 체크리스트

- [x] HTTPS 강제 리다이렉트
- [x] 보안 헤더 추가
- [x] 로그 분리 (aitrader_access.log, aitrader_error.log)
- [x] 파일 업로드 크기 제한 (10M)
- [x] robots.txt (크롤링 방지)
- [x] 웹소켓 지원 (실시간 업데이트)

## 📌 참고

- 완전한 설정 예시: `nginx/darkhorsetip-default.conf`
- aitrader 단독 설정: `nginx/aitrader.conf`
- 자동 설치 스크립트: `scripts/setup_nginx.sh`

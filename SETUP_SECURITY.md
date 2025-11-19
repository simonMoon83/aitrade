# 🔐 보안 설정 가이드

## Flask Secret Key 설정하기

Flask Secret Key는 **세션 쿠키 암호화**와 **CSRF 보호**를 위해 반드시 필요합니다.

---

## 🚀 빠른 설정 (3분)

### 1단계: Secret Key 생성

#### 방법 A: Python으로 생성 (권장)
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**출력 예시:**
```
a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

#### 방법 B: OpenSSL로 생성
```bash
openssl rand -hex 32
```

#### 방법 C: 온라인 생성기
- https://randomkeygen.com/
- "CodeIgniter Encryption Keys" 섹션 사용

---

### 2단계: .env 파일에 추가

#### .env 파일이 없으면 생성:
```bash
cp env.example .env
```

#### .env 파일 편집:
```bash
nano .env
# 또는
vim .env
# 또는 텍스트 에디터로 열기
```

#### 생성한 키를 추가:
```bash
# .env 파일 내용

# 웹 대시보드 인증
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=your_secure_password_here

# Flask Secret Key (방금 생성한 키로 변경!)
FLASK_SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

⚠️ **주의**: 반드시 생성한 키로 변경하세요! 예시 키를 그대로 사용하지 마세요!

---

### 3단계: 확인

서버 재시작 후 로그 확인:
```bash
# 대시보드 재시작
sudo systemctl restart aitrader-dashboard

# 로그 확인
journalctl -u aitrader-dashboard -n 20
```

Python에서 확인:
```python
python -c "from config import FLASK_SECRET_KEY; print('✅ Key loaded!' if FLASK_SECRET_KEY else '❌ Key missing!')"
```

---

## 🔒 보안 모범 사례

### ✅ 해야 할 것
```
1. 64자 이상의 랜덤 문자열 사용
2. 각 환경(개발/운영)마다 다른 키 사용
3. .env 파일을 .gitignore에 추가 (절대 커밋 금지!)
4. 키를 정기적으로 변경 (3-6개월마다)
5. 백업 시 .env 파일 포함
```

### ❌ 하지 말아야 할 것
```
1. 예측 가능한 값 사용 ('password', '123456' 등)
2. 코드에 하드코딩
3. Git에 커밋
4. 다른 사람과 공유
5. 공개 서버에 동일한 키 사용
```

---

## 🛠 자동 설정 스크립트

### setup_secret_key.sh 생성
```bash
#!/bin/bash
# Flask Secret Key 자동 설정 스크립트

echo "🔐 Flask Secret Key 설정"
echo "========================"

# Secret Key 생성
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

echo "생성된 Secret Key:"
echo "$SECRET_KEY"
echo ""

# .env 파일 확인
if [ ! -f .env ]; then
    echo "📝 .env 파일이 없습니다. env.example을 복사합니다..."
    cp env.example .env
fi

# Secret Key 추가/업데이트
if grep -q "FLASK_SECRET_KEY=" .env; then
    echo "📝 기존 FLASK_SECRET_KEY를 업데이트합니다..."
    sed -i "s|FLASK_SECRET_KEY=.*|FLASK_SECRET_KEY=$SECRET_KEY|" .env
else
    echo "📝 FLASK_SECRET_KEY를 추가합니다..."
    echo "" >> .env
    echo "# Flask Secret Key (자동 생성됨)" >> .env
    echo "FLASK_SECRET_KEY=$SECRET_KEY" >> .env
fi

echo ""
echo "✅ Flask Secret Key가 설정되었습니다!"
echo "⚠️  .env 파일을 안전하게 보관하세요!"
```

### 사용법:
```bash
chmod +x setup_secret_key.sh
./setup_secret_key.sh
```

---

## 🔄 키 변경하기 (로그아웃됨)

Secret Key를 변경하면 **모든 사용자가 로그아웃**됩니다.

### 방법:
```bash
# 1. 새 키 생성
NEW_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# 2. .env 파일 업데이트
sed -i "s|FLASK_SECRET_KEY=.*|FLASK_SECRET_KEY=$NEW_KEY|" .env

# 3. 서비스 재시작
sudo systemctl restart aitrader-dashboard
```

---

## 🚨 키 유출 시 긴급 조치

만약 Secret Key가 유출되었다면:

### 즉시 조치:
```bash
# 1. 새 키로 즉시 변경
python -c "import secrets; print(secrets.token_hex(32))" > /tmp/new_key
NEW_KEY=$(cat /tmp/new_key)
sed -i "s|FLASK_SECRET_KEY=.*|FLASK_SECRET_KEY=$NEW_KEY|" .env
rm /tmp/new_key

# 2. 서비스 재시작
sudo systemctl restart aitrader-dashboard

# 3. 비밀번호 변경
# .env 파일에서 DASHBOARD_PASSWORD도 변경

# 4. 로그 확인
journalctl -u aitrader-dashboard -n 50 | grep "login"
```

### 사후 조치:
```
1. Git 히스토리에서 키 제거
2. 다른 API 키들도 확인
3. 접근 로그 확인
4. 필요시 서버 재설정
```

---

## 🧪 테스트

### 설정 확인:
```python
# test_secret_key.py
import os
from config import FLASK_SECRET_KEY

def test_secret_key():
    # 키가 설정되었는지 확인
    assert FLASK_SECRET_KEY is not None, "❌ Secret Key가 설정되지 않았습니다!"
    
    # 키 길이 확인 (최소 32자)
    assert len(FLASK_SECRET_KEY) >= 32, "❌ Secret Key가 너무 짧습니다!"
    
    # 예시 키가 아닌지 확인
    forbidden = ['your_flask_secret', 'password', '123456', 'test']
    for word in forbidden:
        assert word not in FLASK_SECRET_KEY.lower(), f"❌ 안전하지 않은 키입니다: {word}"
    
    print("✅ Secret Key가 올바르게 설정되었습니다!")
    print(f"   길이: {len(FLASK_SECRET_KEY)} 문자")

if __name__ == "__main__":
    test_secret_key()
```

### 실행:
```bash
python test_secret_key.py
```

---

## 📚 추가 보안 권장사항

### 1. 대시보드 비밀번호 강화
```bash
# .env 파일
DASHBOARD_PASSWORD=$(python -c "import secrets; print(secrets.token_urlsafe(16))")
```

### 2. HTTPS 사용 (운영 환경)
```nginx
# nginx 설정
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:5000;
    }
}
```

### 3. IP 화이트리스트 (선택사항)
```python
# config.py
ALLOWED_IPS = ['127.0.0.1', '192.168.1.0/24']
```

### 4. Rate Limiting
```python
# 로그인 시도 제한
MAX_LOGIN_ATTEMPTS = 5
LOGIN_COOLDOWN = 300  # 5분
```

---

## ❓ FAQ

### Q: Secret Key를 잊어버렸어요!
**A:** 괜찮습니다. 새로 생성하면 됩니다. 단, 모든 사용자가 로그아웃됩니다.

### Q: 여러 서버에서 같은 키를 사용해도 되나요?
**A:** 아니요! 각 서버마다 다른 키를 사용하세요.

### Q: 키를 얼마나 자주 변경해야 하나요?
**A:** 3-6개월마다 권장합니다. 유출 의심 시 즉시 변경하세요.

### Q: 백업 시 .env 파일도 포함해야 하나요?
**A:** 네, 반드시 포함하세요. 단, 안전한 곳에 암호화하여 보관하세요.

### Q: 개발 환경과 운영 환경에서 같은 키를 사용해도 되나요?
**A:** 절대 안됩니다! 반드시 다른 키를 사용하세요.

---

## 📞 문제 해결

### 로그인이 안 돼요
```bash
# 1. 키가 로드되었는지 확인
python -c "from config import FLASK_SECRET_KEY; print(FLASK_SECRET_KEY)"

# 2. 서비스 재시작
sudo systemctl restart aitrader-dashboard

# 3. 브라우저 쿠키 삭제 후 다시 시도
```

### "Bad session" 오류
```bash
# Secret Key가 변경되었거나 없습니다
# 1. .env 파일 확인
cat .env | grep FLASK_SECRET_KEY

# 2. 키가 없으면 생성
python -c "import secrets; print(secrets.token_hex(32))"

# 3. .env에 추가 후 재시작
```

---

## 🔗 관련 문서

- `env.example` - 환경변수 예시
- `config.py` - 설정 파일
- `dashboard/web_dashboard.py` - Flask 앱

---

**작성일:** 2025-11-07  
**버전:** 1.0  
**보안 등급:** 🔴 중요

⚠️ 이 문서의 보안 권장사항을 반드시 따르세요!



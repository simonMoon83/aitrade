# 대시보드 API 테스트 가이드

## 🚀 빠른 시작

### 1. 대시보드 접속
```bash
# 브라우저에서
http://localhost:5000

# 또는 원격 서버에서
http://your-server-ip:5000
```

### 2. 로그인
```
ID: admin (또는 config.py의 DASHBOARD_USERNAME)
PW: admin123 (또는 config.py의 DASHBOARD_PASSWORD)
```

---

## 🔍 새로운 API 테스트

### 1. 시스템 진단 API

#### 요청
```bash
curl -X GET http://localhost:5000/api/diagnostics \
  -H "Content-Type: application/json" \
  --cookie "session=your-session-cookie"
```

#### 응답 예시
```json
{
  "status": "WARNING",
  "summary": "일부 문제가 감지되었습니다",
  "timestamp": "2025-11-07T...",
  "issues": [
    {
      "severity": "HIGH",
      "category": "SIGNALS",
      "message": "오늘 생성된 거래 신호가 없습니다",
      "suggestion": "전략 파라미터를 완화하거나 데이터 수집 상태를 확인하세요"
    }
  ],
  "warnings": [],
  "info": [],
  "signal_analysis": {
    "total_signals": 0,
    "today_signals": 0,
    "buy_signals": 0,
    "sell_signals": 0,
    "hold_signals": 0
  },
  "system_status": {
    "trader_running": true,
    "trades_today": 0
  }
}
```

#### 상태 코드 의미
- `HEALTHY`: 모든 시스템 정상
- `OK`: 경미한 경고가 있지만 정상
- `WARNING`: 일부 문제 발견 (조치 권장)
- `CRITICAL`: 긴급 조치 필요

---

### 2. 시장 상태 API

#### 요청
```bash
curl -X GET http://localhost:5000/api/market/status \
  -H "Content-Type: application/json" \
  --cookie "session=your-session-cookie"
```

#### 응답 예시 (장 개장 시)
```json
{
  "us_time": "2025-11-07 10:30:00 EST/EDT",
  "korea_time": "2025-11-07 00:30:00 KST",
  "is_market_open": true,
  "is_weekend": false,
  "market_open": "09:30",
  "market_close": "16:00",
  "time_to_close": "5:30:00",
  "time_to_open": null
}
```

#### 응답 예시 (장 마감 후)
```json
{
  "us_time": "2025-11-07 18:00:00 EST/EDT",
  "korea_time": "2025-11-08 08:00:00 KST",
  "is_market_open": false,
  "is_weekend": false,
  "market_open": "09:30",
  "market_close": "16:00",
  "time_to_close": null,
  "time_to_open": "15:30:00"
}
```

---

### 3. 신호 분석 API (개선됨)

#### 요청
```bash
curl -X GET http://localhost:5000/api/signals \
  -H "Content-Type: application/json" \
  --cookie "session=your-session-cookie"
```

#### 응답 예시
```json
{
  "signals": [
    {
      "timestamp": "2025-11-06 14:30:00",
      "level": "INFO",
      "message": "AAPL - BUY 신호 생성 (신뢰도: 0.65)",
      "signal_type": "BUY",
      "symbol": "AAPL",
      "source": "paper_trader_20251106.log",
      "date": "20251106"
    }
  ],
  "total": 15,
  "buy_count": 8,
  "sell_count": 5,
  "hold_count": 2,
  "no_signals": false
}
```

---

### 4. 전략 파라미터 조회 API

#### 요청
```bash
curl -X GET http://localhost:5000/api/strategy/parameters \
  -H "Content-Type: application/json" \
  --cookie "session=your-session-cookie"
```

#### 응답 예시
```json
{
  "confidence_threshold": 0.35,
  "buy_signal_threshold": 3.0,
  "sell_signal_threshold": 2.5,
  "rsi_oversold": 30,
  "rsi_overbought": 70,
  "volume_threshold": 1.3
}
```

---

## 🧪 Python으로 테스트

### 설치
```bash
pip install requests
```

### 테스트 스크립트
```python
import requests

# 1. 로그인
session = requests.Session()
login_data = {
    'username': 'admin',
    'password': 'admin123'
}
response = session.post('http://localhost:5000/login', data=login_data)
print(f"로그인: {response.status_code}")

# 2. 시스템 진단
diag = session.get('http://localhost:5000/api/diagnostics').json()
print(f"\n시스템 상태: {diag['status']}")
print(f"요약: {diag['summary']}")
print(f"문제 개수: {len(diag['issues'])}")

for issue in diag['issues']:
    print(f"  - [{issue['severity']}] {issue['message']}")

# 3. 시장 상태
market = session.get('http://localhost:5000/api/market/status').json()
print(f"\n시장 개장: {market['is_market_open']}")
print(f"미국 시간: {market['us_time']}")
print(f"한국 시간: {market['korea_time']}")

# 4. 신호 분석
signals = session.get('http://localhost:5000/api/signals').json()
print(f"\n총 신호: {signals['total']}")
print(f"BUY: {signals['buy_count']}, SELL: {signals['sell_count']}, HOLD: {signals['hold_count']}")

# 5. 전략 파라미터
params = session.get('http://localhost:5000/api/strategy/parameters').json()
print(f"\n전략 파라미터:")
for key, value in params.items():
    print(f"  {key}: {value}")
```

---

## 📊 브라우저에서 테스트

### 1. 개발자 도구 열기 (F12)

### 2. Console에서 실행
```javascript
// 시스템 진단
fetch('/api/diagnostics')
  .then(r => r.json())
  .then(data => console.log('진단:', data));

// 시장 상태
fetch('/api/market/status')
  .then(r => r.json())
  .then(data => console.log('시장:', data));

// 신호 분석
fetch('/api/signals')
  .then(r => r.json())
  .then(data => console.log('신호:', data));

// 전략 파라미터
fetch('/api/strategy/parameters')
  .then(r => r.json())
  .then(data => console.log('파라미터:', data));
```

---

## 🔧 문제 해결

### 1. "Unauthorized" 오류
```bash
# 해결: 먼저 로그인하세요
# 브라우저에서 http://localhost:5000/login 접속 후 로그인
```

### 2. "Connection refused" 오류
```bash
# 해결: 대시보드가 실행 중인지 확인
sudo systemctl status aitrader-dashboard

# 또는 수동 실행
python -m dashboard.web_dashboard
```

### 3. 진단 API에서 "trader_running: null"
```bash
# 해결: systemctl 권한 설정
sudo visudo
# 추가: www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl
```

---

## 📈 실전 활용 예시

### 아침 체크리스트 자동화
```bash
#!/bin/bash
# morning_check.sh

echo "=== 일일 시스템 체크 ==="

# 1. 시장 상태
echo -e "\n[시장 상태]"
curl -s http://localhost:5000/api/market/status | jq '.is_market_open'

# 2. 시스템 진단
echo -e "\n[시스템 진단]"
curl -s http://localhost:5000/api/diagnostics | jq '.status, .summary'

# 3. 어제 거래
echo -e "\n[어제 거래]"
curl -s http://localhost:5000/api/performance | jq '.daily_trades'

# 4. 신호 통계
echo -e "\n[신호 통계]"
curl -s http://localhost:5000/api/signals | jq '.total, .buy_count, .sell_count'
```

### cron으로 자동 실행
```bash
# 매일 오전 9시에 체크
0 9 * * * /path/to/morning_check.sh >> /var/log/morning_check.log
```

---

## 💡 활용 팁

### 1. 거래 신호 모니터링
```bash
# 5분마다 신호 확인
watch -n 300 'curl -s http://localhost:5000/api/signals | jq ".total, .buy_count"'
```

### 2. 시장 개장 알림
```python
import requests
import time

while True:
    market = requests.get('http://localhost:5000/api/market/status').json()
    if market['is_market_open']:
        print("🔔 미국 시장이 개장했습니다!")
        # 여기에 알림 로직 추가 (텔레그램, 이메일 등)
        break
    time.sleep(300)  # 5분마다 체크
```

### 3. 문제 발생 시 자동 알림
```python
import requests

diag = requests.get('http://localhost:5000/api/diagnostics').json()

if diag['status'] in ['CRITICAL', 'WARNING']:
    # 알림 전송
    print(f"⚠️ 주의: {diag['summary']}")
    for issue in diag['issues']:
        print(f"  - {issue['message']}")
        print(f"    💡 {issue['suggestion']}")
```

---

## 📞 추가 도움말

- API 문서: `dashboard/web_dashboard.py` 파일 참조
- 로그 확인: `logs/web_dashboard_YYYYMMDD.log`
- 시스템 로그: `journalctl -u aitrader-dashboard -f`

---

**마지막 업데이트:** 2025-11-07



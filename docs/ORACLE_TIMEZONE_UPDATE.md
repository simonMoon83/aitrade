# 오라클 클라우드 시간대 업데이트 가이드

오라클 클라우드 서버에서 UTC 시간대 및 썸머타임 자동 적용을 위한 업데이트 가이드입니다.

## 📋 업데이트 내용

### 변경 사항
1. **requirements.txt**: pytz 라이브러리 추가
2. **paper_trader.py**: `_is_market_open()` 함수를 UTC 기준으로 수정 (썸머타임 자동 적용)
3. **ORACLE_CLOUD_DEPLOYMENT.md**: 시간대 설정 가이드 추가

### 주요 개선사항
- ✅ UTC 시간대 완벽 지원
- ✅ 썸머타임(EDT/EST) 자동 전환
- ✅ 주말 자동 감지
- ✅ 상세 디버깅 로그 추가

---

## 🚀 오라클 클라우드 서버 적용 방법

### 1단계: SSH 접속
```bash
# Windows PowerShell 또는 Linux/Mac 터미널에서
ssh -i path/to/your/key.pem ubuntu@<YOUR_PUBLIC_IP>
```

### 2단계: 프로젝트 업데이트

#### 옵션 A: Git 사용 (권장)
```bash
cd ~/aitrader
git pull origin main  # 또는 master
```

#### 옵션 B: 파일 직접 업로드
```bash
# 로컬 PC에서 실행 (별도 터미널)
scp -i path/to/key.pem -r C:\Project\aitrader\requirements.txt ubuntu@<YOUR_IP>:~/aitrader/
scp -i path/to/key.pem -r C:\Project\aitrader\live_trading\paper_trader.py ubuntu@<YOUR_IP>:~/aitrader/live_trading/
scp -i path/to/key.pem -r C:\Project\aitrader\ORACLE_CLOUD_DEPLOYMENT.md ubuntu@<YOUR_IP>:~/aitrader/
```

### 3단계: 가상환경 활성화 및 pytz 설치
```bash
cd ~/aitrader
source venv/bin/activate

# pytz 설치
pip install pytz

# 또는 전체 requirements 재설치
pip install -r requirements.txt --upgrade
```

### 4단계: 시간 설정 확인
```bash
# 서버 시간 확인 (UTC여야 함)
date
timedatectl

# Python으로 미국 동부시간 확인
python3 << EOF
import pytz
from datetime import datetime
utc_now = datetime.now(pytz.UTC)
et_now = utc_now.astimezone(pytz.timezone('US/Eastern'))
print(f"서버 시간(UTC): {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"미국 동부시간(ET): {et_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"현재 시간대: {et_now.tzname()}")  # EST 또는 EDT
print(f"장 상태: {'개장' if (9 <= et_now.hour < 16 or (et_now.hour == 9 and et_now.minute >= 30)) and et_now.weekday() < 5 else '휴장'}")
EOF
```

**예상 출력:**
```
서버 시간(UTC): 2025-11-03 08:10:00 UTC
미국 동부시간(ET): 2025-11-03 03:10:00 EST
현재 시간대: EST
장 상태: 휴장
```

### 5단계: 장시간 체크 테스트
```bash
# 실제 코드로 테스트
python3 << EOF
import sys
sys.path.insert(0, '/home/ubuntu/aitrader')

from live_trading.paper_trader import PaperTrader
from config import *

# 테스트 트레이더 생성
trader = PaperTrader(['AAPL'], INITIAL_CAPITAL)

# 장시간 확인
is_open = trader._is_market_open()
print(f"\n=== 장시간 체크 결과 ===")
print(f"현재 미국 장 상태: {'✅ 개장' if is_open else '❌ 휴장'}")
print(f"========================\n")
EOF
```

### 6단계: 서비스 재시작
```bash
# 페이퍼 트레이딩 서비스 재시작
sudo systemctl restart aitrader-paper

# 대시보드 서비스 재시작 (선택)
sudo systemctl restart aitrader-dashboard

# 상태 확인
sudo systemctl status aitrader-paper
```

### 7단계: 로그 모니터링
```bash
# 실시간 로그 확인 (새 터미널)
tail -f ~/aitrader/logs/paper_trading.log

# 시간 체크 로그만 필터링
tail -f ~/aitrader/logs/paper_trading.log | grep "시간 체크"

# 또는 systemd 로그
sudo journalctl -u aitrader-paper -f
```

**정상 작동 시 로그 예시:**
```
2025-11-03 03:15:00 - paper_trader - DEBUG - 시간 체크 - UTC: 08:15:00, ET: 03:15:00 EST, 장개장: False
2025-11-03 03:15:30 - paper_trader - INFO - 장 마감 시간입니다.
```

---

## ✅ 검증 체크리스트

업데이트가 제대로 적용되었는지 확인하세요:

- [ ] `pip list | grep pytz` 실행 시 pytz가 보임
- [ ] 시간 확인 스크립트에서 UTC와 ET 시간이 모두 표시됨
- [ ] ET 시간대가 EST 또는 EDT로 표시됨 (시즌에 따라)
- [ ] 장시간 체크 테스트가 정상 작동
- [ ] 서비스 재시작 후 에러 없음
- [ ] 로그에 "시간 체크" 메시지가 표시됨

---

## 📊 시간대 참고표

### 현재 시간 (2025년 11월 3일 기준)
- **시간대**: EST (Eastern Standard Time)
- **UTC 오프셋**: -5시간
- **장시간 (UTC)**: 14:30 - 21:00

### 썸머타임 전환 일정
| 년도 | DST 시작 | DST 종료 |
|------|----------|----------|
| 2025 | 3월 9일 (일) | 11월 2일 (일) ✅ 종료됨 |
| 2026 | 3월 8일 (일) | 11월 1일 (일) |

### 장시간 매트릭스
| 시간대 | UTC 오프셋 | 미국 장 개장 (ET) | UTC 시간 |
|--------|-----------|------------------|----------|
| EDT (서머타임) | UTC-4 | 09:30 - 16:00 | 13:30 - 20:00 |
| EST (표준시) | UTC-5 | 09:30 - 16:00 | 14:30 - 21:00 |

---

## 🔍 문제 해결

### 문제 1: pytz를 찾을 수 없음
```bash
# 해결
pip install pytz

# 확인
python3 -c "import pytz; print('✅ pytz 설치 완료')"
```

### 문제 2: 시간대가 맞지 않음
```bash
# 서버 시간대 확인
timedatectl

# UTC가 아니면 시스템 관리자에게 문의
# (일반적으로 오라클 클라우드는 UTC 고정)
```

### 문제 3: 장시간인데 거래가 안됨
```bash
# 디버그 로그 레벨 확인
cd ~/aitrader
nano config.py
# LOG_LEVEL = "DEBUG" 로 변경

# 서비스 재시작
sudo systemctl restart aitrader-paper

# 로그 확인
tail -f ~/aitrader/logs/paper_trading.log
```

### 문제 4: 서비스가 시작되지 않음
```bash
# 상세 에러 확인
sudo journalctl -u aitrader-paper -xe

# 수동 실행으로 에러 확인
cd ~/aitrader
source venv/bin/activate
python main.py --mode paper --symbols AAPL
```

---

## 📝 추가 정보

### 수동으로 현재 장 상태 확인
```bash
# 간단한 원라이너
python3 -c "import pytz; from datetime import datetime as dt; et=dt.now(pytz.UTC).astimezone(pytz.timezone('US/Eastern')); print(f'ET: {et:%H:%M %Z} | 장: {\"개장\" if 9*60+30<=et.hour*60+et.minute<16*60 and et.weekday()<5 else \"휴장\"}')"
```

### cron으로 주기적 시간 체크
```bash
# 매시간 시간 확인
crontab -e

# 추가
0 * * * * cd ~/aitrader && source venv/bin/activate && python3 -c "import pytz; from datetime import datetime; et=datetime.now(pytz.UTC).astimezone(pytz.timezone('US/Eastern')); print(f'{datetime.now():%Y-%m-%d %H:%M} | ET: {et:%H:%M %Z}')" >> ~/aitrader/logs/time_check.log
```

### Docker 환경인 경우
```bash
# 컨테이너 재시작
docker-compose restart aitrader-paper

# 컨테이너 내부에서 테스트
docker exec -it aitrader-paper python3 -c "import pytz; from datetime import datetime; print(datetime.now(pytz.timezone('US/Eastern')))"
```

---

## 🎯 다음 단계

업데이트 완료 후:

1. **1-2일 모니터링**: 로그를 확인하여 시간대가 올바르게 작동하는지 검증
2. **장 개장 시 확인**: 실제 장시간에 거래가 실행되는지 확인
3. **3월/11월 전환기**: 썸머타임 전환 시기에 자동으로 전환되는지 확인

---

## 📞 지원

문제가 발생하면:
1. 위의 문제 해결 섹션 참조
2. 로그 파일 확인: `~/aitrader/logs/`
3. GitHub Issues에 로그와 함께 문의

**업데이트 성공을 기원합니다! 🚀**


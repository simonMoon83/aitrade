# 🚀 빠른 시작 가이드

## 📌 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [설치 방법](#설치-방법)
3. [사용 방법](#사용-방법)
4. [추천 워크플로우](#추천-워크플로우)

---

## 프로젝트 개요

AI 기반 자동 트레이딩 시스템입니다.
- ✅ 주식 백테스트
- ✅ 암호화폐 백테스트  
- ✅ Paper Trading (모의투자)
- ⏳ Live Trading (실전투자 - 준비 중)

---

## 설치 방법

```bash
# 1. 저장소 클론 (이미 완료)
cd C:\Project\aitrader

# 2. 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate

# 3. 필요한 패키지 설치
pip install -r requirements.txt

# 4. 환경 변수 설정
copy env.example .env
# .env 파일을 열어서 Alpaca API 키 입력
```

---

## 사용 방법

### 🔥 가장 중요한 3가지 명령어

#### 1. 주식 백테스트 실행
```bash
python scripts/backtest_stocks.py
```
**결과 위치:** `results/backtests/stock_*.csv`

#### 2. 암호화폐 백테스트 실행
```bash
python scripts/backtest_crypto.py
```
**결과 위치:** `results/backtests/crypto_*.csv`

#### 3. Paper Trading 실행 (⭐ 가장 중요!)
```bash
# 대시보드와 함께 실행
python scripts/paper_trade.py --dashboard

# 접속: http://localhost:5000
# 로그인: admin / password123
```

---

## 추천 워크플로우

### 📅 1주차: 백테스트로 전략 검증

```bash
# 주식 백테스트
python scripts/backtest_stocks.py

# 암호화폐 백테스트
python scripts/backtest_crypto.py

# 결과 분석
# results/backtests/ 폴더의 CSV 파일 확인
```

**확인 사항:**
- ✅ 수익률 10% 이상
- ✅ 승률 50% 이상
- ✅ 최대 낙폭 -20% 이하
- ✅ 샤프 비율 1.0 이상

---

### 📅 2~12주차: Paper Trading으로 실전 검증

```bash
# Paper Trading 시작
python scripts/paper_trade.py --dashboard
```

**매일 확인:**
- 대시보드에서 성과 모니터링
- 백테스트 vs 실제 성과 비교
- 슬리피지 및 체결 실패율 확인

**중요! Paper Trading 최소 기간:**
- 최소: 1개월
- 권장: 3개월
- 안전: 6개월

---

### 📅 13주차 이후: 실전 투자 (소액)

⚠️ **주의:** Paper Trading에서 충분한 검증 후에만 진행!

```bash
# 아직 구현 안 됨
# python scripts/live_trade.py
```

**실전 투자 체크리스트:**
- [ ] Paper Trading 3개월 이상 완료
- [ ] 실전 데이터 분석 완료
- [ ] 전략 파라미터 최적화 완료
- [ ] 손실 감수 가능 금액만 투자
- [ ] $100~1,000 소액으로 시작

---

## 📁 폴더 구조

```
aitrader/
├── scripts/              ⭐ 실행 스크립트
│   ├── backtest_stocks.py   # 주식 백테스트
│   ├── backtest_crypto.py   # 암호화폐 백테스트
│   ├── paper_trade.py       # 모의투자
│   └── live_trade.py        # 실전투자 (준비중)
│
├── strategies/          # 전략 코드
│   ├── improved/        # 개선된 전략 (사용)
│   └── legacy/          # 기존 전략 (참고)
│
├── results/             ⭐ 결과 파일
│   ├── backtests/       # 백테스트 결과
│   ├── paper_trading/   # Paper Trading 로그
│   └── analysis/        # 분석 결과
│
├── config.py            # 설정 파일
├── main.py              # 레거시 실행 파일
└── docs/                # 문서
```

---

## 🎯 현재 상태 요약

### ✅ 완료된 기능
- 주식 백테스트 (2024.06~2025.06)
  - 수익률: **105.46%** 🚀
  - 승률: **88.89%** ✅
  - 샤프 비율: **7.53** 🏆
  
- 암호화폐 백테스트 (2024.06~2025.06)
  - 수익률: **19.31%** 📈
  - 승률: **56.16%** ✅
  - 샤프 비율: **0.94** ⚡

- Paper Trading
  - Alpaca Paper API 연동 ✅
  - 웹 대시보드 ✅
  - 실시간 거래 시뮬레이션 ✅

### ⏳ 다음 단계
1. Paper Trading 1~3개월 실행
2. 실전 데이터 수집 및 분석
3. 전략 파라미터 재최적화
4. 실전 투자 준비

---

## 💡 팁

### 백테스트 vs 실전 차이
```
백테스트 수익률: 100%
실전 예상 수익률: 80~90% ⚠️

이유:
- 슬리피지: -3~5%
- 체결 실패: -2~3%
- 심리적 요인: -5~10%
```

### Paper Trading이 중요한 이유
- ✅ 실제 시장 데이터 사용
- ✅ 슬리피지 실측 가능
- ✅ 비용 $0
- ✅ 리스크 $0
- ✅ 실전 전 필수 검증

---

## 🆘 문제 해결

### Q: 백테스트 실행 시 "ModuleNotFoundError"
```bash
# 가상환경 활성화 확인
venv\Scripts\activate

# 패키지 재설치
pip install -r requirements.txt
```

### Q: Paper Trading 로그인 실패
```
기본 계정: admin
기본 비밀번호: password123

변경하려면 .env 파일에서 DASHBOARD_PASSWORD 설정
```

### Q: 한글이 깨져 보임
```bash
# PowerShell에서 실행 전
chcp 65001
```

---

## 📚 더 알아보기

- [전체 README](../README.md)
- [개선된 전략 설명](../README_IMPROVED.md)
- [웹 대시보드 가이드](../WEB_DASHBOARD_GUIDE.md)
- [Paper Trading 가이드](../PAPER_TRADING_GUIDE.md)

---

## 🎯 다음에 실행할 명령어

```bash
# 지금 바로 Paper Trading 시작!
python scripts/paper_trade.py --dashboard
```

**그 다음:**
1. 웹브라우저에서 http://localhost:5000 접속
2. admin / password123로 로그인
3. 매일 대시보드 확인
4. 1~3개월 후 실전 데이터 분석

---

**🎊 행운을 빕니다! 📈**


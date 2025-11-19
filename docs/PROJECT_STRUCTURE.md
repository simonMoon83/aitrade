# 📁 프로젝트 구조 상세 설명

## 🎯 재구성 완료!

프로젝트가 **프로덕션 기준**으로 깔끔하게 재구성되었습니다.

---

## 📂 폴더 구조

### ⭐ scripts/ - 실행 스크립트 (가장 중요!)

```
scripts/
├── backtest_stocks.py    # 주식 백테스트 실행
├── backtest_crypto.py    # 암호화폐 백테스트 실행
├── paper_trade.py        # Paper Trading 실행
└── live_trade.py         # 실전 투자 (준비중)
```

**사용법:**
```bash
python scripts/backtest_stocks.py     # 주식 백테스트
python scripts/backtest_crypto.py     # 암호화폐 백테스트
python scripts/paper_trade.py --dashboard  # 모의투자
```

---

### 📊 results/ - 결과 파일

```
results/
├── backtests/         # 백테스트 CSV 결과
├── paper_trading/     # Paper Trading 로그
└── analysis/          # 분석 결과
```

모든 백테스트 및 트레이딩 결과가 여기에 저장됩니다.

---

### 🧠 strategies/ - 전략 코드

```
strategies/
├── improved/          # 개선된 전략 (현재 사용 중) ✅
│   └── buy_low_sell_high.py
├── legacy/            # 기존 전략 (참고용)
│   └── buy_low_sell_high.py
└── crypto_strategy.py # 암호화폐 전용 전략
```

---

### 🛠️ utils/ - 유틸리티

```
utils/
├── data_collector.py          # 주식 데이터 수집
├── crypto_data_collector.py   # 암호화폐 데이터 수집
├── feature_engineering.py     # 기술적 지표 추가
├── position_manager.py        # 포지션 관리
├── market_analyzer.py         # 시장 분석
├── logger.py                  # 로깅
└── scheduler.py               # 스케줄링
```

---

### 💼 live_trading/ - 실시간 거래

```
live_trading/
├── paper_trader.py    # Paper Trading 엔진
└── risk_manager.py    # 리스크 관리
```

---

### 🖥️ dashboard/ - 웹 대시보드

```
dashboard/
├── web_dashboard.py   # Flask 대시보드
└── templates/         # HTML 템플릿 (자동 생성)
```

---

### 📚 docs/ - 문서

```
docs/
├── QUICK_START.md         # 빠른 시작 가이드 ⭐
└── PROJECT_STRUCTURE.md   # 이 파일
```

---

### 📦 archive/ - 아카이브

```
archive/
├── test_*.py          # 기존 테스트 파일
├── run_*.py           # 기존 실행 파일
└── *_results/         # 기존 결과 폴더
```

정리된 기존 파일들. 필요 시 참고용으로 사용.

---

## 🎯 파일명 규칙

### 실행 스크립트
- `scripts/` 폴더에 위치
- 명확한 동사 사용: `backtest_`, `paper_trade`, `live_trade`
- Python으로 직접 실행 가능

### 결과 파일
- `results/` 폴더에 저장
- 타임스탬프 포함: `stock_trades_20251031_123456.csv`
- CSV 형식으로 저장

### 설정 파일
- 루트 디렉토리에 `config.py`
- 백업은 `config_files/`에 보관

---

## 🚀 실행 순서

### 1단계: 환경 설정
```bash
# 가상환경 활성화
venv\Scripts\activate

# 환경변수 확인
# .env 파일에 Alpaca API 키 입력
```

### 2단계: 백테스트
```bash
# 주식
python scripts/backtest_stocks.py

# 암호화폐
python scripts/backtest_crypto.py

# 결과 확인
dir results\backtests
```

### 3단계: Paper Trading
```bash
# 대시보드와 함께 실행
python scripts/paper_trade.py --dashboard

# 접속
# http://localhost:5000
# admin / password123
```

### 4단계: 모니터링 (매일)
- 대시보드에서 성과 확인
- 백테스트 vs 실제 비교
- 로그 파일 검토

### 5단계: 분석 (1~3개월 후)
- 실전 데이터 분석
- 전략 최적화
- A/B 테스트

---

## 📝 주요 변경 사항

### Before (기존)
```
❌ test_improved_strategy.py
❌ run_backtest_improved.py
❌ visualize_improved_results.py
❌ improved_results/
❌ crypto_results/
```

### After (현재)
```
✅ scripts/backtest_stocks.py
✅ scripts/backtest_crypto.py
✅ scripts/paper_trade.py
✅ results/backtests/
✅ docs/QUICK_START.md
```

---

## 🎨 네이밍 규칙

### 폴더
- 소문자, 언더스코어
- 복수형: `scripts/`, `results/`, `strategies/`
- 명확한 목적: `paper_trading/`, `backtests/`

### 파일
- 소문자, 언더스코어
- 동사로 시작: `backtest_`, `paper_trade_`
- 목적 명시: `_stocks`, `_crypto`

### 클래스
- PascalCase
- 명사 사용: `StockBacktester`, `CryptoStrategy`

### 함수
- snake_case
- 동사 사용: `run_backtest()`, `get_signal()`

---

## 🔍 파일 찾기

### "백테스트를 실행하고 싶어요"
```bash
python scripts/backtest_stocks.py     # 주식
python scripts/backtest_crypto.py     # 암호화폐
```

### "Paper Trading을 시작하고 싶어요"
```bash
python scripts/paper_trade.py --dashboard
```

### "백테스트 결과를 보고 싶어요"
```
results/backtests/ 폴더의 CSV 파일 확인
```

### "설정을 변경하고 싶어요"
```
config.py 파일 수정
```

### "전략 코드를 보고 싶어요"
```
strategies/improved/buy_low_sell_high.py  # 주식
strategies/crypto_strategy.py             # 암호화폐
```

---

## 💡 팁

### 실행 전 체크리스트
- [ ] 가상환경 활성화
- [ ] .env 파일 설정 확인
- [ ] 필요한 패키지 설치
- [ ] 폴더 구조 확인

### 디버깅
```bash
# 로그 파일 확인
dir logs\*.log

# 최근 로그 보기
type logs\backtest_stocks_*.log | more
```

### 백업
```bash
# 중요! 정기적으로 백업
xcopy results results_backup\ /E /I /Y
xcopy config.py config_backup.py /Y
```

---

## 🎯 다음 단계

1. `docs/QUICK_START.md` 읽기
2. Paper Trading 시작
3. 매일 모니터링
4. 1~3개월 후 데이터 분석

---

**🎊 프로젝트 재구성 완료!**


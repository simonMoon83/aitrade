# 🤖 AI Stock Trader - 자동 주식 트레이딩 시스템

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production_Ready-success.svg)]()
[![Cloud](https://img.shields.io/badge/Cloud-Oracle_Cloud-red.svg)](https://cloud.oracle.com)

> AI 기반 자동 주식 트레이딩 시스템 - 기술적 분석과 머신러닝을 활용한 "저점매수-고점매도" 전략

---

## 🎯 핵심 기능

### ✅ 주식 트레이딩 (2023-2024 백테스트)
- **총 수익률:** 68.61% (2년)
- **연환산 수익률:** 30.05%
- **샤프 비율:** 2.4
- **승률:** 24.39%
- **수익 팩터:** 4.07
- **최대 낙폭:** -6.98%
- **총 거래:** 492건

### ✅ 주요 기능
- 📊 **백테스트**: 역사적 데이터로 전략 검증
- 📈 **페이퍼 트레이딩**: 실전 없이 실시간 시뮬레이션
- 🤖 **라이브 트레이딩**: Alpaca API 연동 실전 거래
- 📱 **웹 대시보드**: 실시간 모니터링
- 🔔 **텔레그램 알림**: 거래 실시간 통지
- ☁️ **클라우드 배포**: Oracle Cloud 무료 티어 지원

---

## 🚀 빠른 시작

### 1. 설치

```bash
# 저장소 클론
git clone https://github.com/yourusername/aitrader.git
cd aitrader

# 가상환경 생성
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 설정

```bash
# .env 파일 생성
copy env.example .env

# .env 파일 편집 (Alpaca API 키 입력)
notepad .env
```

### 3. 실행

```bash
# 주식 백테스트
python scripts/backtest_stocks.py

# 암호화폐 백테스트
python scripts/backtest_crypto.py

# Paper Trading (⭐ 추천!)
python scripts/paper_trade.py --dashboard
```

---

## 📊 사용 방법

### 🔥 실행 명령어

| 작업 | 명령어 | 설명 |
|------|--------|------|
| 📈 백테스트 | `python main.py --mode backtest --symbols AAPL,MSFT --start 2023-01-01 --end 2024-12-31` | 역사적 데이터로 전략 검증 |
| 🎯 페이퍼 트레이딩 | `python main.py --mode paper --symbols AAPL,MSFT,GOOGL --daemon` | 실시간 시뮬레이션 |
| 📱 대시보드 | `python simple_dashboard.py` | http://localhost:5000 |
| ⚠️ 실전 투자 | `python main.py --mode live --symbols AAPL,MSFT --daemon` | 실전 거래 (주의!) |

---

## 📁 프로젝트 구조

```
aitrader/
├── 📁 scripts/              실행 스크립트 ⭐
│   ├── backtest_stocks.py   주식 백테스트
│   ├── backtest_crypto.py   암호화폐 백테스트
│   ├── paper_trade.py       모의투자
│   └── live_trade.py        실전투자 (준비중)
│
├── 📁 strategies/           전략 코드
│   ├── improved/            개선된 전략 (사용 중)
│   └── legacy/              기존 전략 (참고용)
│
├── 📁 results/              결과 파일 ⭐
│   ├── backtests/           백테스트 결과
│   ├── paper_trading/       모의투자 로그
│   └── analysis/            분석 결과
│
├── 📁 utils/                유틸리티
│   ├── data_collector.py    주식 데이터 수집
│   ├── crypto_data_collector.py  암호화폐 데이터
│   ├── feature_engineering.py    기술적 지표
│   ├── position_manager.py  포지션 관리
│   └── market_analyzer.py   시장 분석
│
├── 📁 live_trading/         실시간 거래
│   ├── paper_trader.py      모의투자
│   └── risk_manager.py      리스크 관리
│
├── 📁 dashboard/            웹 대시보드
│   └── web_dashboard.py     Flask 대시보드
│
├── 📁 docs/                 문서 ⭐
│   └── QUICK_START.md       빠른 시작 가이드
│
├── config.py                설정 파일
├── main.py                  레거시 실행 파일
└── README.md                이 파일
```

---

## 💡 추천 워크플로우

### 단계 1: 백테스트 (1주)
```bash
# 전략 검증
python scripts/backtest_stocks.py
python scripts/backtest_crypto.py

# 결과 분석
# - 수익률 확인
# - 승률 확인
# - 최대 낙폭 확인
```

### 단계 2: Paper Trading (1~3개월) ⭐
```bash
# 모의투자 시작
python scripts/paper_trade.py --dashboard

# 매일 확인
# - http://localhost:5000 접속
# - 성과 모니터링
# - 백테스트 vs 실제 비교
```

### 단계 3: 데이터 분석 (1주)
```bash
# 실전 데이터 분석
# - 슬리피지 패턴
# - 체결 실패율
# - 수익률 차이

# 전략 최적화
# - 파라미터 조정
# - A/B 테스트
```

### 단계 4: 실전 투자 (조심스럽게!)
```bash
# ⚠️ 주의: 소액($100~1,000)으로 시작!
python scripts/live_trade.py
```

---

## 📈 성과 비교

### 주식 vs 암호화폐 (2024.06 ~ 2025.06)

| 지표 | 주식 | 암호화폐 | 승자 |
|------|------|----------|------|
| 수익률 | **105.46%** | 19.31% | 🏆 주식 |
| 승률 | **88.89%** | 56.16% | 🏆 주식 |
| 샤프 비율 | **7.53** | 0.94 | 🏆 주식 |
| 최대 낙폭 | **-1.37%** | -12.06% | 🏆 주식 |
| 거래 횟수 | 450회 | 149회 | - |

**결론:** 주식 전략이 압도적으로 우수! 🚀

---

## 🛠️ 핵심 기술

- **머신러닝:** XGBoost, Random Forest
- **기술적 지표:** RSI, MACD, 볼린저밴드, ATR
- **리스크 관리:** 켈리 공식, 동적 손절/익절
- **시장 분석:** VIX, 섹터 로테이션, 시장 강도
- **데이터:** yfinance (무료), Alpaca API
- **대시보드:** Flask, Plotly
- **백테스팅:** 자체 백테스팅 엔진

---

## ⚙️ 설정 파일

`config.py`에서 주요 파라미터 조정:

```python
# 초기 자본
INITIAL_CAPITAL = 10000  # $10,000

# 거래 종목 (주식)
DEFAULT_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "META", "TSLA", "LLY", "V", "IONQ"
]

# 암호화폐
CRYPTO_SYMBOLS = [
    "BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD",
    "ADA/USD", "AVAX/USD", "DOT/USD", "LINK/USD"
]

# 리스크 관리
MAX_POSITION_SIZE = 0.2     # 20%
STOP_LOSS_PCT = 0.03        # 3%
TAKE_PROFIT_PCT = 0.05      # 5%
MAX_POSITIONS = 5           # 최대 5개 종목

# 전략 파라미터
RSI_OVERSOLD = 25
RSI_OVERBOUGHT = 75
MIN_SIGNAL_STRENGTH = 4.5
```

---

## 📊 백테스트 결과

### 주식 포트폴리오 (2024.06 ~ 2025.06)

| 종목 | 거래 횟수 | 총 손익 |
|------|-----------|---------|
| IONQ | 124회 | **$2,952** 🥇 |
| TSLA | 80회 | **$1,685** 🥈 |
| NVDA | 68회 | **$1,466** 🥉 |
| META | 42회 | $978 |
| AMZN | 34회 | $932 |

**총 수익:** $10,546 (105.46%)

### 암호화폐 포트폴리오 (2024.06 ~ 2025.06)

| 코인 | 거래 횟수 | 총 손익 |
|------|-----------|---------|
| XRP | 14회 | **$911** 🥇 |
| SOL | 22회 | **$675** 🥈 |
| LINK | 12회 | **$668** 🥉 |
| DOT | 24회 | $452 |
| AVAX | 22회 | $299 |

**총 수익:** $1,931 (19.31%)

---

## 🔐 보안 및 API

### Alpaca API 설정

1. [Alpaca](https://alpaca.markets) 계정 생성 (무료)
2. Paper Trading API 키 발급
3. `.env` 파일에 입력:

```env
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
```

⚠️ **중요:** 
- Paper Trading은 무료!
- 실전 투자 전 반드시 Paper Trading으로 검증
- API 키는 절대 공개하지 마세요

---

## 📚 문서

- 📖 [빠른 시작 가이드](docs/QUICK_START.md) ⭐
- 📊 [개선된 전략 설명](README_IMPROVED.md)
- 🖥️ [웹 대시보드 가이드](WEB_DASHBOARD_GUIDE.md)
- 📝 [Paper Trading 가이드](PAPER_TRADING_GUIDE.md)

---

## ⚠️ 면책 조항

이 프로젝트는 **교육 및 연구 목적**으로 제공됩니다.

- 투자 결과에 대한 책임은 사용자에게 있습니다
- 실전 투자 전 반드시 Paper Trading으로 충분히 테스트하세요
- 손실을 감당할 수 있는 금액만 투자하세요
- 과거 성과가 미래 수익을 보장하지 않습니다

---

## 🤝 기여

이슈와 Pull Request는 환영합니다!

---

## 📄 라이선스

MIT License

---

## 🎯 다음 단계

```bash
# 지금 바로 시작하세요!
python scripts/paper_trade.py --dashboard
```

**그 다음:**
1. http://localhost:5000 접속
2. admin / password123 로그인
3. 매일 성과 모니터링
4. 1~3개월 후 실전 투자 결정

---

## ☁️ 클라우드 배포

### Oracle Cloud 무료 티어 배포

Oracle Cloud의 무료 티어 (Always Free)를 활용하면 **완전 무료**로 24/7 자동 트레이딩 시스템을 운영할 수 있습니다!

**무료 제공 리소스:**
- VM.Standard.A1.Flex (ARM): 4 OCPU, 24GB RAM
- VM.Standard.E2.1.Micro (x86): 1 OCPU, 1GB RAM
- 200GB 블록 스토리지
- 매월 10TB 아웃바운드 데이터 전송

#### 빠른 배포 (Systemd + Nginx)

```bash
# 1. 서버 초기 설정 (Python, 가상환경, 의존성)
chmod +x scripts/*.sh
./scripts/quick_start.sh

# 2. API 키 설정
nano .env
# ALPACA_API_KEY와 ALPACA_SECRET_KEY 입력

# 3. Systemd 서비스 설치
./scripts/setup_services.sh

# 4. Nginx 설정 추가
./scripts/setup_nginx.sh

# 5. 서비스 시작
sudo systemctl start aitrader-paper
sudo systemctl start aitrader-dashboard
```

#### Docker로 배포 (선택사항)

```bash
# Docker Compose 사용 (Nginx 포함)
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

#### 서비스 관리

```bash
# 서비스 상태 확인
sudo systemctl status aitrader-paper
sudo systemctl status aitrader-dashboard

# 서비스 재시작
sudo systemctl restart aitrader-dashboard

# 실시간 모니터링
./scripts/monitor.sh

# 헬스 체크
./scripts/health_check.sh

# 백업
./scripts/backup.sh

# 로그 확인
tail -f logs/paper_trading.log
sudo tail -f /var/log/nginx/aitrader_access.log
```

#### 상세 문서

- 🚀 **[배포 가이드](DEPLOYMENT.md)** - 최종 배포 가이드 (권장)
- 📖 [Oracle Cloud 상세 가이드](ORACLE_CLOUD_DEPLOYMENT.md) - 전체 배포 프로세스
- 🔧 [Nginx 설정 가이드](nginx/SIMPLE_SETUP.md) - Nginx 통합 방법
- ✅ [배포 체크리스트](DEPLOYMENT_CHECKLIST.md) - 배포 전후 확인사항
- 🐳 [Docker 배포](docker-compose.yml) - 컨테이너 배포 옵션 (선택)

**배포 후 접속:**
- URL: `https://aitrader.your-domain.com`
- 기본 로그인: admin / password123

---

## 📞 문의

문제가 있거나 질문이 있으시면 이슈를 생성해주세요!

**🎊 성공적인 트레이딩 되세요! 📈**

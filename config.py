"""
AI 주식 트레이더 설정 파일
"""
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# =============================================================================
# API 설정
# =============================================================================

# Alpaca API 설정 (모의투자용)
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"  # 모의투자용
# ALPACA_BASE_URL = "https://api.alpaca.markets"  # 실전투자용

# 텔레그램 봇 설정 (선택사항)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Finnhub API 설정 (뉴스 감성 분석용)
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# FRED API 설정 (거시경제 지표용)
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# =============================================================================
# 트레이딩 파라미터
# =============================================================================

# 초기 자본
INITIAL_CAPITAL = 10000  # $10,000

# 포지션 관리
MAX_POSITION_SIZE = 0.2  # 한 종목당 최대 20% (기존 10% -> 20%)
MIN_POSITION_SIZE = 0.01  # 최소 1%
MAX_POSITIONS = 5  # 최대 보유 종목 수

# 리스크 관리 (개선된 값)
USE_ATR_BASED_SL_TP = True  # 고정 % 대신 ATR 기반 손절/익절 사용 여부
ATR_MULTIPLIER_SL = 2.0     # 손절: ATR의 2.0배
ATR_MULTIPLIER_TP = 3.5     # 익절: ATR의 3.5배

STOP_LOSS_PCT = 0.03     # 3% 손절 (ATR 미사용 시 기본값)
TAKE_PROFIT_PCT = 0.05   # 5% 익절 (ATR 미사용 시 기본값)
MAX_DAILY_LOSS = 0.02    # 일일 최대 손실 2%
MAX_WEEKLY_LOSS = 0.05   # 주간 최대 손실 5%
MAX_PORTFOLIO_RISK = 0.06  # 포트폴리오 전체 최대 리스크 6%

# 암호화폐 전용 리스크 관리 (변동성 높으므로 더 넓은 범위)
CRYPTO_STOP_LOSS_PCT = 0.05     # 5% 손절
CRYPTO_TAKE_PROFIT_PCT = 0.10   # 10% 익절
CRYPTO_MAX_POSITION_SIZE = 0.15  # 한 코인당 최대 15%
CRYPTO_MAX_POSITIONS = 5         # 최대 5개 코인

# 켈리 공식 파라미터
TARGET_WIN_RATE = 0.35  # 목표 승률 35%
AVG_WIN_LOSS_RATIO = 2.0  # 평균 수익/손실 비율

# 거래 수수료 (Alpaca는 무료)
COMMISSION = 0.0
SLIPPAGE = 0.001  # 0.1% 슬리피지

# =============================================================================
# 전략 파라미터
# =============================================================================

# 기술적 지표 설정 (개선된 값)
RSI_PERIOD = 14
RSI_OVERSOLD = 25  # 더 엄격한 과매도 (기존 40 -> 25)
RSI_OVERBOUGHT = 75  # 더 엄격한 과매수 (기존 60 -> 75)

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2

MA_SHORT = 20
MA_LONG = 50
MA_LONGER = 200

# 저점/고점 판단 기준
LOW_POINT_DAYS = 10  # 최근 N일 최저가 (기존 5 -> 10)
HIGH_POINT_DAYS = 10  # 최근 N일 최고가 (기존 5 -> 10)
VOLUME_SPIKE_THRESHOLD = 1.5  # 거래량 급증 기준 (평균의 1.5배)

# 추가 전략 파라미터
MIN_HOLDING_DAYS = 3  # 최소 보유 기간
MAX_HOLDING_DAYS = 30  # 최대 보유 기간
MIN_SIGNAL_STRENGTH = 4.5  # 최소 신호 강도 (매수)
MIN_SELL_STRENGTH = 4.0  # 최소 신호 강도 (매도)

# 다이버전스 감지 기간
DIVERGENCE_LOOKBACK = 20  # 다이버전스 확인 기간

# 시장 필터 파라미터
MIN_ADV20 = 1000000  # 최소 일평균 거래대금 ($1M)
MAX_VIX_LEVEL = 35  # VIX 35 이상시 거래 중단
VIX_CAUTION_LEVEL = 25  # VIX 25 이상시 포지션 축소

# 뉴스 감성 분석 파라미터
NEWS_CACHE_HOURS = 1  # 뉴스 캐시 시간 (시간)
NEWS_LOOKBACK_DAYS = 7  # 분석할 뉴스 기간 (일)
NEWS_SENTIMENT_THRESHOLD = 0.3  # 강한 감성 임계값 (-1 ~ 1)
NEWS_BUZZ_THRESHOLD = 1.5  # 뉴스 급증 임계값 (평균 대비)

# 섹터 순환 분석 파라미터
SECTOR_CACHE_HOURS = 6  # 섹터 데이터 캐시 (시간)
SECTOR_TOP_N = 3  # 강세 섹터 판단 기준 (상위 N개)
SECTOR_ANALYSIS_PERIOD = '1mo'  # 섹터 분석 기간

# 거시경제 지표 파라미터
MACRO_CACHE_HOURS = 24  # 거시경제 데이터 캐시 (하루 1회)
MACRO_SCORE_THRESHOLD = 2  # 거시환경 점수 임계값
USE_LOCAL_FINBERT = True  # 로컬 FinBERT 모델 사용 (Finnhub 백업)

# =============================================================================
# 데이터 설정
# =============================================================================

# 기본 거래 종목 (성장주 + 대형주 조합)
DEFAULT_SYMBOLS = [
    "AAPL",  # Apple
    "MSFT",  # Microsoft
    "GOOGL", # Google
    "AMZN",  # Amazon
    "NVDA",  # NVIDIA (AI/반도체)
    "META",  # Meta
    "TSLA",  # Tesla (전기차)
    "LLY",   # Eli Lilly (제약)
    "V",     # Visa (결제)
    "IONQ",  # IonQ (양자컴퓨팅) - 백테스팅 고성과
]

# 암호화폐 종목
CRYPTO_SYMBOLS = [
    "BTC/USD",    # Bitcoin - 암호화폐의 왕
    "ETH/USD",    # Ethereum - 스마트컨트랙트 리더
    "BNB/USD",    # Binance Coin - 거래소 토큰
    "SOL/USD",    # Solana - 고속 블록체인
    "XRP/USD",    # Ripple - 송금 특화
    "ADA/USD",    # Cardano - 학술적 접근
    "AVAX/USD",   # Avalanche - 빠른 합의
    "DOT/USD",    # Polkadot - 체인 연결
    "MATIC/USD",  # Polygon - 이더리움 레이어2
    "LINK/USD",   # Chainlink - 오라클 네트워크
]

# 데이터 수집 기간 (주식 백테스트)
DATA_START_DATE = "2024-06-01"
DATA_END_DATE = "2025-06-30"

# 암호화폐 백테스트 기간
CRYPTO_START_DATE = "2024-06-01"
CRYPTO_END_DATE = "2025-06-30"

# =============================================================================
# 서버 설정
# =============================================================================

# 웹 대시보드
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000
DASHBOARD_DEBUG = False

# Flask Secret Key (세션 암호화용 - 반드시 .env에 설정 필요!)
# 생성 방법: python -c "import secrets; print(secrets.token_hex(32))"
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", None)

# 로깅
LOG_LEVEL = "INFO"
LOG_FILE = "logs/trader.log"

# =============================================================================
# 스케줄링
# =============================================================================

# 미국 장 시간 (한국 시간 기준)
MARKET_OPEN_HOUR = 23  # 23:30 (서머타임: 22:30)
MARKET_CLOSE_HOUR = 6  # 06:00 (서머타임: 05:00)

# 백테스팅 주기
BACKTEST_UPDATE_HOUR = 2  # 매일 새벽 2시

# =============================================================================
# 보안 설정
# =============================================================================

# 웹 대시보드 인증
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "password123")

# API 키 암호화
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "your-secret-key-here")

# =============================================================================
# 파일 경로
# =============================================================================

# 데이터 저장 경로
DATA_DIR = "data"
MODELS_DIR = "models"
LOGS_DIR = "logs"
REPORTS_DIR = "reports"

# 백테스팅 결과 저장
BACKTEST_RESULTS_DIR = "backtest_results"

# =============================================================================
# 머신러닝 모델 설정
# =============================================================================

# 모델 파라미터
MODEL_TYPE = "xgboost"  # "random_forest" 또는 "xgboost"
TRAIN_TEST_SPLIT = 0.8
CROSS_VALIDATION_FOLDS = 5

# 특성 선택
FEATURE_IMPORTANCE_THRESHOLD = 0.01

# =============================================================================
# 알림 설정
# =============================================================================

# 알림 임계값
PROFIT_ALERT_THRESHOLD = 0.05  # 5% 수익 시 알림
LOSS_ALERT_THRESHOLD = -0.03   # 3% 손실 시 알림

# 일일 요약 시간
DAILY_SUMMARY_HOUR = 7  # 오전 7시 (장 마감 후)

# =============================================================================
# AI 레포트 생성 설정 (Gemini API)
# =============================================================================

# Gemini API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash-exp"  # 모델명

# 일일 레포트 설정
ENABLE_DAILY_REPORT = True  # 일일 레포트 생성 여부
DAILY_REPORT_HOUR = 7  # 레포트 생성 시간 (오전 7시, 장 마감 후)
REPORTS_SAVE_DIR = "reports/daily"  # 일일 레포트 저장 경로


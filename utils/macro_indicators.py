"""
거시경제 지표 추적 모듈
FRED API와 yfinance를 사용하여 거시경제 환경 평가
"""

import yfinance as yf
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# FRED API 임포트 (선택사항)
try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False

from config import *
from utils.logger import setup_logger

logger = setup_logger("macro_indicators")


class MacroIndicatorTracker:
    """거시경제 지표 추적 클래스"""
    
    def __init__(self, fred_api_key: str = ""):
        """
        초기화
        
        Args:
            fred_api_key (str): FRED API 키
        """
        self.fred_api_key = fred_api_key
        self.fred_client = None
        
        # 캐시
        self.cache = None
        self.cache_time = None
        self.cache_duration = MACRO_CACHE_HOURS * 3600  # 초 단위
        
        # FRED 클라이언트 초기화
        if FRED_AVAILABLE and fred_api_key:
            try:
                self.fred_client = Fred(api_key=fred_api_key)
                logger.info("FRED API 클라이언트 초기화 완료")
            except Exception as e:
                logger.warning(f"FRED API 초기화 실패: {str(e)}")
                self.fred_client = None
        else:
            if not FRED_AVAILABLE:
                logger.warning("fredapi 패키지가 설치되지 않았습니다")
            elif not fred_api_key:
                logger.info("FRED API 키가 설정되지 않았습니다 (기본 지표만 사용)")
    
    def get_current_indicators(self) -> Dict:
        """
        현재 거시경제 지표 수집
        
        Returns:
            Dict: {
                'treasury_10y': 10년 국채 수익률 (%),
                'treasury_trend': 금리 추세 ('RISING', 'FALLING', 'STABLE'),
                'unemployment_rate': 실업률 (%) - FRED 필요,
                'unemployment_trend': 실업률 추세 - FRED 필요,
                'cpi_yoy': 전년 대비 인플레이션 (%) - FRED 필요,
                'gdp_growth': GDP 성장률 (%) - FRED 필요,
                'fed_funds_rate': 연준 기준금리 (%) - FRED 필요,
                'consumer_sentiment': 소비자 신뢰지수 - FRED 필요,
                'vix': VIX 지수
            }
        """
        indicators = {}
        
        # 1. 10년 국채 수익률 (yfinance - 무료)
        try:
            treasury_10y = yf.Ticker("^TNX")
            tnx_data = treasury_10y.history(period="1mo")
            
            if not tnx_data.empty:
                indicators['treasury_10y'] = tnx_data['Close'].iloc[-1]
                indicators['treasury_trend'] = self._calc_trend(tnx_data['Close'])
                logger.info(f"10년 국채 수익률: {indicators['treasury_10y']:.2f}% ({indicators['treasury_trend']})")
            else:
                indicators['treasury_10y'] = 4.0  # 기본값
                indicators['treasury_trend'] = 'STABLE'
        except Exception as e:
            logger.warning(f"국채 수익률 가져오기 실패: {str(e)}")
            indicators['treasury_10y'] = 4.0
            indicators['treasury_trend'] = 'STABLE'
        
        # 2. VIX 지수 (yfinance - 무료)
        try:
            vix = yf.Ticker("^VIX")
            vix_data = vix.history(period="5d")
            
            if not vix_data.empty:
                indicators['vix'] = vix_data['Close'].iloc[-1]
                logger.info(f"VIX 지수: {indicators['vix']:.2f}")
            else:
                indicators['vix'] = 20.0  # 기본값
        except Exception as e:
            logger.warning(f"VIX 지수 가져오기 실패: {str(e)}")
            indicators['vix'] = 20.0
        
        # 3. FRED 지표들 (FRED API 필요)
        if self.fred_client:
            try:
                # 실업률
                unemployment = self.fred_client.get_series(
                    'UNRATE',
                    observation_start=datetime.now() - timedelta(days=180)
                )
                if not unemployment.empty:
                    indicators['unemployment_rate'] = unemployment.iloc[-1]
                    indicators['unemployment_trend'] = self._calc_trend(unemployment)
                    logger.info(f"실업률: {indicators['unemployment_rate']:.1f}% ({indicators['unemployment_trend']})")
                
                # 인플레이션 (CPI)
                cpi = self.fred_client.get_series(
                    'CPIAUCSL',
                    observation_start=datetime.now() - timedelta(days=400)
                )
                if len(cpi) >= 13:
                    indicators['cpi_yoy'] = ((cpi.iloc[-1] / cpi.iloc[-13]) - 1) * 100
                    logger.info(f"CPI YoY: {indicators['cpi_yoy']:.2f}%")
                
                # GDP 성장률
                gdp = self.fred_client.get_series(
                    'GDPC1',
                    observation_start=datetime.now() - timedelta(days=400)
                )
                if len(gdp) >= 5:
                    indicators['gdp_growth'] = ((gdp.iloc[-1] / gdp.iloc[-5]) - 1) * 100
                    logger.info(f"GDP 성장률: {indicators['gdp_growth']:.2f}%")
                
                # 연준 기준금리
                fed_rate = self.fred_client.get_series(
                    'FEDFUNDS',
                    observation_start=datetime.now() - timedelta(days=90)
                )
                if not fed_rate.empty:
                    indicators['fed_funds_rate'] = fed_rate.iloc[-1]
                    logger.info(f"연준 기준금리: {indicators['fed_funds_rate']:.2f}%")
                
                # 소비자 신뢰지수
                consumer_sentiment = self.fred_client.get_series(
                    'UMCSENT',
                    observation_start=datetime.now() - timedelta(days=90)
                )
                if not consumer_sentiment.empty:
                    indicators['consumer_sentiment'] = consumer_sentiment.iloc[-1]
                    logger.info(f"소비자 신뢰지수: {indicators['consumer_sentiment']:.1f}")
                    
            except Exception as e:
                logger.warning(f"FRED 지표 가져오기 실패: {str(e)}")
        
        else:
            logger.debug("FRED API 미사용 - 기본 지표만 수집")
        
        # 기본값 설정 (FRED 데이터 없을 때)
        indicators.setdefault('unemployment_rate', 4.0)
        indicators.setdefault('unemployment_trend', 'STABLE')
        indicators.setdefault('cpi_yoy', 3.0)
        indicators.setdefault('gdp_growth', 2.5)
        indicators.setdefault('fed_funds_rate', 5.0)
        indicators.setdefault('consumer_sentiment', 70.0)
        
        return indicators
    
    def assess_market_environment(self) -> Dict:
        """
        거시경제 환경 평가
        
        Returns:
            Dict: {
                'environment': 환경 분류 ('VERY_FAVORABLE' ~ 'VERY_UNFAVORABLE'),
                'score': 점수 (-10 ~ +10),
                'indicators': 지표 딕셔너리,
                'signals': 신호 리스트,
                'position_multiplier': 포지션 크기 조정 배수 (0.2 ~ 1.3)
            }
        """
        # 캐시 확인
        if self.cache and self.cache_time:
            elapsed = (datetime.now() - self.cache_time).total_seconds()
            if elapsed < self.cache_duration:
                logger.debug("캐시된 거시경제 환경 사용")
                return self.cache
        
        logger.info("거시경제 환경 평가 시작")
        
        # 지표 수집 시도 (실패 시 캐시된 값 또는 기본값 사용)
        try:
            indicators = self.get_current_indicators()
        except Exception as e:
            logger.error(f"지표 수집 중 심각한 오류: {str(e)}")
            if self.cache:
                logger.info("이전 캐시 데이터를 대신 사용합니다.")
                return self.cache
            else:
                logger.warning("사용 가능한 데이터가 없어 중립 상태를 반환합니다.")
                return {
                    'environment': 'NEUTRAL',
                    'score': 0,
                    'indicators': {},
                    'signals': ['DATA_FETCH_ERROR'],
                    'position_multiplier': 1.0,
                    'timestamp': datetime.now()
                }
        
        # 점수 계산 (-10 ~ +10)
        score = 0
        signals = []
        
        # 1. 금리 평가 (높은 금리 = 부정적)
        treasury_10y = indicators['treasury_10y']
        if treasury_10y > 5.0:
            score -= 2
            signals.append('HIGH_RATES')
        elif treasury_10y < 3.0:
            score += 1
            signals.append('LOW_RATES')
        
        if indicators['treasury_trend'] == 'RISING':
            score -= 1
            signals.append('RISING_RATES')
        elif indicators['treasury_trend'] == 'FALLING':
            score += 1
            signals.append('FALLING_RATES')
        
        # 2. 실업률 평가 (높은 실업률 = 부정적)
        unemployment = indicators['unemployment_rate']
        if unemployment > 5.0:
            score -= 2
            signals.append('HIGH_UNEMPLOYMENT')
        elif unemployment < 4.0:
            score += 1
            signals.append('LOW_UNEMPLOYMENT')
        
        if indicators['unemployment_trend'] == 'RISING':
            score -= 2
            signals.append('UNEMPLOYMENT_RISING')
        
        # 3. 인플레이션 평가 (높은 인플레이션 = 부정적)
        cpi_yoy = indicators['cpi_yoy']
        if cpi_yoy > 4.0:
            score -= 2
            signals.append('HIGH_INFLATION')
        elif 2.0 <= cpi_yoy <= 3.0:
            score += 1
            signals.append('STABLE_INFLATION')
        elif cpi_yoy < 1.0:
            score -= 1
            signals.append('LOW_INFLATION')
        
        # 4. GDP 평가 (높은 성장 = 긍정적)
        gdp_growth = indicators['gdp_growth']
        if gdp_growth > 3.0:
            score += 2
            signals.append('STRONG_GROWTH')
        elif gdp_growth < 0:
            score -= 3
            signals.append('RECESSION')
        elif gdp_growth < 1.0:
            score -= 1
            signals.append('WEAK_GROWTH')
        
        # 5. 소비자 신뢰 평가
        consumer_sentiment = indicators['consumer_sentiment']
        if consumer_sentiment > 80:
            score += 1
            signals.append('HIGH_CONFIDENCE')
        elif consumer_sentiment < 60:
            score -= 2
            signals.append('LOW_CONFIDENCE')
        
        # 6. VIX 평가 (높은 변동성 = 부정적)
        vix = indicators['vix']
        if vix > 30:
            score -= 2
            signals.append('HIGH_VOLATILITY')
        elif vix < 15:
            score += 1
            signals.append('LOW_VOLATILITY')
        elif vix > 25:
            score -= 1
            signals.append('ELEVATED_VOLATILITY')
        
        # 환경 분류
        if score >= 5:
            environment = 'VERY_FAVORABLE'
            position_multiplier = 1.3
        elif score >= 2:
            environment = 'FAVORABLE'
            position_multiplier = 1.1
        elif score >= -2:
            environment = 'NEUTRAL'
            position_multiplier = 1.0
        elif score >= -5:
            environment = 'UNFAVORABLE'
            position_multiplier = 0.7
        else:
            environment = 'VERY_UNFAVORABLE'
            position_multiplier = 0.3
        
        result = {
            'environment': environment,
            'score': score,
            'indicators': indicators,
            'signals': signals,
            'position_multiplier': position_multiplier,
            'timestamp': datetime.now()
        }
        
        # 캐시 저장
        self.cache = result
        self.cache_time = datetime.now()
        
        logger.info(f"거시경제 환경: {environment} (점수: {score:+d}, 신호: {len(signals)}개)")
        logger.info(f"주요 신호: {', '.join(signals[:5])}")
        
        return result
    
    def _calc_trend(self, series: pd.Series) -> str:
        """
        시계열 데이터의 추세 계산
        
        Args:
            series (pd.Series): 시계열 데이터
            
        Returns:
            str: 'RISING', 'FALLING', 'STABLE'
        """
        try:
            if len(series) < 5:
                return 'STABLE'
            
            # 최근 값 vs 이전 평균
            recent_value = series.iloc[-1]
            prev_avg = series.iloc[-10:-1].mean() if len(series) >= 10 else series.iloc[:-1].mean()
            
            change_pct = ((recent_value - prev_avg) / prev_avg) * 100
            
            if change_pct > 5:
                return 'RISING'
            elif change_pct < -5:
                return 'FALLING'
            else:
                return 'STABLE'
                
        except Exception as e:
            logger.debug(f"추세 계산 실패: {str(e)}")
            return 'STABLE'
    
    def clear_cache(self):
        """캐시 초기화"""
        self.cache = None
        self.cache_time = None
        logger.info("거시경제 캐시 초기화")


# 전역 인스턴스
macro_tracker = None

def get_macro_tracker() -> MacroIndicatorTracker:
    """전역 거시경제 추적기 가져오기"""
    global macro_tracker
    if macro_tracker is None:
        macro_tracker = MacroIndicatorTracker(FRED_API_KEY)
    return macro_tracker




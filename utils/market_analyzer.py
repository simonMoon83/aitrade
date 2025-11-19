"""
시장 상황 분석 모듈
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import yfinance as yf
from datetime import datetime, timedelta

from config import *
from utils.logger import setup_logger

logger = setup_logger("market_analyzer")

class MarketAnalyzer:
    """시장 상황 분석 클래스"""
    
    def __init__(self):
        """초기화"""
        # 시장 지표
        self.market_indices = {
            'SPY': 'S&P 500',
            'QQQ': 'NASDAQ',
            'IWM': 'Russell 2000',
            'VIX': 'Volatility Index'
        }
        
        # 섹터 ETF
        self.sector_etfs = {
            'XLK': 'Technology',
            'XLF': 'Financials',
            'XLV': 'Healthcare',
            'XLE': 'Energy',
            'XLI': 'Industrials',
            'XLY': 'Consumer Discretionary',
            'XLP': 'Consumer Staples',
            'XLU': 'Utilities',
            'XLRE': 'Real Estate'
        }
        
        # 시장 체제 임계값
        self.trend_thresholds = {
            'strong_bull': 0.02,  # 20일 MA 대비 +2% 이상
            'bull': 0.005,        # +0.5% 이상
            'neutral': -0.005,    # -0.5% ~ +0.5%
            'bear': -0.02,        # -2% 이하
            'strong_bear': -0.05  # -5% 이하
        }
        
        # 공포탐욕 지수 임계값
        self.fear_greed_levels = {
            'extreme_fear': 20,
            'fear': 40,
            'neutral': 60,
            'greed': 80,
            'extreme_greed': 100
        }
        
        # 캐시
        self._cache = {}
        self._cache_timestamp = {}
        self._cache_duration = timedelta(minutes=15)  # 15분 캐시
        self._filter_cache = None
        self._filter_cache_time = None
        self._filter_cache_ttl = timedelta(minutes=5)
        
    def get_market_data(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        """
        시장 데이터 가져오기
        
        Args:
            symbol (str): 티커 심볼
            period (str): 데이터 기간
        
        Returns:
            pd.DataFrame: 시장 데이터
        """
        cache_key = f"{symbol}_{period}"
        
        # 캐시 확인
        if cache_key in self._cache:
            if datetime.now() - self._cache_timestamp[cache_key] < self._cache_duration:
                return self._cache[cache_key]
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if not data.empty:
                self._cache[cache_key] = data
                self._cache_timestamp[cache_key] = datetime.now()
            else:
                # VIX 데이터가 비어있을 때는 경고만 출력 (에러 아님)
                if 'VIX' in symbol or '^VIX' in symbol:
                    logger.debug(f"{symbol} 데이터가 비어있습니다 (정상일 수 있음)")
                else:
                    logger.warning(f"{symbol} 데이터가 비어있습니다")
                
            return data
            
        except Exception as e:
            # VIX 데이터 수집 실패는 경고로 처리 (시스템 중단 방지)
            if 'VIX' in symbol or '^VIX' in symbol:
                logger.warning(f"{symbol} 데이터 가져오기 실패 (VIX 기반 분석 기능 제한됨): {str(e)}")
            else:
                logger.error(f"{symbol} 데이터 가져오기 실패: {str(e)}")
            return pd.DataFrame()
    
    def analyze_market_trend(self) -> Dict[str, any]:
        """
        전체 시장 추세 분석
        
        Returns:
            Dict: 시장 추세 정보
        """
        market_analysis = {
            'timestamp': datetime.now(),
            'indices': {},
            'trend': 'neutral',
            'strength': 0.0,
            'vix_level': 0.0,
            'market_breadth': {},
            'recommendation': ''
        }
        
        # 주요 지수 분석
        for symbol, name in self.market_indices.items():
            # VIX는 ^VIX로 접근 시도 (yfinance에서 VIX는 ^VIX로 접근)
            ticker_symbol = symbol
            if symbol == 'VIX':
                ticker_symbol = '^VIX'
            
            data = self.get_market_data(ticker_symbol)
            if data.empty:
                # VIX 데이터 수집 실패 시 경고만 출력하고 계속 진행
                if symbol == 'VIX':
                    logger.warning(f"VIX 데이터 수집 실패 - VIX 기반 분석 기능 제한됨")
                continue
            
            # 현재 가격과 이동평균 비교
            current_price = data['Close'].iloc[-1]
            ma20 = data['Close'].rolling(20).mean().iloc[-1]
            ma50 = data['Close'].rolling(50).mean().iloc[-1]
            
            trend_strength = (current_price - ma20) / ma20
            
            market_analysis['indices'][symbol] = {
                'name': name,
                'price': current_price,
                'ma20': ma20,
                'ma50': ma50,
                'trend_strength': trend_strength,
                'above_ma20': current_price > ma20,
                'above_ma50': current_price > ma50
            }
        
        # VIX 레벨
        if 'VIX' in market_analysis['indices']:
            market_analysis['vix_level'] = market_analysis['indices']['VIX']['price']
        
        # 전체 시장 추세 판단
        spy_trend = market_analysis['indices'].get('SPY', {}).get('trend_strength', 0)
        market_analysis['trend'] = self._classify_trend(spy_trend)
        market_analysis['strength'] = spy_trend
        
        # 시장 너비 (Market Breadth) 분석
        market_analysis['market_breadth'] = self._analyze_market_breadth()
        
        # 거래 권고사항
        market_analysis['recommendation'] = self._generate_market_recommendation(market_analysis)
        
        return market_analysis
    
    def _classify_trend(self, trend_strength: float) -> str:
        """추세 분류"""
        if trend_strength >= self.trend_thresholds['strong_bull']:
            return 'strong_bull'
        elif trend_strength >= self.trend_thresholds['bull']:
            return 'bull'
        elif trend_strength <= self.trend_thresholds['strong_bear']:
            return 'strong_bear'
        elif trend_strength <= self.trend_thresholds['bear']:
            return 'bear'
        else:
            return 'neutral'
    
    def _analyze_market_breadth(self) -> Dict[str, float]:
        """시장 너비 분석"""
        breadth = {
            'advancing_pct': 0.0,
            'declining_pct': 0.0,
            'new_highs': 0,
            'new_lows': 0
        }
        
        # 섹터별 성과 분석을 통한 간접적인 시장 너비 측정
        sector_performance = []
        
        for symbol in self.sector_etfs.keys():
            data = self.get_market_data(symbol, period="5d")
            if not data.empty:
                daily_return = (data['Close'].iloc[-1] - data['Close'].iloc[-2]) / data['Close'].iloc[-2]
                sector_performance.append(daily_return)
        
        if sector_performance:
            advancing = sum(1 for ret in sector_performance if ret > 0)
            declining = sum(1 for ret in sector_performance if ret < 0)
            total = len(sector_performance)
            
            breadth['advancing_pct'] = advancing / total
            breadth['declining_pct'] = declining / total
        
        return breadth
    
    def analyze_sector_rotation(self) -> Dict[str, any]:
        """
        섹터 로테이션 분석
        
        Returns:
            Dict: 섹터별 성과 및 추천
        """
        sector_analysis = {
            'timestamp': datetime.now(),
            'sectors': {},
            'top_sectors': [],
            'bottom_sectors': [],
            'rotation_signal': ''
        }
        
        sector_scores = []
        
        for symbol, name in self.sector_etfs.items():
            data = self.get_market_data(symbol, period="3mo")
            if data.empty:
                continue
            
            # 상대 강도 계산
            returns_1m = (data['Close'].iloc[-1] - data['Close'].iloc[-20]) / data['Close'].iloc[-20]
            returns_3m = (data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0]
            
            # 모멘텀 점수
            momentum_score = returns_1m * 0.7 + returns_3m * 0.3
            
            sector_info = {
                'name': name,
                'symbol': symbol,
                'returns_1m': returns_1m,
                'returns_3m': returns_3m,
                'momentum_score': momentum_score,
                'trend': 'up' if returns_1m > 0 else 'down'
            }
            
            sector_analysis['sectors'][symbol] = sector_info
            sector_scores.append((symbol, momentum_score))
        
        # 상위/하위 섹터 식별
        sector_scores.sort(key=lambda x: x[1], reverse=True)
        sector_analysis['top_sectors'] = [s[0] for s in sector_scores[:3]]
        sector_analysis['bottom_sectors'] = [s[0] for s in sector_scores[-3:]]
        
        # 로테이션 신호 생성
        sector_analysis['rotation_signal'] = self._generate_rotation_signal(sector_analysis)
        
        return sector_analysis
    
    def _generate_rotation_signal(self, sector_analysis: Dict) -> str:
        """섹터 로테이션 신호 생성"""
        top_sectors = sector_analysis['top_sectors']
        
        # 위험 자산 선호 (기술주, 소비재)
        risk_on_sectors = ['XLK', 'XLY', 'XLF']
        # 방어 자산 선호 (유틸리티, 필수소비재, 헬스케어)
        risk_off_sectors = ['XLU', 'XLP', 'XLV']
        
        risk_on_count = sum(1 for s in top_sectors if s in risk_on_sectors)
        risk_off_count = sum(1 for s in top_sectors if s in risk_off_sectors)
        
        if risk_on_count >= 2:
            return "Risk-On: 성장주/기술주 선호"
        elif risk_off_count >= 2:
            return "Risk-Off: 방어주/배당주 선호"
        else:
            return "Neutral: 균형잡힌 포트폴리오 유지"
    
    def calculate_market_regime(self) -> Dict[str, any]:
        """
        시장 체제 판단 (Bull/Bear/Sideways)
        
        Returns:
            Dict: 시장 체제 정보
        """
        spy_data = self.get_market_data('SPY', period="6mo")
        if spy_data.empty:
            return {'regime': 'unknown', 'confidence': 0.0}
        
        # 다양한 지표로 시장 체제 판단
        current_price = spy_data['Close'].iloc[-1]
        
        # 1. 추세 분석
        ma50 = spy_data['Close'].rolling(50).mean().iloc[-1]
        ma200 = spy_data['Close'].rolling(200).mean().iloc[-1]
        
        trend_score = 0
        if current_price > ma50:
            trend_score += 1
        if current_price > ma200:
            trend_score += 1
        if ma50 > ma200:
            trend_score += 2
        
        # 2. 변동성 분석
        returns = spy_data['Close'].pct_change()
        volatility = returns.std() * np.sqrt(252)
        
        # 3. 모멘텀 분석
        rsi = self._calculate_rsi(spy_data['Close'])
        
        # 체제 판단
        if trend_score >= 3 and rsi > 50:
            regime = 'bull'
            confidence = min(trend_score / 4 * 0.7 + (rsi - 50) / 50 * 0.3, 1.0)
        elif trend_score <= 1 and rsi < 50:
            regime = 'bear'
            confidence = min((4 - trend_score) / 4 * 0.7 + (50 - rsi) / 50 * 0.3, 1.0)
        else:
            regime = 'sideways'
            confidence = 1.0 - abs(trend_score - 2) / 2
        
        return {
            'regime': regime,
            'confidence': confidence,
            'trend_score': trend_score,
            'volatility': volatility,
            'rsi': rsi,
            'details': {
                'price_vs_ma50': (current_price - ma50) / ma50,
                'price_vs_ma200': (current_price - ma200) / ma200,
                'ma50_vs_ma200': (ma50 - ma200) / ma200
            }
        }
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]
    
    def _generate_market_recommendation(self, market_analysis: Dict) -> str:
        """시장 상황에 따른 거래 권고사항 생성"""
        trend = market_analysis['trend']
        vix = market_analysis['vix_level']
        breadth = market_analysis['market_breadth']
        
        recommendations = []
        
        # 추세 기반 권고
        if trend == 'strong_bull':
            recommendations.append("강한 상승장: 공격적 매수 전략 가능")
        elif trend == 'bull':
            recommendations.append("상승장: 선별적 매수 전략 권장")
        elif trend == 'neutral':
            recommendations.append("횡보장: 단기 스윙 전략 고려")
        elif trend == 'bear':
            recommendations.append("하락장: 방어적 전략, 현금 비중 확대")
        elif trend == 'strong_bear':
            recommendations.append("강한 하락장: 매수 자제, 손절매 철저")
        
        # VIX 기반 권고
        if vix > 30:
            recommendations.append("높은 변동성: 포지션 축소, 리스크 관리 강화")
        elif vix < 15:
            recommendations.append("낮은 변동성: 안정적 시장, 포지션 확대 가능")
        
        # 시장 너비 기반 권고
        if breadth.get('advancing_pct', 0) > 0.7:
            recommendations.append("광범위한 상승: 시장 참여 적극 고려")
        elif breadth.get('declining_pct', 0) > 0.7:
            recommendations.append("광범위한 하락: 방어적 포지션 유지")
        
        return " | ".join(recommendations)
    
    def get_market_filter_signal(self) -> Dict[str, any]:
        """
        종합적인 시장 필터 신호
        
        Returns:
            Dict: 거래 허용 여부 및 조정 계수
        """
        # 캐시 확인
        if self._filter_cache and self._filter_cache_time:
            if datetime.now() - self._filter_cache_time < self._filter_cache_ttl:
                return self._filter_cache

        # 시장 분석
        market_trend = self.analyze_market_trend()
        market_regime = self.calculate_market_regime()
        
        # 기본 설정
        filter_result = {
            'allow_trading': True,
            'position_size_multiplier': 1.0,
            'preferred_sectors': [],
            'avoid_sectors': [],
            'reasons': []
        }
        
        # VIX 기반 필터
        vix = market_trend.get('vix_level', 20)
        if vix > 35:
            filter_result['allow_trading'] = False
            filter_result['reasons'].append(f"VIX 너무 높음: {vix:.1f}")
        elif vix > 25:
            filter_result['position_size_multiplier'] *= 0.5
            filter_result['reasons'].append(f"VIX 상승: {vix:.1f}, 포지션 축소")
        
        # 시장 체제 기반 필터
        regime = market_regime.get('regime', 'unknown')
        if regime == 'bear' and market_regime.get('confidence', 0) > 0.7:
            filter_result['position_size_multiplier'] *= 0.3
            filter_result['reasons'].append("약세장: 매수 제한")
        elif regime == 'bull' and market_regime.get('confidence', 0) > 0.7:
            filter_result['position_size_multiplier'] *= 1.2
            filter_result['reasons'].append("강세장: 포지션 확대 가능")
        
        # 섹터 로테이션 기반 필터
        sector_rotation = self.analyze_sector_rotation()
        filter_result['preferred_sectors'] = sector_rotation.get('top_sectors', [])[:2]
        filter_result['avoid_sectors'] = sector_rotation.get('bottom_sectors', [])[:2]
        
        self._filter_cache = filter_result
        self._filter_cache_time = datetime.now()
        return filter_result

# 전역 시장 분석기 인스턴스
market_analyzer = MarketAnalyzer()

def get_market_conditions() -> Dict[str, any]:
    """
    편의 함수: 현재 시장 상황 가져오기
    
    Returns:
        Dict: 시장 상황 정보
    """
    return {
        'trend': market_analyzer.analyze_market_trend(),
        'regime': market_analyzer.calculate_market_regime(),
        'sectors': market_analyzer.analyze_sector_rotation(),
        'filter': market_analyzer.get_market_filter_signal()
    }

def should_trade_today() -> Tuple[bool, str]:
    """
    편의 함수: 오늘 거래 여부 결정
    
    Returns:
        Tuple[bool, str]: (거래 여부, 이유)
    """
    filter_signal = market_analyzer.get_market_filter_signal()
    
    if not filter_signal['allow_trading']:
        reasons = " | ".join(filter_signal['reasons'])
        return False, f"시장 상황 부적합: {reasons}"
    
    return True, "거래 가능"

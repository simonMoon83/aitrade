"""
섹터 순환 분석 모듈
11개 섹터 ETF를 추적하여 강세/약세 섹터 판단 및 경기 사이클 감지
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from config import *
from utils.logger import setup_logger

logger = setup_logger("sector_analyzer")

# 11개 섹터 ETF (SPDR Select Sector ETFs)
SECTOR_ETFS = {
    'Technology': 'XLK',              # 기술
    'Financial': 'XLF',               # 금융
    'Healthcare': 'XLV',              # 헬스케어
    'ConsumerDiscretionary': 'XLY',  # 임의소비재
    'ConsumerStaples': 'XLP',        # 필수소비재
    'Energy': 'XLE',                 # 에너지
    'Industrials': 'XLI',            # 산업재
    'Materials': 'XLB',              # 소재
    'RealEstate': 'XLRE',            # 부동산
    'Utilities': 'XLU',              # 유틸리티
    'Communication': 'XLC'           # 통신
}

# 섹터 이름 매핑 (yfinance sector -> 우리 섹터)
SECTOR_NAME_MAPPING = {
    'Technology': 'Technology',
    'Financial Services': 'Financial',
    'Financials': 'Financial',
    'Healthcare': 'Healthcare',
    'Consumer Cyclical': 'ConsumerDiscretionary',
    'Consumer Defensive': 'ConsumerStaples',
    'Energy': 'Energy',
    'Industrials': 'Industrials',
    'Basic Materials': 'Materials',
    'Real Estate': 'RealEstate',
    'Utilities': 'Utilities',
    'Communication Services': 'Communication',
    'Telecommunications': 'Communication'
}


class SectorRotationAnalyzer:
    """섹터 순환 분석 클래스"""
    
    def __init__(self):
        """초기화"""
        self.sector_etfs = SECTOR_ETFS
        self.cache = None
        self.cache_time = None
        self.cache_duration = SECTOR_CACHE_HOURS * 3600  # 초 단위
        
        logger.info("섹터 순환 분석기 초기화 완료")
    
    def get_sector_strength(self, period: str = SECTOR_ANALYSIS_PERIOD) -> Dict:
        """
        섹터별 강도 분석
        
        Args:
            period (str): 분석 기간 ('1mo', '3mo', '6mo', '1y' 등)
            
        Returns:
            Dict: {
                'sectors': {sector_name: {
                    'rank': 순위 (1~11),
                    'returns': {'1week': %, '1month': %, '3month': %},
                    'relative_strength': S&P500 대비 상대 강도,
                    'momentum': 모멘텀 점수,
                    'etf': ETF 심볼
                }},
                'top_3': [상위 3개 섹터],
                'bottom_3': [하위 3개 섹터],
                'market_phase': 경기 사이클 국면
            }
        """
        # 캐시 확인
        if self.cache and self.cache_time:
            elapsed = (datetime.now() - self.cache_time).total_seconds()
            if elapsed < self.cache_duration:
                logger.debug("캐시된 섹터 데이터 사용")
                return self.cache
        
        logger.info(f"섹터 강도 분석 시작 (기간: {period})")
        
        strengths = {}
        
        # S&P 500 데이터 가져오기 (비교 기준)
        try:
            spy = yf.download('^GSPC', period=period, progress=False)
            spy_return_1m = self._calc_return(spy, 20) if len(spy) >= 20 else 0
        except Exception as e:
            logger.warning(f"S&P 500 데이터 가져오기 실패: {str(e)}")
            spy_return_1m = 0
        
        # 각 섹터 ETF 분석
        successful_sectors = 0
        for sector, etf in self.sector_etfs.items():
            try:
                data = yf.download(etf, period=period, progress=False)
                
                if data.empty or len(data) < 5:
                    logger.warning(f"[{sector}] 데이터 부족: {len(data)}일")
                    continue
                
                # 수익률 계산
                returns = {
                    '1week': self._calc_return(data, 5) if len(data) >= 5 else 0,
                    '1month': self._calc_return(data, 20) if len(data) >= 20 else 0,
                    '3month': self._calc_return(data, 60) if len(data) >= 60 else 0
                }
                
                # 상대 강도 (vs S&P500)
                relative_strength = returns['1month'] - spy_return_1m
                
                # 모멘텀 계산 (최근 데이터에 더 가중)
                momentum = self._calc_momentum(data)
                
                strengths[sector] = {
                    'rank': 0,  # 나중에 계산
                    'returns': returns,
                    'relative_strength': relative_strength,
                    'momentum': momentum,
                    'etf': etf
                }
                successful_sectors += 1
                
                logger.debug(f"[{sector}] 1M 수익률: {returns['1month']:.2f}%, "
                           f"상대강도: {relative_strength:.2f}%")
                
            except Exception as e:
                logger.error(f"[{sector}] 분석 실패: {str(e)}")
                continue
        
        # 데이터가 아예 없거나 너무 적으면 중립 반환
        if successful_sectors < 3:
            logger.error(f"성공한 섹터 데이터가 너무 적습니다 ({successful_sectors}개). 중립 데이터 반환.")
            return self._get_neutral_sectors()
        
        # 섹터 순위 매기기 (상대 강도 기준)
        sorted_sectors = sorted(
            strengths.items(),
            key=lambda x: x[1]['relative_strength'],
            reverse=True
        )
        
        for rank, (sector, data) in enumerate(sorted_sectors, 1):
            strengths[sector]['rank'] = rank
        
        # 상위/하위 섹터
        top_3 = [s[0] for s in sorted_sectors[:SECTOR_TOP_N]]
        bottom_3 = [s[0] for s in sorted_sectors[-SECTOR_TOP_N:]]
        
        # 경기 사이클 국면 감지
        market_phase = self._detect_market_phase(strengths, top_3)
        
        result = {
            'sectors': strengths,
            'top_3': top_3,
            'bottom_3': bottom_3,
            'market_phase': market_phase,
            'spy_return_1m': spy_return_1m
        }
        
        # 캐시 저장
        self.cache = result
        self.cache_time = datetime.now()
        
        logger.info(f"섹터 분석 완료 - 강세: {', '.join(top_3)}, 국면: {market_phase}")
        
        return result
    
    def get_symbol_sector(self, symbol: str) -> str:
        """
        종목의 섹터 확인
        
        Args:
            symbol (str): 종목 심볼
            
        Returns:
            str: 섹터 이름 (SECTOR_ETFS 키 중 하나, 알 수 없으면 'Unknown')
        """
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            
            # yfinance 섹터 가져오기
            yf_sector = info.get('sector', 'Unknown')
            
            # 우리 섹터로 매핑
            mapped_sector = SECTOR_NAME_MAPPING.get(yf_sector, 'Unknown')
            
            logger.debug(f"[{symbol}] 섹터: {mapped_sector} (원본: {yf_sector})")
            
            return mapped_sector
            
        except Exception as e:
            logger.warning(f"[{symbol}] 섹터 확인 실패: {str(e)}")
            return 'Unknown'
    
    def should_favor_sector(self, symbol: str) -> Dict:
        """
        해당 종목의 섹터가 강세인지 판단
        
        Args:
            symbol (str): 종목 심볼
            
        Returns:
            Dict: {
                'sector': 섹터 이름,
                'rank': 섹터 순위 (1~11, 999=Unknown),
                'is_strong': 강세 섹터 여부,
                'phase': 시장 국면,
                'weight_adjustment': 포지션 가중치 조정 (0.7~1.3)
            }
        """
        # 섹터 확인
        sector = self.get_symbol_sector(symbol)
        
        # 섹터 강도 분석
        sector_strength = self.get_sector_strength()
        
        if sector == 'Unknown' or sector not in sector_strength['sectors']:
            logger.warning(f"[{symbol}] 섹터 정보 없음 또는 알 수 없음")
            return {
                'sector': sector,
                'rank': 999,
                'is_strong': False,
                'phase': sector_strength.get('market_phase', 'UNKNOWN'),
                'weight_adjustment': 1.0,
                'relative_strength': 0.0
            }
        
        sector_data = sector_strength['sectors'][sector]
        rank = sector_data['rank']
        relative_strength = sector_data['relative_strength']
        
        # 강세 섹터 판단 (상위 N개)
        is_strong = rank <= SECTOR_TOP_N
        
        # 포지션 가중치 조정
        if rank <= 2:
            weight_adjustment = 1.3  # 최상위 섹터 +30%
        elif rank <= 4:
            weight_adjustment = 1.1  # 상위 섹터 +10%
        elif rank >= 10:
            weight_adjustment = 0.7  # 최하위 섹터 -30%
        elif rank >= 8:
            weight_adjustment = 0.9  # 하위 섹터 -10%
        else:
            weight_adjustment = 1.0  # 중간 섹터 유지
        
        logger.info(f"[{symbol}] 섹터: {sector} (순위: {rank}/11, "
                   f"상대강도: {relative_strength:+.2f}%, 가중치: {weight_adjustment:.2f}x)")
        
        return {
            'sector': sector,
            'rank': rank,
            'is_strong': is_strong,
            'phase': sector_strength['market_phase'],
            'weight_adjustment': weight_adjustment,
            'relative_strength': relative_strength
        }
    
    def _calc_return(self, data: pd.DataFrame, days: int) -> float:
        """
        N일 수익률 계산
        
        Args:
            data (pd.DataFrame): 가격 데이터
            days (int): 기간 (영업일 기준)
            
        Returns:
            float: 수익률 (%)
        """
        try:
            if len(data) < days:
                return 0.0
            
            start_price = data['Close'].iloc[-days]
            end_price = data['Close'].iloc[-1]
            
            return ((end_price - start_price) / start_price) * 100
            
        except Exception as e:
            logger.debug(f"수익률 계산 실패: {str(e)}")
            return 0.0
    
    def _calc_momentum(self, data: pd.DataFrame) -> float:
        """
        모멘텀 계산 (최근 데이터에 가중치)
        
        Args:
            data (pd.DataFrame): 가격 데이터
            
        Returns:
            float: 모멘텀 점수
        """
        try:
            if len(data) < 10:
                return 0.0
            
            # 최근 5일 vs 이전 5일 수익률
            recent_return = self._calc_return(data, 5)
            prev_return = self._calc_return(data.iloc[:-5], 5) if len(data) >= 10 else 0
            
            # 가속도 계산
            momentum = recent_return - prev_return
            
            return momentum
            
        except Exception as e:
            logger.debug(f"모멘텀 계산 실패: {str(e)}")
            return 0.0
    
    def _detect_market_phase(self, strengths: Dict, top_sectors: List[str]) -> str:
        """
        경기 사이클 국면 감지
        
        Args:
            strengths (Dict): 섹터 강도 데이터
            top_sectors (List[str]): 상위 섹터 리스트
            
        Returns:
            str: 'EXPANSION', 'PEAK', 'CONTRACTION', 'RECOVERY', 'TRANSITION'
        """
        # 사이클별 특징 섹터
        expansion_sectors = ['Technology', 'ConsumerDiscretionary', 'Communication']
        peak_sectors = ['Industrials', 'Materials', 'Energy']
        contraction_sectors = ['Healthcare', 'ConsumerStaples', 'Utilities']
        recovery_sectors = ['Financial', 'RealEstate', 'Technology']
        
        # 각 국면 점수 계산
        expansion_score = sum(1 for s in top_sectors if s in expansion_sectors)
        peak_score = sum(1 for s in top_sectors if s in peak_sectors)
        contraction_score = sum(1 for s in top_sectors if s in contraction_sectors)
        recovery_score = sum(1 for s in top_sectors if s in recovery_sectors)
        
        # 최고 점수 국면 반환
        scores = {
            'EXPANSION': expansion_score,
            'PEAK': peak_score,
            'CONTRACTION': contraction_score,
            'RECOVERY': recovery_score
        }
        
        max_phase = max(scores, key=scores.get)
        max_score = scores[max_phase]
        
        # 명확한 신호가 없으면 전환기
        if max_score == 0:
            return 'TRANSITION'
        
        logger.info(f"경기 국면 점수: {scores}, 판단: {max_phase}")
        
        return max_phase
    
    def _get_neutral_sectors(self) -> Dict:
        """중립 섹터 데이터 반환"""
        return {
            'sectors': {},
            'top_3': [],
            'bottom_3': [],
            'market_phase': 'UNKNOWN',
            'spy_return_1m': 0.0
        }
    
    def clear_cache(self):
        """캐시 초기화"""
        self.cache = None
        self.cache_time = None
        logger.info("섹터 분석 캐시 초기화")


# 전역 인스턴스
sector_analyzer = None

def get_sector_analyzer() -> SectorRotationAnalyzer:
    """전역 섹터 분석기 가져오기"""
    global sector_analyzer
    if sector_analyzer is None:
        sector_analyzer = SectorRotationAnalyzer()
    return sector_analyzer




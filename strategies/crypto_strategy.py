"""
암호화폐 전용 거래 전략
기존 improved 전략을 암호화폐의 높은 변동성에 맞게 조정
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta

from utils.logger import setup_logger

logger = setup_logger("crypto_strategy")

class CryptoTradingStrategy:
    """암호화폐 전용 거래 전략"""
    
    def __init__(self):
        """초기화"""
        # 암호화폐는 변동성이 크므로 파라미터 조정 (개선: 더 완화)
        self.rsi_oversold = 35  # 30 → 35 (완화)
        self.rsi_overbought = 65  # 70 → 65 (완화)
        self.bb_std = 2.0
        self.volume_spike_threshold = 1.5  # 2.0 → 1.5 (완화)
        
        # 리스크 관리 (변동성 높으므로 더 넓은 범위)
        self.stop_loss_pct = 0.05     # 5% 손절 (주식 3%)
        self.take_profit_pct = 0.10   # 10% 익절 (주식 5%)
        self.position_size_pct = 0.15 # 한 코인당 15%
        self.max_positions = 5
        
        # 암호화폐 특화 파라미터
        self.volatility_threshold = 0.05  # 5% 이상 움직임
        self.fear_greed_threshold = 25     # 공포/탐욕 지수
        
        self.positions = {}
        
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        전략용 데이터 준비
        
        Args:
            data (pd.DataFrame): 기술적 지표가 포함된 데이터
        
        Returns:
            pd.DataFrame: 전략용 데이터
        """
        df = data.copy()
        
        # 암호화폐 특화 지표 추가
        df = self._add_crypto_indicators(df)
        
        # 신호 생성
        df = self._generate_signals(df)
        
        return df
    
    def _add_crypto_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """암호화폐 특화 지표 추가"""
        
        # 변동성 지표 (암호화폐는 변동성이 핵심)
        df['VOLATILITY'] = df['CLOSE'].pct_change().rolling(20).std()
        
        # 가격 모멘텀
        df['MOMENTUM_5'] = df['CLOSE'].pct_change(5)
        df['MOMENTUM_10'] = df['CLOSE'].pct_change(10)
        df['MOMENTUM_20'] = df['CLOSE'].pct_change(20)
        
        # 거래량 급증 탐지 (펌핑 감지)
        df['VOLUME_RATIO'] = df['VOLUME'] / df['VOLUME'].rolling(20).mean()
        
        # 트렌드 강도
        if 'MA_20' in df.columns and 'MA_50' in df.columns:
            df['TREND_STRENGTH'] = (df['MA_20'] - df['MA_50']) / df['MA_50']
        
        return df
    
    def _generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """매매 신호 생성"""
        
        # 매수 신호 점수
        df['BUY_SCORE'] = 0.0
        df['SELL_SCORE'] = 0.0
        
        # 1. RSI 기반 신호 (개선: 점수 상향)
        if 'RSI' in df.columns:
            df.loc[df['RSI'] < self.rsi_oversold, 'BUY_SCORE'] += 2.0  # 1.5 → 2.0
            df.loc[df['RSI'] > self.rsi_overbought, 'SELL_SCORE'] += 2.0  # 1.5 → 2.0
            
            # 극단적 과매도/과매수
            df.loc[df['RSI'] < 25, 'BUY_SCORE'] += 1.5  # 20 → 25, 1.0 → 1.5
            df.loc[df['RSI'] > 75, 'SELL_SCORE'] += 1.5  # 80 → 75, 1.0 → 1.5
        
        # 2. 볼린저 밴드
        if 'BB_LOWER' in df.columns and 'BB_UPPER' in df.columns:
            # 하단 돌파 = 매수 기회
            df.loc[df['CLOSE'] < df['BB_LOWER'], 'BUY_SCORE'] += 1.5
            # 상단 돌파 = 매도 기회
            df.loc[df['CLOSE'] > df['BB_UPPER'], 'SELL_SCORE'] += 1.5
        
        # 3. MACD 크로스
        if 'MACD' in df.columns and 'MACD_SIGNAL' in df.columns:
            # 골든 크로스
            df['MACD_CROSS'] = (df['MACD'] > df['MACD_SIGNAL']).astype(int).diff()
            df.loc[df['MACD_CROSS'] == 1, 'BUY_SCORE'] += 2.0
            # 데드 크로스
            df.loc[df['MACD_CROSS'] == -1, 'SELL_SCORE'] += 2.0
        
        # 4. 거래량 급증 (펌핑 감지)
        if 'VOLUME_RATIO' in df.columns:
            df.loc[df['VOLUME_RATIO'] > 2.5, 'BUY_SCORE'] += 1.0
            df.loc[df['VOLUME_RATIO'] > 5.0, 'BUY_SCORE'] += 1.0  # 초대형 거래량
        
        # 5. 모멘텀
        if 'MOMENTUM_5' in df.columns:
            # 급격한 하락 후 반등
            df.loc[(df['MOMENTUM_5'] < -0.1) & (df['CLOSE'] > df['CLOSE'].shift(1)), 'BUY_SCORE'] += 1.0
            # 급격한 상승 후 고점
            df.loc[(df['MOMENTUM_5'] > 0.15) & (df['CLOSE'] < df['CLOSE'].shift(1)), 'SELL_SCORE'] += 1.0
        
        # 6. 이동평균선 배열
        if 'MA_20' in df.columns and 'MA_50' in df.columns:
            # 골든크로스
            df.loc[(df['MA_20'] > df['MA_50']) & (df['MA_20'].shift(1) <= df['MA_50'].shift(1)), 'BUY_SCORE'] += 1.5
            # 데드크로스
            df.loc[(df['MA_20'] < df['MA_50']) & (df['MA_20'].shift(1) >= df['MA_50'].shift(1)), 'SELL_SCORE'] += 1.5
        
        return df
    
    def get_signal(self, data: pd.DataFrame, symbol: str, capital: float = 10000) -> Dict:
        """
        현재 시점의 거래 신호 생성
        
        Args:
            data (pd.DataFrame): 최신 데이터
            symbol (str): 코인 심볼
            capital (float): 현재 자본
        
        Returns:
            Dict: 거래 신호 정보
        """
        if data.empty or len(data) < 50:
            return {'signal': 'HOLD', 'confidence': 0.0, 'reason': 'Insufficient data'}
        
        # 최신 데이터
        latest = data.iloc[-1]
        
        # 필수 컬럼 확인
        if 'BUY_SCORE' not in data.columns:
            data = self._generate_signals(data)
            latest = data.iloc[-1]
        
        buy_score = latest.get('BUY_SCORE', 0)
        sell_score = latest.get('SELL_SCORE', 0)
        
        # 신호 근거 수집
        reasons = []
        
        # 매수 신호 분석 (개선: 임계값 완화)
        if buy_score >= 2.5:  # 4.0 → 2.5 (완화)
            signal = 'BUY'
            confidence = min(buy_score / 5.0, 1.0)  # 7.0 → 5.0
            
            if latest.get('RSI', 50) < self.rsi_oversold:
                reasons.append(f"RSI 과매도: {latest['RSI']:.1f}")
            if 'BB_LOWER' in latest and latest['CLOSE'] < latest['BB_LOWER']:
                reasons.append("볼린저밴드 하단 돌파")
            if latest.get('VOLUME_RATIO', 1) > 2.0:
                reasons.append(f"거래량 {latest['VOLUME_RATIO']:.1f}배 급증")
            if latest.get('MOMENTUM_5', 0) < -0.1:
                reasons.append("급락 후 반등 시그널")
                
        # 매도 신호 분석 (개선: 임계값 완화)
        elif sell_score >= 2.0:  # 3.5 → 2.0 (완화)
            signal = 'SELL'
            confidence = min(sell_score / 4.0, 1.0)  # 6.0 → 4.0
            
            if latest.get('RSI', 50) > self.rsi_overbought:
                reasons.append(f"RSI 과매수: {latest['RSI']:.1f}")
            if 'BB_UPPER' in latest and latest['CLOSE'] > latest['BB_UPPER']:
                reasons.append("볼린저밴드 상단 돌파")
            if latest.get('MOMENTUM_5', 0) > 0.15:
                reasons.append("급등 후 조정 시그널")
                
        else:
            signal = 'HOLD'
            confidence = 0.0
            reasons.append("신호 강도 부족")
        
        # 포지션 크기 계산
        if signal == 'BUY':
            price = latest.get('CLOSE', 0)
            if price > 0:
                position_value = capital * self.position_size_pct
                shares = int(position_value / price)
            else:
                shares = 0
        else:
            shares = 0
        
        return {
            'signal': signal,
            'confidence': confidence,
            'reasons': reasons,
            'price': latest.get('CLOSE', 0),
            'buy_score': buy_score,
            'sell_score': sell_score,
            'position_size': shares,
            'rsi': latest.get('RSI', 50),
            'volume_ratio': latest.get('VOLUME_RATIO', 1.0),
            'volatility': latest.get('VOLATILITY', 0.02)
        }
    
    def calculate_position_size(self, capital: float, price: float, volatility: float) -> int:
        """
        포지션 크기 계산 (변동성 기반)
        
        Args:
            capital (float): 현재 자본
            price (float): 현재 가격
            volatility (float): 변동성
        
        Returns:
            int: 매수할 수량
        """
        if price <= 0:
            return 0
        
        # 변동성이 높을수록 포지션 축소
        volatility_factor = 1.0
        if volatility > 0.1:  # 변동성 10% 이상
            volatility_factor = 0.5
        elif volatility > 0.05:  # 변동성 5% 이상
            volatility_factor = 0.7
        
        position_value = capital * self.position_size_pct * volatility_factor
        shares = int(position_value / price)
        
        return shares
    
    def check_stop_loss_take_profit(self, entry_price: float, current_price: float) -> tuple:
        """
        손절/익절 확인
        
        Args:
            entry_price (float): 진입 가격
            current_price (float): 현재 가격
        
        Returns:
            tuple: (should_close, reason)
        """
        if entry_price <= 0:
            return False, ""
        
        price_change = (current_price - entry_price) / entry_price
        
        # 손절
        if price_change <= -self.stop_loss_pct:
            return True, f"손절: {price_change:.2%}"
        
        # 익절
        if price_change >= self.take_profit_pct:
            return True, f"익절: {price_change:.2%}"
        
        return False, ""

# 전역 인스턴스
crypto_strategy = CryptoTradingStrategy()

def get_crypto_signal(data: pd.DataFrame, symbol: str, capital: float = 10000) -> Dict:
    """편의 함수: 암호화폐 거래 신호 생성"""
    return crypto_strategy.get_signal(data, symbol, capital)


"""
기술적 지표 및 특성 엔지니어링 모듈
"""

import pandas as pd
import numpy as np
import ta
from typing import Dict, List, Optional
from utils.logger import setup_logger

logger = setup_logger("feature_engineering")

class FeatureEngineer:
    """기술적 지표 및 특성 생성 클래스"""
    
    def __init__(self):
        """초기화"""
        pass
    
    def add_technical_indicators(self, data: pd.DataFrame, symbol: str = None) -> pd.DataFrame:
        """
        기술적 지표 추가
        
        Args:
            data (pd.DataFrame): OHLCV 데이터
            symbol (str, optional): 종목 코드 (로깅용)
        
        Returns:
            pd.DataFrame: 기술적 지표가 추가된 데이터
        """
        if data.empty:
            symbol_str = f"[{symbol}] " if symbol else ""
            logger.warning(f"{symbol_str}빈 데이터에 기술적 지표를 추가할 수 없습니다")
            return data
        
        df = data.copy()
        original_cols = len(df.columns)
        
        try:
            # 가격 기반 지표
            df = self._add_price_indicators(df)
            
            # 모멘텀 지표
            df = self._add_momentum_indicators(df)
            
            # 변동성 지표
            df = self._add_volatility_indicators(df)
            
            # 거래량 지표
            df = self._add_volume_indicators(df)
            
            # 추세 지표
            df = self._add_trend_indicators(df)
            
            # 파생 특성
            df = self._add_derived_features(df)
            
            added_indicators = len(df.columns) - original_cols
            symbol_str = f"[{symbol}] " if symbol else ""
            logger.info(f"{symbol_str}기술적 지표 추가 완료: +{added_indicators}개 지표 (총 {len(df.columns)}개 컬럼)")
            return df
            
        except Exception as e:
            symbol_str = f"[{symbol}] " if symbol else ""
            logger.error(f"{symbol_str}기술적 지표 추가 실패: {str(e)}")
            return data
    
    def _add_price_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """가격 기반 지표 추가"""
        # 이동평균선
        df['MA_5'] = ta.trend.sma_indicator(df['CLOSE'], window=5)
        df['MA_10'] = ta.trend.sma_indicator(df['CLOSE'], window=10)
        df['MA_20'] = ta.trend.sma_indicator(df['CLOSE'], window=20)
        df['MA_50'] = ta.trend.sma_indicator(df['CLOSE'], window=50)
        df['MA_200'] = ta.trend.sma_indicator(df['CLOSE'], window=200)
        
        # 지수이동평균
        df['EMA_12'] = ta.trend.ema_indicator(df['CLOSE'], window=12)
        df['EMA_26'] = ta.trend.ema_indicator(df['CLOSE'], window=26)
        
        # 가격 변화율
        df['PRICE_CHANGE'] = df['CLOSE'].pct_change()
        df['PRICE_CHANGE_5D'] = df['CLOSE'].pct_change(periods=5)
        df['PRICE_CHANGE_10D'] = df['CLOSE'].pct_change(periods=10)
        
        # 고가-저가 비율
        df['HIGH_LOW_RATIO'] = df['HIGH'] / df['LOW']
        df['CLOSE_OPEN_RATIO'] = df['CLOSE'] / df['OPEN']
        
        return df
    
    def _add_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """모멘텀 지표 추가"""
        # RSI (Relative Strength Index)
        df['RSI'] = ta.momentum.rsi(df['CLOSE'], window=14)
        df['RSI_OVERSOLD'] = (df['RSI'] < 30).astype(int)
        df['RSI_OVERBOUGHT'] = (df['RSI'] > 70).astype(int)
        
        # MACD
        macd = ta.trend.MACD(df['CLOSE'])
        df['MACD'] = macd.macd()
        df['MACD_SIGNAL'] = macd.macd_signal()
        df['MACD_HIST'] = macd.macd_diff()
        df['MACD_BULLISH'] = (df['MACD'] > df['MACD_SIGNAL']).astype(int)
        
        # 스토캐스틱 오실레이터
        stoch = ta.momentum.StochasticOscillator(df['HIGH'], df['LOW'], df['CLOSE'])
        df['STOCH_K'] = stoch.stoch()
        df['STOCH_D'] = stoch.stoch_signal()
        df['STOCH_OVERSOLD'] = (df['STOCH_K'] < 20).astype(int)
        df['STOCH_OVERBOUGHT'] = (df['STOCH_K'] > 80).astype(int)
        
        # Williams %R
        df['WILLIAMS_R'] = ta.momentum.williams_r(df['HIGH'], df['LOW'], df['CLOSE'])
        
        # CCI (Commodity Channel Index)
        df['CCI'] = ta.trend.cci(df['HIGH'], df['LOW'], df['CLOSE'])
        
        return df
    
    def _add_volatility_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """변동성 지표 추가"""
        # 볼린저 밴드
        bollinger = ta.volatility.BollingerBands(df['CLOSE'])
        df['BB_UPPER'] = bollinger.bollinger_hband()
        df['BB_MIDDLE'] = bollinger.bollinger_mavg()
        df['BB_LOWER'] = bollinger.bollinger_lband()
        df['BB_WIDTH'] = (df['BB_UPPER'] - df['BB_LOWER']) / df['BB_MIDDLE']
        df['BB_POSITION'] = (df['CLOSE'] - df['BB_LOWER']) / (df['BB_UPPER'] - df['BB_LOWER'])
        df['BB_SQUEEZE'] = (df['BB_WIDTH'] < df['BB_WIDTH'].rolling(20).mean() * 0.5).astype(int)
        
        # ATR (Average True Range)
        df['ATR'] = ta.volatility.average_true_range(df['HIGH'], df['LOW'], df['CLOSE'])
        df['ATR_RATIO'] = df['ATR'] / df['CLOSE']
        
        # 변동성 (표준편차)
        df['VOLATILITY_5D'] = df['CLOSE'].rolling(5).std()
        df['VOLATILITY_20D'] = df['CLOSE'].rolling(20).std()
        
        return df
    
    def _add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """거래량 지표 추가"""
        # 거래량 이동평균
        df['VOLUME_MA_5'] = df['VOLUME'].rolling(5).mean()
        df['VOLUME_MA_20'] = df['VOLUME'].rolling(20).mean()
        df['VOLUME_RATIO'] = df['VOLUME'] / df['VOLUME_MA_20']
        
        # 거래량 급증 감지
        df['VOLUME_SPIKE'] = (df['VOLUME'] > df['VOLUME_MA_20'] * 1.5).astype(int)
        
        # OBV (On-Balance Volume)
        df['OBV'] = ta.volume.on_balance_volume(df['CLOSE'], df['VOLUME'])
        
        # VWAP (Volume Weighted Average Price)
        df['VWAP'] = ta.volume.volume_weighted_average_price(
            df['HIGH'], df['LOW'], df['CLOSE'], df['VOLUME']
        )
        df['VWAP_RATIO'] = df['CLOSE'] / df['VWAP']
        
        # Chaikin Money Flow
        df['CMF'] = ta.volume.chaikin_money_flow(df['HIGH'], df['LOW'], df['CLOSE'], df['VOLUME'])
        
        return df
    
    def _add_trend_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """추세 지표 추가"""
        # ADX (Average Directional Index)
        adx = ta.trend.ADXIndicator(df['HIGH'], df['LOW'], df['CLOSE'])
        df['ADX'] = adx.adx()
        df['ADX_POS'] = adx.adx_pos()
        df['ADX_NEG'] = adx.adx_neg()
        df['ADX_STRONG'] = (df['ADX'] > 25).astype(int)
        
        # Parabolic SAR
        df['PSAR'] = ta.trend.psar_up(df['HIGH'], df['LOW'], df['CLOSE'])
        df['PSAR_BULLISH'] = (df['CLOSE'] > df['PSAR']).astype(int)
        
        # Aroon
        aroon = ta.trend.AroonIndicator(df['HIGH'], df['LOW'])
        df['AROON_UP'] = aroon.aroon_up()
        df['AROON_DOWN'] = aroon.aroon_down()
        df['AROON_INDICATOR'] = aroon.aroon_indicator()
        
        return df
    
    def _add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """파생 특성 추가"""
        # 가격 위치 (최근 N일 중 위치)
        for period in [5, 10, 20]:
            df[f'PRICE_POSITION_{period}D'] = (
                df['CLOSE'].rolling(period).rank(pct=True)
            )
        
        # 최고가/최저가 근접도
        df['HIGH_PROXIMITY'] = (df['CLOSE'] - df['LOW']) / (df['HIGH'] - df['LOW'])
        
        # 연속 상승/하락 일수
        df['CONSECUTIVE_UP'] = (df['CLOSE'] > df['CLOSE'].shift(1)).astype(int)
        df['CONSECUTIVE_DOWN'] = (df['CLOSE'] < df['CLOSE'].shift(1)).astype(int)
        
        # 갭 (전일 종가 대비 당일 시가)
        df['GAP'] = (df['OPEN'] - df['CLOSE'].shift(1)) / df['CLOSE'].shift(1)
        df['GAP_UP'] = (df['GAP'] > 0.02).astype(int)  # 2% 이상 갭업
        df['GAP_DOWN'] = (df['GAP'] < -0.02).astype(int)  # 2% 이상 갭다운
        
        # 시간 특성 (요일, 월)
        df['Date'] = pd.to_datetime(df['Date'])
        df['WEEKDAY'] = df['Date'].dt.weekday
        df['MONTH'] = df['Date'].dt.month
        df['QUARTER'] = df['Date'].dt.quarter
        
        return df
    
    def create_target_variables(self, df: pd.DataFrame, 
                              future_periods: List[int] = [1, 3, 5, 10]) -> pd.DataFrame:
        """
        타겟 변수 생성 (미래 수익률)
        
        Args:
            df (pd.DataFrame): 데이터
            future_periods (List[int]): 미래 기간 리스트
        
        Returns:
            pd.DataFrame: 타겟 변수가 추가된 데이터
        """
        df = df.copy()
        
        for period in future_periods:
            # 미래 수익률
            df[f'FUTURE_RETURN_{period}D'] = df['CLOSE'].pct_change(periods=period).shift(-period)
            
            # 미래 최고가/최저가 대비 현재가
            df[f'FUTURE_HIGH_{period}D'] = df['HIGH'].rolling(period).max().shift(-period)
            df[f'FUTURE_LOW_{period}D'] = df['LOW'].rolling(period).min().shift(-period)
            
            # 매수/매도 신호 (임계값 기반)
            df[f'BUY_SIGNAL_{period}D'] = (df[f'FUTURE_RETURN_{period}D'] > 0.05).astype(int)  # 5% 이상 수익
            df[f'SELL_SIGNAL_{period}D'] = (df[f'FUTURE_RETURN_{period}D'] < -0.03).astype(int)  # 3% 이상 손실
        
        return df
    
    def get_feature_importance(self, df: pd.DataFrame, target_column: str) -> Dict[str, float]:
        """
        특성 중요도 계산 (상관관계 기반)
        
        Args:
            df (pd.DataFrame): 데이터
            target_column (str): 타겟 컬럼명
        
        Returns:
            Dict[str, float]: 특성별 중요도
        """
        if target_column not in df.columns:
            logger.warning(f"타겟 컬럼을 찾을 수 없음: {target_column}")
            return {}
        
        # 수치형 컬럼만 선택
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        feature_columns = [col for col in numeric_columns if col != target_column]
        
        # 상관관계 계산
        correlations = df[feature_columns + [target_column]].corr()[target_column]
        correlations = correlations.drop(target_column)
        
        # 절댓값으로 정렬
        importance = correlations.abs().sort_values(ascending=False)
        
        return importance.to_dict()
    
    def select_features(self, df: pd.DataFrame, 
                       target_column: str,
                       min_importance: float = 0.01,
                       max_features: int = 50) -> List[str]:
        """
        특성 선택
        
        Args:
            df (pd.DataFrame): 데이터
            target_column (str): 타겟 컬럼명
            min_importance (float): 최소 중요도
            max_features (int): 최대 특성 수
        
        Returns:
            List[str]: 선택된 특성 리스트
        """
        importance = self.get_feature_importance(df, target_column)
        
        # 중요도 기준으로 필터링
        selected_features = [
            feature for feature, imp in importance.items() 
            if imp >= min_importance
        ]
        
        # 최대 특성 수로 제한
        selected_features = selected_features[:max_features]
        
        logger.info(f"특성 선택 완료: {len(selected_features)}개 특성")
        return selected_features

# 전역 특성 엔지니어 인스턴스
feature_engineer = FeatureEngineer()

def add_technical_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """
    편의 함수: 기술적 지표 추가
    
    Args:
        data (pd.DataFrame): OHLCV 데이터
    
    Returns:
        pd.DataFrame: 기술적 지표가 추가된 데이터
    """
    return feature_engineer.add_technical_indicators(data)


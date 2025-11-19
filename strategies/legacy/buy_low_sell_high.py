"""
저점매수-고점매도 전략 구현
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
import xgboost as xgb
import joblib
import os

from config import *
from utils.logger import setup_logger
from utils.feature_engineering import feature_engineer

logger = setup_logger("buy_low_sell_high")

class BuyLowSellHighStrategy:
    """저점매수-고점매도 전략 클래스"""
    
    def __init__(self, model_type: str = MODEL_TYPE):
        """
        초기화
        
        Args:
            model_type (str): 모델 타입 ('random_forest' 또는 'xgboost')
        """
        self.model_type = model_type
        self.model = None
        self.feature_columns = []
        self.is_trained = False
        
        # 전략 파라미터
        self.rsi_oversold = RSI_OVERSOLD
        self.rsi_overbought = RSI_OVERBOUGHT
        self.bb_std = BOLLINGER_STD
        self.volume_spike_threshold = VOLUME_SPIKE_THRESHOLD
        
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        전략용 데이터 준비
        
        Args:
            data (pd.DataFrame): 기술적 지표가 포함된 데이터
        
        Returns:
            pd.DataFrame: 전략용 데이터
        """
        df = data.copy()
        
        # 저점/고점 신호 생성
        df = self._generate_buy_signals(df)
        df = self._generate_sell_signals(df)
        
        # 종합 신호 생성
        df = self._generate_combined_signals(df)
        
        # 타겟 변수 생성
        df = self._create_target_variables(df)
        
        return df
    
    def _generate_buy_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """매수 신호 생성"""
        # RSI 과매도
        df['BUY_RSI'] = (df['RSI'] < self.rsi_oversold).astype(int)
        
        # 볼린저 밴드 하단 근처
        df['BUY_BB'] = (df['CLOSE'] <= df['BB_LOWER']).astype(int)
        
        # 최근 N일 최저가 근처
        df['BUY_LOW'] = (df['CLOSE'] <= df['LOW'].rolling(LOW_POINT_DAYS).min()).astype(int)
        
        # 거래량 급증
        df['BUY_VOLUME'] = (df['VOLUME_RATIO'] > self.volume_spike_threshold).astype(int)
        
        # 이동평균선 지지
        df['BUY_MA_SUPPORT'] = (
            (df['CLOSE'] > df['MA_20']) & 
            (df['CLOSE'] > df['MA_50'])
        ).astype(int)
        
        # MACD 상승 전환
        df['BUY_MACD'] = (
            (df['MACD'] > df['MACD_SIGNAL']) & 
            (df['MACD'].shift(1) <= df['MACD_SIGNAL'].shift(1))
        ).astype(int)
        
        return df
    
    def _generate_sell_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """매도 신호 생성"""
        # RSI 과매수
        df['SELL_RSI'] = (df['RSI'] > self.rsi_overbought).astype(int)
        
        # 볼린저 밴드 상단 근처
        df['SELL_BB'] = (df['CLOSE'] >= df['BB_UPPER']).astype(int)
        
        # 최근 N일 최고가 근처
        df['SELL_HIGH'] = (df['CLOSE'] >= df['HIGH'].rolling(HIGH_POINT_DAYS).max()).astype(int)
        
        # 이동평균선 저항
        df['SELL_MA_RESISTANCE'] = (
            (df['CLOSE'] < df['MA_20']) & 
            (df['CLOSE'] < df['MA_50'])
        ).astype(int)
        
        # MACD 하락 전환
        df['SELL_MACD'] = (
            (df['MACD'] < df['MACD_SIGNAL']) & 
            (df['MACD'].shift(1) >= df['MACD_SIGNAL'].shift(1))
        ).astype(int)
        
        # 목표 수익률 달성
        df['SELL_PROFIT'] = (df['PRICE_CHANGE_5D'] > TAKE_PROFIT_PCT).astype(int)
        
        return df
    
    def _generate_combined_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """종합 신호 생성"""
        # 매수 신호 점수
        buy_signals = ['BUY_RSI', 'BUY_BB', 'BUY_LOW', 'BUY_VOLUME', 'BUY_MA_SUPPORT', 'BUY_MACD']
        df['BUY_SCORE'] = df[buy_signals].sum(axis=1)
        
        # 매도 신호 점수
        sell_signals = ['SELL_RSI', 'SELL_BB', 'SELL_HIGH', 'SELL_MA_RESISTANCE', 'SELL_MACD', 'SELL_PROFIT']
        df['SELL_SCORE'] = df[sell_signals].sum(axis=1)
        
        # 종합 신호 (임계값 기반) - 2개 이상의 신호로 완화
        df['SIGNAL'] = 0  # HOLD
        df.loc[df['BUY_SCORE'] >= 2, 'SIGNAL'] = 1  # BUY (3->2로 완화)
        df.loc[df['SELL_SCORE'] >= 2, 'SIGNAL'] = -1  # SELL (3->2로 완화)
        
        # 신호 강도
        df['SIGNAL_STRENGTH'] = np.abs(df['BUY_SCORE'] - df['SELL_SCORE'])
        
        return df
    
    def _create_target_variables(self, df: pd.DataFrame) -> pd.DataFrame:
        """타겟 변수 생성"""
        # 미래 수익률 (1일, 3일, 5일 후)
        for period in [1, 3, 5]:
            df[f'FUTURE_RETURN_{period}D'] = df['CLOSE'].pct_change(periods=period).shift(-period)
        
        # 매수/매도 타겟 (임계값 기반)
        df['TARGET_BUY'] = (df['FUTURE_RETURN_3D'] > 0.03).astype(int)  # 3일 후 3% 이상 수익
        df['TARGET_SELL'] = (df['FUTURE_RETURN_3D'] < -0.02).astype(int)  # 3일 후 2% 이상 손실
        
        # 다중 클래스 타겟
        df['TARGET_MULTI'] = 1  # HOLD
        df.loc[df['TARGET_BUY'] == 1, 'TARGET_MULTI'] = 2  # BUY
        df.loc[df['TARGET_SELL'] == 1, 'TARGET_MULTI'] = 0  # SELL
        
        return df
    
    def train_model(self, data: pd.DataFrame, target_column: str = 'TARGET_MULTI'):
        """
        머신러닝 모델 학습
        
        Args:
            data (pd.DataFrame): 학습 데이터
            target_column (str): 타겟 컬럼명
        """
        logger.info("머신러닝 모델 학습 시작")
        
        # 특성 선택
        feature_columns = feature_engineer.select_features(data, target_column)
        self.feature_columns = feature_columns
        
        # 데이터 준비
        X = data[feature_columns].fillna(0)
        y = data[target_column].fillna(1)  # 결측치는 HOLD로 처리
        
        # 학습/테스트 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=1-TRAIN_TEST_SPLIT, random_state=42, stratify=y
        )
        
        # 모델 생성 및 학습
        if self.model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == 'xgboost':
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                n_jobs=-1
            )
        
        # 모델 학습
        self.model.fit(X_train, y_train)
        
        # 성능 평가
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        logger.info(f"모델 학습 완료 - Train Score: {train_score:.3f}, Test Score: {test_score:.3f}")
        
        # 교차 검증
        cv_scores = cross_val_score(self.model, X_train, y_train, cv=CROSS_VALIDATION_FOLDS)
        logger.info(f"교차 검증 점수: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
        
        # 상세 평가
        y_pred = self.model.predict(X_test)
        logger.info("분류 보고서:")
        logger.info(classification_report(y_test, y_pred))
        
        self.is_trained = True
        
        # 모델 저장
        self.save_model()
    
    def predict(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        예측 수행
        
        Args:
            data (pd.DataFrame): 예측할 데이터
        
        Returns:
            pd.DataFrame: 예측 결과가 추가된 데이터
        """
        if not self.is_trained:
            logger.error("모델이 학습되지 않았습니다")
            return data
        
        df = data.copy()
        
        # 특성 데이터 준비
        X = df[self.feature_columns].fillna(0)
        
        # 예측
        predictions = self.model.predict(X)
        probabilities = self.model.predict_proba(X)
        
        # 결과 추가
        df['PREDICTION'] = predictions
        df['CONFIDENCE'] = np.max(probabilities, axis=1)
        
        # 신호 해석
        df['ML_SIGNAL'] = df['PREDICTION'].map({0: 'SELL', 1: 'HOLD', 2: 'BUY'})
        
        return df
    
    def get_signal(self, data: pd.DataFrame, symbol: str) -> Dict:
        """
        현재 시점의 거래 신호 생성
        
        Args:
            data (pd.DataFrame): 최신 데이터
            symbol (str): 종목 코드
        
        Returns:
            Dict: 거래 신호 정보
        """
        if data.empty:
            return {'signal': 'HOLD', 'confidence': 0.0, 'reason': 'No data'}
        
        # 최신 데이터로 예측
        latest_data = data.tail(1)
        prediction_result = self.predict(latest_data)
        
        if prediction_result.empty:
            return {'signal': 'HOLD', 'confidence': 0.0, 'reason': 'Prediction failed'}
        
        latest = prediction_result.iloc[0]
        
        # 신호 생성
        signal = latest['ML_SIGNAL']
        confidence = latest['CONFIDENCE']
        
        # 신호 근거
        reasons = []
        if latest.get('BUY_SCORE', 0) >= 3:
            reasons.append(f"매수 신호 점수: {latest['BUY_SCORE']}")
        if latest.get('SELL_SCORE', 0) >= 3:
            reasons.append(f"매도 신호 점수: {latest['SELL_SCORE']}")
        if latest.get('RSI', 0) < self.rsi_oversold:
            reasons.append(f"RSI 과매도: {latest['RSI']:.1f}")
        if latest.get('RSI', 0) > self.rsi_overbought:
            reasons.append(f"RSI 과매수: {latest['RSI']:.1f}")
        
        return {
            'symbol': symbol,
            'signal': signal,
            'confidence': confidence,
            'reasons': reasons,
            'timestamp': latest.get('Date', pd.Timestamp.now()),
            'price': latest.get('CLOSE', 0),
            'rsi': latest.get('RSI', 0),
            'bb_position': latest.get('BB_POSITION', 0.5),
            'volume_ratio': latest.get('VOLUME_RATIO', 1.0)
        }
    
    def save_model(self, filepath: Optional[str] = None):
        """모델 저장"""
        if not self.is_trained:
            logger.warning("학습되지 않은 모델은 저장할 수 없습니다")
            return
        
        if filepath is None:
            filepath = os.path.join(MODELS_DIR, f"buy_low_sell_high_{self.model_type}.joblib")
        
        os.makedirs(MODELS_DIR, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'feature_columns': self.feature_columns,
            'model_type': self.model_type,
            'is_trained': self.is_trained
        }
        
        joblib.dump(model_data, filepath)
        logger.info(f"모델 저장 완료: {filepath}")
    
    def load_model(self, filepath: Optional[str] = None):
        """모델 로드"""
        if filepath is None:
            filepath = os.path.join(MODELS_DIR, f"buy_low_sell_high_{self.model_type}.joblib")
        
        try:
            model_data = joblib.load(filepath)
            self.model = model_data['model']
            self.feature_columns = model_data['feature_columns']
            self.model_type = model_data['model_type']
            self.is_trained = model_data['is_trained']
            
            logger.info(f"모델 로드 완료: {filepath}")
            
        except FileNotFoundError:
            logger.warning(f"모델 파일을 찾을 수 없음: {filepath}")
        except Exception as e:
            logger.error(f"모델 로드 실패: {str(e)}")
    
    def get_feature_importance(self) -> Dict[str, float]:
        """특성 중요도 반환"""
        if not self.is_trained:
            return {}
        
        if hasattr(self.model, 'feature_importances_'):
            importance = dict(zip(self.feature_columns, self.model.feature_importances_))
            return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        
        return {}

# 전역 전략 인스턴스
strategy = BuyLowSellHighStrategy()

def train_strategy_model(data: pd.DataFrame, target_column: str = 'TARGET_MULTI'):
    """
    편의 함수: 전략 모델 학습
    
    Args:
        data (pd.DataFrame): 학습 데이터
        target_column (str): 타겟 컬럼명
    """
    strategy.train_model(data, target_column)

def get_trading_signal(data: pd.DataFrame, symbol: str) -> Dict:
    """
    편의 함수: 거래 신호 생성
    
    Args:
        data (pd.DataFrame): 최신 데이터
        symbol (str): 종목 코드
    
    Returns:
        Dict: 거래 신호 정보
    """
    return strategy.get_signal(data, symbol)


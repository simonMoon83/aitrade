"""
개선된 저점매수-고점매도 전략 구현 (Paper Trading 전용 설정)

📊 전략 설정 요약
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Paper Trading 모드 (전문가 권장)
  - RSI 임계값: 30/70 (완화)
  - 신호 임계값: BUY 3.0, SELL 2.5 (완화)
  - 거래량 조건: 1.3x (완화)
  - 신뢰도 임계값: 0.35~0.40 (완화)

📌 설계 의도:
  1. 더 많은 거래 기회 → 데이터 축적
  2. 신호 검증 및 성과 분석
  3. 전략 파라미터 최적화 기반 마련

⚠️ 실전 전환 시 적용할 엄격한 기준:
  - RSI: 25/75
  - 신호 임계값: BUY 4.5, SELL 4.0
  - 신뢰도: 0.7~0.8
  - 거래량 조건: 1.5x
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
from datetime import datetime, timedelta

from config import *
from utils.logger import setup_logger
from utils.feature_engineering import feature_engineer
from utils.market_analyzer import market_analyzer
from utils.news_sentiment import NewsSentimentAnalyzer
from utils.sector_analyzer import SectorRotationAnalyzer
from utils.macro_indicators import MacroIndicatorTracker

logger = setup_logger("improved_buy_low_sell_high")

class ImprovedBuyLowSellHighStrategy:
    """개선된 저점매수-고점매도 전략 클래스"""
    
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
        
        # 전략 파라미터 (Paper Trading 전용 - 완화된 조건)
        self.rsi_oversold = 30  # Paper Trading: 더 많은 신호
        self.rsi_overbought = 70  # Paper Trading: 더 많은 신호
        self.bb_std = BOLLINGER_STD
        self.volume_spike_threshold = 1.3  # Paper Trading: 거래량 조건 완화
        
        # 리스크 관리 파라미터 (config.py에서 로드)
        self.use_atr_sl_tp = USE_ATR_BASED_SL_TP
        self.atr_multiplier_sl = ATR_MULTIPLIER_SL
        self.atr_multiplier_tp = ATR_MULTIPLIER_TP
        
        self.stop_loss_pct = STOP_LOSS_PCT
        self.take_profit_pct = TAKE_PROFIT_PCT
        self.position_size_pct = 0.1  # 포트폴리오의 10%
        self.max_positions = 5  # 최대 5개 종목
        self.min_holding_days = 3  # 최소 보유 기간
        
        # 시장 상황 필터
        self.market_trend_ma = 50  # 시장 추세 판단용 이동평균
        self.min_adv20 = 1000000  # 최소 일평균 거래대금
        
        # 포지션 추적
        self.positions = {}  # {symbol: {'entry_date': date, 'entry_price': price}}
        
        # 뉴스 감성, 섹터, 거시경제 분석기 (지연 로딩)
        self.news_analyzer = None
        self.sector_analyzer = None
        self.macro_tracker = None
        
        # 캐시
        self.news_cache = {}
        self.sector_cache = None
        self.macro_cache = None
        self.cache_timestamps = {}
        
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        전략용 데이터 준비
        
        Args:
            data (pd.DataFrame): 기술적 지표가 포함된 데이터
        
        Returns:
            pd.DataFrame: 전략용 데이터
        """
        df = data.copy()
        
        # 시장 상황 지표 추가
        df = self._add_market_context(df)
        
        # 저점/고점 신호 생성
        df = self._generate_buy_signals(df)
        df = self._generate_sell_signals(df)
        
        # 종합 신호 생성
        df = self._generate_combined_signals(df)
        
        # 타겟 변수 생성
        df = self._create_target_variables(df)
        
        return df
    
    def _add_market_context(self, df: pd.DataFrame) -> pd.DataFrame:
        """시장 상황 지표 추가"""
        # 추세 강도
        df['TREND_STRENGTH'] = (df['CLOSE'] - df['MA_50']) / df['MA_50']
        
        # 변동성 지표
        df['ATR'] = self._calculate_atr(df)
        df['VOLATILITY_RATIO'] = df['ATR'] / df['CLOSE']
        
        # 상대강도 (다른 종목 대비)
        df['RELATIVE_STRENGTH'] = df['CLOSE'].pct_change(20) / df['CLOSE'].pct_change(20).rolling(250).mean()
        
        # 거래 활동성
        df['ADV_20'] = df['CLOSE'] * df['VOLUME'].rolling(20).mean()
        
        return df
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average True Range 계산"""
        high_low = df['HIGH'] - df['LOW']
        high_close = np.abs(df['HIGH'] - df['CLOSE'].shift())
        low_close = np.abs(df['LOW'] - df['CLOSE'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        
        return true_range.rolling(period).mean()
    
    def _generate_buy_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """매수 신호 생성 (개선된 버전)"""
        # RSI 과매도 (더 엄격한 조건)
        df['BUY_RSI'] = (df['RSI'] < self.rsi_oversold).astype(int)
        
        # 볼린저 밴드 하단 터치 + RSI 확인
        df['BUY_BB'] = (
            (df['CLOSE'] <= df['BB_LOWER']) & 
            (df['RSI'] < 40)
        ).astype(int)
        
        # 최근 N일 최저가 근처 + 거래량 확인
        df['BUY_LOW'] = (
            (df['CLOSE'] <= df['LOW'].rolling(LOW_POINT_DAYS).min() * 1.02) &
            (df['VOLUME_RATIO'] > 0.8)  # 평균 거래량 이상
        ).astype(int)
        
        # 거래량 급증 + 가격 하락
        df['BUY_VOLUME'] = (
            (df['VOLUME_RATIO'] > self.volume_spike_threshold) &
            (df['PRICE_CHANGE'] < 0)
        ).astype(int)
        
        # 이동평균선 지지 + 상승 추세
        df['BUY_MA_SUPPORT'] = (
            (df['CLOSE'] > df['MA_20']) & 
            (df['CLOSE'] > df['MA_50']) &
            (df['MA_20'] > df['MA_50'])  # 골든크로스
        ).astype(int)
        
        # MACD 상승 전환 + 히스토그램 양수 전환
        df['BUY_MACD'] = (
            (df['MACD'] > df['MACD_SIGNAL']) & 
            (df['MACD'].shift(1) <= df['MACD_SIGNAL'].shift(1)) &
            (df['MACD_HIST'] > 0)
        ).astype(int)
        
        # 다이버전스 신호
        df['BUY_DIVERGENCE'] = self._detect_bullish_divergence(df)

        # 장기 추세 필터 (MA200 상회) - 전문가 권장
        df['BUY_TREND_FILTER'] = (df['CLOSE'] > df['MA_200']).astype(int)
        
        # 시장 상황 필터
        df['BUY_MARKET'] = (
            (df['TREND_STRENGTH'] > -0.05) &  # 큰 하락 추세가 아님
            (df['ADV_20'] > self.min_adv20)  # 충분한 유동성
        ).astype(int)
        
        return df
    
    def _generate_sell_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """매도 신호 생성 (개선된 버전)"""
        # RSI 과매수 (더 엄격한 조건)
        df['SELL_RSI'] = (df['RSI'] > self.rsi_overbought).astype(int)
        
        # 볼린저 밴드 상단 돌파
        df['SELL_BB'] = (
            (df['CLOSE'] >= df['BB_UPPER']) &
            (df['RSI'] > 60)
        ).astype(int)
        
        # 최근 N일 최고가 근처
        df['SELL_HIGH'] = (
            df['CLOSE'] >= df['HIGH'].rolling(HIGH_POINT_DAYS).max() * 0.98
        ).astype(int)
        
        # 이동평균선 저항 + 하락 추세
        df['SELL_MA_RESISTANCE'] = (
            (df['CLOSE'] < df['MA_20']) & 
            (df['CLOSE'] < df['MA_50']) &
            (df['MA_20'] < df['MA_50'])  # 데드크로스
        ).astype(int)
        
        # MACD 하락 전환
        df['SELL_MACD'] = (
            (df['MACD'] < df['MACD_SIGNAL']) & 
            (df['MACD'].shift(1) >= df['MACD_SIGNAL'].shift(1)) &
            (df['MACD_HIST'] < 0)
        ).astype(int)
        
        # 목표 수익률 달성 및 손절매 (ATR 기반 또는 고정 %)
        if self.use_atr_sl_tp:
            # 5일 전 진입 가정, 당시 ATR 기준
            prev_atr = df['ATR'].shift(5)
            # 익절: 상승폭 > ATR * Multiplier
            df['SELL_PROFIT'] = ((df['CLOSE'] - df['CLOSE'].shift(5)) > (prev_atr * self.atr_multiplier_tp)).astype(int)
            # 손절: 하락폭 > ATR * Multiplier
            df['SELL_STOPLOSS'] = ((df['CLOSE'].shift(5) - df['CLOSE']) > (prev_atr * self.atr_multiplier_sl)).astype(int)
        else:
            # 목표 수익률 달성
            df['SELL_PROFIT'] = (df['PRICE_CHANGE_5D'] > self.take_profit_pct).astype(int)
            # 손절매 신호
            df['SELL_STOPLOSS'] = (df['PRICE_CHANGE_5D'] < -self.stop_loss_pct).astype(int)
        
        # 베어리시 다이버전스
        df['SELL_DIVERGENCE'] = self._detect_bearish_divergence(df)
        
        return df
    
    def _detect_bullish_divergence(self, df: pd.DataFrame) -> pd.Series:
        """강세 다이버전스 감지"""
        # 가격은 저점 갱신, RSI는 저점 상승
        price_low = df['LOW'].rolling(20).min()
        rsi_low = df['RSI'].rolling(20).min()
        
        bullish_div = (
            (df['LOW'] <= price_low.shift(20)) &  # 가격 저점 갱신
            (df['RSI'] > rsi_low.shift(20))  # RSI 저점 상승
        ).astype(int)
        
        return bullish_div
    
    def _detect_bearish_divergence(self, df: pd.DataFrame) -> pd.Series:
        """약세 다이버전스 감지"""
        # 가격은 고점 갱신, RSI는 고점 하락
        price_high = df['HIGH'].rolling(20).max()
        rsi_high = df['RSI'].rolling(20).max()
        
        bearish_div = (
            (df['HIGH'] >= price_high.shift(20)) &  # 가격 고점 갱신
            (df['RSI'] < rsi_high.shift(20))  # RSI 고점 하락
        ).astype(int)
        
        return bearish_div
    
    def _generate_combined_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """종합 신호 생성 (개선된 버전)"""
        # 매수 신호 점수 (가중치 적용)
        buy_weights = {
            'BUY_RSI': 1.5,
            'BUY_BB': 1.5,
            'BUY_LOW': 1.0,
            'BUY_VOLUME': 1.2,
            'BUY_MA_SUPPORT': 1.0,
            'BUY_MACD': 1.3,
            'BUY_DIVERGENCE': 2.0,
            'BUY_MARKET': 1.0,
            'BUY_TREND_FILTER': 1.5  # 전문가 제안: 장기 추세 필터
        }
        
        df['BUY_SCORE'] = sum(df[signal] * weight for signal, weight in buy_weights.items())
        
        # 매도 신호 점수 (가중치 적용)
        sell_weights = {
            'SELL_RSI': 1.5,
            'SELL_BB': 1.5,
            'SELL_HIGH': 1.0,
            'SELL_MA_RESISTANCE': 1.0,
            'SELL_MACD': 1.3,
            'SELL_PROFIT': 2.0,
            'SELL_STOPLOSS': 3.0,  # 손절매는 높은 가중치
            'SELL_DIVERGENCE': 2.0
        }
        
        df['SELL_SCORE'] = sum(df[signal] * weight for signal, weight in sell_weights.items())
        
        # 종합 신호 (Paper Trading 전용 - 완화된 임계값)
        df['SIGNAL'] = 0  # HOLD
        df.loc[df['BUY_SCORE'] >= 3.0, 'SIGNAL'] = 1  # BUY (Paper Trading: 3.0)
        df.loc[df['SELL_SCORE'] >= 2.5, 'SIGNAL'] = -1  # SELL (Paper Trading: 2.5)
        
        # 신호 강도
        df['SIGNAL_STRENGTH'] = np.maximum(df['BUY_SCORE'], df['SELL_SCORE'])
        
        # 신뢰도 (0~1)
        df['SIGNAL_CONFIDENCE'] = df['SIGNAL_STRENGTH'] / 10.0  # 정규화
        
        return df
    
    def calculate_position_size(self, capital: float, price: float, volatility: float) -> int:
        """
        포지션 크기 계산 (켈리 공식 변형)
        
        Args:
            capital (float): 현재 자본
            price (float): 주식 가격
            volatility (float): 변동성 (ATR/Price)
        
        Returns:
            int: 매수 수량
        """
        # 입력값 검증
        if pd.isna(price) or price <= 0:
            return 0
        if pd.isna(volatility):
            volatility = 0.02  # 기본값 2%
        
        # 기본 포지션 크기
        base_position_value = capital * self.position_size_pct
        
        # 변동성 조정 (변동성이 높을수록 포지션 축소)
        volatility_adj = 1.0 / (1.0 + volatility * 10)
        
        # 최종 포지션 크기
        position_value = base_position_value * volatility_adj
        
        # 주식 수량 계산
        try:
            shares = int(position_value / price)
        except:
            return 0
        
        # 최소 1주, 최대 포지션의 20%
        max_shares = int(capital * 0.2 / price) if price > 0 else 0
        shares = max(1, min(shares, max_shares))
        
        return shares
    
    def check_position_constraints(self, symbol: str, current_date: pd.Timestamp) -> bool:
        """
        포지션 제약 조건 확인
        
        Args:
            symbol (str): 종목 코드
            current_date (pd.Timestamp): 현재 날짜
        
        Returns:
            bool: 거래 가능 여부
        """
        # 이미 보유 중인 종목인지 확인
        if symbol in self.positions:
            entry_date = self.positions[symbol]['entry_date']
            holding_days = (current_date - entry_date).days
            
            # 최소 보유 기간 확인
            if holding_days < self.min_holding_days:
                return False
        
        # 최대 포지션 수 확인
        if len(self.positions) >= self.max_positions:
            return False
        
        return True
    
    def update_positions(self, symbol: str, action: str, price: float, date: pd.Timestamp):
        """포지션 업데이트"""
        if action == 'BUY':
            self.positions[symbol] = {
                'entry_date': date,
                'entry_price': price
            }
        elif action == 'SELL' and symbol in self.positions:
            del self.positions[symbol]
    
    def get_signal(
        self,
        data: pd.DataFrame,
        symbol: str,
        capital: float = 10000,
        market_filter: Optional[Dict] = None
    ) -> Dict:
        """
        현재 시점의 거래 신호 생성 (개선된 버전)
        
        Args:
            data (pd.DataFrame): 최신 데이터
            symbol (str): 종목 코드
            capital (float): 현재 자본
        
        Returns:
            Dict: 거래 신호 정보
        """
        if data.empty:
            logger.debug(f"[{symbol}] 신호 없음: 데이터 비어있음")
            return {'signal': 'HOLD', 'confidence': 0.0, 'reason': 'No data'}
        
        if market_filter is None:
            try:
                market_filter = market_analyzer.get_market_filter_signal()
            except Exception as e:
                logger.warning(f"[{symbol}] 시장 필터 조회 실패: {str(e)}")
                market_filter = {'allow_trading': True, 'position_size_multiplier': 1.0, 'reasons': [f'필터 오류: {e}']}
        
        if market_filter and not market_filter.get('allow_trading', True):
            reasons = market_filter.get('reasons', [])
            message = ", ".join(reasons) if reasons else "시장 필터 차단"
            logger.info(f"[{symbol}] HOLD: 시장 필터 차단 - {message}")
            return {
                'symbol': symbol,
                'signal': 'HOLD',
                'confidence': 0.0,
                'reason': message,
                'market_filter': market_filter
            }
        
        # 최신 데이터로 예측
        latest_data = data.tail(1)
        prediction_result = self.predict(latest_data)
        
        if prediction_result.empty:
            logger.warning(f"[{symbol}] 신호 없음: 예측 실패 (모델 미학습 또는 데이터 부족)")
            return {'signal': 'HOLD', 'confidence': 0.0, 'reason': 'Prediction failed'}
        
        latest = prediction_result.iloc[0]
        current_date = latest.get('Date', pd.Timestamp.now())
        
        # 포지션 제약 확인
        if not self.check_position_constraints(symbol, current_date):
            logger.debug(f"[{symbol}] 신호 없음: 포지션 제약 (최소 보유 기간 미충족 등)")
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'reason': 'Position constraints not met'
            }
        
        # 신호 생성
        signal = latest['ML_SIGNAL']
        confidence = latest['SIGNAL_CONFIDENCE']
        
        # 신호 강도 로깅
        buy_score = latest.get('BUY_SCORE', 0)
        sell_score = latest.get('SELL_SCORE', 0)
        logger.debug(f"[{symbol}] 기본 신호 분석: BUY={buy_score:.1f}, SELL={sell_score:.1f}, 신뢰도={confidence:.2f}, 신호={signal}")
        
        # ==============================================
        # 뉴스 감성, 섹터, 거시경제 정보 통합
        # ==============================================
        news_sentiment = self._get_news_sentiment(symbol)
        sector_info = self._get_sector_info(symbol)
        macro_env = self._get_macro_environment()
        
        # 신호 강도 조정
        original_buy_score = buy_score
        original_sell_score = sell_score
        
        # 1. 뉴스 감성 반영
        if news_sentiment['trend'] == 'VERY_POSITIVE':
            buy_score += 2
            logger.info(f"[{symbol}] 📰 매우 긍정적 뉴스 → 매수 신호 +2")
        elif news_sentiment['trend'] == 'POSITIVE':
            buy_score += 1
        elif news_sentiment['trend'] == 'VERY_NEGATIVE':
            sell_score += 2
            logger.info(f"[{symbol}] 📰 매우 부정적 뉴스 → 매도 신호 +2")
        elif news_sentiment['trend'] == 'NEGATIVE':
            sell_score += 1
        
        # 2. 섹터 강도 반영
        if sector_info['is_strong']:
            buy_score += 1
            logger.info(f"[{symbol}] 🏢 강세 섹터 ({sector_info['sector']}, 순위 {sector_info['rank']}) → 매수 신호 +1")
        elif sector_info['rank'] > 8 and sector_info['rank'] < 999:
            sell_score += 1
            logger.info(f"[{symbol}] 🏢 약세 섹터 ({sector_info['sector']}, 순위 {sector_info['rank']}) → 매도 신호 +1")
        
        # 3. 거시경제 환경 반영
        if macro_env['environment'] == 'VERY_UNFAVORABLE':
            if signal == 'BUY':
                signal = 'HOLD'
                logger.warning(f"[{symbol}] 🌍 거시경제 매우 불리 → 매수 신호 무효화")
        elif macro_env['environment'] == 'VERY_FAVORABLE':
            buy_score += 1
            logger.info(f"[{symbol}] 🌍 거시경제 매우 유리 → 매수 신호 +1")
        elif macro_env['environment'] == 'UNFAVORABLE':
            sell_score += 0.5
        
        # 조정된 신호 로깅
        if buy_score != original_buy_score or sell_score != original_sell_score:
            logger.info(f"[{symbol}] 조정된 신호: BUY {original_buy_score:.1f}→{buy_score:.1f}, "
                       f"SELL {original_sell_score:.1f}→{sell_score:.1f}")
        
        logger.debug(f"[{symbol}] 최종 신호: BUY={buy_score:.1f}, SELL={sell_score:.1f}, 신뢰도={confidence:.2f}, 신호={signal}")
        
        # 신호가 HOLD인 이유 상세 로깅
        if signal == 'HOLD':
            reasons_for_hold = []
            if buy_score < 3.0:
                reasons_for_hold.append(f"매수점수 부족({buy_score:.1f}<3.0)")
            if sell_score < 2.5:
                reasons_for_hold.append(f"매도점수 부족({sell_score:.1f}<2.5)")
            if confidence < 0.35:
                reasons_for_hold.append(f"신뢰도 낮음({confidence:.2f}<0.35)")
            
            logger.debug(f"[{symbol}] HOLD 이유: {', '.join(reasons_for_hold) if reasons_for_hold else '조건 미충족'}")
            logger.debug(f"[{symbol}] 기술지표: RSI={latest.get('RSI', 0):.1f}, VOLUME_RATIO={latest.get('VOLUME_RATIO', 1):.1f}x")
        
        # 신호 근거 (Paper Trading: 상세 로깅)
        reasons = []
        
        # 매수 신호 상세 분석
        if buy_score >= 3.0:
            reasons.append(f"✅ 매수 신호 점수: {buy_score:.1f}/10.0")
            if latest.get('BUY_RSI', 0) > 0:
                reasons.append(f"  - RSI 과매도: {latest.get('RSI', 0):.1f}")
            if latest.get('BUY_BB', 0) > 0:
                reasons.append(f"  - 볼린저밴드 하단")
            if latest.get('BUY_MACD', 0) > 0:
                reasons.append(f"  - MACD 골든크로스")
            if latest.get('BUY_DIVERGENCE', 0) > 0:
                reasons.append(f"  - 강세 다이버전스")
        
        # 매도 신호 상세 분석
        if sell_score >= 2.5:
            reasons.append(f"⚠️ 매도 신호 점수: {sell_score:.1f}/10.0")
            if latest.get('SELL_RSI', 0) > 0:
                reasons.append(f"  - RSI 과매수: {latest.get('RSI', 0):.1f}")
            if latest.get('SELL_BB', 0) > 0:
                reasons.append(f"  - 볼린저밴드 상단")
            if latest.get('SELL_MACD', 0) > 0:
                reasons.append(f"  - MACD 데드크로스")
            if latest.get('SELL_DIVERGENCE', 0) > 0:
                reasons.append(f"  - 약세 다이버전스")
        
        # 추가 시장 정보
        if latest.get('TREND_STRENGTH') is not None:
            reasons.append(f"📊 트렌드 강도: {latest['TREND_STRENGTH']:.2%}")
        if latest.get('VOLUME_RATIO') is not None:
            reasons.append(f"📈 거래량 비율: {latest['VOLUME_RATIO']:.1f}x")
        
        # 시장 필터 이유 추가
        if market_filter:
            filter_reasons = market_filter.get('reasons', [])
            if filter_reasons:
                reasons.append(f"🌐 시장 필터: {', '.join(filter_reasons)}")
        
        # 포지션 크기 계산
        price = latest.get('CLOSE', 0)
        if pd.isna(price) or price <= 0:
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'reason': 'Invalid price data'
            }
        
        volatility = latest.get('VOLATILITY_RATIO', 0.02)
        if pd.isna(volatility):
            volatility = 0.02
        
        position_size = self.calculate_position_size(capital, price, volatility)
        
        # 포지션 배수 조정 (시장 필터 + 섹터 + 거시경제)
        position_multiplier = market_filter.get('position_size_multiplier', 1.0) if market_filter else 1.0
        position_multiplier *= sector_info.get('weight_adjustment', 1.0)
        position_multiplier *= macro_env.get('position_multiplier', 1.0)
        
        position_size = int(position_size * position_multiplier)
        
        if signal == 'BUY' and position_size <= 0:
            logger.info(f"[{symbol}] HOLD: 시장 필터 포지션 제한으로 매수 보류")
            return {
                'symbol': symbol,
                'signal': 'HOLD',
                'confidence': confidence,
                'reason': 'Market filter reduced position size to zero',
                'market_filter': market_filter
            }
        
        # 손절/익절 가격 계산 (ATR 기반 동적 설정)
        atr = latest.get('ATR', 0)
        if self.use_atr_sl_tp and atr > 0:
            stop_loss = price - (atr * self.atr_multiplier_sl)
            take_profit = price + (atr * self.atr_multiplier_tp)
            reasons.append(f"🛡️ ATR 기반 리스크 관리: SL ${stop_loss:.2f}, TP ${take_profit:.2f} (ATR: {atr:.2f})")
        else:
            stop_loss = price * (1 - self.stop_loss_pct)
            take_profit = price * (1 + self.take_profit_pct)
        
        return {
            'symbol': symbol,
            'signal': signal,
            'confidence': confidence,
            'reasons': reasons,
            'timestamp': current_date,
            'price': price,
            'position_size': position_size,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'rsi': latest.get('RSI', 0),
            'bb_position': latest.get('BB_POSITION', 0.5),
            'volume_ratio': latest.get('VOLUME_RATIO', 1.0),
            'atr': latest.get('ATR', 0),
            'trend_strength': latest.get('TREND_STRENGTH', 0),
            'market_filter': market_filter,
            'context': {
                'news': news_sentiment,
                'sector': sector_info,
                'macro': macro_env
            }
        }
    
    def _create_target_variables(self, df: pd.DataFrame) -> pd.DataFrame:
        """타겟 변수 생성"""
        # 미래 수익률 (1일, 3일, 5일, 10일 후)
        for period in [1, 3, 5, 10]:
            df[f'FUTURE_RETURN_{period}D'] = df['CLOSE'].pct_change(periods=period).shift(-period)
        
        # 매수/매도 타겟 (개선된 임계값)
        df['TARGET_BUY'] = (df['FUTURE_RETURN_5D'] > 0.05).astype(int)  # 5일 후 5% 이상 수익
        df['TARGET_SELL'] = (df['FUTURE_RETURN_3D'] < -0.03).astype(int)  # 3일 후 3% 이상 손실
        
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
        logger.info("개선된 머신러닝 모델 학습 시작")
        
        # 특성 선택
        feature_columns = feature_engineer.select_features(data, target_column)
        self.feature_columns = feature_columns
        
        # 데이터 준비
        X = data[feature_columns].fillna(0)
        y = data[target_column].fillna(1)  # 결측치는 HOLD로 처리
        
        # 클래스 불균형 처리를 위한 가중치
        class_weights = {0: 2.0, 1: 1.0, 2: 2.0}  # SELL과 BUY에 더 높은 가중치
        
        # 학습/테스트 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=1-TRAIN_TEST_SPLIT, random_state=42, stratify=y
        )
        
        # 모델 생성 및 학습
        if self.model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=200,  # 더 많은 트리
                max_depth=15,
                min_samples_split=10,
                min_samples_leaf=5,
                max_features='sqrt',
                class_weight=class_weights,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == 'xgboost':
            self.model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=8,
                learning_rate=0.05,  # 더 낮은 학습률
                subsample=0.8,
                colsample_bytree=0.8,
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
    
    def save_model(self, filepath: Optional[str] = None):
        """모델 저장"""
        if not self.is_trained:
            logger.warning("학습되지 않은 모델은 저장할 수 없습니다")
            return
        
        if filepath is None:
            filepath = os.path.join(MODELS_DIR, f"improved_buy_low_sell_high_{self.model_type}.joblib")
        
        os.makedirs(MODELS_DIR, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'feature_columns': self.feature_columns,
            'model_type': self.model_type,
            'is_trained': self.is_trained,
            'positions': self.positions,
            'parameters': {
                'rsi_oversold': self.rsi_oversold,
                'rsi_overbought': self.rsi_overbought,
                'stop_loss_pct': self.stop_loss_pct,
                'take_profit_pct': self.take_profit_pct,
                'position_size_pct': self.position_size_pct,
                'max_positions': self.max_positions,
                'min_holding_days': self.min_holding_days
            }
        }
        
        joblib.dump(model_data, filepath)
        logger.info(f"모델 저장 완료: {filepath}")
    
    def load_model(self, filepath: Optional[str] = None):
        """모델 로드"""
        if filepath is None:
            filepath = os.path.join(MODELS_DIR, f"improved_buy_low_sell_high_{self.model_type}.joblib")
        
        try:
            model_data = joblib.load(filepath)
            self.model = model_data['model']
            self.feature_columns = model_data['feature_columns']
            self.model_type = model_data['model_type']
            self.is_trained = model_data['is_trained']
            self.positions = model_data.get('positions', {})
            
            # 파라미터 로드
            params = model_data.get('parameters', {})
            for key, value in params.items():
                setattr(self, key, value)
            
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
    
    def _get_news_analyzer(self) -> Optional[NewsSentimentAnalyzer]:
        """뉴스 분석기 인스턴스를 지연 로딩"""
        if self.news_analyzer is None:
            try:
                self.news_analyzer = NewsSentimentAnalyzer(FINNHUB_API_KEY, USE_LOCAL_FINBERT)
            except Exception as e:
                logger.warning(f"뉴스 분석기 초기화 실패: {str(e)}")
                self.news_analyzer = None
        return self.news_analyzer

    def _get_sector_analyzer(self) -> Optional[SectorRotationAnalyzer]:
        """섹터 분석기 인스턴스를 지연 로딩"""
        if self.sector_analyzer is None:
            try:
                self.sector_analyzer = SectorRotationAnalyzer()
            except Exception as e:
                logger.warning(f"섹터 분석기 초기화 실패: {str(e)}")
                self.sector_analyzer = None
        return self.sector_analyzer

    def _get_macro_tracker(self) -> Optional[MacroIndicatorTracker]:
        """거시경제 추적기 인스턴스를 지연 로딩"""
        if self.macro_tracker is None:
            try:
                self.macro_tracker = MacroIndicatorTracker(FRED_API_KEY)
            except Exception as e:
                logger.warning(f"거시경제 추적기 초기화 실패: {str(e)}")
                self.macro_tracker = None
        return self.macro_tracker

    def _get_news_sentiment(self, symbol: str) -> Dict:
        """
        뉴스 감성 정보 가져오기 (캐시 관리)
        
        Args:
            symbol (str): 종목 심볼
            
        Returns:
            Dict: 뉴스 감성 정보
        """
        analyzer = self._get_news_analyzer()
        if analyzer is None:
            return {
                'score': 0.0,
                'trend': 'NEUTRAL',
                'news_count': 0,
                'buzz_ratio': 1.0,
                'source': 'error'
            }

        try:
            return analyzer.get_sentiment_score(symbol)
        except Exception as e:
            logger.warning(f"[{symbol}] 뉴스 감성 분석 실패: {str(e)}")
            return {
                'score': 0.0,
                'trend': 'NEUTRAL',
                'news_count': 0,
                'buzz_ratio': 1.0,
                'source': 'error'
            }
    
    def _get_sector_info(self, symbol: str) -> Dict:
        """
        섹터 정보 가져오기 (캐시 관리)
        
        Args:
            symbol (str): 종목 심볼
            
        Returns:
            Dict: 섹터 정보
        """
        analyzer = self._get_sector_analyzer()
        if analyzer is None:
            return {
                'sector': 'Unknown',
                'rank': 999,
                'is_strong': False,
                'phase': 'UNKNOWN',
                'weight_adjustment': 1.0,
                'relative_strength': 0.0
            }

        try:
            return analyzer.should_favor_sector(symbol)
        except Exception as e:
            logger.warning(f"[{symbol}] 섹터 분석 실패: {str(e)}")
            return {
                'sector': 'Unknown',
                'rank': 999,
                'is_strong': False,
                'phase': 'UNKNOWN',
                'weight_adjustment': 1.0,
                'relative_strength': 0.0
            }
    
    def _get_macro_environment(self) -> Dict:
        """
        거시경제 환경 가져오기 (캐시 관리)
        
        Returns:
            Dict: 거시경제 환경 정보
        """
        tracker = self._get_macro_tracker()
        if tracker is None:
            return {
                'environment': 'NEUTRAL',
                'score': 0,
                'indicators': {},
                'signals': [],
                'position_multiplier': 1.0
            }

        try:
            return tracker.assess_market_environment()
        except Exception as e:
            logger.warning(f"거시경제 환경 분석 실패: {str(e)}")
            return {
                'environment': 'NEUTRAL',
                'score': 0,
                'indicators': {},
                'signals': [],
                'position_multiplier': 1.0
            }

# 전역 전략 인스턴스
improved_strategy = ImprovedBuyLowSellHighStrategy()

def train_strategy_model(data: pd.DataFrame, target_column: str = 'TARGET_MULTI'):
    """
    편의 함수: 전략 모델 학습
    
    Args:
        data (pd.DataFrame): 학습 데이터
        target_column (str): 타겟 컬럼명
    """
    improved_strategy.train_model(data, target_column)

def get_trading_signal(
    data: pd.DataFrame,
    symbol: str,
    capital: float = 10000,
    market_filter: Optional[Dict] = None
) -> Dict:
    """
    편의 함수: 거래 신호 생성
    
    Args:
        data (pd.DataFrame): 최신 데이터
        symbol (str): 종목 코드
        capital (float): 현재 자본
    
    Returns:
        Dict: 거래 신호 정보
    """
    return improved_strategy.get_signal(data, symbol, capital, market_filter=market_filter)

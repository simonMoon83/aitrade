"""
리스크 관리 모듈
거래 리스크를 모니터링하고 관리합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from enum import Enum

from config import *
from utils.logger import setup_logger

logger = setup_logger("risk_manager")

class RiskLevel(Enum):
    """리스크 레벨"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class RiskAlert:
    """리스크 알림"""
    level: RiskLevel
    message: str
    timestamp: datetime
    symbol: Optional[str] = None
    value: Optional[float] = None
    threshold: Optional[float] = None

class RiskManager:
    """리스크 관리 클래스"""
    
    def __init__(self, initial_capital: float = INITIAL_CAPITAL):
        """
        초기화
        
        Args:
            initial_capital (float): 초기 자본
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.base_max_position_size = MAX_POSITION_SIZE
        self.base_stop_loss_pct = STOP_LOSS_PCT
        self.base_take_profit_pct = TAKE_PROFIT_PCT
        self.base_max_daily_loss = MAX_DAILY_LOSS
        
        # 리스크 한도
        self.max_position_size = MAX_POSITION_SIZE
        self.max_daily_loss = MAX_DAILY_LOSS
        self.stop_loss_pct = STOP_LOSS_PCT
        self.take_profit_pct = TAKE_PROFIT_PCT
        
        # 모니터링 데이터
        self.daily_pnl_history = []
        self.position_risks = {}
        self.risk_alerts = []
        
        # 긴급 정지 플래그
        self.emergency_stop = False
        self.market_filter_state: Dict[str, Any] = {
            'allow_trading': True,
            'position_size_multiplier': 1.0,
            'reasons': []
        }
        self.market_blocked = False
        
        logger.info("리스크 관리자 초기화 완료")
    
    def check_portfolio_risk(self, portfolio_value: float, 
                           positions: Dict, 
                           current_prices: Dict[str, float]) -> List[RiskAlert]:
        """
        포트폴리오 리스크 체크
        
        Args:
            portfolio_value (float): 현재 포트폴리오 가치
            positions (Dict): 보유 포지션
            current_prices (Dict[str, float]): 현재 가격
        
        Returns:
            List[RiskAlert]: 리스크 알림 리스트
        """
        alerts = []
        
        # 전체 포트폴리오 리스크
        alerts.extend(self._check_total_portfolio_risk(portfolio_value))
        
        # 개별 포지션 리스크
        alerts.extend(self._check_position_risks(positions, current_prices))
        
        # 일일 손실 리스크
        alerts.extend(self._check_daily_loss_risk(portfolio_value))
        
        # 집중도 리스크
        alerts.extend(self._check_concentration_risk(positions, portfolio_value))
        
        # 변동성 리스크
        alerts.extend(self._check_volatility_risk(positions, current_prices))
        
        return alerts
    
    def apply_market_filter(self, filter_signal: Dict[str, Any]):
        """시장 필터에 따른 리스크 파라미터 조정"""
        if not filter_signal:
            return
        
        self.market_filter_state = filter_signal
        multiplier = max(filter_signal.get('position_size_multiplier', 1.0), 0.0)
        self.market_blocked = not filter_signal.get('allow_trading', True)
        
        # 포지션 한도 조정
        adjusted_position_size = self.base_max_position_size * multiplier
        adjusted_position_size = min(adjusted_position_size, self.base_max_position_size)
        adjusted_position_size = max(adjusted_position_size, MIN_POSITION_SIZE)
        self.max_position_size = adjusted_position_size
        
        # 일일 손실 한도도 함께 조정 (최소 50% 유지)
        self.max_daily_loss = max(self.base_max_daily_loss * multiplier, self.base_max_daily_loss * 0.5)
        
        if self.market_blocked:
            logger.warning(f"시장 필터로 거래 제한: {', '.join(filter_signal.get('reasons', []))}")
    
    def allows_trading(self) -> bool:
        """시장 및 리스크 상태 기준 거래 가능 여부"""
        return not self.market_blocked and not self.emergency_stop
    
    def _check_total_portfolio_risk(self, portfolio_value: float) -> List[RiskAlert]:
        """전체 포트폴리오 리스크 체크"""
        alerts = []
        
        # 총 손실률 계산
        total_loss_pct = (self.initial_capital - portfolio_value) / self.initial_capital
        
        if total_loss_pct > 0.20:  # 20% 이상 손실
            alerts.append(RiskAlert(
                level=RiskLevel.CRITICAL,
                message=f"전체 포트폴리오 손실률이 {total_loss_pct:.2%}에 도달했습니다",
                timestamp=datetime.now(),
                value=total_loss_pct,
                threshold=0.20
            ))
            self.emergency_stop = True
            
        elif total_loss_pct > 0.15:  # 15% 이상 손실
            alerts.append(RiskAlert(
                level=RiskLevel.HIGH,
                message=f"전체 포트폴리오 손실률이 {total_loss_pct:.2%}에 도달했습니다",
                timestamp=datetime.now(),
                value=total_loss_pct,
                threshold=0.15
            ))
            
        elif total_loss_pct > 0.10:  # 10% 이상 손실
            alerts.append(RiskAlert(
                level=RiskLevel.MEDIUM,
                message=f"전체 포트폴리오 손실률이 {total_loss_pct:.2%}에 도달했습니다",
                timestamp=datetime.now(),
                value=total_loss_pct,
                threshold=0.10
            ))
        
        return alerts
    
    def _check_position_risks(self, positions: Dict, 
                            current_prices: Dict[str, float]) -> List[RiskAlert]:
        """개별 포지션 리스크 체크"""
        alerts = []
        
        for symbol, position in positions.items():
            current_price = current_prices.get(symbol, position.current_price)
            
            # 손절매 체크
            loss_pct = (position.avg_price - current_price) / position.avg_price
            if loss_pct > self.stop_loss_pct:
                alerts.append(RiskAlert(
                    level=RiskLevel.HIGH,
                    message=f"{symbol} 손절매 신호: {loss_pct:.2%} 손실",
                    timestamp=datetime.now(),
                    symbol=symbol,
                    value=loss_pct,
                    threshold=self.stop_loss_pct
                ))
            
            # 익절매 체크
            profit_pct = (current_price - position.avg_price) / position.avg_price
            if profit_pct > self.take_profit_pct:
                alerts.append(RiskAlert(
                    level=RiskLevel.LOW,
                    message=f"{symbol} 익절매 신호: {profit_pct:.2%} 수익",
                    timestamp=datetime.now(),
                    symbol=symbol,
                    value=profit_pct,
                    threshold=self.take_profit_pct
                ))
            
            # 포지션 크기 체크
            position_value = current_price * position.quantity
            position_ratio = position_value / self.current_capital
            
            if position_ratio > self.max_position_size:
                alerts.append(RiskAlert(
                    level=RiskLevel.MEDIUM,
                    message=f"{symbol} 포지션 크기 초과: {position_ratio:.2%}",
                    timestamp=datetime.now(),
                    symbol=symbol,
                    value=position_ratio,
                    threshold=self.max_position_size
                ))
        
        return alerts
    
    def _check_daily_loss_risk(self, portfolio_value: float) -> List[RiskAlert]:
        """일일 손실 리스크 체크"""
        alerts = []
        
        # 일일 손실 계산
        today = date.today()
        daily_loss = self._calculate_daily_loss(portfolio_value, today)
        
        if daily_loss > self.max_daily_loss:
            alerts.append(RiskAlert(
                level=RiskLevel.CRITICAL,
                message=f"일일 손실 한도 초과: ${daily_loss:.2f}",
                timestamp=datetime.now(),
                value=daily_loss,
                threshold=self.max_daily_loss
            ))
            self.emergency_stop = True
            
        elif daily_loss > self.max_daily_loss * 0.8:  # 80% 도달
            alerts.append(RiskAlert(
                level=RiskLevel.HIGH,
                message=f"일일 손실 한도 80% 도달: ${daily_loss:.2f}",
                timestamp=datetime.now(),
                value=daily_loss,
                threshold=self.max_daily_loss * 0.8
            ))
        
        return alerts
    
    def _check_concentration_risk(self, positions: Dict, 
                                portfolio_value: float) -> List[RiskAlert]:
        """집중도 리스크 체크"""
        alerts = []
        
        if not positions:
            return alerts
        
        # 최대 포지션 비중
        max_position_ratio = 0
        max_symbol = None
        
        for symbol, position in positions.items():
            position_ratio = (position.current_price * position.quantity) / portfolio_value
            if position_ratio > max_position_ratio:
                max_position_ratio = position_ratio
                max_symbol = symbol
        
        # 집중도 경고
        if max_position_ratio > 0.3:  # 30% 이상
            alerts.append(RiskAlert(
                level=RiskLevel.HIGH,
                message=f"포지션 집중도 높음: {max_symbol} {max_position_ratio:.2%}",
                timestamp=datetime.now(),
                symbol=max_symbol,
                value=max_position_ratio,
                threshold=0.30
            ))
        elif max_position_ratio > 0.2:  # 20% 이상
            alerts.append(RiskAlert(
                level=RiskLevel.MEDIUM,
                message=f"포지션 집중도 주의: {max_symbol} {max_position_ratio:.2%}",
                timestamp=datetime.now(),
                symbol=max_symbol,
                value=max_position_ratio,
                threshold=0.20
            ))
        
        return alerts
    
    def _check_volatility_risk(self, positions: Dict, 
                             current_prices: Dict[str, float]) -> List[RiskAlert]:
        """변동성 리스크 체크"""
        alerts = []
        
        # 간단한 변동성 체크 (실제로는 더 정교한 계산 필요)
        for symbol, position in positions.items():
            current_price = current_prices.get(symbol, position.current_price)
            
            # 일일 변동률
            daily_change = abs(current_price - position.avg_price) / position.avg_price
            
            if daily_change > 0.10:  # 10% 이상 변동
                alerts.append(RiskAlert(
                    level=RiskLevel.MEDIUM,
                    message=f"{symbol} 높은 변동성: {daily_change:.2%}",
                    timestamp=datetime.now(),
                    symbol=symbol,
                    value=daily_change,
                    threshold=0.10
                ))
        
        return alerts
    
    def calculate_position_size(self, symbol: str, price: float, 
                              risk_percentage: float = None) -> int:
        """
        안전한 포지션 크기 계산
        
        Args:
            symbol (str): 종목 코드
            price (float): 가격
            risk_percentage (float): 리스크 비율
        
        Returns:
            int: 권장 포지션 크기
        """
        if risk_percentage is None:
            risk_percentage = self.max_position_size
        
        # 사용 가능한 자본
        available_capital = self.current_capital * 0.95  # 5% 여유분
        
        # 포지션 크기 계산
        position_value = available_capital * risk_percentage
        quantity = int(position_value / price)
        
        # 최소/최대 수량 제한
        min_quantity = 1
        max_quantity = int(available_capital * 0.5 / price)  # 최대 50%
        
        quantity = max(min_quantity, min(quantity, max_quantity))
        
        logger.debug(f"포지션 크기 계산: {symbol} - {quantity}주 (${price:.2f})")
        
        return quantity
    
    def should_stop_trading(self) -> bool:
        """거래 중지 여부 확인"""
        return self.emergency_stop
    
    def reset_emergency_stop(self):
        """긴급 정지 해제"""
        self.emergency_stop = False
        logger.info("긴급 정지 해제")
    
    def _calculate_daily_loss(self, current_value: float, target_date: date) -> float:
        """일일 손실 계산"""
        # 간단한 구현 (실제로는 더 정교한 계산 필요)
        daily_loss = max(0, self.initial_capital - current_value)
        return daily_loss
    
    def update_capital(self, new_capital: float):
        """자본 업데이트"""
        self.current_capital = new_capital
        logger.info(f"자본 업데이트: ${new_capital:,.2f}")
    
    def get_risk_summary(self) -> Dict:
        """리스크 요약 반환"""
        return {
            'emergency_stop': self.emergency_stop,
            'market_blocked': self.market_blocked,
            'current_capital': self.current_capital,
            'max_position_size': self.max_position_size,
            'max_daily_loss': self.max_daily_loss,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct,
            'market_filter': self.market_filter_state,
            'recent_alerts': len([a for a in self.risk_alerts 
                                if (datetime.now() - a.timestamp).days <= 1])
        }
    
    def log_risk_alerts(self, alerts: List[RiskAlert]):
        """리스크 알림 로그"""
        for alert in alerts:
            self.risk_alerts.append(alert)
            
            if alert.level == RiskLevel.CRITICAL:
                logger.critical(f"CRITICAL RISK: {alert.message}")
            elif alert.level == RiskLevel.HIGH:
                logger.warning(f"HIGH RISK: {alert.message}")
            elif alert.level == RiskLevel.MEDIUM:
                logger.warning(f"MEDIUM RISK: {alert.message}")
            else:
                logger.info(f"LOW RISK: {alert.message}")
    
    def adapt_to_market_conditions(self, market_filter: Dict, macro_env: Optional[Dict] = None):
        """
        시장 및 거시경제 조건에 따라 리스크 파라미터 조정
        
        Args:
            market_filter (Dict): 시장 필터 정보
            macro_env (Optional[Dict]): 거시경제 환경 정보
        """
        if not market_filter:
            return
        
        # 시장 필터 상태 저장
        self.market_filter_state = market_filter
        
        # 거래 차단 여부
        if not market_filter.get('allow_trading', True):
            self.market_blocked = True
            reasons = market_filter.get('reasons', [])
            logger.warning(f"시장 필터에 의해 거래 차단: {', '.join(reasons)}")
            return
        else:
            self.market_blocked = False
        
        # 포지션 크기 조정
        filter_multiplier = market_filter.get('position_size_multiplier', 1.0)
        
        # 거시경제 환경 반영
        if macro_env:
            env = macro_env.get('environment', 'NEUTRAL')
            macro_multiplier = macro_env.get('position_multiplier', 1.0)
            
            if env == 'VERY_UNFAVORABLE':
                # 초방어 모드
                self.max_position_size = self.base_max_position_size * 0.3
                self.stop_loss_pct = self.base_stop_loss_pct * 0.7  # 타이트하게
                self.max_daily_loss = self.base_max_daily_loss * 0.5  # 더 보수적으로
                logger.warning(f"거시경제 환경 매우 불리 ({env}) → 초방어 모드")
                logger.warning(f"  - 최대 포지션: {self.max_position_size:.1%}")
                logger.warning(f"  - 손절: {self.stop_loss_pct:.1%}")
                
            elif env == 'UNFAVORABLE':
                # 방어 모드
                self.max_position_size = self.base_max_position_size * 0.5
                self.stop_loss_pct = self.base_stop_loss_pct * 0.85
                logger.info(f"거시경제 환경 불리 ({env}) → 방어 모드")
                
            elif env == 'VERY_FAVORABLE':
                # 공격 모드
                self.max_position_size = self.base_max_position_size * 1.3
                self.take_profit_pct = self.base_take_profit_pct * 1.5  # 더 많이
                logger.info(f"거시경제 환경 매우 유리 ({env}) → 공격 모드")
                logger.info(f"  - 최대 포지션: {self.max_position_size:.1%}")
                logger.info(f"  - 익절: {self.take_profit_pct:.1%}")
                
            elif env == 'FAVORABLE':
                # 적극 모드
                self.max_position_size = self.base_max_position_size * 1.1
                self.take_profit_pct = self.base_take_profit_pct * 1.2
                logger.info(f"거시경제 환경 유리 ({env}) → 적극 모드")
                
            else:  # NEUTRAL
                # 기본 모드
                self.max_position_size = self.base_max_position_size
                self.stop_loss_pct = self.base_stop_loss_pct
                self.take_profit_pct = self.base_take_profit_pct
                self.max_daily_loss = self.base_max_daily_loss
            
            # 시장 필터와 결합
            self.max_position_size *= filter_multiplier
            
            # 거시경제 신호 로깅
            signals = macro_env.get('signals', [])
            if signals:
                logger.info(f"거시경제 신호: {', '.join(signals[:3])}")
        
        else:
            # 거시경제 정보 없으면 시장 필터만 적용
            self.max_position_size = self.base_max_position_size * filter_multiplier
            
            if filter_multiplier < 1.0:
                logger.info(f"시장 필터에 의한 포지션 축소: {filter_multiplier:.2f}x")
            elif filter_multiplier > 1.0:
                logger.info(f"시장 필터에 의한 포지션 확대: {filter_multiplier:.2f}x")

class StopLossManager:
    """손절매 관리 클래스"""
    
    def __init__(self, stop_loss_pct: float = STOP_LOSS_PCT):
        """
        초기화
        
        Args:
            stop_loss_pct (float): 손절매 비율
        """
        self.stop_loss_pct = stop_loss_pct
        self.stop_loss_orders = {}
        
    def set_stop_loss(self, symbol: str, entry_price: float, quantity: int):
        """
        손절매 주문 설정
        
        Args:
            symbol (str): 종목 코드
            entry_price (float): 진입 가격
            quantity (int): 수량
        """
        stop_price = entry_price * (1 - self.stop_loss_pct)
        
        self.stop_loss_orders[symbol] = {
            'stop_price': stop_price,
            'quantity': quantity,
            'entry_price': entry_price,
            'set_time': datetime.now()
        }
        
        logger.info(f"손절매 설정: {symbol} @ ${stop_price:.2f}")
    
    def check_stop_loss(self, symbol: str, current_price: float) -> bool:
        """
        손절매 체크
        
        Args:
            symbol (str): 종목 코드
            current_price (float): 현재 가격
        
        Returns:
            bool: 손절매 실행 여부
        """
        if symbol not in self.stop_loss_orders:
            return False
        
        stop_order = self.stop_loss_orders[symbol]
        stop_price = stop_order['stop_price']
        
        if current_price <= stop_price:
            logger.warning(f"손절매 실행: {symbol} @ ${current_price:.2f} (손절가: ${stop_price:.2f})")
            del self.stop_loss_orders[symbol]
            return True
        
        return False
    
    def remove_stop_loss(self, symbol: str):
        """손절매 주문 제거"""
        if symbol in self.stop_loss_orders:
            del self.stop_loss_orders[symbol]
            logger.info(f"손절매 제거: {symbol}")

class TakeProfitManager:
    """익절매 관리 클래스"""
    
    def __init__(self, take_profit_pct: float = TAKE_PROFIT_PCT):
        """
        초기화
        
        Args:
            take_profit_pct (float): 익절매 비율
        """
        self.take_profit_pct = take_profit_pct
        self.take_profit_orders = {}
    
    def set_take_profit(self, symbol: str, entry_price: float, quantity: int):
        """
        익절매 주문 설정
        
        Args:
            symbol (str): 종목 코드
            entry_price (float): 진입 가격
            quantity (int): 수량
        """
        take_profit_price = entry_price * (1 + self.take_profit_pct)
        
        self.take_profit_orders[symbol] = {
            'take_profit_price': take_profit_price,
            'quantity': quantity,
            'entry_price': entry_price,
            'set_time': datetime.now()
        }
        
        logger.info(f"익절매 설정: {symbol} @ ${take_profit_price:.2f}")
    
    def check_take_profit(self, symbol: str, current_price: float) -> bool:
        """
        익절매 체크
        
        Args:
            symbol (str): 종목 코드
            current_price (float): 현재 가격
        
        Returns:
            bool: 익절매 실행 여부
        """
        if symbol not in self.take_profit_orders:
            return False
        
        take_profit_order = self.take_profit_orders[symbol]
        take_profit_price = take_profit_order['take_profit_price']
        
        if current_price >= take_profit_price:
            logger.info(f"익절매 실행: {symbol} @ ${current_price:.2f} (익절가: ${take_profit_price:.2f})")
            del self.take_profit_orders[symbol]
            return True
        
        return False
    
    def remove_take_profit(self, symbol: str):
        """익절매 주문 제거"""
        if symbol in self.take_profit_orders:
            del self.take_profit_orders[symbol]
            logger.info(f"익절매 제거: {symbol}")

# 전역 리스크 관리자 인스턴스
risk_manager = RiskManager()
stop_loss_manager = StopLossManager()
take_profit_manager = TakeProfitManager()

def check_portfolio_risk(portfolio_value: float, positions: Dict, 
                        current_prices: Dict[str, float]) -> List[RiskAlert]:
    """
    편의 함수: 포트폴리오 리스크 체크
    
    Args:
        portfolio_value (float): 현재 포트폴리오 가치
        positions (Dict): 보유 포지션
        current_prices (Dict[str, float]): 현재 가격
    
    Returns:
        List[RiskAlert]: 리스크 알림 리스트
    """
    return risk_manager.check_portfolio_risk(portfolio_value, positions, current_prices)


"""
포지션 사이징 및 리스크 관리 모듈
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from config import *
from utils.logger import setup_logger

logger = setup_logger("position_manager")

class PositionManager:
    """포지션 및 리스크 관리 클래스"""
    
    def __init__(self, initial_capital: float = INITIAL_CAPITAL):
        """
        초기화
        
        Args:
            initial_capital (float): 초기 자본
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}  # {symbol: Position}
        self.closed_positions = []  # 청산된 포지션 기록
        
        # 리스크 관리 파라미터
        self.max_position_size = 0.2  # 단일 종목 최대 20%
        self.max_portfolio_risk = 0.06  # 포트폴리오 전체 최대 리스크 6%
        self.max_daily_loss = 0.02  # 일일 최대 손실 2%
        self.max_weekly_loss = 0.05  # 주간 최대 손실 5%
        self.max_positions = 5  # 최대 보유 종목 수
        
        # 켈리 공식 파라미터
        self.win_rate = 0.35  # 목표 승률 35%
        self.avg_win_loss_ratio = 2.0  # 평균 수익/손실 비율
        
        # 추적 변수
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.last_reset_date = datetime.now()
        
    def calculate_kelly_fraction(self, win_rate: Optional[float] = None, 
                               win_loss_ratio: Optional[float] = None) -> float:
        """
        켈리 공식을 사용한 최적 베팅 비율 계산
        
        Kelly % = (bp - q) / b
        where:
        b = 수익/손실 비율
        p = 승률
        q = 1 - p (패율)
        
        Args:
            win_rate (float): 승률 (0-1)
            win_loss_ratio (float): 평균 수익/손실 비율
        
        Returns:
            float: 최적 베팅 비율 (0-1)
        """
        p = win_rate or self.win_rate
        b = win_loss_ratio or self.avg_win_loss_ratio
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b
        
        # 켈리 비율의 25%만 사용 (보수적 접근)
        conservative_kelly = kelly_fraction * 0.25
        
        # 최소 1%, 최대 20%로 제한
        return max(0.01, min(0.2, conservative_kelly))
    
    def calculate_position_size(self, symbol: str, price: float, 
                              stop_loss_pct: float, volatility: float,
                              signal_strength: float = 1.0) -> Tuple[int, float]:
        """
        포지션 크기 계산 (리스크 기반)
        
        Args:
            symbol (str): 종목 코드
            price (float): 현재 가격
            stop_loss_pct (float): 손절 비율
            volatility (float): 변동성 (ATR/Price)
            signal_strength (float): 신호 강도 (0-1)
        
        Returns:
            Tuple[int, float]: (주식 수, 포지션 금액)
        """
        # 1. 켈리 기반 기본 포지션 크기
        kelly_fraction = self.calculate_kelly_fraction()
        base_position_value = self.current_capital * kelly_fraction
        
        # 2. 리스크 기반 조정
        # 단일 거래 최대 리스크: 자본의 1%
        max_risk_per_trade = self.current_capital * 0.01
        position_value_risk_based = max_risk_per_trade / stop_loss_pct
        
        # 3. 변동성 조정
        # 변동성이 높을수록 포지션 축소
        volatility_multiplier = 1.0 / (1.0 + volatility * 10)
        
        # 4. 신호 강도 조정
        signal_multiplier = 0.5 + (signal_strength * 0.5)  # 0.5 ~ 1.0
        
        # 최종 포지션 크기 결정
        position_value = min(
            base_position_value,
            position_value_risk_based
        ) * volatility_multiplier * signal_multiplier
        
        # 최대 포지션 크기 제한
        max_position = self.current_capital * self.max_position_size
        position_value = min(position_value, max_position)
        
        # 주식 수 계산
        shares = int(position_value / price)
        
        # 최소 1주
        shares = max(1, shares)
        
        # 실제 포지션 금액
        actual_position_value = shares * price
        
        logger.info(f"{symbol} 포지션 크기 계산: {shares}주 (${actual_position_value:.2f})")
        
        return shares, actual_position_value
    
    def check_risk_limits(self) -> Dict[str, bool]:
        """
        리스크 한도 확인
        
        Returns:
            Dict[str, bool]: 각 리스크 한도 준수 여부
        """
        current_date = datetime.now()
        
        # 일일 리셋 확인
        if current_date.date() > self.last_reset_date.date():
            self.daily_pnl = 0.0
            
        # 주간 리셋 확인
        if (current_date - self.last_reset_date).days >= 7:
            self.weekly_pnl = 0.0
            self.last_reset_date = current_date
        
        checks = {
            'daily_loss_ok': self.daily_pnl > -self.max_daily_loss * self.initial_capital,
            'weekly_loss_ok': self.weekly_pnl > -self.max_weekly_loss * self.initial_capital,
            'position_count_ok': len(self.positions) < self.max_positions,
            'portfolio_risk_ok': self.calculate_portfolio_risk() < self.max_portfolio_risk
        }
        
        return checks
    
    def calculate_portfolio_risk(self) -> float:
        """
        포트폴리오 전체 리스크 계산
        
        Returns:
            float: 포트폴리오 리스크 비율
        """
        if not self.positions:
            return 0.0
        
        total_risk = 0.0
        
        for symbol, position in self.positions.items():
            position_risk = position['value'] * position['stop_loss_pct']
            total_risk += position_risk
        
        return total_risk / self.current_capital
    
    def can_open_position(self, symbol: str) -> Tuple[bool, str]:
        """
        새 포지션 개설 가능 여부 확인
        
        Args:
            symbol (str): 종목 코드
        
        Returns:
            Tuple[bool, str]: (가능 여부, 불가 사유)
        """
        # 이미 보유 중인지 확인
        if symbol in self.positions:
            return False, "이미 보유 중인 종목"
        
        # 리스크 한도 확인
        risk_checks = self.check_risk_limits()
        
        if not risk_checks['daily_loss_ok']:
            return False, "일일 손실 한도 초과"
        
        if not risk_checks['weekly_loss_ok']:
            return False, "주간 손실 한도 초과"
        
        if not risk_checks['position_count_ok']:
            return False, "최대 보유 종목 수 초과"
        
        if not risk_checks['portfolio_risk_ok']:
            return False, "포트폴리오 리스크 한도 초과"
        
        return True, "OK"
    
    def open_position(self, symbol: str, shares: int, price: float, 
                     stop_loss: float, take_profit: float,
                     signal_strength: float = 1.0) -> bool:
        """
        포지션 개설
        
        Args:
            symbol (str): 종목 코드
            shares (int): 주식 수
            price (float): 진입 가격
            stop_loss (float): 손절 가격
            take_profit (float): 익절 가격
            signal_strength (float): 신호 강도
        
        Returns:
            bool: 성공 여부
        """
        can_open, reason = self.can_open_position(symbol)
        if not can_open:
            logger.warning(f"{symbol} 포지션 개설 불가: {reason}")
            return False
        
        position_value = shares * price
        
        self.positions[symbol] = {
            'shares': shares,
            'entry_price': price,
            'entry_date': datetime.now(),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'stop_loss_pct': (price - stop_loss) / price,
            'take_profit_pct': (take_profit - price) / price,
            'value': position_value,
            'signal_strength': signal_strength,
            'unrealized_pnl': 0.0
        }
        
        logger.info(f"{symbol} 포지션 개설: {shares}주 @ ${price:.2f}")
        
        return True
    
    def close_position(self, symbol: str, price: float, reason: str = "Manual") -> Optional[Dict]:
        """
        포지션 청산
        
        Args:
            symbol (str): 종목 코드
            price (float): 청산 가격
            reason (str): 청산 사유
        
        Returns:
            Optional[Dict]: 청산 결과
        """
        if symbol not in self.positions:
            logger.warning(f"{symbol} 포지션이 존재하지 않음")
            return None
        
        position = self.positions[symbol]
        
        # 손익 계산
        pnl = (price - position['entry_price']) * position['shares']
        pnl_pct = (price - position['entry_price']) / position['entry_price']
        
        # 보유 기간
        holding_days = (datetime.now() - position['entry_date']).days
        
        # 청산 기록
        closed_position = {
            'symbol': symbol,
            'shares': position['shares'],
            'entry_price': position['entry_price'],
            'exit_price': price,
            'entry_date': position['entry_date'],
            'exit_date': datetime.now(),
            'holding_days': holding_days,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason
        }
        
        self.closed_positions.append(closed_position)
        
        # 자본 업데이트
        self.current_capital += pnl
        self.daily_pnl += pnl
        self.weekly_pnl += pnl
        
        # 포지션 제거
        del self.positions[symbol]
        
        logger.info(f"{symbol} 포지션 청산: {position['shares']}주 @ ${price:.2f}, "
                   f"손익: ${pnl:.2f} ({pnl_pct*100:.2f}%), 사유: {reason}")
        
        return closed_position
    
    def update_positions(self, current_prices: Dict[str, float]) -> List[Dict]:
        """
        포지션 업데이트 및 손절/익절 확인
        
        Args:
            current_prices (Dict[str, float]): 현재 가격 {symbol: price}
        
        Returns:
            List[Dict]: 청산된 포지션 리스트
        """
        closed_positions = []
        
        for symbol, position in list(self.positions.items()):
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            
            # 미실현 손익 업데이트
            position['unrealized_pnl'] = (current_price - position['entry_price']) * position['shares']
            
            # 손절 확인
            if current_price <= position['stop_loss']:
                result = self.close_position(symbol, current_price, "Stop Loss")
                if result:
                    closed_positions.append(result)
            
            # 익절 확인
            elif current_price >= position['take_profit']:
                result = self.close_position(symbol, current_price, "Take Profit")
                if result:
                    closed_positions.append(result)
            
            # 시간 기반 청산 (선택적)
            elif (datetime.now() - position['entry_date']).days > 30:
                result = self.close_position(symbol, current_price, "Time Stop (30 days)")
                if result:
                    closed_positions.append(result)
        
        return closed_positions
    
    def get_portfolio_summary(self) -> Dict:
        """
        포트폴리오 요약 정보
        
        Returns:
            Dict: 포트폴리오 요약
        """
        total_value = self.current_capital
        positions_value = sum(p['value'] + p['unrealized_pnl'] for p in self.positions.values())
        cash = self.current_capital - sum(p['value'] for p in self.positions.values())
        
        # 승률 계산
        if self.closed_positions:
            winning_trades = [p for p in self.closed_positions if p['pnl'] > 0]
            win_rate = len(winning_trades) / len(self.closed_positions)
            
            # 평균 수익/손실
            avg_win = np.mean([p['pnl'] for p in winning_trades]) if winning_trades else 0
            losing_trades = [p for p in self.closed_positions if p['pnl'] <= 0]
            avg_loss = np.mean([abs(p['pnl']) for p in losing_trades]) if losing_trades else 0
            
            profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
        else:
            win_rate = 0
            profit_factor = 0
        
        return {
            'total_value': total_value + sum(p['unrealized_pnl'] for p in self.positions.values()),
            'cash': cash,
            'positions_value': positions_value,
            'num_positions': len(self.positions),
            'total_trades': len(self.closed_positions),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'daily_pnl': self.daily_pnl,
            'weekly_pnl': self.weekly_pnl,
            'total_pnl': self.current_capital - self.initial_capital,
            'total_return': (self.current_capital - self.initial_capital) / self.initial_capital
        }
    
    def reset_daily_stats(self):
        """일일 통계 리셋"""
        self.daily_pnl = 0.0
        
    def reset_weekly_stats(self):
        """주간 통계 리셋"""
        self.weekly_pnl = 0.0
        self.last_reset_date = datetime.now()

# 전역 포지션 매니저 인스턴스
position_manager = PositionManager()

def calculate_optimal_position_size(symbol: str, price: float, 
                                  stop_loss_pct: float, volatility: float,
                                  signal_strength: float = 1.0) -> Tuple[int, float]:
    """
    편의 함수: 최적 포지션 크기 계산
    
    Args:
        symbol (str): 종목 코드
        price (float): 현재 가격
        stop_loss_pct (float): 손절 비율
        volatility (float): 변동성
        signal_strength (float): 신호 강도
    
    Returns:
        Tuple[int, float]: (주식 수, 포지션 금액)
    """
    return position_manager.calculate_position_size(
        symbol, price, stop_loss_pct, volatility, signal_strength
    )

def can_trade(symbol: str) -> Tuple[bool, str]:
    """
    편의 함수: 거래 가능 여부 확인
    
    Args:
        symbol (str): 종목 코드
    
    Returns:
        Tuple[bool, str]: (가능 여부, 불가 사유)
    """
    return position_manager.can_open_position(symbol)

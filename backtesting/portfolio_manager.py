"""
포트폴리오 관리 모듈
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass
from enum import Enum

from config import *
from utils.logger import setup_logger

logger = setup_logger("portfolio_manager")

class OrderType(Enum):
    """주문 타입"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    entry_date: date
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    def update_price(self, price: float):
        """현재 가격 업데이트"""
        self.current_price = price
        self.unrealized_pnl = (price - self.avg_price) * self.quantity
    
    @property
    def market_value(self) -> float:
        """시장 가치"""
        return self.current_price * self.quantity
    
    @property
    def total_pnl(self) -> float:
        """총 손익"""
        return self.unrealized_pnl + self.realized_pnl

@dataclass
class Trade:
    """거래 기록"""
    symbol: str
    order_type: OrderType
    quantity: int
    price: float
    timestamp: datetime
    commission: float = 0.0
    pnl: float = 0.0

class PortfolioManager:
    """포트폴리오 관리 클래스"""
    
    def __init__(self, initial_capital: float = INITIAL_CAPITAL):
        """
        초기화
        
        Args:
            initial_capital (float): 초기 자본
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.daily_values: List[Dict] = []
        self.portfolio_history: List[Dict] = []
        
        # 성과 추적
        self.total_commission = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """
        포트폴리오 총 가치 계산
        
        Args:
            current_prices (Dict[str, float]): 현재 가격 딕셔너리
        
        Returns:
            float: 포트폴리오 총 가치
        """
        # 포지션 가치 업데이트
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                position.update_price(current_prices[symbol])
        
        # 총 가치 계산
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + positions_value
    
    def execute_trade(self, 
                     symbol: str, 
                     order_type: OrderType, 
                     quantity: int, 
                     price: float,
                     timestamp: datetime,
                     commission: float = COMMISSION) -> bool:
        """
        거래 실행
        
        Args:
            symbol (str): 종목 코드
            order_type (OrderType): 주문 타입
            quantity (int): 수량
            price (float): 가격
            timestamp (datetime): 거래 시간
            commission (float): 수수료
        
        Returns:
            bool: 거래 실행 성공 여부
        """
        try:
            if order_type == OrderType.BUY:
                return self._execute_buy(symbol, quantity, price, timestamp, commission)
            elif order_type == OrderType.SELL:
                return self._execute_sell(symbol, quantity, price, timestamp, commission)
            else:
                return True  # HOLD는 아무것도 하지 않음
                
        except Exception as e:
            logger.error(f"거래 실행 실패 {symbol}: {str(e)}")
            return False
    
    def _execute_buy(self, symbol: str, quantity: int, price: float, 
                    timestamp: datetime, commission: float) -> bool:
        """매수 실행"""
        total_cost = quantity * price + commission
        
        # 현금 부족 확인
        if self.cash < total_cost:
            logger.warning(f"현금 부족으로 매수 실패: {symbol} - 필요: ${total_cost:.2f}, 보유: ${self.cash:.2f}")
            return False
        
        # 포지션 업데이트
        if symbol in self.positions:
            # 기존 포지션에 추가
            pos = self.positions[symbol]
            total_quantity = pos.quantity + quantity
            total_cost_basis = (pos.avg_price * pos.quantity) + (price * quantity)
            pos.avg_price = total_cost_basis / total_quantity
            pos.quantity = total_quantity
        else:
            # 새 포지션 생성
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_price=price,
                current_price=price,
                entry_date=timestamp.date()
            )
        
        # 현금 차감
        self.cash -= total_cost
        
        # 거래 기록
        trade = Trade(
            symbol=symbol,
            order_type=OrderType.BUY,
            quantity=quantity,
            price=price,
            timestamp=timestamp,
            commission=commission
        )
        self.trades.append(trade)
        
        # 통계 업데이트
        self.total_commission += commission
        self.total_trades += 1
        
        logger.info(f"매수 완료: {quantity} {symbol} @ ${price:.2f}")
        return True
    
    def _execute_sell(self, symbol: str, quantity: int, price: float,
                     timestamp: datetime, commission: float) -> bool:
        """매도 실행"""
        # 포지션 확인
        if symbol not in self.positions:
            logger.warning(f"보유하지 않은 종목 매도 시도: {symbol}")
            return False
        
        pos = self.positions[symbol]
        
        # 수량 확인
        if pos.quantity < quantity:
            logger.warning(f"보유 수량 부족: {symbol} - 필요: {quantity}, 보유: {pos.quantity}")
            return False
        
        # 손익 계산
        pnl = (price - pos.avg_price) * quantity - commission
        
        # 포지션 업데이트
        if pos.quantity == quantity:
            # 전체 매도
            pos.realized_pnl += pnl
            del self.positions[symbol]
        else:
            # 부분 매도
            pos.quantity -= quantity
            pos.realized_pnl += pnl
        
        # 현금 추가
        self.cash += (quantity * price - commission)
        
        # 거래 기록
        trade = Trade(
            symbol=symbol,
            order_type=OrderType.SELL,
            quantity=quantity,
            price=price,
            timestamp=timestamp,
            commission=commission,
            pnl=pnl
        )
        self.trades.append(trade)
        
        # 통계 업데이트
        self.total_commission += commission
        self.total_trades += 1
        
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        logger.info(f"매도 완료: {quantity} {symbol} @ ${price:.2f} (손익: ${pnl:.2f})")
        return True
    
    def calculate_position_size(self, symbol: str, price: float, 
                              risk_percentage: float = MAX_POSITION_SIZE) -> int:
        """
        포지션 크기 계산
        
        Args:
            symbol (str): 종목 코드
            price (float): 가격
            risk_percentage (float): 리스크 비율
        
        Returns:
            int: 매수할 수량
        """
        # 사용 가능한 현금
        available_cash = self.cash * 0.95  # 5% 여유분 유지
        
        # 포지션 크기 계산
        position_value = available_cash * risk_percentage
        quantity = int(position_value / price)
        
        return max(0, quantity)
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """포지션 정보 반환"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """모든 포지션 반환"""
        return self.positions.copy()
    
    def record_daily_value(self, current_prices: Dict[str, float], timestamp: datetime):
        """포트폴리오 스냅샷 기록"""
        portfolio_value = self.get_portfolio_value(current_prices)
        
        daily_record = {
            'date': timestamp.date(),
            'timestamp': timestamp,
            'portfolio_value': portfolio_value,
            'cash': self.cash,
            'positions_value': portfolio_value - self.cash,
            'total_return': (portfolio_value - self.initial_capital) / self.initial_capital,
            'num_positions': len(self.positions),
            'num_trades': len(self.trades)
        }
        
        self.daily_values.append(daily_record)
        self.portfolio_history.append({
            'timestamp': timestamp,
            'total_value': portfolio_value,
            'cash': self.cash
        })
    
    def get_performance_metrics(self) -> Dict:
        """성과 지표 계산"""
        if not self.daily_values:
            return {}

        df = pd.DataFrame(self.daily_values)
        df = df.sort_values('timestamp')

        # 기본 지표
        total_return = (df['portfolio_value'].iloc[-1] - self.initial_capital) / self.initial_capital
        total_trades = len(self.trades)
        win_rate = self.winning_trades / total_trades if total_trades > 0 else 0

        # 일일 수익률
        df['daily_return'] = df['portfolio_value'].pct_change()

        # 샤프 비율
        sharpe_ratio = df['daily_return'].mean() / df['daily_return'].std() * np.sqrt(252) if df['daily_return'].std() > 0 else 0

        # 소르티노 비율 (하방 변동성만 고려)
        downside_returns = df['daily_return'][df['daily_return'] < 0]
        downside_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = df['daily_return'].mean() / downside_volatility * np.sqrt(252) if downside_volatility > 0 else 0

        # 최대 낙폭
        df['cumulative_max'] = df['portfolio_value'].expanding().max()
        df['drawdown'] = (df['portfolio_value'] - df['cumulative_max']) / df['cumulative_max']
        max_drawdown = df['drawdown'].min()

        # 최대 낙폭 기간 계산
        max_drawdown_duration = 0
        current_duration = 0
        for dd in df['drawdown']:
            if dd < 0:
                current_duration += 1
                max_drawdown_duration = max(max_drawdown_duration, current_duration)
            else:
                current_duration = 0

        # 변동성
        volatility = df['daily_return'].std() * np.sqrt(252)

        # 거래 손익 분석 (SELL 거래만)
        trade_history = self.get_trade_history()
        if not trade_history.empty:
            sell_trades = trade_history[trade_history['order_type'] == 'SELL']
            if not sell_trades.empty:
                winning_trades = sell_trades[sell_trades['pnl'] > 0]
                losing_trades = sell_trades[sell_trades['pnl'] < 0]

                avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
                avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0

                total_wins = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
                total_losses = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
                profit_factor = total_wins / total_losses if total_losses > 0 else 0
            else:
                avg_win = 0
                avg_loss = 0
                profit_factor = 0
        else:
            avg_win = 0
            avg_loss = 0
            profit_factor = 0

        return {
            'initial_capital': self.initial_capital,
            'total_return': total_return,
            'annualized_return': (1 + total_return) ** (252 / len(df)) - 1,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'max_drawdown_duration': max_drawdown_duration,
            'volatility': volatility,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_commission': self.total_commission,
            'final_value': df['portfolio_value'].iloc[-1]
        }
    
    def get_trade_history(self) -> pd.DataFrame:
        """거래 내역 반환"""
        if not self.trades:
            return pd.DataFrame()
        
        trades_data = []
        for trade in self.trades:
            trades_data.append({
                'symbol': trade.symbol,
                'order_type': trade.order_type.value,
                'quantity': trade.quantity,
                'price': trade.price,
                'timestamp': trade.timestamp,
                'commission': trade.commission,
                'pnl': trade.pnl
            })
        
        return pd.DataFrame(trades_data)
    
    def reset(self):
        """포트폴리오 초기화"""
        self.cash = self.initial_capital
        self.positions.clear()
        self.trades.clear()
        self.daily_values.clear()
        self.total_commission = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        logger.info("포트폴리오 초기화 완료")


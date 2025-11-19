"""
모의투자 트레이더
실제 돈 없이 거래를 시뮬레이션합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, date, time
import time as time_module
import threading
from dataclasses import dataclass

from config import *
from utils.logger import setup_logger, log_trade, log_signal, log_portfolio
from utils.data_collector import data_collector
from utils.feature_engineering import feature_engineer
from strategies.improved.buy_low_sell_high import get_trading_signal
from utils.position_manager import position_manager
from utils.market_analyzer import market_analyzer
from backtesting.portfolio_manager import PortfolioManager, OrderType

logger = setup_logger("paper_trader")

@dataclass
class PaperPosition:
    """모의투자 포지션"""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    entry_date: date
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

class PaperTrader:
    """모의투자 트레이더 클래스"""
    
    def __init__(self, symbols: List[str]):
        """
        초기화
        
        Args:
            symbols (List[str]): 거래할 종목 리스트
        """
        self.symbols = symbols
        self.portfolio_manager = PortfolioManager(INITIAL_CAPITAL)
        
        # 포지션 매니저 초기화 (개선된 전략)
        position_manager.current_capital = INITIAL_CAPITAL
        position_manager.positions = {}
        position_manager.closed_positions = []
        
        self.is_running = False
        self.trading_thread = None
        
        # 실시간 데이터 저장
        self.current_data: Dict[str, pd.DataFrame] = {}
        self.current_prices: Dict[str, float] = {}
        
        # 거래 제한
        self.daily_trade_count = 0
        self.last_trade_date = None
        
        logger.info(f"모의투자 트레이더 초기화 완료 (개선된 전략 사용) - 종목: {symbols}")
    
    def start_trading(self):
        """거래 시작"""
        logger.info("모의투자 거래 시작")
        self.is_running = True
        
        # 초기 데이터 로드
        self._load_initial_data()
        
        # 거래 스레드 시작
        self.trading_thread = threading.Thread(target=self._trading_loop)
        self.trading_thread.daemon = True
        self.trading_thread.start()
        
        # 메인 스레드에서 포트폴리오 모니터링
        self._monitoring_loop()
    
    def stop_trading(self):
        """거래 중지"""
        logger.info("모의투자 거래 중지")
        self.is_running = False
        
        if self.trading_thread:
            self.trading_thread.join(timeout=5)
        
        # 최종 포트폴리오 상태 로그
        self._log_final_status()
    
    def _load_initial_data(self):
        """초기 데이터 로드"""
        logger.info("초기 데이터 로드 중...")
        
        # 모델 로드 시도
        try:
            from strategies.improved.buy_low_sell_high import improved_strategy
            improved_strategy.load_model()
            logger.info("개선된 전략 모델 로드 완료")
        except Exception as e:
            logger.warning(f"모델 로드 실패 (규칙 기반 전략만 사용): {str(e)}")
        
        for symbol in self.symbols:
            try:
                # 최근 60일 데이터 수집
                data = data_collector.get_latest_data(symbol, days=60)
                if not data.empty:
                    # 기술적 지표 추가
                    data_with_indicators = feature_engineer.add_technical_indicators(data)
                    
                    # 전략 데이터 준비 (개선된 전략용)
                    try:
                        from strategies.improved.buy_low_sell_high import improved_strategy
                        data_with_indicators = improved_strategy.prepare_data(data_with_indicators)
                    except Exception as e:
                        logger.warning(f"전략 데이터 준비 실패 {symbol}: {str(e)}")
                    
                    self.current_data[symbol] = data_with_indicators
                    
                    # 현재 가격 저장
                    if not data_with_indicators.empty:
                        # Date 컬럼이 인덱스인지 확인
                        if 'Date' in data_with_indicators.columns:
                            self.current_prices[symbol] = data_with_indicators.iloc[-1]['CLOSE']
                        elif 'CLOSE' in data_with_indicators.columns:
                            self.current_prices[symbol] = data_with_indicators.iloc[-1]['CLOSE']
                    
                    logger.info(f"데이터 로드 완료: {symbol}")
                else:
                    logger.warning(f"데이터 로드 실패: {symbol}")
                    
            except Exception as e:
                logger.error(f"데이터 로드 오류 {symbol}: {str(e)}")
    
    def _trading_loop(self):
        """거래 루프"""
        logger.info("거래 루프 시작")
        
        while self.is_running:
            try:
                # 미국 장 시간 확인
                if not self._is_market_open():
                    time_module.sleep(300)  # 5분 대기
                    continue
                
                # 일일 거래 제한 확인
                if not self._check_daily_limits():
                    time_module.sleep(3600)  # 1시간 대기
                    continue
                
                # 각 종목별 신호 확인 및 손절/익절 확인
                for symbol in self.symbols:
                    if not self.is_running:
                        break
                    
                    # 손절/익절 확인 (개선된 전략)
                    self._check_stop_loss_take_profit(symbol)
                    
                    # 거래 신호 처리
                    self._process_symbol_signal(symbol)
                
                # 1분 대기
                time_module.sleep(60)
                
            except Exception as e:
                logger.error(f"거래 루프 오류: {str(e)}")
                time_module.sleep(60)
    
    def _monitoring_loop(self):
        """모니터링 루프"""
        logger.info("모니터링 루프 시작")
        
        while self.is_running:
            try:
                # 미국 장 시간 확인
                if self._is_market_open():
                    # 장 시간에만 포트폴리오 상태 로그
                    self._log_portfolio_status()
                    # 5분 대기
                    time_module.sleep(300)
                else:
                    # 장 마감 시간에는 30분 대기
                    logger.debug("장 마감 시간 - 모니터링 대기 중")
                    time_module.sleep(1800)
                
            except Exception as e:
                logger.error(f"모니터링 루프 오류: {str(e)}")
                time_module.sleep(60)
    
    def _is_market_open(self) -> bool:
        """미국 장 시간 확인 (UTC 기준, 썸머타임 자동 적용)"""
        try:
            import pytz
            from datetime import datetime as dt
            
            # 현재 UTC 시간
            now_utc = dt.now(pytz.UTC)
            
            # 미국 동부 시간으로 변환 (EST/EDT 자동 처리)
            eastern = pytz.timezone('US/Eastern')
            now_et = now_utc.astimezone(eastern)
            
            # 주말 체크
            if now_et.weekday() >= 5:  # 토요일(5), 일요일(6)
                logger.info(f"주말입니다. (현재 ET: {now_et.strftime('%Y-%m-%d %H:%M:%S %Z')})")
                return False
            
            # 장 시간: 09:30 - 16:00 ET
            market_open_time = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
            market_close_time = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
            
            is_open = market_open_time <= now_et <= market_close_time
            
            # 장 상태 로그 (간결하게)
            if is_open:
                logger.debug(f"장 개장 중 (ET: {now_et.strftime('%H:%M:%S %Z')})")
            else:
                logger.info(f"장 마감 시간 (현재 ET: {now_et.strftime('%H:%M:%S %Z')}, 장시간: 09:30-16:00)")
            
            return is_open
            
        except ImportError:
            logger.error("pytz 라이브러리가 설치되지 않았습니다. pip install pytz")
            return False
        except Exception as e:
            logger.error(f"장시간 확인 오류: {e}")
            return False
    
    def _check_daily_limits(self) -> bool:
        """일일 거래 제한 확인"""
        today = date.today()
        
        # 날짜가 바뀌면 카운터 리셋
        if self.last_trade_date != today:
            self.daily_trade_count = 0
            self.last_trade_date = today
        
        # 일일 최대 거래 횟수 확인
        max_daily_trades = 20  # 설정 가능
        if self.daily_trade_count >= max_daily_trades:
            return False
        
        return True
    
    def _check_stop_loss_take_profit(self, symbol: str):
        """손절/익절 확인"""
        try:
            # 포지션 확인
            position = self.portfolio_manager.get_position(symbol)
            if not position:
                return
            
            current_price = self.current_prices.get(symbol, 0)
            if current_price <= 0:
                return
            
            # 포지션 매니저에서 손절/익절 가격 확인
            if symbol in position_manager.positions:
                pos_info = position_manager.positions[symbol]
                entry_price = pos_info['entry_price']
                
                # 손절/익절 확인
                price_change = (current_price - entry_price) / entry_price
                
                if price_change <= -STOP_LOSS_PCT or price_change >= TAKE_PROFIT_PCT:
                    # 청산
                    reason = "Stop Loss" if price_change <= -STOP_LOSS_PCT else "Take Profit"
                    
                    # 매도 실행
                    success = self.portfolio_manager.execute_trade(
                        symbol=symbol,
                        order_type=OrderType.SELL,
                        quantity=position.quantity,
                        price=current_price,
                        timestamp=datetime.now(),
                        commission=COMMISSION
                    )
                    
                    if success:
                        self.daily_trade_count += 1
                        position_manager.close_position(symbol, current_price, reason)
                        
                        pnl = (current_price - entry_price) * position.quantity
                        pnl_pct = price_change
                        
                        logger.info(f"{symbol} 자동 청산 ({reason}): {position.quantity}주 @ ${current_price:.2f} "
                                  f"(손익: ${pnl:.2f}, {pnl_pct:.2%})")
        
        except Exception as e:
            logger.debug(f"손절/익절 확인 오류 {symbol}: {str(e)}")
    
    def _process_symbol_signal(self, symbol: str):
        """종목별 신호 처리"""
        try:
            # 시장 필터 확인 (개선된 전략)
            market_filter = market_analyzer.get_market_filter_signal()
            if not market_filter['allow_trading']:
                logger.debug(f"시장 필터로 인해 거래 불가: {market_filter.get('reasons', [])}")
                return
            
            # 최신 데이터 업데이트
            self._update_symbol_data(symbol)
            
            if symbol not in self.current_data or self.current_data[symbol].empty:
                return
            
            # 포지션 제약 확인 (개선된 전략)
            current_date = datetime.now()
            can_trade, reason = position_manager.can_open_position(symbol)
            
            # 거래 신호 생성 (개선된 전략)
            current_capital = self.portfolio_manager.get_portfolio_value(self.current_prices)
            data_for_signal = self.current_data[symbol].reset_index() if 'Date' in self.current_data[symbol].index.names else self.current_data[symbol]
            
            signal_info = get_trading_signal(data_for_signal, symbol, current_capital, market_filter=market_filter)
            
            if signal_info['signal'] == 'HOLD':
                return
            
            # 포지션 제약 확인 (매수 시)
            if signal_info['signal'] == 'BUY' and not can_trade:
                logger.debug(f"포지션 제약으로 인해 거래 불가: {symbol} - {reason}")
                return
            
            # 신호 로그
            log_signal(logger, symbol, signal_info['signal'], 
                      signal_info.get('confidence', 0.0), signal_info)
            
            # 거래 실행
            self._execute_signal(signal_info)
            
        except Exception as e:
            logger.error(f"신호 처리 오류 {symbol}: {str(e)}")
    
    def _update_symbol_data(self, symbol: str):
        """종목 데이터 업데이트"""
        try:
            # 최신 데이터 가져오기
            latest_data = data_collector.get_latest_data(symbol, days=1)
            
            if not latest_data.empty:
                # 기존 데이터에 추가
                if symbol in self.current_data:
                    # Date 컬럼 확인
                    date_col = 'Date' if 'Date' in self.current_data[symbol].columns else self.current_data[symbol].index.name
                    
                    if date_col == 'Date':
                        existing_dates = set(self.current_data[symbol]['Date'])
                        new_data = latest_data[~latest_data['Date'].isin(existing_dates)]
                    else:
                        # 인덱스가 Date인 경우
                        existing_dates = set(self.current_data[symbol].index)
                        new_data = latest_data[~latest_data.index.isin(existing_dates)]
                    
                    if not new_data.empty:
                        # 데이터 합치기
                        if date_col == 'Date':
                            combined_data = pd.concat([self.current_data[symbol], new_data], ignore_index=True)
                        else:
                            combined_data = pd.concat([self.current_data[symbol], new_data])
                        
                        # 기술적 지표 추가
                        new_data_with_indicators = feature_engineer.add_technical_indicators(combined_data)
                        
                        # 전략 데이터 준비 (개선된 전략용)
                        try:
                            from strategies.improved.buy_low_sell_high import improved_strategy
                            new_data_with_indicators = improved_strategy.prepare_data(new_data_with_indicators)
                        except Exception as e:
                            logger.debug(f"전략 데이터 준비 실패 {symbol}: {str(e)}")
                        
                        self.current_data[symbol] = new_data_with_indicators
                        
                        # 현재 가격 업데이트
                        if 'CLOSE' in new_data_with_indicators.columns:
                            self.current_prices[symbol] = new_data_with_indicators.iloc[-1]['CLOSE']
                
        except Exception as e:
            logger.error(f"데이터 업데이트 오류 {symbol}: {str(e)}")
    
    def _execute_signal(self, signal_info: Dict):
        """신호 실행"""
        symbol = signal_info['symbol']
        signal = signal_info['signal']
        confidence = signal_info['confidence']
        
        # 신뢰도 임계값 확인
        min_confidence = 0.6  # 설정 가능
        if confidence < min_confidence:
            logger.debug(f"신뢰도 부족으로 거래 건너뜀: {symbol} ({confidence:.2f})")
            return
        
        current_price = self.current_prices.get(symbol, 0)
        if current_price <= 0:
            logger.warning(f"유효하지 않은 가격: {symbol}")
            return
        
        if signal == 'BUY':
            self._execute_buy_order(symbol, current_price, signal_info)
        elif signal == 'SELL':
            self._execute_sell_order(symbol, current_price, signal_info)
    
    def _execute_buy_order(self, symbol: str, price: float, signal_info: Dict):
        """매수 주문 실행"""
        # 개선된 전략에서 제공하는 포지션 크기 사용
        if 'position_size' in signal_info:
            quantity = signal_info['position_size']
        else:
            # 포지션 크기 계산 (기본값)
            quantity = self.portfolio_manager.calculate_position_size(symbol, price)
        
        if quantity <= 0:
            logger.debug(f"매수 수량 부족: {symbol}")
            return
        
        # 거래 실행
        success = self.portfolio_manager.execute_trade(
            symbol=symbol,
            order_type=OrderType.BUY,
            quantity=quantity,
            price=price,
            timestamp=datetime.now(),
            commission=COMMISSION
        )
        
        if success:
            self.daily_trade_count += 1
            
            # 포지션 매니저 업데이트 (개선된 전략)
            try:
                stop_loss = signal_info.get('stop_loss', price * (1 - STOP_LOSS_PCT))
                take_profit = signal_info.get('take_profit', price * (1 + TAKE_PROFIT_PCT))
                signal_strength = signal_info.get('confidence', 1.0)
                
                position_manager.open_position(
                    symbol=symbol,
                    shares=quantity,
                    price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    signal_strength=signal_strength
                )
            except Exception as e:
                logger.debug(f"포지션 매니저 업데이트 실패: {str(e)}")
            
            log_trade(logger, "BUY", symbol, quantity, price)
            logger.info(f"매수 완료: {quantity} {symbol} @ ${price:.2f} (손절: ${stop_loss:.2f}, 익절: ${take_profit:.2f})")
    
    def _execute_sell_order(self, symbol: str, price: float, signal_info: Dict):
        """매도 주문 실행"""
        # 보유 포지션 확인
        position = self.portfolio_manager.get_position(symbol)
        if not position:
            logger.debug(f"보유하지 않은 종목 매도 시도: {symbol}")
            return
        
        # 전체 매도
        quantity = position.quantity
        
        # 거래 실행
        success = self.portfolio_manager.execute_trade(
            symbol=symbol,
            order_type=OrderType.SELL,
            quantity=quantity,
            price=price,
            timestamp=datetime.now(),
            commission=COMMISSION
        )
        
        if success:
            self.daily_trade_count += 1
            
            # 포지션 매니저 업데이트 (개선된 전략)
            try:
                reason = signal_info.get('reasons', ['Signal'])[0] if signal_info.get('reasons') else 'Signal'
                position_manager.close_position(symbol, price, reason)
            except Exception as e:
                logger.debug(f"포지션 매니저 업데이트 실패: {str(e)}")
            
            # 손익 계산
            pnl = (price - position.avg_price) * quantity
            pnl_pct = (price - position.avg_price) / position.avg_price
            
            log_trade(logger, "SELL", symbol, quantity, price)
            logger.info(f"매도 완료: {quantity} {symbol} @ ${price:.2f} (손익: ${pnl:.2f}, {pnl_pct:.2%})")
    
    def _log_portfolio_status(self):
        """포트폴리오 상태 로그"""
        try:
            portfolio_value = self.portfolio_manager.get_portfolio_value(self.current_prices)
            cash = self.portfolio_manager.cash
            positions = self.portfolio_manager.get_all_positions()
            
            log_portfolio(logger, portfolio_value, cash, positions)
            
            # 상세 정보
            logger.info(f"포트폴리오 가치: ${portfolio_value:.2f}")
            logger.info(f"현금: ${cash:.2f}")
            logger.info(f"보유 포지션: {len(positions)}개")
            
            for symbol, position in positions.items():
                logger.info(f"  {symbol}: {position.quantity}주 @ ${position.avg_price:.2f} "
                          f"(현재: ${position.current_price:.2f}, 손익: ${position.unrealized_pnl:.2f})")
            
        except Exception as e:
            logger.error(f"포트폴리오 상태 로그 오류: {str(e)}")
    
    def _log_final_status(self):
        """최종 상태 로그"""
        try:
            portfolio_value = self.portfolio_manager.get_portfolio_value(self.current_prices)
            total_return = (portfolio_value - INITIAL_CAPITAL) / INITIAL_CAPITAL
            
            logger.info("=== 모의투자 최종 결과 ===")
            logger.info(f"초기 자본: ${INITIAL_CAPITAL:,.2f}")
            logger.info(f"최종 가치: ${portfolio_value:,.2f}")
            logger.info(f"총 수익률: {total_return:.2%}")
            logger.info(f"총 거래 횟수: {len(self.portfolio_manager.trades)}")
            
            # 성과 지표
            performance = self.portfolio_manager.get_performance_metrics()
            logger.info(f"승률: {performance.get('win_rate', 0):.2%}")
            logger.info(f"샤프 비율: {performance.get('sharpe_ratio', 0):.2f}")
            logger.info(f"최대 낙폭: {performance.get('max_drawdown', 0):.2%}")
            
        except Exception as e:
            logger.error(f"최종 상태 로그 오류: {str(e)}")
    
    def get_current_status(self) -> Dict:
        """현재 상태 반환"""
        try:
            portfolio_value = self.portfolio_manager.get_portfolio_value(self.current_prices)
            positions = self.portfolio_manager.get_all_positions()
            
            return {
                'portfolio_value': portfolio_value,
                'cash': self.portfolio_manager.cash,
                'total_return': (portfolio_value - INITIAL_CAPITAL) / INITIAL_CAPITAL,
                'positions': {symbol: {
                    'quantity': pos.quantity,
                    'avg_price': pos.avg_price,
                    'current_price': pos.current_price,
                    'unrealized_pnl': pos.unrealized_pnl
                } for symbol, pos in positions.items()},
                'daily_trades': self.daily_trade_count,
                'is_running': self.is_running
            }
            
        except Exception as e:
            logger.error(f"상태 조회 오류: {str(e)}")
            return {}
    
    def get_trade_history(self) -> pd.DataFrame:
        """거래 내역 반환"""
        return self.portfolio_manager.get_trade_history()


"""
백테스팅 엔진
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
import os

from config import *
from utils.logger import setup_logger
from utils.data_collector import collect_stock_data
from utils.feature_engineering import add_technical_indicators
from strategies.buy_low_sell_high import BuyLowSellHighStrategy
from backtesting.portfolio_manager import PortfolioManager, OrderType

logger = setup_logger("backtest_engine")

class BacktestEngine:
    """백테스팅 엔진 클래스"""
    
    def __init__(self, 
                 symbols: List[str],
                 start_date: str,
                 end_date: str,
                 initial_capital: float = INITIAL_CAPITAL):
        """
        초기화
        
        Args:
            symbols (List[str]): 백테스팅할 종목 리스트
            start_date (str): 시작 날짜
            end_date (str): 종료 날짜
            initial_capital (float): 초기 자본
        """
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        
        # 데이터 저장
        self.data: Dict[str, pd.DataFrame] = {}
        self.portfolio_manager = PortfolioManager(initial_capital)
        self.strategy = BuyLowSellHighStrategy()
        
        # 결과 저장
        self.results = {}
        
    def prepare_data(self) -> bool:
        """
        백테스팅 데이터 준비
        
        Returns:
            bool: 데이터 준비 성공 여부
        """
        logger.info("백테스팅 데이터 준비 시작")
        
        try:
            # 데이터 수집
            raw_data = collect_stock_data(
                self.symbols, 
                self.start_date, 
                self.end_date,
                save_to_file=False
            )
            
            if not raw_data:
                logger.error("데이터 수집 실패")
                return False
            
            # 기술적 지표 추가
            for symbol, df in raw_data.items():
                if not df.empty:
                    df_with_indicators = add_technical_indicators(df)
                    self.data[symbol] = df_with_indicators
                    logger.info(f"데이터 준비 완료: {symbol} - {len(df_with_indicators)}개 레코드")
            
            if not self.data:
                logger.error("유효한 데이터가 없습니다")
                return False
            
            # 전략 데이터 준비
            for symbol, df in self.data.items():
                self.data[symbol] = self.strategy.prepare_data(df)
            
            logger.info(f"총 {len(self.data)}개 종목 데이터 준비 완료")
            return True
            
        except Exception as e:
            logger.error(f"데이터 준비 실패: {str(e)}")
            return False
    
    def run_backtest(self) -> Dict:
        """
        백테스팅 실행
        
        Returns:
            Dict: 백테스팅 결과
        """
        logger.info("백테스팅 시작")
        
        if not self.prepare_data():
            return {}
        
        # 공통 날짜 범위 찾기
        common_dates = self._get_common_dates()
        if not common_dates:
            logger.error("공통 날짜 범위를 찾을 수 없습니다")
            return {}
        
        logger.info(f"백테스팅 기간: {common_dates[0]} ~ {common_dates[-1]}")
        
        # 일별 백테스팅 실행
        for current_date in common_dates:
            self._process_daily_signals(current_date)
        
        # 결과 계산
        results = self._calculate_results()
        
        logger.info("백테스팅 완료")
        return results
    
    def _get_common_dates(self) -> List[date]:
        """공통 날짜 범위 계산"""
        all_dates = set()
        
        for symbol, df in self.data.items():
            if not df.empty:
                dates = pd.to_datetime(df['Date']).dt.date.tolist()
                all_dates.update(dates)
        
        if not all_dates:
            return []
        
        # 날짜 범위 필터링
        start_date = pd.to_datetime(self.start_date).date()
        end_date = pd.to_datetime(self.end_date).date()
        
        filtered_dates = [
            d for d in sorted(all_dates) 
            if start_date <= d <= end_date
        ]
        
        return filtered_dates
    
    def _process_daily_signals(self, current_date: date):
        """일별 신호 처리"""
        current_prices = {}

        # 현재 날짜의 가격 정보 수집
        for symbol, df in self.data.items():
            # Date를 date 객체로 변환하여 비교
            day_data = df[pd.to_datetime(df['Date']).dt.date == current_date]
            if not day_data.empty:
                current_prices[symbol] = day_data.iloc[0]['CLOSE']

        if not current_prices:
            return
        
        # 각 종목별 신호 처리
        for symbol, df in self.data.items():
            if symbol not in current_prices:
                continue

            # Date를 date 객체로 변환하여 비교
            day_data = df[pd.to_datetime(df['Date']).dt.date == current_date]
            if day_data.empty:
                continue
            
            signal_data = day_data.iloc[0]
            current_price = current_prices[symbol]
            
            # 거래 신호 생성
            signal = self._generate_trading_signal(signal_data, symbol)

            # 거래 실행
            if signal['action'] != 'HOLD':
                self._execute_trade_signal(signal, current_price, current_date)
        
        # 일일 포트폴리오 가치 기록
        self.portfolio_manager.record_daily_value(current_prices, current_date)
    
    def _generate_trading_signal(self, signal_data: pd.Series, symbol: str) -> Dict:
        """거래 신호 생성"""
        signal = signal_data.get('SIGNAL', 0)
        confidence = signal_data.get('SIGNAL_STRENGTH', 0)
        
        # 기본 신호
        if signal == 1:  # BUY
            action = 'BUY'
        elif signal == -1:  # SELL
            action = 'SELL'
        else:
            action = 'HOLD'
        
        # 포지션 크기 계산
        quantity = 0
        if action == 'BUY':
            quantity = self.portfolio_manager.calculate_position_size(symbol, signal_data['CLOSE'])
        elif action == 'SELL':
            position = self.portfolio_manager.get_position(symbol)
            if position:
                quantity = position.quantity  # 전체 매도
        
        return {
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'price': signal_data['CLOSE'],
            'confidence': confidence,
            'rsi': signal_data.get('RSI', 0),
            'bb_position': signal_data.get('BB_POSITION', 0.5)
        }
    
    def _execute_trade_signal(self, signal: Dict, current_price: float, current_date: date):
        """거래 신호 실행"""
        symbol = signal['symbol']
        action = signal['action']
        quantity = signal['quantity']

        if quantity <= 0:
            return
        
        # 주문 타입 변환
        order_type = OrderType.BUY if action == 'BUY' else OrderType.SELL
        
        # 거래 실행
        success = self.portfolio_manager.execute_trade(
            symbol=symbol,
            order_type=order_type,
            quantity=quantity,
            price=current_price,
            timestamp=datetime.combine(current_date, datetime.min.time()),
            commission=COMMISSION
        )
        
        if success:
            logger.debug(f"거래 실행: {action} {quantity} {symbol} @ ${current_price:.2f}")
    
    def _calculate_results(self) -> Dict:
        """백테스팅 결과 계산"""
        # 성과 지표
        performance = self.portfolio_manager.get_performance_metrics()
        
        # 거래 내역
        trade_history = self.portfolio_manager.get_trade_history()
        
        # 일일 가치 데이터
        daily_values = pd.DataFrame(self.portfolio_manager.daily_values)
        
        # 종목별 성과
        symbol_performance = self._calculate_symbol_performance()
        
        # 벤치마크 비교 (S&P 500)
        benchmark_performance = self._calculate_benchmark_performance()
        
        results = {
            'performance': performance,
            'trade_history': trade_history,
            'daily_values': daily_values,
            'symbol_performance': symbol_performance,
            'benchmark_performance': benchmark_performance,
            'parameters': {
                'symbols': self.symbols,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'initial_capital': self.initial_capital,
                'strategy': 'Buy Low Sell High'
            }
        }
        
        return results
    
    def _calculate_symbol_performance(self) -> Dict[str, Dict]:
        """종목별 성과 계산"""
        symbol_performance = {}
        
        for symbol, df in self.data.items():
            if df.empty:
                continue
            
            # 기본 지표
            start_price = df.iloc[0]['CLOSE']
            end_price = df.iloc[-1]['CLOSE']
            total_return = (end_price - start_price) / start_price
            
            # 거래 내역에서 해당 종목 필터링
            trade_history = self.portfolio_manager.get_trade_history()

            if trade_history.empty:
                num_trades = 0
                total_pnl = 0
            else:
                symbol_trades = trade_history[trade_history['symbol'] == symbol]
                num_trades = len(symbol_trades)
                total_pnl = symbol_trades['pnl'].sum() if not symbol_trades.empty else 0
            
            symbol_performance[symbol] = {
                'total_return': total_return,
                'num_trades': num_trades,
                'total_pnl': total_pnl,
                'start_price': start_price,
                'end_price': end_price
            }
        
        return symbol_performance
    
    def _calculate_benchmark_performance(self) -> Dict:
        """벤치마크 성과 계산 (S&P 500)"""
        try:
            # S&P 500 데이터 수집
            benchmark_data = collect_stock_data(
                ['^GSPC'], 
                self.start_date, 
                self.end_date,
                save_to_file=False
            )
            
            if '^GSPC' not in benchmark_data or benchmark_data['^GSPC'].empty:
                return {}
            
            df = benchmark_data['^GSPC']
            start_price = df.iloc[0]['CLOSE']
            end_price = df.iloc[-1]['CLOSE']
            total_return = (end_price - start_price) / start_price
            
            # 일일 수익률
            df['daily_return'] = df['CLOSE'].pct_change()
            volatility = df['daily_return'].std() * np.sqrt(252)
            
            return {
                'total_return': total_return,
                'volatility': volatility,
                'start_price': start_price,
                'end_price': end_price
            }
            
        except Exception as e:
            logger.warning(f"벤치마크 성과 계산 실패: {str(e)}")
            return {}
    
    def save_results(self, results: Dict, filename: Optional[str] = None):
        """결과 저장"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"backtest_results_{timestamp}.pkl"
        
        filepath = os.path.join(BACKTEST_RESULTS_DIR, filename)
        os.makedirs(BACKTEST_RESULTS_DIR, exist_ok=True)
        
        import pickle
        with open(filepath, 'wb') as f:
            pickle.dump(results, f)
        
        logger.info(f"백테스팅 결과 저장: {filepath}")
        return filepath


"""
개선된 전략 간단한 백테스팅 스크립트
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from config import *
from utils.data_collector import data_collector
from utils.feature_engineering import feature_engineer
from strategies.improved.buy_low_sell_high import improved_strategy
from utils.market_analyzer import market_analyzer
from utils.position_manager import PositionManager
from utils.logger import setup_logger

logger = setup_logger("test_improved_strategy_simple")

class SimpleBacktester:
    """간단한 백테스팅 클래스"""
    
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # {symbol: {'shares': n, 'avg_price': p}}
        self.trades = []
        self.portfolio_values = []
        self.dates = []
        
    def buy(self, symbol, shares, price, date):
        """매수 실행"""
        cost = shares * price
        if cost > self.cash:
            return False
            
        self.cash -= cost
        
        if symbol in self.positions:
            # 평균 단가 계산
            old_shares = self.positions[symbol]['shares']
            old_price = self.positions[symbol]['avg_price']
            new_shares = old_shares + shares
            new_avg_price = (old_shares * old_price + shares * price) / new_shares
            
            self.positions[symbol] = {
                'shares': new_shares,
                'avg_price': new_avg_price
            }
        else:
            self.positions[symbol] = {
                'shares': shares,
                'avg_price': price
            }
            
        self.trades.append({
            'date': date,
            'symbol': symbol,
            'type': 'BUY',
            'shares': shares,
            'price': price,
            'value': cost
        })
        
        return True
        
    def sell(self, symbol, shares, price, date):
        """매도 실행"""
        if symbol not in self.positions:
            return False
            
        if self.positions[symbol]['shares'] < shares:
            shares = self.positions[symbol]['shares']
            
        proceeds = shares * price
        self.cash += proceeds
        
        # 손익 계산
        avg_price = self.positions[symbol]['avg_price']
        pnl = (price - avg_price) * shares
        pnl_pct = (price - avg_price) / avg_price
        
        self.positions[symbol]['shares'] -= shares
        if self.positions[symbol]['shares'] == 0:
            del self.positions[symbol]
            
        self.trades.append({
            'date': date,
            'symbol': symbol,
            'type': 'SELL',
            'shares': shares,
            'price': price,
            'value': proceeds,
            'pnl': pnl,
            'pnl_pct': pnl_pct
        })
        
        return True
        
    def get_portfolio_value(self, prices):
        """포트폴리오 가치 계산"""
        total_value = self.cash
        
        for symbol, position in self.positions.items():
            if symbol in prices:
                total_value += position['shares'] * prices[symbol]
                
        return total_value

def run_improved_backtest():
    """개선된 전략으로 백테스팅 실행"""
    
    logger.info("=== 개선된 전략 백테스팅 시작 ===")
    
    # 1. 시장 상황 확인
    logger.info("시장 상황 분석 중...")
    market_conditions = market_analyzer.get_market_filter_signal()
    logger.info(f"시장 필터 신호: {market_conditions}")
    
    # 2. 데이터 수집
    logger.info("데이터 수집 중...")
    all_data = {}
    
    for symbol in DEFAULT_SYMBOLS:
        logger.info(f"{symbol} 데이터 수집 중...")
        try:
            # 데이터 수집
            stock_data = data_collector.download_stock_data(symbol, DATA_START_DATE, DATA_END_DATE)
            
            if stock_data is not None and not stock_data.empty:
                # 기술적 지표 추가
                stock_data = feature_engineer.add_technical_indicators(stock_data)
                
                # 전략 데이터 준비
                stock_data = improved_strategy.prepare_data(stock_data)
                
                # Date 인덱스 설정
                if 'Date' in stock_data.columns:
                    stock_data.set_index('Date', inplace=True)
                
                all_data[symbol] = stock_data
                logger.info(f"{symbol} 데이터 준비 완료: {len(stock_data)} 개 레코드")
            else:
                logger.warning(f"{symbol} 데이터 수집 실패")
                
        except Exception as e:
            logger.error(f"{symbol} 처리 중 오류: {str(e)}")
    
    if not all_data:
        logger.error("수집된 데이터가 없습니다")
        return
    
    # 3. 머신러닝 모델 학습
    logger.info("머신러닝 모델 학습 중...")
    
    # 모든 데이터 통합
    combined_data = pd.concat(all_data.values(), ignore_index=True)
    combined_data = combined_data.dropna(subset=['TARGET_MULTI'])
    
    if len(combined_data) > 1000:
        improved_strategy.train_model(combined_data)
        logger.info("모델 학습 완료")
    else:
        logger.warning("학습 데이터 부족, 규칙 기반 전략만 사용")
    
    # 4. 백테스팅 실행
    logger.info("백테스팅 실행 중...")
    
    # 백테스터 초기화
    backtester = SimpleBacktester(INITIAL_CAPITAL)
    position_manager = PositionManager(INITIAL_CAPITAL)
    
    # 모든 날짜 수집
    all_dates = set()
    for data in all_data.values():
        all_dates.update(data.index)
    all_dates = sorted(list(all_dates))
    
    # 날짜별로 백테스팅 실행
    for current_date in all_dates:
        current_prices = {}
        signals = {}
        
        # 각 종목별로 신호 생성
        for symbol, data in all_data.items():
            if current_date in data.index:
                # 현재까지의 데이터만 사용
                historical_data = data.loc[:current_date]
                current_prices[symbol] = data.loc[current_date, 'CLOSE']
                
                # 거래 신호 생성
                signal = improved_strategy.get_signal(
                    historical_data.reset_index(), 
                    symbol, 
                    backtester.cash
                )
                signals[symbol] = signal
        
        # 포지션 업데이트 (손절/익절 확인)
        for symbol in list(backtester.positions.keys()):
            if symbol in current_prices:
                position = backtester.positions[symbol]
                current_price = current_prices[symbol]
                avg_price = position['avg_price']
                
                # 손절/익절 확인
                price_change = (current_price - avg_price) / avg_price
                
                if price_change <= -STOP_LOSS_PCT or price_change >= TAKE_PROFIT_PCT:
                    # 청산
                    backtester.sell(symbol, position['shares'], current_price, current_date)
                    logger.info(f"{current_date}: {symbol} 청산 - 손익: {price_change:.2%}")
        
        # 신호에 따른 거래 실행
        for symbol, signal in signals.items():
            if signal['signal'] == 'BUY' and symbol not in backtester.positions:
                # 포지션 크기 계산
                position_size = signal.get('position_size', 100)
                
                # 매수 실행
                if backtester.buy(symbol, position_size, signal['price'], current_date):
                    logger.info(f"{current_date}: {symbol} 매수 - {position_size}주 @ ${signal['price']:.2f}")
                    
            elif signal['signal'] == 'SELL' and symbol in backtester.positions:
                # 매도 실행
                position = backtester.positions[symbol]
                if backtester.sell(symbol, position['shares'], signal['price'], current_date):
                    logger.info(f"{current_date}: {symbol} 매도 - 전량 @ ${signal['price']:.2f}")
        
        # 포트폴리오 가치 기록
        portfolio_value = backtester.get_portfolio_value(current_prices)
        backtester.portfolio_values.append(portfolio_value)
        backtester.dates.append(current_date)
    
    # 5. 성과 분석
    logger.info("\n=== 백테스팅 결과 ===")
    
    # 기본 성과 지표
    final_value = backtester.portfolio_values[-1]
    total_return = (final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL
    
    # 연환산 수익률
    days = len(backtester.dates)
    years = days / 252
    annual_return = (final_value / INITIAL_CAPITAL) ** (1/years) - 1 if years > 0 else 0
    
    # 샤프 비율
    daily_returns = pd.Series(backtester.portfolio_values).pct_change().dropna()
    sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0
    
    # 최대 낙폭
    portfolio_series = pd.Series(backtester.portfolio_values)
    rolling_max = portfolio_series.expanding().max()
    drawdown = (portfolio_series - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    # 승률
    winning_trades = [t for t in backtester.trades if t['type'] == 'SELL' and t.get('pnl', 0) > 0]
    losing_trades = [t for t in backtester.trades if t['type'] == 'SELL' and t.get('pnl', 0) <= 0]
    total_sell_trades = len(winning_trades) + len(losing_trades)
    win_rate = len(winning_trades) / total_sell_trades if total_sell_trades > 0 else 0
    
    # 평균 수익/손실
    avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
    avg_loss = np.mean([abs(t['pnl']) for t in losing_trades]) if losing_trades else 0
    profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
    
    # 결과 출력
    logger.info(f"초기 자본: ${INITIAL_CAPITAL:,.2f}")
    logger.info(f"최종 자산: ${final_value:,.2f}")
    logger.info(f"총 수익률: {total_return:.2%}")
    logger.info(f"연환산 수익률: {annual_return:.2%}")
    logger.info(f"샤프 비율: {sharpe_ratio:.2f}")
    logger.info(f"최대 낙폭: {max_drawdown:.2%}")
    logger.info(f"총 거래 횟수: {len(backtester.trades)}")
    logger.info(f"승률: {win_rate:.2%}")
    logger.info(f"평균 수익: ${avg_win:.2f}")
    logger.info(f"평균 손실: ${avg_loss:.2f}")
    logger.info(f"수익 팩터: {profit_factor:.2f}")
    
    # 종목별 성과
    logger.info("\n=== 종목별 성과 ===")
    symbol_performance = {}
    
    for trade in backtester.trades:
        symbol = trade['symbol']
        if symbol not in symbol_performance:
            symbol_performance[symbol] = {'trades': 0, 'pnl': 0, 'wins': 0}
        
        symbol_performance[symbol]['trades'] += 1
        
        if trade['type'] == 'SELL':
            pnl = trade.get('pnl', 0)
            symbol_performance[symbol]['pnl'] += pnl
            if pnl > 0:
                symbol_performance[symbol]['wins'] += 1
    
    for symbol, perf in symbol_performance.items():
        logger.info(f"{symbol}: 거래 {perf['trades']}회, 손익 ${perf['pnl']:.2f}")
    
    # 거래 내역 저장
    trades_df = pd.DataFrame(backtester.trades)
    trades_df.to_csv('improved_strategy_trades.csv', index=False)
    logger.info("\n거래 내역 저장: improved_strategy_trades.csv")
    
    # 포트폴리오 가치 저장
    portfolio_df = pd.DataFrame({
        'Date': backtester.dates,
        'Portfolio_Value': backtester.portfolio_values
    })
    portfolio_df.to_csv('improved_strategy_portfolio.csv', index=False)
    logger.info("포트폴리오 가치 저장: improved_strategy_portfolio.csv")
    
    logger.info("\n=== 개선 효과 분석 ===")
    logger.info("기존 전략 대비 개선사항:")
    logger.info(f"- 목표 승률: 24.39% → {win_rate:.2%} ({'달성' if win_rate > 0.35 else '미달성'})")
    logger.info(f"- 거래 빈도: 492회 → {len(backtester.trades)}회")
    logger.info(f"- 최대 낙폭: -6.98% → {max_drawdown:.2%}")
    logger.info(f"- 샤프 비율: 2.4 → {sharpe_ratio:.2f}")

if __name__ == "__main__":
    run_improved_backtest()

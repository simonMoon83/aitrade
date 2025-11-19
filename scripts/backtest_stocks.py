"""
주식 백테스트 실행 스크립트
Usage: python scripts/backtest_stocks.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

logger = setup_logger("backtest_stocks")

class StockBacktester:
    """주식 백테스팅 클래스"""
    
    def __init__(self, initial_capital=INITIAL_CAPITAL):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.trades = []
        self.portfolio_values = []
        self.dates = []
        
    def buy(self, symbol, shares, price, date):
        cost = shares * price
        if cost > self.cash:
            return False
            
        self.cash -= cost
        
        if symbol in self.positions:
            old_shares = self.positions[symbol]['shares']
            old_price = self.positions[symbol]['avg_price']
            new_shares = old_shares + shares
            new_avg_price = (old_shares * old_price + shares * price) / new_shares
            
            self.positions[symbol] = {
                'shares': new_shares,
                'avg_price': new_avg_price,
                'entry_date': self.positions[symbol]['entry_date']
            }
        else:
            self.positions[symbol] = {
                'shares': shares,
                'avg_price': price,
                'entry_date': date
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
        if symbol not in self.positions:
            return False
            
        if self.positions[symbol]['shares'] < shares:
            shares = self.positions[symbol]['shares']
            
        proceeds = shares * price
        self.cash += proceeds
        
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
        total_value = self.cash
        
        for symbol, position in self.positions.items():
            if symbol in prices:
                total_value += position['shares'] * prices[symbol]
                
        return total_value

def run_backtest():
    """백테스트 실행"""
    logger.info("="*80)
    logger.info("📊 주식 백테스트 시작")
    logger.info("="*80)
    logger.info(f"기간: {DATA_START_DATE} ~ {DATA_END_DATE}")
    logger.info(f"초기 자본: ${INITIAL_CAPITAL:,.2f}")
    logger.info(f"대상 종목: {', '.join(DEFAULT_SYMBOLS)}")
    logger.info("="*80)
    
    # 시장 분석
    logger.info("\n[1/5] 시장 상황 분석 중...")
    market_filter = market_analyzer.get_market_filter_signal()
    logger.info(f"시장 필터 신호: {market_filter}")
    
    # 데이터 수집
    logger.info("\n[2/5] 데이터 수집 중...")
    all_data = {}
    
    for symbol in DEFAULT_SYMBOLS:
        logger.info(f"{symbol} 데이터 수집 중...")
        stock_data = data_collector.download_stock_data(symbol, DATA_START_DATE, DATA_END_DATE)
        
        if not stock_data.empty:
            stock_data = feature_engineer.add_technical_indicators(stock_data)
            stock_data = improved_strategy.prepare_data(stock_data)
            all_data[symbol] = stock_data
            logger.info(f"{symbol} 데이터 준비 완료: {len(stock_data)} 개 레코드")
    
    # 모델 학습
    logger.info("\n[3/5] 머신러닝 모델 학습 중...")
    combined_data = pd.concat(all_data.values(), ignore_index=True)
    combined_data = combined_data.dropna(subset=['TARGET_MULTI'])
    
    if len(combined_data) > 100:
        improved_strategy.train_model(combined_data)
        logger.info("모델 학습 완료")
    
    # 백테스팅
    logger.info("\n[4/5] 백테스팅 실행 중...")
    backtester = StockBacktester(INITIAL_CAPITAL)
    position_manager = PositionManager(
        initial_capital=INITIAL_CAPITAL,
        max_positions=MAX_POSITIONS
    )
    
    # 모든 날짜 추출
    all_dates = set()
    for data in all_data.values():
        all_dates.update(data['Date'].tolist())
    all_dates = sorted(list(all_dates))
    
    logger.info(f"백테스트 기간: {all_dates[0]} ~ {all_dates[-1]} ({len(all_dates)}일)")
    
    for current_date in all_dates:
        current_prices = {}
        signals = {}
        
        # 각 종목의 신호 확인
        for symbol, data in all_data.items():
            data_until_date = data[data['Date'] <= current_date]
            
            if not data_until_date.empty:
                latest_price = data_until_date.iloc[-1]['CLOSE']
                current_prices[symbol] = latest_price
                
                signal = improved_strategy.get_signal(
                    data_until_date,
                    symbol,
                    backtester.cash
                )
                signals[symbol] = signal
        
        # 손절/익절 확인
        for symbol in list(backtester.positions.keys()):
            if symbol in current_prices:
                position = backtester.positions[symbol]
                current_price = current_prices[symbol]
                avg_price = position['avg_price']
                
                price_change = (current_price - avg_price) / avg_price
                
                if price_change <= -STOP_LOSS_PCT or price_change >= TAKE_PROFIT_PCT:
                    backtester.sell(symbol, position['shares'], current_price, current_date)
                    logger.info(f"{current_date}: {symbol} 청산 - 손익: {price_change:.2%}")
        
        # 신호에 따른 거래
        for symbol, signal in signals.items():
            if signal['signal'] == 'BUY' and symbol not in backtester.positions:
                if len(backtester.positions) < MAX_POSITIONS and position_manager.can_open_position():
                    position_size = signal.get('position_size', 0)
                    if position_size > 0 and backtester.buy(symbol, position_size, signal['price'], current_date):
                        logger.info(f"{current_date}: {symbol} 매수 - {position_size}주 @ ${signal['price']:.2f}")
                        
            elif signal['signal'] == 'SELL' and symbol in backtester.positions:
                position = backtester.positions[symbol]
                if backtester.sell(symbol, position['shares'], signal['price'], current_date):
                    logger.info(f"{current_date}: {symbol} 매도 - 전량 @ ${signal['price']:.2f}")
        
        # 포트폴리오 가치 기록
        portfolio_value = backtester.get_portfolio_value(current_prices)
        backtester.portfolio_values.append(portfolio_value)
        backtester.dates.append(current_date)
    
    # 결과 저장
    logger.info("\n[5/5] 결과 저장 중...")
    
    # 성과 지표 계산
    final_value = backtester.portfolio_values[-1]
    total_return = (final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL
    
    # 거래 내역 저장
    trades_df = pd.DataFrame(backtester.trades)
    portfolio_df = pd.DataFrame({
        'Date': backtester.dates,
        'Portfolio_Value': backtester.portfolio_values
    })
    
    output_dir = "results/backtests"
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    trades_df.to_csv(f"{output_dir}/stock_trades_{timestamp}.csv", index=False)
    portfolio_df.to_csv(f"{output_dir}/stock_portfolio_{timestamp}.csv", index=False)
    
    logger.info(f"  ✓ 거래 내역: {output_dir}/stock_trades_{timestamp}.csv")
    logger.info(f"  ✓ 포트폴리오: {output_dir}/stock_portfolio_{timestamp}.csv")
    
    # 최종 결과
    logger.info("\n" + "="*80)
    logger.info("백테스팅 결과")
    logger.info("="*80)
    logger.info(f"초기 자본: ${INITIAL_CAPITAL:,.2f}")
    logger.info(f"최종 자산: ${final_value:,.2f}")
    logger.info(f"총 수익률: {total_return:.2%}")
    logger.info(f"총 거래 횟수: {len(trades_df)}")
    logger.info("="*80)
    
    return {
        'final_value': final_value,
        'total_return': total_return,
        'trades': trades_df,
        'portfolio': portfolio_df
    }

if __name__ == "__main__":
    results = run_backtest()


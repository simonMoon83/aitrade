"""
암호화폐 백테스팅 스크립트
2023-01-01 ~ 2025-06-30 기간 동안 10개 암호화폐 백테스팅
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import os
warnings.filterwarnings('ignore')

from config import *
from utils.crypto_data_collector import crypto_collector
from utils.feature_engineering import feature_engineer
from strategies.crypto_strategy import crypto_strategy
from utils.logger import setup_logger

logger = setup_logger("crypto_backtest")

class CryptoBacktester:
    """암호화폐 백테스팅 클래스"""
    
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # {symbol: {'shares': n, 'avg_price': p, 'entry_date': d}}
        self.trades = []
        self.portfolio_values = []
        self.dates = []
        
    def buy(self, symbol, shares, price, date):
        """매수 실행"""
        if shares <= 0 or price <= 0:
            return False
            
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
        
        logger.info(f"{date}: {symbol} 매수 - {shares}개 @ ${price:.2f}")
        
        return True
        
    def sell(self, symbol, shares, price, date):
        """매도 실행"""
        if symbol not in self.positions:
            return False
            
        if self.positions[symbol]['shares'] < shares:
            shares = self.positions[symbol]['shares']
            
        if shares <= 0:
            return False
            
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
        
        logger.info(f"{date}: {symbol} 매도 - {shares}개 @ ${price:.2f} (손익: {pnl_pct:.2%})")
        
        return True
        
    def get_portfolio_value(self, prices):
        """포트폴리오 가치 계산"""
        total_value = self.cash
        
        for symbol, position in self.positions.items():
            if symbol in prices and prices[symbol] > 0:
                total_value += position['shares'] * prices[symbol]
                
        return total_value

def run_crypto_backtest():
    """암호화폐 백테스팅 실행"""
    
    logger.info("=" * 80)
    logger.info("암호화폐 백테스팅 시작")
    logger.info("=" * 80)
    logger.info(f"기간: {CRYPTO_START_DATE} ~ {CRYPTO_END_DATE}")
    logger.info(f"초기 자본: ${INITIAL_CAPITAL:,.2f}")
    logger.info(f"대상 코인: {', '.join(CRYPTO_SYMBOLS)}")
    logger.info("=" * 80)
    
    # 1. 데이터 수집
    logger.info("\n[1/5] 데이터 수집 중...")
    all_data = {}
    
    for symbol in CRYPTO_SYMBOLS:
        try:
            logger.info(f"  {symbol} 데이터 수집 중...")
            
            # 데이터 수집
            crypto_data = crypto_collector.download_crypto_data(
                symbol, 
                CRYPTO_START_DATE, 
                CRYPTO_END_DATE
            )
            
            if crypto_data is not None and not crypto_data.empty:
                # 기술적 지표 추가
                crypto_data = feature_engineer.add_technical_indicators(crypto_data)
                
                # 전략 데이터 준비
                crypto_data = crypto_strategy.prepare_data(crypto_data)
                
                # Date 인덱스 설정
                if 'Date' in crypto_data.columns:
                    crypto_data.set_index('Date', inplace=True)
                
                all_data[symbol] = crypto_data
                logger.info(f"  ✓ {symbol} 완료: {len(crypto_data)} 개 레코드")
            else:
                logger.warning(f"  ✗ {symbol} 데이터 없음")
                
        except Exception as e:
            logger.error(f"  ✗ {symbol} 오류: {str(e)}")
    
    if not all_data:
        logger.error("수집된 데이터가 없습니다!")
        return
    
    logger.info(f"\n총 {len(all_data)}개 코인 데이터 수집 완료")
    
    # 2. 백테스팅 실행
    logger.info("\n[2/5] 백테스팅 실행 중...")
    
    backtester = CryptoBacktester(INITIAL_CAPITAL)
    
    # 모든 날짜 수집
    all_dates = set()
    for data in all_data.values():
        all_dates.update(data.index)
    all_dates = sorted(list(all_dates))
    
    logger.info(f"백테스트 기간: {all_dates[0]} ~ {all_dates[-1]} ({len(all_dates)}일)")
    
    # 날짜별로 백테스팅 실행
    for idx, current_date in enumerate(all_dates):
        if idx % 30 == 0:
            logger.info(f"  진행률: {idx}/{len(all_dates)} ({idx/len(all_dates)*100:.1f}%)")
        
        current_prices = {}
        signals = {}
        
        # 각 코인별로 신호 생성
        for symbol, data in all_data.items():
            if current_date in data.index:
                # 현재까지의 데이터만 사용
                historical_data = data.loc[:current_date]
                current_prices[symbol] = data.loc[current_date, 'CLOSE']
                
                # 거래 신호 생성
                signal = crypto_strategy.get_signal(
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
                should_close, reason = crypto_strategy.check_stop_loss_take_profit(
                    avg_price, current_price
                )
                
                if should_close:
                    backtester.sell(symbol, position['shares'], current_price, current_date)
        
        # 신호에 따른 거래 실행
        for symbol, signal in signals.items():
            if signal['signal'] == 'BUY' and symbol not in backtester.positions:
                # 최대 포지션 수 확인
                if len(backtester.positions) >= CRYPTO_MAX_POSITIONS:
                    continue
                
                # 신호 강도 확인 (개선: 40%로 완화)
                if signal['confidence'] < 0.4:  # 0.6 → 0.4 (완화)
                    continue
                
                # 포지션 크기 계산
                position_size = signal.get('position_size', 0)
                
                if position_size > 0:
                    backtester.buy(symbol, position_size, signal['price'], current_date)
                    
            elif signal['signal'] == 'SELL' and symbol in backtester.positions:
                # 신호 강도 확인 (개선: 30%로 완화)
                if signal['confidence'] < 0.3:  # 0.5 → 0.3 (완화)
                    continue
                
                # 매도 실행
                position = backtester.positions[symbol]
                backtester.sell(symbol, position['shares'], signal['price'], current_date)
        
        # 포트폴리오 가치 기록
        portfolio_value = backtester.get_portfolio_value(current_prices)
        backtester.portfolio_values.append(portfolio_value)
        backtester.dates.append(current_date)
    
    logger.info(f"  완료: 총 {len(backtester.trades)}회 거래")
    
    # 3. 성과 분석
    logger.info("\n[3/5] 성과 분석 중...")
    
    final_value = backtester.portfolio_values[-1]
    total_return = (final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL
    
    # 연환산 수익률
    days = len(backtester.dates)
    years = days / 365  # 암호화폐는 365일
    annual_return = (final_value / INITIAL_CAPITAL) ** (1/years) - 1 if years > 0 else 0
    
    # 샤프 비율
    daily_returns = pd.Series(backtester.portfolio_values).pct_change().dropna()
    sharpe_ratio = np.sqrt(365) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0
    
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
    logger.info("\n" + "=" * 80)
    logger.info("백테스팅 결과")
    logger.info("=" * 80)
    logger.info(f"초기 자본:      ${INITIAL_CAPITAL:,.2f}")
    logger.info(f"최종 자산:      ${final_value:,.2f}")
    logger.info(f"총 수익:        ${final_value - INITIAL_CAPITAL:,.2f}")
    logger.info(f"총 수익률:      {total_return:.2%}")
    logger.info(f"연환산 수익률:  {annual_return:.2%}")
    logger.info(f"샤프 비율:      {sharpe_ratio:.2f}")
    logger.info(f"최대 낙폭(MDD): {max_drawdown:.2%}")
    logger.info(f"총 거래 횟수:   {len(backtester.trades)}회")
    logger.info(f"매수:           {len([t for t in backtester.trades if t['type'] == 'BUY'])}회")
    logger.info(f"매도:           {total_sell_trades}회")
    logger.info(f"승률:           {win_rate:.2%}")
    logger.info(f"평균 수익:      ${avg_win:.2f}")
    logger.info(f"평균 손실:      ${avg_loss:.2f}")
    logger.info(f"수익 팩터:      {profit_factor:.2f}")
    logger.info("=" * 80)
    
    # 4. 코인별 성과
    logger.info("\n[4/5] 코인별 성과 분석 중...")
    
    coin_performance = {}
    
    for trade in backtester.trades:
        symbol = trade['symbol']
        if symbol not in coin_performance:
            coin_performance[symbol] = {
                'trades': 0, 
                'buys': 0,
                'sells': 0,
                'pnl': 0, 
                'wins': 0,
                'losses': 0
            }
        
        coin_performance[symbol]['trades'] += 1
        
        if trade['type'] == 'BUY':
            coin_performance[symbol]['buys'] += 1
        elif trade['type'] == 'SELL':
            coin_performance[symbol]['sells'] += 1
            pnl = trade.get('pnl', 0)
            coin_performance[symbol]['pnl'] += pnl
            if pnl > 0:
                coin_performance[symbol]['wins'] += 1
            else:
                coin_performance[symbol]['losses'] += 1
    
    logger.info("\n코인별 상세 성과:")
    logger.info("-" * 80)
    logger.info(f"{'코인':<12} {'거래':<6} {'매수':<6} {'매도':<6} {'승률':<8} {'손익':<15}")
    logger.info("-" * 80)
    
    for symbol, perf in sorted(coin_performance.items(), key=lambda x: x[1]['pnl'], reverse=True):
        win_rate_coin = perf['wins'] / perf['sells'] if perf['sells'] > 0 else 0
        logger.info(
            f"{symbol:<12} {perf['trades']:<6} {perf['buys']:<6} {perf['sells']:<6} "
            f"{win_rate_coin:>6.1%}  ${perf['pnl']:>12,.2f}"
        )
    
    # 5. 결과 저장
    logger.info("\n[5/5] 결과 저장 중...")
    
    # crypto_results 폴더 생성
    os.makedirs('crypto_results', exist_ok=True)
    
    # 거래 내역 저장
    trades_df = pd.DataFrame(backtester.trades)
    trades_df.to_csv('crypto_results/crypto_trades.csv', index=False)
    logger.info("  ✓ 거래 내역 저장: crypto_results/crypto_trades.csv")
    
    # 포트폴리오 가치 저장
    portfolio_df = pd.DataFrame({
        'Date': backtester.dates,
        'Portfolio_Value': backtester.portfolio_values
    })
    portfolio_df.to_csv('crypto_results/crypto_portfolio.csv', index=False)
    logger.info("  ✓ 포트폴리오 저장: crypto_results/crypto_portfolio.csv")
    
    # 성과 요약 저장
    summary = {
        '초기자본': INITIAL_CAPITAL,
        '최종자산': final_value,
        '총수익': final_value - INITIAL_CAPITAL,
        '총수익률': f"{total_return:.2%}",
        '연환산수익률': f"{annual_return:.2%}",
        '샤프비율': f"{sharpe_ratio:.2f}",
        '최대낙폭': f"{max_drawdown:.2%}",
        '총거래횟수': len(backtester.trades),
        '승률': f"{win_rate:.2%}",
        '평균수익': f"${avg_win:.2f}",
        '평균손실': f"${avg_loss:.2f}",
        '수익팩터': f"{profit_factor:.2f}"
    }
    
    summary_df = pd.DataFrame([summary]).T
    summary_df.columns = ['값']
    summary_df.to_csv('crypto_results/crypto_summary.csv')
    logger.info("  ✓ 성과 요약 저장: crypto_results/crypto_summary.csv")
    
    # 코인별 성과 저장
    coin_perf_df = pd.DataFrame(coin_performance).T
    coin_perf_df.to_csv('crypto_results/crypto_coin_performance.csv')
    logger.info("  ✓ 코인별 성과 저장: crypto_results/crypto_coin_performance.csv")
    
    logger.info("\n" + "=" * 80)
    logger.info("백테스팅 완료!")
    logger.info("=" * 80)
    
    return {
        'backtester': backtester,
        'final_value': final_value,
        'total_return': total_return,
        'annual_return': annual_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'coin_performance': coin_performance
    }

if __name__ == "__main__":
    try:
        results = run_crypto_backtest()
        print("\n백테스트가 성공적으로 완료되었습니다!")
        print("결과 파일은 'crypto_results' 폴더에 저장되었습니다.")
    except Exception as e:
        logger.error(f"백테스트 실행 중 오류 발생: {str(e)}", exc_info=True)
        print(f"\n오류 발생: {str(e)}")


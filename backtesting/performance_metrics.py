"""
성과 지표 계산 모듈
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

from utils.logger import setup_logger

logger = setup_logger("performance_metrics")

class PerformanceMetrics:
    """성과 지표 계산 클래스"""
    
    def __init__(self):
        """초기화"""
        pass
    
    def calculate_all_metrics(self, daily_values: pd.DataFrame, 
                            trade_history: pd.DataFrame,
                            initial_capital: float) -> Dict:
        """
        모든 성과 지표 계산
        
        Args:
            daily_values (pd.DataFrame): 일일 포트폴리오 가치
            trade_history (pd.DataFrame): 거래 내역
            initial_capital (float): 초기 자본
        
        Returns:
            Dict: 성과 지표 딕셔너리
        """
        metrics = {}
        
        # 기본 수익률 지표
        metrics.update(self._calculate_return_metrics(daily_values, initial_capital))
        
        # 리스크 지표
        metrics.update(self._calculate_risk_metrics(daily_values))
        
        # 거래 지표
        metrics.update(self._calculate_trade_metrics(trade_history))
        
        # 기타 지표
        metrics.update(self._calculate_other_metrics(daily_values, trade_history))
        
        return metrics
    
    def _calculate_return_metrics(self, daily_values: pd.DataFrame, 
                                initial_capital: float) -> Dict:
        """수익률 지표 계산"""
        if daily_values.empty:
            return {}
        
        final_value = daily_values['portfolio_value'].iloc[-1]
        total_return = (final_value - initial_capital) / initial_capital
        
        # 일일 수익률
        daily_returns = daily_values['portfolio_value'].pct_change().dropna()
        
        # 연환산 수익률
        num_days = len(daily_values)
        annualized_return = (1 + total_return) ** (252 / num_days) - 1
        
        # 기하평균 수익률
        geometric_mean = (daily_returns + 1).prod() ** (252 / len(daily_returns)) - 1
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'geometric_mean_return': geometric_mean,
            'final_value': final_value,
            'initial_capital': initial_capital
        }
    
    def _calculate_risk_metrics(self, daily_values: pd.DataFrame) -> Dict:
        """리스크 지표 계산"""
        if daily_values.empty:
            return {}
        
        daily_returns = daily_values['portfolio_value'].pct_change().dropna()
        
        if daily_returns.empty:
            return {}
        
        # 변동성
        volatility = daily_returns.std() * np.sqrt(252)
        
        # 샤프 비율 (무위험 수익률 0% 가정)
        sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0
        
        # 소르티노 비율 (하방 변동성만 고려)
        downside_returns = daily_returns[daily_returns < 0]
        downside_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = daily_returns.mean() / downside_volatility * np.sqrt(252) if downside_volatility > 0 else 0
        
        # 최대 낙폭 (Maximum Drawdown)
        cumulative_max = daily_values['portfolio_value'].expanding().max()
        drawdown = (daily_values['portfolio_value'] - cumulative_max) / cumulative_max
        max_drawdown = drawdown.min()
        
        # 최대 낙폭 기간
        drawdown_periods = self._calculate_drawdown_periods(drawdown)
        max_drawdown_duration = max(drawdown_periods) if drawdown_periods else 0
        
        # VaR (Value at Risk) - 95% 신뢰구간
        var_95 = np.percentile(daily_returns, 5)
        
        # CVaR (Conditional Value at Risk)
        cvar_95 = daily_returns[daily_returns <= var_95].mean()
        
        return {
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'max_drawdown_duration': max_drawdown_duration,
            'var_95': var_95,
            'cvar_95': cvar_95
        }
    
    def _calculate_trade_metrics(self, trade_history: pd.DataFrame) -> Dict:
        """거래 지표 계산"""
        if trade_history.empty:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'avg_trade_duration': 0
            }
        
        # 기본 통계
        total_trades = len(trade_history)
        
        # 매도 거래만 필터링 (실현 손익)
        sell_trades = trade_history[trade_history['order_type'] == 'SELL']
        
        if sell_trades.empty:
            return {
                'total_trades': total_trades,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'avg_trade_duration': 0
            }
        
        # 승률 계산
        winning_trades = sell_trades[sell_trades['pnl'] > 0]
        losing_trades = sell_trades[sell_trades['pnl'] < 0]
        
        win_rate = len(winning_trades) / len(sell_trades) if len(sell_trades) > 0 else 0
        
        # 평균 수익/손실
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
        
        # 수익 팩터
        total_wins = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        total_losses = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # 평균 거래 기간 (간단한 추정)
        avg_trade_duration = 5  # 기본값 (실제로는 포지션 진입/청산 시간 계산 필요)
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'avg_trade_duration': avg_trade_duration,
            'total_wins': total_wins,
            'total_losses': total_losses
        }
    
    def _calculate_other_metrics(self, daily_values: pd.DataFrame, 
                               trade_history: pd.DataFrame) -> Dict:
        """기타 지표 계산"""
        if daily_values.empty:
            return {}
        
        # 칼마 비율 (Calmar Ratio)
        annualized_return = self._calculate_return_metrics(daily_values, daily_values['portfolio_value'].iloc[0])['annualized_return']
        max_drawdown = self._calculate_risk_metrics(daily_values)['max_drawdown']
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # 연속 수익/손실
        daily_returns = daily_values['portfolio_value'].pct_change().dropna()
        consecutive_stats = self._calculate_consecutive_stats(daily_returns)
        
        # 월별 수익률
        monthly_returns = self._calculate_monthly_returns(daily_values)
        
        return {
            'calmar_ratio': calmar_ratio,
            'consecutive_wins': consecutive_stats['max_consecutive_wins'],
            'consecutive_losses': consecutive_stats['max_consecutive_losses'],
            'monthly_returns': monthly_returns,
            'positive_months': len([r for r in monthly_returns if r > 0]),
            'negative_months': len([r for r in monthly_returns if r < 0])
        }
    
    def _calculate_drawdown_periods(self, drawdown: pd.Series) -> List[int]:
        """낙폭 기간 계산"""
        periods = []
        current_period = 0
        
        for dd in drawdown:
            if dd < 0:
                current_period += 1
            else:
                if current_period > 0:
                    periods.append(current_period)
                current_period = 0
        
        if current_period > 0:
            periods.append(current_period)
        
        return periods
    
    def _calculate_consecutive_stats(self, returns: pd.Series) -> Dict:
        """연속 수익/손실 통계"""
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0
        
        for ret in returns:
            if ret > 0:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            elif ret < 0:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
            else:
                current_wins = 0
                current_losses = 0
        
        return {
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses
        }
    
    def _calculate_monthly_returns(self, daily_values: pd.DataFrame) -> List[float]:
        """월별 수익률 계산"""
        if daily_values.empty:
            return []
        
        daily_values['date'] = pd.to_datetime(daily_values['date'])
        daily_values.set_index('date', inplace=True)
        
        # 월별 리샘플링
        monthly = daily_values['portfolio_value'].resample('M').last()
        monthly_returns = monthly.pct_change().dropna().tolist()
        
        return monthly_returns
    
    def compare_with_benchmark(self, strategy_returns: pd.Series, 
                             benchmark_returns: pd.Series) -> Dict:
        """벤치마크와 비교"""
        if strategy_returns.empty or benchmark_returns.empty:
            return {}
        
        # 공통 인덱스로 정렬
        common_index = strategy_returns.index.intersection(benchmark_returns.index)
        if len(common_index) == 0:
            return {}
        
        strategy_aligned = strategy_returns.loc[common_index]
        benchmark_aligned = benchmark_returns.loc[common_index]
        
        # 베타 계산
        covariance = np.cov(strategy_aligned, benchmark_aligned)[0, 1]
        benchmark_variance = np.var(benchmark_aligned)
        beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
        
        # 알파 계산 (무위험 수익률 0% 가정)
        strategy_mean = strategy_aligned.mean() * 252
        benchmark_mean = benchmark_aligned.mean() * 252
        alpha = strategy_mean - beta * benchmark_mean
        
        # 상관관계
        correlation = np.corrcoef(strategy_aligned, benchmark_aligned)[0, 1]
        
        # 정보 비율 (Information Ratio)
        excess_returns = strategy_aligned - benchmark_aligned
        information_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
        
        return {
            'beta': beta,
            'alpha': alpha,
            'correlation': correlation,
            'information_ratio': information_ratio,
            'excess_return': excess_returns.mean() * 252
        }

# 전역 성과 지표 계산기 인스턴스
performance_metrics = PerformanceMetrics()

def calculate_performance_metrics(daily_values: pd.DataFrame, 
                                trade_history: pd.DataFrame,
                                initial_capital: float) -> Dict:
    """
    편의 함수: 성과 지표 계산
    
    Args:
        daily_values (pd.DataFrame): 일일 포트폴리오 가치
        trade_history (pd.DataFrame): 거래 내역
        initial_capital (float): 초기 자본
    
    Returns:
        Dict: 성과 지표 딕셔너리
    """
    return performance_metrics.calculate_all_metrics(daily_values, trade_history, initial_capital)


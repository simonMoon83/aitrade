"""
백테스팅 보고서 생성 모듈
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os
from datetime import datetime
from typing import Dict, List, Optional
import jinja2

from config import REPORTS_DIR
from utils.logger import setup_logger
from backtesting.performance_metrics import calculate_performance_metrics

logger = setup_logger("report_generator")

class ReportGenerator:
    """백테스팅 보고서 생성 클래스"""
    
    def __init__(self):
        """초기화"""
        self.reports_dir = REPORTS_DIR
        os.makedirs(self.reports_dir, exist_ok=True)
        
        # 한글 폰트 설정
        plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['axes.unicode_minus'] = False
        
    def generate_report(self, results: Dict, symbols: List[str], 
                       start_date: str, end_date: str) -> str:
        """
        종합 보고서 생성
        
        Args:
            results (Dict): 백테스팅 결과
            symbols (List[str]): 거래 종목
            start_date (str): 시작 날짜
            end_date (str): 종료 날짜
        
        Returns:
            str: 생성된 보고서 파일 경로
        """
        logger.info("백테스팅 보고서 생성 시작")
        
        try:
            # HTML 보고서 생성
            html_report = self._generate_html_report(results, symbols, start_date, end_date)
            
            # 차트 생성
            self._generate_charts(results)
            
            # CSV 데이터 내보내기
            self._export_csv_data(results)
            
            logger.info(f"보고서 생성 완료: {html_report}")
            return html_report
            
        except Exception as e:
            logger.error(f"보고서 생성 실패: {str(e)}")
            return ""
    
    def _generate_html_report(self, results: Dict, symbols: List[str],
                            start_date: str, end_date: str) -> str:
        """HTML 보고서 생성"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backtest_report_{timestamp}.html"
        filepath = os.path.join(self.reports_dir, filename)
        
        # 성과 지표 계산
        performance = results.get('performance', {})
        trade_history = results.get('trade_history', pd.DataFrame())
        daily_values = results.get('daily_values', pd.DataFrame())
        
        # HTML 템플릿
        html_template = """
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI 주식 트레이더 백테스팅 보고서</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { text-align: center; margin-bottom: 30px; }
                .section { margin-bottom: 30px; }
                .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
                .metric-card { background: #f5f5f5; padding: 15px; border-radius: 5px; text-align: center; }
                .metric-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
                .metric-label { font-size: 14px; color: #7f8c8d; margin-top: 5px; }
                .positive { color: #27ae60; }
                .negative { color: #e74c3c; }
                table { width: 100%; border-collapse: collapse; margin-top: 10px; }
                th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background-color: #f2f2f2; }
                .chart-container { margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>AI 주식 트레이더 백테스팅 보고서</h1>
                <p>전략: 저점매수-고점매도 | 기간: {{ start_date }} ~ {{ end_date }}</p>
                <p>종목: {{ symbols_str }}</p>
            </div>
            
            <div class="section">
                <h2>1. 전략 개요</h2>
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-value">{{ initial_capital | currency }}</div>
                        <div class="metric-label">초기 자본</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{ final_value | currency }}</div>
                        <div class="metric-label">최종 자산</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value {{ 'positive' if total_return > 0 else 'negative' }}">{{ total_return | percent }}</div>
                        <div class="metric-label">총 수익률</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{ annualized_return | percent }}</div>
                        <div class="metric-label">연환산 수익률</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>2. 수익성 지표</h2>
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-value">{{ total_trades }}</div>
                        <div class="metric-label">총 거래 횟수</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{ win_rate | percent }}</div>
                        <div class="metric-label">승률</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{ avg_win | currency }}</div>
                        <div class="metric-label">평균 수익</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{ avg_loss | currency }}</div>
                        <div class="metric-label">평균 손실</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{ profit_factor | round(2) }}</div>
                        <div class="metric-label">수익 팩터</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>3. 리스크 지표</h2>
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-value">{{ volatility | percent }}</div>
                        <div class="metric-label">변동성</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{ sharpe_ratio | round(2) }}</div>
                        <div class="metric-label">샤프 비율</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{ sortino_ratio | round(2) }}</div>
                        <div class="metric-label">소르티노 비율</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value negative">{{ max_drawdown | percent }}</div>
                        <div class="metric-label">최대 낙폭</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{ max_drawdown_duration }}</div>
                        <div class="metric-label">최대 낙폭 기간 (일)</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>4. 거래 내역</h2>
                {{ trade_history_table }}
            </div>
            
            <div class="section">
                <h2>5. 종목별 성과</h2>
                {{ symbol_performance_table }}
            </div>
            
            <div class="section">
                <h2>6. 벤치마크 비교</h2>
                {{ benchmark_comparison }}
            </div>
            
            <div class="section">
                <h2>7. 실전 적용 권고사항</h2>
                <div style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
                    <h3>권장사항:</h3>
                    <ul>
                        <li>승률이 {{ win_rate | percent }}로 {% if win_rate > 0.5 %}양호{% else %}개선 필요{% endif %}합니다</li>
                        <li>샤프 비율이 {{ sharpe_ratio | round(2) }}로 {% if sharpe_ratio > 1 %}우수{% else %}보통{% endif %}합니다</li>
                        <li>최대 낙폭이 {{ max_drawdown | percent }}로 {% if max_drawdown > -0.2 %}주의 필요{% else %}양호{% endif %}합니다</li>
                        <li>{% if total_return > 0.1 %}수익률이 양호하여 실전 적용을 고려할 수 있습니다{% else %}추가 전략 개선이 필요합니다{% endif %}</li>
                    </ul>
                </div>
            </div>
            
            <div class="section">
                <p style="text-align: center; color: #7f8c8d; font-size: 12px;">
                    보고서 생성 시간: {{ timestamp }}<br>
                    AI 주식 트레이더 v1.0
                </p>
            </div>
        </body>
        </html>
        """
        
        # 데이터 준비
        template_data = {
            'start_date': start_date,
            'end_date': end_date,
            'symbols_str': ', '.join(symbols),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'initial_capital': performance.get('initial_capital', 0),
            'final_value': performance.get('final_value', 0),
            'total_return': performance.get('total_return', 0),
            'annualized_return': performance.get('annualized_return', 0),
            'total_trades': performance.get('total_trades', 0),
            'win_rate': performance.get('win_rate', 0),
            'avg_win': performance.get('avg_win', 0),
            'avg_loss': performance.get('avg_loss', 0),
            'profit_factor': performance.get('profit_factor', 0),
            'volatility': performance.get('volatility', 0),
            'sharpe_ratio': performance.get('sharpe_ratio', 0),
            'sortino_ratio': performance.get('sortino_ratio', 0),
            'max_drawdown': performance.get('max_drawdown', 0),
            'max_drawdown_duration': performance.get('max_drawdown_duration', 0)
        }
        
        # 테이블 생성
        template_data['trade_history_table'] = self._generate_trade_history_table(trade_history)
        template_data['symbol_performance_table'] = self._generate_symbol_performance_table(results.get('symbol_performance', {}))
        template_data['benchmark_comparison'] = self._generate_benchmark_comparison(results.get('benchmark_performance', {}))
        
        # 커스텀 필터 정의
        def currency_filter(value):
            return f"${value:,.2f}"

        def percent_filter(value):
            return f"{value:.2%}"

        # Jinja2 Environment with custom filters
        env = jinja2.Environment()
        env.filters['currency'] = currency_filter
        env.filters['percent'] = percent_filter

        # 템플릿 렌더링
        template = env.from_string(html_template)
        html_content = template.render(**template_data)
        
        # 파일 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def _generate_trade_history_table(self, trade_history: pd.DataFrame) -> str:
        """거래 내역 테이블 생성"""
        if trade_history.empty:
            return "<p>거래 내역이 없습니다.</p>"
        
        # 최근 20개 거래만 표시
        recent_trades = trade_history.tail(20)
        
        html = "<table><tr><th>날짜</th><th>종목</th><th>거래</th><th>수량</th><th>가격</th><th>손익</th></tr>"
        
        for _, trade in recent_trades.iterrows():
            pnl_class = "positive" if trade['pnl'] > 0 else "negative" if trade['pnl'] < 0 else ""
            html += f"""
            <tr>
                <td>{trade['timestamp'].strftime('%Y-%m-%d')}</td>
                <td>{trade['symbol']}</td>
                <td>{trade['order_type']}</td>
                <td>{trade['quantity']}</td>
                <td>${trade['price']:.2f}</td>
                <td class="{pnl_class}">${trade['pnl']:.2f}</td>
            </tr>
            """
        
        html += "</table>"
        return html
    
    def _generate_symbol_performance_table(self, symbol_performance: Dict) -> str:
        """종목별 성과 테이블 생성"""
        if not symbol_performance:
            return "<p>종목별 성과 데이터가 없습니다.</p>"
        
        html = "<table><tr><th>종목</th><th>총 수익률</th><th>거래 횟수</th><th>총 손익</th></tr>"
        
        for symbol, perf in symbol_performance.items():
            return_class = "positive" if perf['total_return'] > 0 else "negative"
            pnl_class = "positive" if perf['total_pnl'] > 0 else "negative" if perf['total_pnl'] < 0 else ""
            
            html += f"""
            <tr>
                <td>{symbol}</td>
                <td class="{return_class}">{perf['total_return']:.2%}</td>
                <td>{perf['num_trades']}</td>
                <td class="{pnl_class}">${perf['total_pnl']:.2f}</td>
            </tr>
            """
        
        html += "</table>"
        return html
    
    def _generate_benchmark_comparison(self, benchmark_performance: Dict) -> str:
        """벤치마크 비교 생성"""
        if not benchmark_performance:
            return "<p>벤치마크 데이터가 없습니다.</p>"
        
        return f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value">{benchmark_performance.get('total_return', 0):.2%}</div>
                <div class="metric-label">S&P 500 수익률</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{benchmark_performance.get('volatility', 0):.2%}</div>
                <div class="metric-label">S&P 500 변동성</div>
            </div>
        </div>
        """
    
    def _generate_charts(self, results: Dict):
        """차트 생성"""
        try:
            daily_values = results.get('daily_values', pd.DataFrame())
            if daily_values.empty:
                return
            
            # 포트폴리오 가치 변화 차트
            self._create_portfolio_value_chart(daily_values)
            
            # 수익률 분포 차트
            self._create_returns_distribution_chart(daily_values)
            
            # 월별 수익률 히트맵
            self._create_monthly_returns_heatmap(daily_values)
            
        except Exception as e:
            logger.error(f"차트 생성 실패: {str(e)}")
    
    def _create_portfolio_value_chart(self, daily_values: pd.DataFrame):
        """포트폴리오 가치 변화 차트"""
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=daily_values['date'],
            y=daily_values['portfolio_value'],
            mode='lines',
            name='포트폴리오 가치',
            line=dict(color='blue', width=2)
        ))
        
        fig.update_layout(
            title='포트폴리오 가치 변화',
            xaxis_title='날짜',
            yaxis_title='포트폴리오 가치 ($)',
            template='plotly_white'
        )
        
        chart_path = os.path.join(self.reports_dir, 'portfolio_value_chart.html')
        fig.write_html(chart_path)
    
    def _create_returns_distribution_chart(self, daily_values: pd.DataFrame):
        """수익률 분포 차트"""
        daily_returns = daily_values['portfolio_value'].pct_change().dropna()
        
        fig = go.Figure()
        
        fig.add_trace(go.Histogram(
            x=daily_returns,
            nbinsx=50,
            name='일일 수익률 분포',
            marker_color='lightblue'
        ))
        
        fig.update_layout(
            title='일일 수익률 분포',
            xaxis_title='일일 수익률',
            yaxis_title='빈도',
            template='plotly_white'
        )
        
        chart_path = os.path.join(self.reports_dir, 'returns_distribution_chart.html')
        fig.write_html(chart_path)
    
    def _create_monthly_returns_heatmap(self, daily_values: pd.DataFrame):
        """월별 수익률 히트맵"""
        # 데이터프레임 복사본 생성하여 원본 보존
        df = daily_values.copy()
        
        # 날짜 컬럼을 datetime으로 변환
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # 월별 수익률 계산
        monthly_returns = df['portfolio_value'].resample('ME').last().pct_change().dropna()
        
        # 데이터프레임으로 변환
        monthly_df = monthly_returns.to_frame(name='return')
        
        # 연도와 월 추출
        monthly_df['year'] = monthly_df.index.year
        monthly_df['month'] = monthly_df.index.month
        
        pivot_table = monthly_df.pivot_table(
            values='return', 
            index='year', 
            columns='month', 
            aggfunc='first'
        )
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_table.values,
            x=['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'],
            y=pivot_table.index,
            colorscale='RdYlGn',
            zmid=0
        ))
        
        fig.update_layout(
            title='월별 수익률 히트맵',
            xaxis_title='월',
            yaxis_title='연도',
            template='plotly_white'
        )
        
        chart_path = os.path.join(self.reports_dir, 'monthly_returns_heatmap.html')
        fig.write_html(chart_path)
    
    def _export_csv_data(self, results: Dict):
        """CSV 데이터 내보내기"""
        try:
            # 일일 가치 데이터
            daily_values = results.get('daily_values', pd.DataFrame())
            if not daily_values.empty:
                csv_path = os.path.join(self.reports_dir, 'daily_values.csv')
                daily_values.to_csv(csv_path, index=False)
            
            # 거래 내역
            trade_history = results.get('trade_history', pd.DataFrame())
            if not trade_history.empty:
                csv_path = os.path.join(self.reports_dir, 'trade_history.csv')
                trade_history.to_csv(csv_path, index=False)
            
            # 성과 지표
            performance = results.get('performance', {})
            if performance:
                perf_df = pd.DataFrame([performance])
                csv_path = os.path.join(self.reports_dir, 'performance_metrics.csv')
                perf_df.to_csv(csv_path, index=False)
            
        except Exception as e:
            logger.error(f"CSV 내보내기 실패: {str(e)}")

# 전역 보고서 생성기 인스턴스
report_generator = ReportGenerator()

def generate_backtest_report(results: Dict, symbols: List[str], 
                           start_date: str, end_date: str) -> str:
    """
    편의 함수: 백테스팅 보고서 생성
    
    Args:
        results (Dict): 백테스팅 결과
        symbols (List[str]): 거래 종목
        start_date (str): 시작 날짜
        end_date (str): 종료 날짜
    
    Returns:
        str: 생성된 보고서 파일 경로
    """
    return report_generator.generate_report(results, symbols, start_date, end_date)


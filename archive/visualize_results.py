"""
개선된 전략 결과 시각화
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

def create_performance_dashboard():
    """성과 대시보드 생성"""
    
    # 데이터 로드
    try:
        portfolio_df = pd.read_csv('improved_strategy_portfolio.csv')
        trades_df = pd.read_csv('improved_strategy_trades.csv')
        portfolio_df['Date'] = pd.to_datetime(portfolio_df['Date'])
        trades_df['date'] = pd.to_datetime(trades_df['date'])
    except Exception as e:
        print(f"데이터 로드 실패: {str(e)}")
        return
    
    # 누적 수익률 계산
    portfolio_df['Cumulative_Return'] = ((portfolio_df['Portfolio_Value'] / 10000) - 1) * 100
    
    # 일일 수익률 계산
    portfolio_df['Daily_Return'] = portfolio_df['Portfolio_Value'].pct_change()
    
    # 1. 대시보드 생성 (4개 서브플롯)
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('포트폴리오 가치 변화', '누적 수익률', '일일 수익률 분포', '종목별 거래 횟수'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"type": "histogram"}, {"type": "bar"}]]
    )
    
    # 1. 포트폴리오 가치 추이
    fig.add_trace(
        go.Scatter(x=portfolio_df['Date'], y=portfolio_df['Portfolio_Value'],
                   mode='lines', name='포트폴리오 가치', line=dict(color='blue', width=2)),
        row=1, col=1
    )
    
    # 매수/매도 시점 표시
    buy_trades = trades_df[trades_df['type'] == 'BUY']
    sell_trades = trades_df[trades_df['type'] == 'SELL']
    
    # 2. 누적 수익률
    fig.add_trace(
        go.Scatter(x=portfolio_df['Date'], y=portfolio_df['Cumulative_Return'],
                   mode='lines', name='누적 수익률 (%)', line=dict(color='green', width=2)),
        row=1, col=2
    )
    
    # 3. 일일 수익률 히스토그램
    fig.add_trace(
        go.Histogram(x=portfolio_df['Daily_Return']*100, name='일일 수익률',
                     nbinsx=50, marker_color='lightblue'),
        row=2, col=1
    )
    
    # 4. 종목별 거래 횟수
    symbol_trades = trades_df.groupby('symbol').size().sort_values(ascending=False)
    fig.add_trace(
        go.Bar(x=symbol_trades.index, y=symbol_trades.values, name='거래 횟수',
               marker_color='orange'),
        row=2, col=2
    )
    
    # 레이아웃 업데이트
    fig.update_xaxes(title_text="날짜", row=1, col=1)
    fig.update_yaxes(title_text="포트폴리오 가치 ($)", row=1, col=1)
    
    fig.update_xaxes(title_text="날짜", row=1, col=2)
    fig.update_yaxes(title_text="수익률 (%)", row=1, col=2)
    
    fig.update_xaxes(title_text="일일 수익률 (%)", row=2, col=1)
    fig.update_yaxes(title_text="빈도", row=2, col=1)
    
    fig.update_xaxes(title_text="종목", row=2, col=2)
    fig.update_yaxes(title_text="거래 횟수", row=2, col=2)
    
    fig.update_layout(
        title_text="개선된 전략 성과 대시보드 (2023-01 ~ 2024-12)",
        height=800,
        showlegend=False
    )
    
    fig.write_html('improved_strategy_dashboard.html')
    print("대시보드 생성 완료: improved_strategy_dashboard.html")
    
    # 2. 종목별 손익 차트
    symbol_pnl = trades_df[trades_df['type'] == 'SELL'].groupby('symbol')['pnl'].sum().sort_values(ascending=False)
    
    fig_pnl = go.Figure(data=[
        go.Bar(x=symbol_pnl.index, y=symbol_pnl.values, 
               marker_color=['green' if x > 0 else 'red' for x in symbol_pnl.values])
    ])
    
    fig_pnl.update_layout(
        title='종목별 총 손익',
        xaxis_title='종목',
        yaxis_title='손익 ($)',
        height=500
    )
    
    fig_pnl.write_html('symbol_pnl_chart.html')
    print("종목별 손익 차트 생성 완료: symbol_pnl_chart.html")
    
    # 3. 거래 타이밍 분석
    trades_by_month = trades_df.groupby([pd.Grouper(key='date', freq='M'), 'type']).size().unstack(fill_value=0)
    
    fig_timing = go.Figure()
    fig_timing.add_trace(go.Scatter(x=trades_by_month.index, y=trades_by_month['BUY'], 
                                    mode='lines+markers', name='매수', line=dict(color='blue')))
    fig_timing.add_trace(go.Scatter(x=trades_by_month.index, y=trades_by_month['SELL'], 
                                    mode='lines+markers', name='매도', line=dict(color='red')))
    
    fig_timing.update_layout(
        title='월별 거래 타이밍',
        xaxis_title='월',
        yaxis_title='거래 횟수',
        height=500
    )
    
    fig_timing.write_html('trade_timing_chart.html')
    print("거래 타이밍 차트 생성 완료: trade_timing_chart.html")
    
    # 4. 성과 요약 테이블
    portfolio_value_start = portfolio_df['Portfolio_Value'].iloc[0]
    portfolio_value_end = portfolio_df['Portfolio_Value'].iloc[-1]
    total_return = (portfolio_value_end / portfolio_value_start - 1) * 100
    
    # 승률 계산
    profitable_trades = trades_df[trades_df['type'] == 'SELL'][trades_df['pnl'] > 0]
    total_sell_trades = len(trades_df[trades_df['type'] == 'SELL'])
    win_rate = len(profitable_trades) / total_sell_trades * 100 if total_sell_trades > 0 else 0
    
    summary_data = {
        '지표': ['초기 자본', '최종 자산', '총 수익률', '승률', '총 거래 횟수', '최대 일일 수익률', '최대 일일 손실률'],
        '값': [
            f'${portfolio_value_start:,.0f}',
            f'${portfolio_value_end:,.0f}',
            f'{total_return:.2f}%',
            f'{win_rate:.2f}%',
            f'{len(trades_df)}회',
            f'{portfolio_df["Daily_Return"].max()*100:.2f}%',
            f'{portfolio_df["Daily_Return"].min()*100:.2f}%'
        ]
    }
    
    summary_df = pd.DataFrame(summary_data)
    
    fig_table = go.Figure(data=[go.Table(
        header=dict(values=['지표', '값'],
                    fill_color='lightblue',
                    align='left'),
        cells=dict(values=[summary_df['지표'], summary_df['값']],
                   fill_color='white',
                   align='left'))
    ])
    
    fig_table.update_layout(
        title='전략 성과 요약',
        height=400
    )
    
    fig_table.write_html('performance_summary_table.html')
    print("성과 요약 테이블 생성 완료: performance_summary_table.html")
    
    print("\n=== 개선된 전략 성과 요약 ===")
    print(f"총 수익률: {total_return:.2f}%")
    print(f"승률: {win_rate:.2f}%")
    print(f"최종 자산: ${portfolio_value_end:,.2f}")

if __name__ == "__main__":
    create_performance_dashboard()

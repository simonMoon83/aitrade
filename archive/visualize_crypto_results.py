"""
암호화폐 백테스트 결과 시각화 및 주식 전략과 비교
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def visualize_crypto_results():
    """암호화폐 백테스트 결과 시각화"""
    
    print("암호화폐 백테스트 결과 시각화 중...")
    
    # 1. 포트폴리오 가치 차트
    crypto_portfolio = pd.read_csv('crypto_results/crypto_portfolio.csv')
    crypto_portfolio['Date'] = pd.to_datetime(crypto_portfolio['Date'])
    
    # 주식 포트폴리오 데이터 (있으면 로드)
    if os.path.exists('improved_results/improved_strategy_portfolio.csv'):
        stock_portfolio = pd.read_csv('improved_results/improved_strategy_portfolio.csv')
        stock_portfolio['Date'] = pd.to_datetime(stock_portfolio['Date'])
        has_stock_data = True
    else:
        has_stock_data = False
    
    # 포트폴리오 비교 차트
    fig = go.Figure()
    
    # 암호화폐 라인
    fig.add_trace(go.Scatter(
        x=crypto_portfolio['Date'],
        y=crypto_portfolio['Portfolio_Value'],
        mode='lines',
        name='암호화폐 포트폴리오',
        line=dict(color='orange', width=2)
    ))
    
    # 주식 라인 (있으면 추가)
    if has_stock_data:
        fig.add_trace(go.Scatter(
            x=stock_portfolio['Date'],
            y=stock_portfolio['Portfolio_Value'],
            mode='lines',
            name='주식 포트폴리오',
            line=dict(color='blue', width=2)
        ))
    
    # 기준선 (초기자본)
    fig.add_hline(y=10000, line_dash="dash", line_color="gray",
                  annotation_text="초기자본 $10,000")
    
    fig.update_layout(
        title='포트폴리오 가치 비교: 암호화폐 vs 주식',
        xaxis_title='날짜',
        yaxis_title='포트폴리오 가치 ($)',
        hovermode='x unified',
        template='plotly_white',
        height=600
    )
    
    fig.write_html('crypto_results/portfolio_comparison.html')
    print("  ✓ 포트폴리오 비교 차트 생성")
    
    # 2. 수익률 비교 차트
    crypto_portfolio['Return'] = (crypto_portfolio['Portfolio_Value'] / 10000 - 1) * 100
    
    fig2 = go.Figure()
    
    fig2.add_trace(go.Scatter(
        x=crypto_portfolio['Date'],
        y=crypto_portfolio['Return'],
        mode='lines',
        name='암호화폐 수익률',
        fill='tozeroy',
        line=dict(color='orange', width=2)
    ))
    
    if has_stock_data:
        stock_portfolio['Return'] = (stock_portfolio['Portfolio_Value'] / 10000 - 1) * 100
        fig2.add_trace(go.Scatter(
            x=stock_portfolio['Date'],
            y=stock_portfolio['Return'],
            mode='lines',
            name='주식 수익률',
            fill='tozeroy',
            line=dict(color='blue', width=2)
        ))
    
    fig2.update_layout(
        title='누적 수익률 비교',
        xaxis_title='날짜',
        yaxis_title='수익률 (%)',
        hovermode='x unified',
        template='plotly_white',
        height=600
    )
    
    fig2.write_html('crypto_results/returns_comparison.html')
    print("  ✓ 수익률 비교 차트 생성")
    
    # 3. 거래 내역 차트
    crypto_trades = pd.read_csv('crypto_results/crypto_trades.csv')
    crypto_trades['date'] = pd.to_datetime(crypto_trades['date'])
    
    # 매수/매도 시점 표시
    buys = crypto_trades[crypto_trades['type'] == 'BUY']
    sells = crypto_trades[crypto_trades['type'] == 'SELL']
    
    fig3 = go.Figure()
    
    # 포트폴리오 가치
    fig3.add_trace(go.Scatter(
        x=crypto_portfolio['Date'],
        y=crypto_portfolio['Portfolio_Value'],
        mode='lines',
        name='포트폴리오 가치',
        line=dict(color='gray', width=1)
    ))
    
    # 매수 지점
    fig3.add_trace(go.Scatter(
        x=buys['date'],
        y=[10000] * len(buys),  # 간단하게 초기자본 라인에 표시
        mode='markers',
        name='매수',
        marker=dict(color='green', size=15, symbol='triangle-up')
    ))
    
    # 매도 지점
    fig3.add_trace(go.Scatter(
        x=sells['date'],
        y=[10000] * len(sells),
        mode='markers',
        name='매도',
        marker=dict(color='red', size=15, symbol='triangle-down')
    ))
    
    fig3.update_layout(
        title='거래 시점 분석',
        xaxis_title='날짜',
        yaxis_title='포트폴리오 가치 ($)',
        hovermode='x unified',
        template='plotly_white',
        height=600
    )
    
    fig3.write_html('crypto_results/trades_timeline.html')
    print("  ✓ 거래 시점 차트 생성")
    
    # 4. 코인별 성과 차트
    coin_perf = pd.read_csv('crypto_results/crypto_coin_performance.csv')
    coin_perf.columns = ['symbol'] + list(coin_perf.columns[1:])
    
    # 손익이 있는 코인만
    coin_perf_filtered = coin_perf[coin_perf['pnl'] != 0].sort_values('pnl', ascending=True)
    
    if not coin_perf_filtered.empty:
        fig4 = go.Figure()
        
        colors = ['green' if x > 0 else 'red' for x in coin_perf_filtered['pnl']]
        
        fig4.add_trace(go.Bar(
            y=coin_perf_filtered['symbol'],
            x=coin_perf_filtered['pnl'],
            orientation='h',
            marker=dict(color=colors),
            text=[f"${x:.2f}" for x in coin_perf_filtered['pnl']],
            textposition='outside'
        ))
        
        fig4.update_layout(
            title='코인별 손익',
            xaxis_title='손익 ($)',
            yaxis_title='코인',
            template='plotly_white',
            height=400
        )
        
        fig4.write_html('crypto_results/coin_performance.html')
        print("  ✓ 코인별 성과 차트 생성")
    
    # 5. 종합 리포트 생성
    create_summary_report(has_stock_data)
    
    print("\n시각화 완료! 'crypto_results' 폴더를 확인하세요.")

def create_summary_report(has_stock_data):
    """종합 비교 리포트 생성"""
    
    # 암호화폐 데이터
    crypto_summary = pd.read_csv('crypto_results/crypto_summary.csv', index_col=0)
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>암호화폐 백테스트 결과 리포트</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: #f5f7fa; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
            h2 { color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 15px; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th { background: #3498db; color: white; padding: 12px; text-align: left; }
            td { padding: 12px; border-bottom: 1px solid #ecf0f1; }
            tr:hover { background: #f8f9fa; }
            .metric { display: inline-block; margin: 15px; padding: 20px; background: #ecf0f1; border-radius: 8px; min-width: 200px; }
            .metric-label { font-size: 14px; color: #7f8c8d; }
            .metric-value { font-size: 28px; font-weight: bold; color: #2c3e50; margin-top: 5px; }
            .positive { color: #27ae60; }
            .negative { color: #e74c3c; }
            .warning { background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0; border-radius: 4px; }
            .info { background: #d1ecf1; padding: 15px; border-left: 4px solid #17a2b8; margin: 20px 0; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 암호화폐 백테스트 결과 리포트</h1>
            <p><strong>기간:</strong> 2023-01-01 ~ 2025-06-30 (2.5년)</p>
            <p><strong>대상:</strong> BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, MATIC, LINK (10개 코인)</p>
            
            <h2>📊 핵심 성과 지표</h2>
            <div style="text-align: center;">
    """
    
    # 메트릭 추가
    metrics = {
        '초기자본': crypto_summary.loc['초기자본', '값'],
        '최종자산': crypto_summary.loc['최종자산', '값'],
        '총수익률': crypto_summary.loc['총수익률', '값'],
        '연환산수익률': crypto_summary.loc['연환산수익률', '값'],
        '샤프비율': crypto_summary.loc['샤프비율', '값'],
        '최대낙폭': crypto_summary.loc['최대낙폭', '값'],
        '총거래횟수': crypto_summary.loc['총거래횟수', '값'],
        '승률': crypto_summary.loc['승률', '값']
    }
    
    for label, value in metrics.items():
        html += f"""
            <div class="metric">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
            </div>
        """
    
    html += """
            </div>
            
            <div class="warning">
                <strong>⚠️ 전략 개선 필요</strong><br>
                현재 결과가 예상보다 낮습니다 (3.98% 수익, 4회 거래). 
                전략의 매수 신호 조건이 너무 엄격하여 거래 기회를 놓치고 있습니다.
                <br><br>
                <strong>개선 방안:</strong>
                <ul>
                    <li>신호 강도 임계값 낮추기 (현재: 4.0 → 제안: 3.0)</li>
                    <li>RSI 임계값 완화 (현재: 30/70 → 제안: 35/65)</li>
                    <li>거래량 조건 완화</li>
                </ul>
            </div>
    """
    
    # 주식 비교 (있으면)
    if has_stock_data:
        stock_portfolio = pd.read_csv('improved_results/improved_strategy_portfolio.csv')
        stock_final = stock_portfolio['Portfolio_Value'].iloc[-1]
        stock_return = (stock_final / 10000 - 1) * 100
        
        html += f"""
            <h2>📈 주식 전략과 비교</h2>
            <table>
                <tr>
                    <th>구분</th>
                    <th>주식 전략</th>
                    <th>암호화폐 전략</th>
                    <th>차이</th>
                </tr>
                <tr>
                    <td>최종 자산</td>
                    <td>${stock_final:,.2f}</td>
                    <td>{metrics['최종자산']}</td>
                    <td class="{'positive' if float(metrics['최종자산'].replace('$','').replace(',','')) > stock_final else 'negative'}">
                        ${float(metrics['최종자산'].replace('$','').replace(',','')) - stock_final:,.2f}
                    </td>
                </tr>
                <tr>
                    <td>수익률</td>
                    <td>{stock_return:.2f}%</td>
                    <td>{metrics['총수익률']}</td>
                    <td class="{'positive' if float(metrics['총수익률'].replace('%','')) > stock_return else 'negative'}">
                        {float(metrics['총수익률'].replace('%','')) - stock_return:.2f}%
                    </td>
                </tr>
            </table>
            
            <div class="info">
                <strong>💡 결론</strong><br>
                현재 암호화폐 전략은 주식 전략보다 낮은 성과를 보이고 있습니다.
                전략 파라미터를 조정하여 재테스트가 필요합니다.
            </div>
        """
    
    html += """
            <h2>📁 생성된 파일</h2>
            <ul>
                <li><a href="portfolio_comparison.html">포트폴리오 비교 차트</a></li>
                <li><a href="returns_comparison.html">수익률 비교 차트</a></li>
                <li><a href="trades_timeline.html">거래 시점 분석</a></li>
                <li><a href="coin_performance.html">코인별 성과</a></li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    with open('crypto_results/summary_report.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("  ✓ 종합 리포트 생성: crypto_results/summary_report.html")

if __name__ == "__main__":
    visualize_crypto_results()


"""
간단한 Flask 웹 대시보드
"""

from flask import Flask, render_template_string
import glob
import os
from datetime import datetime

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Stock Trader Dashboard</title>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="5">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f7fa;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-label {
            font-size: 14px;
            color: #7f8c8d;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 32px;
            font-weight: bold;
            color: #2c3e50;
        }
        .positive {
            color: #27ae60;
        }
        .negative {
            color: #e74c3c;
        }
        .section {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .section h2 {
            margin-top: 0;
            color: #2c3e50;
        }
        .log-entry {
            font-family: 'Courier New', monospace;
            font-size: 12px;
            padding: 5px;
            border-bottom: 1px solid #ecf0f1;
        }
        .trade {
            color: #3498db;
        }
        .signal {
            color: #9b59b6;
        }
        .error {
            color: #e74c3c;
        }
        .status {
            text-align: center;
            padding: 10px;
            background: #27ae60;
            color: white;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .timestamp {
            text-align: center;
            color: #95a5a6;
            font-size: 12px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Stock Trader Dashboard</h1>

        <div class="status">
            System Running - Auto-refresh every 5 seconds
        </div>

        <div class="metrics">
            <div class="metric-card">
                <div class="metric-label">Portfolio Value</div>
                <div class="metric-value">${{ portfolio_value }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Cash</div>
                <div class="metric-value">${{ cash }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Positions</div>
                <div class="metric-value">{{ positions }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Return</div>
                <div class="metric-value {{ 'positive' if return_pct >= 0 else 'negative' }}">
                    {{ return_pct_display }}%
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Recent Activity</h2>
            {% for log in recent_logs %}
            <div class="log-entry {{ log.type }}">
                <span style="color: #95a5a6;">[{{ log.time }}]</span> {{ log.message }}
            </div>
            {% endfor %}
        </div>

        <div class="timestamp">
            Last Updated: {{ current_time }}
        </div>
    </div>
</body>
</html>
"""

def read_latest_log():
    """최신 로그 파일 읽기"""
    log_files = glob.glob('logs/*.log')
    if not log_files:
        return []

    latest_log = max(log_files, key=os.path.getmtime)

    try:
        with open(latest_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return lines
    except:
        return []

def parse_logs(lines):
    """로그 파싱"""
    portfolio_value = 10000.0
    cash = 10000.0
    positions = 0
    recent_logs = []

    for line in lines[-50:]:  # 최근 50줄
        line = line.strip()
        if not line:
            continue

        log_type = ''
        if 'PORTFOLIO - Value:' in line:
            try:
                portfolio_value = float(line.split('Value: $')[1].split(',')[0].replace(',', ''))
                cash = float(line.split('Cash: $')[1].split(',')[0].replace(',', ''))
                positions = int(line.split('Positions: ')[1].split()[0])
            except:
                pass

        # 로그 타입 분류
        if 'TRADE' in line or '매수' in line or '매도' in line:
            log_type = 'trade'
        elif 'SIGNAL' in line or '신호' in line:
            log_type = 'signal'
        elif 'ERROR' in line or '오류' in line:
            log_type = 'error'

        # 타임스탬프와 메시지 추출
        if ' - ' in line:
            parts = line.split(' - ')
            if len(parts) >= 3:
                timestamp = parts[0][-8:]  # HH:MM:SS만
                message = ' - '.join(parts[2:])
                recent_logs.append({
                    'time': timestamp,
                    'message': message[:100],
                    'type': log_type
                })

    return portfolio_value, cash, positions, recent_logs[-20:]  # 최근 20개

@app.route('/')
def dashboard():
    """대시보드 메인 페이지"""
    lines = read_latest_log()

    if not lines:
        portfolio_value = 10000.0
        cash = 10000.0
        positions = 0
        recent_logs = [{'time': '00:00:00', 'message': 'Waiting for trading system...', 'type': ''}]
    else:
        portfolio_value, cash, positions, recent_logs = parse_logs(lines)

    return_pct = round(((portfolio_value - 10000) / 10000) * 100, 2)

    return render_template_string(
        HTML_TEMPLATE,
        portfolio_value=f"{portfolio_value:,.2f}",
        cash=f"{cash:,.2f}",
        positions=positions,
        return_pct=return_pct,  # 숫자로 전달
        return_pct_display=f"{return_pct:+.2f}",  # 표시용 문자열
        recent_logs=recent_logs,
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  AI Stock Trader Web Dashboard")
    print("="*60)
    print(f"  Open your browser and go to: http://localhost:5000")
    print("  Press Ctrl+C to stop")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=False)

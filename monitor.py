"""
간단한 모니터링 스크립트
실행 중인 모의투자 상태를 실시간으로 확인
"""

import os
import time
from datetime import datetime
import glob

def clear_screen():
    """화면 지우기"""
    os.system('cls' if os.name == 'nt' else 'clear')

def read_latest_log():
    """최신 로그 파일 읽기"""
    log_files = glob.glob('logs/*.log')
    if not log_files:
        return []

    latest_log = max(log_files, key=os.path.getmtime)

    try:
        with open(latest_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return lines[-50:]  # 최근 50줄만
    except:
        return []

def parse_portfolio_info(lines):
    """로그에서 포트폴리오 정보 추출"""
    portfolio_value = None
    cash = None
    positions = None
    trades = 0

    for line in lines:
        if '포트폴리오 가치:' in line or 'PORTFOLIO - Value:' in line:
            try:
                if 'PORTFOLIO - Value:' in line:
                    parts = line.split('Value: $')[1].split(',')
                    portfolio_value = parts[0].replace(',', '')
                else:
                    portfolio_value = line.split('$')[1].split()[0]
            except:
                pass

        if '현금:' in line or 'Cash:' in line:
            try:
                if 'Cash:' in line:
                    cash = line.split('Cash: $')[1].split(',')[0].replace(',', '')
                else:
                    cash = line.split('$')[1].split()[0]
            except:
                pass

        if '보유 포지션:' in line or 'Positions:' in line:
            try:
                if 'Positions:' in line:
                    positions = line.split('Positions: ')[1].split()[0]
                else:
                    positions = line.split(':')[1].strip().replace('개', '')
            except:
                pass

        if '매수 완료:' in line or '매도 완료:' in line:
            trades += 1

    return portfolio_value, cash, positions, trades

def display_status():
    """상태 표시"""
    while True:
        clear_screen()

        print("=" * 60)
        print("  AI 주식 트레이더 - 실시간 모니터링")
        print("=" * 60)
        print(f"  현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()

        # 로그 읽기
        lines = read_latest_log()

        if not lines:
            print("  [WARNING] Log file not found.")
            print("  Please check if paper trading is running.")
        else:
            # 포트폴리오 정보 추출
            portfolio_value, cash, positions, trades = parse_portfolio_info(lines)

            print("  [Portfolio Status]")
            print("  " + "-" * 56)
            if portfolio_value:
                print(f"  Total Value:  ${portfolio_value}")
            if cash:
                print(f"  Cash:         ${cash}")
            if positions is not None:
                print(f"  Positions:    {positions}")
            print(f"  Trades:       {trades}")
            print()

            print("  [Recent Logs - Last 10 lines]")
            print("  " + "-" * 56)
            for line in lines[-10:]:
                line = line.strip()
                if line:
                    # 타임스탬프와 메시지만 표시
                    if ' - ' in line:
                        parts = line.split(' - ', 2)
                        if len(parts) >= 3:
                            timestamp = parts[0]
                            message = parts[2]
                            print(f"  {timestamp[-8:]} | {message[:50]}")

        print()
        print("=" * 60)
        print("  Press Ctrl+C to exit")
        print("=" * 60)

        # 5초마다 업데이트
        time.sleep(5)

if __name__ == "__main__":
    try:
        display_status()
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")

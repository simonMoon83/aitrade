"""
Paper Trading (모의투자) 실행 스크립트
Usage: python scripts/paper_trade.py [--dashboard]
"""

import sys
import os
import argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import *
from live_trading.paper_trader import PaperTrader
from utils.logger import setup_logger

logger = setup_logger("paper_trade")

def main():
    parser = argparse.ArgumentParser(description='Paper Trading 실행')
    parser.add_argument('--dashboard', action='store_true', help='웹 대시보드 활성화')
    parser.add_argument('--symbols', nargs='+', default=DEFAULT_SYMBOLS, help='거래할 종목 리스트')
    args = parser.parse_args()
    
    logger.info("="*80)
    logger.info("📊 Paper Trading (모의투자) 시작")
    logger.info("="*80)
    logger.info(f"대상 종목: {', '.join(args.symbols)}")
    logger.info(f"대시보드: {'활성화' if args.dashboard else '비활성화'}")
    logger.info("="*80)
    
    trader = PaperTrader(symbols=args.symbols)
    
    if args.dashboard:
        # 대시보드와 함께 실행
        import threading
        from dashboard.web_dashboard import run_dashboard, set_trader_instance
        
        set_trader_instance(trader)
        
        # 트레이더를 별도 스레드에서 시작
        trader_thread = threading.Thread(target=trader.start_trading, daemon=True)
        trader_thread.start()
        
        logger.info("웹 대시보드 시작...")
        logger.info(f"접속 주소: http://localhost:{DASHBOARD_PORT}")
        logger.info(f"로그인: admin / {os.getenv('DASHBOARD_PASSWORD', 'password123')}")
        
        run_dashboard(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=DASHBOARD_DEBUG)
    else:
        # 직접 실행
        logger.info("Paper Trading 시작... (Ctrl+C로 중지)")
        try:
            trader.start_trading()
        except KeyboardInterrupt:
            logger.info("\nPaper Trading 중지됨")

if __name__ == "__main__":
    main()


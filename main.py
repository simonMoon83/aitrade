#!/usr/bin/env python3
"""
AI 주식 트레이더 메인 실행 파일
"""

import argparse
import sys
import os
import logging
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import *
from utils.logger import setup_logger
from utils.scheduler import TradingScheduler

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="AI 주식 트레이더")
    parser.add_argument("--mode", choices=["backtest", "paper", "live"], 
                       required=True, help="실행 모드")
    parser.add_argument("--symbols", type=str, 
                       default=",".join(DEFAULT_SYMBOLS),
                       help="거래할 종목들 (쉼표로 구분)")
    parser.add_argument("--start", type=str, 
                       default=DATA_START_DATE,
                       help="백테스팅 시작 날짜 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, 
                       default=DATA_END_DATE,
                       help="백테스팅 종료 날짜 (YYYY-MM-DD)")
    parser.add_argument("--daemon", action="store_true",
                       help="데몬 모드로 실행 (서버용)")
    parser.add_argument("--dashboard", action="store_true",
                       help="웹 대시보드도 함께 실행")
    
    args = parser.parse_args()
    
    # 로거 설정
    logger = setup_logger("main", LOG_LEVEL)
    logger.info(f"AI 주식 트레이더 시작 - 모드: {args.mode}")
    
    # 종목 리스트 파싱
    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    logger.info(f"거래 종목: {symbols}")
    
    try:
        if args.mode == "backtest":
            from backtesting.backtest_engine import BacktestEngine
            from backtesting.report_generator import ReportGenerator
            
            logger.info("백테스팅 모드 시작")
            engine = BacktestEngine(
                symbols=symbols,
                start_date=args.start,
                end_date=args.end,
                initial_capital=INITIAL_CAPITAL
            )
            
            results = engine.run_backtest()
            
            # 보고서 생성
            report_gen = ReportGenerator()
            report_path = report_gen.generate_report(results, symbols, args.start, args.end)
            logger.info(f"백테스팅 보고서 생성: {report_path}")
            
        elif args.mode == "paper":
            from live_trading.paper_trader import PaperTrader
            
            logger.info("모의투자 모드 시작")
            trader = PaperTrader(symbols=symbols)
            
            if args.dashboard:
                # 대시보드와 함께 실행 - 트레이더를 스레드로 실행
                import threading
                from dashboard.web_dashboard import run_dashboard, set_trader_instance
                
                set_trader_instance(trader)
                
                # 트레이더를 별도 스레드에서 시작
                trader_thread = threading.Thread(target=trader.start_trading, daemon=True)
                trader_thread.start()
                
                logger.info("웹 대시보드 시작")
                run_dashboard(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=DASHBOARD_DEBUG)
                
            elif args.daemon:
                # 스케줄러로 실행
                scheduler = TradingScheduler(trader)
                scheduler.start()
            else:
                # 직접 실행
                trader.start_trading()
                
        elif args.mode == "live":
            from live_trading.live_trader import LiveTrader
            
            logger.info("실전투자 모드 시작")
            trader = LiveTrader(symbols=symbols)
            
            if args.dashboard:
                # 대시보드와 함께 실행 - 트레이더를 스레드로 실행
                import threading
                from dashboard.web_dashboard import run_dashboard, set_trader_instance
                
                set_trader_instance(trader)
                
                # 트레이더를 별도 스레드에서 시작
                trader_thread = threading.Thread(target=trader.start_trading, daemon=True)
                trader_thread.start()
                
                logger.info("웹 대시보드 시작")
                run_dashboard(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=DASHBOARD_DEBUG)
                
            elif args.daemon:
                # 스케줄러로 실행
                scheduler = TradingScheduler(trader)
                scheduler.start()
            else:
                # 직접 실행
                trader.start_trading()
            
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"오류 발생: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()


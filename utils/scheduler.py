"""
스케줄링 유틸리티
미국 장 시간에 맞춰 거래를 실행합니다.
"""

import schedule
import time
import threading
from datetime import datetime, time as dt_time, date
from typing import Optional, Callable, Dict

from config import MARKET_OPEN_HOUR, MARKET_CLOSE_HOUR, BACKTEST_UPDATE_HOUR, ENABLE_DAILY_REPORT, DAILY_REPORT_HOUR
from utils.logger import setup_logger
from utils.market_calendar import market_calendar
from utils.market_analyzer import market_analyzer
from datetime import timedelta
import pandas as pd

logger = setup_logger("scheduler")

# 시스템 모니터 import
try:
    from utils.system_monitor import system_monitor
    SYSTEM_MONITOR_ENABLED = True
except ImportError:
    SYSTEM_MONITOR_ENABLED = False
    logger.warning("시스템 모니터를 불러올 수 없습니다 - 헬스체크 기능 비활성화")

class TradingScheduler:
    """거래 스케줄러 클래스"""
    
    def __init__(self, trader_instance):
        """
        초기화

        Args:
            trader_instance: 거래자 인스턴스 (PaperTrader 또는 LiveTrader)
        """
        self.trader = trader_instance
        self.is_running = False
        self.scheduler_thread = None
        self.market_state = {
            'is_open': False,
            'session_date': None
        }

        # 일일 레포트 생성기 초기화
        self.report_generator = None
        if ENABLE_DAILY_REPORT:
            try:
                from utils.daily_report_generator import report_generator
                self.report_generator = report_generator
                logger.info("AI 일일 레포트 생성기 활성화")
            except ImportError as e:
                logger.warning(f"일일 레포트 생성기 import 실패: {str(e)}")
        
    def start(self):
        """스케줄러 시작"""
        logger.info("거래 스케줄러 시작")
        self.is_running = True
        
        # 스케줄 설정
        self._setup_schedules()
        
        # 스케줄러 스레드 시작
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        # 거래 시작
        self.trader.start_trading()
    
    def stop(self):
        """스케줄러 중지"""
        logger.info("거래 스케줄러 중지")
        self.is_running = False
        
        # 거래 중지
        if hasattr(self.trader, 'stop_trading'):
            self.trader.stop_trading()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
    
    def _setup_schedules(self):
        """스케줄 설정"""
        # 시장 상태 폴링 (DST/휴장 대응)
        schedule.every().minute.do(self._check_market_state)
        
        # 백테스팅 업데이트 (새벽 2시)
        schedule.every().day.at(f"{BACKTEST_UPDATE_HOUR:02d}:00").do(self._update_backtest)
        
        # 일일 요약 (장 마감 후)
        schedule.every().day.at("07:00").do(self._daily_summary)

        # AI 일일 레포트 생성 (장 마감 후)
        if ENABLE_DAILY_REPORT and self.report_generator:
            schedule.every().day.at(f"{DAILY_REPORT_HOUR:02d}:00").do(self._generate_ai_report)
            logger.info(f"AI 일일 레포트 생성 스케줄 등록 ({DAILY_REPORT_HOUR:02d}:00)")

        # 주간 요약 (매주 월요일)
        schedule.every().monday.at("09:00").do(self._weekly_summary)
        
        # 시스템 헬스체크 (매 시간)
        if SYSTEM_MONITOR_ENABLED:
            schedule.every().hour.do(self._record_heartbeat)
            logger.info("시스템 헬스체크 스케줄 등록 (매 시간)")
    
    def _run_scheduler(self):
        """스케줄러 실행 루프"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 체크
            except Exception as e:
                logger.error(f"스케줄러 오류: {str(e)}")
                time.sleep(60)
    
    def _check_market_state(self):
        """시장 개장/폐장 상태 감시"""
        try:
            state = market_calendar.get_market_state()
        except Exception as e:
            logger.error(f"시장 상태 확인 실패: {str(e)}")
            return

        currently_open = state.get('is_open', False)
        previous_open = self.market_state.get('is_open', False)
        session_changed = self.market_state.get('session_date') != state.get('session_date')

        if currently_open and (not previous_open or session_changed):
            self.market_state = {
                'is_open': True,
                'session_date': state.get('session_date')
            }
            self._on_market_open(state)
        elif not currently_open and previous_open:
            self.market_state = {
                'is_open': False,
                'session_date': state.get('previous_session_date')
            }
            self._on_market_close(state)
    
    def _on_market_open(self, state: Optional[Dict] = None):
        """장 시작 시 실행"""
        if state and state.get('market_open'):
            logger.info(f"미국 장 시작 ({state['market_open'].strftime('%Y-%m-%d %H:%M')})")
        else:
            logger.info("미국 장 시작")
        
        try:
            # 포트폴리오 상태 확인
            if hasattr(self.trader, 'get_current_status'):
                status = self.trader.get_current_status()
                logger.info(f"장 시작 시 포트폴리오 가치: ${status.get('portfolio_value', 0):,.2f}")
            
            # 일일 거래 카운터 리셋
            if hasattr(self.trader, 'daily_trade_count'):
                self.trader.daily_trade_count = 0
            
        except Exception as e:
            logger.error(f"장 시작 처리 오류: {str(e)}")
    
    def _on_market_close(self, state: Optional[Dict] = None):
        """장 마감 시 실행"""
        if state and state.get('previous_session_date'):
            logger.info(f"미국 장 마감 ({state['previous_session_date']})")
        else:
            logger.info("미국 장 마감")
        
        try:
            # 최종 포트폴리오 상태 로그
            if hasattr(self.trader, 'get_current_status'):
                status = self.trader.get_current_status()
                logger.info(f"장 마감 시 포트폴리오 가치: ${status.get('portfolio_value', 0):,.2f}")
                logger.info(f"일일 거래 횟수: {status.get('daily_trades', 0)}")
            
            # 일일 성과 요약 생성
            summary_date = state.get('previous_session_date') if state else None
            self._generate_daily_summary(summary_date)
            
        except Exception as e:
            logger.error(f"장 마감 처리 오류: {str(e)}")
    
    def _update_backtest(self):
        """백테스팅 업데이트"""
        logger.info("백테스팅 업데이트 시작")
        
        try:
            # 최신 데이터로 백테스팅 재실행
            # 이 부분은 실제 구현에 따라 달라질 수 있습니다
            pass
            
        except Exception as e:
            logger.error(f"백테스팅 업데이트 오류: {str(e)}")
    
    def _daily_summary(self):
        """일일 요약"""
        logger.info("일일 요약 생성")
        
        try:
            trading_day = market_calendar.get_last_completed_trading_day()
            if not trading_day:
                logger.warning("일일 요약 생성 불가: 최근 거래일 미확인")
                return

            if hasattr(self.trader, 'get_current_status'):
                status = self.trader.get_current_status()
                
                summary = {
                    'date': trading_day.strftime('%Y-%m-%d'),
                    'portfolio_value': status.get('portfolio_value', 0),
                    'total_return': status.get('total_return', 0),
                    'daily_trades': status.get('daily_trades', 0),
                    'positions': len(status.get('positions', {}))
                }
                
                logger.info(f"일일 요약: {summary}")

        except Exception as e:
            logger.error(f"일일 요약 생성 오류: {str(e)}")

    def _generate_ai_report(self):
        """AI 일일 레포트 생성"""
        logger.info("AI 일일 레포트 생성 시작")

        if not self.report_generator:
            logger.warning("레포트 생성기가 초기화되지 않았습니다")
            return

        try:
            # 거래자 인스턴스에서 데이터 수집
            if not hasattr(self.trader, 'get_current_status'):
                logger.warning("거래자 인스턴스에 get_current_status 메서드가 없습니다")
                return

            status = self.trader.get_current_status()

            # 포트폴리오 데이터
            portfolio_data = {
                'portfolio_value': status.get('portfolio_value', 0),
                'cash': status.get('cash', 0),
                'positions': status.get('positions', {}),
                'total_return': status.get('total_return', 0),
                'daily_return': status.get('daily_return', 0)
            }

            # 거래 내역 수집
            trades = []
            if hasattr(self.trader, 'get_trade_history'):
                trade_history = self.trader.get_trade_history()

                if not trade_history.empty:
                    # 오늘 거래만 필터링
                    today = datetime.now().date()
                    if 'timestamp' in trade_history.columns:
                        today_trades = trade_history[
                            pd.to_datetime(trade_history['timestamp']).dt.date == today
                        ]

                        # Dict 리스트로 변환
                        trades = today_trades.to_dict('records')

            # 신호 내역 수집 (현재는 임시로 빈 리스트)
            signals = []
            # TODO: 신호 히스토리 추적 기능 추가 필요

            # 시장 데이터
            try:
                market_data = market_analyzer.get_market_conditions()
            except Exception as e:
                logger.warning(f"시장 데이터 수집 실패(레포트에는 누락됨): {str(e)}")
                market_data = None

            # AI 레포트 생성
            result = self.report_generator.generate_daily_report(
                portfolio_data=portfolio_data,
                trades=trades,
                signals=signals,
                market_data=market_data,
                report_date=datetime.now().date()
            )

            if result['success']:
                logger.info(f"AI 일일 레포트 생성 완료: {result['report_path']}")
            else:
                logger.error(f"AI 일일 레포트 생성 실패: {result.get('error', '알 수 없는 오류')}")

        except Exception as e:
            logger.error(f"AI 일일 레포트 생성 오류: {str(e)}")
    
    def _weekly_summary(self):
        """주간 요약"""
        logger.info("주간 요약 생성")
        
        try:
            if hasattr(self.trader, 'get_trade_history'):
                trade_history = self.trader.get_trade_history()
                
                if not trade_history.empty:
                    # 최근 7일 거래 필터링
                    week_ago = datetime.now() - timedelta(days=7)
                    recent_trades = trade_history[
                        pd.to_datetime(trade_history['timestamp']) >= week_ago
                    ]
                    
                    weekly_summary = {
                        'week': datetime.now().strftime('%Y-%W'),
                        'total_trades': len(recent_trades),
                        'total_pnl': recent_trades['pnl'].sum(),
                        'winning_trades': len(recent_trades[recent_trades['pnl'] > 0]),
                        'losing_trades': len(recent_trades[recent_trades['pnl'] < 0])
                    }
                    
                    logger.info(f"주간 요약: {weekly_summary}")
                
        except Exception as e:
            logger.error(f"주간 요약 생성 오류: {str(e)}")
    
    def _record_heartbeat(self):
        """시스템 헬스체크 기록"""
        try:
            if SYSTEM_MONITOR_ENABLED:
                system_monitor.record_heartbeat()
        except Exception as e:
            logger.error(f"헬스체크 기록 오류: {str(e)}")
    
    def _generate_daily_summary(self, session_date: Optional[date] = None):
        """일일 성과 요약 생성"""
        try:
            if hasattr(self.trader, 'get_current_status'):
                status = self.trader.get_current_status()
                summary_day = session_date or market_calendar.get_last_completed_trading_day()
                if summary_day is None:
                    summary_day = datetime.now().date()
                
                # 요약 정보
                summary = {
                    'date': summary_day.strftime('%Y-%m-%d'),
                    'portfolio_value': status.get('portfolio_value', 0),
                    'cash': status.get('cash', 0),
                    'total_return': status.get('total_return', 0),
                    'daily_trades': status.get('daily_trades', 0),
                    'positions_count': len(status.get('positions', {})),
                    'is_running': status.get('is_running', False)
                }
                
                # 포지션별 손익
                positions_summary = []
                for symbol, pos_info in status.get('positions', {}).items():
                    positions_summary.append({
                        'symbol': symbol,
                        'quantity': pos_info['quantity'],
                        'avg_price': pos_info['avg_price'],
                        'current_price': pos_info['current_price'],
                        'unrealized_pnl': pos_info['unrealized_pnl']
                    })
                
                summary['positions'] = positions_summary
                
                logger.info("=== 일일 성과 요약 ===")
                logger.info(f"날짜: {summary['date']}")
                logger.info(f"포트폴리오 가치: ${summary['portfolio_value']:,.2f}")
                logger.info(f"총 수익률: {summary['total_return']:.2%}")
                logger.info(f"일일 거래: {summary['daily_trades']}회")
                logger.info(f"보유 포지션: {summary['positions_count']}개")
                
                for pos in positions_summary:
                    logger.info(f"  {pos['symbol']}: {pos['quantity']}주 "
                              f"(손익: ${pos['unrealized_pnl']:.2f})")
                
        except Exception as e:
            logger.error(f"일일 요약 생성 오류: {str(e)}")

def is_market_hours() -> bool:
    """현재가 미국 장 시간인지 확인"""
    state = market_calendar.get_market_state()
    return state.get('is_open', False)

def is_weekend() -> bool:
    """
    현재가 주말인지 확인
    
    Returns:
        bool: 주말 여부
    """
    return datetime.now().weekday() >= 5  # 토요일(5), 일요일(6)

def get_next_market_open() -> datetime:
    """다음 장 시작 시간 계산"""
    state = market_calendar.get_market_state()
    if state.get('is_open') and state.get('market_open'):
        return state['market_open']
    
    next_day = market_calendar.get_next_trading_day(include_today=True)
    session = market_calendar.get_session_times(next_day) if next_day else None
    if session:
        return session['market_open_local']
    return datetime.now()

def get_next_market_close() -> datetime:
    """다음 장 마감 시간 계산"""
    state = market_calendar.get_market_state()
    if state.get('is_open') and state.get('market_close'):
        return state['market_close']
    
    next_day = market_calendar.get_next_trading_day(include_today=True)
    session = market_calendar.get_session_times(next_day) if next_day else None
    if session:
        return session['market_close_local']
    return datetime.now()


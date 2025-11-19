"""
모의투자 트레이더 (Alpaca Paper Trading)
Alpaca Paper Trading API를 사용하여 가상 자금으로 실제 시장 환경을 시뮬레이션합니다.

📊 Paper Trading 전용 설정 (전문가 권장)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 신뢰도 임계값: 0.35 (실전: 0.7~0.8)
✅ 신호 임계값: BUY 3.0, SELL 2.5 (실전: 4.5/4.0)
✅ RSI: 30/70 (실전: 25/75)
✅ 거래량 조건: 1.3x (실전: 1.5x)

📌 목표:
- 일일 2~5건 거래 예상
- 신호 검증 및 데이터 축적
- 전략 성과 분석

⚠️ 주의:
- 실전 전환 시 더 엄격한 기준 적용 필수
- 최소 1~2개월 Paper Trading 데이터 축적 권장
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import pandas as pd
import numpy as np
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, date, time, timedelta
import time as time_module
import threading
from dataclasses import dataclass

try:
    import alpaca_trade_api as tradeapi
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

from config import *
from utils.logger import setup_logger, log_trade, log_signal, log_portfolio, log_error
from utils.data_collector import data_collector
from utils.feature_engineering import feature_engineer
from strategies.improved.buy_low_sell_high import get_trading_signal
from backtesting.portfolio_manager import PortfolioManager, OrderType
from utils.position_manager import position_manager
from utils.market_analyzer import market_analyzer
from live_trading.risk_manager import risk_manager
from utils.settings_manager import settings_manager

logger = setup_logger("paper_trader")

class PaperTrader:
    """Alpaca Paper Trading 트레이더 클래스"""
    
    def __init__(self, symbols: List[str]):
        """
        초기화
        
        Args:
            symbols (List[str]): 초기 종목 리스트 (설정 파일이 있으면 무시될 수 있음)
        """
        self.settings_manager = settings_manager
        self.symbols = symbols
        self.short_term_symbols = []  # 시스템이 선정한 단기 종목
        self.is_running = False
        self.trading_thread = None
        
        # Alpaca API 초기화
        if not ALPACA_AVAILABLE:
            logger.error("Alpaca API가 설치되지 않았습니다. pip install alpaca-trade-api")
            raise ImportError("Alpaca API가 필요합니다. pip install alpaca-trade-api")
        
        if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
            raise ValueError("Alpaca API 키가 설정되지 않았습니다")
        
        # Paper Trading API URL 강제 설정
        self.api = tradeapi.REST(
            ALPACA_API_KEY,
            ALPACA_SECRET_KEY,
            "https://paper-api.alpaca.markets",  # Paper Trading 강제
            api_version='v2'
        )
        
        # 포트폴리오 관리 (Alpaca 계정과 동기화)
        self.portfolio_manager = PortfolioManager()
        
        # 실시간 데이터 저장
        self.current_data: Dict[str, pd.DataFrame] = {}
        self.current_prices: Dict[str, float] = {}
        
        # 거래 제한
        self.daily_trade_count = 0
        self.last_trade_date = None
        self.daily_loss_limit = INITIAL_CAPITAL * MAX_DAILY_LOSS
        
        # 안전 장치
        self.emergency_stop = False
        self._market_filter = None
        self._market_filter_updated_at = None
        self._market_filter_ttl = timedelta(minutes=5)
        
        logger.info("=" * 80)
        logger.info("📊 Paper Trading 트레이더 초기화 완료")
        logger.info("=" * 80)
        logger.info(f"거래 종목: {', '.join(symbols)}")
        logger.info("")
        logger.info("📌 Paper Trading 전용 설정 (전문가 권장)")
        logger.info("  - 신뢰도 임계값: 0.35 (더 많은 거래 기회)")
        logger.info("  - 신호 임계값: BUY 3.0, SELL 2.5")
        logger.info("  - RSI: 30/70 (완화)")
        logger.info("  - 거래량 조건: 1.3x (완화)")
        logger.info("")
        logger.info("🎯 목표: 일일 2~5건 거래 예상")
        logger.info("⚠️  주의: 실전 전환 시 더 엄격한 기준 적용 필수")
        logger.info("=" * 80)
        
        # 계정 정보 확인
        self._check_account_status()
    
    def start_trading(self):
        """거래 시작"""
        logger.info("Paper Trading 거래 시작")

        if self.emergency_stop:
            logger.error("긴급 정지 상태입니다. 거래를 시작할 수 없습니다")
            return

        self.is_running = True

        # 종목 리스트 업데이트 (장기 + 단기)
        self._update_target_symbols()

        # 초기 데이터 로드
        self._load_initial_data()

        # 포트폴리오 동기화
        self._sync_portfolio()

        # 초기 상태 파일 생성 (즉시 생성)
        try:
            portfolio_value = self.portfolio_manager.get_portfolio_value(self.current_prices)
            cash = self.portfolio_manager.cash
            positions = self.portfolio_manager.get_all_positions()
            self._save_status_file(portfolio_value, cash, positions)
            logger.info("초기 상태 파일 생성 완료")
        except Exception as e:
            logger.error(f"초기 상태 파일 생성 실패: {str(e)}")

        # 거래 스레드 시작
        self.trading_thread = threading.Thread(target=self._trading_loop)
        self.trading_thread.daemon = True
        self.trading_thread.start()

        # 메인 스레드에서 포트폴리오 모니터링
        self._monitoring_loop()
    
    def stop_trading(self):
        """거래 중지"""
        logger.info("Paper Trading 거래 중지")
        self.is_running = False
        
        if self.trading_thread:
            self.trading_thread.join(timeout=5)
        
        # 최종 포트폴리오 상태 로그
        self._log_final_status()
    
    def emergency_stop_trading(self):
        """긴급 거래 중지"""
        logger.warning("긴급 거래 중지 실행")
        self.emergency_stop = True
        self.is_running = False
    
    def _check_account_status(self):
        """계정 상태 확인"""
        try:
            account = self.api.get_account()
            logger.info(f"Paper Trading 계정 상태: {account.status}")
            logger.info(f"Paper Trading 계정 자산: ${float(account.portfolio_value):,.2f}")
            logger.info(f"현금: ${float(account.cash):,.2f}")
            
            # 거래 가능 여부 확인
            if account.trading_blocked:
                logger.error("계정이 거래 차단 상태입니다")
                self.emergency_stop = True
                return
            
            if account.account_blocked:
                logger.error("계정이 차단 상태입니다")
                self.emergency_stop = True
                return
            
        except Exception as e:
            log_error(logger, e, "계정 상태 확인")
            self.emergency_stop = True
    
    def _load_initial_data(self):
        """초기 데이터 로드"""
        logger.info("초기 데이터 로드 중...")
        
        # 모델 로드 시도
        try:
            from strategies.improved.buy_low_sell_high import improved_strategy
            improved_strategy.load_model()
            logger.info("개선된 전략 모델 로드 완료")
        except Exception as e:
            logger.warning(f"모델 로드 실패 (규칙 기반 전략만 사용): {str(e)}")
        
        for symbol in self.symbols:
            try:
                # 최근 60일 데이터 수집 (증분 업데이트 방식)
                data = data_collector.get_latest_data_incremental(symbol, target_days=60)
                if not data.empty:
                    # 기술적 지표 추가
                    data_with_indicators = feature_engineer.add_technical_indicators(data, symbol=symbol)
                    
                    # 전략 데이터 준비 (개선된 전략용)
                    try:
                        from strategies.improved.buy_low_sell_high import improved_strategy
                        data_with_indicators = improved_strategy.prepare_data(data_with_indicators)
                    except Exception as e:
                        logger.warning(f"전략 데이터 준비 실패 {symbol}: {str(e)}")
                    
                    self.current_data[symbol] = data_with_indicators
                    
                    # 현재 가격 저장
                    if not data_with_indicators.empty:
                        if 'Date' in data_with_indicators.columns:
                            self.current_prices[symbol] = data_with_indicators.iloc[-1]['CLOSE']
                        elif 'CLOSE' in data_with_indicators.columns:
                            self.current_prices[symbol] = data_with_indicators.iloc[-1]['CLOSE']
                    
                    logger.info(f"데이터 로드 완료: {symbol}")
                else:
                    logger.warning(f"데이터 로드 실패: {symbol}")
                    
            except Exception as e:
                log_error(logger, e, f"데이터 로드 {symbol}")
    
    def _sync_portfolio(self):
        """포트폴리오 동기화"""
        try:
            # Alpaca Paper Trading 계정에서 포지션 정보 가져오기
            positions = self.api.list_positions()
            
            # 포트폴리오 매니저 초기화
            self.portfolio_manager.reset()
            
            # 현금 정보
            account = self.api.get_account()
            self.portfolio_manager.cash = float(account.cash)
            
            # 포지션 정보 동기화
            for pos in positions:
                symbol = pos.symbol
                quantity = int(pos.qty)
                avg_price = float(pos.avg_entry_price)
                current_price = float(pos.current_price)
                
                # 포지션 생성
                from backtesting.portfolio_manager import Position
                position = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=avg_price,
                    current_price=current_price,
                    entry_date=date.today()  # 실제 진입일은 알 수 없음
                )
                
                self.portfolio_manager.positions[symbol] = position
                self.current_prices[symbol] = current_price
                
                logger.info(f"포지션 동기화: {symbol} - {quantity}주 @ ${avg_price:.2f}")
            
            logger.info("포트폴리오 동기화 완료")
            
        except Exception as e:
            log_error(logger, e, "포트폴리오 동기화")
    
    def _trading_loop(self):
        """거래 루프 (신호 생성 및 거래 실행)"""
        logger.info("🔄 거래 루프 시작")
        loop_count = 0

        while self.is_running and not self.emergency_stop:
            try:
                loop_count += 1
                logger.debug(f"📊 거래 루프 실행 #{loop_count}")

                # 미국 장 시간 확인
                if not self._is_market_open():
                    logger.debug("⏰ 장 마감 시간 - 대기 중 (5분)")
                    time_module.sleep(300)  # 5분 대기
                    continue

                market_filter = self._get_market_filter()
                if not risk_manager.allows_trading():
                    reasons = market_filter.get('reasons', [])
                    logger.warning(f"🛑 시장 필터로 거래 대기: {', '.join(reasons) if reasons else '조건 미충족'} (10분 대기)")
                    time_module.sleep(600)
                    continue

                logger.info(f"✅ 장 시간 - 신호 생성 시작 (루프 #{loop_count})")

                # 일일 거래 제한 확인
                if not self._check_daily_limits():
                    logger.warning("⚠️ 일일 거래 제한 도달 - 대기 중 (1시간)")
                    time_module.sleep(3600)  # 1시간 대기
                    continue

                # 일일 손실 한도 확인
                if not self._check_daily_loss_limit():
                    logger.warning("🛑 일일 손실 한도 도달. 거래 중지")
                    self.emergency_stop_trading()
                    break

                # 각 종목별 신호 확인 및 손절/익절 확인
                logger.info(f"🔍 {len(self.symbols)}개 종목 신호 확인 시작")
                for symbol in self.symbols:
                    if not self.is_running or self.emergency_stop:
                        break

                    # 손절/익절 확인
                    self._check_stop_loss_take_profit(symbol)

                    # 거래 신호 처리
                    self._process_symbol_signal(symbol, market_filter)

                logger.info(f"✅ 신호 확인 완료 - 다음 확인까지 60초 대기")
                # 1분 대기
                time_module.sleep(60)

            except Exception as e:
                log_error(logger, e, "거래 루프")
                time_module.sleep(60)
    
    def _monitoring_loop(self):
        """모니터링 루프"""
        logger.info("모니터링 루프 시작")

        while self.is_running and not self.emergency_stop:
            try:
                # 미국 장 시간 확인
                if self._is_market_open():
                    # 장 시간: 포트폴리오 상태 로그 및 동기화
                    self._log_portfolio_status()
                    self._sync_portfolio()
                    
                    # 종목 리스트 업데이트 (주기적)
                    self._update_target_symbols()

                    # 5분 대기
                    time_module.sleep(300)
                else:
                    # 장 마감 시간: 상태 파일만 업데이트 (로그 없이)
                    logger.debug("장 마감 시간 - 상태 파일만 업데이트")
                    try:
                        portfolio_value = self.portfolio_manager.get_portfolio_value(self.current_prices)
                        cash = self.portfolio_manager.cash
                        positions = self.portfolio_manager.get_all_positions()
                        self._save_status_file(portfolio_value, cash, positions)
                    except Exception as e:
                        logger.debug(f"장 마감 시간 상태 파일 업데이트 실패: {str(e)}")

                    # 5분 대기 (장 마감 시간에도 정기적으로 업데이트)
                    time_module.sleep(300)

            except Exception as e:
                log_error(logger, e, "모니터링 루프")
                time_module.sleep(60)
    
    def _is_market_open(self) -> bool:
        """미국 장 시간 확인 (Alpaca API 사용)"""
        try:
            clock = self.api.get_clock()
            return clock.is_open
        except Exception as e:
            log_error(logger, e, "장 시간 확인")
            # API 오류 시 fallback: pytz 사용
            try:
                import pytz
                from datetime import datetime as dt
                
                now_utc = dt.now(pytz.UTC)
                eastern = pytz.timezone('US/Eastern')
                now_et = now_utc.astimezone(eastern)
                
                if now_et.weekday() >= 5:
                    return False
                
                market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
                market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
                
                return market_open <= now_et <= market_close
            except:
                return False
    
    def _check_daily_limits(self) -> bool:
        """일일 거래 제한 확인"""
        today = date.today()
        
        # 날짜가 바뀌면 카운터 리셋
        if self.last_trade_date != today:
            self.daily_trade_count = 0
            self.last_trade_date = today
        
        # 일일 최대 거래 횟수 확인
        max_daily_trades = 20  # 설정 가능
        if self.daily_trade_count >= max_daily_trades:
            return False
        
        return True
    
    def _check_daily_loss_limit(self) -> bool:
        """일일 손실 한도 확인"""
        try:
            # 현재 포트폴리오 가치 계산
            portfolio_value = self.portfolio_manager.get_portfolio_value(self.current_prices)
            daily_loss = INITIAL_CAPITAL - portfolio_value
            
            if daily_loss > self.daily_loss_limit:
                logger.error(f"일일 손실 한도 초과: ${daily_loss:.2f} > ${self.daily_loss_limit:.2f}")
                return False
            
            return True
            
        except Exception as e:
            log_error(logger, e, "일일 손실 한도 확인")
            return True  # 오류 시 계속 진행
    
    def _check_stop_loss_take_profit(self, symbol: str):
        """손절/익절 확인"""
        try:
            # 포지션 확인
            position = self.portfolio_manager.get_position(symbol)
            if not position:
                return
            
            current_price = self.current_prices.get(symbol, 0)
            if current_price <= 0:
                return
            
            # 포지션 매니저에서 손절/익절 가격 확인
            if symbol in position_manager.positions:
                pos_info = position_manager.positions[symbol]
                entry_price = pos_info['entry_price']
                
                # 손절/익절 확인
                price_change = (current_price - entry_price) / entry_price
                
                if price_change <= -STOP_LOSS_PCT or price_change >= TAKE_PROFIT_PCT:
                    # 청산
                    reason = "Stop Loss" if price_change <= -STOP_LOSS_PCT else "Take Profit"
                    
                    # Alpaca API로 매도 실행
                    try:
                        order = self.api.submit_order(
                            symbol=symbol,
                            qty=position.quantity,
                            side='sell',
                            type='market',
                            time_in_force='day'
                        )
                        
                        self.daily_trade_count += 1
                        position_manager.close_position(symbol, current_price, reason)
                        
                        pnl = (current_price - entry_price) * position.quantity
                        pnl_pct = price_change
                        
                        logger.info(f"{symbol} 자동 청산 ({reason}): {position.quantity}주 @ ${current_price:.2f} "
                                  f"(손익: ${pnl:.2f}, {pnl_pct:.2%})")
                    except Exception as e:
                        log_error(logger, e, f"자동 청산 주문 {symbol}")
        
        except Exception as e:
            logger.debug(f"손절/익절 확인 오류 {symbol}: {str(e)}")
    
    def _get_market_filter(self) -> Dict:
        """시장 필터 정보 캐시"""
        now = datetime.now()
        if (
            self._market_filter is not None and
            self._market_filter_updated_at and
            now - self._market_filter_updated_at < self._market_filter_ttl
        ):
            risk_manager.apply_market_filter(self._market_filter)
            return self._market_filter

        try:
            self._market_filter = market_analyzer.get_market_filter_signal()
            self._market_filter_updated_at = now
        except Exception as e:
            logger.warning(f"시장 필터 조회 실패 - 기본값 사용: {str(e)}")
            self._market_filter = {
                'allow_trading': True,
                'position_size_multiplier': 1.0,
                'reasons': [f"필터 오류: {e}"]
            }
            self._market_filter_updated_at = now

        risk_manager.apply_market_filter(self._market_filter)
        return self._market_filter
    
    def _process_symbol_signal(self, symbol: str, market_filter: Optional[Dict] = None):
        """종목별 신호 처리 (상세 로깅 강화)"""
        try:
            logger.debug(f"🔍 [{symbol}] 신호 생성 시작")

            # 시장 필터 확인 (개선된 전략)
            market_filter = market_filter or self._get_market_filter()
            if not market_filter['allow_trading']:
                reasons = market_filter.get('reasons', [])
                logger.info(f"⛔ [{symbol}] 시장 필터로 인해 거래 불가: {', '.join(reasons)}")
                return

            # 최신 데이터 업데이트
            self._update_symbol_data(symbol)

            if symbol not in self.current_data or self.current_data[symbol].empty:
                logger.warning(f"⚠️ [{symbol}] 데이터가 비어있어 신호 생성 불가")
                return

            # 포지션 제약 확인 (개선된 전략)
            current_date = datetime.now()
            can_trade, reason = position_manager.can_open_position(symbol)

            # 거래 신호 생성 (개선된 전략)
            current_capital = self.portfolio_manager.get_portfolio_value(self.current_prices)
            data_for_signal = self.current_data[symbol].reset_index() if 'Date' in self.current_data[symbol].index.names else self.current_data[symbol]

            logger.debug(f"📈 [{symbol}] 신호 생성 호출 (자본금: ${current_capital:,.2f})")

            signal_info = get_trading_signal(data_for_signal, symbol, current_capital, market_filter=market_filter)

            # HOLD 신호 상세 로깅
            if signal_info['signal'] == 'HOLD':
                logger.info(f"⏸️ [{symbol}] HOLD 신호")
                logger.info(f"  - 신뢰도: {signal_info.get('confidence', 0):.2%}")
                logger.info(f"  - 현재가: ${signal_info.get('price', 0):.2f}")

                # HOLD 이유 상세 로깅
                if 'reasons' in signal_info and signal_info['reasons']:
                    logger.info(f"  - HOLD 이유: {', '.join(signal_info['reasons'])}")
                else:
                    logger.info(f"  - 신호 점수가 임계값 미달 (BUY < 3.0, SELL < 2.5)")

                return

            # 포지션 제약 확인 (매수 시)
            if signal_info['signal'] == 'BUY' and not can_trade:
                logger.warning(f"⛔ [{symbol}] 포지션 제약으로 인해 거래 불가: {reason}")
                return

            # 신호 로그 (Paper Trading: 상세 정보)
            log_signal(logger, symbol, signal_info['signal'],
                      signal_info.get('confidence', 0.0), signal_info)

            # 상세 신호 정보 로깅
            logger.info(f"🎯 [{symbol}] {signal_info['signal']} 신호 감지!")
            logger.info(f"  신호: {signal_info['signal']}")
            logger.info(f"  신뢰도: {signal_info.get('confidence', 0):.2%}")
            logger.info(f"  가격: ${signal_info.get('price', 0):.2f}")
            logger.info(f"  포지션 크기: {signal_info.get('position_size', 0)}주")
            
            # 컨텍스트 정보 로깅 (뉴스, 섹터, 거시경제)
            if 'context' in signal_info:
                context = signal_info['context']
                
                # 뉴스 감성
                if 'news' in context:
                    news = context['news']
                    logger.info(f"  📰 뉴스 감성: {news.get('trend', 'NEUTRAL')} "
                               f"(점수: {news.get('score', 0):+.2f}, 뉴스: {news.get('news_count', 0)}개)")
                
                # 섹터 정보
                if 'sector' in context:
                    sector = context['sector']
                    if sector.get('sector', 'Unknown') != 'Unknown':
                        logger.info(f"  🏢 섹터: {sector.get('sector')} "
                                   f"(순위: {sector.get('rank')}/11, "
                                   f"상대강도: {sector.get('relative_strength', 0):+.1f}%)")
                
                # 거시경제 환경
                if 'macro' in context:
                    macro = context['macro']
                    logger.info(f"  🌍 거시경제: {macro.get('environment', 'NEUTRAL')} "
                               f"(점수: {macro.get('score', 0):+d})")
            
            if 'reasons' in signal_info and signal_info['reasons']:
                logger.info(f"  근거:")
                for reason in signal_info['reasons']:
                    logger.info(f"    ✓ {reason}")

            # 거래 실행
            self._execute_signal(signal_info)

        except Exception as e:
            log_error(logger, e, f"신호 처리 {symbol}")
    
    def _update_symbol_data(self, symbol: str):
        """종목 데이터 업데이트 (상세 로깅)"""
        try:
            logger.debug(f"📥 [{symbol}] 최신 데이터 수집 시작")

            # 최신 데이터 가져오기
            latest_data = data_collector.get_latest_data(symbol, days=1)

            if latest_data.empty:
                logger.warning(f"⚠️ [{symbol}] 최신 데이터가 비어있음 - 기존 데이터 유지")
                return

            if not latest_data.empty:
                # 기존 데이터에 추가
                if symbol in self.current_data:
                    # Date 컬럼 확인
                    date_col = 'Date' if 'Date' in self.current_data[symbol].columns else self.current_data[symbol].index.name
                    
                    if date_col == 'Date':
                        existing_dates = set(self.current_data[symbol]['Date'])
                        new_data = latest_data[~latest_data['Date'].isin(existing_dates)]
                    else:
                        # 인덱스가 Date인 경우
                        existing_dates = set(self.current_data[symbol].index)
                        new_data = latest_data[~latest_data.index.isin(existing_dates)]
                    
                    if not new_data.empty:
                        # 데이터 합치기
                        if date_col == 'Date':
                            combined_data = pd.concat([self.current_data[symbol], new_data], ignore_index=True)
                        else:
                            combined_data = pd.concat([self.current_data[symbol], new_data])
                        
                        # 기술적 지표 추가
                        new_data_with_indicators = feature_engineer.add_technical_indicators(combined_data)
                        
                        # 전략 데이터 준비 (개선된 전략용)
                        try:
                            from strategies.improved.buy_low_sell_high import improved_strategy
                            new_data_with_indicators = improved_strategy.prepare_data(new_data_with_indicators)
                        except Exception as e:
                            logger.debug(f"전략 데이터 준비 실패 {symbol}: {str(e)}")
                        
                        self.current_data[symbol] = new_data_with_indicators
                        
                        # 현재 가격 업데이트
                        if 'CLOSE' in new_data_with_indicators.columns:
                            self.current_prices[symbol] = new_data_with_indicators.iloc[-1]['CLOSE']
                
        except Exception as e:
            log_error(logger, e, f"데이터 업데이트 {symbol}")
    
    def _execute_signal(self, signal_info: Dict):
        """신호 실행"""
        symbol = signal_info['symbol']
        signal = signal_info['signal']
        confidence = signal_info['confidence']
        
        # 신뢰도 임계값 확인 (Paper Trading 전용: 0.35~0.40)
        min_confidence = 0.35  # Paper Trading: 더 많은 거래 기회
        if confidence < min_confidence:
            logger.debug(f"[Paper Trading] 신뢰도 부족으로 거래 건너뜀: {symbol} (신뢰도: {confidence:.2f} < {min_confidence})")
            return
        
        # 신뢰도 수준별 로깅
        if confidence >= 0.7:
            logger.info(f"🌟 [높은 신뢰도] {symbol}: {confidence:.2%}")
        elif confidence >= 0.5:
            logger.info(f"⭐ [중간 신뢰도] {symbol}: {confidence:.2%}")
        else:
            logger.info(f"💫 [낮은 신뢰도] {symbol}: {confidence:.2%}")
        
        current_price = self.current_prices.get(symbol, 0)
        if current_price <= 0:
            logger.warning(f"유효하지 않은 가격: {symbol}")
            return
        
        if signal == 'BUY':
            self._execute_buy_order(symbol, current_price, signal_info)
        elif signal == 'SELL':
            self._execute_sell_order(symbol, current_price, signal_info)
    
    def _execute_buy_order(self, symbol: str, price: float, signal_info: Dict):
        """매수 주문 실행"""
        try:
            # 개선된 전략에서 제공하는 포지션 크기 사용
            if 'position_size' in signal_info:
                quantity = signal_info['position_size']
            else:
                # 포지션 크기 계산 (기본값)
                quantity = self.portfolio_manager.calculate_position_size(symbol, price)
            
            if quantity <= 0:
                logger.debug(f"매수 수량 부족: {symbol}")
                return
            
            # Alpaca Paper Trading 주문 실행
            order = self.api.submit_order(
                symbol=symbol,
                qty=quantity,
                side='buy',
                type='market',
                time_in_force='day'
            )
            
            logger.info(f"💰 [매수 주문 제출] {quantity}주 {symbol} @ 시장가")
            logger.info(f"   현재 가격: ${price:.2f}")
            logger.info(f"   주문 금액: ${quantity * price:,.2f}")
            logger.info(f"   신호 신뢰도: {signal_info.get('confidence', 0):.2%}")
            log_trade(logger, "BUY", symbol, quantity, price)
            
            self.daily_trade_count += 1
            logger.info(f"   금일 거래 횟수: {self.daily_trade_count}")
            
            # 포지션 매니저 업데이트 (개선된 전략)
            try:
                stop_loss = signal_info.get('stop_loss', price * (1 - STOP_LOSS_PCT))
                take_profit = signal_info.get('take_profit', price * (1 + TAKE_PROFIT_PCT))
                signal_strength = signal_info.get('confidence', 1.0)
                
                position_manager.open_position(
                    symbol=symbol,
                    shares=quantity,
                    price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    signal_strength=signal_strength
                )
                
                logger.info(f"매수 완료: {quantity} {symbol} @ ${price:.2f} (손절: ${stop_loss:.2f}, 익절: ${take_profit:.2f})")
            except Exception as e:
                logger.debug(f"포지션 매니저 업데이트 실패: {str(e)}")
            
        except Exception as e:
            log_error(logger, e, f"매수 주문 {symbol}")
    
    def _execute_sell_order(self, symbol: str, price: float, signal_info: Dict):
        """매도 주문 실행"""
        try:
            # 보유 포지션 확인
            position = self.portfolio_manager.get_position(symbol)
            if not position:
                logger.debug(f"보유하지 않은 종목 매도 시도: {symbol}")
                return
            
            # 전체 매도
            quantity = position.quantity
            
            # Alpaca Paper Trading 주문 실행
            order = self.api.submit_order(
                symbol=symbol,
                qty=quantity,
                side='sell',
                type='market',
                time_in_force='day'
            )
            
            logger.info(f"💵 [매도 주문 제출] {quantity}주 {symbol} @ 시장가")
            logger.info(f"   현재 가격: ${price:.2f}")
            logger.info(f"   주문 금액: ${quantity * price:,.2f}")
            logger.info(f"   신호 신뢰도: {signal_info.get('confidence', 0):.2%}")
            log_trade(logger, "SELL", symbol, quantity, price)
            
            self.daily_trade_count += 1
            logger.info(f"   금일 거래 횟수: {self.daily_trade_count}")
            
            # 포지션 매니저 업데이트 (개선된 전략)
            try:
                reason = signal_info.get('reasons', ['Signal'])[0] if signal_info.get('reasons') else 'Signal'
                position_manager.close_position(symbol, price, reason)
            except Exception as e:
                logger.debug(f"포지션 매니저 업데이트 실패: {str(e)}")
            
            # 손익 계산
            pnl = (price - position.avg_price) * quantity
            pnl_pct = (price - position.avg_price) / position.avg_price
            
            logger.info(f"매도 완료: {quantity} {symbol} @ ${price:.2f} (손익: ${pnl:.2f}, {pnl_pct:.2%})")
            
        except Exception as e:
            log_error(logger, e, f"매도 주문 {symbol}")
    
    def _close_all_positions(self):
        """모든 포지션 청산"""
        try:
            positions = self.api.list_positions()
            
            for pos in positions:
                symbol = pos.symbol
                quantity = int(pos.qty)
                
                if quantity > 0:
                    # 매도 주문
                    self.api.submit_order(
                        symbol=symbol,
                        qty=quantity,
                        side='sell',
                        type='market',
                        time_in_force='day'
                    )
                    logger.info(f"긴급 청산: {quantity} {symbol}")
            
        except Exception as e:
            log_error(logger, e, "긴급 청산")
    
    def _log_portfolio_status(self):
        """포트폴리오 상태 로그"""
        try:
            portfolio_value = self.portfolio_manager.get_portfolio_value(self.current_prices)
            cash = self.portfolio_manager.cash
            positions = self.portfolio_manager.get_all_positions()

            log_portfolio(logger, portfolio_value, cash, positions)

            # 상세 정보
            logger.info(f"포트폴리오 가치: ${portfolio_value:.2f}")
            logger.info(f"현금: ${cash:.2f}")
            logger.info(f"보유 포지션: {len(positions)}개")

            for symbol, position in positions.items():
                logger.info(f"  {symbol}: {position.quantity}주 @ ${position.avg_price:.2f} "
                          f"(현재: ${position.current_price:.2f}, 손익: ${position.unrealized_pnl:.2f})")

            # 상태 파일 저장 (대시보드용)
            self._save_status_file(portfolio_value, cash, positions)

        except Exception as e:
            log_error(logger, e, "포트폴리오 상태 로그")

    def _update_target_symbols(self):
        """설정에서 종목 리스트 업데이트 (장기 + 단기)"""
        try:
            # 1. 설정 다시 로드
            self.settings_manager.settings = self.settings_manager._load_settings()
            
            # 2. 장기 투자 종목 로드
            long_term_symbols = self.settings_manager.get_long_term_symbols()
            
            # 3. 단기 투자 종목 선정 (활성화 된 경우)
            short_term_symbols = []
            if self.settings_manager.is_short_term_enabled():
                count = self.settings_manager.get_short_term_pool_size()
                candidates = self.settings_manager.get_short_term_candidates()
                
                # 장기 투자 종목 제외 (중복 방지)
                candidates = [s for s in candidates if s not in long_term_symbols]
                
                # TODO: 여기에 지능형 단기 종목 선정 로직 구현 (예: 모멘텀, 거래량 등)
                # 현재는 후보군 중에서 앞에서부터 N개 선택
                short_term_symbols = candidates[:count]
                
            # 4. 종목 리스트 병합
            # 기존 symbols와 비교하여 변경사항이 있을 때만 로그 출력
            new_symbols = list(set(long_term_symbols + short_term_symbols))
            
            if set(new_symbols) != set(self.symbols):
                logger.info(f"🔄 종목 리스트 업데이트: 총 {len(new_symbols)}개")
                logger.info(f"  - 장기 ({len(long_term_symbols)}): {long_term_symbols}")
                logger.info(f"  - 단기 ({len(short_term_symbols)}): {short_term_symbols}")
                
                self.symbols = new_symbols
                self.short_term_symbols = short_term_symbols
                
                # 새로운 종목에 대한 데이터 로드
                self._load_initial_data()
                
        except Exception as e:
            log_error(logger, e, "종목 리스트 업데이트")
    
    def _save_status_file(self, portfolio_value: float, cash: float, positions: Dict):
        """상태 파일 저장 (대시보드가 별도 프로세스일 때 사용)"""
        try:
            status_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'trader_status.json')

            status_data = {
                'portfolio_value': portfolio_value,
                'cash': cash,
                'total_return': (portfolio_value - INITIAL_CAPITAL) / INITIAL_CAPITAL if INITIAL_CAPITAL > 0 else 0,
                'daily_return': 0,  # 일일 수익률은 별도 계산 필요
                'positions': {
                    symbol: {
                        'quantity': pos.quantity,
                        'avg_price': pos.avg_price,
                        'current_price': pos.current_price,
                        'unrealized_pnl': pos.unrealized_pnl
                    } for symbol, pos in positions.items()
                },
                'daily_trades': self.daily_trade_count,
                'is_running': self.is_running,
                'last_updated': datetime.now().isoformat()
            }

            with open(status_file, 'w') as f:
                json.dump(status_data, f, indent=2)

            logger.debug(f"상태 파일 저장: {status_file}")

        except Exception as e:
            logger.debug(f"상태 파일 저장 실패: {str(e)}")

    def _log_final_status(self):
        """최종 상태 로그"""
        try:
            portfolio_value = self.portfolio_manager.get_portfolio_value(self.current_prices)
            total_return = (portfolio_value - INITIAL_CAPITAL) / INITIAL_CAPITAL

            logger.info("=== Paper Trading 최종 결과 ===")
            logger.info(f"초기 자본: ${INITIAL_CAPITAL:,.2f}")
            logger.info(f"최종 가치: ${portfolio_value:,.2f}")
            logger.info(f"총 수익률: {total_return:.2%}")
            logger.info(f"총 거래 횟수: {len(self.portfolio_manager.trades)}")

        except Exception as e:
            log_error(logger, e, "최종 상태 로그")
    
    def get_current_status(self) -> Dict:
        """현재 상태 반환"""
        try:
            portfolio_value = self.portfolio_manager.get_portfolio_value(self.current_prices)
            positions = self.portfolio_manager.get_all_positions()
            
            return {
                'portfolio_value': portfolio_value,
                'cash': self.portfolio_manager.cash,
                'total_return': (portfolio_value - INITIAL_CAPITAL) / INITIAL_CAPITAL,
                'positions': {symbol: {
                    'quantity': pos.quantity,
                    'avg_price': pos.avg_price,
                    'current_price': pos.current_price,
                    'unrealized_pnl': pos.unrealized_pnl
                } for symbol, pos in positions.items()},
                'daily_trades': self.daily_trade_count,
                'is_running': self.is_running,
                'emergency_stop': self.emergency_stop
            }
            
        except Exception as e:
            log_error(logger, e, "상태 조회")
            return {}
    
    def get_trade_history(self) -> pd.DataFrame:
        """거래 내역 반환"""
        return self.portfolio_manager.get_trade_history()



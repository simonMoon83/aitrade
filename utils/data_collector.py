"""
주식 데이터 수집 모듈
yfinance를 사용하여 미국 주식 데이터를 수집합니다.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict
import pickle

from config import DATA_DIR, DATA_START_DATE, DATA_END_DATE
from utils.logger import setup_logger
from utils.market_calendar import market_calendar

logger = setup_logger("data_collector")

class DataCollector:
    """주식 데이터 수집 클래스"""
    
    def __init__(self, data_dir: str = DATA_DIR):
        """
        초기화
        
        Args:
            data_dir (str): 데이터 저장 디렉토리
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def _resolve_last_trading_day(self) -> date:
        last_trading_day = market_calendar.get_last_completed_trading_day()
        if last_trading_day:
            return last_trading_day
        return datetime.now().date()

    def _resolve_start_trading_day(self, end_date: date, target_days: int) -> date:
        recent_days = market_calendar.get_recent_trading_days(end_date, target_days)
        if recent_days:
            return recent_days[0]
        # fallback: 단순 날짜 계산
        return end_date - timedelta(days=target_days * 2)
        
    def download_stock_data(self,
                           symbol: str,
                           start_date: str = DATA_START_DATE,
                           end_date: str = DATA_END_DATE,
                           period: str = "1d",
                           max_retries: int = 3) -> pd.DataFrame:
        """
        개별 종목 데이터 다운로드 (재시도 로직 포함)

        Args:
            symbol (str): 종목 코드
            start_date (str): 시작 날짜 (YYYY-MM-DD)
            end_date (str): 종료 날짜 (YYYY-MM-DD)
            period (str): 데이터 주기 (1d, 1h, 5m 등)
            max_retries (int): 최대 재시도 횟수

        Returns:
            pd.DataFrame: OHLCV 데이터
        """
        import time

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # 지수 백오프: 2, 4, 8초
                    logger.info(f"재시도 대기 중... ({wait_time}초)")
                    time.sleep(wait_time)

                logger.info(f"다운로드 중: {symbol} ({start_date} ~ {end_date}) [시도 {attempt + 1}/{max_retries}]")

                ticker = yf.Ticker(symbol)
                data = ticker.history(
                    start=start_date,
                    end=end_date,
                    auto_adjust=True,
                    prepost=True
                )

                if data.empty:
                    logger.warning(f"데이터가 비어있음: {symbol} (시도 {attempt + 1}/{max_retries})")

                    # 마지막 시도가 아니면 계속 재시도
                    if attempt < max_retries - 1:
                        continue

                    # 마지막 시도에서도 실패하면 이전 영업일 시도
                    logger.info(f"{symbol} 이전 영업일 데이터로 fallback 시도")
                    from pandas.tseries.offsets import BDay
                    fallback_end = pd.Timestamp(end_date) - BDay(1)
                    fallback_start = pd.Timestamp(start_date) - BDay(1)

                    data = ticker.history(
                        start=fallback_start.strftime('%Y-%m-%d'),
                        end=fallback_end.strftime('%Y-%m-%d'),
                        auto_adjust=True,
                        prepost=True
                    )

                    if data.empty:
                        logger.error(f"{symbol} fallback도 실패 - 빈 데이터 반환")
                        return pd.DataFrame()

                # 컬럼명 정규화
                data.columns = [col.upper() for col in data.columns]

                # 인덱스를 날짜 컬럼으로 변환
                data.reset_index(inplace=True)
                data['Date'] = pd.to_datetime(data['Date']).dt.date

                # 결측치 처리
                data = self._clean_data(data)

                logger.info(f"다운로드 완료: {symbol} - {len(data)}개 레코드")
                return data

            except Exception as e:
                logger.error(f"데이터 다운로드 실패 {symbol} (시도 {attempt + 1}/{max_retries}): {str(e)}")

                if attempt == max_retries - 1:
                    logger.error(f"{symbol} 모든 재시도 실패 - 빈 데이터 반환")
                    return pd.DataFrame()

        return pd.DataFrame()
    
    def download_multiple_stocks(self, 
                                symbols: List[str],
                                start_date: str = DATA_START_DATE,
                                end_date: str = DATA_END_DATE,
                                period: str = "1d") -> Dict[str, pd.DataFrame]:
        """
        여러 종목 데이터 일괄 다운로드
        
        Args:
            symbols (List[str]): 종목 코드 리스트
            start_date (str): 시작 날짜
            end_date (str): 종료 날짜
            period (str): 데이터 주기
        
        Returns:
            Dict[str, pd.DataFrame]: 종목별 데이터 딕셔너리
        """
        all_data = {}
        
        for symbol in symbols:
            data = self.download_stock_data(symbol, start_date, end_date, period)
            if not data.empty:
                all_data[symbol] = data
                
        logger.info(f"총 {len(all_data)}개 종목 데이터 수집 완료")
        return all_data
    
    def get_cached_data(self, symbol: str) -> pd.DataFrame:
        """
        캐시된 데이터 로드 (증분 업데이트용)
        
        Args:
            symbol (str): 종목 코드
        
        Returns:
            pd.DataFrame: 캐시된 데이터 (없으면 빈 DataFrame)
        """
        cache_file = os.path.join(self.data_dir, f"{symbol}_cache.pkl")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    logger.info(f"캐시 로드: {symbol} - {len(cached_data)}개 레코드 (마지막: {cached_data.iloc[-1]['Date']})")
                    return cached_data
            except Exception as e:
                logger.warning(f"캐시 로드 실패 {symbol}: {str(e)}")
        
        return pd.DataFrame()
    
    def save_cache(self, data: pd.DataFrame, symbol: str):
        """
        데이터를 캐시 파일로 저장
        
        Args:
            data (pd.DataFrame): 저장할 데이터
            symbol (str): 종목 코드
        """
        cache_file = os.path.join(self.data_dir, f"{symbol}_cache.pkl")
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            logger.debug(f"캐시 저장: {symbol} - {len(data)}개 레코드")
        except Exception as e:
            logger.error(f"캐시 저장 실패 {symbol}: {str(e)}")
    
    def get_latest_data_incremental(self, symbol: str, target_days: int = 60) -> pd.DataFrame:
        """
        증분 업데이트 방식으로 최신 데이터 가져오기
        캐시된 데이터가 있으면 마지막 날짜 이후만 다운로드
        
        Args:
            symbol (str): 종목 코드
            target_days (int): 최종적으로 유지할 일수
        
        Returns:
            pd.DataFrame: 최신 데이터
        """
        # 캐시된 데이터 확인
        cached_data = self.get_cached_data(symbol)
        
        # 최신 거래일 기준
        end_date = self._resolve_last_trading_day()
        logger.debug(f"{symbol} 최신 거래일 기준: {end_date}")
        
        if not cached_data.empty:
            # 캐시가 있으면 마지막 날짜 이후만 다운로드
            last_date = cached_data.iloc[-1]['Date']
            if isinstance(last_date, str):
                last_date = datetime.strptime(last_date, '%Y-%m-%d').date()
            elif isinstance(last_date, pd.Timestamp):
                last_date = last_date.date()
            
            # 이미 최신이면 캐시 반환
            if last_date >= end_date:
                logger.info(f"{symbol} 캐시가 최신 상태 - 다운로드 생략")
                return cached_data.tail(target_days).reset_index(drop=True)
            
            # 마지막 날짜 다음 날부터 다운로드
            next_trading_day = market_calendar.get_next_trading_day(last_date, include_today=False)
            if not next_trading_day:
                logger.info(f"{symbol} 다음 거래일 정보를 확인할 수 없어 캐시 반환")
                return cached_data.tail(target_days).reset_index(drop=True)

            start_date = next_trading_day
            if start_date > end_date:
                logger.info(f"{symbol} 새 거래일 데이터 없음 - 캐시 반환")
                return cached_data.tail(target_days).reset_index(drop=True)

            logger.info(f"{symbol} 증분 업데이트: {start_date} ~ {end_date}")
            
            new_data = self.download_stock_data(
                symbol,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            if not new_data.empty:
                # 기존 데이터와 병합
                combined_data = pd.concat([cached_data, new_data], ignore_index=True)
                combined_data = combined_data.drop_duplicates(subset=['Date'], keep='last')
                combined_data = combined_data.sort_values('Date').tail(target_days).reset_index(drop=True)
                
                # 캐시 업데이트
                self.save_cache(combined_data, symbol)
                logger.info(f"{symbol} 증분 업데이트 완료: +{len(new_data)}개 레코드")
                
                return combined_data
            else:
                # 새 데이터가 없으면 캐시 반환
                logger.info(f"{symbol} 새 데이터 없음 - 캐시 반환")
                return cached_data.tail(target_days).reset_index(drop=True)
        else:
            # 캐시가 없으면 전체 다운로드
            end_date = self._resolve_last_trading_day()
            start_date = self._resolve_start_trading_day(end_date, target_days)
            
            logger.info(f"{symbol} 초기 다운로드: {start_date} ~ {end_date}")
            
            data = self.download_stock_data(
                symbol,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            if not data.empty:
                self.save_cache(data, symbol)
            
            return data
    
    def save_data(self, data: pd.DataFrame, symbol: str, file_format: str = "csv"):
        """
        데이터를 파일로 저장
        
        Args:
            data (pd.DataFrame): 저장할 데이터
            symbol (str): 종목 코드
            file_format (str): 파일 형식 (csv, pickle)
        """
        if data.empty:
            logger.warning(f"빈 데이터는 저장하지 않음: {symbol}")
            return
        
        filename = f"{symbol}_{datetime.now().strftime('%Y%m%d')}.{file_format}"
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            if file_format == "csv":
                data.to_csv(filepath, index=False)
            elif file_format == "pickle":
                with open(filepath, 'wb') as f:
                    pickle.dump(data, f)
            
            logger.info(f"데이터 저장 완료: {filepath}")
            
        except Exception as e:
            logger.error(f"데이터 저장 실패 {symbol}: {str(e)}")
    
    def load_data(self, symbol: str, file_format: str = "csv") -> pd.DataFrame:
        """
        저장된 데이터 로드
        
        Args:
            symbol (str): 종목 코드
            file_format (str): 파일 형식
        
        Returns:
            pd.DataFrame: 로드된 데이터
        """
        filename = f"{symbol}_{datetime.now().strftime('%Y%m%d')}.{file_format}"
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            if file_format == "csv":
                data = pd.read_csv(filepath)
                data['Date'] = pd.to_datetime(data['Date']).dt.date
            elif file_format == "pickle":
                with open(filepath, 'rb') as f:
                    data = pickle.load(f)
            
            logger.info(f"데이터 로드 완료: {filepath}")
            return data
            
        except FileNotFoundError:
            logger.warning(f"파일을 찾을 수 없음: {filepath}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"데이터 로드 실패 {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def get_latest_data(self, symbol: str, days: int = 1) -> pd.DataFrame:
        """
        최신 데이터 가져오기 (실시간 거래용)
        주말/휴장일 자동 처리

        Args:
            symbol (str): 종목 코드
            days (int): 가져올 일수

        Returns:
            pd.DataFrame: 최신 데이터
        """
        end_date = self._resolve_last_trading_day()
        recent_days = market_calendar.get_recent_trading_days(end_date, max(days, 1) + 1)
        if recent_days:
            start_date = recent_days[0]
        else:
            start_date = end_date - timedelta(days=days * 2)

        logger.info(f"{symbol} 최신 데이터 요청: {start_date} ~ {end_date}")

        return self.download_stock_data(
            symbol,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
    
    def _clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        데이터 정리 (결측치, 이상치 처리)
        
        Args:
            data (pd.DataFrame): 원본 데이터
        
        Returns:
            pd.DataFrame: 정리된 데이터
        """
        # 결측치 제거
        data = data.dropna()
        
        # 가격이 0 이하인 행 제거
        price_columns = ['OPEN', 'HIGH', 'LOW', 'CLOSE']
        for col in price_columns:
            if col in data.columns:
                data = data[data[col] > 0]
        
        # 거래량이 0인 행 제거
        if 'VOLUME' in data.columns:
            data = data[data['VOLUME'] > 0]
        
        # 중복 날짜 제거
        data = data.drop_duplicates(subset=['Date'])
        
        # 날짜순 정렬
        data = data.sort_values('Date').reset_index(drop=True)
        
        return data
    
    def validate_data(self, data: pd.DataFrame, symbol: str) -> bool:
        """
        데이터 유효성 검사
        
        Args:
            data (pd.DataFrame): 검사할 데이터
            symbol (str): 종목 코드
        
        Returns:
            bool: 유효성 여부
        """
        if data.empty:
            logger.warning(f"빈 데이터: {symbol}")
            return False
        
        # 필수 컬럼 확인
        required_columns = ['Date', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            logger.error(f"필수 컬럼 누락 {symbol}: {missing_columns}")
            return False
        
        # 가격 로직 검사 (High >= Low, High >= Close, Low <= Close)
        invalid_rows = (
            (data['HIGH'] < data['LOW']) |
            (data['HIGH'] < data['CLOSE']) |
            (data['LOW'] > data['CLOSE'])
        )
        
        if invalid_rows.any():
            logger.warning(f"가격 로직 오류 {symbol}: {invalid_rows.sum()}개 행")
            return False
        
        logger.info(f"데이터 유효성 검사 통과: {symbol}")
        return True
    
    def get_market_info(self, symbol: str) -> Dict:
        """
        종목 기본 정보 가져오기
        
        Args:
            symbol (str): 종목 코드
        
        Returns:
            Dict: 종목 정보
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'symbol': symbol,
                'name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'beta': info.get('beta', 0),
                '52_week_high': info.get('fiftyTwoWeekHigh', 0),
                '52_week_low': info.get('fiftyTwoWeekLow', 0),
            }
            
        except Exception as e:
            logger.error(f"종목 정보 조회 실패 {symbol}: {str(e)}")
            return {}

# 전역 데이터 수집기 인스턴스
data_collector = DataCollector()

def collect_stock_data(symbols: List[str], 
                      start_date: str = DATA_START_DATE,
                      end_date: str = DATA_END_DATE,
                      save_to_file: bool = True) -> Dict[str, pd.DataFrame]:
    """
    편의 함수: 주식 데이터 수집
    
    Args:
        symbols (List[str]): 종목 코드 리스트
        start_date (str): 시작 날짜
        end_date (str): 종료 날짜
        save_to_file (bool): 파일 저장 여부
    
    Returns:
        Dict[str, pd.DataFrame]: 종목별 데이터
    """
    all_data = data_collector.download_multiple_stocks(symbols, start_date, end_date)
    
    if save_to_file:
        for symbol, data in all_data.items():
            if data_collector.validate_data(data, symbol):
                data_collector.save_data(data, symbol)
    
    return all_data


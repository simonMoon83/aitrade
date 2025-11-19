"""
암호화폐 데이터 수집 모듈
yfinance를 사용하여 암호화폐 데이터를 수집합니다.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import time

from utils.logger import setup_logger

logger = setup_logger("crypto_data_collector")

class CryptoDataCollector:
    """암호화폐 데이터 수집 클래스"""
    
    def __init__(self):
        """초기화"""
        pass
    
    def download_crypto_data(self, 
                            symbol: str, 
                            start_date: str,
                            end_date: str) -> pd.DataFrame:
        """
        개별 암호화폐 데이터 다운로드
        
        Args:
            symbol (str): 암호화폐 심볼 (예: 'BTC/USD')
            start_date (str): 시작 날짜 (YYYY-MM-DD)
            end_date (str): 종료 날짜 (YYYY-MM-DD)
        
        Returns:
            pd.DataFrame: OHLCV 데이터
        """
        try:
            # yfinance는 / 대신 - 사용
            ticker_symbol = symbol.replace('/', '-')
            
            logger.info(f"다운로드 중: {symbol} ({start_date} ~ {end_date})")
            
            ticker = yf.Ticker(ticker_symbol)
            data = ticker.history(
                start=start_date,
                end=end_date,
                auto_adjust=True
            )
            
            if data.empty:
                logger.warning(f"데이터가 비어있음: {symbol}")
                return pd.DataFrame()
            
            # 컬럼명 정규화 (주식과 동일하게)
            data.columns = [col.upper() for col in data.columns]
            
            # 인덱스를 날짜 컬럼으로 변환
            data.reset_index(inplace=True)
            
            # Date 컬럼 처리
            if 'DATE' in data.columns:
                data.rename(columns={'DATE': 'Date'}, inplace=True)
            
            data['Date'] = pd.to_datetime(data['Date']).dt.date
            
            # 결측치 처리
            data = self._clean_data(data)
            
            logger.info(f"다운로드 완료: {symbol} - {len(data)}개 레코드")
            return data
            
        except Exception as e:
            logger.error(f"데이터 다운로드 실패 {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def _clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """데이터 정제"""
        if data.empty:
            return data
        
        # 결측치 제거
        data = data.dropna(subset=['CLOSE', 'VOLUME'])
        
        # 가격이 0인 행 제거
        data = data[data['CLOSE'] > 0]
        
        # 거래량이 0인 행 제거 (암호화폐는 24/7이므로 거래량이 항상 있어야 함)
        data = data[data['VOLUME'] > 0]
        
        return data
    
    def download_multiple_cryptos(self, 
                                  symbols: List[str], 
                                  start_date: str,
                                  end_date: str) -> Dict[str, pd.DataFrame]:
        """
        여러 암호화폐 데이터 다운로드
        
        Args:
            symbols (List[str]): 암호화폐 심볼 리스트
            start_date (str): 시작 날짜
            end_date (str): 종료 날짜
        
        Returns:
            Dict[str, pd.DataFrame]: 심볼별 데이터
        """
        all_data = {}
        
        for symbol in symbols:
            try:
                data = self.download_crypto_data(symbol, start_date, end_date)
                
                if not data.empty:
                    all_data[symbol] = data
                    # API rate limit 방지
                    time.sleep(1)
                else:
                    logger.warning(f"{symbol} 데이터 없음")
                    
            except Exception as e:
                logger.error(f"{symbol} 다운로드 실패: {str(e)}")
                continue
        
        return all_data
    
    def get_realtime_price(self, symbol: str) -> float:
        """
        실시간 가격 조회
        
        Args:
            symbol (str): 암호화폐 심볼
        
        Returns:
            float: 현재 가격
        """
        try:
            ticker_symbol = symbol.replace('/', '-')
            ticker = yf.Ticker(ticker_symbol)
            
            # 최근 데이터 조회
            data = ticker.history(period='1d')
            
            if not data.empty:
                return data['Close'].iloc[-1]
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"{symbol} 실시간 가격 조회 실패: {str(e)}")
            return 0.0
    
    def get_crypto_info(self, symbol: str) -> Dict:
        """
        암호화폐 기본 정보 조회
        
        Args:
            symbol (str): 암호화폐 심볼
        
        Returns:
            Dict: 기본 정보
        """
        try:
            ticker_symbol = symbol.replace('/', '-')
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            return {
                'symbol': symbol,
                'name': info.get('name', symbol),
                'market_cap': info.get('marketCap', 0),
                'volume_24h': info.get('volume24Hr', 0),
                'circulating_supply': info.get('circulatingSupply', 0),
                'max_supply': info.get('maxSupply', 0),
            }
            
        except Exception as e:
            logger.error(f"{symbol} 정보 조회 실패: {str(e)}")
            return {'symbol': symbol}

# 전역 인스턴스
crypto_collector = CryptoDataCollector()

def download_crypto_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """편의 함수: 암호화폐 데이터 다운로드"""
    return crypto_collector.download_crypto_data(symbol, start_date, end_date)

def download_multiple_cryptos(symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
    """편의 함수: 여러 암호화폐 데이터 다운로드"""
    return crypto_collector.download_multiple_cryptos(symbols, start_date, end_date)


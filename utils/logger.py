"""
로깅 유틸리티
"""

import logging
import os
import sys
from datetime import datetime
from config import LOG_LEVEL, LOGS_DIR

def setup_logger(name, level=LOG_LEVEL, log_file=None):
    """
    로거 설정
    
    Args:
        name (str): 로거 이름
        level (str): 로그 레벨
        log_file (str): 로그 파일 경로
    
    Returns:
        logging.Logger: 설정된 로거
    """
    # Windows 콘솔 UTF-8 설정
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            # Python 3.6 이하 버전 대응
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    
    # 로그 디렉토리 생성
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 중복 핸들러 방지
    if logger.handlers:
        return logger
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러 (UTF-8 인코딩)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러
    if log_file is None:
        log_file = os.path.join(LOGS_DIR, f"{name}_{datetime.now().strftime('%Y%m%d')}.log")
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(getattr(logging, level.upper()))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

def log_trade(logger, action, symbol, quantity, price, timestamp=None):
    """
    거래 로그 기록
    
    Args:
        logger: 로거 객체
        action (str): 거래 액션 (BUY/SELL)
        symbol (str): 종목 코드
        quantity (int): 수량
        price (float): 가격
        timestamp (datetime): 거래 시간
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    logger.info(f"TRADE - {action} {quantity} {symbol} @ ${price:.2f} at {timestamp}")

def log_signal(logger, symbol, signal, confidence, indicators):
    """
    AI 신호 로그 기록
    
    Args:
        logger: 로거 객체
        symbol (str): 종목 코드
        signal (str): 신호 (BUY/SELL/HOLD)
        confidence (float): 신호 확신도 (0-1)
        indicators (dict): 기술적 지표 값들
    """
    logger.info(f"SIGNAL - {symbol}: {signal} (confidence: {confidence:.2f}) - {indicators}")

def log_portfolio(logger, portfolio_value, cash, positions):
    """
    포트폴리오 상태 로그 기록
    
    Args:
        logger: 로거 객체
        portfolio_value (float): 포트폴리오 총 가치
        cash (float): 현금
        positions (dict): 보유 포지션
    """
    logger.info(f"PORTFOLIO - Value: ${portfolio_value:.2f}, Cash: ${cash:.2f}, Positions: {len(positions)}")

def log_error(logger, error, context=None):
    """
    에러 로그 기록
    
    Args:
        logger: 로거 객체
        error (Exception): 에러 객체
        context (str): 에러 발생 컨텍스트
    """
    if context:
        logger.error(f"ERROR in {context}: {str(error)}", exc_info=True)
    else:
        logger.error(f"ERROR: {str(error)}", exc_info=True)


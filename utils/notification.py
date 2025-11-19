"""
알림 시스템
텔레그램, 이메일 등을 통한 알림 발송
"""

import requests
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Dict, List, Optional
from datetime import datetime
import json

from config import *
from utils.logger import setup_logger

logger = setup_logger("notification")

class NotificationManager:
    """알림 관리 클래스"""
    
    def __init__(self):
        """초기화"""
        self.telegram_enabled = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
        self.email_enabled = False  # 이메일 설정은 별도로 필요
        
        if self.telegram_enabled:
            logger.info("텔레그램 알림 활성화")
        else:
            logger.info("텔레그램 알림 비활성화 (토큰 또는 채팅 ID 없음)")
    
    def send_trade_notification(self, symbol: str, action: str, quantity: int, 
                              price: float, pnl: float = 0.0):
        """
        거래 알림 발송
        
        Args:
            symbol (str): 종목 코드
            action (str): 거래 액션 (BUY/SELL)
            quantity (int): 수량
            price (float): 가격
            pnl (float): 손익
        """
        message = f"🔔 거래 알림\n\n"
        message += f"종목: {symbol}\n"
        message += f"액션: {action}\n"
        message += f"수량: {quantity}주\n"
        message += f"가격: ${price:.2f}\n"
        
        if pnl != 0:
            pnl_emoji = "📈" if pnl > 0 else "📉"
            message += f"손익: {pnl_emoji} ${pnl:.2f}\n"
        
        message += f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self._send_telegram_message(message)
    
    def send_portfolio_notification(self, portfolio_value: float, total_return: float,
                                  daily_trades: int, positions_count: int):
        """
        포트폴리오 상태 알림 발송
        
        Args:
            portfolio_value (float): 포트폴리오 가치
            total_return (float): 총 수익률
            daily_trades (int): 일일 거래 횟수
            positions_count (int): 보유 포지션 수
        """
        message = f"📊 포트폴리오 현황\n\n"
        message += f"포트폴리오 가치: ${portfolio_value:,.2f}\n"
        
        return_emoji = "📈" if total_return > 0 else "📉"
        message += f"총 수익률: {return_emoji} {total_return:.2%}\n"
        message += f"일일 거래: {daily_trades}회\n"
        message += f"보유 포지션: {positions_count}개\n"
        message += f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self._send_telegram_message(message)
    
    def send_risk_alert(self, alert_level: str, message: str, symbol: str = None):
        """
        리스크 알림 발송
        
        Args:
            alert_level (str): 알림 레벨 (LOW/MEDIUM/HIGH/CRITICAL)
            message (str): 알림 메시지
            symbol (str): 종목 코드 (선택사항)
        """
        level_emojis = {
            'LOW': '🟢',
            'MEDIUM': '🟡',
            'HIGH': '🟠',
            'CRITICAL': '🔴'
        }
        
        emoji = level_emojis.get(alert_level, '⚠️')
        
        alert_message = f"{emoji} 리스크 알림 ({alert_level})\n\n"
        if symbol:
            alert_message += f"종목: {symbol}\n"
        alert_message += f"내용: {message}\n"
        alert_message += f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self._send_telegram_message(alert_message)
    
    def send_daily_summary(self, summary_data: Dict):
        """
        일일 요약 알림 발송
        
        Args:
            summary_data (Dict): 요약 데이터
        """
        message = f"📋 일일 요약 ({summary_data.get('date', 'N/A')})\n\n"
        message += f"포트폴리오 가치: ${summary_data.get('portfolio_value', 0):,.2f}\n"
        message += f"총 수익률: {summary_data.get('total_return', 0):.2%}\n"
        message += f"일일 거래: {summary_data.get('daily_trades', 0)}회\n"
        message += f"보유 포지션: {summary_data.get('positions_count', 0)}개\n"
        
        # 주요 포지션 손익
        positions = summary_data.get('positions', [])
        if positions:
            message += f"\n주요 포지션:\n"
            for pos in positions[:5]:  # 상위 5개만
                pnl_emoji = "📈" if pos['unrealized_pnl'] > 0 else "📉"
                message += f"• {pos['symbol']}: {pnl_emoji} ${pos['unrealized_pnl']:.2f}\n"
        
        self._send_telegram_message(message)
    
    def send_error_notification(self, error_message: str, context: str = None):
        """
        에러 알림 발송
        
        Args:
            error_message (str): 에러 메시지
            context (str): 에러 발생 컨텍스트
        """
        message = f"❌ 시스템 오류\n\n"
        if context:
            message += f"위치: {context}\n"
        message += f"오류: {error_message}\n"
        message += f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self._send_telegram_message(message)
    
    def _send_telegram_message(self, message: str):
        """
        텔레그램 메시지 발송
        
        Args:
            message (str): 발송할 메시지
        """
        if not self.telegram_enabled:
            logger.debug("텔레그램 알림 비활성화됨")
            return
        
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                logger.debug("텔레그램 메시지 발송 성공")
            else:
                logger.error(f"텔레그램 메시지 발송 실패: {response.status_code}")
                
        except Exception as e:
            logger.error(f"텔레그램 메시지 발송 오류: {str(e)}")
    
    def send_email_notification(self, subject: str, message: str, 
                              to_emails: List[str] = None):
        """
        이메일 알림 발송 (구현 예정)
        
        Args:
            subject (str): 이메일 제목
            message (str): 이메일 내용
            to_emails (List[str]): 수신자 이메일 리스트
        """
        # 이메일 발송 기능은 별도 설정 필요
        logger.info(f"이메일 알림 (구현 예정): {subject}")
        pass
    
    def test_notification(self):
        """알림 테스트"""
        test_message = f"🧪 알림 테스트\n\n"
        test_message += f"시스템이 정상적으로 작동 중입니다.\n"
        test_message += f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self._send_telegram_message(test_message)
        logger.info("알림 테스트 완료")

class TelegramBot:
    """텔레그램 봇 클래스 (명령어 처리)"""
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        초기화
        
        Args:
            bot_token (str): 봇 토큰
            chat_id (str): 채팅 ID
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.last_update_id = 0
        
    def get_updates(self) -> List[Dict]:
        """업데이트 가져오기"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            params = {
                'offset': self.last_update_id + 1,
                'timeout': 10
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data['ok']:
                    return data['result']
            
            return []
            
        except Exception as e:
            logger.error(f"텔레그램 업데이트 가져오기 오류: {str(e)}")
            return []
    
    def process_commands(self, trader_instance=None):
        """명령어 처리"""
        updates = self.get_updates()
        
        for update in updates:
            if 'message' in update:
                message = update['message']
                text = message.get('text', '')
                chat_id = message['chat']['id']
                
                # 명령어 처리
                if text.startswith('/'):
                    self._handle_command(text, chat_id, trader_instance)
                
                self.last_update_id = update['update_id']
    
    def _handle_command(self, command: str, chat_id: str, trader_instance=None):
        """명령어 처리"""
        if chat_id != int(self.chat_id):
            return  # 허용되지 않은 채팅 ID
        
        command = command.lower().strip()
        
        try:
            if command == '/status':
                self._send_status(chat_id, trader_instance)
            elif command == '/today':
                self._send_today_summary(chat_id, trader_instance)
            elif command == '/trades':
                self._send_recent_trades(chat_id, trader_instance)
            elif command == '/help':
                self._send_help(chat_id)
            else:
                self._send_message(chat_id, "알 수 없는 명령어입니다. /help를 입력하세요.")
                
        except Exception as e:
            logger.error(f"명령어 처리 오류: {str(e)}")
            self._send_message(chat_id, "명령어 처리 중 오류가 발생했습니다.")
    
    def _send_status(self, chat_id: str, trader_instance=None):
        """상태 정보 전송"""
        if not trader_instance:
            self._send_message(chat_id, "트레이더가 초기화되지 않았습니다.")
            return
        
        try:
            status = trader_instance.get_current_status()
            
            message = f"📊 현재 상태\n\n"
            message += f"포트폴리오 가치: ${status.get('portfolio_value', 0):,.2f}\n"
            message += f"총 수익률: {status.get('total_return', 0):.2%}\n"
            message += f"현금: ${status.get('cash', 0):,.2f}\n"
            message += f"보유 포지션: {len(status.get('positions', {}))}개\n"
            message += f"일일 거래: {status.get('daily_trades', 0)}회\n"
            message += f"상태: {'실행 중' if status.get('is_running', False) else '중지'}"
            
            self._send_message(chat_id, message)
            
        except Exception as e:
            self._send_message(chat_id, f"상태 조회 오류: {str(e)}")
    
    def _send_today_summary(self, chat_id: str, trader_instance=None):
        """오늘 요약 전송"""
        # 구현 예정
        self._send_message(chat_id, "오늘 요약 기능은 구현 예정입니다.")
    
    def _send_recent_trades(self, chat_id: str, trader_instance=None):
        """최근 거래 내역 전송"""
        if not trader_instance:
            self._send_message(chat_id, "트레이더가 초기화되지 않았습니다.")
            return
        
        try:
            trade_history = trader_instance.get_trade_history()
            
            if trade_history.empty:
                self._send_message(chat_id, "거래 내역이 없습니다.")
                return
            
            # 최근 5개 거래
            recent_trades = trade_history.tail(5)
            
            message = f"📋 최근 거래 내역\n\n"
            
            for _, trade in recent_trades.iterrows():
                pnl_emoji = "📈" if trade['pnl'] > 0 else "📉" if trade['pnl'] < 0 else "➖"
                message += f"{pnl_emoji} {trade['symbol']} {trade['order_type']} "
                message += f"{trade['quantity']}주 @ ${trade['price']:.2f}\n"
                if trade['pnl'] != 0:
                    message += f"   손익: ${trade['pnl']:.2f}\n"
                message += f"   {trade['timestamp'].strftime('%m-%d %H:%M')}\n\n"
            
            self._send_message(chat_id, message)
            
        except Exception as e:
            self._send_message(chat_id, f"거래 내역 조회 오류: {str(e)}")
    
    def _send_help(self, chat_id: str):
        """도움말 전송"""
        message = f"🤖 AI 트레이더 봇 명령어\n\n"
        message += f"/status - 현재 포트폴리오 상태\n"
        message += f"/today - 오늘 거래 요약\n"
        message += f"/trades - 최근 거래 내역\n"
        message += f"/help - 이 도움말\n\n"
        message += f"자동 알림: 거래 실행, 리스크 알림, 일일 요약"
        
        self._send_message(chat_id, message)
    
    def _send_message(self, chat_id: str, message: str):
        """메시지 전송"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                logger.debug(f"텔레그램 메시지 전송 성공: {chat_id}")
            else:
                logger.error(f"텔레그램 메시지 전송 실패: {response.status_code}")
                
        except Exception as e:
            logger.error(f"텔레그램 메시지 전송 오류: {str(e)}")

# 전역 알림 관리자 인스턴스
notification_manager = NotificationManager()

def send_telegram_message(message: str):
    """
    편의 함수: 텔레그램 메시지 발송
    
    Args:
        message (str): 발송할 메시지
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.debug("텔레그램 알림 비활성화됨 (토큰 또는 채팅 ID 없음)")
        return
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            logger.debug("텔레그램 메시지 발송 성공")
        else:
            logger.error(f"텔레그램 메시지 발송 실패: {response.status_code}")
            
    except Exception as e:
        logger.error(f"텔레그램 메시지 발송 오류: {str(e)}")

def send_trade_notification(symbol: str, action: str, quantity: int, price: float, pnl: float = 0.0):
    """
    편의 함수: 거래 알림 발송
    
    Args:
        symbol (str): 종목 코드
        action (str): 거래 액션
        quantity (int): 수량
        price (float): 가격
        pnl (float): 손익
    """
    notification_manager.send_trade_notification(symbol, action, quantity, price, pnl)

def send_risk_alert(alert_level: str, message: str, symbol: str = None):
    """
    편의 함수: 리스크 알림 발송
    
    Args:
        alert_level (str): 알림 레벨
        message (str): 알림 메시지
        symbol (str): 종목 코드
    """
    notification_manager.send_risk_alert(alert_level, message, symbol)


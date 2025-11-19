"""
시스템 상태 모니터링 및 헬스체크 모듈
"""

import os
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from utils.logger import setup_logger
from utils.market_calendar import market_calendar

logger = setup_logger("system_monitor")

class SystemMonitor:
    """시스템 상태 모니터링 클래스"""
    
    def __init__(self, log_dir: str = "logs"):
        """
        초기화
        
        Args:
            log_dir (str): 로그 디렉토리 경로
        """
        self.log_dir = Path(log_dir)
        self.heartbeat_file = self.log_dir / "system_heartbeat.txt"
    
    def record_heartbeat(self):
        """
        시스템 생존 신호 기록
        매 시간마다 호출하여 시스템이 정상 작동 중임을 기록
        """
        try:
            with open(self.heartbeat_file, 'w') as f:
                f.write(datetime.now().isoformat())
            logger.debug(f"시스템 헬스체크 기록: {datetime.now()}")
        except Exception as e:
            logger.error(f"헬스체크 기록 실패: {str(e)}")
    
    def check_last_heartbeat(self) -> Dict:
        """
        마지막 헬스체크 확인
        
        Returns:
            Dict: 시스템 상태 정보
        """
        if not self.heartbeat_file.exists():
            return {
                'status': 'UNKNOWN',
                'last_heartbeat': None,
                'message': '헬스체크 파일 없음 - 시스템이 한 번도 실행되지 않았습니다'
            }
        
        try:
            with open(self.heartbeat_file, 'r') as f:
                last_heartbeat_str = f.read().strip()
                last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
            
            time_diff = datetime.now() - last_heartbeat
            
            if time_diff < timedelta(hours=2):
                status = 'HEALTHY'
                message = '시스템 정상 작동 중'
            elif time_diff < timedelta(hours=24):
                status = 'WARNING'
                message = f'시스템이 {time_diff.seconds // 3600}시간 동안 응답 없음'
            else:
                status = 'CRITICAL'
                message = f'시스템이 {time_diff.days}일 동안 응답 없음'
            
            return {
                'status': status,
                'last_heartbeat': last_heartbeat,
                'time_since_last': time_diff,
                'message': message
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'last_heartbeat': None,
                'message': f'헬스체크 파일 읽기 실패: {str(e)}'
            }
    
    def check_log_files(self, days: int = 7) -> Dict:
        """
        최근 N일간의 로그 파일 존재 여부 확인
        
        Args:
            days (int): 확인할 일수
        
        Returns:
            Dict: 로그 파일 상태 정보
        """
        today = datetime.now()
        missing_dates = []
        existing_dates = []
        
        for i in range(days):
            check_date = today - timedelta(days=i)
            date_str = check_date.strftime('%Y%m%d')
            
            # 주요 로그 파일 확인
            log_files = [
                self.log_dir / f"main_{date_str}.log",
                self.log_dir / f"paper_trader_{date_str}.log",
                self.log_dir / f"scheduler_{date_str}.log"
            ]
            
            if any(f.exists() for f in log_files):
                existing_dates.append(check_date.strftime('%Y-%m-%d'))
            else:
                # 실제 거래일만 누락으로 표시
                if market_calendar.is_trading_day(check_date.date()):
                    missing_dates.append(check_date.strftime('%Y-%m-%d'))
        
        return {
            'total_days_checked': days,
            'existing_dates': existing_dates,
            'missing_dates': missing_dates,
            'missing_count': len(missing_dates),
            'status': 'OK' if len(missing_dates) == 0 else 'WARNING'
        }
    
    def get_system_resources(self) -> Dict:
        """
        시스템 리소스 사용량 확인
        
        Returns:
            Dict: CPU, 메모리, 디스크 사용량 정보
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_usage': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
                'status': 'OK' if cpu_percent < 80 and memory.percent < 80 else 'WARNING'
            }
        except Exception as e:
            logger.error(f"시스템 리소스 확인 실패: {str(e)}")
            return {
                'status': 'ERROR',
                'message': str(e)
            }
    
    def get_process_info(self) -> Dict:
        """
        현재 프로세스 정보 확인
        
        Returns:
            Dict: 프로세스 정보
        """
        try:
            process = psutil.Process()
            
            return {
                'pid': process.pid,
                'cpu_percent': process.cpu_percent(),
                'memory_mb': process.memory_info().rss / (1024**2),
                'threads': process.num_threads(),
                'create_time': datetime.fromtimestamp(process.create_time()),
                'status': process.status()
            }
        except Exception as e:
            logger.error(f"프로세스 정보 확인 실패: {str(e)}")
            return {
                'status': 'ERROR',
                'message': str(e)
            }
    
    def generate_health_report(self) -> str:
        """
        종합 시스템 상태 리포트 생성
        
        Returns:
            str: 상태 리포트 텍스트
        """
        report = []
        report.append("=" * 60)
        report.append("시스템 상태 리포트")
        report.append("=" * 60)
        report.append(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 헬스체크 상태
        heartbeat = self.check_last_heartbeat()
        report.append("📍 시스템 헬스체크:")
        report.append(f"  상태: {heartbeat['status']}")
        if heartbeat['last_heartbeat']:
            report.append(f"  마지막 응답: {heartbeat['last_heartbeat'].strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"  메시지: {heartbeat['message']}")
        report.append("")
        
        # 로그 파일 상태
        log_status = self.check_log_files(days=7)
        report.append("📁 로그 파일 상태 (최근 7일):")
        report.append(f"  상태: {log_status['status']}")
        report.append(f"  로그 존재: {len(log_status['existing_dates'])}일")
        report.append(f"  로그 누락: {len(log_status['missing_dates'])}일")
        if log_status['missing_dates']:
            report.append(f"  누락 날짜: {', '.join(log_status['missing_dates'])}")
        report.append("")
        
        # 시스템 리소스
        resources = self.get_system_resources()
        report.append("💻 시스템 리소스:")
        if resources['status'] != 'ERROR':
            report.append(f"  CPU 사용률: {resources['cpu_usage']:.1f}%")
            report.append(f"  메모리 사용률: {resources['memory_usage']:.1f}%")
            report.append(f"  메모리 가용: {resources['memory_available_gb']:.1f}GB")
            report.append(f"  디스크 사용률: {resources['disk_usage']:.1f}%")
            report.append(f"  디스크 여유: {resources['disk_free_gb']:.1f}GB")
        else:
            report.append(f"  오류: {resources['message']}")
        report.append("")
        
        # 프로세스 정보
        process_info = self.get_process_info()
        report.append("🔄 프로세스 정보:")
        if process_info.get('status') != 'ERROR':
            report.append(f"  PID: {process_info['pid']}")
            report.append(f"  CPU: {process_info['cpu_percent']:.1f}%")
            report.append(f"  메모리: {process_info['memory_mb']:.1f}MB")
            report.append(f"  스레드: {process_info['threads']}")
            report.append(f"  시작 시간: {process_info['create_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            report.append(f"  오류: {process_info['message']}")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def save_health_report(self):
        """상태 리포트를 파일로 저장"""
        report = self.generate_health_report()
        report_file = self.log_dir / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"상태 리포트 저장: {report_file}")
            print(report)  # 콘솔에도 출력
        except Exception as e:
            logger.error(f"상태 리포트 저장 실패: {str(e)}")

# 전역 모니터 인스턴스
system_monitor = SystemMonitor()


#!/usr/bin/env python3
"""
서버 상태 모니터링 및 헬스체크
"""

import requests
import psutil
import time
import logging
from datetime import datetime
import subprocess
import os

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/aitrader/logs/health_check.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HealthChecker:
    """헬스체크 클래스"""
    
    def __init__(self):
        """초기화"""
        self.dashboard_url = "http://localhost:5000"
        self.alert_thresholds = {
            'cpu_usage': 80,      # CPU 사용률 80%
            'memory_usage': 85,   # 메모리 사용률 85%
            'disk_usage': 90,     # 디스크 사용률 90%
            'response_time': 5.0  # 응답 시간 5초
        }
    
    def check_system_resources(self):
        """시스템 리소스 체크"""
        try:
            # CPU 사용률
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            
            # 로그 기록
            logger.info(f"시스템 리소스 - CPU: {cpu_usage:.1f}%, Memory: {memory_usage:.1f}%, Disk: {disk_usage:.1f}%")
            
            # 임계값 체크
            alerts = []
            if cpu_usage > self.alert_thresholds['cpu_usage']:
                alerts.append(f"높은 CPU 사용률: {cpu_usage:.1f}%")
            
            if memory_usage > self.alert_thresholds['memory_usage']:
                alerts.append(f"높은 메모리 사용률: {memory_usage:.1f}%")
            
            if disk_usage > self.alert_thresholds['disk_usage']:
                alerts.append(f"높은 디스크 사용률: {disk_usage:.1f}%")
            
            return {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage,
                'alerts': alerts
            }
            
        except Exception as e:
            logger.error(f"시스템 리소스 체크 오류: {str(e)}")
            return None
    
    def check_dashboard_health(self):
        """대시보드 헬스체크"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.dashboard_url}/api/portfolio", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                logger.info(f"대시보드 응답 시간: {response_time:.2f}초")
                
                if response_time > self.alert_thresholds['response_time']:
                    return {
                        'status': 'slow',
                        'response_time': response_time,
                        'alerts': [f"느린 응답 시간: {response_time:.2f}초"]
                    }
                else:
                    return {
                        'status': 'healthy',
                        'response_time': response_time,
                        'alerts': []
                    }
            else:
                return {
                    'status': 'error',
                    'response_time': response_time,
                    'alerts': [f"HTTP 오류: {response.status_code}"]
                }
                
        except requests.exceptions.Timeout:
            logger.error("대시보드 응답 시간 초과")
            return {
                'status': 'timeout',
                'response_time': None,
                'alerts': ["대시보드 응답 시간 초과"]
            }
        except Exception as e:
            logger.error(f"대시보드 헬스체크 오류: {str(e)}")
            return {
                'status': 'error',
                'response_time': None,
                'alerts': [f"대시보드 연결 오류: {str(e)}"]
            }
    
    def check_supervisor_services(self):
        """Supervisor 서비스 체크"""
        try:
            # Supervisor 상태 확인
            result = subprocess.run(['supervisorctl', 'status'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                services = {}
                alerts = []
                
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            service_name = parts[0]
                            status = parts[1]
                            services[service_name] = status
                            
                            if status not in ['RUNNING']:
                                alerts.append(f"서비스 {service_name} 상태: {status}")
                
                logger.info(f"Supervisor 서비스 상태: {services}")
                
                return {
                    'services': services,
                    'alerts': alerts
                }
            else:
                logger.error(f"Supervisor 상태 확인 실패: {result.stderr}")
                return {
                    'services': {},
                    'alerts': ["Supervisor 상태 확인 실패"]
                }
                
        except Exception as e:
            logger.error(f"Supervisor 서비스 체크 오류: {str(e)}")
            return {
                'services': {},
                'alerts': [f"Supervisor 체크 오류: {str(e)}"]
            }
    
    def check_log_files(self):
        """로그 파일 체크"""
        try:
            log_dir = '/opt/aitrader/logs'
            alerts = []
            
            if os.path.exists(log_dir):
                for filename in os.listdir(log_dir):
                    if filename.endswith('.log'):
                        filepath = os.path.join(log_dir, filename)
                        file_size = os.path.getsize(filepath)
                        
                        # 로그 파일 크기 체크 (100MB 이상)
                        if file_size > 100 * 1024 * 1024:
                            alerts.append(f"큰 로그 파일: {filename} ({file_size / 1024 / 1024:.1f}MB)")
            
            return {
                'alerts': alerts
            }
            
        except Exception as e:
            logger.error(f"로그 파일 체크 오류: {str(e)}")
            return {
                'alerts': [f"로그 파일 체크 오류: {str(e)}"]
            }
    
    def run_health_check(self):
        """전체 헬스체크 실행"""
        logger.info("=== 헬스체크 시작 ===")
        
        # 시스템 리소스 체크
        system_health = self.check_system_resources()
        
        # 대시보드 헬스체크
        dashboard_health = self.check_dashboard_health()
        
        # Supervisor 서비스 체크
        supervisor_health = self.check_supervisor_services()
        
        # 로그 파일 체크
        log_health = self.check_log_files()
        
        # 전체 알림 수집
        all_alerts = []
        if system_health and system_health.get('alerts'):
            all_alerts.extend(system_health['alerts'])
        if dashboard_health and dashboard_health.get('alerts'):
            all_alerts.extend(dashboard_health['alerts'])
        if supervisor_health and supervisor_health.get('alerts'):
            all_alerts.extend(supervisor_health['alerts'])
        if log_health and log_health.get('alerts'):
            all_alerts.extend(log_health['alerts'])
        
        # 결과 요약
        if all_alerts:
            logger.warning(f"발견된 문제: {len(all_alerts)}개")
            for alert in all_alerts:
                logger.warning(f"  - {alert}")
        else:
            logger.info("모든 체크 통과 - 시스템 정상")
        
        logger.info("=== 헬스체크 완료 ===")
        
        return {
            'timestamp': datetime.now().isoformat(),
            'system_health': system_health,
            'dashboard_health': dashboard_health,
            'supervisor_health': supervisor_health,
            'log_health': log_health,
            'total_alerts': len(all_alerts),
            'alerts': all_alerts
        }

def main():
    """메인 함수"""
    health_checker = HealthChecker()
    
    # 헬스체크 실행
    result = health_checker.run_health_check()
    
    # 결과를 JSON 파일로 저장
    import json
    result_file = '/opt/aitrader/logs/health_check_result.json'
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    # 알림이 있으면 종료 코드 1 반환
    if result['total_alerts'] > 0:
        exit(1)
    else:
        exit(0)

if __name__ == '__main__':
    main()


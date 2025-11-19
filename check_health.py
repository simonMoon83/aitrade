#!/usr/bin/env python3
"""
시스템 상태 확인 스크립트
"""

from utils.system_monitor import system_monitor

if __name__ == "__main__":
    print("\n시스템 상태를 확인하는 중...\n")
    system_monitor.save_health_report()





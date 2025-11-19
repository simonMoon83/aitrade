"""
암호화폐 백테스트 실행 스크립트
Usage: python scripts/backtest_crypto.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_crypto_backtest import run_crypto_backtest

if __name__ == "__main__":
    print("🚀 암호화폐 백테스트 시작...")
    print("="*80)
    run_crypto_backtest()
    print("="*80)
    print("✅ 백테스트 완료! 결과는 'results/backtests' 폴더를 확인하세요.")


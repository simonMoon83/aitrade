"""
실전 투자 실행 스크립트
Usage: python scripts/live_trade.py

⚠️ 주의: 실제 돈으로 거래합니다! Paper Trading으로 먼저 충분히 테스트하세요!
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("="*80)
    print("⚠️  경고: 실전 투자 모드")
    print("="*80)
    print("이 모드는 실제 돈으로 거래를 실행합니다!")
    print("")
    print("실전 투자 전 체크리스트:")
    print("✓ Paper Trading으로 최소 1개월 이상 테스트했습니까?")
    print("✓ 실전 데이터를 분석하고 전략을 최적화했습니까?")
    print("✓ 소액($100~1,000)으로 시작하시겠습니까?")
    print("✓ 손실을 감당할 수 있는 금액입니까?")
    print("✓ Alpaca API 키가 실전용(Live)으로 설정되어 있습니까?")
    print("")
    print("="*80)
    
    response = input("정말 실전 투자를 시작하시겠습니까? (yes/no): ")
    
    if response.lower() != 'yes':
        print("취소되었습니다.")
        return
    
    response2 = input("다시 한번 확인합니다. 실제 돈으로 거래합니다! (YES 입력): ")
    
    if response2 != 'YES':
        print("취소되었습니다.")
        return
    
    print("\n실전 투자는 아직 구현되지 않았습니다.")
    print("Paper Trading으로 충분히 테스트한 후,")
    print("config.py에서 ALPACA_BASE_URL을 실전용으로 변경하고")
    print("live_trader.py를 구현해야 합니다.")
    print("\n현재는 Paper Trading을 사용하세요:")
    print("python scripts/paper_trade.py --dashboard")

if __name__ == "__main__":
    main()


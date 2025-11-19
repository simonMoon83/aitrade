"""
일일 레포트 생성기
Gemini API를 사용하여 AI 기반 일일 거래 분석 레포트 생성
"""

import os
import json
from datetime import datetime, date
from typing import Dict, List, Optional
import pandas as pd

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from config import *
from utils.logger import setup_logger

logger = setup_logger("daily_report_generator")


class DailyReportGenerator:
    """일일 레포트 생성기 클래스"""

    def __init__(self):
        """초기화"""
        self.api_key = GEMINI_API_KEY
        self.model_name = GEMINI_MODEL
        self.reports_dir = REPORTS_SAVE_DIR
        self.model = None

        # 레포트 디렉토리 생성
        os.makedirs(self.reports_dir, exist_ok=True)

        # Gemini API 초기화
        if not GEMINI_AVAILABLE:
            logger.warning("google-generativeai 패키지가 설치되지 않았습니다. pip install google-generativeai")
            return

        if not self.api_key:
            logger.warning("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일에 API 키를 추가하세요")
            return

        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"Gemini API 초기화 완료 (모델: {self.model_name})")
        except Exception as e:
            logger.error(f"Gemini API 초기화 실패: {str(e)}")

    def generate_daily_report(self,
                            portfolio_data: Dict,
                            trades: List[Dict],
                            signals: List[Dict],
                            market_data: Optional[Dict] = None,
                            report_date: Optional[date] = None) -> Dict:
        """
        일일 레포트 생성

        Args:
            portfolio_data (Dict): 포트폴리오 데이터
                - portfolio_value: 포트폴리오 가치
                - cash: 현금
                - positions: 보유 포지션
                - total_return: 총 수익률
                - daily_return: 일일 수익률
            trades (List[Dict]): 당일 거래 내역
            signals (List[Dict]): 당일 신호 내역
            market_data (Optional[Dict]): 시장 데이터
            report_date (Optional[date]): 레포트 날짜 (None이면 오늘)

        Returns:
            Dict: 생성된 레포트 정보
                - success: 성공 여부
                - report_path: 레포트 파일 경로
                - report_content: 레포트 내용
                - error: 에러 메시지 (실패 시)
        """
        if report_date is None:
            report_date = date.today()

        logger.info(f"일일 레포트 생성 시작: {report_date}")

        # Gemini API 사용 불가 시 기본 레포트 생성
        if not self.model:
            logger.warning("Gemini API를 사용할 수 없습니다. 기본 레포트를 생성합니다")
            return self._generate_basic_report(portfolio_data, trades, signals, market_data, report_date)

        try:
            # 프롬프트 생성
            prompt = self._create_prompt(portfolio_data, trades, signals, market_data, report_date)

            # Gemini API 호출
            logger.info("Gemini API 호출 중...")
            response = self.model.generate_content(prompt)
            report_content = response.text

            # 레포트 저장
            report_path = self._save_report(report_content, report_date)

            # 메타데이터 저장
            metadata = {
                'date': report_date.isoformat(),
                'portfolio_value': portfolio_data.get('portfolio_value', 0),
                'total_return': portfolio_data.get('total_return', 0),
                'daily_return': portfolio_data.get('daily_return', 0),
                'trades_count': len(trades),
                'signals_count': len(signals),
                'generated_at': datetime.now().isoformat()
            }
            self._save_metadata(metadata, report_date)

            logger.info(f"일일 레포트 생성 완료: {report_path}")

            return {
                'success': True,
                'report_path': report_path,
                'report_content': report_content,
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"일일 레포트 생성 실패: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _create_prompt(self,
                      portfolio_data: Dict,
                      trades: List[Dict],
                      signals: List[Dict],
                      market_data: Optional[Dict],
                      report_date: date) -> str:
        """AI 레포트 생성용 프롬프트 생성"""

        prompt = f"""
당신은 전문 주식 트레이더이자 금융 분석가입니다. 다음 데이터를 바탕으로 {report_date.strftime('%Y년 %m월 %d일')} 일일 거래 레포트를 작성해주세요.

## 📊 포트폴리오 현황
- 포트폴리오 가치: ${portfolio_data.get('portfolio_value', 0):,.2f}
- 현금: ${portfolio_data.get('cash', 0):,.2f}
- 총 수익률: {portfolio_data.get('total_return', 0):.2%}
- 일일 수익률: {portfolio_data.get('daily_return', 0):.2%}

## 📈 보유 포지션
{self._format_positions(portfolio_data.get('positions', {}))}

## 💰 당일 거래 내역 ({len(trades)}건)
{self._format_trades(trades)}

## 🎯 당일 신호 내역 ({len(signals)}건)
{self._format_signals(signals)}

## 🌍 시장 상황
{self._format_market_data(market_data) if market_data else "시장 데이터 없음"}

---

위 데이터를 분석하여 다음 형식으로 레포트를 작성해주세요:

# 📋 일일 거래 레포트 - {report_date.strftime('%Y년 %m월 %d일')}

## 1. 📊 요약 (Executive Summary)
- 오늘의 핵심 성과를 3-5줄로 요약
- 주요 수치와 성과 하이라이트

## 2. 💼 포트폴리오 분석
- 포트폴리오 가치 변화 분석
- 수익률 평가 (일일/누적)
- 현금 보유 비율 및 적정성

## 3. 📈 보유 종목 분석
- 각 보유 종목의 현황 및 평가
- 수익/손실 종목 분석
- 포지션별 리스크 평가

## 4. 💱 거래 분석
- 당일 체결된 거래 분석
- 매수/매도 결정의 적절성 평가
- 거래 타이밍 및 가격 분석

## 5. 🎯 신호 분석
- 발생한 매매 신호 분석
- 신호의 신뢰도 및 정확도 평가
- 미체결 신호에 대한 검토

## 6. 🔍 시장 환경 분석
- 오늘 시장 전반적인 흐름
- 주요 종목들의 움직임
- 시장 심리 및 변동성

## 7. ⚠️ 리스크 및 주의사항
- 현재 포트폴리오의 리스크 요인
- 주의해야 할 종목이나 상황
- 손절/익절 대상 검토

## 8. 💡 내일 전략 제안
- 내일 주목해야 할 종목
- 추천 매매 전략
- 포트폴리오 조정 제안

## 9. 📌 결론
- 오늘 거래의 총평
- 전략 실행 평가 (A/B/C/D/F 등급)
- 개선이 필요한 부분

---

**작성 지침:**
1. 한국어로 작성
2. 데이터에 기반한 객관적 분석
3. 구체적인 수치와 근거 제시
4. 실행 가능한 제안
5. 전문적이면서도 이해하기 쉬운 표현
6. 긍정적 측면과 개선점 균형있게 서술
"""

        return prompt

    def _format_positions(self, positions: Dict) -> str:
        """보유 포지션 포맷팅"""
        if not positions:
            return "보유 포지션 없음"

        result = []
        for symbol, pos in positions.items():
            quantity = pos.get('quantity', 0)
            avg_price = pos.get('avg_price', 0)
            current_price = pos.get('current_price', 0)
            unrealized_pnl = pos.get('unrealized_pnl', 0)
            pnl_pct = (current_price - avg_price) / avg_price if avg_price > 0 else 0

            result.append(
                f"- {symbol}: {quantity}주 @ ${avg_price:.2f} "
                f"(현재: ${current_price:.2f}, 손익: ${unrealized_pnl:.2f} / {pnl_pct:.2%})"
            )

        return "\n".join(result)

    def _format_trades(self, trades: List[Dict]) -> str:
        """거래 내역 포맷팅"""
        if not trades:
            return "당일 거래 없음"

        result = []
        for trade in trades:
            action = trade.get('action', 'N/A')
            symbol = trade.get('symbol', 'N/A')
            quantity = trade.get('quantity', 0)
            price = trade.get('price', 0)
            timestamp = trade.get('timestamp', 'N/A')

            result.append(
                f"- [{timestamp}] {action} {quantity}주 {symbol} @ ${price:.2f}"
            )

        return "\n".join(result)

    def _format_signals(self, signals: List[Dict]) -> str:
        """신호 내역 포맷팅"""
        if not signals:
            return "당일 신호 없음"

        result = []
        for signal in signals:
            sig_type = signal.get('signal', 'N/A')
            symbol = signal.get('symbol', 'N/A')
            confidence = signal.get('confidence', 0)
            price = signal.get('price', 0)
            reasons = signal.get('reasons', [])

            reason_str = ', '.join(reasons[:3]) if reasons else '이유 없음'

            result.append(
                f"- {sig_type} {symbol} (신뢰도: {confidence:.1%}, 가격: ${price:.2f})\n"
                f"  근거: {reason_str}"
            )

        return "\n".join(result)

    def _format_market_data(self, market_data: Dict) -> str:
        """시장 데이터 포맷팅 (뉴스, 섹터, 거시경제 포함)"""
        if not market_data:
            return "시장 데이터 없음"

        result = []
        
        # 거시경제 환경
        if 'macro_environment' in market_data:
            macro = market_data['macro_environment']
            result.append(f"### 🌍 거시경제 환경")
            result.append(f"- 환경 평가: {macro.get('environment', 'N/A')}")
            result.append(f"- 종합 점수: {macro.get('score', 0):+d}/10")
            
            signals = macro.get('signals', [])
            if signals:
                result.append(f"- 주요 신호: {', '.join(signals[:5])}")
            
            indicators = macro.get('indicators', {})
            if indicators:
                result.append(f"- 10년 국채 수익률: {indicators.get('treasury_10y', 0):.2f}%")
                result.append(f"- VIX 지수: {indicators.get('vix', 0):.1f}")
                if 'unemployment_rate' in indicators:
                    result.append(f"- 실업률: {indicators.get('unemployment_rate', 0):.1f}%")
            result.append("")
        
        # 섹터 순환
        if 'sector_rotation' in market_data:
            sector = market_data['sector_rotation']
            result.append(f"### 🏢 섹터 순환")
            result.append(f"- 시장 국면: {sector.get('market_phase', 'N/A')}")
            
            top_3 = sector.get('top_3', [])
            if top_3:
                result.append(f"- 강세 섹터: {', '.join(top_3)}")
            
            bottom_3 = sector.get('bottom_3', [])
            if bottom_3:
                result.append(f"- 약세 섹터: {', '.join(bottom_3)}")
            result.append("")
        
        # 뉴스 요약
        if 'news_summary' in market_data:
            news_summary = market_data['news_summary']
            result.append(f"### 📰 뉴스 감성 분석")
            
            for symbol, news_data in list(news_summary.items())[:5]:  # 상위 5개 종목만
                if isinstance(news_data, dict):
                    trend = news_data.get('trend', 'NEUTRAL')
                    score = news_data.get('score', 0)
                    count = news_data.get('news_count', 0)
                    result.append(f"- {symbol}: {trend} (점수: {score:+.2f}, 뉴스: {count}개)")
            result.append("")
        
        # 기타 시장 데이터
        other_data = {k: v for k, v in market_data.items() 
                     if k not in ['macro_environment', 'sector_rotation', 'news_summary']}
        if other_data:
            result.append(f"### 📊 기타 시장 정보")
            for key, value in other_data.items():
                result.append(f"- {key}: {value}")

        return "\n".join(result) if result else "시장 데이터 없음"

    def _save_report(self, content: str, report_date: date) -> str:
        """레포트 저장"""
        filename = f"daily_report_{report_date.strftime('%Y%m%d')}.md"
        filepath = os.path.join(self.reports_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def _save_metadata(self, metadata: Dict, report_date: date):
        """메타데이터 저장"""
        filename = f"metadata_{report_date.strftime('%Y%m%d')}.json"
        filepath = os.path.join(self.reports_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def _generate_basic_report(self,
                              portfolio_data: Dict,
                              trades: List[Dict],
                              signals: List[Dict],
                              market_data: Optional[Dict],
                              report_date: date) -> Dict:
        """기본 레포트 생성 (Gemini API 사용 불가 시)"""

        content = f"""# 📋 일일 거래 레포트 - {report_date.strftime('%Y년 %m월 %d일')}

## 📊 포트폴리오 현황
- 포트폴리오 가치: ${portfolio_data.get('portfolio_value', 0):,.2f}
- 현금: ${portfolio_data.get('cash', 0):,.2f}
- 총 수익률: {portfolio_data.get('total_return', 0):.2%}
- 일일 수익률: {portfolio_data.get('daily_return', 0):.2%}

## 📈 보유 포지션
{self._format_positions(portfolio_data.get('positions', {}))}

## 💰 당일 거래 내역 ({len(trades)}건)
{self._format_trades(trades)}

## 🎯 당일 신호 내역 ({len(signals)}건)
{self._format_signals(signals)}

---
*이 레포트는 기본 템플릿으로 생성되었습니다. AI 분석을 활성화하려면 Gemini API 키를 설정하세요.*
"""

        report_path = self._save_report(content, report_date)

        metadata = {
            'date': report_date.isoformat(),
            'portfolio_value': portfolio_data.get('portfolio_value', 0),
            'total_return': portfolio_data.get('total_return', 0),
            'daily_return': portfolio_data.get('daily_return', 0),
            'trades_count': len(trades),
            'signals_count': len(signals),
            'generated_at': datetime.now().isoformat(),
            'ai_generated': False
        }
        self._save_metadata(metadata, report_date)

        return {
            'success': True,
            'report_path': report_path,
            'report_content': content,
            'metadata': metadata,
            'ai_generated': False
        }

    def get_report(self, report_date: Optional[date] = None) -> Optional[Dict]:
        """
        저장된 레포트 조회

        Args:
            report_date (Optional[date]): 조회할 날짜 (None이면 오늘)

        Returns:
            Optional[Dict]: 레포트 정보 (없으면 None)
        """
        if report_date is None:
            report_date = date.today()

        report_filename = f"daily_report_{report_date.strftime('%Y%m%d')}.md"
        report_path = os.path.join(self.reports_dir, report_filename)

        metadata_filename = f"metadata_{report_date.strftime('%Y%m%d')}.json"
        metadata_path = os.path.join(self.reports_dir, metadata_filename)

        if not os.path.exists(report_path):
            return None

        try:
            # 레포트 내용 읽기
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 메타데이터 읽기
            metadata = {}
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

            return {
                'date': report_date.isoformat(),
                'content': content,
                'metadata': metadata,
                'path': report_path
            }

        except Exception as e:
            logger.error(f"레포트 조회 실패: {str(e)}")
            return None

    def list_reports(self, limit: int = 30) -> List[Dict]:
        """
        레포트 목록 조회

        Args:
            limit (int): 조회할 최대 개수

        Returns:
            List[Dict]: 레포트 목록
        """
        reports = []

        try:
            files = os.listdir(self.reports_dir)
            metadata_files = [f for f in files if f.startswith('metadata_') and f.endswith('.json')]
            metadata_files.sort(reverse=True)  # 최신순

            for filename in metadata_files[:limit]:
                filepath = os.path.join(self.reports_dir, filename)

                with open(filepath, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                reports.append(metadata)

            return reports

        except Exception as e:
            logger.error(f"레포트 목록 조회 실패: {str(e)}")
            return []


# 전역 인스턴스
report_generator = DailyReportGenerator()

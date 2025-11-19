"""
뉴스 감성 분석 모듈
yfinance와 Finnhub를 사용하여 뉴스 수집 및 감성 분석
"""

import yfinance as yf
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time

# Finnhub 임포트 (선택사항)
try:
    import finnhub
    FINNHUB_AVAILABLE = True
except ImportError:
    FINNHUB_AVAILABLE = False

# FinBERT 임포트 (로컬 백업용)
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from config import *
from utils.logger import setup_logger

logger = setup_logger("news_sentiment")


class NewsSentimentAnalyzer:
    """뉴스 감성 분석 클래스"""
    
    def __init__(self, finnhub_api_key: str = "", use_local_model: bool = USE_LOCAL_FINBERT):
        """
        초기화
        
        Args:
            finnhub_api_key (str): Finnhub API 키
            use_local_model (bool): 로컬 FinBERT 모델 사용 여부
        """
        self.finnhub_api_key = finnhub_api_key
        self.use_local_model = use_local_model
        self.finnhub_client = None
        self.sentiment_model = None
        
        # 캐시
        self.cache = {}
        self.cache_duration = NEWS_CACHE_HOURS * 3600  # 초 단위
        
        # Finnhub 클라이언트 초기화
        if FINNHUB_AVAILABLE and finnhub_api_key:
            try:
                self.finnhub_client = finnhub.Client(api_key=finnhub_api_key)
                logger.info("Finnhub 클라이언트 초기화 완료")
            except Exception as e:
                logger.warning(f"Finnhub 초기화 실패: {str(e)}")
                self.finnhub_client = None
        else:
            if not FINNHUB_AVAILABLE:
                logger.warning("finnhub-python 패키지가 설치되지 않았습니다")
            elif not finnhub_api_key:
                logger.info("Finnhub API 키가 설정되지 않았습니다 (yfinance만 사용)")
        
        # 로컬 FinBERT 모델 초기화 (백업용)
        if use_local_model and TRANSFORMERS_AVAILABLE:
            try:
                logger.info("FinBERT 모델 로딩 중... (처음 실행 시 시간이 걸릴 수 있습니다)")
                self.sentiment_model = pipeline(
                    "sentiment-analysis",
                    model="ProsusAI/finbert",
                    max_length=512,
                    truncation=True
                )
                logger.info("FinBERT 모델 로딩 완료")
            except Exception as e:
                logger.warning(f"FinBERT 모델 로딩 실패: {str(e)}")
                self.sentiment_model = None
        elif not TRANSFORMERS_AVAILABLE:
            logger.warning("transformers 패키지가 설치되지 않았습니다")
    
    def get_sentiment_score(self, symbol: str) -> Dict:
        """
        종목의 뉴스 감성 점수 가져오기 (캐시 포함)
        
        Args:
            symbol (str): 종목 심볼
            
        Returns:
            Dict: {
                'score': -1~1 감성 점수,
                'trend': 'VERY_POSITIVE'|'POSITIVE'|'NEUTRAL'|'NEGATIVE'|'VERY_NEGATIVE',
                'news_count': 뉴스 개수,
                'buzz_ratio': 뉴스 급증 비율,
                'top_headlines': 최근 헤드라인 리스트,
                'source': 'finnhub'|'yfinance'|'none'
            }
        """
        # 캐시 확인
        if symbol in self.cache:
            cached_time, cached_data = self.cache[symbol]
            if (datetime.now() - cached_time).total_seconds() < self.cache_duration:
                logger.debug(f"[{symbol}] 캐시된 뉴스 감성 사용")
                return cached_data
        
        # 새로 가져오기
        try:
            # 1. Finnhub 시도 (우선순위)
            if self.finnhub_client:
                result = self._fetch_finnhub_sentiment(symbol)
                if result['news_count'] > 0:
                    self.cache[symbol] = (datetime.now(), result)
                    return result
            
            # 2. yfinance 폴백
            result = self._fetch_yfinance_sentiment(symbol)
            self.cache[symbol] = (datetime.now(), result)
            return result
            
        except Exception as e:
            logger.error(f"[{symbol}] 뉴스 감성 분석 실패: {str(e)}")
            return self._get_neutral_sentiment()
    
    def _fetch_finnhub_sentiment(self, symbol: str) -> Dict:
        """
        Finnhub에서 감성 점수 가져오기
        
        Args:
            symbol (str): 종목 심볼
            
        Returns:
            Dict: 감성 분석 결과
        """
        try:
            # 뉴스 감성 지표 가져오기
            sentiment_data = self.finnhub_client.news_sentiment(symbol)
            
            if not sentiment_data:
                raise Exception("Finnhub에서 데이터를 가져오지 못했습니다")
            
            # 감성 점수 추출
            company_score = sentiment_data.get('companyNewsScore', 0)
            buzz_info = sentiment_data.get('buzz', {})
            sentiment_info = sentiment_data.get('sentiment', {})
            
            # 뉴스 개수 및 버즈 비율
            news_count = buzz_info.get('articlesInLastWeek', 0)
            buzz_ratio = buzz_info.get('buzz', 1.0)
            
            # 강세/약세 비율
            bullish_pct = sentiment_info.get('bullishPercent', 0.5)
            bearish_pct = sentiment_info.get('bearishPercent', 0.5)
            
            # 최근 뉴스 헤드라인 가져오기
            end_date = datetime.now()
            start_date = end_date - timedelta(days=NEWS_LOOKBACK_DAYS)
            
            news_list = self.finnhub_client.company_news(
                symbol,
                _from=start_date.strftime('%Y-%m-%d'),
                to=end_date.strftime('%Y-%m-%d')
            )
            
            top_headlines = [
                {
                    'title': article.get('headline', ''),
                    'source': article.get('source', ''),
                    'datetime': datetime.fromtimestamp(article.get('datetime', 0)).strftime('%Y-%m-%d %H:%M')
                }
                for article in news_list[:5]
            ]
            
            # 트렌드 분류
            trend = self._classify_trend(company_score, bullish_pct)
            
            logger.info(f"[{symbol}] Finnhub 감성: {trend} (점수: {company_score:.3f}, "
                       f"뉴스: {news_count}개, 버즈: {buzz_ratio:.2f}x)")
            
            return {
                'score': company_score,
                'trend': trend,
                'news_count': news_count,
                'buzz_ratio': buzz_ratio,
                'bullish_percent': bullish_pct,
                'bearish_percent': bearish_pct,
                'top_headlines': top_headlines,
                'source': 'finnhub'
            }
            
        except Exception as e:
            logger.warning(f"[{symbol}] Finnhub 감성 분석 실패: {str(e)}, yfinance로 폴백")
            # Finnhub 실패 시 예외를 발생시켜 yfinance로 넘어가게 함
            raise

    def _fetch_yfinance_sentiment(self, symbol: str) -> Dict:
        """
        yfinance에서 뉴스 가져와서 감성 분석
        
        Args:
            symbol (str): 종목 심볼
            
        Returns:
            Dict: 감성 분석 결과
        """
        try:
            # yfinance는 간헐적으로 실패할 수 있으므로 중립 처리
            stock = yf.Ticker(symbol)
            try:
                news = stock.news
            except Exception as e:
                logger.warning(f"[{symbol}] yfinance 뉴스 데이터 접근 실패: {str(e)}")
                return self._get_neutral_sentiment()
            
            if not news:
                logger.info(f"[{symbol}] yfinance에서 뉴스를 찾지 못했습니다")
                return self._get_neutral_sentiment()
            
            # 최근 N일 뉴스만 필터링
            cutoff_time = (datetime.now() - timedelta(days=NEWS_LOOKBACK_DAYS)).timestamp()
            recent_news = [
                article for article in news
                if article.get('providerPublishTime', 0) > cutoff_time
            ]
            
            if not recent_news:
                recent_news = news[:10]  # 최소한 최근 10개
            
            # 헤드라인 + 요약으로 감성 분석
            sentiments = []
            top_headlines = []
            
            for article in recent_news[:10]:
                title = article.get('title', '')
                summary = article.get('summary', '')
                text = f"{title}. {summary}" if summary else title
                
                # FinBERT로 분석 (사용 가능한 경우)
                if self.sentiment_model:
                    score = self._analyze_with_finbert(text)
                else:
                    # 간단한 키워드 기반 감성 (백업)
                    score = self._simple_sentiment_analysis(text)
                
                sentiments.append(score)
                
                # 상위 헤드라인 저장
                if len(top_headlines) < 5:
                    pub_time = datetime.fromtimestamp(article.get('providerPublishTime', 0))
                    top_headlines.append({
                        'title': title,
                        'source': article.get('publisher', 'Unknown'),
                        'datetime': pub_time.strftime('%Y-%m-%d %H:%M')
                    })
            
            # 평균 감성 점수 계산
            if sentiments:
                avg_score = sum(sentiments) / len(sentiments)
            else:
                avg_score = 0.0
            
            # 트렌드 분류
            trend = self._classify_trend_from_score(avg_score)
            
            logger.info(f"[{symbol}] yfinance 감성: {trend} (점수: {avg_score:.3f}, 뉴스: {len(sentiments)}개)")
            
            return {
                'score': avg_score,
                'trend': trend,
                'news_count': len(sentiments),
                'buzz_ratio': 1.0,  # yfinance는 버즈 비율 없음
                'bullish_percent': (avg_score + 1) / 2,  # -1~1을 0~1로 변환
                'bearish_percent': (1 - avg_score) / 2,
                'top_headlines': top_headlines,
                'source': 'yfinance'
            }
            
        except Exception as e:
            logger.error(f"[{symbol}] yfinance 뉴스 분석 실패: {str(e)}")
            return self._get_neutral_sentiment()
    
    def _analyze_with_finbert(self, text: str) -> float:
        """
        FinBERT 모델로 텍스트 감성 분석
        
        Args:
            text (str): 분석할 텍스트
            
        Returns:
            float: -1 ~ 1 사이의 감성 점수
        """
        try:
            if not self.sentiment_model:
                return 0.0
            
            # FinBERT 분석 (최대 512 토큰)
            result = self.sentiment_model(text[:512])[0]
            
            label = result['label'].lower()
            score = result['score']
            
            # positive/negative/neutral을 -1~1로 변환
            if 'positive' in label:
                return score
            elif 'negative' in label:
                return -score
            else:  # neutral
                return 0.0
                
        except Exception as e:
            logger.debug(f"FinBERT 분석 실패: {str(e)}")
            return 0.0
    
    def _simple_sentiment_analysis(self, text: str) -> float:
        """
        간단한 키워드 기반 감성 분석 (백업용)
        
        Args:
            text (str): 분석할 텍스트
            
        Returns:
            float: -1 ~ 1 사이의 감성 점수
        """
        text_lower = text.lower()
        
        # 긍정 키워드
        positive_words = [
            'surge', 'soar', 'rally', 'gain', 'rise', 'jump', 'climbs', 'beats',
            'strong', 'growth', 'profit', 'positive', 'bullish', 'upgrade', 'buy',
            'record', 'high', 'outperform', 'success', 'boom', 'breakthrough'
        ]
        
        # 부정 키워드
        negative_words = [
            'fall', 'drop', 'plunge', 'decline', 'loss', 'down', 'weak', 'negative',
            'bearish', 'downgrade', 'sell', 'low', 'underperform', 'crisis', 'concern',
            'risk', 'fear', 'crash', 'slump', 'miss', 'disappoint'
        ]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total_words = positive_count + negative_count
        
        if total_words == 0:
            return 0.0
        
        # -1 ~ 1로 정규화
        score = (positive_count - negative_count) / max(total_words, 1)
        return max(-1.0, min(1.0, score))
    
    def _classify_trend(self, score: float, bullish_pct: float = 0.5) -> str:
        """
        감성 점수와 강세 비율로 트렌드 분류
        
        Args:
            score (float): Finnhub 감성 점수 (-1 ~ 1)
            bullish_pct (float): 강세 비율 (0 ~ 1)
            
        Returns:
            str: 트렌드 ('VERY_POSITIVE', 'POSITIVE', 'NEUTRAL', 'NEGATIVE', 'VERY_NEGATIVE')
        """
        # Finnhub 점수는 일반적으로 0.4~0.6 범위
        if score > 0.7 or bullish_pct > 0.75:
            return 'VERY_POSITIVE'
        elif score > 0.55 or bullish_pct > 0.6:
            return 'POSITIVE'
        elif score < 0.3 or bullish_pct < 0.25:
            return 'VERY_NEGATIVE'
        elif score < 0.45 or bullish_pct < 0.4:
            return 'NEGATIVE'
        else:
            return 'NEUTRAL'
    
    def _classify_trend_from_score(self, score: float) -> str:
        """
        순수 감성 점수로 트렌드 분류
        
        Args:
            score (float): 감성 점수 (-1 ~ 1)
            
        Returns:
            str: 트렌드
        """
        threshold = NEWS_SENTIMENT_THRESHOLD
        
        if score > threshold * 2:
            return 'VERY_POSITIVE'
        elif score > threshold:
            return 'POSITIVE'
        elif score < -threshold * 2:
            return 'VERY_NEGATIVE'
        elif score < -threshold:
            return 'NEGATIVE'
        else:
            return 'NEUTRAL'
    
    def _get_neutral_sentiment(self) -> Dict:
        """중립 감성 반환"""
        return {
            'score': 0.0,
            'trend': 'NEUTRAL',
            'news_count': 0,
            'buzz_ratio': 1.0,
            'bullish_percent': 0.5,
            'bearish_percent': 0.5,
            'top_headlines': [],
            'source': 'none'
        }
    
    def clear_cache(self):
        """캐시 초기화"""
        self.cache = {}
        logger.info("뉴스 감성 캐시 초기화")


# 전역 인스턴스
news_analyzer = None

def get_news_analyzer() -> NewsSentimentAnalyzer:
    """전역 뉴스 분석기 가져오기"""
    global news_analyzer
    if news_analyzer is None:
        news_analyzer = NewsSentimentAnalyzer(FINNHUB_API_KEY, USE_LOCAL_FINBERT)
    return news_analyzer




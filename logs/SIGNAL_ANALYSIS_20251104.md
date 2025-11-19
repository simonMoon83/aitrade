# 📊 시장 신호 및 신뢰도 분석 리포트 (2025-11-04)

## 🔍 **시장에서 보낸 신호 분석**

### **1. 신호 타입 분포**
```
BUY 신호:  0건 (0%)
SELL 신호: 0건 (0%)
HOLD 신호: 100% (모든 경우)
```

**결론**: 시장 상황이 **중립적**이어서 명확한 매수/매도 신호가 없었습니다.

---

## 📈 **신뢰도가 낮은 이유**

### **신뢰도 계산 공식**
```python
신뢰도 = SIGNAL_CONFIDENCE = SIGNAL_STRENGTH / 10.0

SIGNAL_STRENGTH = max(BUY_SCORE, SELL_SCORE)

BUY_SCORE = 가중치 합산:
  - BUY_RSI (RSI < 25) × 1.5
  - BUY_BB (볼린저 하단) × 1.5
  - BUY_LOW (저점 근처) × 1.0
  - BUY_VOLUME (거래량 급증) × 1.2
  - BUY_MA_SUPPORT (이동평균 지지) × 1.0
  - BUY_MACD (MACD 상승) × 1.3
  - BUY_DIVERGENCE (강세 다이버전스) × 2.0
  - BUY_MARKET (시장 필터 통과) × 1.0

SELL_SCORE = 가중치 합산:
  - SELL_RSI (RSI > 75) × 1.5
  - SELL_BB (볼린저 상단) × 1.5
  - SELL_HIGH (고점 근처) × 1.0
  - SELL_MA_RESISTANCE (이동평균 저항) × 1.0
  - SELL_MACD (MACD 하락) × 1.3
  - SELL_PROFIT (익절 목표) × 2.0
  - SELL_STOPLOSS (손절) × 3.0
  - SELL_DIVERGENCE (약세 다이버전스) × 2.0
```

---

## 💡 **신뢰도가 낮은 구체적 원인**

### **원인 1: 신호 점수가 임계값 미만**

**임계값**:
- BUY 신호: BUY_SCORE >= 4.5 필요
- SELL 신호: SELL_SCORE >= 4.0 필요

**실제 상황** (로그 분석):
```
[AAPL] 신뢰도: 0.00 ~ 0.30
  → BUY_SCORE와 SELL_SCORE가 모두 낮음
  → 예상: BUY_SCORE = 0~3.0, SELL_SCORE = 0~3.0
  → SIGNAL_STRENGTH = max(0~3.0) = 최대 3.0
  → 신뢰도 = 3.0 / 10.0 = 0.30

[AMZN] 신뢰도: 0.45 (가장 높음)
  → 예상: BUY_SCORE 또는 SELL_SCORE = 4.5
  → SIGNAL_STRENGTH = 4.5
  → 신뢰도 = 4.5 / 10.0 = 0.45
  → 하지만 여전히 임계값(0.60) 미만!
```

### **원인 2: 기술적 지표가 중립 상태**

**예상되는 시장 상황** (2025-11-04):
```
RSI: 30~70 (과매수/과매도 아님)
볼린저 밴드: 중간 위치 (상단/하단 돌파 없음)
MACD: 중립 (상승/하락 전환 없음)
이동평균: 교차 없음 (골든크로스/데드크로스 없음)
다이버전스: 없음
거래량: 정상 범위
```

**결과**:
- 대부분의 신호 지표가 0 또는 매우 낮음
- BUY_SCORE와 SELL_SCORE가 모두 낮음
- SIGNAL_STRENGTH 낮음 → 신뢰도 낮음

### **원인 3: ML 모델이 HOLD 예측**

**ML 모델 예측**:
```python
XGBoost 예측:
  - 입력: 수십 개의 기술적 지표
  - 출력: SELL(0), HOLD(1), BUY(2)
  - 예측 확률: 각 클래스별 확률

현재 상황:
  - ML_SIGNAL = "HOLD" (대부분)
  - ML 모델 확신도도 낮을 가능성 높음
```

**왜 HOLD를 예측하는가?**
1. 시장이 횡보 구간
2. 명확한 추세 없음
3. 변동성이 낮음
4. 과거 학습 데이터에서 HOLD가 가장 많았음

---

## 📊 **실제 신호 점수 예시 (추정)**

### **시나리오 1: 신뢰도 0.00 (AAPL, NVDA)**
```
BUY_SCORE = 0.0
  - BUY_RSI: 0 (RSI가 25 이상)
  - BUY_BB: 0 (볼린저 하단 아님)
  - BUY_LOW: 0
  - BUY_VOLUME: 0
  - BUY_MACD: 0
  - BUY_DIVERGENCE: 0
  - BUY_MARKET: 1.0 (시장 필터 통과)
  → 합계: 1.0

SELL_SCORE = 0.0
  - 모든 SELL 신호: 0
  → 합계: 0.0

SIGNAL_STRENGTH = max(1.0, 0.0) = 1.0
신뢰도 = 1.0 / 10.0 = 0.10 (하지만 로그는 0.00?)
```

**문제**: 신뢰도가 0.00인 경우는 **BUY_MARKET도 0**이거나, 데이터 문제일 수 있음

### **시나리오 2: 신뢰도 0.45 (AMZN - 최고)**
```
BUY_SCORE = 4.5 (추정)
  - BUY_RSI: 1.5 (RSI 약간 낮음)
  - BUY_BB: 1.5 (볼린저 중하단)
  - BUY_LOW: 1.0
  - BUY_VOLUME: 0
  - BUY_MACD: 0
  - BUY_DIVERGENCE: 0
  - BUY_MARKET: 1.0
  → 합계: 5.0 정도

SIGNAL_STRENGTH = 5.0
신뢰도 = 5.0 / 10.0 = 0.50 (로그는 0.45)
```

---

## 🎯 **신뢰도가 낮은 핵심 이유 요약**

### **1. 시장 상황이 중립적**
- 명확한 매수/매도 신호 없음
- 기술적 지표가 모두 중간 범위
- 추세 없음, 횡보 구간

### **2. 신호 점수 합산이 낮음**
- 개별 신호들이 모두 약함
- 가중치 합산이 임계값(4.5/4.0) 미만
- 결과: SIGNAL_STRENGTH 낮음

### **3. 신뢰도 계산 공식의 문제**
```python
신뢰도 = SIGNAL_STRENGTH / 10.0

문제점:
- 최대 신뢰도가 1.0이 되려면 SIGNAL_STRENGTH = 10.0 필요
- 하지만 실제 최대 점수는 약 8~10 정도
- 대부분의 경우 3~5 정도
- 따라서 신뢰도가 0.3~0.5 수준

현재 임계값 0.60은:
- SIGNAL_STRENGTH = 6.0 필요
- 매우 강한 신호만 통과
```

### **4. ML 모델의 보수적 예측**
- 과거 학습 데이터에서 HOLD가 많았음
- 현재 시장 패턴이 HOLD에 가까움
- 모델이 확신을 갖지 못함

---

## 🔧 **개선 방안**

### **방안 1: 신뢰도 계산 공식 수정**
```python
# 현재
신뢰도 = SIGNAL_STRENGTH / 10.0

# 제안 1: 최대값 조정
신뢰도 = SIGNAL_STRENGTH / 8.0  # 더 높은 신뢰도

# 제안 2: ML 모델 확률 결합
ML_CONFIDENCE = max(predict_proba)  # 0~1
RULE_CONFIDENCE = SIGNAL_STRENGTH / 10.0
신뢰도 = (ML_CONFIDENCE * 0.6) + (RULE_CONFIDENCE * 0.4)
```

### **방안 2: 임계값 조정**
```python
# 현재
min_confidence = 0.6  # 너무 높음

# 제안 (Paper Trading)
min_confidence = 0.4  # 또는 0.35
```

### **방안 3: 신호 점수 임계값 완화**
```python
# 현재
BUY_SCORE >= 4.5  # 매우 엄격
SELL_SCORE >= 4.0

# 제안
BUY_SCORE >= 3.5  # 약간 완화
SELL_SCORE >= 3.0
```

### **방안 4: 로깅 개선**
현재 신호 생성 과정이 로그에 충분히 남지 않음:
- BUY_SCORE, SELL_SCORE 값
- 각 신호 지표 상태
- ML 모델 예측 확률
- 최종 신호 결정 과정

---

## 📝 **결론**

### **시장 신호 요약**
- **타입**: 모두 HOLD (중립)
- **신뢰도**: 0.00 ~ 0.45 (모두 임계값 0.60 미만)
- **신호 강도**: 매우 약함 (SIGNAL_STRENGTH 낮음)

### **신뢰도가 낮은 이유**
1. ✅ **시장이 중립적**: 명확한 추세/신호 없음
2. ✅ **신호 점수 낮음**: 개별 지표들이 모두 약함
3. ✅ **신뢰도 공식**: SIGNAL_STRENGTH / 10.0으로 계산되어 낮게 나옴
4. ✅ **ML 모델 보수적**: HOLD 예측, 확신도 낮음
5. ✅ **임계값 높음**: 0.60은 매우 엄격한 기준

### **다음 단계**
1. 신뢰도 임계값을 0.4로 낮춤 (Paper Trading이므로)
2. 신호 생성 과정 상세 로깅 추가
3. BUY_SCORE, SELL_SCORE 값을 로그에 출력
4. ML 모델 예측 확률도 함께 확인

---

**생성일**: 2025-11-04
**분석자**: AI Assistant



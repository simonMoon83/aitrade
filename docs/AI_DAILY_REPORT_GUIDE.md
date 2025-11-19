# 📊 AI 일일 레포트 생성 가이드

## 개요

Gemini API를 사용하여 매일 장 마감 후 AI 기반 거래 분석 레포트를 자동으로 생성합니다.

## 주요 기능

✅ **자동 생성**: 매일 오전 7시 (장 마감 후) 자동으로 레포트 생성
✅ **AI 분석**: Google Gemini API를 사용한 전문적인 거래 분석
✅ **포괄적 내용**: 포트폴리오 분석, 거래 분석, 신호 분석, 시장 환경 분석, 내일 전략 제안
✅ **대시보드 통합**: 웹 대시보드에서 레포트 조회 및 관리
✅ **수동 생성**: API를 통해 언제든지 즉시 레포트 생성 가능

---

## 1. 설정 방법

### 1-1. Gemini API 키 발급

1. [Google AI Studio](https://makersuite.google.com/app/apikey) 접속
2. "Create API key" 버튼 클릭
3. API 키 복사

### 1-2. 환경 변수 설정

`.env` 파일에 API 키 추가:

```bash
# =============================================================================
# Gemini API 설정 (AI 일일 레포트 생성용)
# =============================================================================
GEMINI_API_KEY=여기에_발급받은_API_키_입력
```

### 1-3. 의존성 설치

```bash
pip install google-generativeai
```

또는 전체 의존성 재설치:

```bash
pip install -r requirements.txt
```

### 1-4. 설정 확인

`config.py`에서 레포트 생성 활성화 여부 확인:

```python
# 일일 레포트 설정
ENABLE_DAILY_REPORT = True  # 일일 레포트 생성 여부
DAILY_REPORT_HOUR = 7  # 레포트 생성 시간 (오전 7시, 장 마감 후)
REPORTS_SAVE_DIR = "reports/daily"  # 일일 레포트 저장 경로
```

---

## 2. 사용 방법

### 2-1. 자동 생성 (스케줄러)

Paper Trading을 실행하면 자동으로 스케줄러가 동작합니다:

```bash
python main.py --mode paper --symbols AAPL,MSFT,GOOGL --daemon
```

**자동 생성 시간**: 매일 오전 7시 (한국 시간, 미국 장 마감 후)

**생성 로직**:
1. 당일 포트폴리오 데이터 수집
2. 당일 거래 내역 수집
3. 당일 신호 내역 수집
4. Gemini API로 AI 분석 요청
5. 레포트 파일 저장 (`reports/daily/daily_report_YYYYMMDD.md`)
6. 메타데이터 저장 (`reports/daily/metadata_YYYYMMDD.json`)

### 2-2. 수동 생성 (대시보드)

웹 대시보드에서 즉시 생성 가능:

1. 대시보드 접속: `http://localhost:5000`
2. 로그인
3. "Reports" 메뉴 클릭
4. "Generate Report Now" 버튼 클릭

### 2-3. API를 통한 생성

```bash
curl -X POST http://localhost:5000/api/reports/generate \
  -H "Content-Type: application/json" \
  -u admin:password
```

---

## 3. 대시보드에서 레포트 조회

### 3-1. 레포트 목록 조회

**URL**: `/reports` 또는 `/api/reports/list`

**응답 예시**:
```json
{
  "reports": [
    {
      "date": "2025-11-12",
      "portfolio_value": 100500.00,
      "total_return": 0.005,
      "daily_return": 0.002,
      "trades_count": 3,
      "signals_count": 8,
      "generated_at": "2025-11-12T07:00:15",
      "ai_generated": true
    }
  ],
  "total": 1
}
```

### 3-2. 특정 날짜 레포트 조회

**URL**: `/api/reports/{YYYYMMDD}`

**예시**:
```bash
curl http://localhost:5000/api/reports/20251112 \
  -u admin:password
```

**응답**:
```json
{
  "date": "2025-11-12",
  "content": "# 📋 일일 거래 레포트 - 2025년 11월 12일\n\n...",
  "metadata": {
    "date": "2025-11-12",
    "portfolio_value": 100500.00,
    ...
  },
  "path": "reports/daily/daily_report_20251112.md"
}
```

---

## 4. 레포트 내용 구조

### 📋 일일 거래 레포트

#### 1. 📊 요약 (Executive Summary)
- 오늘의 핵심 성과 (3-5줄)
- 주요 수치와 하이라이트

#### 2. 💼 포트폴리오 분석
- 포트폴리오 가치 변화 분석
- 수익률 평가 (일일/누적)
- 현금 보유 비율 및 적정성

#### 3. 📈 보유 종목 분석
- 각 보유 종목의 현황 및 평가
- 수익/손실 종목 분석
- 포지션별 리스크 평가

#### 4. 💱 거래 분석
- 당일 체결된 거래 분석
- 매수/매도 결정의 적절성 평가
- 거래 타이밍 및 가격 분석

#### 5. 🎯 신호 분석
- 발생한 매매 신호 분석
- 신호의 신뢰도 및 정확도 평가
- 미체결 신호에 대한 검토

#### 6. 🔍 시장 환경 분석
- 오늘 시장 전반적인 흐름
- 주요 종목들의 움직임
- 시장 심리 및 변동성

#### 7. ⚠️ 리스크 및 주의사항
- 현재 포트폴리오의 리스크 요인
- 주의해야 할 종목이나 상황
- 손절/익절 대상 검토

#### 8. 💡 내일 전략 제안
- 내일 주목해야 할 종목
- 추천 매매 전략
- 포트폴리오 조정 제안

#### 9. 📌 결론
- 오늘 거래의 총평
- 전략 실행 평가 (등급)
- 개선이 필요한 부분

---

## 5. 파일 구조

```
reports/
└── daily/
    ├── daily_report_20251112.md      # 레포트 본문 (마크다운)
    ├── metadata_20251112.json        # 메타데이터
    ├── daily_report_20251113.md
    └── metadata_20251113.json
```

---

## 6. 트러블슈팅

### 문제 1: "google-generativeai 패키지가 설치되지 않았습니다"

**해결**:
```bash
pip install google-generativeai
```

### 문제 2: "GEMINI_API_KEY가 설정되지 않았습니다"

**해결**:
1. `.env` 파일 확인
2. `GEMINI_API_KEY=` 부분에 API 키 입력
3. 프로그램 재시작

### 문제 3: "레포트가 생성되지 않습니다"

**확인 사항**:
1. API 키가 올바른지 확인
2. 인터넷 연결 확인
3. Gemini API 할당량 확인
4. 로그 파일 확인: `logs/scheduler_YYYYMMDD.log`

**기본 레포트 생성**:
- Gemini API를 사용할 수 없는 경우 기본 템플릿으로 레포트 생성
- AI 분석 없이 데이터만 정리하여 제공

### 문제 4: "레포트가 중복 생성됩니다"

**원인**: 같은 날짜에 여러 번 생성하면 기존 파일 덮어쓰기

**해결**: 의도된 동작입니다. 최신 데이터로 레포트를 다시 생성하려면 수동 생성 사용

---

## 7. API 레퍼런스

### 7-1. GET `/api/reports/list`

레포트 목록 조회

**Query Parameters**:
- `limit` (optional, default=30): 조회할 최대 개수

**Response**:
```json
{
  "reports": [...],
  "total": 10
}
```

### 7-2. GET `/api/reports/<report_date>`

특정 날짜 레포트 조회

**Path Parameters**:
- `report_date`: 날짜 (YYYYMMDD 형식, 예: 20251112)

**Response**:
```json
{
  "date": "2025-11-12",
  "content": "레포트 내용 (마크다운)",
  "metadata": {...},
  "path": "reports/daily/daily_report_20251112.md"
}
```

**Error Responses**:
- `400`: 잘못된 날짜 형식
- `404`: 레포트를 찾을 수 없음

### 7-3. POST `/api/reports/generate`

즉시 레포트 생성

**Request**: Empty body

**Response**:
```json
{
  "success": true,
  "message": "레포트가 생성되었습니다.",
  "report_path": "reports/daily/daily_report_20251112.md",
  "metadata": {...}
}
```

**Error Response**:
```json
{
  "success": false,
  "error": "에러 메시지"
}
```

---

## 8. 비용 및 제한사항

### Gemini API 무료 할당량 (2024년 기준)

- **gemini-2.0-flash-exp**:
  - 분당 15 요청
  - 일일 1,500 요청
  - 월 무료

**비용 절감 팁**:
1. 하루 한 번만 자동 생성 (충분함)
2. 수동 생성은 필요할 때만 사용
3. API 키 보안 유지

### 제한사항

1. **인터넷 연결 필수**: Gemini API 호출을 위해 인터넷 필요
2. **응답 시간**: 10~30초 소요 (레포트 길이에 따라 다름)
3. **언어**: 한국어로 프롬프트 작성됨
4. **데이터 의존성**: 거래 데이터가 없으면 간단한 레포트 생성

---

## 9. 향후 개선 계획

- [ ] 차트 이미지 자동 생성 및 첨부
- [ ] PDF 형식 내보내기
- [ ] 이메일 자동 발송
- [ ] 주간/월간 요약 레포트
- [ ] 맞춤형 레포트 템플릿
- [ ] 다국어 지원 (영어, 일본어 등)
- [ ] 레포트 비교 기능 (전일 대비, 주간 대비)

---

## 10. 문의 및 지원

문제가 발생하면:
1. 로그 파일 확인: `logs/daily_report_generator_YYYYMMDD.log`
2. GitHub Issues 등록
3. API 키 및 민감한 정보는 절대 공유하지 마세요

---

**작성일**: 2025-11-12
**버전**: 1.0.0
**업데이트**: Gemini 2.0 Flash Exp 모델 사용

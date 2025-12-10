# 키움증권 시스템 트레이딩 봇

## 전략 개요
- **매수**: 볼린저밴드 하단 돌파 시
- **매도**:
  - +1.0% 도달 시 50% 매도
  - +1.5% 도달 시 전량 매도
  - -1.5% 도달 시 손절 (시장가)
- **대상**: 코스닥 종목

## 설치 방법

### 1. 키움증권 OpenAPI 설치
1. 키움증권 홈페이지 접속
2. [트레이딩] > [시스템트레이딩] > [OpenAPI]
3. KOA Studio 다운로드 및 설치
4. OpenAPI 사용 신청

### 2. Python 패키지 설치
```bash
pip install -r requirements.txt
```

## 실행 방법

```bash
python trading_bot.py
```

## 주의사항

⚠️ **반드시 모의투자로 먼저 테스트하세요!**

1. 키움증권 HTS에서 로그인되어 있어야 합니다
2. 장 시작 전에 실행하는 것을 권장합니다
3. 실제 투자 시 손실 위험이 있습니다
4. 투자 금액과 종목 수는 `trading_bot.py`에서 조정 가능합니다

## 설정 변경

`trading_bot.py` 파일에서 다음 값들을 수정할 수 있습니다:

```python
self.max_stocks = 5  # 최대 보유 종목 수
self.investment_per_stock = 1000000  # 종목당 투자금액
self.profit_target_half = 1.0  # 50% 매도 수익률
self.profit_target_full = 1.5  # 전량 매도 수익률
self.stop_loss = -1.5  # 손절 수익률
```

## 파일 구조

- `kiwoom_api.py`: 키움 OpenAPI 연동
- `strategy.py`: 볼린저밴드 전략 및 포지션 관리
- `trading_bot.py`: 메인 트레이딩 봇
- `requirements.txt`: 필요한 패키지 목록

## 문제 해결

### "KHOPENAPI.KHOpenAPICtrl.1" 오류
- KOA Studio가 설치되지 않았거나 등록되지 않음
- 키움증권 OpenAPI를 재설치하세요

### 로그인 실패
- 키움증권 HTS에 로그인되어 있는지 확인
- OpenAPI 사용 신청이 승인되었는지 확인

### 주문 실패
- 계좌에 충분한 잔고가 있는지 확인
- 모의투자 계좌인지 실계좌인지 확인

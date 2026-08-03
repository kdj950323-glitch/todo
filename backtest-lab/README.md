# 매수·매도 수익률 계산기 (주식·ETF·코인)

국내 주식/ETF, 미국 주식/ETF, 코인(암호화폐)을 대상으로 "이 날 사서 이 날 팔았으면 수익률이
얼마였을지"를 계산하는 개인용 Streamlit 앱입니다. 인기 종목 퀵 선택 목록에서 고르거나 종목코드/티커를
직접 입력할 수 있습니다.
**LLM을 사용하지 않으며**, 결과 요약은 계산된 수치를 고정 규칙 템플릿에 대입해 생성합니다. 투자 조언이 아닙니다.

## 로컬 실행

### 더블클릭 (Windows)
`실행.bat`을 더블클릭하면 처음 실행 시 가상환경 생성 및 패키지 설치(몇 분 소요) 후 브라우저가 자동으로 열립니다.

### 수동 실행
```powershell
cd backtest-lab
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\streamlit run app.py
```
브라우저에서 `http://localhost:8501` 접속 → 좌측 사이드바에서 자산군/종목/매수일/매도일/투자금액 입력 후 실행.

## 테스트
```powershell
.venv\Scripts\python -m pytest tests/ -v
```
거래일 스냅(주말/휴일 처리), 수익률·연환산수익률(CAGR) 계산 로직에 대한 유닛테스트가
네트워크 없이 실행됩니다.

## 데이터 소스 및 한계

| 자산군 | 소스 | 한계 |
|---|---|---|
| 국내 주식/ETF | `pykrx` (비공식 KRX 스크레이퍼), 실패 시 `FinanceDataReader` 자동 폴백 | KRX 웹사이트 구조 변경 시 예고 없이 깨질 수 있음 |
| 미국 주식/ETF | `yfinance` | Yahoo의 비공식 클라이언트로 간헐적 차단/레이트리밋 발생 가능 |
| 코인 | `yfinance`의 `BTC-USD` 등 `<심볼>-USD` 티커 (거래소 API 키 불필요, USD 기준) | 국내 거래소(업비트 등) 원화 시세와는 정확히 일치하지 않을 수 있음 |

수수료·슬리피지·세금·배당은 계산에 포함되지 않습니다.

## 공개 배포 (Streamlit Community Cloud, 무료)

다른 사람이 링크로 접속해 써볼 수 있게 하려면 아래 단계로 배포합니다. 이 단계는 본인 GitHub/Streamlit
계정 로그인이 필요해 직접 진행해야 합니다.

1. 이 저장소(`backtest-lab` 폴더 포함)를 GitHub에 push
2. https://share.streamlit.io 접속 → GitHub 계정으로 로그인
3. "New app" 클릭 → 저장소 선택 → **Main file path**에 `backtest-lab/app.py` 입력 → Deploy
4. 몇 분 후 `https://<앱이름>.streamlit.app` 형태의 공개 링크가 발급됩니다
5. 코드를 다시 push하면 자동으로 재배포됩니다 (수동 재배포 불필요)

배포된 앱은 접속자 수가 많아지면 무료 티어 리소스 한도(CPU/메모리)에 걸릴 수 있으니, 트래픽이 많다면
유료 플랜 또는 다른 호스팅(Render, Railway 등)을 고려하세요.

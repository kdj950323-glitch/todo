# 주식 물타기 계산기

기존 보유 수량/평균단가에 추가 매수(물타기)를 더하면 평균단가가 얼마나 낮아지는지, 현재가를
입력하면 손익이 물타기 전후로 어떻게 달라지는지 계산하는 개인용 Streamlit 앱입니다. 주식·ETF·코인
등 종목 종류에 상관없이 가격/수량만으로 계산하는 순수 계산기라 시세 조회(API)가 필요 없습니다.
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
브라우저에서 `http://localhost:8501` 접속 → 좌측 사이드바에서 기존 보유 수량/평균단가, 추가 매수 정보,
(선택) 현재가를 입력 후 실행.

## 테스트
```powershell
.venv\Scripts\python -m pytest tests/ -v
```
평균단가 계산, 물타기 전/후 손익 비교, 손익분기 계산 로직에 대한 유닛테스트가 네트워크 없이 실행됩니다.

## 한계

현재가는 직접 입력만 지원하며 실시간 시세 자동 조회 기능은 없습니다. 수수료·세금은 계산에 포함되지 않습니다.

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

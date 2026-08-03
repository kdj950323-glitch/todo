@echo off
cd /d "%~dp0"
if not exist .venv (
    echo [1/2] 가상환경 생성 및 패키지 설치 중... (처음 한 번만, 몇 분 걸릴 수 있습니다)
    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
)
echo [2/2] 백테스팅 랩 실행 중... 잠시 후 브라우저가 자동으로 열립니다.
.venv\Scripts\streamlit run app.py
pause

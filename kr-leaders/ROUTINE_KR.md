# 국내 시장 점유율 1위 기업 추적 루틴 (GitHub 전용)

사용자와 대화 없이 혼자 실행되므로 질문하지 말고 끝까지 처리한다. 전략 배경은 `kr-leaders/STRATEGY.md`. 저장소는 **공개**이다: 개인정보·보유 종목·평단·손익·계좌·API 키를 어떤 파일에도 쓰지 않는다. 투자 권유·매수 추천은 쓰지 않는다. 숫자는 실제로 조회한 값만 쓴다.
실행 시각: 한국시간 월~금 오후 4시 30분(장 마감 15:30 이후). 도구: Bash(python3, curl), Read/Write/Edit, PushNotification. 네이버 증권 모바일 주소와 네이버 검색 API 키(환경변수 NAVER_CLIENT_ID/SECRET, 키 출력 금지)를 쓴다.

## 0. 준비
1. `git pull --rebase`. 커밋 작성자가 없으면 `git config user.name "Claude Routine"`, `git config user.email "noreply@anthropic.com"`.
2. 한국 증시 휴장일(주말, 공휴일, 12/31 등)이면 `python3 kr-leaders/tools/track.py` 가 직전 거래일 지수 일자를 쓴다. 이미 `kr-leaders/daily/<해당일>.md` 가 있으면 새로 만들지 말고 끝낸다.

## 1. 점유율 1위 후보 갱신 (뉴스)
1. `python3 kr-leaders/tools/discover.py fetch --days 14 --out /tmp/kr_cand.json`
2. 후보 중 `new_articles` 가 1 이상이고 `state/leaders_kr.csv` 에서 상태가 '확인'이 아닌 것(없거나 '후보')만 읽는다. 각 회사의 `articles[].snippet`·title 을 보고 판정한다:
   - **확인**: 기사에 그 회사가 해당 분야(국내/세계, 전체/세부 품목)의 점유율 1위라고 직접 나온다. `segment` 에 분야를 짧게(예: "HBM 장비 세계 1위") 쓰고 reason 은 한 줄. 금융업이면 reason 에 '금융업' 을 포함한다(부채비율 해석 제외용).
   - **제외**: 1위 주체가 다른 회사·계열사·경쟁사이거나 이름이 우연히 겹쳤거나 "1위를 다툰다/목표" 등 근거가 약함.
   - **보류**: 애매함. 기사가 더 쌓이면 다시 판단.
   `/tmp/kr_decided.json` 형식: `[{"code":"005930","verdict":"확인","segment":"...","reason":"..."}]`. 기사에 있는 내용만 근거로 하고 추측하지 않는다.
3. `python3 kr-leaders/tools/discover.py apply --cand /tmp/kr_cand.json --decided /tmp/kr_decided.json`
4. 기존 '확인' 종목은 다시 판정하지 않는다. 새로 '확인'된 종목이 있으면 보고에 이름과 분야를 적는다.

## 2. 일일 추적
`python3 kr-leaders/tools/track.py` → `kr-leaders/daily/YYYY-MM-DD.md`, `state/kr_status.csv`, `state/kr_flow.csv`. 출력 JSON 의 `fails` 가 있으면 보고에 적는다. 파일을 임의로 고치지 않는다(생성물).

## 3. 사이트 빌드·점검·저장
1. `python3 kr-leaders/tools/build_kr_site.py` (docs/kr 재생성). 이어서 미국 증시 사이트 목차에 링크가 반영되도록 `python3 market-log/tools/build_site.py`.
2. **`python3 market-log/tools/privacy_check.py kr-leaders docs` 가 '이상 없음'이 될 때까지** 고친다(통과 전 커밋·푸시 금지).
3. `git add kr-leaders docs` → 커밋 `kr-leaders: YYYY-MM-DD` → master 에 push. 거부되면 `git pull --rebase` 후 재시도(docs/ 충돌은 build_kr_site·build_site 로 재생성해 `git add docs`).
4. kr-leaders/ 와 docs/ 밖의 파일은 수정·삭제하지 않는다.

## 4. 알림·보고
PushNotification 1건(한국어 100자 안팎): `10/26 국내 점유율1위 추적 · 코스닥 2주 -12.2%(낙폭과대 구간) · 추적 47종목(정상 38) · 신규 확인 2` 형태. 브레이크 신호가 발생한 날은 맨 앞에 "브레이크 신호"를 쓴다. 실패는 사유와 함께. 최종 응답에는 기준일, 시장 구간, 추적 종목 수, 신규 확인·제외, 커밋을 짧게 적는다.

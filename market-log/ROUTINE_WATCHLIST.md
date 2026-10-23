# 루틴: 관심종목 데일리 체크 + 종목 뉴스 (GitHub 전용)

2026-10-23부로 **Notion 은 폐지**되었다. 이 문서가 최우선이며 `EARNINGS_CONTEXT.md`·`ADDENDUM.md` 와 충돌하면 이 문서를 따른다. 그 문서들의 Notion 관련 문구는 전부 무시하고 Notion 도구는 호출하지 않는다.
저장소는 **공개**이다. 개인정보·보유 종목·평단·손익·메모·관심 가격대(사용자 개인 기준)를 쓰지 않는다. 투자 권유·매수 추천 없음. 숫자는 조회한 값만.
실행 시각: 한국시간 화~토 오전 8시 30분(UTC 월~금 23:30). 도구: Bash(curl, python3), Read/Write/Edit, WebFetch/WebSearch, PushNotification.

## 0. 준비
1. `git pull --rebase`. 커밋 작성자 없으면 `Claude Routine` / `noreply@anthropic.com`.
2. 대상 거래일 = 미국 동부 기준 가장 최근 마감일. NYSE 휴장일 다음 날 아침이면 건너뛰고 푸시(휴장일 목록은 ROUTINE_DAILY.md 0절).
3. `market-log/watchlist/<대상일>.md` 가 이미 있고 실패 메모뿐이 아니면 건너뛴다.

## 1. 관심종목 목록
`market-log/watchlist.csv` (열: ticker,name_ko)가 원본이다. 사용자가 이 파일을 고치거나 Claude 에게 요청해 바꾼다. 티커 비어 있는 행 무시, 대문자 정규화, Finviz 에 없는 티커는 '조회 불가 종목'으로 맨 아래에 적는다. **이 파일은 수정하지 않는다.**

## 2. 상태 계산 (고정 도구)
`python3 market-log/tools/watchlist_status.py --date <대상일> --tickers "NVDA:엔비디아,AMD:AMD,..." --out-dir /tmp/wl` (watchlist.csv 의 ticker:name_ko 를 이어 붙인다. 관심 가격대는 쓰지 않으므로 하단·상단 칸은 비운다).
결과 table.md, changes.md, state.csv, summary.json, status.json 으로 `market-log/watchlist/<대상일>.md` 를 만든다: 변화 요약 → 종목 현황 표 → 뉴스 → 읽는 법과 출처. 하단에 다음 날 비교용 상태 CSV. 점수는 상태 파악용 보조 지표일 뿐 매매 신호가 아니다.
방어 상승일 플래그는 EARNINGS_CONTEXT 6~7절(`state/watchlist_prices.csv`, `reversal_flags.py`)대로 갱신한다.

## 3. 실적 앞둔 낙폭 종목
EARNINGS_CONTEXT 1~5절대로 '52주 고점 대비 -20% 이하 + 다음 실적 30일 이내' 종목(최대 10)을 분석해 같은 파일에 '실적 앞둔 낙폭 종목' 소제목으로 추가한다. 결과 중 확정된 발표 일정·실제치는 `market-log/earnings/calendar.csv` 에 반영한다(같은 date+ticker 한 행).

## 4. 종목 뉴스 (14일 보관)
EARNINGS_CONTEXT 9절의 `python3 market-log/tools/news_tracker.py fetch/apply/sync` 절차를 따르되 Notion 페이지 갱신 단계는 생략한다. 결과는 `market-log/news/latest.md` 이다. 목록 동기화는 `watchlist.csv` 기준(`news_universe.csv` 의 source 가 관심종목인 행).

## 5. 빌드·점검·저장
`python3 market-log/tools/build_site.py` → `python3 market-log/tools/privacy_check.py` (이상 없음 확인 전 푸시 금지) → `git add market-log docs` → 커밋 `market-log: watchlist YYYY-MM-DD` → master push(거부 시 pull --rebase 재시도, docs 충돌은 build_site 재생성 후 `git add docs`).

## 6. 알림
PushNotification 1건(항상): 변화 있으면 `관심종목 N개 중 변화 K건: NVDA 200일선 이탈, … 외 N건`, 없으면 `관심종목 N개 변화 없음 · 평균 등락 ±x.x%`, 실패·건너뜀은 사유와 함께. 최종 응답에 기준일, 종목 수, 변화 목록, 조회 불가 종목, 커밋을 짧게 적는다.

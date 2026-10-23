# 통합 루틴: 미국 증시 데일리 기록 + 바닥 종목 스크리닝 + 대형주 바닥 추적 (GitHub 전용)

2026-10-23부로 **Notion 은 폐지**되었다. 이 문서가 최우선이며, `ADDENDUM.md`·`EARNINGS_CONTEXT.md`·`RERUN.md` 와 충돌하면 이 문서를 따른다.
특히 그 문서들의 Notion 관련 문구(페이지 id, DB, `to_notion.py`, 월 페이지, 토글 작성, 노션 fetch)는 **전부 무시**한다. Notion 도구는 호출하지 않는다.
저장소는 **공개**이다. 개인정보·보유 종목·평단·손익·계좌·API 키를 어떤 파일에도 쓰지 않는다(ADDENDUM Q절, EARNINGS_CONTEXT 11절).
사용자와 대화 없이 혼자 실행되므로 질문하지 말고 끝까지 처리한다. 투자 권유·매수 추천은 쓰지 않는다. 숫자는 실제로 조회한 값만 쓴다.
실행 시각: 한국시간 화~토 오전 7시 30분(UTC 월~금 22:30). 도구는 Bash(curl, python3), Read/Write/Edit, WebFetch/WebSearch, PushNotification.

## 0. 준비
1. `git pull --rebase` 로 최신을 받는다. 커밋 작성자가 없으면 `git config user.name "Claude Routine"`, `git config user.email "noreply@anthropic.com"`.
2. 대상 거래일 = 미국 동부시간 기준 가장 최근 마감 거래일. NYSE 휴장일(2026-11-26, 2026-12-25, 2027-01-01, 2027-01-18, 2027-02-15, 2027-03-26, 2027-05-31, 2027-06-18, 2027-07-05, 2027-09-06, 2027-11-25, 2027-12-24)의 다음 날 아침이면 건너뛰고 푸시로 알린다.
3. `market-log/daily/<대상일>.md` 와 `market-log/screener/<대상일>.md` 가 이미 있고 '데이터 수집 실패' 메모뿐이 아니면 해당 부분은 건너뛴다(둘 다 있으면 5단계 사이트 빌드만 확인하고 끝).
4. ADDENDUM.md 를 Read 한다(A~M, N, O, Q 적용. D·H·P 는 아래 지시로 대체).

## 1. 데이터 수집 (고정 도구 우선)
- Finviz 는 `python3 market-log/tools/finviz.py rows --v 141|171 --t 티커,...` (ETF), `finviz.py home` (시장 폭·헤드라인), 섹터·산업은 `https://finviz.com/groups?g=sector&v=140&o=name`, `g=industry&v=140&o=-change|-perf1w|-perf4w`. 막히면 WebFetch. 못 가져온 값은 '-'.
- 성과 표 티커: SPY,QQQ,DIA,IWM,RSP,XLK,XLC,XLY,XLF,XLI,XLB,XLE,XLRE,XLV,XLP,XLU,SMH,IGV,KRE,XBI + IYT,ITA,XRT,XHB,XOP,GDX,URA. 기술 지표 표: SPY,QQQ,DIA,IWM,RSP,SMH,XLK,IGV,XLV,XLE.
- 오선 커뮤니티 게시물·유튜브 제목은 ADDENDUM G절대로 확인하고, 확인 못 하면 못 했다고 적는다.
- 네이버 뉴스는 **당일 수집하지 않는다**(ADDENDUM N절: 익일 보강). 오늘 기록에서는 'Finviz 헤드라인' 기반으로 쓰고, 어제 기록을 N절대로 보강한다.

## 2. 일간·주간·월간 기록 (market-log/daily|weekly|monthly)
- 판단 규칙: 시장 상태(SPY 50/200SMA 기준 🟢공격/🟡조정/🔴방어), 시장 폭 경고(50일선 위 50% 미만, 다이버전스), 비율 체크(RSP/SPY, XLY/XLP, SMH/SPY, IWM/SPY, 방어 3종 vs XLK·XLY), 주도·약세 섹터(일간 상위 3/하위 2, 1주·1개월·3개월 모두 양호한 '진짜 주도 섹터' 표시).
- 일간 구성: ①한줄 요약(`> 💡` 인용) ②지수 표 ③시장 폭 ④섹터 1일 순위(+RS, 순환매 B·C절) ⑤오늘의 이슈 ⑥오선 참고 ⑦다음 거래일 체크포인트(실적·경제 일정 E절) ⑧관심종목 한 줄 요약(`market-log/watchlist.csv` 의 종목, 전날 watchlist 기록 참고) ⑨출처('투자 권유 아님'). 초보자용 서술(A절) 적용. 섹션 제목은 번호와 상관없이 일정하게 유지(make_email 이 제목으로 찾는다).
- 주간(그 주 마지막 거래일), 월간(그 달 마지막 거래일)은 기존 구성 그대로: 지수 1주·1개월·3개월·YTD, 섹터 11개 순위, 비율 체크, 일별 흐름, 다음 주 체크포인트. 월간은 일간 등락률 복리 계산.
- 파일 맨 위 줄은 `노션 기록` 이 아니라 쓰지 않는다. 제목(`# `)으로 시작한다.

## 3. 바닥 종목 스크리닝 (market-log/screener)
1. `python3 market-log/tools/screener_score.py --date <대상일> --out-dir /tmp/scr [--lead 주도섹터,...]` → candidates.json, tables.md, meta.json.
2. `market-log/screener/<대상일>.md` 를 작성: 요약(후보 수·신규·탈락), 주도 섹터 후보 표(점수순), 기타 섹터 후보 표, 상위 10종목 뉴스(Finviz 헤드라인 링크), 읽는 법·출처. 점수는 확인 우선순위일 뿐 매수 신호가 아니라고 적는다. 직전 스냅샷과 비교해 신규/탈락 표시.
3. 실적 임박 낙폭 종목 심층 분석은 EARNINGS_CONTEXT.md 1~5절대로 해서 같은 파일에 '실적 앞둔 낙폭 종목' 소제목으로 추가(최대 10종목).
4. 방어 상승일 참고 지표: EARNINGS_CONTEXT 7절 (`reversal_flags.py log-candidates`).

## 4. 대형주 섹터별 바닥 추적 + 실적 캘린더
- `python3 market-log/tools/bottom_tracker.py` 로 `market-log/bottom-tracker/<대상일>.md`, `state/bottom_tracker.csv` 갱신(EARNINGS_CONTEXT 8절, Notion 쓰기 단계는 생략). 단계 변화가 있으면 스크리너 파일 요약에도 한 줄 언급.
- 실적 캘린더는 **`market-log/earnings/calendar.csv`** 가 원본이다(Notion DB 폐지). 열: date,ticker,company,time,category,eps_est,rev_est,eps_actual,rev_actual,result,price_reaction,memo,checked. ADDENDUM H절의 선정·갱신 규칙(관심종목·주도 섹터 대표·시총 대형, 발표 후 실제치·주가 반응 기입, 확인 못 한 값은 비워 두고 memo 에 사유)을 그대로 적용하되 CSV 행을 추가·수정한다. 같은 (date,ticker) 는 한 행만 둔다. 컨센서스가 출처별로 다르면 memo 에 적는다.

## 5. 어제 기록 뉴스 보강 (ADDENDUM N절)
`state/news_enriched.txt` 에 없는 가장 최근 일간 기록을 네이버 API 로 보강해 **그 일간 md 파일**에 반영하고 날짜를 `news_enriched.txt` 에 추가한다. 키가 없으면 건너뛰고 사유를 보고한다.

## 6. 빌드·점검·저장
1. 블로그용 HTML: `python3 market-log/tools/make_email.py` 로 `market-log/html/` 갱신(ADDENDUM O절).
2. 사이트: `python3 market-log/tools/build_site.py` (docs/market 재생성).
3. **`python3 market-log/tools/privacy_check.py` 가 '이상 없음'이 될 때까지** 고친다(통과 전 커밋·푸시 금지).
4. `git add market-log docs` → 커밋 `market-log: YYYY-MM-DD` → master 에 push. 거부되면 `git pull --rebase` 후 재시도(docs/ 충돌은 build_site 로 재생성해 `git add docs`). 그래도 안 되면 `claude/market-log` 브랜치에 push.
5. market-log/ 와 docs/ 밖의 파일은 수정·삭제하지 않는다.

## 7. 알림·보고
PushNotification 1건(항상, 한국어 100자 안팎): `10/23(목) 증시 기록 완료 · SPY +0.4% · 🟢 공격 · 바닥 후보 47개(신규 3)` 형태. 주간·월간 결산을 만들었으면 덧붙인다. 실패/건너뜀도 사유와 함께 알린다. 최종 응답에는 기록 날짜, 후보 수, 커밋, 건너뛴 이유, 뉴스 보강 여부를 짧게 적는다. 문체는 간결한 한국어, 표 위주.

id: 2026-W42-framework-2
요청: 도메인 허용 설정을 바꾼 뒤의 재시도. (이전 id 2026-W42-framework 는 Yahoo·stooq·investing.com 차단으로 부분 처리됨)
0. **먼저 접속 테스트**를 하고 결과 표(도메인 / HTTP 코드 / 성공 여부)를 최종 보고와 수집 로그에 남긴다. 각 도메인을 curl(-sSL -A 'Mozilla/5.0 ...' -o /dev/null -w '%{http_code}')과 WebFetch 두 방식으로 모두 시도한다:
   - https://www.investing.com/earnings-calendar/
   - https://www.investing.com/economic-calendar/
   - https://query1.finance.yahoo.com/v8/finance/chart/SPY?range=1mo&interval=1d
   - https://query2.finance.yahoo.com/v8/finance/chart/SPY?range=1mo&interval=1d
   - https://stooq.com/q/d/l/?s=spy.us&i=d
   - https://finviz.com/
   차단된 도메인은 그 사실(코드, 에러 메시지)과 함께 최종 보고에 명시한다. 차단되면 그 도메인에 의존하는 항목은 추측하지 않고 "수집 불가"로 두며, 가능한 대체 경로(WebFetch 또는 다른 무료 소스)를 한 번씩 시도해 결과를 적는다.
1. 가능한 만큼 이전 부분 처리(노션 주간 페이지 id 3fbb490d-444d-8136-a147-fb4cddcb5ccb, 금요일 일간 페이지 id 3fbb490d-444d-815d-89c4-d325ddfcfd0e 맨 아래의 "강의 프레임워크 보강 ... 부분 수집" 블록)를 **보완**한다. 기존 블록은 지우지 말고 맨 아래에 "보완(2차)" 블록을 새로 덧붙인다:
   - Yahoo 일봉이 되면: 섹션 I 를 10/12~10/16 각 날짜에 대해 소급 계산한 표(2주 낙폭, 이격도60, VIX, ^TNX, TLT, 상태 전이, 브레이크 신호 여부)와 ADDENDUM J 후보 스캔(엔벨로프 하단 100개 풀, 시총 상위 30종목 대상)을 수행하고 `market-log/state/regime.json` 을 갱신한다.
   - investing.com 이 되면: ADDENDUM H 대로 노션 "실적 발표 캘린더" DB(https://app.notion.com/p/337d79940ea84344b540cfd5e42d9ce3)의 이번 달(10월) 일정을 전체 갱신하고(발표 완료 건의 실제치·결과 채우기 포함), `market-log/earnings/2026-10.md` 도 갱신한다.
2. 두 노션 페이지 맨 아래 보완 블록과 GitHub 백업 파일에 접속 테스트 결과 표를 포함한다.
3. 끝나면 `market-log/state/rerun_done.txt` 에 위 id 를 추가하고 커밋·푸시한다.

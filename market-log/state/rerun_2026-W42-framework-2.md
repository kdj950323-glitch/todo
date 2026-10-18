# RERUN 2026-W42-framework-2 처리 결과 (2026-10-18 실행)
접속 테스트 (curl / WebFetch)
| 도메인 | curl | WebFetch |
|---|---|---|
| investing.com/earnings-calendar | 403 | 성공 (10/19~ 예정 일정만 표시, 실제치 없음) |
| investing.com/economic-calendar | 403 | 미시도 |
| query1.finance.yahoo.com | CONNECT 403 | ENOTFOUND |
| query2.finance.yahoo.com | CONNECT 403 | 미시도 |
| stooq.com | CONNECT 403 | 미시도 |
| finviz.com | 200 | - |

결과: Yahoo·stooq 여전히 차단 → 섹션 I 소급 계산·ADDENDUM J 후보 스캔은 수집 불가(추측하지 않음), regime.json은 '판정보류' 유지.
investing.com은 WebFetch만 가능. 노션 실적 캘린더 DB 전체 갱신과 보완 블록 추가는 이번 실행에서 수행하지 않음(미처리).
대상 거래일 10/16 일간·주간(W42) 기록은 이미 존재하여 건너뜀.

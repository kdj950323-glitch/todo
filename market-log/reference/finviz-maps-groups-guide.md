# Finviz MAPS·GROUPS 가이드북

미국 증시 **업종별 흐름**을 한눈에 보는 Finviz의 두 화면, **MAPS**(히트맵)와 **GROUPS**(업종 순위표) 사용법 정리. (Notion 보관본을 2026-10-23에 GitHub로 옮김. 화면 구성 기준일 2026-10-10, 사이트 개편 시 메뉴 이름·위치가 바뀔 수 있음)

한 줄 요약: **MAPS로 "오늘 어디가 뜨거운지" 보고 → GROUPS로 "그게 며칠째, 몇 주째인지" 확인**한다.

바로가기: [MAPS](https://finviz.com/map) · [GROUPS](https://finviz.com/groups) · 관련 문서: [업종별 흐름 체크 ETF](sector-etfs.md)

## PART 1. MAPS (히트맵)

### 1-1. 화면 읽는 법 — 이것만 알면 70%
- **네모 크기 = 시가총액**: 클수록 지수에 미치는 영향이 큼(NVDA·MSFT·AAPL이 거대한 이유)
- **색 = 등락률**: 초록 = 상승, 빨강 = 하락. 색이 진할수록 많이 움직임(하단 범례 -3% ~ +3%)
- **큰 구역 = 섹터, 작은 구역 = 산업**: 예) TECHNOLOGY 안에 SEMICONDUCTORS, SOFTWARE-INFRASTRUCTURE 등

판단 포인트: 지수가 올랐는데 **초록이 몇몇 거대 네모에만** 있으면 → 빅테크 몇 개가 끌어올린 장. **화면 전체가 초록**이면 → 매수세가 넓게 퍼진 건강한 장.

### 1-2. 왼쪽 사이드바 메뉴

| 메뉴 | 선택지 | 설명 / 추천 |
|---|---|---|
| VIEW AS(보기 방식) | Map / Bubbles / Matrix | Map: 기본 히트맵 ✅ 추천. Bubbles: 거품(원) 형태. Matrix(신규): 섹터→산업→종목 순으로 파고드는 목록형 |
| SIZE BY(네모 크기 기준) | Market / Equal | Market: 시총 비례(기본). Equal: 모든 종목 같은 크기 → 대형주에 가려진 중소형 종목들의 분위기를 볼 때 유용 |
| MAP FILTER(어떤 종목을 볼지) | S&P 500 / Dow Jones 30 / Nasdaq 100 / Russell 2000 / All Stocks / Market Cap / World / ETFs / Crypto / Futures / Themes | S&P 500: 기본 ✅. All Stocks: 미국 상장 전 종목(약 5,600개). Russell 2000: 중소형주 분위기. ETFs: 섹터 ETF를 한 번에. World: 국가별 증시. Themes: AI·원전 등 테마 |
| 기간 드롭다운(기본 1-Day Performance) | Performance / Fundamentals 두 그룹 | 색깔이 무엇을 기준으로 칠해지는지 결정 → 아래 1-3 |
| Search ticker | 티커 입력 | 지도에서 특정 종목 위치를 바로 찾기 |

### 1-3. 기간 드롭다운 (가장 중요)

| 구분 | 항목 | 언제 쓰나 |
|---|---|---|
| ⏱️ 장중 단기 | 1·2·3·5·10·15·30-Minute, 1·2·4-Hour, Aftermarket | 장중 실시간 수급. Aftermarket = 시간외(실적 발표 반응) |
| 📅 **흐름 파악 ✅** | **1-Day, 1-Week, 1-Month**, Month to Date, **3-Month**, 6-Month | **업종 흐름 체크의 핵심**. 1-Day → 1-Week → 1-Month 순서로 바꿔보며 색이 유지되는지 확인 |
| 📆 장기 | Year to Date, 1·3·5·10-Year | 올해 주도 섹터 / 장기 승자 확인 |
| 📉 고점·저점 | **Drawdown from 52-Week High**, Gain from 52-Week Low | 52주 고점 대비 얼마나 빠졌나 → 조정 깊이 확인(추격매수 방지에 유용) |
| 🔊 거래량 | **Relative Volume** | 평소 대비 거래량 배수. 진하게 칠해진 곳 = 돈이 몰리는(또는 빠지는) 곳 |
| 📊 Fundamentals | P/E, Forward P/E, PEG, P/S, 배당수익률, EPS·매출 성장률, ROE, 마진, Float Short, Analysts Recom., Earnings Date 등 | 섹터별 밸류에이션 비교. Earnings Date로 실적발표 몰린 섹터 확인 |

무료 버전은 **지연 시세**. 실시간 데이터·광고 제거는 Elite(유료) 전용이며 분 단위 등 일부 항목은 무료에서 제한될 수 있다. 흐름 파악(1-Day 이상)은 무료로 충분.

### 1-4. 오른쪽 위 아이콘
- ⚙️ Heatmap Settings: **Why Is It Moving**(종목 위에 마우스를 올리면 AI 요약), **Show Industry**, **Fixed Sector Order**(섹터 배치 고정 → 매일 같은 자리에서 비교 ✅ 추천), Colorblind Mode
- 🔗 Share Map(공유 링크), ⛶ Fullscreen, ➖/➕ Zoom, Embed Map(블로그 삽입 코드)
- 마우스 올리기: 종목명·등락률·같은 산업 종목 목록 팝업 / 네모 클릭: 종목 상세 페이지로 이동

### 1-5. MAPS 활용 시나리오
- **A. 오늘 시장을 누가 끌어올렸나?** MAP FILTER = S&P 500, 기간 = 1-Day → 가장 큰 초록/빨강 덩어리가 어느 섹터인지 확인 → SIZE BY를 Equal로 바꿔 다시 보기(색이 비슷하면 넓은 상승, 확 달라지면 대형주 쏠림)
- **B. 일시적 반등인가, 진짜 추세인가?** 기간을 1-Day → 1-Week → 1-Month → 3-Month로 바꾸기. 모든 기간에서 초록 = 추세 주도 섹터, 1-Day만 초록이고 1-Month는 빨강 = 반등일 가능성(추격매수 주의)
- **C. 섹터 ETF로 한 번에 보기** MAP FILTER = ETFs, Search ticker에 XLK·XLF·SMH 등을 입력해 위치 확인
- **D. 어디에 돈이 몰리나?** 기간 = Relative Volume → 진하게 칠해진 곳 확인 → 다시 1-Day로 돌려 상승(매수)인지 하락(매도)인지 확인

## PART 2. GROUPS (업종 순위표)

### 2-1. 상단 컨트롤 3개

| 컨트롤 | 선택지 | 설명 |
|---|---|---|
| Group | Sector / Industry / Industry(섹터명) / Country / Capitalization | Sector: 11개 섹터 비교 ✅ 시작은 여기. Industry: 약 140개 세부 산업. Industry(Technology) 등: 특정 섹터 안의 산업만. Capitalization: 대형/중형/소형 규모별 |
| Order By | Name, Market Cap, P/E, 배당, 성장률, Performance(Week/Month/Quarter/Half Year/Year/YTD), Relative Volume, Change % 등 40여 개 | 흐름 체크용은 Performance(Week), Performance(Month), Change %(오늘) |
| Ascending / Descending | 오름차순 / 내림차순 | Descending = 가장 많이 오른 곳이 맨 위 |

표 위쪽 열 이름(예: Perf Week)을 클릭해도 바로 정렬된다. 한 번 더 누르면 순서 반대.

### 2-2. 보기 탭 9개

| 탭 | 보여주는 것 | 활용도 |
|---|---|---|
| Overview | 종목 수, 시총, 배당, P/E, Fwd P/E, PEG, 부채비율, Float Short, 애널리스트 의견, 오늘 등락, 거래량 | ⭐⭐ 섹터 기본 정보 |
| Valuation | P/E, P/S, P/B, EV/EBITDA, 성장률 | ⭐⭐ 어느 섹터가 비싼지/싼지 |
| Financial | ROA, ROE, 마진, 유동비율 | ⭐ 수익성 비교 |
| **Performance** ✅ | Perf Week/Month/Quart/Half/Year/YTD, Avg Volume, Rel Volume, Change %, Volume | ⭐⭐⭐ 흐름 체크의 핵심 표 |
| Custom | 보고 싶은 열만 골라 구성 | ⭐⭐ |
| **Performance Chart** ✅ | 1 Day / 1 Week / 1 Month / 3 Month / Half Year / 1 Year / YTD 수익률을 막대그래프 7개로 | ⭐⭐⭐ 한 화면에 기간별 순위가 다 보임 |
| Spectrum | 섹터별로 한 줄씩, 소속 종목을 오늘 등락률 순으로 빨강→초록 배치 | ⭐⭐ 섹터 내부가 고르게 올랐는지 확인 |
| Charts | 섹터/산업별 미니 차트 모음 | ⭐⭐ 추세 모양 확인 |
| Maps | 그룹 단위 히트맵 | ⭐ |

### 2-3. Performance 표 열 해석
Perf Week/Month/Quart/Half/Year/YTD = 1주/1개월/3개월/6개월/1년/연초 이후 수익률. Avg Volume = 3개월 평균 거래량. **Rel Volume** = 오늘 거래량 ÷ 평균 거래량(1.5 이상이면 평소보다 관심 급증). Change % = 오늘(최근 거래일) 등락률.

### 2-4. Finviz 섹터 이름 ↔ 우리말 ↔ ETF 대응표

| Finviz 표기 | 우리말 | 대응 ETF |
|---|---|---|
| Technology | 정보기술 | XLK |
| Communication Services | 커뮤니케이션 | XLC |
| Consumer Cyclical | 경기소비재(헷갈림 주의) | XLY |
| Consumer Defensive | 필수소비재(헷갈림 주의) | XLP |
| Financial | 금융 | XLF |
| Industrials | 산업재 | XLI |
| Basic Materials | 소재 | XLB |
| Energy | 에너지 | XLE |
| Real Estate | 부동산 | XLRE |
| Healthcare | 헬스케어 | XLV |
| Utilities | 유틸리티 | XLU |

GROUPS는 S&P 500만이 아니라 **미국 상장 종목 전체**를 묶어 계산한다. Finviz의 섹터 분류도 GICS와 조금 달라 XL 섹터 ETF 수익률과 **수치가 정확히 일치하지는 않음** → 방향(순위)을 보는 용도로 쓴다.

### 2-5. GROUPS 활용 시나리오
- **A. 이번 주/이번 달 1등 섹터는?** Group = Sector, 탭 = Performance Chart → 1 Week·1 Month·3 Month 막대에서 매번 상위권인 섹터 = 주도 섹터. 단기만 1등이면 순환매 초기일 수도, 일시적일 수도 있어 다음 주에 다시 확인
- **B. 섹터 안에서 실제로 뭐가 오르나?** Group = Industry(Technology) 같은 관심 섹터, 탭 = Performance, Order By = Performance(Month), Descending
- **C. 새로 떠오르는 산업 찾기** Group = Industry, 탭 = Performance. Perf Month는 낮은데(또는 마이너스) Perf Week가 상위 + Rel Volume 1.5 이상 → 막 돈이 들어오기 시작한 후보
- **D. 시장이 방어 모드로 가나?** 1 Week·1 Month 상위권에 Consumer Defensive·Utilities·Healthcare가 몰려 있으면 경기 둔화/조정 대비 신호, Technology·Consumer Cyclical·Financial이 상위면 위험선호
- **E. 대형주 장인가, 중소형주 장인가?** Group = Capitalization, 탭 = Performance → Mega/Large vs Small/Micro 수익률 비교

## PART 3. 두 화면 함께 쓰는 루틴

**MAPS = 오늘의 온도계 / GROUPS = 추세 기록표.** 둘 다 봐야 "하루짜리 반짝"과 "진짜 흐름"을 구분할 수 있다.

매일 5분(장 마감 후 아침):
- [ ] MAPS(S&P 500, 1-Day): 가장 큰 초록/빨강 섹터 1개씩 확인
- [ ] MAPS SIZE BY = Equal로 한 번 더 → 넓은 상승인지 쏠림인지
- [ ] GROUPS(Sector, Performance Chart): 1 Day 순위가 1 Week 순위와 같은 방향인지

주 1회 20분(주말):
- [ ] GROUPS Performance Chart: 1 Week·1 Month·3 Month 상위 3 / 하위 3 섹터 메모
- [ ] 상위 섹터를 Industry(섹터명)로 들어가서 1등 세부 산업 확인
- [ ] MAPS 기간 = 1-Month로 바꿔 지도 색이 GROUPS 결과와 맞는지 확인
- [ ] MAPS 기간 = Drawdown from 52-Week High → 많이 빠진 섹터(역발상 후보) 체크

## PART 4. 즐겨찾기용 바로가기 URL

| 용도 | 링크 |
|---|---|
| S&P 500 히트맵 | https://finviz.com/map?t=sec |
| 미국 전 종목 히트맵 | https://finviz.com/map?t=sec_all |
| Russell 2000 히트맵 | https://finviz.com/map?t=sec_rut |
| ETF 히트맵 | https://finviz.com/map?t=etf |
| 세계 증시 히트맵 | https://finviz.com/map?t=geo |
| 섹터 기간별 막대그래프 ✅ | https://finviz.com/groups?g=sector&v=210&o=name |
| 섹터 Performance 표(1주 수익률 순) | https://finviz.com/groups?g=sector&v=140&o=-perf1w |
| 전체 산업 1개월 수익률 순 | https://finviz.com/groups?g=industry&v=140&o=-perf4w |
| 기술 섹터 내 산업 비교 | https://finviz.com/groups?g=industry&sg=technology&v=140&o=-perf4w |
| 섹터 Spectrum | https://finviz.com/groups?g=sector&v=310&o=name |

URL 규칙: `g=` 그룹(sector/industry/country/capitalization), `sg=` 섹터 지정(g=industry일 때: technology, financial, energy, healthcare, industrials, basicmaterials, communicationservices, consumercyclical, consumerdefensive, realestate, utilities), `v=` 보기(110 Overview · 120 Valuation · 160 Financial · 140 Performance · 150 Custom · 210 Performance Chart · 310 Spectrum · 410 Charts · 510 Maps), `o=` 정렬(perf1w · perf4w · perf13w · perf26w · perf52w · perfytd · change · relativevolume, 앞에 `-` 붙이면 내림차순), MAPS `t=`(sec · sec_dji · sec_ndx · sec_rut · sec_all · cap · geo · etf).

## PART 5. 초보가 자주 하는 실수
- ❌ **1-Day만 보고 판단** → 하루 색깔은 노이즈가 많음. 반드시 1-Week·1-Month와 같이 볼 것
- ❌ **큰 네모만 보기** → 시총 큰 몇 종목이 지도를 지배함. Equal 모드나 Spectrum으로 내부 폭도 확인
- ❌ **Consumer Cyclical / Defensive 혼동** → Cyclical = 경기소비재(XLY), Defensive = 필수소비재(XLP)
- ❌ **GROUPS 수치 = ETF 수익률로 착각** → 계산 대상 종목이 달라 숫자는 다름. 순위·방향만 참고
- ❌ **초록 = 바로 매수** → 이미 많이 오른 섹터일 수 있음. Drawdown from 52-Week High로 위치를 확인

이 문서는 투자 권유가 아닌 도구 사용법 정리다.

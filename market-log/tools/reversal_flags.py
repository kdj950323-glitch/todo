#!/usr/bin/env python3
"""바닥 반등 참고 지표: '방어 상승일' 횟수(최근 5거래일).

방어 상승일 = 시장(SPY)이 -0.8% 이하로 약한 날, 종목이 +2% 이상 오르고 SPY보다 3%p 이상 더 오른 날.
2026-10 방산주 사례 학습(market-log/learning/2026-10-defense-primes-reversal.md)에서 나온 '추적할 가설'이며,
매수·매도 신호가 아니다(대형주 검증에서 과적합 가능성이 큼). 참고 열로만 쓴다.

사용법 (저장소 루트에서):
  python3 market-log/tools/reversal_flags.py watchlist
      관심종목: state/watchlist_prices.csv + state/prices.csv(SPY) 로 계산
  python3 market-log/tools/reversal_flags.py log-candidates --date 2026-10-21 --json cand.json
      바닥 후보 스크리너 결과(finviz.py rows 출력 JSON 의 rows 배열 또는 {"rows": [...]})의
      ticker/change/industry 를 state/candidate_daily.csv 에 추가(같은 date+ticker 는 건너뜀)
  python3 market-log/tools/reversal_flags.py candidates
      후보: state/candidate_daily.csv 로 계산하고 업종별 동조 카운트(방어 상승일 1회 이상인 종목 수) 출력
출력은 stdout JSON. 기록이 5일 미만이면 days_recorded 로 '누적 중'임을 알린다.
"""
import argparse, csv, json, os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
STATE = os.path.join(ROOT, 'state')
SPY_DROP, STOCK_UP, EXCESS = -0.8, 2.0, 3.0


def read_csv(name):
    p = os.path.join(STATE, name)
    if not os.path.exists(p):
        return []
    return list(csv.DictReader(open(p, encoding='utf-8')))


def spy_returns():
    rows = read_csv('prices.csv')
    out, prev = {}, None
    for r in rows:
        try:
            c = float(r['SPY'])
        except (KeyError, ValueError):
            continue
        if prev:
            out[r['date']] = (c / prev - 1) * 100
        prev = c
    return out


def flags(series, spy):
    """series: {ticker: [(date, ret_pct), ...]} 날짜 오름차순"""
    res = {}
    for t, L in series.items():
        L = [(d, r) for d, r in L if d in spy][-5:]
        n = sum(1 for d, r in L if spy[d] <= SPY_DROP and r >= STOCK_UP and r - spy[d] >= EXCESS)
        res[t] = {'defiance_5d': n, 'days_recorded': len(L),
                  'dates': [d for d, r in L if spy[d] <= SPY_DROP and r >= STOCK_UP and r - spy[d] >= EXCESS]}
    return res


def cmd_watchlist(a):
    rows = read_csv('watchlist_prices.csv')
    by = {}
    for r in rows:
        by.setdefault(r['ticker'], []).append((r['date'], float(r['close'])))
    series = {}
    for t, L in by.items():
        L.sort()
        series[t] = [(L[i][0], (L[i][1] / L[i - 1][1] - 1) * 100) for i in range(1, len(L))]
    print(json.dumps(flags(series, spy_returns()), ensure_ascii=False))


def cmd_log(a):
    data = json.load(open(a.json, encoding='utf-8'))
    rows = data['rows'] if isinstance(data, dict) else data
    p = os.path.join(STATE, 'candidate_daily.csv')
    exist = {(r['date'], r['ticker']) for r in read_csv('candidate_daily.csv')}
    new = not os.path.exists(p)
    n = 0
    with open(p, 'a', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        if new:
            w.writerow(['date', 'ticker', 'change_pct', 'industry'])
        for r in rows:
            t = r.get('ticker')
            if not t or r.get('change') is None or (a.date, t) in exist:
                continue
            w.writerow([a.date, t, f"{float(r['change']):.2f}", r.get('industry', '')])
            n += 1
    print(json.dumps({'added': n, 'date': a.date}))


def cmd_candidates(a):
    rows = read_csv('candidate_daily.csv')
    by, ind = {}, {}
    for r in rows:
        by.setdefault(r['ticker'], []).append((r['date'], float(r['change_pct'])))
        ind[r['ticker']] = r.get('industry', '')
    series = {t: sorted(L) for t, L in by.items()}
    fl = flags(series, spy_returns())
    co = {}
    for t, v in fl.items():
        if v['defiance_5d'] >= 1:
            co.setdefault(ind.get(t) or '?', []).append(t)
    print(json.dumps({'flags': fl, 'industry_cluster': {k: {'count': len(v), 'tickers': v, 'cluster': len(v) >= 3} for k, v in co.items()}}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest='c', required=True)
    s.add_parser('watchlist').set_defaults(fn=cmd_watchlist)
    l = s.add_parser('log-candidates'); l.add_argument('--date', required=True); l.add_argument('--json', required=True); l.set_defaults(fn=cmd_log)
    s.add_parser('candidates').set_defaults(fn=cmd_candidates)
    a = p.parse_args()
    a.fn(a)

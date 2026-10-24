#!/usr/bin/env python3
"""대형주 섹터별 바닥 추적표 (state/universe_large.csv 의 종목, 섹터당 5개).

고점 대비 많이 하락했지만 펀더멘털에 큰 문제가 없는 종목을 단계별로 추려 Notion 페이지 본문(마크다운)으로 만든다.
매수·매도 추천이 아니라 상태 분류다. 모든 수치는 Finviz(screener JSON)에서 읽고 직접 계산하지 않은 값은 없다.

사용법 (저장소 루트에서):
  python3 market-log/tools/bottom_tracker.py --date 2026-10-21
출력:
  market-log/bottom-tracker/YYYY-MM-DD.md   Notion 페이지 본문(루틴이 그대로 replace_content 로 넣는다)
  market-log/state/bottom_tracker.csv       종목별 일간 이력(추가만, 같은 date+ticker 는 건너뜀)
  stdout                                    요약 JSON(단계별 종목 수, 전일 대비 변화)
Finviz 구조가 바뀌어 읽지 못하면 {"error": ...} 를 내고 종료한다.
"""
import argparse, csv, datetime, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import finviz  # noqa: E402

ROOT = os.path.join(HERE, '..')
STATE = os.path.join(ROOT, 'state')
OUT = os.path.join(ROOT, 'bottom-tracker')
SPY_DROP, STOCK_UP, EXCESS = -0.8, 2.0, 3.0
NO_DEBT_CHECK = {'금융', '유틸리티', '부동산'}
STAGES = [
    ('위험', '🔴'), ('가치함정 주의', '⚠️'), ('펀더멘털 미확인', '⚪'), ('바닥 후보(반등 확인)', '🔵'),
    ('바닥 탐색', '🟠'), ('눌림 관찰', '🟡'), ('정상', '🟢'),
]
ICON = dict(STAGES)


def read_csv(path):
    return list(csv.DictReader(open(path, encoding='utf-8'))) if os.path.exists(path) else []


def fetch(view, tickers):
    out = {}
    for i in range(0, len(tickers), 20):
        chunk = tickers[i:i + 20]
        s = finviz.get(f'https://finviz.com/screener.ashx?v={view}&t={",".join(chunk)}')
        rows, _ = finviz.parse_rows(s)
        if rows is None:
            raise RuntimeError(f'v={view} rows JSON not found')
        for x in rows:
            d = dict(x.get('text', {}))
            d.update(x.get('numbers', {}))
            out[d['ticker']] = d
    return out


def fnum(x):
    try:
        return None if x is None else float(x)
    except (TypeError, ValueError):
        return None


def fundamentals(r, sector):
    """(상태, 실패 항목 목록, 미확인 개수). 항목: 영업이익률, 순이익률, 올해 EPS 성장, 내년 EPS 추정, ROE, 부채비율."""
    checks = [
        ('영업이익률 적자', fnum(r.get('operMargin')), lambda v: v > 0),
        ('순이익률 적자', fnum(r.get('netMargin')), lambda v: v > 0),
        ('올해 EPS 역성장', fnum(r.get('epsYoY')), lambda v: v >= 0),
        ('내년 EPS 추정 역성장', fnum(r.get('epsYoY1')), lambda v: v >= 0),
        ('ROE 음수', fnum(r.get('roe')), lambda v: v > 0),
    ]
    if sector not in NO_DEBT_CHECK:
        checks.append(('부채비율≥2', fnum(r.get('debtEq')), lambda v: v < 2))
    fails = [n for n, v, ok in checks if v is not None and not ok(v)]
    miss = sum(1 for n, v, ok in checks if v is None)
    if miss >= 3:
        return '미확인', fails, miss
    return ('양호' if not fails else '주의' if len(fails) == 1 else '위험'), fails, miss


def stage_of(off_high, fund, sma20, rsi):
    if off_high is None:
        return '정상'
    if off_high <= -20:
        if fund == '위험':
            return '위험'
        if fund == '주의':
            return '가치함정 주의'
        if fund == '미확인':
            return '펀더멘털 미확인'
        if sma20 is not None and rsi is not None and sma20 >= 0 and rsi >= 45:
            return '바닥 후보(반등 확인)'
        return '바닥 탐색'
    if off_high <= -10:
        return '눌림 관찰' if fund == '양호' else '정상'
    return '정상'


def leader_score(r, spy13):
    """주도주 4조건 충족 개수: 3개월 수익률 > SPY, 50일선 위, 200일선 위, 52주 고점 대비 -10% 이내."""
    p13, s50, s200, off = fnum(r.get('perf13w')), fnum(r.get('sma50')), fnum(r.get('sma200')), fnum(r.get('high52w'))
    ok = [p13 is not None and spy13 is not None and p13 > spy13, s50 is not None and s50 > 0,
          s200 is not None and s200 > 0, off is not None and off >= -10]
    return sum(ok), ok


SECTOR_ETF = [('정보기술', 'XLK', '기술주'), ('커뮤니케이션', 'XLC', '통신·미디어주'), ('경기소비재', 'XLY', '경기소비재'),
              ('필수소비재', 'XLP', '필수소비재'), ('헬스케어', 'XLV', '헬스케어'), ('금융', 'XLF', '금융주'),
              ('산업재', 'XLI', '산업재'), ('에너지', 'XLE', '에너지'), ('소재', 'XLB', '소재'),
              ('유틸리티', 'XLU', '유틸리티'), ('부동산', 'XLRE', '부동산')]


def etf_flow_lines(date):
    """섹터 ETF 11개를 SPY 와 비교해 쉬운 문장과 표로 만든다. 거래량 신호는 실제 자금 이동이 아니라 추정이다."""
    try:
        d = fetch(141, [e for _, e, _ in SECTOR_ETF] + ['SPY'])
    except Exception:
        return []
    spy = d.get('SPY') or {}
    sp = [fnum(spy.get(k)) for k in ('perf1w', 'perf4w', 'perf13w')]
    if None in sp:
        return []
    rows = []
    for sct, etf, nick in SECTOR_ETF:
        r = d.get(etf)
        if not r:
            continue
        p = [fnum(r.get(k)) for k in ('perf1w', 'perf4w', 'perf13w')]
        if None in p:
            continue
        ex = [p[i] - sp[i] for i in range(3)]
        rv, ch = fnum(r.get('relativeVolume')), fnum(r.get('change')) or 0.0
        if ex[2] > 0 and ex[1] > 0:
            flow = '계속 강함'
        elif ex[2] > 0:
            flow = '강했지만 최근 힘 빠짐'
        elif ex[1] > 0:
            flow = '약했지만 최근 돌아오는 중'
        else:
            flow = '계속 약함'
        vol = '보통'
        if rv is not None and rv >= 1.3:
            vol = '유입 추정 (거래량↑ 상승)' if ch >= 0 else '유출 추정 (거래량↑ 하락)'
        rows.append({'sct': sct, 'etf': etf, 'nick': nick, 'p': p, 'ex': ex, 'flow': flow, 'vol': vol, 'rv': rv})
    if len(rows) < 8:
        return []
    hp = os.path.join(STATE, 'sector_etf.csv')
    hh = read_csv(hp)
    have = {(h['date'], h['etf']) for h in hh}
    with open(hp, 'a', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        if not hh:
            w.writerow(['date', 'etf', 'perf1w', 'perf4w', 'perf13w', 'ex1w', 'ex4w', 'ex13w', 'relvol'])
        for x in rows:
            if (date, x['etf']) not in have:
                w.writerow([date, x['etf']] + [round(v, 2) for v in x['p']] + [round(v, 2) for v in x['ex']] + ['' if x['rv'] is None else round(x['rv'], 2)])
    by13 = sorted(rows, key=lambda x: -x['ex'][2])
    rank = {x['sct']: i + 1 for i, x in enumerate(by13)}
    ln = ['## 섹터 ETF 자금 흐름', '섹터를 대표하는 ETF 11개(XLK, XLV 등)를 미국 대표 지수 ETF인 SPY와 비교했습니다. **SPY보다 강하다**는 말은 같은 기간 SPY보다 더 많이 올랐거나 덜 내렸다는 뜻으로, 시장에서 돈이 상대적으로 그 섹터로 몰렸다고 읽습니다.']
    strong = [x for x in by13 if x['ex'][2] > 0]
    weak = by13[-1]
    ln.append('- **한 줄 결론**: 최근 3개월 기준 SPY(%+.1f%%)보다 강한 섹터는 %s입니다. 가장 약한 섹터는 %s(SPY보다 %+.1f%%p)입니다.' % (
        sp[2], '·'.join(x['nick'] for x in strong) if strong else '없음', weak['nick'], weak['ex'][2]))
    tech = next((x for x in rows if x['sct'] == '정보기술'), None)
    if tech:
        better = [x['nick'] for x in rows if x is not tech and x['ex'][2] > tech['ex'][2] and x['ex'][1] > tech['ex'][1]]
        worse = [x['nick'] for x in rows if x is not tech and x['ex'][2] < tech['ex'][2] and x['ex'][1] < tech['ex'][1]]
        ln.append('- **기술주와 비교**: 기술주는 11개 섹터 중 3개월 기준 %d위입니다. 3개월·1개월 모두 기술주보다 더 좋은 섹터는 %s, 모두 기술주보다 나쁜 섹터는 %s입니다.' % (
            rank['정보기술'], '·'.join(better) if better else '없음', '·'.join(worse) if worse else '없음'))
    back = [x['nick'] for x in rows if x['flow'] == '약했지만 최근 돌아오는 중']
    fade = [x['nick'] for x in rows if x['flow'] == '강했지만 최근 힘 빠짐']
    if back:
        ln.append('- **최근 자금이 돌아오는 섹터**: %s. 3개월로는 시장보다 약했지만 최근 1개월은 SPY보다 강해졌습니다.' % '·'.join(back))
    if fade:
        ln.append('- **힘이 빠지는 섹터**: %s. 3개월로는 시장보다 강했지만 최근 1개월은 SPY보다 약해졌습니다.' % '·'.join(fade))
    inflow = [x['nick'] for x in rows if x['vol'].startswith('유입')]
    outflow = [x['nick'] for x in rows if x['vol'].startswith('유출')]
    if inflow or outflow:
        ln.append('- **오늘 거래량 신호**: 거래량이 평소의 1.3배 이상 터진 섹터 중 오른 쪽은 %s, 내린 쪽은 %s입니다. 실제 자금 이동이 아니라 거래량과 방향으로 짐작한 추정입니다.' % ('·'.join(inflow) or '없음', '·'.join(outflow) or '없음'))
    ln.append('<table header-row="true">\n<tr><td>섹터</td><td>ETF</td><td>1주</td><td>1개월</td><td>3개월</td><td>1개월 SPY 대비</td><td>3개월 SPY 대비</td><td>쉬운 풀이</td><td>거래량 신호</td></tr>')
    for x in by13:
        ln.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            x['sct'], x['etf'], pct(x['p'][0]), pct(x['p'][1]), pct(x['p'][2]), pct(x['ex'][1]), pct(x['ex'][2]), x['flow'], x['vol']))
    ln.append('</table>')
    ln.append('표는 3개월 기준 강한 순서입니다. 쉬운 풀이는 3개월과 1개월을 함께 본 분류입니다(계속 강함 / 강했지만 최근 힘 빠짐 / 약했지만 최근 돌아오는 중 / 계속 약함). 미국 시장은 기관·외국인·개인별 일간 매매 데이터가 공개되지 않아 거래량으로 대신 추정했으며, 참고용이고 매수·매도 추천이 아닙니다.')
    return ln


def spy_returns():
    rows, out, prev = read_csv(os.path.join(STATE, 'prices.csv')), {}, None
    for r in rows:
        try:
            c = float(r['SPY'])
        except (KeyError, ValueError):
            continue
        if prev:
            out[r['date']] = (c / prev - 1) * 100
        prev = c
    return out


def defiance(hist, spy):
    """hist: [(date, change_pct)] 날짜 오름차순. 최근 5거래일 안의 방어 상승일 횟수와 기록 일수."""
    L = [(d, c) for d, c in hist if d in spy][-5:]
    n = sum(1 for d, c in L if spy[d] <= SPY_DROP and c >= STOCK_UP and c - spy[d] >= EXCESS)
    return n, len(L)


def rsi_s(v):
    return '-' if v is None else '%.0f' % v


def price_s(v):
    return '-' if v is None else '{:,.2f}'.format(v)


def fmt_cap(m):
    m = fnum(m)
    if m is None:
        return '-'
    return f'{m / 1e6:.2f}T' if m >= 1e6 else f'{m / 1e3:,.0f}B'


def pct(v, d=1, sign=True):
    return '-' if v is None else (f'{v:+.{d}f}%' if sign else f'{v:.{d}f}%')


def earn(r, today):
    s = r.get('earningsDate')
    if not s:
        return '-'
    try:
        d = datetime.datetime.fromisoformat(s[:19]).date()
    except ValueError:
        return '-'
    n = (d - today).days
    return f'{d:%m/%d} (D-{n})' if n >= 0 else '미확인(지난 날짜)'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--note', default='')
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.date)
    uni = read_csv(os.path.join(STATE, 'universe_large.csv'))
    tk = [u['ticker'] for u in uni]
    try:
        v171, v121, v161, v141 = fetch(171, tk), fetch(121, tk), fetch(161, tk), fetch(141, tk)
        try:
            spy13 = fnum(fetch(141, ['SPY']).get('SPY', {}).get('perf13w'))
        except Exception:
            spy13 = None
    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False))
        return 1
    hist_path = os.path.join(STATE, 'bottom_tracker.csv')
    hist = read_csv(hist_path)
    by_hist = {}
    for h in hist:
        by_hist.setdefault(h['ticker'], []).append((h['date'], float(h['change']) if h['change'] else 0.0))
    prev_dates = sorted({h['date'] for h in hist if h['date'] < a.date})
    prev_stage = {h['ticker']: h['stage'] for h in hist if prev_dates and h['date'] == prev_dates[-1] and h['stage']}
    spy = spy_returns()
    rows = []
    for u in uni:
        t = u['ticker']
        r = {}
        for src in (v121, v161, v171, v141):
            r.update(src.get(t, {}))
        if not r:
            rows.append({'u': u, 'missing': True})
            continue
        fund, fails, miss = fundamentals(r, u['sector'])
        off, s20, s200, rsi = fnum(r.get('high52w')), fnum(r.get('sma20')), fnum(r.get('sma200')), fnum(r.get('rsi'))
        stg = stage_of(off, fund, s20, rsi)
        h = [x for x in by_hist.get(t, []) if x[0] != a.date] + [(a.date, fnum(r.get('change')) or 0.0)]
        h.sort()
        dn, dd = defiance(h, spy)
        note = []
        if fails:
            note.append('/'.join(fails))
        if rsi is not None and rsi <= 35:
            note.append('과매도')
        if t in prev_stage and prev_stage[t] != stg:
            note.append(f'전일 {prev_stage[t]}→')
        lead = leader_score(r, spy13)
        rows.append({'lead': lead, 'u': u, 'r': r, 'fund': fund, 'stage': stg, 'off': off, 's20': s20, 's200': s200, 'rsi': rsi,
                     'dn': dn, 'dd': dd, 'note': ' · '.join(note), 'earn': earn(r, today), 'miss': miss})
    # 이력 기록(추가만)
    exist = {(h['date'], h['ticker']) for h in hist}
    new = not os.path.exists(hist_path)
    with open(hist_path, 'a', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        if new:
            w.writerow(['date', 'ticker', 'price', 'change', 'off_high', 'sma20', 'sma200', 'rsi', 'fund', 'stage'])
        for x in rows:
            if x.get('missing') or (a.date, x['u']['ticker']) in exist:
                continue
            r = x['r']
            w.writerow([a.date, x['u']['ticker'], r.get('price'), r.get('change'), x['off'], x['s20'], x['s200'], x['rsi'], x['fund'], x['stage']])
    # Notion 마크다운
    ok = [x for x in rows if not x.get('missing')]
    cnt = {s: sum(1 for x in ok if x['stage'] == s) for s, _ in STAGES}
    lines = []
    lines.append('<callout icon="🏛️" color="blue_bg">\n\t**대형주 섹터별 현황(주도주 · 바닥 추적)** — 섹터별 시가총액 상위 5개(미국 본사, 총 %d종목)를 매일 갱신합니다. 기준일 %s. 위쪽은 강세·주도주 점검, 아래쪽은 고점 대비 많이 하락했지만 펀더멘털에 큰 문제가 없는 종목을 **단계**로 분류한 참고 자료이며 매수·매도 추천이 아닙니다.%s\n</callout>' % (len(ok), a.date, ('\n\t' + a.note) if a.note else ''))
    # 섹터별 주도주 현황 (state/leaders.csv 에 이력 기록)
    lp = os.path.join(STATE, 'leaders.csv')
    lhist = read_csv(lp)
    ldates = sorted({h['date'] for h in lhist if h['date'] < a.date})
    prev_lead = {h['ticker'] for h in lhist if ldates and h['date'] == ldates[-1] and h['score'] == '4'}
    lexist = {(h['date'], h['ticker']) for h in lhist}
    lnew = not os.path.exists(lp)
    with open(lp, 'a', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        if lnew:
            w.writerow(['date', 'ticker', 'sector', 'perf4w', 'perf13w', 'excess13', 'sma50', 'off_high', 'score'])
        for x in ok:
            if (a.date, x['u']['ticker']) in lexist:
                continue
            r = x['r']
            p13 = fnum(r.get('perf13w'))
            w.writerow([a.date, x['u']['ticker'], x['u']['sector'], r.get('perf4w'), r.get('perf13w'),
                        '' if p13 is None or spy13 is None else round(p13 - spy13, 2), r.get('sma50'), x['off'], x['lead'][0]])
    sectors = []
    for x in ok:
        if x['u']['sector'] not in sectors:
            sectors.append(x['u']['sector'])
    def ex13(x):
        p13 = fnum(x['r'].get('perf13w'))
        return None if p13 is None or spy13 is None else p13 - spy13
    lines.extend(etf_flow_lines(a.date))
    lines.append('## 섹터별 주도주 현황')
    lines.append('SPY의 최근 3개월 수익률은 %s입니다. **주도주**는 아래 4가지를 모두 충족한 종목, **근접**은 3가지를 충족한 종목입니다: ① 3개월 수익률이 SPY보다 높음 ② 50일선 위 ③ 200일선 위 ④ 52주 고점 대비 -10%% 이내. 강세 종목을 모아 본 참고 자료이며 매수 추천이 아닙니다.' % pct(spy13))
    lines.append('<table header-row="true">\n<tr><td>섹터</td><td>주도주</td><td>근접</td><td>종목 수</td><td>평균 3개월</td><td>SPY 대비 평균</td><td>주도주 종목</td></tr>')
    srows = []
    for sct in sectors:
        g = [x for x in ok if x['u']['sector'] == sct]
        lead4 = [x for x in g if x['lead'][0] == 4]
        near = [x for x in g if x['lead'][0] == 3]
        p13s = [fnum(x['r'].get('perf13w')) for x in g if fnum(x['r'].get('perf13w')) is not None]
        e = [ex13(x) for x in g if ex13(x) is not None]
        srows.append((sum(e) / len(e) if e else -999, sct, len(lead4), len(near), len(g),
                      sum(p13s) / len(p13s) if p13s else None, sum(e) / len(e) if e else None,
                      ', '.join(x['u']['ticker'] for x in sorted(lead4, key=lambda y: -(ex13(y) or -999)))))
    for _, sct, n4, n3, n, avg, avge, names in sorted(srows, key=lambda t: -t[0]):
        lines.append('<tr><td>%s</td><td>%d</td><td>%d</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (sct, n4, n3, n, pct(avg), pct(avge), names or '-'))
    lines.append('</table>')
    lines.append('### 종목별 주도 점검')
    lines.append('<table header-row="true">\n<tr><td>섹터</td><td>티커</td><td>종목</td><td>1개월</td><td>3개월</td><td>SPY 대비</td><td>50일선</td><td>고점 대비</td><td>거래량 배수</td><td>충족</td><td>판정</td><td>비고</td></tr>')
    srank = {s_[1]: i for i, s_ in enumerate(sorted(srows, key=lambda t: -t[0]))}
    for x in sorted(ok, key=lambda y: (srank[y['u']['sector']], -(ex13(y) if ex13(y) is not None else -999))):
        r = x['r']
        sc = x['lead'][0]
        verdict = {4: '🟢 주도', 3: '🟡 근접'}.get(sc, '-')
        t = x['u']['ticker']
        nt = ('신규 주도' if sc == 4 and t not in prev_lead else ('주도 이탈' if sc < 4 and t in prev_lead else '')) if ldates else ''
        rv = fnum(r.get('relativeVolume'))
        lines.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%d/4</td><td>%s</td><td>%s</td></tr>' % (
            x['u']['sector'], t, x['u']['name_ko'], pct(fnum(r.get('perf4w'))), pct(fnum(r.get('perf13w'))), pct(ex13(x)),
            pct(fnum(r.get('sma50'))), pct(x['off']), '-' if rv is None else '%.1f배' % rv, sc, verdict, nt))
    lines.append('</table>')
    lines.append('## 오늘의 단계 요약')
    lines.append('<table header-row="true">\n<tr><td>단계</td><td>종목 수</td><td>뜻</td></tr>')
    meaning = {
        '위험': '고점 대비 -20% 이하 + 펀더멘털 항목 2개 이상 문제',
        '가치함정 주의': '고점 대비 -20% 이하 + 펀더멘털 항목 1개 문제 (싸 보여도 이유가 있을 수 있음)',
        '펀더멘털 미확인': '-20% 이하이지만 Finviz 재무 자료가 부족해 점검 불가 (직접 확인 필요, 신규 상장 등)',
        '바닥 후보(반등 확인)': '-20% 이하 + 펀더멘털 양호 + 종가가 20일선 위 + RSI 45 이상 (반등이 확인되기 시작)',
        '바닥 탐색': '-20% 이하 + 펀더멘털 양호 + 아직 20일선 아래 (바닥 형성 여부 지켜보는 단계)',
        '눌림 관찰': '-10~-20% 하락 + 펀더멘털 양호',
        '정상': '고점 대비 -10% 이내이거나 하락했지만 펀더멘털 문제가 있는 눌림',
    }
    for s, ic in STAGES:
        lines.append(f'<tr><td>{ic} {s}</td><td>{cnt[s]}</td><td>{meaning[s]}</td></tr>')
    lines.append('</table>')
    focus = [x for x in ok if x['stage'] != '정상']
    order = {s: i for i, (s, _) in enumerate(STAGES[::-1])}
    focus.sort(key=lambda x: (-['정상', '눌림 관찰', '바닥 탐색', '바닥 후보(반등 확인)', '펀더멘털 미확인', '가치함정 주의', '위험'].index(x['stage']), x['off'] if x['off'] is not None else 0))
    lines.append('## 관찰 대상 (정상 제외)')
    if not focus:
        lines.append('오늘은 고점 대비 -10% 이하로 내린 종목이 없습니다.')
    else:
        lines.append('<table header-row="true">\n<tr><td>단계</td><td>섹터</td><td>티커</td><td>종목</td><td>고점 대비</td><td>20일선 대비</td><td>RSI</td><td>방어 상승일(5일)</td><td>펀더멘털</td><td>다음 실적</td><td>비고</td></tr>')
        for x in focus:
            r = x['r']
            dn = f"{x['dn']}회" + ('' if x['dd'] >= 5 else f" (누적 {x['dd']}일)")
            lines.append(f"<tr><td>{ICON[x['stage']]} {x['stage']}</td><td>{x['u']['sector']}</td><td>{x['u']['ticker']}</td><td>{x['u']['name_ko']}</td><td>{pct(x['off'])}</td><td>{pct(x['s20'])}</td><td>{rsi_s(x['rsi'])}</td><td>{dn}</td><td>{x['fund']}</td><td>{x['earn']}</td><td>{x['note']}</td></tr>")
        lines.append('</table>')
    lines.append('## 섹터별 전체 현황')
    lines.append('<table header-row="true">\n<tr><td>섹터</td><td>티커</td><td>종목</td><td>시총(USD)</td><td>종가</td><td>일간</td><td>고점 대비</td><td>20일선</td><td>200일선</td><td>RSI</td><td>방어 상승일</td><td>펀더멘털</td><td>단계</td></tr>')
    for x in rows:
        u = x['u']
        if x.get('missing'):
            lines.append(f"<tr><td>{u['sector']}</td><td>{u['ticker']}</td><td>{u['name_ko']}</td><td colspan=\"10\">조회 실패</td></tr>")
            continue
        r = x['r']
        px = price_s(fnum(r.get('price')))
        dn = str(x['dn']) + ('' if x['dd'] >= 5 else '(%d일)' % x['dd'])
        chg = pct(fnum(r.get('change')), 2)
        lines.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s %s</td></tr>' % (
            u['sector'], u['ticker'], u['name_ko'], fmt_cap(r.get('marketCap')), px, chg, pct(x['off']), pct(x['s20']), pct(x['s200']),
            rsi_s(x['rsi']), dn, x['fund'], ICON[x['stage']], x['stage']))
    lines.append('</table>')
    lines.append('## 읽는 법과 한계')
    lines.append('- **고점 대비**는 Finviz의 52주 고점 대비 %, **20일선·200일선**은 그 이동평균 대비 %, **RSI**는 14일 기준(30 이하 과매도)입니다.\n'
                 '- **펀더멘털**은 Finviz 수치 6개로 만든 간이 점검입니다: 영업이익률 흑자, 순이익률 흑자, 올해 EPS 성장 0 이상, 내년 EPS 추정 성장 0 이상, ROE 양수, 부채비율 2 미만(금융·유틸리티·부동산은 부채비율 제외; 자사주 매입이 많은 기업은 자본이 작아 부채비율이 높게 나올 수 있어 HD·MCD 같은 경우 과대평가될 수 있음). 모두 통과=양호, 1개 실패=주의, 2개 이상=위험, 자료 3개 이상 없음=미확인. 분기 실적 추세, 가이던스, 업황 같은 정성 요소는 반영하지 않으므로 관심이 가는 종목은 직접 실적과 뉴스를 확인해야 합니다.\n'
                 '- **방어 상승일**은 시장(SPY)이 -0.8% 이하인 날 종목이 +2% 이상 오르고 SPY보다 3%p 이상 더 오른 날의 최근 5거래일 횟수입니다(참고 가설, 근거 약함). 필수소비재·유틸리티·헬스케어처럼 시장이 약한 날 오히려 오르기 쉬운 방어 성격 종목은 횟수가 높게 나오므로, 고점 대비 하락이 큰 종목에서만 의미를 둡니다. 기록이 쌓이기 전에는 "누적 N일"로 표시합니다.\n'
                 '- **다음 실적**은 Finviz 값이며 이미 지난 날짜가 남아 있으면 "미확인"으로 표시합니다.\n'
                 '- 단계는 "지금 상태"를 나눈 것일 뿐 매수·매도 시점을 알려 주지 않습니다. 대형주라도 추가 하락할 수 있습니다.')
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f'{a.date}.md')
    open(p, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    changes = [f"{x['u']['ticker']}: {prev_stage[x['u']['ticker']]}→{x['stage']}" for x in ok if x['u']['ticker'] in prev_stage and prev_stage[x['u']['ticker']] != x['stage']]
    print(json.dumps({'date': a.date, 'file': os.path.relpath(p, ROOT), 'stage_counts': cnt, 'changes_vs_prev': changes,
                      'missing': [x['u']['ticker'] for x in rows if x.get('missing')]}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""'시장 점유율 1위' 기업 일일 추적 (state/leaders_kr.csv 의 '확인'·'후보' 종목).

강의 프레임워크(참고용, 매수 추천 아님)에 맞춘 상태를 계산해 kr-leaders/daily/YYYY-MM-DD.md 와
state/kr_status.csv(이력), state/kr_flow.csv(지수 투자자 수급 이력)를 만든다.
  python3 kr-leaders/tools/track.py [--date YYYY-MM-DD]
기준:
  시장 구간   코스닥 지수의 '최근 10거래일 최고 종가 대비 현재 낙폭'(2주 낙폭). -10% 이내 평상시 / -10~-15% 낙폭과대 구간 / -15% 이하 바겐세일 구간
  브레이크    구간 안(최근 5거래일 낙폭 -10% 이하 경험)에서 지수 일봉이 양봉이고 전일보다 오르며 마감한 첫 날(전일도 오른 날이면 반등 지속)
  종목 필터   부채비율 200% 미만, 영업이익 흑자, 배당 여부, 2년 안 저점 대비 10배 이상 상승 이력(제외 후보)
  엔벨로프    20일 이동평균 ±20% (하단=낙폭과대, 상단=과열)
출력은 모두 '상태 분류'이며 매수·매도 시점을 알려 주지 않는다.
"""
import argparse, csv, datetime, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import krlib as K  # noqa: E402

DAILY = os.path.join(K.ROOT, 'daily')
STATUS_HEAD = ['date', 'code', 'name', 'close', 'chg', 'off52', 'dd10', 'env', 'debt', 'op', 'dps', 'mult2y', 'state', 'flow', 'f20', 'o20', 'hold_chg']
FLOW_HEAD = ['date', 'market', 'personal', 'foreign', 'institutional']


def pct(v, d=1, sign=True):
    return '-' if v is None else (('%+.' + str(d) + 'f%%') if sign else ('%.' + str(d) + 'f%%')) % v


def fmt(v, d=0):
    return '-' if v is None else ('{:,.%df}' % d).format(v)


def regime(ic):
    """지수 일봉(오름차순) → 구간 정보"""
    c = [x['c'] for x in ic]
    if len(c) < 12:
        return None
    last = ic[-1]
    dd10 = (c[-1] / max(c[-10:]) - 1) * 100
    dd20 = (c[-1] / max(c[-20:]) - 1) * 100
    recent_dd = min((c[i] / max(c[max(0, i - 9):i + 1]) - 1) * 100 for i in range(len(c) - 5, len(c)))
    zone = '바겐세일 구간' if dd10 <= -15 else '낙폭과대 구간' if dd10 <= -10 else '평상시'
    in_zone = recent_dd <= -10
    up_close = last['c'] > last['o'] and last['c'] > ic[-2]['c']
    prev_up = len(ic) >= 3 and ic[-2]['c'] > ic[-3]['c']  # 전일도 오른 날이면 '첫 반등'이 아니라 반등 지속
    brk = in_zone and up_close and not prev_up
    cont = in_zone and up_close and prev_up
    return {'close': c[-1], 'chg': (c[-1] / c[-2] - 1) * 100, 'dd10': dd10, 'dd20': dd20, 'zone': zone, 'recent_dd': recent_dd,
            'break': brk, 'cont': cont, 'up_close': up_close, 'date': last['d']}


def latest_confirmed(row, cols):
    """결산 확정 컬럼(예상치 제외) 중 값이 있는 가장 최근 값 (키, 값)"""
    for k in sorted(row, reverse=True):
        if not cols.get(k, ('', True))[1] and row[k] is not None:
            return k, row[k]
    return None, None


def stock_row(u, idx_dd10):
    code = u['code']
    info = K.integration(code)
    inf = info['info']
    cs = K.candles(code, 400)
    wk = K.http_json('https://api.stock.naver.com/chart/domestic/item/%s?periodType=weekCandle&startDateTime=20200101&endDateTime=%s'
                     % (code, datetime.date.today().strftime('%Y%m%d')))['priceInfos']
    close = cs[-1]['c'] if cs else None
    chg = (cs[-1]['c'] / cs[-2]['c'] - 1) * 100 if len(cs) >= 2 else None
    hi52, lo52 = K.num(inf.get('highPriceOf52Weeks')), K.num(inf.get('lowPriceOf52Weeks'))
    off52 = (close / hi52 - 1) * 100 if close and hi52 else None
    closes = [x['c'] for x in cs]
    dd10 = (closes[-1] / max(closes[-10:]) - 1) * 100 if len(closes) >= 10 else None
    s20 = K.sma(closes, 20)
    env = None
    if s20 and close:
        r = close / s20 - 1
        env = '하단 이탈' if r <= -0.2 else '상단 과열' if r >= 0.2 else '밴드 안(%+.0f%%)' % (r * 100)
    low2y = min([w['lowPrice'] for w in wk if w.get('lowPrice')] or [None]) if wk else None
    mult2y = (close / low2y) if close and low2y else None
    ann, acols = K.finance(code, 'annual')
    _, debt = latest_confirmed(ann.get('debt', {}), acols)
    _, op = latest_confirmed(ann.get('op', {}), acols)
    _, dps = latest_confirmed(ann.get('dps', {}), acols)
    qtr, qcols = K.finance(code, 'quarter')
    qyoy = {}
    for key, nm in (('sales', '매출'), ('op', '영업이익'), ('ni', '순이익')):
        k, v = latest_confirmed(qtr.get(key, {}), qcols)
        prev = qtr.get(key, {}).get(str(int(k) - 100)) if k else None
        if v is not None and prev not in (None, 0):
            qyoy[nm] = (v - prev) / abs(prev) * 100
    ttm = None
    qs = [k for k in sorted(qtr.get('op', {}), reverse=True) if not qcols.get(k, ('', True))[1] and qtr['op'][k] is not None][:4]
    if len(qs) == 4:
        ttm = sum(qtr['op'][k] for k in qs)
    flow5 = {'foreign': 0, 'organ': 0, 'individual': 0}
    for f in info['flow'][:5]:
        flow5['foreign'] += K.num(f.get('foreignerPureBuyQuant')) or 0
        flow5['organ'] += K.num(f.get('organPureBuyQuant')) or 0
        flow5['individual'] += K.num(f.get('individualPureBuyQuant')) or 0
    try:
        sig = K.flow_signal(K.trend(code, 60))
    except Exception:
        sig = None
    return {'u': u, 'close': close, 'chg': chg, 'off52': off52, 'dd10': dd10, 'env': env, 'debt': debt, 'op': op, 'dps': dps, 'mult2y': mult2y,
            'qyoy': qyoy, 'ttm': ttm, 'flow5': flow5, 'sig': sig, 'dyield': K.num(inf.get('dividendYieldRatio')), 'per': K.num(inf.get('per')), 'pbr': K.num(inf.get('pbr'))}


def classify(r, fin_exempt):
    """(상태, 사유목록). 제외 > 주의 > 정상"""
    why = []
    turn = r['op'] is not None and r['op'] <= 0 and r.get('ttm') is not None and r['ttm'] > 0  # 직전 사업연도 적자지만 최근 4분기 합산은 흑자
    if r['op'] is not None and r['op'] <= 0 and not turn:
        why.append('영업적자')
    if r['mult2y'] and r['mult2y'] >= 10:
        why.append('2년 저점 대비 %.0f배 상승' % r['mult2y'])
    if why:
        return '제외 후보', why
    if not fin_exempt and r['debt'] is not None and r['debt'] >= 200:
        why.append('부채비율 %.0f%%' % r['debt'])
    if r['dps'] is not None and r['dps'] <= 0:
        why.append('무배당')
    if turn:
        why.append('직전 연도 영업적자, 최근 4분기 합산 흑자(%s억)' % '{:,.0f}'.format(r['ttm']))
    if r['op'] is None:
        why.append('영업이익 미확인')
    return ('주의' if why else '정상'), why


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default='')
    a = ap.parse_args()
    leaders = [r for r in K.read_csv('leaders_kr.csv') if r['status'] in ('확인', '후보')]
    if not leaders:
        print(json.dumps({'error': 'leaders_kr.csv 비어 있음 - discover.py 먼저'}, ensure_ascii=False))
        return 1
    ics = {m: K.index_candles(m, 2) for m in ('KOSDAQ', 'KOSPI')}
    reg = {m: regime(ics[m]) for m in ics}
    date = a.date or ics['KOSDAQ'][-1]['d']
    flows = {}
    for m in ics:
        try:
            flows[m] = K.index_flow(m)
        except Exception:
            flows[m] = None
    uni = {u['code']: u for u in K.read_csv('universe_kr.csv')}
    rows, fails = [], []
    def work(L):
        r = stock_row(L, reg['KOSDAQ']['dd10'] if reg['KOSDAQ'] else None)
        r['u'] = L
        r['mcap'] = float(uni.get(L['code'], {}).get('mcap') or 0)
        fe = '금융업' in (L.get('note') or '')
        r['state'], r['why'] = classify(r, fe)
        r['fin_exempt'] = fe
        return r

    # 종목별 호출이 5~6번이라 순차로는 클라우드에서 2분 넘게 걸려 8개씩 병렬 처리
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [(L, ex.submit(work, L)) for L in leaders]
    for L, fu in futs:
        try:
            rows.append(fu.result())
        except Exception as e:
            fails.append('%s %s: %s' % (L['code'], L['name'], str(e)[:80]))
    # 이력 저장
    st = K.read_csv('kr_status.csv')
    st = [x for x in st if x['date'] != date]
    for r in rows:
        st.append({'date': date, 'code': r['u']['code'], 'name': r['u']['name'], 'close': r['close'], 'chg': '%.2f' % r['chg'] if r['chg'] is not None else '',
                   'off52': '%.1f' % r['off52'] if r['off52'] is not None else '', 'dd10': '%.1f' % r['dd10'] if r['dd10'] is not None else '',
                   'env': r['env'], 'debt': r['debt'], 'op': r['op'], 'dps': r['dps'], 'mult2y': '%.1f' % r['mult2y'] if r['mult2y'] else '', 'state': r['state'],
                   'flow': (r['sig']['label'] + (' · ' + r['sig']['turn'] if r['sig']['turn'] else '')) if r['sig'] else '',
                   'f20': '%.1f' % r['sig']['f20'] if r['sig'] else '', 'o20': '%.1f' % r['sig']['o20'] if r['sig'] else '',
                   'hold_chg': '%.2f' % r['sig']['hold_chg'] if r['sig'] and r['sig']['hold_chg'] is not None else ''})
    K.write_csv('kr_status.csv', st, STATUS_HEAD)
    fl = [x for x in K.read_csv('kr_flow.csv') if x['date'] != date]
    for m, f in flows.items():
        if f:
            fl.append({'date': date, 'market': m, 'personal': f['personal'], 'foreign': f['foreign'], 'institutional': f['institutional']})
    K.write_csv('kr_flow.csv', fl, FLOW_HEAD)
    # 마크다운
    L = []
    L.append('<callout>\n\t**국내 시장 점유율 1위 기업 추적** — 기준일 %s. 뉴스에서 "시장 점유율 1위"로 소개된 코스피·코스닥 상장사를 모아 매일 상태를 점검하는 참고 자료입니다. 강의에서 소개된 기준(지수 낙폭 구간, 재무 3가지, 엔벨로프)에 맞춘 **상태 분류**이며 매수·매도 추천이 아닙니다.\n</callout>' % date)
    L.append('## 오늘의 시장 구간')
    L.append('<table header-row="true">\n<tr><td>지수</td><td>종가</td><td>일간</td><td>2주 낙폭</td><td>4주 낙폭</td><td>구간</td><td>브레이크 신호</td><td>개인(억)</td><td>외국인(억)</td><td>기관(억)</td></tr>')
    for m in ('KOSDAQ', 'KOSPI'):
        g, f = reg[m], flows.get(m) or {}
        if not g:
            continue
        L.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            '코스닥' if m == 'KOSDAQ' else '코스피', fmt(g['close'], 2), pct(g['chg'], 2), pct(g['dd10']), pct(g['dd20']), g['zone'],
            '발생' if g['break'] else ('반등 지속(신호 이후)' if g['cont'] else ('양봉 마감(구간 밖)' if g['up_close'] else '없음')), fmt(f.get('personal')), fmt(f.get('foreign')), fmt(f.get('institutional'))))
    L.append('</table>')
    kq, kp = reg['KOSDAQ'], reg['KOSPI']
    if kq:
        zone_txt = {'평상시': '코스닥 2주 낙폭이 -10% 이내라 강의 기준상 평상시(대기)입니다.',
                    '낙폭과대 구간': '코스닥 2주 낙폭이 -10%~-15%라 강의 기준상 낙폭과대주 방식으로 대응하는 구간입니다.',
                    '바겐세일 구간': '코스닥 2주 낙폭이 -15% 이하라 강의 기준상 점유율 1위 기업을 보는 바겐세일 구간입니다.'}[kq['zone']]
        L.append('- **한 줄 요약**: ' + zone_txt)
        L.append('- 강의에서는 지수 낙폭의 약 2배가 개별 종목의 할인율이라고 봅니다. 코스닥 2주 낙폭 %s 기준으로 종목은 대략 %s 안팎입니다.' % (pct(kq['dd10']), pct(kq['dd10'] * 2)))
        if kq['break']:
            L.append('- 코스닥이 최근 -10%% 이상 빠진 뒤 오늘 양봉으로 오르며 마감해 **브레이크 신호 조건**에 해당합니다.%s' % (
                ' 코스피도 상승 마감했습니다.' if kp and kp['up_close'] else ' 코스피는 함께 상승 마감하지 못했습니다.'))
        elif kq['cont']:
            L.append('- 급락 뒤 첫 양봉(브레이크 신호) 이후 반등이 이어지는 중입니다. 신호는 첫 양봉 날에만 표시합니다.')
        else:
            L.append('- 브레이크 신호(급락 후 지수 양봉 마감)는 오늘 없습니다.')
    ok = [r for r in rows if r['u']['status'] == '확인']
    cand = [r for r in rows if r['u']['status'] == '후보']
    cnt = {s: sum(1 for r in ok if r['state'] == s) for s in ('정상', '주의', '제외 후보')}
    L.append('## 추적 종목 현황')
    L.append('확인된 점유율 1위 기업 %d개: 정상 %d · 주의 %d · 제외 후보 %d. 낙폭(52주 고점 대비)이 큰 순서입니다. 상태는 강의의 재무 3가지(부채비율 200%% 미만, 영업이익 흑자, 배당)와 "저점 대비 10배 이상 상승 종목 제외" 규칙을 단순 적용한 값입니다.' % (len(ok), cnt['정상'], cnt['주의'], cnt['제외 후보']))
    L.append('<table header-row="true">\n<tr><td>종목</td><td>시장</td><td>1위 분야</td><td>종가</td><td>일간</td><td>52주 고점 대비</td><td>2주 낙폭</td><td>엔벨로프(20,20)</td><td>부채비율</td><td>영업이익(억)</td><td>배당</td><td>최근 분기 영업이익 YoY</td><td>외국인 20일(억)</td><td>기관 20일(억)</td><td>수급 신호</td><td>상태</td><td>사유</td></tr>')
    for r in sorted(ok, key=lambda r: (r['off52'] if r['off52'] is not None else 0)):
        u, sg = r['u'], r['sig']
        L.append('<tr><td>%s (%s)</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            u['name'], u['code'], u['market'], u['segment'], fmt(r['close']), pct(r['chg'], 2), pct(r['off52']), pct(r['dd10']), r['env'] or '-',
            ('-' if r['debt'] is None else ('금융업' if r['fin_exempt'] else '%.0f%%' % r['debt'])), fmt(r['op']),
            ('-' if r['dps'] is None else ('%s원' % fmt(r['dps']) if r['dps'] > 0 else '없음')), pct(r['qyoy'].get('영업이익'), 0),
            '{:+,.0f}'.format(sg['f20']) if sg else '-', '{:+,.0f}'.format(sg['o20']) if sg else '-',
            (sg['label'] + (' (' + sg['turn'] + ')' if sg['turn'] else '')) if sg else '-', r['state'], ' · '.join(r['why'])))
    L.append('</table>')
    inflow = [r for r in ok if r['sig'] and r['sig']['inflow'] and r['state'] != '제외 후보']
    if inflow:
        L.append('## 외국인·기관 수급이 들어오는 종목')
        L.append('최근 20거래일 순매수 금액(순매수 수량 × 당일 종가)이 20일 거래대금의 1% 이상(최소 3억원)인 종목입니다. 코스닥을 먼저, 순매수 금액이 큰 순입니다. 개인 수급만 늘어난 종목은 넣지 않았습니다.')
        L.append('<table header-row="true">\n<tr><td>종목</td><td>시장</td><td>수급 신호</td><td>외국인 20일(억)</td><td>기관 20일(억)</td><td>외국인 5일(억)</td><td>기관 5일(억)</td><td>외국인 보유비율 20일 변화</td><td>52주 고점 대비</td><td>상태</td></tr>')
        for r in sorted(inflow, key=lambda r: (r['u']['market'] != 'KOSDAQ', -(r['sig']['f20'] + r['sig']['o20']))):
            sg = r['sig']
            L.append('<tr><td>%s (%s)</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                r['u']['name'], r['u']['code'], r['u']['market'], sg['label'] + (' (' + sg['turn'] + ')' if sg['turn'] else ''),
                '{:+,.0f}'.format(sg['f20']), '{:+,.0f}'.format(sg['o20']), '{:+,.0f}'.format(sg['f5']), '{:+,.0f}'.format(sg['o5']),
                '-' if sg['hold_chg'] is None else '%+.2f%%p' % sg['hold_chg'], pct(r['off52']), r['state']))
        L.append('</table>')
    if cand:
        L.append('## 후보 (점유율 1위 여부 보류)')
        L.append('<table header-row="true">\n<tr><td>종목</td><td>시장</td><td>근거 기사</td><td>종가</td><td>52주 고점 대비</td><td>보류 사유</td></tr>')
        for r in cand:
            u = r['u']
            L.append('<tr><td>%s (%s)</td><td>%s</td><td><a href="%s">%s</a></td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                u['name'], u['code'], u['market'], u['evidence_link'], (u['evidence_title'] or '')[:40].replace('|', '/'), fmt(r['close']), pct(r['off52']), u.get('note') or u.get('segment') or ''))
        L.append('</table>')
    L.append('## 읽는 법과 한계')
    L.append('- **시장 구간**은 코스닥 지수의 최근 10거래일 최고 종가 대비 낙폭입니다(강의의 "2주간 지수 하락률"을 단순화). 코스닥 일간 지수는 네이버 증권 값입니다.\n'
             '- **브레이크 신호**는 구간 안에서 지수 일봉이 양봉이고 전일 종가보다 오르며 마감한 첫 날입니다(전일도 오른 날이면 "반등 지속"으로 표시). 강의는 코스피도 함께 상승 마감해야 한다고 합니다.\n'
             '- **재무**는 네이버 증권의 최근 확정 사업연도 값입니다. 금융업(은행·증권·보험)은 부채비율이 구조적으로 높아 제외했습니다. 분기 YoY는 직전 확정 분기와 전년 같은 분기를 비교한 영업이익 증감률입니다.\n'
             '- **수급 신호**는 네이버 증권 종목별 투자자 동향(최근 60거래일)에서 외국인·기관의 최근 20거래일 순매수 금액(순매수 수량 × 당일 종가)을 20일 거래대금과 비교해 만든 한 줄 요약입니다. 기관은 합산 값이라 연기금·투신 등으로 나누지 못하고, 당일 값은 잠정치일 수 있습니다. 주가 상승의 보장이 아니라 참고 자료입니다.\n'
             '- **점유율 1위** 판정은 뉴스 기사(제목·요약) 근거이며 기사 표현에 따라 국내/세계, 전체/세부 품목이 다릅니다. 1위 분야 열을 함께 보세요.\n'
             '- 강의의 신용잔고(반대매매) 지표는 아직 포함하지 않았습니다. 이 페이지는 투자 권유가 아닙니다.')
    os.makedirs(DAILY, exist_ok=True)
    path = os.path.join(DAILY, date + '.md')
    open(path, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print(json.dumps({'date': date, 'file': os.path.relpath(path, K.ROOT), 'tracked': len(rows), 'fails': fails,
                      'kosdaq': {k: kq[k] for k in ('close', 'dd10', 'zone', 'break')} if kq else None,
                      'states': cnt}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())

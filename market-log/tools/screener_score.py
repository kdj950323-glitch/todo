#!/usr/bin/env python3
"""바닥 후보 스크리너 데이터 수집·점수 계산 (루틴이 매일 다시 짜던 부분을 고정).

사용법 (저장소 루트에서):
  python3 market-log/tools/screener_score.py --date 2026-10-22 --out-dir /tmp/scr [--lead "Healthcare,Energy"]
출력:
  <out-dir>/candidates.json  후보 전체(점수·신호·주도 섹터 여부, 가격·이평선·RSI 등), 정렬 완료
  <out-dir>/tables.md        '주도 섹터 후보(상위 30)' '기타 섹터 후보(상위 20)' 마크다운 표(티커 링크 포함)
  <out-dir>/meta.json        기준일, 시장 상태, 주도 섹터, 후보 수, 신규·탈락, 직전 스냅샷 날짜, 티커 CSV 한 줄
  stdout                     요약 JSON
점수(0~5): ①낙폭 -20~-45% ②200일선 위 0~10% ③RSI≤40 ④20일선 위 ⑤거래량 배수≤0.8.
-45% 초과 낙폭은 ⚠️(점수 제외), 거래량 배수≥2 이면서 당일 하락은 🔥(점수 제외). 점수는 확인 우선순위일 뿐 매수 신호가 아니다.
"""
import argparse, csv, datetime, glob, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import finviz  # noqa: E402

ROOT = os.path.join(HERE, '..')
BASE_F = 'cap_midover,sh_avgvol_o500,sh_price_o10,ta_highlow52w_b20h,ta_perf_52w30o,ta_sma200_pa'
SECTOR_KO = {'Technology': '기술', 'Communication Services': '커뮤니케이션', 'Consumer Cyclical': '경기소비재', 'Consumer Defensive': '필수소비재',
             'Healthcare': '헬스케어', 'Financial': '금융', 'Industrials': '산업재', 'Basic Materials': '소재', 'Energy': '에너지',
             'Real Estate': '부동산', 'Utilities': '유틸리티'}


def fnum(x):
    try:
        return None if x is None else float(x)
    except (TypeError, ValueError):
        return None


def pct(v, d=2, sign=True):
    return '-' if v is None else (f'{v:+.{d}f}%' if sign else f'{v:.{d}f}%')


def fetch_all(v, f):
    out, r = {}, 1
    while True:
        s = finviz.get(f'https://finviz.com/screener.ashx?v={v}&f={f}&o=-marketcap&r={r}')
        rows, _ = finviz.parse_rows(s)
        if rows is None:
            raise RuntimeError(f'v={v} rows JSON not found')
        for x in rows:
            d = dict(x.get('text', {}))
            d.update(x.get('numbers', {}))
            out[d['ticker']] = d
        if len(rows) < 20 or r > 200:
            break
        r += 20
    return out


def sector_table():
    s = finviz.get('https://finviz.com/groups?g=sector&v=140&o=name')
    res = []
    for tr in re.findall(r'<tr[^>]*>(.*?)(?=<tr|</table)', s, re.S):
        c = [html.unescape(re.sub(r'<[^>]+>', '', x)).strip() for x in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)]
        if len(c) >= 11 and c[0].isdigit() and c[1] in SECTOR_KO:
            num = lambda t: float(t.rstrip('%').replace(',', '')) if t.rstrip('%').replace('.', '', 1).replace('-', '', 1).replace(',', '').isdigit() else None
            res.append({'name': c[1], 'week': num(c[2]), 'month': num(c[3]), 'quart': num(c[4]), 'half': num(c[5]), 'year': num(c[6]), 'ytd': num(c[7]), 'change': num(c[10])})
    return res


def leading(sectors):
    top = sorted([x for x in sectors if x['quart'] is not None], key=lambda x: -x['quart'])[:5]
    return [x['name'] for x in top if (x['month'] or 0) > 0 and (x['quart'] or 0) > 0]


def market_state():
    rows, _ = finviz.parse_rows(finviz.get('https://finviz.com/screener.ashx?v=171&t=SPY'))
    d = rows[0]['numbers'] if rows else {}
    s50, s200 = fnum(d.get('sma50')), fnum(d.get('sma200'))
    if s50 is None or s200 is None:
        return '확인 불가', s50, s200
    return ('🟢 공격' if s50 > 0 and s200 > 0 else '🟡 조정' if s200 > 0 else '🔴 방어'), s50, s200


def prev_snapshot(date):
    files = sorted(f for f in glob.glob(os.path.join(ROOT, 'screener', '20*.md')) if os.path.basename(f)[:10] < date)
    if not files:
        return None, set()
    txt = open(files[-1], encoding='utf-8').read()
    m = re.search(r'## 후보 티커 \(CSV\)\s*```?\s*([A-Z0-9.,\- ]+)', txt) or re.search(r'후보 티커.*?\n+([A-Z0-9.,\- ]{5,})\n', txt, re.S)
    tick = set(t.strip() for t in m.group(1).split(',') if t.strip()) if m else set()
    return os.path.basename(files[-1])[:10], tick


def score(r):
    off, s200, rsi, s20, rv, chg = (fnum(r.get(k)) for k in ('high52w', 'sma200', 'rsi', 'sma20', 'relativeVolume', 'change'))
    sig, sc = [], 0
    warn = ''
    if off is not None and -45 <= off <= -20:
        sc += 1; sig.append('낙폭')
    elif off is not None and off < -45:
        warn = '⚠️'
    if s200 is not None and 0 <= s200 <= 10:
        sc += 1; sig.append('200일선')
    if rsi is not None and rsi <= 40:
        sc += 1; sig.append('과매도')
    if s20 is not None and s20 > 0:
        sc += 1; sig.append('20일선회복')
    if rv is not None and rv <= 0.8:
        sc += 1; sig.append('거래량마름')
    fire = '🔥' if (rv is not None and rv >= 2 and chg is not None and chg < 0) else ''
    return sc, sig, warn, fire


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--lead')
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    try:
        v111, v171, v141 = fetch_all(111, BASE_F), fetch_all(171, BASE_F), fetch_all(141, BASE_F)
        secs = sector_table()
        state, s50, s200 = market_state()
    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False))
        return 1
    lead = [x.strip() for x in a.lead.split(',')] if a.lead else leading(secs)
    cands = []
    for t in v111:
        r = {}
        for src in (v111, v171, v141):
            r.update(src.get(t, {}))
        sc, sig, warn, fire = score(r)
        r.update({'score': sc, 'signals': sig, 'warn': warn, 'fire': fire, 'lead': r.get('sector') in lead})
        cands.append(r)
    cands.sort(key=lambda r: (not r['lead'], -r['score'], -(fnum(r.get('marketCap')) or 0)))
    prev_date, prev = prev_snapshot(a.date)
    cur = {r['ticker'] for r in cands}
    new, drop = sorted(cur - prev) if prev else [], sorted(prev - cur) if prev else []
    json.dump(cands, open(os.path.join(a.out_dir, 'candidates.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

    def row(r):
        t = r['ticker']
        sig = ' '.join(r['signals']) + (' ' + r['warn'] if r['warn'] else '') + (' ' + r['fire'] + '투매 가능' if r['fire'] else '')
        cap = fnum(r.get('marketCap')) or 0
        return ('<tr><td>[%s](https://finviz.com/quote.ashx?t=%s)</td><td>%s</td><td>%s / %s</td><td>%s</td><td>$%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%d</td><td>%s</td></tr>' % (
            t, t, r.get('company', ''), SECTOR_KO.get(r.get('sector'), r.get('sector', '')), r.get('industry', ''),
            ('%.2fT' % (cap / 1e6)) if cap >= 1e6 else ('%.1fB' % (cap / 1e3)), '{:,.2f}'.format(fnum(r.get('price')) or 0),
            pct(fnum(r.get('high52w')), 1), pct(fnum(r.get('sma200')), 1), pct(fnum(r.get('sma20')), 1),
            '-' if fnum(r.get('rsi')) is None else '%.0f' % fnum(r.get('rsi')), '-' if fnum(r.get('relativeVolume')) is None else '%.2f' % fnum(r.get('relativeVolume')),
            pct(fnum(r.get('perf13w')), 1), pct(fnum(r.get('perf52w')), 1), r['score'], sig.strip()))
    head = '<tr><td>티커</td><td>회사</td><td>섹터/산업</td><td>시총</td><td>가격</td><td>고점 대비%</td><td>200일선 대비%</td><td>20일선 대비%</td><td>RSI</td><td>거래량 배수</td><td>3개월%</td><td>1년%</td><td>점수</td><td>신호</td></tr>'
    lead_rows = [r for r in cands if r['lead']]
    oth_rows = [r for r in cands if not r['lead']]
    md = ['### 주도 섹터 후보 (점수순 상위 30개 / 전체는 GitHub)', '<table header-row="true">', head] + [row(r) for r in lead_rows[:30]] + ['</table>',
          '### 기타 섹터 후보 (상위 20개)', '<table header-row="true">', head] + [row(r) for r in oth_rows[:20]] + ['</table>']
    open(os.path.join(a.out_dir, 'tables.md'), 'w', encoding='utf-8').write('\n'.join(md).replace('$', '\\$') + '\n')
    meta = {'date': a.date, 'state': state, 'sma50': s50, 'sma200': s200, 'lead_sectors': lead, 'lead_sectors_ko': [SECTOR_KO.get(x, x) for x in lead],
            'count': len(cands), 'lead_count': len(lead_rows), 'new': new, 'dropped': drop, 'prev_date': prev_date, 'ticker_csv': ','.join(r['ticker'] for r in cands),
            'sector_table': secs}
    json.dump(meta, open(os.path.join(a.out_dir, 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(json.dumps({k: meta[k] for k in ('date', 'state', 'lead_sectors', 'count', 'lead_count', 'new', 'dropped', 'prev_date')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())

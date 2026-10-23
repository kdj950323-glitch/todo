#!/usr/bin/env python3
"""관심종목 데일리 상태 계산 (Finviz 수집, 상태·점수·변화 감지, 표·CSV 생성). 루틴이 매일 다시 짜던 부분을 고정한 도구.

사용법 (저장소 루트에서):
  python3 market-log/tools/watchlist_status.py --date 2026-10-22 --tickers "NVDA:엔비디아,AMD:AMD,LMT:록히드마틴" --out-dir /tmp/wl
    --tickers   노션 '관심 종목 목록' 표의 티커[:종목명[:하단[:상단]]] 쉼표 목록(표 순서 유지). 하단·상단은 관심 가격대(둘 중 하나만 있어도 됨, 비우려면 빈 칸).
    --no-earn   실적일 조회(종목별 quote 페이지)를 건너뜀
출력:
  <out-dir>/status.json   종목별 계산값(종가, 등락, 고점 대비, 이평선 대비, RSI, 점수, 위치 라벨, 이평선 요약, 다음 실적일, 방어 상승일)
  <out-dir>/table.md      '종목 현황' 표(Notion <table>, 16열, 티커 링크, $ 이스케이프)
  <out-dir>/changes.md    '오늘의 변화' 목록(항목별 한 줄: 티커 — 변화 내용). 모델이 뉴스·실적 맥락을 덧붙인다.
  <out-dir>/state.csv     다음 날 비교용 종목별 상태 CSV (watchlist 백업 파일 하단에 그대로 붙인다)
  <out-dir>/summary.json  평균 등락, 상승·하락 상위 3, 변화 건수, 조회 불가 종목
위치 라벨: 신고가권(-5% 이내)/조정(-5~-20%)/낙폭 구간(-20% 이하)/깊은 낙폭(-45% 이하).
점수(0~5): ①낙폭 -20~-45% ②200일선 위 0~10% ③RSI≤40 ④20일선 위 ⑤거래량 배수≤0.8 (상태 파악용, 매매 신호 아님).
"""
import argparse, concurrent.futures as cf, csv, datetime, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import finviz  # noqa: E402

ROOT = os.path.join(HERE, '..')


def fnum(x):
    try:
        return None if x is None else float(x)
    except (TypeError, ValueError):
        return None


def fetch_view(v, tickers):
    out = {}
    for i in range(0, len(tickers), 20):
        chunk = tickers[i:i + 20]
        s = finviz.get(f'https://finviz.com/screener.ashx?v={v}&t={",".join(chunk)}')
        rows, _ = finviz.parse_rows(s)
        for x in rows or []:
            d = dict(x.get('text', {})); d.update(x.get('numbers', {}))
            out[d['ticker']] = d
    miss = [t for t in tickers if t not in out]
    for t in miss:  # 주식·ETF 혼합 조회에서 빠지는 종목은 따로 재조회
        s = finviz.get(f'https://finviz.com/screener.ashx?v={v}&t={t}')
        rows, _ = finviz.parse_rows(s)
        for x in rows or []:
            d = dict(x.get('text', {})); d.update(x.get('numbers', {}))
            out[d['ticker']] = d
    return out


def label_of(off):
    if off is None:
        return '-'
    return '신고가권' if off >= -5 else '조정' if off > -20 else '깊은 낙폭' if off <= -45 else '낙폭 구간'


def score_of(r):
    off, s200, rsi, s20, rv = (fnum(r.get(k)) for k in ('high52w', 'sma200', 'rsi', 'sma20', 'relativeVolume'))
    return sum([off is not None and -45 <= off <= -20, s200 is not None and 0 <= s200 <= 10, rsi is not None and rsi <= 40,
                s20 is not None and s20 > 0, rv is not None and rv <= 0.8])


def ma_text(r):
    names = (('20', fnum(r.get('sma20'))), ('50', fnum(r.get('sma50'))), ('200', fnum(r.get('sma200'))))
    above = [n for n, v in names if v is not None and v > 0]
    below = [n for n, v in names if v is not None and v <= 0]
    if len(above) == 3:
        return '20·50·200일선 모두 위(강세)'
    if len(below) == 3:
        return '20·50·200일선 모두 아래(약세)'
    if '200' in below:
        return '200일선 아래(약세)'
    return '·'.join(below) + '일선 아래, ' + '·'.join(above) + '일선 위' + ('(조정)' if '200' in above else '')


def sign(v):
    return '-' if v is None else ('+' if v > 0 else '-')


def prev_state(date):
    files = sorted(f for f in glob.glob(os.path.join(ROOT, 'watchlist', '20*.md')) if os.path.basename(f)[:10] < date)
    if not files:
        return None, {}
    txt = open(files[-1], encoding='utf-8').read()
    m = re.search(r'```csv\s*\n(.*?)```', txt, re.S)
    st = {}
    if m:
        for r in csv.DictReader(m.group(1).strip().split('\n')):
            st[r['ticker']] = r
    return os.path.basename(files[-1])[:10], st


def biz_days(a, b):
    n, d = 0, a
    while d < b:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def next_earn(t, today):
    s = finviz.get(f'https://finviz.com/quote.ashx?t={t}')
    m = re.search(r'>Earnings</a></div></td>\s*<td[^>]*>.*?<small[^>]*>([^<]+)</small>', s, re.S)
    txt = m.group(1).strip() if m else None
    d = finviz.next_date(txt, today) if txt else None
    return t, txt, bool(d and d < today), d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--tickers', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--no-earn', action='store_true')
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.date)
    os.makedirs(a.out_dir, exist_ok=True)
    items = []
    for part in [p for p in a.tickers.split(',') if p.strip()]:
        f = part.split(':')
        items.append({'t': f[0].strip().upper(), 'name': f[1].strip() if len(f) > 1 else '', 'lo': fnum(f[2]) if len(f) > 2 else None, 'hi': fnum(f[3]) if len(f) > 3 else None})
    tk = [x['t'] for x in items]
    try:
        v171, v141 = fetch_view(171, tk), fetch_view(141, tk)
    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False))
        return 1
    earn = {}
    if not a.no_earn:
        with cf.ThreadPoolExecutor(8) as ex:
            for t, txt, stale, d in ex.map(lambda t: next_earn(t, today), [t for t in tk if t in v171]):
                earn[t] = (txt, stale, d)
    pdate, prev = prev_state(a.date)
    sys.path.insert(0, HERE)
    import reversal_flags as rf  # noqa: E402
    try:
        rev = rf.flags_for_watchlist() if hasattr(rf, 'flags_for_watchlist') else {}
    except Exception:
        rev = {}
    rows, missing = [], []
    for it in items:
        t = it['t']
        r = {}
        r.update(v171.get(t, {})); r.update(v141.get(t, {}))
        if not r:
            missing.append(t); continue
        off, chg = fnum(r.get('high52w')), fnum(r.get('change'))
        r.update({'ticker': t, 'name': it['name'] or r.get('company', t), 'label': label_of(off), 'score': score_of(r), 'ma': ma_text(r), 'zone': '', 'item': it})
        px = fnum(r.get('price'))
        if px is not None and (it['lo'] is not None or it['hi'] is not None):
            lo_ok = it['lo'] is None or px >= it['lo']
            hi_ok = it['hi'] is None or px <= it['hi']
            if it['lo'] is not None and it['hi'] is not None:
                r['zone'] = '🎯 관심 가격대 진입' if lo_ok and hi_ok else ''
            elif it['lo'] is not None:
                r['zone'] = '🎯 하단 이하' if px <= it['lo'] else ''
            else:
                r['zone'] = '🎯 상단 이상' if px >= it['hi'] else ''
        e = earn.get(t)
        r['earn_txt'], r['earn_stale'], r['earn_date'] = (e if e else (None, False, None))
        r['soon'] = bool(r['earn_date'] and not r['earn_stale'] and 0 <= biz_days(today, r['earn_date']) <= 3)
        rows.append(r)
    # 변화 감지
    changes = []
    for r in rows:
        t, p = r['ticker'], prev.get(r['ticker'])
        c = []
        off, rsi, chg, rv = fnum(r.get('high52w')), fnum(r.get('rsi')), fnum(r.get('change')), fnum(r.get('relativeVolume'))
        if p:
            for nm, k in (('200일선', 'sma200'), ('50일선', 'sma50'), ('20일선', 'sma20')):
                now, was = sign(fnum(r.get(k))), p.get(k, '')
                if was in ('+', '-') and now != was:
                    c.append('%s %s(%s→%s)' % (nm, '회복' if now == '+' else '이탈', '아래' if was == '-' else '위', '위' if now == '+' else '아래'))
            if p.get('label') and p['label'] != r['label']:
                c.append('위치 라벨 %s→%s(고점 대비 %+.1f%%)' % (p['label'], r['label'], off if off is not None else 0))
            prsi = fnum(p.get('rsi'))
            if rsi is not None and prsi is not None:
                if rsi < 30 <= prsi:
                    c.append('RSI 30 아래로 하락(%.1f)' % rsi)
                if rsi > 70 >= prsi:
                    c.append('RSI 70 위로 상승(%.1f)' % rsi)
            ps = fnum(p.get('score'))
            if ps is not None and r['score'] >= 3 > ps:
                c.append('바닥 신호 점수 %d로 상승' % r['score'])
            if r['label'] == '신고가권' and p.get('label') != '신고가권':
                c.append('신고가권 진입')
            if r['zone'] and not (p.get('watch_zone') == 'Y'):
                c.append(r['zone'].replace('진입', '새로 진입') if '진입' in r['zone'] else r['zone'] + ' 새로 진입')
        if chg is not None and abs(chg) >= 5:
            c.append('일간 %+.2f%% (±5%% 이상)' % chg)
        if rv is not None and rv >= 2 and chg is not None and abs(chg) >= 2:
            c.append('거래량 배수 %.2f의 큰 움직임(%+.2f%%)' % (rv, chg))
        if r['soon']:
            c.append('⏰ 실적 임박(%s)' % r['earn_txt'])
        if c:
            changes.append((t, c))
    # 출력
    def earn_cell(r):
        if r['earn_stale']:
            return '미확인 (Finviz 지난 날짜 %s)' % r['earn_txt']
        return r['earn_txt'] or '-'
    def pc(v, d=2):
        return '-' if v is None else '%+.*f%%' % (d, v)
    lines = ['<table header-row="true">', '<tr><td>티커</td><td>종목명</td><td>종가</td><td>일간</td><td>20일선</td><td>50일선</td><td>200일선</td><td>고점 대비</td><td>RSI</td><td>거래량 배수</td><td>1주</td><td>1개월</td><td>점수</td><td>방어 상승일(5일)</td><td>상태</td><td>다음 실적</td></tr>']
    for r in rows:
        t = r['ticker']; chg = fnum(r.get('change'))
        arrow = '➖' if chg is None or abs(chg) < 0.5 else ('🔺' if chg > 0 else '🔻')
        dn = rev.get(t, {})
        dtxt = '-' if not dn else ('%d' % dn.get('defiance_5d', 0) + ('' if dn.get('days_recorded', 0) >= 5 else '(%d일)' % dn.get('days_recorded', 0)))
        st = ' '.join(x for x in (r['ma'] + ' · ' + r['label'], r['zone'], '⏰ 실적 임박' if r['soon'] else '') if x)
        lines.append('<tr><td>[%s](https://finviz.com/quote.ashx?t=%s)</td><td>%s</td><td>$%s</td><td>%s %s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            t, t, r['name'], '{:,.2f}'.format(fnum(r.get('price')) or 0), arrow, pc(chg), pc(fnum(r.get('sma20'))), pc(fnum(r.get('sma50'))), pc(fnum(r.get('sma200'))),
            pc(fnum(r.get('high52w'))), '-' if fnum(r.get('rsi')) is None else '%.1f' % fnum(r.get('rsi')), '-' if fnum(r.get('relativeVolume')) is None else '%.2f' % fnum(r.get('relativeVolume')),
            pc(fnum(r.get('perf1w'))), pc(fnum(r.get('perf4w'))), r['score'], dtxt, st, earn_cell(r)))
    lines.append('</table>')
    open(os.path.join(a.out_dir, 'table.md'), 'w', encoding='utf-8').write('\n'.join(lines).replace('$', '\\$') .replace('\\\\$', '\\$') + '\n')
    open(os.path.join(a.out_dir, 'changes.md'), 'w', encoding='utf-8').write(('\n'.join('- %s — %s' % (t, ', '.join(c)) for t, c in changes) if changes else ('- 첫 기록' if not prev else '- 의미 있는 변화 없음')) + '\n')
    with open(os.path.join(a.out_dir, 'state.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['ticker', 'close', 'off_high_pct', 'sma20', 'sma50', 'sma200', 'rsi', 'score', 'label', 'watch_zone'])
        for r in rows:
            w.writerow([r['ticker'], '%.2f' % (fnum(r.get('price')) or 0), '%.2f' % (fnum(r.get('high52w')) or 0), sign(fnum(r.get('sma20'))), sign(fnum(r.get('sma50'))), sign(fnum(r.get('sma200'))),
                        '%.2f' % (fnum(r.get('rsi')) or 0), r['score'], r['label'], 'Y' if r['zone'] else 'N'])
    ch = [(fnum(r.get('change')), r['ticker']) for r in rows if fnum(r.get('change')) is not None]
    ch.sort()
    summ = {'date': a.date, 'prev_date': pdate, 'count': len(rows), 'avg_change': round(sum(c for c, _ in ch) / len(ch), 2) if ch else None,
            'up': sum(1 for c, _ in ch if c > 0), 'down': sum(1 for c, _ in ch if c < 0), 'top_up': [(t, round(c, 2)) for c, t in ch[::-1][:3]],
            'top_down': [(t, round(c, 2)) for c, t in ch[:3]], 'changes': len(changes), 'missing': missing,
            'earn_stale': [r['ticker'] for r in rows if r['earn_stale']], 'soon': [r['ticker'] for r in rows if r['soon']]}
    json.dump(summ, open(os.path.join(a.out_dir, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    json.dump([{k: v for k, v in r.items() if k not in ('item', 'earn_date')} for r in rows], open(os.path.join(a.out_dir, 'status.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0, default=str)
    print(json.dumps(summ, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())

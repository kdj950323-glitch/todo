#!/usr/bin/env python3
"""Finviz 파서 (표 HTML 대신 페이지 안 JSON/스냅샷 표를 읽는다). 루틴이 매번 파서를 새로 짜지 않도록 공용으로 쓴다.

사용법 (저장소 루트에서):
  python3 market-log/tools/finviz.py rows --v 171 --t NVDA,MU,SPY          # 티커 목록 → JSON(종목별 text+numbers)
  python3 market-log/tools/finviz.py rows --v 141 --t SPY,QQQ,XLK          # ETF 성과 화면 (v=141/111/171 모두 동일 구조)
  python3 market-log/tools/finviz.py rows --v 111 --f "sh_avgvol_o500,sh_price_o5,cap_smallover,ta_sma20_pb20" --all
                                                                           # 필터 결과 전체(페이지 자동 순회), total 포함
  python3 market-log/tools/finviz.py earnings NVDA MU AVGO                # quote 페이지의 다음 실적일 + 지난 날짜(stale) 여부
  python3 market-log/tools/finviz.py home                                  # 홈: 10년물 금리 타일 등 텍스트 후보

주의: 주식과 ETF 를 한 번에 섞어 조회하면 ETF 가 빠진다 → 따로 조회한다.
출력은 항상 stdout JSON. 구조가 바뀌어 파싱이 실패하면 {"error": ...} 를 내므로 수집 로그에 그대로 적고 WebFetch 로 대체한다.
"""
import argparse, datetime, html, json, re, subprocess, sys

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'


def get(url):
    r = subprocess.run(['curl', '-sL', '-A', UA, '-H', 'Accept-Language: en-US,en;q=0.9', url],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore')
    return r.stdout


def parse_rows(s):
    i = s.find('"data":{"rows":')
    if i < 0:
        return None, None
    obj, _ = json.JSONDecoder().raw_decode(s[i + 7:])
    total = None
    m = re.search(r'"totalRows":\s*(\d+)', s) or re.search(r'"total":\s*(\d+)', s)
    if m:
        total = int(m.group(1))
    return obj.get('rows', []), total


def cmd_rows(a):
    base = f'https://finviz.com/screener.ashx?v={a.v}'
    if a.t:
        base += '&t=' + a.t
    if a.f:
        base += '&f=' + a.f
    out, total, r = [], None, 1
    while True:
        s = get(base + f'&r={r}')
        rows, t = parse_rows(s)
        if rows is None:
            print(json.dumps({'error': 'rows JSON not found (Finviz 구조 변경 또는 차단)', 'url': base}, ensure_ascii=False))
            return
        total = total or t
        out += rows
        if not a.all or len(rows) < 20 or (total and len(out) >= total) or r > 2000:
            break
        r += 20
    flat = []
    for x in out:
        d = dict(x.get('text', {}))
        d.update(x.get('numbers', {}))
        d['range52w'] = x.get('range52w')
        flat.append(d)
    print(json.dumps({'total': total if total is not None else len(flat), 'count': len(flat), 'rows': flat}, ensure_ascii=False))


def next_date(txt, today):
    m = re.match(r'([A-Z][a-z]{2}) (\d{1,2})', txt or '')
    if not m:
        return None
    for y in (today.year, today.year + 1):
        try:
            d = datetime.datetime.strptime(f'{m.group(1)} {m.group(2)} {y}', '%b %d %Y').date()
        except ValueError:
            return None
        if y == today.year:
            first = d
    return first


def cmd_earnings(a):
    today = datetime.date.today()
    res = {}
    for t in a.tickers:
        s = get(f'https://finviz.com/quote.ashx?t={t}')
        m = re.search(r'>Earnings</a></div></td>\s*<td[^>]*>.*?<small[^>]*>([^<]+)</small>', s, re.S) \
            or re.search(r'>Earnings<.{0,500}?<b>(?:<small[^>]*>)?([^<]+)', s, re.S)
        txt = html.unescape(m.group(1)).strip() if m else None
        d = next_date(txt, today)
        res[t] = {'finviz': txt, 'stale': bool(d and d < today),
                  'note': 'Finviz 날짜가 이미 지났다 → WebSearch/investing.com 으로 다음 발표일 재확인' if d and d < today else None}
    print(json.dumps(res, ensure_ascii=False))


def cmd_home(a):
    s = get('https://finviz.com/')
    txt = re.sub(r'<[^>]+>', ' ', s)
    txt = html.unescape(re.sub(r'\s+', ' ', txt))
    m = re.search(r'10-Year Treasury.{0,80}', txt)
    print(json.dumps({'tnx_context': m.group(0) if m else None}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='c', required=True)
    r = sub.add_parser('rows'); r.add_argument('--v', default='171'); r.add_argument('--t'); r.add_argument('--f'); r.add_argument('--all', action='store_true'); r.set_defaults(fn=cmd_rows)
    e = sub.add_parser('earnings'); e.add_argument('tickers', nargs='+'); e.set_defaults(fn=cmd_earnings)
    h = sub.add_parser('home'); h.set_defaults(fn=cmd_home)
    a = p.parse_args()
    a.fn(a)

#!/usr/bin/env python3
"""국내주식 '시장 점유율 1위' 추적 시스템 공용 함수 (표준 라이브러리만 사용).

- 종목 목록·시세·재무·수급: 네이버 증권 모바일 JSON (비공식, 키 없음)
- 뉴스 검색: 네이버 검색 Open API (환경변수 NAVER_CLIENT_ID/SECRET, 없으면 로컬 naver-api-blog/.env). 키는 출력하지 않는다.
"""
import csv, datetime, html, json, os, re, subprocess, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
STATE = os.path.join(ROOT, 'state')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'}
M = 'https://m.stock.naver.com/api'


def http_json(url, tries=3, timeout=20):
    err = None
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)
            return json.loads(r.read().decode('utf-8'))
        except Exception as e:  # 네트워크·형식 오류는 재시도
            err = e
            time.sleep(0.8 * (i + 1))
    raise RuntimeError('%s: %s' % (url, err))


def num(s):
    """'1,234.5%' / '+627,670' / '-' → float 또는 None"""
    if s is None:
        return None
    t = str(s).replace(',', '').replace('%', '').replace('원', '').replace('배', '').replace('+', '').strip()
    try:
        return float(t)
    except ValueError:
        return None


def clean(s):
    return html.unescape(re.sub(r'<.*?>', '', s or '')).strip()


def read_csv(name):
    p = os.path.join(STATE, name)
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def write_csv(name, rows, header):
    os.makedirs(STATE, exist_ok=True)
    with open(os.path.join(STATE, name), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


# ---------- 종목 목록 ----------
def listing(markets=('KOSPI', 'KOSDAQ')):
    """코스피·코스닥 일반 주식(ETF·ETN 제외) 목록. [{code,name,market,mcap(억원)}]"""
    out = []
    for m in markets:
        page = 1
        while True:
            d = http_json('%s/stocks/marketValue/%s?page=%d&pageSize=100' % (M, m, page))
            rows = d.get('stocks') or []
            for r in rows:
                if r.get('stockEndType') != 'stock':
                    continue
                out.append({'code': r['itemCode'], 'name': r['stockName'], 'market': m,
                            'mcap': num(r.get('marketValue')) or 0, 'close': num(r.get('closePrice'))})
            if len(rows) < 100 or page >= 40:
                break
            page += 1
    return out


# ---------- 시세 ----------
def candles(code, days=900):
    """일봉 [{d,o,h,l,c,v}] 오름차순. 상장 후 짧으면 있는 만큼."""
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    d = http_json('https://api.stock.naver.com/chart/domestic/item/%s?periodType=dayCandle&startDateTime=%s&endDateTime=%s'
                  % (code, start.strftime('%Y%m%d'), end.strftime('%Y%m%d')))
    out = []
    for p in d.get('priceInfos') or []:
        out.append({'d': '%s-%s-%s' % (p['localDate'][:4], p['localDate'][4:6], p['localDate'][6:]), 'o': p['openPrice'], 'h': p['highPrice'],
                    'l': p['lowPrice'], 'c': p['closePrice'], 'v': p.get('accumulatedTradingVolume')})
    return out


def index_candles(name, pages=3):
    """지수(KOSPI/KOSDAQ) 일봉 오름차순. 한 페이지 60개."""
    rows = []
    for pg in range(1, pages + 1):
        d = http_json('%s/index/%s/price?pageSize=60&page=%d' % (M, name, pg))
        if not d:
            break
        rows += d
    out = []
    for r in rows:
        out.append({'d': r['localTradedAt'], 'o': num(r['openPrice']), 'h': num(r['highPrice']), 'l': num(r['lowPrice']), 'c': num(r['closePrice'])})
    out.sort(key=lambda x: x['d'])
    return out


def index_flow(name):
    """지수 투자자 동향(당일, 억원 단위 추정치). {bizdate, personal, foreign, institutional}"""
    d = http_json('%s/index/%s/trend' % (M, name))
    return {'bizdate': d.get('bizdate'), 'personal': num(d.get('personalValue')), 'foreign': num(d.get('foreignValue')),
            'institutional': num(d.get('institutionalValue'))}


# ---------- 종목 정보 ----------
def integration(code):
    d = http_json('%s/stock/%s/integration' % (M, code))
    info = {t['code']: t['value'] for t in d.get('totalInfos', [])}
    return {'info': info, 'industry': d.get('industryCode'), 'flow': d.get('dealTrendInfos') or [], 'raw': d}


FIN_ROWS = {'매출액': 'sales', '영업이익': 'op', '당기순이익': 'ni', '부채비율': 'debt', 'ROE': 'roe', '주당배당금': 'dps', '시가배당률': 'dyield'}


def finance(code, period='annual'):
    """재무 행 → {key: {'202412': value,...}}, 컬럼 라벨 {'202412': (title, isConsensus)}"""
    d = http_json('%s/stock/%s/finance/%s' % (M, code, period))
    fi = d.get('financeInfo') or {}
    cols = {t['key']: (t['title'], t.get('isConsensus') == 'Y') for t in fi.get('trTitleList', [])}
    rows = {}
    for r in fi.get('rowList', []):
        key = FIN_ROWS.get(r['title'])
        if key:
            rows[key] = {k: num(v.get('value')) for k, v in r['columns'].items()}
    return rows, cols


# ---------- 뉴스 ----------
def naver_keys():
    cid, sec = os.environ.get('NAVER_CLIENT_ID'), os.environ.get('NAVER_CLIENT_SECRET')
    base = os.environ.get('NAVER_API_ENDPOINT', 'https://naverapihub.apigw.ntruss.com')
    if not (cid and sec):
        for p in (os.path.join(ROOT, '..', 'naver-api-blog', '.env'),):
            if os.path.exists(p):
                env = dict(l.strip().split('=', 1) for l in open(p, encoding='utf-8') if '=' in l and not l.startswith('#'))
                cid, sec = env.get('NAVER_CLIENT_ID'), env.get('NAVER_CLIENT_SECRET')
                base = env.get('NAVER_API_ENDPOINT', base)
    return cid, sec, base.rstrip('/')


def news_search(query, cid, sec, base, display=100, start=1, sort='date'):
    url = '%s/search/v1/news?query=%s&display=%d&start=%d&sort=%s' % (base, urllib.parse.quote(query), display, start, sort)
    r = subprocess.run(['curl', '-s', '--max-time', '25', url, '-H', 'X-NCP-APIGW-API-KEY-ID: ' + cid, '-H', 'X-NCP-APIGW-API-KEY: ' + sec],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore')
    try:
        return json.loads(r.stdout).get('items', [])
    except Exception:
        return None


def pub_date(s):
    import email.utils
    try:
        return email.utils.parsedate_to_datetime(s).astimezone(datetime.timezone(datetime.timedelta(hours=9))).date()
    except Exception:
        return None


def sma(vals, n):
    return None if len(vals) < n else sum(vals[-n:]) / n

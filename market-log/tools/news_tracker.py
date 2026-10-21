#!/usr/bin/env python3
"""관심종목·대형주 추적 종목의 주요 뉴스 수집·정리 (네이버 뉴스 검색 API).

흐름 (루틴이 하는 일):
  1) python3 market-log/tools/news_tracker.py fetch --date YYYY-MM-DD --out /tmp/news_items.json
       state/news_universe.csv 의 종목마다 네이버 뉴스를 검색해, 최근 14일 이내이고 아직 본 적 없으며
       종목명(별칭)이 제목·요약에 있고 '주가에 영향을 줄 만한 키워드'가 있는 기사 후보만 JSON 으로 낸다.
  2) 모델이 후보를 읽고 정말 영향이 있는 기사만 골라 impact(호재/악재/중립/불확실), type, summary(한 줄, 직접 요약)를
     붙여 /tmp/news_decided.json 로 만든다 (제목·요약에 있는 내용만 근거, 추측 금지).
  3) python3 market-log/tools/news_tracker.py apply --date YYYY-MM-DD --items /tmp/news_items.json --decided /tmp/news_decided.json
       결정된 기사를 state/news_log.csv 에 추가하고, **발행일이 14일 넘은 기사는 삭제**하며, Notion 본문 마크다운
       market-log/news/latest.md 를 만든다. 후보로 나온 모든 링크는 state/news_seen.csv 에 기록해 다시 보지 않는다(14일 후 정리).
  4) python3 market-log/tools/news_tracker.py sync --watchlist "NVDA:엔비디아:엔비디아 주가:엔비디아;NVIDIA,..."
       관심종목 표에 종목이 추가·삭제됐을 때 news_universe.csv 의 watchlist 항목을 맞춘다(선택).
네이버 키: 환경변수 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET (없으면 로컬 naver-api-blog/.env). 키는 출력하지 않는다.
"""
import argparse, csv, datetime, email.utils, hashlib, html, json, os, re, subprocess, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
STATE = os.path.join(ROOT, 'state')
OUT = os.path.join(ROOT, 'news')
KEEP_DAYS = 14
KEYWORDS = ['실적', '가이던스', '어닝', '매출', '순이익', '영업이익', '인수', '합병', 'M&A', '소송', '규제', '제재', '관세', '수주', '계약',
            '리콜', '승인', '임상', '목표가', '목표주가', '투자의견', '상향', '하향', '감원', '구조조정', '배당', '자사주', '공매도', '조사',
            '급락', '급등', '폭락', '폭등', '신고가', '신저가', '파업', '해킹', '유출', '화재', '사고', '특허', '증자', '상장', '분할', 'CEO', '사임', '발표']
HEADER = ['first_seen', 'pub', 'ticker', 'name', 'impact', 'type', 'title', 'press', 'link', 'summary']


def keys():
    cid, sec = os.environ.get('NAVER_CLIENT_ID'), os.environ.get('NAVER_CLIENT_SECRET')
    base = os.environ.get('NAVER_API_ENDPOINT', 'https://naverapihub.apigw.ntruss.com')
    if not (cid and sec):
        p = os.path.join(ROOT, '..', 'naver-api-blog', '.env')
        if os.path.exists(p):
            env = dict(l.strip().split('=', 1) for l in open(p, encoding='utf-8') if '=' in l and not l.startswith('#'))
            cid, sec = env.get('NAVER_CLIENT_ID'), env.get('NAVER_CLIENT_SECRET')
            base = env.get('NAVER_API_ENDPOINT', base)
    return cid, sec, base.rstrip('/')


def read_csv(name):
    p = os.path.join(STATE, name)
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def write_csv(name, rows, header):
    with open(os.path.join(STATE, name), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator='\n', extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def clean(s):
    return html.unescape(re.sub(r'<.*?>', '', s or '')).strip()


def search(query, cid, sec, base, display=30):
    url = '%s/search/v1/news?query=%s&display=%d&sort=date' % (base, urllib.parse.quote(query), display)
    r = subprocess.run(['curl', '-s', '--max-time', '20', url, '-H', 'X-NCP-APIGW-API-KEY-ID: ' + cid, '-H', 'X-NCP-APIGW-API-KEY: ' + sec],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore')
    try:
        return json.loads(r.stdout).get('items', [])
    except Exception:
        return None


def lid(link):
    return hashlib.md5(link.encode('utf-8')).hexdigest()[:12]


def cmd_fetch(a):
    cid, sec, base = keys()
    if not (cid and sec):
        print(json.dumps({'error': 'NAVER 키 없음'}, ensure_ascii=False))
        return 1
    today = datetime.date.fromisoformat(a.date)
    cutoff = datetime.datetime.combine(today - datetime.timedelta(days=KEEP_DAYS), datetime.time.min, tzinfo=datetime.timezone.utc)
    seen = {r['id'] for r in read_csv('news_seen.csv')} | {lid(r['link']) for r in read_csv('news_log.csv')}
    uni = read_csv('news_universe.csv')
    items, failed, nsearch = [], [], 0
    dup_titles = set()
    for u in uni:
        res = search(u['query'], cid, sec, base)
        nsearch += 1
        if res is None:
            failed.append(u['ticker'])
            continue
        aliases = [x for x in u['aliases'].split(';') if x]
        for it in res:
            try:
                pub = email.utils.parsedate_to_datetime(it['pubDate'])
            except Exception:
                continue
            if pub < cutoff:
                continue
            title, desc = clean(it.get('title')), clean(it.get('description'))
            link = it.get('originallink') or it.get('link') or ''
            i = lid(link)
            if i in seen or (u['ticker'], title) in dup_titles:
                continue
            text = title + ' ' + desc
            if not any(al.lower() in text.lower() for al in aliases):
                continue
            kw = [k for k in KEYWORDS if k in text]
            dup_titles.add((u['ticker'], title))
            items.append({'id': i, 'ticker': u['ticker'], 'name': u['name_ko'], 'title': title, 'desc': desc,
                          'press': re.sub(r'^https?://(www\.)?', '', link).split('/')[0], 'link': link,
                          'pub': pub.astimezone(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M'), 'kw': kw,
                          'title_in_name': any(al.lower() in title.lower() for al in aliases)})
    # 키워드가 없고 제목에 종목명도 없는 기사는 후보에서 제외(잡음)
    cand = [x for x in items if x['kw'] and x['title_in_name']]
    json.dump({'date': a.date, 'items': items, 'candidates': cand}, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(json.dumps({'searched': nsearch, 'failed': failed, 'new_articles': len(items), 'candidates': len(cand), 'out': a.out}, ensure_ascii=False))
    return 0


def md_link(title, link):
    t = title.replace('[', '(').replace(']', ')').replace('|', '/')
    return '[%s](%s)' % (t, link.replace(')', '%29').replace(' ', '%20'))


ICON = {'호재': '🟢', '악재': '🔴', '중립': '⚪', '불확실': '🟡'}


def cmd_apply(a):
    today = datetime.date.fromisoformat(a.date)
    cutoff = (today - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    cand = json.load(open(a.items, encoding='utf-8')) if a.items and os.path.exists(a.items) else {'items': []}
    decided = json.load(open(a.decided, encoding='utf-8')) if a.decided and os.path.exists(a.decided) else []
    byid = {x['id']: x for x in cand.get('items', [])}
    log = read_csv('news_log.csv')
    have = {lid(r['link']) for r in log}
    added = 0
    for d in decided:
        link = d.get('link') or ''
        i = d.get('id') or lid(link)
        if i in have or not link:
            continue
        src = byid.get(i, {})
        log.append({'first_seen': a.date, 'pub': (d.get('pub') or src.get('pub') or '')[:16], 'ticker': d['ticker'],
                    'name': d.get('name') or src.get('name', ''), 'impact': d.get('impact', '불확실'), 'type': d.get('type', ''),
                    'title': d.get('title') or src.get('title', ''), 'press': d.get('press') or src.get('press', ''),
                    'link': link, 'summary': d.get('summary', '')})
        have.add(i)
        added += 1
    before = len(log)
    log = [r for r in log if (r['pub'] or r['first_seen'])[:10] >= cutoff]
    removed = before - len(log)
    log.sort(key=lambda r: r['pub'], reverse=True)
    write_csv('news_log.csv', log, HEADER)
    # 본 기사 기록(후보로 나온 모든 링크) + 14일 지난 기록 정리
    seen = read_csv('news_seen.csv')
    sids = {r['id'] for r in seen}
    for x in cand.get('items', []):
        if x['id'] not in sids:
            seen.append({'id': x['id'], 'first_seen': a.date}); sids.add(x['id'])
    seen = [r for r in seen if r['first_seen'] >= cutoff]
    write_csv('news_seen.csv', seen, ['id', 'first_seen'])
    # Notion 본문
    n_new = sum(1 for r in log if r['first_seen'] == a.date)
    cnt = {k: sum(1 for r in log if r['impact'] == k) for k in ICON}
    L = ['<callout icon="📰" color="gray_bg">\n\t**종목 주요 뉴스** — 관심종목과 대형주 추적 종목(약 70개)의 네이버 뉴스 중 주가에 영향을 줄 만한 기사만 모았습니다. 기준일 %s, 발행일 기준 최근 %d일치만 유지하고 그 전 기사는 자동으로 지웁니다. 영향 판단(호재·악재)은 기사 제목·요약만 보고 한 참고 분류이며 매수·매도 추천이 아닙니다.\n\t전체 %d건(🟢 호재 %d · 🔴 악재 %d · 🟡 불확실 %d · ⚪ 중립 %d), 오늘 새로 추가 %d건, 이번 정리로 삭제 %d건.\n</callout>' % (
        a.date, KEEP_DAYS, len(log), cnt['호재'], cnt['악재'], cnt['불확실'], cnt['중립'], n_new, removed)]
    def table(rows):
        t = ['<table header-row="true">\n<tr><td>발행(KST)</td><td>종목</td><td>영향</td><td>유형</td><td>기사</td><td>언론사</td><td>한 줄 요약</td></tr>']
        for r in rows:
            t.append('<tr><td>%s</td><td>%s %s</td><td>%s %s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                r['pub'][5:], r['ticker'], r['name'], ICON.get(r['impact'], '🟡'), r['impact'], r['type'], md_link(r['title'], r['link']), r['press'], r['summary'].replace('|', '/')))
        t.append('</table>')
        return '\n'.join(t)
    L.append('## 오늘 새로 추가된 뉴스')
    new = [r for r in log if r['first_seen'] == a.date]
    L.append('오늘 새로 추가된 주요 뉴스는 없습니다.' if not new else ('오늘 처음 기록해 아래 전체 표와 같습니다.' if len(new) == len(log) else table(new)))
    L.append('## 최근 %d일 전체 (최신순)' % KEEP_DAYS)
    L.append(table(log) if log else '아직 기록된 뉴스가 없습니다.')
    L.append('## 읽는 법과 한계')
    L.append('- 기사 후보는 종목명(별칭)이 제목에 있고 실적·수주·소송·규제·목표가·인수합병 등 영향 키워드가 있는 것만 봅니다. 키워드가 없는 기사나 시황 기사 속 단순 언급은 빠질 수 있습니다.\n'
             '- 한 줄 요약은 기사 제목·요약(description)에 나온 내용만 근거로 직접 쓴 것입니다. 사실 확인이 필요하면 기사 원문을 열어 보세요.\n'
             '- 미국 종목은 한국어 기사만 검색하므로 현지 속보보다 늦을 수 있습니다. 한국 아침에 전날 밤~새벽 기사가 모입니다.\n'
             '- 발행일이 %d일 지난 기사는 이 페이지와 `market-log/state/news_log.csv` 에서 삭제됩니다(GitHub 커밋 이력에는 남을 수 있음).' % KEEP_DAYS)
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'latest.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print(json.dumps({'date': a.date, 'added': added, 'removed_old': removed, 'total': len(log), 'file': 'news/latest.md'}, ensure_ascii=False))
    return 0


def cmd_sync(a):
    rows = read_csv('news_universe.csv')
    want = {}
    for part in [p for p in a.watchlist.split(',') if p.strip()]:
        f = part.split(':')
        want[f[0].strip()] = {'ticker': f[0].strip(), 'name_ko': f[1] if len(f) > 1 else f[0], 'query': f[2] if len(f) > 2 else (f[1] + ' 주가' if len(f) > 1 else f[0]),
                              'aliases': f[3] if len(f) > 3 else (f[1] if len(f) > 1 else f[0]), 'source': 'watchlist'}
    cur = {r['ticker']: r for r in rows}
    added = []
    for t, r in want.items():
        if t not in cur:
            rows.append(r); added.append(t)
        elif cur[t]['source'] == 'universe':
            cur[t]['source'] = 'both'
    keep = []
    removed = []
    for r in rows:
        if r['source'] == 'watchlist' and r['ticker'] not in want:
            removed.append(r['ticker']); continue
        if r['source'] == 'both' and r['ticker'] not in want:
            r['source'] = 'universe'
        keep.append(r)
    write_csv('news_universe.csv', keep, ['ticker', 'name_ko', 'query', 'aliases', 'source'])
    print(json.dumps({'added': added, 'removed': removed, 'total': len(keep)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest='c', required=True)
    f = s.add_parser('fetch'); f.add_argument('--date', default=datetime.date.today().isoformat()); f.add_argument('--out', default='/tmp/news_items.json'); f.set_defaults(fn=cmd_fetch)
    ap = s.add_parser('apply'); ap.add_argument('--date', default=datetime.date.today().isoformat()); ap.add_argument('--items'); ap.add_argument('--decided'); ap.set_defaults(fn=cmd_apply)
    sy = s.add_parser('sync'); sy.add_argument('--watchlist', required=True); sy.set_defaults(fn=cmd_sync)
    a = p.parse_args()
    sys.exit(a.fn(a))

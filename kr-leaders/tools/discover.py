#!/usr/bin/env python3
"""'시장 점유율 1위' 뉴스에서 코스피·코스닥 상장사를 찾아 추적 명단(state/leaders_kr.csv)을 만든다.

흐름:
  1) python3 kr-leaders/tools/discover.py fetch --days 30 --out /tmp/kr_cand.json
       네이버 뉴스 검색으로 점유율 1위 기사를 모으고, 제목·요약에서 '1위' 근처에 나온 상장사를 뽑아 후보 JSON 으로 낸다.
       이미 본 기사(state/kr_news_seen.csv)는 건너뛴다.
  2) 모델이 후보를 읽고 회사별로 판정해 /tmp/kr_decided.json 을 만든다:
       [{"code":"005930","verdict":"확인|제외|보류","segment":"점유율 1위 분야(짧게)","reason":"한 줄 근거"}]
       - 확인: 기사에 그 회사가 해당 분야 점유율(국내 또는 세계) 1위라고 직접 나옴
       - 제외: 1위 주체가 다른 회사/경쟁사 언급일 뿐이거나, 점유율 1위가 아닌 맥락(판매 1위 순위 비교 등 근거 약함)
       - 보류: 애매함(다음에 기사가 더 나오면 다시 판단)
  3) python3 kr-leaders/tools/discover.py apply --cand /tmp/kr_cand.json --decided /tmp/kr_decided.json
       명단 갱신. 판정이 없는 후보는 '후보'로 저장한다. '제외'된 종목은 이후 후보에서 다시 올리지 않는다.
"""
import argparse, csv, datetime, hashlib, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import krlib as K  # noqa: E402

QUERIES = ['시장 점유율 1위', '시장점유율 1위', '점유율 1위 기업', '국내 시장 점유율 1위', '글로벌 시장 점유율 1위', '세계 시장 점유율 1위',
           '점유율 1위 상장사', '점유율 1위 업체 코스닥', '독보적 점유율 1위']
HEAD = ['code', 'name', 'market', 'status', 'segment', 'first_seen', 'last_seen', 'evidence', 'evidence_title', 'evidence_link', 'note']
UNI_AGE_DAYS = 7
NEAR = 70  # '1위' 와 회사명 사이 허용 글자 수
# '점유율 1위' 맥락 표현 (단순 '브랜드평판 1위' 같은 순위는 제외하려는 것)
SHARE_RX = re.compile(r'점유율\s*(?:\S{0,6})?\s*1위|(?:업계|시장|세계|글로벌|국내|독보적|압도적|업종|분야|부문)\s*(?:\S{0,4})?\s*1위|1위\s*(?:업체|기업|사업자|메이커|제조사|회사)|점유율\s*(?:\d{1,2}(?:\.\d)?%\s*)?(?:로|를|으로)?\s*(?:\S{0,3})?\s*(?:선두|1등)')
PARTICLES = set('은는이가을를의에도와과로만')
# 일반 단어와 겹쳐 오인식이 잦은 상장사명 (원하면 추가)
STOP_NAMES = {'대상', '신흥', '태양', '레이', '카스', '진양', '한창', '동양', '대한', '서울', '한국', '삼화', '대원', '고려', '코리아', '글로벌', '에이스', '세종', '대성', '삼성', '현대', '동일', '선진', '신세계'}


def lid(link):
    return hashlib.md5(link.encode('utf-8')).hexdigest()[:12]


def universe():
    """상장사 목록 캐시(7일). state/universe_kr.csv"""
    p = os.path.join(K.STATE, 'universe_kr.csv')
    if os.path.exists(p) and (datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(p))).days < UNI_AGE_DAYS:
        return [dict(r, mcap=float(r['mcap'] or 0)) for r in K.read_csv('universe_kr.csv')]
    rows = K.listing()
    K.write_csv('universe_kr.csv', rows, ['code', 'name', 'market', 'mcap', 'close'])
    return rows


def boundary_ok(text, m):
    """회사명이 다른 단어의 일부가 아닌지: 앞 글자가 한글·영문·숫자가 아니고, 뒤 글자가 한글이면 조사일 때만 허용."""
    b = text[m.start() - 1] if m.start() > 0 else ' '
    a = text[m.end()] if m.end() < len(text) else ' '
    if re.match(r'[0-9A-Za-z가-힣]', b):
        return False
    if re.match(r'[0-9A-Za-z]', a):
        return False
    if re.match(r'[가-힣]', a):
        return a in PARTICLES
    return True


def name_regex(uni):
    names = sorted({u['name'] for u in uni if len(u['name']) >= 2}, key=len, reverse=True)
    return re.compile('|'.join(re.escape(n) for n in names))


def cmd_fetch(a):
    cid, sec, base = K.naver_keys()
    if not (cid and sec):
        print(json.dumps({'error': 'NAVER 키 없음'}, ensure_ascii=False))
        return 1
    uni = universe()
    by_name = {u['name']: u for u in uni}
    rx = name_regex(uni)
    seen = {r['id'] for r in K.read_csv('kr_news_seen.csv')}
    banned = {r['code'] for r in K.read_csv('leaders_kr.csv') if r['status'] == '제외'}
    cutoff = datetime.date.today() - datetime.timedelta(days=a.days)
    arts, ids = [], set()
    for q in QUERIES:
        for start in (1, 101):
            items = K.news_search(q, cid, sec, base, display=100, start=start)
            if items is None:
                print(json.dumps({'warn': '검색 실패: ' + q}, ensure_ascii=False), file=sys.stderr)
                break
            for it in items:
                link = it.get('originallink') or it.get('link')
                i = lid(link)
                d = K.pub_date(it.get('pubDate'))
                if i in ids or (d and d < cutoff):
                    continue
                ids.add(i)
                arts.append({'id': i, 'pub': d.isoformat() if d else '', 'title': K.clean(it['title']), 'desc': K.clean(it['description']), 'link': link,
                             'was_seen': i in seen})
            if len(items) < 100:
                break
    cand = {}
    for ar in arts:
        text = ar['title'] + ' ' + ar['desc']
        marks = [m.start() for m in SHARE_RX.finditer(text)]
        if not marks:
            continue
        for m in rx.finditer(text):
            u = by_name[m.group(0)]
            if u['code'] in banned or u['name'] in STOP_NAMES or not boundary_ok(text, m):
                continue
            if not any(abs(m.start() - p) <= NEAR for p in marks):
                continue
            c = cand.setdefault(u['code'], {'code': u['code'], 'name': u['name'], 'market': u['market'], 'mcap': u['mcap'], 'articles': []})
            if not any(x['id'] == ar['id'] for x in c['articles']):
                near = min(marks, key=lambda p: abs(p - m.start()))
                lo = max(0, min(m.start(), near) - 40)
                c['articles'].append({**{k: ar[k] for k in ('id', 'pub', 'title', 'desc', 'link', 'was_seen')},
                                      'snippet': text[lo:max(m.end(), near) + 50]})
    out = sorted(cand.values(), key=lambda c: -len(c['articles']))
    for c in out:
        c['articles'].sort(key=lambda x: x['pub'], reverse=True)
        c['new_articles'] = sum(1 for x in c['articles'] if not x['was_seen'])
    json.dump({'fetched': datetime.date.today().isoformat(), 'articles_scanned': len(arts), 'candidates': out},
              open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'articles': len(arts), 'candidates': len(out), 'with_new_articles': sum(1 for c in out if c['new_articles']), 'out': a.out}, ensure_ascii=False))
    return 0


def cmd_apply(a):
    cand = json.load(open(a.cand, encoding='utf-8'))
    decided = {d['code']: d for d in json.load(open(a.decided, encoding='utf-8'))} if a.decided and os.path.exists(a.decided) else {}
    today = cand.get('fetched') or datetime.date.today().isoformat()
    cur = {r['code']: r for r in K.read_csv('leaders_kr.csv')}
    changed = {'new': 0, 'updated': 0, 'excluded': 0}
    for c in cand['candidates']:
        d = decided.get(c['code'])
        art = c['articles'][0]
        row = cur.get(c['code'])
        if row is None:
            row = {'code': c['code'], 'name': c['name'], 'market': c['market'], 'status': '후보', 'segment': '', 'first_seen': today, 'note': ''}
            cur[c['code']] = row
            changed['new'] += 1
        else:
            changed['updated'] += 1
        row.update({'last_seen': today, 'evidence': str(len(c['articles'])), 'evidence_title': art['title'], 'evidence_link': art['link']})
        if d:
            v = d.get('verdict', '보류')
            row['status'] = {'확인': '확인', '제외': '제외', '보류': '후보'}.get(v, '후보')
            if d.get('segment'):
                row['segment'] = d['segment']
            if d.get('reason'):
                row['note'] = d['reason']
            changed['excluded'] += v == '제외'
    K.write_csv('leaders_kr.csv', sorted(cur.values(), key=lambda r: (r['status'] != '확인', r['status'] != '후보', r['name'])), HEAD)
    seen = {r['id']: r for r in K.read_csv('kr_news_seen.csv')}
    for c in cand['candidates']:
        for x in c['articles']:
            seen.setdefault(x['id'], {'id': x['id'], 'pub': x['pub']})
    cutoff = (datetime.date.today() - datetime.timedelta(days=60)).isoformat()
    K.write_csv('kr_news_seen.csv', [r for r in seen.values() if (r.get('pub') or '9999') >= cutoff], ['id', 'pub'])
    print(json.dumps(changed, ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    f = sp.add_parser('fetch')
    f.add_argument('--days', type=int, default=30)
    f.add_argument('--out', default='kr_cand.json')
    f.set_defaults(fn=cmd_fetch)
    p = sp.add_parser('apply')
    p.add_argument('--cand', required=True)
    p.add_argument('--decided', default='')
    p.set_defaults(fn=cmd_apply)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main())

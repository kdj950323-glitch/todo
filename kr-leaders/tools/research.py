#!/usr/bin/env python3
"""추적 종목(확인)의 증권사 종목분석 리포트를 모으고, '상승 모멘텀' 류 키워드가 있는 리포트를 정밀분석 대상으로 뽑는다.

흐름:
  1) python3 kr-leaders/tools/research.py fetch --days 90 --out /tmp/kr_reports.json
       네이버 증권 종목분석 리포트 목록(최신순)을 받아 추적 종목 것만 남기고, 아직 기록 안 한 리포트의 본문을 받아
       키워드(모멘텀·턴어라운드·수혜 등)를 검사한다. 키워드가 걸린 새 리포트는 본문 요약과 함께 JSON 으로 낸다.
       리포트 메타(제목·증권사·의견·목표주가)는 state/reports_kr.csv 에 쌓는다. 본문 전문은 저장소에 남기지 않는다(저작권).
  2) 모델이 JSON 의 본문을 읽고 리포트별로 판정해 /tmp/kr_reports_decided.json 을 만든다:
       [{"id":97049,"verdict":"모멘텀|단기 이벤트|근거 약함","note":"모멘텀 근거 한 줄(수치 포함)","risk":"리스크 한 줄"}]
  3) python3 kr-leaders/tools/research.py apply --decided /tmp/kr_reports_decided.json
증권사 의견은 낙관 쪽으로 치우치는 경향이 있어 참고 자료로만 쓴다.
"""
import argparse, concurrent.futures as cf, datetime, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import krlib as K  # noqa: E402

HEAD = ['id', 'date', 'code', 'name', 'broker', 'title', 'opinion', 'goal', 'price', 'link', 'hits', 'verdict', 'note', 'risk']
# 강의에서 강조한 '상승 모멘텀'과 같은 맥락의 표현
KEYWORDS = ['상승 모멘텀', '모멘텀', '턴어라운드', '수혜', '서프라이즈', '슈퍼사이클', '호황', '신성장', '성장 동력', '레벨업', '재평가']
LIST = K.M + '/research/company?page=%d&pageSize=100'


def strip(h):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', h or '')).strip()


def fetch_list(cutoff):
    out, p = [], 1
    while True:
        batch = list(cf_map(lambda q: _page(q), range(p, p + 8)))
        for b in batch:
            out += b
        if not batch or not batch[-1] or min(x['writeDate'] for x in batch[-1]) < cutoff or p > 80:
            break
        p += 8
    return [x for x in out if x['writeDate'] >= cutoff]


def _page(p):
    try:
        return K.http_json(LIST % p)
    except Exception:
        return []


def cf_map(fn, it):
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        return list(ex.map(fn, it))


def detail(rid):
    try:
        return K.http_json('%s/research/company/%d' % (K.M, rid))['researchContent']
    except Exception:
        return None


def cmd_fetch(a):
    cutoff = (datetime.date.today() - datetime.timedelta(days=a.days)).isoformat()
    ok = {r['code']: r for r in K.read_csv('leaders_kr.csv') if r['status'] == '확인'}
    known = {r['id']: r for r in K.read_csv('reports_kr.csv')}
    lst = [x for x in fetch_list(cutoff) if x['itemCode'] in ok]
    new = [x for x in lst if str(x['researchId']) not in known]
    ds = cf_map(lambda x: detail(x['researchId']), new)
    cand, rows = [], dict(known)
    for x, d in zip(new, ds):
        if not d:
            continue
        text = strip(d.get('content'))
        hits = sorted({k for k in KEYWORDS if k in (x['title'] + ' ' + text)}, key=len, reverse=True)
        hits = [k for k in hits if not any(k != o and k in o for o in hits)]  # '상승 모멘텀' 이 있으면 '모멘텀' 은 중복이라 뺀다
        rows[str(x['researchId'])] = {'id': x['researchId'], 'date': x['writeDate'], 'code': x['itemCode'], 'name': x['itemName'], 'broker': x['brokerName'],
                                      'title': x['title'], 'opinion': d.get('opinion') or '', 'goal': d.get('goalPrice') or '', 'price': d.get('priceAtWriteDate') or '',
                                      'link': x.get('endUrl') or '', 'hits': ' '.join(hits), 'verdict': '', 'note': '', 'risk': ''}
        if hits:
            cand.append({'id': x['researchId'], 'date': x['writeDate'], 'code': x['itemCode'], 'name': x['itemName'], 'market': ok[x['itemCode']]['market'],
                         'broker': x['brokerName'], 'title': x['title'], 'opinion': d.get('opinion'), 'goal': d.get('goalPrice'), 'price': d.get('priceAtWriteDate'),
                         'hits': hits, 'text': text[:1800]})
    K.write_csv('reports_kr.csv', sorted(rows.values(), key=lambda r: (r['date'], str(r['id'])), reverse=True), HEAD)
    cand.sort(key=lambda c: (c['market'] != 'KOSDAQ', c['date']), reverse=False)
    json.dump({'fetched': datetime.date.today().isoformat(), 'candidates': cand}, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'reports_in_period': len(lst), 'new': len(new), 'keyword_new': len(cand), 'out': a.out}, ensure_ascii=False))
    return 0


def cmd_apply(a):
    dec = {str(d['id']): d for d in json.load(open(a.decided, encoding='utf-8'))}
    rows = {r['id']: r for r in K.read_csv('reports_kr.csv')}
    n = 0
    for i, d in dec.items():
        if i in rows:
            rows[i].update({'verdict': d.get('verdict', ''), 'note': d.get('note', ''), 'risk': d.get('risk', '')})
            n += 1
    K.write_csv('reports_kr.csv', sorted(rows.values(), key=lambda r: (r['date'], str(r['id'])), reverse=True), HEAD)
    print(json.dumps({'applied': n}, ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    f = sp.add_parser('fetch')
    f.add_argument('--days', type=int, default=90)
    f.add_argument('--out', default='kr_reports.json')
    f.set_defaults(fn=cmd_fetch)
    p = sp.add_parser('apply')
    p.add_argument('--decided', required=True)
    p.set_defaults(fn=cmd_apply)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main())

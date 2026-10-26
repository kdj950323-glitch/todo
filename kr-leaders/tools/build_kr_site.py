#!/usr/bin/env python3
"""국내 '시장 점유율 1위' 추적 페이지를 docs/kr/ 로 만든다 (GitHub Pages /docs).
  python3 kr-leaders/tools/build_kr_site.py
만드는 것: index.html(최신 일간 + SVG 차트), leaders.html(추적 명단과 근거 기사), daily/YYYY-MM-DD.html
market-log 의 렌더러(build_site)·차트 함수(charts)를 재사용한다.
"""
import csv, glob, html, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
KR = os.path.join(ROOT, 'kr-leaders')
OUT = os.path.join(ROOT, 'docs', 'kr')
sys.path.insert(0, os.path.join(ROOT, 'market-log', 'tools'))
import build_site as B  # noqa: E402
import charts as C  # noqa: E402

SCOPE_NARROW = ('세부 품목', '브랜드 한정', '사업부 한정', '품목 한정', 'HBM 한정', '국가별', '일부 국가', '복수 품목', '일부 품목', '한정')
CSS_EXTRA ='.badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;background:var(--bd)}'


def read_csv(name):
    p = os.path.join(KR, 'state', name)
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8', newline='\n').write(text)


@C.safe
def kr_charts(md):
    tabs = C.html_table(md)
    parts = []
    mk = next((t for t in tabs if t and '구간' in t[0] and '브레이크 신호' in t[0]), None)
    if mk:
        h = mk[0]
        ci, cd, cz = C.col(h, '지수'), C.col(h, '2주 낙폭'), C.col(h, '구간')
        items = [(r[ci], C.num(r[cd])) for r in mk[1:] if C.num(r[cd]) is not None]
        if items:
            parts.append(C.card('지수 2주 낙폭', '-10%부터 낙폭과대 구간, -15% 이하는 바겐세일 구간(강의 기준)', C.hbars(items, label_w=52, row=26), wide=False))
    tb = next((t for t in tabs if t and '1위 분야' in t[0] and '52주 고점 대비' in t[0]), None)
    if tb:
        h = tb[0]
        cn, co, cs = C.col(h, '종목'), C.col(h, '52주 고점 대비'), C.col(h, '상태')
        items = [(r[cn].split(' (')[0], C.num(r[co])) for r in tb[1:] if C.num(r[co]) is not None]
        counts = {}
        for r in tb[1:]:
            counts[r[cs]] = counts.get(r[cs], 0) + 1
        cls = {'정상': 'bn', '주의': 'bw', '제외 후보': 'bd'}
        parts.append(C.card('상태 분포', '재무 3가지와 10배 이력 필터', C.stack_bar([(k, counts[k], cls[k]) for k in ('정상', '주의', '제외 후보') if k in counts], '상태 분포')))
        parts.append(C.card('52주 고점 대비 낙폭', '아래쪽(길게 왼쪽)일수록 많이 내린 종목', C.hbars(sorted(items, key=lambda p: p[1]), label_w=84, row=17), wide=True))
    return '<div class="dash">%s</div>' % ''.join(parts) if parts else ''


def leaders_page():
    rows = read_csv('leaders_kr.csv')
    ok = [r for r in rows if r['status'] == '확인']
    cand = [r for r in rows if r['status'] == '후보']
    ex = [r for r in rows if r['status'] == '제외']
    mcap = {r['code']: float(r['mcap'] or 0) for r in read_csv('universe_kr.csv')}
    for r in ok:
        r['_mcap'] = mcap.get(r['code'], 0)
        r['_scope'] = '품목 한정' if any(k in (r['note'] + r['segment']) for k in SCOPE_NARROW) else '전체'
    ok.sort(key=lambda r: (r['market'] != 'KOSDAQ', -r['_mcap']))
    n_kq = sum(1 for r in ok if r['market'] == 'KOSDAQ')
    L = ['## 확인된 점유율 1위 기업 (%d)' % len(ok),
         '뉴스 기사에서 해당 분야 점유율 1위로 소개된 코스피·코스닥 상장사입니다. 분야·지역(국내/세계)은 기사 표현 그대로 요약했습니다. '
         '이 전략은 코스닥 중견·중소 기업 발굴이 목적이라 코스닥(%d곳)을 위에 시가총액 큰 순으로, 코스피(%d곳)를 아래에 두었습니다.' % (n_kq, len(ok) - n_kq),
         '규모는 시가총액 기준 대형(5조 이상)·중형(5천억~5조)·소형(5천억 미만)입니다. 범위가 "품목 한정"인 곳은 기업 전체가 아니라 일부 품목·브랜드·사업부·일부 국가의 1위라는 뜻으로, 기록은 하되 판단은 직접 합니다.',
         '<table header-row="true">\n<tr><td>종목</td><td>시장</td><td>시총(억)</td><td>규모</td><td>범위</td><td>1위 분야</td><td>근거 기사</td><td>처음 발견</td><td>비고</td></tr>']
    for r in ok:
        m = r['_mcap']
        L.append('<tr><td>%s (%s)</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><a href="%s">%s</a></td><td>%s</td><td>%s</td></tr>' % (
            r['name'], r['code'], r['market'], '{:,.0f}'.format(m) if m else '-', '대형' if m >= 50000 else '중형' if m >= 5000 else '소형' if m else '-',
            r['_scope'], r['segment'], r['evidence_link'], (r['evidence_title'] or '')[:36].replace('|', '/'), r['first_seen'], r['note']))
    L.append('</table>')
    if cand:
        L.append('## 보류 (%d)' % len(cand))
        L.append('<table header-row="true">\n<tr><td>종목</td><td>시장</td><td>기사</td><td>보류 사유</td></tr>')
        for r in cand:
            L.append('<tr><td>%s (%s)</td><td>%s</td><td><a href="%s">%s</a></td><td>%s</td></tr>' % (
                r['name'], r['code'], r['market'], r['evidence_link'], (r['evidence_title'] or '')[:36].replace('|', '/'), r['note'] or r['segment']))
        L.append('</table>')
    L.append('## 제외한 후보 (%d)' % len(ex))
    L.append('기사에서 회사명이 나왔지만 1위 주체가 다른 회사거나 이름이 우연히 겹친 경우입니다. 같은 종목은 이후 후보로 다시 올리지 않습니다.')
    L.append('<table header-row="true">\n<tr><td>종목</td><td>제외 사유</td></tr>')
    for r in ex:
        L.append('<tr><td>%s (%s)</td><td>%s</td></tr>' % (r['name'], r['code'], r['note']))
    L.append('</table>')
    return '\n'.join(L)


def main():
    B.CSS += C.CSS + CSS_EXTRA
    files = sorted(glob.glob(os.path.join(KR, 'daily', '20*.md')))
    if not files:
        print('daily 기록 없음')
        return 1
    nav = '<div class="nav"><a href="../market/index.html">← 미국 증시 기록</a> · <a href="index.html">국내 추적</a> · <a href="leaders.html">추적 명단</a></div>'
    nav_sub = '<div class="nav"><a href="../index.html">← 국내 추적</a> · <a href="../leaders.html">추적 명단</a></div>'
    for f in files:
        d = os.path.basename(f)[:10]
        md = open(f, encoding='utf-8').read()
        write(os.path.join(OUT, 'daily', d + '.html'), B.page('국내 점유율 1위 기업 추적 ' + d, kr_charts(md) + B.render(md)[1], nav_sub, '기준일 ' + d))
    last = files[-1]
    d = os.path.basename(last)[:10]
    md = open(last, encoding='utf-8').read()
    hist = ''.join('<li><a href="daily/%s.html">%s</a></li>' % (os.path.basename(f)[:10], os.path.basename(f)[:10]) for f in reversed(files[-30:]))
    body = kr_charts(md) + B.render(md)[1] + '<h2>지난 기록</h2><ul>%s</ul>' % hist
    write(os.path.join(OUT, 'index.html'), B.page('국내 시장 점유율 1위 기업 추적', body, nav, '기준일 ' + d))
    write(os.path.join(OUT, 'leaders.html'), B.page('추적 명단과 근거 기사', B.render(leaders_page())[1], nav, '뉴스 검색으로 모은 점유율 1위 상장사'))
    print('kr site built:', d, len(files), 'daily pages')
    return 0


if __name__ == '__main__':
    sys.exit(main())

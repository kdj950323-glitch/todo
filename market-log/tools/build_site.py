#!/usr/bin/env python3
"""market-log 마크다운 → GitHub Pages 정적 사이트(docs/market/). 휴대폰 열람용, 외부 라이브러리 없음.

사용법 (저장소 루트에서):  python3 market-log/tools/build_site.py
만드는 것:
  docs/.nojekyll, docs/index.html           (docs/market/ 으로 안내)
  docs/market/index.html                    목차(최신 날짜별 일간·스크리너·관심종목 링크, 최신 대형주 추적·종목 뉴스, 학습 노트)
  docs/market/daily/YYYY-MM-DD.html, screener/…, watchlist/…, learning/….html
  docs/market/tracker.html, news.html       bottom-tracker 최신, news/latest.md
모든 페이지에 noindex 메타를 넣어 검색 엔진 노출을 줄인다(비공개는 아님 — 주소를 아는 사람은 볼 수 있다).
게시 전 반드시 market-log/tools/privacy_check.py 를 통과시킨다.
"""
import glob, html, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
ML = os.path.join(ROOT, 'market-log')
OUT = os.path.join(ROOT, 'docs', 'market')

CSS = """
:root{--bg:#fff;--fg:#1f2328;--mut:#6b7280;--bd:#e3e5e8;--card:#f6f7f9;--acc:#2563eb;--up:#117a3d;--dn:#c0392b;--call:#eff6ff}
@media(prefers-color-scheme:dark){:root{--bg:#16181c;--fg:#e8eaed;--mut:#9aa0a6;--bd:#2c3036;--card:#1f2226;--acc:#7aa7ff;--up:#5fd08b;--dn:#ff8a7a;--call:#1b2638}}
*{box-sizing:border-box}body{margin:0;padding:14px;background:var(--bg);color:var(--fg);font:15px/1.65 -apple-system,"Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",sans-serif;max-width:980px;margin:auto}
h1{font-size:20px;margin:6px 0 4px}h2{font-size:17px;margin:26px 0 8px;padding-left:9px;border-left:4px solid var(--acc)}h3{font-size:15px;margin:18px 0 6px}
a{color:var(--acc);text-decoration:none;word-break:break-all}.mut{color:var(--mut);font-size:13px}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:8px 0;border:1px solid var(--bd);border-radius:8px}
table{border-collapse:collapse;font-size:13px;min-width:100%}th,td{padding:6px 8px;border-bottom:1px solid var(--bd);text-align:left;vertical-align:top;white-space:nowrap}
td.l{white-space:normal;min-width:200px}th{background:var(--card);color:var(--mut);font-weight:600;position:sticky;top:0}
.callout{background:var(--call);border-radius:8px;padding:10px 12px;margin:10px 0}.quote{border-left:3px solid var(--bd);padding:2px 10px;margin:8px 0;color:var(--mut)}
details{border:1px solid var(--bd);border-radius:8px;padding:6px 10px;margin:8px 0}summary{cursor:pointer;font-weight:600}
ul{padding-left:20px;margin:6px 0}li{margin:3px 0}pre{background:var(--card);padding:8px;border-radius:6px;overflow-x:auto;font-size:12px}code{background:var(--card);padding:1px 4px;border-radius:4px;font-size:13px}
.nav{font-size:13px;margin-bottom:8px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:10px 12px}
.foot{margin-top:28px;font-size:12px;color:var(--mut)}
"""


def inline(s):
    s = html.escape(s, quote=False)
    s = s.replace('\\$', '$').replace('\\~', '~').replace('\\|', '|').replace('\\&lt;', '&lt;').replace('\\_', '_')
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', s)
    s = re.sub(r'(?<![">])(https?://[^\s<)]+)', lambda m: '<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>' % (m.group(1), m.group(1)) if 'href=' not in s[max(0, m.start() - 8):m.start()] else m.group(1), s)
    return s


def split_row(line):
    body = line.strip()
    if body.startswith('|'):
        body = body[1:]
    if body.endswith('|') and not body.endswith('\\|'):
        body = body[:-1]
    return [c.strip() for c in re.split(r'(?<!\\)\|', body)]


def render(md):
    L = md.split('\n')
    out, i, n = [], 0, len(L)
    title = ''
    para = []

    def flush():
        if para:
            out.append('<p>%s</p>' % inline(' '.join(para)))
            para.clear()
    while i < n:
        ln = L[i]
        if re.match(r'^(- )?노션 기록:', ln):
            i += 1; continue
        if ln.startswith('```'):
            flush(); j = i + 1; buf = []
            while j < n and not L[j].startswith('```'):
                buf.append(L[j]); j += 1
            out.append('<pre>%s</pre>' % html.escape('\n'.join(buf)))
            i = j + 1; continue
        if ln.startswith('# ') and not title:
            title = ln[2:].strip(); i += 1; continue
        m = re.match(r'^(#{2,4}) (.+)$', ln)
        if m:
            flush(); lvl = min(len(m.group(1)), 3)
            out.append('<h%d>%s</h%d>' % (lvl, inline(m.group(2)), lvl)); i += 1; continue
        if ln.startswith('|') and i + 1 < n and re.match(r'^\|[\s:|-]+\|\s*$', L[i + 1]):
            flush(); j = i; rows = []
            while j < n and L[j].startswith('|'):
                if not re.match(r'^\|[\s:|-]+\|\s*$', L[j]):
                    rows.append(split_row(L[j]))
                j += 1
            t = ['<div class="tw"><table><thead><tr>%s</tr></thead><tbody>' % ''.join('<th>%s</th>' % inline(c) for c in rows[0])]
            for r in rows[1:]:
                t.append('<tr>%s</tr>' % ''.join('<td%s>%s</td>' % (' class="l"' if len(c) > 26 else '', inline(c)) for c in r))
            t.append('</tbody></table></div>')
            out.append(''.join(t)); i = j; continue
        if ln.startswith('<table'):
            flush(); j = i; blk = []
            while j < n:
                blk.append(L[j])
                if '</table>' in L[j]:
                    break
                j += 1
            rows = re.findall(r'<tr>(.*?)</tr>', '\n'.join(blk), re.S)
            t = ['<div class="tw"><table>']
            for k, r in enumerate(rows):
                cells = re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)
                tag = 'th' if k == 0 else 'td'
                t.append('<tr>%s</tr>' % ''.join('<%s%s>%s</%s>' % (tag, ' class="l"' if (tag == 'td' and len(re.sub(r'<[^>]+>', '', c).strip()) > 26) else '', inline(re.sub(r'<[^>]+>', '', c).strip()), tag) for c in cells))
            t.append('</table></div>')
            out.append(''.join(t)); i = j + 1; continue
        m = re.match(r'^<callout[^>]*>\s*$', ln)
        if m or ln.startswith('<callout'):
            flush(); j = i + 1; buf = []
            while j < n and '</callout>' not in L[j]:
                buf.append(L[j].strip()); j += 1
            out.append('<div class="callout">%s</div>' % '<br>'.join(inline(b) for b in buf if b))
            i = j + 1; continue
        if ln.startswith('>'):
            flush(); j = i; buf = []
            while j < n and L[j].startswith('>'):
                buf.append(re.sub(r'^>\s?', '', L[j])); j += 1
            is_sum = any(b.startswith('**한줄 요약') or b.startswith('**①') or b.startswith('**② ') for b in buf)
            out.append('<div class="%s">%s</div>' % ('callout' if is_sum else 'quote', '<br>'.join(inline(b) for b in buf if b.strip())))
            i = j; continue
        if ln.startswith('<details'):
            flush(); m2 = re.match(r'<details>\s*<summary>(.*?)</summary>', ln)
            out.append('<details><summary>%s</summary>' % inline(m2.group(1) if m2 else '자세히'))
            i += 1; continue
        if ln.strip() == '</details>':
            flush(); out.append('</details>'); i += 1; continue
        if re.match(r'^\s*[-*] ', ln):
            flush(); j = i; items = []
            while j < n and re.match(r'^\s*[-*] ', L[j]):
                items.append(re.sub(r'^\s*[-*] (\[[ x]\] )?', lambda mm: ('☑ ' if mm.group(1) == '[x] ' else '☐ ') if mm.group(1) else '', L[j])); j += 1
            out.append('<ul>%s</ul>' % ''.join('<li>%s</li>' % inline(x) for x in items)); i = j; continue
        if not ln.strip():
            flush(); i += 1; continue
        para.append(ln.strip()); i += 1
    flush()
    return title, '\n'.join(out)


def page(title, body, nav='', desc=''):
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,nofollow"><title>%s</title><style>%s</style></head><body>%s<h1>%s</h1>%s%s'
            '<div class="foot">시장 흐름 기록용이며 투자 권유가 아닙니다. 자동 생성 페이지.</div></body></html>') % (
        html.escape(title), CSS, nav, inline(title), ('<div class="mut">%s</div>' % html.escape(desc)) if desc else '', body)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8', newline='\n').write(text)


def main():
    kinds = {'daily': '일간', 'screener': '바닥 후보', 'watchlist': '관심종목'}
    dates = {}
    for k in kinds:
        for f in sorted(glob.glob(os.path.join(ML, k, '20*.md'))):
            d = os.path.basename(f)[:10]
            title, body = render(open(f, encoding='utf-8').read())
            nav = '<div class="nav"><a href="../index.html">← 목차</a></div>'
            write(os.path.join(OUT, k, d + '.html'), page(title or d, body, nav))
            dates.setdefault(d, {})[k] = '%s/%s.html' % (k, d)
    extra = []
    for f in sorted(glob.glob(os.path.join(ML, 'learning', '*.md'))):
        b = os.path.basename(f)[:-3]
        title, body = render(open(f, encoding='utf-8').read())
        write(os.path.join(OUT, 'learning', b + '.html'), page(title or b, body, '<div class="nav"><a href="../index.html">← 목차</a></div>'))
        extra.append((title or b, 'learning/%s.html' % b))
    special = []
    bt = sorted(glob.glob(os.path.join(ML, 'bottom-tracker', '20*.md')))
    if bt:
        title, body = render(open(bt[-1], encoding='utf-8').read())
        write(os.path.join(OUT, 'tracker.html'), page('대형주 섹터별 바닥 추적', body, '<div class="nav"><a href="index.html">← 목차</a></div>', '기준일 ' + os.path.basename(bt[-1])[:10]))
        special.append(('🏛️ 대형주 섹터별 바닥 추적', 'tracker.html', os.path.basename(bt[-1])[:10]))
    nw = os.path.join(ML, 'news', 'latest.md')
    if os.path.exists(nw):
        title, body = render(open(nw, encoding='utf-8').read())
        write(os.path.join(OUT, 'news.html'), page('종목 주요 뉴스 (최근 2주)', body, '<div class="nav"><a href="index.html">← 목차</a></div>'))
        special.append(('📰 종목 주요 뉴스 (최근 2주)', 'news.html', ''))
    cards = ''.join('<a class="card" href="%s"><b>%s</b><div class="mut">%s</div></a>' % (u, t, d) for t, u, d in special)
    rows = []
    for d in sorted(dates, reverse=True):
        links = ' · '.join('<a href="%s">%s</a>' % (dates[d][k], kinds[k]) for k in kinds if k in dates[d])
        rows.append('<tr><td>%s</td><td>%s</td></tr>' % (d, links))
    body = ('<div class="grid">%s</div><h2>날짜별 기록</h2><div class="tw"><table><thead><tr><th>날짜</th><th>보기</th></tr></thead><tbody>%s</tbody></table></div>'
            '<h2>학습 노트</h2><ul>%s</ul>') % (cards, ''.join(rows), ''.join('<li><a href="%s">%s</a></li>' % (u, t) for t, u in extra))
    write(os.path.join(OUT, 'index.html'), page('미국 증시 기록', body, '', '매일 자동 갱신 · 휴대폰 열람용'))
    write(os.path.join(ROOT, 'docs', 'index.html'), '<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0; url=market/"><a href="market/">미국 증시 기록</a>')
    write(os.path.join(ROOT, 'docs', '.nojekyll'), '')
    print('built %d pages' % (sum(len(v) for v in dates.values()) + len(extra) + len(special) + 1))
    return 0


if __name__ == '__main__':
    sys.exit(main())

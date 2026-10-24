#!/usr/bin/env python3
"""market-log 마크다운·CSV → 인라인 SVG 차트(외부 라이브러리 없음). build_site.py 가 불러 쓴다.

각 함수는 HTML 조각 문자열을 돌려준다. 데이터 표를 못 찾거나 형식이 달라 실패하면 빈 문자열을 돌려주므로
(try/except) 차트 때문에 사이트 빌드가 깨지지 않는다. 색은 CSS 변수(--up, --dn, --acc, --mut, --fg, --bd)만 쓴다.
"""
import csv, html, math, os, re

W = 360  # SVG 기본 폭(viewBox). 화면 폭에 맞춰 늘어나고 줄어든다.


# ---------- 파싱 ----------
def esc(s):
    return html.escape(str(s), quote=True)


def clean(s):
    s = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub('[\U0001F300-\U0001FAFF☀-➿️]', '', s)
    return s.replace('**', '').strip()


def num(s, default=None):
    m = re.search(r'[-+−]?\d[\d,]*\.?\d*', str(s).replace('−', '-'))
    if not m:
        return default
    try:
        return float(m.group(0).replace(',', '').replace('+', ''))
    except ValueError:
        return default


def split_row(line):
    b = line.strip().strip('|')
    return [clean(c) for c in re.split(r'(?<!\\)\|', b)]


def md_table(md, heading_re, skip=0):
    """heading_re 에 맞는 제목 아래 첫(skip 번째) 표를 (헤더, 행들)로."""
    lines = md.split('\n')
    for i, ln in enumerate(lines):
        m = re.match(r'^#{2,4}\s+(.*)$', ln)
        if m and re.search(heading_re, re.sub(r'^\d+[.)]?\s*', '', m.group(1))):
            seen = 0
            j = i + 1
            while j < len(lines) and not re.match(r'^#{2,4}\s', lines[j]):
                if lines[j].startswith('|') and j + 1 < len(lines) and re.match(r'^\|[\s:|-]+\|\s*$', lines[j + 1]):
                    rows = []
                    k = j
                    while k < len(lines) and lines[k].startswith('|'):
                        if not re.match(r'^\|[\s:|-]+\|\s*$', lines[k]):
                            rows.append(split_row(lines[k]))
                        k += 1
                    if seen == skip:
                        return rows[0], rows[1:]
                    seen += 1
                    j = k
                    continue
                j += 1
    return None, []


def html_table(md):
    """<table> 블록(<tr><td>)을 [[셀,...],...] 목록들로."""
    out = []
    for blk in re.findall(r'<table.*?</table>', md, re.S):
        rows = []
        for tr in re.findall(r'<tr>(.*?)</tr>', blk, re.S):
            rows.append([clean(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)])
        out.append(rows)
    return out


def col(header, *names):
    for i, h in enumerate(header):
        for n in names:
            if n in h:
                return i
    return None


def read_csv(path):
    try:
        with open(path, encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def safe(fn):
    def wrap(*a, **k):
        try:
            return fn(*a, **k)
        except Exception:  # 차트 실패가 사이트 빌드를 막지 않게
            return ''
    wrap.__name__ = fn.__name__
    return wrap


# ---------- SVG 부품 ----------
def svg(w, h, body, label=''):
    return '<svg class="sv" viewBox="0 0 %d %d" width="100%%" role="img" aria-label="%s">%s</svg>' % (w, h, esc(label), body)


def card(title, note, inner, wide=False):
    return '<section class="ch%s"><h3>%s</h3>%s%s</section>' % (' wide' if wide else '', esc(title), ('<div class="mut">%s</div>' % esc(note)) if note else '', inner)


def fmt_pct(v, d=2):
    return ('%+.' + str(d) + 'f%%') % v


def hbars(items, label_w=76, row=22, fmt=lambda v: fmt_pct(v), title=''):
    """위아래로 갈라지는 가로 막대. items = [(라벨, 값)]."""
    items = [(l, v) for l, v in items if v is not None]
    if not items:
        return ''
    ext = max(abs(v) for _, v in items) or 1
    pad_r = 52
    x0, x1 = label_w + 44, W - pad_r
    zero = (x0 + x1) / 2 if min(v for _, v in items) < 0 < max(v for _, v in items) else (x0 if min(v for _, v in items) >= 0 else x1)
    scale = ((x1 - x0) / 2 / ext) if x0 < zero < x1 else ((x1 - x0) / ext)
    h = row * len(items) + 8
    b = ['<line x1="%.1f" x2="%.1f" y1="2" y2="%d" class="ax"/>' % (zero, zero, h - 4)]
    for k, (l, v) in enumerate(items):
        y = 4 + k * row
        bw = abs(v) * scale
        xs = zero if v >= 0 else zero - bw
        cls = 'bu' if v >= 0 else 'bd'
        b.append('<text x="%d" y="%.1f" text-anchor="end" class="t">%s</text>' % (label_w, y + row / 2 + 4, esc(l)))
        b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%d" rx="3" class="%s"/>' % (xs, y + 3, max(bw, 1), row - 6, cls))
        tx = zero + bw + 4 if v >= 0 else zero - bw - 4
        b.append('<text x="%.1f" y="%.1f" text-anchor="%s" class="m">%s</text>' % (tx, y + row / 2 + 4, 'start' if v >= 0 else 'end', esc(fmt(v))))
    return svg(W, h, ''.join(b), title)


def dotstrip(groups, lo, hi, ticks, ref=None, label_w=70, row=26, title=''):
    """그룹별 점도표. groups = [(그룹명, [(값, 툴팁문구, 강조여부)])]."""
    if not groups:
        return ''
    x0, x1 = label_w + 6, W - 10
    sx = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
    h = row * len(groups) + 24
    b = []
    for t in ticks:
        b.append('<line x1="%.1f" x2="%.1f" y1="2" y2="%d" class="%s"/>' % (sx(t), sx(t), h - 20, 'rf' if t == ref else 'gr'))
        b.append('<text x="%.1f" y="%d" text-anchor="middle" class="m">%s</text>' % (sx(t), h - 6, esc('%g%%' % t)))
    for k, (g, pts) in enumerate(groups):
        cy = 4 + k * row + row / 2
        b.append('<text x="%d" y="%.1f" text-anchor="end" class="t">%s</text>' % (label_w, cy + 4, esc(g)))
        for n, (v, tip, hot) in enumerate(sorted(pts, key=lambda p: p[0])):
            b.append('<circle cx="%.1f" cy="%.1f" r="5.5" class="%s"><title>%s</title></circle>' % (sx(max(lo, min(hi, v))), cy + ((n % 2) * 3 - 1.5), 'dh' if hot else 'dn', esc(tip)))
    return svg(W, h, ''.join(b), title)


def line_chart(series, h=150, base=None, y_fmt=lambda v: '%g' % v, title=''):
    """series = [(이름, 클래스, [(라벨, 값)...])] — 같은 x 길이를 가정."""
    series = [s for s in series if len(s[2]) >= 2]
    if not series:
        return ''
    vals = [v for _, _, pts in series for _, v in pts]
    lo, hi = min(vals), max(vals)
    if base is not None:
        lo, hi = min(lo, base), max(hi, base)
    if hi == lo:
        hi = lo + 1
    padv = (hi - lo) * 0.08
    lo -= padv; hi += padv
    x0, x1, y0, y1 = 34, W - 8, 8, h - 20
    sy = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
    b = []
    for t in [lo + (hi - lo) * i / 3 for i in range(4)]:
        b.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="gr"/><text x="%d" y="%.1f" text-anchor="end" class="m">%s</text>' % (x0, x1, sy(t), sy(t), x0 - 4, sy(t) + 4, esc(y_fmt(t))))
    if base is not None:
        b.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="rf"/>' % (x0, x1, sy(base), sy(base)))
    first = series[0][2]
    n = len(first)
    sx = lambda i: x0 + i / (n - 1) * (x1 - x0)
    b.append('<text x="%d" y="%d" class="m">%s</text><text x="%d" y="%d" text-anchor="end" class="m">%s</text>' % (x0, h - 5, esc(first[0][0]), x1, h - 5, esc(first[-1][0])))
    for name, cls, pts in series:
        d = ' '.join('%s%.1f,%.1f' % ('M' if i == 0 else 'L', sx(i), sy(v)) for i, (_, v) in enumerate(pts))
        b.append('<path d="%s" class="ln %s"/>' % (d, cls))
        b.append('<circle cx="%.1f" cy="%.1f" r="3" class="pt %s"/>' % (sx(len(pts) - 1), sy(pts[-1][1]), cls))
    leg = ''.join('<span class="lg %s">%s</span>' % (c, esc(nm)) for nm, c, _ in series) if len(series) > 1 else ''
    return svg(W, h, ''.join(b), title) + (('<div class="legend">%s</div>' % leg) if leg else '')


def spark(vals, w=70, h=22, up=None):
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return ''
    lo, hi = min(vals), max(vals)
    if hi == lo:
        hi = lo + 1
    d = ' '.join('%s%.1f,%.1f' % ('M' if i == 0 else 'L', 1 + i / (len(vals) - 1) * (w - 2), h - 2 - (v - lo) / (hi - lo) * (h - 4)) for i, v in enumerate(vals))
    cls = 'su' if (vals[-1] >= vals[0] if up is None else up) else 'sd'
    return '<svg class="sp" viewBox="0 0 %d %d" width="%d" height="%d"><path d="%s" class="ln %s"/></svg>' % (w, h, w, h, d, cls)


def scatter(points, xlo, xhi, ylo, yhi, xt, yt, xlabel, ylabel, h=230, title=''):
    """points = [(x, y, 툴팁, 강조여부)]"""
    if not points:
        return ''
    x0, x1, y0, y1 = 36, W - 10, 10, h - 28
    sx = lambda v: x0 + (v - xlo) / (xhi - xlo) * (x1 - x0)
    sy = lambda v: y1 - (v - ylo) / (yhi - ylo) * (y1 - y0)
    b = []
    for t in xt:
        b.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" class="gr"/><text x="%.1f" y="%d" text-anchor="middle" class="m">%g</text>' % (sx(t), sx(t), y0, y1, sx(t), y1 + 13, t))
    for t in yt:
        b.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="gr"/><text x="%d" y="%.1f" text-anchor="end" class="m">%g</text>' % (x0, x1, sy(t), sy(t), x0 - 4, sy(t) + 4, t))
    b.append('<text x="%d" y="%d" text-anchor="end" class="m">%s</text><text x="%d" y="%d" class="m">%s</text>' % (x1, h - 4, esc(xlabel), 2, 8, esc(ylabel)))
    for x, y, tip, hot in points:
        b.append('<circle cx="%.1f" cy="%.1f" r="4.5" class="%s"><title>%s</title></circle>' % (sx(max(xlo, min(xhi, x))), sy(max(ylo, min(yhi, y))), 'dh' if hot else 'dn', esc(tip)))
    return svg(W, h, ''.join(b), title)


def stack_bar(parts, title=''):
    """parts = [(라벨, 개수, css클래스)] — 한 줄 누적 막대 + 범례."""
    tot = sum(n for _, n, _ in parts) or 1
    x, b = 0.0, []
    for l, n, c in parts:
        w = n / tot * (W - 4)
        if n:
            b.append('<rect x="%.1f" y="2" width="%.1f" height="26" class="%s"/>' % (2 + x, max(w, 1), c))
            if w > 18:
                b.append('<text x="%.1f" y="20" text-anchor="middle" class="wt">%d</text>' % (2 + x + w / 2, n))
        x += w
    leg = ''.join('<span class="lg"><i class="sw %s"></i>%s %d</span>' % (c, esc(l), n) for l, n, c in parts)
    return svg(W, 30, ''.join(b), title) + '<div class="legend">%s</div>' % leg


def heat_table(rows, cols, label_head='섹터'):
    """rows = [(라벨, [값...])], cols = 열 이름. 값 부호·크기로 칸 색을 칠한다."""
    if not rows:
        return ''
    ext = max(abs(v) for _, vs in rows for v in vs if v is not None) or 1
    t = ['<div class="tw"><table class="heat"><thead><tr><th>%s</th>%s</tr></thead><tbody>' % (esc(label_head), ''.join('<th>%s</th>' % esc(c) for c in cols))]
    for l, vs in rows:
        cells = []
        for v in vs:
            if v is None:
                cells.append('<td>-</td>')
                continue
            a = min(70, 12 + abs(v) / ext * 58)
            colr = 'var(--up)' if v >= 0 else 'var(--dn)'
            cells.append('<td style="background:color-mix(in srgb,%s %d%%,transparent)">%s</td>' % (colr, a, esc('%+.1f' % v)))
        t.append('<tr><td class="l1">%s</td>%s</tr>' % (esc(l), ''.join(cells)))
    t.append('</tbody></table></div>')
    return ''.join(t)


# ---------- 일간 기록 ----------
def _sector_rows(md):
    h, rows = md_table(md, r'^섹터( \(|$|\s)')
    if not h:
        return []
    ci_name, ci_day, ci_multi = col(h, '섹터'), col(h, '1일'), col(h, '1주')
    out = []
    for r in rows:
        if ci_name is None or ci_day is None or len(r) <= max(ci_name, ci_day):
            continue
        multi = [num(x) for x in re.split(r'/', r[ci_multi])] if ci_multi is not None and len(r) > ci_multi else []
        out.append({'name': r[ci_name], 'day': num(r[ci_day]), 'w1': multi[0] if len(multi) > 0 else None,
                    'm1': multi[1] if len(multi) > 1 else None, 'q3': multi[2] if len(multi) > 2 else None})
    return out


@safe
def daily(md, ml):
    parts = []
    # 1) 지수 카드
    h, rows = md_table(md, r'^지수')
    if h:
        ci = col(h, '일간'); c50 = col(h, '50일선')
        hist = {r['date']: r for r in read_csv(os.path.join(ml, 'state', 'prices.csv'))}
        dates = sorted(hist)[-30:]
        cards = []
        for r in rows:
            v = num(r[ci]) if ci is not None else None
            if v is None:
                continue
            t = r[0].strip()
            sp = spark([num(hist[d].get(t)) for d in dates]) if t in ('SPY', 'QQQ', 'IWM') else ''
            sub = ('50일선 대비 ' + r[c50]) if c50 is not None and len(r) > c50 else ''
            cards.append('<div class="kc"><div class="mut">%s</div><div class="kv %s">%s</div><div class="mut">%s</div>%s</div>' % (
                esc(t), 'u' if v > 0 else ('d' if v < 0 else ''), esc(('▲ ' if v > 0 else ('▼ ' if v < 0 else '')) + fmt_pct(v)), esc(sub), sp))
        if cards:
            parts.append('<div class="kpis">%s</div>' % ''.join(cards))
    # 2) 섹터 막대 + 히트맵
    sec = _sector_rows(md)
    if sec:
        s1 = sorted([(x['name'], x['day']) for x in sec if x['day'] is not None], key=lambda p: -p[1])
        parts.append(card('섹터별 1일 등락', '위에서 아래로 강한 순서', hbars(s1)))
        hm = heat_table([(x['name'], [x['day'], x['w1'], x['m1'], x['q3']]) for x in sec], ['1일', '1주', '1개월', '3개월'])
        parts.append(card('섹터 기간별 열지도', '초록은 상승, 빨강은 하락, 진할수록 폭이 큼(단위 %)', hm))
    # 3) 시장 폭
    h, rows = md_table(md, r'^시장 폭')
    if rows:
        d = {r[0]: r for r in rows}
        def find(k):
            for kk, rr in d.items():
                if k in kk:
                    return rr
            return None
        b = []
        r50, r200, rhl = find('50일선'), find('200일선'), find('신고가')
        items = []
        if r50 and num(r50[1]) is not None: items.append(('50일선 위', num(r50[1])))
        if r200 and num(r200[1]) is not None: items.append(('200일선 위', num(r200[1])))
        if items:
            bars = []
            for k, (l, v) in enumerate(items):
                y = 4 + k * 26
                bars.append('<text x="76" y="%d" text-anchor="end" class="t">%s</text><rect x="84" y="%d" width="%.1f" height="16" rx="3" class="tr"/><rect x="84" y="%d" width="%.1f" height="16" rx="3" class="%s"/>'
                            '<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" class="rf"/><text x="%.1f" y="%d" class="m">%.1f%%</text>' % (
                                y + 13, esc(l), y, 220, y, 220 * v / 100, 'bu' if v >= 50 else 'bd', 84 + 110, 84 + 110, y - 2, y + 18, 84 + 224, y + 13, v))
            b.append(svg(W, 4 + 26 * len(items), ''.join(bars), '시장 폭'))
            b.append('<div class="mut">가운데 선 = 50%. 50일선 위 종목이 절반 아래이면 경고</div>')
        if rhl:
            nums = re.findall(r'[\d,]+', rhl[1])
            if len(nums) >= 2:
                hi_, lo_ = float(nums[0].replace(',', '')), float(nums[1].replace(',', ''))
                tot = (hi_ + lo_) or 1
                b.append(svg(W, 40, '<rect x="2" y="6" width="%.1f" height="18" class="bu"/><rect x="%.1f" y="6" width="%.1f" height="18" class="bd"/>'
                             '<text x="2" y="38" class="m">신고가 %d</text><text x="%d" y="38" text-anchor="end" class="m">신저가 %d</text>' % (
                                 (W - 4) * hi_ / tot, 2 + (W - 4) * hi_ / tot, (W - 4) * lo_ / tot, hi_, W - 2, lo_), '신고가 대 신저가'))
        hist = read_csv(os.path.join(ml, 'state', 'breadth.csv'))
        if len(hist) >= 2:
            b.append(line_chart([('50일선 위 %', 'l1', [(r['date'][5:], float(r['above_sma50_pct'])) for r in hist if r.get('above_sma50_pct')]),
                                 ('200일선 위 %', 'l2', [(r['date'][5:], float(r['above_sma200_pct'])) for r in hist if r.get('above_sma200_pct')])],
                                base=50, y_fmt=lambda v: '%d' % v, title='시장 폭 추이'))
        if b:
            parts.append(card('시장 폭', '지수가 아니라 종목 전체의 체력', ''.join(b)))
    # 4) 상대강도
    h, rows = md_table(md, r'상대강도')
    if h:
        ci = col(h, 'RS')
        if ci is not None:
            items = sorted([(r[0], num(r[ci])) for r in rows if num(r[ci]) is not None], key=lambda p: -p[1])
            if items:
                parts.append(card('ETF 상대강도(1일)', 'SPY보다 얼마나 더 올랐나(%p). 위쪽이 시장보다 강함', hbars(items, fmt=lambda v: '%+.2fp' % v, row=19)))
    # 5) 관심종목
    h, rows = md_table(md, r'^관심종목')
    if h:
        ci, co = col(h, '일간'), col(h, '고점 대비')
        items = sorted([(r[0], num(r[ci])) for r in rows if ci is not None and num(r[ci]) is not None], key=lambda p: -p[1])
        if items:
            parts.append(card('관심종목 1일 등락', '오른 종목과 내린 종목이 한눈에', hbars(items, fmt=lambda v: fmt_pct(v), row=18), wide=True))
    # 6) 엔벨로프 이력
    hist = read_csv(os.path.join(ml, 'state', 'breadth.csv'))
    pts = [(r['date'][5:], float(r['env_lower'])) for r in hist if r.get('env_lower')]
    if len(pts) >= 2:
        parts.append(card('낙폭과대 종목 수(엔벨로프 하단 이하)', '30 이상이면 단기 낙폭이 큰 구간', line_chart([('하단 이하 종목 수', 'l3', pts)], base=30, y_fmt=lambda v: '%d' % v, title='엔벨로프 하단 종목 수')))
    return '<div class="dash">%s</div>' % ''.join(parts) if parts else ''


# ---------- 관심종목 ----------
@safe
def watchlist(md, ml):
    parts = []
    h, rows = md_table(md, r'^종목 현황')
    if not h:
        return ''
    ci, co, cr = col(h, '일간'), col(h, '고점 대비'), col(h, 'RSI')
    items = sorted([(clean(r[0]), num(r[ci])) for r in rows if ci is not None and num(r[ci]) is not None], key=lambda p: -p[1])
    if items:
        parts.append(card('관심종목 1일 등락', '', hbars(items, row=18, fmt=lambda v: fmt_pct(v)), wide=True))
    if co is not None:
        pts = [(num(r[co]), '%s %s' % (clean(r[0]), r[co]), num(r[co]) <= -20) for r in rows if num(r[co]) is not None]
        if pts:
            lo = min(-50, min(p[0] for p in pts) - 2)
            parts.append(card('고점 대비 낙폭', '붉은 점은 -20% 이하', dotstrip([('관심종목', pts)], lo, 2, [t for t in (-40, -30, -20, -10, 0) if t >= lo], ref=-20, row=40), wide=False))
    if cr is not None and co is not None:
        pts = [(num(r[cr]), num(r[co]), '%s RSI %s, 고점 대비 %s' % (clean(r[0]), r[cr], r[co]), num(r[cr]) <= 40 and num(r[co]) <= -20) for r in rows if num(r[cr]) is not None and num(r[co]) is not None]
        parts.append(card('RSI와 낙폭', '왼쪽 아래(RSI 낮고 낙폭 큼)가 많이 눌린 종목', scatter([(a, b, t, hot) for a, b, t, hot in pts], 20, 80, -50, 0, [30, 40, 50, 60, 70], [-40, -30, -20, -10], 'RSI', '고점 대비 %')))
    # 종목별 최근 가격 흐름(스파크라인 격자)
    wp = read_csv(os.path.join(ml, 'state', 'watchlist_prices.csv'))
    if wp:
        by = {}
        for r in wp:
            by.setdefault(r['ticker'], []).append((r['date'], float(r['close'])))
        cells = []
        for t in [clean(r[0]) for r in rows]:
            ser = sorted(by.get(t, []))
            if len(ser) >= 3:
                ch = (ser[-1][1] / ser[0][1] - 1) * 100
                cells.append('<div class="kc"><div class="mut">%s</div><div class="kv %s" style="font-size:15px">%s</div>%s</div>' % (esc(t), 'u' if ch >= 0 else 'd', esc(fmt_pct(ch, 1)), spark([p[1] for p in ser], w=110, h=28)))
        if cells:
            parts.append(card('기록 시작 이후 흐름', '10/09 이후 종가 변화(%)', '<div class="kpis sm">%s</div>' % ''.join(cells), wide=True))
    return '<div class="dash">%s</div>' % ''.join(parts) if parts else ''


# ---------- 스크리너 ----------
@safe
def screener(md, ml):
    parts = []
    pts, secs = [], {}
    for heading in (r'^주도 섹터 후보', r'^기타 섹터 후보'):
        h, rows = md_table(md, heading)
        if not h:
            continue
        co, cr, cs, ct, cse = col(h, '고점 대비'), col(h, 'RSI'), col(h, '점수'), col(h, '티커'), col(h, '섹터')
        for r in rows:
            try:
                x, y = num(r[cr]), num(r[co])
                if x is None or y is None:
                    continue
                sc = num(r[cs], 0) if cs is not None else 0
                pts.append((x, y, '%s RSI %s, 고점 대비 %s, 점수 %s' % (clean(r[ct]), r[cr], r[co], sc), sc >= 4))
                if cse is not None:
                    secs[r[cse].split('/')[0].strip()] = secs.get(r[cse].split('/')[0].strip(), 0) + 1
            except (IndexError, TypeError):
                continue
    if pts:
        parts.append(card('후보 분포: RSI와 고점 대비 낙폭', '왼쪽 아래일수록 많이 눌림, 붉은 점은 점수 4 이상', scatter(pts, 15, 70, -50, -15, [20, 30, 40, 50, 60], [-45, -40, -30, -20], 'RSI', '고점 대비 %'), wide=True))
        sc = {}
        for p in pts:
            k = int(re.search(r'점수 (\d+)', p[2]).group(1)) if re.search(r'점수 (\d+)', p[2]) else 0
            sc[k] = sc.get(k, 0) + 1
        parts.append(card('점수별 후보 수', '5점에 가까울수록 바닥 신호 항목이 많음', hbars([('%d점' % k, sc[k]) for k in sorted(sc, reverse=True)], fmt=lambda v: '%d개' % v)))
    if secs:
        parts.append(card('섹터별 후보 수', '', hbars(sorted(secs.items(), key=lambda p: -p[1])[:10], fmt=lambda v: '%d개' % v, label_w=96)))
    return '<div class="dash">%s</div>' % ''.join(parts) if parts else ''


# ---------- 대형주 바닥 추적 ----------
STAGE_CLS = [('위험', 'bd'), ('가치함정', 'bw'), ('펀더멘털 미확인', 'bm'), ('바닥 후보', 'bu'), ('바닥 탐색', 'bo'), ('눌림', 'bm2'), ('정상', 'bn')]


@safe
def tracker(md, ml):
    tabs = html_table(md)
    parts = []
    etf = next((t for t in tabs if t and '쉬운 풀이' in t[0]), None)
    if etf:
        h = etf[0]
        cs, c1, c3 = col(h, '섹터'), col(h, '1개월 SPY'), col(h, '3개월 SPY')
        for ci, ttl in ((c3, '섹터 ETF 3개월 강도'), (c1, '섹터 ETF 1개월 강도')):
            items = [(r[cs], num(r[ci])) for r in etf[1:] if num(r[ci]) is not None]
            if items:
                parts.append(card(ttl, 'SPY보다 몇 %p 더 올랐나(오른쪽 초록=시장보다 강함, 왼쪽 빨강=시장보다 약함)', hbars(items, label_w=76)))
    lead = next((t for t in tabs if t and '주도주' in t[0] and '근접' in t[0]), None)
    if lead:
        h = lead[0]
        cs, c4, ce = col(h, '섹터'), col(h, '주도주'), col(h, 'SPY 대비')
        ex = [(r[cs], num(r[ce])) for r in lead[1:] if num(r[ce]) is not None]
        if ex:
            parts.append(card('섹터별 대표주 3개월 강도', '섹터 대표 5종목 평균이 SPY보다 몇 %p 높았나(위쪽이 강한 섹터)', hbars(ex, label_w=76)))
        cnt = [(r[cs], num(r[c4])) for r in lead[1:] if num(r[c4]) is not None]
        if cnt:
            parts.append(card('섹터별 주도주 수', '4가지 조건을 모두 충족한 종목 수(섹터당 5종목 중)', hbars(cnt, label_w=76, fmt=lambda v: '%d개' % v)))
    full = next((t for t in tabs if t and any('시총' in c for c in t[0]) and '단계' in t[0] and len(t) > 30), None)
    if full:
        h = full[0]
        cs, ctk, co, cst = col(h, '섹터'), col(h, '티커'), col(h, '고점 대비'), col(h, '단계')
        counts = {}
        for r in full[1:]:
            st = r[cst]
            counts[st] = counts.get(st, 0) + 1
        seg = []
        for key, cls in STAGE_CLS:
            n = sum(v for k, v in counts.items() if key in k)
            seg.append((key, n, cls))
        parts.append(card('단계별 종목 수', '55종목 전체 분포', stack_bar(seg, '단계별 종목 수'), wide=True))
        groups = {}
        for r in full[1:]:
            v = num(r[co])
            if v is not None:
                groups.setdefault(r[cs], []).append((v, '%s %s %s' % (r[ctk], r[co], r[cst]), v <= -20))
        lo = min(-50, min(p[0] for g in groups.values() for p in g) - 2)
        parts.append(card('섹터별 고점 대비 낙폭', '점 하나가 종목 하나, 붉은 점은 -20% 이하', dotstrip(list(groups.items()), lo, 2, [t for t in (-40, -30, -20, -10, 0) if t >= lo], ref=-20, label_w=76, row=28), wide=True))
        mean = sorted([(g, sum(p[0] for p in pts) / len(pts)) for g, pts in groups.items()], key=lambda p: p[1])
        parts.append(card('섹터 평균 낙폭', '평균 고점 대비 %. 아래쪽 섹터가 더 눌려 있음', hbars(mean, label_w=76)))
    return '<div class="dash">%s</div>' % ''.join(parts) if parts else ''


# ---------- 실적 캘린더 ----------
@safe
def earnings(csv_path):
    rows = read_csv(csv_path)
    items = []
    for r in rows:
        e, a = num(r.get('eps_est')), num(r.get('eps_actual'))
        if e and a is not None and e != 0:
            items.append((r['ticker'], (a / e - 1) * 100, r['date']))
    parts = []
    if items:
        items.sort(key=lambda p: -p[1])
        parts.append(card('EPS 서프라이즈', '실제 EPS가 예상보다 몇 % 높았나(출처별 예상치 차이 있음)', hbars([(t, v) for t, v, _ in items], row=19, fmt=lambda v: fmt_pct(v, 1)), wide=True))
    res = {}
    for r in rows:
        k = (r.get('result') or '').strip() or '미확인'
        res[k] = res.get(k, 0) + 1
    if res:
        cls = {'상회': 'bu', '부합': 'bm', '하회': 'bd', '미확인': 'bn'}
        parts.append(card('결과 분포', '', stack_bar([(k, v, cls.get(k, 'bn')) for k, v in sorted(res.items(), key=lambda p: -p[1])], '실적 결과 분포')))
    return '<div class="dash">%s</div>' % ''.join(parts) if parts else ''


# ---------- 홈 ----------
@safe
def home(ml):
    pr = read_csv(os.path.join(ml, 'state', 'prices.csv'))
    if len(pr) < 5:
        return ''
    pr = pr[-120:]
    def idx(c):
        base = float(pr[0][c]); return [(r['date'][5:], float(r[c]) / base * 100) for r in pr if r.get(c)]
    parts = [card('지수 흐름(최근 약 6개월, 시작=100)', 'SPY · QQQ · IWM', line_chart([('SPY', 'l1', idx('SPY')), ('QQQ', 'l2', idx('QQQ')), ('IWM', 'l3', idx('IWM'))], base=100, y_fmt=lambda v: '%d' % v, title='지수 흐름'))]
    vix = [(r['date'][5:], float(r['VIX'])) for r in pr if r.get('VIX')]
    tnx = [(r['date'][5:], float(r['TNX'])) for r in pr if r.get('TNX')]
    parts.append(card('변동성 지수(VIX)', '20 위는 불안, 30 위는 공포 구간', line_chart([('VIX', 'l4', vix)], base=20, y_fmt=lambda v: '%d' % v, title='VIX')))
    parts.append(card('10년 금리(%)', '금리가 오르면 채권 가격은 내려감', line_chart([('10년물', 'l5', tnx)], y_fmt=lambda v: '%.1f' % v, title='10년 금리')))
    return '<div class="dash">%s</div>' % ''.join(parts)


CSS = """
.dash{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(min(100%,330px),1fr));margin:10px 0 18px}
.dash>.kpis{grid-column:1/-1}.ch.wide{grid-column:1/-1}
.ch{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:10px 12px;min-width:0}
.ch h3{margin:0 0 2px;font-size:15px}.ch .mut{margin-bottom:6px}.ch .sv+.sv,.ch .sv+.mut,.ch .mut+.sv{margin-top:10px}
.sv{display:block;max-width:560px;height:auto;overflow:visible}
.sv text{font-size:11px;font-family:inherit}.sv .t{fill:var(--fg)}.sv .m{fill:var(--mut)}.sv .wt{fill:#fff;font-weight:600}
.sv .ax,.sv .gr{stroke:var(--bd);stroke-width:1}.sv .rf{stroke:var(--mut);stroke-width:1;stroke-dasharray:4 3}
.sv .bu,.bu{fill:var(--up)}.sv .bd,.bd{fill:var(--dn)}.sv .tr{fill:var(--bd)}.sv .bw{fill:#d99a1f}.sv .bm{fill:#8b93a1}.sv .bo{fill:#e08a2e}.sv .bm2{fill:#a9b0bd}.sv .bn{fill:#6aa7a0}
.sv .dn{fill:var(--mut);fill-opacity:.75;stroke:var(--card)}.sv .dh{fill:var(--dn);fill-opacity:.9;stroke:var(--card)}
.ln{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}.pt{stroke:none}
.l1{stroke:var(--acc);fill:var(--acc)}.l2{stroke:#d9822b;fill:#d9822b}.l3{stroke:var(--up);fill:var(--up)}.l4{stroke:var(--dn);fill:var(--dn)}.l5{stroke:#8e6bd1;fill:#8e6bd1}
.ln.l1,.ln.l2,.ln.l3,.ln.l4,.ln.l5{fill:none}.su{stroke:var(--up)}.sd{stroke:var(--dn)}
.legend{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12px;color:var(--mut);margin-top:4px}.lg{display:inline-flex;align-items:center;gap:4px}
.lg.l1::before,.lg.l2::before,.lg.l3::before,.lg.l4::before,.lg.l5::before{content:"";width:10px;height:3px;border-radius:2px;background:currentColor}
.lg.l1{color:var(--acc)}.lg.l2{color:#d9822b}.lg.l3{color:var(--up)}.sw{display:inline-block;width:10px;height:10px;border-radius:2px}
.sw.bu{background:var(--up)}.sw.bd{background:var(--dn)}.sw.bw{background:#d99a1f}.sw.bm{background:#8b93a1}.sw.bo{background:#e08a2e}.sw.bm2{background:#a9b0bd}.sw.bn{background:#6aa7a0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px}.kpis.sm{grid-template-columns:repeat(auto-fill,minmax(112px,1fr))}
.kc{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:8px 10px;min-width:0}.kv{font-size:22px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.3}
.kv.u{color:var(--up)}.kv.d{color:var(--dn)}.sp{display:block;margin-top:4px;max-width:100%}.sp .ln{stroke-width:1.6}
table.heat td{text-align:right;font-variant-numeric:tabular-nums}table.heat td.l1{text-align:left;font-weight:600}table.heat th{text-align:right}table.heat th:first-child{text-align:left}
"""

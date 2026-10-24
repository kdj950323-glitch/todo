#!/usr/bin/env python3
"""블로그(네이버 등) 붙여넣기용 PNG 차트 생성. Pillow 만 쓴다(없으면 건너뜀). charts.py 의 파서를 재사용한다.

사용법 (저장소 루트에서):
  python3 market-log/tools/charts_png.py            # 최신 일간 기록 + 최신 대형주 추적
  python3 market-log/tools/charts_png.py 2026-10-22 # 지정 날짜 일간 기록
결과: docs/market/img/YYYY-MM-DD/*.png (일간), docs/market/img/tracker/*.png (대형주 추적)
build_site.py 가 이 폴더의 PNG 를 해당 페이지 맨 아래 '이미지로 저장' 영역에 보여 준다.
한글 폰트가 없으면 아무것도 만들지 않고 종료 코드 0 으로 끝난다(루틴이 막히지 않게).
"""
import glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import charts as C

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print('charts_png: Pillow 없음, 건너뜀')
    sys.exit(0)

ROOT = os.path.join(HERE, '..', '..')
ML = os.path.join(ROOT, 'market-log')
IMG = os.path.join(ROOT, 'docs', 'market', 'img')
S = 3
W = 360
BG, FG, MUT, GRID = '#ffffff', '#1f2328', '#6b7280', '#e3e5e8'
UP, DN = '#117a3d', '#c0392b'
FONT_CANDS = ['C:/Windows/Fonts/malgun.ttf', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
              '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
              '/System/Library/Fonts/AppleSDGothicNeo.ttc', '/usr/share/fonts/opentype/unifont/unifont_jp.otf']
FONT_BOLD = ['C:/Windows/Fonts/malgunbd.ttf']
_cache = {}


def font(size, bold=False):
    key = (size, bold)
    if key in _cache:
        return _cache[key]
    cands = (FONT_BOLD if bold else []) + FONT_CANDS
    for p in cands:
        if os.path.exists(p):
            try:
                _cache[key] = ImageFont.truetype(p, int(size * S))
                return _cache[key]
            except OSError:
                continue
    return None


def mix(hex_color, a):
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return '#%02x%02x%02x' % (int(255 - (255 - r) * a), int(255 - (255 - g) * a), int(255 - (255 - b) * a))


class Canvas:
    def __init__(self, h, title, sub=''):
        self.h = h
        self.im = Image.new('RGB', (W * S, int(h * S)), BG)
        self.d = ImageDraw.Draw(self.im)
        self.text(12, 10, title, 15, FG, bold=True)
        if sub:
            self.text(12, 30, sub, 10.5, MUT)

    def text(self, x, y, s, size=11, fill=FG, anchor='la', bold=False):
        self.d.text((x * S, y * S), str(s), font=font(size, bold), fill=fill, anchor=anchor)

    def rect(self, x, y, w, h, fill, r=0):
        box = (x * S, y * S, (x + w) * S, (y + h) * S)
        if r:
            self.d.rounded_rectangle(box, radius=r * S, fill=fill)
        else:
            self.d.rectangle(box, fill=fill)

    def line(self, x0, y0, x1, y1, fill=GRID, w=1, dash=False):
        if dash:
            n = int(abs(x1 - x0 + y1 - y0) / 5)
            for i in range(0, n, 2):
                a, b = i / n, min(1, (i + 1) / n)
                self.d.line([((x0 + (x1 - x0) * a) * S, (y0 + (y1 - y0) * a) * S), ((x0 + (x1 - x0) * b) * S, (y0 + (y1 - y0) * b) * S)], fill=fill, width=int(w * S))
        else:
            self.d.line([(x0 * S, y0 * S), (x1 * S, y1 * S)], fill=fill, width=int(w * S))

    def dot(self, x, y, r, fill):
        self.d.ellipse(((x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S), fill=fill, outline=BG, width=S)

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.im.save(path, optimize=True)


def hbars(path, title, sub, items, fmt, row=21, label_w=88):
    items = [(l, v) for l, v in items if v is not None]
    if not items:
        return
    cv = Canvas(46 + row * len(items) + 10, title, sub)
    ext = max(abs(v) for _, v in items) or 1
    x0, x1 = label_w + 40, W - 50
    lo, hi = min(v for _, v in items), max(v for _, v in items)
    zero = (x0 + x1) / 2 if lo < 0 < hi else (x0 if lo >= 0 else x1)
    scale = ((x1 - x0) / 2 / ext) if x0 < zero < x1 else ((x1 - x0) / ext)
    cv.line(zero, 44, zero, 46 + row * len(items), GRID)
    for k, (l, v) in enumerate(items):
        y = 48 + k * row
        bw = max(abs(v) * scale, 1)
        cv.text(label_w, y + row / 2 - 1, l, 11, FG, 'rm')
        cv.rect(zero if v >= 0 else zero - bw, y + 3, bw, row - 6, UP if v >= 0 else DN, 2)
        cv.text(zero + bw + 4 if v >= 0 else zero - bw - 4, y + row / 2 - 1, fmt(v), 10.5, MUT, 'lm' if v >= 0 else 'rm')
    cv.save(path)


def heat(path, title, sub, rows, cols):
    if not rows:
        return
    row = 24
    cv = Canvas(70 + row * len(rows), title, sub)
    ext = max(abs(v) for _, vs in rows for v in vs if v is not None) or 1
    x0, cw = 96, (W - 96 - 10) / len(cols)
    for j, c in enumerate(cols):
        cv.text(x0 + cw * j + cw / 2, 56, c, 10.5, MUT, 'mm')
    for i, (l, vs) in enumerate(rows):
        y = 66 + i * row
        cv.text(10, y + row / 2, l, 11, FG, 'lm', bold=True)
        for j, v in enumerate(vs):
            if v is None:
                continue
            a = min(0.75, 0.12 + abs(v) / ext * 0.63)
            cv.rect(x0 + cw * j + 1, y + 1, cw - 2, row - 2, mix(UP if v >= 0 else DN, a), 2)
            cv.text(x0 + cw * j + cw / 2, y + row / 2, '%+.1f' % v, 10.5, FG, 'mm')
    cv.save(path)


def gauges(path, title, sub, items, hl):
    cv = Canvas(70 + 28 * len(items) + (46 if hl else 0), title, sub)
    for k, (l, v) in enumerate(items):
        y = 52 + k * 28
        cv.text(12, y + 9, l, 11, FG, 'lm')
        cv.rect(96, y, 200, 18, GRID, 3)
        cv.rect(96, y, 200 * v / 100, 18, UP if v >= 50 else DN, 3)
        cv.line(196, y - 2, 196, y + 20, MUT, 1, dash=True)
        cv.text(302, y + 9, '%.1f%%' % v, 11, MUT, 'lm')
    if hl:
        y = 52 + 28 * len(items) + 6
        tot = (hl[0] + hl[1]) or 1
        wid = W - 24
        cv.rect(12, y, wid * hl[0] / tot, 18, UP, 3)
        cv.rect(12 + wid * hl[0] / tot, y, wid * hl[1] / tot, 18, DN, 3)
        cv.text(12, y + 22, '신고가 %d' % hl[0], 10.5, MUT)
        cv.text(W - 12, y + 22, '신저가 %d' % hl[1], 10.5, MUT, 'ra')
    cv.save(path)


def index_cards(path, title, sub, cards):
    if not cards:
        return
    cw, ch = (W - 24 - 8) / 2, 70
    rows = (len(cards) + 1) // 2
    cv = Canvas(46 + rows * (ch + 8) + 4, title, sub)
    for i, (t, v, s) in enumerate(cards):
        x, y = 12 + (i % 2) * (cw + 8), 48 + (i // 2) * (ch + 8)
        cv.rect(x, y, cw, ch, '#f6f7f9', 6)
        cv.text(x + 10, y + 8, t, 10.5, MUT)
        cv.text(x + 10, y + 24, ('▲ ' if v > 0 else ('▼ ' if v < 0 else '')) + '%+.2f%%' % v, 17, UP if v > 0 else (DN if v < 0 else FG), bold=True)
        if s:
            cv.text(x + 10, y + 47, s, 10, MUT)
    cv.save(path)


def stages(path, title, sub, parts):
    tot = sum(n for _, n, _ in parts) or 1
    cv = Canvas(124, title, sub)
    x = 12.0
    for l, n, c in parts:
        w = n / tot * (W - 24)
        if n:
            cv.rect(x, 50, w, 28, c)
            if w > 16:
                cv.text(x + w / 2, 64, n, 11, '#ffffff', 'mm', bold=True)
        x += w
    xx, yy = 12, 88
    for l, n, c in parts:
        cv.rect(xx, yy + 2, 9, 9, c, 2)
        t = '%s %d' % (l, n)
        cv.text(xx + 13, yy, t, 9.5, MUT)
        xx += 13 + cv.d.textlength(t, font=font(9.5)) / S + 12
        if xx > W - 90:
            xx, yy = 12, yy + 15
    cv.save(path)


def dotstrip(path, title, sub, groups, lo=-50, hi=2):
    row = 30
    cv = Canvas(70 + row * len(groups), title, sub)
    x0, x1 = 84, W - 14
    sx = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
    for t in (-40, -30, -20, -10, 0):
        if t < lo:
            continue
        cv.line(sx(t), 48, sx(t), 50 + row * len(groups), MUT if t == -20 else GRID, 1, dash=(t == -20))
        cv.text(sx(t), 56 + row * len(groups), '%d%%' % t, 9.5, MUT, 'mt')
    for k, (g, pts) in enumerate(groups):
        cy = 50 + k * row + row / 2
        cv.text(x0 - 8, cy, g, 11, FG, 'rm')
        for n, v in enumerate(sorted(pts)):
            cv.dot(sx(max(lo, min(hi, v))), cy + ((n % 2) * 4 - 2), 5.5, DN if v <= -20 else '#8b93a1')
    cv.save(path)


def daily_pngs(md, date):
    out = os.path.join(IMG, date)
    made = []
    def p(name):
        made.append(name); return os.path.join(out, name)
    h, rows = C.md_table(md, r'^지수')
    if h:
        ci, c50 = C.col(h, '일간'), C.col(h, '50일선')
        cards = [(r[0], C.num(r[ci]), ('50일선 대비 ' + r[c50]) if c50 is not None and len(r) > c50 else '') for r in rows if ci is not None and C.num(r[ci]) is not None]
        index_cards(p('1_indices.png'), '주요 지수 %s' % date, '일간 등락 · 출처 Finviz', cards)
    sec = C._sector_rows(md)
    if sec:
        hbars(p('2_sectors_day.png'), '섹터별 1일 등락', date, sorted([(x['name'], x['day']) for x in sec if x['day'] is not None], key=lambda a: -a[1]), lambda v: '%+.2f%%' % v)
        heat(p('3_sector_heat.png'), '섹터 기간별 열지도(%)', date, [(x['name'], [x['day'], x['w1'], x['m1'], x['q3']]) for x in sec], ['1일', '1주', '1개월', '3개월'])
    h, rows = C.md_table(md, r'^시장 폭')
    if rows:
        d = {r[0]: r for r in rows}
        find = lambda k: next((rr for kk, rr in d.items() if k in kk), None)
        r50, r200, rhl = find('50일선'), find('200일선'), find('신고가')
        items = []
        if r50 and C.num(r50[1]) is not None: items.append(('50일선 위', C.num(r50[1])))
        if r200 and C.num(r200[1]) is not None: items.append(('200일선 위', C.num(r200[1])))
        hl = None
        if rhl:
            nums = re.findall(r'[\d,]+', rhl[1])
            if len(nums) >= 2:
                hl = (float(nums[0].replace(',', '')), float(nums[1].replace(',', '')))
        if items:
            gauges(p('4_breadth.png'), '시장 폭', date, items, hl)
    h, rows = C.md_table(md, r'상대강도')
    if h and C.col(h, 'RS') is not None:
        ci = C.col(h, 'RS')
        hbars(p('5_rs.png'), 'ETF 상대강도(1일, SPY 대비 %p)', date, sorted([(r[0], C.num(r[ci])) for r in rows if C.num(r[ci]) is not None], key=lambda a: -a[1]), lambda v: '%+.2fp' % v, row=18, label_w=60)
    h, rows = C.md_table(md, r'^관심종목')
    if h and C.col(h, '일간') is not None:
        ci = C.col(h, '일간')
        hbars(p('6_watchlist.png'), '관심종목 1일 등락', date, sorted([(r[0], C.num(r[ci])) for r in rows if C.num(r[ci]) is not None], key=lambda a: -a[1]), lambda v: '%+.2f%%' % v, row=17, label_w=60)
    return made


def tracker_pngs(md, date):
    tabs = C.html_table(md)
    full = next((t for t in tabs if t and any('시총' in c for c in t[0]) and '단계' in t[0] and len(t) > 30), None)
    out = os.path.join(IMG, 'tracker')
    made = []
    etf = next((t for t in tabs if t and '쉬운 풀이' in t[0]), None)
    if etf:
        eh = etf[0]
        es, e1, e3 = C.col(eh, '섹터'), C.col(eh, '1개월 SPY'), C.col(eh, '3개월 SPY')
        for ci, fn, ttl in ((e3, '5_etf_3m.png', '섹터 ETF 3개월 강도 (SPY 대비)'), (e1, '6_etf_1m.png', '섹터 ETF 1개월 강도 (SPY 대비)')):
            items = [(r[es], C.num(r[ci])) for r in etf[1:] if C.num(r[ci]) is not None]
            hbars(os.path.join(out, fn), ttl, date + ' · 초록=시장보다 강함, 빨강=시장보다 약함', items, lambda v: '%+.1f%%p' % v, row=24)
            made.append(fn)
    lead = next((t for t in tabs if t and '주도주' in t[0] and '근접' in t[0]), None)
    if lead:
        lh = lead[0]
        ls, l4, le = C.col(lh, '섹터'), C.col(lh, '주도주'), C.col(lh, 'SPY 대비')
        ex = [(r[ls], C.num(r[le])) for r in lead[1:] if C.num(r[le]) is not None]
        hbars(os.path.join(out, '3_leader_strength.png'), '섹터별 3개월 강도 (SPY 대비)', date + ' · 위쪽일수록 강한 섹터', ex, lambda v: '%+.1f%%p' % v, row=24)
        cnt = [(r[ls], C.num(r[l4])) for r in lead[1:] if C.num(r[l4]) is not None]
        hbars(os.path.join(out, '4_leader_count.png'), '섹터별 주도주 수', date + ' · 4가지 조건 충족 (섹터당 5종목 중)', cnt, lambda v: '%d개' % v, row=24)
        made += ['3_leader_strength.png', '4_leader_count.png']
    if not full:
        return made
    h = full[0]
    cs, ctk, co, cst = C.col(h, '섹터'), C.col(h, '티커'), C.col(h, '고점 대비'), C.col(h, '단계')
    counts = {}
    for r in full[1:]:
        counts[r[cst]] = counts.get(r[cst], 0) + 1
    cols = {'위험': DN, '가치함정': '#d99a1f', '펀더멘털 미확인': '#8b93a1', '바닥 후보': UP, '바닥 탐색': '#e08a2e', '눌림': '#a9b0bd', '정상': '#6aa7a0'}
    parts = [(k, sum(v for kk, v in counts.items() if k in kk), c) for k, c in cols.items()]
    stages(os.path.join(out, '1_stages.png'), '대형주 바닥 추적 단계별 종목 수', date, parts)
    groups = {}
    for r in full[1:]:
        v = C.num(r[co])
        if v is not None:
            groups.setdefault(r[cs], []).append(v)
    dotstrip(os.path.join(out, '2_sector_drawdown.png'), '섹터별 고점 대비 낙폭', date + ' · 붉은 점은 -20% 이하', list(groups.items()))
    return made + ['1_stages.png', '2_sector_drawdown.png']


def main():
    if font(11) is None:
        print('charts_png: 한글 폰트를 찾지 못해 건너뜀')
        return 0
    if len(sys.argv) > 1:
        dates = [sys.argv[1]]
    else:
        fs = sorted(glob.glob(os.path.join(ML, 'daily', '20*.md')))
        dates = [os.path.basename(fs[-1])[:10]] if fs else []
    n = 0
    for d in dates:
        try:
            made = daily_pngs(open(os.path.join(ML, 'daily', d + '.md'), encoding='utf-8').read(), d)
            n += len(made)
        except Exception as e:  # 이미지 실패가 루틴을 막지 않게
            print('charts_png: 일간 %s 실패: %s' % (d, e))
    bt = sorted(glob.glob(os.path.join(ML, 'bottom-tracker', '20*.md')))
    if bt:
        try:
            n += len(tracker_pngs(open(bt[-1], encoding='utf-8').read(), os.path.basename(bt[-1])[:10]))
        except Exception as e:
            print('charts_png: 추적 실패: %s' % e)
    keep = sorted(d for d in glob.glob(os.path.join(IMG, '20*')) if os.path.isdir(d))[:-14]  # 최근 14일만 보관
    for d in keep:
        for f in glob.glob(os.path.join(d, '*.png')):
            os.remove(f)
        os.rmdir(d)
    print('charts_png: PNG %d개 생성' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())

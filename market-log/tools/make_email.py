#!/usr/bin/env python3
"""일간 기록 마크다운(market-log/daily/YYYY-MM-DD.md) → 이메일용 HTML 한 장.

사용: python3 market-log/tools/make_email.py market-log/daily/2026-10-19.md out.html [--lite] [--fragment]
  --lite: 요약판(메일용), --fragment: <body> 안쪽만(블로그 HTML 편집 모드 붙여넣기용)
- 메일 앱 호환을 위해 인라인 style + 표 레이아웃만 쓴다(외부 CSS/JS 없음, 폭 640px).
- 담는 내용: 한줄 요약, 30초 요약, 시장 국면, 지수, 섹터 막대, 관심종목 요약, 내일 체크포인트.
- 마크다운 구조가 바뀌어 섹션을 못 찾으면 그 섹션만 건너뛰고 stderr 에 경고한다.
"""
import html, re, sys

NL = chr(10)
UP, DN, MUT, BD, BG, ACC = '#117a3d', '#c0392b', '#6b7280', '#e3e5e8', '#f6f7f9', '#2563eb'


def esc(s):
    s = html.escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'<a href="\2" style="color:%s">\1</a>' % ACC, s)
    return s


def sections(md):
    out, cur, buf = {}, None, []
    for ln in md.split('\n'):
        if ln.startswith('## '):
            if cur:
                out[cur] = '\n'.join(buf)
            cur, buf = ln[3:].strip(), []
        elif cur:
            buf.append(ln)
    if cur:
        out[cur] = '\n'.join(buf)
    return out


def _norm(t):
    return re.sub(r'^\d+\.\s*', '', t).strip()


def sec(S, prefix):
    # 번호는 모델이 바꿀 수 있어(관심종목이 6번이 되는 등) 번호를 떼고 제목 앞부분으로 찾는다
    want = _norm(prefix)
    for k, v in S.items():
        if _norm(k).startswith(want):
            return v
    sys.stderr.write(f'경고: 섹션 없음 {prefix}\n')
    return ''


def table(txt):
    rows = []
    for ln in txt.split('\n'):
        if ln.startswith('|') and not re.match(r'^\|[-\s|]+\|$', ln):
            rows.append([c.strip() for c in ln.strip().strip('|').split('|')])
    return rows


def num(s):
    m = re.search(r'[-+]?\d+(?:\.\d+)?', s.replace(',', ''))
    return float(m.group(0)) if m else None


def color(s):
    v = num(s)
    return UP if v and v > 0 else DN if v and v < 0 else MUT


def h(title):
    return f'<tr><td style="padding:22px 0 6px;font-size:13px;font-weight:700;color:{MUT}">{esc(title)}</td></tr>'


def tbl(rows, widths=None, bold_first=True, color_cols=()):
    t = [f'<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:12px">']
    for i, r in enumerate(rows):
        t.append('<tr>')
        for j, c in enumerate(r):
            st = f'padding:6px 6px;border-bottom:1px solid {BD};'
            if i == 0:
                st += f'background:{BG};color:{MUT};font-weight:600;'
            elif j in color_cols:
                st += f'color:{color(c)};font-weight:600;'
            elif j == 0 and bold_first:
                st += 'font-weight:700;'
            t.append(f'<td style="{st}">{esc(c)}</td>')
        t.append('</tr>')
    t.append('</table>')
    return '<tr><td>' + ''.join(t) + '</td></tr>'


def bullets(txt):
    items = [re.sub(r'^[-*]\s*(\[.\]\s*)?', '', l).strip() for l in txt.split('\n') if re.match(r'^\s*[-*]\s', l)]
    return ''.join(f'<div style="margin:0 0 6px;font-size:13px;line-height:1.55">• {esc(i)}</div>' for i in items)


def compact(doc):
    # 반복되는 인라인 스타일을 <style> 클래스로 줄여 메일 크기를 줄인다(Gmail 은 head <style> 지원).
    rep = [
        (f'padding:6px 6px;border-bottom:1px solid {BD};background:{BG};color:{MUT};font-weight:600;', 'th'),
        (f'padding:6px 6px;border-bottom:1px solid {BD};font-weight:700;', 'tb'),
        (f'padding:6px 6px;border-bottom:1px solid {BD};color:{UP};font-weight:600;', 'tu'),
        (f'padding:6px 6px;border-bottom:1px solid {BD};color:{DN};font-weight:600;', 'td_'),
        (f'padding:6px 6px;border-bottom:1px solid {BD};', 'tc'),
    ]
    for st, cl in rep:
        doc = doc.replace(f'style="{st}"', f'class="{cl}"')
    css = (f'.th{{padding:6px;border-bottom:1px solid {BD};background:{BG};color:{MUT};font-weight:600}}'
           f'.tb{{padding:6px;border-bottom:1px solid {BD};font-weight:700}}'
           f'.tu{{padding:6px;border-bottom:1px solid {BD};color:{UP};font-weight:600}}'
           f'.td_{{padding:6px;border-bottom:1px solid {BD};color:{DN};font-weight:600}}'
           f'.tc{{padding:6px;border-bottom:1px solid {BD}}}')
    return doc.replace('</head>', f'<style>{css}</style></head>', 1)


def main(src, dst, lite=False, fragment=False):
    md = open(src, encoding='utf-8').read()
    S = sections(md)
    title = md.split('\n')[0].lstrip('# ').strip()
    state = re.search(r'시장 상태:\s*([^|\n]+)', md)
    state = state.group(1).strip() if state else ''
    one = re.search(r'\*\*한줄 요약\*\*:\s*(.+)', md)
    one = one.group(1).strip() if one else ''
    basis = re.search(r'\*\*(데이터 기준[^*]+)\*\*', md)
    basis = basis.group(1).strip() if basis else ''

    P = []
    P.append(f'<tr><td style="padding:0 0 4px"><div style="font-size:20px;font-weight:800">{esc(title)}</div>'
             f'<div style="font-size:12px;color:{MUT};margin-top:2px">{esc(basis)}</div>'
             f'<div style="margin-top:8px"><span style="display:inline-block;padding:3px 12px;border-radius:99px;background:{BG};border:1px solid {BD};font-weight:700;font-size:13px">{esc(state)}</span></div></td></tr>')
    if one:
        P.append(f'<tr><td style="padding:12px 14px;margin-top:10px;background:#eff6ff;border-left:4px solid {ACC};font-size:14px;line-height:1.6">{esc(one)}</td></tr>')

    P.append(h('30초 요약') + f'<tr><td style="padding:10px 14px;background:#fffbeb;border-radius:6px">{bullets(sec(S, "30초 요약"))}</td></tr>')

    t = table(sec(S, '시장 국면'))
    if t:
        P.append(h('시장 국면 판정 (강의 프레임워크, 참고용)'))
        P.append(tbl([[r[0], r[1], r[-1]] for r in t]))

    t = table(sec(S, '1. 지수'))
    if t:
        P.append(h('지수'))
        P.append(tbl([[r[0], r[1], r[2], r[4], r[5], r[7]] for r in t], color_cols=(2, 3, 4)))

    t = table(sec(S, '섹터 ('))[1:]
    if t:
        P.append(h('섹터 1일 등락 (Finviz)'))
        mx = max(abs(num(r[2]) or 0) for r in t) or 1
        bars = ['<table width="100%" cellpadding="0" cellspacing="0" style="font-size:12px">']
        for r in t:
            v = num(r[2]) or 0
            w = max(2, int(abs(v) / mx * 100))
            c = UP if v >= 0 else DN
            bars.append(f'<tr><td width="90" style="padding:3px 0">{esc(r[1])}</td>'
                        f'<td style="padding:3px 6px"><div style="width:{w}%;height:12px;background:{c};border-radius:3px;opacity:.85"></div></td>'
                        f'<td width="60" align="right" style="padding:3px 0;color:{c};font-weight:700">{v:+.2f}%</td></tr>')
        bars.append('</table>')
        P.append('<tr><td>' + ''.join(bars) + '</td></tr>')

    def meaning(txt):
        out = []
        for ln in txt.split(NL):
            if ln.startswith('**의미'):
                body = re.sub(r'^\*\*의미[^*]*\*\*:?\s*', '', ln)
                out.append(f'<tr><td style="padding:8px 12px;background:#f0fdf4;border-left:3px solid {UP};font-size:12.5px;line-height:1.55">{esc(body)}</td></tr>')
        return ''.join(out)

    def full(prefix, title, pick=None, cc=(), note_bullets=False):
        txt = sec(S, prefix)
        if not txt:
            return
        P.append(h(title))
        for blk in re.split(NL + r'\s*' + NL, txt):
            t = table(blk)
            if t:
                ok = pick and len(t[0]) > max(pick)
                P.append(tbl([[r[i] for i in pick] for r in t] if ok else t, color_cols=cc if ok or not pick else ()))
        P.append(meaning(txt))
        if note_bullets:
            P.append('<tr><td style="padding-top:6px">' + bullets(txt) + '</td></tr>')

    if lite:
        t = table(sec(S, '9. 관심종목'))
        if t:
            P.append(h('관심종목 (일간 등락)'))
            P.append(tbl([[r[0], r[1], r[3], r[10]] for r in t], color_cols=(2,)))
        t = table(sec(S, '4. 섹터 상대강도'))
        P.append(h('이 메일은 요약판입니다') + f'<tr><td style="font-size:12.5px;line-height:1.6">시장 폭, 섹터 상대강도, 순환매, 이슈, 오선 요약, 낙폭과대 후보, 금리·실적 일정 등 전체 내용은 Notion 일간 기록에서 확인하세요.</td></tr>')
    else:
        full('2. 시장 폭', '시장 폭 (50일선 위 50% 미만이면 경고)')
        full('4. 섹터 상대강도', '섹터 상대강도 (SPY 대비, %p)', pick=[0, 1, 2, 3, 4, 5, 6], cc=(2,))
        full('5. 순환매', '순환매·주도 섹터')
        full('6. 오늘의 이슈', '오늘의 이슈')
        P.append(h('오선 게시물 요약') + f'<tr><td>{bullets(sec(S, "7. 오선"))}</td></tr>')
        t = table(sec(S, '7. 오선'))
        if t:
            P.append(tbl(t))
        full('8. 낙폭과대', '낙폭과대 스캔 (엔벨로프 20,20)')
        full('9. 관심종목', '관심종목 (읽기 전용)', pick=[0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11], cc=(3,))
        P.append(h('금리·자산배분·분기 전략') + f'<tr><td>{bullets(sec(S, "10. 금리"))}</td></tr>')
        full('11. 실적', '실적·경제 일정 (다음 거래일~1주)')
        P.append(h('내 규칙 체크') + f'<tr><td>{bullets(sec(S, "12. 내 규칙"))}</td></tr>')


    tail = sec(S, '12. 내 규칙')
    m = re.search(r'\*\*다음 거래일 체크포인트\*\*:\s*(.+)', tail)
    if m:
        P.append(h('내일 볼 것') + f'<tr><td style="font-size:13px;line-height:1.6">{esc(m.group(1))}</td></tr>')

    P.append(f'<tr><td style="padding:22px 0 0;font-size:11px;color:{MUT};line-height:1.5">출처: Finviz, 오선의 미국 증시 게시물, 네이버 뉴스(익일 보강), investing.com. 본 기록은 투자 권유가 아닌 시장 흐름 기록용입니다. 상세 내용은 Notion 일간 기록을 참고하세요.</td></tr>')

    doc = ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>{html.escape(title)}</title></head>'
           '<body style="margin:0;padding:0;background:#ffffff;color:#1f2328;font-family:-apple-system,\'Apple SD Gothic Neo\',\'Noto Sans KR\',\'Malgun Gothic\',sans-serif">'
           '<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:16px 8px">'
           '<table width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%">' + ''.join(P) + '</table></td></tr></table></body></html>')
    if fragment:
        # 블로그 붙여넣기용: <html>/<head>/<body> 없이 바깥 표만 남긴다(인라인 스타일 유지)
        m = re.search(r'<body[^>]*>(.*)</body>', doc, re.S)
        font = "-apple-system,'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif"
        doc = f'<div style="font-family:{font};color:#1f2328">' + (m.group(1) if m else doc) + '</div>'
    open(dst, 'w', encoding='utf-8').write(doc)
    print('ok', dst, len(doc))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], '--lite' in sys.argv, '--fragment' in sys.argv)

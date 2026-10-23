#!/usr/bin/env python3
"""GitHub 백업 마크다운(market-log/daily/YYYY-MM-DD.md 등) → Notion 마크다운 변환 + 분할.

왜 필요한가: 일간 기록이 30KB를 넘으면 모델이 한 번의 도구 호출로 쓰다 섹션을 줄여 버렸다(2026-10-22 일간 페이지).
이 스크립트가 변환(표→<table>, 인용→callout, $·~ 이스케이프)과 분할을 결정적으로 처리한다.

사용법 (저장소 루트에서):
  python3 market-log/tools/to_notion.py market-log/daily/2026-10-22.md --out-dir /tmp/notion --max-chars 12000
    → /tmp/notion/part1.md, part2.md ...  (stdout: JSON {title, parts:[{file,chars,first_heading}], total_chars})
  루틴은 part1 로 페이지를 만들고(create-pages, content=part1.md 내용 그대로), 나머지는 순서대로
  update-page insert_content(position end)로 덧붙인다. 내용은 한 글자도 바꾸지 말고 그대로 넣는다.
  python3 market-log/tools/to_notion.py FILE --toggle "📅 2026-10-22 (목) · ..." --out-dir DIR
    → 월 페이지 맨 위에 넣는 날짜 토글 한 덩어리(part1.md 하나, 분할 안 함, 제목 헤딩은 한 단계 낮춤)
  --skip-heading "수집 로그"  : 해당 제목의 섹션 제외(여러 번 지정 가능)
  --drop-meta                 : '- 노션 기록:' 같은 첫 메타 줄 제거(기본 켜짐)
"""
import argparse, json, os, re, sys

CELL_SPLIT = re.compile(r'(?<!\\)\|')


def esc(s):
    s = s.replace('\\$', '$').replace('\\~', '~')
    s = s.replace('$', '\\$').replace('~', '\\~')
    s = re.sub(r'<(?=[\d\s=])', r'\\<', s)
    return s


def cell(c):
    return esc(c.strip().replace('\\|', '|'))


def is_sep(line):
    return bool(re.match(r'^\|[\s:|-]+\|\s*$', line))


def convert_table(lines):
    rows = []
    for ln in lines:
        if is_sep(ln):
            continue
        body = ln.strip()
        if body.startswith('|'):
            body = body[1:]
        if body.endswith('|') and not body.endswith('\\|'):
            body = body[:-1]
        rows.append([cell(c) for c in CELL_SPLIT.split(body)])
    out = ['<table header-row="true">']
    for r in rows:
        out.append('<tr>' + ''.join('<td>%s</td>' % c for c in r) + '</tr>')
    out.append('</table>')
    return out


def convert(md, drop_meta=True, skip_headings=(), nested=False):
    lines = md.split('\n')
    # 제목(H1)
    title = ''
    if lines and lines[0].startswith('# '):
        title = lines[0][2:].strip()
        lines = lines[1:]
    out, i, n = [], 0, len(lines)
    skipping = False
    section_first = {}
    cur_heading = ''
    seen_summary = False
    while i < n:
        ln = lines[i]
        if ln.startswith('## '):
            h = ln[3:].strip()
            skipping = any(h.startswith(s) for s in skip_headings)
            cur_heading = h
            seen_summary = h.startswith('30초 요약')
            if skipping:
                i += 1
                continue
            out.append(('### ' if nested else '## ') + esc(h))
            i += 1
            continue
        if skipping:
            i += 1
            continue
        if drop_meta and re.match(r'^(- )?노션 기록:', ln):
            i += 1
            continue
        if ln.startswith('# ') and not title:
            title = ln[2:].strip()
            i += 1
            continue
        if ln.startswith('|') and i + 1 < n and is_sep(lines[i + 1]):
            j = i
            while j < n and lines[j].startswith('|'):
                j += 1
            out.extend(convert_table(lines[i:j]))
            i = j
            continue
        if ln.startswith('>'):
            j = i
            blk = []
            while j < n and lines[j].startswith('>'):
                blk.append(re.sub(r'^>\s?', '', lines[j]))
                j += 1
            text = '\n\t'.join(esc(b) if b.strip() else '' for b in blk).rstrip()
            first = blk[0] if blk else ''
            em = re.match(r'^([^ -~\s])\ufe0f?\s*', first)
            if first.startswith('**한줄 요약'):
                icon, color = '💡', 'blue_bg'
            elif seen_summary:
                icon, color = '⏱️', 'yellow_bg'
            elif em and em.group(1) in ('⭐', '🔎', '📅', '📰', '🏛'):
                icon = em.group(1)
                color = {'⭐': 'yellow_bg', '🔎': 'blue_bg'}.get(icon, 'gray_bg')
                blk[0] = first[em.end():]
                text = '\n\t'.join(esc(b) if b.strip() else '' for b in blk).rstrip()
            else:
                icon, color = '💬', 'gray_bg'
            out.append('<callout icon="%s" color="%s">\n\t%s\n</callout>' % (icon, color, text))
            i = j
            continue
        m = re.match(r'^<details>\s*<summary>(.*?)</summary>\s*$', ln)
        if m or ln.strip() == '<details>':
            j = i + 1
            title_t = esc(m.group(1)) if m else ''
            if not m and j < n:
                m2 = re.match(r'^\s*<summary>(.*?)</summary>\s*$', lines[j])
                if m2:
                    title_t = esc(m2.group(1)); j += 1
            inner = []
            while j < n and lines[j].strip() != '</details>':
                inner.append(lines[j]); j += 1
            body = convert('\n'.join(inner), drop_meta=False, nested=True)[1]
            body = '\n'.join(('\t' + l if l else l) for l in body.split('\n'))
            out.append('<toggle>\n%s\n%s\n</toggle>' % (title_t, body))
            i = j + 1
            continue
        if ln.strip() == '</details>':
            i += 1
            continue
        out.append(esc(ln))
        i += 1
    text = '\n'.join(out)
    text = re.sub(r'\n{3,}', '\n\n', text).strip('\n')
    return title, text


def split_parts(text, max_chars):
    blocks = re.split(r'(?m)^(?=## )', text)
    parts, cur = [], ''
    for b in blocks:
        if not b:
            continue
        if cur and len(cur) + len(b) > max_chars:
            parts.append(cur); cur = ''
        if len(b) > max_chars:  # 한 섹션이 너무 길면 표 경계에서 추가 분할
            chunks, buf = [], ''
            for piece in re.split(r'(?m)^(?=<table|<toggle|### )', b):
                if buf and len(buf) + len(piece) > max_chars:
                    chunks.append(buf); buf = ''
                buf += piece
            if buf:
                chunks.append(buf)
            for c in chunks:
                if cur and len(cur) + len(c) > max_chars:
                    parts.append(cur); cur = ''
                cur += c
            continue
        cur += b
    if cur:
        parts.append(cur)
    return parts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--max-chars', type=int, default=12000)
    ap.add_argument('--toggle')
    ap.add_argument('--skip-heading', action='append', default=[])
    a = ap.parse_args()
    md = open(a.src, encoding='utf-8').read()
    os.makedirs(a.out_dir, exist_ok=True)
    for f in os.listdir(a.out_dir):
        if re.match(r'part\d+\.md$', f):
            os.remove(os.path.join(a.out_dir, f))
    if a.toggle:
        title, text = convert(md, skip_headings=a.skip_heading, nested=True)
        body = '\n'.join(('\t' + l if l else l) for l in text.split('\n'))
        out = '<toggle>\n%s\n%s\n</toggle>\n' % (esc(a.toggle), body)
        open(os.path.join(a.out_dir, 'part1.md'), 'w', encoding='utf-8').write(out)
        print(json.dumps({'title': title, 'mode': 'toggle', 'parts': [{'file': 'part1.md', 'chars': len(out)}], 'total_chars': len(out)}, ensure_ascii=False))
        return 0
    title, text = convert(md, skip_headings=a.skip_heading)
    parts = split_parts(text, a.max_chars)
    info = []
    for k, p in enumerate(parts, 1):
        fn = 'part%d.md' % k
        open(os.path.join(a.out_dir, fn), 'w', encoding='utf-8').write(p.strip('\n') + '\n')
        m = re.search(r'(?m)^## (.+)$', p)
        info.append({'file': fn, 'chars': len(p), 'first_heading': m.group(1) if m else ''})
    print(json.dumps({'title': title, 'mode': 'page', 'parts': info, 'total_chars': len(text)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())

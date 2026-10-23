#!/usr/bin/env python3
"""공개 저장소(GitHub Pages)에 올라가기 전 개인정보·비밀값 점검.

사용법 (저장소 루트에서):
  python3 market-log/tools/privacy_check.py            # market-log/ 와 docs/ 전체
  python3 market-log/tools/privacy_check.py PATH...    # 지정한 파일·폴더만
종료 코드 0 = 이상 없음, 1 = 의심 항목 발견(내용을 고친 뒤 다시 실행, 통과 전에는 커밋·푸시하지 않는다).
점검 항목: 이메일(허용 목록 제외), 전화번호, 주민등록번호 형태, 카드번호 형태, API 키·토큰 형태, 키 이름=값 대입,
계좌·보유 현황 표현(보유 수량, 평균단가, 평단, 내 계좌, 잔고 등 실제 포트폴리오 정보를 암시하는 말).
오탐은 '그 줄을 지우거나 일반 표현으로 바꾼다'(허용 목록은 이 파일의 ALLOW_EMAIL 에만 추가).
"""
import os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
ALLOW_EMAIL = ('noreply@anthropic.com', 'noreply@github.com', 'users.noreply.github.com')
TEXT_EXT = ('.md', '.html', '.csv', '.txt', '.json', '.py')
SKIP_DIRS = {'.git', '__pycache__', 'node_modules'}
INSTRUCTION_FILES = {'ADDENDUM.md', 'EARNINGS_CONTEXT.md', 'RERUN.md'}  # 지침 문서는 '보유 수량' 같은 금지 표현을 설명하므로 표현 점검만 제외
PATTERNS = [
    ('이메일', re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')),
    ('전화번호', re.compile(r'(?<!\d)01[016789][-. ]?\d{3,4}[-. ]?\d{4}(?!\d)')),
    ('주민등록번호 형태', re.compile(r'(?<![\d.])\d{6}-[1-4]\d{6}(?!\d)')),
    ('카드번호 형태', re.compile(r'(?<!\d)(?:\d{4}[- ]){3}\d{4}(?!\d)')),
    ('API 키·토큰 형태', re.compile(r'(?:ghp_|gho_|github_pat_|xox[bap]-|sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{12,}|AIza[0-9A-Za-z_-]{20,})[A-Za-z0-9_-]*')),
    ('키=값 대입', re.compile(r'(?i)(?:client_secret|api[_-]?key|secret|password|passwd|token)\s*[:=]\s*[\'"]?[A-Za-z0-9_\-]{12,}')),
    ('계좌·보유 현황 표현', re.compile(r'(?:보유\s*수량|보유\s*주식|평균\s*단가|평단가?|내\s*계좌|내\s*보유|계좌\s*번호|잔고\s*[:=]|내\s*포지션|매수\s*단가|손익\s*[:=])')),
]


def iter_files(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
            continue
        for d, dirs, files in os.walk(p):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for f in files:
                if f.endswith(TEXT_EXT):
                    yield os.path.join(d, f)


def main():
    paths = sys.argv[1:] or [os.path.join(ROOT, 'market-log'), os.path.join(ROOT, 'docs')]
    paths = [p for p in paths if os.path.exists(p)]
    hits = []
    for f in iter_files(paths):
        if os.path.basename(f) == 'privacy_check.py':
            continue
        try:
            lines = open(f, encoding='utf-8', errors='ignore').read().split('\n')
        except OSError:
            continue
        for n, ln in enumerate(lines, 1):
            for name, rx in PATTERNS:
                if name.startswith('계좌') and os.path.basename(f) in INSTRUCTION_FILES:
                    continue
                for m in rx.finditer(ln):
                    t = m.group(0)
                    if name == '이메일' and any(a in t for a in ALLOW_EMAIL):
                        continue
                    hits.append((os.path.relpath(f, ROOT), n, name, t[:40]))
    for f, n, name, t in hits[:60]:
        print('%s:%d  [%s] %s' % (f, n, name, t))
    print('privacy_check: %s (%d건)' % ('이상 없음' if not hits else '의심 항목 발견', len(hits)))
    return 1 if hits else 0


if __name__ == '__main__':
    sys.exit(main())

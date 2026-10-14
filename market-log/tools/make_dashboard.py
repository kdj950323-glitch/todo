# 일간 대시보드 HTML 생성기: python3 make_dashboard.py data.json out.html
import json,sys,html
d=json.load(open(sys.argv[1]))
def col(v,scale):
    a=min(abs(v)/scale,1)
    return ('var(--g%d)'%round(a*4)) if v>=0 else ('var(--r%d)'%round(a*4))
def sg(v): return f'{v:+.2f}%'
sec=''.join(f'<div class="cell" style="background:{col(s[1],1.6)}"><b>{html.escape(s[0])}</b><span class="big">{sg(s[1])}</span><small>1주 {s[2]:+.1f}% · 1개월 {s[3]:+.1f}%</small></div>' for s in sorted(d['sectors'],key=lambda x:-x[1]))
kp=''.join(f'<div class="kpi"><small>{html.escape(k[0])}</small><span class="big {"up" if k[1]>=0 else "dn"}">{sg(k[1])}</span></div>' for k in d['kpi'])
br=''.join(f'<div class="bar"><div class="lab"><span>{html.escape(b[0])}</span><b>{html.escape(b[2])}</b></div><div class="track"><i style="width:{b[1]}%;background:{b[3]}"></i></div></div>' for b in d['breadth'])
rs=''.join(f'<div class="rs"><div class="rh"><b>{html.escape(r[0])}</b><span>1주 {r[1]:+.1f}% · 1개월 {r[2]:+.1f}%</span></div><p>{html.escape(r[3])}</p></div>' for r in d['rs']) or '<p class="mut">유의미한 변화 없음</p>'
iss=''.join(f'<li>{html.escape(i)}</li>' for i in d['issues']); nxt=''.join(f'<li>{html.escape(i)}</li>' for i in d['next'])
T=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(d['date'])} 대시보드</title><style>
:root{{--bg:#fff;--fg:#1f2328;--mut:#6b7280;--card:#f6f7f9;--bd:#e3e5e8;--up:#117a3d;--dn:#c0392b;--g0:#eef6f1;--g1:#cfe8d9;--g2:#a4d4b8;--g3:#6fbb90;--g4:#3da06a;--r0:#faf0ee;--r1:#f3d4cf;--r2:#e9aea6;--r3:#dc8579;--r4:#cc5646}}
@media(prefers-color-scheme:dark){{:root{{--bg:#16181c;--fg:#e8eaed;--mut:#9aa0a6;--card:#1f2226;--bd:#2c3036;--up:#5fd08b;--dn:#ff8a7a;--g0:#1d2a23;--g1:#22402f;--g2:#24543a;--g3:#27694a;--g4:#2a8057;--r0:#2d2220;--r1:#472a26;--r2:#5e312c;--r3:#7a3a33;--r4:#964740}}}}
*{{box-sizing:border-box}}body{{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}}
h1{{font-size:18px;margin:0 0 2px}}h2{{font-size:13px;color:var(--mut);margin:20px 0 8px;text-transform:none;letter-spacing:.02em}}.mut,small{{color:var(--mut)}}
.state{{display:inline-block;padding:2px 10px;border-radius:99px;background:var(--card);border:1px solid var(--bd);font-weight:600;margin-left:6px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px}}.kpi,.rs,.cell{{border-radius:10px}}.kpi{{background:var(--card);border:1px solid var(--bd);padding:10px 12px;display:flex;flex-direction:column}}
.big{{font-size:20px;font-weight:700}}.up{{color:var(--up)}}.dn{{color:var(--dn)}}
.heat{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:6px}}.cell{{padding:8px 10px;display:flex;flex-direction:column;border:1px solid var(--bd)}}.cell .big{{font-size:17px}}.cell small{{font-size:11px;color:var(--fg);opacity:.75}}
.bar{{margin-bottom:8px}}.lab{{display:flex;justify-content:space-between;font-size:13px}}.track{{height:10px;border-radius:5px;background:var(--card);border:1px solid var(--bd);overflow:hidden}}.track i{{display:block;height:100%}}
.rs{{background:var(--card);border:1px solid var(--bd);padding:10px 12px;margin-bottom:6px}}.rh{{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}}.rh span{{color:var(--mut);font-size:12px}}.rs p{{margin:4px 0 0;font-size:13px}}
ul{{margin:0;padding-left:18px}}li{{margin-bottom:3px}}.foot{{margin-top:18px;font-size:11px;color:var(--mut)}}
</style></head><body>
<h1>{html.escape(d['date'])} 미국 증시 <span class="state">{html.escape(d['state'])}</span></h1><div class="mut">{html.escape(d['headline'])}</div>
<h2>지수 · 시장 폭</h2><div class="kpis">{kp}</div>
<h2>시장 폭 (경고: 50일선 위 50% 미만)</h2>{br}
<h2>섹터 히트맵 (1일 기준 색)</h2><div class="heat">{sec}</div>
<h2>산업 간 상대강도 — 유의미한 변화만 (1주 ±5%p / 1개월 ±7%p)</h2>{rs}
<h2>오늘의 이슈</h2><ul>{iss}</ul><h2>다음 거래일 체크</h2><ul>{nxt}</ul>
<div class="foot">{html.escape(d['source'])} · 투자 권유 아님</div></body></html>'''
open(sys.argv[2],'w').write(T)

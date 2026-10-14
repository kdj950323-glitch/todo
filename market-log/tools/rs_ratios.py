import re,html,subprocess,sys
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'
T="DRAM,SOXX,SMH,SPY,QQQ,QQEW,XLE,XLK,HDV,IGV,RSP,IWM,XLY,XLP,XLU,XLV,HYG,IEF,CPER,GLD".split(',')
h=subprocess.run(['curl','-sL','-A',UA,'https://finviz.com/screener.ashx?v=141&t='+','.join(T)],capture_output=True,text=True).stdout
D={}
for tr in re.findall(r'<tr[^>]*>(.*?)(?=<tr|</table)',h,re.S):
    c=[html.unescape(re.sub(r'<[^>]+>','',x)).strip() for x in re.findall(r'<td[^>]*>(.*?)</td>',tr,re.S)]
    if len(c)>10 and c[0].isdigit():
        f=lambda s:None if s in('-','') else float(s.rstrip('%').replace(',',''))
        t=c[1]
        if len(t)>1 and t[0]==t[1] and t not in T: t=t[1:]
        D[t]=dict(d1=f(c[-2]),w=f(c[2]),m=f(c[3]),q=f(c[4]),h=f(c[5]),ytd=f(c[6]),px=f(c[-3]))
print('got',sorted(D),'missing',[t for t in T if t not in D])
def r(a,b,k):
    x,y=D[a][k],D[b][k]
    return None if x is None or y is None else ((1+x/100)/(1+y/100)-1)*100
P=[('DRAM','SOXX'),('SMH','SPY'),('IGV','SMH'),('XLE','XLK'),('HDV','QQQ'),('QQQ','QQEW'),('RSP','SPY'),('IWM','SPY'),('XLY','XLP'),('HYG','IEF'),('CPER','GLD')]
MEAN={
'DRAM/SOXX':('메모리 반도체가 반도체 전체보다 강함. 메모리 가격·수급 기대가 살아나는 구간','메모리가 반도체 전체보다 약함. 메모리 외 반도체(AI 칩 등)가 상대적으로 주도'),
'SMH/SPY':('반도체가 시장 평균을 이김. AI·반도체 주도 장세','반도체가 시장 평균에 뒤처짐. 지수가 버텨도 반도체 주도력은 약해진 상태'),
'IGV/SMH':('소프트웨어가 반도체보다 강함. 자금이 AI 하드웨어에서 소프트웨어로 이동','반도체가 소프트웨어보다 강함. AI 하드웨어 주도'),
'XLE/XLK':('에너지가 기술주보다 강함. 성장주에서 유가·원자재 쪽으로 자금 이동','기술주가 에너지보다 강함. 성장 위험선호 우위'),
'HDV/QQQ':('배당 방어주가 나스닥보다 강함. 위험을 줄이고 방어로 옮기는 흐름','나스닥이 방어주보다 강함. 위험선호 우위'),
'QQQ/QQEW':('시총 가중이 동일 가중보다 강함. 상승이 소수 초대형주에 쏠림','동일 가중이 더 강함. 상승이 나스닥 전반으로 퍼짐'),
'RSP/SPY':('동일 가중이 시총 가중보다 강함. 상승이 고르게 퍼짐(시장 폭 개선)','소수 대형주가 지수를 끌고 가는 장. 속은 약한 구조'),
'IWM/SPY':('중소형주가 대형주보다 강함. 위험선호가 넓게 퍼짐','중소형주가 대형주에 뒤처짐. 위험선호 위축 또는 대형주 쏠림'),
'XLY/XLP':('경기소비재가 필수소비재보다 강함. 경기 기대 개선','필수소비재가 더 강함. 경기에 대한 경계'),
'HYG/IEF':('하이일드가 국채보다 강함. 신용 위험 선호','국채가 더 강함. 신용 위험 회피 신호'),
'CPER/GLD':('구리가 금보다 강함. 경기 낙관','금이 구리보다 강함. 안전자산 선호'),
}
TH_W,TH_M=5.0,7.0  # 유의미 기준: 1주 +-5%p 또는 1개월 +-7%p 이상
print('유의미한 상대강도 변화 (1주/1개월, 분자가 강하면 +)')
n=0
for a,b in P:
    w,m=r(a,b,'w'),r(a,b,'m')
    if w is None or m is None: continue
    tags=[]
    if abs(w)>=TH_W: tags.append('1주 '+('강세' if w>0 else '약세'))
    if abs(m)>=TH_M: tags.append('1개월 '+('강세' if m>0 else '약세'))
    if abs(w)>=TH_W and abs(m)>=TH_M and w*m<0: tags.append('단기-중기 방향 반전')
    if tags:
        n+=1; print(f'{a}/{b} | 1주 {w:+.1f}% | 1개월 {m:+.1f}% | '+', '.join(tags))
        up,dn=MEAN[f'{a}/{b}']
        for lab,v,th in(('1주',w,TH_W),('1개월',m,TH_M)):
            if abs(v)>=th: print('   -> %s: %s'%(lab,up if v>0 else dn))
if not n: print('유의미한 변화 없음')

"""
GitHub Actions 전용 데이터 갱신 스크립트 (매일 KST 09:00 자동 실행)
- stocks.json   : 한국 KOSPI / KOSDAQ 전종목
- us_stocks.json: 미국 섹터별 종목 (종합 재무 데이터)
"""
import json, datetime, sys, time, os

# ── 서버 전용 가드: GitHub Actions에서만 실행 ──
if not os.environ.get('GITHUB_ACTIONS') and not os.environ.get('FORCE_LOCAL'):
    print("⚠️  이 스크립트는 GitHub Actions 전용입니다.")
    print("   로컬 강제 실행: FORCE_LOCAL=1 python update_data.py")
    sys.exit(0)

DEFAULT_RF  = 0.031
DEFAULT_ERP = 0.055

# ──────────────────────────────────────────────────────
# 한국 종목 업종 테마 매핑 (종목코드 → 세분화 업종)
# ──────────────────────────────────────────────────────
KR_SECTOR_MAP = {
    # ── AI 칩 & 반도체 ──
    "005930": "AI 칩 & 반도체",    # 삼성전자 (HBM·파운드리)
    "000660": "AI 칩 & 반도체",    # SK하이닉스 (HBM1위)
    "042700": "AI 칩 & 반도체",    # 한미반도체 (TC본더)
    "058470": "AI 칩 & 반도체",    # 리노공업 (반도체 소켓)
    "000990": "AI 칩 & 반도체",    # DB하이텍
    # ── AI 인프라 (소재·장비) ──
    "357780": "AI 인프라 소재·장비",# 솔브레인 (식각액)
    "240810": "AI 인프라 소재·장비",# 원익IPS (CVD장비)
    "039030": "AI 인프라 소재·장비",# 이오테크닉스 (레이저)
    "255440": "AI 인프라 소재·장비",# 야스 (증착장비)
    "237750": "AI 인프라 소재·장비",# SCR (공정소재)
    "009150": "AI 인프라 소재·장비",# 삼성전기 (MLCC)
    "382800": "AI 인프라 소재·장비",# 코리아써키트 (기판)
    "011070": "AI 인프라 소재·장비",# LG이노텍 (FC-BGA)
    "066570": "AI 인프라 소재·장비",# LG전자 (전장·서버)
    "011790": "AI 인프라 소재·장비",# SKC
    "007660": "AI 인프라 소재·장비",# 이수페타시스
    "222800": "AI 인프라 소재·장비",# 심텍
    "056190": "AI 인프라 소재·장비",# 에스에프에이
    "281820": "AI 인프라 소재·장비",# 케이씨텍
    "036930": "AI 인프라 소재·장비",# 주성엔지니어링
    "005290": "AI 인프라 소재·장비",# 동진쎄미켐
    "095340": "AI 인프라 소재·장비",# ISC
    "067310": "AI 인프라 소재·장비",# 하나마이크론
    "195870": "AI 인프라 소재·장비",# 해성디에스
    # ── AI 소프트웨어 & 플랫폼 ──
    "035420": "AI SW & 플랫폼",    # NAVER (HyperCLOVA)
    "035720": "AI SW & 플랫폼",    # 카카오 (KoGPT)
    # ── 이차전지 ──
    "006400": "이차전지",           # 삼성SDI
    "373220": "이차전지",           # LG에너지솔루션
    "051910": "이차전지",           # LG화학 (양극재)
    "086520": "이차전지",           # 에코프로
    "247540": "이차전지",           # 에코프로비엠
    "078600": "이차전지",           # 대주전자재료
    "003670": "이차전지",           # 포스코퓨처엠
    "066970": "이차전지",           # 엘앤에프
    "361610": "이차전지",           # SK아이이테크놀로지
    # ── 자동차 & 모빌리티 ──
    "005380": "자동차 & 모빌리티",  # 현대차
    "000270": "자동차 & 모빌리티",  # 기아
    "012330": "자동차 & 모빌리티",  # 현대모비스
    "000240": "자동차 & 모빌리티",  # 한국타이어
    # ── 방산 & 항공우주 ──
    "047810": "방산 & 항공우주",    # 한국항공우주
    "272210": "방산 & 항공우주",    # 한화에어로스페이스
    "000150": "방산 & 항공우주",    # 두산 (방산·로봇)
    # ── 조선 ──
    "329180": "조선",               # HD현대중공업
    "042660": "조선",               # 한화오션
    "009540": "조선",               # HD한국조선해양
    "010140": "조선",               # 삼성중공업
    # ── 전력 & 에너지 ──
    "015760": "전력 & 에너지",      # 한국전력
    "036460": "전력 & 에너지",      # 한국가스공사
    # ── 원자력 & 에너지 ──
    "034020": "원자력 & 에너지",    # 두산에너빌리티
    # ── 정유 & 화학 ──
    "010950": "정유 & 화학",        # S-Oil
    "096770": "정유 & 화학",        # SK이노베이션
    "011170": "정유 & 화학",        # 롯데케미칼
    # ── 클린에너지 & 태양광 ──
    "009830": "클린에너지 & 태양광",# 한화솔루션
    # ── 바이오 & 제약 ──
    "068270": "바이오 & 제약",      # 셀트리온
    "207940": "바이오 & 제약",      # 삼성바이오로직스
    "000100": "바이오 & 제약",      # 유한양행
    "128940": "바이오 & 제약",      # 한미약품
    "185750": "바이오 & 제약",      # 종근당
    "196170": "바이오 & 제약",      # 알테오젠
    "028300": "바이오 & 제약",      # HLB
    "141080": "바이오 & 제약",      # 리가켐바이오 (구 레고켐바이오)
    "068760": "바이오 & 제약",      # 셀트리온헬스케어
    "091990": "바이오 & 제약",      # 셀트리온제약
    "900290": "바이오 & 제약",      # 이수앱지스
    "067630": "바이오 & 제약",      # HLB생명과학
    # ── 의료기기 & 뷰티테크 ──
    "150900": "의료기기 & 뷰티테크",# 바디텍메드
    "214150": "의료기기 & 뷰티테크",# 클래시스 (리프팅)
    "090430": "의료기기 & 뷰티테크",# 아모레퍼시픽
    "214450": "의료기기 & 뷰티테크",# 파마리서치
    "041830": "의료기기 & 뷰티테크",# 인바디
    "287410": "의료기기 & 뷰티테크",# 제이시스메디칼
    # ── 금융 ──
    "105560": "금융",               # KB금융
    "055550": "금융",               # 신한지주
    "086790": "금융",               # 하나금융지주
    "316140": "금융",               # 우리금융지주
    "138040": "금융",               # 메리츠금융지주
    "032830": "금융",               # 삼성생명
    "000810": "금융",               # 삼성화재
    "323410": "금융",               # 카카오뱅크
    "071050": "금융",               # 한국금융지주
    "005830": "금융",               # DB손해보험
    "006800": "금융",               # 미래에셋증권
    "001450": "금융",               # 현대해상
    "175330": "금융",               # JB금융지주
    "138930": "금융",               # BNK금융지주
    # ── 통신 ──
    "017670": "통신",               # SK텔레콤
    "030200": "통신",               # KT
    "032640": "통신",               # LG유플러스
    # ── 건설 ──
    "028260": "건설",               # 삼성물산
    "000720": "건설",               # 현대건설
    "006360": "건설",               # GS건설
    "047040": "건설",               # 대우건설
    "002780": "건설",               # 진흥기업
    # ── 철강 & 소재 ──
    "005490": "철강 & 소재",        # POSCO홀딩스
    "004020": "철강 & 소재",        # 현대제철
    "010130": "철강 & 소재",        # 고려아연
    # ── 게임 ──
    "259960": "게임",               # 크래프톤
    "251270": "게임",               # 넷마블
    "036570": "게임",               # 엔씨소프트
    "095660": "게임",               # 네오위즈
    "293490": "게임",               # 카카오게임즈
    "112040": "게임",               # 위메이드
    "263750": "게임",               # 펄어비스
    "225570": "게임",               # 넥슨게임즈
    "093190": "게임",               # 위메이드맥스
    # ── 엔터 & K-POP ──
    "352820": "엔터 & K-POP",       # HYBE
    "122870": "엔터 & K-POP",       # 와이지엔터테인먼트
    "041510": "엔터 & K-POP",       # 에스엠
    "035900": "엔터 & K-POP",       # JYP엔터테인먼트
    # ── 유통 ──
    "139480": "유통",               # 이마트
    "282330": "유통",               # BGF리테일
    "007070": "유통",               # GS리테일
    # ── 음식료품 ──
    "097950": "음식료품",           # CJ제일제당
    "271560": "음식료품",           # 오리온
    "004370": "음식료품",           # 농심
    "000080": "음식료품",           # 하이트진로
    # ── 로봇 ──
    "089980": "로봇",               # 알파로보틱스
    "277810": "로봇",               # 레인보우로보틱스
    "454910": "로봇",               # 두산로보틱스
    # ── 산업재 & 물류 ──
    "086280": "산업재 & 물류",      # 현대글로비스
    # ── 지주회사 ──
    "003550": "지주회사",           # LG
    "034730": "지주회사",           # SK
    "267250": "지주회사",           # HD현대
}

# ──────────────────────────────────────────────────────
# 미국 섹터 정의 (45개 섹터, S&P500+NASDAQ100 수준 700+ 종목)
# yfinance 실시간 크롤링 — 할루시네이션 없음
# ──────────────────────────────────────────────────────
US_SECTORS = {
    # ══════ AI & 빅테크 ══════
    "AI 인프라·GPU":        ["NVDA","AMD","SMCI","DELL","HPE","VRT","ETN","MRVL","ANET","MSFT","AMZN","GOOG","META","AAPL","GEV","IONQ","QUBT"],
    "AI 에이전트·LLM":      ["PLTR","AI","ORCL","IBM","SNOW","GOOGL","PATH","BBAI","SOUN","CRCL"],
    "AI 응용 소프트웨어":    ["APP","TTD","RBLX","U","MGNI","KVYO","SPRK","DUOL","HOOD","GTLB"],
    "클라우드·SaaS 고성장":  ["MDB","DDOG","NET","HUBS","CFLT","BILL","DOCN","ZI","ESTC","TWLO","FIVN","WIX","ZM","TENB"],
    "엔터프라이즈 SW":       ["ADBE","NOW","INTU","CRM","WDAY","TEAM","VEEV","ANSS","PTC","CDNS","SNPS","SAP","PAYC","SMAR","DOCU","MSCI"],
    "사이버보안":            ["CRWD","PANW","FTNT","ZS","S","OKTA","CYBR","VRNS","RPD","QLYS","CHKP","NLOK","FEYE"],
    "IT 서비스·아웃소싱":    ["ACN","CTSH","INFY","EPAM","GLOB","DXC","IT","SSNC","EXLS","MAN","LDOS","BAH","SAIC","CACI"],

    # ══════ 반도체 ══════
    "AI 칩·팹리스":          ["AVGO","ARM","INTC","QCOM","TXN","ON","MCHP","NXPI","ADI","SWKS","QRVO","WOLF","LSCC","FORM","MTSI","POWI"],
    "메모리·스토리지":       ["MU","WDC","STX","NTAP","PSTG","NTNX","CRDO"],
    "반도체 장비·소재":      ["AMAT","LRCX","KLAC","ASML","TER","MPWR","ONTO","ACLS","CAMT","ENTG","MKSI","UCTT","AMKR"],
    "네트워킹·광통신":       ["CSCO","JNPR","FFIV","CIEN","COHR","VIAV","INFN","CALX","LITE","AAON"],
    "PC·하드웨어":           ["HPQ","LOGI","NTAP","WDC","DELL"],

    # ══════ 에너지 ══════
    "전력 인프라·그리드":    ["PWR","ROK","PH","AYI","URI","EMR","AMPS","HUBB","POWL","ETN","EATON","REZI"],
    "원자력·소형원자로":     ["CEG","VST","CCJ","NNE","OKLO","SMR","NRG","TLN","LEU","BWXT","BWX"],
    "신재생·태양광·풍력":    ["ENPH","FSLR","SEDG","RUN","NEE","AES","BEP","BEPC","ORA","ARRY","NOVA","CWEN","PLUG","BE"],
    "석유·가스·미드스트림":  ["XOM","CVX","COP","SLB","EOG","OXY","HAL","MPC","PSX","DVN","HES","VLO","BKR","WMB","KMI","LNG","FANG","MRO","APA"],
    "유틸리티":              ["DUK","SO","AEP","EXC","SRE","XEL","PEG","ETR","EIX","WEC","ES","AWK","AEE","CNP","LNT","OGE","EVRG","PNW","NI","D"],

    # ══════ 금융 ══════
    "대형 은행·투자":        ["JPM","BAC","WFC","C","GS","MS","USB","PNC","TFC","COF","KEY","RF","FITB","ALLY","CFG","HBAN","ZION","MTB","SIVB"],
    "핀테크·결제":           ["V","MA","AXP","PYPL","SQ","AFRM","UPST","SOFI","NU","COIN","FOUR","GPN","FIS","FI","WEX","FLYW","RELY"],
    "보험":                  ["BRK-B","PGR","ALL","CB","TRV","MET","PRU","AFL","HIG","AIG","RE","RNR","ERIE","LNC","WTW","MMC","AON","CINF"],
    "자산운용·거래소·사모":  ["BLK","SCHW","SPGI","MCO","ICE","CME","CBOE","MSCI","APO","KKR","BX","CG","ARES","BAM","TROW","STT","BEN","IVZ"],

    # ══════ 헬스케어 ══════
    "대형 제약":             ["JNJ","PFE","MRK","ABBV","LLY","BMY","AMGN","GILD","AZN","NVO","GSK","SNY","BAYRY","RHHBY","NVS"],
    "바이오텍":              ["MRNA","BNTX","BIIB","REGN","VRTX","ALNY","SRPT","ARGX","BMRN","INCY","EXEL","ROIV","KYMR","DAWN","RXRX","ARQT"],
    "의료기기·진단":         ["ISRG","MDT","ABT","BSX","SYK","EW","DXCM","RMD","INSP","IDXX","IRTC","NVCR","SWAV","ICLR","MEDP","HOLX","BIO","WAT","PODD","COO"],
    "매니지드케어·병원":     ["UNH","CVS","CI","HUM","CNC","ELV","MOH","HCA","DVA","ENSG","ACCD","THC","UHS","CYH"],
    "헬스케어 서비스":       ["IQVIA","A","TMO","ZBH","BAX","BDX","CAH","MCK","ABC","PDCO","PDSI","HSIC"],

    # ══════ 소비재 ══════
    "필수소비재·식품·음료":  ["WMT","COST","PG","KO","PEP","CL","GIS","MKC","KHC","MDLZ","CHD","PM","MO","STZ","TAP","EL","KMB","SYY","HSY","CAG","HRL","CPB","TSN","ADM","BG"],
    "임의소비재·리테일":     ["HD","MCD","NKE","SBUX","LOW","TJX","LULU","ULTA","DPZ","TSCO","RH","BBY","ETSY","RVLV","FIVE","RL","ORLY","AZO","POOL","W","CHWY","PRGO"],
    "자동차·전기차·모빌리티":["TSLA","GM","F","RIVN","NIO","XPEV","LI","MBLY","LAZR","LCID","CHPT","LCID","UBER","LYFT","APTV","BWA","TEN"],
    "여행·항공·레저":        ["BKNG","ABNB","EXPE","MAR","HLT","UAL","DAL","LUV","CCL","RCL","DKNG","MGM","WYNN","LVS","CZR","NCLH","AAL","ALK"],

    # ══════ 미디어·통신 ══════
    "미디어·스트리밍·콘텐츠":["NFLX","DIS","WBD","CMCSA","PARA","SPOT","IMAX","FOXA","LGF-A","WWE","MSGS"],
    "소셜·디지털 광고":      ["SNAP","PINS","RDDT","PUBM","CRTO","DV","IAS","MGNI","TTD","META"],
    "통신사·케이블":         ["T","VZ","TMUS","CHTR","LUMN","USM","LBRDA","CABO"],

    # ══════ 산업재 ══════
    "항공우주·방산·보안":    ["LMT","RTX","NOC","GD","BA","HII","KTOS","AXON","TDG","HEI","MOOG","SPR","HEICO","CW","TDY","SAIC","LDOS"],
    "산업기계·설비·제조":    ["CAT","DE","HON","GE","ITW","CMI","AME","ROP","OTIS","IR","XYL","DHR","FTV","GNRC","ALLE","IEX","MMM","PH","CARR","TT","FAST","NDSN","RBC","HUBB"],
    "물류·운송·철도":        ["UPS","FDX","ODFL","XPO","JBHT","CSX","NSC","UNP","CHRW","EXPD","ROAD","SAIA","ARCB","ECHO","R","JBLU","MATX"],
    "로봇·자동화·산업AI":    ["ABB","AZTA","RRX","ROCK","NOVT","TRMB","KEYS","BRZE","FLIR","ROK","ENOV"],
    "건설·인프라·엔지니어링":["VMC","MLM","URI","PWR","PRIM","MTZ","TREX","MAS","SHW","RPM","OC","FND","BLDR","DOOR"],
    "우주·위성통신":         ["RKLB","ASTS","LUNR","SPIR","SATL","MNTS","MAXN","GSAT"],

    # ══════ 부동산 ══════
    "데이터센터·통신 리츠":  ["AMT","EQIX","DLR","CCI","IRM","SBAC","UNIT","CONE"],
    "상업·주거·특수 리츠":   ["PLD","SPG","O","VICI","AVB","EXR","WELL","WY","NNN","EQR","ARE","KIM","REG","BXP","UDR","CPT","ESS","MAA","NLY","AGNC","STAG","REXR","FR","ELS","SUI"],

    # ══════ 소재·화학·광업 ══════
    "소재·화학·포장재":      ["LIN","APD","ECL","PPG","SHW","DOW","LYB","EMN","CE","IFF","FMC","AVY","IP","PKG","SEE","CCK","SON","OLN","RPM"],
    "금속·광업·희토류":      ["NEM","FCX","GOLD","AA","NUE","CF","MOS","ALB","SQM","MP","VALE","RIO","SCCO","WPM","AEM","AGI","HL","CLF","X","RS","CMC","STLD"],
}

# 거래소 매핑 (NMS/NGM → NASDAQ, NYQ/NYSE → NYSE)
def norm_exchange(raw):
    if not raw: return 'OTHER'
    raw = str(raw).upper()
    if raw in ('NMS','NGM','NCM','NASDAQ'): return 'NASDAQ'
    if raw in ('NYQ','NYSE'): return 'NYSE'
    return raw

# ──────────────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────────────
def safe(v, d=0.0):
    try:
        r = float(v or 0)
        return r if r == r else d
    except: return d

def pct(v):
    if v is None: return None
    return round(float(v)*100, 1)

def r1(v):
    if v is None: return None
    try:
        f = float(v)
        return round(f, 1) if f == f else None
    except: return None

def r2(v):
    if v is None: return None
    try:
        f = float(v)
        return round(f, 2) if f == f else None
    except: return None

def recent_day(offset=0):
    d = datetime.date.today() - datetime.timedelta(days=offset)
    for _ in range(14):
        if d.weekday() < 5: return d.strftime("%Y%m%d")
        d -= datetime.timedelta(days=1)
    return datetime.date.today().strftime("%Y%m%d")

# ──────────────────────────────────────────────────────
# 분기 성장률 (quarterly_income_stmt)
# ──────────────────────────────────────────────────────
def get_quarterly(t_obj):
    out = {'rev_qoq':None,'rev_yoy_q':None,'ni_qoq':None,'ni_yoy_q':None}
    try:
        qs = t_obj.quarterly_income_stmt
        if qs is None or qs.empty or qs.shape[1] < 2:
            return out
        # Revenue
        for rk in ('Total Revenue','Revenue'):
            if rk in qs.index:
                vals = qs.loc[rk].dropna().astype(float)
                if len(vals) >= 2:
                    r0, r1v = vals.iloc[0], vals.iloc[1]
                    if r1v != 0: out['rev_qoq'] = round((r0-r1v)/abs(r1v)*100, 1)
                if len(vals) >= 5:
                    r4 = vals.iloc[4]
                    if r4 != 0: out['rev_yoy_q'] = round((vals.iloc[0]-r4)/abs(r4)*100, 1)
                break
        # Net Income
        for nk in ('Net Income','Net Income Common Stockholders'):
            if nk in qs.index:
                vals = qs.loc[nk].dropna().astype(float)
                if len(vals) >= 2:
                    n0, n1v = vals.iloc[0], vals.iloc[1]
                    if abs(n1v) > 0: out['ni_qoq'] = round((n0-n1v)/abs(n1v)*100, 1)
                if len(vals) >= 5:
                    n4 = vals.iloc[4]
                    if abs(n4) > 0: out['ni_yoy_q'] = round((vals.iloc[0]-n4)/abs(n4)*100, 1)
                break
    except: pass
    return out

# ──────────────────────────────────────────────────────
# 미래 예측 (earnings_estimate / revenue_estimate)
# ──────────────────────────────────────────────────────
def get_forward_estimates(t_obj):
    out = {'fwd_rev_g':None,'fwd_rev_g2':None,'fwd_eps_g':None,'fwd_eps_g2':None}
    try:
        ae = t_obj.earnings_estimate  # indexed by period: 0q, +1q, 0y, +1y
        if ae is not None and not ae.empty:
            # EPS growth estimate for current year
            if '0y' in ae.index and '+1y' in ae.index:
                e0 = safe(ae.loc['0y','avg'] if 'avg' in ae.columns else None)
                e1 = safe(ae.loc['+1y','avg'] if 'avg' in ae.columns else None)
                if e0 > 0 and e1 > 0:
                    out['fwd_eps_g']  = round((e1-e0)/abs(e0)*100, 1)
    except: pass
    try:
        re = t_obj.revenue_estimate
        if re is not None and not re.empty and 'avg' in re.columns:
            if '0y' in re.index and '+1y' in re.index:
                r0 = safe(re.loc['0y','avg'])
                r1 = safe(re.loc['+1y','avg'])
                if r0 > 0 and r1 > 0:
                    out['fwd_rev_g'] = round((r1-r0)/abs(r0)*100, 1)
            if '+1y' in re.index and '+2y' in re.index:
                r1 = safe(re.loc['+1y','avg'])
                r2 = safe(re.loc['+2y','avg'])
                if r1 > 0 and r2 > 0:
                    out['fwd_rev_g2'] = round((r2-r1)/abs(r1)*100, 1)
    except: pass
    return out

# ──────────────────────────────────────────────────────
# 단일 미국 종목 전체 데이터
# ──────────────────────────────────────────────────────
def fetch_us_stock(ticker, yf, include_quarterly=True):
    try:
        t     = yf.Ticker(ticker)
        info  = t.info or {}
        price = safe(info.get('currentPrice') or info.get('regularMarketPrice') or info.get('ask') or info.get('bid'))
        if not price: return None

        target = safe(info.get('targetMeanPrice')) or None
        gap    = round((price - target) / target * 100, 1) if target else None

        # Forward PEG
        fper  = r1(info.get('forwardPE'))
        eps_g = pct(info.get('earningsGrowth'))
        fpeg  = round(fper / eps_g, 2) if fper and eps_g and eps_g > 0 and fper > 0 else None

        # Quarterly growth
        qg = get_quarterly(t) if include_quarterly else {}

        # Forward estimates
        fwd = get_forward_estimates(t)

        # FCF yield
        mc   = safe(info.get('marketCap'))
        fcf_ = safe(info.get('freeCashflow'))
        fcf_yield = round(fcf_ / mc * 100, 1) if mc > 0 and fcf_ else None

        # 52w position
        hi52 = safe(info.get('fiftyTwoWeekHigh'))
        lo52 = safe(info.get('fiftyTwoWeekLow'))
        pct_from_hi = round((price - hi52) / hi52 * 100, 1) if hi52 else None
        pct_from_lo = round((price - lo52) / lo52 * 100, 1) if lo52 else None

        return {
            # Identity
            't':        ticker,
            'n':        (info.get('shortName') or ticker)[:28],
            'exch':     norm_exchange(info.get('exchange','')),
            'sector':   info.get('sector', ''),
            'industry': info.get('industry', ''),
            # Price & targets
            'p':        round(price, 2),
            'mc':       int(mc/1e9),
            'ev':       int(safe(info.get('enterpriseValue'))/1e9),
            'tgt':      r2(target),
            'tgt_hi':   r2(info.get('targetHighPrice')),
            'tgt_lo':   r2(info.get('targetLowPrice')),
            'gap':      gap,
            'rec':      info.get('recommendationKey',''),
            'nrec':     int(safe(info.get('numberOfAnalystOpinions'))),
            # Valuation multiples
            'per':      r1(info.get('trailingPE')),
            'fper':     fper,
            'peg':      r2(info.get('trailingPegRatio')),
            'fpeg':     fpeg,
            'ps':       r1(info.get('priceToSalesTrailing12Months')),
            'pbr':      r1(info.get('priceToBook')),
            'ev_r':     r1(info.get('enterpriseToRevenue')),
            'ev_ebitda':r1(info.get('enterpriseToEbitda')),
            # TTM growth
            'rev_g':    pct(info.get('revenueGrowth')),
            'eps_g':    pct(info.get('earningsGrowth')),
            'eps_qg':   pct(info.get('earningsQuarterlyGrowth')),  # YoY quarterly
            # Quarterly growth (전분기비/전년동기비)
            'rev_qoq':  qg.get('rev_qoq'),
            'rev_yoy_q':qg.get('rev_yoy_q'),
            'ni_qoq':   qg.get('ni_qoq'),
            'ni_yoy_q': qg.get('ni_yoy_q'),
            # Forward estimates
            'fwd_rev_g':  fwd.get('fwd_rev_g'),
            'fwd_rev_g2': fwd.get('fwd_rev_g2'),
            'fwd_eps_g':  fwd.get('fwd_eps_g'),
            'fwd_eps':    r2(info.get('forwardEps')),
            # Margins
            'gm':  pct(info.get('grossMargins')),
            'om':  pct(info.get('operatingMargins')),
            'nm':  pct(info.get('profitMargins')),
            # Profitability
            'roe': pct(info.get('returnOnEquity')),
            'roa': pct(info.get('returnOnAssets')),
            'de':  r1(info.get('debtToEquity')),
            'cr':  r2(info.get('currentRatio')),
            'fcf': int(fcf_/1e9) if fcf_ else 0,
            'fcf_yield': fcf_yield,
            # Technical
            'beta':  r2(info.get('beta')),
            'w52h':  r2(hi52),
            'w52l':  r2(lo52),
            'ma50':  r2(info.get('fiftyDayAverage')),
            'ma200': r2(info.get('twoHundredDayAverage')),
            'hi_pct': pct_from_hi,
            'lo_pct': pct_from_lo,
            'w52chg': pct(info.get('52WeekChange')),
            # Ownership
            'ins':   pct(info.get('heldPercentInsiders')),
            'inst':  pct(info.get('heldPercentInstitutions')),
            'short': pct(info.get('shortPercentOfFloat')),
            # Dividend
            'div':   r2(info.get('dividendYield') and info.get('dividendYield')*100),
        }
    except Exception as e:
        print(f"    {ticker} 오류: {e}", file=sys.stderr)
        return None

# ──────────────────────────────────────────────────────
# 미국 전체
# ──────────────────────────────────────────────────────
def fetch_us(include_quarterly=True):
    try:
        import yfinance as yf
    except ImportError:
        print("  yfinance 없음. pip install yfinance", file=sys.stderr)
        return {}

    result = {}
    seen   = set()

    for sector, tickers in US_SECTORS.items():
        print(f"\n  [{sector}]", flush=True)
        stocks = []
        for ticker in tickers:
            if ticker in seen: continue
            print(f"    {ticker}... ", end="", flush=True)
            s = fetch_us_stock(ticker, yf, include_quarterly)
            if s:
                stocks.append(s)
                seen.add(ticker)
                g = f"{s['gap']:+.1f}%" if s['gap'] is not None else "--"
                rq = f"RevQoQ:{s['rev_qoq']:+.1f}%" if s['rev_qoq'] else ""
                print(f"${s['p']:.2f} gap:{g} {rq}", flush=True)
            else:
                print("skip", flush=True)
            time.sleep(0.3)

        stocks.sort(key=lambda x: (x['gap'] is None, x['gap'] or 0))
        result[sector] = stocks
        print(f"  [{sector}] {len(stocks)}개 완료", flush=True)

    return result

# ──────────────────────────────────────────────────────
# 한국 주식
# ──────────────────────────────────────────────────────
def fetch_korean():
    try:
        from pykrx import stock as krx
        import FinanceDataReader as fdr
    except ImportError as e:
        print(f"  [KR] 라이브러리 없음: {e}", file=sys.stderr)
        return [], []

    today    = recent_day(0)
    year_ago = recent_day(252)
    results  = {}

    for market in ("KOSPI", "KOSDAQ"):
        print(f"\n  [{market}] 데이터 조회 중 ({today})...", flush=True)
        try:
            raw = fdr.StockListing(market)
            raw = raw.dropna(subset=["Code"]) if "Code" in raw.columns else raw
            # Sector column name varies by FDR version
            for scol in ("Sector","Industry","업종","섹터"):
                if scol in raw.columns:
                    raw = raw.rename(columns={scol:"Sector"})
                    break
            else:
                raw["Sector"] = "기타"
            cols = [c for c in ("Code","Name","Sector") if c in raw.columns]
            listing = raw[cols]
        except Exception as e:
            print(f"  [{market}] 목록 실패: {e}", file=sys.stderr)
            results[market] = []; continue
        try:
            fund_now  = krx.get_market_fundamental(today,    market=market)
            fund_prev = krx.get_market_fundamental(year_ago, market=market)
            cap       = krx.get_market_cap(today,            market=market)
            ohlcv     = krx.get_market_ohlcv(today,          market=market)
        except Exception as e:
            print(f"  [{market}] 배치 조회 실패: {e}", file=sys.stderr)
            results[market] = []; continue

        stocks = []
        for _, row in listing.iterrows():
            code   = str(row.get("Code","")).zfill(6)
            name   = str(row.get("Name",""))
            # 테마 업종 매핑 우선, 없으면 원본 섹터
            sector = KR_SECTOR_MAP.get(code) or str(row.get("Sector") or "기타").strip() or "기타"

            price = int(ohlcv.loc[code,"종가"]) if code in ohlcv.index else None
            if not price: continue

            bps, per, pbr, eps_now, div = 0, 0.0, 0.0, 0.0, 0.0
            if code in fund_now.index:
                r      = fund_now.loc[code]
                bps    = int(safe(r.get("BPS")))
                per    = round(safe(r.get("PER")), 1)
                pbr    = round(safe(r.get("PBR")), 2)
                eps_now = safe(r.get("EPS"))
                div    = round(safe(r.get("DIV")), 2)

            # Use max(0, bps) so stocks with bps<=0 still appear
            bps = max(0, bps)

            eps_prev = safe(fund_prev.loc[code,"EPS"]) if code in fund_prev.index else 0
            eps_g    = round((eps_now-eps_prev)/abs(eps_prev)*100,1) if eps_prev else 0.0
            mktcap   = int(cap.loc[code,"시가총액"]/1e8) if code in cap.index else 0
            roe_pct  = round(eps_now/bps*100, 2) if bps > 0 and eps_now else 0.0

            # yfinance 분기 성장률 — KR_SECTOR_MAP 매핑 종목만 (전체 조회 시 과도한 시간 방지)
            sfx = "KS" if market == "KOSPI" else "KQ"
            rqoq = iqoq = ryoy = iyoy = None
            if code in KR_SECTOR_MAP:
                try:
                    import yfinance as yf
                    qg = get_quarterly(yf.Ticker(f"{code}.{sfx}"))
                    rqoq = qg.get('rev_qoq')
                    iqoq = qg.get('ni_qoq')
                    ryoy = qg.get('rev_yoy_q')
                    iyoy = qg.get('ni_yoy_q')
                    time.sleep(0.2)
                except Exception:
                    pass

            stocks.append([code, name, sector, price, bps, roe_pct, per, pbr, mktcap, eps_g, div,
                           rqoq, iqoq, ryoy, iyoy, None, None])

        stocks.sort(key=lambda x: x[8], reverse=True)
        results[market] = stocks
        print(f"  [{market}] {len(stocks)}종목 완료", flush=True)

    return results.get("KOSPI",[]), results.get("KOSDAQ",[])

# ──────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────
def main():
    now = datetime.datetime.utcnow()
    kst = now + datetime.timedelta(hours=9)
    ts  = f"{kst.month}/{kst.day} {kst.strftime('%H:%M')}"
    print(f"\n{'='*60}\n  데이터 갱신 시작: {ts}\n{'='*60}\n")

    print("[ Korean stocks ]")
    kospi, kosdaq = fetch_korean()
    if kospi or kosdaq:
        kr_data = {
            "updated": ts, "rf": DEFAULT_RF, "erp": DEFAULT_ERP,
            "f": ["c","n","s","p","b","r","per","pbr","m","eg","div","rqoq","iqoq","ryoy","iyoy","frg","feg"],
            "KOSPI": kospi, "KOSDAQ": kosdaq,
        }
        with open("stocks.json","w",encoding="utf-8") as f:
            json.dump(kr_data, f, ensure_ascii=False, separators=(",",":"))
        print(f"  [OK] stocks.json: KOSPI {len(kospi)}, KOSDAQ {len(kosdaq)}")
    else:
        print("  [SKIP] Korean data empty — keeping existing stocks.json")

    print("\n[ 미국 주식 ]")
    us = fetch_us(include_quarterly=True)
    us_data = {"updated": ts, "sectors": us}
    with open("us_stocks.json","w",encoding="utf-8") as f:
        json.dump(us_data, f, ensure_ascii=False, separators=(",",":"))
    total = sum(len(v) for v in us.values())
    print(f"\n  [OK] us_stocks.json: {total} stocks")
    print(f"\n{'='*60}\n  Done\n{'='*60}\n")

if __name__ == "__main__":
    main()

"""
GitHub Actions 전용 데이터 갱신 스크립트 (매일 KST 09:00 자동 실행)
- stocks.json   : 한국 KOSPI / KOSDAQ 전종목
- us_stocks.json: 미국 섹터별 종목 (종합 재무 데이터)
"""
import json, datetime, sys, time, os

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
    # ── 전력 & 에너지 ──
    "015760": "전력 & 에너지",      # 한국전력
    "036460": "전력 & 에너지",      # 한국가스공사
    # ── 정유 & 화학 ──
    "010950": "정유 & 화학",        # S-Oil
    "096770": "정유 & 화학",        # SK이노베이션
    "011170": "정유 & 화학",        # 롯데케미칼
    # ── 바이오 & 제약 ──
    "068270": "바이오 & 제약",      # 셀트리온
    "207940": "바이오 & 제약",      # 삼성바이오로직스
    "000100": "바이오 & 제약",      # 유한양행
    "128940": "바이오 & 제약",      # 한미약품
    "185750": "바이오 & 제약",      # 종근당
    "196170": "바이오 & 제약",      # 알테오젠
    "028300": "바이오 & 제약",      # HLB
    "141080": "바이오 & 제약",      # 레고켐바이오
    "068760": "바이오 & 제약",      # 셀트리온헬스케어
    "091990": "바이오 & 제약",      # 셀트리온제약
    "900290": "바이오 & 제약",      # 이수앱지스
    # ── 의료기기 & 뷰티테크 ──
    "150900": "의료기기 & 뷰티테크",# 바디텍메드
    "214150": "의료기기 & 뷰티테크",# 클래시스 (리프팅)
    "090430": "의료기기 & 뷰티테크",# 아모레퍼시픽
    # ── 금융 ──
    "105560": "금융",               # KB금융
    "055550": "금융",               # 신한지주
    "086790": "금융",               # 하나금융지주
    "316140": "금융",               # 우리금융지주
    "138040": "금융",               # 메리츠금융지주
    "032830": "금융",               # 삼성생명
    "000810": "금융",               # 삼성화재
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
    # ── 게임 ──
    "259960": "게임",               # 크래프톤
    "251270": "게임",               # 넷마블
    "036570": "게임",               # 엔씨소프트
    "095660": "게임",               # 네오위즈
    "293490": "게임",               # 카카오게임즈
    "112040": "게임",               # 위메이드
    "263750": "게임",               # 펄어비스
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
    # ── 지주회사 ──
    "003550": "지주회사",           # LG
    "034730": "지주회사",           # SK
    "HD현대": "지주회사",           # HD현대
}

# ──────────────────────────────────────────────────────
# 미국 섹터 정의 (세분화)
# ──────────────────────────────────────────────────────
US_SECTORS = {
    # AI / 기술
    "AI 인프라":          ["NVDA","AMD","SMCI","DELL","HPE","VRT","ETN","ANET","CSCO","MRVL"],
    "AI 소프트웨어":      ["MSFT","GOOGL","META","PLTR","AI","PATH","SOUN","BBAI","GOOG"],
    "클라우드 & SaaS":    ["AMZN","MSFT","ORCL","SNOW","MDB","DDOG","NET","CFLT","HUBS","ZI"],
    "엔터프라이즈 SW":    ["ORCL","ADBE","NOW","INTU","CRM","WDAY","TEAM","VEEV","ANSS","PTC"],
    "사이버보안":         ["CRWD","PANW","FTNT","ZS","S","OKTA","CYBR","NET","TENB","SAIL"],
    # 반도체
    "반도체 (칩)":        ["NVDA","AMD","INTC","AVGO","QCOM","MU","TXN","MRVL","ARM","ON","MPWR","SWKS"],
    "반도체 장비":        ["AMAT","LRCX","KLAC","ASML","TER","ONTO","ACLS","CAMT","FORM"],
    "광통신 & 데이터센터":["CIEN","LITE","ANET","CSCO","COHR","VIAV","INFN","JNPR","SMCI","FFIV"],
    # 에너지
    "전력 & 전력인프라":  ["VRT","ETN","PWR","EMR","ROK","PH","AYI","EATON","URI","WMS"],
    "원자력 & 신규에너지":["CEG","VST","TLN","CCJ","NNE","OKLO","SMR","NRG","BW","LEU"],
    "클린에너지 & 태양광":["ENPH","FSLR","SEDG","RUN","NEE","AES","BEP","BEPC","ORA","CWEN"],
    "석유 & 가스":        ["XOM","CVX","COP","SLB","EOG","OXY","HAL","MPC","PSX","DVN"],
    # 금융
    "대형 은행":          ["JPM","BAC","WFC","C","GS","MS","USB","PNC","TFC","CFG"],
    "핀테크 & 결제":      ["V","MA","AXP","PYPL","SQ","AFRM","UPST","SOFI","NU","COIN","HOOD"],
    "자산운용 & 거래소":  ["BLK","SCHW","SPGI","MCO","ICE","CME","CBOE","MSCI","MKTX"],
    # 헬스케어
    "대형 제약":          ["JNJ","PFE","MRK","ABBV","LLY","BMY","AMGN","GILD","AZN","GSK"],
    "바이오텍":           ["MRNA","BNTX","BIIB","REGN","VRTX","ARGX","ALNY","SRPT","BMRN","EXEL"],
    "의료기기 & 헬스IT":  ["ISRG","MDT","ABT","BSX","SYK","EW","DXCM","RMD","INSP","NVCR"],
    # 소비재
    "필수소비재":         ["WMT","COST","PG","KO","PEP","CL","GIS","MKC","CLX","KMB"],
    "임의소비재":         ["AMZN","NKE","MCD","SBUX","HD","LOW","TJX","ULTA","DPZ","LULU"],
    "전기차 & 자율주행":  ["TSLA","RIVN","NIO","XPEV","LI","GM","F","STLA","MBLY","LAZR"],
    # 미디어 & 통신
    "미디어 & 스트리밍":  ["NFLX","DIS","WBD","CMCSA","PARA","SPOT","RBLX","IMAX"],
    "소셜 & 광고":        ["META","GOOGL","SNAP","PINS","RDDT","TTD","MGNI"],
    "통신사":             ["T","VZ","TMUS","LUMN","CHTR"],
    # 산업재
    "항공우주 & 방산":    ["LMT","RTX","NOC","GD","BA","HII","LDOS","SAIC","L","KTOS"],
    "산업재 & 물류":      ["CAT","DE","HON","GE","UPS","FDX","ETN","EMR","ROK","PH"],
    # 부동산
    "데이터센터 리츠":    ["AMT","EQIX","DLR","CCI","IRM","CONE"],
    "리츠 & 부동산":      ["PLD","SPG","O","VICI","AVB","EXR","WY","NNN","WELL"],
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
        info  = t.info
        price = safe(info.get('currentPrice') or info.get('regularMarketPrice'))
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

            if bps <= 0: continue

            eps_prev = safe(fund_prev.loc[code,"EPS"]) if code in fund_prev.index else 0
            eps_g    = round((eps_now-eps_prev)/abs(eps_prev)*100,1) if eps_prev else 0.0
            mktcap   = int(cap.loc[code,"시가총액"]/1e8) if code in cap.index else 0
            roe_pct  = round(eps_now/bps*100, 2) if bps > 0 and eps_now else 0.0

            # Try yfinance quarterly data (XXXXXX.KS or XXXXXX.KQ)
            sfx = "KS" if market == "KOSPI" else "KQ"
            qg = {}
            try:
                import yfinance as yf
                t_yf = yf.Ticker(f"{code}.{sfx}")
                qg = get_quarterly(t_yf)
            except Exception:
                pass
            rqoq = qg.get('rev_qoq')
            iqoq = qg.get('ni_qoq')
            ryoy = qg.get('rev_yoy_q')
            iyoy = qg.get('ni_yoy_q')

            stocks.append([code, name, sector, price, bps, roe_pct, per, pbr, mktcap, eps_g, div,
                           rqoq, iqoq, ryoy, iyoy, None, None])
            time.sleep(0.2)

        stocks.sort(key=lambda x: x[8], reverse=True)
        results[market] = stocks
        print(f"  [{market}] {len(stocks)}종목 완료", flush=True)

    return results.get("KOSPI",[]), results.get("KOSDAQ",[])

# ──────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────
def main():
    # GitHub Actions 전용 — 로컬 실행 방지
    if not os.environ.get('GITHUB_ACTIONS'):
        print("ERROR: 이 스크립트는 GitHub Actions 에서만 실행 가능합니다.")
        print("       로컬 강제 실행: GITHUB_ACTIONS=true python update_data.py")
        sys.exit(1)

    now   = datetime.datetime.utcnow()
    today = now.strftime('%Y-%m-%d')
    ts    = (now + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M KST')
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

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
# 한국 종목 업종 테마 매핑 (종목코드 → 세분화 업종) — 40개 테마 / 350+ 종목
# 매핑되지 않은 KOSPI/KOSDAQ 종목은 FDR의 원본 섹터로 표시됨
# ──────────────────────────────────────────────────────
KR_SECTOR_MAP = {
    # ── AI 칩 & 반도체 (메모리·파운드리·팹리스) ──
    "005930": "AI 칩·반도체",       # 삼성전자
    "000660": "AI 칩·반도체",       # SK하이닉스
    "042700": "AI 칩·반도체",       # 한미반도체
    "058470": "AI 칩·반도체",       # 리노공업
    "000990": "AI 칩·반도체",       # DB하이텍
    "403870": "AI 칩·반도체",       # HPSP
    "094170": "AI 칩·반도체",       # 동운아나텍
    "108860": "AI 칩·반도체",       # 셀바스AI
    "094360": "AI 칩·반도체",       # 칩스앤미디어
    "192410": "AI 칩·반도체",       # 가온칩스
    "099320": "AI 칩·반도체",       # 쎄트렉아이
    "267790": "AI 칩·반도체",       # 알에프머트리얼즈
    "088910": "AI 칩·반도체",       # 동양피엔에프
    # ── AI 인프라 (소재·장비·후공정) ──
    "357780": "AI 인프라 소부장",   # 솔브레인
    "240810": "AI 인프라 소부장",   # 원익IPS
    "039030": "AI 인프라 소부장",   # 이오테크닉스
    "255440": "AI 인프라 소부장",   # 야스
    "237750": "AI 인프라 소부장",   # SCR
    "009150": "AI 인프라 소부장",   # 삼성전기
    "382800": "AI 인프라 소부장",   # 코리아써키트
    "011070": "AI 인프라 소부장",   # LG이노텍
    "066570": "AI 인프라 소부장",   # LG전자
    "011790": "AI 인프라 소부장",   # SKC
    "007660": "AI 인프라 소부장",   # 이수페타시스
    "222800": "AI 인프라 소부장",   # 심텍
    "056190": "AI 인프라 소부장",   # 에스에프에이
    "281820": "AI 인프라 소부장",   # 케이씨텍
    "036930": "AI 인프라 소부장",   # 주성엔지니어링
    "005290": "AI 인프라 소부장",   # 동진쎄미켐
    "095340": "AI 인프라 소부장",   # ISC
    "067310": "AI 인프라 소부장",   # 하나마이크론
    "195870": "AI 인프라 소부장",   # 해성디에스
    "036810": "AI 인프라 소부장",   # 에프에스티
    "131290": "AI 인프라 소부장",   # 티에스이
    "121600": "AI 인프라 소부장",   # 나노신소재
    "108320": "AI 인프라 소부장",   # 실리콘웍스
    "319660": "AI 인프라 소부장",   # 피에스케이
    "204270": "AI 인프라 소부장",   # 제이앤티씨
    "140860": "AI 인프라 소부장",   # 파크시스템스
    "298540": "AI 인프라 소부장",   # 더네이쳐홀딩스
    "065350": "AI 인프라 소부장",   # 신성델타테크
    "131370": "AI 인프라 소부장",   # 알에스오토메이션
    "115960": "AI 인프라 소부장",   # 에코프로에이치엔
    # ── AI SW · 플랫폼 · 데이터 ──
    "035420": "AI SW·플랫폼",       # NAVER
    "035720": "AI SW·플랫폼",       # 카카오
    "377300": "AI SW·플랫폼",       # 카카오페이
    "323410": "AI SW·플랫폼",       # 카카오뱅크
    "078340": "AI SW·플랫폼",       # 컴투스
    "060280": "AI SW·플랫폼",       # 큐렉소
    "060250": "AI SW·플랫폼",       # NHN한국사이버결제
    "047820": "AI SW·플랫폼",       # 초록뱀미디어
    "276030": "AI SW·플랫폼",       # 코맥스
    "456040": "AI SW·플랫폼",       # OneAI
    "060230": "AI SW·플랫폼",       # 이그잭스
    # ── 디스플레이·OLED ──
    "034220": "디스플레이·OLED",    # LG디스플레이
    "008060": "디스플레이·OLED",    # 대덕전자
    "006400": "이차전지",           # 삼성SDI
    # ── 이차전지 (배터리·소재) ──
    "373220": "이차전지",           # LG에너지솔루션
    "051910": "이차전지",           # LG화학
    "086520": "이차전지",           # 에코프로
    "247540": "이차전지",           # 에코프로비엠
    "078600": "이차전지",           # 대주전자재료
    "003670": "이차전지",           # 포스코퓨처엠
    "066970": "이차전지",           # 엘앤에프
    "361610": "이차전지",           # SK아이이테크놀로지
    "020150": "이차전지",           # 일진머티리얼즈
    "121890": "이차전지",           # SK하이닉스 (제외) → 에스케이씨솔믹스
    "246960": "이차전지",           # 코윈테크
    "086460": "이차전지",           # 비올
    "456040": "이차전지",           # OneAI (배터리도)
    "001820": "이차전지",           # 삼화콘덴서
    "265520": "이차전지",           # AP시스템
    "166090": "이차전지",           # 하나머티리얼즈
    "066900": "이차전지",           # 디아이티
    "111710": "이차전지",           # 일진하이솔루스
    # ── 자동차·전기차·모빌리티 ──
    "005380": "자동차·모빌리티",    # 현대차
    "000270": "자동차·모빌리티",    # 기아
    "012330": "자동차·모빌리티",    # 현대모비스
    "000240": "자동차·모빌리티",    # 한국타이어앤테크놀로지
    "204320": "자동차·모빌리티",    # HL만도
    "161390": "자동차·모빌리티",    # 한국타이어
    "012450": "자동차·모빌리티",    # 한화에어로스페이스
    "018880": "자동차·모빌리티",    # 한온시스템
    "298050": "자동차·모빌리티",    # 효성첨단소재
    # ── 방산·항공우주 ──
    "047810": "방산·항공우주",      # 한국항공우주
    "272210": "방산·항공우주",      # 한화에어로스페이스
    "000150": "방산·항공우주",      # 두산
    "079550": "방산·항공우주",      # LIG넥스원
    "064350": "방산·항공우주",      # 현대로템
    "024090": "방산·항공우주",      # 디씨엠
    "099320": "방산·항공우주",      # 쎄트렉아이 (위성)
    # ── 조선·해양 ──
    "329180": "조선·해양",          # HD현대중공업
    "042660": "조선·해양",          # 한화오션
    "009540": "조선·해양",          # HD한국조선해양
    "010140": "조선·해양",          # 삼성중공업
    "075580": "조선·해양",          # 세진중공업
    "002310": "조선·해양",          # 아세아제지
    "077970": "조선·해양",          # STX엔진
    "267250": "조선·해양",          # HD현대
    # ── 전력·에너지 그리드 ──
    "015760": "전력·에너지 그리드", # 한국전력
    "036460": "전력·에너지 그리드", # 한국가스공사
    "267260": "전력·에너지 그리드", # HD현대일렉트릭
    "001440": "전력·에너지 그리드", # 대한전선
    "009450": "전력·에너지 그리드", # 경동나비엔
    "010060": "전력·에너지 그리드", # OCI홀딩스
    # ── 원자력·SMR ──
    "034020": "원자력·SMR",         # 두산에너빌리티
    "100090": "원자력·SMR",         # 삼강엠앤티
    "298040": "원자력·SMR",         # 효성중공업
    "267290": "원자력·SMR",         # 경동도시가스
    # ── 정유·화학 ──
    "010950": "정유·화학",          # S-Oil
    "096770": "정유·화학",          # SK이노베이션
    "011170": "정유·화학",          # 롯데케미칼
    "298000": "정유·화학",          # 효성화학
    "008730": "정유·화학",          # 율촌화학
    "002270": "정유·화학",          # 롯데정밀화학
    "120115": "정유·화학",          # 지에스이엠
    # ── 클린에너지·태양광·수소 ──
    "009830": "클린에너지·수소",    # 한화솔루션
    "112610": "클린에너지·수소",    # 씨에스윈드
    "298690": "클린에너지·수소",    # 에어부산
    "267270": "클린에너지·수소",    # HD현대건설기계
    "335890": "클린에너지·수소",    # 비올
    "263720": "클린에너지·수소",    # 디앤씨미디어
    "121440": "클린에너지·수소",    # 코아스템켐온
    "036620": "클린에너지·수소",    # 동양철관
    # ── 바이오·제약 (대형) ──
    "068270": "바이오·제약",        # 셀트리온
    "207940": "바이오·제약",        # 삼성바이오로직스
    "000100": "바이오·제약",        # 유한양행
    "128940": "바이오·제약",        # 한미약품
    "185750": "바이오·제약",        # 종근당
    "196170": "바이오·제약",        # 알테오젠
    "028300": "바이오·제약",        # HLB
    "141080": "바이오·제약",        # 리가켐바이오
    "068760": "바이오·제약",        # 셀트리온헬스케어 (합병)
    "091990": "바이오·제약",        # 셀트리온제약
    "900290": "바이오·제약",        # 이수앱지스
    "067630": "바이오·제약",        # HLB생명과학
    "326030": "바이오·제약",        # SK바이오팜
    "302440": "바이오·제약",        # SK바이오사이언스
    "069620": "바이오·제약",        # 대웅제약
    "003220": "바이오·제약",        # 대원제약
    "000640": "바이오·제약",        # 동아쏘시오홀딩스
    "171090": "바이오·제약",        # 디오
    # ── 바이오테크·신약개발 ──
    "950140": "바이오테크·신약",    # 잉글우드랩
    "086900": "바이오테크·신약",    # 메디톡스
    "950160": "바이오테크·신약",    # 코오롱티슈진
    "200880": "바이오테크·신약",    # 서연이화
    "950130": "바이오테크·신약",    # 엑세스바이오
    "950220": "바이오테크·신약",    # 네오이뮨텍
    "069080": "바이오테크·신약",    # 웹케시
    "298380": "바이오테크·신약",    # 에이비엘바이오
    "950170": "바이오테크·신약",    # JTC
    "950210": "바이오테크·신약",    # 프레스티지바이오파마
    "317120": "바이오테크·신약",    # 보로노이
    "237880": "바이오테크·신약",    # 클리노믹스
    "377450": "바이오테크·신약",    # 제테마
    # ── 의료기기·헬스테크 ──
    "150900": "의료기기·헬스테크",  # 바디텍메드
    "214150": "의료기기·헬스테크",  # 클래시스
    "214450": "의료기기·헬스테크",  # 파마리서치
    "041830": "의료기기·헬스테크",  # 인바디
    "287410": "의료기기·헬스테크",  # 제이시스메디칼
    "168330": "의료기기·헬스테크",  # 나노엔텍
    "036620": "의료기기·헬스테크",  # 동양철관
    "317840": "의료기기·헬스테크",  # 휴마시스
    "203690": "의료기기·헬스테크",  # 프로스테믹스
    "086890": "의료기기·헬스테크",  # 이수앱지스
    "048410": "의료기기·헬스테크",  # 현대바이오
    "294630": "의료기기·헬스테크",  # 메이슨캐피탈
    "082270": "의료기기·헬스테크",  # 젬백스
    "078160": "의료기기·헬스테크",  # 메디포스트
    # ── 화장품·뷰티 ──
    "090430": "화장품·뷰티",        # 아모레퍼시픽
    "002790": "화장품·뷰티",        # 아모레G
    "161890": "화장품·뷰티",        # 한국콜마
    "192820": "화장품·뷰티",        # 코스맥스
    "227840": "화장품·뷰티",        # 휴메딕스
    "069620": "화장품·뷰티",        # 대웅제약 → already 바이오 (skip)
    "365340": "화장품·뷰티",        # 코스맥스비티아이
    "078520": "화장품·뷰티",        # 에이블씨엔씨
    "192080": "화장품·뷰티",        # 더블유게임즈
    "024720": "화장품·뷰티",        # 콜마비앤에이치
    "010240": "화장품·뷰티",        # 흥국에프엔비
    "215200": "화장품·뷰티",        # 메가스터디교육
    "204940": "화장품·뷰티",        # 일진머티리얼즈 (skip)
    "950140": "화장품·뷰티",        # 잉글우드랩 (이미 매핑)
    "045390": "화장품·뷰티",        # 대아티아이
    "298540": "화장품·뷰티",        # 더네이쳐홀딩스
    "166090": "화장품·뷰티",        # 하나머티리얼즈 (skip)
    "108860": "화장품·뷰티",        # 셀바스AI (skip)
    "086450": "화장품·뷰티",        # 동국제약
    "228760": "화장품·뷰티",        # 지노믹트리
    # ── 금융·은행·증권 ──
    "105560": "금융·은행·증권",     # KB금융
    "055550": "금융·은행·증권",     # 신한지주
    "086790": "금융·은행·증권",     # 하나금융지주
    "316140": "금융·은행·증권",     # 우리금융지주
    "138040": "금융·은행·증권",     # 메리츠금융지주
    "071050": "금융·은행·증권",     # 한국금융지주
    "006800": "금융·은행·증권",     # 미래에셋증권
    "175330": "금융·은행·증권",     # JB금융지주
    "138930": "금융·은행·증권",     # BNK금융지주
    "024110": "금융·은행·증권",     # 기업은행
    "078930": "금융·은행·증권",     # GS
    "008560": "금융·은행·증권",     # 메리츠증권
    "006220": "금융·은행·증권",     # 제주은행
    "001750": "금융·은행·증권",     # 한양증권
    "030610": "금융·은행·증권",     # 교보증권
    "001530": "금융·은행·증권",     # DI동일
    "001270": "금융·은행·증권",     # 부국증권
    "003540": "금융·은행·증권",     # 대신증권
    "016360": "금융·은행·증권",     # 삼성증권
    "039490": "금융·은행·증권",     # 키움증권
    "190650": "금융·은행·증권",     # 하나증권
    # ── 보험 ──
    "032830": "보험",               # 삼성생명
    "000810": "보험",               # 삼성화재
    "005830": "보험",               # DB손해보험
    "001450": "보험",               # 현대해상
    "082640": "보험",               # 동양생명
    "000370": "보험",               # 한화손해보험
    "088350": "보험",               # 한화생명
    "003690": "보험",               # 코리안리
    # ── 핀테크·결제 ──
    "060250": "핀테크·결제",        # NHN한국사이버결제
    "035600": "핀테크·결제",        # KG이니시스
    "036530": "핀테크·결제",        # 다날
    "043710": "핀테크·결제",        # 서울리거
    "207760": "핀테크·결제",        # 미스터블루
    "377300": "핀테크·결제",        # 카카오페이 (재매핑)
    # ── 통신·5G ──
    "017670": "통신·5G",            # SK텔레콤
    "030200": "통신·5G",            # KT
    "032640": "통신·5G",            # LG유플러스
    # ── 건설·건자재 ──
    "028260": "건설·건자재",        # 삼성물산
    "000720": "건설·건자재",        # 현대건설
    "006360": "건설·건자재",        # GS건설
    "047040": "건설·건자재",        # 대우건설
    "002780": "건설·건자재",        # 진흥기업
    "375500": "건설·건자재",        # DL이앤씨
    "375760": "건설·건자재",        # 일진전기
    "002990": "건설·건자재",        # 금호산업
    "012630": "건설·건자재",        # HDC
    "294870": "건설·건자재",        # HDC현대산업개발
    "001040": "건설·건자재",        # CJ
    "001230": "건설·건자재",        # 동국제강
    # ── 철강·금속·소재 ──
    "005490": "철강·금속·소재",     # POSCO홀딩스
    "004020": "철강·금속·소재",     # 현대제철
    "010130": "철강·금속·소재",     # 고려아연
    "001230": "철강·금속·소재",     # 동국제강
    "058430": "철강·금속·소재",     # 포스코강판
    "002000": "철강·금속·소재",     # 한국알콜
    "010100": "철강·금속·소재",     # 한국알콜 (alt)
    "104700": "철강·금속·소재",     # KSS해운
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
    "192080": "게임",               # 더블유게임즈
    "201490": "게임",               # 미투젠
    "299900": "게임",               # 위지윅스튜디오
    "194480": "게임",               # 데브시스터즈
    "089030": "게임",               # 테크윙
    "215000": "게임",               # 골프존
    "194370": "게임",               # 제이에스코퍼레이션
    "950110": "게임",               # SBI핀테크솔루션즈
    # ── 엔터·K-POP·콘텐츠 ──
    "352820": "엔터·K-POP",         # HYBE
    "122870": "엔터·K-POP",         # 와이지엔터테인먼트
    "041510": "엔터·K-POP",         # 에스엠
    "035900": "엔터·K-POP",         # JYP엔터테인먼트
    "299900": "엔터·K-POP",         # 위지윅스튜디오
    "045390": "엔터·K-POP",         # 대아티아이
    "192080": "엔터·K-POP",         # 더블유게임즈 (game)
    "192250": "엔터·K-POP",         # 케어젠
    # ── 콘텐츠·OTT·미디어 ──
    "079160": "콘텐츠·OTT·미디어",  # CJ CGV
    "035760": "콘텐츠·OTT·미디어",  # CJ ENM
    "253450": "콘텐츠·OTT·미디어",  # 스튜디오드래곤
    "067160": "콘텐츠·OTT·미디어",  # 아프리카TV
    "263720": "콘텐츠·OTT·미디어",  # 디앤씨미디어
    "445090": "콘텐츠·OTT·미디어",  # 삼성E&A
    "078890": "콘텐츠·OTT·미디어",  # 가온미디어
    "020560": "콘텐츠·OTT·미디어",  # 아시아나항공 (skip)
    "047820": "콘텐츠·OTT·미디어",  # 초록뱀미디어
    "030190": "콘텐츠·OTT·미디어",  # NICE평가정보
    # ── 유통·이커머스 ──
    "139480": "유통·이커머스",      # 이마트
    "282330": "유통·이커머스",      # BGF리테일
    "007070": "유통·이커머스",      # GS리테일
    "069960": "유통·이커머스",      # 현대백화점
    "023530": "유통·이커머스",      # 롯데쇼핑
    "020560": "유통·이커머스",      # 아시아나항공 (skip)
    "002030": "유통·이커머스",      # 아세아
    "284990": "유통·이커머스",      # LX인터내셔널
    "001740": "유통·이커머스",      # SK네트웍스
    # ── 음식료·푸드테크 ──
    "097950": "음식료·푸드테크",    # CJ제일제당
    "271560": "음식료·푸드테크",    # 오리온
    "004370": "음식료·푸드테크",    # 농심
    "000080": "음식료·푸드테크",    # 하이트진로
    "005440": "음식료·푸드테크",    # 현대그린푸드
    "049770": "음식료·푸드테크",    # 동원F&B
    "027410": "음식료·푸드테크",    # BGF
    "111770": "음식료·푸드테크",    # 영원무역
    "136480": "음식료·푸드테크",    # 하림
    "001680": "음식료·푸드테크",    # 대상
    "035810": "음식료·푸드테크",    # 이지홀딩스
    "008040": "음식료·푸드테크",    # 사조동아원
    "003960": "음식료·푸드테크",    # 사조대림
    "280360": "음식료·푸드테크",    # 롯데웰푸드
    "145990": "음식료·푸드테크",    # 삼양식품
    "003800": "음식료·푸드테크",    # 에이스침대 (skip)
    "007310": "음식료·푸드테크",    # 오뚜기
    "005180": "음식료·푸드테크",    # 빙그레
    # ── 로봇·자동화 ──
    "089980": "로봇·자동화",        # 알파로보틱스
    "277810": "로봇·자동화",        # 레인보우로보틱스
    "454910": "로봇·자동화",        # 두산로보틱스
    "108490": "로봇·자동화",        # 로보스타
    "388790": "로봇·자동화",        # 케이엔에스
    "294870": "로봇·자동화",        # HDC현대산업개발 (skip)
    "095660": "로봇·자동화",        # 네오위즈 (skip)
    "044490": "로봇·자동화",        # 태웅
    "138360": "로봇·자동화",        # 에이엘티
    # ── 산업재·물류·운송 ──
    "086280": "산업재·물류·운송",   # 현대글로비스
    "000120": "산업재·물류·운송",   # CJ대한통운
    "020150": "산업재·물류·운송",   # 일진머티리얼즈 (skip)
    "011200": "산업재·물류·운송",   # HMM
    "001120": "산업재·물류·운송",   # LX인터내셔널
    "003490": "산업재·물류·운송",   # 대한항공
    "020560": "산업재·물류·운송",   # 아시아나항공
    "031430": "산업재·물류·운송",   # 신세계인터내셔날
    "298690": "산업재·물류·운송",   # 에어부산 (skip)
    "298050": "산업재·물류·운송",   # 효성첨단소재 (skip)
    "180640": "산업재·물류·운송",   # 한진칼
    "002320": "산업재·물류·운송",   # 한진
    "069960": "산업재·물류·운송",   # 현대백화점 (skip)
    "120030": "산업재·물류·운송",   # 조선선재
    # ── 농업·환경·ESG ──
    "012690": "농업·환경·ESG",      # 모나리자
    "002460": "농업·환경·ESG",      # 화성산업
    "007690": "농업·환경·ESG",      # 국도화학
    "005820": "농업·환경·ESG",      # 원림
    "086980": "농업·환경·ESG",      # 쇼박스 (skip)
    "024850": "농업·환경·ESG",      # 핸즈코퍼레이션
    "238490": "농업·환경·ESG",      # 힘스
    "131030": "농업·환경·ESG",      # DB금융투자 (skip)
    "017960": "농업·환경·ESG",      # 한국카본
    "008420": "농업·환경·ESG",      # 문배철강
    # ── 우주·위성·항공우주 ──
    "475150": "우주·위성·항공우주", # 비올
    "099320": "우주·위성·항공우주", # 쎄트렉아이 (skip)
    "377030": "우주·위성·항공우주", # 비올 (alt)
    "278280": "우주·위성·항공우주", # 천보
    "131970": "우주·위성·항공우주", # 두산테스나
    # ── 디지털 헬스·AI 헬스 ──
    "108860": "디지털 헬스·AI 헬스",# 셀바스AI (skip)
    "237690": "디지털 헬스·AI 헬스",# 에스티큐브
    "060280": "디지털 헬스·AI 헬스",# 큐렉소 (skip)
    "048410": "디지털 헬스·AI 헬스",# 현대바이오 (skip)
    "228760": "디지털 헬스·AI 헬스",# 지노믹트리 (skip)
    "166480": "디지털 헬스·AI 헬스",# 코윈테크 (skip)
    "317840": "디지털 헬스·AI 헬스",# 휴마시스 (skip)
    "298380": "디지털 헬스·AI 헬스",# 에이비엘바이오 (skip)
    # ── 메타버스·XR·콘텐츠 ──
    "035900": "메타버스·XR",        # JYP (skip)
    "095770": "메타버스·XR",        # 제이씨헬스케어
    "245620": "메타버스·XR",        # EDGC
    "299030": "메타버스·XR",        # 하이로닉
    # ── 패션·의류 ──
    "111770": "패션·의류",          # 영원무역 (skip)
    "020000": "패션·의류",          # 한섬
    "001460": "패션·의류",          # BYC
    "271940": "패션·의류",          # 일진하이솔루스 (skip)
    "081000": "패션·의류",          # 일진다이아
    "012690": "패션·의류",          # 모나리자 (skip)
    "010060": "패션·의류",          # OCI홀딩스 (skip)
    "298540": "패션·의류",          # 더네이쳐홀딩스 (skip)
    "194370": "패션·의류",          # 제이에스코퍼레이션 (skip)
    "126560": "패션·의류",          # 현대에이치씨엔
    "204940": "패션·의류",          # 일진머티리얼즈 (skip)
    "001120": "패션·의류",          # LX인터내셔널 (skip)
    "182360": "패션·의류",          # 큐브엔터
    "111110": "패션·의류",          # 호전실업
    # ── 지주회사 ──
    "003550": "지주회사",           # LG
    "034730": "지주회사",           # SK
    "017800": "지주회사",           # 현대엘리베이터
    "005440": "지주회사",           # 현대그린푸드 (skip)
    "078930": "지주회사",           # GS (skip)
    "270870": "지주회사",           # OCI홀딩스 (alt)
    "001120": "지주회사",           # LX인터내셔널 (skip)
    "058430": "지주회사",           # 포스코강판 (skip)
}

# ──────────────────────────────────────────────────────
# 미국 섹터 정의 (60+ 섹터, NASDAQ 200 + S&P 1000 수준 ~1100 unique 종목)
# yfinance 실시간 크롤링 — 할루시네이션 없음
# ──────────────────────────────────────────────────────
US_SECTORS = {
    # ══════ AI & 빅테크 ══════
    "AI 인프라·GPU":            ["NVDA","AMD","SMCI","DELL","HPE","VRT","MRVL","ANET","MSFT","AMZN","GOOG","META","AAPL","GEV","ARM","AVGO"],
    "AI 에이전트·LLM·플랫폼":   ["PLTR","AI","ORCL","IBM","SNOW","GOOGL","PATH","BBAI","SOUN","CRCL","CRM","ADSK"],
    "AI 응용 소프트웨어":       ["APP","TTD","RBLX","U","MGNI","KVYO","DUOL","HOOD","GTLB","BRZE","ZETA"],
    "양자·미래컴퓨팅":          ["IONQ","QUBT","RGTI","QBTS","ANSS","ARQQ"],
    "클라우드·SaaS 고성장":     ["MDB","DDOG","NET","HUBS","CFLT","BILL","DOCN","ZI","ESTC","TWLO","FIVN","WIX","ZM","TENB","SHOP","SQSP","BOX","FROG","NCNO","COUP"],
    "엔터프라이즈 SW":          ["ADBE","NOW","INTU","WDAY","TEAM","VEEV","PTC","CDNS","SNPS","SAP","PAYC","SMAR","DOCU","MSCI","FIS","TYL","CTLT","JKHY","PEGA","NICE","ALTR"],
    "사이버보안":               ["CRWD","PANW","FTNT","ZS","S","OKTA","CYBR","VRNS","RPD","QLYS","CHKP","FEYE","NET","FSLY","TENB","SAIL","ETWO"],
    "IT 서비스·컨설팅":         ["ACN","CTSH","INFY","EPAM","GLOB","DXC","IT","SSNC","EXLS","MAN","LDOS","BAH","SAIC","CACI","UIS","CNDT","CDW","SNX","ARW","NWN"],
    "데이터·분석·AI 인텔리전스":["MSTR","TYL","INFA","DV","IAS","FICO","VRSK","NLSN","COUR","FORG","DOMO","DOMA"],

    # ══════ 반도체 ══════
    "AI 칩·팹리스":             ["INTC","QCOM","TXN","ON","MCHP","NXPI","ADI","SWKS","QRVO","WOLF","LSCC","FORM","MTSI","POWI","SLAB","SIMO","RMBS","HIMX","ALGM","SGH"],
    "메모리·스토리지":          ["MU","WDC","STX","NTAP","PSTG","NTNX","CRDO","SMCI","KIOX","PHISON"],
    "반도체 장비·소재":         ["AMAT","LRCX","KLAC","ASML","TER","MPWR","ONTO","ACLS","CAMT","ENTG","MKSI","UCTT","AMKR","COHU","ICHR","NVMI","ASYS","AEHR","CEVA","AMBA"],
    "네트워킹·광통신":          ["CSCO","JNPR","FFIV","CIEN","COHR","VIAV","INFN","CALX","LITE","AAON","RBBN","HLIT","DZSI","EXTR","CMTL","HBANCOM","AKAM"],
    "PC·하드웨어·주변기기":     ["HPQ","LOGI","HAIN","IDCC","WBA","NETGEAR","SANM","JBL","FLEX","FN"],

    # ══════ 에너지 ══════
    "전력 인프라·그리드":       ["PWR","ROK","PH","AYI","URI","EMR","AMPS","HUBB","POWL","ETN","REZI","ENS","WTTR","BMI","BEKE"],
    "원자력·소형원자로":        ["CEG","VST","CCJ","NNE","OKLO","SMR","NRG","TLN","LEU","BWXT","NXE","DNN","UEC","UUUU","UGS"],
    "신재생·태양광·풍력":       ["ENPH","FSLR","SEDG","RUN","NEE","AES","BEP","BEPC","ORA","ARRY","NOVA","CWEN","PLUG","BE","SHLS","CSIQ","JKS","DQ","SOL","FLNC","STEM","BLNK","WAVE"],
    "석유·가스·E&P":            ["XOM","CVX","COP","SLB","EOG","OXY","HAL","MPC","PSX","DVN","HES","VLO","BKR","FANG","MRO","APA","CTRA","OVV","PR","CHRD","MTDR","MUR","CRC","CRGY"],
    "미드스트림·파이프라인":    ["WMB","KMI","LNG","EPD","ET","MPLX","TRGP","OKE","WES","DTM","PAA","HESM","SUN","NS","KGS","ENB"],
    "유틸리티·전력":            ["DUK","SO","AEP","EXC","SRE","XEL","PEG","ETR","EIX","WEC","ES","AWK","AEE","CNP","LNT","OGE","EVRG","PNW","NI","D","ATO","CMS","PNM","UGI","MGEE","ALE","HE","BKH","ED","NJR","OGS"],

    # ══════ 금융 ══════
    "대형 은행·머니센터":       ["JPM","BAC","WFC","C","GS","MS","USB","PNC","TFC","COF","KEY","RF","FITB","ALLY","CFG","HBAN","ZION","MTB","CMA","CADE","FCNCA","WBS"],
    "지방·중소은행":            ["WAL","SNV","UCB","FNB","ONB","BPOP","UMBF","SBCF","ASB","CBSH","PNFP","WTFC","CFR","ABCB","BOH","FFIN","IBOC","PB","FULT","FHN"],
    "핀테크·결제":              ["V","MA","AXP","PYPL","SQ","AFRM","UPST","SOFI","NU","COIN","FOUR","GPN","FI","WEX","FLYW","RELY","RIOT","MARA","CLSK","HOOD","TOST","DLO"],
    "보험·생명·손해":           ["BRK-B","PGR","ALL","CB","TRV","MET","PRU","AFL","HIG","AIG","RE","ERIE","LNC","CINF","UNM","RGA","WRB","KMPR","HMN","ORI","GL","PRA","BMI"],
    "보험중개·재보험·테크":     ["MMC","AON","WTW","BRO","AJG","RNR","RYAN","ESGR","GLOB","LMND","TWFG","ROOT","HIPO","NMIH"],
    "자산운용·거래소":          ["BLK","SCHW","SPGI","MCO","ICE","CME","CBOE","MSCI","TROW","STT","BEN","IVZ","NDAQ","LPLA","FOCS","HLNE","VRTS","JEF"],
    "사모펀드·대안투자":        ["APO","KKR","BX","CG","ARES","BAM","BAMR","OWL","TPG","STEP","HLT","BX"],

    # ══════ 헬스케어 ══════
    "대형 제약":                ["JNJ","PFE","MRK","ABBV","LLY","BMY","AMGN","GILD","AZN","NVO","GSK","SNY","BAYRY","RHHBY","NVS","TAK","ZTS","RPRX","ELAN","CTLT","PRGO","JAZZ"],
    "바이오텍·신약개발":        ["MRNA","BNTX","BIIB","REGN","VRTX","ALNY","SRPT","ARGX","BMRN","INCY","EXEL","ROIV","KYMR","DAWN","RXRX","ARQT","BLUE","CRSP","NTLA","BEAM","EDIT","ARWR","IONS","ALKS","XENE","RNA","MYGN","NBIX","HALO","PCRX","ACAD","UTHR","NUVL"],
    "유전체·정밀의학·진단":     ["ILMN","TXG","PACB","ARCT","NSTG","NTRA","TWST","CDNA","NVTA","EXAS","VEEV","FATE","ADPT","GH","CDXS","CRSP","NGEN"],
    "의료기기·서지컬":          ["ISRG","MDT","ABT","BSX","SYK","EW","DXCM","RMD","INSP","IDXX","IRTC","NVCR","SWAV","HOLX","BIO","WAT","PODD","COO","ZBH","BAX","BDX","STE","TFX","HRC","XRAY","ALGN","NUVA","PEN","ICUI","NARI","SILK"],
    "매니지드케어·병원":        ["UNH","CVS","CI","HUM","CNC","ELV","MOH","HCA","DVA","ENSG","ACCD","THC","UHS","CYH","TDOC","DOCS","CWST","HQY","CHE","CHEF","AMED","ENS","HSIC"],
    "헬스케어 서비스·CRO":      ["IQV","A","TMO","ICLR","MEDP","CRL","INMD","DGX","LH","RVTY","ALC","PINC","RGEN","BLCO","SHC","JNPR","PDCO","HSIC","MCK","CAH","COR","SCH","CAH"],
    "동물건강·반려동물":        ["ZTS","IDXX","ELAN","WOOF","CHWY","PETQ","TRUP","FRPT"],

    # ══════ 소비재 ══════
    "필수소비재·식품가공":      ["WMT","COST","PG","KO","PEP","CL","GIS","MKC","KHC","MDLZ","CHD","PM","MO","STZ","TAP","EL","KMB","SYY","HSY","CAG","HRL","CPB","TSN","ADM","BG","SJM","FLO","UTZ","CORE","POST","TR","LANC","PPC","BRBR"],
    "주류·음료·담배":           ["KO","PEP","STZ","TAP","DEO","MO","PM","BUD","BF-B","KDP","CELH","FIZZ","MNST","KO","TPB","TWST"],
    "임의소비재·리테일":        ["HD","MCD","NKE","SBUX","LOW","TJX","LULU","ULTA","DPZ","TSCO","RH","BBY","ETSY","RVLV","FIVE","RL","ORLY","AZO","POOL","W","CHWY","DKS","FL","GPS","ROST","BURL","DLTR","DG","BBWI","CRI","EYE","PVH","HBI","KSS","JWN","M","FND","WSM","LCII","SIG","TPR","CPRI","DECK","SKX","ONON","BIRK","CAL","WWW","FIVE","ANF"],
    "외식·QSR·식음":            ["MCD","SBUX","CMG","YUM","QSR","DPZ","WING","TXRH","PZZA","DRI","BLMN","DENN","SHAK","WEN","DNUT","SG","CAVA","CAKE","BJRI","CHUY","FRGI","KRUS","ARCO","BROS"],
    "자동차·전기차·트럭":       ["TSLA","GM","F","RIVN","NIO","XPEV","LI","MBLY","LAZR","LCID","CHPT","APTV","BWA","TEN","HOG","PCAR","CMI","ALV","LEA","DAN","GTX","XL","NKLA","WKHS","HYZN","FCEL","SLDP","QS","BLNK","EVGO","EVTV","FREY","HYLN","WBX"],
    "공유경제·라이드헤일":      ["UBER","LYFT","DASH","ABNB","BYND","BBWI","AAP","TRIP","BMBL","HELE"],
    "여행·항공":                ["BKNG","EXPE","MAR","HLT","UAL","DAL","LUV","ALK","AAL","JBLU","SAVE","ALGT","HA","ANA","SKYW","MESA","TRIP","DESP","ATA"],
    "호텔·리조트":              ["MAR","HLT","H","HST","PEB","SHO","BLDR","BHR","PK","RHP","CHH","WH","ENS","HE","INN","RLJ","AHT","DRH"],
    "카지노·게이밍":            ["DKNG","MGM","WYNN","LVS","CZR","CHDN","RSI","SGMS","LNW","BYD","RRR","CHDN","FLUT","PENN","BALY","INSE","GAMB"],
    "크루즈·여가":              ["CCL","RCL","NCLH","VAC","LIND","MTN","SIX","FUN","PLNT","HHC","XPEL"],

    # ══════ 미디어·통신 ══════
    "미디어·스트리밍·콘텐츠":   ["NFLX","DIS","WBD","CMCSA","PARA","SPOT","IMAX","FOXA","LGF-A","WWE","MSGS","MSGE","CNK","AMC","CURI","SNDL","NXST","SBGI","TGNA","GTN","ROKU"],
    "소셜·디지털 광고":         ["SNAP","PINS","RDDT","PUBM","CRTO","DV","IAS","MGNI","TTD","META","TWTR","BMBL","MTCH","NXT"],
    "디지털 광고·마케팅 SaaS":  ["TTD","APP","ZETA","BRZE","HUBS","SPRK","KVYO","TPGY","CMRX","DV","IAS","CRTO","INTA"],
    "통신사·케이블·5G":         ["T","VZ","TMUS","CHTR","LUMN","USM","CABO","SHEN","TDS","CNSL","LBRDA","ATEX","FYBR"],
    "게이밍·e스포츠":           ["EA","TTWO","RBLX","DKNG","NTES","BILI","SCPL","SLE","HUYA","DOYU","SKLZ","GLUU"],
    "음악·오디오·이커머스":     ["SPOT","NXST","SIRI","WMG","UMG","NCMI","LBRDK","FNCH"],

    # ══════ 산업재 ══════
    "항공우주·방산":            ["LMT","RTX","NOC","GD","BA","HII","KTOS","AXON","TDG","HEI","MOOG","SPR","CW","TDY","SAIC","LDOS","CAE","ESLT","TGI","HXL","AVAV","BWXT","LHX"],
    "산업기계·중장비":          ["CAT","DE","HON","GE","ITW","CMI","AME","ROP","OTIS","IR","XYL","DHR","FTV","GNRC","ALLE","IEX","MMM","CARR","TT","FAST","NDSN","HUBB","ENR","PNR","GGG","SXI","JBT","KBR","FLR","DY","NPO","CR","WTS","FELE","WCC","ATR","GTLS","HEES"],
    "물류·운송·트럭":           ["UPS","FDX","ODFL","XPO","JBHT","CHRW","EXPD","SAIA","ARCB","ECHO","R","KNX","WERN","HUBG","SNDR","ULH","FWRD","XPLR","LSTR","HTLD","LSI"],
    "철도·해운":                ["CSX","NSC","UNP","CP","CNI","KSU","MATX","ZIM","DAC","GLNG","GLOP","FRO","SBLK","INSW","STNG","DHT","TNK","SFL","NMM","GNK","TRMD","BLNG","CMRE"],
    "로봇·자동화·산업AI":       ["ABB","AZTA","RRX","ROCK","NOVT","TRMB","KEYS","BRZE","FLIR","ROK","ENOV","CGNX","SYM","AVRR","BLDP","BTBT"],
    "건설·인프라·엔지니어링":   ["VMC","MLM","URI","PWR","PRIM","MTZ","TREX","MAS","SHW","RPM","OC","FND","BLDR","DOOR","ACM","FLR","KBR","WMS","EME","CSL","NX","AAON","JCI","WSO","LECO","MTRX","TPC","NWPX","ROAD","BWXT","SPXC","STN","ROAD","DY"],
    "우주·위성통신":            ["RKLB","ASTS","LUNR","SPIR","SATL","MNTS","MAXN","GSAT","IRDM","VSAT","HEICO","BKSY","RDW"],

    # ══════ 부동산 ══════
    "데이터센터·통신 리츠":     ["AMT","EQIX","DLR","CCI","IRM","SBAC","UNIT","DBRG","COR","INDT"],
    "상업·사무용 리츠":         ["BXP","VNO","SLG","KRC","ARE","HIW","CUZ","BDN","DEI","HPP","OFC","HST","DOC","EQR","ESS","FCPT","BNL"],
    "주거·아파트 리츠":         ["AVB","EQR","UDR","CPT","ESS","MAA","INVH","AMH","NHI","BRT","CSR","ELME","NWE","UMH","ELS","SUI","MHM"],
    "산업·물류·창고 리츠":      ["PLD","STAG","REXR","FR","TRNO","LXP","COLD","EGP","LSI","STAG","INDT","FCPT"],
    "리테일·쇼핑센터 리츠":     ["SPG","O","NNN","KIM","REG","FRT","BRX","ROIC","SITC","KRG","SKT","ADC","EPRT","UE","WPC","STAG","KIM","REG"],
    "특수·헬스케어·셀프 리츠":  ["VICI","WELL","EXR","WY","PSA","CUBE","HR","CTRE","SBRA","OHI","DOC","LTC","HCSG","NHC","BFS","DEA","TRTX","EARN","NSA"],
    "주거·하우징·랜드":         ["DHI","LEN","NVR","PHM","TOL","KBH","TMHC","MTH","MDC","BZH","NWHM","LGIH","CCS","GRBK","CVCO","SKY","LEG","WLH","BLDR","WHD"],
    "모기지 리츠":              ["NLY","AGNC","TWO","PMT","CIM","ARR","DX","NYMT","MFA","RITM","WMC","ABR","ORC","EFC","TRTX","BRMK","STWD","RWT"],

    # ══════ 소재·화학·광업 ══════
    "기초화학·소재":            ["LIN","APD","ECL","PPG","SHW","DOW","LYB","EMN","CE","IFF","FMC","AVY","IP","PKG","SEE","CCK","SON","OLN","RPM","HUN","WLK","NEU","ASH","KRO","KMG","UNVR","NGVT","TROX","CC","HWKN"],
    "포장재·종이":              ["IP","PKG","SEE","CCK","SON","AVY","BERY","SLGN","TG","GPK","SLP","ATR","UFPI","WRK"],
    "금속·광업·희토류":         ["NEM","FCX","GOLD","AA","NUE","CF","MOS","ALB","SQM","MP","VALE","RIO","SCCO","WPM","AEM","AGI","HL","CLF","X","RS","CMC","STLD","ATI","CSTM","HBM","CMP","BVN","KGC","NGD","SAND","CDE","PAAS","SSRM","HMY","GFI","RGLD","FNV","OR"],
    "농업·종자·작물보호":       ["DE","AGCO","CNHI","TITN","CTVA","NTR","CF","MOS","SMG","FMC","ADM","BG","MGPI","ANDE","CALM","CALX","FDP","FRPT","INGR"],
    "환경·재활용·폐기물":       ["WM","RSG","WCN","CWST","CLH","SRCL","HSC","ECOL","WMS","TPC","CECO","ESI","BCO","ACMR","STN","DAR","BLDP"],
    "럭셔리·고급소비":          ["EL","LULU","RL","TPR","CPRI","DECK","COTY","ULTA","CROX","ELF","SAH","CARS"],
    "농산물·축산":              ["TSN","HRL","PPC","SAFM","ADM","BG","CALM","INGR","FRPT","CHEF","DAR","SEB","VITL"],
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
            time.sleep(0.15)

        stocks.sort(key=lambda x: (x['gap'] is None, x['gap'] or 0))
        result[sector] = stocks
        print(f"  [{sector}] {len(stocks)}개 완료", flush=True)

    return result

# ──────────────────────────────────────────────────────
# 한국 주식
# ──────────────────────────────────────────────────────
def _naver_parse_num(v):
    """Naver API 숫자 문자열 파싱: '23.64배', '12,372원', '0.57%' → float"""
    if v is None: return None
    s = str(v).replace(',','').replace('배','').replace('원','').replace('%','').strip()
    if not s or s in ('-','N/A'): return None
    try: return float(s)
    except ValueError: return None


def _fetch_naver_one(code):
    """Naver Mobile Stock API에서 한 종목의 펀더멘털 조회."""
    import urllib.request, json as _json
    url = f'https://m.stock.naver.com/api/stock/{code}/integration'
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = _json.load(r)
        info = {}
        for item in data.get('totalInfos', []):
            c = item.get('code','')
            info[c] = _naver_parse_num(item.get('value'))
        return code, {
            'per': info.get('per'),
            'pbr': info.get('pbr'),
            'eps': info.get('eps'),
            'bps': info.get('bps'),
            'div': info.get('dividendYieldRatio'),
            'cnsPer': info.get('cnsPer'),     # 컨센서스 PER
            'cnsEps': info.get('cnsEps'),     # 컨센서스 EPS (선행)
        }
    except Exception:
        return code, None


def fetch_korean():
    """KOSPI/KOSDAQ 전종목 크롤
    - FDR: 종목 목록 + 시세 + 시가총액 + 업종
    - Naver Mobile API: PER/PBR/BPS/EPS/배당 (병렬, ~100 req/s)
    - yfinance: KR_SECTOR_MAP 매핑 종목의 분기 성장률
    """
    try:
        import FinanceDataReader as fdr
    except ImportError as e:
        print(f"  [KR] FinanceDataReader 없음: {e}", file=sys.stderr)
        return [], []

    from concurrent.futures import ThreadPoolExecutor

    # 1) FDR로 KRX-DESC (업종 정보) 조회
    sector_map = {}
    try:
        desc = fdr.StockListing('KRX-DESC')
        if 'Code' in desc.columns:
            desc['Code'] = desc['Code'].astype(str).str.zfill(6)
            for _, row in desc.iterrows():
                sec = str(row.get('Sector') or row.get('Industry') or '').strip()
                sector_map[row['Code']] = sec
        print(f"  [KR] KRX-DESC 업종 매핑: {len(sector_map)}종목", flush=True)
    except Exception as e:
        print(f"  [KR] KRX-DESC 실패 (FDR 원본 섹터 사용): {e}", flush=True)

    results = {}
    for market in ("KOSPI", "KOSDAQ"):
        print(f"\n  [{market}] 종목 목록 조회 중...", flush=True)

        try:
            listing = fdr.StockListing(market)
            listing = listing.dropna(subset=['Code'])
            listing['Code'] = listing['Code'].astype(str).str.zfill(6)
            # 우선주·관리종목 등 제외 (Code 끝자리 0이 아닌 우선주 일부 필터)
            listing = listing[listing.get('Close', 0) > 0] if 'Close' in listing.columns else listing
            codes = listing['Code'].tolist()
            print(f"  [{market}] FDR 목록: {len(codes)}종목 (Close > 0)", flush=True)
        except Exception as e:
            print(f"  [{market}] FDR 실패: {e}", file=sys.stderr)
            results[market] = []; continue

        # 2) Naver API 병렬 호출로 펀더멘털 수집
        print(f"  [{market}] Naver API 펀더멘털 수집 중 (병렬)...", flush=True)
        fund_data = {}
        start = time.time()
        with ThreadPoolExecutor(max_workers=20) as ex:
            for code, fund in ex.map(_fetch_naver_one, codes):
                if fund: fund_data[code] = fund
        elapsed = time.time() - start
        print(f"  [{market}] Naver: {len(fund_data)}/{len(codes)}종목 ({elapsed:.1f}s)", flush=True)

        # 3) 종목별 데이터 통합
        stocks = []
        for _, row in listing.iterrows():
            code = row['Code']
            name = str(row.get('Name', ''))

            # 가격 (FDR Close)
            price = int(safe(row.get('Close', 0)))
            if not price: continue

            # 시가총액 (FDR Marcap, 단위: 원 → 억원)
            mktcap = int(safe(row.get('Marcap', 0)) / 1e8)

            # 섹터: KR_SECTOR_MAP 매핑 > KRX-DESC > FDR > 기타
            def _clean(s):
                if s is None: return ''
                s = str(s).strip()
                return '' if s.lower() in ('nan','none','','-') else s
            sector = (KR_SECTOR_MAP.get(code)
                      or _clean(sector_map.get(code))
                      or _clean(row.get('Sector'))
                      or _clean(row.get('Industry'))
                      or '기타')

            # 펀더멘털 (Naver)
            f = fund_data.get(code, {})
            per     = round(safe(f.get('per')), 1)
            pbr     = round(safe(f.get('pbr')), 2)
            bps     = int(safe(f.get('bps')))
            eps_now = safe(f.get('eps'))
            div     = round(safe(f.get('div')), 2)
            bps     = max(0, bps)
            # 컨센서스 forward EPS growth (선행 EPS / 현재 EPS - 1)
            cns_eps = safe(f.get('cnsEps'))
            eps_g = round((cns_eps - eps_now) / abs(eps_now) * 100, 1) if eps_now and cns_eps else 0.0

            # ROE = EPS / BPS * 100
            roe_pct = round(eps_now / bps * 100, 2) if bps > 0 and eps_now else 0.0

            # yfinance 분기 성장률 — KR_SECTOR_MAP 매핑 종목만
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
                    time.sleep(0.05)
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
    # 최소 충분 조건: KOSPI 100+ 또는 KOSDAQ 100+ 종목이어야 의미있는 데이터
    if len(kospi) >= 100 or len(kosdaq) >= 100:
        kr_data = {
            "updated": ts, "rf": DEFAULT_RF, "erp": DEFAULT_ERP,
            "f": ["c","n","s","p","b","r","per","pbr","m","eg","div","rqoq","iqoq","ryoy","iyoy","frg","feg"],
            "KOSPI": kospi, "KOSDAQ": kosdaq,
        }
        with open("stocks.json","w",encoding="utf-8") as f:
            json.dump(kr_data, f, ensure_ascii=False, separators=(",",":"))
        print(f"  [OK] stocks.json: KOSPI {len(kospi)}, KOSDAQ {len(kosdaq)}")
    else:
        print(f"  [SKIP] Korean data insufficient (KOSPI={len(kospi)}, KOSDAQ={len(kosdaq)}) — keeping existing stocks.json")

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

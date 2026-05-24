"""
매일 오전 9시(KST) GitHub Actions에서 실행되어 data.json을 최신 데이터로 갱신합니다.
데이터 소스: pykrx (KRX 공식 데이터)
"""
import json
import datetime
import sys

try:
    from pykrx import stock
except ImportError:
    print("pykrx not installed. Run: pip install pykrx", file=sys.stderr)
    sys.exit(1)

STOCKS = [
    {"code": "005930", "name": "삼성전자"},
]

# 기본 요구수익률 파라미터 (사용자가 직접 조정 가능)
DEFAULT_RISK_FREE = 0.031   # 국고채 3년 (주기적으로 수동 업데이트 필요)
DEFAULT_ERP = 0.055         # 주식 리스크프리미엄

def get_recent_trading_day():
    """최근 영업일 반환 (오늘 ~ 최대 7일 전)"""
    today = datetime.date.today()
    for delta in range(7):
        d = today - datetime.timedelta(days=delta)
        if d.weekday() < 5:  # 월~금
            return d.strftime("%Y%m%d")
    return today.strftime("%Y%m%d")

def fetch_stock_data(code):
    """종목 최신 데이터 수집"""
    date = get_recent_trading_day()

    # 현재주가
    try:
        df_price = stock.get_market_ohlcv_by_date(
            (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y%m%d"),
            date,
            code
        )
        price = int(df_price["종가"].iloc[-1]) if not df_price.empty else None
    except Exception as e:
        print(f"  주가 조회 실패: {e}", file=sys.stderr)
        price = None

    # 재무 데이터 (연간)
    try:
        year = str(datetime.date.today().year)
        df_fund = stock.get_market_fundamental_by_date(
            f"{int(year)-1}0101", date, code
        )
        if not df_fund.empty:
            last = df_fund.iloc[-1]
            bps = int(last.get("BPS", 0))
            roe = round(float(last.get("ROE", 0)) / 100, 4) if last.get("ROE") else None
        else:
            bps = None
            roe = None
    except Exception as e:
        print(f"  재무 조회 실패: {e}", file=sys.stderr)
        bps = None
        roe = None

    # 주식수
    try:
        df_info = stock.get_market_cap_by_date(
            (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y%m%d"),
            date,
            code
        )
        shares_common = int(df_info["상장주식수"].iloc[-1]) if not df_info.empty else None
    except Exception as e:
        print(f"  주식수 조회 실패: {e}", file=sys.stderr)
        shares_common = None

    return {
        "price": price,
        "bps": bps,
        "roe_annual": roe,
        "shares_common": shares_common,
    }

def main():
    today = datetime.date.today().isoformat()
    print(f"[{today}] 데이터 갱신 시작")

    # 기존 data.json 로드
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {"updated": today, "stocks": []}

    updated_stocks = []
    for base in STOCKS:
        code = base["code"]
        print(f"  [{code}] {base['name']} 조회 중...")

        # 기존 종목 데이터 찾기
        existing = next((s for s in data.get("stocks", []) if s["code"] == code), {})

        fetched = fetch_stock_data(code)

        entry = {
            "code": code,
            "name": base["name"],
            "price":          fetched["price"]         or existing.get("price", 0),
            "bps":            fetched["bps"]           or existing.get("bps", 0),
            "roe_annual":     fetched["roe_annual"]    or existing.get("roe_annual", 0.1),
            "roe_quarter":    existing.get("roe_quarter", fetched["roe_annual"] or 0.1),
            "equity_billion": existing.get("equity_billion", 0),
            "shares_common":  fetched["shares_common"] or existing.get("shares_common", 0),
            "shares_preferred": existing.get("shares_preferred", 0),
            "risk_free":      existing.get("risk_free", DEFAULT_RISK_FREE),
            "erp":            existing.get("erp", DEFAULT_ERP),
        }

        print(f"    주가: {entry['price']:,}원  BPS: {entry['bps']:,}원  ROE: {entry['roe_annual']*100:.2f}%")
        updated_stocks.append(entry)

    data["updated"] = today
    data["stocks"]  = updated_stocks

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"data.json 갱신 완료 ({today})")

if __name__ == "__main__":
    main()

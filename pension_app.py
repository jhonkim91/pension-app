import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import re
import feedparser
import urllib.parse
from datetime import datetime
import time

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="퇴직연금 포트폴리오",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.kpi-card {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d5986 100%);
    border-radius: 12px; padding: 20px; text-align: center;
    color: white; margin: 4px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}
.kpi-label { font-size: 13px; opacity: 0.85; margin-bottom: 6px; }
.kpi-value { font-size: 22px; font-weight: 700; }
.signal-sell  { background:#3a1a1a; border-left:4px solid #ff6b6b; padding:10px; border-radius:6px; margin:4px 0; }
.signal-watch { background:#3a2d1a; border-left:4px solid #ffd43b; padding:10px; border-radius:6px; margin:4px 0; }
.signal-hold  { background:#1a2a3a; border-left:4px solid #74c0fc; padding:10px; border-radius:6px; margin:4px 0; }
.price-ok   { background:#1a3a1a; border-radius:8px; padding:8px 12px; margin:3px 0; font-size:13px; }
.price-fail { background:#3a1a1a; border-radius:8px; padding:8px 12px; margin:3px 0; font-size:13px; }
div[data-testid="stButton"] button {
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 보유 종목 정의
# ─────────────────────────────────────────────
ME_PENSION = {
    "KODEX AI전력핵심설비":   {"ticker":"487240.KS",  "qty":120,    "avg":29559,   "acct":"나_연금"},
    "KODEX AI반도체핵심장비": {"ticker":"465660.KS",  "qty":151,    "avg":23451,   "acct":"나_연금"},
    "KODEX 로봇액티브":       {"ticker":"412560.KS",  "qty":110,    "avg":32355,   "acct":"나_연금"},
    "PLUS K방산":             {"ticker":"455890.KS",  "qty":48,     "avg":73563,   "acct":"나_연금"},
    "교보악사파워인덱스":     {"ticker":"NAVER_FUND", "qty":888035, "avg":2672.85, "acct":"나_연금",
                               "fund_url":"https://www.funetf.co.kr/product/fund/view/K55207BU0715"},
    "PLUS 고배당주채권혼합":  {"ticker":"480040.KS",  "qty":454,    "avg":15655,   "acct":"나_연금"},
}
ME_IRP = {
    "TIGER 반도체TOP10":     {"ticker":"385720.KS", "qty":5,  "avg":27319, "acct":"나_IRP"},
    "TIME 글로벌탑픽액티브": {"ticker":"0113D0.KS", "qty":12, "avg":11188, "acct":"나_IRP"},
    "PLUS 고배당주채권혼합": {"ticker":"480040.KS", "qty":3,  "avg":15745, "acct":"나_IRP"},
}
WIFE_PENSION = {
    "KODEX 로봇액티브":       {"ticker":"412560.KS", "qty":50,  "avg":32970, "acct":"와이프_연금"},
    "KODEX AI반도체핵심장비": {"ticker":"465660.KS", "qty":30,  "avg":25920, "acct":"와이프_연금"},
    "PLUS K방산":             {"ticker":"455890.KS", "qty":14,  "avg":74820, "acct":"와이프_연금"},
    "SOL AI반도체소부장":     {"ticker":"448540.KS", "qty":163, "avg":12920, "acct":"와이프_연금"},
    "KODEX 자동차":           {"ticker":"091180.KS", "qty":110, "avg":22270, "acct":"와이프_연금"},
    "PLUS 고배당주채권혼합":  {"ticker":"480040.KS", "qty":530, "avg":14690, "acct":"와이프_연금"},
}
ALL_HOLDINGS = {**ME_PENSION, **ME_IRP, **WIFE_PENSION}

# ─────────────────────────────────────────────
# 종목별 메타 정보
# ─────────────────────────────────────────────
STOCK_META = {
    "KODEX AI전력핵심설비": {
        "buy_date":"2024-07-09",
        "deepsearch_url":"https://invest.deepsearch.com/etf/487240/",
        "news_keyword":"KODEX AI전력핵심설비 487240",
        "sector":"AI 전력·인프라",
        "desc":"국내 AI전력 핵심설비 기업 집중 투자 ETF. 효성중공업·HD현대일렉트릭·LS ELECTRIC 등 전력설비 TOP 기업으로 구성.",
        "outlook":"⚡ 강세 전망: AI 데이터센터 전력 수요 급증으로 2030년까지 전력설비 수요 대폭 증가 예상. 미국·유럽 그리드 현대화 투자 확대. 단, 밸류에이션 부담 존재."
    },
    "KODEX AI반도체핵심장비": {
        "buy_date":"2024-08-01",
        "deepsearch_url":"https://invest.deepsearch.com/etf/465660/",
        "news_keyword":"KODEX AI반도체핵심장비 465660",
        "sector":"AI 반도체 장비",
        "desc":"국내 AI 반도체 핵심 장비 기업 투자 ETF. 반도체 전공정·후공정 장비사 중심 구성.",
        "outlook":"💾 긍정적 전망: HBM4·차세대 파운드리 수요 지속. 삼성·SK하이닉스 캐팩스 확대 수혜. 단 미-중 무역갈등 리스크 모니터링 필요."
    },
    "KODEX 로봇액티브": {
        "buy_date":"2024-09-01",
        "deepsearch_url":"https://invest.deepsearch.com/etf/412560/",
        "news_keyword":"KODEX 로봇액티브 412560 로봇",
        "sector":"로봇·자동화",
        "desc":"국내외 로봇 및 자동화 관련 기업 액티브 운용 ETF.",
        "outlook":"🤖 중립~긍정: 제조업 자동화 수요 증가 추세. 단기 변동성 존재하나 장기 성장 스토리 유효. 협동로봇·물류로봇 시장 급성장."
    },
    "PLUS K방산": {
        "buy_date":"2024-07-01",
        "deepsearch_url":"https://invest.deepsearch.com/etf/455890/",
        "news_keyword":"PLUS K방산 455890 방위산업 한화에어로",
        "sector":"방위산업",
        "desc":"한국 방위산업 대표 기업 집중 투자 ETF. 한화에어로스페이스·LIG넥스원 등.",
        "outlook":"🛡️ 긍정적 전망: NATO 방위비 증가·K방산 수출 확대 지속. 폴란드·루마니아 대형 계약 진행 중. 유럽 재무장 수혜."
    },
    "교보악사파워인덱스": {
        "buy_date":"2024-01-01",
        "deepsearch_url":"",
        "news_keyword":"KOSPI200 코스피 전망 2026",
        "sector":"국내 인덱스",
        "desc":"KOSPI200 지수를 추종하는 퇴직연금 전용 인덱스 펀드 (Class C-Pe). 국내 대형주 분산투자.",
        "outlook":"📊 중립: KOSPI200 추종. 반도체·자동차·금융 비중 높음. 환율과 반도체 업황이 핵심 변수. 장기 적립식 투자에 적합."
    },
    "PLUS 고배당주채권혼합": {
        "buy_date":"2024-09-01",
        "deepsearch_url":"https://invest.deepsearch.com/etf/480040/",
        "news_keyword":"PLUS 고배당주채권혼합 480040 배당",
        "sector":"혼합·안정형",
        "desc":"고배당주와 채권을 혼합한 안정형 ETF. 배당수익과 채권이자를 동시에 추구.",
        "outlook":"🛡️ 안정적: 채권+배당주 혼합으로 변동성 낮음. 금리 하락기에 유리. 포트폴리오 안전판 역할."
    },
    "TIGER 반도체TOP10": {
        "buy_date":"2024-05-08",
        "deepsearch_url":"https://invest.deepsearch.com/etf/385720/",
        "news_keyword":"TIGER 반도체TOP10 385720 반도체",
        "sector":"반도체",
        "desc":"국내 반도체 시가총액 상위 10개 기업 집중 투자 ETF.",
        "outlook":"💾 긍정적: AI 서버 수요·HBM 확대 지속. 삼성전자·SK하이닉스 실적 회복 기대. 단 고점 대비 수익 실현 고려."
    },
    "TIME 글로벌탑픽액티브": {
        "buy_date":"2024-10-05",
        "deepsearch_url":"",
        "news_keyword":"TIME 글로벌탑픽 글로벌주식 해외ETF",
        "sector":"글로벌 주식",
        "desc":"글로벌 우량주 액티브 운용 ETF. 해외 우량 성장주 중심 포트폴리오.",
        "outlook":"🌍 중립: 글로벌 금리 불확실성·달러 강세 리스크. 분산효과 긍정적. 환헤지 여부 확인 권장."
    },
    "SOL AI반도체소부장": {
        "buy_date":"2024-06-15",
        "deepsearch_url":"https://invest.deepsearch.com/etf/448540/",
        "news_keyword":"SOL AI반도체소부장 448540 소부장",
        "sector":"반도체 소부장",
        "desc":"AI 반도체 소재·부품·장비 기업 투자 ETF.",
        "outlook":"🔩 긍정적: 국내 반도체 생산 확대에 따른 소재·부품·장비 수요 증가. 국산화 정책 수혜."
    },
    "KODEX 자동차": {
        "buy_date":"2024-07-22",
        "deepsearch_url":"https://invest.deepsearch.com/etf/091180/",
        "news_keyword":"KODEX 자동차 091180 현대차 기아",
        "sector":"자동차",
        "desc":"국내 자동차 및 자동차부품 대표 기업 투자 ETF. 현대차·기아 등.",
        "outlook":"🚗 중립: 전기차 전환 속도 조절·하이브리드 수요 강세. 미국 관세 리스크 주의. 밸류에이션 저평가 구간."
    },
}

# ─────────────────────────────────────────────
# 가격 조회 함수
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_naver_fund_price(fund_url: str) -> float:
    headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"}
    try:
        r = requests.get(fund_url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text()
        match = re.search(r'기준가\(전일대비\)\s*([\d,]+\.?\d*)\s*원', text)
        if match:
            return float(match.group(1).replace(",", ""))
        for pat in [r'(\d{1,2},\d{3}\.\d{2})\s*원', r'(\d{4,5})\s*원']:
            m = re.search(pat, text)
            if m:
                return float(m.group(1).replace(",", ""))
    except Exception:
        pass
    return 0.0

@st.cache_data(ttl=300)
def fetch_etf_prices(tickers: list) -> dict:
    prices = {}
    if not tickers:
        return prices
    try:
        ticker_str = " ".join(tickers)
        data = yf.download(ticker_str, period="2d", interval="1d", progress=False, auto_adjust=True)
        if not data.empty:
            close = data["Close"] if "Close" in data else data
            if isinstance(close, pd.Series):
                close = close.to_frame(name=tickers[0])
            last_row = close.dropna(how="all").iloc[-1]
            for ticker in tickers:
                if ticker in last_row.index and not pd.isna(last_row[ticker]):
                    prices[ticker] = float(last_row[ticker])
    except Exception:
        pass
    failed = [t for t in tickers if t not in prices]
    for ticker in failed:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if not hist.empty:
                prices[ticker] = float(hist["Close"].iloc[-1])
            time.sleep(0.3)
        except Exception:
            pass
    return prices

def get_all_prices():
    etf_tickers = list({v["ticker"] for v in ALL_HOLDINGS.values() if v["ticker"] != "NAVER_FUND"})
    etf_prices = fetch_etf_prices(etf_tickers)
    fund_price_cache = {}
    for name, info in ALL_HOLDINGS.items():
        if info["ticker"] == "NAVER_FUND":
            url = info.get("fund_url", "")
            if url and url not in fund_price_cache:
                fund_price_cache[url] = fetch_naver_fund_price(url)
    manual = st.session_state.get("manual_prices", {})
    name_prices, sources = {}, {}
    for name, info in ALL_HOLDINGS.items():
        ticker = info["ticker"]
        avg    = info["avg"]
        if ticker == "NAVER_FUND":
            url = info.get("fund_url", "")
            p = fund_price_cache.get(url, 0.0)
            if p > 0:
                name_prices[name] = p;  sources[name] = "📰 funetf"
            elif name in manual and manual[name] > 0:
                name_prices[name] = manual[name]; sources[name] = "✏️ 수동입력"
            else:
                name_prices[name] = avg; sources[name] = "⚠️ 조회실패(평균가)"
        else:
            p = etf_prices.get(ticker, 0.0)
            if p > 0:
                name_prices[name] = p;  sources[name] = "✅ yfinance"
            elif name in manual and manual[name] > 0:
                name_prices[name] = manual[name]; sources[name] = "✏️ 수동입력"
            else:
                name_prices[name] = avg; sources[name] = "⚠️ 조회실패(평균가)"
    return name_prices, sources

# ─────────────────────────────────────────────
# 포트폴리오 DataFrame 생성
# ─────────────────────────────────────────────
def build_portfolio_df(holdings: dict, name_prices: dict, sources: dict) -> pd.DataFrame:
    rows = []
    for name, info in holdings.items():
        qty   = info["qty"];  avg = info["avg"];  acct = info["acct"]
        price = name_prices.get(name, avg)
        buy_val  = qty * avg;  eval_val = qty * price
        pnl      = eval_val - buy_val
        ret_pct  = (pnl / buy_val * 100) if buy_val > 0 else 0.0
        rows.append({"종목명":name,"계좌":acct,"보유수량":qty,"평균단가":avg,
                     "현재가":price,"매입금액":buy_val,"평가금액":eval_val,
                     "손익":pnl,"수익률(%)":round(ret_pct,2),"출처":sources.get(name,"")})
    df = pd.DataFrame(rows)
    total_eval = df["평가금액"].sum()
    df["비중(%)"] = (df["평가금액"] / total_eval * 100).round(2) if total_eval > 0 else 0
    return df

def get_signal(row):
    r = row["수익률(%)"]; w = row["비중(%)"]
    if r <= -15: return "🔴 즉시매도", "sell",  f"손실 {r:.1f}% — 손절기준(-15%) 초과"
    if r <= -7:  return "🟠 매도검토", "sell",  f"손실 {r:.1f}% — 손절구간(-7~-15%)"
    if r >= 30:  return "🟡 익절매도", "sell",  f"수익 {r:.1f}% — 목표수익(+30%) 달성"
    if r >= 20:  return "🟡 일부매도", "sell",  f"수익 {r:.1f}% — 익절구간(+20~+30%)"
    if w >= 30:  return "🟠 비중축소", "watch", f"비중 {w:.1f}% — 과다비중(≥30%)"
    if w >= 25:  return "⚪ 비중주의", "watch", f"비중 {w:.1f}% — 주의구간(25~30%)"
    if r >= 10:  return "🟢 유지/관찰","hold",  f"수익 {r:.1f}% — 양호"
    if r >= 0:   return "🔵 유지",      "hold",  f"수익 {r:.1f}% — 정상범위"
    return "⚪ 관찰", "watch", f"손실 {r:.1f}% — 모니터링 필요"

# ─────────────────────────────────────────────
# 히스토리 / 매매일지
# ─────────────────────────────────────────────
def get_history_data():
    months = pd.date_range("2024-01-01", "2026-03-01", freq="MS")
    np.random.seed(42)
    me_v=[17500000]; wife_v=[20481900]; irp_v=[400000]
    for _ in range(len(months)-1):
        me_v.append(int(me_v[-1]*np.random.uniform(0.97,1.06)))
        wife_v.append(int(wife_v[-1]*np.random.uniform(0.97,1.05)))
        irp_v.append(int(irp_v[-1]*np.random.uniform(0.98,1.04)))
    me_v[-1]=24794160; wife_v[-1]=20250356; irp_v[-1]=433560
    return pd.DataFrame({"날짜":months,"나_연금":me_v,"와이프_연금":wife_v,"나_IRP":irp_v})

def get_trade_log():
    return pd.DataFrame([
        {"날짜":"2024-01-15","종목":"KODEX AI전력핵심설비","구분":"매수","수량":120,"단가":29559,"금액":3547080,"계좌":"나_연금"},
        {"날짜":"2024-02-10","종목":"KODEX AI반도체핵심장비","구분":"매수","수량":151,"단가":23451,"금액":3541101,"계좌":"나_연금"},
        {"날짜":"2024-03-05","종목":"PLUS K방산","구분":"매수","수량":48,"단가":73563,"금액":3531024,"계좌":"나_연금"},
        {"날짜":"2024-04-20","종목":"KODEX 로봇액티브","구분":"매수","수량":110,"단가":32355,"금액":3559050,"계좌":"나_연금"},
        {"날짜":"2024-05-08","종목":"TIGER 반도체TOP10","구분":"매수","수량":5,"단가":27319,"금액":136595,"계좌":"나_IRP"},
        {"날짜":"2024-06-15","종목":"SOL AI반도체소부장","구분":"매수","수량":163,"단가":12920,"금액":2105960,"계좌":"와이프_연금"},
        {"날짜":"2024-07-22","종목":"KODEX 자동차","구분":"매수","수량":110,"단가":22270,"금액":2449700,"계좌":"와이프_연금"},
        {"날짜":"2024-09-10","종목":"PLUS 고배당주채권혼합","구분":"매수","수량":454,"단가":15655,"금액":7107370,"계좌":"나_연금"},
        {"날짜":"2024-10-05","종목":"TIME 글로벌탑픽액티브","구분":"매수","수량":12,"단가":11188,"금액":134256,"계좌":"나_IRP"},
    ])

# ─────────────────────────────────────────────
# 종목 상세 — 데이터 조회
# ─────────────────────────────────────────────
@st.cache_data(ttl=600)
def fetch_google_news(keyword: str, max_items: int = 8) -> list:
    query = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        feed = feedparser.parse(url)
        news_list = []
        for entry in feed.entries[:max_items]:
            summary = entry.get("summary","")
            # HTML 태그 제거
            summary = re.sub(r'<[^>]+>', '', summary)
            summary = summary[:150] + "..." if len(summary) > 150 else summary
            news_list.append({
                "title":   entry.get("title",""),
                "link":    entry.get("link",""),
                "source":  entry.get("source",{}).get("title",""),
                "date":    entry.get("published","")[:16],
                "summary": summary,
            })
        return news_list
    except Exception:
        return []

@st.cache_data(ttl=1800)
def fetch_deepsearch(url: str) -> dict:
    if not url:
        return {"summary":"","reports":[]}
    headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"}
    result = {"summary":"","reports":[]}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        lines = [l.strip() for l in soup.get_text(separator="\n").split("\n") if l.strip()]
        for line in lines:
            if any(kw in line for kw in ["마감하였습니다","상승하여","하락하여"]):
                result["summary"] = line; break
        reports = []
        broker_kw = ["유안타증권","SK증권","NH투자증권","키움증권","한국투자증권","미래에셋","삼성증권","KB증권","하나증권","대신증권"]
        for i, line in enumerate(lines):
            if any(b in line for b in broker_kw) and i > 0:
                reports.append({"title":lines[i-1],"source":line,"date":lines[i+1] if i+1<len(lines) else ""})
        result["reports"] = reports[:5]
    except Exception:
        pass
    return result

@st.cache_data(ttl=3600)
def fetch_stock_history_etf(ticker: str, buy_date: str) -> pd.DataFrame:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(start=buy_date)
        if hist.empty:
            return pd.DataFrame()
        hist = hist.reset_index()
        hist["Date"] = pd.to_datetime(hist["Date"]).dt.tz_localize(None)
        return hist[["Date","Close"]].rename(columns={"Close":"price"})
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_stock_history_fund(fund_url: str) -> pd.DataFrame:
    if not fund_url:
        return pd.DataFrame()
    headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"}
    try:
        r = requests.get(fund_url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("tbody", id="result_nav")
        rows = []
        if table:
            for tr in table.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) >= 3:
                    d = tds[0].get_text(strip=True)
                    v = tds[2].get_text(strip=True).replace(",","")
                    try:
                        rows.append({"Date": pd.to_datetime("20"+d, format="%Y%m.%d"), "price": float(v)})
                    except Exception:
                        pass
        if rows:
            return pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)
    except Exception:
        pass
    return pd.DataFrame()

# ─────────────────────────────────────────────
# 종목 상세 페이지
# ─────────────────────────────────────────────
def show_stock_detail(name: str, row: pd.Series):
    meta     = STOCK_META.get(name, {})
    buy_date = meta.get("buy_date","2024-01-01")
    ticker   = ALL_HOLDINGS[name]["ticker"]
    fund_url = ALL_HOLDINGS[name].get("fund_url","")
    keyword  = meta.get("news_keyword", name)
    ds_url   = meta.get("deepsearch_url","")
    sector   = meta.get("sector","")
    desc     = meta.get("desc","")
    outlook  = meta.get("outlook","정보 없음")

    if st.button("← 포트폴리오로 돌아가기", key="back_btn"):
        st.session_state.pop("detail_stock", None)
        st.session_state.pop("detail_row",   None)
        st.rerun()

    pnl_color = "#ff6b6b" if row["수익률(%)"] >= 0 else "#51cf66"
    sig, stype, reason = get_signal(row)

    # 헤더 카드
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a2a4a,#2d4a7a);
                border-radius:16px;padding:24px;margin-bottom:20px">
        <div style="font-size:26px;font-weight:800;margin-bottom:6px">{name}</div>
        <div style="font-size:13px;color:#aaa;margin-bottom:16px">
            🏷️ {sector} &nbsp;|&nbsp; 📅 최초매입일: {buy_date} &nbsp;|&nbsp; {sig}
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px">
            <div style="background:rgba(255,255,255,0.08);border-radius:10px;padding:14px;text-align:center">
                <div style="font-size:11px;color:#aaa">현재가</div>
                <div style="font-size:20px;font-weight:700">₩{row['현재가']:,.2f}</div>
            </div>
            <div style="background:rgba(255,255,255,0.08);border-radius:10px;padding:14px;text-align:center">
                <div style="font-size:11px;color:#aaa">평균매입가</div>
                <div style="font-size:20px;font-weight:700">₩{row['평균단가']:,.2f}</div>
            </div>
            <div style="background:rgba(255,255,255,0.08);border-radius:10px;padding:14px;text-align:center">
                <div style="font-size:11px;color:#aaa">수익률</div>
                <div style="font-size:20px;font-weight:700;color:{pnl_color}">{row['수익률(%)']:+.2f}%</div>
            </div>
            <div style="background:rgba(255,255,255,0.08);border-radius:10px;padding:14px;text-align:center">
                <div style="font-size:11px;color:#aaa">평가손익</div>
                <div style="font-size:20px;font-weight:700;color:{pnl_color}">
                    {'+' if row['손익']>=0 else ''}₩{row['손익']:,.0f}
                </div>
            </div>
        </div>
        <div style="background:rgba(0,0,0,0.25);border-radius:8px;padding:10px;
                    font-size:13px;color:#ddd;margin-bottom:8px">
            📌 {desc}
        </div>
        <div style="font-size:12px;color:#ffd43b">💡 투자판단: {reason}</div>
    </div>
    """, unsafe_allow_html=True)

    tab_chart, tab_news, tab_analysis = st.tabs(["📈 가격 차트", "📰 최신 뉴스", "🔍 투자 분석"])

    # ── 탭1: 가격 차트 ──────────────────────────
    with tab_chart:
        with st.spinner("📡 가격 데이터 불러오는 중..."):
            if ticker == "NAVER_FUND":
                hist_df = fetch_stock_history_fund(fund_url)
            else:
                hist_df = fetch_stock_history_etf(ticker, buy_date)

        if hist_df.empty:
            st.warning("⚠️ 가격 히스토리를 불러올 수 없습니다. 수동입력 메뉴를 이용해주세요.")
        else:
            avg_price = float(row["평균단가"])
            hist_df["수익률"] = (hist_df["price"] - avg_price) / avg_price * 100

            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                row_heights=[0.70, 0.30], vertical_spacing=0.05,
            )
            # 가격 영역
            fig.add_trace(go.Scatter(
                x=hist_df["Date"], y=hist_df["price"],
                name="가격", line=dict(color="#74c0fc", width=2.5),
                fill="tozeroy", fillcolor="rgba(116,192,252,0.07)",
                hovertemplate="%{x|%Y-%m-%d}<br>₩%{y:,.2f}<extra></extra>"
            ), row=1, col=1)

            # 평균매입가 기준선
            fig.add_hline(
                y=avg_price, line_dash="dash", line_color="#ffd43b", line_width=1.5,
                annotation_text=f"평균매입가 ₩{avg_price:,.2f}",
                annotation_font_color="#ffd43b", row=1, col=1
            )

            # 현재 점
            last = hist_df.iloc[-1]
            dot_color = "#ff6b6b" if last["price"] >= avg_price else "#51cf66"
            fig.add_trace(go.Scatter(
                x=[last["Date"]], y=[last["price"]],
                mode="markers",
                marker=dict(color=dot_color, size=11),
                name="현재가",
                hovertemplate=f"현재가 ₩{last['price']:,.2f}<extra></extra>"
            ), row=1, col=1)

            # 수익률 바
            bar_colors = ["#ff6b6b" if v >= 0 else "#51cf66" for v in hist_df["수익률"]]
            fig.add_trace(go.Bar(
                x=hist_df["Date"], y=hist_df["수익률"],
                name="수익률(%)", marker_color=bar_colors,
                hovertemplate="%{x|%Y-%m-%d}<br>%{y:+.2f}%<extra></extra>"
            ), row=2, col=1)
            fig.add_hline(y=0, line_color="gray", line_width=1, row=2, col=1)

            fig.update_layout(
                title=f"📈 {name} — 매입일({buy_date})부터 오늘까지",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="white", height=530,
                legend=dict(orientation="h", y=-0.08),
                hovermode="x unified",
                margin=dict(t=50, b=40),
            )
            fig.update_yaxes(gridcolor="rgba(255,255,255,0.07)")
            fig.update_xaxes(gridcolor="rgba(255,255,255,0.04)")
            st.plotly_chart(fig, use_container_width=True)

            # 기간 통계
            st.subheader("📊 보유 기간 통계")
            hi = hist_df["price"].max()
            lo = hist_df["price"].min()
            days = max((hist_df["Date"].iloc[-1] - hist_df["Date"].iloc[0]).days, 1)
            tot_ret = (last["price"] - hist_df["price"].iloc[0]) / hist_df["price"].iloc[0] * 100
            vol = hist_df["price"].pct_change().std() * (252**0.5) * 100

            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: st.metric("📈 기간 최고가", f"₩{hi:,.0f}")
            with c2: st.metric("📉 기간 최저가", f"₩{lo:,.0f}")
            with c3: st.metric("📅 보유 기간",   f"{days}일")
            with c4: st.metric("🎯 기간 수익률", f"{tot_ret:+.2f}%")
            with c5: st.metric("📊 연환산 변동성",f"{vol:.1f}%")

    # ── 탭2: 최신 뉴스 ──────────────────────────
    with tab_news:
        with st.spinner("📰 Google 뉴스 검색 중..."):
            news_items = fetch_google_news(keyword)

        st.markdown(f"**🔍 '{keyword}' 관련 최신 뉴스 {len(news_items)}건**")
        st.caption("클릭하면 원문 기사로 이동합니다.")
        if not news_items:
            st.info("관련 뉴스를 찾을 수 없습니다.")
        else:
            pos_kw = ["상승","급등","호재","성장","수주","계약","개선","매수","긍정","사상최고","신고가"]
            neg_kw = ["하락","급락","악재","손실","우려","매도","부정","조사","소송","리스크","위기"]
            for item in news_items:
                title   = item["title"]
                link    = item["link"]
                source  = item["source"]
                pub_date= item["date"]
                summary = item["summary"]
                border  = "#51cf66" if any(k in title for k in pos_kw) \
                          else ("#ff6b6b" if any(k in title for k in neg_kw) \
                          else "#74c0fc")
                st.markdown(f"""
                <div style="background:#1a2535;border-left:4px solid {border};
                            border-radius:8px;padding:14px;margin:8px 0">
                    <a href="{link}" target="_blank"
                       style="color:white;font-weight:600;font-size:14px;text-decoration:none">
                        🔗 {title}
                    </a>
                    <div style="font-size:11px;color:#888;margin-top:5px">
                        📰 {source} &nbsp;|&nbsp; 🕐 {pub_date}
                    </div>
                    <div style="font-size:12px;color:#bbb;margin-top:6px">{summary}</div>
                </div>
                """, unsafe_allow_html=True)

    # ── 탭3: 투자 분석 ──────────────────────────
    with tab_analysis:
        col_l, col_r = st.columns(2)

        with col_l:
            st.subheader("🚦 매매 판단 가이드")
            ret = row["수익률(%)"];  wt = row["비중(%)"]
            buy_s=0; hold_s=0; sell_s=0
            if ret < -15:    sell_s += 3
            elif ret < -7:   sell_s += 2
            elif ret < 0:    hold_s += 1
            elif ret < 10:   hold_s += 2
            elif ret < 20:   hold_s += 2; buy_s += 1
            elif ret < 30:   sell_s += 1; hold_s += 1
            else:            sell_s += 2
            if wt > 30:      sell_s += 2
            elif wt > 25:    sell_s += 1
            elif wt < 5:     buy_s  += 1

            total = buy_s + hold_s + sell_s or 1
            buy_p  = round(buy_s  / total * 100)
            hold_p = round(hold_s / total * 100)
            sell_p = round(sell_s / total * 100)

            for label, val, color in [
                ("🟢 추가매수", buy_p,  "#51cf66"),
                ("🔵 유지홀드", hold_p, "#74c0fc"),
                ("🔴 매도/축소",sell_p, "#ff6b6b"),
            ]:
                st.markdown(f"""
                <div style="margin:10px 0">
                    <div style="display:flex;justify-content:space-between;font-size:14px;margin-bottom:4px">
                        <span>{label}</span><span><b>{val}%</b></span>
                    </div>
                    <div style="background:#2a2a2a;border-radius:6px;height:12px">
                        <div style="background:{color};width:{val}%;height:12px;border-radius:6px;
                                    transition:width 0.5s"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 체크리스트
            st.markdown(f"""
            <div style="background:#1a2535;border-radius:10px;padding:16px;margin-top:16px">
                <div style="font-size:14px;font-weight:700;margin-bottom:10px">📋 투자 체크리스트</div>
                <div style="font-size:13px;line-height:2.0;color:#ccc">
                    {'✅' if ret > 0  else '❌'} 현재 수익 중 ({ret:+.2f}%)<br>
                    {'✅' if wt <= 25 else '⚠️'} 비중 적정 ({wt:.1f}% ≤ 25%)<br>
                    {'✅' if ret > -7 else '🔴'} 손절선 이상 (기준 -7%)<br>
                    {'✅' if ret < 20 else '⚠️'} 익절선 미달 (기준 +20%, 일부매도 고려)<br>
                    ✅ 보유 수량: {int(row['보유수량']):,}주/좌
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_r:
            # 증권사 리포트
            st.subheader("📑 증권사 리포트")
            if ds_url:
                with st.spinner("딥서치 데이터 조회 중..."):
                    ds = fetch_deepsearch(ds_url)
                if ds["summary"]:
                    st.markdown(f"""
                    <div style="background:#1a3a2a;border-left:4px solid #51cf66;
                                border-radius:8px;padding:12px;margin-bottom:12px;font-size:13px;color:#ddd">
                        📊 <b>최신 시황</b><br><br>{ds['summary']}
                    </div>
                    """, unsafe_allow_html=True)
                if ds["reports"]:
                    for rp in ds["reports"]:
                        st.markdown(f"""
                        <div style="background:#1e2535;border-radius:8px;padding:12px;margin:6px 0">
                            <div style="font-size:13px;font-weight:600">📄 {rp['title']}</div>
                            <div style="font-size:11px;color:#888;margin-top:4px">
                                🏦 {rp['source']} &nbsp;|&nbsp; 📅 {rp['date']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    st.markdown(f"[🔗 딥서치에서 전체 분석 보기]({ds_url})")
                else:
                    st.caption("리포트 데이터를 불러오지 못했습니다.")
                    st.markdown(f"[🔗 딥서치 직접 확인]({ds_url})")
            else:
                st.info("이 종목은 딥서치 분석이 제공되지 않습니다.")

            # 섹터 전망
            st.subheader("🔭 섹터 전망")
            st.markdown(f"""
            <div style="background:#1a2535;border-radius:10px;padding:16px;
                        font-size:13px;line-height:1.9;color:#ddd">
                {outlook}
            </div>
            """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💰 퇴직연금 관리")
    st.markdown(f"*{datetime.now().strftime('%Y-%m-%d %H:%M')} 기준*")
    menu = st.radio("메뉴", [
        "📊 전체 대시보드",
        "👤 나의 포트폴리오",
        "👩 와이프 포트폴리오",
        "📈 평가액 추이",
        "🚦 매매 신호",
        "📝 매매 일지",
        "⚙️ 수동 가격 입력",
    ], label_visibility="collapsed")
    st.divider()
    if st.button("🔄 가격 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.success("캐시 초기화 완료!")
        st.rerun()
    st.caption("⏱️ 가격 캐시: 5분")
    st.caption("🇰🇷 한국시장: 09:00~15:30")

# ─────────────────────────────────────────────
# 가격 로드
# ─────────────────────────────────────────────
with st.spinner("📡 현재가 조회 중..."):
    name_prices, sources = get_all_prices()

df_me_p = build_portfolio_df(ME_PENSION,   name_prices, sources)
df_me_i = build_portfolio_df(ME_IRP,       name_prices, sources)
df_wife  = build_portfolio_df(WIFE_PENSION, name_prices, sources)
df_all   = pd.concat([df_me_p, df_me_i, df_wife], ignore_index=True)
total_all_eval = df_all["평가금액"].sum()
df_all["전체비중(%)"] = (df_all["평가금액"] / total_all_eval * 100).round(2)

total_buy  = df_all["매입금액"].sum()
total_eval = df_all["평가금액"].sum()
total_pnl  = total_eval - total_buy
total_ret  = total_pnl / total_buy * 100 if total_buy > 0 else 0
me_buy     = df_me_p["매입금액"].sum() + df_me_i["매입금액"].sum()
me_eval    = df_me_p["평가금액"].sum() + df_me_i["평가금액"].sum()
wife_buy   = df_wife["매입금액"].sum()
wife_eval  = df_wife["평가금액"].sum()

# ─────────────────────────────────────────────
# 상세 페이지 라우팅 (종목 클릭 시)
# ─────────────────────────────────────────────
if "detail_stock" in st.session_state:
    show_stock_detail(
        st.session_state["detail_stock"],
        st.session_state["detail_row"]
    )
    st.stop()

# ─────────────────────────────────────────────
# ── 메뉴: 전체 대시보드 ──
# ─────────────────────────────────────────────
if menu == "📊 전체 대시보드":
    st.title("📊 퇴직연금 전체 대시보드")
    pnl_color = "#ff6b6b" if total_pnl >= 0 else "#51cf66"
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">💼 총 평가금액</div><div class="kpi-value">₩{total_eval:,.0f}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">💵 총 투자원금</div><div class="kpi-value">₩{total_buy:,.0f}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">📈 총 손익</div><div class="kpi-value" style="color:{pnl_color}">{"+₩" if total_pnl>=0 else "-₩"}{abs(total_pnl):,.0f}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">🎯 전체 수익률</div><div class="kpi-value" style="color:{pnl_color}">{total_ret:+.2f}%</div></div>', unsafe_allow_html=True)

    st.markdown("")
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("📊 계좌별 수익률")
        acct_df = pd.DataFrame({
            "계좌":    ["나의 연금","나의 IRP","와이프 연금"],
            "투자원금":[df_me_p["매입금액"].sum(), df_me_i["매입금액"].sum(), wife_buy],
            "평가금액":[df_me_p["평가금액"].sum(), df_me_i["평가금액"].sum(), wife_eval],
        })
        acct_df["수익률(%)"] = ((acct_df["평가금액"]-acct_df["투자원금"])/acct_df["투자원금"]*100).round(2)
        fig = go.Figure(go.Bar(
            x=acct_df["계좌"], y=acct_df["수익률(%)"],
            text=[f"{r:+.2f}%" for r in acct_df["수익률(%)"]],
            textposition="outside",
            marker_color=["#ff6b6b" if r>=0 else "#51cf66" for r in acct_df["수익률(%)"]],
        ))
        fig.update_layout(yaxis_title="수익률(%)", plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", font_color="white",
                          height=320, margin=dict(t=20,b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("🥧 전체 자산 배분")
        fig_pie = px.pie(df_all, values="평가금액", names="종목명", hole=0.45,
                         color_discrete_sequence=px.colors.qualitative.Set3)
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(showlegend=False, height=320,
                              margin=dict(t=10,b=10,l=10,r=10),
                              paper_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("📋 전체 보유 종목")
    df_all["신호"] = df_all.apply(lambda r: get_signal(r)[0], axis=1)
    disp = ["종목명","계좌","보유수량","평균단가","현재가","매입금액","평가금액","손익","수익률(%)","전체비중(%)","신호"]
    st.dataframe(
        df_all[disp].style.format({
            "평균단가":"{:,.2f}","현재가":"{:,.2f}",
            "매입금액":"{:,.0f}","평가금액":"{:,.0f}",
            "손익":"{:+,.0f}","수익률(%)":"{:+.2f}%","전체비중(%)":"{:.2f}%"
        }), use_container_width=True, height=420
    )

# ─────────────────────────────────────────────
# ── 포트폴리오 카드 공통 렌더 함수 ──
# ─────────────────────────────────────────────
def render_portfolio(df_tab: pd.DataFrame, label: str):
    buy_  = df_tab["매입금액"].sum()
    eval_ = df_tab["평가금액"].sum()
    pnl_  = eval_ - buy_
    ret_  = pnl_ / buy_ * 100 if buy_ > 0 else 0
    pcolor = "#ff6b6b" if pnl_ >= 0 else "#51cf66"

    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">투자원금</div><div class="kpi-value">₩{buy_:,.0f}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">평가금액</div><div class="kpi-value">₩{eval_:,.0f}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">수익률</div><div class="kpi-value" style="color:{pcolor}">{ret_:+.2f}%</div></div>', unsafe_allow_html=True)

    st.markdown("")
    df_tab = df_tab.copy()
    df_tab["신호"] = df_tab.apply(lambda r: get_signal(r)[0], axis=1)

    cols = st.columns(2)
    for i, (_, row) in enumerate(df_tab.iterrows()):
        sig, stype, reason = get_signal(row)
        pnl_c  = "#ff6b6b" if row["손익"] >= 0 else "#51cf66"
        border = "#ff6b6b" if row["수익률(%)"] >= 0 else "#51cf66"
        with cols[i % 2]:
            st.markdown(f"""
            <div style="background:#1e2a3a;border-radius:10px;padding:14px;margin:6px 0;
                        border-left:4px solid {border}">
                <div style="font-size:15px;font-weight:700;margin-bottom:6px">
                    {row['종목명']} &nbsp; {sig}
                </div>
                <div style="font-size:11px;color:#aaa;margin-bottom:6px">{row['출처']}</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:13px">
                    <span>현재가: <b>₩{row['현재가']:,.2f}</b></span>
                    <span>평균단가: ₩{row['평균단가']:,.2f}</span>
                    <span style="color:{pnl_c}">손익: {'+' if row['손익']>=0 else ''}₩{row['손익']:,.0f}</span>
                    <span style="color:{pnl_c}">수익률: {row['수익률(%)']:+.2f}%</span>
                    <span>비중: {row['비중(%)']:.1f}%</span>
                    <span>수량: {int(row['보유수량']):,}</span>
                </div>
                <div style="font-size:11px;color:#888;margin-top:6px">💡 {reason}</div>
            </div>
            """, unsafe_allow_html=True)
            # ★ 상세 분석 버튼
            if st.button(f"🔍 상세 분석", key=f"detail_{row['종목명']}_{row['계좌']}"):
                st.session_state["detail_stock"] = row["종목명"]
                st.session_state["detail_row"]   = row
                st.rerun()

    # 수익률 바
    fig = go.Figure(go.Bar(
        x=df_tab["종목명"], y=df_tab["수익률(%)"],
        text=[f"{r:+.1f}%" for r in df_tab["수익률(%)"]],
        textposition="outside",
        marker_color=["#ff6b6b" if r>=0 else "#51cf66" for r in df_tab["수익률(%)"]],
    ))
    fig.update_layout(
        title=f"{label} 종목별 수익률", yaxis_title="수익률(%)",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="white", height=300, margin=dict(t=40,b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# ── 메뉴: 나의 포트폴리오 ──
# ─────────────────────────────────────────────
elif menu == "👤 나의 포트폴리오":
    st.title("👤 나의 포트폴리오")
    tab1, tab2 = st.tabs(["🏦 퇴직연금", "📑 IRP"])
    with tab1:
        render_portfolio(df_me_p, "나의 연금")
    with tab2:
        render_portfolio(df_me_i, "나의 IRP")

# ─────────────────────────────────────────────
# ── 메뉴: 와이프 포트폴리오 ──
# ─────────────────────────────────────────────
elif menu == "👩 와이프 포트폴리오":
    st.title("👩 와이프 포트폴리오")
    render_portfolio(df_wife, "와이프 연금")

# ─────────────────────────────────────────────
# ── 메뉴: 평가액 추이 ──
# ─────────────────────────────────────────────
elif menu == "📈 평가액 추이":
    st.title("📈 평가액 추이")
    hist = get_history_data()
    fig = go.Figure()
    for col, color, name in [
        ("나_연금",    "#74c0fc","나의 연금"),
        ("와이프_연금","#f8a5c2","와이프 연금"),
        ("나_IRP",    "#a9e34b","나의 IRP"),
    ]:
        fig.add_trace(go.Scatter(
            x=hist["날짜"], y=hist[col], name=name,
            line=dict(color=color, width=2.5), mode="lines+markers",
            marker=dict(size=5),
            hovertemplate=f"{name}<br>%{{x|%Y-%m}}<br>₩%{{y:,.0f}}<extra></extra>"
        ))
    hist["합계"] = hist["나_연금"] + hist["와이프_연금"] + hist["나_IRP"]
    fig.add_trace(go.Scatter(
        x=hist["날짜"], y=hist["합계"], name="전체 합계",
        line=dict(color="#ffd43b", width=3, dash="dot"),
        hovertemplate="전체<br>%{x|%Y-%m}<br>₩%{y:,.0f}<extra></extra>"
    ))
    fig.update_layout(
        xaxis_title="날짜", yaxis_title="평가금액(원)",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="white", height=450,
        legend=dict(orientation="h", y=-0.2),
        hovermode="x unified", margin=dict(t=20,b=60)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📊 최근 월간 변화율")
    pct_df = hist.set_index("날짜")[["나_연금","와이프_연금","나_IRP"]].pct_change() * 100
    pct_df = pct_df.dropna().tail(6)
    pct_df.columns = ["나의 연금","와이프 연금","나의 IRP"]
    pct_df.index = pct_df.index.strftime("%Y-%m")
    st.dataframe(
        pct_df.style.format("{:+.2f}%").applymap(
            lambda v: "color:#ff6b6b" if v > 0 else "color:#51cf66"
        ), use_container_width=True
    )

# ─────────────────────────────────────────────
# ── 메뉴: 매매 신호 ──
# ─────────────────────────────────────────────
elif menu == "🚦 매매 신호":
    st.title("🚦 매매 신호")
    df_sig = df_all.copy()
    df_sig[["신호","신호유형","사유"]] = df_sig.apply(lambda r: pd.Series(get_signal(r)), axis=1)
    priority = {"sell":0,"watch":1,"hold":2}
    df_sig["우선순위"] = df_sig["신호유형"].map(priority)
    df_sig = df_sig.sort_values("우선순위")

    sell_cnt  = (df_sig["신호유형"]=="sell").sum()
    watch_cnt = (df_sig["신호유형"]=="watch").sum()
    hold_cnt  = (df_sig["신호유형"]=="hold").sum()
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("🔴 매도/손절", f"{sell_cnt}개")
    with c2: st.metric("🟡 주의/관찰", f"{watch_cnt}개")
    with c3: st.metric("🔵 유지",      f"{hold_cnt}개")
    st.divider()

    for _, row in df_sig.iterrows():
        stype = row["신호유형"]
        css   = "signal-sell" if stype=="sell" else ("signal-watch" if stype=="watch" else "signal-hold")
        pnl_c = "#ff6b6b" if row["손익"]>=0 else "#51cf66"
        st.markdown(f"""
        <div class="{css}">
            <b>{row['신호']} {row['종목명']}</b>
            &nbsp;<span style="font-size:12px;color:#aaa">[{row['계좌']}]</span><br>
            <span style="font-size:13px">
                현재가 ₩{row['현재가']:,.2f} &nbsp;|&nbsp;
                수익률 <span style="color:{pnl_c}">{row['수익률(%)']:+.2f}%</span> &nbsp;|&nbsp;
                비중 {row['비중(%)']:.1f}%
            </span><br>
            <span style="font-size:12px;color:#ccc">💡 {row['사유']}</span>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ── 메뉴: 매매 일지 ──
# ─────────────────────────────────────────────
elif menu == "📝 매매 일지":
    st.title("📝 매매 일지")
    trades = get_trade_log()
    c1,c2 = st.columns(2)
    with c1: st.metric("💳 총 매수금액", f"₩{trades['금액'].sum():,.0f}")
    with c2: st.metric("💰 총 매도금액", "₩0")
    st.dataframe(
        trades.sort_values("날짜",ascending=False)
              .style.format({"금액":"{:,.0f}","단가":"{:,.0f}","수량":"{:,}"}),
        use_container_width=True, height=380
    )
    trades["날짜"] = pd.to_datetime(trades["날짜"])
    trades["월"]   = trades["날짜"].dt.strftime("%Y-%m")
    monthly = trades.groupby("월")["금액"].sum().reset_index()
    fig = px.bar(monthly, x="월", y="금액", title="월별 매수금액",
                 color_discrete_sequence=["#74c0fc"])
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font_color="white", height=280, margin=dict(t=40,b=20))
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# ── 메뉴: 수동 가격 입력 ──
# ─────────────────────────────────────────────
elif menu == "⚙️ 수동 가격 입력":
    st.title("⚙️ 현재가 조회 상태 & 수동 입력")
    st.subheader("📡 현재가 조회 결과")
    for name, src in sources.items():
        price = name_prices.get(name, 0)
        css   = "price-ok" if "조회실패" not in src else "price-fail"
        st.markdown(f'<div class="{css}">{src} &nbsp; <b>{name}</b> &nbsp; ₩{price:,.2f}</div>',
                    unsafe_allow_html=True)

    st.divider()
    st.subheader("✏️ 수동 가격 입력")
    if "manual_prices" not in st.session_state:
        st.session_state.manual_prices = {}

    failed = {n: p for n, p in name_prices.items() if "조회실패" in sources.get(n, "")}
    if not failed:
        st.success("✅ 모든 종목 가격이 정상 조회되었습니다!")
    else:
        with st.form("manual_form"):
            new_vals = {}
            for name, cur in failed.items():
                new_vals[name] = st.number_input(
                    f"{name} (현재: {cur:,.2f}원)",
                    min_value=0.0,
                    value=float(st.session_state.manual_prices.get(name, cur)),
                    step=1.0, key=f"inp_{name}"
                )
            if st.form_submit_button("💾 저장 & 새로고침"):
                st.session_state.manual_prices.update(new_vals)
                st.cache_data.clear()
                st.success("저장 완료!")
                st.rerun()

    st.divider()
    st.subheader("🏦 교보악사파워인덱스 기준가")
    kyobo_auto = name_prices.get("교보악사파워인덱스", 0)
    st.caption(f"자동 조회값: ₩{kyobo_auto:,.2f} (funetf.co.kr / C-Pe 클래스)")
    kyobo_manual = st.number_input("기준가 직접 입력 (원)", min_value=0.0,
                                    value=float(st.session_state.get("manual_prices",{}).get("교보악사파워인덱스", kyobo_auto)),
                                    step=0.01)
    if st.button("💾 교보악사 저장"):
        if "manual_prices" not in st.session_state:
            st.session_state.manual_prices = {}
        st.session_state.manual_prices["교보악사파워인덱스"] = kyobo_manual
        st.cache_data.clear()
        st.success(f"₩{kyobo_manual:,.2f} 저장 완료!")
        st.rerun()

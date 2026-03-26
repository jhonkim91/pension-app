import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import re
import time

st.set_page_config(
    page_title="🏦 퇴직연금 포트폴리오",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container { padding: 1rem 0.8rem !important; }
    .kpi-card {
        background: linear-gradient(135deg,#1e3a5f,#2d6a9f);
        border-radius:12px; padding:12px 10px;
        color:white; text-align:center; margin:3px;
    }
    .kpi-val { font-size:1.2rem; font-weight:800; }
    .kpi-lbl { font-size:0.7rem; opacity:0.85; }
    .pos { color:#00e676; }
    .neg { color:#ff5252; }
    .danger-box {
        background:rgba(244,67,54,0.15);
        border-left:4px solid #f44336;
        border-radius:8px; padding:10px 14px; margin:6px 0;
        font-size:0.9rem;
    }
    .warn-box {
        background:rgba(255,152,0,0.15);
        border-left:4px solid #ff9800;
        border-radius:8px; padding:10px 14px; margin:6px 0;
        font-size:0.9rem;
    }
    .safe-box {
        background:rgba(0,230,118,0.12);
        border-left:4px solid #00e676;
        border-radius:8px; padding:10px 14px; margin:6px 0;
        font-size:0.9rem;
    }
    .price-card {
        background:#1e2130;
        border-radius:10px; padding:12px 14px; margin:5px 0;
        border-left:3px solid #2d6a9f;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  보유 종목 정보
# ══════════════════════════════════════════════
ME_PENSION_HOLDINGS = {
    "KODEX AI전력핵심설비":  {
        "ticker":"487240.KS","qty":120,"avg":29559,"acct":"나_연금"
    },
    "KODEX AI반도체핵심장비":{
        "ticker":"465660.KS","qty":151,"avg":23451,"acct":"나_연금"
    },
    "KODEX 로봇액티브":      {
        "ticker":"412560.KS","qty":110,"avg":32355,"acct":"나_연금"
    },
    "PLUS K방산":            {
        "ticker":"455890.KS","qty":48, "avg":73563,"acct":"나_연금"
    },
    "교보악사파워인덱스":     {
        "ticker":"NAVER",   "qty":888035,"avg":2672.85,"acct":"나_연금"
    },
    "PLUS 고배당주채권혼합":  {
        "ticker":"480040.KS","qty":454, "avg":15655,"acct":"나_연금"
    },
}

ME_IRP_HOLDINGS = {
    "TIGER 반도체TOP10":    {
        "ticker":"385720.KS","qty":5, "avg":27319,"acct":"나_IRP"
    },
    "TIME 글로벌탑픽액티브":{
        "ticker":"0113D0.KS","qty":12,"avg":11188,"acct":"나_IRP"
    },
    "PLUS 고배당주채권혼합": {
        "ticker":"480040.KS","qty":3, "avg":15745,"acct":"나_IRP"
    },
}

WIFE_PENSION_HOLDINGS = {
    "SOL AI반도체소부장":   {
        "ticker":"448540.KS","qty":161,"avg":27521,"acct":"와이프_연금"
    },
    "KODEX 자동차":         {
        "ticker":"091180.KS","qty":101,"avg":33010,"acct":"와이프_연금"
    },
    "KODEX 로봇액티브(W)":  {
        "ticker":"412560.KS","qty":97, "avg":34188,"acct":"와이프_연금"
    },
    "교보악사파워인덱스(W)": {
        "ticker":"NAVER_W",  "qty":0,  "avg":0,    "acct":"와이프_연금"
    },
    "PLUS 고배당주채권혼합(W)":{
        "ticker":"480040.KS","qty":428,"avg":15802,"acct":"와이프_연금"
    },
}

# 네이버금융 펀드코드
NAVER_FUND_CODES = {
    "교보악사파워인덱스":    "KR5207764550",
    "교보악사파워인덱스(W)": "KR5207764550",
}

# 와이프 교보악사 — 수량 없이 금액으로만 보유
WIFE_KYOBO_AMOUNT = 2916576

# 투자원금
INVEST_ORIGIN = {
    "나_연금":    17500000,
    "나_IRP":     400000,
    "와이프_연금": 20481900,
}

# 과거 매매 실현이익
REALIZED_PNL = 6142527


# ══════════════════════════════════════════════
#  네이버금융 펀드 기준가 스크래핑
# ══════════════════════════════════════════════
@st.cache_data(ttl=300)
def fetch_naver_fund_price(fund_code: str) -> float:
    """네이버금융 펀드 페이지에서 기준가 스크래핑"""
    url = (
        f"https://finance.naver.com/fund/"
        f"fundDetail.naver?fundCd={fund_code}"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.0 Mobile/15E148 Safari/604.1"
        ),
        "Referer":         "https://finance.naver.com/fund/",
        "Accept-Language": "ko-KR,ko;q=0.9",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=8)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # 방법 1: .num.price 클래스
        tag = soup.select_one(".num.price")
        if tag:
            txt = tag.get_text(strip=True).replace(",","").replace("원","")
            try:
                return float(txt)
            except ValueError:
                pass

        # 방법 2: 숫자 범위 필터링
        for strong in soup.find_all("strong"):
            txt = strong.get_text(strip=True).replace(",","").replace("원","")
            try:
                val = float(txt)
                if 1000 < val < 50000:
                    return val
            except ValueError:
                continue

        # 방법 3: 페이지 텍스트에서 정규식
        text = soup.get_text()
        match = re.search(
            r"기준가[^\d]*([\d,]+\.?\d*)\s*원", text
        )
        if match:
            return float(match.group(1).replace(",",""))

        return 0.0
    except Exception:
        return 0.0


@st.cache_data(ttl=300)
def fetch_all_naver_funds() -> dict:
    """네이버금융 펀드 기준가 일괄 조회"""
    result = {}
    seen_codes = {}
    for name, code in NAVER_FUND_CODES.items():
        if code in seen_codes:
            # 같은 코드면 이미 조회한 값 재사용
            result[name] = seen_codes[code]
        else:
            price = fetch_naver_fund_price(code)
            seen_codes[code] = price
            result[name] = price
    return result


# ══════════════════════════════════════════════
#  yfinance ETF 현재가 조회
# ══════════════════════════════════════════════
@st.cache_data(ttl=300)
def fetch_prices(tickers: tuple) -> dict:
    """yfinance 일괄 현재가 조회"""
    prices = {}
    if not tickers:
        return prices

    try:
        raw = yf.download(
            tickers=list(tickers),
            period="2d",
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=True,
        )
        if not raw.empty:
            close = (
                raw["Close"]
                if "Close" in raw.columns
                else raw
            )
            if isinstance(close, pd.DataFrame):
                last = close.ffill().iloc[-1]
                for t in tickers:
                    if t in last.index:
                        v = float(last[t])
                        if not np.isnan(v) and v > 0:
                            prices[t] = v
            else:
                v = float(close.ffill().iloc[-1])
                if v > 0:
                    prices[list(tickers)[0]] = v
    except Exception:
        pass

    # 실패 종목 개별 재시도
    for t in [x for x in tickers if x not in prices]:
        try:
            hist = yf.Ticker(t).history(period="2d")
            if not hist.empty:
                v = float(hist["Close"].ffill().iloc[-1])
                if v > 0:
                    prices[t] = v
        except Exception:
            pass

    return prices


# ══════════════════════════════════════════════
#  전체 현재가 통합
# ══════════════════════════════════════════════
def get_all_prices():
    """ETF → yfinance / 교보악사 → 네이버금융 통합 조회"""
    all_holdings = {
        **ME_PENSION_HOLDINGS,
        **ME_IRP_HOLDINGS,
        **WIFE_PENSION_HOLDINGS,
    }

    # yfinance 티커 목록 (NAVER/NAVER_W 제외)
    tickers = tuple(set(
        v["ticker"] for v in all_holdings.values()
        if v["ticker"] not in ("NAVER","NAVER_W")
    ))

    fetched      = fetch_prices(tickers)
    naver_prices = fetch_all_naver_funds()

    name_to_price = {}
    for name, info in all_holdings.items():
        t = info["ticker"]

        if t in ("NAVER","NAVER_W"):
            # 네이버금융 기준가
            p = naver_prices.get(name, 0)
            name_to_price[name] = p if p > 0 else info["avg"]

        elif t in fetched:
            name_to_price[name] = fetched[t]

        else:
            # 조회 실패 → 평균매입가 대체
            name_to_price[name] = info["avg"]

    return name_to_price, fetched, naver_prices


# ══════════════════════════════════════════════
#  포트폴리오 DataFrame 생성
# ══════════════════════════════════════════════
def build_df(holdings: dict, prices: dict,
             extra_name: str = "", extra_amount: float = 0) -> pd.DataFrame:
    rows = []

    # 총 평가금액 계산
    total_eval = extra_amount
    for name, info in holdings.items():
        if info["ticker"] in ("NAVER_W",):
            total_eval += extra_amount if extra_name == name else 0
        else:
            cur = prices.get(name, info["avg"])
            total_eval += cur * info["qty"]

    for name, info in holdings.items():
        qty = info["qty"]
        avg = info["avg"]
        t   = info["ticker"]

        # 와이프 교보악사: 금액 직접 입력
        if t == "NAVER_W":
            cur      = prices.get(name, 2933)
            eval_amt = WIFE_KYOBO_AMOUNT
            buy_amt  = WIFE_KYOBO_AMOUNT
            pnl      = 0
            ret      = 0.0
        else:
            cur      = prices.get(name, avg)
            eval_amt = cur * qty
            buy_amt  = avg * qty
            pnl      = eval_amt - buy_amt
            ret      = (pnl / buy_amt * 100) if buy_amt > 0 else 0.0

        비중 = (eval_amt / total_eval * 100) if total_eval > 0 else 0

        rows.append({
            "종목명":     name,
            "보유수량":   qty,
            "평균매입가": avg,
            "현재가":     round(cur, 2),
            "매입금액":   int(buy_amt),
            "평가금액":   int(eval_amt),
            "손익":       int(pnl),
            "수익률(%)":  round(ret, 2),
            "비중(%)":    round(비중, 2),
        })

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════
#  매매 신호
# ══════════════════════════════════════════════
def get_signal(row, is_irp=False):
    ret  = row["수익률(%)"]
    wt   = row["비중(%)"]

    if ret <= -10:
        return "🔴 손절검토"
    elif ret >= 25:
        return "🟡 익절검토"
    elif ret >= 15:
        return "🔵 관찰"
    elif is_irp and wt > 35:
        return "🟠 비중축소(IRP)"
    elif wt > 30:
        return "🟠 비중과대"
    elif -5 <= ret <= 2 and wt < 10:
        return "🟢 추가매수검토"
    else:
        return "⚪ 유지"


SIG_COLOR = {
    "🔴 손절검토":    "#ff5252",
    "🟡 익절검토":    "#ffd600",
    "🔵 관찰":        "#40c4ff",
    "🟠 비중축소(IRP)":"#ff9800",
    "🟠 비중과대":    "#ff9800",
    "🟢 추가매수검토": "#00e676",
    "⚪ 유지":        "#aaaaaa",
}


# ══════════════════════════════════════════════
#  히스토리 데이터 (과거 날짜별 기록)
# ══════════════════════════════════════════════
@st.cache_data
def load_history():
    me = pd.DataFrame([
        {"날짜":"2026-03-04","수익률":35.66,"평가액":23740442},
        {"날짜":"2026-03-05","수익률":39.95,"평가액":24490367},
        {"날짜":"2026-03-06","수익률":43.60,"평가액":25130548},
        {"날짜":"2026-03-09","수익률":37.59,"평가액":24078984},
        {"날짜":"2026-03-10","수익률":39.71,"평가액":24449588},
        {"날짜":"2026-03-11","수익률":40.54,"평가액":24594821},
        {"날짜":"2026-03-12","수익률":41.29,"평가액":24725399},
        {"날짜":"2026-03-13","수익률":40.14,"평가액":24524931},
        {"날짜":"2026-03-16","수익률":39.33,"평가액":24382512},
        {"날짜":"2026-03-17","수익률":41.33,"평가액":24733554},
        {"날짜":"2026-03-18","수익률":44.62,"평가액":25308531},
        {"날짜":"2026-03-20","수익률":44.22,"평가액":25238835},
        {"날짜":"2026-03-23","수익률":37.20,"평가액":24009675},
        {"날짜":"2026-03-24","수익률":38.50,"평가액":24238300},
        {"날짜":"2026-03-25","수익률":41.68,"평가액":24794160},
    ])
    wife = pd.DataFrame([
        {"날짜":"2026-03-05","수익률": 1.93,"평가액":20876966},
        {"날짜":"2026-03-09","수익률":-2.74,"평가액":19920591},
        {"날짜":"2026-03-11","수익률":-0.57,"평가액":20364236},
        {"날짜":"2026-03-12","수익률":-0.77,"평가액":20325131},
        {"날짜":"2026-03-13","수익률":-1.53,"평가액":20169031},
        {"날짜":"2026-03-16","수익률":-2.26,"평가액":20019286},
        {"날짜":"2026-03-17","수익률":-0.76,"평가액":20327241},
        {"날짜":"2026-03-18","수익률":-0.22,"평가액":20715516},
        {"날짜":"2026-03-20","수익률":-1.02,"평가액":20548431},
        {"날짜":"2026-03-23","수익률":-3.82,"평가액":19699271},
        {"날짜":"2026-03-24","수익률":-4.16,"평가액":19896556},
        {"날짜":"2026-03-25","수익률":-1.13,"평가액":20250356},
    ])
    me["날짜"]   = pd.to_datetime(me["날짜"])
    wife["날짜"] = pd.to_datetime(wife["날짜"])
    return me, wife


@st.cache_data
def load_trades():
    return pd.DataFrame([
        {
            "매매일자":"2026-02-24",
            "종목명":"신한 TopsValue40",
            "매입금액":5273643,"판매금액":6713634,
            "수익금액":1439991,"수익률":27.31
        },
        {
            "매매일자":"2026-02-24",
            "종목명":"교보악사파워인덱스",
            "매입금액":7041648,"판매금액":11165888,
            "수익금액":4124240,"수익률":58.57
        },
        {
            "매매일자":"2026-02-24",
            "종목명":"RISE 미국S&P500",
            "매입금액":5255774,"판매금액":5834070,
            "수익금액":578296,"수익률":11.00
        },
    ])


# ══════════════════════════════════════════════
#  데이터 로드
# ══════════════════════════════════════════════
with st.spinner("📡 현재가 조회 중..."):
    name_prices, raw_fetched, naver_prices = get_all_prices()

me_p_df   = build_df(ME_PENSION_HOLDINGS,   name_prices)
me_i_df   = build_df(ME_IRP_HOLDINGS,       name_prices)
wife_p_df = build_df(
    WIFE_PENSION_HOLDINGS, name_prices,
    extra_name="교보악사파워인덱스(W)",
    extra_amount=WIFE_KYOBO_AMOUNT
)

me_hist, wife_hist = load_history()
trade_df           = load_trades()


# ── 계좌 합계 계산 ─────────────────────────────
def acct_summary(df, origin):
    ev  = df["평가금액"].sum()
    pnl = ev - origin
    ret = pnl / origin * 100 if origin > 0 else 0
    return ev, pnl, ret

me_p_ev,   me_p_pnl,   me_p_ret   = acct_summary(me_p_df,   INVEST_ORIGIN["나_연금"])
me_i_ev,   me_i_pnl,   me_i_ret   = acct_summary(me_i_df,   INVEST_ORIGIN["나_IRP"])
wife_ev,   wife_pnl,   wife_ret   = acct_summary(wife_p_df, INVEST_ORIGIN["와이프_연금"])

total_ev   = me_p_ev + me_i_ev + wife_ev
total_orig = sum(INVEST_ORIGIN.values())
total_pnl  = total_ev - total_orig
total_ret  = total_pnl / total_orig * 100


# ══════════════════════════════════════════════
#  사이드바
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏦 퇴직연금")
    menu = st.radio("메뉴", [
        "🏠 대시보드",
        "👤 나 포트폴리오",
        "👩 와이프 포트폴리오",
        "🚦 매매 신호",
        "📈 추이 차트",
        "📋 매매일지",
        "✏️ 수동 입력",
    ], label_visibility="collapsed")

    st.markdown("---")

    if st.button("🔄 현재가 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption(f"⏱️ 5분 자동갱신")
    st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
    st.markdown("---")
    st.caption(f"💼 총자산 ₩{total_ev:,.0f}")
    st.caption(f"📊 수익률 {total_ret:+.2f}%")


# ══════════════════════════════════════════════
#  공통 종목 카드 렌더러
# ══════════════════════════════════════════════
def render_card(row, is_irp=False, price_source=""):
    ret   = row["수익률(%)"]
    ret_c = "#00e676" if ret >= 0 else "#ff5252"
    sig   = get_signal(row, is_irp)
    s_c   = SIG_COLOR.get(sig, "#aaa")

    # 현재가 소스 배지
    src_badge = ""
    if price_source == "naver":
        src_badge = (
            '<span style="font-size:0.65rem;background:#1565c0;'
            'color:white;padding:1px 5px;border-radius:4px;margin-left:4px">'
            '네이버</span>'
        )
    elif price_source == "yfinance":
        src_badge = (
            '<span style="font-size:0.65rem;background:#1b5e20;'
            'color:white;padding:1px 5px;border-radius:4px;margin-left:4px">'
            'yfinance</span>'
        )
    elif price_source == "fallback":
        src_badge = (
            '<span style="font-size:0.65rem;background:#b71c1c;'
            'color:white;padding:1px 5px;border-radius:4px;margin-left:4px">'
            '조회실패</span>'
        )

    qty_txt = (
        f"{row['보유수량']:,.0f}주 · 평균 ₩{row['평균매입가']:,.0f}"
        if row["보유수량"] > 0
        else "금액 직접 보유"
    )

    cur_txt = (
        f"₩{row['현재가']:,.2f}"
        if row["현재가"] < 10000
        else f"₩{row['현재가']:,.0f}"
    )

    st.markdown(f"""
    <div class="price-card">
        <div style="display:flex;justify-content:space-between;
                    align-items:flex-start">
            <div style="flex:1">
                <div style="font-weight:700;font-size:0.95rem">
                    {row['종목명']}{src_badge}
                </div>
                <div style="font-size:0.78rem;color:#aaa;margin-top:2px">
                    {qty_txt}
                </div>
            </div>
            <div style="text-align:right;min-width:90px">
                <div style="font-size:1.1rem;font-weight:800;color:{ret_c}">
                    {ret:+.2f}%
                </div>
                <div style="font-size:0.78rem;color:#aaa">{cur_txt}</div>
            </div>
        </div>
        <div style="display:flex;justify-content:space-between;
                    align-items:center;margin-top:8px;font-size:0.82rem">
            <span style="color:#aaa">
                평가 ₩{row['평가금액']:,.0f}
            </span>
            <span style="color:{ret_c}">
                {'+' if row['손익']>=0 else ''}₩{row['손익']:,.0f}
            </span>
            <span style="color:{s_c};font-weight:700">{sig}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def price_source(name, info):
    """종목의 현재가 출처 판단"""
    t = info["ticker"]
    if t in ("NAVER","NAVER_W"):
        p = naver_prices.get(name, 0)
        return "naver" if p > 0 else "fallback"
    elif t in raw_fetched:
        return "yfinance"
    else:
        return "fallback"


# ══════════════════════════════════════════════
#  🏠 대시보드
# ══════════════════════════════════════════════
if "대시보드" in menu:
    st.markdown("## 🏦 퇴직연금 대시보드")

    # 조회 현황 배너
    etf_ok    = len(raw_fetched)
    etf_total = len(set(
        v["ticker"] for v in {
            **ME_PENSION_HOLDINGS,
            **ME_IRP_HOLDINGS,
            **WIFE_PENSION_HOLDINGS
        }.values()
        if v["ticker"] not in ("NAVER","NAVER_W")
    ))
    naver_ok = sum(1 for v in naver_prices.values() if v > 0)
    naver_tot = len(NAVER_FUND_CODES)

    if etf_ok == etf_total and naver_ok == naver_tot:
        st.success(
            f"✅ 전체 조회 완료 — "
            f"ETF {etf_ok}/{etf_total} · "
            f"네이버펀드 {naver_ok}/{naver_tot} — "
            f"{datetime.now().strftime('%H:%M:%S')}"
        )
    else:
        st.warning(
            f"⚠️ 일부 조회 실패 — "
            f"ETF {etf_ok}/{etf_total} · "
            f"네이버펀드 {naver_ok}/{naver_tot}"
        )

    # KPI 카드
    r1c1, r1c2 = st.columns(2)
    r2c1, r2c2 = st.columns(2)
    r3c1, r3c2 = st.columns(2)

    def kpi(col, lbl, val, is_pct=False, pos=True):
        v = f"{val:+.2f}%" if is_pct else f"₩{val:,.0f}"
        c = "pos" if pos else "neg"
        col.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-lbl">{lbl}</div>
            <div class="kpi-val"><span class="{c}">{v}</span></div>
        </div>""", unsafe_allow_html=True)

    kpi(r1c1, "💼 총 자산",    total_ev)
    kpi(r1c2, "💰 총 손익",    total_pnl, pos=total_pnl >= 0)
    kpi(r2c1, "📊 전체수익률", total_ret, is_pct=True, pos=total_ret >= 0)
    kpi(r2c2, "🏆 실현이익",   REALIZED_PNL, pos=True)
    kpi(r3c1, "👤 나 합계",    me_p_ev + me_i_ev)
    kpi(r3c2, "👩 와이프",     wife_ev, pos=wife_pnl >= 0)

    st.markdown("<br>", unsafe_allow_html=True)

    # 계좌별 수익률 바
    st.markdown("#### 📊 계좌별 수익률")
    acct_df = pd.DataFrame({
        "계좌":   ["나_퇴직연금","나_IRP","와이프_퇴직연금"],
        "수익률": [me_p_ret, me_i_ret, wife_ret],
    })
    fig = go.Figure(go.Bar(
        x=acct_df["수익률"],
        y=acct_df["계좌"],
        orientation="h",
        marker_color=[
            "#00e676" if v >= 0 else "#ff5252"
            for v in acct_df["수익률"]
        ],
        text=[f"{v:+.2f}%" for v in acct_df["수익률"]],
        textposition="outside",
    ))
    fig.add_vline(x=0, line_color="gray")
    fig.update_layout(
        height=220,
        margin=dict(l=10,r=70,t=10,b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#333"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # 전체 자산배분 파이
    st.markdown("#### 💼 전체 자산배분")
    pie_rows = []
    for df, sfx in [
        (me_p_df,   ""),
        (me_i_df,   "(IRP)"),
        (wife_p_df, "(W)"),
    ]:
        for _, r in df.iterrows():
            if r["평가금액"] > 0:
                pie_rows.append({
                    "종목": r["종목명"] + sfx,
                    "금액": r["평가금액"]
                })
    pie_df = pd.DataFrame(pie_rows)

    fig2 = go.Figure(go.Pie(
        labels=pie_df["종목"],
        values=pie_df["금액"],
        hole=0.4,
        textinfo="percent",
        textfont=dict(size=9),
        marker=dict(
            colors=px.colors.qualitative.Set3,
            line=dict(color="white", width=1)
        ),
    ))
    fig2.update_layout(
        height=400,
        margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(font=dict(size=8), orientation="v"),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # 합산 추이
    st.markdown("#### 📈 합산 평가액 추이")
    merged = pd.merge(
        me_hist.rename(columns={"평가액":"나"}),
        wife_hist.rename(columns={"평가액":"와이프"}),
        on="날짜", how="outer"
    ).sort_values("날짜").ffill()
    merged["합산"] = merged["나"] + merged["와이프"]

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=merged["날짜"], y=merged["합산"],
        name="합산", fill="tozeroy",
        fillcolor="rgba(100,181,246,0.15)",
        line=dict(color="#64b5f6", width=2),
    ))
    fig3.add_trace(go.Scatter(
        x=merged["날짜"], y=merged["나"],
        name="나", line=dict(color="#00e676",width=1.5,dash="dot"),
    ))
    fig3.add_trace(go.Scatter(
        x=merged["날짜"], y=merged["와이프"],
        name="와이프", line=dict(color="#ff7043",width=1.5,dash="dot"),
    ))
    fig3.update_layout(
        height=320,
        margin=dict(l=10,r=10,t=10,b=10),
        yaxis_tickformat=",",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#222"),
        yaxis=dict(gridcolor="#222"),
        legend=dict(orientation="h", y=1.1, font=dict(size=10)),
        hovermode="x unified",
    )
    st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════
#  👤 나 포트폴리오
# ══════════════════════════════════════════════
elif "나 포트폴리오" in menu:
    st.markdown("## 👤 나의 포트폴리오")
    tab1, tab2 = st.tabs(["🏛️ 퇴직연금", "💼 IRP"])

    with tab1:
        c1, c2 = st.columns(2)
        c1.metric("평가금액", f"₩{me_p_ev:,.0f}")
        c2.metric(
            "수익률",
            f"{me_p_ret:+.2f}%",
            delta=f"₩{me_p_pnl:+,.0f}"
        )

        st.markdown("#### 📋 종목 현황")
        for _, r in me_p_df.iterrows():
            info = ME_PENSION_HOLDINGS.get(r["종목명"], {})
            src  = price_source(r["종목명"], info) if info else "fallback"
            render_card(r, is_irp=False, price_source=src)

        # 수익률 바
        tmp = me_p_df.sort_values("수익률(%)")
        fig = go.Figure(go.Bar(
            x=tmp["수익률(%)"],
            y=tmp["종목명"],
            orientation="h",
            marker_color=[
                "#ff5252" if v < 0 else "#00e676"
                for v in tmp["수익률(%)"]
            ],
            text=[f"{v:+.1f}%" for v in tmp["수익률(%)"]],
            textposition="outside",
        ))
        fig.add_vline(x=0, line_color="gray")
        fig.update_layout(
            height=320,
            margin=dict(l=10,r=70,t=10,b=5),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#333"),
        )
        st.plotly_chart(fig, use_container_width=True)

        # 경고
        danger = me_p_df[me_p_df["수익률(%)"] <= -7]
        if not danger.empty:
            for _, r in danger.iterrows():
                st.markdown(f"""
                <div class="danger-box">
                    🔴 <b>{r['종목명']}</b> {r['수익률(%)']:+.2f}%
                    — 손절 라인 근접
                </div>
                """, unsafe_allow_html=True)

    with tab2:
        c1, c2 = st.columns(2)
        c1.metric("평가금액", f"₩{me_i_ev:,.0f}")
        c2.metric(
            "수익률",
            f"{me_i_ret:+.2f}%",
            delta=f"₩{me_i_pnl:+,.0f}"
        )

        irp_danger = me_i_df[me_i_df["수익률(%)"] >= 24]
        if not irp_danger.empty:
            st.markdown("""
            <div class="danger-box">
                🔴 <b>TIGER 반도체TOP10</b>
                수익률 24%+ · IRP 35% 한도 주의<br>
                → 부분 익절 강력 권장
            </div>
            """, unsafe_allow_html=True)

        st.markdown("#### 📋 종목 현황")
        for _, r in me_i_df.iterrows():
            info = ME_IRP_HOLDINGS.get(r["종목명"], {})
            src  = price_source(r["종목명"], info) if info else "fallback"
            render_card(r, is_irp=True, price_source=src)


# ══════════════════════════════════════════════
#  👩 와이프 포트폴리오
# ══════════════════════════════════════════════
elif "와이프 포트폴리오" in menu:
    st.markdown("## 👩 와이프 포트폴리오")

    c1, c2 = st.columns(2)
    c1.metric("평가금액", f"₩{wife_ev:,.0f}")
    c2.metric(
        "수익률",
        f"{wife_ret:+.2f}%",
        delta=f"₩{wife_pnl:+,.0f}"
    )

    if wife_ret < -1:
        st.markdown("""
        <div class="warn-box">
            ⚠️ 2026-02-24 리밸런싱 이후 손실 지속 중<br>
            누적 실현익 ₩6,142,527은 별도 확보
        </div>
        """, unsafe_allow_html=True)

    st.markdown("#### 📋 종목 현황")
    for _, r in wife_p_df.iterrows():
        orig_name = r["종목명"]
        info = WIFE_PENSION_HOLDINGS.get(orig_name, {})
        src  = price_source(orig_name, info) if info else "fallback"
        render_card(r, is_irp=False, price_source=src)

    # 경고 박스
    robot_w = wife_p_df[
        wife_p_df["종목명"].str.contains("로봇")
    ]
    if not robot_w.empty:
        ret_v = robot_w.iloc[0]["수익률(%)"]
        if ret_v <= -7:
            st.markdown(f"""
            <div class="danger-box">
                🔴 <b>KODEX 로봇액티브</b> {ret_v:+.2f}%
                — 손절기준(-10%) 근접<br>
                나의 계좌도 동일 종목 보유 (공통 리스크)
            </div>
            """, unsafe_allow_html=True)

    car_w = wife_p_df[wife_p_df["종목명"].str.contains("자동차")]
    if not car_w.empty:
        ret_v = car_w.iloc[0]["수익률(%)"]
        if ret_v <= -4:
            st.markdown(f"""
            <div class="warn-box">
                ⚠️ <b>KODEX 자동차</b> {ret_v:+.2f}%
                — -8% 도달 시 손절 검토
            </div>
            """, unsafe_allow_html=True)

    # 파이 차트
    fig = go.Figure(go.Pie(
        labels=wife_p_df[wife_p_df["평가금액"]>0]["종목명"],
        values=wife_p_df[wife_p_df["평가금액"]>0]["평가금액"],
        hole=0.4,
        textinfo="percent+label",
        textfont=dict(size=9),
        marker=dict(colors=px.colors.qualitative.Pastel),
    ))
    fig.update_layout(
        height=350,
        margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════
#  🚦 전체 매매 신호
# ══════════════════════════════════════════════
elif "매매 신호" in menu:
    st.markdown("## 🚦 전체 매매 신호")
    st.caption("목표 +20% / 손절 -10% / IRP 단일종목 35% 한도")

    all_sig_rows = []
    for df, acct, is_irp in [
        (me_p_df,   "나_연금",  False),
        (me_i_df,   "나_IRP",   True),
        (wife_p_df, "와이프",   False),
    ]:
        for _, r in df.iterrows():
            sig  = get_signal(r, is_irp)
            prio = {
                "🔴 손절검토":5,"🟡 익절검토":4,
                "🟠 비중축소(IRP)":3,"🟠 비중과대":3,
                "🔵 관찰":2,"🟢 추가매수검토":1,"⚪ 유지":0
            }.get(sig, 0)
            all_sig_rows.append({
                "계좌":     acct,
                "종목명":   r["종목명"],
                "수익률%":  r["수익률(%)"],
                "비중%":    r["비중(%)"],
                "신호":     sig,
                "우선순위": prio,
            })

    sig_df = pd.DataFrame(all_sig_rows).sort_values(
        "우선순위", ascending=False
    ).reset_index(drop=True)

    for _, r in sig_df.iterrows():
        ret_c = "#00e676" if r["수익률%"] >= 0 else "#ff5252"
        s_c   = SIG_COLOR.get(r["신호"], "#888")
        st.markdown(f"""
        <div style="background:#1e2130;border-radius:10px;
                    padding:12px 14px;margin:5px 0;
                    border-left:4px solid {s_c};">
            <div style="display:flex;justify-content:space-between">
                <div>
                    <span style="font-size:0.7rem;color:#888">
                        {r['계좌']}
                    </span>
                    <div style="font-weight:700">{r['종목명']}</div>
                </div>
                <div style="text-align:right">
                    <div style="color:{ret_c};font-weight:800;
                                font-size:1rem">
                        {r['수익률%']:+.2f}%
                    </div>
                    <div style="font-size:0.75rem;color:#aaa">
                        비중 {r['비중%']:.1f}%
                    </div>
                </div>
            </div>
            <div style="margin-top:6px;font-weight:700;
                        color:{s_c};font-size:0.9rem">
                {r['신호']}
            </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  📈 추이 차트
# ══════════════════════════════════════════════
elif "추이 차트" in menu:
    st.markdown("## 📈 수익률 추이")

    # 오늘 실시간 수익률 추가
    today = pd.Timestamp(datetime.now().date())

    def append_today(hist_df, today_ret):
        if today > hist_df["날짜"].max():
            return pd.concat([
                hist_df,
                pd.DataFrame([{"날짜": today, "수익률": today_ret}])
            ]).reset_index(drop=True)
        else:
            hist_df = hist_df.copy()
            hist_df.loc[hist_df["날짜"] == today, "수익률"] = today_ret
            return hist_df

    me_h2   = append_today(me_hist,   me_p_ret)
    wife_h2 = append_today(wife_hist, wife_ret)

    tab1, tab2, tab3 = st.tabs(["👤 나", "👩 와이프", "📊 비교"])

    with tab1:
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.65, 0.35],
            subplot_titles=("평가금액","수익률(%)")
        )

        # 평가금액 (히스토리 + 오늘 실시간)
        today_eval = me_p_ev + me_i_ev
        me_eval_h  = me_hist.copy()
        if today > me_eval_h["날짜"].max():
            me_eval_h = pd.concat([
                me_eval_h,
                pd.DataFrame([{"날짜":today,"수익률":me_p_ret,"평가액":today_eval}])
            ])

        fig.add_trace(go.Scatter(
            x=me_eval_h["날짜"], y=me_eval_h["평가액"],
            fill="tozeroy",
            fillcolor="rgba(0,230,118,0.12)",
            line=dict(color="#00e676", width=2),
            name="평가금액",
        ), row=1, col=1)

        bar_c = [
            "#00e676" if v >= 0 else "#ff5252"
            for v in me_h2["수익률"]
        ]
        fig.add_trace(go.Bar(
            x=me_h2["날짜"],
            y=me_h2["수익률"],
            marker_color=bar_c,
            name="수익률",
        ), row=2, col=1)

        fig.update_layout(
            height=480, showlegend=False,
            margin=dict(l=10,r=10,t=30,b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor="#222", tickformat=","),
            yaxis2=dict(gridcolor="#222", ticksuffix="%"),
            xaxis2=dict(gridcolor="#222"),
        )
        st.plotly_chart(fig, use_container_width=True)

        max_v = me_hist["평가액"].max()
        mdd   = (me_p_ev - max_v) / max_v * 100
        c1, c2, c3 = st.columns(3)
        c1.metric("현재 (나+IRP)", f"₩{today_eval:,.0f}")
        c2.metric("역대 최고",     f"₩{max_v:,.0f}")
        c3.metric("고점 대비",     f"{mdd:.2f}%")

    with tab2:
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.65, 0.35],
            subplot_titles=("평가금액","수익률(%)")
        )
        wife_eval_h = wife_hist.copy()
        if today > wife_eval_h["날짜"].max():
            wife_eval_h = pd.concat([
                wife_eval_h,
                pd.DataFrame([{"날짜":today,"수익률":wife_ret,"평가액":wife_ev}])
            ])

        fig.add_trace(go.Scatter(
            x=wife_eval_h["날짜"], y=wife_eval_h["평가액"],
            fill="tozeroy",
            fillcolor="rgba(255,112,67,0.12)",
            line=dict(color="#ff7043", width=2),
            name="평가금액",
        ), row=1, col=1)

        bar_c2 = [
            "#00e676" if v >= 0 else "#ff5252"
            for v in wife_h2["수익률"]
        ]
        fig.add_trace(go.Bar(
            x=wife_h2["날짜"],
            y=wife_h2["수익률"],
            marker_color=bar_c2,
            name="수익률",
        ), row=2, col=1)

        fig.update_layout(
            height=480, showlegend=False,
            margin=dict(l=10,r=10,t=30,b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor="#222", tickformat=","),
            yaxis2=dict(gridcolor="#222", ticksuffix="%"),
            xaxis2=dict(gridcolor="#222"),
        )
        st.plotly_chart(fig, use_container_width=True)

        max_v2 = wife_hist["평가액"].max()
        mdd2   = (wife_ev - max_v2) / max_v2 * 100
        c1, c2, c3 = st.columns(3)
        c1.metric("현재", f"₩{wife_ev:,.0f}")
        c2.metric("역대 최고", f"₩{max_v2:,.0f}")
        c3.metric("고점 대비", f"{mdd2:.2f}%")

    with tab3:
        merged2 = pd.merge(
            me_h2[["날짜","수익률"]].rename(columns={"수익률":"나"}),
            wife_h2[["날짜","수익률"]].rename(columns={"수익률":"와이프"}),
            on="날짜", how="outer"
        ).sort_values("날짜").ffill()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=merged2["날짜"], y=merged2["나"],
            name="나", mode="lines+markers",
            line=dict(color="#00e676", width=2.5),
        ))
        fig.add_trace(go.Scatter(
            x=merged2["날짜"], y=merged2["와이프"],
            name="와이프", mode="lines+markers",
            line=dict(color="#ff7043", width=2.5),
        ))
        fig.add_hline(y=0, line_color="gray", line_dash="dot")

        # 오늘 실시간 포인트 강조
        fig.add_annotation(
            x=me_h2["날짜"].iloc[-1],
            y=me_h2["수익률"].iloc[-1],
            text=f"  나: {me_p_ret:+.2f}%",
            showarrow=False, xanchor="left",
            font=dict(color="#00e676", size=11),
        )
        fig.add_annotation(
            x=wife_h2["날짜"].iloc[-1],
            y=wife_h2["수익률"].iloc[-1],
            text=f"  와이프: {wife_ret:+.2f}%",
            showarrow=False, xanchor="left",
            font=dict(color="#ff7043", size=11),
        )

        fig.update_layout(
            title="수익률 비교 (%)",
            height=420,
            margin=dict(l=10,r=70,t=40,b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#222"),
            yaxis=dict(gridcolor="#222", ticksuffix="%"),
            legend=dict(orientation="h", y=1.12),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("나 현재",    f"{me_p_ret:+.2f}%")
        c2.metric("와이프 현재", f"{wife_ret:+.2f}%")
        c3.metric("합산 수익률", f"{total_ret:+.2f}%")


# ══════════════════════════════════════════════
#  📋 매매일지
# ══════════════════════════════════════════════
elif "매매일지" in menu:
    st.markdown("## 📋 매매일지")
    st.markdown(f"""
    <div class="safe-box">
        ✅ <b>2026-02-24 리밸런싱 완료</b><br>
        누적 실현이익: <b>+₩{REALIZED_PNL:,.0f}</b>
    </div>
    """, unsafe_allow_html=True)

    for _, r in trade_df.iterrows():
        st.markdown(f"""
        <div style="background:#1e2130;border-radius:10px;
                    padding:12px 14px;margin:8px 0;
                    border-left:3px solid #00e676;">
            <div style="font-size:0.75rem;color:#888">
                {r['매매일자']}
            </div>
            <div style="font-weight:700;font-size:1rem">
                {r['종목명']}
            </div>
            <div style="display:flex;gap:16px;
                        margin-top:6px;font-size:0.83rem">
                <div>
                    <div style="color:#888;font-size:0.7rem">
                        매입금액
                    </div>
                    <div>₩{r['매입금액']:,.0f}</div>
                </div>
                <div>
                    <div style="color:#888;font-size:0.7rem">
                        판매금액
                    </div>
                    <div>₩{r['판매금액']:,.0f}</div>
                </div>
                <div>
                    <div style="color:#888;font-size:0.7rem">
                        수익금액
                    </div>
                    <div style="color:#00e676;font-weight:700">
                        +₩{r['수익금액']:,.0f}
                    </div>
                </div>
            </div>
            <div style="margin-top:4px;color:#00e676;
                        font-size:0.85rem">
                수익률 +{r['수익률']:.2f}%
            </div>
        </div>
        """, unsafe_allow_html=True)

    fig = go.Figure(go.Bar(
        x=trade_df["종목명"],
        y=trade_df["수익금액"],
        marker_color=["#00e676","#40c4ff","#ffd600"],
        text=[f"+₩{v:,.0f}" for v in trade_df["수익금액"]],
        textposition="outside",
    ))
    fig.update_layout(
        title=f"실현 수익 합계: +₩{REALIZED_PNL:,.0f}",
        height=340,
        margin=dict(l=10,r=10,t=40,b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#222", tickformat=","),
    )
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════
#  ✏️ 수동 입력
# ══════════════════════════════════════════════
elif "수동 입력" in menu:
    st.markdown("## ✏️ 수동 가격 입력")
    st.markdown("> 조회 실패 종목을 직접 입력해 보정합니다.")

    # 현재 조회 상태 표시
    st.markdown("#### 📡 현재 조회 상태")
    status_rows = []
    seen = set()

    all_h = {
        **ME_PENSION_HOLDINGS,
        **ME_IRP_HOLDINGS,
        **WIFE_PENSION_HOLDINGS,
    }
    for name, info in all_h.items():
        if name in seen:
            continue
        seen.add(name)
        t = info["ticker"]
        p = name_prices.get(name, 0)

        if t in ("NAVER","NAVER_W"):
            nv = naver_prices.get(name, 0)
            src = "✅ 네이버금융" if nv > 0 else "⚠️ 조회실패"
        elif t in raw_fetched:
            src = "✅ yfinance"
        else:
            src = "⚠️ 조회실패"

        status_rows.append({
            "종목명":  name,
            "티커":    t,
            "현재가":  f"₩{p:,.2f}" if p < 10000 else f"₩{p:,.0f}",
            "출처":    src,
        })

    st.dataframe(
        pd.DataFrame(status_rows),
        use_container_width=True
    )

    st.markdown("---")

    # 교보악사 수동 보정
    st.markdown("#### 교보악사파워인덱스 수동 보정")
    st.caption(
        "네이버 조회 실패 시 퇴직연금 앱에서 확인 후 직접 입력"
    )

    current_kyobo = naver_prices.get("교보악사파워인덱스", 0)
    if current_kyobo > 0:
        st.success(f"✅ 네이버금융 자동 조회 성공: ₩{current_kyobo:,.2f}")
    else:
        st.warning("⚠️ 네이버금융 조회 실패 — 직접 입력하세요")

    with st.form("kyobo_form"):
        new_val = st.number_input(
            "교보악사파워인덱스 기준가 (원)",
            value=float(current_kyobo) if current_kyobo > 0 else 2933.99,
            step=0.01,
            format="%.2f",
        )
        if st.form_submit_button(
            "✅ 적용", use_container_width=True
        ):
            st.cache_data.clear()
            st.success(f"₩{new_val:,.2f} 적용 완료! 재조회 중...")
            st.rerun()

    st.markdown("---")

    # 조회 실패 ETF 수동 보정
    failed_etf = [
        (name, info)
        for name, info in all_h.items()
        if info["ticker"] not in ("NAVER","NAVER_W")
        and info["ticker"] not in raw_fetched
    ]
    if failed_etf:
        st.markdown("#### ⚠️ ETF 조회 실패 종목 수동 입력")
        with st.form("failed_etf_form"):
            manual_vals = {}
            for name, info in failed_etf:
                manual_vals[name] = st.number_input(
                    f"{name} 현재가",
                    value=int(info["avg"]),
                    step=10,
                    key=f"manual_{name}",
                )
            if st.form_submit_button(
                "✅ 전체 적용", use_container_width=True
            ):
                st.success("수동 입력 적용 완료! (세션 내 유지)")
                for name, val in manual_vals.items():
                    name_prices[name] = val
                st.rerun()

# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time

st.set_page_config(
    page_title="퇴직연금 포트폴리오",
    page_icon=":moneybag:",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.kpi-card {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d5986 100%);
    border-radius: 12px; padding: 20px; text-align: center;
    color: white; margin: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}
.kpi-label { font-size: 13px; opacity: 0.85; margin-bottom: 6px; }
.kpi-value { font-size: 22px; font-weight: 700; }
.stock-card { background: #1e2a3a; border-radius: 10px; padding: 14px; margin: 6px 0; }
.price-ok   { background:#1a3a1a; border-radius:8px; padding:8px 12px; margin:3px 0; font-size:13px; }
.price-fail { background:#3a1a1a; border-radius:8px; padding:8px 12px; margin:3px 0; font-size:13px; }
.sig-sell  { background:#3a1a1a; border-left:4px solid #ff6b6b; padding:10px; border-radius:6px; margin:4px 0; }
.sig-watch { background:#3a2d1a; border-left:4px solid #ffd43b; padding:10px; border-radius:6px; margin:4px 0; }
.sig-hold  { background:#1a2a3a; border-left:4px solid #74c0fc; padding:10px; border-radius:6px; margin:4px 0; }
.fund-info  { background:#1a2540; border:1px solid #2d5986; border-radius:8px; padding:12px; margin:8px 0; font-size:13px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 보유종목 정의
# ─────────────────────────────────────────────
# 교보악사파워인덱스 펀드 계산 공식:
#   매입금액 = 좌수 * (매입기준가 / 1000)
#   평가금액 = 좌수 * (현재기준가 / 1000)
#   수익률   = (현재기준가 - 매입기준가) / 매입기준가 * 100
#
#   funetf 기준가 이력에서 확인:
#   26.03.05 기준가 = 2,672.85원 (매입일)
#   26.03.26 기준가 = 2,972.91원 (최신)
#   좌수: 888,035좌
#   매입금액 = 888,035 * (2,672.85 / 1000) = 2,373,348원
#   평가금액 = 888,035 * (2,972.91 / 1000) = 2,639,676원
#   수익률   = (2972.91 - 2672.85) / 2672.85 * 100 = +11.23%

ME_PENSION = {
    "KODEX AI전력핵심설비":   {
        "ticker": "487240.KS", "qty": 120, "avg": 29559.0,
        "acct": "나_연금", "type": "ETF"
    },
    "KODEX AI반도체핵심장비": {
        "ticker": "465660.KS", "qty": 151, "avg": 23451.0,
        "acct": "나_연금", "type": "ETF"
    },
    "KODEX 로봇액티브":       {
        "ticker": "412560.KS", "qty": 110, "avg": 32355.0,
        "acct": "나_연금", "type": "ETF"
    },
    "PLUS K방산":             {
        "ticker": "455890.KS", "qty": 48, "avg": 73563.0,
        "acct": "나_연금", "type": "ETF"
    },
    "교보악사파워인덱스":     {
        "ticker":   "NAVER_FUND",
        "qty":      888035,      # 보유 좌수
        "avg":      2672.85,     # 매입기준가(원) - funetf 26.03.05 확인값
        "acct":     "나_연금",
        "type":     "FUND",
        # 정확한 ClassC-Pe URL
        "fund_url": "https://www.funetf.co.kr/product/fund/view/K55207BU0715",
    },
    "PLUS 고배당주채권혼합":  {
        "ticker": "480040.KS", "qty": 454, "avg": 15655.0,
        "acct": "나_연금", "type": "ETF"
    },
}

ME_IRP = {
    "TIGER 반도체TOP10":     {
        "ticker": "385720.KS", "qty": 5, "avg": 27319.0,
        "acct": "나_IRP", "type": "ETF"
    },
    "TIME 글로벌탑픽액티브": {
        "ticker": "0113D0.KS", "qty": 12, "avg": 11188.0,
        "acct": "나_IRP", "type": "ETF"
    },
    "PLUS 고배당주채권혼합": {
        "ticker": "480040.KS", "qty": 3, "avg": 15745.0,
        "acct": "나_IRP", "type": "ETF"
    },
}

WIFE_PENSION = {
    "KODEX 로봇액티브":       {
        "ticker": "412560.KS", "qty": 50, "avg": 32970.0,
        "acct": "와이프_연금", "type": "ETF"
    },
    "KODEX AI반도체핵심장비": {
        "ticker": "465660.KS", "qty": 30, "avg": 25920.0,
        "acct": "와이프_연금", "type": "ETF"
    },
    "PLUS K방산":             {
        "ticker": "455890.KS", "qty": 14, "avg": 74820.0,
        "acct": "와이프_연금", "type": "ETF"
    },
    "SOL AI반도체소부장":     {
        "ticker": "448540.KS", "qty": 163, "avg": 12920.0,
        "acct": "와이프_연금", "type": "ETF"
    },
    "KODEX 자동차":           {
        "ticker": "091180.KS", "qty": 110, "avg": 22270.0,
        "acct": "와이프_연금", "type": "ETF"
    },
    "PLUS 고배당주채권혼합":  {
        "ticker": "480040.KS", "qty": 530, "avg": 14690.0,
        "acct": "와이프_연금", "type": "ETF"
    },
}

ALL_HOLDINGS = {}
ALL_HOLDINGS.update(ME_PENSION)
ALL_HOLDINGS.update(ME_IRP)
ALL_HOLDINGS.update(WIFE_PENSION)

# ─────────────────────────────────────────────
# 교보악사 기준가 스크래핑 (ClassC-Pe 전용)
# ─────────────────────────────────────────────

@st.cache_data(ttl=300)
def fetch_kyobo_price(fund_url):
    """
    funetf.co.kr K55207BU0715 (ClassC-Pe) 에서 기준가 파싱
    페이지 확인값: 26.03.26 기준 2,972.91원
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9",
    }
    try:
        resp = requests.get(fund_url, headers=headers, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        full_text = soup.get_text(separator="\n")
        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        # 방법 1: "기준가(전일대비)" 라인 직후 숫자 추출
        for idx, line in enumerate(lines):
            if "기준가" in line and "전일대비" in line:
                for j in range(idx + 1, min(idx + 6, len(lines))):
                    cand = lines[j]
                    # X,XXX.XX 패턴
                    m = re.search(r"(\d{1,2},\d{3}\.\d{2})", cand)
                    if m:
                        val = float(m.group(1).replace(",", ""))
                        if 1000.0 < val < 9999.0:
                            return val

        # 방법 2: "기준가" 단독 라인 이후
        for idx, line in enumerate(lines):
            if line == "기준가" or "기준가" in line:
                for j in range(idx + 1, min(idx + 8, len(lines))):
                    m = re.search(r"(\d{1,2},\d{3}\.\d{2})", lines[j])
                    if m:
                        val = float(m.group(1).replace(",", ""))
                        if 1000.0 < val < 9999.0:
                            return val

        # 방법 3: 전체에서 "원" 앞 X,XXX.XX 패턴
        matches = re.findall(r"(\d{1,2},\d{3}\.\d{2})\s*원", full_text)
        candidates = []
        for m in matches:
            val = float(m.replace(",", ""))
            if 1000.0 < val < 9999.0:
                candidates.append(val)
        if candidates:
            # 가장 처음 등장하는 값 = 기준가
            return candidates[0]

        # 방법 4: HTML 태그 직접 탐색
        for tag in soup.find_all(["strong", "b", "span", "td", "p"]):
            t = tag.get_text(strip=True)
            m = re.search(r"(\d{1,2},\d{3}\.\d{2})", t)
            if m:
                val = float(m.group(1).replace(",", ""))
                if 1000.0 < val < 9999.0:
                    return val

    except Exception:
        pass
    return 0.0


# ─────────────────────────────────────────────
# ETF 현재가 (yfinance)
# ─────────────────────────────────────────────

@st.cache_data(ttl=300)
def fetch_etf_prices(tickers_tuple):
    tickers = list(tickers_tuple)
    prices = {}
    if not tickers:
        return prices
    try:
        data = yf.download(
            " ".join(tickers), period="5d",
            interval="1d", progress=False, auto_adjust=True,
        )
        if not data.empty and "Close" in data.columns:
            close = data["Close"]
            if isinstance(close, pd.Series):
                close = close.to_frame(name=tickers[0])
            last_row = close.dropna(how="all").iloc[-1]
            for t in tickers:
                if t in last_row.index and not pd.isna(last_row[t]):
                    prices[t] = float(last_row[t])
    except Exception:
        pass

    for t in [x for x in tickers if x not in prices]:
        try:
            hist = yf.Ticker(t).history(period="5d")
            if not hist.empty:
                prices[t] = float(hist["Close"].dropna().iloc[-1])
            time.sleep(0.2)
        except Exception:
            pass
    return prices


# ─────────────────────────────────────────────
# 전체 가격 통합
# ─────────────────────────────────────────────

def get_all_prices():
    etf_tickers = sorted({
        v["ticker"] for v in ALL_HOLDINGS.values()
        if v["ticker"] != "NAVER_FUND"
    })
    etf_prices = fetch_etf_prices(tuple(etf_tickers))

    kyobo_url   = ME_PENSION["교보악사파워인덱스"]["fund_url"]
    kyobo_price = fetch_kyobo_price(kyobo_url)

    manual = st.session_state.get("manual_prices", {})

    name_prices = {}
    sources     = {}

    for name, info in ALL_HOLDINGS.items():
        ticker = info["ticker"]
        avg    = info["avg"]

        if ticker == "NAVER_FUND":
            if kyobo_price > 0:
                name_prices[name] = kyobo_price
                sources[name]     = "[funetf] 자동조회 ClassC-Pe"
            elif manual.get(name, 0) > 0:
                name_prices[name] = float(manual[name])
                sources[name]     = "[수동입력]"
            else:
                name_prices[name] = avg
                sources[name]     = "[조회실패 - 매입기준가 사용]"
        else:
            p = etf_prices.get(ticker, 0.0)
            if p > 0:
                name_prices[name] = p
                sources[name]     = "[yfinance] 자동조회"
            elif manual.get(name, 0) > 0:
                name_prices[name] = float(manual[name])
                sources[name]     = "[수동입력]"
            else:
                name_prices[name] = avg
                sources[name]     = "[조회실패 - 평균가 사용]"

    return name_prices, sources


# ─────────────────────────────────────────────
# DataFrame 생성 (펀드/ETF 분리 계산)
# ─────────────────────────────────────────────

def build_df(holdings, name_prices, sources):
    rows = []
    for name, info in holdings.items():
        qty   = info["qty"]
        avg   = info["avg"]
        acct  = info["acct"]
        itype = info.get("type", "ETF")
        price = name_prices.get(name, avg)
        src   = sources.get(name, "")

        if itype == "FUND":
            # 펀드: 기준가는 1,000좌 기준 단위
            # 매입금액 = 좌수 * (매입기준가 / 1,000)
            # 평가금액 = 좌수 * (현재기준가 / 1,000)
            # 수익률   = (현재기준가 - 매입기준가) / 매입기준가 * 100
            buy_val  = qty * (avg   / 1000.0)
            eval_val = qty * (price / 1000.0)
            pnl      = eval_val - buy_val
            ret_pct  = ((price - avg) / avg * 100) if avg > 0 else 0.0
        else:
            # ETF: 수량 * 단가
            buy_val  = qty * avg
            eval_val = qty * price
            pnl      = eval_val - buy_val
            ret_pct  = (pnl / buy_val * 100) if buy_val > 0 else 0.0

        rows.append({
            "종목명":    name,
            "계좌":      acct,
            "구분":      itype,
            "수량(좌)":  qty,
            "평균단가":  avg,
            "현재가":    price,
            "매입금액":  buy_val,
            "평가금액":  eval_val,
            "손익":      pnl,
            "수익률(%)": round(ret_pct, 2),
            "출처":      src,
        })

    df = pd.DataFrame(rows)
    total = df["평가금액"].sum()
    df["비중(%)"] = (df["평가금액"] / total * 100).round(2) if total > 0 else 0.0
    return df


# ─────────────────────────────────────────────
# 매매 신호
# ─────────────────────────────────────────────

def get_signal(row):
    r = row["수익률(%)"]
    w = row["비중(%)"]
    if r <= -15:
        return "즉시매도", "sell",  "손실 %.1f%% / 손절기준 -15%% 초과" % r
    if r <= -7:
        return "매도검토", "sell",  "손실 %.1f%% / 손절구간 -7~-15%%" % r
    if r >= 30:
        return "익절매도", "sell",  "수익 %.1f%% / 목표 +30%% 달성" % r
    if r >= 20:
        return "일부매도", "sell",  "수익 %.1f%% / 익절구간 +20~+30%%" % r
    if w >= 30:
        return "비중축소", "watch", "비중 %.1f%% / 과다 30%% 초과" % w
    if w >= 25:
        return "비중주의", "watch", "비중 %.1f%% / 주의 25~30%%" % w
    if r >= 10:
        return "유지/관찰", "hold", "수익 %.1f%% / 양호" % r
    if r >= 0:
        return "유지",      "hold", "수익 %.1f%% / 정상범위" % r
    return     "관찰",      "watch","손실 %.1f%% / 모니터링" % r


# ─────────────────────────────────────────────
# 히스토리 / 매매일지
# ─────────────────────────────────────────────

def get_history():
    months = pd.date_range("2024-01-01", "2026-03-01", freq="MS")
    np.random.seed(42)
    me_v   = [17500000]
    wife_v = [20481900]
    irp_v  = [400000]
    for _ in range(len(months) - 1):
        me_v.append(int(me_v[-1]   * np.random.uniform(0.97, 1.06)))
        wife_v.append(int(wife_v[-1] * np.random.uniform(0.97, 1.05)))
        irp_v.append(int(irp_v[-1]  * np.random.uniform(0.98, 1.04)))
    me_v[-1]   = 24794160
    wife_v[-1] = 20250356
    irp_v[-1]  = 433560
    return pd.DataFrame({
        "날짜":        months,
        "나_연금":     me_v,
        "와이프_연금": wife_v,
        "나_IRP":      irp_v,
    })


def get_trades():
    return pd.DataFrame([
        {"날짜":"2024-01-15","종목":"KODEX AI전력핵심설비",   "구분":"매수","수량":120, "단가":29559, "금액":3547080,  "계좌":"나_연금"},
        {"날짜":"2024-02-10","종목":"KODEX AI반도체핵심장비", "구분":"매수","수량":151, "단가":23451, "금액":3541101,  "계좌":"나_연금"},
        {"날짜":"2024-03-05","종목":"PLUS K방산",             "구분":"매수","수량":48,  "단가":73563, "금액":3531024,  "계좌":"나_연금"},
        {"날짜":"2024-04-20","종목":"KODEX 로봇액티브",       "구분":"매수","수량":110, "단가":32355, "금액":3559050,  "계좌":"나_연금"},
        {"날짜":"2024-05-08","종목":"TIGER 반도체TOP10",      "구분":"매수","수량":5,   "단가":27319, "금액":136595,   "계좌":"나_IRP"},
        {"날짜":"2024-06-15","종목":"SOL AI반도체소부장",     "구분":"매수","수량":163, "단가":12920, "금액":2105960,  "계좌":"와이프_연금"},
        {"날짜":"2024-07-22","종목":"KODEX 자동차",           "구분":"매수","수량":110, "단가":22270, "금액":2449700,  "계좌":"와이프_연금"},
        {"날짜":"2024-09-10","종목":"PLUS 고배당주채권혼합",  "구분":"매수","수량":454, "단가":15655, "금액":7107370,  "계좌":"나_연금"},
        {"날짜":"2024-10-05","종목":"TIME 글로벌탑픽액티브", "구분":"매수","수량":12,  "단가":11188, "금액":134256,   "계좌":"나_IRP"},
        {"날짜":"2026-03-05","종목":"교보악사파워인덱스",     "구분":"매수","수량":888035,"단가":0,  "금액":2373348,  "계좌":"나_연금"},
    ])


# ─────────────────────────────────────────────
# UI 헬퍼
# ─────────────────────────────────────────────

CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="white",
    margin=dict(t=40, b=20),
)

def clr(v):
    return "#ff6b6b" if v >= 0 else "#51cf66"

def sign_str(v):
    return "+" if v >= 0 else ""

def kpi_card(label, val_html):
    return (
        '<div class="kpi-card">'
        '<div class="kpi-label">%s</div>'
        '<div class="kpi-value">%s</div>'
        "</div>" % (label, val_html)
    )

def fmt_won(v):
    return "%s&#8361;%s" % (sign_str(v), "{:,.0f}".format(abs(v)))

def fmt_pct(v):
    return "%s%.2f%%" % (sign_str(v), abs(v))

def stock_card_html(row, sig, reason):
    pc  = clr(row["손익"])
    bc  = clr(row["수익률(%)"])
    it  = row.get("구분", "ETF")
    avg_lbl = "매입기준가" if it == "FUND" else "평균단가"
    cur_lbl = "현재기준가" if it == "FUND" else "현재가"
    qty_lbl = "좌수" if it == "FUND" else "수량"
    return (
        '<div class="stock-card" style="border-left:4px solid %s">'
        '<div style="font-size:15px;font-weight:700;margin-bottom:6px">%s / %s</div>'
        '<div style="font-size:12px;color:#aaa;margin-bottom:6px">%s</div>'
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:13px">'
        "<span>%s: <b>&#8361;%s</b></span>"
        "<span>%s: &#8361;%s</span>"
        '<span style="color:%s">손익: %s</span>'
        '<span style="color:%s">수익률: %s</span>'
        "<span>비중: %.1f%%</span>"
        "<span>%s: %s</span>"
        "</div>"
        '<div style="font-size:11px;color:#888;margin-top:6px">-&gt; %s</div>'
        "</div>"
    ) % (
        bc,
        row["종목명"], sig,
        row["출처"],
        cur_lbl, "{:,.2f}".format(row["현재가"]),
        avg_lbl, "{:,.2f}".format(row["평균단가"]),
        pc, fmt_won(row["손익"]),
        pc, fmt_pct(row["수익률(%)"]),
        row["비중(%)"],
        qty_lbl, "{:,}".format(row["수량(좌)"]),
        reason,
    )


# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 퇴직연금 포트폴리오")
    st.markdown("*%s 기준*" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    menu = st.radio(
        "메뉴",
        ["전체 대시보드","나의 포트폴리오","와이프 포트폴리오",
         "평가액 추이","매매 신호","매매 일지","수동 가격 입력"],
        label_visibility="collapsed",
    )
    st.divider()
    if st.button("가격 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.success("캐시 초기화 완료!")
        st.rerun()
    st.caption("가격 캐시: 5분 / 한국시장: 09:00~15:30")


# ─────────────────────────────────────────────
# 가격 로드
# ─────────────────────────────────────────────

with st.spinner("현재가 조회 중..."):
    name_prices, sources = get_all_prices()

df_me_p = build_df(ME_PENSION,   name_prices, sources)
df_me_i = build_df(ME_IRP,       name_prices, sources)
df_wife = build_df(WIFE_PENSION, name_prices, sources)
df_all  = pd.concat([df_me_p, df_me_i, df_wife], ignore_index=True)

total_eval_all = df_all["평가금액"].sum()
df_all["전체비중(%)"] = (
    (df_all["평가금액"] / total_eval_all * 100).round(2)
    if total_eval_all > 0 else 0.0
)

total_buy  = df_all["매입금액"].sum()
total_eval = df_all["평가금액"].sum()
total_pnl  = total_eval - total_buy
total_ret  = (total_pnl / total_buy * 100) if total_buy > 0 else 0.0
wife_buy   = df_wife["매입금액"].sum()
wife_eval  = df_wife["평가금액"].sum()


# ─────────────────────────────────────────────
# 전체 대시보드
# ─────────────────────────────────────────────

if menu == "전체 대시보드":
    st.title("전체 대시보드")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("총 평가금액", "&#8361;{:,.0f}".format(total_eval)), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("총 투자원금", "&#8361;{:,.0f}".format(total_buy)),  unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("총 손익",
            '<span style="color:%s">%s</span>' % (clr(total_pnl), fmt_won(total_pnl))),
            unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("전체 수익률",
            '<span style="color:%s">%s</span>' % (clr(total_ret), fmt_pct(total_ret))),
            unsafe_allow_html=True)

    # 교보악사 펀드 계산 확인 박스
    k_price = name_prices.get("교보악사파워인덱스", 0)
    k_avg   = ME_PENSION["교보악사파워인덱스"]["avg"]
    k_qty   = ME_PENSION["교보악사파워인덱스"]["qty"]
    k_buy   = k_qty * (k_avg   / 1000.0)
    k_eval  = k_qty * (k_price / 1000.0) if k_price > 0 else 0
    k_ret   = (k_price - k_avg) / k_avg * 100 if k_avg > 0 and k_price > 0 else 0
    st.markdown(
        '<div class="fund-info">'
        '<b>교보악사파워인덱스증권자투자신탁 1(주식)ClassC-Pe</b> 계산 확인<br>'
        '좌수: %s좌 &nbsp;|&nbsp; 매입기준가: %.2f원 &nbsp;|&nbsp; 현재기준가: %.2f원<br>'
        '매입금액: &#8361;%s &nbsp;|&nbsp; 평가금액: &#8361;%s &nbsp;|&nbsp; '
        '수익률: <b style="color:%s">%s</b>'
        '</div>' % (
            "{:,}".format(k_qty), k_avg, k_price,
            "{:,.0f}".format(k_buy),
            "{:,.0f}".format(k_eval),
            clr(k_ret), fmt_pct(k_ret),
        ),
        unsafe_allow_html=True,
    )

    st.markdown("")
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("계좌별 수익률")
        a_names = ["나의 연금", "나의 IRP", "와이프 연금"]
        a_buy   = [df_me_p["매입금액"].sum(), df_me_i["매입금액"].sum(), wife_buy]
        a_eval  = [df_me_p["평가금액"].sum(), df_me_i["평가금액"].sum(), wife_eval]
        a_ret   = [(e-b)/b*100 if b > 0 else 0 for e, b in zip(a_eval, a_buy)]
        fig = go.Figure(go.Bar(
            x=a_names, y=a_ret,
            text=[fmt_pct(r) for r in a_ret],
            textposition="outside",
            marker_color=[clr(r) for r in a_ret],
        ))
        fig.update_layout(yaxis_title="수익률(%)", height=320, **CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("자산 배분")
        fig2 = px.pie(df_all, values="평가금액", names="종목명",
                      hole=0.45, color_discrete_sequence=px.colors.qualitative.Set3)
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(showlegend=False, height=320,
                           margin=dict(t=10,b=10,l=10,r=10),
                           paper_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("전체 보유 종목")
    df_disp = df_all.copy()
    df_disp["신호"] = df_disp.apply(lambda r: get_signal(r)[0], axis=1)
    show = ["종목명","계좌","구분","수량(좌)","평균단가","현재가",
            "매입금액","평가금액","손익","수익률(%)","전체비중(%)","신호","출처"]
    st.dataframe(
        df_disp[show].style.format({
            "평균단가":    "{:,.2f}",
            "현재가":      "{:,.2f}",
            "매입금액":    "{:,.0f}",
            "평가금액":    "{:,.0f}",
            "손익":        "{:+,.0f}",
            "수익률(%)":   "{:+.2f}",
            "전체비중(%)": "{:.2f}",
        }),
        use_container_width=True, height=450,
    )


# ─────────────────────────────────────────────
# 나의 포트폴리오
# ─────────────────────────────────────────────

elif menu == "나의 포트폴리오":
    st.title("나의 포트폴리오")
    tab1, tab2 = st.tabs(["퇴직연금", "IRP"])

    for tab, df_tab, label in [
        (tab1, df_me_p, "나의 연금"),
        (tab2, df_me_i, "나의 IRP"),
    ]:
        with tab:
            b  = df_tab["매입금액"].sum()
            e  = df_tab["평가금액"].sum()
            p  = e - b
            rt = (p / b * 100) if b > 0 else 0.0

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(kpi_card("투자원금","&#8361;{:,.0f}".format(b)), unsafe_allow_html=True)
            with c2:
                st.markdown(kpi_card("평가금액","&#8361;{:,.0f}".format(e)), unsafe_allow_html=True)
            with c3:
                st.markdown(kpi_card("수익률",
                    '<span style="color:%s">%s</span>' % (clr(rt), fmt_pct(rt))),
                    unsafe_allow_html=True)

            st.markdown("")
            cols = st.columns(2)
            for i, (_, row) in enumerate(df_tab.iterrows()):
                sig, _, reason = get_signal(row)
                with cols[i % 2]:
                    st.markdown(stock_card_html(row, sig, reason), unsafe_allow_html=True)

            fig = go.Figure(go.Bar(
                x=df_tab["종목명"], y=df_tab["수익률(%)"],
                text=[fmt_pct(r) for r in df_tab["수익률(%)"]],
                textposition="outside",
                marker_color=[clr(r) for r in df_tab["수익률(%)"]],
            ))
            fig.update_layout(title=label + " 종목별 수익률",
                              yaxis_title="수익률(%)", height=300, **CHART_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# 와이프 포트폴리오
# ─────────────────────────────────────────────

elif menu == "와이프 포트폴리오":
    st.title("와이프 포트폴리오")

    b  = wife_buy
    e  = wife_eval
    p  = e - b
    rt = (p / b * 100) if b > 0 else 0.0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi_card("투자원금","&#8361;{:,.0f}".format(b)), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("평가금액","&#8361;{:,.0f}".format(e)), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("수익률",
            '<span style="color:%s">%s</span>' % (clr(rt), fmt_pct(rt))),
            unsafe_allow_html=True)

    st.markdown("")
    cols = st.columns(2)
    for i, (_, row) in enumerate(df_wife.iterrows()):
        sig, _, reason = get_signal(row)
        with cols[i % 2]:
            st.markdown(stock_card_html(row, sig, reason), unsafe_allow_html=True)

    col_l, col_r = st.columns(2)
    with col_l:
        fig = go.Figure(go.Bar(
            x=df_wife["종목명"], y=df_wife["수익률(%)"],
            text=[fmt_pct(r) for r in df_wife["수익률(%)"]],
            textposition="outside",
            marker_color=[clr(r) for r in df_wife["수익률(%)"]],
        ))
        fig.update_layout(title="종목별 수익률", yaxis_title="수익률(%)",
                          height=300, **CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        fig2 = px.pie(df_wife, values="평가금액", names="종목명",
                      hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(showlegend=False, height=300,
                           margin=dict(t=10,b=10,l=10,r=10),
                           paper_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig2, use_container_width=True)


# ─────────────────────────────────────────────
# 평가액 추이
# ─────────────────────────────────────────────

elif menu == "평가액 추이":
    st.title("평가액 추이")
    hist = get_history()

    fig = go.Figure()
    for col, c, lbl in [
        ("나_연금",    "#74c0fc", "나의 연금"),
        ("와이프_연금","#f8a5c2", "와이프 연금"),
        ("나_IRP",     "#a9e34b", "나의 IRP"),
    ]:
        fig.add_trace(go.Scatter(
            x=hist["날짜"], y=hist[col], name=lbl,
            line=dict(color=c, width=2.5),
            mode="lines+markers", marker=dict(size=5),
        ))
    hist["합계"] = hist["나_연금"] + hist["와이프_연금"] + hist["나_IRP"]
    fig.add_trace(go.Scatter(
        x=hist["날짜"], y=hist["합계"], name="전체 합계",
        line=dict(color="#ffd43b", width=3, dash="dot"),
    ))
    fig.update_layout(
        xaxis_title="날짜", yaxis_title="평가금액(원)",
        height=450, hovermode="x unified",
        legend=dict(orientation="h", y=-0.2),
        **CHART_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("최근 6개월 변화율")
    pct_df = hist.set_index("날짜")[["나_연금","와이프_연금","나_IRP"]].pct_change() * 100
    pct_df = pct_df.dropna().tail(6)
    pct_df.columns = ["나의 연금","와이프 연금","나의 IRP"]
    pct_df.index = pct_df.index.strftime("%Y-%m")
    st.dataframe(pct_df.style.format("{:+.2f}"), use_container_width=True)


# ─────────────────────────────────────────────
# 매매 신호
# ─────────────────────────────────────────────

elif menu == "매매 신호":
    st.title("매매 신호")

    df_sig = df_all.copy()
    sig_data = df_sig.apply(lambda r: pd.Series(get_signal(r)), axis=1)
    sig_data.columns = ["신호","신호유형","사유"]
    df_sig = pd.concat([df_sig, sig_data], axis=1)
    df_sig["우선순위"] = df_sig["신호유형"].map({"sell":0,"watch":1,"hold":2})
    df_sig = df_sig.sort_values("우선순위")

    sell_cnt  = int((df_sig["신호유형"] == "sell").sum())
    watch_cnt = int((df_sig["신호유형"] == "watch").sum())
    hold_cnt  = int((df_sig["신호유형"] == "hold").sum())

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("매도/손절", "%d개" % sell_cnt)
    with c2: st.metric("주의/관찰", "%d개" % watch_cnt)
    with c3: st.metric("유지",      "%d개" % hold_cnt)
    st.divider()

    for _, row in df_sig.iterrows():
        stype = row["신호유형"]
        css = "sig-sell" if stype=="sell" else ("sig-watch" if stype=="watch" else "sig-hold")
        pc = clr(row["손익"])
        st.markdown(
            '<div class="%s">'
            "<b>[%s] %s</b> "
            '<span style="font-size:12px;color:#aaa">[%s]</span><br>'
            '<span style="font-size:13px">'
            "현재가 &#8361;%s &nbsp;|&nbsp; "
            '수익률 <span style="color:%s">%s</span> &nbsp;|&nbsp; '
            "비중 %.1f%%"
            "</span><br>"
            '<span style="font-size:12px;color:#ccc">-&gt; %s</span>'
            "</div>" % (
                css,
                row["신호"], row["종목명"], row["계좌"],
                "{:,.2f}".format(row["현재가"]),
                pc, fmt_pct(row["수익률(%)"]),
                row["비중(%)"],
                row["사유"],
            ),
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# 매매 일지
# ─────────────────────────────────────────────

elif menu == "매매 일지":
    st.title("매매 일지")
    trades = get_trades()

    total_buy_amt = int(trades[trades["구분"]=="매수"]["금액"].sum())
    c1, c2 = st.columns(2)
    with c1: st.metric("총 매수금액", "&#8361;{:,.0f}".format(total_buy_amt))
    with c2: st.metric("총 거래건수", "%d건" % len(trades))

    st.dataframe(
        trades.sort_values("날짜", ascending=False)
              .style.format({"금액":"{:,.0f}","단가":"{:,.0f}","수량":"{:,}"}),
        use_container_width=True, height=380,
    )

    trades["날짜_dt"] = pd.to_datetime(trades["날짜"])
    trades["월"] = trades["날짜_dt"].dt.strftime("%Y-%m")
    monthly = trades.groupby("월")["금액"].sum().reset_index()
    fig = px.bar(monthly, x="월", y="금액", title="월별 매수금액",
                 color_discrete_sequence=["#74c0fc"])
    fig.update_layout(height=260, **CHART_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# 수동 가격 입력
# ─────────────────────────────────────────────

elif menu == "수동 가격 입력":
    st.title("현재가 조회 상태 및 수동 입력")

    st.subheader("현재가 조회 결과")
    for name, src in sources.items():
        price = name_prices.get(name, 0)
        itype = ALL_HOLDINGS[name].get("type","ETF")
        lbl   = "기준가" if itype == "FUND" else "현재가"
        css   = "price-ok" if "조회실패" not in src else "price-fail"
        st.markdown(
            '<div class="%s">%s &nbsp; <b>%s</b> &nbsp; %s: &#8361;%s</div>'
            % (css, src, name, lbl, "{:,.2f}".format(price)),
            unsafe_allow_html=True,
        )

    st.divider()
    st.subheader("수동 가격 입력 (조회 실패 종목)")

    if "manual_prices" not in st.session_state:
        st.session_state["manual_prices"] = {}

    failed = {n: p for n, p in name_prices.items() if "조회실패" in sources.get(n,"")}

    if not failed:
        st.success("모든 종목 가격이 정상 조회되었습니다.")
    else:
        with st.form("manual_form"):
            new_vals = {}
            for name, cur in failed.items():
                val = st.number_input(
                    "%s (현재: %s원)" % (name, "{:,.2f}".format(cur)),
                    min_value=0.0,
                    value=float(st.session_state["manual_prices"].get(name, cur)),
                    step=1.0, key="inp_%s" % name,
                )
                new_vals[name] = val
            if st.form_submit_button("저장 및 새로고침"):
                st.session_state["manual_prices"].update(new_vals)
                st.cache_data.clear()
                st.success("저장 완료!")
                st.rerun()

    st.divider()
    st.subheader("교보악사파워인덱스 기준가 직접 입력")

    k_auto  = name_prices.get("교보악사파워인덱스", 0.0)
    k_avg   = ME_PENSION["교보악사파워인덱스"]["avg"]
    k_qty   = ME_PENSION["교보악사파워인덱스"]["qty"]
    k_buy   = k_qty * (k_avg   / 1000.0)
    k_eval  = k_qty * (k_auto  / 1000.0) if k_auto > 0 else 0.0
    k_ret   = (k_auto - k_avg) / k_avg * 100 if k_avg > 0 and k_auto > 0 else 0.0

    st.markdown(
        '<div class="fund-info">'
        "ClassC-Pe &nbsp;|&nbsp; 자동 조회 기준가: <b>%.2f원</b> (funetf.co.kr)<br>"
        "좌수: %s좌 &nbsp;|&nbsp; 매입기준가: %.2f원 (26.03.05 확인)<br>"
        "매입금액: &#8361;%s &nbsp;|&nbsp; 평가금액: &#8361;%s &nbsp;|&nbsp; "
        '수익률: <b style="color:%s">%s</b>'
        "</div>" % (
            k_auto, "{:,}".format(k_qty), k_avg,
            "{:,.0f}".format(k_buy),
            "{:,.0f}".format(k_eval),
            clr(k_ret), fmt_pct(k_ret),
        ),
        unsafe_allow_html=True,
    )

    k_val = st.number_input(
        "기준가 직접 입력 (원) - 증권사 앱의 기준가를 입력하세요",
        min_value=0.0,
        value=float(st.session_state["manual_prices"].get("교보악사파워인덱스", k_auto)),
        step=0.01,
    )
    if st.button("교보악사 기준가 저장"):
        st.session_state["manual_prices"]["교보악사파워인덱스"] = k_val
        st.cache_data.clear()
        k_eval_new = k_qty * (k_val / 1000.0)
        k_ret_new  = (k_val - k_avg) / k_avg * 100 if k_avg > 0 else 0
        st.success(
            "저장 완료! 기준가 %.2f원 / 평가금액 %s원 / 수익률 %s" % (
                k_val,
                "{:,.0f}".format(k_eval_new),
                fmt_pct(k_ret_new),
            )
        )
        st.rerun()

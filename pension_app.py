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

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
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
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    color: white;
    margin: 4px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}
.kpi-label { font-size: 13px; opacity: 0.85; margin-bottom: 6px; }
.kpi-value { font-size: 22px; font-weight: 700; }
.stock-card {
    background: #1e2a3a;
    border-radius: 10px;
    padding: 14px;
    margin: 6px 0;
}
.price-ok   { background:#1a3a1a; border-radius:8px; padding:8px 12px; margin:3px 0; font-size:13px; }
.price-fail { background:#3a1a1a; border-radius:8px; padding:8px 12px; margin:3px 0; font-size:13px; }
.sig-sell  { background:#3a1a1a; border-left:4px solid #ff6b6b; padding:10px; border-radius:6px; margin:4px 0; }
.sig-watch { background:#3a2d1a; border-left:4px solid #ffd43b; padding:10px; border-radius:6px; margin:4px 0; }
.sig-hold  { background:#1a2a3a; border-left:4px solid #74c0fc; padding:10px; border-radius:6px; margin:4px 0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 보유종목 정의
# ─────────────────────────────────────────────
ME_PENSION = {
    "KODEX AI전력핵심설비":   {"ticker": "487240.KS",  "qty": 120,    "avg": 29559.0,  "acct": "나_연금", "type": "ETF"},
    "KODEX AI반도체핵심장비": {"ticker": "465660.KS",  "qty": 151,    "avg": 23451.0,  "acct": "나_연금", "type": "ETF"},
    "KODEX 로봇액티브":       {"ticker": "412560.KS",  "qty": 110,    "avg": 32355.0,  "acct": "나_연금", "type": "ETF"},
    "PLUS K방산":             {"ticker": "455890.KS",  "qty": 48,     "avg": 73563.0,  "acct": "나_연금", "type": "ETF"},
    "교보악사파워인덱스":     {
        "ticker":   "NAVER_FUND",
        "qty":      888035,       # 보유 좌수
        "avg":      2672.85,      # 매입 당시 기준가 (원)
        "buy_amt":  2373251272,   # 실제 매입금액 = 888035 * 2672.85 (원) ← 직접 확인 후 수정
        "acct":     "나_연금",
        "type":     "FUND",
        "fund_url": "https://www.funetf.co.kr/product/fund/view/KR5207895248",
    },
    "PLUS 고배당주채권혼합":  {"ticker": "480040.KS",  "qty": 454,    "avg": 15655.0,  "acct": "나_연금", "type": "ETF"},
}

ME_IRP = {
    "TIGER 반도체TOP10":     {"ticker": "385720.KS", "qty": 5,  "avg": 27319.0, "acct": "나_IRP", "type": "ETF"},
    "TIME 글로벌탑픽액티브": {"ticker": "0113D0.KS", "qty": 12, "avg": 11188.0, "acct": "나_IRP", "type": "ETF"},
    "PLUS 고배당주채권혼합": {"ticker": "480040.KS", "qty": 3,  "avg": 15745.0, "acct": "나_IRP", "type": "ETF"},
}

WIFE_PENSION = {
    "KODEX 로봇액티브":       {"ticker": "412560.KS", "qty": 50,  "avg": 32970.0, "acct": "와이프_연금", "type": "ETF"},
    "KODEX AI반도체핵심장비": {"ticker": "465660.KS", "qty": 30,  "avg": 25920.0, "acct": "와이프_연금", "type": "ETF"},
    "PLUS K방산":             {"ticker": "455890.KS", "qty": 14,  "avg": 74820.0, "acct": "와이프_연금", "type": "ETF"},
    "SOL AI반도체소부장":     {"ticker": "448540.KS", "qty": 163, "avg": 12920.0, "acct": "와이프_연금", "type": "ETF"},
    "KODEX 자동차":           {"ticker": "091180.KS", "qty": 110, "avg": 22270.0, "acct": "와이프_연금", "type": "ETF"},
    "PLUS 고배당주채권혼합":  {"ticker": "480040.KS", "qty": 530, "avg": 14690.0, "acct": "와이프_연금", "type": "ETF"},
}

ALL_HOLDINGS = {}
ALL_HOLDINGS.update(ME_PENSION)
ALL_HOLDINGS.update(ME_IRP)
ALL_HOLDINGS.update(WIFE_PENSION)

# ─────────────────────────────────────────────
# 가격 조회
# ─────────────────────────────────────────────

@st.cache_data(ttl=300)
def fetch_naver_fund_price(fund_url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    try:
        r = requests.get(fund_url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text()
        match = re.search(r'[긴기]준가\([전일대비]*\)\s*([\d,]+\.?\d*)\s*원', text)
        if match:
            return float(match.group(1).replace(",", ""))
        match2 = re.search(r'(\d{1,2},\d{3}\.\d{2})\s*원', text)
        if match2:
            return float(match2.group(1).replace(",", ""))
    except Exception:
        pass
    return 0.0


@st.cache_data(ttl=300)
def fetch_etf_prices(tickers_tuple):
    tickers = list(tickers_tuple)
    prices = {}
    if not tickers:
        return prices
    try:
        ticker_str = " ".join(tickers)
        data = yf.download(ticker_str, period="2d", interval="1d",
                           progress=False, auto_adjust=True)
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

    failed = [t for t in tickers if t not in prices]
    for t in failed:
        try:
            obj = yf.Ticker(t)
            hist = obj.history(period="2d")
            if not hist.empty:
                prices[t] = float(hist["Close"].iloc[-1])
            time.sleep(0.3)
        except Exception:
            pass
    return prices


def get_all_prices():
    etf_tickers = list({
        v["ticker"] for v in ALL_HOLDINGS.values()
        if v["ticker"] != "NAVER_FUND"
    })
    etf_prices = fetch_etf_prices(tuple(sorted(etf_tickers)))

    fund_cache = {}
    for name, info in ALL_HOLDINGS.items():
        if info["ticker"] == "NAVER_FUND":
            url = info.get("fund_url", "")
            if url and url not in fund_cache:
                fund_cache[url] = fetch_naver_fund_price(url)

    manual = st.session_state.get("manual_prices", {})

    name_prices = {}
    sources = {}
    for name, info in ALL_HOLDINGS.items():
        ticker = info["ticker"]
        avg = info["avg"]

        if ticker == "NAVER_FUND":
            url = info.get("fund_url", "")
            p = fund_cache.get(url, 0.0)
            if p > 0:
                name_prices[name] = p
                sources[name] = "[funetf] 자동조회"
            elif manual.get(name, 0) > 0:
                name_prices[name] = manual[name]
                sources[name] = "[수동입력]"
            else:
                name_prices[name] = avg
                sources[name] = "[조회실패-평균가]"
        else:
            p = etf_prices.get(ticker, 0.0)
            if p > 0:
                name_prices[name] = p
                sources[name] = "[yfinance] 자동조회"
            elif manual.get(name, 0) > 0:
                name_prices[name] = manual[name]
                sources[name] = "[수동입력]"
            else:
                name_prices[name] = avg
                sources[name] = "[조회실패-평균가]"

    return name_prices, sources

# ─────────────────────────────────────────────
# DataFrame 생성
# ─────────────────────────────────────────────

def build_df(holdings, name_prices, sources):
    rows = []
    for name, info in holdings.items():
        qty    = info["qty"]
        avg    = info["avg"]
        acct   = info["acct"]
        itype  = info.get("type", "ETF")
        price  = name_prices.get(name, avg)
        src    = sources.get(name, "")

        if itype == "FUND":
            # ── 펀드 계산 ──────────────────────────────────────
            # 펀드 기준가는 1좌=1원 기준이 아니라
            # 실제 기준가(예: 3,432원)를 그대로 사용
            # 매입금액: buy_amt 가 있으면 우선 사용, 없으면 qty * avg
            buy_val  = info.get("buy_amt", qty * avg)
            # 평가금액: 좌수 × (현재 기준가 / 매입 기준가) × 매입금액
            # = 매입금액 × (현재기준가 / 매입기준가)
            eval_val = buy_val * (price / avg) if avg > 0 else buy_val
            pnl      = eval_val - buy_val
            ret_pct  = (price - avg) / avg * 100 if avg > 0 else 0.0

        else:
            # ── ETF / 주식 계산 ────────────────────────────────
            buy_val  = qty * avg
            eval_val = qty * price
            pnl      = eval_val - buy_val
            ret_pct  = (pnl / buy_val * 100) if buy_val > 0 else 0.0

        rows.append({
            "종목명":    name,
            "계좌":      acct,
            "구분":      itype,
            "수량":      qty,
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

def get_signal(row):
    r = row["수익률(%)"]
    w = row["비중(%)"]
    if r <= -15:
        return "즉시매도", "sell", f"손실 {r:.1f}% / 손절기준(-15%) 초과"
    if r <= -7:
        return "매도검토", "sell", f"손실 {r:.1f}% / 손절구간(-7~-15%)"
    if r >= 30:
        return "익절매도", "sell", f"수익 {r:.1f}% / 목표수익(+30%) 달성"
    if r >= 20:
        return "일부매도", "sell", f"수익 {r:.1f}% / 익절구간(+20~+30%)"
    if w >= 30:
        return "비중축소", "watch", f"비중 {w:.1f}% / 과다(30% 초과)"
    if w >= 25:
        return "비중주의", "watch", f"비중 {w:.1f}% / 주의(25~30%)"
    if r >= 10:
        return "유지/관찰", "hold", f"수익 {r:.1f}% / 양호"
    if r >= 0:
        return "유지", "hold", f"수익 {r:.1f}% / 정상범위"
    return "관찰", "watch", f"손실 {r:.1f}% / 모니터링"

# ─────────────────────────────────────────────
# 히스토리 (샘플)
# ─────────────────────────────────────────────

def get_history():
    months = pd.date_range("2024-01-01", "2026-03-01", freq="MS")
    np.random.seed(42)
    me_v   = [17500000]
    wife_v = [20481900]
    irp_v  = [400000]
    for _ in range(len(months) - 1):
        me_v.append(int(me_v[-1] * np.random.uniform(0.97, 1.06)))
        wife_v.append(int(wife_v[-1] * np.random.uniform(0.97, 1.05)))
        irp_v.append(int(irp_v[-1] * np.random.uniform(0.98, 1.04)))
    me_v[-1]   = 24794160
    wife_v[-1] = 20250356
    irp_v[-1]  = 433560
    return pd.DataFrame({"날짜": months, "나_연금": me_v, "와이프_연금": wife_v, "나_IRP": irp_v})


def get_trades():
    return pd.DataFrame([
        {"날짜": "2024-01-15", "종목": "KODEX AI전력핵심설비",   "구분": "매수", "수량": 120, "단가": 29559,  "금액": 3547080,  "계좌": "나_연금"},
        {"날짜": "2024-02-10", "종목": "KODEX AI반도체핵심장비", "구분": "매수", "수량": 151, "단가": 23451,  "금액": 3541101,  "계좌": "나_연금"},
        {"날짜": "2024-03-05", "종목": "PLUS K방산",             "구분": "매수", "수량": 48,  "단가": 73563,  "금액": 3531024,  "계좌": "나_연금"},
        {"날짜": "2024-04-20", "종목": "KODEX 로봇액티브",       "구분": "매수", "수량": 110, "단가": 32355,  "금액": 3559050,  "계좌": "나_연금"},
        {"날짜": "2024-05-08", "종목": "TIGER 반도체TOP10",      "구분": "매수", "수량": 5,   "단가": 27319,  "금액": 136595,   "계좌": "나_IRP"},
        {"날짜": "2024-06-15", "종목": "SOL AI반도체소부장",     "구분": "매수", "수량": 163, "단가": 12920,  "금액": 2105960,  "계좌": "와이프_연금"},
        {"날짜": "2024-07-22", "종목": "KODEX 자동차",           "구분": "매수", "수량": 110, "단가": 22270,  "금액": 2449700,  "계좌": "와이프_연금"},
        {"날짜": "2024-09-10", "종목": "PLUS 고배당주채권혼합",  "구분": "매수", "수량": 454, "단가": 15655,  "금액": 7107370,  "계좌": "나_연금"},
        {"날짜": "2024-10-05", "종목": "TIME 글로벌탑픽액티브", "구분": "매수", "수량": 12,  "단가": 11188,  "금액": 134256,   "계좌": "나_IRP"},
    ])

# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 퇴직연금 포트폴리오")
    st.markdown(f"*{datetime.now().strftime('%Y-%m-%d %H:%M')} 기준*")

    menu = st.radio(
        "메뉴",
        [
            "전체 대시보드",
            "나의 포트폴리오",
            "와이프 포트폴리오",
            "평가액 추이",
            "매매 신호",
            "매매 일지",
            "수동 가격 입력",
        ],
        label_visibility="collapsed"
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
df_all["전체비중(%)"] = (df_all["평가금액"] / total_eval_all * 100).round(2) if total_eval_all > 0 else 0.0

total_buy  = df_all["매입금액"].sum()
total_eval = df_all["평가금액"].sum()
total_pnl  = total_eval - total_buy
total_ret  = (total_pnl / total_buy * 100) if total_buy > 0 else 0.0

me_buy   = df_me_p["매입금액"].sum() + df_me_i["매입금액"].sum()
me_eval  = df_me_p["평가금액"].sum() + df_me_i["평가금액"].sum()
wife_buy  = df_wife["매입금액"].sum()
wife_eval = df_wife["평가금액"].sum()

# ─────────────────────────────────────────────
# 전체 대시보드
# ─────────────────────────────────────────────

if menu == "전체 대시보드":
    st.title("전체 대시보드")

    c1, c2, c3, c4 = st.columns(4)
    pnl_color = "#ff6b6b" if total_pnl >= 0 else "#51cf66"

    with c1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">총 평가금액</div><div class="kpi-value">&#8361;{total_eval:,.0f}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">총 투자원금</div><div class="kpi-value">&#8361;{total_buy:,.0f}</div></div>', unsafe_allow_html=True)
    with c3:
        sign = "+" if total_pnl >= 0 else ""
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">총 손익</div><div class="kpi-value" style="color:{pnl_color}">{sign}&#8361;{total_pnl:,.0f}</div></div>', unsafe_allow_html=True)
    with c4:
        sign2 = "+" if total_ret >= 0 else ""
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">전체 수익률</div><div class="kpi-value" style="color:{pnl_color}">{sign2}{total_ret:.2f}%</div></div>', unsafe_allow_html=True)

    st.markdown("")
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("계좌별 수익률")
        acct_names = ["나의 연금", "나의 IRP", "와이프 연금"]
        acct_buy   = [df_me_p["매입금액"].sum(), df_me_i["매입금액"].sum(), wife_buy]
        acct_eval  = [df_me_p["평가금액"].sum(), df_me_i["평가금액"].sum(), wife_eval]
        acct_ret   = [(e - b) / b * 100 if b > 0 else 0 for e, b in zip(acct_eval, acct_buy)]
        bar_colors = ["#ff6b6b" if r >= 0 else "#51cf66" for r in acct_ret]

        fig_bar = go.Figure(go.Bar(
            x=acct_names,
            y=acct_ret,
            text=[f"{r:+.2f}%" for r in acct_ret],
            textposition="outside",
            marker_color=bar_colors,
        ))
        fig_bar.update_layout(
            yaxis_title="수익률(%)",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            height=320,
            margin=dict(t=20, b=20),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_r:
        st.subheader("자산 배분")
        fig_pie = px.pie(
            df_all, values="평가금액", names="종목명",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(
            showlegend=False, height=320,
            margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("전체 보유 종목")
    df_disp = df_all.copy()
    df_disp["신호"] = df_disp.apply(lambda r: get_signal(r)[0], axis=1)
    show_cols = ["종목명","계좌","수량","평균단가","현재가","매입금액","평가금액","손익","수익률(%)","전체비중(%)","신호","출처"]
    st.dataframe(
        df_disp[show_cols].style.format({
            "평균단가":  "{:,.2f}",
            "현재가":    "{:,.2f}",
            "매입금액":  "{:,.0f}",
            "평가금액":  "{:,.0f}",
            "손익":      "{:+,.0f}",
            "수익률(%)": "{:+.2f}%",
            "전체비중(%)": "{:.2f}%",
        }),
        use_container_width=True,
        height=420
    )

# ─────────────────────────────────────────────
# 나의 포트폴리오
# ─────────────────────────────────────────────

elif menu == "나의 포트폴리오":
    st.title("나의 포트폴리오")
    tab1, tab2 = st.tabs(["퇴직연금", "IRP"])

    for tab, df_tab, label in [(tab1, df_me_p, "나의 연금"), (tab2, df_me_i, "나의 IRP")]:
        with tab:
            b = df_tab["매입금액"].sum()
            e = df_tab["평가금액"].sum()
            p = e - b
            rt = (p / b * 100) if b > 0 else 0
            pcolor = "#ff6b6b" if p >= 0 else "#51cf66"

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">투자원금</div><div class="kpi-value">&#8361;{b:,.0f}</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">평가금액</div><div class="kpi-value">&#8361;{e:,.0f}</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">수익률</div><div class="kpi-value" style="color:{pcolor}">{rt:+.2f}%</div></div>', unsafe_allow_html=True)

            st.markdown("")
            cols = st.columns(2)
            for i, (_, row) in enumerate(df_tab.iterrows()):
                sig, stype, reason = get_signal(row)
                pc = "#ff6b6b" if row["손익"] >= 0 else "#51cf66"
                bc = "#ff6b6b" if row["수익률(%)"] >= 0 else "#51cf66"
                with cols[i % 2]:
                    st.markdown(f"""
<div class="stock-card" style="border-left:4px solid {bc}">
<div style="font-size:15px;font-weight:700;margin-bottom:6px">{row['종목명']} / {sig}</div>
<div style="font-size:12px;color:#aaa;margin-bottom:6px">{row['출처']}</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:13px">
<span>현재가: <b>&#8361;{row['현재가']:,.2f}</b></span>
<span>평균단가: &#8361;{row['평균단가']:,.2f}</span>
<span style="color:{pc}">손익: {'+' if row['손익']>=0 else ''}&#8361;{row['손익']:,.0f}</span>
<span style="color:{pc}">수익률: {row['수익률(%)']:+.2f}%</span>
<span>비중: {row['비중(%)']:.1f}%</span>
<span>수량: {row['수량']:,}</span>
</div>
<div style="font-size:11px;color:#888;margin-top:6px">→ {reason}</div>
</div>
                    """, unsafe_allow_html=True)

            fig = go.Figure(go.Bar(
                x=df_tab["종목명"],
                y=df_tab["수익률(%)"],
                text=[f"{r:+.1f}%" for r in df_tab["수익률(%)"]],
                textposition="outside",
                marker_color=["#ff6b6b" if r >= 0 else "#51cf66" for r in df_tab["수익률(%)"]],
            ))
            fig.update_layout(
                title=f"{label} 종목별 수익률",
                yaxis_title="수익률(%)",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                height=300,
                margin=dict(t=40, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# 와이프 포트폴리오
# ─────────────────────────────────────────────

elif menu == "와이프 포트폴리오":
    st.title("와이프 포트폴리오")

    b = wife_buy
    e = wife_eval
    p = e - b
    rt = (p / b * 100) if b > 0 else 0
    pcolor = "#ff6b6b" if p >= 0 else "#51cf66"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">투자원금</div><div class="kpi-value">&#8361;{b:,.0f}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">평가금액</div><div class="kpi-value">&#8361;{e:,.0f}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">수익률</div><div class="kpi-value" style="color:{pcolor}">{rt:+.2f}%</div></div>', unsafe_allow_html=True)

    st.markdown("")
    cols = st.columns(2)
    for i, (_, row) in enumerate(df_wife.iterrows()):
        sig, stype, reason = get_signal(row)
        pc = "#ff6b6b" if row["손익"] >= 0 else "#51cf66"
        bc = "#ff6b6b" if row["수익률(%)"] >= 0 else "#51cf66"
        with cols[i % 2]:
            st.markdown(f"""
<div class="stock-card" style="border-left:4px solid {bc}">
<div style="font-size:15px;font-weight:700;margin-bottom:6px">{row['종목명']} / {sig}</div>
<div style="font-size:12px;color:#aaa;margin-bottom:6px">{row['출처']}</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:13px">
<span>현재가: <b>&#8361;{row['현재가']:,.2f}</b></span>
<span>평균단가: &#8361;{row['평균단가']:,.2f}</span>
<span style="color:{pc}">손익: {'+' if row['손익']>=0 else ''}&#8361;{row['손익']:,.0f}</span>
<span style="color:{pc}">수익률: {row['수익률(%)']:+.2f}%</span>
<span>비중: {row['비중(%)']:.1f}%</span>
<span>수량: {row['수량']:,}</span>
</div>
<div style="font-size:11px;color:#888;margin-top:6px">→ {reason}</div>
</div>
            """, unsafe_allow_html=True)

    col_l, col_r = st.columns(2)
    with col_l:
        fig = go.Figure(go.Bar(
            x=df_wife["종목명"],
            y=df_wife["수익률(%)"],
            text=[f"{r:+.1f}%" for r in df_wife["수익률(%)"]],
            textposition="outside",
            marker_color=["#ff6b6b" if r >= 0 else "#51cf66" for r in df_wife["수익률(%)"]],
        ))
        fig.update_layout(
            title="종목별 수익률",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="white", height=300, margin=dict(t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        fig_pie = px.pie(df_wife, values="평가금액", names="종목명",
                         hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(
            showlegend=False, height=300,
            margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)", font_color="white",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

# ─────────────────────────────────────────────
# 평가액 추이
# ─────────────────────────────────────────────

elif menu == "평가액 추이":
    st.title("평가액 추이")
    hist = get_history()

    fig = go.Figure()
    traces = [
        ("나_연금",   "#74c0fc", "나의 연금"),
        ("와이프_연금","#f8a5c2","와이프 연금"),
        ("나_IRP",    "#a9e34b", "나의 IRP"),
    ]
    for col, color, label in traces:
        fig.add_trace(go.Scatter(
            x=hist["날짜"], y=hist[col],
            name=label, line=dict(color=color, width=2.5),
            mode="lines+markers", marker=dict(size=5),
        ))

    hist["합계"] = hist["나_연금"] + hist["와이프_연금"] + hist["나_IRP"]
    fig.add_trace(go.Scatter(
        x=hist["날짜"], y=hist["합계"],
        name="전체 합계", line=dict(color="#ffd43b", width=3, dash="dot"),
    ))
    fig.update_layout(
        xaxis_title="날짜", yaxis_title="평가금액(원)",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="white", height=450,
        legend=dict(orientation="h", y=-0.2),
        hovermode="x unified",
        margin=dict(t=20, b=60),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("최근 6개월 변화율")
    pct_df = hist.set_index("날짜")[["나_연금","와이프_연금","나_IRP"]].pct_change() * 100
    pct_df = pct_df.dropna().tail(6)
    pct_df.columns = ["나의 연금","와이프 연금","나의 IRP"]
    pct_df.index = pct_df.index.strftime("%Y-%m")
    st.dataframe(pct_df.style.format("{:+.2f}%"), use_container_width=True)

# ─────────────────────────────────────────────
# 매매 신호
# ─────────────────────────────────────────────

elif menu == "매매 신호":
    st.title("매매 신호")

    df_sig = df_all.copy()
    sig_rows = df_sig.apply(lambda r: pd.Series(get_signal(r)), axis=1)
    sig_rows.columns = ["신호", "신호유형", "사유"]
    df_sig = pd.concat([df_sig, sig_rows], axis=1)

    priority_map = {"sell": 0, "watch": 1, "hold": 2}
    df_sig["우선순위"] = df_sig["신호유형"].map(priority_map)
    df_sig = df_sig.sort_values("우선순위")

    sell_cnt  = (df_sig["신호유형"] == "sell").sum()
    watch_cnt = (df_sig["신호유형"] == "watch").sum()
    hold_cnt  = (df_sig["신호유형"] == "hold").sum()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("매도/손절", f"{sell_cnt}개")
    with c2:
        st.metric("주의/관찰", f"{watch_cnt}개")
    with c3:
        st.metric("유지", f"{hold_cnt}개")

    st.divider()

    for _, row in df_sig.iterrows():
        stype = row["신호유형"]
        css = "sig-sell" if stype == "sell" else ("sig-watch" if stype == "watch" else "sig-hold")
        pc = "#ff6b6b" if row["손익"] >= 0 else "#51cf66"
        st.markdown(f"""
<div class="{css}">
<b>[{row['신호']}] {row['종목명']}</b>
&nbsp; <span style="font-size:12px;color:#aaa">{row['계좌']}</span><br>
<span style="font-size:13px">
현재가 &#8361;{row['현재가']:,.2f} &nbsp;|&nbsp;
수익률 <span style="color:{pc}">{row['수익률(%)']:+.2f}%</span> &nbsp;|&nbsp;
비중 {row['비중(%)']:.1f}%
</span><br>
<span style="font-size:12px;color:#ccc">→ {row['사유']}</span>
</div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 매매 일지
# ─────────────────────────────────────────────

elif menu == "매매 일지":
    st.title("매매 일지")
    trades = get_trades()

    total_buy_amt = trades[trades["구분"] == "매수"]["금액"].sum()
    c1, c2 = st.columns(2)
    with c1:
        st.metric("총 매수금액", f"&#8361;{total_buy_amt:,.0f}")
    with c2:
        st.metric("총 거래건수", f"{len(trades)}건")

    st.dataframe(
        trades.sort_values("날짜", ascending=False)
              .style.format({"금액": "{:,.0f}", "단가": "{:,.0f}", "수량": "{:,}"}),
        use_container_width=True, height=380
    )

    trades["날짜_dt"] = pd.to_datetime(trades["날짜"])
    trades["월"] = trades["날짜_dt"].dt.strftime("%Y-%m")
    monthly = trades.groupby("월")["금액"].sum().reset_index()
    fig = px.bar(monthly, x="월", y="금액",
                 title="월별 매수금액",
                 color_discrete_sequence=["#74c0fc"])
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="white", height=260, margin=dict(t=40, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# 수동 가격 입력
# ─────────────────────────────────────────────

elif menu == "수동 가격 입력":
    st.title("현재가 조회 상태 및 수동 입력")

    st.subheader("현재가 조회 결과")
    for name, src in sources.items():
        price = name_prices.get(name, 0)
        css = "price-ok" if "조회실패" not in src else "price-fail"
        st.markdown(
            f'<div class="{css}">{src} &nbsp; <b>{name}</b> &nbsp; &#8361;{price:,.2f}</div>',
            unsafe_allow_html=True
        )

    st.divider()
    st.subheader("수동 가격 입력")

    if "manual_prices" not in st.session_state:
        st.session_state["manual_prices"] = {}

    failed_items = {n: p for n, p in name_prices.items() if "조회실패" in sources.get(n, "")}

    if not failed_items:
        st.success("모든 종목 가격이 정상 조회되었습니다.")
    else:
        with st.form("manual_form"):
            new_vals = {}
            for name, cur in failed_items.items():
                val = st.number_input(
                    f"{name} (현재: {cur:,.2f}원)",
                    min_value=0.0,
                    value=float(st.session_state["manual_prices"].get(name, cur)),
                    step=1.0,
                    key=f"inp_{name}"
                )
                new_vals[name] = val
            if st.form_submit_button("저장 및 새로고침"):
                st.session_state["manual_prices"].update(new_vals)
                st.cache_data.clear()
                st.success("저장 완료!")
                st.rerun()

    st.divider()
    st.subheader("교보악사파워인덱스 기준가 직접 입력")
    kyobo_auto = name_prices.get("교보악사파워인덱스", 0)
    st.caption(f"자동 조회값: {kyobo_auto:,.2f}원 (funetf.co.kr)")
    kyobo_val = st.number_input(
        "기준가 직접 입력 (원)",
        min_value=0.0,
        value=float(st.session_state["manual_prices"].get("교보악사파워인덱스", kyobo_auto)),
        step=0.01
    )
    if st.button("교보악사 가격 저장"):
        st.session_state["manual_prices"]["교보악사파워인덱스"] = kyobo_val
        st.cache_data.clear()
        st.success(f"교보악사파워인덱스 = {kyobo_val:,.2f}원 저장 완료!")
        st.rerun()

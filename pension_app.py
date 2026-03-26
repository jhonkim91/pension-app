import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
import yfinance as yf
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
#  ETF 종목 정보 (보유수량 + 평균매입가)
# ══════════════════════════════════════════════
# 나 퇴직연금
ME_PENSION_HOLDINGS = {
    "KODEX AI전력핵심설비":  {"ticker":"451340.KS","qty":120, "avg":29559,"acct":"나_연금"},
    "KODEX AI반도체핵심장비":{"ticker":"465660.KS","qty":151, "avg":23451,"acct":"나_연금"},
    "KODEX 로봇액티브":      {"ticker":"412560.KS","qty":110, "avg":32355,"acct":"나_연금"},
    "PLUS K방산":            {"ticker":"455890.KS","qty":48,  "avg":73563,"acct":"나_연금"},
    "교보악사파워인덱스":     {"ticker":"MANUAL",  "qty":888035,"avg":2672.85,"acct":"나_연금"},
    "PLUS 고배당주채권혼합":  {"ticker":"480040.KS","qty":454, "avg":15655,"acct":"나_연금"},
}

# 나 IRP
ME_IRP_HOLDINGS = {
    "TIGER 반도체TOP10":    {"ticker":"385720.KS","qty":5,  "avg":27319,"acct":"나_IRP"},
    "TIME 글로벌탑픽액티브":{"ticker":"476290.KQ","qty":12, "avg":11188,"acct":"나_IRP"},
    "PLUS 고배당주채권혼합": {"ticker":"480040.KS","qty":3,  "avg":15745,"acct":"나_IRP"},
}

# 와이프 퇴직연금
WIFE_PENSION_HOLDINGS = {
    "SOL AI반도체소부장":   {"ticker":"448540.KS","qty":161,"avg":27521,"acct":"와이프_연금"},
    "KODEX 자동차":         {"ticker":"091180.KS","qty":101,"avg":33010,"acct":"와이프_연금"},
    "KODEX 로봇액티브":     {"ticker":"412560.KS","qty":97, "avg":34188,"acct":"와이프_연금"},
    "교보악사파워인덱스":    {"ticker":"MANUAL",  "qty":0,  "avg":0,    "acct":"와이프_연금"},
    "PLUS 고배당주채권혼합": {"ticker":"480040.KS","qty":428,"avg":15802,"acct":"와이프_연금"},
}

# 교보악사파워인덱스 수동 현재가 (야후에 없는 상품)
MANUAL_PRICES = {
    "교보악사파워인덱스": 2933.99,
}

# 투자원금
INVEST_ORIGIN = {
    "나_연금":   17500000,
    "나_IRP":    400000,
    "와이프_연금": 20481900,
}

# 와이프 교보악사 평가금액 (수량 정보 없어서 직접)
WIFE_KYOBO_AMOUNT = 2916576


# ══════════════════════════════════════════════
#  현재가 조회 (yfinance + 수동 보완)
# ══════════════════════════════════════════════
@st.cache_data(ttl=300)  # 5분 캐시
def fetch_prices(tickers: tuple) -> dict:
    """
    야후 파이낸스에서 현재가 일괄 조회.
    실패 종목은 개별 재시도.
    ttl=300 → 5분마다 자동 갱신
    """
    prices = {}
    valid_tickers = [t for t in tickers if t != "MANUAL"]

    if not valid_tickers:
        return prices

    try:
        raw = yf.download(
            tickers=valid_tickers,
            period="2d",
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=True
        )
        if not raw.empty:
            close = raw["Close"] if "Close" in raw.columns else raw
            if isinstance(close, pd.DataFrame):
                last = close.ffill().iloc[-1]
                for t in valid_tickers:
                    if t in last.index:
                        v = float(last[t])
                        if not np.isnan(v) and v > 0:
                            prices[t] = v
            else:
                v = float(close.ffill().iloc[-1])
                if v > 0:
                    prices[valid_tickers[0]] = v
    except Exception:
        pass

    # 실패 종목 개별 재시도
    failed = [t for t in valid_tickers if t not in prices]
    for t in failed:
        try:
            hist = yf.Ticker(t).history(period="2d")
            if not hist.empty:
                v = float(hist["Close"].ffill().iloc[-1])
                if v > 0:
                    prices[t] = v
        except Exception:
            pass

    return prices


def get_all_prices():
    """전체 보유 종목 현재가 딕셔너리 반환"""
    all_holdings = {
        **ME_PENSION_HOLDINGS,
        **ME_IRP_HOLDINGS,
        **WIFE_PENSION_HOLDINGS
    }
    tickers = tuple(set(
        v["ticker"] for v in all_holdings.values()
        if v["ticker"] != "MANUAL"
    ))
    fetched = fetch_prices(tickers)

    # 종목명 → 현재가 매핑
    name_to_price = {}
    for name, info in all_holdings.items():
        t = info["ticker"]
        if t == "MANUAL":
            name_to_price[name] = MANUAL_PRICES.get(name, info["avg"])
        elif t in fetched:
            name_to_price[name] = fetched[t]
        else:
            # 조회 실패 시 평균매입가 사용 (0으로 표시 방지)
            name_to_price[name] = info["avg"]
    return name_to_price, fetched


def build_portfolio_df(holdings: dict, prices: dict,
                       extra_amount: float = 0) -> pd.DataFrame:
    """보유정보 + 현재가 → 포트폴리오 DataFrame"""
    rows = []
    total_eval = sum(
        prices.get(n, info["avg"]) * info["qty"]
        for n, info in holdings.items()
        if info["qty"] > 0
    ) + extra_amount

    for name, info in holdings.items():
        qty = info["qty"]
        avg = info["avg"]

        if name == "교보악사파워인덱스" and qty == 0:
            # 와이프 교보악사: 수량 없이 금액만
            cur  = prices.get(name, avg)
            eval_amt = WIFE_KYOBO_AMOUNT
            매입금액 = WIFE_KYOBO_AMOUNT
            pnl  = 0
            ret  = 0.0
        else:
            cur      = prices.get(name, avg)
            eval_amt = cur * qty
            매입금액  = avg * qty
            pnl      = eval_amt - 매입금액
            ret      = (pnl / 매입금액 * 100) if 매입금액 > 0 else 0

        비중 = (eval_amt / total_eval * 100) if total_eval > 0 else 0

        rows.append({
            "종목명":    name,
            "보유수량":  qty,
            "평균매입가": avg,
            "현재가":    int(cur),
            "매입금액":  int(매입금액),
            "평가금액":  int(eval_amt),
            "손익":      int(pnl),
            "수익률(%)": round(ret, 2),
            "비중(%)":   round(비중, 2),
        })

    df = pd.DataFrame(rows)
    return df


def get_signal(row):
    ret  = row["수익률(%)"]
    wt   = row["비중(%)"]
    name = row["종목명"]

    if ret <= -10:
        return "🔴 손절검토"
    elif ret >= 25:
        return "🟡 익절검토"
    elif ret >= 15:
        return "🔵 관찰"
    elif wt > 35:
        return "🟠 비중축소"
    elif -5 <= ret <= 2 and wt < 10:
        return "🟢 추가매수"
    else:
        return "⚪ 유지"


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
        "✏️ 수동 입력",
    ], label_visibility="collapsed")

    st.markdown("---")

    # 새로고침 버튼
    if st.button("🔄 현재가 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption(f"⏱️ 5분마다 자동갱신")
    st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')} 기준")


# ══════════════════════════════════════════════
#  현재가 로드
# ══════════════════════════════════════════════
with st.spinner("📡 현재가 조회 중..."):
    name_prices, raw_fetched = get_all_prices()

# 포트폴리오 DataFrame 생성
me_p_df   = build_portfolio_df(ME_PENSION_HOLDINGS,   name_prices)
me_i_df   = build_portfolio_df(ME_IRP_HOLDINGS,       name_prices)
wife_p_df = build_portfolio_df(
    WIFE_PENSION_HOLDINGS, name_prices,
    extra_amount=WIFE_KYOBO_AMOUNT
)

# 계좌별 합계
def acct_summary(df, origin):
    eval_tot = df["평가금액"].sum()
    buy_tot  = df["매입금액"].sum()
    pnl      = eval_tot - origin
    ret      = pnl / origin * 100 if origin > 0 else 0
    return eval_tot, pnl, ret

me_p_eval,   me_p_pnl,   me_p_ret   = acct_summary(me_p_df,   INVEST_ORIGIN["나_연금"])
me_i_eval,   me_i_pnl,   me_i_ret   = acct_summary(me_i_df,   INVEST_ORIGIN["나_IRP"])
wife_p_eval, wife_p_pnl, wife_p_ret = acct_summary(wife_p_df, INVEST_ORIGIN["와이프_연금"])

total_eval = me_p_eval + me_i_eval + wife_p_eval
total_orig = sum(INVEST_ORIGIN.values())
total_pnl  = total_eval - total_orig
total_ret  = total_pnl / total_orig * 100


# ══════════════════════════════════════════════
#  🏠 대시보드
# ══════════════════════════════════════════════
if "대시보드" in menu:
    st.markdown("## 🏦 퇴직연금 대시보드")

    # 조회 성공/실패 표시
    success_cnt = len(raw_fetched)
    total_cnt   = len(set(
        v["ticker"] for v in {
            **ME_PENSION_HOLDINGS,
            **ME_IRP_HOLDINGS,
            **WIFE_PENSION_HOLDINGS
        }.values() if v["ticker"] != "MANUAL"
    ))

    if success_cnt == total_cnt:
        st.success(f"✅ 현재가 조회 완료 ({success_cnt}/{total_cnt}) "
                   f"— {datetime.now().strftime('%H:%M:%S')}")
    else:
        st.warning(f"⚠️ 일부 조회 실패 ({success_cnt}/{total_cnt}) "
                   f"— 실패 종목은 평균매입가로 표시")

    # KPI 카드
    r1c1, r1c2 = st.columns(2)
    r2c1, r2c2 = st.columns(2)
    r3c1, r3c2 = st.columns(2)

    def kpi(col, lbl, val, is_pct=False, positive=True):
        v = f"{val:+.2f}%" if is_pct else f"₩{val:,.0f}"
        c = "pos" if positive else "neg"
        col.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-lbl">{lbl}</div>
            <div class="kpi-val"><span class="{c}">{v}</span></div>
        </div>""", unsafe_allow_html=True)

    kpi(r1c1, "💼 총 자산",    total_eval)
    kpi(r1c2, "💰 총 손익",    total_pnl,  positive=total_pnl>=0)
    kpi(r2c1, "📊 전체수익률", total_ret,  is_pct=True, positive=total_ret>=0)
    kpi(r2c2, "📥 투자원금",   total_orig)
    kpi(r3c1, "👤 나 합계",    me_p_eval + me_i_eval)
    kpi(r3c2, "👩 와이프",     wife_p_eval, positive=wife_p_pnl>=0)

    st.markdown("<br>", unsafe_allow_html=True)

    # 계좌별 수익률 바
    st.markdown("#### 📊 계좌별 수익률")
    acct_data = pd.DataFrame({
        "계좌":   ["나_퇴직연금", "나_IRP", "와이프_퇴직연금"],
        "수익률": [me_p_ret, me_i_ret, wife_p_ret],
        "평가금액": [me_p_eval, me_i_eval, wife_p_eval],
    })
    fig = go.Figure(go.Bar(
        x=acct_data["수익률"],
        y=acct_data["계좌"],
        orientation="h",
        marker_color=["#00e676" if v>=0 else "#ff5252"
                      for v in acct_data["수익률"]],
        text=[f"{v:+.2f}%" for v in acct_data["수익률"]],
        textposition="outside"
    ))
    fig.add_vline(x=0, line_color="gray")
    fig.update_layout(
        height=200,
        margin=dict(l=10,r=70,t=10,b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#333"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # 전체 자산배분 파이
    st.markdown("#### 💼 전체 자산배분")
    all_rows = []
    for df, suffix in [(me_p_df,""), (me_i_df,"(IRP)"), (wife_p_df,"(W)")]:
        for _, r in df.iterrows():
            if r["평가금액"] > 0:
                all_rows.append({
                    "종목": r["종목명"]+suffix,
                    "금액": r["평가금액"]
                })
    all_df = pd.DataFrame(all_rows)
    fig2 = go.Figure(go.Pie(
        labels=all_df["종목"],
        values=all_df["금액"],
        hole=0.4,
        textinfo="percent",
        textfont=dict(size=9),
        marker=dict(
            colors=px.colors.qualitative.Set3,
            line=dict(color="white", width=1)
        )
    ))
    fig2.update_layout(
        height=380,
        margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(font=dict(size=8), orientation="v")
    )
    st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════
#  👤 나 포트폴리오
# ══════════════════════════════════════════════
elif "나 포트폴리오" in menu:
    st.markdown("## 👤 나의 포트폴리오")
    tab1, tab2 = st.tabs(["🏛️ 퇴직연금", "💼 IRP"])

    with tab1:
        c1, c2 = st.columns(2)
        c1.metric("평가금액", f"₩{me_p_eval:,.0f}")
        c2.metric("수익률",
                  f"{me_p_ret:+.2f}%",
                  delta=f"₩{me_p_pnl:+,.0f}")

        me_p_df["신호"] = me_p_df.apply(get_signal, axis=1)

        # 종목 카드 형식
        st.markdown("#### 📋 종목별 현황")
        for _, r in me_p_df.iterrows():
            ret_c = "#00e676" if r["수익률(%)"]>=0 else "#ff5252"
            sig   = r["신호"]
            sig_c = {"🔴":"#ff5252","🟡":"#ffd600","🟠":"#ff9800",
                     "🔵":"#40c4ff","🟢":"#00e676","⚪":"#aaa"}
            s_color = next((v for k,v in sig_c.items() if k in sig), "#aaa")

            st.markdown(f"""
            <div class="price-card">
                <div style="display:flex;justify-content:space-between;
                            align-items:center">
                    <div>
                        <div style="font-weight:700;font-size:0.95rem">
                            {r['종목명']}
                        </div>
                        <div style="font-size:0.8rem;color:#aaa;margin-top:2px">
                            {r['보유수량']:,}주 · 평균 ₩{r['평균매입가']:,.0f}
                        </div>
                    </div>
                    <div style="text-align:right">
                        <div style="font-size:1.1rem;font-weight:800;
                                    color:{ret_c}">
                            {r['수익률(%)']:+.2f}%
                        </div>
                        <div style="font-size:0.8rem;color:#aaa">
                            ₩{r['현재가']:,}
                        </div>
                    </div>
                </div>
                <div style="display:flex;justify-content:space-between;
                            margin-top:8px;font-size:0.82rem">
                    <span style="color:#aaa">
                        평가 ₩{r['평가금액']:,.0f}
                    </span>
                    <span style="color:{ret_c}">
                        손익 {'+' if r['손익']>=0 else ''}₩{r['손익']:,.0f}
                    </span>
                    <span style="color:{s_color};font-weight:600">
                        {sig}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with tab2:
        c1, c2 = st.columns(2)
        c1.metric("평가금액", f"₩{me_i_eval:,.0f}")
        c2.metric("수익률",
                  f"{me_i_ret:+.2f}%",
                  delta=f"₩{me_i_pnl:+,.0f}")

        me_i_df["신호"] = me_i_df.apply(get_signal, axis=1)

        for _, r in me_i_df.iterrows():
            ret_c = "#00e676" if r["수익률(%)"]>=0 else "#ff5252"
            sig   = r["신호"]
            sig_c_map = {"🔴":"#ff5252","🟡":"#ffd600","🟠":"#ff9800",
                         "🔵":"#40c4ff","🟢":"#00e676","⚪":"#aaa"}
            s_color = next(
                (v for k,v in sig_c_map.items() if k in sig), "#aaa"
            )
            st.markdown(f"""
            <div class="price-card">
                <div style="display:flex;justify-content:space-between;
                            align-items:center">
                    <div>
                        <div style="font-weight:700;font-size:0.95rem">
                            {r['종목명']}
                        </div>
                        <div style="font-size:0.8rem;color:#aaa;margin-top:2px">
                            {r['보유수량']:,}주 · 평균 ₩{r['평균매입가']:,.0f}
                        </div>
                    </div>
                    <div style="text-align:right">
                        <div style="font-size:1.1rem;font-weight:800;
                                    color:{ret_c}">
                            {r['수익률(%)']:+.2f}%
                        </div>
                        <div style="font-size:0.8rem;color:#aaa">
                            ₩{r['현재가']:,}
                        </div>
                    </div>
                </div>
                <div style="display:flex;justify-content:space-between;
                            margin-top:8px;font-size:0.82rem">
                    <span style="color:#aaa">
                        평가 ₩{r['평가금액']:,.0f}
                    </span>
                    <span style="color:{ret_c}">
                        손익 {'+' if r['손익']>=0 else ''}₩{r['손익']:,.0f}
                    </span>
                    <span style="color:{s_color};font-weight:600">
                        {sig}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        if me_i_df[me_i_df["수익률(%)"]>=24].shape[0] > 0:
            st.markdown("""
            <div class="danger-box">
                🔴 <b>TIGER 반도체TOP10</b> 수익률 24%+ 도달<br>
                IRP 35% 한도 주의 → 부분 익절 검토
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  👩 와이프 포트폴리오
# ══════════════════════════════════════════════
elif "와이프 포트폴리오" in menu:
    st.markdown("## 👩 와이프 포트폴리오")

    c1, c2 = st.columns(2)
    c1.metric("평가금액", f"₩{wife_p_eval:,.0f}")
    c2.metric("수익률",
              f"{wife_p_ret:+.2f}%",
              delta=f"₩{wife_p_pnl:+,.0f}")

    wife_p_df["신호"] = wife_p_df.apply(get_signal, axis=1)

    for _, r in wife_p_df.iterrows():
        ret_c = "#00e676" if r["수익률(%)"]>=0 else "#ff5252"
        sig   = r["신호"]
        sig_c_map = {"🔴":"#ff5252","🟡":"#ffd600","🟠":"#ff9800",
                     "🔵":"#40c4ff","🟢":"#00e676","⚪":"#aaa"}
        s_color = next(
            (v for k,v in sig_c_map.items() if k in sig), "#aaa"
        )
        st.markdown(f"""
        <div class="price-card">
            <div style="display:flex;justify-content:space-between;
                        align-items:center">
                <div>
                    <div style="font-weight:700;font-size:0.95rem">
                        {r['종목명']}
                    </div>
                    <div style="font-size:0.8rem;color:#aaa;margin-top:2px">
                        {r['보유수량']:,}주 · 평균 ₩{r['평균매입가']:,.0f}
                    </div>
                </div>
                <div style="text-align:right">
                    <div style="font-size:1.1rem;font-weight:800;
                                color:{ret_c}">
                        {r['수익률(%)']:+.2f}%
                    </div>
                    <div style="font-size:0.8rem;color:#aaa">
                        ₩{r['현재가']:,}
                    </div>
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;
                        margin-top:8px;font-size:0.82rem">
                <span style="color:#aaa">
                    평가 ₩{r['평가금액']:,.0f}
                </span>
                <span style="color:{ret_c}">
                    손익 {'+' if r['손익']>=0 else ''}₩{r['손익']:,.0f}
                </span>
                <span style="color:{s_color};font-weight:600">
                    {sig}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  🚦 매매 신호
# ══════════════════════════════════════════════
elif "매매 신호" in menu:
    st.markdown("## 🚦 전체 매매 신호")
    st.caption("목표 +20% / 손절 -10% / IRP 비중 35% 한도")

    all_rows = []
    for df, acct in [
        (me_p_df,   "나_연금"),
        (me_i_df,   "나_IRP"),
        (wife_p_df, "와이프"),
    ]:
        tmp = df.copy()
        tmp["신호"]    = tmp.apply(get_signal, axis=1)
        tmp["계좌"]    = acct
        tmp["우선순위"] = tmp["신호"].map({
            "🔴 손절검토":5,"🟡 익절검토":4,
            "🟠 비중축소":3,"🔵 관찰":2,
            "🟢 추가매수":1,"⚪ 유지":0
        }).fillna(0)
        all_rows.append(tmp)

    sig_df = pd.concat(all_rows).sort_values(
        "우선순위", ascending=False
    ).reset_index(drop=True)

    sig_color = {
        "🔴 손절검토":"#ff5252","🟡 익절검토":"#ffd600",
        "🟠 비중축소":"#ff9800","🔵 관찰":"#40c4ff",
        "🟢 추가매수":"#00e676","⚪ 유지":"#888"
    }

    for _, r in sig_df.iterrows():
        ret_c = "#00e676" if r["수익률(%)"]>=0 else "#ff5252"
        sig   = r["신호"]
        s_c   = sig_color.get(sig, "#888")
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
                    <div style="color:{ret_c};font-weight:800;font-size:1rem">
                        {r['수익률(%)']:+.2f}%
                    </div>
                    <div style="font-size:0.75rem;color:#aaa">
                        비중 {r['비중(%)']:.1f}%
                    </div>
                </div>
            </div>
            <div style="margin-top:6px;font-weight:700;color:{s_c}">
                {sig}
            </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  📈 추이 차트 (수익률 기준)
# ══════════════════════════════════════════════
elif "추이 차트" in menu:
    st.markdown("## 📈 수익률 추이")

    # 하드코딩 히스토리 (과거 데이터)
    me_hist = pd.DataFrame([
        {"날짜":"2026-03-04","수익률":35.66},
        {"날짜":"2026-03-05","수익률":39.95},
        {"날짜":"2026-03-06","수익률":43.60},
        {"날짜":"2026-03-09","수익률":37.59},
        {"날짜":"2026-03-10","수익률":39.71},
        {"날짜":"2026-03-11","수익률":40.54},
        {"날짜":"2026-03-12","수익률":41.29},
        {"날짜":"2026-03-13","수익률":40.14},
        {"날짜":"2026-03-16","수익률":39.33},
        {"날짜":"2026-03-17","수익률":41.33},
        {"날짜":"2026-03-18","수익률":44.62},
        {"날짜":"2026-03-20","수익률":44.22},
        {"날짜":"2026-03-23","수익률":37.20},
        {"날짜":"2026-03-24","수익률":38.50},
        {"날짜":"2026-03-25","수익률":me_p_ret},  # 실시간
    ])

    wife_hist = pd.DataFrame([
        {"날짜":"2026-03-05","수익률":1.93},
        {"날짜":"2026-03-09","수익률":-2.74},
        {"날짜":"2026-03-11","수익률":-0.57},
        {"날짜":"2026-03-12","수익률":-0.77},
        {"날짜":"2026-03-13","수익률":-1.53},
        {"날짜":"2026-03-16","수익률":-2.26},
        {"날짜":"2026-03-17","수익률":-0.76},
        {"날짜":"2026-03-18","수익률":-0.22},
        {"날짜":"2026-03-20","수익률":-1.02},
        {"날짜":"2026-03-23","수익률":-3.82},
        {"날짜":"2026-03-24","수익률":-4.16},
        {"날짜":"2026-03-25","수익률":wife_p_ret},  # 실시간
    ])

    me_hist["날짜"]   = pd.to_datetime(me_hist["날짜"])
    wife_hist["날짜"] = pd.to_datetime(wife_hist["날짜"])

    # 오늘 날짜 실시간 수익률 추가
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_ts  = pd.Timestamp(today_str)

    if today_ts > me_hist["날짜"].max():
        me_hist = pd.concat([me_hist, pd.DataFrame([{
            "날짜": today_ts, "수익률": me_p_ret
        }])]).reset_index(drop=True)

    if today_ts > wife_hist["날짜"].max():
        wife_hist = pd.concat([wife_hist, pd.DataFrame([{
            "날짜": today_ts, "수익률": wife_p_ret
        }])]).reset_index(drop=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=me_hist["날짜"], y=me_hist["수익률"],
        name="나", line=dict(color="#00e676", width=2.5),
        mode="lines+markers",
        hovertemplate="%{x|%m/%d}<br>나: %{y:.2f}%<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=wife_hist["날짜"], y=wife_hist["수익률"],
        name="와이프", line=dict(color="#ff7043", width=2.5),
        mode="lines+markers",
        hovertemplate="%{x|%m/%d}<br>와이프: %{y:.2f}%<extra></extra>"
    ))
    fig.add_hline(y=0, line_color="gray", line_dash="dot", line_width=1)

    # 오늘 현재 수익률 표시
    fig.add_annotation(
        x=me_hist["날짜"].iloc[-1],
        y=me_hist["수익률"].iloc[-1],
        text=f"  나: {me_p_ret:+.2f}%",
        showarrow=False, xanchor="left",
        font=dict(color="#00e676", size=11)
    )
    fig.add_annotation(
        x=wife_hist["날짜"].iloc[-1],
        y=wife_hist["수익률"].iloc[-1],
        text=f"  와이프: {wife_p_ret:+.2f}%",
        showarrow=False, xanchor="left",
        font=dict(color="#ff7043", size=11)
    )

    fig.update_layout(
        title="수익률 추이 (%)",
        height=420,
        margin=dict(l=10,r=60,t=40,b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#222"),
        yaxis=dict(gridcolor="#222", ticksuffix="%"),
        legend=dict(orientation="h", y=1.12),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    # 현재 수익률 지표
    c1, c2, c3 = st.columns(3)
    c1.metric("나 현재",    f"{me_p_ret:+.2f}%")
    c2.metric("와이프 현재", f"{wife_p_ret:+.2f}%")
    c3.metric("합산 수익률", f"{total_ret:+.2f}%")


# ══════════════════════════════════════════════
#  ✏️ 수동 입력 (수동 가격 보정)
# ══════════════════════════════════════════════
elif "수동 입력" in menu:
    st.markdown("## ✏️ 수동 가격 입력")
    st.markdown("""
    > yfinance 조회 실패 종목이나  
    > **교보악사파워인덱스** 같은 수동 입력 필요 상품을  
    > 직접 입력해 현재가를 보정합니다.
    """)

    st.markdown("#### 현재 조회 결과")
    status_rows = []
    all_holdings = {
        **ME_PENSION_HOLDINGS,
        **ME_IRP_HOLDINGS,
        **WIFE_PENSION_HOLDINGS
    }
    seen = set()
    for name, info in all_holdings.items():
        if name in seen:
            continue
        seen.add(name)
        t      = info["ticker"]
        price  = name_prices.get(name, 0)
        source = "수동입력" if t == "MANUAL" else \
                 ("✅ yfinance" if t in raw_fetched else "⚠️ 조회실패")
        status_rows.append({
            "종목명":  name,
            "티커":    t,
            "현재가":  f"₩{price:,.0f}",
            "출처":    source
        })

    st.dataframe(
        pd.DataFrame(status_rows),
        use_container_width=True
    )

    st.markdown("---")
    st.markdown("#### 교보악사파워인덱스 수동 입력")
    st.caption("야후 파이낸스에 없는 상품 — 퇴직연금 앱에서 직접 확인 후 입력")

    new_kyobo = st.number_input(
        "교보악사파워인덱스 현재가",
        value=int(MANUAL_PRICES.get("교보악사파워인덱스", 2933)),
        step=1,
        help="퇴직연금 앱 기준가격을 입력하세요"
    )

    if st.button("✅ 적용 (현재 세션)", use_container_width=True):
        MANUAL_PRICES["교보악사파워인덱스"] = new_kyobo
        st.cache_data.clear()
        st.success(f"교보악사파워인덱스 → ₩{new_kyobo:,.0f} 적용!")
        st.rerun()

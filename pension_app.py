import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
import io

st.set_page_config(
    page_title="🏦 퇴직연금 포트폴리오",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* 모바일 최적화 */
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
    /* 모바일 테이블 폰트 */
    .dataframe { font-size:0.75rem !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  데이터 정의
# ══════════════════════════════════════════════
@st.cache_data
def load_data():
    me_pension = pd.DataFrame([
        {"종목명":"KODEX AI전력핵심설비","보유수량":120,"평균매입가":29559,
         "현재가":33995,"매입금액":3547080,"평가금액":4079400,
         "손익":532320,"수익률":0.150073,"최고가":35895,
         "고점대비":0.055891,"비중":0.164531,"자산구분":"위험"},
        {"종목명":"KODEX AI반도체핵심장비","보유수량":151,"평균매입가":23451,
         "현재가":26617,"매입금액":3541101,"평가금액":4019167,
         "손익":478066,"수익률":0.135005,"최고가":26550,
         "고점대비":-0.002517,"비중":0.162101,"자산구분":"위험"},
        {"종목명":"KODEX 로봇액티브","보유수량":110,"평균매입가":32355,
         "현재가":31675,"매입금액":3559050,"평가금액":3484250,
         "손익":-74800,"수익률":-0.021017,"최고가":38970,
         "고점대비":0.230308,"비중":0.140527,"자산구분":"위험"},
        {"종목명":"PLUS K방산","보유수량":48,"평균매입가":73563,
         "현재가":70460,"매입금액":3531024,"평가금액":3382080,
         "손익":-148944,"수익률":-0.042182,"최고가":88030,
         "고점대비":0.249361,"비중":0.136406,"자산구분":"위험"},
        {"종목명":"교보악사파워인덱스","보유수량":888035,"평균매입가":2672.85,
         "현재가":2933.99,"매입금액":2373584,"평가금액":2605486,
         "손익":231902,"수익률":0.097701,"최고가":3335.72,
         "고점대비":0.136923,"비중":0.105085,"자산구분":"위험"},
        {"종목명":"PLUS 고배당주채권혼합","보유수량":454,"평균매입가":15655,
         "현재가":15730,"매입금액":7107370,"평가금액":7141420,
         "손익":34050,"수익률":0.004791,"최고가":17040,
         "고점대비":0.083280,"비중":0.288028,"자산구분":"안전"},
        {"종목명":"현금성자산","보유수량":0,"평균매입가":0,
         "현재가":0,"매입금액":0,"평가금액":82357,
         "손익":0,"수익률":0,"최고가":0,
         "고점대비":0,"비중":0.003322,"자산구분":"안전"},
    ])

    me_irp = pd.DataFrame([
        {"종목명":"TIGER 반도체TOP10","보유수량":5,"평균매입가":27319,
         "현재가":33915,"매입금액":136595,"평가금액":169575,
         "손익":32980,"수익률":0.241444,"최고가":36570,
         "고점대비":0.055891,"비중":0.391122,"자산구분":"위험"},
        {"종목명":"TIME 글로벌탑픽액티브","보유수량":12,"평균매입가":11188,
         "현재가":11240,"매입금액":134256,"평가금액":134880,
         "손익":624,"수익률":0.004648,"최고가":0,
         "고점대비":0,"비중":0.311099,"자산구분":"위험"},
        {"종목명":"PLUS 고배당주채권혼합","보유수량":3,"평균매입가":15745,
         "현재가":15730,"매입금액":47235,"평가금액":47190,
         "손익":-45,"수익률":-0.000953,"최고가":0,
         "고점대비":0,"비중":0.108843,"자산구분":"안전"},
        {"종목명":"현금성자산","보유수량":0,"평균매입가":0,
         "현재가":81915,"매입금액":81915,"평가금액":81915,
         "손익":0,"수익률":0,"최고가":0,
         "고점대비":0,"비중":0.188936,"자산구분":"안전"},
    ])

    wife_pension = pd.DataFrame([
        {"종목명":"SOL AI반도체소부장","보유수량":161,"평균매입가":27521,
         "현재가":27065,"매입금액":4430835,"평가금액":4357465,
         "손익":-73370,"수익률":-0.016559,"최고가":0,
         "고점대비":0,"비중":0.215180,"자산구분":"위험"},
        {"종목명":"KODEX 자동차","보유수량":101,"평균매입가":33010,
         "현재가":31400,"매입금액":3333970,"평가금액":3171400,
         "손익":-162570,"수익률":-0.048762,"최고가":0,
         "고점대비":0,"비중":0.156610,"자산구분":"위험"},
        {"종목명":"KODEX 로봇액티브","보유수량":97,"평균매입가":34188,
         "현재가":31675,"매입금액":3316220,"평가금액":3072475,
         "손익":-243745,"수익률":-0.073501,"최고가":38970,
         "고점대비":0.230308,"비중":0.151724,"자산구분":"위험"},
        {"종목명":"교보악사파워인덱스","보유수량":0,"평균매입가":0,
         "현재가":2933.99,"매입금액":2916576,"평가금액":2916576,
         "손익":0,"수익률":0,"최고가":3335.72,
         "고점대비":0.136923,"비중":0.144026,"자산구분":"위험"},
        {"종목명":"PLUS 고배당주채권혼합","보유수량":428,"평균매입가":15802,
         "현재가":15730,"매입금액":6763162,"평가금액":6732440,
         "손익":-30722,"수익률":-0.004543,"최고가":17040,
         "고점대비":0.083280,"비중":0.332460,"자산구분":"안전"},
    ])

    me_hist = pd.DataFrame([
        {"날짜":"2026-03-04","평가액":23740442,"수익률":0.356597},
        {"날짜":"2026-03-05","평가액":24490367,"수익률":0.399450},
        {"날짜":"2026-03-06","평가액":25130548,"수익률":0.436031},
        {"날짜":"2026-03-09","평가액":24078984,"수익률":0.375942},
        {"날짜":"2026-03-10","평가액":24449588,"수익률":0.397119},
        {"날짜":"2026-03-11","평가액":24594821,"수익률":0.405418},
        {"날짜":"2026-03-12","평가액":24725399,"수익률":0.412880},
        {"날짜":"2026-03-13","평가액":24524931,"수익률":0.401425},
        {"날짜":"2026-03-16","평가액":24382512,"수익률":0.393286},
        {"날짜":"2026-03-17","평가액":24733554,"수익률":0.413346},
        {"날짜":"2026-03-18","평가액":25308531,"수익률":0.446202},
        {"날짜":"2026-03-20","평가액":25238835,"수익률":0.442219},
        {"날짜":"2026-03-23","평가액":24009675,"수익률":0.371981},
        {"날짜":"2026-03-24","평가액":24238300,"수익률":0.385046},
        {"날짜":"2026-03-25","평가액":24794160,"수익률":0.416809},
    ])
    me_hist["날짜"] = pd.to_datetime(me_hist["날짜"])

    wife_hist = pd.DataFrame([
        {"날짜":"2026-03-05","평가액":20876966,"수익률":0.019289},
        {"날짜":"2026-03-06","평가액":20876966,"수익률":0.019289},
        {"날짜":"2026-03-09","평가액":19920591,"수익률":-0.027405},
        {"날짜":"2026-03-11","평가액":20364236,"수익률":-0.005745},
        {"날짜":"2026-03-12","평가액":20325131,"수익률":-0.007654},
        {"날짜":"2026-03-13","평가액":20169031,"수익률":-0.015275},
        {"날짜":"2026-03-16","평가액":20019286,"수익률":-0.022586},
        {"날짜":"2026-03-17","평가액":20327241,"수익률":-0.007551},
        {"날짜":"2026-03-18","평가액":20715516,"수익률":-0.002179},
        {"날짜":"2026-03-20","평가액":20548431,"수익률":-0.010228},
        {"날짜":"2026-03-23","평가액":19699271,"수익률":-0.038211},
        {"날짜":"2026-03-24","평가액":19896556,"수익률":-0.041627},
        {"날짜":"2026-03-25","평가액":20250356,"수익률":-0.024585},
    ])
    wife_hist["날짜"] = pd.to_datetime(wife_hist["날짜"])

    trade_df = pd.DataFrame([
        {"매매일자":"2026-02-24","종목명":"신한 TopsValue40",
         "매입금액":5273643,"판매금액":6713634,"수익금액":1439991,"수익률":0.273054},
        {"매매일자":"2026-02-24","종목명":"교보악사파워인덱스",
         "매입금액":7041648,"판매금액":11165888,"수익금액":4124240,"수익률":0.585692},
        {"매매일자":"2026-02-24","종목명":"RISE 미국S&P500",
         "매입금액":5255774,"판매금액":5834070,"수익금액":578296,"수익률":0.110031},
    ])

    return me_pension, me_irp, wife_pension, me_hist, wife_hist, trade_df


def get_signal(row, acct_type="pension"):
    ret   = row["수익률"]
    wt    = row["비중"]
    고점비 = row.get("고점대비", 0)
    명    = row["종목명"]
    if "현금" in 명:
        return "💵 현금유지", 0
    if acct_type == "irp" and wt > 0.35:
        return f"🟠 비중축소 (IRP {wt*100:.0f}%)", 3
    if ret <= -0.10:
        return f"🔴 손절검토 ({ret*100:+.1f}%)", 5
    elif ret >= 0.25:
        return f"🟡 익절검토 ({ret*100:+.1f}%)", 4
    elif 고점비 > 0.20:
        return f"⚠️ 낙폭주의 (고점대비-{고점비*100:.0f}%)", 3
    elif ret >= 0.15:
        return f"🔵 관찰 ({ret*100:+.1f}%)", 2
    elif -0.05 <= ret <= 0.02 and wt < 0.10:
        return f"🟢 추가매수검토 ({wt*100:.0f}%)", 1
    else:
        return f"⚪ 유지 ({ret*100:+.1f}%)", 0


# ── 데이터 로드 ───────────────────────────────
me_p, me_i, wife_p, me_h, wife_h, trade = load_data()

# ══════════════════════════════════════════════
#  사이드바 메뉴
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏦 퇴직연금 관리")
    menu = st.radio("메뉴", [
        "🏠 대시보드",
        "👤 나 포트폴리오",
        "👩 와이프 포트폴리오",
        "📈 평가액 추이",
        "🚦 매매 신호",
        "📋 매매일지",
        "✏️ 데이터 수정",
    ], label_visibility="collapsed")
    st.markdown("---")
    st.caption("📅 기준: 2026-03-25")
    st.caption(f"💼 합계: ₩{45478076:,.0f}")


# ══════════════════════════════════════════════
#  🏠 대시보드
# ══════════════════════════════════════════════
if "대시보드" in menu:
    st.markdown("## 🏦 퇴직연금 통합 대시보드")
    st.caption("기준일: 2026-03-25")

    # KPI (모바일: 2열)
    r1c1, r1c2 = st.columns(2)
    r2c1, r2c2 = st.columns(2)
    r3c1, r3c2 = st.columns(2)

    def kpi(col, lbl, val, is_money=True, positive=True):
        v = f"₩{val:,.0f}" if is_money else f"{val:+.2f}%"
        c = "pos" if positive else "neg"
        col.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-lbl">{lbl}</div>
            <div class="kpi-val"><span class="{c}">{v}</span></div>
        </div>""", unsafe_allow_html=True)

    kpi(r1c1, "💼 총자산",     45478076)
    kpi(r1c2, "📥 투자원금",   38381900)
    kpi(r2c1, "💰 총손익",     7096176,  positive=True)
    kpi(r2c2, "📊 수익률",     18.49, is_money=False, positive=True)
    kpi(r3c1, "👤 나 합계",    25227720)
    kpi(r3c2, "👩 와이프",     20250356, positive=False)

    st.markdown("<br>", unsafe_allow_html=True)

    # 계좌별 수익률 바
    st.markdown("#### 📊 계좌별 수익률")
    acct_df = pd.DataFrame({
        "계좌":   ["나_퇴직연금", "나_IRP", "와이프_퇴직연금"],
        "수익률": [41.68, 8.39, -1.13]
    })
    fig = go.Figure(go.Bar(
        x=acct_df["수익률"], y=acct_df["계좌"],
        orientation="h",
        marker_color=["#00e676","#40c4ff","#ff5252"],
        text=[f"{v:+.2f}%" for v in acct_df["수익률"]],
        textposition="outside"
    ))
    fig.add_vline(x=0, line_color="gray")
    fig.update_layout(
        height=220, margin=dict(l=10,r=50,t=10,b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#333"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # 전체 자산배분 파이
    st.markdown("#### 💼 전체 자산배분")
    all_rows = []
    for _, r in me_p.iterrows():
        if r["평가금액"] > 0:
            all_rows.append({"종목": r["종목명"], "금액": r["평가금액"]})
    for _, r in me_i.iterrows():
        if r["평가금액"] > 0:
            all_rows.append({"종목": r["종목명"]+"(IRP)", "금액": r["평가금액"]})
    for _, r in wife_p.iterrows():
        if r["평가금액"] > 0:
            all_rows.append({"종목": r["종목명"]+"(W)", "금액": r["평가금액"]})
    all_df = pd.DataFrame(all_rows)
    fig2 = go.Figure(go.Pie(
        labels=all_df["종목"], values=all_df["금액"],
        hole=0.4, textinfo="percent",
        marker=dict(colors=px.colors.qualitative.Set3,
                    line=dict(color="white", width=1))
    ))
    fig2.update_layout(
        height=380, margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(font=dict(size=9), orientation="v")
    )
    st.plotly_chart(fig2, use_container_width=True)

    # 합산 추이
    st.markdown("#### 📈 합산 평가액 추이")
    merged = pd.merge(
        me_h.rename(columns={"평가액":"나"}),
        wife_h.rename(columns={"평가액":"와이프"}),
        on="날짜", how="outer"
    ).sort_values("날짜").ffill()
    merged["합산"] = merged["나"] + merged["와이프"]

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=merged["날짜"], y=merged["합산"],
        name="합산", fill="tozeroy",
        fillcolor="rgba(100,181,246,0.15)",
        line=dict(color="#64b5f6", width=2)
    ))
    fig3.add_trace(go.Scatter(
        x=merged["날짜"], y=merged["나"],
        name="나", line=dict(color="#00e676", width=1.5, dash="dot")
    ))
    fig3.add_trace(go.Scatter(
        x=merged["날짜"], y=merged["와이프"],
        name="와이프", line=dict(color="#ff7043", width=1.5, dash="dot")
    ))
    fig3.update_layout(
        height=320, margin=dict(l=10,r=10,t=10,b=10),
        yaxis_tickformat=",",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#222"),
        yaxis=dict(gridcolor="#222"),
        legend=dict(orientation="h", y=1.1, font=dict(size=10)),
        hovermode="x unified"
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
        c1.metric("평가금액", "₩24,794,160")
        c2.metric("수익률",   "+41.68%", delta="+ ₩7,294,160")

        st.markdown("#### 📋 종목 현황")
        df = me_p[me_p["종목명"] != "현금성자산"].copy()
        df["수익률%"] = (df["수익률"]*100).round(2)
        df["비중%"]   = (df["비중"]*100).round(1)
        df["신호"]    = df.apply(lambda r: get_signal(r,"pension")[0], axis=1)

        st.dataframe(
            df[["종목명","현재가","수익률%","비중%","신호"]],
            use_container_width=True, height=280
        )

        # 수익률 바
        tmp = df.sort_values("수익률%")
        fig = go.Figure(go.Bar(
            x=tmp["수익률%"], y=tmp["종목명"],
            orientation="h",
            marker_color=["#ff5252" if v<0 else "#00e676" for v in tmp["수익률%"]],
            text=[f"{v:+.1f}%" for v in tmp["수익률%"]],
            textposition="outside"
        ))
        fig.add_vline(x=0, line_color="gray")
        fig.update_layout(
            height=300, margin=dict(l=10,r=60,t=5,b=5),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#333"),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        <div class="warn-box">
            ⚠️ <b>PLUS K방산</b> -4.2%, 고점대비 -24.9%<br>
            손절 라인 -7% 설정 권장
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        c1, c2 = st.columns(2)
        c1.metric("평가금액", "₩433,560")
        c2.metric("수익률",   "+8.39%", delta="+₩33,560")

        st.markdown("""
        <div class="danger-box">
            🔴 <b>TIGER 반도체TOP10</b> +24.1% / 비중 39.1%<br>
            IRP 35% 한도 초과 → <b>부분 익절 강력 권장</b>
        </div>
        """, unsafe_allow_html=True)

        df_i = me_i.copy()
        df_i["수익률%"] = (df_i["수익률"]*100).round(2)
        df_i["비중%"]   = (df_i["비중"]*100).round(1)
        df_i["신호"]    = df_i.apply(lambda r: get_signal(r,"irp")[0], axis=1)

        st.dataframe(
            df_i[["종목명","현재가","수익률%","비중%","신호"]],
            use_container_width=True, height=220
        )


# ══════════════════════════════════════════════
#  👩 와이프 포트폴리오
# ══════════════════════════════════════════════
elif "와이프 포트폴리오" in menu:
    st.markdown("## 👩 와이프 포트폴리오")

    c1, c2 = st.columns(2)
    c1.metric("평가금액", "₩20,250,356")
    c2.metric("수익률",   "-1.13%", delta="-₩231,544")

    st.markdown("""
    <div class="warn-box">
        ⚠️ 2026-02-24 리밸런싱 이후 전 종목 손실 중<br>
        누적 실현익 ₩6,142,527은 별도 확보 완료
    </div>
    """, unsafe_allow_html=True)

    df_w = wife_p.copy()
    df_w["수익률%"] = (df_w["수익률"]*100).round(2)
    df_w["비중%"]   = (df_w["비중"]*100).round(1)
    df_w["신호"]    = df_w.apply(lambda r: get_signal(r,"pension")[0], axis=1)

    st.dataframe(
        df_w[["종목명","현재가","수익률%","비중%","신호"]],
        use_container_width=True, height=280
    )

    # 경고 박스
    st.markdown("""
    <div class="danger-box">
        🔴 <b>KODEX 로봇액티브</b> -7.35% / 고점대비 -23%<br>
        손절기준(-10%) 근접. 즉시 손절 라인 설정 필요<br>
        ※ 나의 계좌도 동일 종목 보유 (공통 리스크)
    </div>
    <div class="warn-box">
        ⚠️ <b>KODEX 자동차</b> -4.88%<br>
        -8% 도달 시 손절 검토
    </div>
    <div class="warn-box">
        ⚠️ <b>SOL AI반도체소부장</b> -1.66%<br>
        현재 관망. AI 반도체 사이클 모니터링
    </div>
    """, unsafe_allow_html=True)

    # 파이
    fig = go.Figure(go.Pie(
        labels=wife_p[wife_p["평가금액"]>0]["종목명"],
        values=wife_p[wife_p["평가금액"]>0]["평가금액"],
        hole=0.4, textinfo="percent+label",
        textfont=dict(size=10),
        marker=dict(colors=px.colors.qualitative.Pastel)
    ))
    fig.update_layout(
        height=350, margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════
#  📈 평가액 추이
# ══════════════════════════════════════════════
elif "평가액 추이" in menu:
    st.markdown("## 📈 평가액 추이")

    tab1, tab2, tab3 = st.tabs(["👤 나", "👩 와이프", "📊 비교"])

    with tab1:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.65,0.35],
                            subplot_titles=("평가금액","수익률(%)"))
        fig.add_trace(go.Scatter(
            x=me_h["날짜"], y=me_h["평가액"],
            fill="tozeroy", fillcolor="rgba(0,230,118,0.12)",
            line=dict(color="#00e676", width=2),
            name="평가금액"
        ), row=1, col=1)
        bar_c = ["#00e676" if v>=0 else "#ff5252" for v in me_h["수익률"]]
        fig.add_trace(go.Bar(
            x=me_h["날짜"],
            y=(me_h["수익률"]*100).round(2),
            marker_color=bar_c, name="수익률"
        ), row=2, col=1)
        fig.update_layout(
            height=480, showlegend=False,
            margin=dict(l=10,r=10,t=30,b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor="#222", tickformat=","),
            yaxis2=dict(gridcolor="#222"),
            xaxis2=dict(gridcolor="#222"),
        )
        st.plotly_chart(fig, use_container_width=True)

        # 통계
        max_v = me_h["평가액"].max()
        cur_v = me_h["평가액"].iloc[-1]
        mdd   = (cur_v - max_v) / max_v * 100
        c1, c2, c3 = st.columns(3)
        c1.metric("현재",    f"₩{cur_v:,.0f}")
        c2.metric("최고점",  f"₩{max_v:,.0f}")
        c3.metric("MDD",     f"{mdd:.2f}%")

    with tab2:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.65,0.35],
                            subplot_titles=("평가금액","수익률(%)"))
        fig.add_trace(go.Scatter(
            x=wife_h["날짜"], y=wife_h["평가액"],
            fill="tozeroy", fillcolor="rgba(255,112,67,0.12)",
            line=dict(color="#ff7043", width=2),
            name="평가금액"
        ), row=1, col=1)
        bar_c2 = ["#00e676" if v>=0 else "#ff5252" for v in wife_h["수익률"]]
        fig.add_trace(go.Bar(
            x=wife_h["날짜"],
            y=(wife_h["수익률"]*100).round(2),
            marker_color=bar_c2, name="수익률"
        ), row=2, col=1)
        fig.update_layout(
            height=480, showlegend=False,
            margin=dict(l=10,r=10,t=30,b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor="#222", tickformat=","),
            yaxis2=dict(gridcolor="#222"),
            xaxis2=dict(gridcolor="#222"),
        )
        st.plotly_chart(fig, use_container_width=True)

        max_v2 = wife_h["평가액"].max()
        cur_v2 = wife_h["평가액"].iloc[-1]
        mdd2   = (cur_v2 - max_v2) / max_v2 * 100
        c1, c2, c3 = st.columns(3)
        c1.metric("현재",   f"₩{cur_v2:,.0f}")
        c2.metric("최고점", f"₩{max_v2:,.0f}")
        c3.metric("MDD",    f"{mdd2:.2f}%")

    with tab3:
        merged = pd.merge(
            me_h[["날짜","수익률"]].rename(columns={"수익률":"나"}),
            wife_h[["날짜","수익률"]].rename(columns={"수익률":"와이프"}),
            on="날짜", how="outer"
        ).sort_values("날짜").ffill()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=merged["날짜"], y=(merged["나"]*100).round(2),
            name="나", line=dict(color="#00e676", width=2)
        ))
        fig.add_trace(go.Scatter(
            x=merged["날짜"], y=(merged["와이프"]*100).round(2),
            name="와이프", line=dict(color="#ff7043", width=2)
        ))
        fig.add_hline(y=0, line_color="gray", line_dash="dot")
        fig.update_layout(
            title="수익률 비교 (%)", height=380,
            margin=dict(l=10,r=10,t=40,b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#222"),
            yaxis=dict(gridcolor="#222"),
            legend=dict(orientation="h", y=1.12),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════
#  🚦 매매 신호
# ══════════════════════════════════════════════
elif "매매 신호" in menu:
    st.markdown("## 🚦 전체 매매 신호")
    st.caption("목표수익 +20% / 손절 -10% / IRP 단일종목 35% 한도")

    rows = []
    for df, acct, atype in [
        (me_p,   "나_연금",  "pension"),
        (me_i,   "나_IRP",   "irp"),
        (wife_p, "와이프",   "pension"),
    ]:
        for _, r in df.iterrows():
            if "현금" in r["종목명"]:
                continue
            sig, prio = get_signal(r, atype)
            rows.append({
                "계좌":     acct,
                "종목명":   r["종목명"],
                "수익률%":  round(r["수익률"]*100,2),
                "비중%":    round(r["비중"]*100,1),
                "신호":     sig,
                "우선순위": prio
            })

    sig_df = pd.DataFrame(rows).sort_values("우선순위", ascending=False)

    # 신호별 색상 배지
    def badge(sig):
        color_map = {
            "🔴":"#ff5252","🟡":"#ffd600","🟠":"#ff9800",
            "⚠️":"#ffb74d","🔵":"#40c4ff","🟢":"#00e676","⚪":"#aaa"
        }
        for k, v in color_map.items():
            if k in sig:
                return f'<span style="color:{v};font-weight:700">{sig}</span>'
        return sig

    # 모바일 카드 형식으로 출력
    for _, r in sig_df.iterrows():
        sig_html = badge(r["신호"])
        ret_color = "#00e676" if r["수익률%"] >= 0 else "#ff5252"
        st.markdown(f"""
        <div style="background:#1e2130;border-radius:10px;
                    padding:12px 14px;margin:6px 0;
                    border-left:3px solid #444;">
            <div style="font-size:0.75rem;color:#888">{r['계좌']}</div>
            <div style="font-size:1rem;font-weight:700;margin:2px 0">
                {r['종목명']}
            </div>
            <div style="display:flex;gap:12px;font-size:0.85rem;margin-top:4px">
                <span style="color:{ret_color}">
                    수익률 {r['수익률%']:+.1f}%
                </span>
                <span style="color:#aaa">비중 {r['비중%']:.1f}%</span>
            </div>
            <div style="margin-top:6px;font-size:0.9rem">{sig_html}</div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  📋 매매일지
# ══════════════════════════════════════════════
elif "매매일지" in menu:
    st.markdown("## 📋 매매일지")
    st.markdown("""
    <div class="safe-box">
        ✅ <b>2026-02-24 리밸런싱 완료</b><br>
        누적 실현이익: <b>+₩6,142,527</b>
    </div>
    """, unsafe_allow_html=True)

    for _, r in trade.iterrows():
        color = "#00e676"
        st.markdown(f"""
        <div style="background:#1e2130;border-radius:10px;
                    padding:12px 14px;margin:8px 0;
                    border-left:3px solid {color};">
            <div style="font-size:0.75rem;color:#888">{r['매매일자']}</div>
            <div style="font-size:1rem;font-weight:700">{r['종목명']}</div>
            <div style="display:flex;gap:16px;margin-top:6px;font-size:0.85rem">
                <div>
                    <div style="color:#888;font-size:0.7rem">매입금액</div>
                    <div>₩{r['매입금액']:,.0f}</div>
                </div>
                <div>
                    <div style="color:#888;font-size:0.7rem">판매금액</div>
                    <div>₩{r['판매금액']:,.0f}</div>
                </div>
                <div>
                    <div style="color:#888;font-size:0.7rem">수익금액</div>
                    <div style="color:#00e676;font-weight:700">
                        +₩{r['수익금액']:,.0f}
                    </div>
                </div>
            </div>
            <div style="margin-top:4px;color:#00e676;font-size:0.85rem">
                수익률 {r['수익률']*100:+.2f}%
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 수익 합계 바
    fig = go.Figure(go.Bar(
        x=trade["종목명"], y=trade["수익금액"],
        marker_color=["#00e676","#40c4ff","#ffd600"],
        text=[f"+₩{v:,.0f}" for v in trade["수익금액"]],
        textposition="outside"
    ))
    fig.update_layout(
        height=320, margin=dict(l=10,r=10,t=10,b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#222", tickformat=","),
    )
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════
#  ✏️ 데이터 수정
# ══════════════════════════════════════════════
elif "데이터 수정" in menu:
    st.markdown("## ✏️ 현재가 직접 입력")
    st.markdown("> 퇴직연금은 실시간 시세 조회가 안되므로 직접 입력하여 업데이트하세요.")

    st.markdown("#### 👤 나 — 퇴직연금 현재가 업데이트")
    with st.form("update_me"):
        cols_data = {
            "KODEX AI전력핵심설비":  33995,
            "KODEX AI반도체핵심장비": 26617,
            "KODEX 로봇액티브":      31675,
            "PLUS K방산":           70460,
            "교보악사파워인덱스":     2933,
            "PLUS 고배당주채권혼합":  15730,
        }
        new_prices = {}
        for name, default in cols_data.items():
            new_prices[name] = st.number_input(
                name, value=default, step=10,
                key=f"me_{name}"
            )
        submitted = st.form_submit_button(
            "✅ 업데이트 (현재 세션에만 반영)",
            use_container_width=True
        )
        if submitted:
            st.success("✅ 현재가 업데이트 완료! (새로고침 시 초기화)")
            # 업데이트된 수익률 미리보기
            preview = []
            holdings = {
                "KODEX AI전력핵심설비":  (120, 29559),
                "KODEX AI반도체핵심장비": (151, 23451),
                "KODEX 로봇액티브":      (110, 32355),
                "PLUS K방산":           (48,  73563),
                "교보악사파워인덱스":     (888035, 2672.85),
                "PLUS 고배당주채권혼합":  (454, 15655),
            }
            for name, price in new_prices.items():
                qty, avg = holdings[name]
                pnl = (price - avg) / avg * 100
                preview.append({
                    "종목명": name,
                    "입력가": f"₩{price:,.0f}",
                    "수익률": f"{pnl:+.2f}%"
                })
            st.dataframe(
                pd.DataFrame(preview),
                use_container_width=True
            )

    st.markdown("---")
    st.markdown("#### 📥 엑셀 파일 업로드")
    uploaded = st.file_uploader(
        "퇴직연금 엑셀 (.xls/.xlsx)",
        type=["xls","xlsx"]
    )
    if uploaded:
        try:
            xl = pd.ExcelFile(uploaded)
            st.success(f"✅ 업로드 완료! 시트: {xl.sheet_names}")
            sheet = st.selectbox("시트 선택", xl.sheet_names)
            df_preview = xl.parse(sheet, header=None)
            st.dataframe(df_preview.head(15), use_container_width=True)
        except Exception as e:
            st.error(f"오류: {e}")
            st.info("pip install xlrd openpyxl 설치 확인")

# -*- coding: utf-8 -*-
"""월 매출 10억 만들기 - 메인 대시보드 (일간/주간/월간 보고서)"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import calendar
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import data_loader as dl
import styles as S

st.set_page_config(
    page_title="JCOHS 매출 10억 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

S.inject_css()
TPL = S.TPL

# ── 추가 CSS (보고서 스타일) ─────────────────────────────────
st.markdown("""
<style>
.report-section {
    background: linear-gradient(135deg, #F8FAFC 0%, #FFFFFF 100%);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 20px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.ai-opinion {
    background: linear-gradient(135deg, #EEF2FF 0%, #F5F3FF 100%);
    border-left: 4px solid #7C3AED;
    border-radius: 0 12px 12px 0;
    padding: 16px 20px;
    margin-top: 16px;
    font-size: 0.9rem;
    color: #374151;
    line-height: 1.7;
}
.ai-opinion .ai-label {
    font-weight: 800;
    color: #7C3AED;
    font-size: 0.78rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.section-divider {
    height: 2px;
    background: linear-gradient(90deg, transparent, #CBD5E1, transparent);
    margin: 32px 0;
    border: none;
}
.report-date {
    text-align: center;
    color: #64748B;
    font-size: 0.85rem;
    margin-bottom: 24px;
}
</style>
""", unsafe_allow_html=True)


# ── 사이드바 ─────────────────────────────────────────────────
with st.sidebar:
    st.title("JCOHS 대시보드")
    st.caption("월 매출 10억 달성 관리")
    st.divider()
    if st.button("🔄 데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.info("📌 좌측 메뉴에서 상세 페이지 이동")


# ── 데이터 로드 ──────────────────────────────────────────────
with st.spinner("데이터 로딩 중..."):
    df_26 = dl.load_sales_26()
    df_25 = dl.load_sales_25()
    df_nsa = dl.load_naver_sa()
    df_cpg = dl.load_coupang_ad()
    df_gfa = dl.load_gfa()
    df_meta = dl.load_meta()

if df_26.empty:
    st.error("26년 매출 데이터를 불러올 수 없습니다.")
    st.stop()


# ── 헬퍼 함수 ────────────────────────────────────────────────
def fmt(v, unit="원"):
    if abs(v) >= 1e8:
        return f"{v/1e8:.2f}억{unit}"
    elif abs(v) >= 1e6:
        return f"{v/1e6:.1f}백만{unit}"
    elif abs(v) >= 1e4:
        return f"{v/1e4:.0f}만{unit}"
    return f"{v:,.0f}{unit}"

def pct_change(cur, prev):
    if prev == 0:
        return 0, "N/A"
    change = (cur - prev) / prev * 100
    return change, f"{change:+.1f}%"

def ai_box(text):
    return f'<div class="ai-opinion"><div class="ai-label">AI Expert Opinion</div>{text}</div>'


# ── 날짜 기준 설정 ───────────────────────────────────────────
now = datetime.now()
today = now.date()
yesterday = today - timedelta(days=1)
week_start = today - timedelta(days=today.weekday())
last_week_start = week_start - timedelta(days=7)
last_week_end = week_start - timedelta(days=1)
month_start = today.replace(day=1)
last_month_start = (month_start - timedelta(days=1)).replace(day=1)
last_month_end = month_start - timedelta(days=1)
days_in_month = calendar.monthrange(today.year, today.month)[1]
TARGET = config.MONTHLY_TARGET

# 매출 날짜 필터
df_26["일자"] = df_26["주문일시"].dt.date
df_today = df_26[df_26["일자"] == yesterday]
df_this_week = df_26[(df_26["일자"] >= week_start) & (df_26["일자"] <= today)]
df_last_week = df_26[(df_26["일자"] >= last_week_start) & (df_26["일자"] <= last_week_end)]
df_this_month = df_26[(df_26["일자"] >= month_start) & (df_26["일자"] <= today)]
df_last_month = df_26[(df_26["일자"] >= last_month_start) & (df_26["일자"] <= last_month_end)]

# 매출 집계
sales_yesterday = df_today["총 판매금액"].sum()
sales_this_week = df_this_week["총 판매금액"].sum()
sales_last_week = df_last_week["총 판매금액"].sum()
sales_this_month = df_this_month["총 판매금액"].sum()
sales_last_month_full = df_last_month["총 판매금액"].sum()

margin_yesterday = df_today["마진"].sum() if "마진" in df_today.columns else 0
margin_this_month = df_this_month["마진"].sum() if "마진" in df_this_month.columns else 0

orders_yesterday = len(df_today)
orders_this_week = len(df_this_week)
orders_this_month = len(df_this_month)

avg_order_yesterday = sales_yesterday / max(orders_yesterday, 1)
avg_order_month = sales_this_month / max(orders_this_month, 1)

elapsed_days = max((today - month_start).days, 1)
daily_avg = sales_this_month / elapsed_days
projected_month = daily_avg * days_in_month

week_change, week_change_str = pct_change(sales_this_week, sales_last_week)
margin_rate = (margin_this_month / sales_this_month * 100) if sales_this_month > 0 else 0


# ═══════════════════════════════════════════════════════════════
#  COVER
# ═══════════════════════════════════════════════════════════════
S.page_header("JCOHS 경영 현황 보고서", f"{now.strftime('%Y년 %m월 %d일')} 기준")
st.markdown(f'<div class="report-date">보고서 생성: {now.strftime("%Y-%m-%d %H:%M")} | 데이터 기준: ~{yesterday.strftime("%m/%d")}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  SLIDE 1 — 목표 달성률
# ═══════════════════════════════════════════════════════════════
S.slide_header("월간 목표 달성 현황", "Monthly Target Progress")

progress = min(sales_this_month / TARGET, 1.0) if TARGET > 0 else 0
gap = TARGET - sales_this_month

fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=sales_this_month / 1e8,
    number={"suffix": "억", "font": {"size": 48}},
    delta={"reference": TARGET / 1e8, "suffix": "억", "relative": False},
    gauge={
        "axis": {"range": [0, TARGET / 1e8 * 1.2], "ticksuffix": "억"},
        "bar": {"color": "#3B82F6"},
        "steps": [
            {"range": [0, TARGET / 1e8 * 0.5], "color": "#FEE2E2"},
            {"range": [TARGET / 1e8 * 0.5, TARGET / 1e8 * 0.8], "color": "#FEF3C7"},
            {"range": [TARGET / 1e8 * 0.8, TARGET / 1e8], "color": "#DCFCE7"},
        ],
        "threshold": {"line": {"color": "#EF4444", "width": 3}, "thickness": 0.8, "value": TARGET / 1e8},
    },
    title={"text": f"목표 {TARGET/1e8:.0f}억 대비 달성률 {progress*100:.1f}%"},
))
fig_gauge.update_layout(height=300, margin=dict(t=60, b=20, l=40, r=40), template=TPL)

col_g, col_k = st.columns([3, 2])
with col_g:
    st.plotly_chart(fig_gauge, use_container_width=True)
with col_k:
    st.markdown(S.kpi_card("현재 누적 매출", fmt(sales_this_month, ""), border_color="#3B82F6"), unsafe_allow_html=True)
    st.markdown("")
    st.markdown(S.kpi_card("목표까지 남은 금액", fmt(gap, "") if gap > 0 else "달성!", border_color="#EF4444" if gap > 0 else "#22C55E"), unsafe_allow_html=True)
    st.markdown("")
    st.markdown(S.kpi_card("월말 예상 매출", fmt(projected_month, ""),
                           delta=f"{'달성 가능' if projected_month >= TARGET else f'{fmt(TARGET - projected_month, \"\")} 부족'}",
                           delta_up=projected_month >= TARGET,
                           border_color="#8B5CF6"), unsafe_allow_html=True)

remaining_days = days_in_month - elapsed_days
needed_daily = gap / max(remaining_days, 1) if gap > 0 else 0
if projected_month >= TARGET:
    _op = f"현재 일평균 매출 <b>{fmt(daily_avg, '')}</b>을 유지하면 월말 <b>{fmt(projected_month, '')}</b> 달성이 가능합니다. 남은 {remaining_days}일간 안정적 운영이 핵심입니다. 보수적 예측(10% 하락 감안)은 약 <b>{fmt(projected_month * 0.9, '')}</b> 수준입니다."
else:
    pct_up = ((needed_daily / max(daily_avg, 1) - 1) * 100)
    _op = f"목표 달성을 위해 남은 {remaining_days}일간 <b>일평균 {fmt(needed_daily, '')}</b>이 필요합니다. 현재 일평균 대비 <b>{pct_up:+.0f}%</b> 증가가 필요하며, 광고 예산 증액 또는 프로모션 집행을 권고합니다."
st.markdown(ai_box(_op), unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  SLIDE 2 — 어제 영업 현황
# ═══════════════════════════════════════════════════════════════
S.slide_header("어제 영업 현황", f"Daily Report — {yesterday.strftime('%m월 %d일')}")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(S.kpi_card("어제 매출", fmt(sales_yesterday, ""), border_color="#3B82F6"), unsafe_allow_html=True)
with c2:
    st.markdown(S.kpi_card("주문 건수", f"{orders_yesterday:,}건", border_color="#8B5CF6"), unsafe_allow_html=True)
with c3:
    st.markdown(S.kpi_card("평균 객단가", fmt(avg_order_yesterday, ""), border_color="#06B6D4"), unsafe_allow_html=True)
with c4:
    mr_y = (margin_yesterday / sales_yesterday * 100) if sales_yesterday > 0 else 0
    st.markdown(S.kpi_card("마진율", f"{mr_y:.1f}%", delta=fmt(margin_yesterday, ""),
                           delta_up=mr_y > 20, border_color="#22C55E"), unsafe_allow_html=True)

if "채널" in df_today.columns and not df_today.empty:
    ch_sales = df_today.groupby("채널")["총 판매금액"].sum().sort_values(ascending=False)
    if not ch_sales.empty:
        fig_ch = px.bar(ch_sales.reset_index(), x="채널", y="총 판매금액",
                       color="채널", color_discrete_sequence=S.PALETTE, title="어제 채널별 매출")
        fig_ch.update_layout(height=300, template=TPL, showlegend=False)
        fig_ch.update_yaxes(tickformat=",")
        st.plotly_chart(fig_ch, use_container_width=True)

if daily_avg > 0 and sales_yesterday > 0:
    _op = f"어제 매출 <b>{fmt(sales_yesterday, '')}</b>은 월 일평균 <b>{fmt(daily_avg, '')}</b> 대비 <b>{((sales_yesterday/daily_avg-1)*100):+.0f}%</b>입니다. "
    _op += "양호한 수준입니다." if sales_yesterday >= daily_avg else "주력 채널의 광고 노출/재고 상황을 점검해 보세요."
elif sales_yesterday == 0:
    _op = "어제 매출 데이터가 아직 집계되지 않았습니다."
else:
    _op = f"어제 매출 <b>{fmt(sales_yesterday, '')}</b>을 기록했습니다."
st.markdown(ai_box(_op), unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  SLIDE 3 — 주간 현황
# ═══════════════════════════════════════════════════════════════
S.slide_header("주간 현황", f"Weekly — {week_start.strftime('%m/%d')}~{today.strftime('%m/%d')}")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(S.kpi_card("금주 매출", fmt(sales_this_week, ""), border_color="#3B82F6"), unsafe_allow_html=True)
with c2:
    st.markdown(S.kpi_card("전주 매출", fmt(sales_last_week, ""), border_color="#94A3B8"), unsafe_allow_html=True)
with c3:
    st.markdown(S.kpi_card("전주 대비", week_change_str, delta_up=week_change >= 0, border_color="#F59E0B"), unsafe_allow_html=True)
with c4:
    st.markdown(S.kpi_card("금주 주문", f"{orders_this_week:,}건", border_color="#8B5CF6"), unsafe_allow_html=True)

recent_14 = df_26[df_26["일자"] >= (today - timedelta(days=14))]
if not recent_14.empty:
    daily_sales = recent_14.groupby("일자")["총 판매금액"].sum().reset_index()
    daily_sales.columns = ["날짜", "매출"]
    fig_d = px.bar(daily_sales, x="날짜", y="매출", color_discrete_sequence=["#3B82F6"],
                   title="최근 14일 일별 매출 추이")
    fig_d.add_hline(y=daily_avg, line_dash="dash", line_color="#EF4444",
                    annotation_text=f"월 일평균 {fmt(daily_avg, '')}")
    fig_d.update_layout(height=320, template=TPL)
    fig_d.update_yaxes(tickformat=",")
    st.plotly_chart(fig_d, use_container_width=True)

if week_change >= 10:
    _op = f"전주 대비 <b>{week_change_str}</b> 성장으로 매우 좋은 흐름입니다. 성장 요인을 파악하여 지속 확대하세요."
elif week_change >= 0:
    _op = f"전주 대비 <b>{week_change_str}</b>로 안정적입니다. 전환율 높은 키워드 중심으로 광고 비중을 높이는 것을 검토하세요."
elif week_change >= -10:
    _op = f"전주 대비 <b>{week_change_str}</b> 소폭 하락. 일시적 변동인지 채널별 분석이 필요합니다."
else:
    _op = f"전주 대비 <b>{week_change_str}</b> 큰 폭 하락. 재고/광고 중단/경쟁사 프로모션/시즌 요인을 긴급 점검하세요."
st.markdown(ai_box(_op), unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  SLIDE 4 — 월간 매출 & 이익
# ═══════════════════════════════════════════════════════════════
S.slide_header("월간 매출 & 이익 현황", f"Monthly P&L — {now.strftime('%Y년 %m월')}")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(S.kpi_card("월 누적 매출", fmt(sales_this_month, ""), border_color="#3B82F6"), unsafe_allow_html=True)
with c2:
    st.markdown(S.kpi_card("월 누적 마진", fmt(margin_this_month, ""), border_color="#22C55E"), unsafe_allow_html=True)
with c3:
    st.markdown(S.kpi_card("마진율", f"{margin_rate:.1f}%", border_color="#F59E0B"), unsafe_allow_html=True)
with c4:
    st.markdown(S.kpi_card("전월 매출", fmt(sales_last_month_full, ""), border_color="#94A3B8"), unsafe_allow_html=True)

monthly_sales = df_26.groupby(df_26["주문일시"].dt.to_period("M")).agg(
    매출=("총 판매금액", "sum"),
    주문수=("총 판매금액", "count"),
    **( {"마진": ("마진", "sum")} if "마진" in df_26.columns else {} ),
).reset_index()
monthly_sales["월"] = monthly_sales["주문일시"].astype(str)

if len(monthly_sales) > 0:
    fig_m = go.Figure()
    fig_m.add_trace(go.Bar(x=monthly_sales["월"], y=monthly_sales["매출"], name="매출", marker_color="#3B82F6"))
    if "마진" in monthly_sales.columns:
        fig_m.add_trace(go.Bar(x=monthly_sales["월"], y=monthly_sales["마진"], name="마진", marker_color="#22C55E"))
    fig_m.add_hline(y=TARGET, line_dash="dash", line_color="#EF4444", annotation_text=f"목표 {TARGET/1e8:.0f}억")
    fig_m.update_layout(height=350, template=TPL, barmode="group", title="월별 매출/마진 추이")
    fig_m.update_yaxes(tickformat=",")
    st.plotly_chart(fig_m, use_container_width=True)

if margin_rate >= 25:
    _op = f"마진율 <b>{margin_rate:.1f}%</b>는 건강한 수준입니다. 매출 확대에 집중하면서 고마진 상품 비중을 유지하세요."
elif margin_rate >= 15:
    _op = f"마진율 <b>{margin_rate:.1f}%</b>는 보통 수준입니다. 광고비 효율화(ROAS 개선)와 매입 원가 협상으로 개선 가능합니다."
else:
    _op = f"마진율 <b>{margin_rate:.1f}%</b>는 주의가 필요합니다. 상품별 수익성 분석으로 적자 상품을 식별하고 구조 개선이 필요합니다."
st.markdown(ai_box(_op), unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  SLIDE 5 — 광고 효율 종합
# ═══════════════════════════════════════════════════════════════
S.slide_header("광고 효율 종합", "Advertising Performance")

ad_summary = []

if not df_nsa.empty:
    nsa_m = df_nsa[df_nsa["날짜"].dt.date >= month_start]
    if not nsa_m.empty:
        cost = nsa_m["총비용(VAT포함,원)"].sum()
        rev = nsa_m["전환매출액(원)"].sum() if "전환매출액(원)" in nsa_m.columns else 0
        clicks = nsa_m["클릭수"].sum()
        impr = nsa_m["노출수"].sum()
        conv = nsa_m["전환수"].sum() if "전환수" in nsa_m.columns else 0
        ad_summary.append({"채널": "네이버 SA", "광고비": cost, "전환매출": rev,
            "ROAS": (rev / cost * 100) if cost > 0 else 0,
            "클릭수": clicks, "노출수": impr, "전환수": conv,
            "CTR": (clicks / impr * 100) if impr > 0 else 0,
            "CPC": cost / max(clicks, 1)})

if not df_cpg.empty:
    cpg_m = df_cpg[df_cpg["날짜"].dt.date >= month_start]
    if not cpg_m.empty:
        cost = cpg_m["광고비"].sum()
        rev = cpg_m["총 전환매출액(1일)"].sum() if "총 전환매출액(1일)" in cpg_m.columns else 0
        clicks = cpg_m["클릭수"].sum()
        impr = cpg_m["노출수"].sum()
        orders = cpg_m["총 주문수(1일)"].sum() if "총 주문수(1일)" in cpg_m.columns else 0
        ad_summary.append({"채널": "쿠팡 광고", "광고비": cost, "전환매출": rev,
            "ROAS": (rev / cost * 100) if cost > 0 else 0,
            "클릭수": clicks, "노출수": impr, "전환수": orders,
            "CTR": (clicks / impr * 100) if impr > 0 else 0,
            "CPC": cost / max(clicks, 1)})

if not df_gfa.empty:
    gfa_m = df_gfa[df_gfa["기간"].dt.date >= month_start]
    if not gfa_m.empty:
        cost = gfa_m["총 비용"].sum()
        clicks = gfa_m["클릭"].sum() if "클릭" in gfa_m.columns else 0
        impr = gfa_m["노출"].sum() if "노출" in gfa_m.columns else 0
        ad_summary.append({"채널": "네이버 GFA", "광고비": cost, "전환매출": 0, "ROAS": 0,
            "클릭수": clicks, "노출수": impr, "전환수": 0,
            "CTR": (clicks / impr * 100) if impr > 0 else 0,
            "CPC": cost / max(clicks, 1)})

if not df_meta.empty:
    meta_m = df_meta[df_meta["Day"].dt.date >= month_start]
    if not meta_m.empty:
        cost = meta_m["Amount spent"].sum()
        clicks = meta_m["Clicks (all)"].sum() if "Clicks (all)" in meta_m.columns else 0
        reach = meta_m["Reach"].sum() if "Reach" in meta_m.columns else 0
        ad_summary.append({"채널": "Meta 광고", "광고비": cost, "전환매출": 0, "ROAS": 0,
            "클릭수": clicks, "노출수": reach, "전환수": 0,
            "CTR": (clicks / reach * 100) if reach > 0 else 0,
            "CPC": cost / max(clicks, 1)})

ad_ratio = 0
total_roas = 0

if ad_summary:
    df_ad = pd.DataFrame(ad_summary)
    total_ad_cost = df_ad["광고비"].sum()
    total_ad_rev = df_ad["전환매출"].sum()
    total_roas = (total_ad_rev / total_ad_cost * 100) if total_ad_cost > 0 else 0
    ad_ratio = (total_ad_cost / sales_this_month * 100) if sales_this_month > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(S.kpi_card("총 광고비", fmt(total_ad_cost, ""), border_color="#EF4444"), unsafe_allow_html=True)
    with c2:
        st.markdown(S.kpi_card("광고 전환매출", fmt(total_ad_rev, ""), border_color="#3B82F6"), unsafe_allow_html=True)
    with c3:
        rc = "#22C55E" if total_roas >= 300 else "#F59E0B" if total_roas >= 200 else "#EF4444"
        st.markdown(S.kpi_card("종합 ROAS", f"{total_roas:.0f}%", border_color=rc), unsafe_allow_html=True)
    with c4:
        st.markdown(S.kpi_card("광고비 비중", f"{ad_ratio:.1f}%", border_color="#8B5CF6"), unsafe_allow_html=True)

    col_l, col_r = st.columns(2)
    with col_l:
        fig_pie = px.pie(df_ad, values="광고비", names="채널", title="채널별 광고비 비중",
                        color_discrete_sequence=S.PALETTE)
        fig_pie.update_layout(height=300, template=TPL)
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_r:
        df_roas = df_ad[df_ad["ROAS"] > 0]
        if not df_roas.empty:
            fig_r = px.bar(df_roas, x="채널", y="ROAS", color="채널", title="채널별 ROAS (%)",
                          color_discrete_sequence=S.PALETTE)
            fig_r.add_hline(y=300, line_dash="dash", line_color="#22C55E", annotation_text="목표 300%")
            fig_r.update_layout(height=300, template=TPL, showlegend=False)
            st.plotly_chart(fig_r, use_container_width=True)

    with st.expander("광고 채널별 상세 데이터"):
        disp = df_ad.copy()
        for c in ["광고비", "전환매출", "클릭수", "노출수", "CPC"]:
            disp[c] = disp[c].apply(lambda x: f"{x:,.0f}")
        disp["ROAS"] = disp["ROAS"].apply(lambda x: f"{x:.0f}%")
        disp["CTR"] = disp["CTR"].apply(lambda x: f"{x:.2f}%")
        st.dataframe(disp, use_container_width=True, hide_index=True)

    best_ch = df_ad.loc[df_ad["ROAS"].idxmax(), "채널"] if df_ad["ROAS"].max() > 0 else "N/A"
    _parts = [f"이번 달 총 광고비 <b>{fmt(total_ad_cost, '')}</b>, 종합 ROAS <b>{total_roas:.0f}%</b>."]
    if total_roas >= 300:
        _parts.append("광고 효율 양호. 고효율 채널 예산 확대로 매출 성장을 가속화하세요.")
    elif total_roas >= 200:
        _parts.append("광고 효율 보통. 저효율 키워드 예산을 고효율 채널로 재배분하세요.")
    else:
        _parts.append("광고 효율 저조. 적자 키워드 정리와 타겟팅 개선이 시급합니다.")
    if best_ch != "N/A":
        _parts.append(f"최고 효율 채널: <b>{best_ch}</b>.")
    st.markdown(ai_box(" ".join(_parts)), unsafe_allow_html=True)
else:
    st.info("이번 달 광고 데이터가 없습니다.")

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  SLIDE 6 — 채널별 매출
# ═══════════════════════════════════════════════════════════════
S.slide_header("채널별 매출 분석", "Sales by Channel")

if "채널" in df_this_month.columns:
    ch_m = df_this_month.groupby("채널").agg(
        매출=("총 판매금액", "sum"), 주문수=("총 판매금액", "count"),
        **( {"마진": ("마진", "sum")} if "마진" in df_this_month.columns else {} ),
    ).sort_values("매출", ascending=False).reset_index()

    if not ch_m.empty:
        col_l, col_r = st.columns(2)
        with col_l:
            fig_p = px.pie(ch_m, values="매출", names="채널", title="채널별 매출 비중",
                          color_discrete_sequence=S.PALETTE)
            fig_p.update_layout(height=350, template=TPL)
            st.plotly_chart(fig_p, use_container_width=True)
        with col_r:
            fig_b = px.bar(ch_m, x="채널", y="매출", color="채널", title="채널별 매출",
                          color_discrete_sequence=S.PALETTE)
            fig_b.update_layout(height=350, template=TPL, showlegend=False)
            fig_b.update_yaxes(tickformat=",")
            st.plotly_chart(fig_b, use_container_width=True)

        top = ch_m.iloc[0]
        top_r = top["매출"] / ch_m["매출"].sum() * 100
        _op = f"매출 1위 <b>{top['채널']}</b> (전체의 <b>{top_r:.1f}%</b>). "
        if top_r > 60:
            _op += "특정 채널 의존도가 높으므로 채널 다각화로 리스크를 분산하세요. "
        if len(ch_m) > 1:
            _op += f"2위 <b>{ch_m.iloc[1]['채널']}</b> 성장을 위한 맞춤 전략을 수립하세요."
        st.markdown(ai_box(_op), unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  SLIDE 7 — 상품 TOP 10
# ═══════════════════════════════════════════════════════════════
S.slide_header("상품별 판매 TOP 10", "Product Sales Ranking")

if "상품명" in df_this_month.columns:
    pr = df_this_month.groupby("상품명").agg(
        매출=("총 판매금액", "sum"),
        수량=("수량", "sum") if "수량" in df_this_month.columns else ("총 판매금액", "count"),
        주문수=("총 판매금액", "count"),
    ).sort_values("매출", ascending=False).head(10).reset_index()

    if not pr.empty:
        pr["객단가"] = pr["매출"] / pr["주문수"].replace(0, 1)
        fig_pr = px.bar(pr, x="매출", y="상품명", orientation="h",
                       color="매출", color_continuous_scale="Blues", title="상품별 매출 TOP 10")
        fig_pr.update_layout(height=400, template=TPL, yaxis=dict(autorange="reversed"))
        fig_pr.update_xaxes(tickformat=",")
        st.plotly_chart(fig_pr, use_container_width=True)

        with st.expander("상품 상세 데이터"):
            d = pr.copy()
            d["매출"] = d["매출"].apply(lambda x: f"{x:,.0f}")
            d["객단가"] = d["객단가"].apply(lambda x: f"{x:,.0f}")
            st.dataframe(d, use_container_width=True, hide_index=True)

        _op = f"매출 1위: <b>{pr.iloc[0]['상품명'][:30]}</b>. 상위 3개 상품의 재고/리뷰 관리를 강화하고, 하위 상품은 상품페이지 개선과 가격 경쟁력을 점검하세요."
        st.markdown(ai_box(_op), unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  SLIDE 8 — 종합 요약 & 액션
# ═══════════════════════════════════════════════════════════════
S.slide_header("종합 요약 & 핵심 액션", "Executive Summary")

summary_lines = [
    f"<b>[월간]</b> 현재 매출 <b>{fmt(sales_this_month, '')}</b>, 목표 대비 <b>{progress*100:.1f}%</b>. 월말 예상 <b>{fmt(projected_month, '')}</b>.",
    f"<b>[수익성]</b> 마진율 <b>{margin_rate:.1f}%</b>" + (f", 광고비 비중 <b>{ad_ratio:.1f}%</b>." if ad_summary else "."),
    f"<b>[주간]</b> 전주 대비 <b>{week_change_str}</b>.",
]

actions = []
if gap > 0:
    actions.append(f"남은 {remaining_days}일간 일평균 <b>{fmt(needed_daily, '')}</b> 필요 → 광고 예산 증액/프로모션 검토")
if ad_summary and total_roas < 300:
    actions.append(f"광고 ROAS <b>{total_roas:.0f}%</b> → 저효율 키워드 정리, 고효율 채널 예산 재배분")
if margin_rate < 20:
    actions.append(f"마진율 <b>{margin_rate:.1f}%</b> → 저마진 상품 광고 축소, 매입 원가 재협상")
if week_change < -10:
    actions.append(f"주간 매출 <b>{week_change_str}</b> 급감 → 긴급 원인 분석")
if not actions:
    actions.append("안정적 성장세 유지 중. 기존 전략 지속 + 채널 다각화로 추가 성장 기회를 모색하세요.")

st.markdown(f"""
<div class="report-section">
    <h4 style="margin:0 0 12px 0; color:#1E293B;">경영 현황 요약</h4>
    <div style="line-height:1.8; font-size:0.92rem; color:#374151;">{"<br>".join(summary_lines)}</div>
</div>
""", unsafe_allow_html=True)

st.markdown(ai_box(f"<b>핵심 액션 아이템</b><br><br>{'<br>'.join(['▸ ' + a for a in actions])}"), unsafe_allow_html=True)

st.markdown("")
st.markdown("")

# ── 네비게이션 ───────────────────────────────────────────────
S.slide_header("상세 분석 바로가기", "Quick Navigation")
c1, c2, c3 = st.columns(3)
with c1:
    st.page_link("pages/1_현재현황.py", label="📊 현재 현황 상세", use_container_width=True)
with c2:
    st.page_link("pages/2_미래예측.py", label="🔮 미래 예측", use_container_width=True)
with c3:
    st.page_link("pages/3_NOW_Action.py", label="⚡ NOW Action", use_container_width=True)

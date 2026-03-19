# -*- coding: utf-8 -*-
"""Pillar 1: 현재 현황 — 목표달성 · 매출 · 광고 · 채널 통합"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import calendar
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import data_loader as dl
import styles as S
import ai_chat as chat

st.set_page_config(page_title="현재 현황", page_icon="📊", layout="wide")
S.inject_css()
TPL = S.TPL
S.page_header("현재 현황", "매출 · 광고 · 채널 통합 분석")

# ── 데이터 로드 ──────────────────────────────────────────────
with st.spinner("데이터 로딩 중..."):
    df_26 = dl.load_sales_26()
    df_25 = dl.load_sales_25()
    df_nsa = dl.load_naver_sa()
    df_cpg = dl.load_coupang_ad()
    df_gfa = dl.load_gfa()
    df_meta = dl.load_meta()
    df_product = dl.load_naver_product()
    df_channel = dl.load_naver_channel()
    df_keyword = dl.load_naver_keyword()
    df_ckw = dl.load_coupang_keyword()

if df_26.empty:
    st.error("26년 매출 데이터를 불러올 수 없습니다.")
    st.stop()

TARGET = config.MONTHLY_TARGET

# ── 사이드바 공통 필터 ───────────────────────────────────────
with st.sidebar:
    st.header("📅 기간 필터")
    today_d = date.today()
    yesterday = today_d - timedelta(days=1)

    # 빠른 선택 버튼
    qc1, qc2, qc3 = st.columns(3)
    with qc1:
        if st.button("금월", use_container_width=True, key="p1_q_cur"):
            if today_d.day == 1:
                lp = yesterday
                st.session_state["p1_sel_month"] = f"{lp.year}-{lp.month:02d}"
            else:
                st.session_state["p1_sel_month"] = f"{today_d.year}-{today_d.month:02d}"
            st.rerun()
    with qc2:
        if st.button("전월", use_container_width=True, key="p1_q_prev"):
            first = today_d.replace(day=1)
            lp = first - timedelta(days=1)
            st.session_state["p1_sel_month"] = f"{lp.year}-{lp.month:02d}"
            st.rerun()
    with qc3:
        if st.button("최근7일", use_container_width=True, key="p1_q_7d"):
            st.session_state["p1_sel_month"] = f"{today_d.year}-{today_d.month:02d}"
            st.session_state["p1_recent_7d"] = True
            st.rerun()

    available_months = sorted(df_26["주문일시"].dt.to_period("M").unique())
    month_labels = [str(m) for m in available_months]

    # 세션에서 선택된 월 복원
    default_idx = len(month_labels) - 1
    if "p1_sel_month" in st.session_state:
        target_m = st.session_state["p1_sel_month"]
        if target_m in month_labels:
            default_idx = month_labels.index(target_m)

    selected_month = st.selectbox("월 선택", month_labels,
                                   index=default_idx, key="p1_month")
    sel_year = int(selected_month[:4])
    sel_mon = int(selected_month[5:7])
    st.divider()

    # 매출 분석 필터 (사이드바에 미리 배치)
    st.header("매출 분석 필터")
    brands = ["전체"] + sorted(df_26["브랜드"].unique().tolist())
    sel_brand = st.selectbox("브랜드", brands, key="p1_brand")
    channels = ["전체"] + sorted(df_26["외부몰/벤더명"].unique().tolist())
    sel_channel = st.selectbox("채널(외부몰)", channels, key="p1_channel")
    st.divider()

    # 광고 필터
    st.header("광고 필터")
    platforms = st.multiselect("플랫폼", ["네이버SA", "쿠팡", "GFA", "Meta"],
                               default=["네이버SA", "쿠팡", "GFA", "Meta"], key="p1_platforms")
    st.divider()

    # 네이버 스토어 필터
    st.header("네이버 스토어 필터")
    all_stores = set()
    if not df_product.empty:
        all_stores.update(df_product["스토어명"].unique())
    if not df_channel.empty:
        all_stores.update(df_channel["스토어명"].unique())
    store_list = ["전체"] + sorted(all_stores)
    sel_store = st.selectbox("스토어", store_list, key="p1_nv_store")
    st.divider()

    # 쿠팡 키워드 기간
    st.header("쿠팡 키워드 기간")
    if "p1_ck_start" not in st.session_state:
        st.session_state["p1_ck_start"] = today_d - timedelta(days=14)
        st.session_state["p1_ck_end"] = yesterday

    ck_cols = st.columns(4)
    with ck_cols[0]:
        if st.button("14일", use_container_width=True, key="p1_ck_14d"):
            st.session_state["p1_ck_start"] = today_d - timedelta(days=14)
            st.session_state["p1_ck_end"] = yesterday
            st.rerun()
    with ck_cols[1]:
        if st.button("한달", use_container_width=True, key="p1_ck_30d"):
            st.session_state["p1_ck_start"] = today_d - timedelta(days=30)
            st.session_state["p1_ck_end"] = yesterday
            st.rerun()
    with ck_cols[2]:
        if st.button("전월", use_container_width=True, key="p1_ck_prev"):
            first_this = today_d.replace(day=1)
            last_prev = first_this - timedelta(days=1)
            st.session_state["p1_ck_start"] = last_prev.replace(day=1)
            st.session_state["p1_ck_end"] = last_prev
            st.rerun()
    with ck_cols[3]:
        if st.button("당월", use_container_width=True, key="p1_ck_cur"):
            if today_d.day == 1:
                last_prev = yesterday
                st.session_state["p1_ck_start"] = last_prev.replace(day=1)
                st.session_state["p1_ck_end"] = last_prev
            else:
                st.session_state["p1_ck_start"] = today_d.replace(day=1)
                st.session_state["p1_ck_end"] = yesterday
            st.rerun()

    ck_range = st.date_input(
        "직접 선택",
        value=[st.session_state["p1_ck_start"], st.session_state["p1_ck_end"]],
        key="p1_ck_date_input",
    )
    if len(ck_range) == 2:
        st.session_state["p1_ck_start"] = ck_range[0]
        st.session_state["p1_ck_end"] = ck_range[1]

# ── 공통 계산 ────────────────────────────────────────────────
df_month = df_26[
    (df_26["주문일시"].dt.year == sel_year) &
    (df_26["주문일시"].dt.month == sel_mon)
]
month_sales = df_month["총 판매금액"].sum()
month_margin = df_month["마진"].sum()
days_in_month = calendar.monthrange(sel_year, sel_mon)[1]
today = datetime.now()
if sel_year == today.year and sel_mon == today.month:
    elapsed_days = today.day
else:
    elapsed_days = days_in_month
remaining_days = days_in_month - elapsed_days
daily_avg = month_sales / max(elapsed_days, 1)
projected = daily_avg * days_in_month
achievement = month_sales / TARGET * 100

# 전년 동월
df_25_month = pd.DataFrame()
if not df_25.empty:
    df_25_month = df_25[
        (df_25["주문일시"].dt.year == sel_year - 1) &
        (df_25["주문일시"].dt.month == sel_mon)
    ]
last_year_sales = df_25_month["총 판매금액"].sum() if not df_25_month.empty else 0
yoy_change = ((month_sales - last_year_sales) / max(last_year_sales, 1) * 100) if last_year_sales > 0 else None

# 채널별 매출 (탭1 & 탭2에서 공통 사용)
channel_sales = df_month.groupby("외부몰/벤더명")["총 판매금액"].sum().reset_index()
channel_sales = channel_sales.sort_values("총 판매금액", ascending=False)

# 매출 분석 필터 적용
df_f = df_month.copy()
if sel_brand != "전체":
    df_f = df_f[df_f["브랜드"] == sel_brand]
if sel_channel != "전체":
    df_f = df_f[df_f["외부몰/벤더명"] == sel_channel]
total_sales = df_f["총 판매금액"].sum()
total_margin = df_f["마진"].sum()
total_qty = df_f["수량"].sum()
margin_rate_v = (total_margin / total_sales * 100) if total_sales > 0 else 0

# 광고 데이터 필터
def _filter_ad(df, date_col):
    return df[(df[date_col].dt.year == sel_year) & (df[date_col].dt.month == sel_mon)]

nsa_f = _filter_ad(df_nsa, "날짜") if not df_nsa.empty else pd.DataFrame()
cpg_f = _filter_ad(df_cpg, "날짜") if not df_cpg.empty else pd.DataFrame()
gfa_f = _filter_ad(df_gfa, "기간") if not df_gfa.empty else pd.DataFrame()
meta_f = _filter_ad(df_meta, "Day") if not df_meta.empty else pd.DataFrame()

# 광고 요약 계산
ad_summary = []
if "네이버SA" in platforms and not nsa_f.empty:
    nsa_cost = nsa_f["총비용(VAT포함,원)"].sum()
    nsa_rev = nsa_f["전환매출액(원)"].sum()
    nsa_clicks = nsa_f["클릭수"].sum()
    nsa_imp = nsa_f["노출수"].sum()
    ad_summary.append({"플랫폼": "네이버SA", "광고비": nsa_cost, "전환매출": nsa_rev,
                     "ROAS(%)": nsa_rev / max(nsa_cost, 1) * 100,
                     "클릭수": nsa_clicks, "노출수": nsa_imp,
                     "CTR(%)": nsa_clicks / max(nsa_imp, 1) * 100,
                     "CPC": nsa_cost / max(nsa_clicks, 1)})
if "쿠팡" in platforms and not cpg_f.empty:
    cpg_cost = cpg_f["광고비"].sum()
    cpg_rev = cpg_f["총 전환매출액(1일)"].sum()
    cpg_clicks = cpg_f["클릭수"].sum()
    cpg_imp = cpg_f["노출수"].sum()
    ad_summary.append({"플랫폼": "쿠팡", "광고비": cpg_cost, "전환매출": cpg_rev,
                     "ROAS(%)": cpg_rev / max(cpg_cost, 1) * 100,
                     "클릭수": cpg_clicks, "노출수": cpg_imp,
                     "CTR(%)": cpg_clicks / max(cpg_imp, 1) * 100,
                     "CPC": cpg_cost / max(cpg_clicks, 1)})
if "GFA" in platforms and not gfa_f.empty:
    gfa_cost = gfa_f["총 비용"].sum()
    gfa_clicks = gfa_f["클릭"].sum()
    gfa_imp = gfa_f["노출"].sum()
    ad_summary.append({"플랫폼": "GFA", "광고비": gfa_cost, "전환매출": 0, "ROAS(%)": 0,
                     "클릭수": gfa_clicks, "노출수": gfa_imp,
                     "CTR(%)": gfa_clicks / max(gfa_imp, 1) * 100,
                     "CPC": gfa_cost / max(gfa_clicks, 1)})
if "Meta" in platforms and not meta_f.empty:
    meta_cost = meta_f["Amount spent"].sum()
    meta_clicks = meta_f["Clicks (all)"].sum()
    meta_reach = meta_f["Reach"].sum()
    meta_links = meta_f["Link clicks"].sum()
    ad_summary.append({"플랫폼": "Meta", "광고비": meta_cost, "전환매출": 0, "ROAS(%)": 0,
                     "클릭수": meta_clicks, "노출수": meta_reach,
                     "CTR(%)": meta_links / max(meta_reach, 1) * 100,
                     "CPC": meta_cost / max(meta_clicks, 1)})

df_summary = pd.DataFrame(ad_summary)

# ═══════════════════════════════════════════════════════════════
#  AI 컨텍스트 빌드
# ═══════════════════════════════════════════════════════════════
ai_contexts = {}

# 목표 달성 컨텍스트
ai_contexts["목표 달성"] = chat.summarize_metrics(
    선택월=selected_month, 이번달매출=f"{month_sales/1e8:.2f}억",
    목표달성률=f"{achievement:.1f}%", 일평균매출=f"{daily_avg/1e6:.0f}백만",
    월말예상=f"{projected/1e8:.1f}억", 남은일수=f"{remaining_days}일",
    전년동월=f"{last_year_sales/1e8:.1f}억" if last_year_sales > 0 else "데이터없음",
)
if not channel_sales.empty:
    ai_contexts["목표 달성"] += "\n" + chat.summarize_dataframe(channel_sales, "채널별 매출")

# 매출 분석 컨텍스트
ai_contexts["매출 분석"] = chat.summarize_metrics(
    선택월=selected_month, 필터_브랜드=sel_brand, 필터_채널=sel_channel,
    총매출=f"{total_sales/1e8:.2f}억", 총마진=f"{total_margin/1e8:.2f}억",
    마진율=f"{margin_rate_v:.1f}%", 총판매수량=f"{total_qty:,.0f}개",
)
ai_contexts["매출 분석"] += "\n" + chat.summarize_dataframe(
    df_f.groupby("외부몰/벤더명").agg(매출=("총 판매금액","sum"), 마진=("마진","sum")).reset_index(),
    "채널별 매출/마진"
)
ai_contexts["매출 분석"] += "\n" + chat.summarize_dataframe(
    df_f.groupby("브랜드").agg(매출=("총 판매금액","sum")).sort_values("매출",ascending=False).head(10).reset_index(),
    "브랜드별 매출 Top10"
)

# 광고 효율 컨텍스트
if not df_summary.empty:
    total_ad = df_summary["광고비"].sum()
    total_rev = df_summary["전환매출"].sum()
    total_clicks = df_summary["클릭수"].sum()
    total_roas = total_rev / max(total_ad, 1) * 100
    ai_contexts["광고 효율"] = chat.summarize_metrics(
        선택월=selected_month, 총광고비=f"{total_ad/1e6:.1f}백만",
        총전환매출=f"{total_rev/1e6:.1f}백만", 통합ROAS=f"{total_roas:.0f}%",
        총클릭수=f"{total_clicks:,.0f}",
    )
    ai_contexts["광고 효율"] += "\n" + chat.summarize_dataframe(df_summary, "플랫폼별 광고 요약")
else:
    total_ad = 0
    total_rev = 0
    total_clicks = 0
    total_roas = 0
    ai_contexts["광고 효율"] = "광고 데이터가 없습니다."

# 채널 상세 컨텍스트
ai_contexts["채널 상세"] = chat.summarize_metrics(선택월=selected_month)
if not df_channel.empty:
    _ch_agg = df_channel.groupby("채널그룹").agg(
        유입수=("유입수","sum"), 결제금액=("결제금액(마지막클릭)","sum")).reset_index()
    ai_contexts["채널 상세"] += "\n" + chat.summarize_dataframe(_ch_agg, "네이버 채널그룹별 요약")
if not df_ckw.empty:
    ai_contexts["채널 상세"] += "\n" + chat.summarize_metrics(
        쿠팡키워드_광고비=f"{df_ckw['광고비'].sum()*1.1:,.0f}원",
        쿠팡키워드_전환매출=f"{df_ckw['총 전환매출액(14일)'].sum():,.0f}원",
    )

# ═══════════════════════════════════════════════════════════════
#  레이아웃: 메인 + AI 패널
# ═══════════════════════════════════════════════════════════════
main_col, ai_col = chat.setup_layout("p1")

with main_col:
    # ═══════════════════════════════════════════════════════════
    #  탭 구성
    # ═══════════════════════════════════════════════════════════
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 목표 달성", "💰 매출 분석", "📢 광고 효율", "🛒 채널 상세"
    ])

    # ═══════════════════════════════════════════════════════════
    #  탭 1: 목표 달성
    # ═══════════════════════════════════════════════════════════
    with tab1:
        # KPI
        S.slide_header("핵심 지표", "Key Metrics")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("이번 달 매출", f"{month_sales/1e8:.1f}억")
        c2.metric("목표 달성률", f"{achievement:.1f}%")
        c3.metric("일평균 매출", f"{daily_avg/1e6:.0f}백만")
        c4.metric("월말 예상", f"{projected/1e8:.1f}억",
                  delta=f"{'달성' if projected >= TARGET else f'{(TARGET-projected)/1e8:.1f}억 부족'}")
        if yoy_change is not None:
            c5.metric("전년 동월 대비", f"{last_year_sales/1e8:.1f}억", delta=f"{yoy_change:+.1f}%")
        else:
            c5.metric("전년 동월", "데이터 없음")

        st.markdown("")

        # 게이지 + 채널 파이
        col_g, col_p = st.columns([1, 1])
        with col_g:
            S.slide_header("목표 달성 게이지", "Monthly Target Gauge")
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=month_sales / 1e8,
                number={"suffix": "억", "font": {"size": 44, "color": S.COLORS["primary"]}},
                delta={"reference": TARGET / 1e8, "suffix": "억"},
                gauge={
                    "axis": {"range": [0, TARGET / 1e8 * 1.2], "ticksuffix": "억",
                             "tickfont": {"size": 12}},
                    "bar": {"color": S.COLORS["primary"], "thickness": 0.75},
                    "bgcolor": "#f0f2f6",
                    "steps": [
                        {"range": [0, TARGET / 1e8 * 0.5], "color": "#fee2e2"},
                        {"range": [TARGET / 1e8 * 0.5, TARGET / 1e8 * 0.8], "color": "#fef3c7"},
                        {"range": [TARGET / 1e8 * 0.8, TARGET / 1e8], "color": "#d1fae5"},
                    ],
                    "threshold": {"line": {"color": S.COLORS["danger"], "width": 3},
                                  "thickness": 0.8, "value": TARGET / 1e8},
                },
                title={"text": f"<b>{selected_month}</b> 매출", "font": {"size": 16}},
            ))
            fig_gauge.update_layout(height=370, margin=dict(t=70, b=20, l=30, r=30),
                                    paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_gauge, use_container_width=True)

        with col_p:
            S.slide_header("채널별 매출 비중", "Sales by Channel")
            if not channel_sales.empty:
                fig_pie = px.pie(channel_sales, values="총 판매금액", names="외부몰/벤더명",
                                hole=0.45, color_discrete_sequence=S.PALETTE)
                fig_pie.update_layout(height=370, margin=dict(t=30, b=20, l=20, r=20),
                                      paper_bgcolor="rgba(0,0,0,0)",
                                      font=dict(family="Pretendard, sans-serif"))
                fig_pie.update_traces(textposition="inside", textinfo="label+percent",
                                      textfont_size=12, pull=[0.03]*len(channel_sales))
                st.plotly_chart(fig_pie, use_container_width=True)

        # 월별 추이
        S.slide_header("월별 매출 추이", "Monthly Sales Trend")
        monthly_26 = df_26.groupby(df_26["주문일시"].dt.to_period("M"))["총 판매금액"].sum().reset_index()
        monthly_26["월"] = monthly_26["주문일시"].dt.to_timestamp()
        monthly_26.rename(columns={"총 판매금액": "26년 매출"}, inplace=True)

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(
            x=monthly_26["월"], y=monthly_26["26년 매출"], name="26년 매출",
            marker=dict(color=S.COLORS["primary"], cornerradius=6),
            text=[f"{v/1e8:.1f}억" for v in monthly_26["26년 매출"]],
            textposition="outside", textfont=dict(size=12, color=S.COLORS["primary"]),
        ))
        if not df_25.empty:
            monthly_25 = df_25.groupby(df_25["주문일시"].dt.to_period("M"))["총 판매금액"].sum().reset_index()
            monthly_25["월"] = monthly_25["주문일시"].dt.to_timestamp()
            monthly_25["월_shifted"] = monthly_25["월"] + pd.DateOffset(years=1)
            monthly_25.rename(columns={"총 판매금액": "25년 매출"}, inplace=True)
            fig_trend.add_trace(go.Scatter(
                x=monthly_25["월_shifted"], y=monthly_25["25년 매출"],
                name="25년 동월", mode="lines+markers", line=dict(color="gray", dash="dot"),
            ))
        fig_trend.add_hline(y=TARGET, line_dash="dash", line_color=S.COLORS["danger"],
                            annotation_text=f"목표 {TARGET/1e8:.0f}억",
                            annotation_font_color=S.COLORS["danger"])
        fig_trend.update_layout(template=TPL, height=420, yaxis_title="매출(원)")
        st.plotly_chart(fig_trend, use_container_width=True)

        # 일별 트렌드
        S.slide_header("일별 매출 트렌드", "Daily Sales Trend")
        daily = df_month.groupby(df_month["주문일시"].dt.date)["총 판매금액"].sum().reset_index()
        daily.columns = ["날짜", "매출"]
        fig_daily = go.Figure()
        fig_daily.add_trace(go.Bar(x=daily["날짜"], y=daily["매출"], name="일별 매출",
                                   marker=dict(color=S.COLORS["primary"], cornerradius=4, opacity=0.85)))
        fig_daily.add_hline(y=daily_avg, line_dash="dash", line_color=S.COLORS["warning"],
                            annotation_text=f"일평균 {daily_avg/1e6:.0f}백만",
                            annotation_font_color=S.COLORS["warning"])
        target_daily = TARGET / days_in_month
        fig_daily.add_hline(y=target_daily, line_dash="dash", line_color=S.COLORS["danger"],
                            annotation_text=f"목표 일평균 {target_daily/1e6:.0f}백만",
                            annotation_font_color=S.COLORS["danger"])
        fig_daily.update_layout(template=TPL, height=370, yaxis_title="매출(원)")
        st.plotly_chart(fig_daily, use_container_width=True)

        # 채널별 테이블
        S.slide_header("채널별 매출 상세", "Channel Sales Detail")
        if not channel_sales.empty:
            ch_detail = channel_sales.copy()
            ch_detail["비중(%)"] = (ch_detail["총 판매금액"] / month_sales * 100).round(1)
            ch_detail["총 판매금액"] = ch_detail["총 판매금액"].apply(lambda x: f"{x:,.0f}")
            st.dataframe(ch_detail, use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════════════════════════
    #  탭 2: 매출 분석
    # ═══════════════════════════════════════════════════════════
    with tab2:
        # KPI
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("총 매출", f"{total_sales/1e8:.2f}억")
        c2.metric("총 마진", f"{total_margin/1e8:.2f}억")
        c3.metric("마진율", f"{margin_rate_v:.1f}%")
        c4.metric("총 판매 수량", f"{total_qty:,.0f}개")
        st.markdown("")

        # 채널별 + 브랜드별
        col1, col2 = st.columns(2)
        with col1:
            S.slide_header("채널별 매출", "Sales by Channel")
            ch = df_f.groupby("외부몰/벤더명").agg(매출=("총 판매금액", "sum")).sort_values("매출", ascending=True).reset_index()
            fig_ch = px.bar(ch, x="매출", y="외부몰/벤더명", orientation="h", text_auto=".3s",
                            color="매출", color_continuous_scale=S.GRADIENT_BLUE)
            fig_ch.update_layout(template=TPL, height=max(350, len(ch) * 35),
                                 yaxis_title="", coloraxis_showscale=False)
            fig_ch.update_traces(marker_cornerradius=6)
            st.plotly_chart(fig_ch, use_container_width=True)

        with col2:
            S.slide_header("브랜드별 매출", "Sales by Brand")
            br = df_f.groupby("브랜드").agg(매출=("총 판매금액", "sum")).sort_values("매출", ascending=True).reset_index()
            fig_br = px.bar(br, x="매출", y="브랜드", orientation="h", text_auto=".3s",
                            color="매출", color_continuous_scale=S.GRADIENT_WARM)
            fig_br.update_layout(template=TPL, height=max(350, len(br) * 35),
                                 yaxis_title="", coloraxis_showscale=False)
            fig_br.update_traces(marker_cornerradius=6)
            st.plotly_chart(fig_br, use_container_width=True)

        # 상품 Top 20
        S.slide_header("상품 매출 Top 20", "Top 20 Products")
        top_prod = df_f.groupby("상품명").agg(매출=("총 판매금액", "sum"), 수량=("수량", "sum"),
                                              마진=("마진", "sum")).sort_values("매출", ascending=False).head(20).reset_index()
        top_prod["마진율(%)"] = (top_prod["마진"] / top_prod["매출"] * 100).round(1)
        top_prod["매출"] = top_prod["매출"].apply(lambda x: f"{x:,.0f}")
        top_prod["마진"] = top_prod["마진"].apply(lambda x: f"{x:,.0f}")
        top_prod["수량"] = top_prod["수량"].apply(lambda x: f"{x:,.0f}")
        st.dataframe(top_prod, use_container_width=True, hide_index=True)

        # WoW/MoM/YoY
        S.slide_header("WoW · MoM · YoY 비교", "Period-over-Period Comparison")
        monthly_all = df_26.groupby(df_26["주문일시"].dt.to_period("M"))["총 판매금액"].sum()
        compare_data = []
        for period in monthly_all.index:
            m_sales = monthly_all[period]
            prev_period = period - 1
            mom = ((m_sales - monthly_all.get(prev_period, 0)) / max(monthly_all.get(prev_period, 1), 1) * 100) if prev_period in monthly_all.index else None
            yoy = None
            if not df_25.empty:
                monthly_25_all = df_25.groupby(df_25["주문일시"].dt.to_period("M"))["총 판매금액"].sum()
                ly_period = pd.Period(year=period.year - 1, month=period.month, freq="M")
                if ly_period in monthly_25_all.index:
                    yoy = ((m_sales - monthly_25_all[ly_period]) / max(monthly_25_all[ly_period], 1) * 100)
            compare_data.append({
                "월": str(period), "매출(억)": f"{m_sales/1e8:.2f}",
                "MoM(%)": f"{mom:+.1f}" if mom is not None else "-",
                "YoY(%)": f"{yoy:+.1f}" if yoy is not None else "-",
            })
        if compare_data:
            st.dataframe(pd.DataFrame(compare_data), use_container_width=True, hide_index=True)

        # 채널별 마진
        S.slide_header("채널별 마진 분석", "Channel Margin Analysis")
        margin_ch = df_f.groupby("외부몰/벤더명").agg(매출=("총 판매금액", "sum"), 마진=("마진", "sum")).reset_index()
        margin_ch["마진율(%)"] = (margin_ch["마진"] / margin_ch["매출"] * 100).round(1)
        margin_ch = margin_ch.sort_values("매출", ascending=False)
        fig_margin = go.Figure()
        fig_margin.add_trace(go.Bar(x=margin_ch["외부몰/벤더명"], y=margin_ch["매출"], name="매출",
                                    marker=dict(color=S.COLORS["primary"], cornerradius=6)))
        fig_margin.add_trace(go.Bar(x=margin_ch["외부몰/벤더명"], y=margin_ch["마진"], name="마진",
                                    marker=dict(color=S.COLORS["success"], cornerradius=6)))
        fig_margin.update_layout(template=TPL, barmode="group", height=400)
        st.plotly_chart(fig_margin, use_container_width=True)

    # ═══════════════════════════════════════════════════════════
    #  탭 3: 광고 효율
    # ═══════════════════════════════════════════════════════════
    with tab3:
        if not df_summary.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("총 광고비", f"{total_ad/1e6:.1f}백만")
            c2.metric("총 전환매출", f"{total_rev/1e6:.1f}백만")
            c3.metric("통합 ROAS", f"{total_roas:.0f}%")
            c4.metric("총 클릭수", f"{total_clicks:,.0f}")
            st.markdown("")

            # 플랫폼 비교
            col1, col2 = st.columns(2)
            with col1:
                S.slide_header("플랫폼별 광고비", "Ad Spend by Platform")
                fig_cost = px.bar(df_summary, x="플랫폼", y="광고비", color="플랫폼", text_auto=".3s")
                fig_cost.update_layout(height=350, showlegend=False, margin=dict(t=30, b=30))
                st.plotly_chart(fig_cost, use_container_width=True)
            with col2:
                S.slide_header("플랫폼별 ROAS", "ROAS by Platform")
                roas_df = df_summary[df_summary["ROAS(%)"] > 0]
                if not roas_df.empty:
                    fig_roas = px.bar(roas_df, x="플랫폼", y="ROAS(%)", color="플랫폼", text_auto=".0f")
                    fig_roas.update_layout(height=350, showlegend=False, margin=dict(t=30, b=30))
                    st.plotly_chart(fig_roas, use_container_width=True)
                else:
                    st.info("ROAS 데이터가 있는 플랫폼이 없습니다.")

            # 요약 테이블
            S.slide_header("플랫폼별 요약", "Platform Summary")
            disp_s = df_summary.copy()
            disp_s["광고비"] = disp_s["광고비"].apply(lambda x: f"{x:,.0f}")
            disp_s["전환매출"] = disp_s["전환매출"].apply(lambda x: f"{x:,.0f}")
            disp_s["ROAS(%)"] = disp_s["ROAS(%)"].apply(lambda x: f"{x:.0f}")
            disp_s["클릭수"] = disp_s["클릭수"].apply(lambda x: f"{x:,.0f}")
            disp_s["노출수"] = disp_s["노출수"].apply(lambda x: f"{x:,.0f}")
            disp_s["CTR(%)"] = disp_s["CTR(%)"].apply(lambda x: f"{x:.2f}")
            disp_s["CPC"] = disp_s["CPC"].apply(lambda x: f"{x:,.0f}")
            st.dataframe(disp_s, use_container_width=True, hide_index=True)

        st.markdown("")

        # 일별 광고비 추이
        S.slide_header("일별 광고비 추이", "Daily Ad Spend Trend")
        daily_costs = []
        if "네이버SA" in platforms and not nsa_f.empty:
            d = nsa_f.groupby(nsa_f["날짜"].dt.date).agg(광고비=("총비용(VAT포함,원)", "sum")).reset_index()
            d.columns = ["날짜", "광고비"]
            d["플랫폼"] = "네이버SA"
            daily_costs.append(d)
        if "쿠팡" in platforms and not cpg_f.empty:
            d = cpg_f.groupby(cpg_f["날짜"].dt.date).agg(광고비=("광고비", "sum")).reset_index()
            d.columns = ["날짜", "광고비"]
            d["플랫폼"] = "쿠팡"
            daily_costs.append(d)
        if "GFA" in platforms and not gfa_f.empty:
            d = gfa_f.groupby(gfa_f["기간"].dt.date)["총 비용"].sum().reset_index()
            d.columns = ["날짜", "광고비"]
            d["플랫폼"] = "GFA"
            daily_costs.append(d)
        if "Meta" in platforms and not meta_f.empty:
            d = meta_f.groupby(meta_f["Day"].dt.date)["Amount spent"].sum().reset_index()
            d.columns = ["날짜", "광고비"]
            d["플랫폼"] = "Meta"
            daily_costs.append(d)
        if daily_costs:
            df_daily_ad = pd.concat(daily_costs, ignore_index=True)
            fig_daily_ad = px.line(df_daily_ad, x="날짜", y="광고비", color="플랫폼", markers=True)
            fig_daily_ad.update_layout(height=400, margin=dict(t=30, b=30), yaxis_title="광고비(원)")
            st.plotly_chart(fig_daily_ad, use_container_width=True)

        # 캠페인별 성과
        tab_nsa, tab_cpg = st.tabs(["네이버 SA 캠페인", "쿠팡 캠페인"])
        with tab_nsa:
            if not nsa_f.empty:
                camp = nsa_f.groupby("캠페인").agg(광고비=("총비용(VAT포함,원)", "sum"),
                                                   전환매출=("전환매출액(원)", "sum"),
                                                   클릭수=("클릭수", "sum"), 노출수=("노출수", "sum")).reset_index()
                camp["ROAS(%)"] = (camp["전환매출"] / camp["광고비"].replace(0, 1) * 100).round(0)
                camp["CTR(%)"] = (camp["클릭수"] / camp["노출수"].replace(0, 1) * 100).round(2)
                camp = camp.sort_values("광고비", ascending=False)
                st.dataframe(camp, use_container_width=True, hide_index=True)
            else:
                st.info("네이버SA 데이터 없음")
        with tab_cpg:
            if not cpg_f.empty:
                camp = cpg_f.groupby("캠페인명").agg(광고비=("광고비", "sum"),
                                                     전환매출=("총 전환매출액(1일)", "sum"),
                                                     클릭수=("클릭수", "sum"), 노출수=("노출수", "sum"),
                                                     주문수=("총 주문수(1일)", "sum")).reset_index()
                camp["ROAS(%)"] = (camp["전환매출"] / camp["광고비"].replace(0, 1) * 100).round(0)
                camp = camp.sort_values("광고비", ascending=False)
                st.dataframe(camp, use_container_width=True, hide_index=True)
            else:
                st.info("쿠팡 데이터 없음")

    # ═══════════════════════════════════════════════════════════
    #  탭 4: 채널 상세
    # ═══════════════════════════════════════════════════════════
    with tab4:
        sub_nv, sub_ck = st.tabs(["🛒 네이버 스토어", "🔑 쿠팡 키워드"])

        # ── 네이버 스토어 ────────────────────────────────────────
        with sub_nv:
            if df_channel.empty and df_product.empty:
                st.warning("네이버 스토어 데이터가 없습니다.")
            else:
                def _nv_filter(df, date_col="날짜"):
                    d = df.copy()
                    if sel_store != "전체":
                        d = d[d["스토어명"] == sel_store]
                    d = d[(d[date_col].dt.year == sel_year) & (d[date_col].dt.month == sel_mon)]
                    return d

                df_ch = _nv_filter(df_channel) if not df_channel.empty else pd.DataFrame()
                df_prod = _nv_filter(df_product) if not df_product.empty else pd.DataFrame()
                df_kw = _nv_filter(df_keyword) if not df_keyword.empty else pd.DataFrame()

                # 채널별 유입/전환
                if not df_ch.empty:
                    S.slide_header("채널별 유입 & 전환", "Traffic & Conversion by Channel")
                    ch_agg = df_ch.groupby("채널그룹").agg(
                        유입수=("유입수", "sum"), 고객수=("고객수", "sum"), 광고비=("광고비", "sum"),
                        결제수=("결제수(마지막클릭)", "sum"), 결제금액=("결제금액(마지막클릭)", "sum"),
                    ).reset_index()
                    ch_agg["전환율(%)"] = (ch_agg["결제수"] / ch_agg["유입수"].replace(0, 1) * 100).round(2)
                    ch_agg["ROAS(%)"] = (ch_agg["결제금액"] / ch_agg["광고비"].replace(0, 1) * 100).round(0)
                    ch_agg = ch_agg.sort_values("유입수", ascending=False)

                    nc1, nc2, nc3, nc4 = st.columns(4)
                    nc1.metric("총 유입수", f"{ch_agg['유입수'].sum():,.0f}")
                    nc2.metric("총 결제수", f"{ch_agg['결제수'].sum():,.0f}")
                    nc3.metric("총 결제금액", f"{ch_agg['결제금액'].sum()/1e6:.1f}백만")
                    overall_cvr = ch_agg["결제수"].sum() / max(ch_agg["유입수"].sum(), 1) * 100
                    nc4.metric("평균 전환율", f"{overall_cvr:.2f}%")

                    ncol1, ncol2 = st.columns(2)
                    with ncol1:
                        fig_inflow = px.bar(ch_agg, x="채널그룹", y="유입수", color="채널그룹", text_auto=".3s")
                        fig_inflow.update_layout(height=350, showlegend=False, title="채널그룹별 유입수")
                        st.plotly_chart(fig_inflow, use_container_width=True)
                    with ncol2:
                        fig_cvr = px.bar(ch_agg, x="채널그룹", y="전환율(%)", color="채널그룹", text_auto=".2f")
                        fig_cvr.update_layout(height=350, showlegend=False, title="채널그룹별 전환율")
                        st.plotly_chart(fig_cvr, use_container_width=True)

                    # 상세 테이블
                    disp_ch = ch_agg.copy()
                    for c in ["유입수", "고객수", "광고비", "결제수", "결제금액"]:
                        disp_ch[c] = disp_ch[c].apply(lambda x: f"{x:,.0f}")
                    st.dataframe(disp_ch, use_container_width=True, hide_index=True)

                    # 채널명 세부


                    S.slide_header("채널명 세부 분석", "Channel Name Breakdown")
                    ch_det = df_ch.groupby(["채널그룹", "채널명"]).agg(
                        유입수=("유입수", "sum"), 결제수=("결제수(마지막클릭)", "sum"),
                        결제금액=("결제금액(마지막클릭)", "sum"), 광고비=("광고비", "sum"),
                    ).reset_index()
                    ch_det["전환율(%)"] = (ch_det["결제수"] / ch_det["유입수"].replace(0, 1) * 100).round(2)
                    ch_det = ch_det.sort_values("결제금액", ascending=False).head(30)
                    st.dataframe(ch_det, use_container_width=True, hide_index=True)

                # 키워드
                if not df_kw.empty:
                    st.markdown("")
                    S.slide_header("키워드별 전환 분석", "Keyword Conversion Analysis")
                    kw_agg = df_kw.groupby("키워드").agg(
                        결제수=("결제수(과거 14일간 기여도추정)", "sum"),
                        결제금액=("결제금액(과거 14일간 기여도추정)", "sum"),
                    ).reset_index().sort_values("결제금액", ascending=False).head(30)
                    fig_kw = px.bar(kw_agg.head(15), x="결제금액", y="키워드", orientation="h",
                                    text_auto=".3s", color="결제금액", color_continuous_scale="Viridis")
                    fig_kw.update_layout(height=500, yaxis={"categoryorder": "total ascending"},
                                         title="Top 15 키워드", coloraxis_showscale=False)
                    st.plotly_chart(fig_kw, use_container_width=True)

                # 상품별 성과
                if not df_prod.empty:
                    st.markdown("")
                    S.slide_header("상품별 판매 성과", "Product Sales Performance")
                    prod_agg = df_prod.groupby("상품명").agg(
                        결제수=("결제수", "sum"), 결제금액=("결제금액", "sum"),
                    ).reset_index().sort_values("결제금액", ascending=False).head(20)
                    fig_prod = px.bar(prod_agg, x="결제금액", y="상품명", orientation="h",
                                      text_auto=".3s", color="결제금액", color_continuous_scale="Blues")
                    fig_prod.update_layout(height=600, yaxis={"categoryorder": "total ascending"},
                                           coloraxis_showscale=False)
                    st.plotly_chart(fig_prod, use_container_width=True)

        # ── 쿠팡 키워드 ─────────────────────────────────────────
        with sub_ck:
            if df_ckw.empty:
                st.warning("쿠팡 키워드 데이터가 없습니다.")
            else:
                d_start = st.session_state["p1_ck_start"]
                d_end = st.session_state["p1_ck_end"]
                df_ck = dl.filter_kw_df(df_ckw, "날짜", d_start, d_end)

                if df_ck.empty:
                    st.warning("선택한 기간에 데이터가 없습니다.")
                else:
                    # 전체 요약 KPI
                    S.slide_header(f"쿠팡 키워드 요약 ({d_start} ~ {d_end})", "Coupang Keyword Summary")
                    ck_cost = df_ck["광고비"].sum() * 1.1
                    ck_rev = df_ck["총 전환매출액(14일)"].sum()
                    ck_clicks = df_ck["클릭수"].sum()
                    ck_imp = df_ck["노출수"].sum()
                    ck_qty = df_ck["총 판매수량(14일)"].sum()
                    ck_roas = dl.safe_div(ck_rev, ck_cost) * 100
                    ck_cpc = dl.safe_div(ck_cost, ck_clicks)
                    ck_cvr = dl.safe_div(ck_qty, ck_clicks) * 100

                    k1, k2, k3, k4, k5, k6 = st.columns(6)
                    k1.metric("광고비(VAT)", dl.fmt_money(ck_cost))
                    k2.metric("전환매출(14일)", dl.fmt_money(ck_rev))
                    k3.metric("ROAS", f"{ck_roas:.0f}%")
                    k4.metric("평균 CPC", f"{ck_cpc:,.0f}원")
                    k5.metric("총 클릭수", f"{ck_clicks:,.0f}")
                    k6.metric("전환율", f"{ck_cvr:.2f}%")

                    # 일별 추이
                    S.slide_header("일별 추이", "Daily Trend")
                    ck_daily = df_ck.groupby(df_ck["날짜"].dt.date).agg(
                        광고비=("광고비", "sum"), 전환매출=("총 전환매출액(14일)", "sum"),
                    ).reset_index()
                    ck_daily.columns = ["날짜", "광고비", "전환매출"]
                    ck_daily["광고비(VAT)"] = ck_daily["광고비"] * 1.1
                    ck_daily["ROAS(%)"] = (ck_daily["전환매출"] / ck_daily["광고비(VAT)"].replace(0, 1) * 100).round(0)

                    fig_ck = go.Figure()
                    fig_ck.add_trace(go.Bar(x=ck_daily["날짜"], y=ck_daily["광고비(VAT)"],
                                            name="광고비(VAT)", marker_color="#636EFA"))
                    fig_ck.add_trace(go.Bar(x=ck_daily["날짜"], y=ck_daily["전환매출"],
                                            name="전환매출(14일)", marker_color="#00CC96"))
                    fig_ck.add_trace(go.Scatter(x=ck_daily["날짜"], y=ck_daily["ROAS(%)"],
                                                name="ROAS(%)", yaxis="y2",
                                                line=dict(color="#EF553B", width=2), mode="lines+markers"))
                    fig_ck.update_layout(height=400, barmode="group",
                                         yaxis=dict(title="금액(원)"),
                                         yaxis2=dict(title="ROAS(%)", overlaying="y", side="right"),
                                         legend=dict(orientation="h", yanchor="bottom", y=1.02))
                    st.plotly_chart(fig_ck, use_container_width=True)

                    # 키워드 테이블
                    S.slide_header("키워드별 성과", "Keyword Performance")
                    kw = dl.aggregate_kw_by_keyword(df_ck).sort_values("광고비(VAT)", ascending=False)
                    disp_kw = kw[["키워드", "노출수", "클릭수", "광고비(VAT)", "CTR(%)",
                                   "전환율(%)", "CPC", "총 판매수량(14일)", "총 전환매출액(14일)", "ROAS(%)"]].copy()
                    styled = disp_kw.style.format({
                        "노출수": "{:,.0f}", "클릭수": "{:,.0f}", "광고비(VAT)": "{:,.0f}",
                        "CPC": "{:,.0f}", "총 판매수량(14일)": "{:,.0f}", "총 전환매출액(14일)": "{:,.0f}",
                        "CTR(%)": "{:.2f}", "전환율(%)": "{:.2f}", "ROAS(%)": "{:.0f}",
                    })
                    st.dataframe(styled, use_container_width=True, hide_index=True, height=400)

                    # 검색 vs 비검색
                    st.markdown("")
                    S.slide_header("검색 vs 비검색 영역", "Search vs Non-Search")
                    area = dl.aggregate_kw_by_area(df_ck)
                    if not area.empty and "광고 노출 지면" in area.columns:
                        area_disp = area[["광고 노출 지면", "노출수", "클릭수", "광고비(VAT)",
                                          "총 전환매출액(14일)", "ROAS(%)", "CPC"]].copy()
                        st.dataframe(area_disp.style.format({
                            "노출수": "{:,.0f}", "클릭수": "{:,.0f}", "광고비(VAT)": "{:,.0f}",
                            "총 전환매출액(14일)": "{:,.0f}", "CPC": "{:,.0f}", "ROAS(%)": "{:.0f}",
                        }), use_container_width=True, hide_index=True)

                        col_p1, col_p2 = st.columns(2)
                        with col_p1:
                            fig_ap1 = px.pie(area, values="광고비(VAT)", names="광고 노출 지면",
                                             title="광고비 비중", hole=0.4)
                            fig_ap1.update_layout(height=300)
                            st.plotly_chart(fig_ap1, use_container_width=True)
                        with col_p2:
                            fig_ap2 = px.pie(area, values="총 전환매출액(14일)", names="광고 노출 지면",
                                             title="전환매출 비중", hole=0.4)
                            fig_ap2.update_layout(height=300)
                            st.plotly_chart(fig_ap2, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
#  AI 우측 패널
# ═══════════════════════════════════════════════════════════════
chat.render_panel(ai_col, "p1", ai_contexts)

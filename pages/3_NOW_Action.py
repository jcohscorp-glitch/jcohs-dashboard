# -*- coding: utf-8 -*-
"""Pillar 3: NOW Action — 6탭 세분화 (통합/쿠팡/네이버/브랜드/채널/상품)"""

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
import ad_analyzer as aa
import action_engine as ae
import predictor as pred
import styles as S
import ai_chat as chat

st.set_page_config(page_title="NOW Action", page_icon="⚡", layout="wide")
S.inject_css()
TPL = S.TPL
TARGET = config.MONTHLY_TARGET


# ═══════════════════════════════════════════════════════════════
#  헬퍼 함수 (키워드 분석 / 예산 시뮬레이션)
# ═══════════════════════════════════════════════════════════════
def _render_keyword_analysis(kw_df, prefix, margin_rate, min_clicks_stat):
    """플랫폼별 키워드 4분면 분석 UI"""
    if kw_df.empty:
        st.info("키워드 데이터가 없습니다.")
        return

    grp_counts = kw_df.groupby("Action_Group").size()
    GROUP_INFO = {
        "A그룹_예산및입찰가증액": ("🟢", "효자"),
        "B그룹_입찰가강력상승": ("🔵", "잠재력"),
        "C그룹_즉시제외키워드": ("🔴", "낭비"),
        "D그룹_판단유보": ("⚪", "대기"),
    }
    gc = st.columns(4)
    for i, (grp_name, (icon, label)) in enumerate(GROUP_INFO.items()):
        cnt = grp_counts.get(grp_name, 0)
        grp_data = kw_df[kw_df["Action_Group"] == grp_name]
        profit = grp_data["Estimated_Profit"].sum() if not grp_data.empty else 0
        with gc[i]:
            with st.container(border=True):
                st.markdown(f"{icon} **{label}**")
                st.metric("키워드", f"{cnt}개")
                st.metric("순이익", f"{profit:,.0f}원")

    scatter_df = kw_df[kw_df["클릭수"] >= min_clicks_stat].copy()
    if not scatter_df.empty:
        st.markdown("#### 키워드 4분면 (광고비 vs 순이익)")
        color_map = {
            "A그룹_예산및입찰가증액": "#28a745", "B그룹_입찰가강력상승": "#007bff",
            "C그룹_즉시제외키워드": "#dc3545", "D그룹_판단유보": "#6c757d",
        }
        fig_quad = px.scatter(
            scatter_df, x="총비용", y="Estimated_Profit",
            color="Action_Group", size="클릭수", hover_name="키워드",
            hover_data={"ROAS(%)": ":.0f", "CVR(%)": ":.2f", "CPC": ":.0f"},
            color_discrete_map=color_map, size_max=40,
        )
        fig_quad.add_hline(y=0, line_dash="dash", line_color="red",
                           annotation_text="손익분기선")
        fig_quad.update_layout(height=450, xaxis_title="총 광고비 (원)",
                               yaxis_title="예상 순이익 (원)")
        st.plotly_chart(fig_quad, use_container_width=True, key=f"p3_quad_{prefix}")

    display_cols = ["키워드", "캠페인명", "노출수", "클릭수", "총비용",
                    "총전환수", "총전환매출액", "ROAS(%)", "CVR(%)", "CPC",
                    "CPA", "Estimated_Profit", "Action_Group"]
    available_cols = [c for c in display_cols if c in kw_df.columns]

    tab_a, tab_b, tab_c, tab_d = st.tabs([
        "🟢 A: 예산 증액", "🔵 B: 트래픽 부스트",
        "🔴 C: 즉시 제외", "⚪ D: 판단유보",
    ])
    for tab_obj, grp_name, fname in [
        (tab_a, "A그룹_예산및입찰가증액", f"Action_A_{prefix}.csv"),
        (tab_b, "B그룹_입찰가강력상승", f"Action_B_{prefix}.csv"),
        (tab_c, "C그룹_즉시제외키워드", f"Action_C_{prefix}.csv"),
        (tab_d, "D그룹_판단유보", f"Action_D_{prefix}.csv"),
    ]:
        grp = kw_df[kw_df["Action_Group"] == grp_name][available_cols].copy()
        grp = grp.sort_values("총비용", ascending=False)
        with tab_obj:
            if grp.empty:
                st.info("해당 그룹 키워드 없음")
                continue
            st.caption(f"총 {len(grp)}개 키워드")
            disp = grp.copy()
            for c in ["노출수", "클릭수", "총비용", "총전환수", "총전환매출액", "CPC", "CPA", "Estimated_Profit"]:
                if c in disp.columns:
                    disp[c] = disp[c].apply(lambda x: f"{x:,.0f}")
            for c in ["ROAS(%)", "CVR(%)"]:
                if c in disp.columns:
                    disp[c] = disp[c].apply(lambda x: f"{x:.1f}")
            st.dataframe(disp, use_container_width=True, hide_index=True, height=400)
            csv_data = grp.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                f"📥 {fname} ({len(grp)}건)", data=csv_data,
                file_name=fname, mime="text/csv",
                key=f"p3_dl_{prefix}_{grp_name}",
            )


def _render_budget_sim(ad_info, prefix, margin_rate):
    """플랫폼별 예산 시뮬레이션 UI"""
    S.slide_header(f"{ad_info['platform']} 예산 시뮬레이션", "Budget Simulation")
    change_pct = st.slider(
        f"예산 변경률", -50, 100, 0, step=5,
        key=f"p3_sim_{prefix}",
        help=f"현재: {ad_info['cost']:,.0f}원 / ROAS: {ad_info['roas']:.0f}%",
    )
    sim = pred.simulate_budget_change(ad_info["cost"], ad_info["roas"], change_pct, margin_rate)

    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("변경 광고비", f"{sim['new_cost']/1e6:.1f}백만")
    sc2.metric("예상 매출", f"{sim['new_revenue']/1e6:.1f}백만")
    sc3.metric("예상 순이익", f"{sim['new_profit']/1e6:.1f}백만")
    sc4.metric("추가 매출", f"{sim['add_revenue']/1e6:+.1f}백만")


# ── 분석 결과 세션 캐싱 (데이터 변경 시만 재계산) ──────────────
def _quick_hash(df):
    """DataFrame 경량 해시 — 행수+컬럼수+첫행"""
    if df is None or (hasattr(df, 'empty') and df.empty):
        return "empty"
    try:
        first = str(df.iloc[0].values[:5].tolist()) if len(df) > 0 else ""
    except Exception:
        first = ""
    return f"{len(df)}_{len(df.columns)}_{first}"

def _get_or_compute(key, compute_fn):
    """session_state 기반 캐시 — 해시 변경 시만 재계산"""
    if key not in st.session_state:
        st.session_state[key] = compute_fn()
    return st.session_state[key]

# ── 데이터 로드 ──────────────────────────────────────────────
with st.spinner("데이터 분석 중..."):
    df_26 = dl.load_sales_26()
    df_25 = dl.load_sales_25()
    df_nsa = dl.load_naver_sa()
    df_cpg = dl.load_coupang_ad()
    df_gfa = dl.load_gfa()
    df_meta = dl.load_meta()
    df_ckw = dl.load_coupang_keyword()

if df_26.empty:
    st.error("매출 데이터를 불러올 수 없습니다.")
    st.stop()

# ── 핵심 계산 ────────────────────────────────────────────────
now = datetime.now()
cur_year, cur_month = now.year, now.month
df_cur = df_26[(df_26["주문일시"].dt.year == cur_year) & (df_26["주문일시"].dt.month == cur_month)]
cur_sales = df_cur["총 판매금액"].sum()
days_total = calendar.monthrange(cur_year, cur_month)[1]
days_elapsed = now.day
days_remain = days_total - days_elapsed
daily_avg = cur_sales / max(days_elapsed, 1)
gap = TARGET - cur_sales
needed_daily = gap / max(days_remain, 1) if days_remain > 0 else 0
projected = daily_avg * days_total

# ── 사이드바 설정 ────────────────────────────────────────────
with st.sidebar:
    st.header("분석 설정")
    margin_rate = st.slider("제품 평균 마진율 (%)", 5, 80, 30, step=5, key="p3_margin") / 100
    st.divider()
    st.header("키워드 분류 기준")
    min_clicks_star = st.number_input("A그룹 최소 클릭수", value=30, min_value=5, step=5, key="p3_min_star")
    min_clicks_stat = st.number_input("D그룹 통계유보 클릭수", value=10, min_value=1, step=1, key="p3_min_stat")
    min_cost_negative = st.number_input("C그룹 최소 광고비 (원)", value=10000, min_value=1000, step=1000, key="p3_min_cost")

# ═══════════════════════════════════════════════════════════════
#  사전 분석
# ═══════════════════════════════════════════════════════════════
# 채널 매트릭스
df_recent = df_26[df_26["주문일시"] >= (pd.Timestamp.now() - pd.Timedelta(days=14))]
df_prev = df_26[
    (df_26["주문일시"] >= (pd.Timestamp.now() - pd.Timedelta(days=28))) &
    (df_26["주문일시"] < (pd.Timestamp.now() - pd.Timedelta(days=14)))
]
ch_recent = df_recent.groupby("외부몰/벤더명")["총 판매금액"].sum()
ch_prev = df_prev.groupby("외부몰/벤더명")["총 판매금액"].sum()
matrix_data = []
for ch in set(list(ch_recent.index) + list(ch_prev.index)):
    r = ch_recent.get(ch, 0)
    p = ch_prev.get(ch, 0)
    growth = ((r - p) / max(p, 1) * 100) if p > 0 else 0
    matrix_data.append({"채널": ch, "최근2주 매출": r, "이전2주 매출": p, "성장률(%)": growth})
channel_matrix = pd.DataFrame(matrix_data)

# 키워드 분석
frames = []
if not df_nsa.empty:
    nsa = aa.normalize_naver_sa(df_nsa.copy())
    nsa["플랫폼"] = "네이버SA"
    frames.append(nsa)
if not df_ckw.empty:
    ckw = aa.normalize_coupang_kw(df_ckw.copy())
    ckw["플랫폼"] = "쿠팡"
    frames.append(ckw)

kw_result = pd.DataFrame()
grp_a = grp_b = grp_c = grp_d = None
if frames:
    df_analysis = pd.concat(frames, ignore_index=True)
    kw_result = aa.analyze(
        df_analysis, margin_rate=margin_rate,
        min_clicks_star=min_clicks_star,
        min_clicks_stat=min_clicks_stat,
        min_cost_negative=min_cost_negative,
    )
    grp_a = kw_result[kw_result["Action_Group"] == "A그룹_예산및입찰가증액"]
    grp_b = kw_result[kw_result["Action_Group"] == "B그룹_입찰가강력상승"]
    grp_c = kw_result[kw_result["Action_Group"] == "C그룹_즉시제외키워드"]
    grp_d = kw_result[kw_result["Action_Group"] == "D그룹_판단유보"]

# 플랫폼별 키워드 분리
kw_coupang = kw_result[kw_result["플랫폼"] == "쿠팡"] if "플랫폼" in kw_result.columns and not kw_result.empty else pd.DataFrame()
kw_naver = kw_result[kw_result["플랫폼"] == "네이버SA"] if "플랫폼" in kw_result.columns and not kw_result.empty else pd.DataFrame()

# 광고 기회
opportunities = []
if not df_nsa.empty:
    camp = df_nsa.groupby("캠페인").agg(
        광고비=("총비용(VAT포함,원)", "sum"), 전환매출=("전환매출액(원)", "sum"),
    ).reset_index()
    camp["ROAS(%)"] = camp["전환매출"] / camp["광고비"].replace(0, 1) * 100
    camp.rename(columns={"캠페인": "캠페인명"}, inplace=True)
    camp["플랫폼"] = "네이버SA"
    opportunities.append(camp)
if not df_cpg.empty:
    camp = df_cpg.groupby("캠페인명").agg(
        광고비=("광고비", "sum"), 전환매출=("총 전환매출액(1일)", "sum"),
    ).reset_index()
    camp["ROAS(%)"] = camp["전환매출"] / camp["광고비"].replace(0, 1) * 100
    camp["플랫폼"] = "쿠팡"
    opportunities.append(camp)
ad_opportunities = pd.concat(opportunities, ignore_index=True) if opportunities else pd.DataFrame()

# 검색/비검색 ROAS
search_roas = nonsearch_roas = None
if not df_ckw.empty:
    area = dl.aggregate_kw_by_area(df_ckw)
    search_row = area[area["광고 노출 지면"].str.contains("검색 영역", na=False)]
    nonsearch_row = area[area["광고 노출 지면"].str.contains("비검색", na=False)]
    if not search_row.empty:
        search_roas = search_row.iloc[0]["ROAS(%)"]
    if not nonsearch_row.empty:
        nonsearch_roas = nonsearch_row.iloc[0]["ROAS(%)"]

# 광고 요약 (시뮬레이션용)
ad_naver = None
ad_coupang = None
if not df_nsa.empty:
    nsa_cost = df_nsa["총비용(VAT포함,원)"].sum()
    nsa_rev = df_nsa["전환매출액(원)"].sum()
    ad_naver = {"platform": "네이버SA", "cost": nsa_cost,
                "revenue": nsa_rev, "roas": nsa_rev / max(nsa_cost, 1) * 100}
if not df_cpg.empty:
    cpg_cost = df_cpg["광고비"].sum()
    cpg_rev = df_cpg["총 전환매출액(1일)"].sum()
    ad_coupang = {"platform": "쿠팡", "cost": cpg_cost,
                  "revenue": cpg_rev, "roas": cpg_rev / max(cpg_cost, 1) * 100}

# 상품 분석
product_data = df_cur.groupby("상품명").agg(
    매출=("총 판매금액", "sum"), 수량=("수량", "sum"), 마진=("마진", "sum"),
).sort_values("매출", ascending=False).reset_index()
if not product_data.empty:
    product_data["마진율(%)"] = (product_data["마진"] / product_data["매출"].replace(0, 1) * 100).round(1)

# 브랜드 분석
brand_cur = df_cur.groupby("브랜드").agg(매출=("총 판매금액", "sum"), 수량=("수량", "sum"),
                                          마진=("마진", "sum")).sort_values("매출", ascending=False).reset_index()

# ═══════════════════════════════════════════════════════════════
#  AI 컨텍스트 사전 생성
# ═══════════════════════════════════════════════════════════════
_base_metrics = chat.summarize_metrics(
    현재매출=f"{cur_sales/1e8:.2f}억", 목표=f"{TARGET/1e8:.0f}억",
    목표갭=f"{gap/1e8:.2f}억", 남은일수=f"{days_remain}일",
    필요일평균=f"{needed_daily/1e6:.0f}백만", 월말예상=f"{projected/1e8:.1f}억",
    마진율=f"{margin_rate*100:.0f}%",
)

ai_contexts = {}

# 통합
_ctx_total = _base_metrics
if not channel_matrix.empty:
    _ctx_total += "\n" + chat.summarize_dataframe(channel_matrix, "채널 성장 매트릭스")
ai_contexts["통합 현황"] = _ctx_total

# 쿠팡광고
_ctx_cpg = _base_metrics
if not kw_coupang.empty:
    _ctx_cpg += "\n" + chat.summarize_dataframe(
        kw_coupang.groupby("Action_Group").agg(
            키워드수=("키워드","count"), 총광고비=("총비용","sum"),
            총매출=("총전환매출액","sum")).reset_index(), "쿠팡 키워드 그룹별 요약")
    _ctx_cpg += "\n" + chat.summarize_dataframe(kw_coupang.head(15), "쿠팡 키워드 상위")
if ad_coupang:
    _ctx_cpg += "\n" + chat.summarize_metrics(
        쿠팡_광고비=f"{ad_coupang['cost']:,.0f}", 쿠팡_전환매출=f"{ad_coupang['revenue']:,.0f}",
        쿠팡_ROAS=f"{ad_coupang['roas']:.0f}%")
ai_contexts["쿠팡 광고"] = _ctx_cpg

# 네이버광고
_ctx_nsa = _base_metrics
if not kw_naver.empty:
    _ctx_nsa += "\n" + chat.summarize_dataframe(
        kw_naver.groupby("Action_Group").agg(
            키워드수=("키워드","count"), 총광고비=("총비용","sum"),
            총매출=("총전환매출액","sum")).reset_index(), "네이버 키워드 그룹별 요약")
    _ctx_nsa += "\n" + chat.summarize_dataframe(kw_naver.head(15), "네이버 키워드 상위")
if ad_naver:
    _ctx_nsa += "\n" + chat.summarize_metrics(
        네이버_광고비=f"{ad_naver['cost']:,.0f}", 네이버_전환매출=f"{ad_naver['revenue']:,.0f}",
        네이버_ROAS=f"{ad_naver['roas']:.0f}%")
ai_contexts["네이버 광고"] = _ctx_nsa

# 브랜드
_ctx_brand = _base_metrics + "\n" + chat.summarize_dataframe(brand_cur.head(15), "브랜드별 매출")
ai_contexts["브랜드 점검"] = _ctx_brand

# 채널
_ctx_ch = _base_metrics
if not channel_matrix.empty:
    _ctx_ch += "\n" + chat.summarize_dataframe(channel_matrix, "채널 매트릭스")
if not ad_opportunities.empty:
    _ctx_ch += "\n" + chat.summarize_dataframe(
        ad_opportunities.sort_values("ROAS(%)", ascending=False).head(15), "캠페인 ROAS 순위")
ai_contexts["채널 점검"] = _ctx_ch

# 상품
_ctx_prod = _base_metrics + "\n" + chat.summarize_dataframe(product_data.head(20), "상품별 매출 Top20")
ai_contexts["상품 점검"] = _ctx_prod

# ═══════════════════════════════════════════════════════════════
#  페이지 레이아웃
# ═══════════════════════════════════════════════════════════════
S.page_header("NOW Action", "10억 달성을 위한 실시간 액션 플랜")

# Executive Summary (탭 위)
progress = min(cur_sales / TARGET, 1.0)
st.progress(progress, text=f"목표 달성률: {progress*100:.1f}% ({cur_sales/1e8:.2f}억 / {TARGET/1e8:.0f}억)")

c1, c2, c3, c4 = st.columns(4)
c1.metric("현재 매출", f"{cur_sales/1e8:.2f}억")
c2.metric("목표 갭", f"{gap/1e8:.2f}억" if gap > 0 else "달성!")
c3.metric("남은 일수", f"{days_remain}일")
c4.metric("필요 일평균", f"{needed_daily/1e6:.0f}백만" if days_remain > 0 else "-")

if projected >= TARGET:
    st.success(f"현재 추세대로면 월말 **{projected/1e8:.1f}억** 예상 — 목표 달성 가능!")
else:
    deficit = TARGET - projected
    st.warning(f"현재 추세대로면 **{projected/1e8:.1f}억** 예상 — **{deficit/1e8:.1f}억 부족**. 아래 액션을 즉시 실행하세요.")

st.markdown("")

# AI 패널 토글 + 레이아웃
main_col, ai_col = chat.setup_layout("p3")

with main_col:
    # ═══════════════════════════════════════════════════════════
    #  6탭 구성
    # ═══════════════════════════════════════════════════════════
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🎯 통합", "🟠 쿠팡광고", "🟢 네이버광고",
        "🏷️ 브랜드 점검", "📊 채널 점검", "📦 상품 점검",
    ])

    # ═══════════════════════════════════════════════════════════
    #  탭 1: 통합
    # ═══════════════════════════════════════════════════════════
    with tab1:
        # 우선순위 액션 리스트
        actions = ae.generate_actions(
            target=TARGET, current_sales=cur_sales,
            remaining_days=days_remain, daily_avg=daily_avg,
            needed_daily=needed_daily,
            grp_a=grp_a if grp_a is not None and not grp_a.empty else None,
            grp_b=grp_b if grp_b is not None and not grp_b.empty else None,
            grp_c=grp_c if grp_c is not None and not grp_c.empty else None,
            grp_d=grp_d if grp_d is not None and not grp_d.empty else None,
            margin_rate=margin_rate,
            channel_matrix=channel_matrix if not channel_matrix.empty else None,
            ad_opportunities=ad_opportunities if not ad_opportunities.empty else None,
            search_roas=search_roas, nonsearch_roas=nonsearch_roas,
        )

        if not actions:
            st.info("현재 데이터 기준 생성된 액션이 없습니다.")
        else:
            S.slide_header(f"오늘의 액션 리스트 ({len(actions)}건)", "Today's Action List")
            for act in actions:
                with st.container(border=True):
                    col_icon, col_content, col_impact = st.columns([1, 6, 2])
                    with col_icon:
                        st.markdown(f"### {act['icon']}")
                        st.caption(f"P{act['priority']}")
                    with col_content:
                        st.markdown(f"**{act['category']}**")
                        st.markdown(act["action"])
                    with col_impact:
                        st.metric("예상 임팩트", act["impact_text"])

        # 채널 효율 매트릭스
        if not channel_matrix.empty:
            st.markdown("")
            S.slide_header("채널 효율 매트릭스", "Channel Efficiency Matrix")
            fig_bubble = px.scatter(
                channel_matrix, x="최근2주 매출", y="성장률(%)",
                size="최근2주 매출", color="성장률(%)", text="채널",
                color_continuous_scale="RdYlGn", size_max=50,
            )
            fig_bubble.update_traces(textposition="top center")
            fig_bubble.add_hline(y=0, line_dash="dash", line_color="gray")
            fig_bubble.update_layout(template=TPL, height=450)
            st.plotly_chart(fig_bubble, use_container_width=True, key="p3_bubble_tab1")

        # 키워드 전체 요약
        if not kw_result.empty:
            st.markdown("")
            S.slide_header("키워드 전체 요약", "Keyword Overview")
            summary = aa.group_summary(kw_result)
            bep_roas = (1 / margin_rate) * 100 if margin_rate > 0 else 0
            st.info(f"마진율 **{margin_rate*100:.0f}%** → 손익분기 ROAS = **{bep_roas:.0f}%**")

            GROUP_INFO = {
                "A그룹_예산및입찰가증액": {"icon": "🟢", "label": "효자 키워드"},
                "B그룹_입찰가강력상승": {"icon": "🔵", "label": "잠재력 키워드"},
                "C그룹_즉시제외키워드": {"icon": "🔴", "label": "돈 먹는 하마"},
                "D그룹_판단유보": {"icon": "⚪", "label": "대기 키워드"},
            }
            cols_grp = st.columns(4)
            for i, grp_name in enumerate(GROUP_INFO):
                row = summary[summary["Action_Group"] == grp_name]
                info = GROUP_INFO[grp_name]
                with cols_grp[i]:
                    cnt = int(row["키워드수"].values[0]) if not row.empty else 0
                    profit = row["총순이익"].values[0] if not row.empty else 0
                    roas = row["평균ROAS"].values[0] if not row.empty else 0
                    with st.container(border=True):
                        st.markdown(f"{info['icon']} **{info['label']}**")
                        st.metric("키워드 수", f"{cnt}개")
                        st.metric("총 순이익", f"{profit:,.0f}원")
                        st.metric("평균 ROAS", f"{roas:.0f}%")

    # ═══════════════════════════════════════════════════════════
    #  탭 2: 쿠팡광고
    # ═══════════════════════════════════════════════════════════
    with tab2:
        if kw_coupang.empty and ad_coupang is None:
            st.warning("쿠팡 광고 데이터가 없습니다.")
        else:
            # KPI
            if ad_coupang:
                S.slide_header("쿠팡 광고 현황", "Coupang Ad Performance")
                ck1, ck2, ck3, ck4 = st.columns(4)
                ck1.metric("광고비", f"{ad_coupang['cost']/1e6:.1f}백만")
                ck2.metric("전환매출", f"{ad_coupang['revenue']/1e6:.1f}백만")
                ck3.metric("ROAS", f"{ad_coupang['roas']:.0f}%")
                margin_profit = (ad_coupang['revenue'] * margin_rate) - ad_coupang['cost']
                ck4.metric("순이익", f"{margin_profit/1e6:.1f}백만",
                           delta="흑자" if margin_profit > 0 else "적자")
                st.markdown("")

            # ══════════════════════════════════════════════════
            #  NEW: 검색/비검색 영역 분리 분석
            # ══════════════════════════════════════════════════
            if not df_ckw.empty:
                S.slide_header("검색 vs 비검색 영역 분석", "Search vs Non-Search Area")
                st.caption("쿠팡은 AI가 비검색 영역(키워드 '-')에 자동 노출합니다. 영역별 효율을 분리하여 광고 밸런스를 맞추세요.")

                cpg_area = aa.campaign_search_analysis(df_ckw)
                if not cpg_area.empty:
                    # 전체 검색/비검색 요약
                    area_total = cpg_area.groupby("노출영역", as_index=False).agg(
                        노출수=("노출수", "sum") if "노출수" in cpg_area.columns else ("노출영역", "count"),
                        클릭수=("클릭수", "sum") if "클릭수" in cpg_area.columns else ("노출영역", "count"),
                        광고비=("광고비", "sum") if "광고비" in cpg_area.columns else ("노출영역", "count"),
                        총전환매출액=("총전환매출액", "sum") if "총전환매출액" in cpg_area.columns else ("노출영역", "count"),
                    )
                    for _, row in area_total.iterrows():
                        ad_cost_vat = row.get("광고비", 0) * 1.1
                        rev = row.get("총전환매출액", 0)
                        roas = (rev / ad_cost_vat * 100) if ad_cost_vat > 0 else 0
                        ctr = (row.get("클릭수", 0) / row.get("노출수", 1) * 100) if row.get("노출수", 0) > 0 else 0
                        label = row["노출영역"]
                        color = "#3B82F6" if label == "검색" else "#F59E0B"
                        ac1, ac2, ac3, ac4 = st.columns(4)
                        ac1.metric(f"{label} 노출수", f"{row.get('노출수', 0):,.0f}")
                        ac2.metric(f"{label} 광고비(VAT)", f"{ad_cost_vat:,.0f}")
                        ac3.metric(f"{label} ROAS", f"{roas:.0f}%")
                        ac4.metric(f"{label} CTR", f"{ctr:.2f}%")

                    # 캠페인별 교차 분석
                    if "캠페인명" in cpg_area.columns:
                        st.markdown("#### 캠페인별 검색/비검색 효율 비교")
                        st.caption("비검색 ROAS가 낮으면 → 목표 ROAS 설정 상향으로 검색 노출 비중을 높이세요")
                        pivot_cols = ["캠페인명", "노출영역"]
                        disp_cols = pivot_cols + [c for c in ["노출수", "클릭수", "광고비(VAT)", "총전환매출액", "ROAS(%)", "CTR(%)", "CPC"] if c in cpg_area.columns]
                        st.dataframe(
                            cpg_area[[c for c in disp_cols if c in cpg_area.columns]].sort_values(
                                ["캠페인명", "노출영역"]),
                            use_container_width=True, hide_index=True,
                        )

                        # 시각화: 캠페인별 검색 vs 비검색 ROAS
                        if "ROAS(%)" in cpg_area.columns:
                            fig_area = px.bar(
                                cpg_area, x="캠페인명", y="ROAS(%)", color="노출영역",
                                barmode="group", title="캠페인별 검색/비검색 ROAS 비교",
                                color_discrete_map={"검색": "#3B82F6", "비검색": "#F59E0B"},
                            )
                            fig_area.add_hline(y=(1/margin_rate)*100, line_dash="dash",
                                              line_color="#EF4444", annotation_text="손익분기 ROAS")
                            fig_area.update_layout(height=400, template=TPL)
                            st.plotly_chart(fig_area, use_container_width=True, key="p3_cpg_area_roas")

            # ══════════════════════════════════════════════════
            #  NEW: 주차별 키워드 트렌드
            # ══════════════════════════════════════════════════
            if not df_ckw.empty:
                st.markdown("")
                S.slide_header("주차별 키워드 트렌드", "Weekly Keyword Trend")
                st.caption("일자별이 아닌 주차별로 집계하여 안정적인 트렌드를 파악합니다. 검색 키워드만 A/B/C/D 분류합니다.")

                weekly_cls = aa.weekly_keyword_classification(df_ckw, margin_rate=margin_rate)
                if not weekly_cls.empty:
                    # 주차별 검색/비검색 ROAS 추이
                    weekly_area = weekly_cls.groupby(["주차라벨", "노출영역"], as_index=False).agg(
                        광고비=("광고비", "sum") if "광고비" in weekly_cls.columns else ("노출영역", "count"),
                        총전환매출액=("총전환매출액", "sum") if "총전환매출액" in weekly_cls.columns else ("노출영역", "count"),
                        클릭수=("클릭수", "sum") if "클릭수" in weekly_cls.columns else ("노출영역", "count"),
                    )
                    if "광고비" in weekly_area.columns and "총전환매출액" in weekly_area.columns:
                        weekly_area["ROAS(%)"] = np.where(
                            weekly_area["광고비"] > 0,
                            weekly_area["총전환매출액"] / (weekly_area["광고비"] * 1.1) * 100, 0)
                        fig_wk = px.line(weekly_area, x="주차라벨", y="ROAS(%)",
                                        color="노출영역", markers=True,
                                        title="주차별 검색/비검색 ROAS 추이",
                                        color_discrete_map={"검색": "#3B82F6", "비검색": "#F59E0B"})
                        fig_wk.add_hline(y=(1/margin_rate)*100, line_dash="dash",
                                        line_color="#EF4444", annotation_text="손익분기")
                        fig_wk.update_layout(height=350, template=TPL)
                        st.plotly_chart(fig_wk, use_container_width=True, key="p3_cpg_weekly_roas")

                    # 검색 키워드 주차별 분류 결과
                    search_weekly = weekly_cls[weekly_cls["노출영역"] == "검색"]
                    if not search_weekly.empty and "Action_Group" in search_weekly.columns:
                        st.markdown("#### 검색 키워드 주차별 등급 분포")
                        grp_weekly = search_weekly.groupby(["주차라벨", "Action_Group"]).size().reset_index(name="키워드수")
                        fig_grp = px.bar(grp_weekly, x="주차라벨", y="키워드수",
                                        color="Action_Group", barmode="stack",
                                        title="주차별 키워드 등급 분포",
                                        color_discrete_map={
                                            "A그룹_예산및입찰가증액": "#28a745",
                                            "B그룹_입찰가강력상승": "#ffc107",
                                            "C그룹_즉시제외키워드": "#dc3545",
                                            "D그룹_판단유보": "#6c757d",
                                        })
                        fig_grp.update_layout(height=350, template=TPL)
                        st.plotly_chart(fig_grp, use_container_width=True, key="p3_cpg_weekly_grp")

                        # 최신 주차 키워드 분류 테이블
                        latest_week = search_weekly["주차라벨"].max()
                        latest_kw = search_weekly[search_weekly["주차라벨"] == latest_week].copy()
                        if not latest_kw.empty:
                            st.markdown(f"#### 최신 주차 ({latest_week}) 검색 키워드 분류")
                            show_cols = [c for c in ["키워드", "캠페인명", "노출수", "클릭수",
                                                     "CTR(%)", "ROAS(%)", "CPC", "Action_Group"]
                                        if c in latest_kw.columns]
                            st.dataframe(
                                latest_kw[show_cols].sort_values("Action_Group"),
                                use_container_width=True, hide_index=True, height=400,
                            )

            # ══════════════════════════════════════════════════
            #  기존: 캠페인 성과
            # ══════════════════════════════════════════════════
            if not df_cpg.empty:
                st.markdown("")
                S.slide_header("쿠팡 캠페인 성과", "Coupang Campaign Performance")
                cpg_camp = df_cpg.groupby("캠페인명").agg(
                    광고비=("광고비", "sum"), 전환매출=("총 전환매출액(1일)", "sum"),
                    클릭수=("클릭수", "sum"), 노출수=("노출수", "sum"),
                    주문수=("총 주문수(1일)", "sum"),
                ).reset_index()
                cpg_camp["ROAS(%)"] = (cpg_camp["전환매출"] / cpg_camp["광고비"].replace(0, 1) * 100).round(0)
                cpg_camp = cpg_camp.sort_values("광고비", ascending=False)
                st.dataframe(cpg_camp, use_container_width=True, hide_index=True)

            # ── 캠페인별 액션 플랜 (검색/비검색 분리) ──
            if not kw_coupang.empty and "캠페인명" in kw_coupang.columns:
                st.markdown("")
                S.slide_header("캠페인별 액션 플랜", "Campaign Action Plan")
                st.caption("검색 키워드와 비검색영역('-')을 분리 분석합니다. 비검색 효율이 낮으면 목표ROAS를 상향하세요.")
                camp_actions = ae.analyze_campaign_actions(kw_coupang, campaign_col="캠페인명", margin_rate=margin_rate)
                for ca in camp_actions:
                    ns_label = f" | 비검색 ROAS {ca.get('nonsearch_roas', 0):.0f}%" if ca.get('nonsearch_count', 0) > 0 else ""
                    with st.expander(
                        f"{ca['verdict']}  **{ca['campaign']}** — "
                        f"ROAS {ca['roas']:.0f}% | 광고비 {ae.fmt_money(ca['cost'])} | "
                        f"검색KW {ca['keywords_total']}개{ns_label}",
                        expanded=(ca['priority_score'] >= 30),
                    ):
                        # KPI 요약 - 전체
                        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
                        mc1.metric("총 광고비", ae.fmt_money(ca['cost']))
                        mc2.metric("총 전환매출", ae.fmt_money(ca['revenue']))
                        mc3.metric("종합 ROAS", f"{ca['roas']:.0f}%")
                        mc4.metric("순이익", ae.fmt_money(ca['profit']),
                                   delta="흑자" if ca['profit'] > 0 else "적자")
                        gc = ca['group_counts']
                        mc5.metric("검색KW", f"A:{gc['A']} B:{gc['B']} C:{gc['C']} D:{gc['D']}")

                        # 검색/비검색 분리 KPI
                        if ca.get('nonsearch_count', 0) > 0:
                            st.markdown("---")
                            st.markdown("**검색 vs 비검색 영역 비교**")
                            sc1, sc2, sc3 = st.columns(3)
                            with sc1:
                                st.metric("검색 광고비", ae.fmt_money(ca.get('search_cost', 0)))
                                st.metric("검색 ROAS", f"{ca.get('search_roas', 0):.0f}%")
                            with sc2:
                                st.metric("비검색 광고비", ae.fmt_money(ca.get('nonsearch_cost', 0)))
                                st.metric("비검색 ROAS", f"{ca.get('nonsearch_roas', 0):.0f}%")
                            with sc3:
                                ratio = (ca.get('nonsearch_cost', 0) / ca['cost'] * 100) if ca['cost'] > 0 else 0
                                st.metric("비검색 비중", f"{ratio:.0f}%")
                                diff = ca.get('search_roas', 0) - ca.get('nonsearch_roas', 0)
                                st.metric("ROAS 차이", f"{diff:+.0f}%p")

                        st.markdown("---")

                        # 액션 리스트
                        for act in ca['actions']:
                            urgency_color = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}.get(act['urgency'], "")
                            st.markdown(f"{act['icon']} **{act['label']}** {urgency_color}")
                            st.markdown(f"  _{act['detail']}_")
                            if 'keywords' in act and act['keywords']:
                                st.code(", ".join(act['keywords'][:10]), language=None)

            # ── 심화 분석 ──
            st.markdown("")
            S.slide_header("쿠팡 심화 분석", "Coupang Deep Analysis")
            # 캐시 키 계산
            _cpg_hash = _quick_hash(df_ckw) + _quick_hash(kw_coupang) + str(min_clicks_stat)
            if st.session_state.get("_cpg_hash") != _cpg_hash:
                st.session_state["_cpg_hash"] = _cpg_hash
                st.session_state["_cpg_cpc_ctr"] = aa.analyze_cpc_ctr_matrix(kw_coupang, min_clicks=min_clicks_stat) if not kw_coupang.empty else pd.DataFrame()
                st.session_state["_cpg_dow"] = aa.analyze_day_of_week(df_ckw) if not df_ckw.empty else pd.DataFrame()
                st.session_state["_cpg_di"] = aa.analyze_direct_indirect(df_ckw) if not df_ckw.empty else pd.DataFrame()
                st.session_state["_cpg_imp"] = aa.analyze_impression_trend(df_ckw) if not df_ckw.empty else pd.DataFrame()

            cpg_sub1, cpg_sub2, cpg_sub3, cpg_sub4 = st.tabs([
                "🎯 CPC×CTR 매트릭스", "📅 요일별 효율",
                "🔄 직접/간접 전환", "📉 노출 추이",
            ])

            # ── CPC×CTR 매트릭스 ──
            with cpg_sub1:
                if kw_coupang.empty:
                    st.info("쿠팡 키워드 데이터가 없습니다.")
                else:
                    cpg_matrix = st.session_state.get("_cpg_cpc_ctr", pd.DataFrame())
                    if cpg_matrix.empty:
                        st.info("CPC×CTR 분석을 위한 충분한 데이터가 없습니다.")
                    else:
                        st.markdown("#### CPC × CTR 4분면 (시장 경쟁·매력도)")
                        st.caption("고CTR+저CPC = 노다지 / 저CTR+고CPC = 돈낭비")

                        quadrant_counts = cpg_matrix["CPC_CTR구간"].value_counts()
                        qc = st.columns(4)
                        q_info = [
                            ("🟢 노다지 (고CTR+저CPC)", "예산 우선 배정"),
                            ("🟡 경쟁격전 (고CTR+고CPC)", "전환율 확보 집중"),
                            ("⚪ 무관심 (저CTR+저CPC)", "소재 교체 또는 제외"),
                            ("🔴 돈낭비 (저CTR+고CPC)", "즉시 중단"),
                        ]
                        for i, (q_name, q_action) in enumerate(q_info):
                            cnt = quadrant_counts.get(q_name, 0)
                            with qc[i]:
                                with st.container(border=True):
                                    st.markdown(f"**{q_name.split(' ')[0]} {q_name.split('(')[1].rstrip(')')}")
                                    st.metric("키워드", f"{cnt}개")
                                    st.caption(q_action)

                        cpc_med = cpg_matrix["CPC중앙값"].iloc[0]
                        ctr_med = cpg_matrix["CTR중앙값"].iloc[0]

                        fig_cpg_cpc = px.scatter(
                            cpg_matrix, x="CPC", y="CTR(%)",
                            color="CPC_CTR구간", hover_name="키워드",
                            size="클릭수", size_max=40,
                            hover_data={"ROAS(%)": ":.0f", "총비용": ":,.0f"},
                            color_discrete_map={
                                "🟢 노다지 (고CTR+저CPC)": "#28a745",
                                "🟡 경쟁격전 (고CTR+고CPC)": "#ffc107",
                                "⚪ 무관심 (저CTR+저CPC)": "#6c757d",
                                "🔴 돈낭비 (저CTR+고CPC)": "#dc3545",
                            },
                        )
                        fig_cpg_cpc.add_vline(x=cpc_med, line_dash="dash", line_color="gray",
                                              annotation_text=f"CPC 중앙값 {cpc_med:,.0f}원")
                        fig_cpg_cpc.add_hline(y=ctr_med, line_dash="dash", line_color="gray",
                                              annotation_text=f"CTR 중앙값 {ctr_med:.2f}%")
                        fig_cpg_cpc.update_layout(height=550, template=TPL,
                                                  xaxis_title="CPC (원)", yaxis_title="CTR (%)")
                        st.plotly_chart(fig_cpg_cpc, use_container_width=True, key="p3_cpg_cpc_ctr")

                        # 노다지 키워드
                        goldmine = cpg_matrix[cpg_matrix["CPC_CTR구간"].str.contains("노다지")]
                        if not goldmine.empty:
                            st.markdown("#### 🟢 노다지 키워드 — 예산 우선 배정 추천")
                            gm_cols = [c for c in ["키워드", "클릭수", "CTR(%)", "CPC",
                                                   "총비용", "총전환수", "총전환매출액", "ROAS(%)"]
                                       if c in goldmine.columns]
                            st.dataframe(goldmine[gm_cols].sort_values("클릭수", ascending=False),
                                         use_container_width=True, hide_index=True)

                        # 돈낭비 키워드
                        waste = cpg_matrix[cpg_matrix["CPC_CTR구간"].str.contains("돈낭비")]
                        if not waste.empty:
                            st.markdown("#### 🔴 돈낭비 키워드 — 즉시 중단 추천")
                            wt_cols = [c for c in ["키워드", "클릭수", "CTR(%)", "CPC",
                                                   "총비용", "총전환수", "총전환매출액", "ROAS(%)"]
                                       if c in waste.columns]
                            st.dataframe(waste[wt_cols].sort_values("총비용", ascending=False),
                                         use_container_width=True, hide_index=True)

            # ── 요일별 효율 ──
            with cpg_sub2:
                if df_ckw.empty:
                    st.info("쿠팡 키워드 일별 데이터가 없습니다.")
                else:
                    cpg_dow = st.session_state.get("_cpg_dow", pd.DataFrame())
                    if cpg_dow.empty:
                        st.info("요일별 분석을 위한 데이터가 부족합니다.")
                    else:
                        st.markdown("#### 요일별 광고 효율 분석")
                        st.caption("어느 요일에 가장 효율이 좋은지 파악하여 예산 집중 배분")

                        if "효율등급" in cpg_dow.columns:
                            dc = st.columns(7)
                            for i, (_, row) in enumerate(cpg_dow.iterrows()):
                                with dc[i % 7]:
                                    with st.container(border=True):
                                        st.markdown(f"**{row['요일']}**")
                                        roas_val = row.get("ROAS(%)", 0)
                                        st.metric("ROAS", f"{roas_val:.0f}%")
                                        st.caption(row.get("효율등급", ""))

                        if "ROAS(%)" in cpg_dow.columns:
                            fig_cpg_dow = px.bar(
                                cpg_dow, x="요일", y="ROAS(%)",
                                color="ROAS(%)", color_continuous_scale="RdYlGn",
                                text=cpg_dow["ROAS(%)"].apply(lambda x: f"{x:.0f}%"),
                            )
                            avg_roas = cpg_dow["ROAS(%)"].mean()
                            fig_cpg_dow.add_hline(y=avg_roas, line_dash="dash", line_color="red",
                                                  annotation_text=f"평균 {avg_roas:.0f}%")
                            fig_cpg_dow.update_layout(height=400, template=TPL)
                            st.plotly_chart(fig_cpg_dow, use_container_width=True, key="p3_cpg_dow_roas")

                        if "CTR(%)" in cpg_dow.columns:
                            fig_cpg_ctr = px.line(cpg_dow, x="요일", y="CTR(%)", markers=True,
                                                  text=cpg_dow["CTR(%)"].apply(lambda x: f"{x:.2f}%"))
                            fig_cpg_ctr.update_traces(textposition="top center")
                            fig_cpg_ctr.update_layout(height=300, template=TPL, title="요일별 CTR")
                            st.plotly_chart(fig_cpg_ctr, use_container_width=True, key="p3_cpg_dow_ctr")

                        st.markdown("#### 요일별 상세 데이터")
                        dow_disp = cpg_dow[["요일"] + [c for c in cpg_dow.columns
                                                       if c.startswith("일평균") or c in ["ROAS(%)", "CTR(%)", "효율등급"]]].copy()
                        st.dataframe(dow_disp, use_container_width=True, hide_index=True)

            # ── 직접/간접 전환 ──
            with cpg_sub3:
                if df_ckw.empty:
                    st.info("쿠팡 키워드 데이터가 없습니다.")
                else:
                    di_df = st.session_state.get("_cpg_di", pd.DataFrame())
                    if di_df.empty:
                        st.info("직접/간접 전환 분석 데이터가 부족합니다.")
                    else:
                        st.markdown("#### 🔄 직접 vs 간접 전환 분석")
                        st.caption("간접전환 = 광고 클릭 후 14일 내 구매 (1일 ROAS만 보면 과소평가)")

                        # 전환유형 분포
                        type_dist = di_df["전환유형"].value_counts()
                        tc = st.columns(min(len(type_dist), 4))
                        for i, (label, cnt) in enumerate(type_dist.items()):
                            with tc[i % 4]:
                                with st.container(border=True):
                                    st.markdown(f"**{label}**")
                                    st.metric("키워드", f"{cnt}개")

                        # ROAS 비교 차트 (1일 vs 14일)
                        roas_compare = di_df[di_df["ROAS_14일(%)"] > 0].nlargest(20, "ROAS_상승폭(%)")
                        if not roas_compare.empty:
                            st.markdown("#### ROAS 비교: 1일 vs 14일 (상승폭 Top 20)")
                            fig_roas = go.Figure()
                            fig_roas.add_trace(go.Bar(
                                x=roas_compare["키워드"], y=roas_compare["ROAS_1일(%)"],
                                name="1일 ROAS", marker_color="#ff7f0e",
                            ))
                            fig_roas.add_trace(go.Bar(
                                x=roas_compare["키워드"], y=roas_compare["ROAS_14일(%)"],
                                name="14일 ROAS", marker_color="#1f77b4",
                            ))
                            fig_roas.update_layout(barmode="group", height=450, template=TPL,
                                                   xaxis_tickangle=-45)
                            st.plotly_chart(fig_roas, use_container_width=True, key="p3_cpg_roas_comp")

                        # 간접전환 우세 키워드 (과소평가 위험)
                        indirect_heavy = di_df[di_df["전환유형"].str.contains("간접전환 우세")].sort_values(
                            "간접전환비율(%)", ascending=False
                        )
                        if not indirect_heavy.empty:
                            st.markdown("#### 🟣 간접전환 우세 키워드 (1일 ROAS로 판단하면 과소평가)")
                            ih_cols = [c for c in ["키워드", "클릭수", "광고비",
                                                   "직접전환비율(%)", "간접전환비율(%)",
                                                   "ROAS_1일(%)", "ROAS_14일(%)", "ROAS_상승폭(%)"]
                                       if c in indirect_heavy.columns]
                            st.dataframe(indirect_heavy[ih_cols].head(20),
                                         use_container_width=True, hide_index=True)

                        # 전체 테이블
                        st.markdown("#### 전체 키워드 직접/간접 전환 분석")
                        di_cols = [c for c in ["키워드", "클릭수", "광고비", "전환유형",
                                               "직접전환비율(%)", "간접전환비율(%)",
                                               "ROAS_1일(%)", "ROAS_14일(%)", "ROAS_상승폭(%)"]
                                   if c in di_df.columns]
                        st.dataframe(
                            di_df[di_cols].sort_values("광고비", ascending=False),
                            use_container_width=True, hide_index=True, height=500,
                        )

            # ── 노출 추이 ──
            with cpg_sub4:
                if df_ckw.empty:
                    st.info("쿠팡 키워드 일별 데이터가 없습니다.")
                else:
                    cpg_imp = st.session_state.get("_cpg_imp", pd.DataFrame())
                    if cpg_imp.empty:
                        st.info("노출 추이 분석 데이터가 부족합니다.")
                    else:
                        st.markdown("#### 노출수(SOV) 추이 분석")

                        trend_label = cpg_imp["노출추이"].iloc[0] if "노출추이" in cpg_imp.columns else ""
                        change_pct = cpg_imp["노출변화율(%)"].iloc[0] if "노출변화율(%)" in cpg_imp.columns else 0

                        ic1, ic2 = st.columns(2)
                        ic1.metric("노출 추이", trend_label)
                        ic2.metric("전반기→후반기 변화", f"{change_pct:+.1f}%")

                        fig_cpg_imp = go.Figure()
                        fig_cpg_imp.add_trace(go.Bar(
                            x=cpg_imp["날짜"], y=cpg_imp["노출수"],
                            name="일별 노출수", marker_color="#aec7e8", opacity=0.6,
                        ))
                        if "노출수_MA7" in cpg_imp.columns:
                            fig_cpg_imp.add_trace(go.Scatter(
                                x=cpg_imp["날짜"], y=cpg_imp["노출수_MA7"],
                                name="7일 이동평균", line=dict(color="#1f77b4", width=3),
                            ))
                        fig_cpg_imp.update_layout(height=450, template=TPL, title="일별 노출수 추이")
                        st.plotly_chart(fig_cpg_imp, use_container_width=True, key="p3_cpg_imp_trend")

                        if "클릭수" in cpg_imp.columns:
                            fig_cpg_click = go.Figure()
                            fig_cpg_click.add_trace(go.Scatter(
                                x=cpg_imp["날짜"], y=cpg_imp["클릭수"],
                                name="일별 클릭수", fill="tozeroy", line=dict(color="#28a745"),
                            ))
                            fig_cpg_click.update_layout(height=300, template=TPL, title="일별 클릭수 추이")
                            st.plotly_chart(fig_cpg_click, use_container_width=True, key="p3_cpg_click_trend")

            # 예산 시뮬레이션
            if ad_coupang:
                st.markdown("")
                _render_budget_sim(ad_coupang, "cpg", margin_rate)

    # ═══════════════════════════════════════════════════════════
    #  탭 3: 네이버광고 (API 직접 연동 상세분석)
    # ═══════════════════════════════════════════════════════════
    with tab3:
        import naver_ad_api as napi
        import naver_ad_analyzer as naa

        # 계정 선택
        acc_names = [a["name"] for a in config.NAVER_AD_ACCOUNTS]
        selected_acc_idx = st.selectbox(
            "📋 광고 계정", range(len(acc_names)),
            format_func=lambda i: acc_names[i], key="p3_naver_acc",
        )
        acc = config.NAVER_AD_ACCOUNTS[selected_acc_idx]

        # 날짜 범위
        nc1, nc2 = st.columns(2)
        with nc1:
            nsa_start = st.date_input("시작일", value=date.today() - timedelta(days=30), key="p3_nsa_start")
        with nc2:
            nsa_end = st.date_input("종료일", value=date.today() - timedelta(days=1), key="p3_nsa_end")

        # API 호출 (캐시)
        @st.cache_data(ttl=300, show_spinner="네이버 광고 API 데이터 수집 중...")
        def _fetch_naver_data(_acc_key, _acc_secret, _acc_cid, start_str, end_str):
            client = napi.NaverAdClient(_acc_key, _acc_secret, _acc_cid)
            camps = client.fetch_campaign_stats(start_str, end_str)
            adgroups = client.fetch_adgroup_stats(start_date=start_str, end_date=end_str)
            keywords = client.fetch_keyword_stats(start_date=start_str, end_date=end_str)
            daily = client.fetch_keyword_daily_stats(start_date=start_str, end_date=end_str)
            return camps, adgroups, keywords, daily

        if st.button("🔄 데이터 새로고침", key="p3_nsa_refresh", type="primary"):
            st.cache_data.clear()

        try:
            nsa_camps, nsa_adgroups, nsa_keywords, nsa_daily = _fetch_naver_data(
                acc["api_key"], acc["secret_key"], acc["customer_id"],
                str(nsa_start), str(nsa_end),
            )
        except Exception as e:
            st.error(f"API 오류: {e}")
            nsa_camps = nsa_adgroups = nsa_keywords = nsa_daily = pd.DataFrame()

        if nsa_keywords.empty:
            st.warning("키워드 데이터가 없습니다. 활성 캠페인을 확인하세요.")
        else:
            # 전체 분석 실행
            _target_roas = st.sidebar.number_input("목표 ROAS(%)", value=500, step=50, key="p3_target_roas")
            _nsa_hash = _quick_hash(nsa_keywords) + _quick_hash(nsa_adgroups) + _quick_hash(nsa_daily) + f"{margin_rate}_{_target_roas}"
            if st.session_state.get("_nsa_hash") != _nsa_hash:
                st.session_state["_nsa_hash"] = _nsa_hash
                st.session_state["_nsa_analysis"] = naa.full_analysis(
                    keyword_df=nsa_keywords,
                    adgroup_df=nsa_adgroups if not nsa_adgroups.empty else None,
                    daily_df=nsa_daily if not nsa_daily.empty else None,
                    margin_rate=margin_rate,
                    target_roas=_target_roas,
                )
            analysis = st.session_state["_nsa_analysis"]
            kw_analyzed = analysis["keywords"]
            summary = analysis["summary"]

            # ── KPI 요약 ──
            S.slide_header(f"{acc['name']} 네이버SA 광고 현황", "Naver SA Ad Performance")
            nk1, nk2, nk3, nk4, nk5 = st.columns(5)
            nk1.metric("총 광고비", f"{summary['총 광고비']/1e6:.1f}백만")
            nk2.metric("전환매출", f"{summary['총 전환매출']/1e6:.1f}백만")
            nk3.metric("ROAS", f"{summary['전체 ROAS(%)']:.0f}%")
            nk4.metric("순이익", f"{summary['총 순이익']/1e6:.1f}백만",
                        delta="흑자" if summary["총 순이익"] > 0 else "적자")
            nk5.metric("키워드", f"{summary['총 키워드 수']}개")
            st.markdown("")

            # ── 서브탭 ──
            nsub1, nsub2, nsub3, nsub4, nsub5, nsub6, nsub7, nsub8, nsub9, nsub10, nsub11 = st.tabs([
                "📊 키워드 분석", "💰 입찰가 추천", "📈 트렌드",
                "🏷️ 광고그룹", "📋 캠페인",
                "⚡ 실시간 모니터링", "💳 잔액/예산 알림",
                "🎯 CPC×CTR 매트릭스", "📅 요일별 효율", "📉 노출 추이",
                "🔍 스토어×광고 교차",
            ])

            # ── 서브탭1: 키워드 분석 ──
            with nsub1:
                # 세부 그룹 카드
                st.markdown("#### 키워드 8분면 분류")
                group_counts = kw_analyzed["세부그룹"].value_counts()
                GROUP_META = {
                    "A1_고효율_고볼륨": ("🟢", "효자-대형"),
                    "A2_고효율_저볼륨": ("🟢", "효자-소형"),
                    "B1_전환있는_잠재력": ("🔵", "잠재력"),
                    "B2_노출만_많은_잠재력": ("🔵", "소재개선"),
                    "C1_고비용_무전환": ("🔴", "즉시제외"),
                    "C2_고비용_저전환": ("🔴", "입찰하향"),
                    "D_데이터부족": ("⚪", "판단유보"),
                }
                gcols = st.columns(min(len(GROUP_META), 4))
                for i, (grp, (icon, label)) in enumerate(GROUP_META.items()):
                    cnt = group_counts.get(grp, 0)
                    grp_data = kw_analyzed[kw_analyzed["세부그룹"] == grp]
                    profit = grp_data["순이익"].sum() if not grp_data.empty else 0
                    with gcols[i % 4]:
                        with st.container(border=True):
                            st.markdown(f"{icon} **{label}**")
                            st.metric("키워드", f"{cnt}개")
                            st.metric("순이익", f"{profit:,.0f}원")

                # 품질지수 분포
                st.markdown("")
                qi_col1, qi_col2 = st.columns([1, 1])
                with qi_col1:
                    st.markdown("#### 품질지수 분포")
                    qi_dist = kw_analyzed["품질등급"].value_counts()
                    fig_qi = px.pie(
                        values=qi_dist.values, names=qi_dist.index,
                        color=qi_dist.index,
                        color_discrete_map={"상": "#28a745", "중": "#ffc107", "하": "#dc3545", "미측정": "#6c757d"},
                    )
                    fig_qi.update_layout(height=300)
                    st.plotly_chart(fig_qi, use_container_width=True, key="p3_qi_pie")

                with qi_col2:
                    st.markdown("#### 그룹별 ROAS 비교")
                    grp_roas = kw_analyzed.groupby("세부그룹").agg(
                        ROAS=("ROAS(%)", "mean"), 광고비=("광고비(VAT포함)", "sum"),
                    ).reset_index()
                    fig_groas = px.bar(
                        grp_roas, x="세부그룹", y="ROAS", color="세부그룹",
                        text=grp_roas["ROAS"].apply(lambda x: f"{x:.0f}%"),
                    )
                    fig_groas.update_layout(height=300, showlegend=False, template=TPL)
                    st.plotly_chart(fig_groas, use_container_width=True, key="p3_groas_bar")

                # 4분면 스캐터
                st.markdown("#### 키워드 4분면 (광고비 vs 순이익)")
                scatter_kw = kw_analyzed[kw_analyzed["클릭수"] >= min_clicks_stat]
                if not scatter_kw.empty:
                    color_map = {
                        "A그룹_예산증액": "#28a745", "B그룹_최적화": "#007bff",
                        "C그룹_제외": "#dc3545", "D그룹_판단유보": "#6c757d",
                    }
                    fig_kw = px.scatter(
                        scatter_kw, x="광고비(VAT포함)", y="순이익",
                        color="Action_Group", size="클릭수", hover_name="키워드",
                        hover_data={"ROAS(%)": ":.0f", "품질지수": True, "입찰가": ":,.0f"},
                        color_discrete_map=color_map, size_max=40,
                    )
                    fig_kw.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="손익분기선")
                    fig_kw.update_layout(height=500, template=TPL)
                    st.plotly_chart(fig_kw, use_container_width=True, key="p3_nsa_scatter")

                # 키워드 테이블
                st.markdown("#### 키워드 상세 테이블")
                kw_display_cols = [c for c in [
                    "키워드", "캠페인명", "광고그룹명", "세부그룹", "노출수", "클릭수",
                    "광고비(VAT포함)", "전환수", "전환매출액", "ROAS(%)", "CTR(%)",
                    "평균CPC", "품질지수", "평균순위", "입찰가", "순이익",
                ] if c in kw_analyzed.columns]
                st.dataframe(
                    kw_analyzed[kw_display_cols].sort_values("광고비(VAT포함)", ascending=False),
                    use_container_width=True, hide_index=True, height=500,
                )

            # ── 서브탭2: 입찰가 추천 ──
            with nsub2:
                st.markdown("#### 입찰가 변경 추천")
                bid_cols = [c for c in [
                    "키워드", "광고그룹명", "클릭수", "ROAS(%)", "품질지수",
                    "입찰가", "적정CPC", "추천입찰가", "입찰가변경률(%)", "입찰가액션",
                ] if c in kw_analyzed.columns]
                bid_df = kw_analyzed[kw_analyzed["클릭수"] >= min_clicks_stat][bid_cols].copy()
                bid_df = bid_df.sort_values("입찰가변경률(%)", ascending=False)

                # 요약
                bc1, bc2, bc3 = st.columns(3)
                bc1.metric("인상 추천", f"{summary['입찰가 인상 추천']}개")
                bc2.metric("인하 추천", f"{summary['입찰가 인하 추천']}개")
                bc3.metric("유지", f"{(kw_analyzed.get('입찰가액션', pd.Series('')).str.contains('유지')).sum()}개")

                st.dataframe(bid_df, use_container_width=True, hide_index=True, height=500)

                # CSV 다운로드
                csv = bid_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "📥 입찰가 추천 CSV 다운로드", data=csv,
                    file_name=f"naver_bid_recommend_{acc['name']}_{nsa_end}.csv",
                    mime="text/csv", key="p3_bid_csv",
                )

            # ── 서브탭3: 트렌드 ──
            with nsub3:
                trends = analysis["trends"]
                if trends.empty:
                    st.info("일별 데이터가 부족합니다.")
                else:
                    st.markdown("#### 키워드 트렌드 (최근 7일 vs 이전)")

                    # 트렌드 분포
                    trend_dist = trends["트렌드"].value_counts()
                    tc = st.columns(min(len(trend_dist), 5))
                    for i, (label, cnt) in enumerate(trend_dist.items()):
                        with tc[i % 5]:
                            st.metric(label, f"{cnt}개")

                    st.markdown("")

                    # 급상승 키워드
                    rising = trends[trends["트렌드"].str.contains("급상승")].sort_values(
                        "클릭수_변화율(%)", ascending=False
                    )
                    if not rising.empty:
                        st.markdown("#### 🚀 급상승 키워드")
                        trend_cols = [c for c in [
                            "키워드", "클릭수_최근", "클릭수_이전", "클릭수_변화율(%)",
                            "ROAS_최근(%)", "ROAS_이전(%)", "트렌드",
                        ] if c in rising.columns]
                        st.dataframe(rising[trend_cols].head(20), use_container_width=True, hide_index=True)

                    # 하락 키워드
                    falling = trends[trends["트렌드"].str.contains("하락")].sort_values(
                        "클릭수_변화율(%)", ascending=True
                    )
                    if not falling.empty:
                        st.markdown("#### 🔻 하락세 키워드")
                        st.dataframe(falling[trend_cols].head(20), use_container_width=True, hide_index=True)

            # ── 서브탭4: 광고그룹 ──
            with nsub4:
                ag_result = analysis["adgroups"]
                if ag_result.empty:
                    st.info("광고그룹 데이터가 없습니다.")
                else:
                    st.markdown("#### 광고그룹 최적화 점수")
                    ag_cols = [c for c in [
                        "광고그룹명", "최적화등급", "최적화점수", "ROAS점수", "CTR점수",
                        "CVR점수", "KW점수", "노출수", "클릭수", "광고비(VAT포함)",
                        "전환수", "전환매출액", "ROAS(%)", "입찰가",
                    ] if c in ag_result.columns]
                    ag_display = ag_result[ag_cols].sort_values("최적화점수", ascending=False)

                    # 등급 분포
                    grade_dist = ag_result["최적화등급"].value_counts()
                    gc = st.columns(min(len(grade_dist), 4))
                    for i, (grade, cnt) in enumerate(grade_dist.items()):
                        with gc[i % 4]:
                            st.metric(grade, f"{cnt}개")

                    st.dataframe(ag_display, use_container_width=True, hide_index=True, height=400)

            # ── 서브탭5: 캠페인 ──
            with nsub5:
                if nsa_camps.empty:
                    st.info("캠페인 데이터가 없습니다.")
                else:
                    st.markdown("#### 캠페인별 성과")
                    camp_cols = [c for c in [
                        "캠페인명", "상태", "노출수", "클릭수", "광고비(VAT포함)",
                        "전환수", "전환매출액", "ROAS(%)", "CTR(%)", "평균CPC",
                    ] if c in nsa_camps.columns]
                    camp_display = nsa_camps[camp_cols].sort_values("광고비(VAT포함)", ascending=False)
                    st.dataframe(camp_display, use_container_width=True, hide_index=True)

                    # 캠페인 ROAS 바 차트
                    active_camps = nsa_camps[nsa_camps.get("상태", pd.Series("")) == "ELIGIBLE"]
                    if not active_camps.empty and "ROAS(%)" in active_camps.columns:
                        fig_camp = px.bar(
                            active_camps.sort_values("ROAS(%)", ascending=True),
                            x="ROAS(%)", y="캠페인명", orientation="h",
                            text=active_camps.sort_values("ROAS(%)", ascending=True)["ROAS(%)"].apply(
                                lambda x: f"{x:.0f}%"
                            ),
                            color="ROAS(%)", color_continuous_scale="RdYlGn",
                        )
                        fig_camp.update_layout(height=max(300, len(active_camps) * 40), template=TPL)
                        st.plotly_chart(fig_camp, use_container_width=True, key="p3_camp_roas")

                    # ── 캠페인별 꼼꼼한 액션 ──
                    if not nsa_keywords.empty and "캠페인" in nsa_keywords.columns:
                        st.markdown("")
                        st.markdown("#### 📋 캠페인별 액션 플랜")
                        st.caption("각 캠페인의 키워드를 분석하여 구체적 액션을 자동 도출합니다.")
                        nsa_camp_actions = ae.analyze_campaign_actions(nsa_keywords, campaign_col="캠페인", margin_rate=margin_rate)
                        for nca in nsa_camp_actions:
                            with st.expander(
                                f"{nca['verdict']}  **{nca['campaign']}** — ROAS {nca['roas']:.0f}% | "
                                f"광고비 {ae.fmt_money(nca['cost'])} | 키워드 {nca['keywords_total']}개",
                                expanded=(nca['priority_score'] >= 30)
                            ):
                                nc1, nc2, nc3, nc4, nc5 = st.columns(5)
                                nc1.metric("광고비", ae.fmt_money(nca['cost']))
                                nc2.metric("전환매출", ae.fmt_money(nca['revenue']))
                                nc3.metric("ROAS", f"{nca['roas']:.0f}%")
                                nc4.metric("순이익", ae.fmt_money(nca['profit']),
                                           delta="흑자" if nca['profit'] > 0 else "적자")
                                ngc = nca['group_counts']
                                nc5.metric("키워드", f"A:{ngc['A']} B:{ngc['B']} C:{ngc['C']} D:{ngc['D']}")

                                for nact in nca['actions']:
                                    urg_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}.get(nact['urgency'], "")
                                    st.markdown(f"{nact['icon']} **{nact['label']}** {urg_icon}")
                                    st.markdown(f"  _{nact['detail']}_")
                                    if 'keywords' in nact and nact['keywords']:
                                        st.code(", ".join(nact['keywords'][:10]), language=None)

            # ── 서브탭6: 실시간 모니터링 ──
            with nsub6:
                st.markdown("#### ⚡ 오늘의 실시간 광고 성과")
                st.caption("※ 네이버 API 특성상 1~3시간 지연이 있습니다. 새로고침으로 최신 데이터를 확인하세요.")

                if st.button("🔄 실시간 데이터 갱신", key="p3_realtime_refresh"):
                    st.cache_data.clear()

                @st.cache_data(ttl=180, show_spinner="오늘 실시간 데이터 수집 중...")
                def _fetch_today(_acc_key, _acc_secret, _acc_cid):
                    client = napi.NaverAdClient(_acc_key, _acc_secret, _acc_cid)
                    return client.fetch_today_stats()

                try:
                    today_df = _fetch_today(acc["api_key"], acc["secret_key"], acc["customer_id"])
                except Exception as e:
                    st.error(f"실시간 데이터 조회 실패: {e}")
                    today_df = pd.DataFrame()

                if today_df.empty:
                    st.info("오늘 아직 집계된 데이터가 없습니다. (광고 시작 후 1~3시간 후 반영)")
                else:
                    # 전체 합산 KPI
                    t_cost = today_df["광고비(VAT포함)"].sum() if "광고비(VAT포함)" in today_df.columns else 0
                    t_clicks = today_df["클릭수"].sum() if "클릭수" in today_df.columns else 0
                    t_imps = today_df["노출수"].sum() if "노출수" in today_df.columns else 0
                    t_conv = today_df["전환수"].sum() if "전환수" in today_df.columns else 0
                    t_rev = today_df["전환매출액"].sum() if "전환매출액" in today_df.columns else 0
                    t_roas = (t_rev / t_cost * 100) if t_cost > 0 else 0

                    rt1, rt2, rt3, rt4, rt5, rt6 = st.columns(6)
                    rt1.metric("오늘 광고비", f"{t_cost:,.0f}원")
                    rt2.metric("노출수", f"{t_imps:,.0f}")
                    rt3.metric("클릭수", f"{t_clicks:,.0f}")
                    rt4.metric("전환수", f"{t_conv:,.0f}")
                    rt5.metric("전환매출", f"{t_rev:,.0f}원")
                    rt6.metric("ROAS", f"{t_roas:.0f}%")

                    st.markdown("")
                    st.markdown("#### 캠페인별 오늘 실시간 성과")
                    rt_cols = [c for c in [
                        "캠페인명", "노출수", "클릭수", "광고비(VAT포함)",
                        "전환수", "전환매출액", "CTR(%)", "평균CPC", "ROAS(%)",
                    ] if c in today_df.columns]
                    st.dataframe(
                        today_df[rt_cols].sort_values("광고비(VAT포함)", ascending=False),
                        use_container_width=True, hide_index=True,
                    )

                    # 기간 평균 대비
                    if not nsa_camps.empty and "광고비(VAT포함)" in nsa_camps.columns:
                        days_in_range = max((nsa_end - nsa_start).days, 1)
                        avg_daily_cost = nsa_camps["광고비(VAT포함)"].sum() / days_in_range
                        avg_daily_rev = nsa_camps["전환매출액"].sum() / days_in_range if "전환매출액" in nsa_camps.columns else 0

                        st.markdown("")
                        st.markdown("#### 기간 평균 대비 오늘 비교")
                        cmp1, cmp2, cmp3 = st.columns(3)
                        cost_diff = ((t_cost / avg_daily_cost - 1) * 100) if avg_daily_cost > 0 else 0
                        rev_diff = ((t_rev / avg_daily_rev - 1) * 100) if avg_daily_rev > 0 else 0
                        cmp1.metric("일평균 광고비", f"{avg_daily_cost:,.0f}원",
                                    delta=f"오늘 {cost_diff:+.1f}%")
                        cmp2.metric("일평균 전환매출", f"{avg_daily_rev:,.0f}원",
                                    delta=f"오늘 {rev_diff:+.1f}%")
                        avg_roas = (avg_daily_rev / avg_daily_cost * 100) if avg_daily_cost > 0 else 0
                        cmp3.metric("기간 평균 ROAS", f"{avg_roas:.0f}%",
                                    delta=f"오늘 {t_roas - avg_roas:+.0f}%p")

            # ── 서브탭7: 잔액/예산 알림 ──
            with nsub7:
                st.markdown("#### 💳 비즈머니 잔액 & 캠페인 예산 현황")

                @st.cache_data(ttl=180, show_spinner="잔액 정보 조회 중...")
                def _fetch_budget_info(_acc_key, _acc_secret, _acc_cid):
                    client = napi.NaverAdClient(_acc_key, _acc_secret, _acc_cid)
                    bizmoney = client.get_bizmoney()
                    budgets = client.get_campaign_budgets()
                    return bizmoney, budgets

                if st.button("🔄 잔액 새로고침", key="p3_budget_refresh"):
                    st.cache_data.clear()

                try:
                    bizmoney, camp_budgets = _fetch_budget_info(
                        acc["api_key"], acc["secret_key"], acc["customer_id"]
                    )
                except Exception as e:
                    st.error(f"잔액 조회 실패: {e}")
                    bizmoney, camp_budgets = {}, []

                # 비즈머니 잔액 표시
                balance = bizmoney.get("bizmoney", bizmoney.get("balance", 0))
                refund = bizmoney.get("refundLock", 0)
                budget_lock = bizmoney.get("budgetLock", 0)

                bm1, bm2, bm3 = st.columns(3)
                bm1.metric("💰 비즈머니 잔액", f"{balance:,.0f}원")
                bm2.metric("🔒 환불보류", f"{refund:,.0f}원")
                bm3.metric("📌 예산잠금", f"{budget_lock:,.0f}원")

                # 잔액 알림 설정
                st.markdown("")
                alert_threshold = st.number_input(
                    "⚠️ 잔액 알림 기준 (원)", value=500000, step=100000,
                    help="비즈머니가 이 금액 이하이면 경고 표시",
                    key="p3_alert_threshold",
                )

                if balance > 0 and balance <= alert_threshold:
                    st.error(
                        f"🚨 **비즈머니 잔액 부족 경고!** "
                        f"현재 잔액 {balance:,.0f}원 ≤ 알림 기준 {alert_threshold:,.0f}원\n\n"
                        f"충전하지 않으면 광고가 중단될 수 있습니다."
                    )
                elif balance > 0:
                    # 예상 소진일 계산
                    if not nsa_camps.empty and "광고비(VAT포함)" in nsa_camps.columns:
                        days_in_range = max((nsa_end - nsa_start).days, 1)
                        avg_daily = nsa_camps["광고비(VAT포함)"].sum() / days_in_range
                        if avg_daily > 0:
                            remain_days = balance / avg_daily
                            if remain_days <= 3:
                                st.warning(
                                    f"⚠️ 일평균 광고비 {avg_daily:,.0f}원 기준, "
                                    f"약 **{remain_days:.1f}일** 후 잔액 소진 예상"
                                )
                            else:
                                st.success(
                                    f"✅ 일평균 광고비 {avg_daily:,.0f}원 기준, "
                                    f"약 **{remain_days:.1f}일** 사용 가능 (충분)"
                                )
                elif balance == 0 and not bizmoney:
                    st.info("비즈머니 잔액 API를 지원하지 않는 계정이거나, 조회 권한이 없습니다.")

                # 캠페인 예산 테이블
                st.markdown("")
                st.markdown("#### 📋 캠페인별 일예산 설정 현황")
                if camp_budgets:
                    budget_df = pd.DataFrame(camp_budgets)
                    active_budgets = budget_df[budget_df["활성"] == True].copy()
                    if not active_budgets.empty:
                        active_budgets["일예산_표시"] = active_budgets["일예산"].apply(
                            lambda x: f"{x:,.0f}원" if x > 0 else "무제한"
                        )
                        # 무제한 예산 캠페인 경고
                        unlimited = active_budgets[active_budgets["일예산"] == 0]
                        if not unlimited.empty:
                            st.warning(
                                f"⚠️ **일예산 미설정(무제한) 캠페인 {len(unlimited)}개**: "
                                + ", ".join(unlimited["캠페인명"].tolist())
                            )

                        display_cols = ["캠페인명", "상태", "일예산_표시", "캠페인유형"]
                        st.dataframe(
                            active_budgets[display_cols],
                            use_container_width=True, hide_index=True,
                        )

                        # 일예산 합산
                        total_daily = active_budgets[active_budgets["일예산"] > 0]["일예산"].sum()
                        st.info(f"📊 활성 캠페인 일예산 합계: **{total_daily:,.0f}원/일** "
                                f"(무제한 제외)")
                    else:
                        st.info("활성 캠페인이 없습니다.")
                else:
                    st.warning("캠페인 예산 정보를 불러오지 못했습니다.")

            # ── 서브탭8: CPC × CTR 매트릭스 ──
            with nsub8:
                cpc_ctr_df = analysis.get("cpc_ctr_matrix", pd.DataFrame())
                if cpc_ctr_df.empty:
                    st.info("CPC×CTR 분석을 위한 충분한 데이터가 없습니다. (최소 클릭 5회 이상 키워드 필요)")
                else:
                    st.markdown("#### 🎯 CPC × CTR 4분면 (시장 경쟁·매력도)")
                    st.caption("고CTR+저CPC = 노다지 / 저CTR+고CPC = 돈낭비")

                    # 4분면 카드
                    quadrant_counts = cpc_ctr_df["CPC_CTR구간"].value_counts()
                    qc = st.columns(4)
                    q_info = [
                        ("🟢 노다지 (고CTR+저CPC)", "예산 우선 배정"),
                        ("🟡 경쟁격전 (고CTR+고CPC)", "전환율 확보 집중"),
                        ("⚪ 무관심 (저CTR+저CPC)", "소재 교체 또는 제외"),
                        ("🔴 돈낭비 (저CTR+고CPC)", "즉시 중단"),
                    ]
                    for i, (q_name, q_action) in enumerate(q_info):
                        cnt = quadrant_counts.get(q_name, 0)
                        with qc[i]:
                            with st.container(border=True):
                                st.markdown(f"**{q_name.split(' ')[0]} {q_name.split('(')[1].rstrip(')')}")
                                st.metric("키워드", f"{cnt}개")
                                st.caption(q_action)

                    # 스캐터플롯
                    cpc_med = cpc_ctr_df["CPC중앙값"].iloc[0] if "CPC중앙값" in cpc_ctr_df.columns else 0
                    ctr_med = cpc_ctr_df["CTR중앙값"].iloc[0] if "CTR중앙값" in cpc_ctr_df.columns else 0

                    fig_cpc = px.scatter(
                        cpc_ctr_df, x="평균CPC", y="CTR(%)",
                        color="CPC_CTR구간", hover_name="키워드",
                        size="클릭수", size_max=40,
                        hover_data={"ROAS(%)": ":.0f", "광고비(VAT포함)": ":,.0f"},
                        color_discrete_map={
                            "🟢 노다지 (고CTR+저CPC)": "#28a745",
                            "🟡 경쟁격전 (고CTR+고CPC)": "#ffc107",
                            "⚪ 무관심 (저CTR+저CPC)": "#6c757d",
                            "🔴 돈낭비 (저CTR+고CPC)": "#dc3545",
                        },
                    )
                    fig_cpc.add_vline(x=cpc_med, line_dash="dash", line_color="gray",
                                      annotation_text=f"CPC 중앙값 {cpc_med:,.0f}원")
                    fig_cpc.add_hline(y=ctr_med, line_dash="dash", line_color="gray",
                                      annotation_text=f"CTR 중앙값 {ctr_med:.2f}%")
                    fig_cpc.update_layout(height=550, template=TPL,
                                          xaxis_title="평균 CPC (원)", yaxis_title="CTR (%)")
                    st.plotly_chart(fig_cpc, use_container_width=True, key="p3_cpc_ctr_scatter")

                    # 노다지 키워드 테이블
                    goldmine = cpc_ctr_df[cpc_ctr_df["CPC_CTR구간"].str.contains("노다지")]
                    if not goldmine.empty:
                        st.markdown("#### 🟢 노다지 키워드 — 예산 우선 배정 추천")
                        gm_cols = [c for c in ["키워드", "클릭수", "CTR(%)", "평균CPC",
                                               "광고비(VAT포함)", "전환수", "전환매출액", "ROAS(%)"]
                                   if c in goldmine.columns]
                        st.dataframe(goldmine[gm_cols].sort_values("클릭수", ascending=False),
                                     use_container_width=True, hide_index=True)

                    # 돈낭비 키워드 테이블
                    waste = cpc_ctr_df[cpc_ctr_df["CPC_CTR구간"].str.contains("돈낭비")]
                    if not waste.empty:
                        st.markdown("#### 🔴 돈낭비 키워드 — 즉시 중단 추천")
                        st.dataframe(waste[gm_cols].sort_values("광고비(VAT포함)", ascending=False),
                                     use_container_width=True, hide_index=True)

            # ── 서브탭9: 요일별 효율 ──
            with nsub9:
                dow_df = analysis.get("day_of_week", pd.DataFrame())
                if dow_df.empty:
                    st.info("요일별 분석을 위한 일별 데이터가 부족합니다.")
                else:
                    st.markdown("#### 📅 요일별 광고 효율 분석")
                    st.caption("어느 요일에 가장 효율이 좋은지 파악하여 예산 집중 배분")

                    # 효율등급 카드
                    if "효율등급" in dow_df.columns:
                        dc = st.columns(7)
                        for i, (_, row) in enumerate(dow_df.iterrows()):
                            with dc[i % 7]:
                                with st.container(border=True):
                                    grade = row.get("효율등급", "")
                                    st.markdown(f"**{row['요일']}**")
                                    roas_val = row.get("ROAS(%)", 0)
                                    st.metric("ROAS", f"{roas_val:.0f}%")
                                    st.caption(grade)

                    # ROAS 바 차트
                    if "ROAS(%)" in dow_df.columns:
                        fig_dow = px.bar(
                            dow_df, x="요일", y="ROAS(%)",
                            color="ROAS(%)", color_continuous_scale="RdYlGn",
                            text=dow_df["ROAS(%)"].apply(lambda x: f"{x:.0f}%"),
                        )
                        if "ROAS(%)" in dow_df.columns:
                            avg_roas = dow_df["ROAS(%)"].mean()
                            fig_dow.add_hline(y=avg_roas, line_dash="dash", line_color="red",
                                              annotation_text=f"평균 {avg_roas:.0f}%")
                        fig_dow.update_layout(height=400, template=TPL,
                                              xaxis_title="요일", yaxis_title="ROAS (%)")
                        st.plotly_chart(fig_dow, use_container_width=True, key="p3_dow_roas")

                    # 일평균 클릭수 & 광고비 차트
                    dow_metrics = []
                    if "일평균_클릭수" in dow_df.columns:
                        dow_metrics.append(("일평균_클릭수", "일평균 클릭수"))
                    if "일평균_광고비(VAT포함)" in dow_df.columns:
                        dow_metrics.append(("일평균_광고비(VAT포함)", "일평균 광고비"))

                    if dow_metrics:
                        mc1, mc2 = st.columns(2)
                        for j, (col, title) in enumerate(dow_metrics):
                            target_col = mc1 if j == 0 else mc2
                            with target_col:
                                fig_m = px.bar(dow_df, x="요일", y=col,
                                               text=dow_df[col].apply(lambda x: f"{x:,.0f}"))
                                fig_m.update_layout(height=300, template=TPL, title=title)
                                st.plotly_chart(fig_m, use_container_width=True,
                                                key=f"p3_dow_{col}")

                    # CTR 요일별
                    if "CTR(%)" in dow_df.columns:
                        fig_ctr = px.line(dow_df, x="요일", y="CTR(%)", markers=True,
                                          text=dow_df["CTR(%)"].apply(lambda x: f"{x:.2f}%"))
                        fig_ctr.update_traces(textposition="top center")
                        fig_ctr.update_layout(height=300, template=TPL, title="요일별 CTR")
                        st.plotly_chart(fig_ctr, use_container_width=True, key="p3_dow_ctr")

                    # 요일별 상세 테이블
                    st.markdown("#### 요일별 상세 데이터")
                    dow_display = dow_df[["요일"] + [c for c in dow_df.columns
                                                    if c.startswith("일평균") or c in ["ROAS(%)", "CTR(%)", "효율등급"]]].copy()
                    st.dataframe(dow_display, use_container_width=True, hide_index=True)

            # ── 서브탭10: 노출 추이 ──
            with nsub10:
                imp_df = analysis.get("impression_trend", pd.DataFrame())
                if imp_df.empty:
                    st.info("노출 추이 분석을 위한 일별 데이터가 부족합니다.")
                else:
                    st.markdown("#### 📉 노출수(SOV) 추이 분석")

                    # 추이 판단 표시
                    trend_label = imp_df["노출추이"].iloc[0] if "노출추이" in imp_df.columns else ""
                    change_pct = imp_df["노출변화율(%)"].iloc[0] if "노출변화율(%)" in imp_df.columns else 0

                    tc1, tc2 = st.columns(2)
                    tc1.metric("노출 추이", trend_label)
                    tc2.metric("전반기→후반기 변화", f"{change_pct:+.1f}%")

                    # 노출수 + 이동평균 차트
                    fig_imp = go.Figure()
                    fig_imp.add_trace(go.Bar(
                        x=imp_df["날짜"], y=imp_df["노출수"],
                        name="일별 노출수", marker_color="#aec7e8", opacity=0.6,
                    ))
                    if "노출수_MA7" in imp_df.columns:
                        fig_imp.add_trace(go.Scatter(
                            x=imp_df["날짜"], y=imp_df["노출수_MA7"],
                            name="7일 이동평균", line=dict(color="#1f77b4", width=3),
                        ))
                    fig_imp.update_layout(height=450, template=TPL,
                                          xaxis_title="날짜", yaxis_title="노출수",
                                          title="일별 노출수 추이")
                    st.plotly_chart(fig_imp, use_container_width=True, key="p3_imp_trend")

                    # 클릭수 추이 (있다면)
                    if "클릭수" in imp_df.columns:
                        fig_click = go.Figure()
                        fig_click.add_trace(go.Scatter(
                            x=imp_df["날짜"], y=imp_df["클릭수"],
                            name="일별 클릭수", fill="tozeroy",
                            line=dict(color="#28a745"),
                        ))
                        fig_click.update_layout(height=300, template=TPL, title="일별 클릭수 추이")
                        st.plotly_chart(fig_click, use_container_width=True, key="p3_click_trend")

                    # 광고비 추이
                    if "광고비(VAT포함)" in imp_df.columns:
                        fig_cost = go.Figure()
                        fig_cost.add_trace(go.Scatter(
                            x=imp_df["날짜"], y=imp_df["광고비(VAT포함)"],
                            name="일별 광고비", fill="tozeroy",
                            line=dict(color="#ff7f0e"),
                        ))
                        fig_cost.update_layout(height=300, template=TPL, title="일별 광고비 추이")
                        st.plotly_chart(fig_cost, use_container_width=True, key="p3_cost_trend")

            # ── 서브탭11: 스토어×광고 교차 분석 ──
            with nsub11:
                st.markdown("#### 🔍 스마트스토어 × 광고 교차 분석")
                st.caption("네이버 광고 API 키워드와 스마트스토어 구매 키워드를 비교합니다.")

                # 스토어 키워드 데이터 로드
                try:
                    df_store_kw = dl.load_naver_keyword()
                except Exception:
                    df_store_kw = pd.DataFrame()

                if df_store_kw.empty:
                    st.warning("스마트스토어 키워드 데이터(상품/검색채널)가 없습니다.")
                elif nsa_keywords.empty:
                    st.warning("네이버 광고 API 키워드 데이터가 없습니다.")
                else:
                    cross_tab1, cross_tab2, cross_tab3 = st.tabs([
                        "📊 키워드 갭 분석", "📈 ROAS 비교", "🏪 채널 효율",
                    ])

                    # 1) 키워드 갭 분석
                    with cross_tab1:
                        st.markdown("##### 광고 키워드 vs 구매 키워드 갭")
                        gap_result = ae.analyze_keyword_gap(
                            nsa_keywords, df_store_kw,
                            ad_kw_col="키워드", store_kw_col="키워드",
                            ad_cost_col="총비용" if "총비용" in nsa_keywords.columns else "광고비(VAT포함)",
                            ad_rev_col="전환매출액" if "전환매출액" in nsa_keywords.columns else "전환매출",
                        )
                        gs = gap_result["summary"]
                        if gs:
                            g1, g2, g3 = st.columns(3)
                            g1.metric("광고만 있는 키워드", f"{gs['ad_only_count']}개",
                                      delta="예산 낭비 가능성", delta_color="inverse")
                            g2.metric("구매만 있는 키워드", f"{gs['store_only_count']}개",
                                      delta="광고 확대 기회", delta_color="normal")
                            g3.metric("양쪽 모두 존재", f"{gs['both_count']}개")

                        if gap_result["waste"]:
                            st.markdown("**🔴 광고비 쓰지만 스토어 결제 없는 키워드 (낭비 의심)**")
                            st.dataframe(pd.DataFrame(gap_result["waste"]).head(15),
                                         use_container_width=True, hide_index=True)
                        if gap_result["opportunity"]:
                            st.markdown("**🟢 광고 안 하는데 스토어에서 결제 발생 (확대 기회)**")
                            st.dataframe(pd.DataFrame(gap_result["opportunity"]).head(15),
                                         use_container_width=True, hide_index=True)

                    # 2) ROAS 비교
                    with cross_tab2:
                        st.markdown("##### 광고 ROAS vs 스토어 실제 ROAS 비교")
                        roas_comp = ae.analyze_roas_comparison(
                            nsa_keywords, df_store_kw,
                            ad_kw_col="키워드", store_kw_col="키워드",
                            ad_cost_col="총비용" if "총비용" in nsa_keywords.columns else "광고비(VAT포함)",
                            ad_rev_col="전환매출액" if "전환매출액" in nsa_keywords.columns else "전환매출",
                        )
                        if roas_comp.empty:
                            st.info("교집합 키워드가 없어 비교할 수 없습니다.")
                        else:
                            overrated = roas_comp[roas_comp["판정"].str.contains("과대")]
                            underrated = roas_comp[roas_comp["판정"].str.contains("과소")]
                            r1, r2 = st.columns(2)
                            r1.metric("광고 과대평가 키워드", f"{len(overrated)}개",
                                      delta="실제보다 ROAS 높게 측정", delta_color="inverse")
                            r2.metric("광고 과소평가 키워드", f"{len(underrated)}개",
                                      delta="실제 가치가 더 높음", delta_color="normal")
                            st.dataframe(roas_comp.head(20), use_container_width=True, hide_index=True)

                    # 3) 채널 효율
                    with cross_tab3:
                        st.markdown("##### 채널별 유입 효율 분석")
                        try:
                            df_ch = dl.load_naver_channel()
                        except Exception:
                            df_ch = pd.DataFrame()

                        if df_ch.empty:
                            st.info("채널 데이터(마케팅분석>검색채널)가 없습니다.")
                        else:
                            ch_eff = ae.analyze_channel_efficiency(df_ch)
                            if ch_eff.empty:
                                st.info("채널 효율 분석에 필요한 컬럼이 부족합니다.")
                            else:
                                st.dataframe(ch_eff, use_container_width=True, hide_index=True)
                                # 채널 ROAS 바 차트
                                paid_ch = ch_eff[ch_eff["광고비"] > 0]
                                if not paid_ch.empty:
                                    fig_ch = px.bar(
                                        paid_ch.sort_values("ROAS(%)", ascending=True),
                                        x="ROAS(%)", y="채널", orientation="h",
                                        color="등급",
                                        text=paid_ch.sort_values("ROAS(%)", ascending=True)["ROAS(%)"].apply(
                                            lambda x: f"{x:.0f}%"
                                        ),
                                    )
                                    fig_ch.update_layout(height=400, template=TPL, title="채널별 ROAS")
                                    st.plotly_chart(fig_ch, use_container_width=True, key="p3_ch_roas")

            # AI 컨텍스트 보강 (API 데이터 기반)
            _ctx_nsa_api = chat.summarize_metrics(
                계정=acc["name"],
                총키워드=f"{summary['총 키워드 수']}개",
                총광고비=f"{summary['총 광고비']:,.0f}원",
                총전환매출=f"{summary['총 전환매출']:,.0f}원",
                전체ROAS=f"{summary['전체 ROAS(%)']:.0f}%",
                총순이익=f"{summary['총 순이익']:,.0f}원",
                평균품질지수=f"{summary['평균 품질지수']:.1f}",
                A그룹비율=f"{summary['A그룹 비율(%)']}%",
                C그룹비율=f"{summary['C그룹 비율(%)']}%",
                입찰가인상추천=f"{summary['입찰가 인상 추천']}개",
                입찰가인하추천=f"{summary['입찰가 인하 추천']}개",
            )
            if not kw_analyzed.empty:
                top_kw = kw_analyzed.nlargest(15, "광고비(VAT포함)")
                _ctx_nsa_api += "\n" + chat.summarize_dataframe(
                    top_kw[[c for c in ["키워드", "클릭수", "광고비(VAT포함)", "전환매출액", "ROAS(%)", "품질지수", "입찰가", "세부그룹", "추천입찰가"] if c in top_kw.columns]],
                    "네이버SA 주요 키워드 Top15",
                )
            ai_contexts["네이버 광고"] = _ctx_nsa_api

    # ═══════════════════════════════════════════════════════════
    #  탭 4: 브랜드 점검
    # ═══════════════════════════════════════════════════════════
    with tab4:
        S.slide_header("브랜드별 매출 현황", "Brand Sales Overview")
        if brand_cur.empty:
            st.warning("브랜드 데이터가 없습니다.")
        else:
            # KPI
            top3 = brand_cur.head(3)
            bc = st.columns(min(len(top3), 3))
            for i, row in top3.iterrows():
                with bc[min(i, 2)]:
                    st.metric(row["브랜드"], f"{row['매출']/1e6:.0f}백만",
                              delta=f"마진율 {row.get('마진', 0) / max(row['매출'], 1) * 100:.0f}%")

            st.markdown("")

            # 브랜드 바 차트
            fig_brand = px.bar(
                brand_cur.head(15), x="매출", y="브랜드", orientation="h",
                text=brand_cur.head(15)["매출"].apply(lambda x: f"{x/1e6:.0f}백만"),
                color="매출", color_continuous_scale=S.GRADIENT_BLUE,
            )
            fig_brand.update_layout(template=TPL, height=max(350, len(brand_cur.head(15)) * 35),
                                    coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_brand, use_container_width=True)

            # YoY 비교
            if not df_25.empty:
                st.markdown("")
                S.slide_header("전년 대비 브랜드 성장", "YoY Brand Growth")
                df_25_ytd = df_25[df_25["주문일시"].dt.month <= cur_month]
                brand_25 = df_25_ytd.groupby("브랜드")["총 판매금액"].sum().reset_index()
                brand_25.rename(columns={"총 판매금액": "25년 매출"}, inplace=True)
                brand_26_all = df_26.groupby("브랜드")["총 판매금액"].sum().reset_index()
                brand_26_all.rename(columns={"총 판매금액": "26년 매출"}, inplace=True)
                brand_compare = brand_26_all.merge(brand_25, on="브랜드", how="left").fillna(0)
                brand_compare["성장률(%)"] = (
                    (brand_compare["26년 매출"] - brand_compare["25년 매출"]) /
                    brand_compare["25년 매출"].replace(0, 1) * 100
                ).round(1)
                brand_compare = brand_compare.sort_values("26년 매출", ascending=False)

                fig_bc = go.Figure()
                fig_bc.add_trace(go.Bar(x=brand_compare["브랜드"], y=brand_compare["26년 매출"],
                                        name="26년", marker_color=S.COLORS["primary"]))
                fig_bc.add_trace(go.Bar(x=brand_compare["브랜드"], y=brand_compare["25년 매출"],
                                        name="25년 동기간", marker_color="#aec7e8"))
                fig_bc.update_layout(barmode="group", height=400, template=TPL)
                st.plotly_chart(fig_bc, use_container_width=True)

                disp_bc = brand_compare.copy()
                disp_bc["26년 매출"] = disp_bc["26년 매출"].apply(lambda x: f"{x:,.0f}")
                disp_bc["25년 매출"] = disp_bc["25년 매출"].apply(lambda x: f"{x:,.0f}")
                st.dataframe(disp_bc, use_container_width=True, hide_index=True)

            # 브랜드 마진 분석
            st.markdown("")
            S.slide_header("브랜드별 마진 분석", "Brand Margin Analysis")
            brand_margin = brand_cur.copy()
            brand_margin["마진율(%)"] = (brand_margin["마진"] / brand_margin["매출"].replace(0, 1) * 100).round(1)
            fig_bm = go.Figure()
            fig_bm.add_trace(go.Bar(x=brand_margin["브랜드"], y=brand_margin["매출"],
                                    name="매출", marker_color=S.COLORS["primary"]))
            fig_bm.add_trace(go.Bar(x=brand_margin["브랜드"], y=brand_margin["마진"],
                                    name="마진", marker_color=S.COLORS["success"]))
            fig_bm.update_layout(barmode="group", height=400, template=TPL)
            st.plotly_chart(fig_bm, use_container_width=True)

    # ═══════════════════════════════════════════════════════════
    #  탭 5: 채널 점검
    # ═══════════════════════════════════════════════════════════
    with tab5:
        if channel_matrix.empty:
            st.warning("채널 데이터가 없습니다.")
        else:
            # 버블 차트
            S.slide_header("채널별 매출 vs 성장률", "Channel Sales vs Growth")
            fig_ch = px.scatter(
                channel_matrix, x="최근2주 매출", y="성장률(%)",
                size="최근2주 매출", color="성장률(%)", text="채널",
                color_continuous_scale="RdYlGn", size_max=50,
            )
            fig_ch.update_traces(textposition="top center")
            fig_ch.add_hline(y=0, line_dash="dash", line_color="gray")
            fig_ch.update_layout(template=TPL, height=450)
            st.plotly_chart(fig_ch, use_container_width=True, key="p3_bubble_tab5")

            # 성장/하락 채널
            col_grow, col_dec = st.columns(2)
            with col_grow:
                S.slide_header("성장 채널 (>20%)", "Growing Channels")
                growing = channel_matrix[channel_matrix["성장률(%)"] > 20].sort_values(
                    "최근2주 매출", ascending=False)
                if growing.empty:
                    st.info("성장 중인 채널 없음")
                else:
                    disp_g = growing.copy()
                    disp_g["최근2주 매출"] = disp_g["최근2주 매출"].apply(lambda x: f"{x:,.0f}")
                    disp_g["이전2주 매출"] = disp_g["이전2주 매출"].apply(lambda x: f"{x:,.0f}")
                    disp_g["성장률(%)"] = disp_g["성장률(%)"].apply(lambda x: f"{x:+.1f}")
                    st.dataframe(disp_g, use_container_width=True, hide_index=True)

            with col_dec:
                S.slide_header("주의 채널 (<-20%)", "Declining Channels")
                declining = channel_matrix[channel_matrix["성장률(%)"] < -20].sort_values(
                    "최근2주 매출", ascending=False)
                if declining.empty:
                    st.success("하락 중인 채널 없음!")
                else:
                    disp_d = declining.copy()
                    disp_d["최근2주 매출"] = disp_d["최근2주 매출"].apply(lambda x: f"{x:,.0f}")
                    disp_d["이전2주 매출"] = disp_d["이전2주 매출"].apply(lambda x: f"{x:,.0f}")
                    disp_d["성장률(%)"] = disp_d["성장률(%)"].apply(lambda x: f"{x:+.1f}")
                    st.dataframe(disp_d, use_container_width=True, hide_index=True)

        # 캠페인 기회/주의
        st.markdown("")
        if not ad_opportunities.empty:
            col_opp, col_warn = st.columns(2)
            with col_opp:
                S.slide_header("성장 기회 캠페인", "Growth Opportunity Campaigns")
                median_cost = ad_opportunities["광고비"].median()
                high_roas = ad_opportunities[
                    (ad_opportunities["ROAS(%)"] >= 300) & (ad_opportunities["광고비"] <= median_cost)
                ].sort_values("ROAS(%)", ascending=False).head(10)
                if high_roas.empty:
                    st.info("해당 캠페인 없음")
                else:
                    disp_h = high_roas[["플랫폼", "캠페인명", "광고비", "전환매출", "ROAS(%)"]].copy()
                    disp_h["광고비"] = disp_h["광고비"].apply(lambda x: f"{x:,.0f}")
                    disp_h["전환매출"] = disp_h["전환매출"].apply(lambda x: f"{x:,.0f}")
                    disp_h["ROAS(%)"] = disp_h["ROAS(%)"].apply(lambda x: f"{x:.0f}")
                    st.dataframe(disp_h, use_container_width=True, hide_index=True)
                    st.info("ROAS 높고 예산 적은 캠페인 → 예산 증액으로 매출 극대화!")

            with col_warn:
                S.slide_header("주의 캠페인", "Underperforming Campaigns")
                low_roas = ad_opportunities[
                    (ad_opportunities["ROAS(%)"] < 100) & (ad_opportunities["광고비"] > 0)
                ].sort_values("ROAS(%)", ascending=True).head(10)
                if low_roas.empty:
                    st.success("ROAS 100% 미만 캠페인 없음!")
                else:
                    disp_l = low_roas[["플랫폼", "캠페인명", "광고비", "전환매출", "ROAS(%)"]].copy()
                    disp_l["광고비"] = disp_l["광고비"].apply(lambda x: f"{x:,.0f}")
                    disp_l["전환매출"] = disp_l["전환매출"].apply(lambda x: f"{x:,.0f}")
                    disp_l["ROAS(%)"] = disp_l["ROAS(%)"].apply(lambda x: f"{x:.0f}")
                    st.dataframe(disp_l, use_container_width=True, hide_index=True)
                    st.warning("ROAS 100% 미만 → 예산 축소 또는 크리에이티브 개선!")

    # ═══════════════════════════════════════════════════════════
    #  탭 6: 상품 점검
    # ═══════════════════════════════════════════════════════════
    with tab6:
        S.slide_header("이번 달 상품 매출 현황", "Monthly Product Sales")
        if product_data.empty:
            st.warning("상품 데이터가 없습니다.")
        else:
            # Top 상품 KPI
            pk1, pk2, pk3 = st.columns(3)
            pk1.metric("총 상품 종류", f"{len(product_data)}개")
            pk2.metric("Top1 상품", product_data.iloc[0]["상품명"][:20])
            pk3.metric("Top1 매출", f"{product_data.iloc[0]['매출']/1e6:.0f}백만")

            st.markdown("")

            # Top 20 상품 바 차트
            S.slide_header("상품 매출 Top 20", "Top 20 Products by Revenue")
            top20 = product_data.head(20)
            fig_prod = px.bar(
                top20, x="매출", y="상품명", orientation="h",
                text=top20["매출"].apply(lambda x: f"{x/1e6:.0f}백만"),
                color="마진율(%)", color_continuous_scale="RdYlGn",
            )
            fig_prod.update_layout(
                template=TPL, height=max(500, len(top20) * 30),
                yaxis={"categoryorder": "total ascending"},
                coloraxis_colorbar=dict(title="마진율(%)"),
            )
            st.plotly_chart(fig_prod, use_container_width=True)

            # 상품 상세 테이블
            S.slide_header("상품 상세 (매출순)", "Product Details by Revenue")
            disp_prod = product_data.head(30).copy()
            disp_prod["매출"] = disp_prod["매출"].apply(lambda x: f"{x:,.0f}")
            disp_prod["마진"] = disp_prod["마진"].apply(lambda x: f"{x:,.0f}")
            disp_prod["수량"] = disp_prod["수량"].apply(lambda x: f"{x:,.0f}")
            st.dataframe(disp_prod, use_container_width=True, hide_index=True)

            # 채널별 상품 분석
            st.markdown("")
            S.slide_header("채널별 Top 상품", "Top Products by Channel")
            top_channels = df_cur.groupby("외부몰/벤더명")["총 판매금액"].sum().nlargest(5).index.tolist()
            for ch_name in top_channels:
                with st.expander(f"📦 {ch_name}"):
                    ch_prods = df_cur[df_cur["외부몰/벤더명"] == ch_name].groupby("상품명").agg(
                        매출=("총 판매금액", "sum"), 수량=("수량", "sum"),
                    ).sort_values("매출", ascending=False).head(10).reset_index()
                    ch_prods["매출"] = ch_prods["매출"].apply(lambda x: f"{x:,.0f}")
                    ch_prods["수량"] = ch_prods["수량"].apply(lambda x: f"{x:,.0f}")
                    st.dataframe(ch_prods, use_container_width=True, hide_index=True)

            # 마진 4분면
            st.markdown("")
            S.slide_header("상품 4분면 (매출 vs 마진율)", "Product Quadrant: Revenue vs Margin")
            prod_scatter = product_data[product_data["매출"] > 0].head(50)
            if not prod_scatter.empty:
                fig_ps = px.scatter(
                    prod_scatter, x="매출", y="마진율(%)",
                    size="수량", color="마진율(%)", text="상품명",
                    color_continuous_scale="RdYlGn", size_max=40,
                    hover_data={"매출": ":,.0f", "수량": ":,.0f"},
                )
                fig_ps.update_traces(textposition="top center", textfont_size=9)
                fig_ps.add_hline(y=margin_rate * 100, line_dash="dash", line_color="gray",
                                 annotation_text=f"평균 마진율 {margin_rate*100:.0f}%")
                fig_ps.update_layout(template=TPL, height=500)
                st.plotly_chart(fig_ps, use_container_width=True)

# AI 패널 렌더
chat.render_panel(ai_col, "p3", ai_contexts)

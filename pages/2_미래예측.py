# -*- coding: utf-8 -*-
"""Pillar 2: 미래 예측 — 시나리오 예측 · 채널 기여도 · 시뮬레이터"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
import calendar
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import data_loader as dl
import predictor as pred
import styles as S
import ai_chat as chat

st.set_page_config(page_title="미래 예측", page_icon="🔮", layout="wide")
S.inject_css()
TPL = S.TPL
st.title("🔮 미래 예측")

TARGET = config.MONTHLY_TARGET

# ── 데이터 로드 ──────────────────────────────────────────────
with st.spinner("데이터 로딩 중..."):
    df_26 = dl.load_sales_26()
    df_nsa = dl.load_naver_sa()
    df_cpg = dl.load_coupang_ad()

if df_26.empty:
    st.error("매출 데이터를 불러올 수 없습니다.")
    st.stop()

# ── 사이드바 ─────────────────────────────────────────────────
with st.sidebar:
    st.header("📅 기간 & 예측 설정")
    today_d = date.today()
    yesterday = today_d - timedelta(days=1)

    qc1, qc2 = st.columns(2)
    with qc1:
        if st.button("금월", use_container_width=True, key="p2_q_cur"):
            if today_d.day == 1:
                lp = yesterday
                st.session_state["p2_sel_month"] = f"{lp.year}-{lp.month:02d}"
            else:
                st.session_state["p2_sel_month"] = f"{today_d.year}-{today_d.month:02d}"
            st.rerun()
    with qc2:
        if st.button("전월", use_container_width=True, key="p2_q_prev"):
            first = today_d.replace(day=1)
            lp = first - timedelta(days=1)
            st.session_state["p2_sel_month"] = f"{lp.year}-{lp.month:02d}"
            st.rerun()

    available_months = sorted(df_26["주문일시"].dt.to_period("M").unique())
    month_labels = [str(m) for m in available_months]
    default_idx = len(month_labels) - 1
    if "p2_sel_month" in st.session_state:
        target_m = st.session_state["p2_sel_month"]
        if target_m in month_labels:
            default_idx = month_labels.index(target_m)

    selected_month = st.selectbox("월 선택", month_labels, index=default_idx, key="p2_month")
    sel_year = int(selected_month[:4])
    sel_mon = int(selected_month[5:7])
    st.divider()
    margin_rate = st.slider("제품 평균 마진율 (%)", 5, 80, 30, step=5, key="p2_margin") / 100

# ── AI 컨텍스트 구축 ─────────────────────────────────────────
ai_contexts = {}

# 월말 예측 컨텍스트
ai_contexts["월말 예측"] = chat.summarize_metrics(
    선택월=selected_month, 목표=f"{TARGET/1e8:.0f}억",
    마진율=f"{margin_rate*100:.0f}%",
)
month_data = df_26[(df_26["주문일시"].dt.year == sel_year) & (df_26["주문일시"].dt.month == sel_mon)]
if not month_data.empty:
    ms = month_data["총 판매금액"].sum()
    now = datetime.now()
    if sel_year == now.year and sel_mon == now.month:
        days_denom = max(now.day, 1)
    else:
        days_denom = calendar.monthrange(sel_year, sel_mon)[1]
    ai_contexts["월말 예측"] += "\n" + chat.summarize_metrics(
        현재매출=f"{ms/1e8:.2f}억",
        일평균=f"{ms / days_denom / 1e6:.0f}백만",
    )

# 채널 기여도 컨텍스트
ai_contexts["채널 기여도"] = chat.summarize_metrics(
    선택월=selected_month, 목표=f"{TARGET/1e8:.0f}억",
)

# 광고 시뮬레이터 컨텍스트 (상세 데이터 포함)
_ctx_sim = chat.summarize_metrics(마진율=f"{margin_rate*100:.0f}%")
_ctx_sim += "\n\n[시뮬레이션 설명] 예산 변경 슬라이더 값은 현재 광고비 대비 증감률(%)입니다. 예: 슬라이더 65 = 현재 광고비 대비 +65% 증가."
if not df_nsa.empty:
    _nsa_cost = df_nsa["총비용(VAT포함,원)"].sum()
    _nsa_rev = df_nsa["전환매출액(원)"].sum()
    _nsa_clicks = df_nsa["클릭수"].sum()
    _nsa_imp = df_nsa["노출수"].sum()
    _nsa_roas = _nsa_rev / max(_nsa_cost, 1) * 100
    _ctx_sim += "\n" + chat.summarize_metrics(
        네이버SA_광고비=f"{_nsa_cost:,.0f}원 ({_nsa_cost/1e6:.1f}백만)",
        네이버SA_전환매출=f"{_nsa_rev:,.0f}원 ({_nsa_rev/1e6:.1f}백만)",
        네이버SA_ROAS=f"{_nsa_roas:.0f}%",
        네이버SA_클릭수=f"{_nsa_clicks:,.0f}",
        네이버SA_노출수=f"{_nsa_imp:,.0f}",
        네이버SA_CPC=f"{_nsa_cost / max(_nsa_clicks, 1):,.0f}원",
    )
if not df_cpg.empty:
    _cpg_cost = df_cpg["광고비"].sum()
    _cpg_rev = df_cpg["총 전환매출액(1일)"].sum()
    _cpg_clicks = df_cpg["클릭수"].sum()
    _cpg_imp = df_cpg["노출수"].sum()
    _cpg_roas = _cpg_rev / max(_cpg_cost, 1) * 100
    _ctx_sim += "\n" + chat.summarize_metrics(
        쿠팡_광고비=f"{_cpg_cost:,.0f}원 ({_cpg_cost/1e6:.1f}백만)",
        쿠팡_전환매출=f"{_cpg_rev:,.0f}원 ({_cpg_rev/1e6:.1f}백만)",
        쿠팡_ROAS=f"{_cpg_roas:.0f}%",
        쿠팡_클릭수=f"{_cpg_clicks:,.0f}",
        쿠팡_노출수=f"{_cpg_imp:,.0f}",
        쿠팡_CPC=f"{_cpg_cost / max(_cpg_clicks, 1):,.0f}원",
    )
ai_contexts["광고 시뮬레이터"] = _ctx_sim

# ── 레이아웃 설정 (메인 + AI 패널) ──────────────────────────
main_col, ai_col = chat.setup_layout("p2")

# ═══════════════════════════════════════════════════════════════
#  탭 구성 (모든 컨텐츠를 main_col 안에 배치)
# ═══════════════════════════════════════════════════════════════
with main_col:
    tab1, tab2, tab3 = st.tabs(["📈 월말 예측", "🏢 채널 기여도 예측", "🎮 광고 예산 시뮬레이터"])

    # ═══════════════════════════════════════════════════════════════
    #  탭 1: 월말 예측
    # ═══════════════════════════════════════════════════════════════
    with tab1:
        scenarios = pred.month_end_scenarios(df_26, TARGET, sel_year, sel_mon)

        if scenarios is None:
            st.warning("선택한 월의 데이터가 없습니다.")
        else:
            # KPI
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("현재 매출", f"{scenarios['current_sales']/1e8:.2f}억")
            c2.metric("남은 일수", f"{scenarios['remaining']}일")
            c3.metric("필요 일평균", f"{scenarios['needed_daily']/1e6:.0f}백만")
            c4.metric("목표 갭", f"{scenarios['gap']/1e8:.2f}억" if scenarios['gap'] > 0 else "달성!")

            st.markdown("---")

            # 다중 시나리오 게이지 (2x2)
            st.markdown("### 시나리오별 월말 예측")
            fig_gauges = make_subplots(
                rows=2, cols=2,
                specs=[[{"type": "indicator"}, {"type": "indicator"}],
                       [{"type": "indicator"}, {"type": "indicator"}]],
                subplot_titles=["기본 예측", "낙관 예측 (최근7일)", "비관 예측 (최저 롤링)", "주말보정 예측"],
            )
            gauge_config = {
                "axis": {"range": [0, TARGET / 1e8 * 1.2], "ticksuffix": "억"},
                "bar": {"color": "#1f77b4"},
                "steps": [
                    {"range": [0, TARGET / 1e8 * 0.5], "color": "#ffcccc"},
                    {"range": [TARGET / 1e8 * 0.5, TARGET / 1e8 * 0.8], "color": "#fff3cd"},
                    {"range": [TARGET / 1e8 * 0.8, TARGET / 1e8], "color": "#d4edda"},
                ],
                "threshold": {"line": {"color": "red", "width": 3}, "thickness": 0.8, "value": TARGET / 1e8},
            }
            for i, (val, row, col, color) in enumerate([
                (scenarios["proj_base"], 1, 1, "#1f77b4"),
                (scenarios["proj_optimistic"], 1, 2, "#2ca02c"),
                (scenarios["proj_pessimistic"], 2, 1, "#d62728"),
                (scenarios["proj_weekend_adj"], 2, 2, "#ff7f0e"),
            ]):
                gc = gauge_config.copy()
                gc["bar"] = {"color": color}
                fig_gauges.add_trace(go.Indicator(
                    mode="gauge+number",
                    value=val / 1e8,
                    number={"suffix": "억", "font": {"size": 28}},
                    gauge=gc,
                ), row=row, col=col)
            fig_gauges.update_layout(height=500, margin=dict(t=60, b=20))
            st.plotly_chart(fig_gauges, use_container_width=True)

            # 시나리오 비교 바 차트
            st.markdown("### 시나리오 비교")
            scenario_df = pd.DataFrame([
                {"시나리오": "비관 (최저 롤링)", "예상매출": scenarios["proj_pessimistic"]},
                {"시나리오": "기본 (전체 일평균)", "예상매출": scenarios["proj_base"]},
                {"시나리오": "주말보정", "예상매출": scenarios["proj_weekend_adj"]},
                {"시나리오": "낙관 (최근7일)", "예상매출": scenarios["proj_optimistic"]},
            ])
            fig_comp = px.bar(
                scenario_df, x="예상매출", y="시나리오", orientation="h",
                color="예상매출",
                color_continuous_scale=["#d62728", "#ff7f0e", "#2ca02c"],
                text=scenario_df["예상매출"].apply(lambda x: f"{x/1e8:.1f}억"),
            )
            fig_comp.add_vline(x=TARGET, line_dash="dash", line_color="red",
                               annotation_text=f"목표 {TARGET/1e8:.0f}억")
            fig_comp.update_layout(template=TPL, height=300, showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_comp, use_container_width=True)

            # 달성 확률 판단
            projs = [scenarios["proj_base"], scenarios["proj_optimistic"],
                     scenarios["proj_pessimistic"], scenarios["proj_weekend_adj"]]
            names = ["기본", "낙관", "비관", "주말보정"]
            achievable = [n for n, p in zip(names, projs) if p >= TARGET]

            if len(achievable) == 4:
                st.success("모든 시나리오에서 목표 달성 가능!")
            elif len(achievable) > 0:
                st.info(f"목표 달성 가능 시나리오: **{', '.join(achievable)}** ({len(achievable)}/4)")
            else:
                st.error("모든 시나리오에서 목표 미달. 즉시 매출 부스트 필요.")

            st.markdown("---")

            # 일별 매출 시계열
            st.markdown("### 일별 매출 추이")
            daily = scenarios["daily_series"]
            daily_df = daily.reset_index()
            daily_df.columns = ["날짜", "매출"]

            fig_daily = go.Figure()
            fig_daily.add_trace(go.Bar(x=daily_df["날짜"], y=daily_df["매출"],
                                       name="일별 매출", marker_color="#1f77b4"))
            fig_daily.add_hline(y=scenarios["avg_daily"], line_dash="dash", line_color="orange",
                                annotation_text=f"현재 일평균 {scenarios['avg_daily']/1e6:.0f}백만")
            if scenarios["needed_daily"] > 0:
                fig_daily.add_hline(y=scenarios["needed_daily"], line_dash="dash", line_color="red",
                                    annotation_text=f"필요 일평균 {scenarios['needed_daily']/1e6:.0f}백만")
            fig_daily.update_layout(template=TPL, height=370, yaxis_title="매출(원)")
            st.plotly_chart(fig_daily, use_container_width=True)

            # 주중/주말 분석
            st.markdown("### 주중 vs 주말 일평균")
            cw1, cw2, cw3 = st.columns(3)
            cw1.metric("주중 일평균", f"{scenarios['avg_weekday']/1e6:.0f}백만")
            cw2.metric("주말 일평균", f"{scenarios['avg_weekend']/1e6:.0f}백만")
            diff_pct = ((scenarios['avg_weekend'] - scenarios['avg_weekday']) /
                        max(scenarios['avg_weekday'], 1) * 100)
            cw3.metric("주말 vs 주중", f"{diff_pct:+.1f}%",
                       delta=f"{'주말 매출 높음' if diff_pct > 0 else '주중 매출 높음'}")

            # 시나리오 데이터를 AI 컨텍스트에 추가 (런타임 보강)
            ai_contexts["월말 예측"] = chat.summarize_metrics(
                선택월=selected_month,
                현재매출=f"{scenarios['current_sales']/1e8:.2f}억",
                남은일수=f"{scenarios['remaining']}일",
                필요일평균=f"{scenarios['needed_daily']/1e6:.0f}백만",
                기본예측=f"{scenarios['proj_base']/1e8:.1f}억",
                낙관예측=f"{scenarios['proj_optimistic']/1e8:.1f}억",
                비관예측=f"{scenarios['proj_pessimistic']/1e8:.1f}억",
                주말보정예측=f"{scenarios['proj_weekend_adj']/1e8:.1f}억",
                주중일평균=f"{scenarios['avg_weekday']/1e6:.0f}백만",
                주말일평균=f"{scenarios['avg_weekend']/1e6:.0f}백만",
                목표=f"{TARGET/1e8:.0f}억",
            )


    # ═══════════════════════════════════════════════════════════════
    #  탭 2: 채널 기여도 예측
    # ═══════════════════════════════════════════════════════════════
    with tab2:
        ch_forecast = pred.channel_contribution_forecast(df_26, TARGET, sel_year, sel_mon)

        if ch_forecast.empty:
            st.warning("채널 기여도 데이터가 없습니다.")
        else:
            # 채널 기여 바 차트
            st.markdown("### 채널별 월말 예상 매출")
            fig_ch = px.bar(
                ch_forecast.sort_values("월말예상", ascending=True),
                x="월말예상", y="채널", orientation="h",
                text=ch_forecast.sort_values("월말예상", ascending=True)["월말예상"].apply(
                    lambda x: f"{x/1e6:.0f}백만"),
                color="월말예상", color_continuous_scale="Blues",
            )
            fig_ch.add_vline(x=TARGET * 0.1, line_dash="dot", line_color="gray",
                             annotation_text="목표 10%")
            fig_ch.update_layout(template=TPL, height=max(350, len(ch_forecast) * 35),
                                 coloraxis_showscale=False)
            st.plotly_chart(fig_ch, use_container_width=True)

            # 기여율 파이
            col_pie, col_target = st.columns(2)
            with col_pie:
                st.markdown("### 기여율 (%)")
                fig_pie = px.pie(ch_forecast, values="월말예상", names="채널", hole=0.4)
                fig_pie.update_layout(template=TPL, height=400)
                fig_pie.update_traces(textposition="inside", textinfo="label+percent")
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_target:
                st.markdown("### 목표 대비 기여도")
                fig_tgt = go.Figure()
                ch_sorted = ch_forecast.sort_values("월말예상", ascending=True)
                fig_tgt.add_trace(go.Bar(
                    y=ch_sorted["채널"], x=ch_sorted["현재매출"],
                    name="현재매출", orientation="h", marker_color="#1f77b4",
                ))
                remaining_est = (ch_sorted["월말예상"] - ch_sorted["현재매출"]).clip(lower=0)
                fig_tgt.add_trace(go.Bar(
                    y=ch_sorted["채널"], x=remaining_est,
                    name="남은 기간 예상", orientation="h", marker_color="#aec7e8",
                ))
                fig_tgt.update_layout(barmode="stack", height=max(350, len(ch_forecast) * 35),
                                      margin=dict(t=30, b=20))
                st.plotly_chart(fig_tgt, use_container_width=True)

            # 채널 상세 테이블
            st.markdown("### 채널별 상세")
            disp_ch = ch_forecast.copy()
            for c in ["현재매출", "최근일평균", "월말예상"]:
                if c in disp_ch.columns:
                    disp_ch[c] = disp_ch[c].apply(lambda x: f"{x:,.0f}")
            st.dataframe(disp_ch, use_container_width=True, hide_index=True)

        st.markdown("---")

        # 모멘텀 지표
        st.markdown("### 매출 모멘텀")
        momentum = pred.momentum_indicator(df_26, sel_year, sel_mon)
        if momentum is None:
            st.warning("모멘텀 데이터가 없습니다.")
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("모멘텀 상태", momentum["status"])
            m2.metric("이번 주 일평균", f"{momentum['this_week_avg']/1e6:.0f}백만",
                      delta=f"{momentum['change_pct']:+.1f}%")
            m3.metric("지난 주 일평균", f"{momentum['last_week_avg']/1e6:.0f}백만")

            # 일별 추이 + 7일 이동평균
            m_daily = momentum["daily"]
            if len(m_daily) > 0:
                m_df = m_daily.reset_index()
                m_df.columns = ["날짜", "매출"]
                m_df["7일이동평균"] = m_df["매출"].rolling(7, min_periods=1).mean()

                fig_mom = go.Figure()
                fig_mom.add_trace(go.Bar(x=m_df["날짜"], y=m_df["매출"],
                                         name="일별 매출", marker_color="#1f77b4", opacity=0.6))
                fig_mom.add_trace(go.Scatter(x=m_df["날짜"], y=m_df["7일이동평균"],
                                             name="7일 이동평균", line=dict(color="red", width=2)))
                fig_mom.update_layout(template=TPL, height=370)
                st.plotly_chart(fig_mom, use_container_width=True)

        # 채널 기여도 컨텍스트 런타임 보강
        _ctx_ch = chat.summarize_metrics(선택월=selected_month)
        if not ch_forecast.empty:
            _ctx_ch += "\n" + chat.summarize_dataframe(ch_forecast, "채널별 기여도 예측")
        if momentum is not None:
            _ctx_ch += "\n" + chat.summarize_metrics(
                모멘텀상태=momentum["status"],
                이번주일평균=f"{momentum['this_week_avg']/1e6:.0f}백만",
                변화율=f"{momentum['change_pct']:+.1f}%",
            )
        ai_contexts["채널 기여도"] = _ctx_ch


    # ═══════════════════════════════════════════════════════════════
    #  탭 3: 광고 예산 시뮬레이터
    # ═══════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("### 광고 예산 변경 시뮬레이션")
        st.caption("각 플랫폼의 예산을 조정하면 예상 매출/순이익 변화를 확인할 수 있습니다.")

        # 현재 광고 데이터 취합
        ad_summary = []
        if not df_nsa.empty:
            nsa_cost = df_nsa["총비용(VAT포함,원)"].sum()
            nsa_rev = df_nsa["전환매출액(원)"].sum()
            ad_summary.append({
                "platform": "네이버SA", "cost": nsa_cost,
                "revenue": nsa_rev, "roas": nsa_rev / max(nsa_cost, 1) * 100
            })
        if not df_cpg.empty:
            cpg_cost = df_cpg["광고비"].sum()
            cpg_rev = df_cpg["총 전환매출액(1일)"].sum()
            ad_summary.append({
                "platform": "쿠팡", "cost": cpg_cost,
                "revenue": cpg_rev, "roas": cpg_rev / max(cpg_cost, 1) * 100
            })

        if not ad_summary:
            st.warning("광고 데이터가 없습니다.")
        else:
            # 현재 상태 표시
            st.markdown("#### 현재 광고 현황")
            current_df = pd.DataFrame(ad_summary)
            disp_cur = current_df.copy()
            disp_cur.columns = ["플랫폼", "광고비", "전환매출", "ROAS(%)"]
            disp_cur["광고비"] = disp_cur["광고비"].apply(lambda x: f"{x:,.0f}")
            disp_cur["전환매출"] = disp_cur["전환매출"].apply(lambda x: f"{x:,.0f}")
            disp_cur["ROAS(%)"] = disp_cur["ROAS(%)"].apply(lambda x: f"{x:.0f}")
            st.dataframe(disp_cur, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("#### 예산 변경 시뮬레이션")

            # 슬라이더
            changes = {}
            cols = st.columns(len(ad_summary))
            for i, ad in enumerate(ad_summary):
                with cols[i]:
                    changes[ad["platform"]] = st.slider(
                        f"{ad['platform']} 예산 변경",
                        -50, 100, 0, step=5,
                        key=f"p2_sim_{ad['platform']}",
                        help=f"현재 광고비: {ad['cost']:,.0f}원",
                    )

            # 시뮬레이션 실행
            sim_results = []
            for ad in ad_summary:
                pct = changes[ad["platform"]]
                sim = pred.simulate_budget_change(ad["cost"], ad["roas"], pct, margin_rate)
                sim["platform"] = ad["platform"]
                sim["current_cost"] = ad["cost"]
                sim["current_revenue"] = ad["revenue"]
                sim["current_roas"] = ad["roas"]
                sim["change_pct"] = pct
                sim_results.append(sim)

            # 결과 표시
            total_add_cost = sum(s["add_cost"] for s in sim_results)
            total_add_rev = sum(s["add_revenue"] for s in sim_results)
            total_new_profit = sum(s["new_profit"] for s in sim_results)
            current_total_profit = sum(
                (ad["revenue"] * margin_rate) - ad["cost"] for ad in ad_summary
            )
            profit_change = total_new_profit - current_total_profit

            st.markdown("#### 시뮬레이션 결과")
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("추가 투자금액", f"{total_add_cost/1e6:+.0f}백만")
            r2.metric("추가 예상매출", f"{total_add_rev/1e6:+.0f}백만")
            r3.metric("순이익 변화", f"{profit_change/1e6:+.0f}백만")
            roi_pct = (total_add_rev / max(abs(total_add_cost), 1) * 100) if total_add_cost != 0 else 0
            r4.metric("투자 대비 수익률", f"{roi_pct:.0f}%")

            # Before vs After 비교 차트
            chart_data = []
            for sim in sim_results:
                chart_data.append({
                    "플랫폼": sim["platform"], "구분": "현재 매출",
                    "금액": sim["current_revenue"],
                })
                chart_data.append({
                    "플랫폼": sim["platform"], "구분": "시뮬레이션 매출",
                    "금액": sim["new_revenue"],
                })
                chart_data.append({
                    "플랫폼": sim["platform"], "구분": "현재 광고비",
                    "금액": sim["current_cost"],
                })
                chart_data.append({
                    "플랫폼": sim["platform"], "구분": "시뮬레이션 광고비",
                    "금액": sim["new_cost"],
                })

            chart_df = pd.DataFrame(chart_data)
            fig_sim = px.bar(
                chart_df, x="플랫폼", y="금액", color="구분",
                barmode="group", text_auto=".3s",
                color_discrete_map={
                    "현재 매출": "#aec7e8", "시뮬레이션 매출": "#1f77b4",
                    "현재 광고비": "#ffbb78", "시뮬레이션 광고비": "#ff7f0e",
                },
            )
            fig_sim.update_layout(template=TPL, height=400)
            st.plotly_chart(fig_sim, use_container_width=True)

            # 플랫폼별 상세
            st.markdown("#### 플랫폼별 상세 결과")
            detail_rows = []
            for sim in sim_results:
                detail_rows.append({
                    "플랫폼": sim["platform"],
                    "변경률": f"{sim['change_pct']:+d}%",
                    "현재광고비": f"{sim['current_cost']:,.0f}",
                    "변경광고비": f"{sim['new_cost']:,.0f}",
                    "현재ROAS": f"{sim['current_roas']:.0f}%",
                    "변경ROAS": f"{sim['adj_roas']:.0f}%",
                    "현재매출": f"{sim['current_revenue']:,.0f}",
                    "변경매출": f"{sim['new_revenue']:,.0f}",
                    "추가매출": f"{sim['add_revenue']:,.0f}",
                    "순이익": f"{sim['new_profit']:,.0f}",
                })
            st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)

            st.caption("※ ROAS 체감 효과 반영: 예산 증가 시 ROAS가 소폭 하락하는 것을 가정합니다.")

            # 광고 시뮬레이터 컨텍스트 런타임 보강 (기존 컨텍스트에 시뮬레이션 결과 추가)
            _sim_detail = "\n\n[시뮬레이션 결과]"
            for sim in sim_results:
                _sim_detail += "\n" + chat.summarize_metrics(
                    **{f"{sim['platform']}_예산변경률": f"{sim['change_pct']:+d}% (슬라이더 값={sim['change_pct']})",
                       f"{sim['platform']}_현재광고비": f"{sim['current_cost']:,.0f}원",
                       f"{sim['platform']}_변경후광고비": f"{sim['new_cost']:,.0f}원",
                       f"{sim['platform']}_현재ROAS": f"{sim['current_roas']:.0f}%",
                       f"{sim['platform']}_변경후ROAS": f"{sim['adj_roas']:.0f}%",
                       f"{sim['platform']}_현재매출": f"{sim['current_revenue']:,.0f}원",
                       f"{sim['platform']}_변경후매출": f"{sim['new_revenue']:,.0f}원",
                       f"{sim['platform']}_추가매출": f"{sim['add_revenue']:,.0f}원",
                       f"{sim['platform']}_순이익": f"{sim['new_profit']:,.0f}원"}
                )
            _sim_detail += "\n" + chat.summarize_metrics(
                총추가투자=f"{total_add_cost:,.0f}원",
                총추가매출=f"{total_add_rev:,.0f}원",
                순이익변화=f"{profit_change:,.0f}원",
                투자수익률=f"{roi_pct:.0f}%",
            )
            ai_contexts["광고 시뮬레이터"] += _sim_detail

# ── AI 우측 패널 렌더링 ──────────────────────────────────────
chat.render_panel(ai_col, "p2", ai_contexts)

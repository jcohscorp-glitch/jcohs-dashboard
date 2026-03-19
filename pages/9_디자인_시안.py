# -*- coding: utf-8 -*-
"""디자인 시안 비교 — A: Executive Dark / B: Slide Deck"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="디자인 시안", page_icon="🎨", layout="wide")

# ── 샘플 데이터 ──────────────────────────────────────────────
sample_sales = pd.DataFrame({
    "날짜": pd.date_range("2026-03-01", periods=19, freq="D"),
    "매출": [4200, 3800, 5100, 4700, 6300, 5500, 4900, 5800, 6100, 4300,
             5600, 6800, 7200, 5400, 6100, 5900, 7500, 6200, 5300],
    "주문건수": [42, 38, 51, 47, 63, 55, 49, 58, 61, 43, 56, 68, 72, 54, 61, 59, 75, 62, 53],
})
sample_sales["매출"] = sample_sales["매출"] * 10000

sample_channels = pd.DataFrame({
    "채널": ["네이버 드림프라이스", "네이버 조이코스", "네이버 한바샵", "쿠팡 드보르", "쿠팡 제이코스", "네이버 레이캅", "네이버 모그원"],
    "매출": [18500, 12300, 8700, 15200, 9800, 6500, 4200],
    "주문건수": [185, 123, 87, 152, 98, 65, 42],
    "전월대비": [12.5, -3.2, 8.1, 22.4, 15.7, -1.8, 5.3],
})
sample_channels["매출"] = sample_channels["매출"] * 10000

# ═══════════════════════════════════════════════════════════════
#  시안 선택
# ═══════════════════════════════════════════════════════════════
design = st.radio(
    "디자인 시안 선택",
    ["시안 A: Executive Dark", "시안 B: Slide Deck"],
    horizontal=True,
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════
#  시안 A: Executive Dark
# ═══════════════════════════════════════════════════════════════
if "A" in design:
    st.markdown("""
    <style>
    /* ── A: Executive Dark Theme ─────────────────── */
    .main .block-container {
        background: linear-gradient(180deg, #0F1117 0%, #1A1D29 50%, #0F1117 100%);
        color: #E8EAED;
        padding-top: 2rem;
    }
    .main { background-color: #0F1117; }

    /* 글래스 카드 */
    .glass-card {
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
        transition: all 0.3s ease;
    }
    .glass-card:hover {
        background: rgba(255,255,255,0.08);
        border-color: rgba(99,102,241,0.3);
        box-shadow: 0 8px 32px rgba(99,102,241,0.15);
    }

    /* KPI 카드 */
    .kpi-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 20px 24px;
        text-align: center;
    }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #818CF8, #6366F1, #A78BFA);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.2;
    }
    .kpi-label {
        font-size: 0.78rem;
        font-weight: 600;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 8px;
    }
    .kpi-delta-up {
        color: #34D399;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .kpi-delta-down {
        color: #F87171;
        font-size: 0.85rem;
        font-weight: 600;
    }

    /* 섹션 제목 */
    .section-title-dark {
        font-size: 1.3rem;
        font-weight: 700;
        color: #E8EAED;
        margin-bottom: 0.3rem;
    }
    .section-sub-dark {
        font-size: 0.82rem;
        color: #6B7280;
        margin-bottom: 1.2rem;
    }

    /* 프로그레스 바 */
    .progress-dark-bg {
        background: rgba(255,255,255,0.06);
        border-radius: 12px;
        height: 28px;
        overflow: hidden;
        position: relative;
    }
    .progress-dark-fill {
        background: linear-gradient(90deg, #6366F1, #8B5CF6, #A78BFA);
        height: 100%;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding-right: 12px;
        font-size: 0.75rem;
        font-weight: 700;
        color: white;
    }

    /* 순위 테이블 */
    .rank-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 16px;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .rank-row:hover { background: rgba(255,255,255,0.03); }
    .rank-num {
        display: inline-flex;
        width: 26px;
        height: 26px;
        border-radius: 8px;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        font-weight: 700;
        margin-right: 12px;
    }
    .rank-1 { background: linear-gradient(135deg, #F59E0B, #D97706); color: white; }
    .rank-2 { background: rgba(156,163,175,0.3); color: #D1D5DB; }
    .rank-3 { background: rgba(180,83,9,0.3); color: #FBBF24; }
    .rank-n { background: rgba(255,255,255,0.06); color: #9CA3AF; }

    /* 메트릭 오버라이드 */
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 16px !important;
    }
    [data-testid="stMetricLabel"] { color: #9CA3AF !important; }
    [data-testid="stMetricValue"] { color: #E8EAED !important; }

    /* 탭 다크 */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255,255,255,0.04);
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] { color: #9CA3AF; }
    .stTabs [aria-selected="true"] {
        background: rgba(99,102,241,0.2) !important;
        color: #A5B4FC !important;
    }

    h1, h2, h3, h4 { color: #E8EAED !important; }
    p, span, label { color: #D1D5DB; }
    </style>
    """, unsafe_allow_html=True)

    # ── 헤더 ──
    st.markdown("""
    <div style="text-align:center; padding:1rem 0 2rem;">
        <div style="font-size:0.8rem; font-weight:600; color:#6366F1; letter-spacing:0.15em; text-transform:uppercase; margin-bottom:8px;">
            JCOHS CORPORATION
        </div>
        <div style="font-size:2.2rem; font-weight:800; background:linear-gradient(135deg,#818CF8,#6366F1,#A78BFA);
             -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
            매출 대시보드
        </div>
        <div style="font-size:0.9rem; color:#6B7280; margin-top:4px;">
            2026년 3월 실시간 현황 — 월 매출 목표 10억
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI 카드 ──
    total_sales = sample_sales["매출"].sum()
    target = 1_000_000_000
    pct = total_sales / target * 100

    cols = st.columns(4)
    kpi_data = [
        ("총 매출", f"{total_sales/1e8:.1f}억", "+12.5%", True),
        ("주문건수", f"{sample_sales['주문건수'].sum():,}건", "+8.3%", True),
        ("목표달성률", f"{pct:.1f}%", f"잔여 {(target-total_sales)/1e8:.1f}억", True),
        ("평균객단가", f"{total_sales/sample_sales['주문건수'].sum():,.0f}원", "-2.1%", False),
    ]

    for col, (label, value, delta, is_up) in zip(cols, kpi_data):
        delta_class = "kpi-delta-up" if is_up else "kpi-delta-down"
        delta_icon = "▲" if is_up else "▼"
        col.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="{delta_class}">{delta_icon} {delta}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 목표 프로그레스 ──
    st.markdown(f"""
    <div class="glass-card">
        <div class="section-title-dark">🎯 월간 목표 달성률</div>
        <div class="section-sub-dark">2026년 3월 | 목표 10억원</div>
        <div class="progress-dark-bg">
            <div class="progress-dark-fill" style="width:{min(pct,100):.0f}%">{pct:.1f}%</div>
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:8px; font-size:0.78rem; color:#6B7280;">
            <span>현재 {total_sales/1e8:.1f}억</span>
            <span>목표 10.0억</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 차트 영역 ──
    col_chart, col_rank = st.columns([3, 2])

    with col_chart:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title-dark">📈 일별 매출 추이</div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=sample_sales["날짜"], y=sample_sales["매출"],
            mode="lines+markers",
            line=dict(color="#818CF8", width=3),
            marker=dict(size=6, color="#6366F1"),
            fill="tozeroy",
            fillcolor="rgba(99,102,241,0.1)",
        ))
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=350,
            margin=dict(t=20, b=30, l=50, r=20),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickformat=",.0f"),
            font=dict(color="#9CA3AF"),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_rank:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title-dark">🏆 채널별 매출 순위</div>', unsafe_allow_html=True)

        rank_html = ""
        for i, row in sample_channels.iterrows():
            rank_class = f"rank-{i+1}" if i < 3 else "rank-n"
            delta_icon = "▲" if row["전월대비"] > 0 else "▼"
            delta_color = "#34D399" if row["전월대비"] > 0 else "#F87171"
            rank_html += f"""
            <div class="rank-row">
                <div style="display:flex; align-items:center;">
                    <span class="rank-num {rank_class}">{i+1}</span>
                    <span style="color:#E8EAED; font-weight:500; font-size:0.9rem;">{row['채널']}</span>
                </div>
                <div style="text-align:right;">
                    <div style="color:#E8EAED; font-weight:700; font-size:0.95rem;">{row['매출']/1e4:,.0f}만</div>
                    <div style="color:{delta_color}; font-size:0.78rem;">{delta_icon} {abs(row['전월대비'])}%</div>
                </div>
            </div>
            """
        st.markdown(rank_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── 채널 도넛 ──
    st.markdown("<br>", unsafe_allow_html=True)
    col_donut, col_bar = st.columns(2)

    with col_donut:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title-dark">📊 채널별 매출 비중</div>', unsafe_allow_html=True)
        fig_donut = go.Figure(go.Pie(
            labels=sample_channels["채널"],
            values=sample_channels["매출"],
            hole=0.6,
            marker=dict(colors=["#6366F1", "#8B5CF6", "#A78BFA", "#F59E0B", "#FBBF24", "#34D399", "#6EE7B7"]),
            textinfo="percent",
            textfont=dict(color="white", size=12),
        ))
        fig_donut.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=320,
            margin=dict(t=20, b=20, l=20, r=20),
            showlegend=True,
            legend=dict(font=dict(color="#9CA3AF", size=11)),
        )
        st.plotly_chart(fig_donut, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_bar:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title-dark">📉 전월 대비 성장률</div>', unsafe_allow_html=True)
        colors = ["#34D399" if v > 0 else "#F87171" for v in sample_channels["전월대비"]]
        fig_bar = go.Figure(go.Bar(
            y=sample_channels["채널"],
            x=sample_channels["전월대비"],
            orientation="h",
            marker_color=colors,
            text=[f"{v:+.1f}%" for v in sample_channels["전월대비"]],
            textposition="outside",
            textfont=dict(color="#D1D5DB", size=11),
        ))
        fig_bar.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=320,
            margin=dict(t=20, b=20, l=120, r=60),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)", zeroline=True,
                      zerolinecolor="rgba(255,255,255,0.1)"),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"),
            font=dict(color="#9CA3AF"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  시안 B: Slide Deck
# ═══════════════════════════════════════════════════════════════
else:
    st.markdown("""
    <style>
    /* ── B: Slide Deck Theme ─────────────────────── */
    .main .block-container {
        background: #FFFFFF;
        padding-top: 2rem;
        max-width: 1200px;
    }

    /* 슬라이드 섹션 */
    .slide-section {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 32px 36px;
        margin-bottom: 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06);
        border: 1px solid rgba(0,0,0,0.04);
    }

    /* 슬라이드 번호 */
    .slide-num {
        display: inline-block;
        width: 32px;
        height: 32px;
        border-radius: 10px;
        background: linear-gradient(135deg, #3B82F6, #2563EB);
        color: white;
        text-align: center;
        line-height: 32px;
        font-weight: 800;
        font-size: 0.85rem;
        margin-right: 12px;
        vertical-align: middle;
    }
    .slide-title {
        display: inline;
        font-size: 1.4rem;
        font-weight: 800;
        color: #1E293B;
        vertical-align: middle;
    }
    .slide-subtitle {
        font-size: 0.82rem;
        color: #94A3B8;
        margin: 4px 0 20px 44px;
    }

    /* KPI 카드 (컬러 상단 라인) */
    .kpi-slide {
        background: #F8FAFC;
        border-radius: 16px;
        padding: 20px 24px;
        text-align: center;
        border-top: 4px solid;
        transition: transform 0.2s;
    }
    .kpi-slide:hover { transform: translateY(-3px); }
    .kpi-slide-value {
        font-size: 2rem;
        font-weight: 800;
        color: #1E293B;
        line-height: 1.2;
    }
    .kpi-slide-label {
        font-size: 0.75rem;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 8px;
    }
    .kpi-slide-delta {
        font-size: 0.82rem;
        font-weight: 600;
        margin-top: 4px;
    }

    /* 진행 바 */
    .progress-slide-bg {
        background: #E2E8F0;
        border-radius: 99px;
        height: 32px;
        overflow: hidden;
        position: relative;
    }
    .progress-slide-fill {
        height: 100%;
        border-radius: 99px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.8rem;
        font-weight: 700;
        color: white;
        text-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }

    /* 인사이트 뱃지 */
    .insight-badge {
        display: inline-block;
        background: linear-gradient(135deg, #EFF6FF, #DBEAFE);
        color: #2563EB;
        padding: 6px 14px;
        border-radius: 99px;
        font-size: 0.78rem;
        font-weight: 600;
        margin: 4px 4px 4px 0;
    }

    /* 채널 카드 */
    .channel-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 16px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        transition: all 0.2s;
    }
    .channel-card:hover {
        border-color: #3B82F6;
        box-shadow: 0 2px 12px rgba(59,130,246,0.1);
    }

    /* 메트릭 오버라이드 */
    [data-testid="stMetric"] {
        background: #F8FAFC !important;
        border: none !important;
        border-radius: 16px !important;
        border-top: 4px solid #3B82F6 !important;
    }

    /* 탭 */
    .stTabs [data-baseweb="tab-list"] {
        background: #F1F5F9;
        border-radius: 14px;
        padding: 4px;
    }
    .stTabs [aria-selected="true"] {
        background: white !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        color: #2563EB !important;
        font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── SLIDE 0: 표지 ──
    st.markdown("""
    <div class="slide-section" style="text-align:center; padding:48px 36px; background:linear-gradient(135deg, #EFF6FF 0%, #FFFFFF 50%, #F0FDF4 100%);">
        <div style="font-size:0.75rem; font-weight:700; color:#3B82F6; letter-spacing:0.2em; text-transform:uppercase;">
            JCOHS Corporation · Monthly Report
        </div>
        <div style="font-size:2.4rem; font-weight:800; color:#1E293B; margin:12px 0 8px;">
            매출 대시보드
        </div>
        <div style="font-size:1rem; color:#64748B;">
            2026년 3월 · 월 매출 목표 <span style="color:#2563EB; font-weight:700;">10억원</span>
        </div>
        <div style="margin-top:20px;">
            <span class="insight-badge">📅 3월 19일 기준</span>
            <span class="insight-badge">📊 7개 채널 통합</span>
            <span class="insight-badge">🎯 목표달성 진행 중</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── SLIDE 1: KPI 요약 ──
    total_sales = sample_sales["매출"].sum()
    target = 1_000_000_000
    pct = total_sales / target * 100

    st.markdown("""
    <div class="slide-section">
        <span class="slide-num">1</span>
        <span class="slide-title">핵심 지표 요약</span>
        <div class="slide-subtitle">Key Performance Indicators — 이번 달 누적 성과</div>
    """, unsafe_allow_html=True)

    cols = st.columns(4)
    kpi_configs = [
        ("총 매출", f"{total_sales/1e8:.1f}억", "▲ +12.5%", "#3B82F6", "#22C55E"),
        ("주문건수", f"{sample_sales['주문건수'].sum():,}건", "▲ +8.3%", "#8B5CF6", "#22C55E"),
        ("목표달성률", f"{pct:.1f}%", f"잔여 {(target-total_sales)/1e8:.1f}억", "#F59E0B", "#64748B"),
        ("평균객단가", f"{total_sales/sample_sales['주문건수'].sum():,.0f}원", "▼ -2.1%", "#EF4444", "#EF4444"),
    ]

    for col, (label, value, delta, border_color, delta_color) in zip(cols, kpi_configs):
        col.markdown(f"""
        <div class="kpi-slide" style="border-top-color:{border_color};">
            <div class="kpi-slide-label">{label}</div>
            <div class="kpi-slide-value">{value}</div>
            <div class="kpi-slide-delta" style="color:{delta_color};">{delta}</div>
        </div>
        """, unsafe_allow_html=True)

    # 프로그레스
    gradient = "linear-gradient(90deg, #3B82F6, #2563EB, #8B5CF6)"
    st.markdown(f"""
    <div style="margin-top:20px;">
        <div style="display:flex; justify-content:space-between; font-size:0.82rem; color:#64748B; margin-bottom:6px;">
            <span>월간 목표 달성률</span>
            <span style="font-weight:700; color:#1E293B;">{total_sales/1e8:.1f}억 / 10.0억</span>
        </div>
        <div class="progress-slide-bg">
            <div class="progress-slide-fill" style="width:{min(pct,100):.0f}%; background:{gradient};">{pct:.1f}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── SLIDE 2: 매출 추이 ──
    st.markdown("""
    <div class="slide-section">
        <span class="slide-num">2</span>
        <span class="slide-title">일별 매출 추이</span>
        <div class="slide-subtitle">Daily Sales Trend — 3월 일별 매출 변화</div>
    """, unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sample_sales["날짜"], y=sample_sales["매출"],
        mode="lines+markers",
        line=dict(color="#3B82F6", width=3, shape="spline"),
        marker=dict(size=7, color="#3B82F6", line=dict(width=2, color="white")),
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.06)",
    ))
    # 평균선
    avg = sample_sales["매출"].mean()
    fig.add_hline(y=avg, line_dash="dash", line_color="#94A3B8",
                  annotation_text=f"평균 {avg/1e4:,.0f}만",
                  annotation_position="top right",
                  annotation_font=dict(color="#64748B", size=11))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=380,
        margin=dict(t=20, b=40, l=60, r=20),
        xaxis=dict(gridcolor="#F1F5F9", showline=True, linecolor="#E2E8F0"),
        yaxis=dict(gridcolor="#F1F5F9", tickformat=",.0f", showline=True, linecolor="#E2E8F0"),
        font=dict(family="Pretendard, sans-serif", color="#64748B"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    # 인사이트 뱃지
    max_day = sample_sales.loc[sample_sales["매출"].idxmax()]
    st.markdown(f"""
    <div style="margin-top:8px;">
        <span class="insight-badge">🔥 최고 매출일: {max_day['날짜'].strftime('%m/%d')} ({max_day['매출']/1e4:,.0f}만원)</span>
        <span class="insight-badge">📊 일평균: {avg/1e4:,.0f}만원</span>
        <span class="insight-badge">📈 추세: 완만한 상승세</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── SLIDE 3: 채널별 성과 ──
    st.markdown("""
    <div class="slide-section">
        <span class="slide-num">3</span>
        <span class="slide-title">채널별 매출 성과</span>
        <div class="slide-subtitle">Channel Performance — 스토어별 매출 비교 및 성장률</div>
    """, unsafe_allow_html=True)

    col_pie, col_list = st.columns([2, 3])

    with col_pie:
        fig_pie = go.Figure(go.Pie(
            labels=sample_channels["채널"],
            values=sample_channels["매출"],
            hole=0.55,
            marker=dict(colors=["#3B82F6", "#8B5CF6", "#06B6D4", "#F59E0B", "#FBBF24", "#22C55E", "#6EE7B7"]),
            textinfo="percent",
            textfont=dict(size=12, color="#1E293B"),
            insidetextorientation="horizontal",
        ))
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            height=340,
            margin=dict(t=10, b=10, l=10, r=10),
            showlegend=False,
            font=dict(family="Pretendard, sans-serif"),
        )
        # 중앙 텍스트
        fig_pie.add_annotation(
            text=f"<b>{total_sales/1e8:.1f}억</b><br><span style='font-size:11px;color:#64748B'>총 매출</span>",
            showarrow=False, font=dict(size=18, color="#1E293B"),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_list:
        channel_colors = ["#3B82F6", "#8B5CF6", "#06B6D4", "#F59E0B", "#FBBF24", "#22C55E", "#6EE7B7"]
        for i, row in sample_channels.iterrows():
            pct_of_total = row["매출"] / total_sales * 100
            delta_color = "#22C55E" if row["전월대비"] > 0 else "#EF4444"
            delta_icon = "▲" if row["전월대비"] > 0 else "▼"
            st.markdown(f"""
            <div class="channel-card">
                <div style="display:flex; align-items:center;">
                    <div style="width:4px; height:36px; border-radius:4px; background:{channel_colors[i]}; margin-right:14px;"></div>
                    <div>
                        <div style="font-weight:700; color:#1E293B; font-size:0.92rem;">{row['채널']}</div>
                        <div style="font-size:0.78rem; color:#94A3B8;">{row['주문건수']}건 · 비중 {pct_of_total:.1f}%</div>
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-weight:800; color:#1E293B; font-size:1rem;">{row['매출']/1e4:,.0f}만</div>
                    <div style="color:{delta_color}; font-size:0.8rem; font-weight:600;">{delta_icon} {abs(row['전월대비'])}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── SLIDE 4: 요약 ──
    st.markdown(f"""
    <div class="slide-section" style="background:linear-gradient(135deg, #EFF6FF 0%, #F0FDF4 100%);">
        <span class="slide-num">4</span>
        <span class="slide-title">이번 달 요약 & Action</span>
        <div class="slide-subtitle">Monthly Summary — 주요 인사이트 및 다음 액션</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:8px;">
            <div style="background:white; border-radius:14px; padding:20px; border-left:4px solid #22C55E;">
                <div style="font-weight:700; color:#1E293B; margin-bottom:8px;">✅ 성과</div>
                <ul style="color:#475569; font-size:0.88rem; margin:0; padding-left:18px; line-height:1.8;">
                    <li>쿠팡 드보르 전월 대비 <b>+22.4%</b> 성장</li>
                    <li>네이버 드림프라이스 매출 1위 유지</li>
                    <li>총 주문건수 전월 대비 증가</li>
                </ul>
            </div>
            <div style="background:white; border-radius:14px; padding:20px; border-left:4px solid #F59E0B;">
                <div style="font-weight:700; color:#1E293B; margin-bottom:8px;">⚡ Action Items</div>
                <ul style="color:#475569; font-size:0.88rem; margin:0; padding-left:18px; line-height:1.8;">
                    <li>조이코스 매출 하락 원인 분석 필요</li>
                    <li>레이캅 프로모션 검토</li>
                    <li>객단가 하락 대응 — 번들 상품 기획</li>
                </ul>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

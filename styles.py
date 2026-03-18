# -*- coding: utf-8 -*-
"""공통 스타일 — CSS · Plotly 템플릿 · 컬러 팔레트"""

import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio

# ═══════════════════════════════════════════════════════════════
#  컬러 팔레트
# ═══════════════════════════════════════════════════════════════
COLORS = {
    "primary": "#4361EE",
    "secondary": "#3A0CA3",
    "success": "#06D6A0",
    "warning": "#FFD166",
    "danger": "#EF476F",
    "info": "#118AB2",
    "light": "#F8F9FA",
    "dark": "#212529",
    "gray": "#6C757D",
    "bg": "#FAFBFC",
}

PALETTE = ["#4361EE", "#3A0CA3", "#7209B7", "#F72585", "#4CC9F0",
           "#06D6A0", "#FFD166", "#EF476F", "#118AB2", "#073B4C"]

GRADIENT_BLUE = ["#E8F4FD", "#B3D9F2", "#7DBDE8", "#4361EE", "#3A0CA3"]
GRADIENT_GREEN = ["#E8FDF4", "#B3F2D9", "#7DE8BD", "#06D6A0", "#048A65"]
GRADIENT_WARM = ["#FFF3E0", "#FFD166", "#FF9F1C", "#EF476F", "#D62828"]


# ═══════════════════════════════════════════════════════════════
#  Plotly 템플릿
# ═══════════════════════════════════════════════════════════════
def get_plotly_template():
    """깔끔한 프레젠테이션 스타일 plotly 템플릿"""
    return go.layout.Template(
        layout=go.Layout(
            font=dict(family="Pretendard, Noto Sans KR, sans-serif", size=13, color="#333"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=40, b=30, l=40, r=20),
            colorway=PALETTE,
            xaxis=dict(
                showgrid=True, gridwidth=1, gridcolor="rgba(0,0,0,0.05)",
                showline=False, zeroline=False,
            ),
            yaxis=dict(
                showgrid=True, gridwidth=1, gridcolor="rgba(0,0,0,0.05)",
                showline=False, zeroline=False,
            ),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                bgcolor="rgba(0,0,0,0)", font=dict(size=12),
            ),
            hoverlabel=dict(
                bgcolor="white", font_size=13, font_family="Pretendard, sans-serif",
                bordercolor="rgba(0,0,0,0.1)",
            ),
        )
    )


TPL = get_plotly_template()


# ═══════════════════════════════════════════════════════════════
#  CSS 주입
# ═══════════════════════════════════════════════════════════════
def inject_css():
    """대시보드 전역 CSS"""
    st.markdown("""
    <style>
    /* ── 메트릭 카드 ──────────────────────────────── */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%);
        border: 1px solid rgba(67, 97, 238, 0.12);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(67, 97, 238, 0.12);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        color: #6C757D !important;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: #212529 !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
    }

    /* ── 탭 스타일 ────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #f0f2f6;
        border-radius: 12px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 8px 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .stTabs [aria-selected="true"] {
        background: white !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }

    /* ── 컨테이너 (border=True) ───────────────────── */
    [data-testid="stVerticalBlock"] > div:has(> [data-testid="stVerticalBlockBorderWrapper"]) {
        border-radius: 12px;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        border-color: rgba(67, 97, 238, 0.1) !important;
        background: linear-gradient(135deg, #ffffff 0%, #fafbff 100%) !important;
    }

    /* ── 프로그레스 바 ────────────────────────────── */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #4361EE, #7209B7, #F72585) !important;
        border-radius: 8px;
    }
    .stProgress > div > div {
        border-radius: 8px;
        background: #e9ecef;
    }

    /* ── 데이터프레임 ─────────────────────────────── */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid rgba(0,0,0,0.06);
    }

    /* ── 사이드바 버튼 ────────────────────────────── */
    .stSidebar .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid rgba(67, 97, 238, 0.2);
        transition: all 0.2s;
    }
    .stSidebar .stButton > button:hover {
        border-color: #4361EE;
        color: #4361EE;
    }

    /* ── 구분선 ───────────────────────────────────── */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(67,97,238,0.2), transparent);
        margin: 1.5rem 0;
    }

    /* ── 마크다운 헤더 ────────────────────────────── */
    h3 {
        color: #212529;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    /* ── 다운로드 버튼 ────────────────────────────── */
    .stDownloadButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)


def styled_header(icon: str, title: str, subtitle: str = ""):
    """섹션 헤더"""
    sub = f'<p style="color:#6C757D; font-size:0.9rem; margin:0;">{subtitle}</p>' if subtitle else ""
    st.markdown(f"""
    <div style="margin-bottom:1rem;">
        <h3 style="margin:0;">{icon} {title}</h3>
        {sub}
    </div>
    """, unsafe_allow_html=True)

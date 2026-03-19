# -*- coding: utf-8 -*-
"""공통 스타일 — Slide Deck 디자인 시스템"""

import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio

# ═══════════════════════════════════════════════════════════════
#  컬러 팔레트
# ═══════════════════════════════════════════════════════════════
COLORS = {
    "primary": "#3B82F6",
    "secondary": "#8B5CF6",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "info": "#06B6D4",
    "light": "#F8FAFC",
    "dark": "#1E293B",
    "gray": "#64748B",
    "bg": "#FFFFFF",
    "border": "#E2E8F0",
    "text": "#1E293B",
    "text_sub": "#64748B",
    "text_muted": "#94A3B8",
}

PALETTE = ["#3B82F6", "#8B5CF6", "#06B6D4", "#F59E0B", "#FBBF24",
           "#22C55E", "#EF4444", "#EC4899", "#14B8A6", "#6366F1"]

CHANNEL_COLORS = ["#3B82F6", "#8B5CF6", "#06B6D4", "#F59E0B", "#FBBF24",
                  "#22C55E", "#6EE7B7"]

GRADIENT_BLUE = ["#EFF6FF", "#BFDBFE", "#60A5FA", "#3B82F6", "#2563EB"]
GRADIENT_GREEN = ["#F0FDF4", "#BBF7D0", "#4ADE80", "#22C55E", "#16A34A"]
GRADIENT_WARM = ["#FFFBEB", "#FDE68A", "#FBBF24", "#F59E0B", "#D97706"]


# ═══════════════════════════════════════════════════════════════
#  Plotly 템플릿
# ═══════════════════════════════════════════════════════════════
def get_plotly_template():
    """Slide Deck 스타일 Plotly 템플릿"""
    return go.layout.Template(
        layout=go.Layout(
            font=dict(family="Pretendard, Noto Sans KR, sans-serif", size=13, color="#64748B"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=40, b=30, l=50, r=20),
            colorway=PALETTE,
            xaxis=dict(
                showgrid=True, gridwidth=1, gridcolor="#F1F5F9",
                showline=True, linecolor="#E2E8F0", zeroline=False,
            ),
            yaxis=dict(
                showgrid=True, gridwidth=1, gridcolor="#F1F5F9",
                showline=True, linecolor="#E2E8F0", zeroline=False,
            ),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                bgcolor="rgba(0,0,0,0)", font=dict(size=12, color="#64748B"),
            ),
            hoverlabel=dict(
                bgcolor="white", font_size=13, font_family="Pretendard, sans-serif",
                bordercolor="#E2E8F0",
            ),
            hovermode="x unified",
        )
    )


TPL = get_plotly_template()

# 슬라이드 번호 카운터 (페이지별 리셋)
_slide_counter = {"n": 0}


# ═══════════════════════════════════════════════════════════════
#  CSS 주입
# ═══════════════════════════════════════════════════════════════
def inject_css():
    """Slide Deck 전역 CSS"""
    st.markdown("""
    <style>
    /* ── 기본 레이아웃 ────────────────────────────── */
    .main .block-container {
        max-width: 1200px;
        padding-top: 2rem;
    }

    /* ── 슬라이드 섹션 ────────────────────────────── */
    .slide-section {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 32px 36px;
        margin-bottom: 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06);
        border: 1px solid rgba(0,0,0,0.04);
    }

    /* ── 슬라이드 번호 + 제목 ─────────────────────── */
    .slide-num {
        display: inline-block;
        width: 32px; height: 32px;
        border-radius: 10px;
        background: linear-gradient(135deg, #3B82F6, #2563EB);
        color: white;
        text-align: center; line-height: 32px;
        font-weight: 800; font-size: 0.85rem;
        margin-right: 12px; vertical-align: middle;
    }
    .slide-title {
        display: inline;
        font-size: 1.4rem; font-weight: 800;
        color: #1E293B; vertical-align: middle;
    }
    .slide-subtitle {
        font-size: 0.82rem; color: #94A3B8;
        margin: 4px 0 20px 44px;
    }

    /* ── KPI 카드 (컬러 상단 라인) ────────────────── */
    [data-testid="stMetric"] {
        background: #F8FAFC !important;
        border: none !important;
        border-radius: 16px !important;
        border-top: 4px solid #3B82F6 !important;
        padding: 16px 20px !important;
        box-shadow: none !important;
        transition: transform 0.2s;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 16px rgba(59,130,246,0.1) !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
        font-weight: 700 !important;
        color: #64748B !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.7rem !important;
        font-weight: 800 !important;
        color: #1E293B !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
    }

    /* ── 탭 스타일 ────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #F1F5F9;
        border-radius: 14px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 8px 20px;
        font-weight: 600;
        font-size: 0.9rem;
        color: #64748B;
    }
    .stTabs [aria-selected="true"] {
        background: white !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        color: #2563EB !important;
        font-weight: 700;
    }

    /* ── 컨테이너 (border=True) ───────────────────── */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px !important;
        border-color: #E2E8F0 !important;
        background: #FFFFFF !important;
    }

    /* ── 프로그레스 바 ────────────────────────────── */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #3B82F6, #2563EB, #8B5CF6) !important;
        border-radius: 99px;
    }
    .stProgress > div > div {
        border-radius: 99px;
        background: #E2E8F0;
    }

    /* ── 데이터프레임 ─────────────────────────────── */
    [data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid #E2E8F0;
    }

    /* ── 사이드바 ─────────────────────────────────── */
    .stSidebar .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid #E2E8F0;
        transition: all 0.2s;
    }
    .stSidebar .stButton > button:hover {
        border-color: #3B82F6;
        color: #3B82F6;
        background: #EFF6FF;
    }

    /* ── 인사이트 뱃지 ────────────────────────────── */
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
    .insight-badge-green {
        background: linear-gradient(135deg, #F0FDF4, #DCFCE7);
        color: #16A34A;
    }
    .insight-badge-amber {
        background: linear-gradient(135deg, #FFFBEB, #FEF3C7);
        color: #D97706;
    }
    .insight-badge-red {
        background: linear-gradient(135deg, #FEF2F2, #FECACA);
        color: #DC2626;
    }

    /* ── 구분선 ───────────────────────────────────── */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #E2E8F0, transparent);
        margin: 1.5rem 0;
    }

    /* ── 마크다운 헤더 ────────────────────────────── */
    h1 { color: #1E293B; font-weight: 800; }
    h2 { color: #1E293B; font-weight: 700; }
    h3 { color: #1E293B; font-weight: 700; margin-bottom: 0.5rem; }
    h4 { color: #334155; font-weight: 700; }

    /* ── 다운로드 버튼 ────────────────────────────── */
    .stDownloadButton > button {
        border-radius: 10px;
        font-weight: 600;
        border: 1px solid #E2E8F0;
    }

    /* ── expander ─────────────────────────────────── */
    [data-testid="stExpander"] {
        border-radius: 14px;
        border-color: #E2E8F0;
    }
    </style>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  헬퍼 함수
# ═══════════════════════════════════════════════════════════════
def page_header(title: str, subtitle: str = "", badge_text: str = "JCOHS Corporation"):
    """페이지 상단 표지 스타일 헤더"""
    _slide_counter["n"] = 0  # 슬라이드 번호 리셋
    badge_html = f'<div style="font-size:0.75rem;font-weight:700;color:#3B82F6;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:8px;">{badge_text}</div>' if badge_text else ""
    sub_html = f'<div style="font-size:0.92rem;color:#64748B;margin-top:4px;">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div style="text-align:center;padding:1.5rem 0 2rem;background:linear-gradient(135deg,#EFF6FF 0%,#FFFFFF 50%,#F0FDF4 100%);border-radius:20px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,0.04),0 4px 16px rgba(0,0,0,0.04);">'
        f'{badge_html}'
        f'<div style="font-size:2.2rem;font-weight:800;color:#1E293B;">{title}</div>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def slide_header(title: str, subtitle: str = ""):
    """슬라이드 번호 + 제목 (자동 번호 증가)"""
    _slide_counter["n"] += 1
    n = _slide_counter["n"]
    sub = f'<div class="slide-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div style="margin-bottom:16px;">'
        f'<span class="slide-num">{n}</span>'
        f'<span class="slide-title">{title}</span>'
        f'{sub}</div>',
        unsafe_allow_html=True,
    )


def styled_header(icon: str, title: str, subtitle: str = ""):
    """섹션 헤더 (기존 호환)"""
    sub = f'<p style="color:#94A3B8;font-size:0.85rem;margin:4px 0 0 0;">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div style="margin-bottom:1rem;">'
        f'<h3 style="margin:0;color:#1E293B;">{icon} {title}</h3>'
        f'{sub}</div>',
        unsafe_allow_html=True,
    )


def badge(text: str, variant: str = "default"):
    """인사이트 뱃지 HTML 반환"""
    cls = {
        "default": "insight-badge",
        "green": "insight-badge insight-badge-green",
        "amber": "insight-badge insight-badge-amber",
        "red": "insight-badge insight-badge-red",
    }.get(variant, "insight-badge")
    return f'<span class="{cls}">{text}</span>'


def kpi_card(label: str, value: str, delta: str = "", delta_up: bool = True,
             border_color: str = "#3B82F6"):
    """커스텀 KPI 카드 HTML 반환"""
    delta_color = "#22C55E" if delta_up else "#EF4444"
    delta_icon = "▲" if delta_up else "▼"
    delta_html = f'<div style="color:{delta_color}; font-size:0.82rem; font-weight:600; margin-top:4px;">{delta_icon} {delta}</div>' if delta else ""
    return f"""
    <div style="background:#F8FAFC; border-radius:16px; padding:20px 24px;
         text-align:center; border-top:4px solid {border_color}; transition:transform 0.2s;"
         onmouseover="this.style.transform='translateY(-3px)'"
         onmouseout="this.style.transform='none'">
        <div style="font-size:0.75rem; font-weight:700; color:#64748B;
             text-transform:uppercase; letter-spacing:0.08em; margin-bottom:8px;">{label}</div>
        <div style="font-size:2rem; font-weight:800; color:#1E293B; line-height:1.2;">{value}</div>
        {delta_html}
    </div>
    """


def progress_bar(value: float, max_val: float, label_left: str = "", label_right: str = ""):
    """커스텀 프로그레스 바"""
    pct = min(value / max_val * 100, 100) if max_val > 0 else 0
    gradient = "linear-gradient(90deg, #3B82F6, #2563EB, #8B5CF6)"
    labels = ""
    if label_left or label_right:
        labels = f"""
        <div style="display:flex; justify-content:space-between; margin-top:8px;
             font-size:0.78rem; color:#64748B;">
            <span>{label_left}</span><span style="font-weight:700; color:#1E293B;">{label_right}</span>
        </div>
        """
    return f"""
    <div>
        <div style="background:#E2E8F0; border-radius:99px; height:32px; overflow:hidden;">
            <div style="height:100%; width:{pct:.0f}%; border-radius:99px; background:{gradient};
                 display:flex; align-items:center; justify-content:center;
                 font-size:0.8rem; font-weight:700; color:white;
                 text-shadow:0 1px 2px rgba(0,0,0,0.2);">{pct:.1f}%</div>
        </div>
        {labels}
    </div>
    """

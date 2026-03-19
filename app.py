# -*- coding: utf-8 -*-
"""월 매출 10억 만들기 - 메인 대시보드"""

import streamlit as st
import pandas as pd
from datetime import datetime
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

# ── 사이드바 ─────────────────────────────────────────────────
with st.sidebar:
    st.title("JCOHS 대시보드")
    st.caption("월 매출 10억 달성 관리")
    st.divider()
    if st.button("🔄 데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.info("📌 좌측 메뉴에서 페이지를 선택하세요")

# ── 타이틀 ───────────────────────────────────────────────────
S.page_header("JCOHS 월 매출 10억 만들기", "커머스 통합 매출 관리 대시보드")

# ── 실시간 요약 KPI ──────────────────────────────────────────
TARGET = config.MONTHLY_TARGET
try:
    df_26 = dl.load_sales_26()
    if not df_26.empty:
        now = datetime.now()
        df_cur = df_26[(df_26["주문일시"].dt.year == now.year) & (df_26["주문일시"].dt.month == now.month)]
        cur_sales = df_cur["총 판매금액"].sum()
        days_total = calendar.monthrange(now.year, now.month)[1]
        daily_avg = cur_sales / max(now.day, 1)
        projected = daily_avg * days_total
        gap = TARGET - cur_sales
        progress = min(cur_sales / TARGET, 1.0)

        st.progress(progress, text=f"이번 달 목표 달성률: {progress*100:.1f}%")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("현재 매출", f"{cur_sales/1e8:.2f}억")
        c2.metric("목표 갭", f"{gap/1e8:.2f}억" if gap > 0 else "달성!")
        c3.metric("일평균", f"{daily_avg/1e6:.0f}백만")
        c4.metric("월말 예상", f"{projected/1e8:.1f}억",
                  delta=f"{'달성 가능' if projected >= TARGET else f'{(TARGET-projected)/1e8:.1f}억 부족'}")
except Exception:
    pass

st.markdown("")

# ── 3 필러 네비게이션 ────────────────────────────────────────
S.slide_header("대시보드 3대 필러", "Dashboard 3 Pillars")

col1, col2, col3 = st.columns(3)

with col1:
    with st.container(border=True):
        st.markdown("### 📊 현재 현황")
        st.caption("지금 매출은 어디까지 왔나?")
        st.markdown("""
        - 목표 달성률 & 게이지
        - 채널/브랜드/상품 매출 분석
        - 4대 플랫폼 광고 효율
        - 네이버 스토어 & 쿠팡 키워드
        """)
        st.page_link("pages/1_현재현황.py", label="📊 현재 현황 보기", use_container_width=True)

with col2:
    with st.container(border=True):
        st.markdown("### 🔮 미래 예측")
        st.caption("이대로면 월말에 얼마 찍히나?")
        st.markdown("""
        - 4가지 시나리오 월말 예측
        - 채널별 기여도 예측
        - 매출 모멘텀 (가속/감속)
        - 광고 예산 시뮬레이터
        """)
        st.page_link("pages/2_미래예측.py", label="🔮 미래 예측 보기", use_container_width=True)

with col3:
    with st.container(border=True):
        st.markdown("### ⚡ NOW Action")
        st.caption("10억 달성을 위해 지금 뭘 해야 하나?")
        st.markdown("""
        - 우선순위 액션 리스트
        - 키워드 4분면 매트릭스
        - 예산 재배분 시뮬레이션
        - 채널 성장/주의 분석
        """)
        st.page_link("pages/3_NOW_Action.py", label="⚡ NOW Action 보기", use_container_width=True)

st.markdown("")
S.slide_header("대시보드 구성", "Dashboard Structure")
st.markdown("""
| 필러 | 핵심 질문 | 주요 기능 |
|------|-----------|-----------|
| **📊 현재 현황** | 지금 어디까지 왔나? | 목표 달성, 매출/광고/채널 분석 통합 |
| **🔮 미래 예측** | 이대로면 어떻게 되나? | 시나리오 예측, 채널 기여도, 시뮬레이터 |
| **⚡ NOW Action** | 10억 하려면 뭘 해야 하나? | 우선순위 액션, 키워드 최적화, 예산 재배분 |
""")

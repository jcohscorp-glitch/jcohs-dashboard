# -*- coding: utf-8 -*-
"""전 페이지 공유 날짜 필터 (session_state 기반)"""

import streamlit as st
from datetime import datetime, timedelta, date
import calendar


def _default_range():
    """기본값: 당월 1일 ~ 어제. 1일이면 전월 전체."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    if today.day == 1:
        # 오늘이 1일이면 당월 데이터가 없으므로 전월 전체
        last_prev = yesterday  # 전월 마지막일
        first_prev = last_prev.replace(day=1)
        return first_prev, last_prev
    first_of_month = today.replace(day=1)
    return first_of_month, yesterday


def render_date_filter():
    """사이드바에 날짜 필터를 렌더링하고 (start, end) 반환.
    session_state에 저장되어 페이지 이동 시에도 유지됨."""

    # 초기값 설정
    if "date_start" not in st.session_state:
        s, e = _default_range()
        st.session_state["date_start"] = s
        st.session_state["date_end"] = e

    with st.sidebar:
        st.header("기간 필터")

        # ── 빠른 선택 버튼 ────────────────────────────────────
        today = date.today()
        yesterday = today - timedelta(days=1)

        cols = st.columns(5)
        with cols[0]:
            if st.button("당월", use_container_width=True):
                if today.day == 1:
                    # 1일이면 전월 전체
                    last_prev = yesterday
                    st.session_state["date_start"] = last_prev.replace(day=1)
                    st.session_state["date_end"] = last_prev
                else:
                    st.session_state["date_start"] = today.replace(day=1)
                    st.session_state["date_end"] = yesterday
                st.rerun()
        with cols[1]:
            if st.button("7일", use_container_width=True):
                st.session_state["date_start"] = today - timedelta(days=7)
                st.session_state["date_end"] = yesterday
                st.rerun()
        with cols[2]:
            if st.button("한달", use_container_width=True):
                st.session_state["date_start"] = today - timedelta(days=30)
                st.session_state["date_end"] = yesterday
                st.rerun()
        with cols[3]:
            if st.button("전월", use_container_width=True):
                first_this = today.replace(day=1)
                last_prev = first_this - timedelta(days=1)
                first_prev = last_prev.replace(day=1)
                st.session_state["date_start"] = first_prev
                st.session_state["date_end"] = last_prev
                st.rerun()
        with cols[4]:
            if st.button("올해", use_container_width=True):
                st.session_state["date_start"] = date(today.year, 1, 1)
                st.session_state["date_end"] = yesterday
                st.rerun()

        # ── 직접 선택 (date_input) ────────────────────────────
        date_range = st.date_input(
            "직접 선택",
            value=[st.session_state["date_start"], st.session_state["date_end"]],
            key="date_input_widget",
        )
        if len(date_range) == 2:
            st.session_state["date_start"] = date_range[0]
            st.session_state["date_end"] = date_range[1]

        st.caption(
            f"조회: {st.session_state['date_start'].strftime('%Y-%m-%d')} ~ "
            f"{st.session_state['date_end'].strftime('%Y-%m-%d')}"
        )

        st.divider()

    return st.session_state["date_start"], st.session_state["date_end"]


def filter_df(df, date_col, start, end):
    """DataFrame을 날짜 범위로 필터링"""
    return df[(df[date_col].dt.date >= start) & (df[date_col].dt.date <= end)]

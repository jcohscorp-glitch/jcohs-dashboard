# -*- coding: utf-8 -*-
"""4) 트렌드 & 스토어 — 네이버 데이터랩 + 커머스 API"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

import naver_datalab as ndl
import naver_commerce as ncom

st.set_page_config(page_title="트렌드 & 스토어", page_icon="📊", layout="wide")
st.title("📊 트렌드 & 스토어 API")

# ─── 메인 탭 ──────────────────────────────────────────────────
tab_trend, tab_store = st.tabs(["🔍 네이버 데이터랩", "🏪 스마트스토어"])


# ═══════════════════════════════════════════════════════════════
#  TAB 1: 네이버 데이터랩
# ═══════════════════════════════════════════════════════════════
with tab_trend:
    st.subheader("🔍 네이버 데이터랩")

    trend_sub = st.tabs(["📈 검색어 트렌드", "🛒 쇼핑인사이트", "👥 타겟 분석"])

    # ── 검색어 트렌드 ──────────────────────────────────────────
    with trend_sub[0]:
        st.markdown("#### 키워드 검색량 추이 비교")

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            kw_input = st.text_input(
                "키워드 입력 (쉼표로 구분, 최대 5개)",
                value="제이코스,레이캅,한바,모그원,드림프라이스",
                help="비교할 키워드를 쉼표로 구분하여 입력하세요",
            )
        with col2:
            period = st.selectbox("기간", ["1개월", "3개월", "6개월", "1년", "2년"], index=3)
        with col3:
            time_unit = st.selectbox("단위", ["일간", "주간", "월간"], index=1)

        period_map = {"1개월": 30, "3개월": 90, "6개월": 180, "1년": 365, "2년": 730}
        unit_map = {"일간": "date", "주간": "week", "월간": "month"}

        if st.button("🔍 검색 트렌드 조회", key="btn_search_trend"):
            keywords_raw = [kw.strip() for kw in kw_input.split(",") if kw.strip()]
            if not keywords_raw:
                st.warning("키워드를 입력하세요.")
            elif len(keywords_raw) > 5:
                st.warning("최대 5개까지 입력 가능합니다.")
            else:
                keywords = [[kw] for kw in keywords_raw]
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=period_map[period])).strftime("%Y-%m-%d")

                with st.spinner("검색어 트렌드 조회 중..."):
                    df = ndl.search_trend(
                        keywords=keywords,
                        start_date=start_date,
                        end_date=end_date,
                        time_unit=unit_map[time_unit],
                    )

                if df.empty:
                    st.info("데이터가 없습니다. API 키를 확인하세요.")
                else:
                    fig = px.line(
                        df, x="날짜", y="검색비율", color="키워드",
                        title="키워드별 검색량 추이 (상대값 0~100)",
                    )
                    fig.update_layout(height=450, hovermode="x unified")
                    st.plotly_chart(fig, use_container_width=True)

                    # 최근 트렌드 요약
                    st.markdown("##### 최근 트렌드 요약")
                    recent = df.groupby("키워드")["검색비율"].agg(["mean", "last"]).round(1)
                    recent.columns = ["평균 검색비율", "최근 검색비율"]
                    recent = recent.sort_values("최근 검색비율", ascending=False)
                    st.dataframe(recent, use_container_width=True)

    # ── 쇼핑인사이트 ──────────────────────────────────────────
    with trend_sub[1]:
        st.markdown("#### 쇼핑 키워드 클릭 트렌드")
        st.caption("네이버 쇼핑에서 특정 키워드가 얼마나 클릭되는지 추이를 봅니다.")

        col1, col2 = st.columns([2, 1])
        with col1:
            shop_kw_input = st.text_input(
                "쇼핑 키워드 (쉼표 구분, 최대 5개)",
                value="청소기,공기청정기,무선청소기",
                key="shop_kw",
            )
        with col2:
            # 주요 카테고리 ID (네이버 쇼핑)
            cat_options = {
                "생활/건강": "50000006",
                "가전/디지털": "50000001",
                "화장품/미용": "50000002",
                "식품": "50000005",
                "패션의류": "50000000",
                "패션잡화": "50000004",
                "출산/육아": "50000007",
            }
            cat_name = st.selectbox("카테고리", list(cat_options.keys()), index=0)
            cat_id = cat_options[cat_name]

        shop_period = st.selectbox("기간", ["3개월", "6개월", "1년"], index=2, key="shop_period")

        if st.button("🛒 쇼핑 트렌드 조회", key="btn_shop_trend"):
            shop_keywords = [kw.strip() for kw in shop_kw_input.split(",") if kw.strip()]
            if not shop_keywords:
                st.warning("키워드를 입력하세요.")
            else:
                kw_groups = [{"name": kw, "param": [kw]} for kw in shop_keywords[:5]]
                end_date = datetime.now().strftime("%Y-%m-%d")
                days = {"3개월": 90, "6개월": 180, "1년": 365}[shop_period]
                start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

                with st.spinner("쇼핑인사이트 조회 중..."):
                    df = ndl.shopping_keyword_trend(
                        category_id=cat_id,
                        keyword_groups=kw_groups,
                        start_date=start_date,
                        end_date=end_date,
                        time_unit="week",
                    )

                if df.empty:
                    st.info("데이터가 없습니다.")
                else:
                    fig = px.line(
                        df, x="날짜", y="클릭비율", color="키워드",
                        title=f"쇼핑 키워드 클릭 트렌드 ({cat_name})",
                    )
                    fig.update_layout(height=450, hovermode="x unified")
                    st.plotly_chart(fig, use_container_width=True)

    # ── 타겟 분석 ──────────────────────────────────────────────
    with trend_sub[2]:
        st.markdown("#### 키워드 타겟 분석 (기기/성별/연령)")
        st.caption("특정 키워드의 검색 사용자 프로필을 분석합니다.")

        col1, col2 = st.columns(2)
        with col1:
            target_kw = st.text_input("분석할 키워드", value="무선청소기", key="target_kw")
        with col2:
            target_cat = st.selectbox(
                "카테고리",
                list(cat_options.keys()) if "cat_options" in dir() else ["생활/건강"],
                index=0,
                key="target_cat",
            )
            target_cat_id = cat_options.get(target_cat, "50000006")

        if st.button("👥 타겟 분석 실행", key="btn_target"):
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

            with st.spinner("타겟 분석 중..."):
                df_device = ndl.shopping_keyword_by_device(
                    target_cat_id, target_kw, start_date, end_date, "month"
                )
                df_gender = ndl.shopping_keyword_by_gender(
                    target_cat_id, target_kw, start_date, end_date, "month"
                )
                df_age = ndl.shopping_keyword_by_age(
                    target_cat_id, target_kw, start_date, end_date, "month"
                )

            col_d, col_g, col_a = st.columns(3)

            with col_d:
                st.markdown("##### 기기별")
                if not df_device.empty:
                    fig = px.line(df_device, x="날짜", y="비율", color="기기",
                                  title="PC vs 모바일")
                    fig.update_layout(height=350)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("데이터 없음")

            with col_g:
                st.markdown("##### 성별")
                if not df_gender.empty:
                    fig = px.line(df_gender, x="날짜", y="비율", color="성별",
                                  title="남성 vs 여성")
                    fig.update_layout(height=350)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("데이터 없음")

            with col_a:
                st.markdown("##### 연령별")
                if not df_age.empty:
                    fig = px.line(df_age, x="날짜", y="비율", color="연령",
                                  title="연령대별 관심도")
                    fig.update_layout(height=350)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("데이터 없음")


# ═══════════════════════════════════════════════════════════════
#  TAB 2: 스마트스토어 (커머스 API)
# ═══════════════════════════════════════════════════════════════
with tab_store:
    st.subheader("🏪 스마트스토어 (커머스 API)")

    stores = ncom.get_store_list()
    if not stores:
        st.info("커머스 API 인증정보가 없습니다. 로컬 환경에서만 사용 가능합니다 (IP 화이트리스트 필요).")
        st.stop()

    store_sub = st.tabs(["📦 주문 현황", "🏷️ 상품 현황", "📊 스토어 비교"])

    # ── 주문 현황 ──────────────────────────────────────────────
    with store_sub[0]:
        st.markdown("#### 스토어별 주문 조회")

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            store_names = [s["name"] for s in stores]
            selected_stores = st.multiselect(
                "스토어 선택", store_names, default=store_names,
            )
        with col2:
            order_start = st.date_input(
                "시작일", datetime.now() - timedelta(days=7), key="order_start",
            )
        with col3:
            order_end = st.date_input("종료일", datetime.now(), key="order_end")

        if st.button("📦 주문 조회", key="btn_orders"):
            all_orders = []
            progress = st.progress(0)

            for i, store in enumerate(stores):
                if store["name"] not in selected_stores:
                    continue
                with st.spinner(f"{store['name']} 조회 중..."):
                    df = ncom.get_orders(
                        store["key"],
                        start_date=order_start.strftime("%Y-%m-%d"),
                        end_date=order_end.strftime("%Y-%m-%d"),
                    )
                    if not df.empty:
                        df["스토어"] = store["name"]
                        all_orders.append(df)
                progress.progress((i + 1) / len(stores))

            progress.empty()

            if not all_orders:
                st.info("해당 기간의 주문이 없습니다.")
            else:
                df_all = pd.concat(all_orders, ignore_index=True)
                st.success(f"총 {len(df_all):,}건 주문 조회 완료")

                # KPI
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("총 주문건수", f"{len(df_all):,}건")
                k2.metric("총 매출", f"{df_all['상품금액'].sum():,.0f}원")
                k3.metric("평균 객단가", f"{df_all['상품금액'].mean():,.0f}원")
                k4.metric("스토어 수", f"{df_all['스토어'].nunique()}개")

                # 스토어별 매출
                store_summary = df_all.groupby("스토어").agg(
                    주문건수=("상품주문번호", "count"),
                    매출합계=("상품금액", "sum"),
                ).sort_values("매출합계", ascending=False)

                fig = px.bar(
                    store_summary.reset_index(),
                    x="스토어", y="매출합계", text="주문건수",
                    title="스토어별 매출",
                    color="스토어",
                )
                fig.update_traces(texttemplate="%{text}건", textposition="outside")
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

                # 일자별 추이
                if "주문일시" in df_all.columns:
                    daily = df_all.groupby([df_all["주문일시"].dt.date, "스토어"]).agg(
                        매출=("상품금액", "sum"),
                    ).reset_index()
                    daily.columns = ["날짜", "스토어", "매출"]

                    fig2 = px.line(
                        daily, x="날짜", y="매출", color="스토어",
                        title="일자별 매출 추이",
                    )
                    fig2.update_layout(height=400)
                    st.plotly_chart(fig2, use_container_width=True)

                # 상세 테이블
                with st.expander("주문 상세 데이터"):
                    st.dataframe(
                        df_all[["스토어", "주문일시", "상품명", "수량", "상품금액", "주문상태"]],
                        use_container_width=True,
                    )

    # ── 상품 현황 ──────────────────────────────────────────────
    with store_sub[1]:
        st.markdown("#### 스토어별 상품 현황")

        if st.button("🏷️ 전체 상품 조회", key="btn_products"):
            all_products = []
            progress = st.progress(0)

            for i, store in enumerate(stores):
                with st.spinner(f"{store['name']} 상품 조회 중..."):
                    df = ncom.get_products(store["key"])
                    if not df.empty:
                        df["스토어"] = store["name"]
                        all_products.append(df)
                progress.progress((i + 1) / len(stores))

            progress.empty()

            if not all_products:
                st.info("상품 데이터가 없습니다.")
            else:
                df_all = pd.concat(all_products, ignore_index=True)
                st.success(f"총 {len(df_all):,}개 상품 조회 완료")

                # 스토어별 상품 수
                product_counts = df_all.groupby("스토어")["상품번호"].count().reset_index()
                product_counts.columns = ["스토어", "상품수"]

                fig = px.pie(
                    product_counts, names="스토어", values="상품수",
                    title="스토어별 상품 비율",
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

                # 상품 테이블
                st.dataframe(
                    df_all[["스토어", "상품명", "판매가", "재고수량", "상태"]],
                    use_container_width=True,
                )

    # ── 스토어 비교 ────────────────────────────────────────────
    with store_sub[2]:
        st.markdown("#### 스토어 성과 비교")
        st.caption("최근 7일 주문 기준으로 스토어를 비교합니다.")

        if st.button("📊 스토어 비교 실행", key="btn_compare"):
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

            with st.spinner("전체 스토어 주문 조회 중..."):
                df_all = ncom.get_all_store_orders(start_date, end_date)

            if df_all.empty:
                st.info("최근 7일 주문이 없습니다.")
            else:
                summary = df_all.groupby("스토어").agg(
                    주문건수=("상품주문번호", "count"),
                    총매출=("상품금액", "sum"),
                    평균객단가=("상품금액", "mean"),
                    총수량=("수량", "sum"),
                ).round(0)

                summary = summary.sort_values("총매출", ascending=False)

                st.dataframe(
                    summary.style.format({
                        "주문건수": "{:,.0f}",
                        "총매출": "{:,.0f}원",
                        "평균객단가": "{:,.0f}원",
                        "총수량": "{:,.0f}",
                    }),
                    use_container_width=True,
                )

                fig = px.bar(
                    summary.reset_index(),
                    x="스토어", y="총매출",
                    color="스토어",
                    title="스토어별 매출 비교 (최근 7일)",
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

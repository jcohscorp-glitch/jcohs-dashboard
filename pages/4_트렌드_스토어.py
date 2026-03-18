# -*- coding: utf-8 -*-
"""4) 트렌드 & 스토어 — 네이버 데이터랩 + 커머스 API"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

import naver_datalab as ndl
import naver_commerce as ncom
import coupang_commerce as cpcom

st.set_page_config(page_title="트렌드 & 스토어", page_icon="📊", layout="wide")
st.title("📊 트렌드 & 스토어 API")

# ─── 메인 탭 ──────────────────────────────────────────────────
tabs = ["🔍 네이버 데이터랩", "🏪 스마트스토어"]
if cpcom.is_configured():
    tabs.append("🟠 쿠팡 스토어")
tab_trend, tab_store, *extra_tabs = st.tabs(tabs)
tab_coupang = extra_tabs[0] if extra_tabs else None


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
        st.info("커머스 API 인증정보가 없습니다.")
        st.stop()

    # 서버 IP 표시 및 연결 테스트
    server_ip = ncom.get_server_ip()
    with st.expander(f"🌐 현재 서버 IP: **{server_ip}** (커머스 API 허용 IP 등록 필요)", expanded=False):
        st.markdown(f"""
        네이버 커머스 API는 **허용된 IP에서만** 접근 가능합니다.

        1. [네이버 커머스 API 개발자센터](https://apicenter.commerce.naver.com) 접속
        2. 각 앱(한바샵, 조이코스, 드림프라이스, 레이캅코리아, 모그원) 설정으로 이동
        3. **허용 IP** 항목에 `{server_ip}` 추가
        4. 저장 후 이 페이지를 새로고침
        """)

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


# ═══════════════════════════════════════════════════════════════
#  TAB 3: 쿠팡 스토어 (Open API) — 멀티 계정
# ═══════════════════════════════════════════════════════════════
if tab_coupang is not None:
    with tab_coupang:
        st.subheader("🟠 쿠팡 스토어 (Open API)")

        cp_stores = cpcom.get_store_list()
        if not cp_stores:
            st.info("쿠팡 API 인증정보가 없습니다. secrets.toml에 설정을 추가하세요.")
            st.stop()

        cp_store_names = [s["name"] for s in cp_stores]

        cp_sub = st.tabs(["📦 주문 현황", "💰 매출 내역", "🏷️ 상품 현황", "📊 스토어 비교"])

        # ── 쿠팡 주문 현황 ────────────────────────────────────────
        with cp_sub[0]:
            st.markdown("#### 쿠팡 주문 조회")

            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                cp_selected_stores = st.multiselect(
                    "스토어 선택", cp_store_names, default=cp_store_names,
                    key="cp_store_select_order",
                )
            with col2:
                cp_order_start = st.date_input(
                    "시작일", datetime.now() - timedelta(days=7), key="cp_order_start",
                )
            with col3:
                cp_order_end = st.date_input("종료일", datetime.now(), key="cp_order_end")
            with col4:
                cp_status = st.selectbox(
                    "주문 상태",
                    ["ACCEPT", "INSTRUCT", "DEPARTURE", "DELIVERING", "FINAL_DELIVERY"],
                    index=0,
                    key="cp_status",
                )

            if st.button("📦 쿠팡 주문 조회", key="btn_cp_orders"):
                all_cp_orders = []
                progress = st.progress(0)

                selected = [s for s in cp_stores if s["name"] in cp_selected_stores]
                for i, store in enumerate(selected):
                    with st.spinner(f"{store['name']} 주문 조회 중..."):
                        df = cpcom.get_orders(
                            store["key"],
                            start_date=cp_order_start.strftime("%Y-%m-%d"),
                            end_date=cp_order_end.strftime("%Y-%m-%d"),
                            status=cp_status,
                        )
                        if not df.empty:
                            df["스토어"] = store["name"]
                            all_cp_orders.append(df)
                    progress.progress((i + 1) / len(selected))
                progress.empty()

                if not all_cp_orders:
                    st.info("해당 기간/상태의 주문이 없습니다.")
                else:
                    df_cp = pd.concat(all_cp_orders, ignore_index=True)
                    st.success(f"총 {len(df_cp):,}건 주문 조회 완료")

                    # KPI
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("총 주문건수", f"{len(df_cp):,}건")
                    k2.metric("총 매출", f"{df_cp['상품금액'].sum():,.0f}원")
                    k3.metric("평균 객단가", f"{df_cp['상품금액'].mean():,.0f}원")
                    k4.metric("스토어 수", f"{df_cp['스토어'].nunique()}개")

                    # 스토어별 매출
                    store_summary = df_cp.groupby("스토어").agg(
                        주문건수=("주문번호", "count"),
                        매출합계=("상품금액", "sum"),
                    ).sort_values("매출합계", ascending=False)

                    fig = px.bar(
                        store_summary.reset_index(),
                        x="스토어", y="매출합계", text="주문건수",
                        title="쿠팡 스토어별 매출",
                        color="스토어",
                        color_discrete_sequence=["#F47521", "#FF6B35"],
                    )
                    fig.update_traces(texttemplate="%{text}건", textposition="outside")
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)

                    # 일자별 추이
                    if "주문일시" in df_cp.columns and df_cp["주문일시"].notna().any():
                        daily = df_cp.groupby([df_cp["주문일시"].dt.date, "스토어"]).agg(
                            매출=("상품금액", "sum"),
                        ).reset_index()
                        daily.columns = ["날짜", "스토어", "매출"]

                        fig2 = px.line(
                            daily, x="날짜", y="매출", color="스토어",
                            title="일자별 쿠팡 매출 추이",
                        )
                        fig2.update_layout(height=400)
                        st.plotly_chart(fig2, use_container_width=True)

                    # 상세 테이블
                    with st.expander("주문 상세 데이터"):
                        st.dataframe(
                            df_cp[["스토어", "주문일시", "상품명", "수량", "상품금액", "주문상태"]],
                            use_container_width=True,
                        )

        # ── 쿠팡 매출 내역 ────────────────────────────────────────
        with cp_sub[1]:
            st.markdown("#### 쿠팡 매출 내역 (구매확정 기준)")

            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                cp_sales_stores = st.multiselect(
                    "스토어 선택", cp_store_names, default=cp_store_names,
                    key="cp_store_select_sales",
                )
            with col2:
                cp_sales_start = st.date_input(
                    "시작일", datetime.now() - timedelta(days=30), key="cp_sales_start",
                )
            with col3:
                cp_sales_end = st.date_input("종료일", datetime.now(), key="cp_sales_end")

            if st.button("💰 매출 조회", key="btn_cp_sales"):
                all_cp_sales = []
                selected = [s for s in cp_stores if s["name"] in cp_sales_stores]
                progress = st.progress(0)

                for i, store in enumerate(selected):
                    with st.spinner(f"{store['name']} 매출 조회 중..."):
                        df = cpcom.get_sales(
                            store["key"],
                            start_date=cp_sales_start.strftime("%Y-%m-%d"),
                            end_date=cp_sales_end.strftime("%Y-%m-%d"),
                        )
                        if not df.empty:
                            df["스토어"] = store["name"]
                            all_cp_sales.append(df)
                    progress.progress((i + 1) / len(selected))
                progress.empty()

                if not all_cp_sales:
                    st.info("해당 기간의 매출 내역이 없습니다.")
                else:
                    df_sales = pd.concat(all_cp_sales, ignore_index=True)
                    st.success(f"총 {len(df_sales):,}건 매출 조회 완료")

                    # KPI
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("총 판매금액", f"{df_sales['판매금액'].sum():,.0f}원")
                    k2.metric("총 수수료", f"{df_sales['수수료'].sum():,.0f}원")
                    k3.metric("총 정산금액", f"{df_sales['정산금액'].sum():,.0f}원")
                    k4.metric("판매건수", f"{len(df_sales):,}건")

                    # 스토어별 매출
                    if df_sales["스토어"].nunique() > 1:
                        store_sales = df_sales.groupby("스토어").agg(
                            판매금액=("판매금액", "sum"),
                            정산금액=("정산금액", "sum"),
                        ).reset_index()
                        fig = px.bar(
                            store_sales, x="스토어", y=["판매금액", "정산금액"],
                            title="스토어별 매출/정산 비교", barmode="group",
                            color_discrete_sequence=["#F47521", "#1A73E8"],
                        )
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)

                    # 일자별 매출
                    if "매출일" in df_sales.columns and df_sales["매출일"].notna().any():
                        daily_sales = df_sales.groupby([df_sales["매출일"].dt.date, "스토어"]).agg(
                            판매금액=("판매금액", "sum"),
                        ).reset_index()
                        daily_sales.columns = ["날짜", "스토어", "판매금액"]

                        fig2 = px.line(
                            daily_sales, x="날짜", y="판매금액", color="스토어",
                            title="일자별 매출 추이",
                        )
                        fig2.update_layout(height=400)
                        st.plotly_chart(fig2, use_container_width=True)

                    # 상세
                    with st.expander("매출 상세 데이터"):
                        st.dataframe(df_sales, use_container_width=True)

        # ── 쿠팡 상품 현황 ────────────────────────────────────────
        with cp_sub[2]:
            st.markdown("#### 쿠팡 상품 목록")

            cp_prod_stores = st.multiselect(
                "스토어 선택", cp_store_names, default=cp_store_names,
                key="cp_store_select_prod",
            )

            if st.button("🏷️ 상품 조회", key="btn_cp_products"):
                all_cp_products = []
                selected = [s for s in cp_stores if s["name"] in cp_prod_stores]
                progress = st.progress(0)

                for i, store in enumerate(selected):
                    with st.spinner(f"{store['name']} 상품 조회 중..."):
                        df = cpcom.get_products(store["key"])
                        if not df.empty:
                            df["스토어"] = store["name"]
                            all_cp_products.append(df)
                    progress.progress((i + 1) / len(selected))
                progress.empty()

                if not all_cp_products:
                    st.info("상품 데이터가 없습니다.")
                else:
                    df_prod = pd.concat(all_cp_products, ignore_index=True)
                    st.success(f"총 {len(df_prod):,}개 상품 조회 완료")

                    # 스토어별 상품 수
                    prod_counts = df_prod.groupby("스토어")["상품번호"].count().reset_index()
                    prod_counts.columns = ["스토어", "상품수"]
                    fig = px.pie(
                        prod_counts, names="스토어", values="상품수",
                        title="스토어별 상품 비율",
                        color_discrete_sequence=["#F47521", "#FF6B35"],
                    )
                    fig.update_layout(height=350)
                    st.plotly_chart(fig, use_container_width=True)

                    st.dataframe(df_prod, use_container_width=True)

        # ── 쿠팡 스토어 비교 ──────────────────────────────────────
        with cp_sub[3]:
            st.markdown("#### 쿠팡 스토어 성과 비교")
            st.caption("최근 7일 주문 기준으로 드보르/제이코스를 비교합니다.")

            if st.button("📊 쿠팡 스토어 비교", key="btn_cp_compare"):
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

                with st.spinner("전체 쿠팡 스토어 주문 조회 중..."):
                    df_all = cpcom.get_all_store_orders(start_date, end_date)

                if df_all.empty:
                    st.info("최근 7일 주문이 없습니다.")
                else:
                    summary = df_all.groupby("스토어").agg(
                        주문건수=("주문번호", "count"),
                        총매출=("상품금액", "sum"),
                        평균객단가=("상품금액", "mean"),
                        총수량=("수량", "sum"),
                    ).round(0).sort_values("총매출", ascending=False)

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
                        x="스토어", y="총매출", color="스토어",
                        title="쿠팡 스토어별 매출 비교 (최근 7일)",
                        color_discrete_sequence=["#F47521", "#FF6B35"],
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)

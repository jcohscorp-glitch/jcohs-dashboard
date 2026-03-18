# -*- coding: utf-8 -*-
"""네이버 커머스 API 연동 (스마트스토어 주문/상품/정산)"""

import bcrypt
import pybase64
import time
import requests
import urllib.parse
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════════
#  인증
# ═══════════════════════════════════════════════════════════════
COMMERCE_STORES = [
    "commerce_hanbashop",
    "commerce_joycoss",
    "commerce_dreamprice",
    "commerce_raycop",
    "commerce_mogone",
]

BASE_URL = "https://api.commerce.naver.com/external"


def _get_store_creds(store_key: str) -> dict | None:
    """secrets.toml에서 스토어 인증정보 읽기"""
    try:
        return dict(st.secrets[store_key])
    except Exception:
        return None


def _get_token(app_id: str, app_secret: str) -> str | None:
    """OAuth 토큰 발급 (bcrypt 서명)"""
    # 3초 전 timestamp 사용 (네이버 공식 권장)
    timestamp = str(int((time.time() - 3) * 1000))

    # bcrypt 해싱: client_secret을 salt로, password = client_id + _ + timestamp
    password = f"{app_id}_{timestamp}"
    hashed = bcrypt.hashpw(password.encode("utf-8"), app_secret.encode("utf-8"))
    client_secret_sign = pybase64.standard_b64encode(hashed).decode("utf-8")

    try:
        data_ = {
            "client_id": app_id,
            "timestamp": timestamp,
            "client_secret_sign": client_secret_sign,
            "grant_type": "client_credentials",
            "type": "SELF",
        }
        query = urllib.parse.urlencode(data_)
        resp = requests.post(
            f"{BASE_URL}/v1/oauth2/token?{query}",
            headers={"content-type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as e:
        st.error(f"커머스 API 토큰 발급 실패: {e}")
        return None


def _get_auth_header(store_key: str) -> dict | None:
    """스토어별 인증 헤더 생성"""
    creds = _get_store_creds(store_key)
    if not creds:
        return None

    token = _get_token(creds["app_id"], creds["app_secret"])
    if not token:
        return None

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_store_list() -> list[dict]:
    """등록된 스토어 목록과 이름 반환"""
    stores = []
    for key in COMMERCE_STORES:
        creds = _get_store_creds(key)
        if creds:
            stores.append({
                "key": key,
                "name": creds.get("name", key),
                "account": creds.get("account", ""),
            })
    return stores


# ═══════════════════════════════════════════════════════════════
#  주문 조회
# ═══════════════════════════════════════════════════════════════
def get_orders(store_key: str,
               start_date: str = None,
               end_date: str = None,
               order_status: str = None) -> pd.DataFrame:
    """
    스토어 주문 목록 조회

    Args:
        store_key: COMMERCE_STORES 중 하나
        start_date: 시작일 (YYYY-MM-DD), 기본 7일 전
        end_date: 종료일 (YYYY-MM-DD), 기본 오늘
        order_status: PAYED, DELIVERING, DELIVERED 등

    Returns:
        DataFrame: 주문 목록
    """
    headers = _get_auth_header(store_key)
    if not headers:
        return pd.DataFrame()

    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    all_orders = []

    # API는 1일 단위 조회만 안정적 → 날짜별로 반복
    from datetime import date as _date
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date()
    current = d_start

    try:
        while current <= d_end:
            next_day = current + timedelta(days=1)
            start_dt = f"{current.isoformat()}T00:00:00.000+09:00"
            end_dt = f"{next_day.isoformat()}T00:00:00.000+09:00"

            params = {
                "lastChangedFrom": start_dt,
                "lastChangedTo": end_dt,
            }
            if order_status:
                params["lastChangedType"] = order_status

            more_sequence = None

            # 페이징 처리
            for _ in range(50):
                if more_sequence:
                    params["moreSequence"] = more_sequence

                resp = requests.get(
                    f"{BASE_URL}/v1/pay-order/seller/product-orders/last-changed-statuses",
                    headers=headers, params=params, timeout=15,
                )
                if resp.status_code != 200:
                    break

                data = resp.json()
                product_order_ids = [
                    item.get("productOrderId")
                    for item in data.get("data", {}).get("lastChangeStatuses", [])
                    if item.get("productOrderId")
                ]

                if not product_order_ids:
                    break

                # 상세 조회
                detail_resp = requests.post(
                    f"{BASE_URL}/v1/pay-order/seller/product-orders/query",
                    headers=headers,
                    json={"productOrderIds": product_order_ids},
                    timeout=15,
                )
                if detail_resp.status_code == 200:
                    detail_data = detail_resp.json()
                    for order in detail_data.get("data", []):
                        po = order.get("productOrder", {})
                        all_orders.append({
                            "주문번호": po.get("orderId", ""),
                            "상품주문번호": po.get("productOrderId", ""),
                            "상품명": po.get("productName", ""),
                            "수량": po.get("quantity", 0),
                            "상품금액": po.get("totalPaymentAmount", 0),
                            "주문상태": po.get("productOrderStatus", ""),
                            "주문일시": po.get("orderDate", ""),
                            "결제일시": po.get("paymentDate", ""),
                            "배송비": po.get("deliveryFeeAmount", 0),
                            "구매자": po.get("ordererName", ""),
                        })

                more_sequence = data.get("data", {}).get("moreSequence")
                if not more_sequence:
                    break

            current = next_day

    except Exception as e:
        st.error(f"주문 조회 오류 ({store_key}): {e}")

    if not all_orders:
        return pd.DataFrame()

    df = pd.DataFrame(all_orders)
    df["주문일시"] = pd.to_datetime(df["주문일시"], errors="coerce")
    df["결제일시"] = pd.to_datetime(df["결제일시"], errors="coerce")
    return df


# ═══════════════════════════════════════════════════════════════
#  상품 조회
# ═══════════════════════════════════════════════════════════════
def get_products(store_key: str) -> pd.DataFrame:
    """스토어 상품 목록 조회 (POST /v1/products/search)"""
    headers = _get_auth_header(store_key)
    if not headers:
        return pd.DataFrame()
    headers["Content-Type"] = "application/json"

    all_products = []
    page = 1

    try:
        for _ in range(20):  # 최대 20페이지
            resp = requests.post(
                f"{BASE_URL}/v1/products/search",
                headers=headers,
                json={"page": page, "size": 100},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            contents = data.get("contents", [])
            if not contents:
                break

            for item in contents:
                # channelProducts 배열에서 첫 번째 상품 정보
                ch_products = item.get("channelProducts", [])
                if ch_products:
                    cp = ch_products[0]
                    all_products.append({
                        "상품번호": item.get("originProductNo", ""),
                        "상품명": cp.get("name", ""),
                        "판매가": cp.get("salePrice", 0),
                        "할인가": cp.get("discountedPrice", 0),
                        "재고수량": cp.get("stockQuantity", 0),
                        "상태": cp.get("statusType", ""),
                        "카테고리": cp.get("categoryId", ""),
                    })

            total_pages = data.get("totalPages", 1)
            if page >= total_pages:
                break
            page += 1

    except Exception as e:
        st.error(f"상품 조회 오류 ({store_key}): {e}")

    if not all_products:
        return pd.DataFrame()

    return pd.DataFrame(all_products)


# ═══════════════════════════════════════════════════════════════
#  전체 스토어 주문 통합
# ═══════════════════════════════════════════════════════════════
def get_all_store_orders(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """모든 스토어의 주문을 통합 조회"""
    all_dfs = []
    stores = get_store_list()

    for store in stores:
        df = get_orders(store["key"], start_date, end_date)
        if not df.empty:
            df["스토어"] = store["name"]
            all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()

    return pd.concat(all_dfs, ignore_index=True)


def get_all_store_products() -> pd.DataFrame:
    """모든 스토어의 상품을 통합 조회"""
    all_dfs = []
    stores = get_store_list()

    for store in stores:
        df = get_products(store["key"])
        if not df.empty:
            df["스토어"] = store["name"]
            all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()

    return pd.concat(all_dfs, ignore_index=True)

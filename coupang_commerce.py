# -*- coding: utf-8 -*-
"""쿠팡 Open API 연동 (WING 판매자 주문/매출/상품 조회)"""

import hmac
import hashlib
import requests
import pandas as pd
import streamlit as st
from time import gmtime, strftime
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════════
#  인증 (HMAC-SHA256)
# ═══════════════════════════════════════════════════════════════
BASE_URL = "https://api-gateway.coupang.com"


def _get_coupang_creds() -> dict | None:
    """쿠팡 API 인증정보 읽기 (secrets.toml → 환경변수)"""
    try:
        creds = st.secrets["coupang_wing"]
        return dict(creds)
    except Exception:
        pass
    import os
    vendor_id = os.environ.get("COUPANG_VENDOR_ID")
    access_key = os.environ.get("COUPANG_ACCESS_KEY")
    secret_key = os.environ.get("COUPANG_SECRET_KEY")
    if vendor_id and access_key and secret_key:
        return {
            "vendor_id": vendor_id,
            "access_key": access_key,
            "secret_key": secret_key,
        }
    return None


def _generate_hmac(method: str, url_path: str, secret_key: str, access_key: str) -> str:
    """HMAC-SHA256 서명 생성 → Authorization 헤더 값 반환"""
    # path와 query 분리
    parts = url_path.split("?")
    path = parts[0]
    query = parts[1] if len(parts) > 1 else ""

    datetime_gmt = strftime("%y%m%d", gmtime()) + "T" + strftime("%H%M%S", gmtime()) + "Z"
    message = datetime_gmt + method + path + query

    signature = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return (
        f"CEA algorithm=HmacSHA256, "
        f"access-key={access_key}, "
        f"signed-date={datetime_gmt}, "
        f"signature={signature}"
    )


def _coupang_request(method: str, path: str, params: dict = None, json_body: dict = None) -> dict | None:
    """쿠팡 API 호출 공통 함수"""
    creds = _get_coupang_creds()
    if not creds:
        return None

    # query string 구성
    if params:
        query_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        full_path = f"{path}?{query_string}"
    else:
        full_path = path

    authorization = _generate_hmac(method, full_path, creds["secret_key"], creds["access_key"])

    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json;charset=UTF-8",
        "X-Requested-By": "JCOHS-Dashboard",
    }

    url = BASE_URL + full_path

    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=json_body or {}, timeout=30)
        elif method == "PUT":
            resp = requests.put(url, headers=headers, json=json_body or {}, timeout=30)
        else:
            return None

        if resp.status_code == 200:
            return resp.json()
        else:
            st.warning(f"쿠팡 API 오류: {resp.status_code} - {resp.text[:200]}")
            return None
    except Exception as e:
        st.error(f"쿠팡 API 호출 실패: {e}")
        return None


def is_configured() -> bool:
    """쿠팡 API 설정 여부 확인"""
    return _get_coupang_creds() is not None


def get_vendor_id() -> str | None:
    """vendor_id 반환"""
    creds = _get_coupang_creds()
    return creds["vendor_id"] if creds else None


# ═══════════════════════════════════════════════════════════════
#  주문 조회
# ═══════════════════════════════════════════════════════════════
def get_orders(
    start_date: str = None,
    end_date: str = None,
    status: str = "ACCEPT",
) -> pd.DataFrame:
    """
    쿠팡 주문 목록 조회 (일별 페이징)

    Args:
        start_date: 시작일 (YYYY-MM-DD), 기본 7일 전
        end_date: 종료일 (YYYY-MM-DD), 기본 오늘
        status: 주문상태 (ACCEPT, INSTRUCT, DEPARTURE, DELIVERING, FINAL_DELIVERY 등)

    Returns:
        DataFrame: 주문 목록
    """
    vendor_id = get_vendor_id()
    if not vendor_id:
        return pd.DataFrame()

    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    all_orders = []
    d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    d_end = datetime.strptime(end_date, "%Y-%m-%d").date()
    current = d_start

    while current <= d_end:
        page = 1
        for _ in range(50):  # 최대 50페이지
            path = f"/v5/vendors/{vendor_id}/ordersheets"
            params = {
                "createdAtFrom": current.strftime("%Y-%m-%d"),
                "createdAtTo": current.strftime("%Y-%m-%d"),
                "status": status,
                "maxPerPage": "50",
                "page": str(page),
            }

            data = _coupang_request("GET", path, params=params)
            if not data or not data.get("data"):
                break

            orders = data["data"]
            if not orders:
                break

            for order in orders:
                all_orders.append({
                    "주문번호": order.get("orderId", ""),
                    "shipmentBoxId": order.get("shipmentBoxId", ""),
                    "주문일시": order.get("orderedAt", ""),
                    "상품명": order.get("items", [{}])[0].get("vendorItemName", "") if order.get("items") else "",
                    "수량": sum(item.get("shippingCount", 0) for item in order.get("items", [])),
                    "상품금액": sum(item.get("orderPrice", 0) for item in order.get("items", [])),
                    "주문상태": order.get("status", ""),
                    "수취인": order.get("receiver", {}).get("name", ""),
                })

            # 다음 페이지 확인
            if len(orders) < 50:
                break
            page += 1

        current += timedelta(days=1)

    if not all_orders:
        return pd.DataFrame()

    df = pd.DataFrame(all_orders)
    df["주문일시"] = pd.to_datetime(df["주문일시"], errors="coerce")
    return df


# ═══════════════════════════════════════════════════════════════
#  매출 내역 조회
# ═══════════════════════════════════════════════════════════════
def get_sales(
    start_date: str = None,
    end_date: str = None,
) -> pd.DataFrame:
    """
    매출 내역 조회 (구매확정 기준)

    Args:
        start_date: 시작일 (YYYY-MM-DD), 기본 30일 전
        end_date: 종료일 (YYYY-MM-DD), 기본 오늘

    Returns:
        DataFrame: 매출 내역
    """
    vendor_id = get_vendor_id()
    if not vendor_id:
        return pd.DataFrame()

    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    all_sales = []
    token = None

    for _ in range(100):  # 페이징
        path = f"/v5/vendors/{vendor_id}/settlementSales"
        params = {
            "recognizedFrom": start_date,
            "recognizedTo": end_date,
            "maxPerPage": "100",
        }
        if token:
            params["token"] = token

        data = _coupang_request("GET", path, params=params)
        if not data or not data.get("data"):
            break

        sales_list = data["data"]
        if not sales_list:
            break

        for sale in sales_list:
            all_sales.append({
                "매출일": sale.get("recognizedAt", ""),
                "주문번호": sale.get("orderId", ""),
                "상품명": sale.get("vendorItemName", ""),
                "수량": sale.get("quantity", 0),
                "판매금액": sale.get("salePrice", 0),
                "수수료": sale.get("commission", 0),
                "배송비": sale.get("shippingFee", 0),
                "정산금액": sale.get("settlementAmount", 0),
            })

        # 다음 페이지
        token = data.get("nextToken")
        if not token:
            break

    if not all_sales:
        return pd.DataFrame()

    df = pd.DataFrame(all_sales)
    df["매출일"] = pd.to_datetime(df["매출일"], errors="coerce")
    return df


# ═══════════════════════════════════════════════════════════════
#  상품 조회
# ═══════════════════════════════════════════════════════════════
def get_products() -> pd.DataFrame:
    """
    판매자 상품 목록 조회

    Returns:
        DataFrame: 상품 목록
    """
    vendor_id = get_vendor_id()
    if not vendor_id:
        return pd.DataFrame()

    all_products = []
    next_token = None

    for _ in range(20):  # 최대 20페이지
        path = f"/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
        params = {
            "vendorId": vendor_id,
            "maxPerPage": "100",
        }
        if next_token:
            params["nextToken"] = next_token

        data = _coupang_request("GET", path, params=params)
        if not data or not data.get("data"):
            break

        products = data["data"]
        if not products:
            break

        for prod in products:
            all_products.append({
                "상품번호": prod.get("sellerProductId", ""),
                "상품명": prod.get("sellerProductName", ""),
                "판매가": prod.get("salePrice", 0),
                "상태": prod.get("statusName", ""),
                "카테고리": prod.get("displayCategoryName", ""),
                "브랜드": prod.get("brand", ""),
                "생성일": prod.get("createdAt", ""),
            })

        next_token = data.get("nextToken")
        if not next_token:
            break

    if not all_products:
        return pd.DataFrame()

    return pd.DataFrame(all_products)


# ═══════════════════════════════════════════════════════════════
#  배송 상태 이력 조회
# ═══════════════════════════════════════════════════════════════
def get_delivery_history(shipment_box_id: str) -> pd.DataFrame:
    """개별 주문의 배송 상태 변경 이력 조회"""
    vendor_id = get_vendor_id()
    if not vendor_id:
        return pd.DataFrame()

    path = f"/v5/vendors/{vendor_id}/ordersheets/{shipment_box_id}/history"
    data = _coupang_request("GET", path)

    if not data or not data.get("data"):
        return pd.DataFrame()

    history = []
    for item in data["data"]:
        history.append({
            "상태": item.get("status", ""),
            "변경일시": item.get("changedAt", ""),
            "설명": item.get("description", ""),
        })

    return pd.DataFrame(history)

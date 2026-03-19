# -*- coding: utf-8 -*-
"""쿠팡 Open API 연동 (WING 판매자 주문/매출/상품 조회) — 멀티 계정 지원"""

import hmac
import hashlib
import requests
import pandas as pd
import streamlit as st
import json
import base64
from time import gmtime, strftime
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════════
#  인증 (HMAC-SHA256) — 멀티 스토어
# ═══════════════════════════════════════════════════════════════
BASE_URL = "https://api-gateway.coupang.com"

# 프록시 설정 (닷넷피아 고정 IP 서버 경유)
PROXY_URL = "http://119.205.211.3/coupang_proxy.asp"
PROXY_SECRET = "jcohs-coupang-proxy-2026-secret"
USE_PROXY = True  # True: 프록시 경유 (Cloud), False: 직접 호출 (로컬)

# secrets.toml의 섹션 이름 목록
COUPANG_STORE_KEYS = [
    "coupang_dvor",
    "coupang_jcohs",
]


@st.cache_data(ttl=3600)
def _load_extra_creds() -> dict:
    """EXTRA_CREDS (base64 JSON) 디코딩. 없으면 빈 dict."""
    try:
        b64 = st.secrets["EXTRA_CREDS"].replace("\n", "").replace(" ", "")
        return json.loads(base64.b64decode(b64))
    except Exception:
        return {}


def _get_store_creds(store_key: str) -> dict | None:
    """스토어별 인증정보 읽기 (TOML 섹션 → EXTRA_CREDS 순)"""
    try:
        return dict(st.secrets[store_key])
    except Exception:
        pass
    extra = _load_extra_creds()
    return extra.get(store_key)


def get_store_list() -> list[dict]:
    """등록된 쿠팡 스토어 목록 반환"""
    stores = []
    for key in COUPANG_STORE_KEYS:
        creds = _get_store_creds(key)
        if creds:
            stores.append({
                "key": key,
                "name": creds.get("name", key),
                "vendor_id": creds.get("vendor_id", ""),
            })
    return stores


def is_configured() -> bool:
    """쿠팡 API 설정 여부 확인 (최소 1개 계정)"""
    return len(get_store_list()) > 0


def _generate_hmac(method: str, url_path: str, secret_key: str, access_key: str) -> str:
    """HMAC-SHA256 서명 생성 → Authorization 헤더 값 반환"""
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


def _coupang_request(store_key: str, method: str, path: str,
                     params: dict = None, json_body: dict = None) -> dict | None:
    """쿠팡 API 호출 공통 함수 (스토어별) — 프록시 지원"""
    creds = _get_store_creds(store_key)
    if not creds:
        return None

    # query string 구성
    if params:
        query_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        full_path = f"{path}?{query_string}"
    else:
        full_path = path

    authorization = _generate_hmac(method, full_path, creds["secret_key"], creds["access_key"])

    try:
        if USE_PROXY:
            # ── 프록시 경유 (Cloud 환경) ──
            proxy_headers = {
                "X-Proxy-Auth": PROXY_SECRET,
                "X-Coupang-Auth": authorization,
                "X-Cp-Method": method,
                "X-Cp-Path": full_path,
                "Content-Type": "application/json;charset=UTF-8",
                "Host": "www.jcohsadmin.com",
                "User-Agent": "JCOHS-Dashboard/1.0",
            }
            if method in ("POST", "PUT"):
                resp = requests.post(PROXY_URL, headers=proxy_headers,
                                     json=json_body or {}, timeout=60,
                                     allow_redirects=False)
            else:
                resp = requests.post(PROXY_URL, headers=proxy_headers,
                                     timeout=60, allow_redirects=False)
        else:
            # ── 직접 호출 (로컬 환경) ──
            headers = {
                "Authorization": authorization,
                "Content-Type": "application/json;charset=UTF-8",
                "X-Requested-By": "JCOHS-Dashboard",
            }
            url = BASE_URL + full_path
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                resp = requests.post(url, headers=headers, json=json_body or {}, timeout=30)
            elif method == "PUT":
                resp = requests.put(url, headers=headers, json=json_body or {}, timeout=30)
            else:
                return None

        if resp.status_code == 200:
            data = resp.json()
            # 프록시 경유 시 실제 상태 확인
            if USE_PROXY and "proxy_status" in data:
                ps = data["proxy_status"]
                if ps != 200:
                    st.warning(f"쿠팡 API 오류 ({store_key}): {ps} - {data.get('proxy_body', data.get('proxy_error', ''))[:200]}")
                    return None
            return data
        else:
            st.warning(f"쿠팡 API 오류 ({store_key}): {resp.status_code} - {resp.text[:200]}")
            return None
    except Exception as e:
        st.error(f"쿠팡 API 호출 실패 ({store_key}): {e}")
        return None


# ═══════════════════════════════════════════════════════════════
#  주문 조회
# ═══════════════════════════════════════════════════════════════
def get_orders(
    store_key: str,
    start_date: str = None,
    end_date: str = None,
    status: str = "ACCEPT",
) -> pd.DataFrame:
    """
    쿠팡 주문 목록 조회 (일별 페이징)

    Args:
        store_key: COUPANG_STORE_KEYS 중 하나
        start_date: 시작일 (YYYY-MM-DD), 기본 7일 전
        end_date: 종료일 (YYYY-MM-DD), 기본 오늘
        status: 주문상태 (ACCEPT, INSTRUCT, DEPARTURE, DELIVERING, FINAL_DELIVERY 등)
    """
    creds = _get_store_creds(store_key)
    if not creds:
        return pd.DataFrame()

    vendor_id = creds["vendor_id"]

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
        for _ in range(50):
            path = f"/v2/providers/openapi/apis/api/v4/vendors/{vendor_id}/ordersheets"
            params = {
                "createdAtFrom": current.strftime("%Y-%m-%d"),
                "createdAtTo": current.strftime("%Y-%m-%d"),
                "status": status,
                "maxPerPage": "50",
                "page": str(page),
            }

            data = _coupang_request(store_key, "GET", path, params=params)
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
    store_key: str,
    start_date: str = None,
    end_date: str = None,
) -> pd.DataFrame:
    """매출 내역 조회 (구매확정 기준)"""
    creds = _get_store_creds(store_key)
    if not creds:
        return pd.DataFrame()

    vendor_id = creds["vendor_id"]

    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    all_sales = []
    token = None

    for _ in range(100):
        path = "/v2/providers/openapi/apis/api/v1/revenue-history"
        params = {
            "vendorId": vendor_id,
            "recognitionDateFrom": start_date,
            "recognitionDateTo": end_date,
            "maxPerPage": "100",
            "token": token or "",
        }

        data = _coupang_request(store_key, "GET", path, params=params)
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
                "판매금액": sale.get("orderPrice", 0),
                "수수료": sale.get("commission", 0),
                "배송비": sale.get("shippingFee", 0),
                "정산금액": sale.get("settlePrice", 0),
            })

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
def get_products(store_key: str) -> pd.DataFrame:
    """판매자 상품 목록 조회"""
    creds = _get_store_creds(store_key)
    if not creds:
        return pd.DataFrame()

    vendor_id = creds["vendor_id"]
    all_products = []
    next_token = None

    for _ in range(20):
        path = f"/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
        params = {
            "vendorId": vendor_id,
            "maxPerPage": "100",
        }
        if next_token:
            params["nextToken"] = next_token

        data = _coupang_request(store_key, "GET", path, params=params)
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
#  전체 스토어 통합 조회
# ═══════════════════════════════════════════════════════════════
def get_all_store_orders(start_date: str = None, end_date: str = None,
                         status: str = "ACCEPT") -> pd.DataFrame:
    """모든 쿠팡 스토어의 주문을 통합 조회"""
    all_dfs = []
    for store in get_store_list():
        df = get_orders(store["key"], start_date, end_date, status)
        if not df.empty:
            df["스토어"] = store["name"]
            all_dfs.append(df)
    if not all_dfs:
        return pd.DataFrame()
    return pd.concat(all_dfs, ignore_index=True)


def get_all_store_sales(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """모든 쿠팡 스토어의 매출을 통합 조회"""
    all_dfs = []
    for store in get_store_list():
        df = get_sales(store["key"], start_date, end_date)
        if not df.empty:
            df["스토어"] = store["name"]
            all_dfs.append(df)
    if not all_dfs:
        return pd.DataFrame()
    return pd.concat(all_dfs, ignore_index=True)


def get_all_store_products() -> pd.DataFrame:
    """모든 쿠팡 스토어의 상품을 통합 조회"""
    all_dfs = []
    for store in get_store_list():
        df = get_products(store["key"])
        if not df.empty:
            df["스토어"] = store["name"]
            all_dfs.append(df)
    if not all_dfs:
        return pd.DataFrame()
    return pd.concat(all_dfs, ignore_index=True)

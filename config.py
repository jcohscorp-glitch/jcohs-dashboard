# -*- coding: utf-8 -*-
"""월 매출 10억 대시보드 - 설정
Streamlit Cloud: secrets.toml에서 읽기
로컬: .streamlit/secrets.toml 또는 환경변수
"""

import os
import json
import tempfile

def _secret(key, default=None):
    """Streamlit secrets → 환경변수 → 기본값 순으로 읽기"""
    try:
        import streamlit as st
        val = st.secrets.get(key, None)
        if val is not None:
            return val
    except Exception:
        pass
    return os.environ.get(key, default)


# ── 목표 ─────────────────────────────────────────────────────
MONTHLY_TARGET = 1_000_000_000  # 월 매출 목표: 10억

# ── 서비스 계정 ──────────────────────────────────────────────
_LOCAL_SA_PATH = os.path.join(
    r"c:\Users\owner\Desktop\ai_workspace\naver_automation",
    "credentials", "service_account.json",
)

def get_service_account_path():
    """서비스 계정 JSON 경로 반환 (Cloud에서는 임시파일 생성)"""
    try:
        import streamlit as st
        sa_info = st.secrets.get("gcp_service_account", None)
        if sa_info is not None:
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            json.dump(dict(sa_info), tmp)
            tmp.close()
            return tmp.name
    except Exception:
        pass
    return _LOCAL_SA_PATH

SERVICE_ACCOUNT_JSON = get_service_account_path()

# ── 구글시트 ID (secrets.toml에서 관리) ───────────────────────
SHEET_MAIN = _secret("SHEET_MAIN")
SHEET_NAVER = _secret("SHEET_NAVER")
SHEET_2025 = _secret("SHEET_2025")

# ── 탭 이름 ──────────────────────────────────────────────────
TAB_SALES_26 = "JCOHS 26년 상반기매출"
TAB_NAVER_SA = "1)naver_dream_daily_cam"
TAB_COUPANG_AD = "2)쿠팡광고_캠페인"
TAB_GFA = "3)네이버GFA-성과/광고소재별/일간"
TAB_META = "4Meta-Looker용"
TAB_NAVER_PRODUCT = "J)판매분석>상품/마케팅채널"
TAB_NAVER_CHANNEL = "마케팅분석>검색채널"
TAB_NAVER_KEYWORD = "상품/검색채널"
TAB_SALES_25 = "주문리스트 25년"

# ── 쿠팡 키워드 광고 ──────────────────────────────────────
SHEET_COUPANG_KW = _secret("SHEET_COUPANG_KW")
TAB_COUPANG_KW = "쿠팡 광고 키워드 점검"

# ── 네이버 검색광고 API (secrets.toml에서 관리) ──────────────
NAVER_AD_ACCOUNTS = [
    {
        "name": "JCOHS",
        "api_key": _secret("NAVER_JCOHS_API_KEY"),
        "secret_key": _secret("NAVER_JCOHS_SECRET_KEY"),
        "customer_id": _secret("NAVER_JCOHS_CUSTOMER_ID"),
    },
    {
        "name": "HAAN",
        "api_key": _secret("NAVER_HAAN_API_KEY"),
        "secret_key": _secret("NAVER_HAAN_SECRET_KEY"),
        "customer_id": _secret("NAVER_HAAN_CUSTOMER_ID"),
    },
]

# ── Gemini AI (secrets.toml에서 관리) ────────────────────────
GEMINI_API_KEY = _secret("GEMINI_API_KEY")

# ── 캐시 TTL (초) ────────────────────────────────────────────
CACHE_TTL = 300  # 5분

# -*- coding: utf-8 -*-
"""월 매출 10억 대시보드 - 설정
Streamlit Cloud 배포 시 secrets.toml에서 읽고,
로컬에서는 .env 또는 기본값 사용
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
# Streamlit Cloud: secrets.toml의 [gcp_service_account] 섹션에서 JSON 생성
# 로컬: 파일 경로 직접 사용
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
            # secrets.toml에서 읽은 dict → 임시 JSON 파일로 저장
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            json.dump(dict(sa_info), tmp)
            tmp.close()
            return tmp.name
    except Exception:
        pass
    return _LOCAL_SA_PATH

SERVICE_ACCOUNT_JSON = get_service_account_path()

# ── 구글시트 ID ──────────────────────────────────────────────
SHEET_MAIN = _secret("SHEET_MAIN", "1NbOXHidkJqR7QF6QEsMYM_WWkjLCRFQi8Vi8vtrfCdM")
SHEET_NAVER = _secret("SHEET_NAVER", "15w6v4w0YWmgl_beSVnXxHFV8g-VEdpFlYb7Vq5OF0dc")
SHEET_2025 = _secret("SHEET_2025", "1fxbg-0GLfPNzAZYmjETzOowwEf6hOgBBCPMN0whGHfE")

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
SHEET_COUPANG_KW = _secret("SHEET_COUPANG_KW", "1gLSPxHBskaLuiwHCdZGCCWQlvuFYaCMts7lpi8GEsIY")
TAB_COUPANG_KW = "쿠팡 광고 키워드 점검"

# ── 네이버 검색광고 API ────────────────────────────────────
NAVER_AD_ACCOUNTS = [
    {
        "name": "JCOHS",
        "api_key": _secret("NAVER_JCOHS_API_KEY", "01000000006ef73d6ee06bf2296a926f2fdd70e821caaf4021b1314d4e41613577312c1b0b"),
        "secret_key": _secret("NAVER_JCOHS_SECRET_KEY", "AQAAAABu9z1u4GvyKWqSby/dcOghrkZYCbrmY0SYFZERc+jrmA=="),
        "customer_id": _secret("NAVER_JCOHS_CUSTOMER_ID", "1212614"),
    },
    {
        "name": "HAAN",
        "api_key": _secret("NAVER_HAAN_API_KEY", "0100000000a9d27ee4b4e9bb05252c8950d46a38f7b2098d06b314ef93ef6195785ef34bd2"),
        "secret_key": _secret("NAVER_HAAN_SECRET_KEY", "AQAAAACp0n7ktOm7BSUsiVDUajj3DmBfaz8WG2bj7xHcvo2jNQ=="),
        "customer_id": _secret("NAVER_HAAN_CUSTOMER_ID", "1973848"),
    },
]

# ── Gemini AI ──────────────────────────────────────────────
GEMINI_API_KEY = _secret("GEMINI_API_KEY", "AIzaSyBRYtRQAK_7IhVSBgf7WZ1HPNZfMhkIr-w")

# ── 캐시 TTL (초) ────────────────────────────────────────────
CACHE_TTL = 300  # 5분

# -*- coding: utf-8 -*-
"""구글시트에서 데이터를 로드하고 pandas DataFrame으로 변환"""

import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import config


def _get_client():
    """gspread 클라이언트 생성 (Cloud: secrets dict / 로컬: JSON 파일)"""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    try:
        sa_info = st.secrets.get("gcp_service_account", None)
        if sa_info is not None:
            creds = Credentials.from_service_account_info(dict(sa_info), scopes=scopes)
            return gspread.authorize(creds)
    except Exception as e:
        st.error(f"서비스 계정 인증 실패: {e}")
    creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_JSON, scopes=scopes)
    return gspread.authorize(creds)


def _load_sheet(sheet_id: str, tab_name: str) -> pd.DataFrame:
    """시트 탭을 DataFrame으로 로드"""
    if not sheet_id:
        st.error(f"시트 ID가 없습니다. tab_name={tab_name}")
        return pd.DataFrame()
    try:
        client = _get_client()
        ws = client.open_by_key(sheet_id).worksheet(tab_name)
        rows = ws.get_all_values()
        if len(rows) < 2:
            return pd.DataFrame()
        return pd.DataFrame(rows[1:], columns=rows[0])
    except Exception as e:
        st.error(f"시트 로드 실패: sheet_id={sheet_id[:8]}..., tab={tab_name}, 에러={e}")
        return pd.DataFrame()


def _parse_number(s):
    """쉼표가 포함된 숫자 문자열 → float 변환"""
    if isinstance(s, (int, float)):
        return float(s)
    if not isinstance(s, str):
        return 0.0
    s = s.strip().replace(",", "").replace(" ", "")
    if s in ("", "-"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_pct(s):
    """퍼센트 문자열 → float (0~100)"""
    if not isinstance(s, str):
        return 0.0
    s = s.strip().replace("%", "").replace(",", "")
    if s in ("", "-"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


# ═══════════════════════════════════════════════════════════════
#  26년 매출
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=config.CACHE_TTL)
def load_sales_26() -> pd.DataFrame:
    """26년 상반기 매출 데이터"""
    df = _load_sheet(config.SHEET_MAIN, config.TAB_SALES_26)
    if df.empty:
        return df
    df["주문일시"] = pd.to_datetime(df["주문일시"], errors="coerce")
    for col in ["수량", "총 판매금액", "매입금액", "배송료", "마진"]:
        if col in df.columns:
            df[col] = df[col].apply(_parse_number)
    return df.dropna(subset=["주문일시"])


# ═══════════════════════════════════════════════════════════════
#  25년 매출
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=config.CACHE_TTL)
def load_sales_25() -> pd.DataFrame:
    """25년 매출 데이터"""
    df = _load_sheet(config.SHEET_2025, config.TAB_SALES_25)
    if df.empty:
        return df
    df["주문일시"] = pd.to_datetime(df["주문일시"], errors="coerce")
    for col in ["수량", "총 판매금액", "매입금액", "배송료", "마진"]:
        if col in df.columns:
            df[col] = df[col].apply(_parse_number)
    return df.dropna(subset=["주문일시"])


# ═══════════════════════════════════════════════════════════════
#  네이버 SA 광고
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=config.CACHE_TTL)
def load_naver_sa() -> pd.DataFrame:
    """네이버 검색광고 캠페인 데이터"""
    df = _load_sheet(config.SHEET_MAIN, config.TAB_NAVER_SA)
    if df.empty:
        return df
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    num_cols = ["노출수", "클릭수", "총비용(VAT포함,원)", "전환수", "직접전환수",
                "전환매출액(원)", "직접전환매출액(원)", "전환당비용(원)"]
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(_parse_number)
    pct_cols = ["클릭률(%)", "전환율(%)", "광고수익률(%)"]
    for col in pct_cols:
        if col in df.columns:
            df[col] = df[col].apply(_parse_pct)
    if "평균클릭비용(VAT포함,원)" in df.columns:
        df["평균클릭비용(VAT포함,원)"] = df["평균클릭비용(VAT포함,원)"].apply(_parse_number)
    return df.dropna(subset=["날짜"])


# ═══════════════════════════════════════════════════════════════
#  쿠팡 광고
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=config.CACHE_TTL)
def load_coupang_ad() -> pd.DataFrame:
    """쿠팡 광고 캠페인 데이터"""
    df = _load_sheet(config.SHEET_MAIN, config.TAB_COUPANG_AD)
    if df.empty:
        return df
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    num_cols = ["노출수", "클릭수", "광고비",
                "총 주문수(1일)", "직접 주문수(1일)", "간접 주문수(1일)",
                "총 판매수량(1일)", "총 전환매출액(1일)", "직접 전환매출액(1일)", "간접 전환매출액(1일)"]
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(_parse_number)
    if "클릭률" in df.columns:
        df["클릭률"] = df["클릭률"].apply(_parse_pct)
    return df.dropna(subset=["날짜"])


# ═══════════════════════════════════════════════════════════════
#  네이버 GFA
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=config.CACHE_TTL)
def load_gfa() -> pd.DataFrame:
    """네이버 GFA 디스플레이 광고"""
    df = _load_sheet(config.SHEET_MAIN, config.TAB_GFA)
    if df.empty:
        return df
    df["기간"] = pd.to_datetime(df["기간"], errors="coerce")
    num_cols = ["결과", "결과당 비용", "총 비용", "노출", "클릭", "CPC", "CPM"]
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(_parse_number)
    if "CTR" in df.columns:
        df["CTR"] = df["CTR"].apply(_parse_number)
    return df.dropna(subset=["기간"])


# ═══════════════════════════════════════════════════════════════
#  Meta 광고
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=config.CACHE_TTL)
def load_meta() -> pd.DataFrame:
    """Meta (Facebook/Instagram) 광고"""
    df = _load_sheet(config.SHEET_MAIN, config.TAB_META)
    if df.empty:
        return df
    df["Day"] = pd.to_datetime(df["Day"], errors="coerce")
    num_cols = ["Amount spent", "Reach", "Clicks (all)", "CPC (all)", "Link clicks"]
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(_parse_number)
    if "CTR (link click-through rate)" in df.columns:
        df["CTR (link click-through rate)"] = df["CTR (link click-through rate)"].apply(_parse_pct)
    return df.dropna(subset=["Day"])


# ═══════════════════════════════════════════════════════════════
#  쿠팡 키워드 광고 (상세 분석용)
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=config.CACHE_TTL)
def load_coupang_keyword() -> pd.DataFrame:
    """쿠팡 키워드 광고 raw 데이터 로드"""
    df = _load_sheet(config.SHEET_COUPANG_KW, config.TAB_COUPANG_KW)
    if df.empty:
        return df
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    num_cols = [
        "노출수", "클릭수", "광고비",
        "총 주문수(14일)", "총 판매수량(14일)", "총 전환매출액(14일)",
        "직접주문수(14일)", "간접 주문수(14일)",
        "직접 판매수량(14일)", "간접 판매수량(14일)",
        "직접 전환매출액(14일)", "간접 전환매출액(14일)",
        "총 주문수(1일)", "총 판매수량(1일)", "총 전환매출액(1일)",
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(_parse_number)
    return df.dropna(subset=["날짜"])


def _add_kw_derived(df: pd.DataFrame) -> pd.DataFrame:
    """쿠팡 키워드 집계에 파생 지표 추가"""
    df["광고비(VAT)"] = df["광고비"] * 1.1
    df["CTR(%)"] = (df["클릭수"] / df["노출수"].replace(0, 1) * 100).round(2)
    df["전환율(%)"] = (df["총 판매수량(14일)"] / df["클릭수"].replace(0, 1) * 100).round(2)
    df["CPC"] = (df["광고비(VAT)"] / df["클릭수"].replace(0, 1)).round(0)
    df["ROAS(%)"] = (df["총 전환매출액(14일)"] / df["광고비(VAT)"].replace(0, 1) * 100).round(0)
    return df


def aggregate_kw_by_keyword(df: pd.DataFrame) -> pd.DataFrame:
    """키워드별 합산"""
    agg = df.groupby("키워드", as_index=False).agg(
        노출수=("노출수", "sum"),
        클릭수=("클릭수", "sum"),
        광고비=("광고비", "sum"),
        **{"총 판매수량(14일)": ("총 판매수량(14일)", "sum")},
        **{"총 전환매출액(14일)": ("총 전환매출액(14일)", "sum")},
    )
    return _add_kw_derived(agg)


def aggregate_kw_by_area(df: pd.DataFrame) -> pd.DataFrame:
    """광고 노출 지면(검색/비검색)별 합산"""
    agg = df.groupby("광고 노출 지면", as_index=False).agg(
        노출수=("노출수", "sum"),
        클릭수=("클릭수", "sum"),
        광고비=("광고비", "sum"),
        **{"총 판매수량(14일)": ("총 판매수량(14일)", "sum")},
        **{"총 전환매출액(14일)": ("총 전환매출액(14일)", "sum")},
    )
    return _add_kw_derived(agg)


def aggregate_kw_by_campaign_area(df: pd.DataFrame) -> pd.DataFrame:
    """캠페인 × 노출 지면별 합산"""
    agg = df.groupby(["캠페인명", "광고 노출 지면"], as_index=False).agg(
        노출수=("노출수", "sum"),
        클릭수=("클릭수", "sum"),
        광고비=("광고비", "sum"),
        **{"총 판매수량(14일)": ("총 판매수량(14일)", "sum")},
        **{"총 전환매출액(14일)": ("총 전환매출액(14일)", "sum")},
    )
    return _add_kw_derived(agg)


def safe_div(a, b, default=0):
    return a / b if b != 0 else default


def fmt_money(v):
    if abs(v) >= 1e8:
        return f"{v/1e8:.1f}억"
    elif abs(v) >= 1e6:
        return f"{v/1e6:.0f}백만"
    elif abs(v) >= 1e4:
        return f"{v/1e4:.0f}만"
    return f"{v:,.0f}원"


def filter_kw_df(df, date_col, start, end):
    """DataFrame을 날짜 범위로 필터링"""
    return df[(df[date_col].dt.date >= start) & (df[date_col].dt.date <= end)]


# ═══════════════════════════════════════════════════════════════
#  네이버 스토어 - 판매분석
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=config.CACHE_TTL)
def load_naver_product() -> pd.DataFrame:
    """네이버 판매분석 - 상품/마케팅채널"""
    df = _load_sheet(config.SHEET_NAVER, config.TAB_NAVER_PRODUCT)
    if df.empty:
        return df
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    for col in ["결제수", "결제금액"]:
        if col in df.columns:
            df[col] = df[col].apply(_parse_number)
    return df.dropna(subset=["날짜"])


# ═══════════════════════════════════════════════════════════════
#  네이버 스토어 - 마케팅/검색채널
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=config.CACHE_TTL)
def load_naver_channel() -> pd.DataFrame:
    """네이버 마케팅분석 - 검색채널"""
    df = _load_sheet(config.SHEET_NAVER, config.TAB_NAVER_CHANNEL)
    if df.empty:
        return df
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    num_cols = ["고객수", "유입수", "광고비", "페이지수",
                "결제수(마지막클릭)", "결제금액(마지막클릭)",
                "결제수(+14일기여도추정)", "결제금액(+14일기여도추정)"]
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(_parse_number)
    pct_cols = ["유입당 결제율(마지막클릭)", "유입당 결제금액(마지막클릭)",
                "ROAS(마지막클릭)", "유입당 결제율(+14일기여도추정)", "유입당 결제금액(+14일기여도추정)"]
    for col in pct_cols:
        if col in df.columns:
            df[col] = df[col].apply(_parse_number)
    return df.dropna(subset=["날짜"])


# ═══════════════════════════════════════════════════════════════
#  네이버 스토어 - 키워드
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=config.CACHE_TTL)
def load_naver_keyword() -> pd.DataFrame:
    """네이버 상품/검색채널 (키워드별)"""
    df = _load_sheet(config.SHEET_NAVER, config.TAB_NAVER_KEYWORD)
    if df.empty:
        return df
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    for col in ["결제수(과거 14일간 기여도추정)", "결제금액(과거 14일간 기여도추정)"]:
        if col in df.columns:
            df[col] = df[col].apply(_parse_number)
    return df.dropna(subset=["날짜"])

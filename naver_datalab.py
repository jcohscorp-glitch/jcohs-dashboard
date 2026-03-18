# -*- coding: utf-8 -*-
"""네이버 데이터랩 API 연동 (검색어트렌드 + 쇼핑인사이트)"""

import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta


def _get_datalab_creds():
    """데이터랩 API 인증정보 읽기 (TOML 섹션 → EXTRA_CREDS 순)"""
    try:
        creds = st.secrets["datalab_dashboard"]
        return creds["client_id"], creds["client_secret"]
    except Exception:
        pass
    try:
        import json, base64
        extra = json.loads(base64.b64decode(st.secrets["EXTRA_CREDS"]))
        creds = extra.get("datalab_dashboard", {})
        return creds.get("client_id"), creds.get("client_secret")
    except Exception:
        return None, None


# ═══════════════════════════════════════════════════════════════
#  검색어트렌드 API
# ═══════════════════════════════════════════════════════════════
def search_trend(keywords: list[list[str]],
                 group_names: list[str] = None,
                 start_date: str = None,
                 end_date: str = None,
                 time_unit: str = "date") -> pd.DataFrame:
    """
    네이버 검색어트렌드 API 호출

    Args:
        keywords: 키워드 그룹 리스트 (예: [["제이코스", "JCOHS"], ["레이캅"]])
        group_names: 각 그룹의 이름 (None이면 첫 번째 키워드 사용)
        start_date: 시작일 (YYYY-MM-DD), 기본 1년 전
        end_date: 종료일 (YYYY-MM-DD), 기본 오늘
        time_unit: "date"(일간), "week"(주간), "month"(월간)

    Returns:
        DataFrame: period, group_name, ratio 컬럼
    """
    client_id, client_secret = _get_datalab_creds()
    if not client_id:
        return pd.DataFrame()

    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    if not group_names:
        group_names = [kw_list[0] for kw_list in keywords]

    keyword_groups = []
    for i, kw_list in enumerate(keywords):
        keyword_groups.append({
            "groupName": group_names[i] if i < len(group_names) else kw_list[0],
            "keywords": kw_list,
        })

    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": time_unit,
        "keywordGroups": keyword_groups,
    }

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            "https://openapi.naver.com/v1/datalab/search",
            json=body, headers=headers, timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.error(f"검색어트렌드 API 오류: {e}")
        return pd.DataFrame()

    rows = []
    for result in data.get("results", []):
        name = result["title"]
        for item in result.get("data", []):
            rows.append({
                "날짜": item["period"],
                "키워드": name,
                "검색비율": item["ratio"],
            })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["날짜"] = pd.to_datetime(df["날짜"])
    return df


# ═══════════════════════════════════════════════════════════════
#  쇼핑인사이트 - 카테고리별 트렌드
# ═══════════════════════════════════════════════════════════════
def shopping_category_trend(category_name: str,
                            category_param: list[dict],
                            start_date: str = None,
                            end_date: str = None,
                            time_unit: str = "date",
                            device: str = "",
                            gender: str = "",
                            ages: list[str] = None) -> pd.DataFrame:
    """
    네이버 쇼핑인사이트 카테고리 트렌드 API

    Args:
        category_name: 표시용 카테고리 이름
        category_param: [{"name": "카테고리명", "param": ["cid"]}] 형태
        start_date, end_date: 기간
        time_unit: "date", "week", "month"
        device: "" (전체), "pc", "mo" (모바일)
        gender: "" (전체), "m", "f"
        ages: ["10", "20", "30", "40", "50", "60"] 중 선택

    Returns:
        DataFrame: 날짜, 카테고리, 클릭비율
    """
    client_id, client_secret = _get_datalab_creds()
    if not client_id:
        return pd.DataFrame()

    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": time_unit,
        "category": category_param,
    }
    if device:
        body["device"] = device
    if gender:
        body["gender"] = gender
    if ages:
        body["ages"] = ages

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            "https://openapi.naver.com/v1/datalab/shopping/categories",
            json=body, headers=headers, timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.error(f"쇼핑인사이트 카테고리 API 오류: {e}")
        return pd.DataFrame()

    rows = []
    for result in data.get("results", []):
        name = result["title"]
        for item in result.get("data", []):
            rows.append({
                "날짜": item["period"],
                "카테고리": name,
                "클릭비율": item["ratio"],
            })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["날짜"] = pd.to_datetime(df["날짜"])
    return df


# ═══════════════════════════════════════════════════════════════
#  쇼핑인사이트 - 키워드별 트렌드
# ═══════════════════════════════════════════════════════════════
def shopping_keyword_trend(category_id: str,
                           keyword_groups: list[dict],
                           start_date: str = None,
                           end_date: str = None,
                           time_unit: str = "date",
                           device: str = "",
                           gender: str = "",
                           ages: list[str] = None) -> pd.DataFrame:
    """
    네이버 쇼핑인사이트 키워드 트렌드 API

    Args:
        category_id: 카테고리 ID (필수)
        keyword_groups: [{"name": "키워드명", "param": ["키워드1", "키워드2"]}]
        start_date, end_date: 기간
        time_unit: "date", "week", "month"

    Returns:
        DataFrame: 날짜, 키워드, 클릭비율
    """
    client_id, client_secret = _get_datalab_creds()
    if not client_id:
        return pd.DataFrame()

    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": time_unit,
        "category": category_id,
        "keyword": keyword_groups,
    }
    if device:
        body["device"] = device
    if gender:
        body["gender"] = gender
    if ages:
        body["ages"] = ages

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            "https://openapi.naver.com/v1/datalab/shopping/category/keywords",
            json=body, headers=headers, timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.error(f"쇼핑인사이트 키워드 API 오류: {e}")
        return pd.DataFrame()

    rows = []
    for result in data.get("results", []):
        name = result["title"]
        for item in result.get("data", []):
            rows.append({
                "날짜": item["period"],
                "키워드": name,
                "클릭비율": item["ratio"],
            })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["날짜"] = pd.to_datetime(df["날짜"])
    return df


# ═══════════════════════════════════════════════════════════════
#  쇼핑인사이트 - 기기별/성별/연령별 트렌드
# ═══════════════════════════════════════════════════════════════
def shopping_keyword_by_device(category_id: str, keyword: str,
                               start_date: str = None, end_date: str = None,
                               time_unit: str = "month") -> pd.DataFrame:
    """키워드의 기기별(PC/모바일) 클릭 비율"""
    client_id, client_secret = _get_datalab_creds()
    if not client_id:
        return pd.DataFrame()

    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": time_unit,
        "category": category_id,
        "keyword": keyword,
    }

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            "https://openapi.naver.com/v1/datalab/shopping/category/keyword/device",
            json=body, headers=headers, timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.error(f"쇼핑인사이트 기기별 API 오류: {e}")
        return pd.DataFrame()

    rows = []
    for result in data.get("results", []):
        device = result["device"]
        for item in result.get("data", []):
            rows.append({
                "날짜": item["period"],
                "기기": "PC" if device == "pc" else "모바일",
                "비율": item["ratio"],
            })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["날짜"] = pd.to_datetime(df["날짜"])
    return df


def shopping_keyword_by_gender(category_id: str, keyword: str,
                                start_date: str = None, end_date: str = None,
                                time_unit: str = "month") -> pd.DataFrame:
    """키워드의 성별 클릭 비율"""
    client_id, client_secret = _get_datalab_creds()
    if not client_id:
        return pd.DataFrame()

    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": time_unit,
        "category": category_id,
        "keyword": keyword,
    }

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            "https://openapi.naver.com/v1/datalab/shopping/category/keyword/gender",
            json=body, headers=headers, timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.error(f"쇼핑인사이트 성별 API 오류: {e}")
        return pd.DataFrame()

    rows = []
    for result in data.get("results", []):
        gender = result["gender"]
        for item in result.get("data", []):
            rows.append({
                "날짜": item["period"],
                "성별": "남성" if gender == "m" else "여성",
                "비율": item["ratio"],
            })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["날짜"] = pd.to_datetime(df["날짜"])
    return df


def shopping_keyword_by_age(category_id: str, keyword: str,
                             start_date: str = None, end_date: str = None,
                             time_unit: str = "month") -> pd.DataFrame:
    """키워드의 연령별 클릭 비율"""
    client_id, client_secret = _get_datalab_creds()
    if not client_id:
        return pd.DataFrame()

    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": time_unit,
        "category": category_id,
        "keyword": keyword,
    }

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            "https://openapi.naver.com/v1/datalab/shopping/category/keyword/age",
            json=body, headers=headers, timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.error(f"쇼핑인사이트 연령별 API 오류: {e}")
        return pd.DataFrame()

    age_map = {"10": "10대", "20": "20대", "30": "30대",
               "40": "40대", "50": "50대", "60": "60대"}

    rows = []
    for result in data.get("results", []):
        age = age_map.get(result["age"], result["age"])
        for item in result.get("data", []):
            rows.append({
                "날짜": item["period"],
                "연령": age,
                "비율": item["ratio"],
            })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["날짜"] = pd.to_datetime(df["날짜"])
    return df

# -*- coding: utf-8 -*-
"""
네이버 검색광고 API 클라이언트
─────────────────────────────
캠페인 / 광고그룹 / 키워드 목록 조회 + 성과 통계 수집
"""

import hashlib
import hmac
import time
import requests
import pandas as pd
from datetime import datetime, timedelta

BASE_URL = "https://api.searchad.naver.com"


class NaverAdClient:
    """네이버 검색광고 API 클라이언트"""

    def __init__(self, api_key: str, secret_key: str, customer_id: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.customer_id = str(customer_id)

    def _signature(self, timestamp: str, method: str, path: str) -> str:
        """HMAC-SHA256 서명 생성"""
        message = f"{timestamp}.{method}.{path}"
        sign = hmac.new(
            self.secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        import base64
        return base64.b64encode(sign).decode("utf-8")

    def _headers(self, method: str, path: str) -> dict:
        timestamp = str(int(time.time() * 1000))
        return {
            "Content-Type": "application/json; charset=UTF-8",
            "X-Timestamp": timestamp,
            "X-API-KEY": self.api_key,
            "X-Customer": self.customer_id,
            "X-Signature": self._signature(timestamp, method, path),
        }

    def _get(self, path: str, params: dict = None) -> list | dict:
        url = BASE_URL + path
        headers = self._headers("GET", path)
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict = None) -> list | dict:
        url = BASE_URL + path
        headers = self._headers("POST", path)
        resp = requests.post(url, headers=headers, json=body, timeout=60)
        resp.raise_for_status()
        return resp.json()

    # ─── 캠페인 ────────────────────────────────────────────
    def get_campaigns(self) -> list:
        """전체 캠페인 목록"""
        return self._get("/ncc/campaigns")

    # ─── 광고그룹 ──────────────────────────────────────────
    def get_adgroups(self, campaign_id: str = None) -> list:
        """광고그룹 목록 (캠페인ID 선택)"""
        params = {}
        if campaign_id:
            params["nccCampaignId"] = campaign_id
        return self._get("/ncc/adgroups", params)

    # ─── 키워드 ────────────────────────────────────────────
    def get_keywords(self, adgroup_id: str) -> list:
        """광고그룹 내 키워드 목록"""
        return self._get("/ncc/keywords", {"nccAdgroupId": adgroup_id})

    # ─── 광고 소재 ─────────────────────────────────────────
    def get_ads(self, adgroup_id: str) -> list:
        """광고그룹 내 광고 소재 목록"""
        return self._get("/ncc/ads", {"nccAdgroupId": adgroup_id})

    # ─── 성과 통계 ─────────────────────────────────────────
    def get_stats(
        self,
        ids: list[str],
        fields: list[str] = None,
        start_date: str = None,
        end_date: str = None,
        time_increment: str = "allDays",  # allDays / 1 (일별)
    ) -> list:
        """
        성과 통계 조회 (GET /stats)

        Args:
            ids: 캠페인/광고그룹/키워드 ID 리스트
            fields: 조회 필드 (기본: 전체)
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            time_increment: 집계 단위 (allDays / 1)
        """
        import json as _json

        if fields is None:
            fields = [
                "impCnt", "clkCnt", "salesAmt", "ctr", "cpc",
                "ccnt", "crto", "convAmt", "ror", "cpConv",
                "avgRnk",
            ]

        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # GET /stats — URL 길이 제한으로 20개씩 배치
        BATCH = 20
        all_data = []
        for i in range(0, len(ids), BATCH):
            batch = ids[i:i+BATCH]
            params = {
                "ids": ",".join(batch),
                "fields": _json.dumps(fields),
                "timeRange": _json.dumps({"since": start_date, "until": end_date}),
                "timeIncrement": time_increment,
            }
            try:
                result = self._get("/stats", params)
                data = result.get("data", []) if isinstance(result, dict) else result
                all_data.extend(data)
            except Exception:
                # 배치 실패 시 건너뜀
                continue

        return all_data

    # ─── 비즈머니 잔액 ─────────────────────────────────────
    def get_bizmoney(self) -> dict:
        """비즈머니(광고비) 잔액 조회"""
        try:
            result = self._get("/billing/bizmoney")
            return result if isinstance(result, dict) else (result[0] if result else {})
        except Exception:
            return {}

    # ─── 캠페인 예산 정보 ─────────────────────────────────
    def get_campaign_budgets(self) -> list:
        """전체 캠페인의 일예산 및 상태 조회"""
        campaigns = self.get_campaigns()
        budgets = []
        for c in campaigns:
            budgets.append({
                "campaignId": c.get("nccCampaignId", ""),
                "캠페인명": c.get("name", ""),
                "상태": c.get("status", ""),
                "일예산": c.get("dailyBudget", 0),
                "캠페인유형": c.get("campaignTp", ""),
                "활성": c.get("enable", False),
                "배송방법": c.get("deliveryMethod", ""),
            })
        return budgets

    # ─── 당일 실시간 캠페인 통계 ──────────────────────────
    def fetch_today_stats(self) -> pd.DataFrame:
        """당일(오늘) 캠페인별 실시간 성과 (1~3시간 지연)"""
        campaigns = self.get_campaigns()
        if not campaigns:
            return pd.DataFrame()

        active = [c for c in campaigns if c.get("status") == "ELIGIBLE"]
        if not active:
            return pd.DataFrame()

        camp_ids = [c["nccCampaignId"] for c in active]
        camp_map = {c["nccCampaignId"]: c.get("name", "") for c in active}

        today = datetime.now().strftime("%Y-%m-%d")
        stats = self.get_stats(
            ids=camp_ids,
            start_date=today,
            end_date=today,
            time_increment="allDays",
        )

        rows = []
        for s in stats:
            row = dict(s)
            cid = row.pop("id", "")
            row["campaignId"] = cid
            row["캠페인명"] = camp_map.get(cid, "")
            rows.append(row)

        df = pd.DataFrame(rows)
        return _rename_stat_cols(df)

    # ─── 키워드 도구 (관련 키워드) ─────────────────────────
    def get_related_keywords(self, keyword: str, include_stats: bool = True) -> list:
        """연관 키워드 조회 (키워드 도구)"""
        params = {
            "siteId": "",
            "biztpId": 0,
            "hintKeywords": keyword,
            "event": 0,
            "month": 0,
            "showDetail": "1" if include_stats else "0",
        }
        return self._get("/keywordstool", params)

    # ═══════════════════════════════════════════════════════
    #  고수준 데이터 수집 함수
    # ═══════════════════════════════════════════════════════

    def fetch_campaign_stats(
        self, start_date: str = None, end_date: str = None, daily: bool = False
    ) -> pd.DataFrame:
        """캠페인별 성과 DataFrame 반환"""
        campaigns = self.get_campaigns()
        if not campaigns:
            return pd.DataFrame()

        camp_ids = [c["nccCampaignId"] for c in campaigns]
        camp_map = {c["nccCampaignId"]: {
            "캠페인명": c.get("name", ""),
            "상태": c.get("status", ""),
            "타입": c.get("campaignTp", ""),
        } for c in campaigns}

        stats = self.get_stats(
            ids=camp_ids,
            start_date=start_date,
            end_date=end_date,
            time_increment="1" if daily else "allDays",
        )

        # GET /stats 응답: [{"id": "...", "impCnt": ..., ...}, ...]
        rows = []
        for s in stats:
            row = dict(s)
            cid = row.pop("id", "")
            row["campaignId"] = cid
            row.update(camp_map.get(cid, {}))
            rows.append(row)

        df = pd.DataFrame(rows)
        return _rename_stat_cols(df)

    def fetch_adgroup_stats(
        self, campaign_id: str = None, start_date: str = None, end_date: str = None
    ) -> pd.DataFrame:
        """광고그룹별 성과 DataFrame 반환"""
        adgroups = self.get_adgroups(campaign_id)
        if not adgroups:
            return pd.DataFrame()

        ag_ids = [ag["nccAdgroupId"] for ag in adgroups]
        ag_map = {
            ag["nccAdgroupId"]: {
                "광고그룹명": ag.get("name", ""),
                "campaignId": ag.get("nccCampaignId", ""),
                "타입": ag.get("adgroupType", ""),
                "활성": ag.get("enable", False),
                "입찰가": ag.get("bidAmt", 0),
            }
            for ag in adgroups
        }

        stats = self.get_stats(ids=ag_ids, start_date=start_date, end_date=end_date)

        rows = []
        for s in stats:
            row = dict(s)
            ag_id = row.pop("id", "")
            row["adgroupId"] = ag_id
            row.update(ag_map.get(ag_id, {}))
            rows.append(row)

        df = pd.DataFrame(rows)
        return _rename_stat_cols(df)

    def fetch_keyword_stats(
        self, adgroup_id: str = None, campaign_id: str = None,
        start_date: str = None, end_date: str = None,
    ) -> pd.DataFrame:
        """키워드별 성과 DataFrame 반환"""
        if adgroup_id:
            adgroups = [{"nccAdgroupId": adgroup_id}]
        else:
            adgroups = self.get_adgroups(campaign_id)

        if not adgroups:
            return pd.DataFrame()

        # 캠페인 이름 매핑 (있으면)
        camp_map = {}
        if campaign_id is None:
            try:
                camps = self.get_campaigns()
                camp_map = {c["nccCampaignId"]: c.get("name", "") for c in camps}
            except Exception:
                pass

        all_keywords = []
        kw_map = {}
        for ag in adgroups:
            ag_id = ag["nccAdgroupId"]
            ag_name = ag.get("name", ag_id)
            ag_camp_id = ag.get("nccCampaignId", "")
            try:
                kws = self.get_keywords(ag_id)
                for kw in kws:
                    kw_id = kw.get("nccKeywordId", "")
                    all_keywords.append(kw_id)
                    # 품질지수 파싱 (nccQi.qiGrade)
                    ncc_qi = kw.get("nccQi") or {}
                    qi_grade = ncc_qi.get("qiGrade", 0) if isinstance(ncc_qi, dict) else 0

                    kw_map[kw_id] = {
                        "키워드": kw.get("keyword", ""),
                        "입찰가": kw.get("bidAmt", 0),
                        "품질지수": qi_grade,
                        "광고관련성": kw.get("adRelevanceScore", 0),
                        "예상클릭률": kw.get("expectedClickScore", 0),
                        "상태": kw.get("status", ""),
                        "활성": kw.get("enable", True),
                        "adgroupId": ag_id,
                        "광고그룹명": ag_name,
                        "campaignId": ag_camp_id,
                        "캠페인명": camp_map.get(ag_camp_id, ""),
                    }
            except Exception:
                continue

        if not all_keywords:
            return pd.DataFrame()

        stats = self.get_stats(ids=all_keywords, start_date=start_date, end_date=end_date)

        rows = []
        for s in stats:
            row = dict(s)
            kw_id = row.pop("id", "")
            row["keywordId"] = kw_id
            row.update(kw_map.get(kw_id, {}))
            rows.append(row)

        df = pd.DataFrame(rows)
        return _rename_stat_cols(df)

    def fetch_keyword_daily_stats(
        self, adgroup_id: str = None, campaign_id: str = None,
        start_date: str = None, end_date: str = None,
        keyword_ids: list = None,
    ) -> pd.DataFrame:
        """키워드별 일별 성과 (트렌드 분석용)

        keyword_ids를 전달하면 해당 키워드만 조회 (속도 최적화)
        """
        # 날짜 범위 제한: 일별 통계는 최근 14일만
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        if keyword_ids:
            # 이미 키워드 ID가 주어진 경우 바로 조회
            kw_map = {}
            all_keywords = keyword_ids
        else:
            adgroups = self.get_adgroups(campaign_id) if not adgroup_id else [{"nccAdgroupId": adgroup_id}]
            if not adgroups:
                return pd.DataFrame()

            # 활성 광고그룹만 필터링
            active_ags = [ag for ag in adgroups if ag.get("enable", True)]
            if not active_ags:
                active_ags = adgroups

            all_keywords = []
            kw_map = {}
            for ag in active_ags:
                ag_id = ag["nccAdgroupId"]
                try:
                    kws = self.get_keywords(ag_id)
                    for kw in kws:
                        if kw.get("status") not in ("PAUSED", "DELETED"):
                            kw_id = kw.get("nccKeywordId", "")
                            all_keywords.append(kw_id)
                            kw_map[kw_id] = {
                                "키워드": kw.get("keyword", ""),
                                "광고그룹명": ag.get("name", ag_id),
                            }
                except Exception:
                    continue

        if not all_keywords:
            return pd.DataFrame()

        stats = self.get_stats(
            ids=all_keywords, start_date=start_date, end_date=end_date,
            time_increment="1",  # 일별
        )

        rows = []
        for s in stats:
            row = dict(s)
            kw_id = row.pop("id", "")
            row["keywordId"] = kw_id
            row.update(kw_map.get(kw_id, {}))
            rows.append(row)

        df = pd.DataFrame(rows)
        return _rename_stat_cols(df)


# ═══════════════════════════════════════════════════════════════
#  API 필드명 → 한글 매핑
# ═══════════════════════════════════════════════════════════════
STAT_COL_MAP = {
    "impCnt": "노출수",
    "clkCnt": "클릭수",
    "salesAmt": "광고비(VAT포함)",
    "ctr": "CTR(%)",
    "cpc": "평균CPC",
    "ccnt": "전환수",
    "crto": "전환율(%)",
    "convAmt": "전환매출액",
    "ror": "ROAS(%)",
    "cpConv": "전환당비용",
    "viewCnt": "노출(뷰)",
    "avgRnk": "평균순위",
    "stat_dt": "날짜",
}


def _rename_stat_cols(df: pd.DataFrame) -> pd.DataFrame:
    """API 통계 컬럼명을 한글로 변환"""
    if df.empty:
        return df
    df = df.rename(columns=STAT_COL_MAP)
    # 숫자 변환
    num_cols = ["노출수", "클릭수", "광고비(VAT포함)", "평균CPC", "전환수",
                "전환매출액", "전환당비용", "평균순위", "입찰가"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    pct_cols = ["CTR(%)", "전환율(%)", "ROAS(%)"]
    for col in pct_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

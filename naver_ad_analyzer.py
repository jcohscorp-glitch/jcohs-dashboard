# -*- coding: utf-8 -*-
"""
네이버 검색광고 상세 분석기
─────────────────────────────
API에서 수집한 키워드/광고그룹/캠페인 데이터를 심층 분석
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════════
#  1. 키워드 4분면 분류 (강화 버전)
# ═══════════════════════════════════════════════════════════════
def classify_keywords_advanced(
    df: pd.DataFrame,
    margin_rate: float = 0.30,
    min_clicks_star: int = 30,
    min_clicks_stat: int = 10,
    min_cost_negative: int = 10_000,
) -> pd.DataFrame:
    """
    키워드를 8개 세부 그룹으로 분류 (기존 4그룹 확장)

    A1: 고효율 고볼륨 — ROAS 높고 클릭 많음 → 예산 증액
    A2: 고효율 저볼륨 — ROAS 높지만 클릭 적음 → 입찰가 상승
    B1: 전환있는 잠재력 — 전환 발생, ROAS 중간 → 최적화 여지
    B2: 노출만 많은 잠재력 — 클릭률 낮음 → 소재 개선
    C1: 고비용 무전환 — 비용만 소진 → 즉시 제외
    C2: 고비용 저전환 — 전환은 있지만 적자 → 입찰가 하향
    D1: 데이터 부족 (신규) — 최근 등록, 판단 유보
    D2: 데이터 부족 (장기) — 오래됐는데 데이터 없음 → 제외 검토
    """
    df = df.copy()

    # 파생 지표
    df["순이익"] = (df.get("전환매출액", 0) * margin_rate) - df.get("광고비(VAT포함)", 0)
    bep = (1 / margin_rate) * 100 if margin_rate > 0 else 0

    # 안전한 컬럼 참조
    clicks = df.get("클릭수", pd.Series(0, index=df.index))
    roas = df.get("ROAS(%)", pd.Series(0, index=df.index))
    cost = df.get("광고비(VAT포함)", pd.Series(0, index=df.index))
    conv = df.get("전환수", pd.Series(0, index=df.index))
    ctr = df.get("CTR(%)", pd.Series(0, index=df.index))
    profit = df["순이익"]

    conditions = [
        # D: 데이터 부족
        (clicks < min_clicks_stat),
        # A1: 고효율 고볼륨
        (roas >= bep) & (clicks >= min_clicks_star) & (profit > 0),
        # A2: 고효율 저볼륨
        (roas >= bep) & (clicks >= min_clicks_stat) & (clicks < min_clicks_star) & (profit > 0),
        # B1: 전환있는 잠재력
        (conv > 0) & (roas < bep) & (roas >= bep * 0.5),
        # B2: 노출만 많은 잠재력
        (clicks >= min_clicks_stat) & (conv == 0) & (cost < min_cost_negative) & (ctr < 2.0),
        # C1: 고비용 무전환
        (cost >= min_cost_negative) & (conv == 0),
        # C2: 고비용 저전환
        (cost >= min_cost_negative) & (conv > 0) & (roas < bep * 0.5),
    ]
    choices = [
        "D_데이터부족",
        "A1_고효율_고볼륨",
        "A2_고효율_저볼륨",
        "B1_전환있는_잠재력",
        "B2_노출만_많은_잠재력",
        "C1_고비용_무전환",
        "C2_고비용_저전환",
    ]
    df["세부그룹"] = np.select(conditions, choices, default="D_데이터부족")

    # 기존 4그룹 호환
    group_map = {
        "A1_고효율_고볼륨": "A그룹_예산증액",
        "A2_고효율_저볼륨": "A그룹_예산증액",
        "B1_전환있는_잠재력": "B그룹_최적화",
        "B2_노출만_많은_잠재력": "B그룹_최적화",
        "C1_고비용_무전환": "C그룹_제외",
        "C2_고비용_저전환": "C그룹_제외",
        "D_데이터부족": "D그룹_판단유보",
    }
    df["Action_Group"] = df["세부그룹"].map(group_map)

    return df


# ═══════════════════════════════════════════════════════════════
#  2. 입찰가 추천
# ═══════════════════════════════════════════════════════════════
def recommend_bid(
    df: pd.DataFrame,
    target_roas: float = 500,  # 목표 ROAS (%)
    margin_rate: float = 0.30,
    max_bid_increase: float = 1.5,   # 최대 50% 인상
    max_bid_decrease: float = 0.5,   # 최대 50% 인하
) -> pd.DataFrame:
    """
    키워드별 적정 입찰가 추천

    로직: 목표 ROAS 달성을 위한 최대 허용 CPC 계산
    적정CPC = (전환매출액 × 마진율) / 클릭수 / (목표ROAS / 100)
    """
    df = df.copy()

    clicks = df.get("클릭수", pd.Series(0, index=df.index)).replace(0, 1)
    conv_amt = df.get("전환매출액", pd.Series(0, index=df.index))
    current_bid = df.get("입찰가", pd.Series(0, index=df.index))

    # 클릭당 마진 수익
    epc_margin = (conv_amt * margin_rate) / clicks

    # 목표 ROAS 기준 최대 허용 CPC
    target_ratio = target_roas / 100
    df["적정CPC"] = np.where(
        target_ratio > 0,
        epc_margin / target_ratio,
        0,
    ).round(0)

    # 추천 입찰가 = 적정CPC (단, 현재 입찰가 대비 ±50% 범위 제한)
    df["추천입찰가"] = df["적정CPC"].clip(
        lower=current_bid * max_bid_decrease,
        upper=current_bid * max_bid_increase,
    ).round(0)

    # 전환 없는 키워드는 현재 입찰가 유지 또는 인하
    no_conv = conv_amt == 0
    df.loc[no_conv, "추천입찰가"] = (current_bid[no_conv] * 0.7).round(0)

    # 변경률
    df["입찰가변경률(%)"] = np.where(
        current_bid > 0,
        ((df["추천입찰가"] - current_bid) / current_bid * 100).round(1),
        0,
    )

    # 액션 라벨
    df["입찰가액션"] = np.select(
        [
            df["입찰가변경률(%)"] >= 20,
            df["입찰가변경률(%)"] >= 5,
            df["입찰가변경률(%)"] <= -20,
            df["입찰가변경률(%)"] <= -5,
        ],
        ["🔺 대폭 인상", "🔼 소폭 인상", "🔻 대폭 인하", "🔽 소폭 인하"],
        default="➖ 유지",
    )

    return df


# ═══════════════════════════════════════════════════════════════
#  3. 품질지수 분석
# ═══════════════════════════════════════════════════════════════
def analyze_quality_index(df: pd.DataFrame) -> pd.DataFrame:
    """품질지수와 성과 상관관계 분석"""
    df = df.copy()

    qi = df.get("품질지수", pd.Series(0, index=df.index))

    df["품질등급"] = np.select(
        [qi >= 7, qi >= 4, qi >= 1, qi == 0],
        ["상", "중", "하", "미측정"],
        default="미측정",
    )

    # 품질지수별 CPC 프리미엄/할인 추정
    # 높은 품질지수 = 낮은 실제 CPC (네이버 알고리즘)
    df["품질_CPC효과"] = np.select(
        [qi >= 7, qi >= 4, qi >= 1],
        ["CPC 할인 (추정 -20~30%)", "기본 CPC", "CPC 프리미엄 (추정 +20~50%)"],
        default="-",
    )

    return df


# ═══════════════════════════════════════════════════════════════
#  4. 키워드 트렌드 분석
# ═══════════════════════════════════════════════════════════════
def analyze_keyword_trend(daily_df: pd.DataFrame, window: int = 7) -> pd.DataFrame:
    """
    일별 데이터에서 키워드 트렌드 추출

    Returns:
        키워드별 최근 vs 이전 기간 비교 + 트렌드 라벨
    """
    if daily_df.empty or "날짜" not in daily_df.columns:
        return pd.DataFrame()

    df = daily_df.copy()
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")

    max_date = df["날짜"].max()
    mid_date = max_date - pd.Timedelta(days=window)

    recent = df[df["날짜"] > mid_date]
    previous = df[df["날짜"] <= mid_date]

    def _agg(grp):
        return grp.groupby("키워드").agg(
            클릭수=("클릭수", "sum"),
            광고비=("광고비(VAT포함)", "sum"),
            전환수=("전환수", "sum"),
            전환매출액=("전환매출액", "sum"),
        ).reset_index()

    r = _agg(recent).add_suffix("_최근")
    p = _agg(previous).add_suffix("_이전")

    r = r.rename(columns={"키워드_최근": "키워드"})
    p = p.rename(columns={"키워드_이전": "키워드"})

    merged = r.merge(p, on="키워드", how="outer").fillna(0)

    # 변화율
    for metric in ["클릭수", "광고비", "전환수", "전환매출액"]:
        prev_col = f"{metric}_이전"
        recent_col = f"{metric}_최근"
        change_col = f"{metric}_변화율(%)"
        merged[change_col] = np.where(
            merged[prev_col] > 0,
            ((merged[recent_col] - merged[prev_col]) / merged[prev_col] * 100).round(1),
            np.where(merged[recent_col] > 0, 100, 0),
        )

    # ROAS 변화
    merged["ROAS_최근(%)"] = np.where(
        merged["광고비_최근"] > 0,
        (merged["전환매출액_최근"] / merged["광고비_최근"] * 100).round(0),
        0,
    )
    merged["ROAS_이전(%)"] = np.where(
        merged["광고비_이전"] > 0,
        (merged["전환매출액_이전"] / merged["광고비_이전"] * 100).round(0),
        0,
    )

    # 트렌드 라벨
    click_change = merged["클릭수_변화율(%)"]
    roas_recent = merged["ROAS_최근(%)"]
    roas_prev = merged["ROAS_이전(%)"]

    merged["트렌드"] = np.select(
        [
            (click_change >= 20) & (roas_recent >= roas_prev),
            (click_change >= 20) & (roas_recent < roas_prev),
            (click_change <= -20) & (roas_recent >= roas_prev),
            (click_change <= -20) & (roas_recent < roas_prev),
        ],
        [
            "🚀 급상승 (효율 유지)",
            "⚠️ 트래픽 증가 (효율 하락)",
            "📉 트래픽 감소 (효율 유지)",
            "🔻 하락세",
        ],
        default="➖ 안정",
    )

    return merged


# ═══════════════════════════════════════════════════════════════
#  5. 광고그룹 최적화 점수
# ═══════════════════════════════════════════════════════════════
def score_adgroups(adgroup_df: pd.DataFrame, keyword_df: pd.DataFrame) -> pd.DataFrame:
    """
    광고그룹별 최적화 점수 (0~100)

    평가 기준:
    - ROAS 점수 (40%)
    - CTR 점수 (20%)
    - 전환율 점수 (20%)
    - 키워드 효율 점수 (20%) — A그룹 비율
    """
    if adgroup_df.empty:
        return pd.DataFrame()

    df = adgroup_df.copy()

    # ROAS 점수 (0~40) — 300% 이상이면 만점
    roas = df.get("ROAS(%)", pd.Series(0, index=df.index))
    df["ROAS점수"] = (roas / 300 * 40).clip(0, 40).round(1)

    # CTR 점수 (0~20) — 5% 이상이면 만점
    ctr = df.get("CTR(%)", pd.Series(0, index=df.index))
    df["CTR점수"] = (ctr / 5 * 20).clip(0, 20).round(1)

    # 전환율 점수 (0~20) — 10% 이상이면 만점
    cvr = df.get("전환율(%)", pd.Series(0, index=df.index))
    df["CVR점수"] = (cvr / 10 * 20).clip(0, 20).round(1)

    # 키워드 효율 점수 (0~20) — A그룹 비율
    if not keyword_df.empty and "adgroupId" in keyword_df.columns and "Action_Group" in keyword_df.columns:
        kw_score = keyword_df.groupby("adgroupId", as_index=False).agg(
            _a_count=("Action_Group", lambda x: (x == "A그룹_예산증액").sum()),
            _total=("Action_Group", "count"),
        )
        kw_score["KW점수"] = (kw_score["_a_count"] / kw_score["_total"].replace(0, 1) * 20).round(1)
        kw_score = kw_score[["adgroupId", "KW점수"]]
        df = df.merge(kw_score, on="adgroupId", how="left")
        df["KW점수"] = df["KW점수"].fillna(0).round(1)
    else:
        df["KW점수"] = 0

    df["최적화점수"] = (df["ROAS점수"] + df["CTR점수"] + df["CVR점수"] + df["KW점수"]).round(0)

    df["최적화등급"] = np.select(
        [df["최적화점수"] >= 80, df["최적화점수"] >= 60, df["최적화점수"] >= 40],
        ["A (우수)", "B (양호)", "C (개선필요)"],
        default="D (위험)",
    )

    return df


# ═══════════════════════════════════════════════════════════════
#  6. 예산 최적 배분 추천
# ═══════════════════════════════════════════════════════════════
def recommend_budget_allocation(
    df: pd.DataFrame,
    total_budget: float = None,
    margin_rate: float = 0.30,
) -> pd.DataFrame:
    """
    키워드별 한계수익(Marginal Revenue) 기반 예산 재배분 추천

    높은 ROAS → 더 많은 예산 / 낮은 ROAS → 예산 축소
    """
    df = df.copy()

    roas = df.get("ROAS(%)", pd.Series(0, index=df.index))
    cost = df.get("광고비(VAT포함)", pd.Series(0, index=df.index))

    if total_budget is None:
        total_budget = cost.sum()

    # 한계수익 점수 = ROAS × 마진율 (순이익 기여도)
    df["한계수익점수"] = (roas * margin_rate).clip(lower=0)

    total_score = df["한계수익점수"].sum()
    if total_score > 0:
        df["추천예산비율(%)"] = (df["한계수익점수"] / total_score * 100).round(1)
        df["추천예산"] = (df["한계수익점수"] / total_score * total_budget).round(0)
    else:
        df["추천예산비율(%)"] = 0
        df["추천예산"] = 0

    df["현재예산비율(%)"] = np.where(
        cost.sum() > 0, (cost / cost.sum() * 100).round(1), 0
    )
    df["예산변경액"] = (df["추천예산"] - cost).round(0)
    df["예산변경률(%)"] = np.where(
        cost > 0, ((df["추천예산"] - cost) / cost * 100).round(1), 0
    )

    return df


# ═══════════════════════════════════════════════════════════════
#  7. CPC × CTR 매트릭스 (시장 경쟁·매력도 분석)
# ═══════════════════════════════════════════════════════════════
def analyze_cpc_ctr_matrix(df: pd.DataFrame, min_clicks: int = 5) -> pd.DataFrame:
    """
    CPC와 CTR의 상관관계로 4분면 분류

    고CTR+저CPC (노다지) → 예산 우선 배정
    고CTR+고CPC (경쟁격전) → 상세페이지 최적화로 전환율 확보
    저CTR+저CPC (무관심) → 썸네일/소재 교체 또는 제외
    저CTR+고CPC (돈낭비) → 즉시 중단
    """
    df = df.copy()
    filtered = df[df.get("클릭수", pd.Series(0, index=df.index)) >= min_clicks].copy()
    if filtered.empty:
        return pd.DataFrame()

    cpc = filtered.get("평균CPC", pd.Series(0, index=filtered.index))
    ctr = filtered.get("CTR(%)", pd.Series(0, index=filtered.index))

    cpc_median = cpc.median() if cpc.median() > 0 else cpc.mean()
    ctr_median = ctr.median() if ctr.median() > 0 else ctr.mean()

    filtered["CPC_CTR구간"] = np.select(
        [
            (ctr >= ctr_median) & (cpc <= cpc_median),
            (ctr >= ctr_median) & (cpc > cpc_median),
            (ctr < ctr_median) & (cpc <= cpc_median),
            (ctr < ctr_median) & (cpc > cpc_median),
        ],
        ["🟢 노다지 (고CTR+저CPC)", "🟡 경쟁격전 (고CTR+고CPC)",
         "⚪ 무관심 (저CTR+저CPC)", "🔴 돈낭비 (저CTR+고CPC)"],
        default="기타",
    )
    filtered["CPC중앙값"] = cpc_median
    filtered["CTR중앙값"] = ctr_median

    return filtered


# ═══════════════════════════════════════════════════════════════
#  8. 요일별 효율 분석
# ═══════════════════════════════════════════════════════════════
def analyze_day_of_week(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    일별 데이터에서 요일별 효율 패턴 추출

    Returns:
        요일별 평균 클릭수, 광고비, 전환수, ROAS, CTR
    """
    if daily_df.empty or "날짜" not in daily_df.columns:
        return pd.DataFrame()

    df = daily_df.copy()
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    df = df.dropna(subset=["날짜"])

    if df.empty:
        return pd.DataFrame()

    df["요일"] = df["날짜"].dt.day_name()
    df["요일번호"] = df["날짜"].dt.dayofweek  # 0=Mon

    # 요일별 합산 후 일수로 나눠 평균
    day_counts = df.groupby("요일번호")["날짜"].apply(lambda x: x.dt.date.nunique()).reset_index()
    day_counts.columns = ["요일번호", "일수"]

    agg_cols = {}
    for col in ["클릭수", "광고비(VAT포함)", "전환수", "전환매출액", "노출수"]:
        if col in df.columns:
            agg_cols[col] = (col, "sum")

    if not agg_cols:
        return pd.DataFrame()

    daily_agg = df.groupby("요일번호", as_index=False).agg(**agg_cols)
    daily_agg = daily_agg.merge(day_counts, on="요일번호")

    for col in agg_cols:
        daily_agg[f"일평균_{col}"] = (daily_agg[col] / daily_agg["일수"]).round(0)

    # ROAS 계산
    if "광고비(VAT포함)" in daily_agg.columns and "전환매출액" in daily_agg.columns:
        daily_agg["ROAS(%)"] = np.where(
            daily_agg["광고비(VAT포함)"] > 0,
            (daily_agg["전환매출액"] / daily_agg["광고비(VAT포함)"] * 100).round(0),
            0,
        )

    # CTR
    if "노출수" in daily_agg.columns and "클릭수" in daily_agg.columns:
        daily_agg["CTR(%)"] = np.where(
            daily_agg["노출수"] > 0,
            (daily_agg["클릭수"] / daily_agg["노출수"] * 100).round(2),
            0,
        )

    # 요일 이름 매핑
    dow_map = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
    daily_agg["요일"] = daily_agg["요일번호"].map(dow_map)
    daily_agg = daily_agg.sort_values("요일번호")

    # 효율 등급
    if "ROAS(%)" in daily_agg.columns:
        roas_avg = daily_agg["ROAS(%)"].mean()
        daily_agg["효율등급"] = np.select(
            [daily_agg["ROAS(%)"] >= roas_avg * 1.2, daily_agg["ROAS(%)"] <= roas_avg * 0.8],
            ["🟢 고효율", "🔴 저효율"],
            default="🟡 보통",
        )

    return daily_agg


# ═══════════════════════════════════════════════════════════════
#  9. 노출 점유율(SOV) 추이 분석
# ═══════════════════════════════════════════════════════════════
def analyze_impression_trend(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    일별 노출수 추이에서 노출 정체/감소 경고 감지

    Returns:
        일별 노출수 + 7일 이동평균 + 추이 판단
    """
    if daily_df.empty or "날짜" not in daily_df.columns:
        return pd.DataFrame()

    df = daily_df.copy()
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    df = df.dropna(subset=["날짜"])

    # 일별 합산
    agg_cols = {}
    for col in ["노출수", "클릭수", "광고비(VAT포함)", "전환수"]:
        if col in df.columns:
            agg_cols[col] = (col, "sum")

    if "노출수" not in agg_cols:
        return pd.DataFrame()

    daily = df.groupby("날짜", as_index=False).agg(**agg_cols)
    daily = daily.sort_values("날짜")

    # 7일 이동평균
    daily["노출수_MA7"] = daily["노출수"].rolling(7, min_periods=3).mean().round(0)

    # 노출 추이 판단
    if len(daily) >= 7:
        first_half = daily["노출수"].iloc[:len(daily)//2].mean()
        second_half = daily["노출수"].iloc[len(daily)//2:].mean()
        change_pct = ((second_half - first_half) / max(first_half, 1) * 100)

        if change_pct >= 10:
            daily["노출추이"] = "📈 노출 증가 중"
        elif change_pct <= -10:
            daily["노출추이"] = "📉 노출 감소 — 입찰가/품질지수 점검 필요"
        else:
            daily["노출추이"] = "➖ 노출 안정"
        daily["노출변화율(%)"] = round(change_pct, 1)
    else:
        daily["노출추이"] = "데이터 부족"
        daily["노출변화율(%)"] = 0

    return daily


# ═══════════════════════════════════════════════════════════════
#  10. 전체 분석 파이프라인
# ═══════════════════════════════════════════════════════════════
def full_analysis(
    keyword_df: pd.DataFrame,
    adgroup_df: pd.DataFrame = None,
    daily_df: pd.DataFrame = None,
    margin_rate: float = 0.30,
    target_roas: float = 500,
) -> dict:
    """
    전체 분석 실행, 결과를 딕셔너리로 반환

    Returns:
        {
            "keywords": 키워드 분석 결과 (분류 + 입찰가 + 품질),
            "adgroups": 광고그룹 최적화 점수,
            "trends": 키워드 트렌드,
            "budget": 예산 배분 추천,
            "summary": 전체 요약 통계,
        }
    """
    result = {}

    # 키워드 분석
    kw = classify_keywords_advanced(keyword_df, margin_rate=margin_rate)
    kw = recommend_bid(kw, target_roas=target_roas, margin_rate=margin_rate)
    kw = analyze_quality_index(kw)
    result["keywords"] = kw

    # 광고그룹 분석
    if adgroup_df is not None and not adgroup_df.empty:
        ag = score_adgroups(adgroup_df, kw)
        result["adgroups"] = ag
    else:
        result["adgroups"] = pd.DataFrame()

    # 트렌드 분석
    if daily_df is not None and not daily_df.empty:
        trends = analyze_keyword_trend(daily_df)
        result["trends"] = trends
    else:
        result["trends"] = pd.DataFrame()

    # 예산 배분
    budget = recommend_budget_allocation(kw, margin_rate=margin_rate)
    result["budget"] = budget

    # CPC × CTR 매트릭스
    cpc_ctr = analyze_cpc_ctr_matrix(kw)
    result["cpc_ctr_matrix"] = cpc_ctr

    # 요일별 효율 분석
    if daily_df is not None and not daily_df.empty:
        dow = analyze_day_of_week(daily_df)
        result["day_of_week"] = dow
    else:
        result["day_of_week"] = pd.DataFrame()

    # 노출 추이 분석
    if daily_df is not None and not daily_df.empty:
        imp_trend = analyze_impression_trend(daily_df)
        result["impression_trend"] = imp_trend
    else:
        result["impression_trend"] = pd.DataFrame()

    # 전체 요약
    summary = {
        "총 키워드 수": len(kw),
        "총 광고비": kw.get("광고비(VAT포함)", pd.Series(0)).sum(),
        "총 전환매출": kw.get("전환매출액", pd.Series(0)).sum(),
        "전체 ROAS(%)": round(
            kw["전환매출액"].sum() / max(kw["광고비(VAT포함)"].sum(), 1) * 100, 1
        ) if "전환매출액" in kw.columns and "광고비(VAT포함)" in kw.columns else 0,
        "총 순이익": kw.get("순이익", pd.Series(0)).sum(),
        "평균 품질지수": kw.get("품질지수", pd.Series(0)).mean(),
        "A그룹 비율(%)": round(
            (kw["Action_Group"] == "A그룹_예산증액").sum() / max(len(kw), 1) * 100, 1
        ),
        "C그룹 비율(%)": round(
            (kw["Action_Group"] == "C그룹_제외").sum() / max(len(kw), 1) * 100, 1
        ),
        "입찰가 인상 추천": (kw.get("입찰가액션", pd.Series("")).str.contains("인상")).sum(),
        "입찰가 인하 추천": (kw.get("입찰가액션", pd.Series("")).str.contains("인하")).sum(),
    }
    result["summary"] = summary

    return result

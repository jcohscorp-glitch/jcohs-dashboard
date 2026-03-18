# -*- coding: utf-8 -*-
"""
광고 키워드 매트릭스 분석기 (순수익 기반 4분면 자동 분류)
──────────────────────────────────────────────────────────
네이버/쿠팡 광고 데이터를 분석하여 키워드를 4개 그룹으로
자동 분류하고, 마케터가 즉시 액션을 취할 수 있도록 지원.
"""

import pandas as pd
import numpy as np


# ═══════════════════════════════════════════════════════════════
#  1. 설정 변수 (실무자가 수정 가능)
# ═══════════════════════════════════════════════════════════════
DEFAULT_MARGIN_RATE = 0.30          # 제품 평균 마진율 (30%)
MIN_CLICKS_STAR = 30                # A그룹(효자) 최소 클릭수
MIN_CLICKS_STAT = 10                # D그룹(판단유보) 기준 클릭수
MIN_COST_NEGATIVE = 10_000          # C그룹(제외) 최소 소진 광고비(원)

# ═══════════════════════════════════════════════════════════════
#  2. 표준 컬럼명 매핑 — 다양한 소스를 통일된 형식으로
# ═══════════════════════════════════════════════════════════════
# CSV 업로드용 표준 컬럼
STANDARD_COLS = ["캠페인명", "광고그룹명", "키워드", "노출수", "클릭수",
                 "총비용", "총전환수", "총전환매출액"]

# 네이버 SA → 표준 컬럼 매핑
NAVER_SA_MAP = {
    "캠페인": "캠페인명",
    "광고그룹": "광고그룹명",
    "총비용(VAT포함,원)": "총비용",
    "전환수": "총전환수",
    "전환매출액(원)": "총전환매출액",
}

# 쿠팡 키워드 → 표준 컬럼 매핑
COUPANG_KW_MAP = {
    "광고비": "총비용",
    "총 판매수량(14일)": "총전환수",
    "총 전환매출액(14일)": "총전환매출액",
}


# ═══════════════════════════════════════════════════════════════
#  3. 파생 지표 계산
# ═══════════════════════════════════════════════════════════════
def _safe_div(a, b):
    """0 나누기 방지 — 결과를 0으로 대체"""
    return np.where(b != 0, a / b, 0)


def compute_derived_metrics(df: pd.DataFrame, margin_rate: float = DEFAULT_MARGIN_RATE) -> pd.DataFrame:
    """
    기초 데이터에서 파생 지표를 계산하여 새 컬럼으로 추가.

    필수 입력 컬럼: 노출수, 클릭수, 총비용, 총전환수, 총전환매출액
    """
    df = df.copy()

    # 숫자 변환 (문자열 입력 대비)
    for col in ["노출수", "클릭수", "총비용", "총전환수", "총전환매출액"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # --- 파생 지표 ---
    df["CTR(%)"] = _safe_div(df["클릭수"], df["노출수"]) * 100                  # 클릭률
    df["CVR(%)"] = _safe_div(df["총전환수"], df["클릭수"]) * 100                 # 전환율
    df["ROAS(%)"] = _safe_div(df["총전환매출액"], df["총비용"]) * 100             # 광고수익률
    df["EPC"] = _safe_div(df["총전환매출액"], df["클릭수"])                       # 클릭당 수익
    df["CPA"] = _safe_div(df["총비용"], df["총전환수"])                           # 전환당 비용
    df["CPC"] = _safe_div(df["총비용"], df["클릭수"])                             # 클릭당 비용
    df["AOV"] = _safe_div(df["총전환매출액"], df["총전환수"])                      # 객단가

    # 손익분기점 ROAS (마진율 기반)
    df["BEP_ROAS(%)"] = (1 / margin_rate) * 100 if margin_rate > 0 else 0

    # 예상 순수익 = (전환매출 × 마진율) - 광고비
    df["Estimated_Profit"] = (df["총전환매출액"] * margin_rate) - df["총비용"]

    # inf → 0 처리
    df = df.replace([np.inf, -np.inf], 0)

    return df


# ═══════════════════════════════════════════════════════════════
#  4. 키워드 4분면 자동 분류 (Action_Group 라벨링)
# ═══════════════════════════════════════════════════════════════
def classify_keywords(
    df: pd.DataFrame,
    margin_rate: float = DEFAULT_MARGIN_RATE,
    min_clicks_star: int = MIN_CLICKS_STAR,
    min_clicks_stat: int = MIN_CLICKS_STAT,
    min_cost_negative: int = MIN_COST_NEGATIVE,
) -> pd.DataFrame:
    """
    각 키워드를 A/B/C/D 그룹으로 분류.

    A그룹_예산및입찰가증액  : ROAS ≥ BEP, 클릭 ≥ 30, 순이익 > 0 (효자 키워드)
    B그룹_입찰가강력상승    : ROAS ≥ BEP, 클릭 < 30 (잠재력 키워드)
    C그룹_즉시제외키워드    : 비용 ≥ 1만원 & (전환 0 or ROAS < BEP) (돈 먹는 하마)
    D그룹_판단유보          : 클릭 < 10 (통계 부족, 대기)
    """
    df = df.copy()
    bep = (1 / margin_rate) * 100 if margin_rate > 0 else 0

    conditions = [
        # D그룹 먼저 — 클릭 10 미만이면 무조건 판단유보
        (df["클릭수"] < min_clicks_stat),
        # A그룹 — 효자 키워드
        (df["ROAS(%)"] >= bep) & (df["클릭수"] >= min_clicks_star) & (df["Estimated_Profit"] > 0),
        # B그룹 — 잠재력 키워드 (ROAS 좋지만 트래픽 부족)
        (df["ROAS(%)"] >= bep) & (df["클릭수"] < min_clicks_star),
        # C그룹 — 즉시 제외 (비용만 소진)
        (df["총비용"] >= min_cost_negative) & ((df["총전환수"] == 0) | (df["ROAS(%)"] < bep)),
    ]
    choices = [
        "D그룹_판단유보",
        "A그룹_예산및입찰가증액",
        "B그룹_입찰가강력상승",
        "C그룹_즉시제외키워드",
    ]
    df["Action_Group"] = np.select(conditions, choices, default="D그룹_판단유보")

    return df


# ═══════════════════════════════════════════════════════════════
#  5. 전체 파이프라인 실행
# ═══════════════════════════════════════════════════════════════
def analyze(
    df: pd.DataFrame,
    margin_rate: float = DEFAULT_MARGIN_RATE,
    min_clicks_star: int = MIN_CLICKS_STAR,
    min_clicks_stat: int = MIN_CLICKS_STAT,
    min_cost_negative: int = MIN_COST_NEGATIVE,
) -> pd.DataFrame:
    """파생 지표 계산 → 4분면 분류 → 결과 반환"""
    df = compute_derived_metrics(df, margin_rate)
    df = classify_keywords(df, margin_rate, min_clicks_star, min_clicks_stat, min_cost_negative)
    return df


# ═══════════════════════════════════════════════════════════════
#  6. 데이터 소스 변환 유틸 (네이버 SA / 쿠팡 → 표준)
# ═══════════════════════════════════════════════════════════════
def normalize_naver_sa(df: pd.DataFrame) -> pd.DataFrame:
    """네이버 SA DataFrame을 표준 컬럼으로 변환"""
    df = df.rename(columns=NAVER_SA_MAP)
    # 네이버SA에는 '키워드' 컬럼이 없을 수 있으므로 캠페인 단위로 처리
    if "키워드" not in df.columns:
        df["키워드"] = df.get("캠페인명", "알수없음")
    if "광고그룹명" not in df.columns:
        df["광고그룹명"] = "-"
    return df


def normalize_coupang_kw(df: pd.DataFrame) -> pd.DataFrame:
    """쿠팡 키워드 DataFrame을 표준 컬럼으로 변환"""
    df = df.rename(columns=COUPANG_KW_MAP)
    # 쿠팡은 VAT 별도이므로 총비용에 1.1 곱하기
    if "총비용" in df.columns:
        df["총비용"] = df["총비용"] * 1.1
    if "광고그룹명" not in df.columns:
        df["광고그룹명"] = "-"
    return df


# ═══════════════════════════════════════════════════════════════
#  7. 그룹별 요약 통계
# ═══════════════════════════════════════════════════════════════
def group_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Action_Group별 주요 지표 요약"""
    return df.groupby("Action_Group", as_index=False).agg(
        키워드수=("키워드", "count"),
        총광고비=("총비용", "sum"),
        총전환매출=("총전환매출액", "sum"),
        총순이익=("Estimated_Profit", "sum"),
        평균ROAS=("ROAS(%)", "mean"),
        평균CVR=("CVR(%)", "mean"),
        평균CPC=("CPC", "mean"),
    ).sort_values("Action_Group")


# ═══════════════════════════════════════════════════════════════
#  8. CPC × CTR 매트릭스 (쿠팡/네이버 공통)
# ═══════════════════════════════════════════════════════════════
def analyze_cpc_ctr_matrix(df: pd.DataFrame, min_clicks: int = 5) -> pd.DataFrame:
    """
    CPC와 CTR의 상관관계로 4분면 분류

    고CTR+저CPC (노다지) → 예산 우선 배정
    고CTR+고CPC (경쟁격전) → 전환율 확보 집중
    저CTR+저CPC (무관심) → 소재 교체 또는 제외
    저CTR+고CPC (돈낭비) → 즉시 중단
    """
    df = df.copy()
    clicks = df.get("클릭수", pd.Series(0, index=df.index))
    filtered = df[clicks >= min_clicks].copy()
    if filtered.empty:
        return pd.DataFrame()

    cpc = filtered.get("CPC", pd.Series(0, index=filtered.index))
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
#  9. 요일별 효율 분석 (쿠팡 키워드 일별 데이터)
# ═══════════════════════════════════════════════════════════════
def analyze_day_of_week(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    쿠팡 키워드 일별 데이터에서 요일별 효율 패턴 추출

    Returns: 요일별 평균 클릭수, 광고비, ROAS, CTR
    """
    if daily_df.empty or "날짜" not in daily_df.columns:
        return pd.DataFrame()

    df = daily_df.copy()
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    df = df.dropna(subset=["날짜"])
    if df.empty:
        return pd.DataFrame()

    df["요일번호"] = df["날짜"].dt.dayofweek

    day_counts = df.groupby("요일번호")["날짜"].apply(lambda x: x.dt.date.nunique()).reset_index()
    day_counts.columns = ["요일번호", "일수"]

    agg_cols = {}
    for col in ["클릭수", "광고비", "노출수", "총 전환매출액(14일)", "총 판매수량(14일)"]:
        if col in df.columns:
            agg_cols[col] = (col, "sum")

    if not agg_cols:
        return pd.DataFrame()

    daily_agg = df.groupby("요일번호", as_index=False).agg(**agg_cols)
    daily_agg = daily_agg.merge(day_counts, on="요일번호")

    for col in agg_cols:
        daily_agg[f"일평균_{col}"] = (daily_agg[col] / daily_agg["일수"]).round(0)

    if "광고비" in daily_agg.columns and "총 전환매출액(14일)" in daily_agg.columns:
        cost_vat = daily_agg["광고비"] * 1.1
        daily_agg["ROAS(%)"] = np.where(
            cost_vat > 0,
            (daily_agg["총 전환매출액(14일)"] / cost_vat * 100).round(0),
            0,
        )

    if "노출수" in daily_agg.columns and "클릭수" in daily_agg.columns:
        daily_agg["CTR(%)"] = np.where(
            daily_agg["노출수"] > 0,
            (daily_agg["클릭수"] / daily_agg["노출수"] * 100).round(2),
            0,
        )

    dow_map = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
    daily_agg["요일"] = daily_agg["요일번호"].map(dow_map)
    daily_agg = daily_agg.sort_values("요일번호")

    if "ROAS(%)" in daily_agg.columns:
        roas_avg = daily_agg["ROAS(%)"].mean()
        daily_agg["효율등급"] = np.select(
            [daily_agg["ROAS(%)"] >= roas_avg * 1.2, daily_agg["ROAS(%)"] <= roas_avg * 0.8],
            ["🟢 고효율", "🔴 저효율"],
            default="🟡 보통",
        )

    return daily_agg


# ═══════════════════════════════════════════════════════════════
#  10. 직접/간접 전환 분석 (쿠팡 전용)
# ═══════════════════════════════════════════════════════════════
def analyze_direct_indirect(df: pd.DataFrame) -> pd.DataFrame:
    """
    쿠팡 키워드별 직접/간접 전환 비율 분석 (14일 기여)

    직접전환: 광고 클릭 후 바로 구매
    간접전환: 광고 클릭 후 나중에 구매 (14일 이내)

    간접전환 비율이 높은 키워드 = 브랜드 인지/검색 유도형
    → 1일 ROAS로만 판단하면 과소평가될 수 있음
    """
    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    # 키워드별 합산
    agg_cols = {"노출수": "sum", "클릭수": "sum", "광고비": "sum"}
    for col in ["직접 전환매출액(14일)", "간접 전환매출액(14일)",
                "총 전환매출액(14일)", "직접주문수(14일)", "간접 주문수(14일)",
                "직접 판매수량(14일)", "간접 판매수량(14일)",
                "총 전환매출액(1일)"]:
        if col in df.columns:
            agg_cols[col] = "sum"

    kw_agg = df.groupby("키워드", as_index=False).agg(agg_cols)

    # 직접/간접 비율
    direct_rev = kw_agg.get("직접 전환매출액(14일)", pd.Series(0, index=kw_agg.index))
    indirect_rev = kw_agg.get("간접 전환매출액(14일)", pd.Series(0, index=kw_agg.index))
    total_14d = kw_agg.get("총 전환매출액(14일)", pd.Series(0, index=kw_agg.index))
    total_1d = kw_agg.get("총 전환매출액(1일)", pd.Series(0, index=kw_agg.index))

    kw_agg["직접전환비율(%)"] = np.where(
        total_14d > 0, (direct_rev / total_14d * 100).round(1), 0
    )
    kw_agg["간접전환비율(%)"] = np.where(
        total_14d > 0, (indirect_rev / total_14d * 100).round(1), 0
    )

    # ROAS 비교 (1일 vs 14일)
    cost_vat = kw_agg["광고비"] * 1.1
    kw_agg["ROAS_1일(%)"] = np.where(
        cost_vat > 0, (total_1d / cost_vat * 100).round(0), 0
    )
    kw_agg["ROAS_14일(%)"] = np.where(
        cost_vat > 0, (total_14d / cost_vat * 100).round(0), 0
    )
    kw_agg["ROAS_상승폭(%)"] = (kw_agg["ROAS_14일(%)"] - kw_agg["ROAS_1일(%)"]).round(0)

    # 전환 유형 분류
    kw_agg["전환유형"] = np.select(
        [
            kw_agg["간접전환비율(%)"] >= 60,
            kw_agg["간접전환비율(%)"] >= 30,
            (kw_agg["직접전환비율(%)"] > 0) & (kw_agg["간접전환비율(%)"] < 30),
            total_14d == 0,
        ],
        [
            "🟣 간접전환 우세 (브랜드/인지형)",
            "🔵 혼합형 (직접+간접)",
            "🟢 직접전환 우세 (즉구매형)",
            "⚪ 전환없음",
        ],
        default="⚪ 전환없음",
    )

    return kw_agg


# ═══════════════════════════════════════════════════════════════
#  11. 노출 추이 분석 (쿠팡 키워드 일별)
# ═══════════════════════════════════════════════════════════════
def analyze_impression_trend(daily_df: pd.DataFrame) -> pd.DataFrame:
    """일별 노출수 추이 + 7일 이동평균 + 추이 판단"""
    if daily_df.empty or "날짜" not in daily_df.columns:
        return pd.DataFrame()

    df = daily_df.copy()
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    df = df.dropna(subset=["날짜"])

    agg_cols = {}
    for col in ["노출수", "클릭수", "광고비", "총 전환매출액(14일)"]:
        if col in df.columns:
            agg_cols[col] = (col, "sum")

    if "노출수" not in agg_cols:
        return pd.DataFrame()

    daily = df.groupby("날짜", as_index=False).agg(**agg_cols)
    daily = daily.sort_values("날짜")

    daily["노출수_MA7"] = daily["노출수"].rolling(7, min_periods=3).mean().round(0)

    if len(daily) >= 7:
        first_half = daily["노출수"].iloc[:len(daily)//2].mean()
        second_half = daily["노출수"].iloc[len(daily)//2:].mean()
        change_pct = ((second_half - first_half) / max(first_half, 1) * 100)

        if change_pct >= 10:
            daily["노출추이"] = "📈 노출 증가 중"
        elif change_pct <= -10:
            daily["노출추이"] = "📉 노출 감소 — 입찰가/품질 점검 필요"
        else:
            daily["노출추이"] = "➖ 노출 안정"
        daily["노출변화율(%)"] = round(change_pct, 1)
    else:
        daily["노출추이"] = "데이터 부족"
        daily["노출변화율(%)"] = 0

    return daily


# ═══════════════════════════════════════════════════════════════
#  12. CLI 실행 (독립 스크립트로 사용 시)
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import os

    # --- 설정 ---
    MARGIN_RATE = 0.30       # 마진율 30%
    INPUT_FILE = "ad_data_raw.csv"
    OUTPUT_DIR = "."

    # --- CSV 로드 ---
    if not os.path.exists(INPUT_FILE):
        print(f"[ERROR] '{INPUT_FILE}' 파일을 찾을 수 없습니다.")
        exit(1)

    raw = pd.read_csv(INPUT_FILE)
    print(f"[INFO] {len(raw)}행 로드 완료. 컬럼: {list(raw.columns)}")

    # --- 분석 실행 ---
    result = analyze(raw, margin_rate=MARGIN_RATE)

    # --- 요약 출력 ---
    summary = group_summary(result)
    print("\n" + "=" * 70)
    print("  키워드 매트릭스 4분면 분석 요약")
    print("=" * 70)
    for _, row in summary.iterrows():
        print(f"\n  [{row['Action_Group']}]")
        print(f"    키워드 수  : {row['키워드수']:,}개")
        print(f"    총 광고비  : {row['총광고비']:,.0f}원")
        print(f"    총 전환매출: {row['총전환매출']:,.0f}원")
        print(f"    총 순이익  : {row['총순이익']:,.0f}원")
        print(f"    평균 ROAS  : {row['평균ROAS']:.0f}%")
    print("=" * 70)

    # --- 그룹별 CSV 저장 ---
    group_a = result[result["Action_Group"] == "A그룹_예산및입찰가증액"]
    group_b = result[result["Action_Group"] == "B그룹_입찰가강력상승"]
    group_c = result[result["Action_Group"] == "C그룹_즉시제외키워드"]

    if not group_a.empty:
        path = os.path.join(OUTPUT_DIR, "Action_A_Increase_Bid.csv")
        group_a.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"[SAVED] A그룹 → {path} ({len(group_a)}건)")

    if not group_b.empty:
        path = os.path.join(OUTPUT_DIR, "Action_B_Boost_Traffic.csv")
        group_b.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"[SAVED] B그룹 → {path} ({len(group_b)}건)")

    if not group_c.empty:
        path = os.path.join(OUTPUT_DIR, "Action_C_Negative_Keywords.csv")
        group_c.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"[SAVED] C그룹 → {path} ({len(group_c)}건)")

    print("\n[DONE] 분석 완료!")

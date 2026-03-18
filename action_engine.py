# -*- coding: utf-8 -*-
"""NOW Action 엔진 — 캠페인별 꼼꼼한 액션 자동 생성
각 캠페인/광고그룹/키워드 단위로 구체적 액션을 도출
"""

import pandas as pd
import numpy as np


def fmt_money(v):
    if abs(v) >= 1e8:
        return f"{v/1e8:.1f}억"
    elif abs(v) >= 1e6:
        return f"{v/1e6:.0f}백만"
    elif abs(v) >= 1e4:
        return f"{v/1e4:.0f}만"
    return f"{v:,.0f}원"


def _pct(v):
    return f"{v:.0f}%" if pd.notna(v) else "-"


# ═══════════════════════════════════════════════════════════════
#  1. 캠페인 단위 액션 분석
# ═══════════════════════════════════════════════════════════════
def analyze_campaign_actions(df_keywords, campaign_col="캠페인", margin_rate=0.30):
    """
    키워드 분석 결과를 캠페인 단위로 집계하고
    캠페인별 구체적 액션을 생성한다.

    Parameters
    ----------
    df_keywords : DataFrame (ad_analyzer 또는 naver_ad_analyzer 결과)
        필수 컬럼: 캠페인, 키워드, 총비용, 전환매출, ROAS(%), 클릭수, 노출수, Action_Group
    campaign_col : str
        캠페인 컬럼명 (쿠팡: '캠페인명', 네이버: '캠페인')

    Returns
    -------
    list of dict: 캠페인별 액션 리스트
    """
    if df_keywords is None or df_keywords.empty:
        return []
    if campaign_col not in df_keywords.columns:
        return []

    actions = []

    # 캠페인별 집계
    for camp_name, camp_df in df_keywords.groupby(campaign_col):
        # 컬럼명 유연 대응
        cost_col = next((c for c in ["총비용", "광고비(VAT포함)", "광고비", "광고비(VAT)"] if c in camp_df.columns), None)
        rev_col = next((c for c in ["전환매출", "전환매출액", "총 전환매출액(14일)", "총 전환매출액(1일)"] if c in camp_df.columns), None)
        click_col = next((c for c in ["클릭수"] if c in camp_df.columns), None)
        imp_col = next((c for c in ["노출수"] if c in camp_df.columns), None)

        camp_action = {
            "campaign": camp_name,
            "keywords_total": len(camp_df),
            "cost": camp_df[cost_col].sum() if cost_col else 0,
            "revenue": camp_df[rev_col].sum() if rev_col else 0,
            "clicks": camp_df[click_col].sum() if click_col else 0,
            "impressions": camp_df[imp_col].sum() if imp_col else 0,
            "actions": [],
            "priority_score": 0,  # 높을수록 급함
            "verdict": "",  # 종합 판정
        }

        cost = camp_action["cost"]
        rev = camp_action["revenue"]
        roas = (rev / cost * 100) if cost > 0 else 0
        profit = (rev * margin_rate) - cost
        camp_action["roas"] = roas
        camp_action["profit"] = profit

        # ── 키워드 그룹별 분류 ──
        # Action_Group 값: "A", "B", "C", "D" 또는 "A그룹_xxx", "B그룹_xxx" 등
        grp_a = pd.DataFrame()
        grp_b = pd.DataFrame()
        grp_c = pd.DataFrame()
        n_a = n_b = n_c = n_d = 0
        if "Action_Group" in camp_df.columns:
            camp_df["_grp_letter"] = camp_df["Action_Group"].astype(str).str[0].str.upper()
            n_a = (camp_df["_grp_letter"] == "A").sum()
            n_b = (camp_df["_grp_letter"] == "B").sum()
            n_c = (camp_df["_grp_letter"] == "C").sum()
            n_d = (camp_df["_grp_letter"] == "D").sum()
            grp_a = camp_df[camp_df["_grp_letter"] == "A"]
            grp_b = camp_df[camp_df["_grp_letter"] == "B"]
            grp_c = camp_df[camp_df["_grp_letter"] == "C"]

        camp_action["group_counts"] = {"A": n_a, "B": n_b, "C": n_c, "D": n_d}

        # ── 액션 1: 예산 판정 ──
        if roas >= 500 and cost > 0:
            camp_action["actions"].append({
                "type": "budget_increase",
                "icon": "🟢",
                "label": "예산 증액 추천",
                "detail": f"ROAS {roas:.0f}% 고효율 캠페인. 예산 30~50% 증액 시 추가매출 {fmt_money(cost * 0.3 * roas / 100)} 기대",
                "urgency": "high",
            })
            camp_action["priority_score"] += 30
        elif roas >= 300:
            camp_action["actions"].append({
                "type": "budget_maintain",
                "icon": "🔵",
                "label": "예산 유지 + 최적화",
                "detail": f"ROAS {roas:.0f}% 양호. 현재 예산 유지하되 C그룹 키워드 정리로 효율 개선",
                "urgency": "medium",
            })
            camp_action["priority_score"] += 15
        elif roas >= 100 and cost > 0:
            camp_action["actions"].append({
                "type": "budget_optimize",
                "icon": "🟡",
                "label": "예산 재조정 필요",
                "detail": f"ROAS {roas:.0f}% 손익분기 수준. 비효율 키워드 제거 후 재평가",
                "urgency": "medium",
            })
            camp_action["priority_score"] += 10
        elif cost > 0:
            camp_action["actions"].append({
                "type": "budget_decrease",
                "icon": "🔴",
                "label": "예산 감액 또는 중단",
                "detail": f"ROAS {roas:.0f}% 적자 캠페인. 손실 {fmt_money(abs(profit))}. 즉시 예산 50% 감액 또는 일시 중단 검토",
                "urgency": "critical",
            })
            camp_action["priority_score"] += 40

        # ── 액션 2: C그룹 키워드 제외 ──
        if n_c > 0 and not grp_c.empty:
            c_cost = grp_c[cost_col].sum() if cost_col and cost_col in grp_c.columns else 0
            sort_col_c = cost_col if cost_col and cost_col in grp_c.columns else grp_c.select_dtypes(include="number").columns[0] if len(grp_c.select_dtypes(include="number").columns) > 0 else None
            c_keywords = grp_c.nlargest(5, sort_col_c)["키워드"].tolist() if sort_col_c and "키워드" in grp_c.columns else []
            camp_action["actions"].append({
                "type": "keyword_exclude",
                "icon": "✂️",
                "label": f"낭비 키워드 {n_c}개 제외",
                "detail": f"전환 없이 광고비 {fmt_money(c_cost)} 소진 중. "
                          f"제외 대상: {', '.join(c_keywords[:5])}",
                "urgency": "high",
                "keywords": c_keywords,
            })
            camp_action["priority_score"] += 20

        # ── 액션 3: A그룹 입찰가 증액 ──
        if n_a > 0 and not grp_a.empty:
            sort_col_a = rev_col if rev_col and rev_col in grp_a.columns else ("ROAS(%)" if "ROAS(%)" in grp_a.columns else None)
            a_top = grp_a.nlargest(5, sort_col_a) if sort_col_a else grp_a.head(5)
            a_keywords = a_top["키워드"].tolist() if "키워드" in a_top.columns else []
            a_rev = grp_a[rev_col].sum() if rev_col and rev_col in grp_a.columns else 0
            camp_action["actions"].append({
                "type": "keyword_boost",
                "icon": "⬆️",
                "label": f"효자 키워드 {n_a}개 입찰가 상승",
                "detail": f"전환매출 {fmt_money(a_rev)} 생성 중. 입찰가 10~20% 상승으로 노출 확대. "
                          f"TOP: {', '.join(a_keywords[:5])}",
                "urgency": "medium",
                "keywords": a_keywords,
            })

        # ── 액션 4: B그룹 → 별도 캠페인 분리 검토 ──
        if n_b >= 5:
            b_keywords = grp_b.nlargest(5, "ROAS(%)")["키워드"].tolist() if (not grp_b.empty and "ROAS(%)" in grp_b.columns and "키워드" in grp_b.columns) else []
            camp_action["actions"].append({
                "type": "campaign_split",
                "icon": "🔀",
                "label": f"잠재 키워드 {n_b}개 캠페인 분리 검토",
                "detail": f"ROAS는 좋지만 트래픽 부족한 키워드 {n_b}개. "
                          f"별도 캠페인으로 분리 후 집중 입찰 추천. 후보: {', '.join(b_keywords[:5])}",
                "urgency": "low",
                "keywords": b_keywords,
            })

        # ── 액션 5: CTR 낮은 캠페인 → 소재 개선 ──
        if camp_action["impressions"] > 0:
            ctr = camp_action["clicks"] / camp_action["impressions"] * 100
            if ctr < 1.0 and camp_action["impressions"] > 1000:
                camp_action["actions"].append({
                    "type": "creative_improve",
                    "icon": "✏️",
                    "label": f"CTR {ctr:.2f}% — 광고 소재 개선 필요",
                    "detail": f"노출 {camp_action['impressions']:,}회 대비 클릭률 매우 낮음. 광고 제목/설명문 A/B 테스트 권장",
                    "urgency": "medium",
                })

        # ── 액션 6: 키워드 전부 D그룹(데이터부족) ──
        if n_d == len(camp_df) and len(camp_df) > 0:
            camp_action["actions"].append({
                "type": "data_insufficient",
                "icon": "⏳",
                "label": "데이터 부족 — 2주 관찰 필요",
                "detail": f"전체 {len(camp_df)}개 키워드 모두 판단 보류 상태. 최소 2주 데이터 수집 후 재평가",
                "urgency": "low",
            })

        # ── 종합 판정 ──
        if roas >= 500 and n_c == 0:
            camp_action["verdict"] = "🟢 최고 효율 — 스케일업"
        elif roas >= 500 and n_c > 0:
            camp_action["verdict"] = "🟢 고효율 — C키워드 정리 후 증액"
        elif roas >= 300:
            camp_action["verdict"] = "🔵 양호 — 키워드 최적화 진행"
        elif roas >= 100:
            camp_action["verdict"] = "🟡 손익분기 — 구조조정 필요"
        elif cost > 0:
            camp_action["verdict"] = "🔴 적자 — 감액/중단 검토"
        else:
            camp_action["verdict"] = "⚪ 미집행"

        actions.append(camp_action)

    # 우선순위 점수 높은 순 정렬
    actions.sort(key=lambda x: x["priority_score"], reverse=True)
    return actions


# ═══════════════════════════════════════════════════════════════
#  2. 스토어 × 광고 교차 분석
# ═══════════════════════════════════════════════════════════════
def analyze_keyword_gap(df_ad_keywords, df_store_keywords,
                        ad_kw_col="키워드", store_kw_col="키워드",
                        ad_cost_col="총비용", ad_rev_col="전환매출",
                        store_rev_col="결제금액(과거 14일간 기여도추정)"):
    """
    광고 키워드 vs 스토어 구매 키워드 갭 분석

    Returns
    -------
    dict with keys: waste_keywords, opportunity_keywords, gap_summary
    """
    result = {"waste": [], "opportunity": [], "summary": {}}

    if df_ad_keywords is None or df_ad_keywords.empty:
        return result
    if df_store_keywords is None or df_store_keywords.empty:
        return result

    # 광고 키워드 집합
    ad_kws = set(df_ad_keywords[ad_kw_col].str.strip().str.lower().unique())
    # 스토어 구매 키워드 집합
    store_kws = set(df_store_keywords[store_kw_col].str.strip().str.lower().unique())

    # 광고O + 구매X = 예산 낭비 가능성
    ad_only = ad_kws - store_kws
    # 광고X + 구매O = 광고 확대 기회
    store_only = store_kws - ad_kws
    # 교집합
    both = ad_kws & store_kws

    # 낭비 키워드 (광고비 쓰는데 스토어에서 결제 없음)
    if ad_only:
        waste_df = df_ad_keywords[
            df_ad_keywords[ad_kw_col].str.strip().str.lower().isin(ad_only)
        ].copy()
        if ad_cost_col in waste_df.columns:
            waste_df = waste_df.sort_values(ad_cost_col, ascending=False)
        result["waste"] = waste_df.head(20).to_dict("records")

    # 기회 키워드 (광고 안 하는데 스토어에서 결제 발생)
    if store_only:
        opp_df = df_store_keywords[
            df_store_keywords[store_kw_col].str.strip().str.lower().isin(store_only)
        ].copy()
        if store_rev_col in opp_df.columns:
            opp_df = opp_df.sort_values(store_rev_col, ascending=False)
        result["opportunity"] = opp_df.head(20).to_dict("records")

    result["summary"] = {
        "ad_only_count": len(ad_only),
        "store_only_count": len(store_only),
        "both_count": len(both),
        "total_ad": len(ad_kws),
        "total_store": len(store_kws),
    }

    return result


def analyze_roas_comparison(df_ad_keywords, df_store_keywords,
                            ad_kw_col="키워드", store_kw_col="키워드",
                            ad_cost_col="총비용", ad_rev_col="전환매출",
                            store_rev_col="결제금액(과거 14일간 기여도추정)"):
    """
    광고 ROAS vs 스토어 실제 ROAS 비교

    Returns
    -------
    DataFrame with 키워드, 광고ROAS, 스토어ROAS, 차이
    """
    if df_ad_keywords is None or df_store_keywords is None:
        return pd.DataFrame()
    if df_ad_keywords.empty or df_store_keywords.empty:
        return pd.DataFrame()

    # 광고 키워드별 집계
    ad_agg = df_ad_keywords.groupby(ad_kw_col).agg(
        광고비=(ad_cost_col, "sum"),
        광고전환매출=(ad_rev_col, "sum"),
    ).reset_index()
    ad_agg.columns = ["키워드", "광고비", "광고전환매출"]
    ad_agg["광고ROAS(%)"] = (ad_agg["광고전환매출"] / ad_agg["광고비"].replace(0, 1) * 100).round(0)

    # 스토어 키워드별 집계
    store_agg = df_store_keywords.groupby(store_kw_col).agg(
        스토어결제금액=(store_rev_col, "sum"),
    ).reset_index()
    store_agg.columns = ["키워드", "스토어결제금액"]

    # 키워드 이름 정규화
    ad_agg["키워드_norm"] = ad_agg["키워드"].str.strip().str.lower()
    store_agg["키워드_norm"] = store_agg["키워드"].str.strip().str.lower()

    # 조인
    merged = ad_agg.merge(store_agg, on="키워드_norm", how="inner", suffixes=("", "_store"))
    if merged.empty:
        return pd.DataFrame()

    merged["스토어ROAS(%)"] = (merged["스토어결제금액"] / merged["광고비"].replace(0, 1) * 100).round(0)
    merged["ROAS차이(%p)"] = merged["스토어ROAS(%)"] - merged["광고ROAS(%)"]
    merged["판정"] = merged["ROAS차이(%p)"].apply(
        lambda x: "🔺 광고 과소평가" if x > 100 else ("🔻 광고 과대평가" if x < -100 else "≈ 유사")
    )

    return merged[["키워드", "광고비", "광고ROAS(%)", "스토어ROAS(%)", "ROAS차이(%p)", "판정"]].sort_values(
        "ROAS차이(%p)", key=abs, ascending=False
    )


def analyze_channel_efficiency(df_channel, df_ad_summary=None):
    """
    채널별 유입 효율 × 실제 전환 교차 분석

    Returns
    -------
    DataFrame with 채널, 유입수, 결제율, ROAS, 등급
    """
    if df_channel is None or df_channel.empty:
        return pd.DataFrame()

    # 채널별 집계
    needed_cols = ["유입수", "결제수(마지막클릭)", "결제금액(마지막클릭)", "광고비"]
    for col in needed_cols:
        if col not in df_channel.columns:
            return pd.DataFrame()

    ch_agg = df_channel.groupby("채널").agg(
        유입수=("유입수", "sum"),
        결제수=("결제수(마지막클릭)", "sum"),
        결제금액=("결제금액(마지막클릭)", "sum"),
        광고비=("광고비", "sum"),
    ).reset_index()

    ch_agg["결제율(%)"] = (ch_agg["결제수"] / ch_agg["유입수"].replace(0, 1) * 100).round(2)
    ch_agg["유입당결제금액"] = (ch_agg["결제금액"] / ch_agg["유입수"].replace(0, 1)).round(0)
    ch_agg["ROAS(%)"] = (ch_agg["결제금액"] / ch_agg["광고비"].replace(0, 1) * 100).round(0)

    def _grade(row):
        if row["ROAS(%)"] >= 500 and row["결제율(%)"] >= 2:
            return "🟢 최고효율"
        elif row["ROAS(%)"] >= 300:
            return "🔵 양호"
        elif row["ROAS(%)"] >= 100:
            return "🟡 보통"
        elif row["광고비"] > 0:
            return "🔴 비효율"
        else:
            return "⚪ 무광고"

    ch_agg["등급"] = ch_agg.apply(_grade, axis=1)
    return ch_agg.sort_values("결제금액", ascending=False)


# ═══════════════════════════════════════════════════════════════
#  3. 기존 호환 — 전체 요약 액션 (통합 탭용)
# ═══════════════════════════════════════════════════════════════
def generate_actions(
    target: int,
    current_sales: float,
    remaining_days: int,
    daily_avg: float,
    needed_daily: float,
    grp_a: pd.DataFrame = None,
    grp_b: pd.DataFrame = None,
    grp_c: pd.DataFrame = None,
    grp_d: pd.DataFrame = None,
    margin_rate: float = 0.30,
    channel_matrix: pd.DataFrame = None,
    ad_opportunities: pd.DataFrame = None,
    search_roas: float = None,
    nonsearch_roas: float = None,
):
    """기존 통합 액션 리스트 생성 (하위 호환)"""
    actions = []
    priority = 0

    gap = target - current_sales

    if gap > 0 and remaining_days > 0:
        priority += 1
        shortfall = needed_daily - daily_avg
        actions.append({
            "priority": priority, "category": "목표 달성", "icon": "🎯",
            "action": f"일평균 매출을 **{fmt_money(daily_avg)}** → **{fmt_money(needed_daily)}**으로 "
                      f"**{fmt_money(shortfall)}** 올려야 10억 달성 (남은 {remaining_days}일)",
            "impact": gap, "impact_text": f"갭: {fmt_money(gap)}",
        })

    if grp_c is not None and not grp_c.empty:
        c_waste = grp_c["총비용"].sum()
        priority += 1
        actions.append({
            "priority": priority, "category": "광고 절감", "icon": "🔴",
            "action": f"**C그룹 {len(grp_c)}개 키워드 즉시 제외** — 낭비 광고비 **{fmt_money(c_waste)}** 절감",
            "impact": c_waste, "impact_text": f"절감: {fmt_money(c_waste)}",
        })

    if grp_c is not None and not grp_c.empty and grp_a is not None and not grp_a.empty:
        c_waste = grp_c["총비용"].sum()
        a_avg_roas = grp_a["ROAS(%)"].mean()
        potential_rev = c_waste * (a_avg_roas / 100)
        priority += 1
        actions.append({
            "priority": priority, "category": "예산 재배분", "icon": "💰",
            "action": f"C그룹 광고비 **{fmt_money(c_waste)}**을 A그룹에 재배분 → 추가매출 **{fmt_money(potential_rev)}**",
            "impact": potential_rev, "impact_text": f"추가매출: {fmt_money(potential_rev)}",
        })

    if grp_a is not None and not grp_a.empty:
        a_profit = grp_a["Estimated_Profit"].sum() if "Estimated_Profit" in grp_a.columns else 0
        top_kw = grp_a.nlargest(3, "전환매출" if "전환매출" in grp_a.columns else "ROAS(%)")["키워드"].tolist()
        priority += 1
        actions.append({
            "priority": priority, "category": "키워드 증액", "icon": "🟢",
            "action": f"**A그룹 효자 키워드 {len(grp_a)}개** 입찰가 & 예산 증액 — TOP: **{', '.join(top_kw[:3])}**",
            "impact": a_profit, "impact_text": f"현재 순이익: {fmt_money(a_profit)}",
        })

    if grp_b is not None and not grp_b.empty:
        b_top = grp_b.nlargest(3, "ROAS(%)")["키워드"].tolist()
        priority += 1
        actions.append({
            "priority": priority, "category": "트래픽 확보", "icon": "🔵",
            "action": f"**B그룹 {len(grp_b)}개 잠재 키워드** 입찰가 강력 상승 — TOP: **{', '.join(b_top[:3])}**",
            "impact": 0, "impact_text": "노출 확대 필요",
        })

    if channel_matrix is not None and not channel_matrix.empty:
        if "성장률(%)" in channel_matrix.columns:
            growing = channel_matrix[channel_matrix["성장률(%)"] > 20].sort_values("최근2주 매출", ascending=False)
            if not growing.empty:
                top = growing.iloc[0]
                priority += 1
                actions.append({
                    "priority": priority, "category": "채널 투자", "icon": "📈",
                    "action": f"**{top['채널']}** 채널 {top['성장률(%)']:.0f}% 성장 중 → 집중 투자",
                    "impact": top["최근2주 매출"], "impact_text": f"최근2주: {fmt_money(top['최근2주 매출'])}",
                })

    if search_roas is not None and nonsearch_roas is not None:
        if search_roas > nonsearch_roas * 1.5 and nonsearch_roas < 100:
            priority += 1
            actions.append({
                "priority": priority, "category": "쿠팡 최적화", "icon": "🔍",
                "action": f"쿠팡 검색 ROAS **{search_roas:.0f}%** >> 비검색 **{nonsearch_roas:.0f}%** → 검색 예산 확대",
                "impact": 0, "impact_text": f"ROAS 갭: {search_roas - nonsearch_roas:.0f}%p",
            })

    return sorted(actions, key=lambda x: x["priority"])

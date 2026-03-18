# -*- coding: utf-8 -*-
"""NOW Action 엔진 — 10억 달성을 위한 우선순위 액션 자동 생성"""

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


def generate_actions(
    target: int,
    current_sales: float,
    remaining_days: int,
    daily_avg: float,
    needed_daily: float,
    # 광고 분석 결과 (ad_analyzer 결과)
    grp_a: pd.DataFrame = None,  # 효자 키워드
    grp_b: pd.DataFrame = None,  # 잠재력 키워드
    grp_c: pd.DataFrame = None,  # 제외 키워드
    grp_d: pd.DataFrame = None,  # 판단유보
    margin_rate: float = 0.30,
    # 채널 매트릭스
    channel_matrix: pd.DataFrame = None,
    # 광고 요약
    ad_opportunities: pd.DataFrame = None,
    # 쿠팡 검색/비검색
    search_roas: float = None,
    nonsearch_roas: float = None,
):
    """
    모든 데이터를 종합하여 우선순위 액션 리스트 생성.
    Returns list of dicts: [{priority, category, action, impact, icon}, ...]
    """
    actions = []
    priority = 0

    gap = target - current_sales

    # ── 1. 목표 갭 분석 ──────────────────────────────────────
    if gap > 0 and remaining_days > 0:
        priority += 1
        shortfall = needed_daily - daily_avg
        actions.append({
            "priority": priority,
            "category": "목표 달성",
            "icon": "🎯",
            "action": f"일평균 매출을 **{fmt_money(daily_avg)}** → **{fmt_money(needed_daily)}**으로 "
                      f"**{fmt_money(shortfall)}** 올려야 10억 달성 (남은 {remaining_days}일)",
            "impact": gap,
            "impact_text": f"갭: {fmt_money(gap)}",
        })

    # ── 2. C그룹 제외 (즉시 절감) ────────────────────────────
    if grp_c is not None and not grp_c.empty:
        c_waste = grp_c["총비용"].sum()
        c_count = len(grp_c)
        priority += 1
        actions.append({
            "priority": priority,
            "category": "광고 절감",
            "icon": "🔴",
            "action": f"**C그룹 {c_count}개 키워드 즉시 제외** — 낭비 광고비 **{fmt_money(c_waste)}** 절감",
            "impact": c_waste,
            "impact_text": f"절감: {fmt_money(c_waste)}",
        })

    # ── 3. C→A 재배분 (매출 극대화) ────────────────────────
    if (grp_c is not None and not grp_c.empty and
        grp_a is not None and not grp_a.empty):
        c_waste = grp_c["총비용"].sum()
        a_avg_roas = grp_a["ROAS(%)"].mean()
        potential_rev = c_waste * (a_avg_roas / 100)
        potential_profit = (potential_rev * margin_rate) - c_waste
        priority += 1
        actions.append({
            "priority": priority,
            "category": "예산 재배분",
            "icon": "💰",
            "action": f"C그룹 광고비 **{fmt_money(c_waste)}**을 A그룹에 재배분 → "
                      f"추가매출 **{fmt_money(potential_rev)}**, 순이익 **{fmt_money(potential_profit)}**",
            "impact": potential_rev,
            "impact_text": f"추가매출: {fmt_money(potential_rev)}",
        })

    # ── 4. A그룹 스케일업 ──────────────────────────────────
    if grp_a is not None and not grp_a.empty:
        a_profit = grp_a["Estimated_Profit"].sum()
        top_kw = grp_a.nlargest(3, "Estimated_Profit")["키워드"].tolist()
        priority += 1
        actions.append({
            "priority": priority,
            "category": "키워드 증액",
            "icon": "🟢",
            "action": f"**A그룹 효자 키워드 {len(grp_a)}개** 입찰가 & 예산 증액 — "
                      f"TOP: **{', '.join(top_kw[:3])}** (현재 순이익 {fmt_money(a_profit)})",
            "impact": a_profit,
            "impact_text": f"현재 순이익: {fmt_money(a_profit)}",
        })

    # ── 5. B그룹 트래픽 확보 ──────────────────────────────
    if grp_b is not None and not grp_b.empty:
        b_top = grp_b.nlargest(3, "ROAS(%)")["키워드"].tolist()
        priority += 1
        actions.append({
            "priority": priority,
            "category": "트래픽 확보",
            "icon": "🔵",
            "action": f"**B그룹 {len(grp_b)}개 잠재 키워드** 입찰가 강력 상승 — "
                      f"ROAS 좋지만 노출 부족. TOP: **{', '.join(b_top[:3])}**",
            "impact": 0,
            "impact_text": "노출 확대 필요",
        })

    # ── 6. 채널 성장/하락 경보 ────────────────────────────
    if channel_matrix is not None and not channel_matrix.empty:
        growing = channel_matrix[channel_matrix["성장률(%)"] > 20].sort_values("최근2주 매출", ascending=False)
        if not growing.empty:
            top = growing.iloc[0]
            priority += 1
            actions.append({
                "priority": priority,
                "category": "채널 투자",
                "icon": "📈",
                "action": f"**{top['채널']}** 채널 {top['성장률(%)']:.0f}% 성장 중 → 이 채널에 집중 투자",
                "impact": top["최근2주 매출"],
                "impact_text": f"최근2주: {fmt_money(top['최근2주 매출'])}",
            })

        declining = channel_matrix[channel_matrix["성장률(%)"] < -20].sort_values("최근2주 매출", ascending=False)
        if not declining.empty:
            top_dec = declining.iloc[0]
            priority += 1
            actions.append({
                "priority": priority,
                "category": "채널 경고",
                "icon": "📉",
                "action": f"**{top_dec['채널']}** 채널 매출 **{top_dec['성장률(%)']:.0f}%** 하락 → 원인 파악 & 대응 시급",
                "impact": abs(top_dec["최근2주 매출"] - top_dec.get("이전2주 매출", 0)),
                "impact_text": f"하락폭 확인 필요",
            })

    # ── 7. 검색/비검색 최적화 ────────────────────────────
    if search_roas is not None and nonsearch_roas is not None:
        if search_roas > nonsearch_roas * 1.5 and nonsearch_roas < 100:
            priority += 1
            actions.append({
                "priority": priority,
                "category": "쿠팡 최적화",
                "icon": "🔍",
                "action": f"쿠팡 검색 ROAS **{search_roas:.0f}%** >> 비검색 **{nonsearch_roas:.0f}%** → "
                          f"목표 광고 수익률 낮춰 검색 영역 예산 확대",
                "impact": 0,
                "impact_text": f"ROAS 갭: {search_roas - nonsearch_roas:.0f}%p",
            })

    # ── 8. 고효율 캠페인 스케일업 ────────────────────────
    if ad_opportunities is not None and not ad_opportunities.empty:
        high_roas = ad_opportunities[ad_opportunities["ROAS(%)"] >= 500]
        if not high_roas.empty:
            priority += 1
            actions.append({
                "priority": priority,
                "category": "캠페인 증액",
                "icon": "🚀",
                "action": f"ROAS 500%+ 캠페인 **{len(high_roas)}개** 발견 → 예산 증액으로 매출 극대화 가능",
                "impact": high_roas["광고비"].sum(),
                "impact_text": f"현재 광고비: {fmt_money(high_roas['광고비'].sum())}",
            })

    return sorted(actions, key=lambda x: x["priority"])

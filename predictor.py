# -*- coding: utf-8 -*-
"""미래예측 엔진 — 매출/광고 예측 및 시뮬레이션 로직"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
import calendar


def month_end_scenarios(df_sales: pd.DataFrame, target: int, sel_year: int, sel_month: int):
    """
    다중 시나리오 월말 매출 예측.
    Returns dict with keys: base, optimistic, pessimistic, weekend_adj, gap, needed_daily, etc.
    """
    today = date.today()
    days_in_month = calendar.monthrange(sel_year, sel_month)[1]

    df_m = df_sales[
        (df_sales["주문일시"].dt.year == sel_year) &
        (df_sales["주문일시"].dt.month == sel_month)
    ]
    if df_m.empty:
        return None

    daily = df_m.groupby(df_m["주문일시"].dt.date)["총 판매금액"].sum()

    is_current = (sel_year == today.year and sel_month == today.month)
    elapsed = today.day if is_current else days_in_month
    remaining = days_in_month - elapsed if is_current else 0
    current_sales = daily.sum()

    # 기본: 전체 일평균
    avg_all = current_sales / max(elapsed, 1)
    proj_base = current_sales + (avg_all * remaining) if is_current else current_sales

    # 낙관: 최근 7일 평균 (또는 최고 7일 롤링)
    recent_7 = daily.tail(7)
    avg_opt = recent_7.mean() if len(recent_7) > 0 else avg_all
    proj_optimistic = current_sales + (avg_opt * remaining) if is_current else current_sales

    # 비관: 최저 7일 롤링 평균
    if len(daily) >= 7:
        rolling_7 = daily.rolling(7).mean().dropna()
        avg_pess = rolling_7.min() if len(rolling_7) > 0 else avg_all
    else:
        avg_pess = daily.min() if len(daily) > 0 else 0
    proj_pessimistic = current_sales + (avg_pess * remaining) if is_current else current_sales

    # 주말/주중 보정
    weekday_sales = []
    weekend_sales = []
    for d, v in daily.items():
        if d.weekday() < 5:
            weekday_sales.append(v)
        else:
            weekend_sales.append(v)
    avg_weekday = np.mean(weekday_sales) if weekday_sales else avg_all
    avg_weekend = np.mean(weekend_sales) if weekend_sales else avg_all

    # 남은 날의 주중/주말 카운트
    remaining_weekday = 0
    remaining_weekend = 0
    if is_current:
        for d in range(elapsed + 1, days_in_month + 1):
            dt = date(sel_year, sel_month, d)
            if dt.weekday() < 5:
                remaining_weekday += 1
            else:
                remaining_weekend += 1
    proj_weekend_adj = current_sales + (avg_weekday * remaining_weekday) + (avg_weekend * remaining_weekend)

    gap = target - current_sales
    needed_daily = gap / max(remaining, 1) if remaining > 0 else 0

    return {
        "current_sales": current_sales,
        "elapsed": elapsed,
        "remaining": remaining,
        "days_in_month": days_in_month,
        "avg_daily": avg_all,
        "proj_base": proj_base,
        "proj_optimistic": proj_optimistic,
        "proj_pessimistic": proj_pessimistic,
        "proj_weekend_adj": proj_weekend_adj,
        "gap": gap,
        "needed_daily": needed_daily,
        "daily_series": daily,
        "avg_weekday": avg_weekday,
        "avg_weekend": avg_weekend,
    }


def channel_contribution_forecast(df_sales: pd.DataFrame, target: int,
                                   sel_year: int, sel_month: int):
    """
    채널별 기여도 예측 — 각 채널이 10억 중 얼마 기여할지.
    최근 2주 일평균 기반으로 월말 예상 기여도 계산.
    """
    today = date.today()
    days_in_month = calendar.monthrange(sel_year, sel_month)[1]
    is_current = (sel_year == today.year and sel_month == today.month)

    df_m = df_sales[
        (df_sales["주문일시"].dt.year == sel_year) &
        (df_sales["주문일시"].dt.month == sel_month)
    ]
    if df_m.empty:
        return pd.DataFrame()

    elapsed = today.day if is_current else days_in_month
    remaining = days_in_month - elapsed if is_current else 0

    ch = df_m.groupby("외부몰/벤더명")["총 판매금액"].sum().reset_index()
    ch.columns = ["채널", "현재매출"]

    # 최근 7일 일평균
    cutoff = today - timedelta(days=7) if is_current else date(sel_year, sel_month, days_in_month) - timedelta(days=7)
    recent = df_m[df_m["주문일시"].dt.date > cutoff]
    recent_days = max((today - cutoff).days, 1) if is_current else 7
    ch_recent = recent.groupby("외부몰/벤더명")["총 판매금액"].sum().reset_index()
    ch_recent.columns = ["채널", "최근7일매출"]
    ch_recent["최근일평균"] = ch_recent["최근7일매출"] / recent_days

    ch = ch.merge(ch_recent[["채널", "최근일평균"]], on="채널", how="left").fillna(0)
    ch["월말예상"] = ch["현재매출"] + (ch["최근일평균"] * remaining)
    ch["기여율(%)"] = (ch["월말예상"] / max(ch["월말예상"].sum(), 1) * 100).round(1)
    ch["목표기여율(%)"] = (ch["월말예상"] / target * 100).round(1)
    ch = ch.sort_values("월말예상", ascending=False)

    return ch


def momentum_indicator(df_sales: pd.DataFrame, sel_year: int, sel_month: int):
    """
    모멘텀 지표 — 이번 주 vs 지난 주 일평균 비교.
    가속/감속/유지 판단.
    """
    df_m = df_sales[
        (df_sales["주문일시"].dt.year == sel_year) &
        (df_sales["주문일시"].dt.month == sel_month)
    ]
    if df_m.empty:
        return None

    daily = df_m.groupby(df_m["주문일시"].dt.date)["총 판매금액"].sum().sort_index()
    if len(daily) < 8:
        return {"status": "데이터 부족", "this_week_avg": 0, "last_week_avg": 0, "change_pct": 0, "daily": daily}

    this_week = daily.tail(7)
    last_week = daily.iloc[-14:-7] if len(daily) >= 14 else daily.iloc[:7]

    tw_avg = this_week.mean()
    lw_avg = last_week.mean()
    change = ((tw_avg - lw_avg) / max(lw_avg, 1)) * 100

    if change > 10:
        status = "가속 📈"
    elif change < -10:
        status = "감속 📉"
    else:
        status = "유지 ➡️"

    return {
        "status": status,
        "this_week_avg": tw_avg,
        "last_week_avg": lw_avg,
        "change_pct": change,
        "daily": daily,
    }


def ad_budget_simulator(ad_summary: list, margin_rate: float = 0.30):
    """
    광고 예산 시뮬레이터 — 각 플랫폼의 예산 변경 시 추가 매출/순이익 계산.

    ad_summary: list of dicts with keys: platform, cost, revenue, roas
    Returns DataFrame with simulation results.
    """
    rows = []
    for ad in ad_summary:
        roas = ad.get("roas", 0)
        cost = ad.get("cost", 0)
        rows.append({
            "플랫폼": ad["platform"],
            "현재광고비": cost,
            "현재매출": ad.get("revenue", 0),
            "현재ROAS(%)": roas,
        })
    return pd.DataFrame(rows)


def simulate_budget_change(current_cost, current_roas, change_pct, margin_rate):
    """단일 플랫폼 예산 변경 시뮬레이션"""
    new_cost = current_cost * (1 + change_pct / 100)
    # ROAS 체감 효과 (예산 증가 시 ROAS 소폭 하락 가정)
    roas_decay = 1 - (abs(change_pct) * 0.001) if change_pct > 0 else 1
    adj_roas = current_roas * roas_decay
    new_revenue = new_cost * (adj_roas / 100)
    new_profit = (new_revenue * margin_rate) - new_cost
    add_revenue = new_revenue - (current_cost * current_roas / 100)
    add_cost = new_cost - current_cost

    return {
        "new_cost": new_cost,
        "adj_roas": adj_roas,
        "new_revenue": new_revenue,
        "new_profit": new_profit,
        "add_revenue": add_revenue,
        "add_cost": add_cost,
    }

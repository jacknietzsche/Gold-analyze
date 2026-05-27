#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险分析模块 — VaR / CVaR / 夏普 / 压力测试
纯函数，接收 pd.Series 收益率，返回 dict。
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional


def compute_risk_metrics(returns: pd.Series, rf_annual: float = 0.018) -> Dict[str, Any]:
    """计算风险指标（最大回撤、VaR、CVaR、夏普、索提诺）"""
    result: Dict[str, Any] = {}
    if returns is None or len(returns) < 60:
        return result

    # 最大回撤
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    result['max_drawdown'] = round(float(drawdown.min()) * 100, 2)

    # VaR (历史模拟法)
    result['value_at_risk'] = round(float(np.percentile(returns, 5)) * 100, 2)
    result['var_99'] = round(float(np.percentile(returns, 1)) * 100, 2)

    # CVaR
    var_threshold = np.percentile(returns, 5)
    cvar = float(returns[returns <= var_threshold].mean()) * 100
    result['conditional_var'] = round(cvar, 2)

    # 夏普比率
    rf_daily = rf_annual / 252
    sharpe = float((returns.mean() - rf_daily) / returns.std() * np.sqrt(252))
    result['sharpe_ratio'] = round(sharpe, 2)

    # 索提诺比率
    downside = returns[returns < 0]
    downside_std = downside.std() if len(downside) > 0 else returns.std()
    sortino = float((returns.mean() - rf_daily) / downside_std * np.sqrt(252))
    result['sortino_ratio'] = round(sortino, 2)

    return result


def compute_stress_tests(var_95: float, bond_yield: float = 2.0,
                         vix: float = 20) -> Dict[str, Dict[str, str]]:
    """压力测试情景"""
    abs_var = abs(var_95)
    tests: Dict[str, Dict[str, str]] = {}

    tests['interest_rate_shock'] = {
        'scenario': '利率上升100bp',
        'impact': f'-{round(abs_var * 1.5, 1)}%',
        'probability': '15%'
    }
    tests['dollar_strength'] = {
        'scenario': '美元指数上涨5%',
        'impact': f'-{round(abs_var * 1.2, 1)}%',
        'probability': '20%'
    }
    if vix and vix > 25:
        geo_impact = f'+{round(abs_var * 0.8, 1)}%'
        geo_prob = '30%'
    else:
        geo_impact = f'+{round(abs_var * 0.5, 1)}%'
        geo_prob = '10%'
    tests['geopolitical_risk'] = {
        'scenario': '地缘政治紧张升级',
        'impact': geo_impact,
        'probability': geo_prob
    }
    tests['equity_market_crash'] = {
        'scenario': '股市下跌20%',
        'impact': f'+{round(abs_var * 1.0, 1)}%',
        'probability': '5%'
    }
    return tests


def risk_level(max_drawdown: float) -> str:
    """根据最大回撤评定风险等级"""
    abs_dd = abs(max_drawdown)
    if abs_dd < 10:
        return '低风险'
    if abs_dd < 20:
        return '中等风险'
    if abs_dd < 30:
        return '较高风险'
    return '高风险'


def full_risk_analysis(returns: pd.Series, bond_yield: float = 2.0,
                       vix: float = 20) -> Dict[str, Any]:
    """完整风险分析（指标 + 压力测试 + 等级）"""
    metrics = compute_risk_metrics(returns)
    if not metrics:
        return {}

    metrics['stress_test'] = compute_stress_tests(
        metrics['value_at_risk'], bond_yield, vix)
    metrics['risk_level'] = risk_level(metrics['max_drawdown'])
    return metrics

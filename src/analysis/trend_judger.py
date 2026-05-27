#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势判断模块 — 多周期收益率 + 技术指标综合评分
纯函数，接收 dict 数据，返回 dict 结果。
"""

from typing import Dict, Any


def judge_trend(data: Dict[str, Any]) -> Dict[str, Any]:
    """近期趋势判断 — 基于多周期收益率和技术指标

    Args:
        data: 包含 returns, rsi_14, macd_signal, boll_signal,
              kdj_signal, ma_signal, gram 等键的字典

    Returns:
        包含 score, trend, outlook, color, components 的字典
    """
    returns = data.get('returns', {})
    gram = data.get('gram', {})

    r5 = returns.get('近5日', {}).get('value', 0)
    r20 = returns.get('近20日(1月)', {}).get('value', 0)
    rsi = data.get('rsi_14', 50)
    macd_sig = data.get('macd_signal', '')
    gram_score = gram.get('total_score', 5)

    score = 5.0

    # 短期趋势 (30%)
    if r5 > 2:
        score += 1.5
    elif r5 > 0:
        score += 0.5
    elif r5 < -2:
        score -= 1.5
    elif r5 < 0:
        score -= 0.5

    # 中期趋势 (30%)
    if r20 > 5:
        score += 1.5
    elif r20 > 0:
        score += 0.5
    elif r20 < -5:
        score -= 1.5
    elif r20 < 0:
        score -= 0.5

    # RSI (15%)
    if rsi > 70:
        score -= 0.75
    elif rsi < 30:
        score += 0.75
    elif rsi > 50:
        score += 0.25
    else:
        score -= 0.25

    # MACD (15%)
    if '多头' in macd_sig:
        score += 0.75
    elif '空头' in macd_sig:
        score -= 0.75

    # GRAM (10%)
    if gram_score >= 6:
        score += 0.5
    elif gram_score <= 4:
        score -= 0.5

    score = max(0, min(10, score))

    if score >= 7:
        trend, outlook, color = '强势上涨', '看多', '#27ae60'
    elif score >= 6:
        trend, outlook, color = '震荡偏多', '偏多', '#2ecc71'
    elif score >= 5:
        trend, outlook, color = '中性震荡', '中性', '#f39c12'
    elif score >= 4:
        trend, outlook, color = '震荡偏空', '偏空', '#e67e22'
    else:
        trend, outlook, color = '弱势下跌', '看空', '#e74c3c'

    return {
        'score': round(score, 1),
        'trend': trend,
        'outlook': outlook,
        'color': color,
        'components': {
            'short_term': r5,
            'mid_term': r20,
            'rsi': rsi,
            'macd': macd_sig,
            'gram': gram_score
        }
    }

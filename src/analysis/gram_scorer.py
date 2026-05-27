#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRAM 评分模块 — WGC Gold Return Attribution Model
纯函数，接收 dict 数据，返回 dict 结果。
"""

from typing import Dict, Any, Optional


def score_gram(data: Dict[str, Any]) -> Dict[str, Any]:
    """计算 GRAM 因子评分 (WGC Gold Return Attribution Model)

    Args:
        data: 包含 bond_yield, tips_yield, vix, central_bank_buying,
              china_reserves, returns 等键的字典

    Returns:
        包含四个子因子 + total_score + outlook + color 的字典
    """
    gram: Dict[str, Any] = {}

    # 1. 机会成本因子 (Opportunity Cost) - 40%
    bond_yield = data.get('bond_yield', 2.0)
    tips_yield = data.get('tips_yield', 1.0)
    if tips_yield is not None:
        oc_score = max(0, min(10, 10 - tips_yield * 2))
        oc_interp = '低利率环境利好黄金' if tips_yield < 1.5 else '利率偏高，机会成本增加'
    else:
        oc_score = max(0, min(10, 10 - bond_yield * 2))
        oc_interp = '低利率环境利好黄金' if bond_yield < 2.5 else '利率偏高，机会成本增加'
    gram['opportunity_cost'] = {'score': round(oc_score, 1), 'interpretation': oc_interp}

    # 2. 风险与不确定性因子 (Risk & Uncertainty) - 25%
    vix = data.get('vix', 20)
    if vix is not None:
        ru_score = max(0, min(10, vix / 3))
        ru_interp = '避险需求强劲' if vix > 25 else '市场情绪平稳'
    else:
        ru_score = 5
        ru_interp = '数据不可用'
    gram['risk_uncertainty'] = {'score': round(ru_score, 1), 'interpretation': ru_interp}

    # 3. 供需因子 (Supply & Demand) - 20%
    cb_buying = data.get('central_bank_buying', 0)
    if cb_buying and cb_buying > 0:
        sd_score = min(10, 5 + cb_buying / 20)
        sd_interp = '央行持续增持黄金' if cb_buying > 50 else '央行购金正常'
    else:
        sd_score = 5
        sd_interp = '央行购金数据不可用'
    gram['supply_demand'] = {'score': round(sd_score, 1), 'interpretation': sd_interp}

    # 4. 动量因子 (Momentum) - 15%
    returns = data.get('returns', {})
    r20 = returns.get('近20日(1月)', {}).get('value', 0)
    r60 = returns.get('近60日(3月)', {}).get('value', 0)
    if r20 is not None and r60 is not None:
        momentum_score = 5 + (r20 / 5) + (r60 / 10)
        momentum_score = max(0, min(10, momentum_score))
        mo_interp = '正向动量' if r20 > 0 else '负向动量'
    else:
        momentum_score = 5
        mo_interp = '数据不足'
    gram['momentum'] = {'score': round(momentum_score, 1), 'interpretation': mo_interp}

    # 综合评分
    total = (oc_score * 0.40 + ru_score * 0.25 +
             sd_score * 0.20 + momentum_score * 0.15)
    gram['total_score'] = round(total, 1)

    if total >= 6.5:
        gram['outlook'] = '强烈看多'
        gram['color'] = '#27ae60'
    elif total >= 5.5:
        gram['outlook'] = '看多'
        gram['color'] = '#2ecc71'
    elif total >= 4.5:
        gram['outlook'] = '中性'
        gram['color'] = '#f39c12'
    elif total >= 3.5:
        gram['outlook'] = '看空'
        gram['color'] = '#e67e22'
    else:
        gram['outlook'] = '强烈看空'
        gram['color'] = '#e74c3c'

    return gram

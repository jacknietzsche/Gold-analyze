#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情景推演引擎 — 基于技术指标和宏观因子动态计算情景概率
纯函数，接收 dict，返回 dict。
"""

from typing import Dict, Any


def calculate_scenario_probabilities(d: Dict[str, Any]) -> Dict[str, Any]:
    """基于当前技术指标和宏观因子，动态计算未来情景概率。

    Returns:
        dict with base_pct, bull_pct, bear_pct, base_reason, bull_reason, bear_reason
    """
    base_pct, bull_pct, bear_pct = 50, 30, 20

    # 技术面
    rsi = float(d.get('rsi_14', 50))
    macd_sig = str(d.get('macd_signal', ''))
    ma_sig = str(d.get('ma_signal', ''))
    boll_pos = float(d.get('boll_position_pct', 50))

    if rsi >= 80:
        bear_pct += 12; bull_pct -= 4
    elif rsi >= 70:
        bear_pct += 8; bull_pct -= 3
    elif rsi < 20:
        bull_pct += 12; bear_pct -= 4
    elif rsi < 30:
        bull_pct += 8; bear_pct -= 3

    if '空头减弱' in macd_sig:
        bear_pct += 5; bull_pct -= 2
    elif '多头减弱' in macd_sig:
        bear_pct += 6; bull_pct -= 3
    elif '空头增强' in macd_sig or '死叉' in macd_sig:
        bear_pct += 8; bull_pct -= 4
    elif '多头增强' in macd_sig or '金叉' in macd_sig:
        bull_pct += 8; bear_pct -= 4

    if '[!]金叉背离' in ma_sig:
        bear_pct += 12; bull_pct -= 6
    elif '[!]死叉背离' in ma_sig:
        bull_pct += 10; bear_pct -= 5
    elif '多头排列' in ma_sig:
        bull_pct += 6; bear_pct -= 3
    elif '空头排列' in ma_sig:
        bear_pct += 8; bull_pct -= 4

    if boll_pos >= 90:
        bear_pct += 8
    elif boll_pos >= 80:
        bear_pct += 5

    # 宏观面
    vix = float(d.get('vix', 20))
    dxy = float(d.get('dollar_index', 100))
    cb_buying = float(d.get('central_bank_buying', 50))
    gram_score = float(d.get('gram_score', 5))
    hist_pct = float(d.get('historical_percentile', 50))
    bond_yield = float(d.get('bond_yield', 2.0))

    if vix >= 40:
        bull_pct += 8; base_pct -= 5
    elif vix >= 30:
        bull_pct += 5

    if dxy >= 108:
        bear_pct += 10; bull_pct -= 6
    elif dxy >= 105:
        bear_pct += 5; bull_pct -= 3
    elif dxy < 95:
        bull_pct += 8; bear_pct -= 4

    if cb_buying >= 200:
        bull_pct += 8
    elif cb_buying >= 100:
        bull_pct += 5

    if gram_score >= 8:
        bull_pct += 6; bear_pct -= 4
    elif gram_score >= 7:
        bull_pct += 4
    elif gram_score < 3:
        bear_pct += 10; bull_pct -= 6
    elif gram_score < 4:
        bear_pct += 5

    if hist_pct >= 95:
        bear_pct += 8; bull_pct -= 4
    elif hist_pct >= 90:
        bear_pct += 5

    if bond_yield <= 1.0:
        bull_pct += 4
    elif bond_yield >= 3.5:
        bear_pct += 5

    # 归一化
    total = base_pct + bull_pct + bear_pct
    base_pct = max(5, min(85, round(base_pct / total * 100)))
    bull_pct = max(5, min(80, round(bull_pct / total * 100)))
    bear_pct = max(5, 100 - base_pct - bull_pct)

    # 生成假设描述
    reasons = []
    if dxy >= 105:
        reasons.append('美元偏强，美联储维持当前政策')
    elif dxy < 95:
        reasons.append('美元走弱，降息预期升温')
    else:
        reasons.append('美联储维持当前政策，通胀逐步回落')

    if hist_pct >= 90:
        reasons.append(f'金价历史分位{round(hist_pct,0)}%高位，震荡整固')
    elif hist_pct < 50:
        reasons.append(f'金价历史分位{round(hist_pct,0)}%低位，估值合理')
    else:
        reasons.append('市场维持当前节奏')
    base_reason = ';'.join(reasons[:2])

    bull_reasons = []
    if cb_buying >= 200:
        bull_reasons.append(f'央行月均购金{round(cb_buying,0)}吨，避险需求激增')
    if vix >= 30:
        bull_reasons.append(f'VIX={round(vix,0)}，地缘风险升温')
    if dxy < 95:
        bull_reasons.append('美元持续走弱，降息提前')
    if gram_score >= 7:
        bull_reasons.append('GRAM评分偏高，基本面支撑强')
    if not bull_reasons:
        bull_reasons.append('地缘冲突升级+避险需求激增')
    bull_reason = '，'.join(bull_reasons[:2])

    bear_reasons = []
    if rsi >= 70 or boll_pos >= 90:
        bear_reasons.append('技术面超买严重(RSI={:.0f})'.format(rsi))
    if dxy >= 105:
        bear_reasons.append(f'DXY={round(dxy,1)}，美元走强压制')
    if hist_pct >= 95:
        bear_reasons.append(f'历史分位{round(hist_pct,0)}%，估值泡沫风险')
    if gram_score < 4:
        bear_reasons.append('GRAM评分偏低，基本面边际转弱')
    if not bear_reasons:
        bear_reasons.append('美联储鹰派立场，利率上行压力')
    bear_reason = '，'.join(bear_reasons[:2])

    return {
        'base_pct': base_pct,
        'bull_pct': bull_pct,
        'bear_pct': bear_pct,
        'base_reason': base_reason,
        'bull_reason': bull_reason,
        'bear_reason': bear_reason,
    }

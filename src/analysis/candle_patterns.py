#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K线形态识别模块 — 纯函数
接收 pd.DataFrame (OHLC)，返回 list[dict]。
"""

import pandas as pd
from typing import List, Dict


def identify_patterns(ohlc: pd.DataFrame) -> List[Dict[str, str]]:
    """识别K线形态（十字星、锤头、吞没、射击之星）"""
    patterns: List[Dict[str, str]] = []

    if ohlc is None or len(ohlc) < 2:
        return [{'name': '无明显形态', 'signal': '中性',
                 'description': '当前K线无明显形态特征'}]

    recent = ohlc.tail(5)
    latest = recent.iloc[-1]
    prev = recent.iloc[-2]

    o, h, l, c = latest['open'], latest['high'], latest['low'], latest['close']
    body = abs(c - o)
    upper_shadow = h - max(o, c)
    lower_shadow = min(o, c) - l
    total_range = h - l

    # 十字星
    if total_range > 0 and body < total_range * 0.1:
        patterns.append({'name': '十字星', 'signal': '中性',
                         'description': '多空力量均衡，可能反转'})

    # 锤头线 (阳线)
    if lower_shadow > body * 2 and upper_shadow < body * 0.5 and c > o:
        patterns.append({'name': '锤头线', 'signal': '看涨',
                         'description': '下跌后出现，可能反转向上'})

    # 上吊线 (阴线)
    if lower_shadow > body * 2 and upper_shadow < body * 0.5 and c < o:
        patterns.append({'name': '上吊线', 'signal': '看跌',
                         'description': '上涨后出现，可能反转向下'})

    # 吞没形态
    prev_o, prev_c = prev['open'], prev['close']
    if prev_c < prev_o and c > o and o < prev_c and c > prev_o:
        patterns.append({'name': '看涨吞没', 'signal': '看涨',
                         'description': '阳线完全包裹前一根阴线，强烈看涨信号'})
    if prev_c > prev_o and c < o:
        if o > prev_c and c < prev_o:
            patterns.append({'name': '看跌吞没', 'signal': '看跌',
                             'description': '阴线完全包裹前一根阳线，强烈看跌信号'})

    # 射击之星
    if upper_shadow > body * 2 and lower_shadow < body * 0.5 and c < o:
        patterns.append({'name': '射击之星', 'signal': '看跌',
                         'description': '上涨后出现长上影线，可能见顶'})

    if not patterns:
        patterns.append({'name': '无明显形态', 'signal': '中性',
                         'description': '当前K线无明显形态特征'})

    return patterns

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术指标纯函数模块 — 唯一权威实现
所有指标函数接受 pd.Series / np.ndarray，返回 pd.Series（或 tuple）。
无副作用，无状态，可被 GoldReportBase / GoldFactors / GoldStrategies 直接调用。
"""

import numpy as np
import pandas as pd
from typing import Union, Tuple, Dict, Optional

SeriesLike = Union[pd.Series, np.ndarray]


# ═══════════════════════════════════════════════════════════════
# 基础工具
# ═══════════════════════════════════════════════════════════════

def ema(data: SeriesLike, period: int) -> np.ndarray:
    """指数移动平均（标准 EMA，multiplier = 2/(period+1)）"""
    arr = np.asarray(data, dtype=float)
    if len(arr) < period:
        return arr.copy()
    out = np.zeros_like(arr, dtype=float)
    k = 2.0 / (period + 1)
    out[0] = arr[0]
    for i in range(1, len(arr)):
        out[i] = (arr[i] - out[i - 1]) * k + out[i - 1]
    return out


def moving_average(prices: SeriesLike, period: int) -> pd.Series:
    """简单移动平均"""
    s = pd.Series(prices) if not isinstance(prices, pd.Series) else prices
    return s.rolling(period).mean()


# ═══════════════════════════════════════════════════════════════
# RSI — Wilder EMA（alpha=1/period）
# ═══════════════════════════════════════════════════════════════

def rsi(prices: SeriesLike, period: int = 14) -> pd.Series:
    """RSI（Wilder 平滑法，与 factors.py 一致）"""
    s = pd.Series(prices) if not isinstance(prices, pd.Series) else prices
    delta = s.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss_safe = avg_loss.replace(0, np.nan)
    rs = avg_gain / avg_loss_safe
    return 100 - (100 / (1 + rs))


def rsi_signal(rsi_value: float) -> str:
    """RSI 单值信号标签"""
    if rsi_value >= 80:
        return "严重超买"
    if rsi_value >= 70:
        return "超买"
    if rsi_value <= 20:
        return "严重超卖"
    if rsi_value <= 30:
        return "超卖"
    return "中性"


# ═══════════════════════════════════════════════════════════════
# MACD (12, 26, 9)
# ═══════════════════════════════════════════════════════════════

def macd(prices: SeriesLike, fast: int = 12, slow: int = 26,
         signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """返回 (DIF, DEA, HIST)，HIST = (DIF-DEA)*2（中国市场惯例）"""
    s = pd.Series(prices) if not isinstance(prices, pd.Series) else prices
    ema_fast = s.ewm(span=fast, adjust=False).mean()
    ema_slow = s.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = (dif - dea) * 2
    return dif, dea, hist


def macd_signal_text(dif: float, dea: float, hist: float,
                     prev_hist: float) -> str:
    """MACD 柱状图信号文本"""
    if dif > dea:
        return "多头增强" if hist > prev_hist else "多头减弱"
    if dif < dea:
        return "空头增强" if hist < prev_hist else "空头减弱"
    return "零轴附近"


# ═══════════════════════════════════════════════════════════════
# 布林带 BOLL (20, 2)
# ═══════════════════════════════════════════════════════════════

def bollinger_bands(prices: SeriesLike, period: int = 20,
                    std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """返回 (upper, middle, lower)"""
    s = pd.Series(prices) if not isinstance(prices, pd.Series) else prices
    mid = s.rolling(period).mean()
    std = s.rolling(period).std()
    upper = mid + std * std_dev
    lower = mid - std * std_dev
    return upper, mid, lower


def boll_position(price: float, upper: float, lower: float) -> float:
    """价格在布林带中的位置百分比 (0-100)"""
    width = upper - lower
    if width <= 0:
        return 50.0
    return (price - lower) / width * 100


def boll_signal_text(price: float, upper: float, lower: float,
                     position_pct: float) -> str:
    """布林带信号文本"""
    if price > upper:
        return "超买区(突破上轨)"
    if price < lower:
        return "超卖区(跌破下轨)"
    if position_pct > 80:
        return "偏强区域(上轨附近)"
    if position_pct < 20:
        return "偏弱区域(下轨附近)"
    return "正常区间"


# ═══════════════════════════════════════════════════════════════
# KDJ (9, 3, 3)
# ═══════════════════════════════════════════════════════════════

def kdj(closes: SeriesLike, highs: SeriesLike = None,
        lows: SeriesLike = None, k_period: int = 9,
        k_smooth: int = 3, d_smooth: int = 3
        ) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """返回 (K, D, J)。若无 high/low 则用 close 的 rolling 代替。"""
    cs = pd.Series(closes) if not isinstance(closes, pd.Series) else closes
    if highs is not None and lows is not None:
        hs = pd.Series(highs) if not isinstance(highs, pd.Series) else highs
        ls = pd.Series(lows) if not isinstance(lows, pd.Series) else lows
    else:
        hs = cs.rolling(k_period).max()
        ls = cs.rolling(k_period).min()

    rsv = ((cs - ls) / (hs - ls + 1e-10)) * 100
    k = rsv.ewm(com=k_smooth - 1, adjust=False).mean()
    d = k.ewm(com=d_smooth - 1, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


def kdj_signal_text(k: float, d: float, j: float) -> str:
    """KDJ 信号文本"""
    if k > 80 and d > 80:
        return "严重超买"
    if k > 70 and d > 70:
        return "轻度超买"
    if k < 20 and d < 20:
        return "严重超卖"
    if k < 30 and d < 30:
        return "轻度超卖"
    if k > d:
        return "多头排列"
    return "空头排列"


# ═══════════════════════════════════════════════════════════════
# ATR (Average True Range)
# ═══════════════════════════════════════════════════════════════

def atr(highs: SeriesLike, lows: SeriesLike, closes: SeriesLike,
        period: int = 14) -> pd.Series:
    """ATR — 使用 Wilder 平滑（ewm alpha=1/period）"""
    h = pd.Series(highs) if not isinstance(highs, pd.Series) else highs
    l = pd.Series(lows) if not isinstance(lows, pd.Series) else lows
    c = pd.Series(closes) if not isinstance(closes, pd.Series) else closes
    prev_c = c.shift(1)
    tr = pd.concat([
        h - l,
        (h - prev_c).abs(),
        (l - prev_c).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def atr_from_ohlc(ohlc_df: pd.DataFrame, period: int = 14) -> pd.Series:
    """从 OHLC DataFrame 计算 ATR（列名: high, low, close）"""
    return atr(ohlc_df['high'], ohlc_df['low'], ohlc_df['close'], period)


# ═══════════════════════════════════════════════════════════════
# 波动率
# ═══════════════════════════════════════════════════════════════

def volatility(prices: SeriesLike, period: int = 20,
               annualize: bool = True) -> float:
    """已实现波动率（年化，默认对数收益率）"""
    s = pd.Series(prices) if not isinstance(prices, pd.Series) else prices
    if len(s) < period + 1:
        return 0.15  # 默认15%
    log_ret = np.log(s / s.shift(1)).dropna()
    rv = float(log_ret.iloc[-period:].std())
    if annualize:
        rv *= np.sqrt(252)
    return max(rv, 0.05)  # 最低5%


def rolling_volatility(prices: SeriesLike, period: int = 20,
                       annualize: bool = True) -> pd.Series:
    """滚动波动率序列"""
    s = pd.Series(prices) if not isinstance(prices, pd.Series) else prices
    log_ret = np.log(s / s.shift(1))
    vol = log_ret.rolling(period).std()
    if annualize:
        vol = vol * np.sqrt(252)
    return vol


# ═══════════════════════════════════════════════════════════════
# 周期收益率
# ═══════════════════════════════════════════════════════════════

def period_returns(prices: SeriesLike,
                   periods: Dict[str, int] = None) -> Dict[str, Optional[float]]:
    """计算多个周期的收益率（对数收益率，百分比）"""
    s = pd.Series(prices) if not isinstance(prices, pd.Series) else prices
    if periods is None:
        periods = {
            '近1日': 2, '近5日': 6, '近20日(1月)': 21,
            '近60日(3月)': 61, '近120日(6月)': 121, '近252日(1年)': 253
        }
    result = {}
    for label, lookback in periods.items():
        if len(s) >= lookback:
            ret = float(np.log(s.iloc[-1] / s.iloc[-lookback]) * 100)
            result[label] = round(ret, 2)
        else:
            result[label] = None
    return result


# ═══════════════════════════════════════════════════════════════
# 均线系统综合信号
# ═══════════════════════════════════════════════════════════════

def ma_system_signal(closes: SeriesLike) -> Tuple[str, str]:
    """均线系统综合信号判断
    返回 (status, detail) — 如 ('偏多', 'MA5>MA20金叉，站上MA60')
    """
    s = pd.Series(closes) if not isinstance(closes, pd.Series) else closes
    n = len(s)
    latest = float(s.iloc[-1])
    ma5 = float(s.iloc[-5:].mean())
    ma20 = float(s.iloc[-20:].mean()) if n >= 20 else latest
    ma60 = float(s.iloc[-60:].mean()) if n >= 60 else latest

    ma5_above_ma20 = ma5 > ma20
    ma5_below_ma20 = ma5 < ma20
    price_above_ma60 = latest > ma60
    ma5_above_ma60 = ma5 > ma60

    if ma5_above_ma20 and price_above_ma60:
        return '偏多', 'MA5>MA20金叉，站上MA60'
    if ma5_below_ma20 and not price_above_ma60:
        return '偏空', 'MA5<MA20死叉，跌破MA60'
    if ma5_above_ma20 and not price_above_ma60 and ma5_above_ma60:
        return '中性', 'MA5>MA20金叉，价格试探MA60'
    if ma5_above_ma20 and not price_above_ma60:
        return '[!]背离', 'MA5>MA20金叉[!]但跌破MA60(偏空)'
    if ma5_below_ma20 and price_above_ma60:
        return '[!]背离', 'MA5<MA20死叉[!]但收于MA60上方'
    if ma5_above_ma20:
        return '短多', 'MA5>MA20金叉'
    if ma5_below_ma20:
        return '短空', 'MA5<MA20死叉'
    return '震荡', 'MA5与MA20纠缠'


# ═══════════════════════════════════════════════════════════════
# 便捷：一次性计算全部指标
# ═══════════════════════════════════════════════════════════════

def compute_all(closes: SeriesLike, highs: SeriesLike = None,
                lows: SeriesLike = None) -> Dict[str, object]:
    """一次性计算全部技术指标，返回 dict（便于直接写入 self.data）。"""
    cs = pd.Series(closes) if not isinstance(closes, pd.Series) else closes
    n = len(cs)
    latest = float(cs.iloc[-1])
    result: Dict[str, object] = {}

    # 移动平均
    for p in [5, 10, 20, 60, 120, 250]:
        key = f'ma{p}'
        if n >= p:
            result[key] = round(float(cs.iloc[-p:].mean()), 2)
        else:
            result[key] = None

    # 高低点
    result['high_60d'] = round(float(cs.iloc[-61:].max()), 2)
    result['low_60d'] = round(float(cs.iloc[-61:].min()), 2)
    result['high_120d'] = round(float(cs.iloc[-121:].max()), 2)
    result['low_120d'] = round(float(cs.iloc[-121:].min()), 2)

    # RSI
    rsi_series = rsi(cs, 14)
    result['rsi_14'] = round(float(rsi_series.iloc[-1]), 1) if not rsi_series.empty else 50.0

    # MACD
    dif_s, dea_s, hist_s = macd(cs)
    result['macd_dif'] = round(float(dif_s.iloc[-1]), 4)
    result['macd_dea'] = round(float(dea_s.iloc[-1]), 4)
    result['macd_hist'] = round(float(hist_s.iloc[-1]), 4)
    prev_hist = float(hist_s.iloc[-2]) if len(hist_s) >= 2 else 0
    result['macd_signal'] = macd_signal_text(
        result['macd_dif'], result['macd_dea'], result['macd_hist'], prev_hist)

    # 布林带
    bu, bm, bl = bollinger_bands(cs, 20, 2)
    result['boll_mid'] = round(float(bm.iloc[-1]), 2)
    result['boll_upper'] = round(float(bu.iloc[-1]), 2)
    result['boll_lower'] = round(float(bl.iloc[-1]), 2)
    bw_pct = (bu.iloc[-1] - bl.iloc[-1]) / (bm.iloc[-1] + 1e-10) * 100
    result['boll_width'] = round(float(bw_pct), 1)
    bpct = boll_position(latest, float(bu.iloc[-1]), float(bl.iloc[-1]))
    result['boll_position_pct'] = round(bpct, 1)
    result['boll_signal'] = boll_signal_text(latest, float(bu.iloc[-1]),
                                              float(bl.iloc[-1]), bpct)

    # KDJ
    k_s, d_s, j_s = kdj(cs, highs, lows)
    result['kdj_k'] = round(float(k_s.iloc[-1]), 1)
    result['kdj_d'] = round(float(d_s.iloc[-1]), 1)
    result['kdj_j'] = round(float(j_s.iloc[-1]), 1)
    result['kdj_signal'] = kdj_signal_text(result['kdj_k'], result['kdj_d'],
                                            result['kdj_j'])

    # ATR
    if highs is not None and lows is not None:
        atr_s = atr(highs, lows, cs, 14)
        result['atr_14'] = round(float(atr_s.iloc[-1]), 2)
    else:
        result['atr_14'] = round(float(cs.diff().abs().tail(14).mean()), 2)

    # 波动率
    returns = cs.pct_change().dropna()
    result['volatility_20d'] = round(float(returns.tail(20).std() * np.sqrt(252) * 100), 2)
    result['volatility_60d'] = round(float(returns.tail(60).std() * np.sqrt(252) * 100), 2)

    # 历史分位
    result['historical_percentile'] = round(float((cs < latest).sum() / len(cs) * 100), 1)

    # 均线信号
    ma_status, ma_detail = ma_system_signal(cs)
    result['ma_signal'] = ma_detail

    return result

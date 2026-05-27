#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金量化风险管理模块 - Phase 3
实现：
  1. 波动率目标化仓位管理 (Volatility Targeting)
     参考: Barroso & Santa-Clara (2015), 提升 Sharpe ~30%
  2. VaR / CVaR 风险价值计算（历史模拟法 + 参数法）
  3. 上海金/国际金溢价因子（A 股黄金市场特有因子）
  4. 宏观数据公布滞后处理（消除前视偏差）
  5. 动态止损宽度计算（ATR-based）

无任何随机/模拟数据。
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple
import warnings

warnings.filterwarnings('ignore')


# ===========================================================================
# 1. 波动率目标化仓位管理
# ===========================================================================

class VolatilityTargetManager:
    """
    波动率目标化仓位管理器
    
    核心思想（Barroso & Santa-Clara, 2015）：
      position_t = vol_target / realized_vol_t
      
    - 高波动期降仓 → 控制下行风险
    - 低波动期加仓 → 充分利用趋势
    - 相比固定仓位，Sharpe Ratio 平均提升约 30%
    
    上限：不允许超过 max_leverage 倍杠杆
    """

    def __init__(
        self,
        vol_target: float = 0.10,
        vol_lookback: int = 20,
        max_leverage: float = 1.5,
        min_position: float = 0.0,
        annualize_factor: int = 252
    ):
        """
        Parameters
        ----------
        vol_target     : 年化波动率目标（默认10%）
        vol_lookback   : 历史波动率计算窗口（交易日数）
        max_leverage   : 最大杠杆倍数（默认1.5倍）
        min_position   : 最小仓位（做多策略设为0）
        annualize_factor: 年化因子（日频=252）
        """
        self.vol_target      = vol_target
        self.vol_lookback    = vol_lookback
        self.max_leverage    = max_leverage
        self.min_position    = min_position
        self.annualize_factor = annualize_factor

    def compute_realized_vol(self, price: pd.Series) -> pd.Series:
        """
        计算已实现波动率（年化）。
        使用对数收益率的滚动标准差。
        """
        log_ret = np.log(price / price.shift(1))
        rv = log_ret.rolling(self.vol_lookback).std() * np.sqrt(self.annualize_factor)
        return rv

    def scale_position(
        self,
        raw_signal: pd.Series,
        price: pd.Series
    ) -> pd.Series:
        """
        将原始信号（-1/0/1）按波动率目标化调整为连续仓位。
        
        Returns
        -------
        scaled_position : pd.Series  仓位大小（0~max_leverage）
        """
        rv = self.compute_realized_vol(price)
        rv_safe = rv.replace(0, np.nan).ffill().fillna(0.1)
        
        # 核心公式：仓位 = 方向 × (vol_target / realized_vol)
        scale = self.vol_target / rv_safe
        scale = scale.clip(upper=self.max_leverage)
        
        scaled = raw_signal * scale
        scaled = scaled.clip(lower=self.min_position, upper=self.max_leverage)
        return scaled

    def summary(self, price: pd.Series, scaled_pos: pd.Series) -> dict:
        """返回波动率目标化的摘要统计"""
        rv = self.compute_realized_vol(price)
        return {
            'vol_target':       self.vol_target,
            'avg_realized_vol': round(float(rv.mean()), 4),
            'avg_position':     round(float(scaled_pos.mean()), 4),
            'max_position':     round(float(scaled_pos.max()),  4),
            'min_position':     round(float(scaled_pos.min()),  4),
        }


# ===========================================================================
# 2. VaR / CVaR 风险价值
# ===========================================================================

class RiskMetrics:
    """
    风险价值计算器
    
    支持方法：
    - 历史模拟法（Historical Simulation）
    - 参数法（正态分布假设）
    - Cornish-Fisher 修正法（考虑偏度/峰度）
    """

    def __init__(self, confidence: float = 0.95):
        """
        Parameters
        ----------
        confidence : float  置信水平（默认 95%）
        """
        self.confidence = confidence
        self._alpha = 1 - confidence

    # ------------------------------------------------------------------
    # 历史模拟法
    # ------------------------------------------------------------------

    def historical_var(
        self,
        returns: pd.Series,
        horizon: int = 1,
        window: int = 252
    ) -> pd.Series:
        """
        滚动历史模拟 VaR。
        
        Parameters
        ----------
        returns  : 日收益率序列
        horizon  : 持有期（天），VaR 乘以 sqrt(horizon)
        window   : 历史窗口（交易日数）
        
        Returns
        -------
        var_series : pd.Series（负数，表示最大可能损失）
        """
        def _var_hist(x):
            return np.percentile(x, self._alpha * 100)
        
        var = returns.rolling(window).apply(_var_hist, raw=True)
        if horizon > 1:
            var = var * np.sqrt(horizon)
        return var

    def historical_cvar(
        self,
        returns: pd.Series,
        horizon: int = 1,
        window: int = 252
    ) -> pd.Series:
        """
        滚动历史模拟 CVaR（Expected Shortfall）。
        CVaR = 超过 VaR 的损失的均值，比 VaR 更保守。
        """
        def _cvar_hist(x):
            threshold = np.percentile(x, self._alpha * 100)
            tail = x[x <= threshold]
            return tail.mean() if len(tail) > 0 else threshold
        
        cvar = returns.rolling(window).apply(_cvar_hist, raw=True)
        if horizon > 1:
            cvar = cvar * np.sqrt(horizon)
        return cvar

    # ------------------------------------------------------------------
    # 参数法
    # ------------------------------------------------------------------

    def parametric_var(
        self,
        returns: pd.Series,
        horizon: int = 1,
        window: int = 252
    ) -> pd.Series:
        """
        参数法（正态分布假设）滚动 VaR。
        VaR = μ - z_α * σ  （z_α 为标准正态分位数）
        """
        from scipy import stats
        z = stats.norm.ppf(self._alpha)  # 负数，e.g. -1.645 for 95%
        roll_mean = returns.rolling(window).mean()
        roll_std  = returns.rolling(window).std()
        var = roll_mean + z * roll_std
        if horizon > 1:
            var = var * np.sqrt(horizon)
        return var

    def parametric_cvar(
        self,
        returns: pd.Series,
        horizon: int = 1,
        window: int = 252
    ) -> pd.Series:
        """
        参数法 CVaR（正态假设下的解析公式）。
        CVaR = -μ + σ * φ(z_α) / α
        """
        from scipy import stats
        z = stats.norm.ppf(self._alpha)
        roll_mean = returns.rolling(window).mean()
        roll_std  = returns.rolling(window).std()
        # CVaR = E[R | R < VaR] = μ - σ * φ(z)/α
        cvar = roll_mean - roll_std * (stats.norm.pdf(z) / self._alpha)
        if horizon > 1:
            cvar = cvar * np.sqrt(horizon)
        return cvar

    # ------------------------------------------------------------------
    # Cornish-Fisher 修正
    # ------------------------------------------------------------------

    def cornish_fisher_var(
        self,
        returns: pd.Series,
        horizon: int = 1,
        window: int = 252
    ) -> pd.Series:
        """
        Cornish-Fisher 展开修正 VaR（考虑偏度和峰度）。
        z_CF = z + (z²-1)S/6 + (z³-3z)K/24 - (2z³-5z)S²/36
        其中 S=偏度，K=超额峰度
        """
        from scipy import stats
        z = stats.norm.ppf(self._alpha)
        
        def _cf_var(x):
            mu  = np.mean(x)
            sig = np.std(x)
            if sig == 0:
                return mu - abs(z) * sig
            skew = stats.skew(x)
            kurt = stats.kurtosis(x)  # Fisher（超额峰度）
            z_cf = (z + (z**2 - 1)*skew/6
                    + (z**3 - 3*z)*kurt/24
                    - (2*z**3 - 5*z)*skew**2/36)
            return mu + z_cf * sig
        
        var = returns.rolling(window).apply(_cf_var, raw=True)
        if horizon > 1:
            var = var * np.sqrt(horizon)
        return var

    # ------------------------------------------------------------------
    # 一键报告
    # ------------------------------------------------------------------

    def risk_report(
        self,
        returns: pd.Series,
        position_value: float = 1.0,
        horizon: int = 1
    ) -> dict:
        """
        生成当前风险报告（基于最近252日数据）。
        
        Parameters
        ----------
        position_value : 持仓价值（万元）
        horizon        : 持有期（天）
        
        Returns
        -------
        dict 含各方法的 VaR / CVaR（绝对值）
        """
        recent = returns.dropna().tail(252)
        if len(recent) < 30:
            return {'error': '数据不足30天，无法计算风险指标'}
        
        mu   = float(recent.mean())
        sigma= float(recent.std())
        skew = float(recent.skew()) if len(recent) >= 3 else 0.0
        
        # 历史模拟
        hist_var  = float(np.percentile(recent, self._alpha * 100))
        hist_cvar = float(recent[recent <= hist_var].mean()) if len(recent[recent <= hist_var]) > 0 else hist_var
        
        # 参数法
        from scipy import stats
        z = stats.norm.ppf(self._alpha)
        param_var  = mu + z * sigma
        param_cvar = mu - sigma * (stats.norm.pdf(z) / self._alpha)
        
        # CF 修正
        kurt = float(recent.kurtosis()) if len(recent) >= 4 else 0.0
        z_cf = (z + (z**2 - 1)*skew/6
                + (z**3 - 3*z)*kurt/24
                - (2*z**3 - 5*z)*skew**2/36)
        cf_var = mu + z_cf * sigma
        
        scale = np.sqrt(horizon)
        pv    = position_value
        
        return {
            'confidence':          f"{self.confidence*100:.0f}%",
            'horizon_days':        horizon,
            'position_value_wan':  pv,
            # 日度 VaR/CVaR（百分比）
            'hist_var_pct':        round(hist_var  * scale * 100, 2),
            'hist_cvar_pct':       round(hist_cvar * scale * 100, 2),
            'param_var_pct':       round(param_var  * scale * 100, 2),
            'param_cvar_pct':      round(param_cvar * scale * 100, 2),
            'cf_var_pct':          round(cf_var    * scale * 100, 2),
            # 绝对金额（万元）
            'hist_var_wan':        round(abs(hist_var  * scale * pv), 4),
            'hist_cvar_wan':       round(abs(hist_cvar * scale * pv), 4),
            # 描述统计
            'daily_mean_pct':      round(mu    * 100, 4),
            'daily_vol_pct':       round(sigma * 100, 4),
            'skewness':            round(skew,        4),
            'excess_kurtosis':     round(kurt,        4),
        }


# ===========================================================================
# 3. 上海金 / 国际金溢价因子
# ===========================================================================

class ShanghaiGoldPremiumFactor:
    """
    上海金/国际金溢价因子
    
    上海黄金交易所（SGE）AU99.99 现货价格与伦敦金现货换算价之差。
    溢价较高时，说明国内买盘旺盛，对金价形成支撑。
    
    公式：
        sge_price_cny  : 沪金价格（元/克）
        lbma_usd_oz    : 伦敦金价格（美元/盎司）
        usdcny         : 美元兑人民币汇率
        
        lbma_cny_gram  = lbma_usd_oz / 31.1035 * usdcny
        premium        = sge_price_cny - lbma_cny_gram
        premium_pct    = premium / lbma_cny_gram
    """

    def compute_premium(
        self,
        sge_price_cny: pd.Series,      # 元/克
        lbma_usd_oz:   pd.Series,      # 美元/盎司
        usdcny:        pd.Series       # 汇率
    ) -> pd.Series:
        """
        计算上海金溢价（元/克）。
        
        Returns
        -------
        premium : pd.Series（正数=沪金贵于国际金）
        """
        # 对齐时间索引
        df = pd.concat([
            sge_price_cny.rename('sge'),
            lbma_usd_oz.rename('lbma_usd'),
            usdcny.rename('usdcny')
        ], axis=1).dropna()
        
        df['lbma_cny'] = df['lbma_usd'] / 31.1035 * df['usdcny']
        df['premium']  = df['sge'] - df['lbma_cny']
        df['premium_pct'] = df['premium'] / df['lbma_cny']
        
        return df['premium_pct']

    def compute_factor(
        self,
        sge_price_cny: pd.Series,
        lbma_usd_oz:   pd.Series,
        usdcny:        pd.Series,
        ma_period:     int = 20
    ) -> pd.Series:
        """
        生成标准化溢价因子（z-score）。
        溢价高于历史均值 → 因子为正（看多）
        溢价低于历史均值 → 因子为负（看空）
        """
        premium_pct = self.compute_premium(sge_price_cny, lbma_usd_oz, usdcny)
        
        # 滚动z-score标准化
        roll_mean = premium_pct.rolling(ma_period * 12).mean()  # ~1年
        roll_std  = premium_pct.rolling(ma_period * 12).std()
        
        z = (premium_pct - roll_mean) / roll_std.replace(0, np.nan)
        return z

    def get_latest_premium(
        self,
        sge_price_cny: pd.Series,
        lbma_usd_oz:   pd.Series,
        usdcny:        pd.Series
    ) -> dict:
        """获取最新溢价摘要"""
        pct = self.compute_premium(sge_price_cny, lbma_usd_oz, usdcny)
        if pct.empty:
            return {'error': '数据不足'}
        
        latest     = float(pct.iloc[-1])
        hist_mean  = float(pct.mean())
        hist_std   = float(pct.std())
        percentile = float((pct < latest).mean())
        
        signal = 1 if latest > hist_mean + 0.5 * hist_std else (
                -1 if latest < hist_mean - 0.5 * hist_std else 0)
        
        return {
            'latest_premium_pct':   round(latest      * 100, 4),
            'hist_mean_pct':        round(hist_mean   * 100, 4),
            'hist_std_pct':         round(hist_std    * 100, 4),
            'percentile':           round(percentile  * 100, 1),
            'signal':               signal,
            'signal_desc': '看多（国内需求旺盛）' if signal == 1 else
                           '看空（国内需求低迷）' if signal == -1 else '中性',
        }


# ===========================================================================
# 4. 宏观数据公布滞后处理（消除前视偏差）
# ===========================================================================

MACRO_PUBLICATION_LAG = {
    'cpi':        25,   # CPI：通常次月中旬公布，约25个交易日
    'm2':         20,   # M2：次月中旬公布，约20个交易日
    'ppi':        25,   # PPI：同 CPI
    'gdp':        60,   # GDP：季度后约2个月
    'trade':      15,   # 贸易数据：次月中
    'pmi':         5,   # PMI：当月末~次月初，约5天
    'treasury':    0,   # 国债收益率：实时
    'dxy':         0,   # 美元指数：实时
    'vix':         0,   # VIX：实时
}


def apply_publication_lag(
    macro_series: pd.Series,
    indicator_name: str,
    custom_lag_days: Optional[int] = None
) -> pd.Series:
    """
    将宏观数据序列后移公布滞后期，消除前视偏差。
    
    Parameters
    ----------
    macro_series     : 宏观指标时间序列
    indicator_name   : 指标名称（用于查找默认滞后天数）
    custom_lag_days  : 自定义滞后天数（优先级高于默认值）
    
    Returns
    -------
    lagged_series : 后移后的时间序列（数据只在公布后才可见）
    """
    lag = custom_lag_days if custom_lag_days is not None else \
          MACRO_PUBLICATION_LAG.get(indicator_name.lower(), 25)
    
    if lag == 0:
        return macro_series.copy()
    
    # 用日历天数计算约 lag 个交易日的滞后
    # 简化：直接 shift（日频序列用 lag 天）
    lagged = macro_series.shift(lag)
    return lagged


def apply_all_macro_lags(macro_dict: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
    """
    批量处理宏观数据字典，为所有指标添加公布滞后。
    
    Parameters
    ----------
    macro_dict : {indicator_name: series}
    
    Returns
    -------
    lagged_dict : 所有序列均已后移
    """
    lagged = {}
    for name, series in macro_dict.items():
        lagged[name] = apply_publication_lag(series, name)
        lag_days = MACRO_PUBLICATION_LAG.get(name.lower(), 25)
        if lag_days > 0:
            print(f"[宏观滞后] {name}: 后移 {lag_days} 天（消除前视偏差）")
    return lagged


# ===========================================================================
# 5. ATR 动态止损
# ===========================================================================

def compute_atr_stop_loss(
    price: pd.Series,
    high: pd.Series,
    low: pd.Series,
    atr_period: int = 14,
    atr_multiplier: float = 2.0,
    direction: int = 1  # 1=多头, -1=空头
) -> pd.Series:
    """
    基于 ATR 的动态止损价格序列。
    
    多头止损 = close - atr_multiplier * ATR
    空头止损 = close + atr_multiplier * ATR
    
    参考: Chandelier Exit (Lebeau & Lucas)
    """
    tr1 = high - low
    tr2 = (high - price.shift(1)).abs()
    tr3 = (low  - price.shift(1)).abs()
    tr  = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(atr_period).mean()
    
    if direction == 1:
        stop = price - atr_multiplier * atr
    else:
        stop = price + atr_multiplier * atr
    
    return stop


# ===========================================================================
# 快捷函数：生成完整风险摘要
# ===========================================================================

def generate_risk_summary(
    gold_price: pd.Series,
    gold_returns: pd.Series,
    position_value_wan: float = 10.0,
    vol_target: float = 0.10,
    confidence: float = 0.95
) -> dict:
    """
    一键生成风险管理摘要（波动率目标化 + VaR/CVaR）。
    
    Parameters
    ----------
    gold_price          : 黄金收盘价序列
    gold_returns        : 日对数收益率序列
    position_value_wan  : 持仓价值（万元）
    """
    # 波动率目标化
    vtm = VolatilityTargetManager(vol_target=vol_target)
    rv  = vtm.compute_realized_vol(gold_price)
    latest_rv = float(rv.dropna().iloc[-1]) if not rv.dropna().empty else np.nan
    
    # 波动率目标化建议仓位（假设当前是纯多头信号）
    raw_sig = pd.Series(1.0, index=gold_price.index)
    scaled  = vtm.scale_position(raw_sig, gold_price)
    latest_scaled = float(scaled.dropna().iloc[-1]) if not scaled.dropna().empty else np.nan
    
    # VaR/CVaR
    rm = RiskMetrics(confidence=confidence)
    risk = rm.risk_report(gold_returns, position_value=position_value_wan)
    
    return {
        'vol_target':               f"{vol_target*100:.0f}%",
        'latest_realized_vol_ann':  f"{latest_rv*100:.1f}%" if not np.isnan(latest_rv) else 'N/A',
        'vol_target_position':      f"{latest_scaled:.2f}x" if not np.isnan(latest_scaled) else 'N/A',
        'risk_metrics':             risk,
    }


# ===========================================================================
# 模块信息
# ===========================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("黄金量化风险管理模块 - Phase 3")
    print("=" * 60)
    print("\n功能包括:")
    print("  1. 波动率目标化仓位管理 (Barroso & Santa-Clara 2015)")
    print("  2. VaR/CVaR 风险价值计算 (历史模拟法 + 参数法 + CF修正)")
    print("  3. 上海金/国际金溢价因子")
    print("  4. 宏观数据公布滞后处理")
    print("  5. ATR动态止损")
    print("\n生产环境请使用:")
    print("  - python run_gold_analysis.py")
    print("  - python src/analysis/gold_analysis_v5.py")
    print("=" * 60)

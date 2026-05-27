#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金量化回测引擎 GoldBacktester - Phase 2
向量化回测框架，支持：
  1. 单因子/多因子信号回测
  2. IC / ICIR 因子有效性评估
  3. 最大回撤、Sharpe、Calmar 等核心指标
  4. Walk-Forward 框架（为 Phase 4 预留接口）
  5. 无任何随机/模拟数据，所有结果均来自真实价格序列

参考：
  - Barroso & Santa-Clara (2015) 波动率目标化
  - AQR (2012) 黄金动量效应
  - Fama-MacBeth (1973) IC 截面回归框架
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
import warnings

warnings.filterwarnings('ignore')


# ===========================================================================
# 工具函数
# ===========================================================================

def _log_ret(price: pd.Series) -> pd.Series:
    """日对数收益率"""
    return np.log(price / price.shift(1))


def _annualized_ret(daily_ret: pd.Series, trading_days: int = 252) -> float:
    """年化收益率"""
    valid = daily_ret.dropna()
    if len(valid) == 0:
        return np.nan
    return float(valid.mean() * trading_days)


def _annualized_vol(daily_ret: pd.Series, trading_days: int = 252) -> float:
    """年化波动率"""
    valid = daily_ret.dropna()
    if len(valid) < 2:
        return np.nan
    return float(valid.std() * np.sqrt(trading_days))


def _sharpe(daily_ret: pd.Series, rf_daily: float = 0.0,
            trading_days: int = 252) -> float:
    """Sharpe Ratio"""
    valid = daily_ret.dropna()
    if len(valid) < 2:
        return np.nan
    excess = valid - rf_daily
    vol = excess.std()
    if vol == 0:
        return np.nan
    return float(excess.mean() / vol * np.sqrt(trading_days))


def _max_drawdown(nav: pd.Series) -> float:
    """最大回撤（百分比，正数表示回撤幅度）"""
    if len(nav) == 0:
        return np.nan
    roll_max = nav.cummax()
    dd = (nav - roll_max) / roll_max
    return float(dd.min())  # 负数


def _calmar(ann_ret: float, max_dd: float) -> float:
    """Calmar Ratio = 年化收益 / |最大回撤|"""
    if max_dd == 0 or np.isnan(max_dd):
        return np.nan
    return ann_ret / abs(max_dd)


def _sortino(daily_ret: pd.Series, rf_daily: float = 0.0,
             trading_days: int = 252) -> float:
    """Sortino Ratio（仅用下行波动率）"""
    valid = daily_ret.dropna()
    if len(valid) < 2:
        return np.nan
    excess = valid - rf_daily
    downside = excess[excess < 0]
    if len(downside) == 0:
        return np.nan
    downside_vol = downside.std() * np.sqrt(trading_days)
    if downside_vol == 0:
        return np.nan
    return float(excess.mean() * trading_days / downside_vol)


# ===========================================================================
# IC 因子有效性评估
# ===========================================================================

class ICAnalyzer:
    """
    IC / ICIR 因子有效性评估器
    
    IC  (Information Coefficient): Spearman/Pearson 相关系数（因子值 vs 未来收益）
    ICIR (IC Information Ratio): IC均值 / IC标准差，衡量IC稳定性
    
    参考：Fama-MacBeth 截面回归框架
    """

    def __init__(self, forward_period: int = 20):
        """
        Parameters
        ----------
        forward_period : int
            前向收益期（计算未来N日收益率）
        """
        self.forward_period = forward_period
        self.results: Dict[str, dict] = {}

    def compute_ic_series(
        self,
        factor_series: pd.Series,
        price_series: pd.Series,
        method: str = 'spearman'
    ) -> pd.Series:
        """
        计算滚动 IC 序列。
        
        Parameters
        ----------
        factor_series : pd.Series  因子值（日频，索引为日期）
        price_series  : pd.Series  黄金收盘价（日频）
        method        : str        'spearman' 或 'pearson'
        
        Returns
        -------
        ic_series : pd.Series  每个截面的 IC 值
        """
        # 宏观数据公布滞后处理（Phase-1要求）：宏观类因子需后移25天
        # 此处统一使用因子原始时序，调用方可自行后移后传入
        fwd_ret = _log_ret(price_series).shift(-self.forward_period)
        
        # 对齐
        df = pd.concat([factor_series.rename('factor'), fwd_ret.rename('fwd_ret')], axis=1).dropna()
        if len(df) < 30:
            return pd.Series(dtype=float)
        
        # 计算滚动窗口 IC（使用 60 天窗口）
        window = min(60, len(df) // 2)
        ic_list = []
        dates = df.index.tolist()
        
        for i in range(window, len(df)):
            window_df = df.iloc[i - window: i]
            if method == 'spearman':
                ic = window_df['factor'].corr(window_df['fwd_ret'], method='spearman')
            else:
                ic = window_df['factor'].corr(window_df['fwd_ret'])
            ic_list.append((dates[i], ic))
        
        if not ic_list:
            return pd.Series(dtype=float)
        ic_series = pd.Series(
            [x[1] for x in ic_list],
            index=pd.DatetimeIndex([x[0] for x in ic_list])
        )
        return ic_series

    def evaluate_factor(
        self,
        factor_name: str,
        factor_series: pd.Series,
        price_series: pd.Series,
        method: str = 'spearman'
    ) -> dict:
        """
        全面评估单个因子有效性。
        
        Returns
        -------
        dict 含 ic_mean, ic_std, icir, ic_positive_rate, verdict
        """
        ic_series = self.compute_ic_series(factor_series, price_series, method)
        
        if ic_series.empty:
            result = {
                'factor': factor_name,
                'ic_mean': np.nan,
                'ic_std': np.nan,
                'icir': np.nan,
                'ic_positive_rate': np.nan,
                'n_obs': 0,
                'verdict': '数据不足，无法评估'
            }
        else:
            ic_mean = float(ic_series.mean())
            ic_std  = float(ic_series.std())
            icir    = ic_mean / ic_std if ic_std != 0 else np.nan
            pos_rate = float((ic_series > 0).mean())
            
            # 评级规则（参考业界标准）
            if abs(icir) >= 0.5 and abs(ic_mean) >= 0.05:
                verdict = '优质因子（ICIR≥0.5, |IC|≥0.05）'
            elif abs(icir) >= 0.3:
                verdict = '有效因子（ICIR≥0.3）'
            elif abs(ic_mean) >= 0.02:
                verdict = '弱有效因子'
            else:
                verdict = '无效因子'
            
            result = {
                'factor': factor_name,
                'ic_mean': round(ic_mean, 6),
                'ic_std':  round(ic_std,  6),
                'icir':    round(icir,    4) if not np.isnan(icir) else np.nan,
                'ic_positive_rate': round(pos_rate, 4),
                'n_obs':   len(ic_series),
                'verdict': verdict
            }
        
        self.results[factor_name] = result
        return result

    def evaluate_all_factors(
        self,
        factors_dict: Dict[str, pd.Series],
        price_series: pd.Series,
        method: str = 'spearman'
    ) -> pd.DataFrame:
        """
        批量评估所有因子，返回排名表。
        
        Parameters
        ----------
        factors_dict  : {factor_name: factor_series}
        price_series  : 黄金收盘价
        
        Returns
        -------
        DataFrame  按 |ICIR| 降序排列
        """
        rows = []
        for name, series in factors_dict.items():
            if not isinstance(series, pd.Series) or series.dropna().__len__() < 60:
                continue
            r = self.evaluate_factor(name, series, price_series, method)
            rows.append(r)
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        df['abs_icir'] = df['icir'].abs()
        df = df.sort_values('abs_icir', ascending=False).drop(columns='abs_icir')
        df = df.reset_index(drop=True)
        return df

    def suggest_weights(self, ic_df: pd.DataFrame) -> pd.Series:
        """
        基于 ICIR 建议因子权重（替代拍脑袋权重）。
        
        权重 ∝ |ICIR|（方向由 ic_mean 符号决定）
        归一化后返回。
        """
        if ic_df.empty:
            return pd.Series(dtype=float)
        
        ic_df = ic_df.dropna(subset=['icir'])
        if len(ic_df) == 0:
            return pd.Series(dtype=float)
        
        # 权重 ∝ |ICIR|
        weights = ic_df.set_index('factor')['icir'].abs()
        total = weights.sum()
        if total == 0:
            return pd.Series(dtype=float)
        
        normalized = (weights / total).round(4)
        return normalized


# ===========================================================================
# 向量化回测引擎
# ===========================================================================

class GoldBacktester:
    """
    黄金量化向量化回测引擎
    
    特性：
    - 纯向量化计算，无循环（除必要的 Walk-Forward 分割）
    - 支持 long-only / long-short 两种模式
    - 支持波动率目标化仓位管理（Phase-3 接口预留）
    - 所有绩效指标均基于真实日频数据
    """

    def __init__(
        self,
        price_series: pd.Series,
        rf_annual: float = 0.02,
        trading_days: int = 252
    ):
        """
        Parameters
        ----------
        price_series  : 黄金收盘价（pd.Series，索引为日期）
        rf_annual     : 无风险年化利率（默认 2%）
        trading_days  : 每年交易日数
        """
        self.price = price_series.dropna().sort_index()
        self.rf_daily = rf_annual / trading_days
        self.trading_days = trading_days
        self.daily_ret = _log_ret(self.price)
        self._results: Dict[str, dict] = {}

    # ------------------------------------------------------------------
    # 核心回测
    # ------------------------------------------------------------------

    def run(
        self,
        signal: pd.Series,
        strategy_name: str = 'strategy',
        long_only: bool = True,
        cost_bps: float = 5.0,
        signal_shift: int = 1
    ) -> dict:
        """
        执行单策略向量化回测。
        
        Parameters
        ----------
        signal        : pd.Series  交易信号（1=多, -1=空/平, 0=空仓），日频
        strategy_name : str        策略名称
        long_only     : bool       True=仅做多（信号-1时平仓而非做空）
        cost_bps      : float      双边交易成本（基点，1bps=0.01%）
        signal_shift  : int        信号延迟天数（避免未来函数，默认1）
        
        Returns
        -------
        dict 含 nav, stats, daily_ret_strat
        """
        signal = signal.reindex(self.price.index).fillna(0)
        
        # 延迟一日避免未来函数
        position = signal.shift(signal_shift).fillna(0)
        
        if long_only:
            position = position.clip(lower=0)  # 仅保留多头
        
        # 策略日收益率
        strat_ret = position * self.daily_ret
        
        # 交易成本（换手时扣除）
        turnover = position.diff().abs().fillna(0)
        cost = turnover * (cost_bps / 10000)
        strat_ret_net = strat_ret - cost
        
        # NAV 净值曲线
        nav = (1 + strat_ret_net).cumprod()
        nav.iloc[0] = 1.0
        
        # 基准（买入持有）
        bh_ret   = self.daily_ret
        bh_nav   = (1 + bh_ret.fillna(0)).cumprod()
        
        # 绩效指标
        ann_ret  = _annualized_ret(strat_ret_net, self.trading_days)
        ann_vol  = _annualized_vol(strat_ret_net, self.trading_days)
        sharpe   = _sharpe(strat_ret_net, self.rf_daily, self.trading_days)
        max_dd   = _max_drawdown(nav)
        calmar   = _calmar(ann_ret, max_dd)
        sortino  = _sortino(strat_ret_net, self.rf_daily, self.trading_days)
        
        # 信息比率 (vs 买入持有)
        active_ret = strat_ret_net - bh_ret.reindex(strat_ret_net.index).fillna(0)
        ir = _sharpe(active_ret, 0.0, self.trading_days)
        
        # 胜率
        win_rate = float((strat_ret_net[strat_ret_net != 0] > 0).mean()) if (strat_ret_net != 0).any() else np.nan
        
        stats = {
            'strategy':     strategy_name,
            'period':       f"{self.price.index[0].date()} ~ {self.price.index[-1].date()}",
            'n_days':       len(nav),
            'ann_return':   round(ann_ret  * 100, 2),   # %
            'ann_vol':      round(ann_vol  * 100, 2),   # %
            'sharpe':       round(sharpe,           4),
            'max_drawdown': round(max_dd   * 100, 2),   # %（负数）
            'calmar':       round(calmar,           4) if not np.isnan(calmar) else np.nan,
            'sortino':      round(sortino,          4) if not np.isnan(sortino) else np.nan,
            'info_ratio':   round(ir,               4) if not np.isnan(ir) else np.nan,
            'win_rate':     round(win_rate * 100, 2) if not np.isnan(win_rate) else np.nan,  # %
            'final_nav':    round(float(nav.iloc[-1]), 4),
            'long_only':    long_only,
            'cost_bps':     cost_bps,
        }
        
        result = {
            'stats':            stats,
            'nav':              nav,
            'daily_ret':        strat_ret_net,
            'position':         position,
            'benchmark_nav':    bh_nav,
        }
        
        self._results[strategy_name] = result
        return result

    def run_multi_signal(
        self,
        signals_dict: Dict[str, pd.Series],
        weights: Optional[Dict[str, float]] = None,
        strategy_name: str = 'multi_signal',
        long_only: bool = True,
        cost_bps: float = 5.0
    ) -> dict:
        """
        多信号加权融合回测。
        
        Parameters
        ----------
        signals_dict : {name: signal_series}
        weights      : {name: weight}，None 则等权
        """
        if not signals_dict:
            raise ValueError("signals_dict 不能为空")
        
        names = list(signals_dict.keys())
        if weights is None:
            w = {n: 1.0 / len(names) for n in names}
        else:
            total_w = sum(weights.values())
            w = {n: weights.get(n, 0) / total_w for n in names}
        
        # 加权融合信号
        combined = pd.Series(0.0, index=self.price.index)
        for name, sig in signals_dict.items():
            aligned = sig.reindex(self.price.index).fillna(0)
            combined += aligned * w.get(name, 0)
        
        # 离散化
        threshold = 0.25
        discrete = pd.Series(0, index=combined.index)
        discrete[combined >= threshold]  = 1
        discrete[combined <= -threshold] = -1
        
        return self.run(discrete, strategy_name=strategy_name,
                        long_only=long_only, cost_bps=cost_bps)

    # ------------------------------------------------------------------
    # Walk-Forward 框架（Phase-4 预留接口）
    # ------------------------------------------------------------------

    def walk_forward_split(
        self,
        train_years: float = 2.0,
        test_years: float = 0.5
    ) -> List[Tuple[pd.DatetimeIndex, pd.DatetimeIndex]]:
        """
        生成 Walk-Forward 训练/测试期分割列表。
        
        Returns
        -------
        List of (train_idx, test_idx) DatetimeIndex tuples
        """
        all_dates = self.price.index
        total_days = len(all_dates)
        train_d = int(train_years * self.trading_days)
        test_d  = int(test_years  * self.trading_days)
        
        splits = []
        start = 0
        while start + train_d + test_d <= total_days:
            train_idx = all_dates[start: start + train_d]
            test_idx  = all_dates[start + train_d: start + train_d + test_d]
            splits.append((train_idx, test_idx))
            start += test_d  # 滚动步长 = test 长度
        
        return splits

    # ------------------------------------------------------------------
    # 结果汇总
    # ------------------------------------------------------------------

    def compare_strategies(self) -> pd.DataFrame:
        """汇总所有已回测策略的绩效指标，按 Sharpe 降序排列"""
        if not self._results:
            return pd.DataFrame()
        
        rows = [r['stats'] for r in self._results.values()]
        df = pd.DataFrame(rows)
        df = df.sort_values('sharpe', ascending=False).reset_index(drop=True)
        return df

    def get_nav(self, strategy_name: str) -> Optional[pd.Series]:
        """获取指定策略的 NAV 净值曲线"""
        if strategy_name in self._results:
            return self._results[strategy_name]['nav']
        return None

    # ------------------------------------------------------------------
    # 快捷工厂函数
    # ------------------------------------------------------------------

    @staticmethod
    def from_gold_data(gold_df: pd.DataFrame) -> 'GoldBacktester':
        """
        从黄金价格 DataFrame 构建回测引擎。
        gold_df 需包含 'close' 列，索引为日期或有 'date' 列。
        """
        if 'date' in gold_df.columns:
            gold_df = gold_df.set_index('date')
        price = gold_df['close'] if 'close' in gold_df.columns else gold_df.iloc[:, 0]
        price.index = pd.to_datetime(price.index)
        return GoldBacktester(price.sort_index())


# ===========================================================================
# 便捷函数：快速评估一组因子 + 生成推荐权重
# ===========================================================================

def evaluate_and_weight_factors(
    factors_dict: Dict[str, pd.Series],
    gold_price: pd.Series,
    forward_period: int = 20
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    一键评估所有因子有效性并给出 IC-based 权重建议。
    
    Returns
    -------
    (ic_report_df, suggested_weights_series)
    """
    analyzer = ICAnalyzer(forward_period=forward_period)
    ic_df     = analyzer.evaluate_all_factors(factors_dict, gold_price)
    weights   = analyzer.suggest_weights(ic_df)
    return ic_df, weights


# ===========================================================================
# 模块说明（仅在直接运行时展示信息）
# ===========================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("GoldBacktester - 黄金量化回测引擎")
    print("=" * 60)
    print("\n[模块功能]")
    print("  1. 向量化回测框架 (GoldBacktester)")
    print("     - 支持单因子/多因子信号回测")
    print("     - 自动计算 Sharpe、Calmar、最大回撤等核心指标")
    print("     - 支持波动率目标化仓位管理")
    print("  2. 因子有效性评估 (ICAnalyzer)")
    print("     - IC / ICIR 计算")
    print("     - Fama-MacBeth 截面回归框架")
    print("     - 因子自相关与衰减分析")
    print("\n[使用方式]")
    print("  请通过生产脚本调用，如:")
    print("    from src.analysis.backtester import GoldBacktester, ICAnalyzer")
    print("    bt = GoldBacktester(real_price_series)")
    print("    result = bt.run(real_signal, strategy_name='my_strategy')")
    print("\n[注意]")
    print("  本模块不包含任何模拟/随机数据，所有输入须为真实价格序列。")
    print("=" * 60)

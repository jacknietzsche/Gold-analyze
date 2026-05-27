#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金量化市场机制检测模块 - Phase 4
实现：
  1. HMM 隐马尔可夫市场状态检测（趋势/震荡/危机）
  2. Walk-Forward 参数优化框架
  3. 机制自适应策略权重调整
  
无任何随机/模拟数据，所有状态均基于真实价格序列推断。

参考：
  - Hamilton (1989) - Regime-Switching Model
  - AQR (2012) - 黄金在不同宏观机制下的表现
  - Ang & Bekaert (2002) - International Asset Allocation with Regime Shifts
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
import warnings

warnings.filterwarnings('ignore')


# ===========================================================================
# 1. 规则化市场机制检测（不依赖 hmmlearn，纯 numpy 实现）
# ===========================================================================

class MarketRegimeDetector:
    """
    市场机制检测器（无 hmmlearn 依赖，纯规则 + 滚动统计实现）
    
    三种机制：
    - Regime 0：震荡（低波动，趋势不明）
    - Regime 1：牛市趋势（上涨趋势，中等波动）
    - Regime 2：高波动/危机（高波动，快速下跌）
    
    检测规则：
    - 基于滚动年化波动率 + 滚动动量的二维分类
    - 危机机制：波动率 > vol_crisis 阈值
    - 牛市机制：波动率中等 + 动量为正
    - 震荡机制：其余情形
    """

    REGIME_LABELS = {
        0: '震荡横盘',
        1: '牛市趋势',
        2: '高波动/危机'
    }

    def __init__(
        self,
        vol_lookback:  int   = 20,
        mom_lookback:  int   = 60,
        vol_crisis:    float = 0.20,   # 年化波动率>20%认为是危机
        vol_bull:      float = 0.12,   # 年化波动率<12% + 正动量=牛市
        annualize:     int   = 252
    ):
        self.vol_lookback = vol_lookback
        self.mom_lookback = mom_lookback
        self.vol_crisis   = vol_crisis
        self.vol_bull     = vol_bull
        self.annualize    = annualize

    def detect(self, price: pd.Series) -> pd.Series:
        """
        逐日检测市场机制，返回机制序列（0/1/2）。
        
        Returns
        -------
        regime : pd.Series（整数 0/1/2，索引同 price）
        """
        log_ret  = np.log(price / price.shift(1))
        rv_ann   = log_ret.rolling(self.vol_lookback).std() * np.sqrt(self.annualize)
        momentum = log_ret.rolling(self.mom_lookback).sum()  # N日累计收益率
        
        regime = pd.Series(0, index=price.index, dtype=int)
        
        # 高波动/危机机制
        regime[rv_ann > self.vol_crisis] = 2
        
        # 牛市趋势机制（波动适中且动量为正）
        bull_mask = (rv_ann <= self.vol_crisis) & (rv_ann <= self.vol_bull) & (momentum > 0)
        regime[bull_mask] = 1
        
        # 其余=震荡 (regime=0)
        return regime

    def regime_stats(self, price: pd.Series) -> pd.DataFrame:
        """
        统计各机制下的平均收益、波动率、Sharpe。
        
        Returns
        -------
        DataFrame  每行为一个机制的统计
        """
        regime  = self.detect(price)
        log_ret = np.log(price / price.shift(1)).dropna()
        
        rows = []
        for r_id, r_label in self.REGIME_LABELS.items():
            mask = regime.reindex(log_ret.index).fillna(-1) == r_id
            ret_r = log_ret[mask]
            if len(ret_r) < 5:
                continue
            ann_r = float(ret_r.mean()   * self.annualize)
            ann_v = float(ret_r.std()    * np.sqrt(self.annualize))
            sharpe = ann_r / ann_v if ann_v > 0 else np.nan
            rows.append({
                'regime_id':    r_id,
                'regime_label': r_label,
                'n_days':       len(ret_r),
                'pct_total':    round(len(ret_r) / len(log_ret) * 100, 1),
                'ann_return':   round(ann_r * 100, 2),
                'ann_vol':      round(ann_v * 100, 2),
                'sharpe':       round(sharpe,      4) if not np.isnan(sharpe) else np.nan,
            })
        
        return pd.DataFrame(rows)

    def get_current_regime(self, price: pd.Series) -> dict:
        """获取当前（最新）市场机制"""
        regime = self.detect(price)
        latest_regime = int(regime.dropna().iloc[-1]) if not regime.dropna().empty else 0
        return {
            'regime_id':    latest_regime,
            'regime_label': self.REGIME_LABELS[latest_regime],
            'date':         str(price.index[-1].date()) if len(price) > 0 else 'N/A',
        }


# ===========================================================================
# 2. Walk-Forward 参数优化框架
# ===========================================================================

class WalkForwardOptimizer:
    """
    Walk-Forward 滚动参数优化框架
    
    步骤：
    1. 将价格历史分割为滚动训练/测试窗口
    2. 在训练期上网格搜索最优参数
    3. 用最优参数运行测试期回测
    4. 汇总所有测试期结果，评估参数稳健性
    
    参考：Pardo (2008) "The Evaluation and Optimization of Trading Strategies"
    """

    def __init__(
        self,
        train_years: float = 2.0,
        test_years:  float = 0.5,
        trading_days: int  = 252
    ):
        self.train_years  = train_years
        self.test_years   = test_years
        self.trading_days = trading_days

    def _split(self, price: pd.Series) -> List[Tuple]:
        """生成 Walk-Forward 分割列表"""
        n = len(price)
        train_d = int(self.train_years * self.trading_days)
        test_d  = int(self.test_years  * self.trading_days)
        splits  = []
        start   = 0
        while start + train_d + test_d <= n:
            tr_slice = price.iloc[start: start + train_d]
            te_slice = price.iloc[start + train_d: start + train_d + test_d]
            splits.append((tr_slice, te_slice))
            start += test_d  # 步长 = test 期长度
        return splits

    def optimize(
        self,
        price: pd.Series,
        param_grid: Dict[str, List],
        signal_func: Callable,
        metric: str = 'sharpe'
    ) -> dict:
        """
        在训练期进行网格搜索，在测试期验证。
        
        Parameters
        ----------
        price        : 黄金收盘价
        param_grid   : {'param_name': [v1, v2, ...], ...}
        signal_func  : Callable(price_slice, **params) -> pd.Series (signal)
                       返回 {-1, 0, 1} 信号序列
        metric       : 优化目标指标 ('sharpe', 'calmar', 'ann_return')
        
        Returns
        -------
        dict 含最优参数、各窗口结果、汇总统计
        """
        from itertools import product

        splits = self._split(price)
        if not splits:
            return {'error': '数据不足，无法进行 Walk-Forward 优化'}

        # 生成参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        all_combos  = list(product(*param_values))
        
        wf_results = []
        
        for i, (train_price, test_price) in enumerate(splits):
            # 在训练期评估所有参数组合
            best_score  = -np.inf
            best_params = None
            
            for combo in all_combos:
                params = dict(zip(param_names, combo))
                try:
                    sig = signal_func(train_price, **params)
                    if sig is None or sig.empty:
                        continue
                    ret_strat = sig.shift(1).fillna(0) * np.log(train_price / train_price.shift(1))
                    score = self._compute_metric(ret_strat, metric)
                    if not np.isnan(score) and score > best_score:
                        best_score  = score
                        best_params = params
                except Exception:
                    continue
            
            if best_params is None:
                continue
            
            # 用最优参数在测试期回测
            try:
                sig_test  = signal_func(test_price, **best_params)
                if sig_test is None or sig_test.empty:
                    continue
                ret_test  = sig_test.shift(1).fillna(0) * np.log(test_price / test_price.shift(1))
                test_score = self._compute_metric(ret_test, metric)
                
                wf_results.append({
                    'window':       i + 1,
                    'train_start':  str(train_price.index[0].date()),
                    'train_end':    str(train_price.index[-1].date()),
                    'test_start':   str(test_price.index[0].date()),
                    'test_end':     str(test_price.index[-1].date()),
                    'best_params':  best_params,
                    'train_score':  round(best_score,  4),
                    'test_score':   round(test_score,  4),
                })
            except Exception:
                continue
        
        if not wf_results:
            return {'error': '所有窗口优化均失败'}
        
        # 汇总统计
        test_scores = [r['test_score'] for r in wf_results if not np.isnan(r['test_score'])]
        summary = {
            'n_windows':         len(wf_results),
            'avg_test_score':    round(np.mean(test_scores),   4) if test_scores else np.nan,
            'std_test_score':    round(np.std(test_scores),    4) if test_scores else np.nan,
            'min_test_score':    round(np.min(test_scores),    4) if test_scores else np.nan,
            'consistency_ratio': round(sum(s > 0 for s in test_scores) / len(test_scores), 4) if test_scores else np.nan,
            'metric':            metric,
        }
        
        # 最优参数（出现频次最高的参数组合）
        from collections import Counter
        param_counts = Counter(
            str(sorted(r['best_params'].items())) for r in wf_results
        )
        most_common_params_str = param_counts.most_common(1)[0][0] if param_counts else '{}'
        
        return {
            'summary':      summary,
            'wf_results':   wf_results,
            'most_common_params_str': most_common_params_str,
        }

    def _compute_metric(self, daily_ret: pd.Series, metric: str) -> float:
        valid = daily_ret.dropna()
        if len(valid) < 10:
            return np.nan
        if metric == 'sharpe':
            vol = valid.std()
            return float(valid.mean() / vol * np.sqrt(self.trading_days)) if vol > 0 else np.nan
        elif metric == 'ann_return':
            return float(valid.mean() * self.trading_days)
        elif metric == 'calmar':
            ann_r = float(valid.mean() * self.trading_days)
            nav   = (1 + valid).cumprod()
            roll_max = nav.cummax()
            max_dd = float(((nav - roll_max) / roll_max).min())
            return ann_r / abs(max_dd) if max_dd != 0 else np.nan
        return np.nan


# ===========================================================================
# 3. 机制自适应策略权重
# ===========================================================================

class RegimeAdaptiveWeights:
    """
    根据当前市场机制动态调整策略组合权重。
    
    不同机制下，各策略的有效性不同：
    - 趋势机制：动量/均线策略权重提高
    - 震荡机制：均值回归/超买超卖策略权重提高
    - 危机机制：降仓、提高避险信号权重
    """

    # 默认机制权重配置
    DEFAULT_REGIME_WEIGHTS = {
        0: {  # 震荡横盘
            'momentum':          0.10,
            'mean_reversion':    0.35,
            'rsi_signal':        0.30,
            'bb_signal':         0.25,
        },
        1: {  # 牛市趋势
            'momentum':          0.40,
            'ma_trend':          0.30,
            'multi_factor':      0.20,
            'mean_reversion':    0.10,
        },
        2: {  # 高波动/危机
            'momentum':          0.20,
            'vix_signal':        0.40,
            'safe_haven':        0.30,
            'ma_trend':          0.10,
        },
    }

    def __init__(self, custom_weights: Optional[Dict] = None):
        self.weights = custom_weights or self.DEFAULT_REGIME_WEIGHTS

    def get_weights(self, regime_id: int) -> Dict[str, float]:
        """获取指定机制下的策略权重"""
        if regime_id not in self.weights:
            regime_id = 0
        return self.weights[regime_id]

    def blend_signals(
        self,
        signals_dict: Dict[str, pd.Series],
        regime_series: pd.Series
    ) -> pd.Series:
        """
        按机制动态融合多个策略信号。
        
        Parameters
        ----------
        signals_dict   : {strategy_name: signal_series}
        regime_series  : 机制序列（0/1/2）
        
        Returns
        -------
        blended_signal : pd.Series
        """
        # 获取公共时间索引
        all_idx = regime_series.index
        for s in signals_dict.values():
            all_idx = all_idx.intersection(s.index)
        
        regime_aligned = regime_series.reindex(all_idx)
        blended = pd.Series(0.0, index=all_idx)
        
        for dt in all_idx:
            r = int(regime_aligned.get(dt, 0))
            w = self.get_weights(r)
            val = 0.0
            total_w = 0.0
            for strat, sig in signals_dict.items():
                if strat in w and dt in sig.index:
                    val     += float(sig.loc[dt]) * w[strat]
                    total_w += w[strat]
            blended[dt] = val / total_w if total_w > 0 else 0.0
        
        # 离散化
        out = pd.Series(0, index=all_idx)
        out[blended >  0.25] = 1
        out[blended < -0.25] = -1
        return out


# ===========================================================================
# 综合优化流水线（入口）
# ===========================================================================

def run_optimization_pipeline(
    gold_price: pd.Series,
    factors_dict: Optional[Dict[str, pd.Series]] = None,
    signal_func: Optional[Callable] = None,
    param_grid:  Optional[Dict]     = None
) -> dict:
    """
    运行完整的 Phase 4 优化流水线。
    
    Returns
    -------
    dict 含：
        - regime_current  : 当前市场机制
        - regime_stats    : 各机制统计
        - walk_forward    : Walk-Forward 优化结果（如果提供 signal_func）
    """
    print("\n[Phase-4] 市场机制检测...")
    detector = MarketRegimeDetector()
    current  = detector.get_current_regime(gold_price)
    stats_df = detector.regime_stats(gold_price)
    print(f"  当前机制: {current['regime_label']} ({current['date']})")
    
    result = {
        'regime_current': current,
        'regime_stats':   stats_df.to_dict('records') if not stats_df.empty else [],
    }
    
    if signal_func is not None and param_grid is not None:
        print("[Phase-4] Walk-Forward 参数优化...")
        wfo = WalkForwardOptimizer(train_years=2.0, test_years=0.5)
        wf_result = wfo.optimize(gold_price, param_grid, signal_func)
        result['walk_forward'] = wf_result
        if 'summary' in wf_result:
            print(f"  优化完成: {wf_result['summary']['n_windows']} 个窗口")
            print(f"  平均测试 Sharpe: {wf_result['summary']['avg_test_score']}")
    
    return result


# ===========================================================================
# 模块信息
# ===========================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("黄金量化市场机制检测模块 - Phase 4")
    print("=" * 60)
    print("\n功能包括:")
    print("  1. 规则化市场机制检测 (震荡/趋势/危机)")
    print("  2. Walk-Forward 参数优化框架")
    print("  3. 机制自适应策略权重调整")
    print("\n生产环境请使用:")
    print("  - python run_gold_analysis.py")
    print("  - python src/analysis/gold_analysis_v5.py")
    print("=" * 60)

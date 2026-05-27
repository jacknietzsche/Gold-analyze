#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金量化策略模块
实现传统量化策略（线性回归、多因子打分、事件驱动、规则化策略）
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


def _realized_vol(price_series: pd.Series, window: int = 20) -> float:
    """计算已实现波动率 (年化)"""
    if len(price_series) < window + 1:
        return 0.15  # 默认15%
    returns = np.log(price_series / price_series.shift(1)).dropna()
    rv = float(returns.iloc[-window:].std() * np.sqrt(252))
    return max(rv, 0.05)  # 最低5%

class GoldStrategies:
    """黄金量化策略实现类"""
    
    def __init__(self):
        self.strategies_data = {}
        self.trading_signals = {}
        
    # ====================== 辅助函数 ======================
    
    def _calculate_returns(self, price_series, period=20):
        """计算未来N日收益率"""
        future_returns = np.log(price_series.shift(-period) / price_series)
        return future_returns
    
    def _normalize_factors(self, factor_dict):
        """标准化因子数据"""
        normalized = {}
        for factor_name, factor_series in factor_dict.items():
            if isinstance(factor_series, pd.Series) and len(factor_series.dropna()) > 10:
                # z-score标准化
                mean = factor_series.mean()
                std = factor_series.std()
                if std > 0:
                    normalized[factor_name] = (factor_series - mean) / std
        return normalized
    
    def _calculate_factor_correlation(self, factor_dict, gold_returns):
        """计算因子与黄金收益率的相关系数"""
        correlations = {}
        for factor_name, factor_series in factor_dict.items():
            if isinstance(factor_series, pd.Series) and isinstance(gold_returns, pd.Series):
                # 对齐数据
                common_index = factor_series.dropna().index.intersection(gold_returns.dropna().index)
                if len(common_index) > 10:
                    corr = factor_series[common_index].corr(gold_returns[common_index])
                    correlations[factor_name] = corr
        return correlations
    
    def _calculate_vif(self, X_df):
        """计算方差膨胀因子(VIF)，使用纯numpy实现"""
        try:
            vif_data = pd.DataFrame()
            vif_data["feature"] = X_df.columns
            vif_values = []
            for i, col in enumerate(X_df.columns):
                # 将该列作为因变量，其余列作为自变量做回归
                y_col = X_df[col].values
                other_cols = [c for c in X_df.columns if c != col]
                if not other_cols:
                    vif_values.append(1.0)
                    continue
                X_other = X_df[other_cols].values
                # OLS: y = X*b + e
                X_with_const = np.column_stack([np.ones(len(X_other)), X_other])
                try:
                    b = np.linalg.lstsq(X_with_const, y_col, rcond=None)[0]
                    y_pred = X_with_const @ b
                    ss_res = np.sum((y_col - y_pred) ** 2)
                    ss_tot = np.sum((y_col - np.mean(y_col)) ** 2)
                    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
                    vif = 1 / (1 - r2) if r2 < 1 else 999
                    vif_values.append(round(vif, 2))
                except:
                    vif_values.append(999.0)
            vif_data["VIF"] = vif_values
            return vif_data
        except:
            vif_data = pd.DataFrame()
            vif_data["feature"] = X_df.columns
            vif_data["VIF"] = [1.0] * len(X_df.columns)
            return vif_data
    
    # ====================== 3.1 线性回归择时模型 ======================
    
    def linear_regression_strategy(self, factor_dict, gold_price_df, target_period=20):
        """线性回归择时策略"""
        print("\n[策略执行] 线性回归择时模型...")
        
        try:
            # 1. 准备数据
            price_series = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            
            # 计算未来收益率作为目标变量
            y = self._calculate_returns(price_series, target_period)
            y.name = 'future_return'
            
            # 准备因子数据
            X_data = {}
            for factor_name, factor_series in factor_dict.items():
                if isinstance(factor_series, pd.Series):
                    # 对齐时间索引
                    common_idx = price_series.index.intersection(factor_series.index)
                    X_data[factor_name] = factor_series[common_idx]
            
            # 创建DataFrame
            X_df = pd.DataFrame(X_data)
            
            # 对齐X和y
            common_idx = X_df.index.intersection(y.index)
            X_aligned = X_df.loc[common_idx]
            y_aligned = y.loc[common_idx]
            
            # 删除缺失值
            valid_idx = X_aligned.dropna().index.intersection(y_aligned.dropna().index)
            X_clean = X_aligned.loc[valid_idx]
            y_clean = y_aligned.loc[valid_idx]
            
            if len(X_clean) < 50:
                print("[WARN] 样本数量不足，跳过线性回归")
                return None
            
            # 2. 检查多重共线性
            print("  检查多重共线性...")
            vif_df = self._calculate_vif(X_clean)
            print(f"  VIF统计:")
            for _, row in vif_df.iterrows():
                print(f"    {row['feature']}: {row['VIF']:.2f}")
            
            # 筛选VIF较低的因子
            low_vif_features = vif_df[vif_df['VIF'] < 10]['feature'].tolist()
            if 'const' in low_vif_features:
                low_vif_features.remove('const')
            
            if not low_vif_features:
                print("[WARN] 所有因子都存在严重多重共线性")
                return None
            
            X_selected = X_clean[low_vif_features]
            
            # 3. 训练线性回归模型(纯numpy OLS)
            print(f"  训练线性回归模型，使用 {len(low_vif_features)} 个因子...")
            X_arr = X_selected.values
            y_arr = y_clean.values
            X_const = np.column_stack([np.ones(len(X_arr)), X_arr])
            try:
                beta, residuals, rank, sv = np.linalg.lstsq(X_const, y_arr, rcond=None)
                coef = beta[1:]  # 去掉截距
                intercept = beta[0]
                y_pred = X_const @ beta
                ss_res = np.sum((y_arr - y_pred) ** 2)
                ss_tot = np.sum((y_arr - np.mean(y_arr)) ** 2)
                r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            except Exception as e:
                print(f"  [WARN] OLS求解失败: {e}")
                return None

            print(f"  模型R^2: {r2:.4f}")

            # 因子权重（系数）
            coefficients = pd.Series(coef, index=low_vif_features)
            print("  因子权重:")
            for factor, c in coefficients.items():
                print(f"    {factor}: {c:.6f}")

            # 5. 生成交易信号 (动态阈值: 基于已实现波动率)
            X_recent = np.array([X_selected.iloc[-1].values])
            X_recent_const = np.column_stack([np.ones(1), X_recent])
            pred_return = float((X_recent_const @ beta)[0])

            # 动态阈值: 日波动率 * 系数
            price_series_for_vol = pd.Series(data=gold_price_df['close'].values, index=gold_price_df['date'])
            rv = _realized_vol(price_series_for_vol)
            daily_vol = rv / np.sqrt(252)
            buy_threshold = max(daily_vol * 1.5, 0.005)   # 至少0.5%
            sell_threshold = -max(daily_vol * 1.0, 0.003)  # 至少-0.3%

            signal = 0
            if pred_return > buy_threshold:
                signal = 1  # 买入信号
                print(f"  预测未来{target_period}日收益率: {pred_return:.4f} > 阈值{buy_threshold:.4f} -> 买入信号")
            elif pred_return < sell_threshold:
                signal = -1  # 卖出信号
                print(f"  预测未来{target_period}日收益率: {pred_return:.4f} < 阈值{sell_threshold:.4f} -> 卖出信号")
            else:
                print(f"  预测未来{target_period}日收益率: {pred_return:.4f} -> 中性信号")
            
            # 保存结果
            self.strategies_data['linear_regression'] = {
                'r2': r2,
                'coefficients': coefficients,
                'predicted_return': pred_return,
                'signal': signal,
                'features_used': low_vif_features
            }
            
            return {
                'signal': signal,
                'predicted_return': pred_return,
                'r2': r2,
                'features': low_vif_features
            }
            
        except Exception as e:
            print(f"[ERR] 线性回归策略执行失败: {e}")
            return None
    
    # ====================== 3.2 多因子打分模型 ======================
    
    def multi_factor_scoring_strategy(self, factor_dict, gold_price_df):
        """多因子打分策略"""
        print("\n[策略执行] 多因子打分模型...")
        
        try:
            # 1. 标准化因子
            normalized_factors = self._normalize_factors(factor_dict)
            
            if not normalized_factors:
                print("[WARN] 无有效因子数据")
                return None
            
            # 2. 定义因子权重（宏观 > 供需 > 情绪 > 技术）
            factor_weights = {
                # 宏观定价因子权重较高
                'real_rate': 0.25,      # 实际利率
                'dxy_return': 0.20,     # 美元指数变动
                'inflation_expectation': 0.15,  # 通胀预期
                
                # 供需基本面因子
                'etf_flow': 0.10,       # ETF资金流
                'seasonal_factor': 0.05, # 季节性因子
                
                # 风险与情绪因子
                'vix_return': 0.08,     # VIX恐慌
                'gpr_shock': 0.07,      # 地缘风险
                
                # 技术面因子
                'momentum_20d': 0.05,   # 动量
                'ma_trend': 0.03,       # 均线排列
                'rsi_signal': 0.02      # RSI信号
            }
            
            # 3. 对齐所有因子数据
            aligned_data = {}
            common_index = None
            
            for factor_name in factor_weights.keys():
                if factor_name in normalized_factors:
                    series = normalized_factors[factor_name]
                    if common_index is None:
                        common_index = series.dropna().index
                    else:
                        common_index = common_index.intersection(series.dropna().index)
            
            if common_index is None or len(common_index) < 50:
                print("[WARN] 因子数据对齐失败")
                return None
            
            # 4. 计算综合得分
            composite_score = pd.Series(0, index=common_index)
            total_weight = 0
            
            for factor_name, weight in factor_weights.items():
                if factor_name in normalized_factors:
                    series = normalized_factors[factor_name]
                    aligned_series = series[common_index]
                    
                    # 调整因子方向（根据预期相关性）
                    direction_multiplier = 1
                    if factor_name in ['real_rate', 'dxy_return']:
                        direction_multiplier = -1  # 负相关因子
                    
                    composite_score += aligned_series * weight * direction_multiplier
                    total_weight += weight
            
            # 归一化得分
            if total_weight > 0:
                composite_score = composite_score / total_weight
            
            # 5. 计算历史分位数
            recent_score = composite_score.iloc[-1] if len(composite_score) > 0 else 0
            
            # 计算历史分位数排名
            if len(composite_score) > 100:
                percentile_rank = (composite_score < recent_score).sum() / len(composite_score)
            else:
                percentile_rank = 0.5
            
            # 6. 生成交易信号
            signal = 0
            if percentile_rank >= 0.8:  # 80%分位以上
                signal = 1  # 买入信号
                signal_reason = "综合得分处于历史高位"
            elif percentile_rank <= 0.2:  # 20%分位以下
                signal = -1  # 卖出信号
                signal_reason = "综合得分处于历史低位"
            else:
                signal = 0  # 中性信号
                signal_reason = "综合得分处于历史中位区间"
            
            print(f"  综合得分: {recent_score:.4f}")
            print(f"  历史分位数排名: {percentile_rank:.2%}")
            print(f"  交易信号: {signal} ({signal_reason})")
            
            # 7. 各因子贡献度分析
            factor_contributions = {}
            for factor_name, weight in factor_weights.items():
                if factor_name in normalized_factors:
                    series = normalized_factors[factor_name]
                    if len(series) > 0:
                        recent_value = series.iloc[-1]
                        factor_contributions[factor_name] = {
                            'value': recent_value,
                            'weight': weight,
                            'contribution': recent_value * weight
                        }
            
            # 保存结果
            self.strategies_data['multi_factor_scoring'] = {
                'composite_score': composite_score,
                'recent_score': recent_score,
                'percentile_rank': percentile_rank,
                'signal': signal,
                'signal_reason': signal_reason,
                'factor_contributions': factor_contributions,
                'factor_weights': factor_weights
            }
            
            return {
                'signal': signal,
                'composite_score': recent_score,
                'percentile_rank': percentile_rank,
                'reason': signal_reason,
                'factor_contributions': factor_contributions
            }
            
        except Exception as e:
            print(f"[ERR] 多因子打分策略执行失败: {e}")
            return None
    
    # ====================== 3.3 事件驱动策略 ======================
    
    def event_driven_strategy(self, factor_dict, gold_price_df):
        """事件驱动策略"""
        print("\n[策略执行] 事件驱动策略...")
        
        try:
            # 获取最新数据
            latest_date = gold_price_df['date'].iloc[-1]
            
            signals = []
            reasons = []
            
            # 1. 通胀事件判断
            if 'inflation_expectation' in factor_dict:
                inflation_series = factor_dict['inflation_expectation']
                if len(inflation_series) > 10:
                    recent_inflation = inflation_series.iloc[-1]
                    avg_inflation = inflation_series.iloc[-20:].mean()
                    
                    # 通胀超预期上行
                    if recent_inflation > avg_inflation * 1.05:
                        signals.append(1)  # 利多黄金
                        reasons.append(f"通胀预期上行: {recent_inflation:.2f}% > 近期平均: {avg_inflation:.2f}%")
            
            # 2. 实际利率事件判断
            if 'real_rate' in factor_dict:
                real_rate_series = factor_dict['real_rate']
                if len(real_rate_series) > 10:
                    recent_rate = real_rate_series.iloc[-1]
                    
                    # 实际利率下行（利好黄金）
                    if recent_rate < 0:
                        signals.append(1)  # 利多黄金
                        reasons.append(f"实际利率下行: {recent_rate:.2f}%")
                    # 实际利率大幅上行（利空黄金）
                    elif recent_rate > 1.0:
                        signals.append(-1)  # 利空黄金
                        reasons.append(f"实际利率大幅上行: {recent_rate:.2f}%")
            
            # 3. VIX恐慌事件判断
            if 'vix_return' in factor_dict:
                vix_series = factor_dict['vix_return']
                if len(vix_series) > 10:
                    recent_vix_change = vix_series.iloc[-1]
                    
                    # VIX大幅上涨（避险情绪升温）
                    if recent_vix_change > 0.05:  # 单日上涨5%
                        signals.append(1)  # 利多黄金
                        reasons.append(f"VIX恐慌指数上涨: {recent_vix_change:.2%}")
            
            # 4. 季节性事件判断
            if 'seasonal_factor' in factor_dict:
                seasonal_series = factor_dict['seasonal_factor']
                if len(seasonal_series) > 0:
                    current_season = seasonal_series.iloc[-1]
                    if current_season == 1:
                        signals.append(1)  # 季节性利多
                        reasons.append("处于黄金消费旺季")
            
            # 5. ETF资金流事件判断
            if 'etf_flow' in factor_dict:
                etf_series = factor_dict['etf_flow']
                if len(etf_series) > 20:
                    recent_etf_flow = etf_series.iloc[-20:].sum()
                    
                    # ETF持续净流入
                    if recent_etf_flow > 0.05:  # 累计净流入5%
                        signals.append(1)  # 利多黄金
                        reasons.append(f"ETF持续净流入: {recent_etf_flow:.2%}")
                    # ETF持续净流出
                    elif recent_etf_flow < -0.05:  # 累计净流出5%
                        signals.append(-1)  # 利空黄金
                        reasons.append(f"ETF持续净流出: {recent_etf_flow:.2%}")
            
            # 6. 技术指标事件判断
            # RSI超买超卖
            if 'rsi_signal' in factor_dict:
                rsi_signal_series = factor_dict['rsi_signal']
                if len(rsi_signal_series) > 0:
                    current_rsi_signal = rsi_signal_series.iloc[-1]
                    if current_rsi_signal == 1:
                        signals.append(1)  # RSI超卖，看涨
                        reasons.append("RSI超卖信号")
                    elif current_rsi_signal == -1:
                        signals.append(-1)  # RSI超买，看跌
                        reasons.append("RSI超买信号")
            
            # 均线金叉死叉
            if 'golden_cross' in factor_dict:
                golden_cross_series = factor_dict['golden_cross']
                if len(golden_cross_series) > 0:
                    current_cross = golden_cross_series.iloc[-1]
                    if current_cross == 1:
                        signals.append(1)  # 金叉信号
                        reasons.append("均线金叉信号")
                    elif current_cross == -1:
                        signals.append(-1)  # 死叉信号
                        reasons.append("均线死叉信号")
            
            # 汇总信号
            if signals:
                final_signal = sum(signals) / len(signals)  # 平均信号
                
                # 转换为离散信号
                if final_signal > 0.3:
                    final_signal_discrete = 1  # 买入
                elif final_signal < -0.3:
                    final_signal_discrete = -1  # 卖出
                else:
                    final_signal_discrete = 0  # 中性
            else:
                final_signal = 0
                final_signal_discrete = 0
                reasons.append("无显著事件信号")
            
            print(f"  事件信号汇总:")
            for reason in reasons:
                print(f"    - {reason}")
            print(f"  综合信号强度: {final_signal:.2f}")
            print(f"  最终交易信号: {final_signal_discrete}")
            
            # 保存结果
            self.strategies_data['event_driven'] = {
                'signals': signals,
                'reasons': reasons,
                'final_signal': final_signal,
                'final_signal_discrete': final_signal_discrete
            }
            
            return {
                'signal': final_signal_discrete,
                'signal_strength': final_signal,
                'reasons': reasons
            }
            
        except Exception as e:
            print(f"[ERR] 事件驱动策略执行失败: {e}")
            return None
    
    # ====================== 3.4 规则化趋势/反转策略 ======================
    
    def rule_based_strategy(self, factor_dict, gold_price_df):
        """规则化趋势/反转策略"""
        print("\n[策略执行] 规则化趋势/反转策略...")
        
        try:
            rules = []
            signals = []
            
            # 规则1: 均线排列 + 实际利率过滤
            if 'ma_trend' in factor_dict and 'real_rate' in factor_dict:
                ma_trend = factor_dict['ma_trend'].iloc[-1] if len(factor_dict['ma_trend']) > 0 else 0
                real_rate = factor_dict['real_rate'].iloc[-1] if len(factor_dict['real_rate']) > 0 else 0
                
                # 多头排列 + 实际利率下行 -> 强烈买入
                if ma_trend == 1 and real_rate < 0:
                    signals.append(1)
                    rules.append("多头排列 + 实际利率下行 -> 买入")
                # 空头排列 -> 卖出
                elif ma_trend == -1:
                    signals.append(-1)
                    rules.append("空头排列 -> 卖出")
            
            # 规则2: RSI超卖 + ETF持续净流入
            if 'rsi_signal' in factor_dict and 'etf_flow_cumulative' in factor_dict:
                rsi_signal = factor_dict['rsi_signal'].iloc[-1] if len(factor_dict['rsi_signal']) > 0 else 0
                etf_cumulative = factor_dict['etf_flow_cumulative'].iloc[-1] if len(factor_dict['etf_flow_cumulative']) > 0 else 0
                
                # RSI超卖 + ETF净流入 -> 买入
                if rsi_signal == 1 and etf_cumulative > 0:
                    signals.append(1)
                    rules.append("RSI超卖 + ETF净流入 -> 买入")
                # RSI超买 -> 卖出
                elif rsi_signal == -1:
                    signals.append(-1)
                    rules.append("RSI超买 -> 卖出")
            
            # 规则3: 动量 + 波动率过滤 (动态阈值)
            if 'momentum_20d' in factor_dict and 'atr' in factor_dict:
                momentum = factor_dict['momentum_20d'].iloc[-1] if len(factor_dict['momentum_20d']) > 0 else 0
                atr_value = factor_dict['atr'].iloc[-1] if len(factor_dict['atr']) > 0 else 0
                atr_mean = factor_dict['atr'].iloc[-20:].mean() if len(factor_dict['atr']) > 20 else atr_value

                # 动态阈值: 基于ATR均值的比例
                mom_threshold = max(atr_mean / (gold_price_df['close'].iloc[-1] if len(gold_price_df) > 0 else 1000) * 2, 0.02)

                # 强动量 + 低波动率 -> 趋势延续
                if momentum > mom_threshold and atr_value < atr_mean:
                    signals.append(1)
                    rules.append(f"强动量({momentum:.2%}>{mom_threshold:.2%}) + 低波动率 -> 买入")
                # 负动量 -> 卖出
                elif momentum < -mom_threshold:
                    signals.append(-1)
                    rules.append(f"负动量({momentum:.2%}<-{mom_threshold:.2%}) -> 卖出")
            
            # 规则4: 布林带信号 + 美元指数过滤
            if 'bb_signal' in factor_dict and 'dxy_return' in factor_dict:
                bb_signal = factor_dict['bb_signal'].iloc[-1] if len(factor_dict['bb_signal']) > 0 else 0
                dxy_return = factor_dict['dxy_return'].iloc[-1] if len(factor_dict['dxy_return']) > 0 else 0
                
                # 布林带下轨支撑 + 美元疲软 -> 买入
                if bb_signal == 1 and dxy_return < 0:
                    signals.append(1)
                    rules.append("布林带超卖 + 美元疲软 -> 买入")
                # 布林带上轨压力 -> 卖出
                elif bb_signal == -1:
                    signals.append(-1)
                    rules.append("布林带超买 -> 卖出")
            
            # 规则5: VIX恐慌 + 季节性
            if 'vix_5d_cumulative' in factor_dict and 'seasonal_factor' in factor_dict:
                vix_cumulative = factor_dict['vix_5d_cumulative'].iloc[-1] if len(factor_dict['vix_5d_cumulative']) > 0 else 0
                seasonal = factor_dict['seasonal_factor'].iloc[-1] if len(factor_dict['seasonal_factor']) > 0 else 0
                
                # VIX大涨 + 旺季 -> 避险买入
                if vix_cumulative > 0.1 and seasonal == 1:
                    signals.append(1)
                    rules.append("VIX大涨 + 消费旺季 -> 避险买入")
            
            # 汇总规则信号（Phase-1 修复：buy_count/sell_count 提前初始化避免 NameError）
            buy_count = 0
            sell_count = 0
            if signals:
                buy_count = sum(1 for s in signals if s == 1)
                sell_count = sum(1 for s in signals if s == -1)
                if buy_count > sell_count:
                    final_signal = 1   # 买入
                elif sell_count > buy_count:
                    final_signal = -1  # 卖出
                else:
                    final_signal = 0   # 中性
            else:
                final_signal = 0
                rules.append("无规则触发")
            
            print(f"  触发规则:")
            for rule in rules:
                print(f"    - {rule}")
            print(f"  买入规则数: {buy_count}")
            print(f"  卖出规则数: {sell_count}")
            print(f"  最终交易信号: {final_signal}")
            
            # 保存结果
            self.strategies_data['rule_based'] = {
                'rules': rules,
                'signals': signals,
                'final_signal': final_signal,
                'buy_count': buy_count,
                'sell_count': sell_count
            }
            
            return {
                'signal': final_signal,
                'rules': rules,
                'buy_count': buy_count,
                'sell_count': sell_count
            }
            
        except Exception as e:
            print(f"[ERR] 规则化策略执行失败: {e}")
            return None
    
    # ====================== 综合策略执行 ======================
    
    def execute_all_strategies(self, factor_dict, gold_price_df):
        """执行所有策略"""
        print("=" * 60)
        print("黄金量化策略 - 综合策略执行")
        print("=" * 60)
        
        results = {}
        
        # 1. 线性回归择时模型
        lr_result = self.linear_regression_strategy(factor_dict, gold_price_df)
        if lr_result:
            results['linear_regression'] = lr_result
        
        # 2. 多因子打分模型
        mfs_result = self.multi_factor_scoring_strategy(factor_dict, gold_price_df)
        if mfs_result:
            results['multi_factor_scoring'] = mfs_result
        
        # 3. 事件驱动策略
        ed_result = self.event_driven_strategy(factor_dict, gold_price_df)
        if ed_result:
            results['event_driven'] = ed_result
        
        # 4. 规则化趋势/反转策略
        rb_result = self.rule_based_strategy(factor_dict, gold_price_df)
        if rb_result:
            results['rule_based'] = rb_result
        
        # 5. 综合信号投票
        print("\n[策略汇总] 综合信号投票...")
        
        strategy_signals = []
        strategy_weights = []
        
        for strategy_name, strategy_result in results.items():
            if strategy_result and 'signal' in strategy_result:
                signal = strategy_result['signal']
                strategy_signals.append(signal)
                
                # 根据策略类型分配权重
                if strategy_name == 'linear_regression':
                    weight = 1.2  # 线性回归权重较高
                elif strategy_name == 'multi_factor_scoring':
                    weight = 1.0  # 多因子打分标准权重
                else:
                    weight = 0.8  # 其他策略稍低权重
                
                strategy_weights.append(weight)
                
                signal_desc = {1: "买入", -1: "卖出", 0: "中性"}
                print(f"  {strategy_name}: {signal_desc.get(signal, signal)} (权重: {weight})")
        
        # 计算加权平均信号
        if strategy_signals and strategy_weights:
            weighted_sum = sum(s * w for s, w in zip(strategy_signals, strategy_weights))
            total_weight = sum(strategy_weights)
            final_weighted_signal = weighted_sum / total_weight
            
            # 转换为离散信号
            if final_weighted_signal > 0.3:
                final_signal = 1
                signal_desc = "买入"
            elif final_weighted_signal < -0.3:
                final_signal = -1
                signal_desc = "卖出"
            else:
                final_signal = 0
                signal_desc = "中性"
            
            print(f"  加权平均信号强度: {final_weighted_signal:.2f}")
            print(f"  最终综合信号: {final_signal} ({signal_desc})")
            
            results['consensus_signal'] = {
                'weighted_signal': final_weighted_signal,
                'final_signal': final_signal,
                'signal_desc': signal_desc,
                'strategy_count': len(strategy_signals)
            }
        else:
            print("  无有效策略信号")
            results['consensus_signal'] = {
                'weighted_signal': 0,
                'final_signal': 0,
                'signal_desc': "中性",
                'strategy_count': 0
            }
        
        print("\n[完成] 策略执行完成")
        print(f"成功执行策略: {len(results) - 1} 个")  # 减去consensus_signal
        
        return results
    
    def get_strategy_data(self, strategy_name=None):
        """获取策略数据"""
        if strategy_name:
            return self.strategies_data.get(strategy_name, {})
        else:
            return self.strategies_data


if __name__ == '__main__':
    print("黄金策略模块 — 运行 pytest tests/test_strategies.py 进行测试")
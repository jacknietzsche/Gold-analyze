#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多源数据融合策略
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from src.data.data_cleaner import DataCleaner
from src.data.data_quality_monitor import DataQualityMonitor


class DataFusion:
    """多源数据融合类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.data_cleaner = DataCleaner()
        self.quality_monitor = DataQualityMonitor()
    
    def fuse_price_data(self, sources_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """融合价格数据"""
        if not sources_data:
            return pd.DataFrame()

        cleaned_data = {}
        quality_reports = {}

        for source, data in sources_data.items():
            if not data.empty:
                cleaned = self.data_cleaner.clean_price_data(data)
                if not cleaned.empty:
                    cleaned_data[source] = cleaned
                    quality_reports[source] = self.quality_monitor.monitor_data_quality(cleaned, 'price', source)

        if not cleaned_data:
            return pd.DataFrame()

        if len(cleaned_data) == 1:
            result = next(iter(cleaned_data.values())).copy()
            return result

        weights = self._calculate_source_weights(quality_reports)

        all_indices = []
        for data in cleaned_data.values():
            all_indices.extend(data.index.tolist())
        all_indices = sorted(list(set(all_indices)))

        fused_data = pd.DataFrame(index=all_indices)

        for idx in all_indices:
            prices = []
            weights_list = []

            for source, data in cleaned_data.items():
                if idx in data.index:
                    price = data.loc[idx, 'close']
                    weight = weights.get(source, 0)
                    if weight > 0 and pd.notna(price):
                        prices.append(float(price))
                        weights_list.append(weight)

            if prices and weights_list:
                fused_price = np.average(prices, weights=weights_list)
                fused_data.loc[idx, 'close'] = fused_price

        if not fused_data.empty:
            fused_data = fused_data.ffill().bfill()

            fused_data['open'] = fused_data['close'].shift(1).fillna(fused_data['close'])

            for source, data in cleaned_data.items():
                if 'high' in data.columns and 'low' in data.columns:
                    high_vals = []
                    low_vals = []
                    for idx in fused_data.index:
                        if idx in data.index:
                            high_vals.append(data.loc[idx, 'high'])
                            low_vals.append(data.loc[idx, 'low'])
                    if high_vals:
                        fused_data.loc[fused_data.index[:len(high_vals)], 'high'] = high_vals
                    if low_vals:
                        fused_data.loc[fused_data.index[:len(low_vals)], 'low'] = low_vals
                    break

            if 'high' not in fused_data.columns:
                fused_data['high'] = fused_data[['open', 'close']].max(axis=1)
            if 'low' not in fused_data.columns:
                fused_data['low'] = fused_data[['open', 'close']].min(axis=1)

            total_volume = 0
            for source, data in cleaned_data.items():
                if 'volume' in data.columns:
                    for idx in fused_data.index:
                        if idx in data.index and pd.notna(data.loc[idx, 'volume']):
                            fused_data.loc[idx, 'volume'] = float(data.loc[idx, 'volume'])
                            total_volume += 1
                    break

            if 'volume' not in fused_data.columns:
                fused_data['volume'] = 0

        return fused_data
    
    # 指标分类: 不同数据源的同名指标可能代表不同概念
    # key: 指标名, value: {'same_meaning': True/False, 'preferred_source': ...}
    INDICATOR_METADATA = {
        # 全球/美国指标 (FRED权威)
        'vix': {'same_meaning': True, 'preferred_source': 'fred'},
        'bond_yield': {'same_meaning': True, 'preferred_source': 'fred'},  # 美国10Y国债
        'dollar_index': {'same_meaning': True, 'preferred_source': 'fred',
                         'note': '[FIX 2026-05-09] FRED DTWEXBGS + ChinaHttp/Sina USDCNH估算均可融合'},
        'cpi': {'same_meaning': False, 'preferred_source': 'akshare',
                'china_source': 'akshare', 'us_source': 'fred',
                'note': 'AkShare是中国CPI同比，FRED是美国CPI同比，完全不同的指标！'},
        'm2': {'same_meaning': False, 'preferred_source': 'akshare',
               'china_source': 'akshare', 'us_source': 'fred',
               'note': 'AkShare是中国M2同比，FRED是美国M2同比，不能融合！'},
        'tips_yield': {'same_meaning': True, 'preferred_source': 'fred'},
        'breakeven_inflation': {'same_meaning': True, 'preferred_source': 'fred'},
        # 中国专属指标
        'central_bank_buying': {'same_meaning': True, 'preferred_source': 'akshare'},
        'china_reserves': {'same_meaning': True, 'preferred_source': 'akshare'},
        'gold_london': {'same_meaning': True, 'preferred_source': 'fred'},
        'sp500': {'same_meaning': True, 'preferred_source': 'fred'},
    }

    def fuse_macro_data(self, sources_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """融合宏观数据
        
        重要修复: 某些指标在不同数据源中代表不同概念(如中国CPI vs 美国CPI)，
        这些指标不能简单融合，需要按国家分类处理。
        """
        if not sources_data:
            return {}
        
        # 清洗各数据源数据
        cleaned_data = {}
        quality_scores = {}
        
        for source, data in sources_data.items():
            if data:
                # 清洗数据
                cleaned = self.data_cleaner.clean_macro_data(data)
                if cleaned:
                    cleaned_data[source] = cleaned
                    # 计算数据质量分数
                    quality_scores[source] = self._calculate_macro_quality_score(cleaned)
        
        if not cleaned_data:
            return {}
        
        # 融合数据
        fused_data = {}
        
        # 获取所有指标
        all_indicators = set()
        for data in cleaned_data.values():
            all_indicators.update(data.keys())
        
        for indicator in all_indicators:
            meta = self.INDICATOR_METADATA.get(indicator, {})
            
            # 检查指标是否需要特殊处理(不同源代表不同概念)
            if not meta.get('same_meaning', True):
                # 不能融合的指标，选择优先数据源
                preferred = meta.get('preferred_source', list(cleaned_data.keys())[0])
                if preferred in cleaned_data and indicator in cleaned_data[preferred]:
                    fused_data[indicator] = cleaned_data[preferred][indicator]
                    # 如果首选源没有，尝试其他源
                elif indicator in cleaned_data.get(meta.get('china_source') or '', {}):
                    # 对于cpi/m2等，优先使用akshare(中国数据)
                    china_src = meta.get('china_source')
                    if china_src and china_src in cleaned_data:
                        fused_data[indicator] = cleaned_data[china_src][indicator]
                elif indicator in cleaned_data.get(meta.get('us_source') or '', {}):
                    us_src = meta.get('us_source')
                    if us_src and us_src in cleaned_data:
                        fused_data[indicator] = cleaned_data[us_src][indicator]
                else:
                    # [FIX 2026-05-09] preferred/china/us都没有时，遍历所有源
                    for source, data in cleaned_data.items():
                        if indicator in data and isinstance(data[indicator], (int, float)):
                            fused_data[indicator] = data[indicator]
                            break
                continue
            
            # 可以融合的指标: 加权平均
            values = []
            weights = []

            for source, data in cleaned_data.items():
                if indicator in data:
                    value = data[indicator]
                    if not isinstance(value, (int, float)):
                        continue
                    weight = quality_scores.get(source, 0)
                    if weight > 0:
                        values.append(float(value))
                        weights.append(weight)

            if values and weights:
                fused_value = np.average(values, weights=weights)
                fused_data[indicator] = fused_value
        
        return fused_data
    
    def fuse_sentiment_data(self, sources_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """融合情绪数据"""
        if not sources_data:
            return {}
        
        # 清洗各数据源数据
        cleaned_data = {}
        quality_scores = {}
        
        for source, data in sources_data.items():
            if data:
                # 清洗数据
                cleaned = self.data_cleaner.clean_sentiment_data(data)
                if cleaned:
                    cleaned_data[source] = cleaned
                    # 计算数据质量分数
                    quality_scores[source] = self._calculate_sentiment_quality_score(cleaned)
        
        if not cleaned_data:
            return {}
        
        # 融合数据
        fused_data = {}
        
        # 处理数值型情绪指标
        numeric_indicators = ['vix', 'gold_sentiment', 'market_sentiment', 'gld_volume', 'gld_price_change', 'gld_price']
        for indicator in numeric_indicators:
            values = []
            weights = []

            for source, data in cleaned_data.items():
                if indicator in data:
                    value = data[indicator]
                    if not isinstance(value, (int, float)):
                        continue
                    weight = quality_scores.get(source, 0)
                    if weight > 0:
                        values.append(float(value))
                        weights.append(weight)

            if values and weights:
                fused_value = np.average(values, weights=weights)
                fused_data[indicator] = fused_value
        
        # 处理情绪标签
        if 'sentiment' in [list(data.keys()) for data in cleaned_data.values()]:
            sentiment_counts = {}
            total_weight = 0
            
            for source, data in cleaned_data.items():
                if 'sentiment' in data:
                    sentiment = data['sentiment']
                    weight = quality_scores.get(source, 0)
                    if weight > 0:
                        if sentiment not in sentiment_counts:
                            sentiment_counts[sentiment] = 0
                        sentiment_counts[sentiment] += weight
                        total_weight += weight
            
            if sentiment_counts:
                # 选择权重最高的情绪标签
                dominant_sentiment = max(sentiment_counts.items(), key=lambda x: x[1])[0]
                fused_data['sentiment'] = dominant_sentiment
        
        return fused_data
    
    def fuse_correlation_data(self, sources_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """融合相关性数据"""
        if not sources_data:
            return pd.DataFrame()
        
        # 清洗和标准化各数据源数据
        cleaned_data = {}
        quality_reports = {}
        
        for source, data in sources_data.items():
            if not data.empty:
                # 清洗数据
                cleaned = self.data_cleaner.clean_correlation_data(data)
                if not cleaned.empty:
                    cleaned_data[source] = cleaned
                    # 监控数据质量
                    quality_reports[source] = self.quality_monitor.monitor_data_quality(cleaned, 'correlation', source)
        
        if not cleaned_data:
            return pd.DataFrame()
        
        # 计算各数据源的权重
        weights = self._calculate_source_weights(quality_reports)
        
        # 获取所有资产
        all_assets = set()
        for data in cleaned_data.values():
            all_assets.update(data.index.tolist())
            all_assets.update(data.columns.tolist())
        all_assets = sorted(list(all_assets))
        
        # 构建融合相关性矩阵
        n = len(all_assets)
        fused_matrix = np.eye(n)
        weight_matrix = np.eye(n)
        
        # 对每对资产进行融合
        for i, asset1 in enumerate(all_assets):
            for j, asset2 in enumerate(all_assets):
                if i < j:
                    correlations = []
                    weights_list = []
                    
                    for source, data in cleaned_data.items():
                        if asset1 in data.index and asset2 in data.columns:
                            corr = data.loc[asset1, asset2]
                            weight = weights.get(source, 0)
                            if weight > 0:
                                correlations.append(corr)
                                weights_list.append(weight)
                    
                    if correlations and weights_list:
                        # 加权平均
                        fused_corr = np.average(correlations, weights=weights_list)
                        fused_matrix[i, j] = fused_corr
                        fused_matrix[j, i] = fused_corr
                        weight_matrix[i, j] = sum(weights_list)
                        weight_matrix[j, i] = sum(weights_list)
        
        # 转换为DataFrame
        fused_df = pd.DataFrame(fused_matrix, index=all_assets, columns=all_assets)
        
        return fused_df
    
    def _calculate_source_weights(self, quality_reports: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """计算数据源权重"""
        weights = {}
        total_score = 0
        
        for source, report in quality_reports.items():
            metrics = report.get('metrics', {})
            # 计算综合质量分数
            quality_score = (metrics.get('completeness', 0) * 0.3 +
                            metrics.get('timeliness', 0) * 0.3 +
                            metrics.get('consistency', 0) * 0.2 +
                            metrics.get('accuracy', 0) * 0.2)
            weights[source] = quality_score
            total_score += quality_score
        
        # 归一化权重
        if total_score > 0:
            for source in weights:
                weights[source] = weights[source] / total_score
        
        return weights
    
    def _calculate_macro_quality_score(self, data: Dict[str, Any]) -> float:
        """计算宏观数据质量分数"""
        # 基于数据完整性和合理性计算质量分数
        total_indicators = 5  # 预期的指标数量
        present_indicators = sum(1 for v in data.values() if isinstance(v, (int, float)) and pd.notna(v))
        
        # 完整性分数
        completeness_score = present_indicators / total_indicators
        
        # 合理性检查
        validity_score = 1.0
        
        # 检查债券收益率范围
        if 'bond_yield' in data and isinstance(data['bond_yield'], (int, float)):
            yield_val = data['bond_yield']
            if not (0 <= yield_val <= 10):
                validity_score *= 0.8
        
        # 检查VIX范围
        if 'vix' in data and isinstance(data['vix'], (int, float)):
            vix_val = data['vix']
            if not (10 <= vix_val <= 80):
                validity_score *= 0.8
        
        # 检查美元指数范围
        if 'dollar_index' in data and isinstance(data['dollar_index'], (int, float)):
            dxy_val = data['dollar_index']
            if not (80 <= dxy_val <= 120):
                validity_score *= 0.8
        
        # 综合分数
        quality_score = (completeness_score * 0.7 + validity_score * 0.3)
        
        return quality_score
    
    def _calculate_sentiment_quality_score(self, data: Dict[str, Any]) -> float:
        """计算情绪数据质量分数"""
        # 基于数据完整性和合理性计算质量分数
        total_indicators = 3  # 预期的指标数量
        present_indicators = sum(1 for v in data.values() if isinstance(v, (int, float)) and pd.notna(v))
        
        # 完整性分数
        completeness_score = present_indicators / total_indicators
        
        # 合理性检查
        validity_score = 1.0
        
        # 检查VIX范围
        if 'vix' in data and isinstance(data['vix'], (int, float)):
            vix_val = data['vix']
            if not (10 <= vix_val <= 80):
                validity_score *= 0.8
        
        # 检查情绪标签
        if 'sentiment' in data:
            valid_sentiments = ['fear', 'anxiety', 'calm', 'greed', 'extreme_fear', 'extreme_greed', 'neutral']
            if data['sentiment'] not in valid_sentiments:
                validity_score *= 0.8
        
        # 综合分数
        quality_score = (completeness_score * 0.7 + validity_score * 0.3)
        
        return quality_score
    
    def generate_fusion_report(self, sources_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成融合报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'sources': list(sources_data.keys()),
            'fusion_results': {},
            'quality_summary': {}
        }
        
        # 计算各数据源的质量
        quality_scores = {}
        for source, data in sources_data.items():
            if isinstance(data, pd.DataFrame):
                quality = self.quality_monitor.monitor_data_quality(data, 'price', source)
                quality_scores[source] = quality['metrics']
            elif isinstance(data, dict):
                if 'vix' in data or 'sentiment' in data:
                    # 情绪数据
                    score = self._calculate_sentiment_quality_score(data)
                    quality_scores[source] = {'overall': score}
                else:
                    # 宏观数据
                    score = self._calculate_macro_quality_score(data)
                    quality_scores[source] = {'overall': score}
        
        report['quality_summary'] = quality_scores
        
        # 计算权重
        weights = {}
        total_score = sum(v.get('overall', 0) for v in quality_scores.values())
        if total_score > 0:
            for source, score in quality_scores.items():
                weights[source] = score.get('overall', 0) / total_score
        
        report['weights'] = weights
        
        return report
    
    def optimize_fusion_strategy(self, historical_data: Dict[str, List[pd.DataFrame]]) -> Dict[str, Any]:
        """优化融合策略"""
        # 这里可以实现更复杂的融合策略优化
        # 例如基于历史数据的权重调整、数据源选择等
        
        return {
            'optimized_weights': {},
            'recommended_sources': [],
            'optimization_date': datetime.now().isoformat()
        }

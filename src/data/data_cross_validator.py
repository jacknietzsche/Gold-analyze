#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据交叉验证模块
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import os


class DataCrossValidator:
    """数据交叉验证器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.validation_history = []
        self.alert_history = []
        self.validation_thresholds = {
            'correlation_threshold': 0.9,
            'relative_diff_threshold': 5.0,  # 百分比
            'absolute_diff_threshold': 10.0,  # 绝对值
            'min_data_points': 10
        }
    
    def validate_price_data(self, sources_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """验证价格数据的一致性"""
        if len(sources_data) < 2:
            return {
                'valid': False,
                'message': '至少需要两个数据源进行交叉验证',
                'details': {}
            }
        
        # 提取收盘价数据
        closing_prices = {}
        for source, data in sources_data.items():
            if not data.empty and 'close' in data.columns:
                closing_prices[source] = data['close']
        
        if len(closing_prices) < 2:
            return {
                'valid': False,
                'message': '至少需要两个数据源包含收盘价数据',
                'details': {}
            }
        
        # 对齐数据
        aligned_data = pd.DataFrame(closing_prices)
        aligned_data = aligned_data.dropna()
        
        if len(aligned_data) < self.validation_thresholds['min_data_points']:
            return {
                'valid': False,
                'message': f'数据点不足，至少需要{self.validation_thresholds["min_data_points"]}个数据点',
                'details': {
                    'available_data_points': len(aligned_data)
                }
            }
        
        # 计算相关性
        correlation_matrix = aligned_data.corr()
        
        # 计算平均相关性
        correlations = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                correlations.append(correlation_matrix.iloc[i, j])
        
        avg_correlation = np.mean(correlations) if correlations else 0
        
        # 计算价格差异
        price_diff = {}
        for source1, prices1 in closing_prices.items():
            for source2, prices2 in closing_prices.items():
                if source1 < source2:
                    common_index = prices1.index.intersection(prices2.index)
                    if len(common_index) > 0:
                        diff = abs(prices1.loc[common_index] - prices2.loc[common_index])
                        avg_diff = diff.mean()
                        max_diff = diff.max()
                        relative_diff = (avg_diff / prices1.loc[common_index].mean()) * 100 if prices1.loc[common_index].mean() > 0 else 0
                        
                        price_diff[f"{source1}_vs_{source2}"] = {
                            'average_difference': float(avg_diff),
                            'max_difference': float(max_diff),
                            'relative_difference': float(relative_diff)
                        }
        
        # 判断一致性
        correlation_valid = avg_correlation >= self.validation_thresholds['correlation_threshold']
        diff_valid = all(v['relative_difference'] < self.validation_thresholds['relative_diff_threshold'] for v in price_diff.values())
        valid = correlation_valid and diff_valid
        
        # 生成告警
        alerts = []
        if not correlation_valid:
            alerts.append({
                'level': 'critical' if avg_correlation < 0.8 else 'warning',
                'type': 'correlation',
                'message': f'数据源间相关性不足: {avg_correlation:.3f} < {self.validation_thresholds["correlation_threshold"]}',
                'value': avg_correlation
            })
        
        for pair, diff_info in price_diff.items():
            if diff_info['relative_difference'] >= self.validation_thresholds['relative_diff_threshold']:
                alerts.append({
                    'level': 'critical' if diff_info['relative_difference'] > 10 else 'warning',
                    'type': 'price_difference',
                    'message': f'{pair} 价格差异过大: {diff_info["relative_difference"]:.2f}%',
                    'value': diff_info['relative_difference']
                })
        
        # 存储验证历史
        validation_result = {
            'timestamp': datetime.now().isoformat(),
            'data_type': 'price',
            'valid': valid,
            'sources': list(sources_data.keys()),
            'details': {
                'average_correlation': round(avg_correlation, 3),
                'price_differences': price_diff,
                'data_points': len(aligned_data),
                'correlation_valid': correlation_valid,
                'diff_valid': diff_valid
            },
            'alerts': alerts
        }
        
        self.validation_history.append(validation_result)
        
        if alerts:
            self.alert_history.append({
                'timestamp': datetime.now().isoformat(),
                'data_type': 'price',
                'alerts': alerts
            })
        
        return validation_result
    
    def validate_macro_data(self, sources_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """验证宏观数据的一致性"""
        if len(sources_data) < 2:
            return {
                'valid': False,
                'message': '至少需要两个数据源进行交叉验证',
                'details': {},
                'alerts': []
            }
        
        # 提取共同指标
        common_indicators = None
        for source, data in sources_data.items():
            if common_indicators is None:
                common_indicators = set(data.keys())
            else:
                common_indicators.intersection_update(data.keys())
        
        if not common_indicators:
            return {
                'valid': False,
                'message': '没有共同的宏观指标',
                'details': {},
                'alerts': []
            }
        
        # 计算每个指标的一致性
        indicator_consistency = {}
        alerts = []
        
        for indicator in common_indicators:
            values = {}
            for source, data in sources_data.items():
                if indicator in data:
                    values[source] = data[indicator]
            
            if len(values) >= 2:
                # 计算值的差异
                value_list = list(values.values())
                
                # 检查是否为数值类型，只有数值才能计算mean和diff
                is_numeric = all(isinstance(v, (int, float)) for v in value_list)
                
                # 初始化（两个分支共用，避免 UnboundLocalError）
                unique_values = None
                
                if is_numeric:
                    avg_value = np.mean(value_list)
                    max_value = max(value_list)
                    min_value = min(value_list)
                    
                    # 计算相对差异
                    if avg_value > 0:
                        relative_diff = ((max_value - min_value) / avg_value) * 100
                    else:
                        relative_diff = 0
                    
                    # 判断一致性
                    consistent = relative_diff < self.validation_thresholds['relative_diff_threshold']
                    
                    indicator_consistency[indicator] = {
                        'values': values,
                        'average_value': float(avg_value),
                        'max_value': float(max_value),
                        'min_value': float(min_value),
                        'relative_difference': float(relative_diff),
                        'consistent': consistent
                    }
                    
                    if not consistent:
                        alerts.append({
                            'level': 'critical' if relative_diff > 10 else 'warning',
                            'type': 'macro_difference',
                            'message': f'指标 {indicator} 差异过大: {relative_diff:.2f}%',
                            'value': relative_diff
                        })
                else:
                    # 非数值类型（如字符串），检查值是否完全一致
                    unique_values = set(value_list)
                    consistent = len(unique_values) == 1
                    
                    indicator_consistency[indicator] = {
                        'values': values,
                        'consistent': consistent,
                        'type': 'string'
                    }
                    
                if not consistent:
                    alerts.append({
                        'level': 'warning',
                        'type': 'sentiment_mismatch',
                        'message': f'情绪指标 {indicator} 值不一致: {unique_values}',
                        'value': None
                    })
        
        # 整体一致性判断
        all_consistent = all(v['consistent'] for v in indicator_consistency.values())
        
        # 存储验证历史
        validation_result = {
            'timestamp': datetime.now().isoformat(),
            'data_type': 'macro',
            'valid': all_consistent,
            'sources': list(sources_data.keys()),
            'details': {
                'common_indicators': list(common_indicators),
                'indicator_consistency': indicator_consistency
            },
            'alerts': alerts
        }
        
        self.validation_history.append(validation_result)
        
        if alerts:
            self.alert_history.append({
                'timestamp': datetime.now().isoformat(),
                'data_type': 'macro',
                'alerts': alerts
            })
        
        return validation_result
    
    def validate_sentiment_data(self, sources_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """验证市场情绪数据的一致性"""
        if len(sources_data) < 2:
            return {
                'valid': False,
                'message': '至少需要两个数据源进行交叉验证',
                'details': {},
                'alerts': []
            }
        
        # 提取共同指标
        common_indicators = None
        for source, data in sources_data.items():
            if common_indicators is None:
                common_indicators = set(data.keys())
            else:
                common_indicators.intersection_update(data.keys())
        
        if not common_indicators:
            return {
                'valid': False,
                'message': '没有共同的情绪指标',
                'details': {},
                'alerts': []
            }
        
        # 计算每个指标的一致性
        indicator_consistency = {}
        alerts = []
        
        for indicator in common_indicators:
            values = {}
            for source, data in sources_data.items():
                if indicator in data:
                    values[source] = data[indicator]
            
            if len(values) >= 2:
                value_list = list(values.values())
                is_numeric = all(isinstance(v, (int, float)) for v in value_list)

                if is_numeric:
                    avg_value = np.mean(value_list)
                    max_value = max(value_list)
                    min_value = min(value_list)

                    if avg_value > 0:
                        relative_diff = ((max_value - min_value) / avg_value) * 100
                    else:
                        relative_diff = 0

                    consistent = relative_diff < self.validation_thresholds['relative_diff_threshold']

                    indicator_consistency[indicator] = {
                        'values': values,
                        'average_value': float(avg_value),
                        'max_value': float(max_value),
                        'min_value': float(min_value),
                        'relative_difference': float(relative_diff),
                        'consistent': consistent
                    }

                    if not consistent:
                        alerts.append({
                            'level': 'critical' if relative_diff > 10 else 'warning',
                            'type': 'sentiment_difference',
                            'message': f'情绪指标 {indicator} 差异过大: {relative_diff:.2f}%',
                            'value': relative_diff
                        })
                else:
                    unique_values = set(str(v) for v in value_list)
                    consistent = len(unique_values) == 1

                    indicator_consistency[indicator] = {
                        'values': values,
                        'consistent': consistent,
                        'type': 'string'
                    }

                    if not consistent:
                        alerts.append({
                            'level': 'warning',
                            'type': 'sentiment_mismatch',
                            'message': f'情绪指标 {indicator} 值不一致: {unique_values}',
                            'value': None
                        })
        
        # 整体一致性判断
        all_consistent = all(v['consistent'] for v in indicator_consistency.values())
        
        # 存储验证历史
        validation_result = {
            'timestamp': datetime.now().isoformat(),
            'data_type': 'sentiment',
            'valid': all_consistent,
            'sources': list(sources_data.keys()),
            'details': {
                'common_indicators': list(common_indicators),
                'indicator_consistency': indicator_consistency
            },
            'alerts': alerts
        }
        
        self.validation_history.append(validation_result)
        
        if alerts:
            self.alert_history.append({
                'timestamp': datetime.now().isoformat(),
                'data_type': 'sentiment',
                'alerts': alerts
            })
        
        return validation_result
    
    def validate_correlation_data(self, sources_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """验证相关性数据的一致性"""
        if len(sources_data) < 2:
            return {
                'valid': False,
                'message': '至少需要两个数据源进行交叉验证',
                'details': {},
                'alerts': []
            }
        
        # 提取相关性矩阵
        correlations = {}
        for source, data in sources_data.items():
            if not data.empty:
                correlations[source] = data
        
        if len(correlations) < 2:
            return {
                'valid': False,
                'message': '至少需要两个数据源包含相关性数据',
                'details': {},
                'alerts': []
            }
        
        # 计算相关性矩阵之间的差异
        matrix_diff = {}
        alerts = []
        
        for source1, matrix1 in correlations.items():
            for source2, matrix2 in correlations.items():
                if source1 < source2:
                    # 找到共同的行和列
                    common_rows = matrix1.index.intersection(matrix2.index)
                    common_cols = matrix1.columns.intersection(matrix2.columns)
                    
                    if len(common_rows) > 0 and len(common_cols) > 0:
                        # 提取共同部分
                        sub_matrix1 = matrix1.loc[common_rows, common_cols]
                        sub_matrix2 = matrix2.loc[common_rows, common_cols]
                        
                        # 计算差异
                        diff = abs(sub_matrix1 - sub_matrix2)
                        avg_diff = diff.mean().mean()
                        max_diff = diff.max().max()
                        
                        matrix_diff[f"{source1}_vs_{source2}"] = {
                            'average_difference': float(avg_diff),
                            'max_difference': float(max_diff),
                            'common_rows': len(common_rows),
                            'common_cols': len(common_cols)
                        }
                        
                        # 检查差异是否过大
                        if avg_diff > 0.1:
                            alerts.append({
                                'level': 'critical' if avg_diff > 0.2 else 'warning',
                                'type': 'correlation_matrix_difference',
                                'message': f'{source1} 和 {source2} 相关性矩阵差异过大: {avg_diff:.3f}',
                                'value': avg_diff
                            })
        
        # 整体一致性判断
        all_consistent = len(alerts) == 0
        
        # 存储验证历史
        validation_result = {
            'timestamp': datetime.now().isoformat(),
            'data_type': 'correlation',
            'valid': all_consistent,
            'sources': list(sources_data.keys()),
            'details': {
                'matrix_differences': matrix_diff
            },
            'alerts': alerts
        }
        
        self.validation_history.append(validation_result)
        
        if alerts:
            self.alert_history.append({
                'timestamp': datetime.now().isoformat(),
                'data_type': 'correlation',
                'alerts': alerts
            })
        
        return validation_result
    
    def generate_validation_report(self, data_type: str = None) -> Dict[str, Any]:
        """生成验证报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {},
            'details': {},
            'alerts': []
        }
        
        # 过滤验证历史
        filtered_history = []
        if data_type:
            filtered_history = [v for v in self.validation_history if v['data_type'] == data_type]
        else:
            filtered_history = self.validation_history
        
        if filtered_history:
            # 计算整体统计
            valid_count = sum(1 for v in filtered_history if v['valid'])
            total_count = len(filtered_history)
            valid_rate = valid_count / total_count if total_count > 0 else 0
            
            report['summary'] = {
                'total_validations': total_count,
                'valid_count': valid_count,
                'valid_rate': round(valid_rate, 2),
                'last_validation': filtered_history[-1]['timestamp']
            }
            
            # 按数据源分组
            by_source = {}
            for validation in filtered_history:
                sources_key = '-'.join(sorted(validation['sources']))
                if sources_key not in by_source:
                    by_source[sources_key] = []
                by_source[sources_key].append(validation)
            
            report['details'] = by_source
            
            # 添加告警
            recent_alerts = [alert for alert in self.alert_history 
                            if (datetime.now() - datetime.fromisoformat(alert['timestamp'])).days <= 7]
            if data_type:
                recent_alerts = [alert for alert in recent_alerts if alert['data_type'] == data_type]
            report['alerts'] = recent_alerts
        
        return report
    
    def save_validation_history(self, file_path: str):
        """保存验证历史"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'validation_history': self.validation_history,
                    'alert_history': self.alert_history,
                    'timestamp': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存验证历史失败: {e}")
            return False
    
    def load_validation_history(self, file_path: str):
        """加载验证历史"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.validation_history = data.get('validation_history', [])
                    self.alert_history = data.get('alert_history', [])
                return True
        except Exception as e:
            print(f"加载验证历史失败: {e}")
        return False
    
    def get_validation_trend(self, data_type: str, days: int = 30) -> Dict[str, List[Any]]:
        """获取验证趋势"""
        trend = {
            'timestamps': [],
            'validations': [],
            'alert_count': []
        }
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for validation in self.validation_history:
            if validation['data_type'] == data_type:
                validation_date = datetime.fromisoformat(validation['timestamp'])
                if validation_date >= cutoff_date:
                    trend['timestamps'].append(validation['timestamp'])
                    trend['validations'].append(1 if validation['valid'] else 0)
                    trend['alert_count'].append(len(validation['alerts']))
        
        return trend

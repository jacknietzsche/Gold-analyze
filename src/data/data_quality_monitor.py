#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据质量监控机制
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import os


class DataQualityMonitor:
    """数据质量监控器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.quality_history = {}
        self.alert_thresholds = {
            'completeness': 0.8,
            'timeliness': 0.7,
            'consistency': 0.8,
            'accuracy': 0.85
        }
        self.alert_history = []
    
    def monitor_data_quality(self, data: pd.DataFrame, data_type: str, source: str) -> Dict[str, Any]:
        """监控数据质量"""
        quality_metrics = self.calculate_quality_metrics(data, data_type)
        
        # 存储质量历史
        timestamp = datetime.now().isoformat()
        if source not in self.quality_history:
            self.quality_history[source] = {}
        if data_type not in self.quality_history[source]:
            self.quality_history[source][data_type] = []
        
        self.quality_history[source][data_type].append({
            'timestamp': timestamp,
            'metrics': quality_metrics
        })
        
        # 检查是否需要告警
        alerts = self.check_quality_alerts(quality_metrics, source, data_type)
        
        # 生成质量报告
        report = {
            'timestamp': timestamp,
            'source': source,
            'data_type': data_type,
            'metrics': quality_metrics,
            'alerts': alerts,
            'data_info': {
                'rows': len(data),
                'columns': list(data.columns),
                'date_range': {
                    'start': data.index.min().strftime('%Y-%m-%d') if isinstance(data.index, pd.DatetimeIndex) else 'N/A',
                    'end': data.index.max().strftime('%Y-%m-%d') if isinstance(data.index, pd.DatetimeIndex) else 'N/A'
                }
            }
        }
        
        return report
    
    def calculate_quality_metrics(self, data: pd.DataFrame, data_type: str) -> Dict[str, float]:
        """计算数据质量指标"""
        metrics = {
            'completeness': 0.0,
            'timeliness': 0.0,
            'consistency': 0.0,
            'accuracy': 0.0
        }
        
        if data.empty:
            return metrics
        
        # 1. 完整性：非空值比例
        total_cells = data.shape[0] * data.shape[1]
        non_null_cells = data.notnull().sum().sum()
        metrics['completeness'] = round(non_null_cells / total_cells, 2)
        
        # 2. 时效性：数据是否最新
        if isinstance(data.index, pd.DatetimeIndex):
            days_since_last_update = (datetime.now() - data.index.max()).days
            metrics['timeliness'] = round(max(0.0, 1.0 - (days_since_last_update / 30)), 2)
        else:
            metrics['timeliness'] = 0.5  # 非时间序列数据时效性默认为0.5
        
        # 3. 一致性：数据的合理性
        if data_type == 'price':
            # 检查价格数据的合理性
            if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
                # 检查high >= close, high >= open, low <= close, low <= open
                valid_rows = ((data['high'] >= data['close']) & 
                             (data['high'] >= data['open']) & 
                             (data['low'] <= data['close']) & 
                             (data['low'] <= data['open'])).sum()
                metrics['consistency'] = round(valid_rows / len(data), 2)
            else:
                metrics['consistency'] = 0.5
        elif data_type == 'macro':
            # 宏观数据一致性检查
            metrics['consistency'] = 0.8  # 默认值
        elif data_type == 'sentiment':
            # 情绪数据一致性检查
            metrics['consistency'] = 0.8  # 默认值
        elif data_type == 'correlation':
            # 相关性数据一致性检查
            if not data.empty:
                # 检查对角线是否为1
                diagonal_correct = 0
                for col in data.columns:
                    if col in data.index and abs(data.loc[col, col] - 1.0) < 0.01:
                        diagonal_correct += 1
                metrics['consistency'] = round(diagonal_correct / len(data.columns), 2)
            else:
                metrics['consistency'] = 0.0
        
        # 4. 准确性：数据的合理性范围
        if data_type == 'price':
            # 检查价格范围是否合理
            if 'close' in data.columns:
                price_range = data['close'].max() - data['close'].min()
                price_mean = data['close'].mean()
                if price_mean > 0:
                    price_volatility = price_range / price_mean
                    # 合理的波动率范围
                    if 0.01 <= price_volatility <= 0.5:
                        metrics['accuracy'] = 1.0
                    elif price_volatility < 0.01:
                        metrics['accuracy'] = 0.5
                    else:
                        metrics['accuracy'] = 0.3
                else:
                    metrics['accuracy'] = 0.0
        
        return metrics
    
    def check_quality_alerts(self, metrics: Dict[str, float], source: str, data_type: str) -> List[Dict[str, Any]]:
        """检查质量告警"""
        alerts = []
        
        for metric_name, metric_value in metrics.items():
            threshold = self.alert_thresholds.get(metric_name, 0.8)
            if metric_value < threshold:
                alerts.append({
                    'level': 'warning' if metric_value > threshold * 0.8 else 'critical',
                    'metric': metric_name,
                    'value': metric_value,
                    'threshold': threshold,
                    'message': f"{source} {data_type} {metric_name} 低于阈值: {metric_value:.2f} < {threshold:.2f}"
                })
        
        # 存储告警历史
        if alerts:
            self.alert_history.append({
                'timestamp': datetime.now().isoformat(),
                'source': source,
                'data_type': data_type,
                'alerts': alerts
            })
        
        return alerts
    
    def generate_quality_report(self, source: str = None) -> Dict[str, Any]:
        """生成质量报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {},
            'details': {}
        }
        
        # 计算总体质量
        total_metrics = []
        
        if source:
            # 特定数据源的报告
            if source in self.quality_history:
                for data_type, history in self.quality_history[source].items():
                    if history:
                        latest_metrics = history[-1]['metrics']
                        report['details'][f"{source}_{data_type}"] = latest_metrics
                        total_metrics.append(list(latest_metrics.values()))
        else:
            # 所有数据源的报告
            for src, data_types in self.quality_history.items():
                for data_type, history in data_types.items():
                    if history:
                        latest_metrics = history[-1]['metrics']
                        report['details'][f"{src}_{data_type}"] = latest_metrics
                        total_metrics.append(list(latest_metrics.values()))
        
        # 计算总体质量指标
        if total_metrics:
            avg_metrics = np.mean(total_metrics, axis=0)
            report['summary'] = {
                'completeness': round(avg_metrics[0], 2),
                'timeliness': round(avg_metrics[1], 2),
                'consistency': round(avg_metrics[2], 2),
                'accuracy': round(avg_metrics[3], 2),
                'overall': round(np.mean(avg_metrics), 2)
            }
        
        # 添加告警信息
        recent_alerts = [alert for alert in self.alert_history 
                        if (datetime.now() - datetime.fromisoformat(alert['timestamp'])).days <= 7]
        report['alerts'] = recent_alerts
        
        return report
    
    def detect_data_anomalies(self, data: pd.DataFrame, data_type: str) -> List[Dict[str, Any]]:
        """检测数据异常"""
        anomalies = []
        
        if data.empty:
            return anomalies
        
        if data_type == 'price':
            # 检测价格异常
            if 'close' in data.columns:
                # 使用Z-score方法检测异常
                prices = data['close']
                mean = prices.mean()
                std = prices.std()
                threshold = 3.0
                
                for idx, price in prices.items():
                    z_score = abs((price - mean) / std) if std > 0 else 0
                    if z_score > threshold:
                        anomalies.append({
                            'type': 'price_anomaly',
                            'date': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
                            'value': price,
                            'z_score': z_score,
                            'message': f"价格异常: {price} (Z-score: {z_score:.2f})"
                        })
            
            # 检测成交量异常
            if 'volume' in data.columns:
                volumes = data['volume']
                mean = volumes.mean()
                std = volumes.std()
                threshold = 3.0
                
                for idx, volume in volumes.items():
                    z_score = abs((volume - mean) / std) if std > 0 else 0
                    if z_score > threshold:
                        anomalies.append({
                            'type': 'volume_anomaly',
                            'date': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
                            'value': volume,
                            'z_score': z_score,
                            'message': f"成交量异常: {volume} (Z-score: {z_score:.2f})"
                        })
        
        return anomalies
    
    def save_quality_history(self, file_path: str):
        """保存质量历史"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'quality_history': self.quality_history,
                    'alert_history': self.alert_history,
                    'timestamp': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存质量历史失败: {e}")
            return False
    
    def load_quality_history(self, file_path: str):
        """加载质量历史"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.quality_history = data.get('quality_history', {})
                    self.alert_history = data.get('alert_history', [])
                return True
        except Exception as e:
            print(f"加载质量历史失败: {e}")
        return False
    
    def get_data_quality_trend(self, source: str, data_type: str, days: int = 30) -> Dict[str, List[Any]]:
        """获取数据质量趋势"""
        trend = {
            'timestamps': [],
            'completeness': [],
            'timeliness': [],
            'consistency': [],
            'accuracy': []
        }
        
        if source in self.quality_history and data_type in self.quality_history[source]:
            history = self.quality_history[source][data_type]
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for record in history:
                record_date = datetime.fromisoformat(record['timestamp'])
                if record_date >= cutoff_date:
                    trend['timestamps'].append(record['timestamp'])
                    trend['completeness'].append(record['metrics'].get('completeness', 0))
                    trend['timeliness'].append(record['metrics'].get('timeliness', 0))
                    trend['consistency'].append(record['metrics'].get('consistency', 0))
                    trend['accuracy'].append(record['metrics'].get('accuracy', 0))
        
        return trend
    
    def validate_cross_source_consistency(self, sources_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """验证跨数据源一致性"""
        if len(sources_data) < 2:
            return {'consistent': True, 'details': {}}
        
        # 获取所有数据源的收盘价
        closing_prices = {}
        for source, data in sources_data.items():
            if 'close' in data.columns:
                closing_prices[source] = data['close']
        
        if len(closing_prices) < 2:
            return {'consistent': True, 'details': {}}
        
        # 对齐数据
        aligned_data = pd.DataFrame(closing_prices)
        aligned_data = aligned_data.dropna()
        
        if len(aligned_data) < 10:
            return {'consistent': True, 'details': {}}
        
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
                        price_diff[f"{source1}_vs_{source2}"] = {
                            'average_difference': avg_diff,
                            'max_difference': max_diff,
                            'relative_difference': (avg_diff / prices1.loc[common_index].mean()) * 100 if prices1.loc[common_index].mean() > 0 else 0
                        }
        
        # 判断一致性
        consistent = avg_correlation > 0.9 and all(v['relative_difference'] < 5 for v in price_diff.values())
        
        return {
            'consistent': consistent,
            'details': {
                'average_correlation': round(avg_correlation, 3),
                'price_differences': price_diff,
                'data_points': len(aligned_data)
            }
        }

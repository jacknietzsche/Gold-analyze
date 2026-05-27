#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据清洗与标准化模块
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


class DataCleaner:
    """数据清洗与标准化类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    def clean_price_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """清洗价格数据"""
        if data.empty:
            return data
        
        # 1. 确保索引是datetime类型
        if not isinstance(data.index, pd.DatetimeIndex):
            try:
                data.index = pd.to_datetime(data.index)
            except:
                if 'date' in data.columns:
                    data['date'] = pd.to_datetime(data['date'])
                    data = data.set_index('date')
                else:
                    return data
        
        # 2. 标准化列名
        data = self._standardize_columns(data)
        
        # 3. 处理缺失值
        data = self._handle_missing_values(data)
        
        # 4. 检测和处理异常值
        data = self._detect_outliers(data)
        
        # 5. 确保数据按时间排序
        data = data.sort_index()
        
        # 6. 填充缺失的OHLC数据
        data = self._fill_ohlc_data(data)
        
        return data
    
    def clean_macro_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗宏观数据"""
        cleaned_data = {}
        
        for key, value in data.items():
            # 处理数值数据
            if isinstance(value, (int, float)):
                # 检查是否为有效数值
                if pd.notna(value) and not np.isinf(value):
                    cleaned_data[key] = float(value)
                else:
                    cleaned_data[key] = self._get_default_value(key)
            
            # 处理字符串数据
            elif isinstance(value, str):
                # 尝试转换为数值
                try:
                    cleaned_data[key] = float(value)
                except:
                    cleaned_data[key] = value
            
            # 处理其他类型
            else:
                cleaned_data[key] = value
        
        return cleaned_data
    
    def clean_sentiment_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗情绪数据"""
        cleaned_data = {}
        
        for key, value in data.items():
            # 处理数值数据
            if isinstance(value, (int, float)):
                if pd.notna(value) and not np.isinf(value):
                    cleaned_data[key] = float(value)
                else:
                    cleaned_data[key] = self._get_default_value(key)
            
            # 处理情绪标签
            elif key == 'sentiment' and isinstance(value, str):
                valid_sentiments = ['fear', 'anxiety', 'calm', 'greed', 'extreme_fear', 'extreme_greed']
                if value.lower() in valid_sentiments:
                    cleaned_data[key] = value.lower()
                else:
                    cleaned_data[key] = 'neutral'
            
            else:
                cleaned_data[key] = value
        
        return cleaned_data
    
    def clean_correlation_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """清洗相关性数据"""
        if data.empty:
            return data
        
        # 1. 确保对角线为1
        for col in data.columns:
            if col in data.index:
                data.loc[col, col] = 1.0
        
        # 2. 处理缺失值
        data = data.fillna(0.0)
        
        # 3. 确保相关性在[-1, 1]范围内
        data = data.clip(-1.0, 1.0)
        
        return data
    
    def _standardize_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        column_mapping = {
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'OPEN': 'open',
            'HIGH': 'high',
            'LOW': 'low',
            'CLOSE': 'close',
            'VOLUME': 'volume',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume',
            '开盘价': 'open',
            '最高价': 'high',
            '最低价': 'low',
            '收盘价': 'close',
            '交易量': 'volume'
        }
        
        data = data.rename(columns=column_mapping)
        
        # 确保必要的列存在
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in data.columns:
                if col == 'volume':
                    data[col] = 0
                else:
                    data[col] = data.get('close', 0)
        
        return data
    
    def _handle_missing_values(self, data: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值"""
        # 填充缺失值
        for col in ['open', 'high', 'low', 'close']:
            if col in data.columns:
                data[col] = data[col].ffill().bfill()
        
        # 成交量填充为0
        if 'volume' in data.columns:
            data['volume'] = data['volume'].fillna(0)
        
        # 移除仍然有缺失值的行
        data = data.dropna()
        
        return data
    
    def _detect_outliers(self, data: pd.DataFrame) -> pd.DataFrame:
        """检测和处理异常值
        
        重要: 对于黄金这种长期趋势向上的资产，不能使用全量历史数据的统计范围来做截断，
        否则近期高价位会被错误地截断为"异常值"。
        策略: 仅用IQR检测极端异常点（如0或负数），不做基于历史分位的截断。
        """
        for col in ['open', 'high', 'low', 'close']:
            if col in data.columns:
                # 检查是否为国际金价（美元/盎司），需要转换为国内金价（元/克）
                # 国际金价通常在1600-6000美元/盎司之间
                max_price = data[col].max()
                if 1600 <= max_price <= 6000:  # 可能是国际金价(美元/盎司)
                    # 转换因子：1盎司 = 31.1035克，假设汇率为7.0
                    conversion_factor = 7.0 / 31.1035  # 美元/盎司 -> 元/克
                    data[col] = data[col] * conversion_factor
                
                # 使用IQR方法仅做下界保护（防止0或负数等明显异常）
                Q1 = data[col].quantile(0.25)
                Q3 = data[col].quantile(0.75)
                IQR = Q3 - Q1
                
                # 只设置一个宽松的下界，防止明显的数据错误（如0、负数、极低价格）
                # 不设上界，因为黄金作为趋势资产，历史新高不应被截断
                lower_bound = Q1 - 3.0 * IQR  # 使用3倍IQR（更宽松）
                
                # 绝对最低价：黄金不可能低于50元/克（历史上从未发生）
                absolute_min = 50.0
                final_lower = max(lower_bound, absolute_min)
                
                # 仅替换明显异常的低值为边界值，不截断上界
                data[col] = data[col].clip(lower=final_lower)
        
        return data
    
    def _fill_ohlc_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """填充缺失的OHLC数据"""
        # 确保OHLC数据的合理性
        if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
            # 确保high >= close, high >= open, low <= close, low <= open
            data['high'] = data[['high', 'open', 'close']].max(axis=1)
            data['low'] = data[['low', 'open', 'close']].min(axis=1)
        
        return data
    
    def _get_default_value(self, key: str) -> Optional[float]:
        """获取默认值 -- 数据不可用时返回None，绝不返回硬编码假值"""
        # 原则: 数据源失败时必须返回None，禁止注入任何硬编码"参考值"
        # 下游代码应通过 pd.notna() / val is not None 检查数据可用性
        return None
    
    def normalize_data(self, data: pd.DataFrame, method: str = 'minmax') -> pd.DataFrame:
        """标准化数据"""
        if data.empty:
            return data
        
        normalized_data = data.copy()
        
        for col in ['open', 'high', 'low', 'close']:
            if col in normalized_data.columns:
                if method == 'minmax':
                    min_val = normalized_data[col].min()
                    max_val = normalized_data[col].max()
                    if max_val > min_val:
                        normalized_data[col] = (normalized_data[col] - min_val) / (max_val - min_val)
                elif method == 'zscore':
                    mean_val = normalized_data[col].mean()
                    std_val = normalized_data[col].std()
                    if std_val > 0:
                        normalized_data[col] = (normalized_data[col] - mean_val) / std_val
        
        return normalized_data
    
    def resample_data(self, data: pd.DataFrame, frequency: str = '1d') -> pd.DataFrame:
        """重采样数据"""
        if data.empty:
            return data
        
        # 重采样
        resampled = data.resample(frequency).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        # 移除空行
        resampled = resampled.dropna()
        
        return resampled
    
    def validate_data_integrity(self, data: pd.DataFrame) -> bool:
        """验证数据完整性"""
        if data.empty:
            return False
        
        # 检查必要列是否存在
        required_columns = ['open', 'high', 'low', 'close']
        for col in required_columns:
            if col not in data.columns:
                return False
        
        # 检查数据量
        if len(data) < 30:
            return False
        
        # 检查日期范围
        if data.index.max() < datetime.now() - timedelta(days=30):
            return False
        
        return True
    
    def calculate_data_quality(self, data: pd.DataFrame) -> Dict[str, float]:
        """计算数据质量指标"""
        if data.empty:
            return {
                'completeness': 0.0,
                'timeliness': 0.0,
                'consistency': 0.0
            }
        
        # 完整性：非空值比例
        completeness = 1.0 - (data.isnull().sum().sum() / (data.shape[0] * data.shape[1]))
        
        # 时效性：数据是否最新
        if isinstance(data.index, pd.DatetimeIndex):
            days_since_last_update = (datetime.now() - data.index.max()).days
            timeliness = max(0.0, 1.0 - (days_since_last_update / 30))
        else:
            timeliness = 0.0
        
        # 一致性：价格数据的合理性
        consistency = 1.0
        if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
            # 检查high >= close, high >= open, low <= close, low <= open
            invalid_rows = ((data['high'] < data['close']) | 
                           (data['high'] < data['open']) | 
                           (data['low'] > data['close']) | 
                           (data['low'] > data['open'])).sum()
            consistency = max(0.0, 1.0 - (invalid_rows / len(data)))
        
        return {
            'completeness': round(completeness, 2),
            'timeliness': round(timeliness, 2),
            'consistency': round(consistency, 2)
        }

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源抽象层 - 统一数据获取接口
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DataProvider(ABC):
    """数据源抽象基类"""

    GOLD_PRICE_RANGES = {
        'Au99.99': (180, 2500),   # 2016年低点~260元/克，2025年后超1000元/克，预留余量
        'GLD': (80, 600),
        'XAU': (900, 5500),
    }

    MACRO_RANGES = {
        'bond_yield': (-1, 15),
        'vix': (5, 100),
        'dollar_index': (70, 130),
        'central_bank_buying': (0, 300),  # 月度购金(吨)，极端月可能超200，上限放宽到300
        'china_reserves': (1000, 5000),  # 中国黄金储备(万盎司)，约2200-3500万盎司
        'cpi': (-5, 15),
        'm2': (0, 30),
    }

    # Provider能力声明 - 子类应覆盖此属性
    # 支持的能力: 'price', 'macro', 'sentiment', 'correlation'
    capabilities: set = set()

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
        self._cache = {}
        self._validation_errors = []

    def has_capability(self, capability: str) -> bool:
        """检查是否支持指定能力"""
        return capability in self.capabilities

    def validate_price_data(self, data: pd.DataFrame, symbol: str = "Au99.99") -> Dict[str, Any]:
        """验证价格数据的合理性"""
        errors = []
        warnings = []

        if data.empty:
            return {'valid': False, 'errors': ['数据为空'], 'warnings': []}

        price_range = self.GOLD_PRICE_RANGES.get(symbol, (0, float('inf')))

        if 'close' in data.columns:
            close = data['close'].dropna()
            if len(close) > 0:
                out_of_range = close[(close < price_range[0]) | (close > price_range[1])]
                if len(out_of_range) > 0:
                    pct = len(out_of_range) / len(close) * 100
                    errors.append(f'{len(out_of_range)}条收盘价超出合理范围({price_range[0]}-{price_range[1]})，占比{pct:.1f}%')

                if len(close) > 1:
                    daily_returns = close.pct_change().dropna()
                    extreme_moves = daily_returns[abs(daily_returns) > 0.1]
                    if len(extreme_moves) > 0:
                        warnings.append(f'{len(extreme_moves)}条日涨跌幅超过10%')

        if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
            ohlc_invalid = data[
                (data['high'] < data['low']) |
                (data['high'] < data['close']) |
                (data['low'] > data['close'])
            ]
            if len(ohlc_invalid) > 0:
                errors.append(f'{len(ohlc_invalid)}条OHLC数据不合理(H<L或H<close或L>close)')

        result = {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'record_count': len(data),
            'price_range_used': price_range
        }
        self._validation_errors.extend(errors)
        return result

    def validate_macro_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证宏观数据的合理性"""
        errors = []
        warnings = []

        for key, value in data.items():
            if not isinstance(value, (int, float)):
                continue
            if key in self.MACRO_RANGES:
                lo, hi = self.MACRO_RANGES[key]
                if not (lo <= value <= hi):
                    errors.append(f'{key}={value}超出合理范围({lo}-{hi})')

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    @abstractmethod
    def get_gold_price(self, symbol: str = "Au99.99", period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """获取黄金价格数据"""
        pass
    
    @abstractmethod
    def get_macro_data(self, indicators: List[str]) -> Dict[str, Any]:
        """获取宏观经济数据"""
        pass
    
    @abstractmethod
    def get_market_sentiment(self) -> Dict[str, Any]:
        """获取市场情绪数据"""
        pass
    
    @abstractmethod
    def get_asset_correlation(self, assets: List[str]) -> pd.DataFrame:
        """获取资产相关性数据"""
        pass
    
    def _cache_key(self, func_name: str, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [func_name]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        return "_".join(key_parts)
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        cached_data = self._cache.get(key)
        if cached_data:
            timestamp, data = cached_data
            if datetime.now() - timestamp < timedelta(hours=1):
                return data
        return None
    
    def _set_cache(self, key: str, data: Any):
        """设置缓存"""
        self._cache[key] = (datetime.now(), data)
    
    def get_data_quality(self) -> Dict[str, float]:
        """获取数据质量指标"""
        return {
            'completeness': 0.0,
            'timeliness': 0.0,
            'consistency': 0.0
        }


class DataSourceManager:
    """数据源管理器"""

    def __init__(self, providers: List[DataProvider], config: Dict[str, Any] = None):
        self.providers = providers
        self.config = config or {}
        self.source_priority = self.config.get('source_priority', {
            'price': ['akshare', 'yinhe', 'yahoo', 'goldapi'],
            'historical': ['akshare', 'yahoo', 'yinhe', 'goldapi'],
            'macro': ['akshare', 'openbb', 'yahoo', 'yinhe'],
            'sentiment': ['akshare', 'yahoo', 'yinhe', 'openbb']
        })
    
    def get_provider_by_name(self, name: str) -> Optional[DataProvider]:
        """根据名称获取数据源"""
        for provider in self.providers:
            if provider.name.lower() == name.lower():
                return provider
        return None
    
    def get_best_provider(self, data_type: str) -> Optional[DataProvider]:
        """获取最佳数据源"""
        priorities = self.source_priority.get(data_type, [])
        for provider_name in priorities:
            provider = self.get_provider_by_name(provider_name)
            if provider:
                quality = provider.get_data_quality()
                if quality['completeness'] > 0.8:
                    return provider
        return self.providers[0] if self.providers else None
    
    def get_gold_price(self, symbol: str = "Au99.99", period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """获取黄金价格数据"""
        provider = self.get_best_provider('price')
        if provider:
            try:
                return provider.get_gold_price(symbol, period, interval)
            except Exception as e:
                print(f"[{provider.name}] 获取黄金价格失败: {e}")
        
        # 尝试其他数据源
        for p in self.providers:
            if p != provider:
                try:
                    return p.get_gold_price(symbol, period, interval)
                except Exception as e:
                    logger.warning(f"操作失败: {e}")

        return pd.DataFrame()
    
    def get_macro_data(self, indicators: List[str]) -> Dict[str, Any]:
        """获取宏观经济数据"""
        provider = self.get_best_provider('macro')
        if provider:
            try:
                return provider.get_macro_data(indicators)
            except Exception as e:
                print(f"[{provider.name}] 获取宏观数据失败: {e}")
        
        # 尝试其他数据源
        for p in self.providers:
            if p != provider:
                try:
                    return p.get_macro_data(indicators)
                except Exception as e:
                    logger.warning(f"操作失败: {e}")

        return {}
    
    def get_market_sentiment(self) -> Dict[str, Any]:
        """获取市场情绪数据"""
        provider = self.get_best_provider('sentiment')
        if provider:
            try:
                return provider.get_market_sentiment()
            except Exception as e:
                print(f"[{provider.name}] 获取市场情绪失败: {e}")
        
        # 尝试其他数据源
        for p in self.providers:
            if p != provider:
                try:
                    return p.get_market_sentiment()
                except Exception as e:
                    logger.warning(f"操作失败: {e}")

        return {}
    
    def get_asset_correlation(self, assets: List[str]) -> pd.DataFrame:
        """获取资产相关性数据"""
        provider = self.get_best_provider('historical')
        if provider:
            try:
                return provider.get_asset_correlation(assets)
            except Exception as e:
                print(f"[{provider.name}] 获取资产相关性失败: {e}")
        
        # 尝试其他数据源
        for p in self.providers:
            if p != provider:
                try:
                    return p.get_asset_correlation(assets)
                except Exception as e:
                    logger.warning(f"操作失败: {e}")

        return pd.DataFrame()

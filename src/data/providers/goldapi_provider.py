#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gold-API.com 数据源实现
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from src.data.data_provider import DataProvider


class GoldAPIProvider(DataProvider):
    """Gold-API.com 数据源实现"""
    capabilities = {'price'}

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "goldapi"
        self.api_key = config.get('api_key', '') if config else ''
        self.base_url = "https://www.goldapi.io/api"

    def get_gold_price(self, symbol: str = "XAU", period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """获取黄金价格数据（仅支持真实API调用，不伪造历史数据）"""
        cache_key = self._cache_key("get_gold_price", symbol=symbol, period=period, interval=interval)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        if not self.api_key:
            print("[Gold-API] 未配置API Key，跳过此数据源。请设置 GOLDAPI_API_KEY 环境变量。")
            return pd.DataFrame()

        try:
            goldapi_symbol = self._map_symbol(symbol)

            # 尝试使用 GoldAPI 的历史数据端点
            # GoldAPI 支持 /{symbol}/{currency}/history?period= 历史数据接口
            for endpoint_suffix in [
                f"{goldapi_symbol}/USD/history?period={period}",
                f"{goldapi_symbol}/USD",
            ]:
                endpoint = f"{self.base_url}/{endpoint_suffix}"
                headers = {'x-access-token': self.api_key}

                response = requests.get(endpoint, headers=headers, timeout=15)
                response.raise_for_status()
                data = response.json()

                df = self._parse_response(data, period)
                if not df.empty:
                    print(f"[Gold-API] 成功获取 {len(df)} 条真实价格记录 (endpoint: {endpoint_suffix})")
                    self._set_cache(cache_key, df)
                    return df

            print("[Gold-API] 所有端点均未返回有效数据")
            return pd.DataFrame()

        except Exception as e:
            print(f"[Gold-API] 获取黄金价格失败: {e}")
            return pd.DataFrame()

    def get_macro_data(self, indicators: list) -> dict:
        """获取宏观经济数据 - GoldAPI不提供宏观数据"""
        return {}

    def get_market_sentiment(self) -> dict:
        """获取市场情绪数据 - GoldAPI不提供情绪数据"""
        return {}

    def get_asset_correlation(self, assets: list) -> pd.DataFrame:
        """获取资产相关性数据 - GoldAPI不提供相关性数据"""
        return pd.DataFrame()

    def get_data_quality(self) -> dict:
        """获取数据质量指标"""
        return {
            'completeness': 0.92,
            'timeliness': 0.95,
            'consistency': 0.90
        }

    def _map_symbol(self, symbol: str) -> str:
        """映射符号到 Gold-API.com 格式"""
        symbol_map = {
            "Au99.99": "XAU", "gold": "XAU", "XAU": "XAU", "GOLD": "XAU"
        }
        return symbol_map.get(symbol, "XAU")

    def _parse_response(self, data: dict, period: str) -> pd.DataFrame:
        """解析 GoldAPI 响应，仅使用真实返回的数据，不伪造历史序列"""
        if not data:
            return pd.DataFrame()

        # 情况1: 返回的是单条实时价格数据
        if 'price' in data and len(data) <= 5:
            current_price = data['price']
            print(f"[Gold-API] 注意：API仅返回单日价格({current_price})，无法构建历史序列。"
                  "如需历史数据请确认 GoldAPI 账户是否支持 history 端点。")
            # 仅返回当日的单条记录（不伪造完整时间序列）
            df = pd.DataFrame({
                'open': [current_price], 'high': [current_price],
                'low': [current_price], 'close': [current_price], 'volume': [0]
            }, index=pd.DatetimeIndex([datetime.now()], name='date'))
            return df

        # 情况2: 返回的是历史数组
        if isinstance(data, list) or (isinstance(data, dict) and 'data' in data):
            rows = data if isinstance(data, list) else data.get('data', [])
            records = []
            for row in rows:
                if isinstance(row, dict):
                    record = {
                        'date': row.get('date') or row.get('datetime', ''),
                        'open': float(row.get('open', row.get('o', 0))),
                        'high': float(row.get('high', row.get('h', 0))),
                        'low': float(row.get('low', row.get('l', 0))),
                        'close': float(row.get('close', row.get('c', 0))),
                        'volume': int(row.get('vol', row.get('volume', 0)))
                    }
                    if record['date']:
                        records.append(record)
            if records:
                df = pd.DataFrame(records)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                return df.sort_index()

        return pd.DataFrame()

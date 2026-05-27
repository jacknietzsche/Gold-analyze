#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
银禾数据 (YinheData) 数据源实现 - 带连接诊断
"""

import pandas as pd
import numpy as np
import requests
import socket
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from src.data.data_provider import DataProvider


class YinheDataProvider(DataProvider):
    """银禾数据 (YinheData) 数据源实现 - 带完整连接诊断"""
    capabilities = {'price'}

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "yinhe"
        self.api_key = config.get('api_key', '') if config else ''
        self.base_url = "https://api.yinhedata.com/v1"
        self.timeout = config.get('timeout', 10)
        self._dns_resolved = None

    def _check_dns_available(self) -> bool:
        """快速DNS检查，避免长时间超时"""
        if self._dns_resolved is not None:
            return self._dns_resolved
        try:
            socket.setdefaulttimeout(3)
            socket.gethostbyname("api.yinhedata.com")
            self._dns_resolved = True
        except socket.gaierror:
            self._dns_resolved = False
        except Exception:
            self._dns_resolved = False
        return self._dns_resolved

    def diagnose_connection(self) -> Dict[str, Any]:
        """系统化诊断连接问题"""
        diagnosis = {
            'overall_status': 'unknown',
            'dns_status': {'ok': False, 'error': None},
            'network_status': {'ok': False, 'error': None},
            'api_key_status': {'ok': False, 'error': None, 'valid': None},
            'api_status': {'ok': False, 'error': None, 'response_time': None},
            'recommendations': []
        }

        self._check_dns(diagnosis)
        self._check_network(diagnosis)
        self._check_api_key(diagnosis)
        self._check_api_endpoint(diagnosis)

        diagnosis['overall_status'] = 'healthy' if all([
            diagnosis['dns_status']['ok'],
            diagnosis['network_status']['ok'],
            diagnosis['api_key_status']['ok'],
            diagnosis['api_status']['ok']
        ]) else 'unhealthy'

        return diagnosis

    def _check_dns(self, diagnosis: Dict[str, Any]):
        """检查DNS配置"""
        try:
            socket.setdefaulttimeout(5)
            host = "api.yinhedata.com"
            ip = socket.gethostbyname(host)
            diagnosis['dns_status']['ok'] = True
            diagnosis['dns_status']['resolved_ip'] = ip
        except socket.gaierror as e:
            diagnosis['dns_status']['ok'] = False
            diagnosis['dns_status']['error'] = f"DNS resolution failed: {e}"
            diagnosis['recommendations'].append("Check DNS configuration or try alternative DNS servers (8.8.8.8, 1.1.1.1)")
        except Exception as e:
            diagnosis['dns_status']['ok'] = False
            diagnosis['dns_status']['error'] = f"DNS check failed: {e}"

    def _check_network(self, diagnosis: Dict[str, Any]):
        """检查网络连接"""
        try:
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            diagnosis['network_status']['ok'] = True
        except Exception as e:
            diagnosis['network_status']['ok'] = False
            diagnosis['network_status']['error'] = f"Network connectivity failed: {e}"
            diagnosis['recommendations'].append("Check internet connection and firewall settings")

        try:
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("api.yinhedata.com", 443))
            diagnosis['network_status']['can_reach_api'] = True
        except Exception as e:
            diagnosis['network_status']['can_reach_api'] = False
            diagnosis['network_status']['api_reach_error'] = f"Cannot reach API server: {e}"
            diagnosis['recommendations'].append("Verify API server is accessible")

    def _check_api_key(self, diagnosis: Dict[str, Any]):
        """检查API Key有效性"""
        if not self.api_key:
            diagnosis['api_key_status']['ok'] = False
            diagnosis['api_key_status']['error'] = "API key is empty"
            diagnosis['api_key_status']['valid'] = False
            diagnosis['recommendations'].append("Provide a valid YinheData API key")
            return

        if len(self.api_key) < 10:
            diagnosis['api_key_status']['ok'] = False
            diagnosis['api_key_status']['error'] = "API key format appears invalid"
            diagnosis['api_key_status']['valid'] = False
            diagnosis['recommendations'].append("Verify API key format with YinheData documentation")
            return

        diagnosis['api_key_status']['ok'] = True
        diagnosis['api_key_status']['valid'] = True
        diagnosis['api_key_status']['masked_key'] = self.api_key[:4] + "***" + self.api_key[-4:]

    def _check_api_endpoint(self, diagnosis: Dict[str, Any]):
        """检查API端点响应"""
        import time
        start_time = time.time()

        try:
            response = requests.get(
                f"{self.base_url}/gold/price",
                params={'symbol': 'Au99.99', 'api_key': self.api_key},
                timeout=self.timeout
            )
            response_time = time.time() - start_time
            diagnosis['api_status']['response_time'] = round(response_time, 3)

            if response.status_code == 200:
                diagnosis['api_status']['ok'] = True
            elif response.status_code == 401:
                diagnosis['api_status']['ok'] = False
                diagnosis['api_status']['error'] = "Unauthorized - Invalid API key"
                diagnosis['recommendations'].append("Re-verify API key or request a new one")
            elif response.status_code == 403:
                diagnosis['api_status']['ok'] = False
                diagnosis['api_status']['error'] = "Forbidden - Check subscription status"
                diagnosis['recommendations'].append("Check subscription status and quota limits")
            elif response.status_code == 429:
                diagnosis['api_status']['ok'] = False
                diagnosis['api_status']['error'] = "Rate limited - Too many requests"
                diagnosis['recommendations'].append("Implement request throttling and caching")
            else:
                diagnosis['api_status']['ok'] = False
                diagnosis['api_status']['error'] = f"HTTP {response.status_code}: {response.reason}"

        except requests.exceptions.Timeout:
            diagnosis['api_status']['ok'] = False
            diagnosis['api_status']['error'] = "Request timeout - Server may be overloaded"
            diagnosis['recommendations'].append("Retry later or check server status")
        except requests.exceptions.ConnectionError as e:
            diagnosis['api_status']['ok'] = False
            diagnosis['api_status']['error'] = f"Connection error: {e}"
            diagnosis['recommendations'].append("Check network connectivity and firewall rules")
        except Exception as e:
            diagnosis['api_status']['ok'] = False
            diagnosis['api_status']['error'] = f"API check failed: {e}"
    
    def get_gold_price(self, symbol: str = "Au99.99", period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """获取黄金价格数据"""
        cache_key = self._cache_key("get_gold_price", symbol=symbol, period=period, interval=interval)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        if not self._check_dns_available():
            return pd.DataFrame()

        try:
            endpoint = f"{self.base_url}/gold/price"
            params = {
                'symbol': symbol,
                'period': period,
                'interval': interval,
                'api_key': self.api_key
            }

            response = requests.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if 'data' in data and data['data']:
                df = pd.DataFrame(data['data'])
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').set_index('date')

                if 'close' not in df.columns and 'price' in df.columns:
                    df['close'] = df['price']

                for col in ['open', 'high', 'low', 'volume']:
                    if col not in df.columns:
                        if col == 'volume':
                            df[col] = 0
                        else:
                            df[col] = df['close']

                self._set_cache(cache_key, df)
                return df

        except Exception as e:
            print(f"[YinheData] 获取黄金价格失败: {e}")

        return pd.DataFrame()
    
    def get_macro_data(self, indicators: list) -> dict:
        """获取宏观经济数据"""
        cache_key = self._cache_key("get_macro_data", indicators=",".join(indicators))
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        if not self._check_dns_available():
            return {}

        data = {}

        try:
            endpoint = f"{self.base_url}/macro/data"
            params = {
                'indicators': ",".join(indicators),
                'api_key': self.api_key
            }

            response = requests.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            api_data = response.json()

            if 'data' in api_data:
                data = api_data['data']

        except Exception as e:
            print(f"[YinheData] 获取宏观数据失败: {e}")

        self._set_cache(cache_key, data)
        return data
    
    def get_market_sentiment(self) -> dict:
        """获取市场情绪数据"""
        cache_key = self._cache_key("get_market_sentiment")
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        if not self._check_dns_available():
            return {}

        sentiment = {}

        try:
            endpoint = f"{self.base_url}/market/sentiment"
            params = {
                'api_key': self.api_key
            }

            response = requests.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if 'data' in data:
                sentiment = data['data']

        except Exception as e:
            print(f"[YinheData] 获取市场情绪失败: {e}")

        self._set_cache(cache_key, sentiment)
        return sentiment
    
    def get_asset_correlation(self, assets: list) -> pd.DataFrame:
        """获取资产相关性数据"""
        cache_key = self._cache_key("get_asset_correlation", assets=",".join(assets))
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        if not self._check_dns_available():
            return pd.DataFrame()

        try:
            endpoint = f"{self.base_url}/asset/correlation"
            params = {
                'assets': ",".join(assets),
                'api_key': self.api_key
            }

            response = requests.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if 'data' in data and 'correlation_matrix' in data['data']:
                corr_matrix = data['data']['correlation_matrix']
                corr_df = pd.DataFrame(corr_matrix, index=assets, columns=assets)

                self._set_cache(cache_key, corr_df)
                return corr_df

        except Exception as e:
            print(f"[YinheData] 获取资产相关性失败: {e}")

        return pd.DataFrame()
    
    def get_data_quality(self) -> dict:
        """获取数据质量指标"""
        return {
            'completeness': 0.90,
            'timeliness': 0.85,
            'consistency': 0.88
        }

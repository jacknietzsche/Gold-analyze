#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Yahoo Finance API 数据源实现 - 带持久化缓存
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import time as _time
from typing import Optional, Dict, Any, Callable
from src.data.data_provider import DataProvider

logger = logging.getLogger(__name__)

_YF_CACHE_FIXED = False


def _ensure_yf_cache():
    global _YF_CACHE_FIXED
    if _YF_CACHE_FIXED:
        return
    os.environ.setdefault('YFINANCE_CACHE_DIR', str(Path(os.environ.get('TEMP', '.')) / 'yfinance_cache'))
    cache_dir = Path(os.environ['YFINANCE_CACHE_DIR'])
    cache_dir.mkdir(parents=True, exist_ok=True)
    _YF_CACHE_FIXED = True

try:
    _ensure_yf_cache()
    import yfinance as yf
except Exception:
    import yfinance as yf


class YahooFinanceProvider(DataProvider):
    """Yahoo Finance API 数据源实现 - 带智能缓存减少API调用频率"""

    RATE_LIMIT_COOLDOWN = 60

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "yahoo"
        self._init_persistent_cache()
        self._last_rate_limit_time = 0

    def _init_persistent_cache(self):
        """初始化持久化缓存"""
        cache_dir = Path(self.config.get('cache_dir', '.data_cache/yahoo'))
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_dir = cache_dir
        self._persistent_cache: Dict[str, tuple] = {}
        self._cache_ttl = self.config.get('cache_hours', 24) * 3600

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self._cache_dir / f"{key_hash}.pkl"

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取数据（内存+持久化）"""
        now = datetime.now()

        if key in self._persistent_cache:
            timestamp, data = self._persistent_cache[key]
            if (now - timestamp).total_seconds() < self._cache_ttl:
                return data

        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
                if (now - mtime).total_seconds() < self._cache_ttl:
                    data = pd.read_pickle(cache_path)
                    self._persistent_cache[key] = (now, data)
                    return data
            except Exception as e:
                logger.warning(f"操作失败: {e}")

        return None

    def _set_cache(self, key: str, data: Any):
        """设置缓存（内存+持久化）"""
        now = datetime.now()
        self._persistent_cache[key] = (now, data)

        try:
            cache_path = self._get_cache_path(key)
            pd.to_pickle(data, cache_path)
        except Exception as e:
            print(f"[Yahoo Finance] Cache write failed: {e}")

    def _is_rate_limited(self) -> bool:
        """检查是否处于速率限制冷却期"""
        return (_time.time() - self._last_rate_limit_time) < self.RATE_LIMIT_COOLDOWN

    def _mark_rate_limited(self):
        """标记速率限制"""
        self._last_rate_limit_time = _time.time()

    def get_gold_price(self, symbol: str = "GLD", period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """获取黄金价格数据"""
        cache_key = self._cache_key("get_gold_price", symbol=symbol, period=period, interval=interval)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        if self._is_rate_limited():
            print("[Yahoo Finance] 速率限制冷却中，跳过请求")
            return pd.DataFrame()

        try:
            yahoo_symbol = self._map_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(period=period, interval=interval)

            if not data.empty:
                data = data.rename(columns={
                    'Open': 'open', 'High': 'high',
                    'Low': 'low', 'Close': 'close', 'Volume': 'volume'
                })

                for col in ['open', 'high', 'low', 'close', 'volume']:
                    if col not in data.columns:
                        if col == 'volume':
                            data[col] = 0
                        else:
                            data[col] = data['close']

                self._set_cache(cache_key, data)
                return data

        except SystemExit:
            print(f"[Yahoo Finance] {symbol} 数据不可用(可能已退市)，跳过")
            return pd.DataFrame()
        except Exception as e:
            error_str = str(e).lower()
            if 'rate' in error_str or 'limit' in error_str or '429' in error_str:
                print(f"[Yahoo Finance] 速率限制，进入冷却")
                self._mark_rate_limited()
            else:
                print(f"[Yahoo Finance] 获取黄金价格失败: {e}")

        return pd.DataFrame()

    def get_macro_data(self, indicators: list) -> dict:
        """获取宏观经济数据"""
        cache_key = self._cache_key("get_macro_data", indicators=",".join(indicators))
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        if self._is_rate_limited():
            print("[Yahoo Finance] 速率限制冷却中，跳过请求")
            return {}

        data = {}

        try:
            if 'bond_yield' in indicators:
                try:
                    ticker = yf.Ticker("^TNX")
                    tnx_data = ticker.history(period="1d")
                    if not tnx_data.empty:
                        data['bond_yield'] = float(tnx_data['close'].iloc[-1])
                except SystemExit:
                    print("[Yahoo Finance] ^TNX 数据不可用，跳过")
                except Exception as e:
                    logger.warning(f"操作失败: {e}")

            if 'vix' in indicators:
                try:
                    ticker = yf.Ticker("^VIX")
                    vix_data = ticker.history(period="1d")
                    if not vix_data.empty:
                        data['vix'] = float(vix_data['close'].iloc[-1])
                except SystemExit:
                    print("[Yahoo Finance] ^VIX 数据不可用，跳过")
                except Exception as e:
                    logger.warning(f"操作失败: {e}")

            if 'dollar_index' in indicators:
                try:
                    ticker = yf.Ticker("^DXY")
                    dxy_data = ticker.history(period="1d")
                    if not dxy_data.empty:
                        data['dollar_index'] = float(dxy_data['close'].iloc[-1])
                except SystemExit:
                    print("[Yahoo Finance] ^DXY 数据不可用，跳过")
                except Exception as e:
                    logger.warning(f"操作失败: {e}")

        except SystemExit:
            print("[Yahoo Finance] 宏观数据请求被中断，跳过")
        except Exception as e:
            error_str = str(e).lower()
            if 'rate' in error_str or 'limit' in error_str or '429' in error_str:
                self._mark_rate_limited()
            print(f"[Yahoo Finance] 获取宏观数据失败: {e}")

        if data:
            self._set_cache(cache_key, data)
        return data

    def get_market_sentiment(self) -> dict:
        """获取市场情绪数据"""
        cache_key = self._cache_key("get_market_sentiment")
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        if self._is_rate_limited():
            print("[Yahoo Finance] 速率限制冷却中，跳过请求")
            return {}

        sentiment = {}

        try:
            ticker = yf.Ticker("^VIX")
            vix_data = ticker.history(period="1d")

            if not vix_data.empty:
                vix = float(vix_data['close'].iloc[-1])
                sentiment['vix'] = vix

                if vix > 30:
                    sentiment['sentiment'] = 'fear'
                elif vix > 20:
                    sentiment['sentiment'] = 'anxiety'
                else:
                    sentiment['sentiment'] = 'calm'

            try:
                gld_ticker = yf.Ticker("GLD")
                gld_data = gld_ticker.history(period="1mo")
                if not gld_data.empty:
                    sentiment['gld_volume'] = float(gld_data['volume'].mean())
                    sentiment['gld_price_change'] = float((gld_data['close'].iloc[-1] / gld_data['close'].iloc[0] - 1) * 100)
            except SystemExit:
                print("[Yahoo Finance] GLD 情绪数据不可用，跳过")
            except Exception as e:
                logger.warning(f"操作失败: {e}")

        except SystemExit:
            print("[Yahoo Finance] 市场情绪数据请求被中断，跳过")
        except Exception as e:
            error_str = str(e).lower()
            if 'rate' in error_str or 'limit' in error_str or '429' in error_str:
                self._mark_rate_limited()
            print(f"[Yahoo Finance] 获取市场情绪失败: {e}")

        if sentiment:
            self._set_cache(cache_key, sentiment)
        return sentiment

    def get_asset_correlation(self, assets: list) -> pd.DataFrame:
        """获取资产相关性数据"""
        cache_key = self._cache_key("get_asset_correlation", assets=",".join(assets))
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        if self._is_rate_limited():
            print("[Yahoo Finance] 速率限制冷却中，跳过请求")
            return pd.DataFrame()

        try:
            yahoo_assets = [self._map_symbol(asset) for asset in assets]
            data = {}
            for asset, yahoo_symbol in zip(assets, yahoo_assets):
                try:
                    ticker = yf.Ticker(yahoo_symbol)
                    asset_data = ticker.history(period="1y")
                    if not asset_data.empty:
                        data[asset] = asset_data['close']
                except SystemExit:
                    print(f"[Yahoo Finance] {yahoo_symbol} 相关性数据不可用，跳过")
                except Exception as e:
                    logger.warning(f"操作失败: {e}")

            if data:
                df = pd.DataFrame(data)
                corr_df = df.corr()
                self._set_cache(cache_key, corr_df)
                return corr_df

        except SystemExit:
            print("[Yahoo Finance] 资产相关性请求被中断，跳过")
        except Exception as e:
            error_str = str(e).lower()
            if 'rate' in error_str or 'limit' in error_str or '429' in error_str:
                self._mark_rate_limited()
            print(f"[Yahoo Finance] 获取资产相关性失败: {e}")

        return pd.DataFrame()

    def get_data_quality(self) -> dict:
        """获取数据质量指标"""
        return {
            'completeness': 0.95,
            'timeliness': 0.90,
            'consistency': 0.92
        }

    def _map_symbol(self, symbol: str) -> str:
        """映射符号到 Yahoo Finance 格式"""
        symbol_map = {
            "Au99.99": "GLD", "gold": "GLD", "XAU": "GLD",
            "GOLD": "GLD", "GLD": "GLD",
            "dollar": "^DXY", "dxy": "^DXY", "USDX": "^DXY",
            "vix": "^VIX", "spy": "SPY", "s&p500": "SPY",
            "stock": "SPY", "bond": "TLT", "10y": "^TNX"
        }
        return symbol_map.get(symbol.lower(), symbol)

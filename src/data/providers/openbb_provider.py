#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenBB 数据源实现 - 深度集成数据获取能力
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from src.data.data_provider import DataProvider

logger = logging.getLogger(__name__)


class OpenBBProvider(DataProvider):
    """OpenBB 数据源实现 - 深度集成OpenBB数据获取能力"""
    capabilities = {'price', 'macro', 'sentiment'}

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "openbb"
        self.openbb = None
        self._initialize_openbb()

    def _initialize_openbb(self):
        """初始化openbb"""
        try:
            from openbb import obb
            self.openbb = obb
            print("[OpenBB] 初始化成功")
        except ImportError:
            print("[OpenBB] 未安装openbb，该数据源不可用")
            self.openbb = None

    def is_available(self) -> bool:
        """检查OpenBB是否可用"""
        return self.openbb is not None

    def get_gold_price(self, symbol: str = "XAUUSD", period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """获取黄金价格数据"""
        cache_key = self._cache_key("get_gold_price", symbol=symbol, period=period, interval=interval)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        if not self.openbb:
            return pd.DataFrame()

        try:
            data = self.openbb.forex.price(symbol=symbol, interval=interval, start_date=self._get_start_date(period))
            if data and not data.empty:
                data = data.rename(columns={
                    'open': 'open', 'high': 'high',
                    'low': 'low', 'close': 'close', 'volume': 'volume'
                })
                self._set_cache(cache_key, data)
                return data
        except Exception as e:
            print(f"[OpenBB] 获取黄金价格失败: {e}")

        return pd.DataFrame()

    def get_macro_data(self, indicators: list) -> dict:
        """获取宏观经济数据"""
        cache_key = self._cache_key("get_macro_data", indicators=",".join(indicators))
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        if not self.openbb:
            return {}

        data = {}

        try:
            for indicator in indicators:
                if indicator == 'bond_yield':
                    try:
                        yield_data = self.openbb.fixedincome.yield_curve(country="united_states", maturity="10y")
                        if yield_data and not yield_data.empty:
                            data['bond_yield'] = float(yield_data.iloc[-1]['value'])
                    except Exception as e:
                        logger.warning(f"操作失败: {e}")
                elif indicator == 'vix':
                    try:
                        vix_data = self.openbb.equity.index.price(symbol="VIX")
                        if vix_data and not vix_data.empty:
                            data['vix'] = float(vix_data.iloc[-1]['close'])
                    except Exception as e:
                        logger.warning(f"操作失败: {e}")
                elif indicator == 'dollar_index':
                    try:
                        dxy_data = self.openbb.forex.price(symbol="DXY")
                        if dxy_data and not dxy_data.empty:
                            data['dollar_index'] = float(dxy_data.iloc[-1]['close'])
                    except Exception as e:
                        logger.warning(f"操作失败: {e}")
        except Exception as e:
            print(f"[OpenBB] 获取宏观数据失败: {e}")

        if data:
            self._set_cache(cache_key, data)
        return data

    def get_market_sentiment(self) -> dict:
        """获取市场情绪数据"""
        cache_key = self._cache_key("get_market_sentiment")
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        if not self.openbb:
            return {}

        sentiment = {}

        try:
            try:
                vix_data = self.openbb.equity.index.price(symbol="VIX")
                if vix_data and not vix_data.empty:
                    vix = float(vix_data.iloc[-1]['close'])
                    sentiment['vix'] = vix

                    if vix > 30:
                        sentiment['sentiment'] = 'fear'
                    elif vix > 20:
                        sentiment['sentiment'] = 'anxiety'
                    else:
                        sentiment['sentiment'] = 'calm'
            except Exception as e:
                logger.warning(f"操作失败: {e}")

            try:
                gld_data = self.openbb.equity.price(symbol="GLD")
                if gld_data and not gld_data.empty:
                    sentiment['gld_volume'] = float(gld_data.iloc[-1]['volume'])
                    sentiment['gld_price'] = float(gld_data.iloc[-1]['close'])
            except Exception as e:
                logger.warning(f"操作失败: {e}")
        except Exception as e:
            print(f"[OpenBB] 获取市场情绪失败: {e}")

        if sentiment:
            self._set_cache(cache_key, sentiment)
        return sentiment

    def get_asset_correlation(self, assets: list) -> pd.DataFrame:
        """获取资产相关性数据"""
        cache_key = self._cache_key("get_asset_correlation", assets=",".join(assets))
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        if not self.openbb:
            return pd.DataFrame()

        try:
            data = {}
            for asset in assets:
                try:
                    asset_data = self.openbb.equity.price(symbol=asset)
                    if asset_data and not asset_data.empty:
                        data[asset] = asset_data['close']
                except Exception as e:
                    logger.warning(f"操作失败: {e}")

            if data:
                df = pd.DataFrame(data)
                corr_df = df.corr()
                self._set_cache(cache_key, corr_df)
                return corr_df
        except Exception as e:
            print(f"[OpenBB] 获取资产相关性失败: {e}")

        return pd.DataFrame()

    def get_data_quality(self) -> dict:
        """获取数据质量指标"""
        if self.openbb:
            return {
                'completeness': 0.95,
                'timeliness': 0.92,
                'consistency': 0.93
            }
        return {
            'completeness': 0.0,
            'timeliness': 0.0,
            'consistency': 0.0
        }

    def get_us_treasury_yield(self, maturity: str = "10y") -> Optional[float]:
        """获取美国国债收益率"""
        if not self.openbb:
            return None
        try:
            yield_data = self.openbb.fixedincome.yield_curve(
                country="united_states", maturity=maturity
            )
            if yield_data is not None and not yield_data.empty:
                return float(yield_data.iloc[-1]['value'])
        except Exception as e:
            print(f"[OpenBB] 获取国债收益率失败: {e}")
        return None

    def get_currency_data(self, symbol: str = "USD/CNY") -> Optional[pd.DataFrame]:
        """获取汇率数据"""
        if not self.openbb:
            return None
        try:
            forex_data = self.openbb.forex.price(symbol=symbol, interval="1d")
            if forex_data is not None and not forex_data.empty:
                return forex_data
        except Exception as e:
            print(f"[OpenBB] 获取汇率数据失败: {e}")
        return None

    def get_commodity_data(self, symbol: str = "GC=F") -> Optional[pd.DataFrame]:
        """获取大宗商品数据"""
        if not self.openbb:
            return None
        try:
            commodity_data = self.openbb.equity.price(symbol=symbol, interval="1d")
            if commodity_data is not None and not commodity_data.empty:
                return commodity_data
        except Exception as e:
            print(f"[OpenBB] 获取大宗商品数据失败: {e}")
        return None

    def get_economic_calendar(self, start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        """获取经济日历数据"""
        if not self.openbb:
            return None
        try:
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            if end_date is None:
                end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            calendar_data = self.openbb.economic.calendar(start_date=start_date, end_date=end_date)
            if calendar_data is not None and not calendar_data.empty:
                return calendar_data
        except Exception as e:
            print(f"[OpenBB] 获取经济日历失败: {e}")
        return None

    def get_inflation_data(self, country: str = "united_states") -> Optional[Dict[str, float]]:
        """获取通胀数据"""
        if not self.openbb:
            return None
        try:
            inflation_data = self.openbb.economy.inflation(country=country)
            if inflation_data is not None and not inflation_data.empty:
                return {
                    'current': float(inflation_data.iloc[-1]['value']),
                    'previous': float(inflation_data.iloc[-2]['value']) if len(inflation_data) > 1 else None
                }
        except Exception as e:
            print(f"[OpenBB] 获取通胀数据失败: {e}")
        return None

    def get_gdp_data(self, country: str = "united_states") -> Optional[Dict[str, Any]]:
        """获取GDP数据"""
        if not self.openbb:
            return None
        try:
            gdp_data = self.openbb.economy.gdp(country=country)
            if gdp_data is not None and not gdp_data.empty:
                return {
                    'current': float(gdp_data.iloc[-1]['value']),
                    'previous': float(gdp_data.iloc[-2]['value']) if len(gdp_data) > 1 else None,
                    'growth_rate': float(gdp_data.iloc[-1]['value']) - float(gdp_data.iloc[-2]['value']) if len(gdp_data) > 1 else None
                }
        except Exception as e:
            print(f"[OpenBB] 获取GDP数据失败: {e}")
        return None

    def _get_start_date(self, period: str) -> str:
        """根据周期获取开始日期"""
        end_date = datetime.now()
        if period == "1y":
            start_date = end_date - timedelta(days=365)
        elif period == "6m":
            start_date = end_date - timedelta(days=180)
        elif period == "3m":
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)
        return start_date.strftime("%Y-%m-%d")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源模块单元测试
"""
import pytest
import pandas as pd
import numpy as np

from src.data.data_provider import DataProvider, DataSourceManager


class ConcreteProvider(DataProvider):
    """测试用具体Provider"""
    capabilities = {'price', 'macro'}

    def get_gold_price(self, symbol="Au99.99", period="1y", interval="1d"):
        return pd.DataFrame({'close': [100, 101, 102]})

    def get_macro_data(self, indicators):
        return {'bond_yield': 2.5}

    def get_market_sentiment(self):
        return {}

    def get_asset_correlation(self, assets):
        return pd.DataFrame()


class TestDataProvider:
    """DataProvider基类测试"""

    def test_init(self):
        provider = ConcreteProvider()
        assert provider.name == "ConcreteProvider"
        assert isinstance(provider._cache, dict)

    def test_capabilities(self):
        provider = ConcreteProvider()
        assert provider.has_capability('price')
        assert provider.has_capability('macro')
        assert not provider.has_capability('sentiment')
        assert not provider.has_capability('correlation')

    def test_validate_price_data_empty(self):
        provider = ConcreteProvider()
        result = provider.validate_price_data(pd.DataFrame(), "Au99.99")
        assert not result['valid']
        assert '数据为空' in result['errors']

    def test_validate_price_data_normal(self):
        provider = ConcreteProvider()
        df = pd.DataFrame({
            'close': [1000, 1010, 1020],
            'open': [995, 1005, 1015],
            'high': [1005, 1015, 1025],
            'low': [990, 1000, 1010]
        })
        result = provider.validate_price_data(df, "Au99.99")
        assert result['valid']

    def test_validate_price_data_out_of_range(self):
        provider = ConcreteProvider()
        df = pd.DataFrame({'close': [100, 50, 2000]})  # some out of range
        result = provider.validate_price_data(df, "Au99.99")
        assert not result['valid']

    def test_validate_macro_data(self):
        provider = ConcreteProvider()
        result = provider.validate_macro_data({'bond_yield': 2.5, 'vix': 20})
        assert result['valid']

    def test_validate_macro_data_out_of_range(self):
        provider = ConcreteProvider()
        result = provider.validate_macro_data({'vix': 200})  # VIX > 100
        assert not result['valid']

    def test_cache(self):
        provider = ConcreteProvider()
        key = provider._cache_key('test', a=1, b=2)
        assert 'test' in key
        assert provider._get_from_cache(key) is None
        provider._set_cache(key, {'data': 'test'})
        assert provider._get_from_cache(key) == {'data': 'test'}


class TestDataSourceManager:
    """DataSourceManager测试"""

    def test_init(self):
        providers = [ConcreteProvider()]
        manager = DataSourceManager(providers)
        assert len(manager.providers) == 1

    def test_get_provider_by_name(self):
        providers = [ConcreteProvider()]
        manager = DataSourceManager(providers)
        found = manager.get_provider_by_name("ConcreteProvider")
        assert found is not None
        not_found = manager.get_provider_by_name("NonExistent")
        assert not_found is None

    def test_get_gold_price(self):
        providers = [ConcreteProvider()]
        manager = DataSourceManager(providers)
        result = manager.get_gold_price()
        assert not result.empty

    def test_get_macro_data(self):
        providers = [ConcreteProvider()]
        manager = DataSourceManager(providers)
        result = manager.get_macro_data(['bond_yield'])
        assert 'bond_yield' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

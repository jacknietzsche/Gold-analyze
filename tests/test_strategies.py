#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略模块单元测试
"""
import pytest
import pandas as pd
import numpy as np

from src.analysis.strategies import GoldStrategies, _realized_vol


class TestRealizedVol:
    """已实现波动率函数测试"""

    def test_basic_vol(self):
        prices = pd.Series([100, 101, 102, 100, 105, 103, 108, 110, 107, 112,
                            115, 113, 118, 120, 117, 122, 125, 123, 128, 130,
                            127, 132])
        vol = _realized_vol(prices, window=20)
        assert vol >= 0.05  # minimum 5%
        assert vol < 1.0    # should be reasonable

    def test_short_series(self):
        prices = pd.Series([100, 101, 102])
        vol = _realized_vol(prices, window=20)
        assert vol == 0.15  # default 15%

    def test_constant_price(self):
        prices = pd.Series([100] * 30)
        vol = _realized_vol(prices, window=20)
        assert vol >= 0.05  # minimum floor


class TestGoldStrategies:
    """策略类测试"""

    def setup_method(self):
        self.strategies = GoldStrategies()

    def test_init(self):
        assert hasattr(self.strategies, 'strategies_data')
        assert isinstance(self.strategies.strategies_data, dict)

    def test_calculate_returns(self):
        prices = pd.Series([100, 102, 104, 103, 108])
        returns = self.strategies._calculate_returns(prices, period=2)
        assert len(returns) == len(prices)

    def test_calculate_vif(self):
        np.random.seed(42)
        X = pd.DataFrame({
            'a': np.random.randn(50),
            'b': np.random.randn(50),
            'c': np.random.randn(50)
        })
        vif = self.strategies._calculate_vif(X)
        assert len(vif) == 3
        assert all(vif['VIF'] >= 1.0)

    def test_multi_factor_empty_factors(self):
        """测试空因子输入"""
        gold_df = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=10, freq='B'),
            'close': np.random.randn(10) * 10 + 1000
        })
        result = self.strategies.multi_factor_scoring_strategy({}, gold_df)
        assert result is None

    def test_event_driven_no_signals(self):
        """测试无事件信号情况"""
        gold_df = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=10, freq='B'),
            'close': np.random.randn(10) * 10 + 1000
        })
        result = self.strategies.event_driven_strategy({}, gold_df)
        assert result is not None
        assert result['signal'] == 0
        assert '无显著事件信号' in result['reasons']

    def test_rule_based_no_rules(self):
        """测试无规则触发情况"""
        gold_df = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=10, freq='B'),
            'close': np.random.randn(10) * 10 + 1000
        })
        result = self.strategies.rule_based_strategy({}, gold_df)
        assert result is not None
        assert result['signal'] == 0
        assert '无规则触发' in result['rules']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

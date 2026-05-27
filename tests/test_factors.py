#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
因子计算模块单元测试
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

# 导入被测模块
from src.analysis.factors import GoldFactors


class TestGoldFactors:
    """GoldFactors 类测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.factors = GoldFactors()

    def _make_price_df(self, n=100, base=1000, trend=0.001):
        """生成模拟价格数据"""
        dates = pd.date_range('2025-01-01', periods=n, freq='B')
        close = base * np.exp(np.cumsum(np.random.randn(n) * 0.01 + trend))
        return pd.DataFrame({
            'date': dates,
            'open': close * (1 + np.random.randn(n) * 0.005),
            'high': close * (1 + abs(np.random.randn(n) * 0.01)),
            'low': close * (1 - abs(np.random.randn(n) * 0.01)),
            'close': close,
            'volume': np.random.randint(1000, 10000, n)
        })

    def test_init(self):
        """测试初始化"""
        assert hasattr(self.factors, 'factors_data')
        assert isinstance(self.factors.factors_data, dict)
        assert len(self.factors.factors_data) == 0

    def test_align_data(self):
        """测试数据对齐"""
        gold_df = self._make_price_df(50)
        factor_series = pd.Series(
            np.random.randn(30),
            index=pd.date_range('2025-02-01', periods=30, freq='B')
        )
        aligned = self.factors._align_data(gold_df, factor_series)
        assert len(aligned) > 0
        # 对齐后应有前23个NaN（因子数据从2月1日开始），后面有值
        assert aligned.notna().sum() > 0

    def test_log_return(self):
        """测试对数收益率计算"""
        prices = pd.Series([100, 101, 102, 100, 105])
        returns = self.factors._log_return(prices)
        assert len(returns) == len(prices)
        assert abs(returns.iloc[1] - np.log(101 / 100)) < 1e-10

    def test_calculate_dxy_return_empty(self):
        """测试空DXY数据处理"""
        gold_df = self._make_price_df(50)
        empty_df = pd.DataFrame()
        result = self.factors.calculate_dxy_return(empty_df, gold_df)
        assert isinstance(result, pd.Series)
        assert len(result) == 0

    def test_factors_data_init(self):
        """测试factors_data初始化"""
        assert self.factors.factors_data == {}
        self.factors.factors_data['test'] = pd.Series([1, 2, 3])
        assert 'test' in self.factors.factors_data


class TestFactorNormalization:
    """因子标准化测试"""

    def test_normalize_factors(self):
        """测试因子z-score标准化"""
        from src.analysis.strategies import GoldStrategies
        strategies = GoldStrategies()
        factor_dict = {
            'test_factor': pd.Series(np.random.randn(100) * 10 + 50)
        }
        normalized = strategies._normalize_factors(factor_dict)
        assert 'test_factor' in normalized
        assert abs(normalized['test_factor'].mean()) < 0.1
        assert abs(normalized['test_factor'].std() - 1.0) < 0.2

    def test_normalize_factors_insufficient_data(self):
        """测试数据不足时的标准化"""
        from src.analysis.strategies import GoldStrategies
        strategies = GoldStrategies()
        factor_dict = {
            'short_factor': pd.Series([1, 2, 3])  # 不足10个数据点
        }
        normalized = strategies._normalize_factors(factor_dict)
        assert len(normalized) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

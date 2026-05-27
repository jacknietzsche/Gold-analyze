#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险管理模块单元测试
"""
import pytest
import pandas as pd
import numpy as np

from src.analysis.risk_manager import VolatilityTargetManager, RiskMetrics


class TestVolatilityTargetManager:
    """波动率目标化管理器测试"""

    def setup_method(self):
        self.vtm = VolatilityTargetManager(vol_target=0.15, max_leverage=2.0)

    def _make_price(self, n=100, base=1000):
        dates = pd.date_range('2025-01-01', periods=n, freq='B')
        close = base * np.exp(np.cumsum(np.random.randn(n) * 0.01))
        return pd.Series(close, index=dates)

    def test_init(self):
        assert self.vtm.vol_target == 0.15
        assert self.vtm.max_leverage == 2.0

    def test_compute_realized_vol(self):
        price = self._make_price(100)
        rv = self.vtm.compute_realized_vol(price)
        assert len(rv) == len(price)
        assert all(rv.dropna() >= 0)

    def test_scale_position(self):
        price = self._make_price(100)
        raw_signal = pd.Series(np.random.choice([-1, 0, 1], 100), index=price.index)
        scaled = self.vtm.scale_position(raw_signal, price)
        assert len(scaled) == len(price)
        assert all(scaled <= self.vtm.max_leverage)
        assert all(scaled >= 0)

    def test_summary(self):
        price = self._make_price(100)
        raw_signal = pd.Series(np.ones(100), index=price.index)
        scaled = self.vtm.scale_position(raw_signal, price)
        summary = self.vtm.summary(price, scaled)
        assert 'vol_target' in summary
        assert 'avg_realized_vol' in summary
        assert 'avg_position' in summary


class TestRiskMetrics:
    """风险价值计算器测试"""

    def setup_method(self):
        self.rm = RiskMetrics(confidence=0.95)

    def test_historical_var(self):
        returns = pd.Series(np.random.randn(200) * 0.02)
        var = self.rm.historical_var(returns, window=100)
        assert len(var) == len(returns)
        # VaR should be negative (loss)
        valid_var = var.dropna()
        assert all(valid_var <= 0)

    def test_historical_cvar(self):
        returns = pd.Series(np.random.randn(200) * 0.02)
        cvar = self.rm.historical_cvar(returns, window=100)
        assert len(cvar) == len(returns)
        # CVaR should be more negative than VaR
        valid_cvar = cvar.dropna()
        assert all(valid_cvar <= 0)

    def test_parametric_var(self):
        returns = pd.Series(np.random.randn(200) * 0.02)
        var = self.rm.parametric_var(returns, window=100)
        assert len(var) == len(returns)

    def test_max_drawdown_manual(self):
        """测试最大回撤计算（手动实现）"""
        prices = pd.Series([100, 110, 105, 90, 95, 100])
        peak = prices.expanding().max()
        drawdown = (prices - peak) / peak
        mdd = drawdown.min()
        assert mdd <= 0
        assert abs(mdd - (-20/110)) < 0.01  # ~18% drawdown


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术指标模块单元测试 — 验证 indicators.py 纯函数
"""
import pytest
import pandas as pd
import numpy as np

from src.analysis.indicators import (
    ema, moving_average, rsi, rsi_signal, macd, macd_signal_text,
    bollinger_bands, boll_position, boll_signal_text,
    kdj, kdj_signal_text, atr, atr_from_ohlc,
    volatility, rolling_volatility, period_returns, ma_system_signal,
    compute_all,
)


@pytest.fixture
def sample_prices():
    """100日模拟金价序列"""
    np.random.seed(42)
    n = 100
    close = 1000 * np.exp(np.cumsum(np.random.randn(n) * 0.01))
    return pd.Series(close, index=pd.date_range('2025-01-01', periods=n, freq='B'))


@pytest.fixture
def sample_ohlc():
    """100日模拟OHLC数据"""
    np.random.seed(42)
    n = 100
    close = 1000 * np.exp(np.cumsum(np.random.randn(n) * 0.01))
    high = close * (1 + abs(np.random.randn(n) * 0.01))
    low = close * (1 - abs(np.random.randn(n) * 0.01))
    return pd.DataFrame({'high': high, 'low': low, 'close': close},
                        index=pd.date_range('2025-01-01', periods=n, freq='B'))


class TestEma:
    def test_basic(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = ema(data, 3)
        assert len(result) == 5
        assert result[0] == 1.0  # first value unchanged

    def test_short_data(self):
        data = np.array([1.0, 2.0])
        result = ema(data, 5)
        assert len(result) == 2


class TestRSI:
    def test_output_length(self, sample_prices):
        result = rsi(sample_prices, 14)
        assert len(result) == len(sample_prices)

    def test_range(self, sample_prices):
        result = rsi(sample_prices, 14).dropna()
        assert all(result >= 0)
        assert all(result <= 100)

    def test_short_data(self):
        prices = pd.Series([100, 101, 102])
        result = rsi(prices, 14)
        assert len(result) == 3

    def test_rsi_signal_text(self):
        assert rsi_signal(85) == "严重超买"
        assert rsi_signal(75) == "超买"
        assert rsi_signal(50) == "中性"
        assert rsi_signal(25) == "超卖"
        assert rsi_signal(15) == "严重超卖"


class TestMACD:
    def test_output_types(self, sample_prices):
        dif, dea, hist = macd(sample_prices)
        assert isinstance(dif, pd.Series)
        assert isinstance(dea, pd.Series)
        assert isinstance(hist, pd.Series)

    def test_lengths(self, sample_prices):
        dif, dea, hist = macd(sample_prices)
        assert len(dif) == len(sample_prices)
        assert len(dea) == len(sample_prices)
        assert len(hist) == len(sample_prices)

    def test_signal_text(self):
        assert macd_signal_text(1.0, 0.5, 2.0, 1.0) == "多头增强"
        assert macd_signal_text(1.0, 0.5, 1.0, 2.0) == "多头减弱"
        assert macd_signal_text(-1.0, 0.5, -2.0, -1.0) == "空头增强"
        assert macd_signal_text(0.0, 0.0, 0.0, 0.0) == "零轴附近"


class TestBollinger:
    def test_output_types(self, sample_prices):
        upper, mid, lower = bollinger_bands(sample_prices)
        assert isinstance(upper, pd.Series)

    def test_band_ordering(self, sample_prices):
        upper, mid, lower = bollinger_bands(sample_prices)
        valid = upper.dropna().index.intersection(mid.dropna().index)
        assert all(upper[valid] >= mid[valid])
        assert all(mid[valid] >= lower[valid])

    def test_position(self):
        assert abs(boll_position(110, 120, 100) - 50.0) < 0.01
        assert boll_position(120, 120, 100) == 100.0
        assert boll_position(100, 120, 100) == 0.0

    def test_signal_text(self):
        assert "超买" in boll_signal_text(121, 120, 100, 105)
        assert "超卖" in boll_signal_text(99, 120, 100, -5)
        assert "正常" in boll_signal_text(110, 120, 100, 50)


class TestKDJ:
    def test_output_lengths(self, sample_prices):
        k, d, j = kdj(sample_prices)
        assert len(k) == len(sample_prices)
        assert len(d) == len(sample_prices)
        assert len(j) == len(sample_prices)

    def test_with_hl(self, sample_ohlc):
        k, d, j = kdj(sample_ohlc['close'], sample_ohlc['high'], sample_ohlc['low'])
        assert len(k.dropna()) > 0

    def test_signal_text(self):
        assert "严重超买" in kdj_signal_text(85, 82, 90)
        assert "严重超卖" in kdj_signal_text(15, 18, 10)
        assert "多头" in kdj_signal_text(60, 40, 100)
        assert "空头" in kdj_signal_text(40, 60, 0)


class TestATR:
    def test_with_ohlc(self, sample_ohlc):
        result = atr(sample_ohlc['high'], sample_ohlc['low'], sample_ohlc['close'])
        assert isinstance(result, pd.Series)
        assert all(result.dropna() >= 0)

    def test_atr_from_ohlc(self, sample_ohlc):
        result = atr_from_ohlc(sample_ohlc)
        assert len(result) == len(sample_ohlc)


class TestVolatility:
    def test_basic(self, sample_prices):
        vol = volatility(sample_prices, 20)
        assert 0 < vol < 2  # reasonable range

    def test_default(self):
        vol = volatility(pd.Series([100, 101, 102]), 20)
        assert vol == 0.15  # default for insufficient data

    def test_rolling(self, sample_prices):
        result = rolling_volatility(sample_prices, 20)
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_prices)


class TestPeriodReturns:
    def test_basic(self, sample_prices):
        result = period_returns(sample_prices)
        assert '近1日' in result
        assert '近252日(1年)' in result

    def test_insufficient_data(self):
        prices = pd.Series([100, 101])
        result = period_returns(prices)
        assert result['近1日'] is not None
        assert result['近252日(1年)'] is None


class TestMASignal:
    def test_output_format(self, sample_prices):
        status, detail = ma_system_signal(sample_prices)
        assert isinstance(status, str)
        assert isinstance(detail, str)


class TestComputeAll:
    def test_returns_dict(self, sample_prices):
        result = compute_all(sample_prices)
        assert isinstance(result, dict)
        assert 'rsi_14' in result
        assert 'macd_dif' in result
        assert 'boll_upper' in result
        assert 'kdj_k' in result
        assert 'atr_14' in result
        assert 'ma_signal' in result

    def test_with_ohlc(self, sample_ohlc):
        result = compute_all(sample_ohlc['close'], sample_ohlc['high'], sample_ohlc['low'])
        assert 'atr_14' in result
        assert result['atr_14'] > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

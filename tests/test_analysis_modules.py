#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 4 分析模块单元测试
gram_scorer / risk_analyzer / trend_judger / candle_patterns
"""
import pytest
import pandas as pd
import numpy as np

from src.analysis.gram_scorer import score_gram
from src.analysis.risk_analyzer import compute_risk_metrics, compute_stress_tests, risk_level, full_risk_analysis
from src.analysis.trend_judger import judge_trend
from src.analysis.candle_patterns import identify_patterns


# ── gram_scorer ──────────────────────────────────────────────

class TestGramScorer:
    def test_basic(self):
        data = {
            'tips_yield': 1.0, 'vix': 20,
            'central_bank_buying': 10,
            'returns': {'近20日(1月)': {'value': 2}, '近60日(3月)': {'value': 5}}
        }
        result = score_gram(data)
        assert 'total_score' in result
        assert 'outlook' in result
        assert 0 <= result['total_score'] <= 10

    def test_high_vix(self):
        data = {'vix': 40, 'tips_yield': 0.5, 'central_bank_buying': 100,
                'returns': {'近20日(1月)': {'value': 3}, '近60日(3月)': {'value': 8}}}
        result = score_gram(data)
        assert result['total_score'] > 5

    def test_empty_returns(self):
        data = {'tips_yield': 2.0, 'vix': 15}
        result = score_gram(data)
        assert 'total_score' in result


# ── risk_analyzer ────────────────────────────────────────────

class TestRiskAnalyzer:
    @pytest.fixture
    def returns(self):
        np.random.seed(42)
        return pd.Series(np.random.randn(200) * 0.02)

    def test_compute_risk_metrics(self, returns):
        m = compute_risk_metrics(returns)
        assert 'max_drawdown' in m
        assert 'value_at_risk' in m
        assert 'sharpe_ratio' in m
        assert m['max_drawdown'] <= 0

    def test_insufficient_data(self):
        assert compute_risk_metrics(pd.Series([0.01, -0.01])) == {}

    def test_stress_tests(self):
        tests = compute_stress_tests(-2.0, vix=30)
        assert 'interest_rate_shock' in tests
        assert 'geopolitical_risk' in tests

    def test_risk_level(self):
        assert risk_level(-5) == '低风险'
        assert risk_level(-15) == '中等风险'
        assert risk_level(-25) == '较高风险'
        assert risk_level(-35) == '高风险'

    def test_full_risk_analysis(self, returns):
        result = full_risk_analysis(returns, bond_yield=2.0, vix=20)
        assert 'stress_test' in result
        assert 'risk_level' in result


# ── trend_judger ─────────────────────────────────────────────

class TestTrendJudger:
    def test_bullish(self):
        data = {
            'returns': {'近5日': {'value': 3}, '近20日(1月)': {'value': 8}},
            'rsi_14': 55, 'macd_signal': '多头增强',
            'gram': {'total_score': 7}
        }
        result = judge_trend(data)
        assert result['score'] >= 6
        assert result['outlook'] in ('看多', '偏多')

    def test_bearish(self):
        data = {
            'returns': {'近5日': {'value': -3}, '近20日(1月)': {'value': -8}},
            'rsi_14': 25, 'macd_signal': '空头增强',
            'gram': {'total_score': 3}
        }
        result = judge_trend(data)
        assert result['score'] <= 4
        assert result['outlook'] in ('看空', '偏空')

    def test_neutral(self):
        data = {'returns': {}, 'rsi_14': 50, 'macd_signal': '', 'gram': {'total_score': 5}}
        result = judge_trend(data)
        assert 0 <= result['score'] <= 10


# ── candle_patterns ──────────────────────────────────────────

class TestCandlePatterns:
    def test_empty(self):
        result = identify_patterns(None)
        assert result[0]['name'] == '无明显形态'

    def test_doji(self):
        # 十字星: open ≈ close, 有上下影线
        ohlc = pd.DataFrame({
            'open': [100, 100, 100, 100, 100.05],
            'high': [101, 101, 101, 101, 102],
            'low':  [99, 99, 99, 99, 98],
            'close': [100, 100, 100, 100, 100.02]
        })
        result = identify_patterns(ohlc)
        names = [p['name'] for p in result]
        assert '十字星' in names

    def test_hammer(self):
        # 锤头线: 长下影线, 阳线, body > range*0.1 (不触发十字星)
        ohlc = pd.DataFrame({
            'open': [100, 100, 100, 100, 90],
            'high': [101, 101, 101, 101, 92],
            'low':  [99, 99, 99, 99, 80],
            'close': [100, 100, 100, 100, 91.5]
        })
        result = identify_patterns(ohlc)
        names = [p['name'] for p in result]
        assert '锤头线' in names


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

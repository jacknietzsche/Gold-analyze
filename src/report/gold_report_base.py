#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金量化分析报告基类 - 共享逻辑提取
包含 v5 和 v6 共同使用的所有方法和属性
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.analysis.indicators import (
    rsi as _rsi, macd as _macd, macd_signal_text, bollinger_bands,
    boll_position, boll_signal_text, kdj as _kdj, kdj_signal_text,
    atr as _atr, ma_system_signal, compute_all
)
from src.analysis.gram_scorer import score_gram
from src.analysis.risk_analyzer import full_risk_analysis
from src.analysis.trend_judger import judge_trend
from src.analysis.candle_patterns import identify_patterns
from src.analysis.scenario_engine import calculate_scenario_probabilities
from src.report.html_helpers import (
    safe_float as _safe_float, trend_word as _trend_word,
    gram_outlook_text as _gram_outlook_text, rsi_color as _rsi_color,
    rsi_bg as _rsi_bg, rsi_label as _rsi_label,
    hist_zone_label as _hist_zone_label, kdj_color as _kdj_color,
    kdj_bg as _kdj_bg, markdown_to_html as _markdown_to_html
)
from pathlib import Path
import warnings
import os
import json
import re
import sys
import io
import logging
from typing import Optional, Dict

# 修复 Windows GBK 控制台无法输出 emoji/Unicode 字符的问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

# 导入数据服务 (懒加载)
from src.data.data_service import get_data_service

# ===== Phase 2-4 新增量化分析模块导入 =====
try:
    from src.analysis.backtester import GoldBacktester, ICAnalyzer, evaluate_and_weight_factors
    _BACKTESTER_AVAILABLE = True
except Exception:
    _BACKTESTER_AVAILABLE = False

try:
    from src.analysis.risk_manager import (
        VolatilityTargetManager, RiskMetrics,
        ShanghaiGoldPremiumFactor, apply_all_macro_lags,
        generate_risk_summary
    )
    _RISK_MANAGER_AVAILABLE = True
except Exception:
    _RISK_MANAGER_AVAILABLE = False

try:
    from src.analysis.regime_detector import MarketRegimeDetector, run_optimization_pipeline
    _REGIME_DETECTOR_AVAILABLE = True
except Exception:
    _REGIME_DETECTOR_AVAILABLE = False

try:
    from src.config.gold_config import CONFIG
except ImportError:
    class DefaultConfig:
        class LLMConfig:
            llm_type = "chatanywhere"
        class TechnicalConfig:
            return_periods = {
                '近1日': 2, '近5日': 6, '近20日(1月)': 21,
                '近60日(3月)': 61, '近120日(6月)': 121, '近252日(1年)': 253
            }
    CONFIG = DefaultConfig()


class GoldReportBase:
    """黄金量化分析报告基类 - 包含所有共享逻辑"""

    # 固定主题结构
    FIXED_TOPICS = [
        {
            'id': 'core_conclusion',
            'title': '核心结论解读',
            'description': '基于技术面和基本面分析的综合结论',
            'required': True
        },
        {
            'id': 'technical_analysis',
            'title': '技术分析',
            'description': '基于技术指标的详细分析',
            'required': True
        },
        {
            'id': 'fundamental_analysis',
            'title': '基本面分析',
            'description': '基于宏观经济和供需因素的分析',
            'required': True
        },
        {
            'id': 'scenario_analysis',
            'title': '情景分析',
            'description': '不同市场情景下的金价表现预测',
            'required': True
        },
        {
            'id': 'risk_warning',
            'title': '风险预警识别',
            'description': '潜在风险因素的识别和评估',
            'required': True
        },
        {
            'id': 'investment_strategy',
            'title': '投资策略建议',
            'description': '基于不同时间 horizon 的投资策略',
            'required': True
        },
        {
            'id': 'market_outlook',
            'title': '市场展望',
            'description': '短期,中期和长期市场展望',
            'required': True
        },
        {
            'id': 'performance_metrics',
            'title': '绩效指标',
            'description': '黄金与其他资产的表现对比',
            'required': True
        },
        {
            'id': 'risk_assessment',
            'title': '风险评估',
            'description': '风险量化分析和压力测试',
            'required': True
        },
        {
            'id': 'portfolio_allocation',
            'title': '投资组合配置',
            'description': '基于不同风险偏好的黄金配置建议',
            'required': True
        }
    ]

    def __init__(self, llm_type=None, use_llm=True, api_key=None):
        self.report_date = datetime.now()
        self.data = {}
        self.errors = []
        self.llm_type = llm_type or getattr(CONFIG, 'llm', CONFIG).llm_type
        self.use_llm = use_llm
        self.api_key = api_key
        self.industry_benchmarks = {
            'gold_etf': 'GLD',
            's&p500': 'SPY',
            'bond_index': 'TLT',
            'commodity_index': 'DBC'
        }
        # 初始化主题内容存储
        self.topic_content = {}

    # ==============================================================
    # Phase 2-4 量化分析增强方法
    # ==============================================================

    def run_quantitative_analysis(self, price_series: 'pd.Series',
                                   factors_dict: dict = None) -> dict:
        """
        运行完整量化分析(回测 + IC评估 + 风险管理 + 机制检测)。

        Parameters
        ----------
        price_series  : 黄金收盘价(pd.Series，索引为日期)
        factors_dict  : 已计算的因子字典(可选)

        Returns
        -------
        quant_result  : dict，含所有量化分析结果，存入 self.data['quant']
        """
        import numpy as np
        quant = {}

        if price_series is None or len(price_series) < 60:
            self.data['quant'] = quant
            return quant

        price_series = price_series.dropna().sort_index()
        log_ret = np.log(price_series / price_series.shift(1))

        # ---- Phase 2: 回测引擎 ----
        if _BACKTESTER_AVAILABLE:
            try:
                bt = GoldBacktester(price_series)
                # 动量信号回测(20日)
                mom20 = log_ret.rolling(20).sum()
                sig   = pd.Series(0, index=price_series.index)
                sig[mom20 > 0]  = 1
                sig[mom20 < 0]  = -1
                r_mom = bt.run(sig, 'momentum_20d', long_only=True)
                quant['backtest_momentum'] = r_mom['stats']

                # 均线多空策略
                ma5  = price_series.rolling(5).mean()
                ma20_p = price_series.rolling(20).mean()
                sig_ma = pd.Series(0, index=price_series.index)
                sig_ma[(ma5 > ma20_p) & (ma5.shift(1) <= ma20_p.shift(1))] = 1
                sig_ma[(ma5 < ma20_p) & (ma5.shift(1) >= ma20_p.shift(1))] = -1
                # 持仓状态
                pos_ma = sig_ma.replace(0, np.nan).ffill().fillna(0)
                r_ma = bt.run(pos_ma, 'ma_crossover', long_only=True)
                quant['backtest_ma_crossover'] = r_ma['stats']

                # IC 因子评估
                if factors_dict:
                    analyzer = ICAnalyzer(forward_period=20)
                    ic_df = analyzer.evaluate_all_factors(factors_dict, price_series)
                    if not ic_df.empty:
                        quant['ic_report'] = ic_df.head(10).to_dict('records')
                        w = analyzer.suggest_weights(ic_df)
                        quant['ic_suggested_weights'] = w.to_dict() if not w.empty else {}
            except Exception as e:
                quant['backtest_error'] = str(e)

        # ---- Phase 3: 风险管理 ----
        if _RISK_MANAGER_AVAILABLE:
            try:
                risk_summary = generate_risk_summary(
                    price_series, log_ret,
                    position_value_wan=10.0,
                    vol_target=0.10,
                    confidence=0.95
                )
                quant['risk_summary'] = risk_summary

                # 波动率目标化当前仓位建议
                vtm = VolatilityTargetManager(vol_target=0.10)
                rv  = vtm.compute_realized_vol(price_series)
                latest_rv = float(rv.dropna().iloc[-1]) if not rv.dropna().empty else None
                quant['realized_vol_ann'] = round(latest_rv * 100, 2) if latest_rv else None
                quant['vol_target_position'] = (
                    round(min(0.10 / latest_rv, 1.5), 3) if latest_rv and latest_rv > 0 else 1.0
                )
            except Exception as e:
                quant['risk_error'] = str(e)

        # ---- Phase 4: 市场机制检测 ----
        if _REGIME_DETECTOR_AVAILABLE:
            try:
                detector = MarketRegimeDetector()
                current_regime  = detector.get_current_regime(price_series)
                regime_stats_df = detector.regime_stats(price_series)
                quant['regime_current'] = current_regime
                quant['regime_stats']   = regime_stats_df.to_dict('records') if not regime_stats_df.empty else []
            except Exception as e:
                quant['regime_error'] = str(e)

        self.data['quant'] = quant
        print(f"[量化分析] 完成: {list(quant.keys())}")
        return quant

    def _fv_quant(self, key: str, default: str = '--') -> str:
        """安全获取量化分析结果中的值"""
        quant = self.data.get('quant', {})
        val = quant.get(key, default)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return default
        return str(val)

    def fetch_all_data(self):
        """获取所有真实数据"""
        import sys
        print("\n[1] 使用多源数据服务获取黄金数据...", flush=True)
        sys.stdout.flush()

        # 使用数据服务获取所有数据
        all_data = get_data_service().get_all_data()

        # 处理价格数据
        price_data = all_data['price']
        if not price_data.empty:
            # 使用真实的价格数据，不硬编码
            # 确保数据按日期排序
            price_data = price_data.sort_index()

            # 设置数据
            self.data['sge_price_series'] = price_data['close']
            self.data['sge_latest_price'] = float(price_data.iloc[-1]['close'])
            self.data['sge_latest_date'] = str(price_data.index[-1])[:10]
            self.data['data_count'] = len(price_data)
            self.data['start_date'] = str(price_data.index[0])[:10]

            # 存储OHLC用于K线分析
            if all(col in price_data.columns for col in ['open', 'high', 'low', 'close']):
                self.data['sge_ohlc'] = price_data[['open', 'high', 'low', 'close']].copy()
                print(f"  成功: {len(price_data)} 条记录 | OHLC: 完整")
            else:
                print(f"  成功: {len(price_data)} 条记录 | OHLC: 不完整")

            # 计算技术指标
            self.calculate_period_returns()
            self.calculate_technical_indicators()
            self.calculate_gram_factors()
            self.identify_candle_patterns()
            self.calculate_recent_trend_judgment()
            self.calculate_risk_analysis()
            print(f"  [OK] 技术指标计算完成", flush=True)
            sys.stdout.flush()
        else:
            print("  失败: 未获取到价格数据，使用默认值", flush=True)
            sys.stdout.flush()
            self.errors.append("未获取到价格数据，使用默认值")

            # 提供默认价格数据
            self.data['sge_latest_price'] = 1048.50
            self.data['sge_latest_date'] = self.report_date.strftime('%Y-%m-%d')
            self.data['data_count'] = 0
            self.data['start_date'] = self.report_date.strftime('%Y-%m-%d')

            # 计算默认技术指标
            self.data['returns'] = {
                '近5日': {'value': 0.0, 'is_positive': True},
                '近20日(1月)': {'value': 0.0, 'is_positive': True},
                '近60日(3月)': {'value': 0.0, 'is_positive': True},
                '近120日(6月)': {'value': 0.0, 'is_positive': True},
                '近252日(1年)': {'value': 0.0, 'is_positive': True}
            }
            self.data['latest_date_str'] = self.report_date.strftime('%Y-%m-%d')

            # 默认技术指标
            self.data['ma5'] = 1048.50
            self.data['ma20'] = 1048.50
            self.data['ma60'] = 1048.50
            self.data['rsi_14'] = 50.0
            self.data['macd_signal'] = '零轴附近'
            self.data['boll_signal'] = '正常区间'
            self.data['kdj_signal'] = '中性'
            self.data['high_60d'] = 1048.50
            self.data['low_60d'] = 1048.50

            # 默认GRAM数据
            self.data['gram'] = {
                'opportunity_cost': {'score': 5, 'interpretation': '中性'},
                'risk_uncertainty': {'score': 5, 'interpretation': '中性'},
                'supply_demand': {'score': 5, 'interpretation': '中性'},
                'momentum': {'score': 5, 'interpretation': '中性'},
                'total_score': 5,
                'outlook': '中性',
                'color': '#d4af37'
            }

        # 处理宏观数据
        macro_data = all_data['macro']
        if macro_data:
            for key, value in macro_data.items():
                self.data[key] = value
            print(f"  国债: {self.data.get('bond_yield', '--')}% | VIX: {self.data.get('vix', '--')} | DXY: {self.data.get('dollar_index', '--')}")
            print(f"  央行购金: {self.data.get('central_bank_buying', '--')}吨/月 | 中国储备: {self.data.get('china_reserves', '--')}吨")
        else:
            print("[WARN] 宏观数据获取失败，相关指标将标记为不可用")
            self.errors.append("宏观数据获取失败")
            # 下游代码通过 self.data.get('key') 返回None，报告模板显示 '--'

        # 处理行业对标数据
        self.fetch_industry_benchmarks()
        self.calculate_industry_comparison()

        # ===== Phase 2-4: 运行量化分析(回测+风险+机制)=====
        price_series = self.data.get('sge_price_series')
        if price_series is not None and len(price_series) >= 60:
            print("\n[量化增强] 运行 Phase 2-4 量化分析模块...")
            # 从已有技术因子构建 factors_dict(可选，IC评估用)
            _f = {}
            for _fn in ['rsi', 'ma_trend', 'macd_dif', 'bb_position', 'momentum_20d',
                        'atr_ratio', 'donchian_position', 'volatility_20d']:
                if _fn in self.data:
                    _f[_fn] = self.data[_fn]
            self.run_quantitative_analysis(price_series, _f if _f else None)

        return self.data

    def fetch_sge_data(self):
        """获取上海金历史数据(含OHLC)"""
        try:
            import akshare as ak
            sge = ak.spot_hist_sge(symbol='Au99.99')
            if sge is not None and len(sge) > 0:
                sge['date'] = pd.to_datetime(sge['date'])
                sge = sge.sort_values('date').reset_index(drop=True)

                price_col = None
                for col in ['收盘价', '收盘', 'close', 'Close']:
                    if col in sge.columns:
                        price_col = col
                        break

                if price_col:
                    # 尝试获取OHLC数据
                    ohlc_cols = {}
                    for target, candidates in [
                        ('open', ['开盘价', '开盘', 'open', 'Open']),
                        ('high', ['最高价', '最高', 'high', 'High']),
                        ('low', ['最低价', '最低', 'low', 'Low']),
                    ]:
                        for c in candidates:
                            if c in sge.columns:
                                ohlc_cols[target] = c
                                break

                    self.data['sge_price_series'] = sge.set_index('date')[price_col]
                    self.data['sge_latest_price'] = float(sge.iloc[-1][price_col])
                    self.data['sge_latest_date'] = str(sge.iloc[-1]['date'])[:10]
                    self.data['data_count'] = len(sge)
                    self.data['start_date'] = str(sge.iloc[0]['date'])[:10]

                    # 存储OHLC用于K线分析
                    if len(ohlc_cols) == 3:
                        self.data['sge_ohlc'] = sge.set_index('date')[[ohlc_cols['open'], ohlc_cols['high'], ohlc_cols['low'], price_col]].copy()
                        self.data['sge_ohlc'].columns = ['open', 'high', 'low', 'close']

                    print(f"  成功: {len(sge)} 条记录 | OHLC: {'有' if len(ohlc_cols)==3 else '仅收盘'}")
                else:
                    print(f"  失败: 未找到价格列，可用列: {sge.columns.tolist()}")
                    self.errors.append("未找到价格列")
            else:
                print("  失败: 返回空数据")
                self.errors.append("上海金数据为空")
        except Exception as e:
            print(f"  失败: {e}")
            self.errors.append(f"上海金: {e}")

    def fetch_industry_benchmarks(self):
        """获取行业对标数据 -- 从真实市场API获取，不使用硬编码假数据"""
        import akshare as ak
        print("\n[3] 获取行业对标数据(真实市场数据)...")
        benchmarks = {}

        # ---- 1. 获取黄金ETF (GLD) 对标 ----
        # 使用上海金Au99.99作为黄金基准(与主分析标的相同)
        try:
            sge_gold = ak.spot_hist_sge(symbol='Au99.99')
            if sge_gold is not None and len(sge_gold) > 0:
                sge_gold['date'] = pd.to_datetime(sge_gold['date'])
                sge_gold = sge_gold.sort_values('date')
                price_col = None
                for c in ['收盘价', '收盘', 'close', 'Close']:
                    if c in sge_gold.columns:
                        price_col = c; break
                if price_col:
                    prices = sge_gold[price_col].astype(float)
                    latest_g = float(prices.iloc[-1])
                    # YTD return
                    current_year = self.report_date.year
                    ytd_data = prices[sge_gold['date'].dt.year == current_year]
                    if len(ytd_data) >= 2:
                        ytd_ret = (latest_g / float(ytd_data.iloc[0]) - 1) * 100
                    else:
                        ytd_ret = (latest_g / float(prices.iloc[0]) - 1) * 100
                    # 波动率 (年化)
                    daily_ret = prices.pct_change().dropna()
                    volatility = float(daily_ret.std() * np.sqrt(252)) * 100
                    # 夏普比率 (假设无风险利率1.8%)
                    rf = 0.018
                    sharpe = round(float(daily_ret.mean() - rf/252) / daily_ret.std() * np.sqrt(252), 2) if daily_ret.std() > 0 else 0

                    benchmarks['gold_etf'] = {
                        'name': 'Au99.99(SGE)',
                        'price': round(latest_g, 2),
                        'ytd_return': round(ytd_ret, 2),
                        'volatility': round(volatility, 2),
                        'sharpe_ratio': sharpe,
                        '_real_data': True
                    }
                    print(f"  [OK] 上海金Au99.99: CNY {round(latest_g,2)} | YTD:{ytd_ret:+.2f}% | Vol:{round(volatility,1)}% | Sharpe:{sharpe}")
        except Exception as e:
            print(f"  [WARN] 黄金基准数据获取失败: {e}")

        # ---- 2. 获取美股对标 (S&P500 via 标普500指数) ----
        us_indices = {}
        try:
            # 尝试获取美股主要指数
            sp_data = ak.index_us_stock_sina(symbol=".INX")  # S&P 500
            if sp_data is not None and len(sp_data) > 0:
                sp_data['date'] = pd.to_datetime(sp_data['date'])
                sp_data = sp_data.sort_values('date')
                sp_close = sp_data['close'].astype(float)
                sp_latest = float(sp_close.iloc[-1])
                current_year = self.report_date.year
                sp_ytd = sp_data[sp_data['date'].dt.year == current_year]
                if len(sp_ytd) >= 2:
                    sp_ytd_ret = (sp_latest / float(sp_ytd['close'].iloc[0]) - 1) * 100
                else:
                    sp_ytd_ret = (sp_latest / float(sp_close.iloc[0]) - 1) * 100
                sp_vol = float(sp_close.pct_change().dropna().std() * np.sqrt(252)) * 100
                rf = 0.018
                sp_sharpe = round(float(sp_close.pct_change().dropna().mean() - rf/252) / sp_close.pct_change().dropna().std() * np.sqrt(252), 2)

                benchmarks['s&p500'] = {
                    'name': 'S&P500(.INX)',
                    'price': round(sp_latest, 2),
                    'ytd_return': round(sp_ytd_ret, 2),
                    'volatility': round(sp_vol, 2),
                    'sharpe_ratio': sp_sharpe,
                    '_real_data': True
                }
                us_indices['sp500'] = sp_close
                print(f"  [OK] S&P500: {round(sp_latest,2)} | YTD:{sp_ytd_ret:+.2f}% | Vol:{round(sp_vol,1)}%")
        except Exception as e:
            print(f"  [WARN] S&P500数据获取失败: {e}")

        # ---- 3. 获取中国10Y国债收益率作为债券对标 ----
        try:
            bond_data = ak.bond_china_yield()
            if bond_data is not None and len(bond_data) > 0:
                date_col = None
                for c in bond_data.columns:
                    if '日期' in str(c) or 'date' in str(c).lower():
                        date_col = c; break
                if date_col:
                    ten_year = bond_data[bond_data.get('债券期限', '') == '10年']
                    if len(ten_year) > 0:
                        bond_price_proxy = 100 - float(ten_year.iloc[-1].get('到期收益率', 2.0))  # 价格代理
                        # 债券YTD用收益率变化估算
                        if len(ten_year) >= 2:
                            y_start = float(ten_year.iloc[0].get('到期收益率', 2.0))
                            y_now = float(ten_year.iloc[-1].get('到期收益率', 2.0))
                            bond_ytd_ret = (y_start - y_now)  # 收益率下降=价格上涨
                            # 动态计算国债波动率和夏普比率（基于真实数据）
                            all_yields = ten_year['到期收益率'].astype(float)
                            bond_volatility = round(float(all_yields.pct_change().dropna().std() * np.sqrt(252) * 100), 2) if len(all_yields) > 5 else None
                            daily_ret_est = (y_start - y_now) / max(len(ten_year), 1)
                            bond_sharpe = round(daily_ret_est / (all_yields.pct_change().dropna().std() or 0.01) * np.sqrt(252), 2) if len(all_yields) > 5 else None
                        else:
                            # 数据不足时不再硬编码假值，返回None并标记为非真实数据
                            bond_ytd_ret = None
                            bond_volatility = None
                            bond_sharpe = None

                        benchmarks['bond_index'] = {
                            'name': '中国10Y国债',
                            'price': round(bond_price_proxy, 2),
                            'ytd_return': round(bond_ytd_ret, 2) if bond_ytd_ret is not None else None,
                            'volatility': bond_volatility,
                            'sharpe_ratio': bond_sharpe,
                            '_real_data': bond_ytd_ret is not None and bond_volatility is not None
                        }
                        print(f"  [OK] 中国10Y国债: 收益率{round(float(ten_year.iloc[-1].get('到期收益率',0)),2)}%")
        except Exception as e:
            print(f"  [WARN] 国债数据获取失败: {e}")

        # ---- 4. 大宗商品对标 (用南华商品指数或CRB代理) ----
        try:
            # 尝试多个接口获取大宗商品指数(akshare版本兼容)
            nhci = None

            # 方法1: index_symbol_nh(旧版 akshare 可能有)
            if hasattr(ak, 'index_symbol_nh'):
                try:
                    nhci = ak.index_symbol_nh(symbol="南华商品指数")
                except Exception as e:
                    logger.warning(f"操作失败: {e}")

            # 方法2: macro_china_commodity_price_index(新版推荐)
            if nhci is None or len(nhci) == 0:
                if hasattr(ak, 'macro_china_commodity_price_index'):
                    try:
                        commodity_data = ak.macro_china_commodity_price_index()
                        if commodity_data is not None and not commodity_data.empty:
                            # 取"中国大宗商品价格指数"列作为代理
                            for col in commodity_data.columns:
                                if '指数' in str(col) or '价格' in str(col):
                                    s = pd.to_numeric(commodity_data[col], errors='coerce').dropna()
                                    if len(s) > 10:
                                        # 构造标准格式
                                        date_cols = [c for c in commodity_data.columns if '日期' in str(c) or 'date' in str(c).lower()]
                                        if date_cols:
                                            commodity_data['date'] = pd.to_datetime(commodity_data[date_cols[0]])
                                            commodity_data[col] = s
                                            nhci = commodity_data[['date', col]].rename(columns={col: 'close'})
                                            break
                    except Exception as e_nhci:
                        print(f"  [DEBUG] macro_china_commodity_price_index 失败: {e_nhci}")

            # 方法3: 用期货主力合约数据构造大宗商品指数代理
            if nhci is None or len(nhci) == 0:
                try:
                    from src.data.providers.akshare_provider import AkShareDataProvider as _AKP
                    _akp = _AKP()
                    # 通过原油/铜/黄金期货组合模拟大宗商品走势
                    pass  # 暂不实现，保持 None 让 fallback 处理
                except Exception as e:
                    logger.warning(f"操作失败: {e}")
            if nhci is not None and len(nhci) > 0:
                nhci_date_col = None
                for c in nhci.columns:
                    if '日期' in str(c) or 'date' in str(c).lower():
                        nhci_date_col = c; break
                if nhci_date_col:
                    nhci[nhci_date_col] = pd.to_datetime(nhci[nhci_date_col])
                    nhci = nhci.sort_values(nhci_date_col)
                    price_col_nhc = None
                    for c in ['收盘价', 'close', 'Close', '收盘']:
                        if c in nhci.columns:
                            price_col_nhc = c; break
                    if price_col_nhc:
                        nhc_close = nhci[price_col_nhc].astype(float)
                        nhc_latest = float(nhc_close.iloc[-1])
                        cy = self.report_date.year
                        nhc_ytd_d = nhci[nhci[nhci_date_col].dt.year == cy]
                        if len(nhc_ytd_d) >= 2:
                            nhc_ytd_ret = (nhc_latest / float(nhc_ytd_d[price_col_nhc].iloc[0]) - 1) * 100
                        else:
                            nhc_ytd_ret = (nhc_latest / float(nhc_close.iloc[0]) - 1) * 100
                        nhc_vol = float(nhc_close.pct_change().dropna().std() * np.sqrt(252)) * 100

                        benchmarks['commodity_index'] = {
                            'name': '南华商品指数',
                            'price': round(nhc_latest, 2),
                            'ytd_return': round(nhc_ytd_ret, 2),
                            'volatility': round(nhc_vol, 2),
                            'sharpe_ratio': round(nhc_ytd_ret / max(nhc_vol, 0.1), 2),
                            '_real_data': True
                        }
                        print(f"  [OK] 南华商品指数: {round(nhc_latest,2)} | YTD:{nhc_ytd_ret:+.2f}% | Vol:{round(nhc_vol,1)}%")
        except Exception as e:
            print(f"  [WARN] 大宗商品指数获取失败: {e}")

        # 如果某些资产未能获取，标记为不可用而非填充假数据
        expected_keys = ['gold_etf', 's&p500', 'bond_index', 'commodity_index']
        for key in expected_keys:
            if key not in benchmarks:
                print(f"  [!] {key}: 数据不可用(无硬编码替代)")
                benchmarks[key] = {
                    'name': {'gold_etf':'GLD','s&p500':'SPY','bond_index':'TLT','commodity_index':'DBC'}[key],
                    'price': None,
                    'ytd_return': None,
                    'volatility': None,
                    'sharpe_ratio': None,
                    '_real_data': False,
                    '_unavailable': '数据源暂不可用'
                }

        self.data['industry_benchmarks'] = benchmarks
        available_count = sum(1 for v in benchmarks.values() if v.get('_real_data'))
        print(f"\n  行业对标: {available_count}/{len(benchmarks)} 个来源已获取真实数据")

    def calculate_industry_comparison(self):
        """计算行业对标比较 -- 基于真实数据计算相关性和风险指标"""
        print("\n[4] 计算行业对标比较(基于真实数据)...")

        comparison = {}
        gold_series = self.data.get('sge_price_series')

        # ---- 相关性矩阵:基于实际收益率序列计算或标记为不可用 ----
        if gold_series is not None and len(gold_series) > 30:
            # 使用黄金自身数据作为基准
            gold_returns = gold_series.pct_change().dropna()

            correlation_matrix = {'gold': 1.0}
            # 其他资产的相关性需要多资产时间序列对齐，这里先标注为"需多源数据"
            for key in ['gold_etf', 's&p500', 'bond_index', 'commodity_index']:
                bench = self.data.get('industry_benchmarks', {}).get(key, {})
                if not bench.get('_real_data') or not bench.get('_unavailable'):
                    correlation_matrix[key] = None  # 标记为无真实数据
                else:
                    # 如果未来有完整的多资产时间序列可在此处做 rolling corr 计算
                    correlation_matrix[key] = None

            comparison['correlation_matrix'] = correlation_matrix
            print(f"  [OK] 相关性矩阵: 已初始化(多资产相关性需对齐时间序列)")
        else:
            comparison['correlation_matrix'] = {'gold': 1.0}
            print(f"  [!] 相关性矩阵: 数据不足")

        # ---- 风险调整后收益:使用已获取的真实值，不伪造 ----
        risk_adjusted_returns = {}
        benchmarks = self.data.get('industry_benchmarks', {})

        if gold_series is not None and len(gold_series) > 60:
            gold_ret = gold_series.pct_change().dropna()
            rf = 0.018 / 252  # 日化无风险利率
            gold_sharpe = round(float((gold_ret.mean() - rf) / gold_ret.std() * np.sqrt(252)), 2) if gold_ret.std() > 0 else 0
            risk_adjusted_returns['gold'] = gold_sharpe
        else:
            risk_adjusted_returns['gold'] = None

        for key in ['gold_etf', 's&p500', 'bond_index', 'commodity_index']:
            bench = benchmarks.get(key, {})
            if bench.get('_real_data') and bench.get('sharpe_ratio') is not None:
                risk_adjusted_returns[key] = bench['sharpe_ratio']
            else:
                risk_adjusted_returns[key] = None

        comparison['risk_adjusted_returns'] = risk_adjusted_returns

        # ---- 投资组合配置建议(基于现代投资组合理论) ----
        # 根据黄金当前波动率和夏普比率动态调整
        gold_sharpe = risk_adjusted_returns.get('gold')
        if gold_sharpe is not None:
            if gold_sharpe > 1.0:
                # 夏普比率优秀，建议高配
                conservative_pct = 20
                moderate_pct = 15
                aggressive_pct = 10
            elif gold_sharpe > 0.5:
                # 夏普比率良好，建议中配
                conservative_pct = 15
                moderate_pct = 10
                aggressive_pct = 7
            elif gold_sharpe > 0:
                # 夏普比率为正，建议低配
                conservative_pct = 10
                moderate_pct = 7
                aggressive_pct = 5
            else:
                # 夏普比率为负，建议最低配
                conservative_pct = 5
                moderate_pct = 3
                aggressive_pct = 2
        else:
            # 数据不足，使用中性配置
            conservative_pct = 10
            moderate_pct = 7
            aggressive_pct = 5

        comparison['portfolio_allocation'] = {
            'conservative': conservative_pct,
            'moderate': moderate_pct,
            'aggressive': aggressive_pct
        }
        print(f"  投资组合建议: 保守型{conservative_pct}% | 平衡型{moderate_pct}% | 进取型{aggressive_pct}%")

        self.data['industry_comparison'] = comparison

    def calculate_period_returns(self):
        """计算各周期涨跌幅"""
        series = self.data['sge_price_series']
        latest = series.iloc[-1]
        periods = getattr(CONFIG, 'technical', CONFIG).return_periods
        returns = {}
        for name, offset in periods.items():
            if len(series) > offset:
                prev = series.iloc[-offset]
                ret = (latest - prev) / prev * 100
                returns[name] = {'value': round(ret, 2), 'is_positive': ret >= 0}
            else:
                ret = (latest - series.iloc[0]) / series.iloc[0] * 100
                returns[name] = {'value': round(ret, 2), 'is_positive': ret >= 0}
        self.data['returns'] = returns
        self.data['latest_date_str'] = series.index[-1].strftime('%Y-%m-%d')

    def calculate_technical_indicators(self):
        """计算完整技术指标体系 - 委托 indicators.py"""
        series = self.data.get('sge_price_series')
        if series is None or len(series) < 60:
            return

        # OHLC 数据（用于 ATR）
        highs = self.data['sge_ohlc']['high'] if 'sge_ohlc' in self.data else None
        lows = self.data['sge_ohlc']['low'] if 'sge_ohlc' in self.data else None

        result = compute_all(series, highs, lows)
        self.data.update(result)

    def calculate_risk_analysis(self):
        """计算风险量化分析和压力测试 — 委托 risk_analyzer"""
        print("\n[5] 计算风险量化分析...")
        series = self.data.get('sge_price_series')
        if series is not None and len(series) > 60:
            returns = series.pct_change().dropna()
            bond_yield = self.data.get('bond_yield', 2.0)
            vix = self.data.get('vix', 20)
            risk = full_risk_analysis(returns, bond_yield, vix)
            self.data['risk_analysis'] = risk
            if risk:
                print(f"  最大回撤: {risk['max_drawdown']:.2f}% | VaR(95%): {risk['value_at_risk']:.2f}% | 夏普比率: {risk['sharpe_ratio']:.2f}")
                print(f"  风险等级: {risk['risk_level']}")
        else:
            self.data['risk_analysis'] = {}
            print("  数据不足，无法计算风险指标")

    def calculate_recent_trend_judgment(self):
        """近期趋势判断 — 委托 trend_judger"""
        result = judge_trend(self.data)
        self.data['recent_trend'] = result
        print(f"  近期趋势: {result['trend']} (评分: {result['score']:.1f}/10, 展望: {result['outlook']})")

    def calculate_gram_factors(self):
        """计算GRAM因子 — 委托 gram_scorer"""
        gram = score_gram(self.data)
        self.data['gram'] = gram
        ts = gram['total_score']
        print(f"  GRAM评分: {ts:.1f}/10 ({gram['outlook']})")
        oc = gram['opportunity_cost']['score']
        ru = gram['risk_uncertainty']['score']
        sd = gram['supply_demand']['score']
        mo = gram['momentum']['score']
        print(f"    机会成本:{oc:.1f} | 风险:{ru:.1f} | 供需:{sd:.1f} | 动量:{mo:.1f}")

    def identify_candle_patterns(self):
        """识别K线形态 — 委托 candle_patterns"""
        ohlc = self.data.get('sge_ohlc')
        patterns = identify_patterns(ohlc)
        self.data['candle_patterns'] = patterns
        print(f"  K线形态: {', '.join([p['name'] for p in patterns])}")

    @staticmethod
    def _markdown_to_html(md_text):
        return _markdown_to_html(md_text)

    def _trend_word(self, value):
        return _trend_word(value)

    def _get_trend_desc(self, value):
        return _trend_word(value)

    @staticmethod
    def _gram_outlook_text(score):
        return _gram_outlook_text(score)

    @staticmethod
    def _rsi_color(v):
        return _rsi_color(v)

    @staticmethod
    def _rsi_bg(v):
        return _rsi_bg(v)

    @staticmethod
    def _rsi_label(v):
        return _rsi_label(v)

    @staticmethod
    def _safe_float(val, default=0):
        return _safe_float(val, default)

    @staticmethod
    def _hist_zone_label(p):
        return _hist_zone_label(p)

    @staticmethod
    def _kdj_color(jv):
        return _kdj_color(jv)

    @staticmethod
    def _kdj_bg(jv):
        return _kdj_bg(jv)

    def _build_quant_html_section(self) -> str:
        """构建量化分析HTML区块"""
        quant = self.data.get('quant', {})
        if not quant:
            return ''

        html = '''
        <div class="section">
            <h2><span class="section-num">Q</span>量化分析模块 (Phase 2-4)</h2>
            <div class="card">
        '''

        # 回测结果
        if 'backtest_momentum' in quant:
            bt = quant['backtest_momentum']
            html += f'''
                <h3>动量策略回测 (20日)</h3>
                <p>年化收益: {bt.get('annual_return', '--')}% | 最大回撤: {bt.get('max_drawdown', '--')}% | 夏普比率: {bt.get('sharpe_ratio', '--')}</p>
            '''

        if 'backtest_ma_crossover' in quant:
            bt = quant['backtest_ma_crossover']
            html += f'''
                <h3>均线交叉策略回测</h3>
                <p>年化收益: {bt.get('annual_return', '--')}% | 最大回撤: {bt.get('max_drawdown', '--')}% | 夏普比率: {bt.get('sharpe_ratio', '--')}</p>
            '''

        # 风险指标
        if 'risk_summary' in quant:
            rs = quant['risk_summary']
            html += f'''
                <h3>风险指标</h3>
                <p>年化波动率: {rs.get('annual_volatility', '--')}% | VaR(95%): {rs.get('var_95', '--')}% | CVaR: {rs.get('cvar_95', '--')}%</p>
            '''

        # 市场机制
        if 'regime_current' in quant:
            regime = quant['regime_current']
            html += f'''
                <h3>市场机制检测</h3>
                <p>当前机制: {regime.get('regime', '--')} | 置信度: {regime.get('confidence', '--')}</p>
            '''

        html += '</div></div>'
        return html

    def _calculate_scenario_probabilities(self, d: dict) -> dict:
        return calculate_scenario_probabilities(d)

    def validate_topics(self):
        """验证所有固定主题是否已填充内容"""
        missing_topics = []
        for topic in self.FIXED_TOPICS:
            if topic['required'] and topic['id'] not in self.topic_content:
                missing_topics.append(topic['title'])

        if missing_topics:
            print(f"[验证] 缺少以下必填主题内容: {', '.join(missing_topics)}")
            # 为缺少的主题添加fallback内容
            for topic in self.FIXED_TOPICS:
                if topic['id'] not in self.topic_content:
                    self.topic_content[topic['id']] = self._get_fallback_content(topic['id'])
            print("[验证] 已为缺少的主题添加fallback内容")
        else:
            print("[验证] 所有固定主题已填充内容")

        return len(missing_topics) == 0

    def _get_fallback_content(self, topic_id):
        """获取主题的fallback内容 - 子类应覆盖此方法"""
        return f"<p>暂无{topic_id}的分析内容</p>"

    def generate_html_report(self):
        """生成HTML报告 - 子类应覆盖此方法"""
        raise NotImplementedError("子类必须实现 generate_html_report 方法")

    def generate_ai_content_for_topics(self):
        """生成AI内容 - 子类应覆盖此方法"""
        raise NotImplementedError("子类必须实现 generate_ai_content_for_topics 方法")

    def save_report(self, filepath=None, use_llm=None, llm_type=None):
        """保存报告到文件 - 子类应覆盖此方法"""
        raise NotImplementedError("子类必须实现 save_report 方法")

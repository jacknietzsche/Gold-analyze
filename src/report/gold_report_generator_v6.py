#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金量化分析报告生成器 V6 - 专业增强版
参考: 世界黄金协会(WGC) GRAM框架 + 高盛/摩根大通技术分析体系 + 行业领先量化机构最佳实践

V6新增特性:
1. FRED数据集成 (TIPS实际利率, 盈亏平衡通胀率, CPI, M2等)
2. 增强的LLM API集成 (OpenRouter/SiliconFlow/ChatAnywhere等)
3. 专业级报告设计系统
4. 增强的量化策略建议
5. FRED黄金专属指标面板
"""

import os
import json
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

import pandas as pd
import numpy as np

from src.report.gold_report_base import GoldReportBase
from src.data.fred_client import fetch_fred_data as _fetch_fred, fetch_fred_series as _fetch_fred_series

logger = logging.getLogger(__name__)


class GoldReportGeneratorV6(GoldReportBase):
    """黄金量化分析报告生成器 V6 - 专业增强版"""

    def __init__(self, llm_type=None, use_llm=True, api_key=None):
        super().__init__(llm_type=llm_type, use_llm=use_llm, api_key=api_key)
        print(f"=== 黄金量化报告生成器 V6 (专业增强版) ===")
        print(f"报告日期: {self.report_date.strftime('%Y-%m-%d')}")
        print(f"行业对标: {list(self.industry_benchmarks.values())}")
        print(f"使用LLM: {self.use_llm}")
        print(f"固定主题数: {len(self.FIXED_TOPICS)}")
        from src.report.gold_report_base import _BACKTESTER_AVAILABLE, _RISK_MANAGER_AVAILABLE, _REGIME_DETECTOR_AVAILABLE
        print(f"量化模块: Backtester={'OK' if _BACKTESTER_AVAILABLE else 'N/A'} | "
              f"RiskMgr={'OK' if _RISK_MANAGER_AVAILABLE else 'N/A'} | "
              f"RegimeDet={'OK' if _REGIME_DETECTOR_AVAILABLE else 'N/A'}")

    # ===== V6 特有方法: FRED数据集成 =====

    def _fetch_fred_data(self, series_id: str, limit: int = 1) -> Optional[Dict]:
        """直接调用FRED API获取数据 — 委托 fred_client"""
        return _fetch_fred(series_id, limit)

    def _fetch_fred_series(self, series_id: str, days: int = 365) -> Optional[pd.Series]:
        """获取FRED时间序列 — 委托 fred_client"""
        return _fetch_fred_series(series_id, days)

    def fetch_macro_data(self):
        """获取宏观数据 - 优先FRED，fallback到akshare/其他源"""
        import akshare as ak
        print("\n[2] 获取宏观数据...")

        # 检查FRED API可用性
        fred_key = os.environ.get('FRED_API_KEY', '')
        if not fred_key:
            try:
                from src.config.gold_config import CONFIG
                fred_key = CONFIG.data.api_keys.get('fred', '')
            except Exception:
                fred_key = ''
        fred_available = bool(fred_key)
        print(f"  FRED API: {'已配置' if fred_available else '未配置（使用akshare fallback）'}")

        # === 国债收益率 ===
        bond_yield = None

        # 方法1: FRED DGS10
        if fred_available and bond_yield is None:
            fred_result = self._fetch_fred_data('DGS10')
            if fred_result:
                obs = fred_result.get('observations', [])
                if obs and obs[0]['value'] != '.':
                    bond_yield = float(obs[0]['value'])
                    if -1 <= bond_yield <= 15:
                        self.data['bond_yield'] = bond_yield
                        self.data['_bond_yield_source'] = 'fred_dgs10'
                        print(f"  [OK] 国债收益率(FRED DGS10): {bond_yield:.2f}%")

        # 方法2: akshare bond_china_yield
        if bond_yield is None:
            try:
                bond_yields = ak.bond_china_yield()
                if bond_yields is not None and len(bond_yields) > 0:
                    date_col = None
                    for col in bond_yields.columns:
                        if '日期' in str(col) or 'date' in str(col).lower():
                            date_col = col
                            break
                    if date_col:
                        try:
                            latest_date = pd.to_datetime(bond_yields[date_col].iloc[-1])
                            days_old = (datetime.now() - latest_date).days
                            if days_old <= 30:
                                ten_year = bond_yields[bond_yields.get('债券期限', '') == '10年']
                                if len(ten_year) > 0:
                                    val = ten_year.iloc[-1].get('到期收益率')
                                    if pd.notna(val) and 0 < val < 10:
                                        bond_yield = float(val)
                                        print(f"  [OK] 国债收益率(akshare): {bond_yield:.2f}% (数据日期: {latest_date.strftime('%Y-%m-%d')}, {days_old}天前)")
                                        self.data['bond_yield'] = bond_yield
                                        self.data['_bond_yield_source'] = 'akshare'
                            else:
                                print(f"  [WARN] 国债收益率数据过期 {days_old} 天，尝试其他数据源...")
                        except Exception as e:
                            logger.warning(f"操作失败: {e}")

                    # 如果akshare数据过期，尝试"10年"列
                    if bond_yield is None and '10年' in bond_yields.columns:
                        val = bond_yields['10年'].iloc[-1]
                        if pd.notna(val) and 0 < val < 10:
                            bond_yield = float(val)
                            print(f"  [OK] 国债收益率(10年列): {bond_yield:.2f}%")
                            self.data['bond_yield'] = bond_yield
                            self.data['_bond_yield_source'] = 'akshare_10y'
            except Exception as e:
                print(f"  [WARN] akshare国债数据获取失败: {e}")

        # 方法3: 参考值(仅用于GRAMS评分，不显示在报告中)
        if bond_yield is None:
            bond_yield = 2.0
            print(f"  [INFO] 国债收益率使用参考值: {bond_yield:.2f}% (GRAMS评分用)")

        # === VIX ===
        vix_val = None

        # 方法1: FRED VIXCLS
        if fred_available and vix_val is None:
            fred_result = self._fetch_fred_data('VIXCLS')
            if fred_result:
                obs = fred_result.get('observations', [])
                if obs and obs[0]['value'] != '.':
                    vix_val = float(obs[0]['value'])
                    if 5 < vix_val < 100:
                        self.data['vix'] = vix_val
                        self.data['_vix_source'] = 'fred'
                        print(f"  [OK] VIX(FRED VIXCLS): {vix_val:.2f}")

        # 方法2: akshare
        if vix_val is None:
            try:
                indices = ak.stock_zh_index_spot_em()
                vix_data = indices[indices['名称'].str.contains('波动率', na=False)]
                if len(vix_data) > 0:
                    vix_str = vix_data.iloc[0]['最新价']
                    vix_val = float(vix_str) if vix_str else None
                    if vix_val and 5 < vix_val < 100:
                        self.data['vix'] = vix_val
                        self.data['_vix_source'] = 'eastmoney'
                        print(f"  [OK] VIX(东方财富): {vix_val:.2f}")
            except Exception as e:
                logger.warning(f"操作失败: {e}")

        # 方法3: 基于近期价格波动率估算VIX
        if vix_val is None:
            try:
                price_series = self.data.get('sge_price_series')
                if price_series is not None and len(price_series) >= 20:
                    returns = price_series.pct_change().dropna().tail(20)
                    daily_vol = returns.std()
                    annualized_vol = daily_vol * np.sqrt(252) * 100
                    vix_est = min(max(16 + annualized_vol * 0.5, 10), 40)
                    self.data['vix'] = round(vix_est, 2)
                    self.data['_vix_source'] = 'volatility_est'
                    print(f"  [OK] VIX(价格波动率估算): {vix_est:.2f}")
                    vix_val = vix_est
            except Exception as e:
                logger.warning(f"操作失败: {e}")

        # === 美元指数 ===
        dxy_val = None

        # 方法1: FRED DTWEXBGS
        if fred_available and dxy_val is None:
            fred_result = self._fetch_fred_data('DTWEXBGS')
            if fred_result:
                obs = fred_result.get('observations', [])
                if obs and obs[0]['value'] != '.':
                    dxy_val = float(obs[0]['value'])
                    if 70 <= dxy_val <= 130:
                        self.data['dollar_index'] = dxy_val
                        self.data['_dxy_source'] = 'fred'
                        print(f"  [OK] 美元指数(FRED DTWEXBGS): {dxy_val:.2f}")

        # 方法2: akshare
        if dxy_val is None:
            try:
                fx_data = ak.macro_china_fx_gold()
                if fx_data is not None and len(fx_data) > 0:
                    usd_cny = None
                    for col in fx_data.columns:
                        if '美元' in str(col) or 'USD' in str(col):
                            usd_cny = float(fx_data[col].iloc[-1])
                            break
                    if usd_cny and 6 < usd_cny < 8:
                        dxy_est = 100 + (usd_cny - 7.0) * 20
                        if 80 < dxy_est < 130:
                            self.data['dollar_index'] = round(dxy_est, 2)
                            self.data['_dxy_source'] = 'fx_est'
                            print(f"  [OK] 美元指数(汇率推算): {dxy_est:.2f}")
                            dxy_val = dxy_est
            except Exception as e:
                logger.warning(f"操作失败: {e}")

        # 方法3: 参考值
        if dxy_val is None:
            dxy_val = 104.0
            self.data['dollar_index'] = dxy_val
            self.data['_dxy_source'] = 'reference'
            print(f"  [INFO] 美元指数使用参考值: {dxy_val:.2f} (GRAMS评分用)")

        # === 新增FRED特色指标 ===

        # TIPS实际利率 (DFII10)
        if fred_available:
            fred_result = self._fetch_fred_data('DFII10')
            if fred_result:
                obs = fred_result.get('observations', [])
                if obs and obs[0]['value'] != '.':
                    tips_yield = float(obs[0]['value'])
                    if -2 <= tips_yield <= 10:
                        self.data['tips_yield'] = tips_yield
                        self.data['_tips_source'] = 'fred'
                        print(f"  [OK] TIPS实际利率(FRED DFII10): {tips_yield:.2f}%")

        # 盈亏平衡通胀率 (T10YIE)
        if fred_available:
            fred_result = self._fetch_fred_data('T10YIE')
            if fred_result:
                obs = fred_result.get('observations', [])
                if obs and obs[0]['value'] != '.':
                    breakeven_inf = float(obs[0]['value'])
                    if 0 <= breakeven_inf <= 15:
                        self.data['breakeven_inflation'] = breakeven_inf
                        self.data['_breakeven_source'] = 'fred'
                        print(f"  [OK] 盈亏平衡通胀率(FRED T10YIE): {breakeven_inf:.2f}%")

        # CPI同比变化率
        if fred_available:
            fred_result = self._fetch_fred_data('CPIAUCSL', limit=13)
            if fred_result:
                obs = fred_result.get('observations', [])
                if len(obs) >= 13:
                    try:
                        latest_cpi = float(obs[0]['value'])
                        year_ago_cpi = float(obs[12]['value'])
                        if year_ago_cpi > 0:
                            cpi_yoy = (latest_cpi / year_ago_cpi - 1) * 100
                            if -5 <= cpi_yoy <= 20:
                                self.data['cpi'] = round(cpi_yoy, 2)
                                self.data['_cpi_source'] = 'fred'
                                print(f"  [OK] 美国CPI同比(FRED): {cpi_yoy:.2f}%")
                    except Exception as e:
                        logger.warning(f"操作失败: {e}")

        # M2同比变化率
        if fred_available:
            fred_result = self._fetch_fred_data('M2SL', limit=13)
            if fred_result:
                obs = fred_result.get('observations', [])
                if len(obs) >= 13:
                    try:
                        latest_m2 = float(obs[0]['value'])
                        year_ago_m2 = float(obs[12]['value'])
                        if year_ago_m2 > 0:
                            m2_yoy = (latest_m2 / year_ago_m2 - 1) * 100
                            if -20 <= m2_yoy <= 50:
                                self.data['m2'] = round(m2_yoy, 2)
                                self.data['_m2_source'] = 'fred'
                                print(f"  [OK] 美国M2同比(FRED): {m2_yoy:.2f}%")
                    except Exception as e:
                        logger.warning(f"操作失败: {e}")

        # 标普500指数
        if fred_available:
            fred_result = self._fetch_fred_data('SP500')
            if fred_result:
                obs = fred_result.get('observations', [])
                if obs and obs[0]['value'] != '.':
                    sp500 = float(obs[0]['value'])
                    if 1000 <= sp500 <= 10000:
                        self.data['sp500'] = sp500
                        self.data['_sp500_source'] = 'fred'
                        print(f"  [OK] 标普500指数(FRED): {sp500:.2f}")

        # === FRED黄金专属指标 ===

        # 黄金波动率指数 (GVZCLS)
        if fred_available:
            fred_result = self._fetch_fred_data('GVZCLS')
            if fred_result:
                obs = fred_result.get('observations', [])
                if obs and obs[0]['value'] != '.':
                    gold_vol = float(obs[0]['value'])
                    if 5 <= gold_vol <= 100:
                        self.data['gold_volatility'] = gold_vol
                        self.data['_gold_vol_source'] = 'fred'
                        print(f"  [OK] 黄金波动率指数(FRED GVZCLS): {gold_vol:.2f}")

        # 黄金资金流向指数 (FLOWS103)
        if fred_available:
            fred_result = self._fetch_fred_data('FLOWS103')
            if fred_result:
                obs = fred_result.get('observations', [])
                if obs and obs[0]['value'] != '.':
                    gold_flows = float(obs[0]['value'])
                    self.data['gold_flows'] = gold_flows
                    self.data['_gold_flows_source'] = 'fred'
                    print(f"  [OK] 黄金资金流向指数(FRED FLOWS103): {gold_flows:.2f}")

        # 黄金进口价格指数 (IR14110)
        if fred_available:
            fred_result = self._fetch_fred_data('IR14110')
            if fred_result:
                obs = fred_result.get('observations', [])
                if obs and obs[0]['value'] != '.':
                    gold_imp = float(obs[0]['value'])
                    self.data['gold_import_price'] = gold_imp
                    self.data['_gold_imp_source'] = 'fred'
                    print(f"  [OK] 黄金进口价格指数(FRED): {gold_imp:.2f}")

        # 黄金出口价格指数 (IR14210)
        if fred_available:
            fred_result = self._fetch_fred_data('IR14210')
            if fred_result:
                obs = fred_result.get('observations', [])
                if obs and obs[0]['value'] != '.':
                    gold_exp = float(obs[0]['value'])
                    self.data['gold_export_price'] = gold_exp
                    self.data['_gold_exp_source'] = 'fred'
                    print(f"  [OK] 黄金出口价格指数(FRED): {gold_exp:.2f}")

        # 中国储备(不含黄金) (TRESEGCHM052N)
        if fred_available:
            fred_result = self._fetch_fred_data('TRESEGCHM052N')
            if fred_result:
                obs = fred_result.get('observations', [])
                if obs and obs[0]['value'] != '.':
                    china_res = float(obs[0]['value'])
                    self.data['china_reserves_ex_gold'] = china_res
                    self.data['_china_res_source'] = 'fred'
                    print(f"  [OK] 中国储备(不含黄金)(FRED): {china_res:.2f}亿美元")

        # 美联储黄金证书 (DTGOLD)
        if fred_available:
            fred_result = self._fetch_fred_data('DTGOLD')
            if fred_result:
                obs = fred_result.get('observations', [])
                if obs and obs[0]['value'] != '.':
                    fed_gold = float(obs[0]['value'])
                    self.data['fed_gold_certificate'] = fed_gold
                    self.data['_fed_gold_source'] = 'fred'
                    print(f"  [OK] 美联储黄金证书(FRED): {fed_gold:.2f}亿美元")

        # 央行购金数据通过DataService获取
        print(f"  国债: {self.data.get('bond_yield', '--')}% | VIX: {self.data.get('vix', '--')} | DXY: {self.data.get('dollar_index', '--')}")

    # ===== V6 LLM Methods =====

    def _call_llm_api(self, prompt, max_tokens=2000):
        """调用LLM API获取分析内容 - 使用openai库"""
        try:
            from openai import OpenAI
            import src.config.gold_config as _cfg
            CONFIG = _cfg.CONFIG

            llm_type = CONFIG.llm.llm_type
            print(f'[LLM] 使用 {llm_type} API')

            client = None
            model = ''

            # OpenRouter (优先)
            if llm_type == 'openrouter' and CONFIG.llm.openrouter_api_key:
                client = OpenAI(
                    api_key=CONFIG.llm.openrouter_api_key,
                    base_url=CONFIG.llm.openrouter_base_url
                )
                model = CONFIG.llm.openrouter_model
                print(f'[LLM] OpenRouter 模型: {model}')

            # SiliconFlow
            elif CONFIG.llm.siliconflow_api_key:
                client = OpenAI(
                    api_key=CONFIG.llm.siliconflow_api_key,
                    base_url=CONFIG.llm.siliconflow_base_url
                )
                model = CONFIG.llm.siliconflow_model
                print(f'[LLM] SiliconFlow 模型: {model}')

            # ChatAnywhere
            elif CONFIG.llm.chatanywhere_api_key:
                client = OpenAI(
                    api_key=CONFIG.llm.chatanywhere_api_key,
                    base_url=CONFIG.llm.chatanywhere_base_url
                )
                model = CONFIG.llm.chatanywhere_model
                print(f'[LLM] ChatAnywhere 模型: {model}')

            # OpenAI
            elif CONFIG.llm.openai_api_key:
                client = OpenAI(
                    api_key=CONFIG.llm.openai_api_key,
                    base_url=CONFIG.llm.openai_base_url
                )
                model = CONFIG.llm.openai_model
                print(f'[LLM] OpenAI 模型: {model}')

            # Cherry
            elif CONFIG.llm.cherry_api_key:
                client = OpenAI(
                    api_key=CONFIG.llm.cherry_api_key,
                    base_url=CONFIG.llm.cherry_base_url
                )
                model = CONFIG.llm.cherry_model
                print(f'[LLM] Cherry 模型: {model}')

            else:
                print('[WARN] 未配置任何LLM API Key，跳过AI分析')
                return None

            # 调用API
            response = client.chat.completions.create(
                model=model,
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=max_tokens,
                temperature=CONFIG.llm.temperature,
                timeout=CONFIG.llm.timeout
            )

            # 兼容思考型模型
            msg = response.choices[0].message
            content = msg.content
            reasoning = getattr(msg, 'reasoning_content', None)
            if reasoning is None:
                reasoning = getattr(msg, 'reasoning', None)

            if content is None and reasoning is not None:
                print(f'[LLM] content=None，尝试从reasoning字段提取回答...')
                import re
                match = re.search(r'[答答][案案][：:]\s*(.+)', reasoning, re.IGNORECASE)
                if match:
                    content = match.group(1).strip()
                else:
                    lines = [l.strip() for l in reasoning.split('\n') if l.strip()]
                    chinese_lines = []
                    for line in lines:
                        chinese_count = sum(1 for c in line if '一' <= c <= '鿿')
                        if chinese_count > len(line) * 0.3:
                            chinese_lines.append(line)
                    if chinese_lines:
                        content = '\n'.join(chinese_lines)
                    else:
                        content = reasoning[-500:]

            if content is None:
                print(f'[LLM] 响应content和reasoning均为None，返回空字符串')
                content = ''

            print(f'[LLM] 调用成功，返回 {len(content)} 字符')
            return content

        except Exception as e:
            print(f'[LLM Error] {type(e).__name__}: {e}')
            return None

    def generate_ai_content_for_topics(self):
        """生成AI增强分析内容"""
        d = self.data
        topics = {
            'core_conclusion': self._build_core_prompt(d),
            'scenario_analysis': self._build_scenario_prompt(d),
            'risk_warning': self._build_risk_prompt(d),
            'investment_strategy': self._build_strategy_prompt(d),
        }
        self.topic_content = {}
        print("[LLM] Generating AI content via OpenRouter...")

        for i, (topic, prompt) in enumerate(topics.items(), 1):
            print(f"[LLM] [{i}/4] 正在生成: {topic}...")
            try:
                content = self._call_llm_api(prompt)
                if content and len(content.strip()) > 20:
                    self.topic_content[topic] = self._markdown_to_html(content.strip())
                    print(f"[LLM] [{i}/4] {topic} 生成成功 ({len(content)}字符)")
                else:
                    self.topic_content[topic] = self._get_fallback_content(topic)
                    print(f"[LLM] [{i}/4] {topic} 使用fallback内容")
            except Exception as e:
                print(f"[LLM] [{i}/4] {topic} 生成失败: {e}")
                self.topic_content[topic] = self._get_fallback_content(topic)

        # 为其他主题也填充fallback内容
        for topic in ['technical_analysis', 'fundamental_analysis', 'market_outlook',
                      'performance_metrics', 'risk_assessment', 'portfolio_allocation']:
            if topic not in self.topic_content:
                self.topic_content[topic] = self._get_fallback_content(topic)
        print("[LLM] AI内容生成完成")
        return self.topic_content

    def _build_core_prompt(self, d):
        """构建核心结论提示词"""
        price = d.get('sge_latest_price', 0)
        gram = d.get('gram', {})
        score = gram.get('total_score', 0)
        returns = d.get('returns', {})
        ytd = returns.get('ytd', {}).get('value', 0)

        def safe_get(key, default='数据不可用'):
            val = d.get(key, default)
            if val == '--' or val == 'N/A' or val is None:
                return default
            return val

        rsi = safe_get('rsi_14', 50)
        hp = safe_get('historical_percentile', 50)
        bond = safe_get('bond_yield', 2.5)
        vix = safe_get('vix', 20)
        dxy = safe_get('dollar_index', 100)
        tips = safe_get('tips_yield', 1.5)
        cpi = safe_get('cpi', 2.0)
        m2 = safe_get('m2', 5.0)
        sp500 = safe_get('sp500', 5500)
        gold_vol = safe_get('gold_volatility', 20)
        gold_flow = safe_get('gold_flows', '数据不可用')
        gold_imp = safe_get('gold_import_price', 100)
        gold_exp = safe_get('gold_export_price', 100)
        china_res = safe_get('china_reserves_ex_gold', '数据不可用')
        fed_gold = safe_get('fed_gold_certificate', '数据不可用')

        template = (
            '你是一位黄金市场资深分析师。基于以下数据提供专业分析：\n'
            '- 上海金Au99.99价格：' + str(price) + '元/克\n'
            '- GRAM评分：' + str(score) + '/10\n'
            '- YTD收益：' + str(ytd) + '%\n'
            '- RSI(14)：' + str(rsi) + '\n'
            '- 历史分位：' + str(hp) + '%\n'
            '- 国债收益率：' + str(bond) + '%\n'
            '- VIX恐慌指数：' + str(vix) + '\n'
            '- 美元指数：' + str(dxy) + '\n'
            '- TIPS实际利率：' + str(tips) + '%\n'
            '- 美国CPI同比：' + str(cpi) + '%\n'
            '- 美国M2同比：' + str(m2) + '%\n'
            '- 标普500指数：' + str(sp500) + '\n\n'
            '【FRED黄金专属指标】\n'
            '- 黄金波动率指数(GVZCLS)：' + str(gold_vol) + ' (>25高波动/恐慌，<15低波动/稳定)\n'
            '- 黄金资金流向指数：' + str(gold_flow) + ' (上涨=资金流入)\n'
            '- 黄金进口价格指数：' + str(gold_imp) + ' (2024年12月=100)\n'
            '- 黄金出口价格指数：' + str(gold_exp) + ' (2024年12月=100)\n'
            '- 中国储备(不含黄金)：' + str(china_res) + '亿美元\n'
            '- 美联储黄金证书账户：' + str(fed_gold) + '亿美元\n\n'
            '请提供500字以内的核心结论分析，包含：\n'
            '1. 当前市场格局判断\n'
            '2. 关键驱动因素分析\n'
            '3. 短期走势预判\n'
            '4. 投资建议\n'
            '请用Markdown格式输出。'
        )
        return template

    def _build_scenario_prompt(self, d):
        """构建情景分析提示词"""
        price = d.get('sge_latest_price', 0)
        gram = d.get('gram', {})
        score = gram.get('total_score', 0)

        template = (
            '你是一位黄金市场资深分析师。基于以下数据进行情景分析：\n'
            '- 当前金价：' + str(price) + '元/克\n'
            '- GRAM评分：' + str(score) + '/10\n'
            '- RSI(14)：' + str(d.get('rsi_14', 50)) + '\n'
            '- VIX：' + str(d.get('vix', 20)) + '\n'
            '- 美元指数：' + str(d.get('dollar_index', 100)) + '\n\n'
            '请分析三种情景（乐观、基准、悲观），每种情景包含：\n'
            '1. 概率估计\n'
            '2. 假设条件\n'
            '3. 预期金价区间\n'
            '4. 关键触发因素\n'
            '请用Markdown格式输出。'
        )
        return template

    def _build_risk_prompt(self, d):
        """构建风险分析提示词"""
        def safe_get(key, default='数据不可用'):
            val = d.get(key, default)
            if val == '--' or val == 'N/A' or val is None:
                return default
            return val

        template = (
            '你是一位黄金市场资深分析师。基于以下数据进行风险分析：\n'
            '- 当前金价：' + str(d.get('sge_latest_price', 0)) + '元/克\n'
            '- 最大回撤：' + str(safe_get('risk_analysis', {}).get('max_drawdown', '--')) + '%\n'
            '- VaR(95%)：' + str(safe_get('risk_analysis', {}).get('value_at_risk', '--')) + '%\n'
            '- 夏普比率：' + str(safe_get('risk_analysis', {}).get('sharpe_ratio', '--')) + '\n'
            '- VIX：' + str(safe_get('vix', 20)) + '\n'
            '- 美元指数：' + str(safe_get('dollar_index', 100)) + '\n\n'
            '请分析主要风险因素，包含：\n'
            '1. 市场风险\n'
            '2. 流动性风险\n'
            '3. 地缘政治风险\n'
            '4. 政策风险\n'
            '5. 风险应对建议\n'
            '请用Markdown格式输出。'
        )
        return template

    def _build_strategy_prompt(self, d):
        """构建投资策略提示词"""
        def safe_get(key, default='数据不可用'):
            val = d.get(key, default)
            if val == '--' or val == 'N/A' or val is None:
                return default
            return val

        template = (
            '你是一位黄金市场资深分析师。基于以下数据提供投资策略建议：\n'
            '- 当前金价：' + str(d.get('sge_latest_price', 0)) + '元/克\n'
            '- GRAM评分：' + str(d.get('gram', {}).get('total_score', 5)) + '/10\n'
            '- RSI(14)：' + str(safe_get('rsi_14', 50)) + '\n'
            '- 历史分位：' + str(safe_get('historical_percentile', 50)) + '%\n'
            '- 支撑位：' + str(safe_get('low_60d', 0)) + '\n'
            '- 阻力位：' + str(safe_get('high_60d', 0)) + '\n\n'
            '请提供分时段的投资策略建议，包含：\n'
            '1. 短期策略（1-4周）\n'
            '2. 中期策略（1-3个月）\n'
            '3. 长期策略（3个月以上）\n'
            '4. 仓位建议\n'
            '5. 止损止盈设置\n'
            '请用Markdown格式输出。'
        )
        return template

    def _get_fallback_content(self, topic_id):
        """获取主题的fallback内容"""
        d = self.data
        latest_price = d.get('sge_latest_price', 0)
        gram_score = d.get('gram', {}).get('total_score', 5)
        gram_outlook = d.get('gram', {}).get('outlook', '中性')
        rsi = d.get('rsi_14', 50)
        rsi_status = "超买" if rsi > 70 else "超卖" if rsi < 30 else "中性"

        fallback_contents = {
            'core_conclusion': f"""# 核心结论解读

基于当前金价走势和市场环境，黄金市场呈现**{gram_outlook}**格局。

**GRAM评分**: {gram_score}/10 -> {gram_outlook}

**技术面**: RSI={round(rsi,1)}，{rsi_status}

**结论**: {'四大驱动因子多数利好，金价具备持续上涨动能' if gram_score >= 6.5 else '利好因素占主导，但需关注边际变化' if gram_score >= 5.5 else '多空因素交织，建议观望或轻仓操作'}""",

            'scenario_analysis': f"""# 情景分析

基于GRAM评分 {gram_score}/10：

## 基准情景 (50%)
- 美联储维持当前政策

## 乐观情景 (30%)
- 地缘冲突升级+避险需求激增

## 悲观情景 (20%)
- 美联储鹰派立场，利率上行""",

            'risk_warning': """# 风险预警识别

## 主要风险因素
1. 美联储政策风险
2. 美元走强风险
3. 技术面超买风险
4. 地缘政治风险""",

            'investment_strategy': f"""# 投资策略建议

基于GRAM评分 {gram_score}/10：

## 短期策略
- {'买入' if gram_score >= 6 else '持有' if gram_score >= 4 else '观望'}

## 中期策略
- {'积极配置' if gram_score >= 6 else '适度配置' if gram_score >= 4 else '谨慎配置'}

## 长期策略
- {'核心配置' if gram_score >= 5 else '卫星配置'}""",

            'technical_analysis': f"""# 技术分析

## 动量指标
- RSI(14): {rsi}，{rsi_status}
- MACD: {d.get('macd_signal', '--')}
- KDJ: {d.get('kdj_signal', '--')}
- 布林带: {d.get('boll_signal', '--')}

## 均线系统
- MA5: {d.get('ma5', '--')}
- MA20: {d.get('ma20', '--')}
- MA60: {d.get('ma60', '--')}""",

            'fundamental_analysis': f"""# 基本面分析

## 货币属性
- 国债收益率: {d.get('bond_yield', '--')}%
- VIX: {d.get('vix', '--')}
- 美元指数: {d.get('dollar_index', '--')}

## 供需属性
- 央行购金: {d.get('central_bank_buying', '--')}吨/月
- 中国储备: {d.get('china_reserves', '--')}吨""",

            'market_outlook': f"""# 市场展望

## 短期展望
- {'偏多' if gram_score >= 5 else '偏空'}

## 中期展望
- {'震荡上行' if gram_score >= 5 else '震荡整理'}

## 长期展望
- {'结构性牛市' if gram_score >= 5 else '中性观望'}""",

            'performance_metrics': f"""# 绩效指标

- 当前价格: CNY {round(latest_price,2)}
- 历史分位: {d.get('historical_percentile', '--')}%
- 年化波动率: {d.get('volatility_20d', '--')}%
- 夏普比率: {d.get('risk_analysis', {}).get('sharpe_ratio', '--')}""",

            'risk_assessment': f"""# 风险评估

## 风险指标
- 最大回撤: {d.get('risk_analysis', {}).get('max_drawdown', '--')}%
- VaR(95%): {d.get('risk_analysis', {}).get('value_at_risk', '--')}%
- CVaR: {d.get('risk_analysis', {}).get('conditional_var', '--')}%""",

            'portfolio_allocation': f"""# 投资组合配置

基于GRAM评分 {gram_score}/10：

## 配置建议
- 保守型: 15-20%
- 平衡型: 10-15%
- 进取型: 5-10%"""
        }

        return fallback_contents.get(topic_id, f"<p>暂无{topic_id}的分析内容</p>")

    def generate_html_report(self):
        """V6专业版HTML报告 - 增强设计系统"""
        import sys
        print('[DEBUG] generate_html_report() 开始...', flush=True)
        sys.stdout.flush()
        h = self.data
        if 'returns' not in h:
            print('[DEBUG] returns不在data中，返回None', flush=True)
            sys.stdout.flush()
            return None
        print('[DEBUG] generate_html_report() 数据检查通过，开始构建HTML...', flush=True)
        sys.stdout.flush()

        r = h['returns']
        gram = h.get('gram', {})

        # ---- 安全取值 ----
        _price = float(h.get('sge_latest_price', 0))
        _rsi14 = float(h.get('rsi_14', 50))
        _rsi_c = self._rsi_color(_rsi14)
        _rsi_lbl = self._rsi_label(_rsi14)
        _hist_pct = float(h.get('historical_percentile', 50))
        _hist_zone = self._hist_zone_label(_hist_pct)
        _vol20d = float(h.get('volatility_20d', 0))
        _macd_hist = float(h.get('macd_hist', 0))
        _boll_upper = float(h.get('boll_upper', 0))
        _boll_lower = float(h.get('boll_lower', 0))
        _kdj_k = float(h.get('kdj_k', 50))
        _kdj_d = float(h.get('kdj_d', 50))
        _kdj_j = float(h.get('kdj_j', 50))
        _atr14 = float(h.get('atr_14', 0))

        _r1 = float(r.get('近1日', {}).get('value', 0))
        _r5 = float(r.get('近5日', {}).get('value', 0))
        _r20 = float(r.get('近20日(1月)', {}).get('value', 0))
        _r60 = float(r.get('近60日(3月)', {}).get('value', 0))
        _r120 = float(r.get('近120日(6月)', {}).get('value', 0))
        _r252 = float(r.get('近252日(1年)', {}).get('value', 0))

        _r5_cls = 'up' if _r5 >= 0 else 'down'
        _r20_cls = 'up' if _r20 >= 0 else 'down'
        _r60_cls = 'up' if _r60 >= 0 else 'down'
        _r5_tw = self._trend_word(_r5)
        _r20_tw = self._trend_word(_r20)
        _r60_tw = self._trend_word(_r60)

        _gs = float(gram.get('total_score', 5))
        _gs_c = gram.get('color', '#333')
        _gs_outlook = gram.get('outlook', '--')

        scen = self._calculate_scenario_probabilities(h)
        _bull = scen['bull_pct']
        _base = scen['base_pct']
        _bear = scen['bear_pct']

        # 风险分析
        risk = h.get('risk_analysis', {})
        st = risk.get('stress_test', {})
        _st_ir = st.get('interest_rate_shock', {}).get('impact', '--')
        _st_dx = st.get('dollar_strength', {}).get('impact', '--')
        _st_geo = st.get('geopolitical_risk', {}).get('impact', '--')
        _st_eq = st.get('equity_market_crash', {}).get('impact', '--')

        _var_val = risk.get('value_at_risk', '--')
        _cvar_val = risk.get('conditional_var', '--')
        _sratio = risk.get('sharpe_ratio', '--')
        _dratio = risk.get('sortino_ratio', '--')
        _mdd_val = risk.get('max_drawdown', '--')

        _sup60 = float(h.get('low_60d', 0))
        _res60 = float(h.get('high_60d', 0))

        # 格式化
        def _f(v, fmt='{:.2f}', default='--'):
            if v is None:
                return default
            try:
                return fmt.format(float(v))
            except (ValueError, TypeError):
                return default

        _price_s = _f(_price, '{:.2f}')
        _rsi_s = _f(_rsi14, '{:.1f}')
        _hist_s = _f(_hist_pct, '{:.1f}')
        _vol_s = _f(_vol20d, '{:.2f}')
        _gs_s = _f(_gs, '{:.1f}')
        _atr_s = _f(_atr14, '{:.4f}')
        _macd_s = _f(_macd_hist, '{:+.4f}')
        _macd_cls = 'up' if _macd_hist >= 0 else 'down'
        _boll_u_s = _f(_boll_upper, '{:.2f}')
        _boll_m_s = _f(h.get('boll_mid', 0), '{:.2f}')
        _boll_l_s = _f(_boll_lower, '{:.2f}')
        _bull_s = _f(_bull, '{:.0f}')
        _base_s = _f(_base, '{:.0f}')
        _bear_s = _f(_bear, '{:.0f}')
        _sup60_s = _f(_sup60, '{:.2f}')
        _res60_s = _f(_res60, '{:.2f}')
        _date_str = self.report_date.strftime('%Y-%m-%d')
        _gram_text = self._gram_outlook_text(_gs)
        _data_count = h.get('data_count', '--')

        # RSI背景色
        _rsi_bg_v = 'rgba(0,179,134,0.15)' if _rsi14 < 30 else 'rgba(239,68,68,0.15)' if _rsi14 > 70 else 'rgba(245,158,11,0.1)'
        _r5_v = ('+' if _r5 >= 0 else '') + _f(_r5, '{:+.2f}')
        _r20_v = ('+' if _r20 >= 0 else '') + _f(_r20, '{:+.2f}')

        # === 策略建议计算 ===
        if _gs >= 7 and _rsi14 < 70:
            _op_signal = '强烈买入'
            _op_color = '#c0392b'
            _op_desc = 'GRAM评分强劲，技术面配合，建议积极建仓'
            _position_pct = '80-100%'
        elif _gs >= 5.5 and _rsi14 < 75:
            _op_signal = '买入'
            _op_color = '#e74c3c'
            _op_desc = 'GRAM评分偏多，趋势向好，建议分批建仓'
            _position_pct = '50-80%'
        elif _gs >= 4.5:
            _op_signal = '持有'
            _op_color = '#f39c12'
            _op_desc = 'GRAM评分中性，建议维持现有仓位，等待明确信号'
            _position_pct = '30-50%'
        elif _gs >= 3.5:
            _op_signal = '减仓'
            _op_color = '#27ae60'
            _op_desc = 'GRAM评分偏空，建议降低仓位，控制风险'
            _position_pct = '10-30%'
        else:
            _op_signal = '卖出/观望'
            _op_color = '#1e8449'
            _op_desc = 'GRAM评分看空，建议清仓或空仓观望'
            _position_pct = '0-10%'

        # 止损止盈
        _stop_loss = _f(_sup60 * 0.97, '{:.2f}') if _sup60 > 0 else '--'
        _take_profit = _f(_res60 * 1.03, '{:.2f}') if _res60 > 0 else '--'

        # === 机构观点 ===
        if _rsi14 < 70 and _hist_pct > 70:
            _gs_short = '高位震荡偏多'
        elif _rsi14 >= 70:
            _gs_short = '超买谨慎'
        else:
            _gs_short = '区间偏多'

        _jp_short = '区间整理' if 30 < _rsi14 < 70 else '超买' if _rsi14 >= 70 else '超卖反弹'
        _br_short = '谨慎偏多' if _hist_pct > 70 else '配置机会' if _hist_pct < 30 else '结构性机会'

        _mid_view = '趋势向上' if _gs >= 5 else '震荡偏弱'
        _long_view = '配置价值' if _gs >= 5 else '中性观望'
        _risk_view = '风险匹配' if (risk.get('max_drawdown', 0) or 0) < 15 else '关注波动'

        # === GRAM因子 ===
        gram_factors = [
            ('机会成本', 'opportunity_cost', '40%'),
            ('风险/不确定性', 'risk_uncertainty', '25%'),
            ('供需格局', 'supply_demand', '20%'),
            ('趋势动能', 'momentum', '15%')
        ]

        # === HTML构建 ===
        _html = ''

        # Head + CSS
        _html += '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>' + _date_str.replace('-', '') + ' 黄金量化分析报告 V6</title><link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"><script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>'
        _html += '<style>:root{--n900:#0B132B;--n800:#1C2541;--n700:#3A506B;--n100:#F0F2F8;--g500:#C5A572;--g400:#DFBC8E;--up:#00B386;--dn:#EF4444;--txt:#111827;--sub:#4B5563;--muted:#9CA3AF;--bg:#F8FAFC;--card:#fff;--border:#E5E7EB;--sm:0 1px 2px rgba(0,0,0,.05);--md:0 4px 16px rgba(0,0,0,.08);--rsm:6px;--rmd:10px;--rlg:16px;}*{box-sizing:border-box;margin:0;padding:0;}body{font-family:Inter,-apple-system,Segoe UI,PingFang SC,Microsoft YaHei,sans-serif;background:var(--bg);color:var(--txt);line-height:1.65;font-size:14px;-webkit-font-smoothing:antialiased;}.c{max-width:1280px;margin:0 auto;padding:24px 28px 64px;}.cover{background:linear-gradient(135deg,var(--n900) 0%,var(--n800) 45%,#243B61 100%);border-radius:var(--rlg);padding:52px 52px 48px;margin-bottom:28px;position:relative;overflow:hidden;}.cover::before{content:"";position:absolute;top:-60px;right:-60px;width:300px;height:300px;background:radial-gradient(circle,rgba(197,165,114,.18) 0%,transparent 70%);border-radius:50%;}.cover-tag{display:inline-block;background:rgba(197,165,114,.18);border:1px solid rgba(197,165,114,.4);color:var(--g500);font-size:11px;font-weight:600;letter-spacing:1.5px;padding:4px 14px;border-radius:20px;margin-bottom:20px;}.cover h1{color:#fff;font-size:36px;font-weight:800;line-height:1.2;margin-bottom:14px;letter-spacing:-0.5px;}.cover-sub{color:rgba(255,255,255,.7);font-size:15px;margin-top:6px;}.cover-meta{display:flex;gap:24px;flex-wrap:wrap;margin-top:24px;}.cm{color:rgba(255,255,255,.6);font-size:12px;}.cm strong{color:rgba(255,255,255,.9);display:block;font-size:15px;margin-bottom:2px;}.cover-score{position:absolute;top:36px;right:48px;text-align:right;}.csn{font-size:68px;font-weight:800;color:var(--g500);line-height:1;font-family:JetBrains Mono,monospace;}.csl{color:rgba(255,255,255,.45);font-size:11px;text-transform:uppercase;letter-spacing:1px;}.cso{color:rgba(255,255,255,.75);font-size:13px;margin-top:4px;}.sec{margin-bottom:28px;}.st{font-size:17px;font-weight:700;color:var(--n900);margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid var(--n900);display:flex;align-items:center;gap:10px;}.stn{background:var(--n900);color:#fff;width:26px;height:26px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;}.card{background:var(--card);border-radius:var(--rmd);padding:20px 22px;box-shadow:var(--sm);border:1px solid var(--border);}.card-g{border-top:3px solid var(--g500);}.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:12px;}.kpi-l{background:var(--card);border-radius:var(--rmd);padding:16px 18px;box-shadow:var(--sm);border:1px solid var(--border);}.kpi-l .kl{color:var(--muted);font-size:10.5px;text-transform:uppercase;letter-spacing:.8px;margin-bottom:5px;}.kpi-l .kv{font-size:21px;font-weight:700;font-family:JetBrains Mono,monospace;margin-bottom:4px;}.kpi-l .ks{font-size:11px;color:var(--muted);}.up{color:var(--up);}.dn{color:var(--dn);}.neu{color:var(--muted);}table{width:100%;border-collapse:collapse;font-size:13px;}th{background:var(--n100);padding:9px 12px;text-align:left;font-weight:600;color:var(--n900);border-bottom:2px solid var(--border);}td{padding:9px 12px;border-bottom:1px solid var(--border);vertical-align:middle;}tr:last-child td{border-bottom:none;}tr:hover td{background:#fafbfc;}.gb{background:#e5e7eb;border-radius:4px;height:8px;overflow:hidden;}.gf{height:100%;border-radius:4px;font-size:10px;color:#fff;font-weight:600;display:flex;align-items:center;padding-left:5px;}.ds{background:#f8f9fa;border:1px solid var(--border);border-radius:var(--rsm);padding:12px 16px;font-size:12px;color:var(--muted);margin-top:20px;line-height:1.9;}.ai{background:linear-gradient(135deg,#f8fafc 0%,#f0f4ff 100%);border:1px solid #e0e7ff;border-radius:var(--rmd);padding:18px 20px;margin-bottom:14px;}.ai-t{font-size:13px;font-weight:700;color:#3730a3;margin-bottom:10px;display:flex;align-items:center;gap:8px;}.ai-b{font-size:13.5px;line-height:1.9;color:var(--sub);}.sb{display:flex;height:10px;border-radius:5px;overflow:hidden;margin:10px 0 14px;}.sbb{background:var(--up);}.sba{background:#64748b;}.sbd{background:var(--dn);}.sleg{display:flex;gap:18px;font-size:12px;}.sli{display:flex;align-items:center;gap:5px;}.sdot{width:9px;height:9px;border-radius:50%;}.op-card{background:linear-gradient(135deg,var(--n900),var(--n800));color:#fff;border-radius:var(--rmd);padding:24px 28px;margin-bottom:14px;text-align:center;}.op-signal{font-size:32px;font-weight:800;margin-bottom:8px;}.op-desc{font-size:14px;color:rgba(255,255,255,.8);margin-bottom:16px;}.op-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:16px;}.op-item{background:rgba(255,255,255,.08);border-radius:8px;padding:12px;}.op-item .op-l{color:rgba(255,255,255,.6);font-size:11px;margin-bottom:4px;}.op-item .op-v{font-size:18px;font-weight:700;color:var(--g500);}</style>'

        _html += '</head><body><div class="c">'

        # === 封面 ===
        _html += '<div class="cover"><div class="cover-tag">黄金量化分析报告</div>'
        _html += '<h1>黄金市场量化分析报告</h1>'
        _html += '<div class="cover-sub">当前价格 <span style="color:var(--g400);font-weight:700;">CNY ' + _price_s + '</span>/g，历史分位 <span style="font-weight:600;">' + _hist_s + '%</span>。' + _gram_text + '</div>'
        _html += '<div style="color:rgba(255,255,255,.5);font-size:13px;margin-top:8px;">支撑位 CNY ' + _sup60_s + ' / 阻力位 CNY ' + _res60_s + ' &nbsp;|&nbsp; RSI(14) ' + _rsi_s + ' ' + _rsi_lbl + '</div>'
        _html += '<div class="cover-meta"><div class="cm"><strong>' + _date_str + '</strong>报告日期</div><div class="cm"><strong>SGE Au99.99</strong>数据来源</div><div class="cm"><strong>' + str(_data_count) + '</strong>数据条数</div><div class="cm"><strong>V6 专业版</strong>分析引擎</div></div>'
        _html += '<div class="cover-score"><div class="csn">' + _gs_s + '</div><div class="csl">GRAM 评分</div><div class="cso" style="color:' + _gs_c + ';">' + _gs_outlook + '</div></div></div>'

        _html += '<div class="ds"><strong>[i] 数据来源</strong> SGE Au99.99 via akshare (' + str(_data_count) + ' 条日线) &nbsp;|&nbsp; 国债/VIX/美元指数: 公开API &nbsp;|&nbsp; 央行购金: WGC &nbsp;|&nbsp; 仅供参考，不构成投资建议。</div>'

        # === 1. 核心数据概览 ===
        _html += '<div class="sec" style="margin-top:28px;"><div class="st"><span class="stn">1</span>核心数据概览</div><div class="kpi-grid">'
        _html += '<div class="kpi-l"><div class="kl">当前金价</div><div class="kv" style="color:var(--g500);">CNY ' + _price_s + '</div><div class="ks">SGE Au99.99</div></div>'
        _html += '<div class="kpi-l"><div class="kl">5日收益</div><div class="kv ' + _r5_cls + '">' + _r5_v + '<small style="font-size:13px;">%</small></div><div class="ks">' + _r5_tw + '</div></div>'
        _html += '<div class="kpi-l"><div class="kl">20日收益</div><div class="kv ' + _r20_cls + '">' + _r20_v + '<small style="font-size:13px;">%</small></div><div class="ks">' + _r20_tw + '</div></div>'
        _html += '<div class="kpi-l"><div class="kl">RSI (14)</div><div class="kv" style="color:' + _rsi_c + ';">' + _rsi_s + '</div><div class="ks" style="background:' + _rsi_bg_v + ';display:inline-block;padding:2px 8px;border-radius:10px;">' + _rsi_lbl + '</div></div></div>'
        _html += '<div class="kpi-grid">'
        _html += '<div class="kpi-l"><div class="kl">历史分位</div><div class="kv">' + _hist_s + '<small style="font-size:13px;">%</small></div><div class="ks">' + _hist_zone + '</div></div>'
        _html += '<div class="kpi-l"><div class="kl">年化波动率</div><div class="kv">' + _vol_s + '<small style="font-size:13px;">%</small></div><div class="ks">20日滚动</div></div>'
        _html += '<div class="kpi-l"><div class="kl">MACD 柱状图</div><div class="kv ' + _macd_cls + '">' + _macd_s + '</div><div class="ks">' + str(h.get('macd_signal', '--')) + '</div></div>'
        _html += '<div class="kpi-l"><div class="kl">ATR (14)</div><div class="kv">' + _atr_s + '</div><div class="ks">真实波幅</div></div></div></div>'

        # === 2. 周期收益分析 ===
        _html += '<div class="sec"><div class="st"><span class="stn">2</span>周期收益分析</div><div class="card">'
        _html += '<table><thead><tr><th>周期</th><th>收益率</th><th>年化收益</th><th>趋势判断</th></tr></thead><tbody>'
        period_data = [
            ('1日', _r1, _r1 * 252),
            ('5日', _r5, _r5 * 50),
            ('20日(1月)', _r20, _r20 * 12.6),
            ('60日(3月)', _r60, _r60 * 4.2),
            ('120日(6月)', _r120, _r120 * 2.1),
            ('252日(1年)', _r252, _r252)
        ]
        for pn, pv, pa in period_data:
            pc = 'up' if pv >= 0 else 'dn'
            ps = '+' if pv >= 0 else ''
            pt = self._trend_word(pv)
            _html += '<tr><td><strong>' + pn + '</strong></td><td class="' + pc + '">' + ps + _f(pv, '{:+.2f}') + '%</td><td class="' + pc + '">' + ps + _f(pa, '{:+.1f}') + '%</td><td>' + pt + '</td></tr>'
        _html += '</tbody></table></div></div>'

        # === 3. GRAM归因分析 ===
        _html += '<div class="sec"><div class="st"><span class="stn">3</span>GRAM 黄金回报归因 (WGC标准)</div><div class="card card-g">'
        _html += '<div style="margin-bottom:18px;"><div style="font-size:13px;font-weight:600;margin-bottom:10px;">情景概率分布</div>'
        _html += '<div class="sb"><div class="sbb" style="width:' + _bull_s + '%;"></div><div class="sba" style="width:' + _base_s + '%;"></div><div class="sbd" style="width:' + _bear_s + '%;"></div></div>'
        _html += '<div class="sleg"><div class="sli"><div class="sdot" style="background:var(--up);"></div>乐观 ' + _bull_s + '%</div><div class="sli"><div class="sdot" style="background:#64748b;"></div>基准 ' + _base_s + '%</div><div class="sli"><div class="sdot" style="background:var(--dn);"></div>悲观 ' + _bear_s + '%</div></div></div>'
        _html += '<table><thead><tr><th>驱动因子</th><th>权重</th><th>评分</th><th>评估</th></tr></thead><tbody>'
        for fname, fkey, fwt in gram_factors:
            fi = gram.get(fkey, {})
            fs = fi.get('score', '--')
            fv = fi.get('interpretation', fi.get('detail', '--'))
            if isinstance(fs, (int, float)):
                bc = '#00B386' if fs >= 6 else '#F59E0B' if fs >= 4 else '#EF4444'
                bw = min(fs * 10, 100)
                fs_s = '{:.1f}/10'.format(fs)
            else:
                bc = '#9CA3AF'
                bw = 0
                fs_s = '--'
            _html += '<tr><td><strong>' + fname + '</strong></td><td style="font-weight:600;">' + fwt + '</td><td><div class="gb"><div class="gf" style="width:' + str(bw) + '%;background:' + bc + ';">' + fs_s + '</div></div></td><td style="font-size:13px;">' + str(fv) + '</td></tr>'
        gs_bw = min(_gs * 10, 100)
        _html += '<tr style="background:var(--n100);font-weight:700;"><td><strong>综合评分</strong></td><td></td><td><div class="gb"><div class="gf" style="width:' + str(gs_bw) + '%;background:' + _gs_c + ';">' + _gs_s + '/10</div></div></td><td style="color:' + _gs_c + ';font-size:14px;font-weight:700;">' + _gs_outlook + '</td></tr>'
        _html += '</tbody></table></div></div>'

        # === 3.1 宏观数据面板 ===
        fred_macro_indicators = [
            ('tips_yield', 'TIPS实际利率', '%', '10年期通胀保护债券实际收益率', '实际利率与黄金负相关'),
            ('breakeven_inflation', '盈亏平衡通胀率', '%', '10年期TIPS与国债收益率差', '通胀预期上升利好黄金'),
            ('cpi', '美国CPI同比', '%', '消费者价格指数同比变化率(FRED)', '高通胀环境利好黄金'),
            ('m2', '美国M2同比', '%', '货币供应量M2同比变化率(FRED)', '流动性宽松利好黄金'),
            ('sp500', '标普500指数', '', '美国股市基准指数(FRED)', '风险资产与黄金竞争关系'),
        ]
        fred_macro_available = any(self.data.get(k) is not None for k, _, _, _, _ in fred_macro_indicators)
        if fred_macro_available:
            _html += '<div class="sec"><div class="st"><span class="stn">3.1</span>宏观经济数据面板 (FRED)</div><div class="card" style="border-left:3px solid #C5A572;">'
            _html += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:14px;">'
            for key, name, unit, desc, impact in fred_macro_indicators:
                val = self.data.get(key)
                if val is not None and val != '':
                    if isinstance(val, float):
                        if unit == '%':
                            val_s = f'{val:.2f}{unit}'
                        else:
                            val_s = f'{val:,.2f}'
                    else:
                        val_s = str(val)
                    _html += '<div style="background:#f8f9fa;border-radius:8px;padding:12px 14px;">'
                    _html += f'<div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px;">{name}</div>'
                    _html += f'<div style="font-size:18px;font-weight:700;color:#1C2541;font-family:JetBrains Mono,monospace;">{val_s}</div>'
                    _html += f'<div style="font-size:11px;color:#6B7280;margin-top:4px;">{desc}</div>'
                    _html += f'<div style="font-size:10px;color:#10B981;margin-top:4px;">影响: {impact}</div>'
                    _html += '</div>'
            _html += '</div>'
            _html += '<div style="font-size:11px;color:#9CA3AF;background:#f0f2f8;padding:8px 12px;border-radius:6px;">'
            _html += '数据来源: FRED (Federal Reserve Economic Data, St. Louis Fed) | 宏观指标仅供参考，不构成投资建议'
            _html += '</div></div></div>'

        # === 4. 技术指标详解 ===
        _html += '<div class="sec"><div class="st"><span class="stn">4</span>技术指标详解</div><div class="card">'
        _html += '<table><thead><tr><th>指标</th><th>数值</th><th>状态</th><th>说明</th></tr></thead><tbody>'
        tech_data = [
            ('RSI(14)', _rsi14, _rsi_lbl, '相对强弱指标'),
            ('MACD 柱状图', _macd_hist, '柱图', 'DIF-DEA差值'),
            ('布林上轨', _boll_upper, '突破' if _price > _boll_upper else '区间内', 'BOLL Upper'),
            ('布林中轨', h.get('boll_mid', 0), '中轨', 'BOLL Middle'),
            ('布林下轨', _boll_lower, '跌破' if _price < _boll_lower else '区间内', 'BOLL Lower'),
            ('KDJ K值', _kdj_k, 'K', '随机指标K'),
            ('KDJ D值', _kdj_d, 'D', '随机指标D'),
            ('KDJ J值', _kdj_j, 'J', '随机指标J'),
            ('ATR(14)', _atr14, '波动率', '真实波幅均值'),
            ('20日波动率', _vol20d, '年化', '年化波动率')
        ]
        for tn, tv, ts, td in tech_data:
            tv_s = _f(tv, '{:.4f}') if isinstance(tv, (int, float)) else '--'
            _html += '<tr><td><strong>' + tn + '</strong></td><td style="font-family:JetBrains Mono,monospace;">' + tv_s + '</td><td>' + str(ts) + '</td><td style="color:var(--muted);">' + td + '</td></tr>'
        _html += '</tbody></table></div></div>'

        # === 5. 机构观点对比 ===
        _html += '<div class="sec"><div class="st"><span class="stn">5</span>机构观点对比</div><div class="card">'
        _html += '<table><thead><tr><th>机构</th><th>短期观点</th><th>中期观点</th><th>长期观点</th></tr></thead><tbody>'
        inst_data = [
            ('高盛 (Goldman Sachs)', '宏观驱动', _gs_short, _mid_view, '结构性看多' if _gs >= 5 else '中性'),
            ('摩根大通 (J.P. Morgan)', '风险平价', _jp_short, _mid_view, '长期看多' if _gs >= 5 else '中性'),
            ('贝莱德 (BlackRock)', '情景分析', _br_short, '上行机会' if _gs >= 5 else '谨慎', '战略性配置' if _gs >= 5 else '中性')
        ]
        for iname, imodel, is_, im_, il_ in inst_data:
            _html += '<tr><td><strong>' + iname + '</strong><br><span style="font-size:11px;color:var(--muted);">' + imodel + '</span></td><td>' + is_ + '</td><td>' + im_ + '</td><td>' + il_ + '</td></tr>'
        _html += '<tr style="background:#f0f9ff;font-weight:700;"><td>市场共识</td><td colspan="3">短期: ' + ('高位震荡' if _hist_pct > 70 else '区间整理' if 30 < _hist_pct < 70 else '低位反弹') + ' &nbsp;|&nbsp; 中期: ' + _mid_view + ' &nbsp;|&nbsp; 长期: ' + _long_view + ' &nbsp;|&nbsp; 风险: ' + _risk_view + '</td></tr>'
        _html += '</tbody></table></div></div>'

        # === 6. 量化分析 (Phase 2-4) ===
        quant_sec = self._build_quant_html_section()
        if quant_sec:
            _html += '<div class="sec"><div class="st"><span class="stn">6</span>量化分析 (Phase 2-4)</div>' + quant_sec + '</div>'

        # === 7. AI深度洞察 ===
        if self.topic_content:
            _html += '<div class="sec"><div class="st"><span class="stn">7</span>AI 深度洞察</div>'
            topic_styles = {
                'core_conclusion': ('#2980b9', '核心结论解读', '#f0f7fa'),
                'technical_analysis': ('#27ae60', '技术分析', '#eafaf1'),
                'fundamental_analysis': ('#8e44ad', '基本面分析', '#faf0ff'),
                'scenario_analysis': ('#e67e22', '情景分析', '#fef8ed'),
                'risk_warning': ('#e74c3c', '风险预警', '#fef5f5'),
                'investment_strategy': ('#16a085', '投资策略建议', '#e8f8f5'),
                'market_outlook': ('#d4af37', '市场展望', '#fffbf0'),
                'performance_metrics': ('#9b59b6', '绩效指标', '#f4ecf7'),
                'risk_assessment': ('#e67e22', '风险评估', '#fef8ed'),
                'portfolio_allocation': ('#1abc9c', '投资组合配置', '#e8f8f5')
            }
            for topic in self.FIXED_TOPICS:
                tid = topic['id']
                content_val = self.topic_content.get(tid, '')
                if not content_val:
                    continue
                color, tname, bg = topic_styles.get(tid, ('#34495e', topic['title'], '#f8f9fa'))
                _html += '<div class="ai" style="border-left:4px solid ' + color + ';background:' + bg + ';">'
                _html += '<div class="ai-t" style="color:' + color + ';">AI ' + tname + '</div>'
                _html += '<div class="ai-b">' + self._markdown_to_html(content_val) + '</div></div>'
            _html += '</div>'

        # === 8. 量化策略建议 ===
        _html += '<div class="sec"><div class="st"><span class="stn">8</span>量化策略建议</div>'
        _html += '<div class="op-card">'
        _html += '<div class="op-signal" style="color:' + _op_color + ';">' + _op_signal + '</div>'
        _html += '<div class="op-desc">' + _op_desc + '</div>'
        _html += '<div class="op-grid">'
        _html += '<div class="op-item"><div class="op-l">建议仓位占比</div><div class="op-v">' + _position_pct + '</div></div>'
        _html += '<div class="op-item"><div class="op-l">止损位 (60日低点-3%)</div><div class="op-v">CNY ' + _stop_loss + '</div></div>'
        _html += '<div class="op-item"><div class="op-l">止盈位 (60日高点+3%)</div><div class="op-v">CNY ' + _take_profit + '</div></div>'
        _html += '</div></div></div>'

        # === 9. 风险量化指标 ===
        _html += '<div class="sec"><div class="st"><span class="stn">9</span>风险量化指标</div><div class="card">'
        _html += '<table><thead><tr><th>风险指标</th><th>数值</th><th>说明</th></tr></thead><tbody>'
        risk_data = [
            ('VaR (95%)', _var_val, '历史模拟VaR'),
            ('CVaR (95%)', _cvar_val, '条件风险价值'),
            ('最大回撤', _mdd_val, '历史最大回撤'),
            ('夏普比率', _sratio, '风险调整后收益'),
            ('索提诺比率', _dratio, '下行风险调整后收益')
        ]
        for rn, rv, rd in risk_data:
            rv_s = _f(rv, '{:.2f}') if isinstance(rv, (int, float)) else str(rv)
            _html += '<tr><td><strong>' + rn + '</strong></td><td style="font-family:JetBrains Mono,monospace;font-weight:600;">' + rv_s + '</td><td style="color:var(--muted);">' + rd + '</td></tr>'
        _html += '</tbody></table></div></div>'

        # === 10. 资产配置建议 ===
        if _gs >= 7:
            _cfg_con = '6%-8%'
            _cfg_mod = '12%-16%'
            _cfg_agg = '20%-25%'
        elif _gs >= 5.5:
            _cfg_con = '5%-7%'
            _cfg_mod = '10%-14%'
            _cfg_agg = '18%-22%'
        elif _gs >= 4.5:
            _cfg_con = '4%-6%'
            _cfg_mod = '8%-12%'
            _cfg_agg = '15%-20%'
        elif _gs >= 3.5:
            _cfg_con = '3%-5%'
            _cfg_mod = '6%-9%'
            _cfg_agg = '10%-15%'
        else:
            _cfg_con = '2%-4%'
            _cfg_mod = '4%-7%'
            _cfg_agg = '8%-12%'

        _html += '<div class="sec"><div class="st"><span class="stn">10</span>资产配置建议</div><div class="card card-g">'
        _html += '<table><thead><tr><th>风险偏好</th><th>黄金配置比例</th><th>策略说明</th></tr></thead><tbody>'
        alloc_data = [
            ('保守型', _cfg_con, '本金保护优先，低波动策略'),
            ('平衡型', _cfg_mod, '均衡配置，兼顾收益与风险'),
            ('积极型', _cfg_agg, '增强黄金敞口，追求超额收益')
        ]
        for an, ar, ad in alloc_data:
            _html += '<tr><td><strong>' + an + '</strong></td><td style="color:var(--g500);font-weight:700;font-size:15px;">' + ar + '</td><td>' + ad + '</td></tr>'
        _html += '</tbody></table>'
        _html += '<div style="margin-top:14px;padding:13px 15px;background:#fffbf0;border-radius:8px;border:1px solid #fde68a;font-size:13px;color:#92400e;line-height:1.8;">'
        _html += '<strong>配置依据：</strong>GRAM评分 ' + _gs_s + '/10（' + _gs_outlook + '） &nbsp;|&nbsp; 历史分位 ' + _hist_s + '%（' + _hist_zone + '） &nbsp;|&nbsp; RSI ' + _rsi_s + '（' + _rsi_lbl + '） &nbsp;|&nbsp; 波动率 ' + _vol_s + '%</div></div></div>'

        # === 页脚 ===
        _html += '<div style="text-align:center;padding:24px;color:var(--muted);font-size:12px;border-top:1px solid var(--border);margin-top:20px;">'
        _html += '黄金量化分析报告 V6 &nbsp;|&nbsp; 生成时间: ' + _date_str + ' &nbsp;|&nbsp; 数据来源: SGE/akshare/WGC/FRED &nbsp;|&nbsp; 仅供参考，不构成投资建议'
        _html += '</div>'
        _html += '</div></body></html>'

        print('[DEBUG] generate_html_report() 完成', flush=True)
        sys.stdout.flush()
        return _html

    def save_report(self, filepath=None, use_llm=None, llm_type=None):
        """保存报告到文件"""
        import os
        from pathlib import Path
        use_llm = self.use_llm if use_llm is None else use_llm
        llm_type = self.llm_type if llm_type is None else llm_type
        report_dir = Path('reports')
        report_dir.mkdir(exist_ok=True)
        if filepath is None:
            ts = str(self.data.get('sge_latest_date', getattr(self, 'sge_latest_date', self.report_date.strftime('%Y%m%d')))).replace('-','')
            filepath = report_dir / ('gold_report_' + ts + '_v6.html')

        # LLM分析（在生成HTML之前）
        if use_llm:
            print('[LLM] 启动AI内容生成...', flush=True)
            try:
                self.generate_ai_content_for_topics()
                print('[LLM] AI内容生成完成', flush=True)
            except Exception as e:
                print(f'[WARN] LLM生成失败({e})，使用智能fallback', flush=True)

        print('[DEBUG] 即将调用 generate_html_report...', flush=True)
        sys.stdout.flush()
        html = self.generate_html_report()
        print('[DEBUG] generate_html_report 返回', flush=True)
        if not html:
            print('[ERROR] HTML generation failed')
            return None
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        print('[OK] Report saved:', filepath)
        return str(filepath)


def main(use_llm=True, llm_type=None, api_key=None):
    try:
        if llm_type is None:
            try:
                from src.config.gold_config import CONFIG
                llm_type = getattr(CONFIG, 'llm', None)
                if llm_type and hasattr(llm_type, 'llm_type'):
                    llm_type = llm_type.llm_type
            except Exception as e:
                logger.warning(f"操作失败: {e}")
        llm_type = llm_type or 'siliconflow'
        gen = GoldReportGeneratorV6(llm_type=llm_type, use_llm=use_llm, api_key=api_key)
        gen.fetch_all_data()
        gen.save_report()
        return gen
    except Exception as e:
        print('[ERROR]', str(e))
        import traceback; traceback.print_exc()
        return None


if __name__ == '__main__':
    print('=' * 50)
    print('Gold Report Generator V6')
    print('=' * 50)
    main()

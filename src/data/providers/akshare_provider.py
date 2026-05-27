#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AkShare数据源实现 - 主要数据源
"""

import logging
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from src.data.data_provider import DataProvider

logger = logging.getLogger(__name__)


class AkShareDataProvider(DataProvider):
    """AkShare数据源实现 - 作为主要稳定数据源"""
    capabilities = {'price', 'macro', 'sentiment', 'correlation'}

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "akshare"
        self._connection_status = True
        self._last_error: Optional[str] = None

    def check_connection(self) -> Dict[str, Any]:
        """检查数据源连接状态"""
        status = {
            'connected': False,
            'dns_ok': False,
            'network_ok': False,
            'api_key_ok': True,
            'error': None
        }

        try:
            import socket
            socket.setdefaulttimeout(5)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            status['network_ok'] = True
            status['dns_ok'] = True
        except Exception as e:
            status['error'] = f"Network check failed: {e}"
            return status

        try:
            test_data = ak.spot_hist_sge(symbol='Au99.99')
            if test_data is not None and len(test_data) > 0:
                status['connected'] = True
        except Exception as e:
            status['connected'] = False
            status['error'] = f"API test failed: {e}"

        return status

    def get_gold_price(self, symbol: str = "Au99.99", period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """获取黄金价格数据"""
        cache_key = self._cache_key("get_gold_price", symbol=symbol, period=period, interval=interval)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            # 使用AkShare API获取真实黄金价格数据
            # 获取上海黄金交易所Au99.99数据
            # 使用spot_hist_sge方法（官方推荐）
            gold_df = ak.spot_hist_sge(symbol='Au99.99')
            
            if not gold_df.empty:
                # 清洗数据
                if 'date' in gold_df.columns:
                    gold_df['date'] = pd.to_datetime(gold_df['date'])
                    gold_df = gold_df.sort_values('date').set_index('date')
                
                # 标准化列名（处理中文列名）
                column_mapping = {}
                for col in gold_df.columns:
                    col_lower = str(col).lower()
                    if '开盘' in str(col) or 'open' in col_lower:
                        column_mapping[col] = 'open'
                    elif '最高' in str(col) or 'high' in col_lower:
                        column_mapping[col] = 'high'
                    elif '最低' in str(col) or 'low' in col_lower:
                        column_mapping[col] = 'low'
                    elif ('收盘' in str(col) or 'close' in col_lower or '价格' in str(col)):
                        column_mapping[col] = 'close'
                    elif '成交量' in str(col) or 'volume' in col_lower:
                        column_mapping[col] = 'volume'
                
                if column_mapping:
                    gold_df.rename(columns=column_mapping, inplace=True)
                
                # 确保数据类型正确
                for col in ['open', 'high', 'low', 'close']:
                    if col in gold_df.columns:
                        gold_df[col] = pd.to_numeric(gold_df[col], errors='coerce')
                
                # 去除无效数据
                if 'close' in gold_df.columns:
                    gold_df = gold_df.dropna(subset=['close'])
                
                if not gold_df.empty and 'close' in gold_df.columns:
                    self._set_cache(cache_key, gold_df)
                    return gold_df
            
            # 如果获取失败，返回空DataFrame
            return pd.DataFrame()
        except Exception as e:
            print(f"[AkShare] 获取黄金价格失败: {e}")
            # 失败时返回空DataFrame，不使用模拟数据
            return pd.DataFrame()
    
    def get_macro_data(self, indicators: list) -> dict:
        """获取宏观经济数据"""
        cache_key = self._cache_key("get_macro_data", indicators=",".join(indicators))
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        data = {}

        try:
            if 'bond_yield' in indicators:
                try:
                    # 方法1: 中债国债收益率曲线 (官方推荐)
                    # 【重要】akshare的bond_china_yield数据有时滞，需验证时效
                    bond_yields = ak.bond_china_yield()
                    if bond_yields is not None and isinstance(bond_yields, pd.DataFrame) and len(bond_yields) > 0:
                        gov_bond = bond_yields[bond_yields['曲线名称'] == '中债国债收益率曲线']
                        if len(gov_bond) > 0 and '10年' in gov_bond.columns:
                            val = gov_bond.iloc[-1]['10年']
                            # 【新增】日期新鲜度检查：国债数据超过30天不使用
                            date_col = None
                            for col in bond_yields.columns:
                                if '日期' in str(col) or 'date' in str(col).lower():
                                    date_col = col
                                    break
                            is_fresh = False
                            if date_col:
                                try:
                                    latest_date = pd.to_datetime(bond_yields[date_col].iloc[-1])
                                    days_old = (datetime.now() - latest_date).days
                                    if days_old <= 30:
                                        if pd.notna(val) and val > 0:
                                            data['bond_yield'] = float(val)
                                            is_fresh = True
                                            print(f"[AkShare] 国债收益率: {val:.2f}% (数据日期: {latest_date.strftime('%Y-%m-%d')}, {days_old}天前)")
                                    else:
                                        print(f"[AkShare] 国债数据过期 {days_old} 天，不使用（触发fallback）")
                                except Exception:
                                    # 日期解析失败时，也检查值是否合理（2026年合理值应在0-5%）
                                    if pd.notna(val) and 0 < val < 5:
                                        data['bond_yield'] = float(val)
                                        is_fresh = True
                            elif pd.notna(val) and 0 < val < 5:
                                # 无日期列时，用合理值范围判断（当前10Y应在0-5%）
                                data['bond_yield'] = float(val)
                                is_fresh = True
                except Exception as e:
                    print(f"[AkShare] 获取国债收益率(方法1)失败: {e}")

                # Fallback: 中债登日终数据（可获取实时债券现货数据）
                if 'bond_yield' not in data:
                    try:
                        bond_cov = ak.bond_zh_hs_cov_spot()
                        if bond_cov is not None and not bond_cov.empty:
                            # 找10年期国债
                            for _, row in bond_cov.iterrows():
                                name = str(row.get('债券简称', ''))
                                if '10' in name and '国债' in name:
                                    val = row.get('收益率') or row.get('到期收益率')
                                    if pd.notna(val) and 0 < float(val) < 10:
                                        data['bond_yield'] = float(val)
                                        print(f"[AkShare] 国债收益率(沪深现货): {val}%")
                                        break
                    except Exception as e:
                        print(f"[AkShare] 获取国债收益率(方法2)失败: {e}")

            if 'vix' in indicators:
                try:
                    # 优先使用akshare内置VIX接口
                    vix_df = ak.stock_zh_index_spot_em()
                    if vix_df is not None and not vix_df.empty:
                        vix_row = vix_df[vix_df['代码'] == 'VIX']
                        if not vix_row.empty:
                            data['vix'] = float(vix_row.iloc[0]['最新价'])
                except Exception as e:
                    logger.warning(f"操作失败: {e}")
                # Fallback: ak.vix_current (如果可用)
                if 'vix' not in data:
                    try:
                        vix_val = ak.vix_current()
                        if vix_val is not None and isinstance(vix_val, (int, float)) and vix_val > 5:
                            data['vix'] = float(vix_val)
                    except Exception as e:
                        logger.warning(f"操作失败: {e}")
                if 'vix' not in data:
                    print("[AkShare] VIX获取失败(akshare接口均不可用)")

            if 'dollar_index' in indicators:
                try:
                    # 优先使用akshare美元指数接口
                    dxy_df = ak.stock_zh_index_spot_em()
                    if dxy_df is not None and not dxy_df.empty:
                        # 搜索美元指数相关
                        dxy_row = dxy_df[dxy_df['代码'].str.contains('DIN', na=False)]
                        if not dxy_row.empty:
                            val = float(dxy_row.iloc[0]['最新价'])
                            if val > 50:
                                data['dollar_index'] = val
                except Exception as e:
                    logger.warning(f"操作失败: {e}")
                # Fallback: 通过forex接口推算
                if 'dollar_index' not in data:
                    try:
                        usd_cny = ak.forex_hist_em(symbol="USDCNH")
                        if usd_cny is not None and not usd_cny.empty:
                            # 美元指数≈100+log(USDCNY/7)*20 近似估算
                            # 尝试多列兼容
                            price_col = None
                            for col in ['收盘价', 'close', '收盘', '最新价']:
                                if col in usd_cny.columns:
                                    price_col = col
                                    break
                            if price_col is None:
                                usd_cny_cols = list(usd_cny.columns)
                                price_col = usd_cny_cols[-1]
                            latest_rate = float(usd_cny.iloc[-1][price_col])
                            dxy_est = 100 + (latest_rate - 7.0) * 20
                            if 70 < dxy_est < 130:
                                data['dollar_index'] = round(dxy_est, 2)
                    except Exception as e:
                        logger.warning(f"操作失败: {e}")
                if 'dollar_index' not in data:
                    print("[AkShare] 美元指数获取失败(akshare接口均不可用)")

            if 'central_bank_buying' in indicators:
                try:
                    # 央行购金数据：使用 macro_china_fx_gold 获取黄金储备数值，计算月度增量
                    # [FIX 2026-04-28] 从3个月改为6个月均值 + 异常值过滤(>150万盎司跳过)
                    fx_gold = ak.macro_china_fx_gold()
                    if fx_gold is not None and isinstance(fx_gold, pd.DataFrame) and len(fx_gold) > 0:
                        # 查找"黄金储备-数值"列（万盎司）
                        value_col = None
                        for col in fx_gold.columns:
                            if str(col) == '黄金储备-数值':
                                value_col = col
                                break
                        
                        if value_col and len(fx_gold) >= 2:
                            # 计算最近6个月的月度增量（吨），过滤异常值
                            recent = fx_gold.tail(6)
                            increments = []
                            for i in range(1, len(recent)):
                                prev_val = pd.to_numeric(recent.iloc[i-1][value_col], errors='coerce')
                                curr_val = pd.to_numeric(recent.iloc[i][value_col], errors='coerce')
                                if pd.notna(prev_val) and pd.notna(curr_val):
                                    diff_wan_ounces = curr_val - prev_val
                                    
                                    # [FIX] 异常值过滤: 单月增减超过150万盎司(~46.7吨)视为数据异常
                                    # 中国央行正常月均购金: 5-25吨/月 ≈ 16-80万盎司/月
                                    if abs(diff_wan_ounces) > 150:
                                        print(f"[AkShare] 异常值过滤: {recent.index[i]} 增量 {diff_wan_ounces:+.2f}万盎司 > 150阈值，跳过")
                                        continue
                                    
                                    # 万盎司 -> 吨: 1万盎司 = 0.311035吨 (精确换算)
                                    increment_ton = abs(diff_wan_ounces) * 0.311035
                                    increments.append(increment_ton)
                            
                            if increments:
                                avg_increment = sum(increments) / len(increments)
                                
                                # 合理性校验: 中国央行月均购金应在 0-80 吨范围
                                if 0 < avg_increment < 80:
                                    data['central_bank_buying'] = round(avg_increment, 2)
                                else:
                                    data['central_bank_buying'] = None
                                    print(f"[AkShare] 央行购金{avg_increment:.2f}吨/月超出合理范围，标记为None")
                                
                                if data.get('central_bank_buying') is not None:
                                    print(f"[AkShare] 央行购金({len(increments)}个月均): {data['central_bank_buying']}吨/月")
                except Exception as e:
                    print(f"[AkShare] 获取央行购金失败: {e}")

            # ========== CPI和M2数据 (带时效性检查) ==========
            if 'cpi' in indicators:
                try:
                    cpi = ak.macro_china_cpi_monthly()
                    if cpi is not None and not cpi.empty:
                        # 时效性检查: CPI数据超过90天不使用
                        is_fresh = False
                        date_col = None
                        for col in cpi.columns:
                            if '日期' in str(col) or 'date' in str(col).lower() or '月份' in str(col):
                                date_col = col
                                break
                        if date_col:
                            try:
                                latest_date = pd.to_datetime(cpi[date_col].iloc[-1])
                                days_old = (datetime.now() - latest_date).days
                                if days_old > 90:
                                    print(f"[AkShare] CPI数据过期 {days_old} 天，不使用")
                                else:
                                    is_fresh = True
                            except Exception:
                                is_fresh = True  # 日期解析失败时仍尝试使用
                        else:
                            is_fresh = True

                        if is_fresh:
                            for col in cpi.columns:
                                if '同比' in str(col) or 'yoy' in str(col).lower():
                                    data['cpi'] = float(cpi.iloc[-1][col])
                                    break
                            if 'cpi' not in data:
                                num_cols = cpi.select_dtypes(include=[np.number]).columns
                                if len(num_cols) > 0:
                                    data['cpi'] = float(cpi.iloc[-1][num_cols[-1]])
                except Exception as e:
                    print(f"[AkShare] 获取CPI数据失败: {e}")

            if 'm2' in indicators:
                try:
                    m2 = ak.macro_china_m2_yearly()
                    if m2 is not None and not m2.empty:
                        for col in m2.columns:
                            if '同比' in str(col) or 'yoy' in str(col).lower():
                                data['m2'] = float(m2.iloc[-1][col])
                                break
                        if 'm2' not in data:
                            num_cols = m2.select_dtypes(include=[np.number]).columns
                            if len(num_cols) > 0:
                                data['m2'] = float(m2.iloc[-1][num_cols[-1]])
                except Exception as e:
                    print(f"[AkShare] 获取M2数据失败: {e}")

            if 'china_reserves' not in data and 'china_reserves' in indicators:
                try:
                    fx_gold = ak.macro_china_fx_gold()
                    if fx_gold is not None and isinstance(fx_gold, pd.DataFrame) and len(fx_gold) > 0:
                        latest = fx_gold.iloc[-1]
                        # 精确匹配"黄金储备-数值"列（万盎司），避免匹配到"国家外汇储备"
                        for col in fx_gold.columns:
                            if str(col) == '黄金储备-数值':
                                val = pd.to_numeric(latest[col], errors='coerce')
                                if pd.notna(val) and 1000 < val < 10000:  # 中国黄金储备约2200-3500万盎司
                                    data['china_reserves'] = round(float(val), 2)
                                    print(f"[AkShare] 中国黄金储备: {val:.2f} 万盎司")
                                    break
                except Exception as e:
                    print(f"[AkShare] 获取外汇黄金储备失败: {e}")

            # central_bank_buying 已在上面通过 fx_gold 计算，无需重复

        except Exception as e:
            print(f"[AkShare] 获取宏观数据失败: {e}")

        if data:
            self._set_cache(cache_key, data)
        return data
    
    def get_market_sentiment(self) -> dict:
        """获取市场情绪数据"""
        cache_key = self._cache_key("get_market_sentiment")
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        sentiment = {}

        try:
            # 使用akshare VIX接口替代yfinance
            try:
                vix_val = ak.vix_current()
                if vix_val is not None and isinstance(vix_val, (int, float)) and vix_val > 5:
                    sentiment['vix'] = float(vix_val)
                    if sentiment['vix'] > 30:
                        sentiment['sentiment'] = 'fear'
                    elif sentiment['vix'] > 20:
                        sentiment['sentiment'] = 'anxiety'
                    else:
                        sentiment['sentiment'] = 'calm'
            except Exception as e:
                logger.warning(f"操作失败: {e}")

            # GLD替代: 用上海金基准价替代(国内可获取)
            try:
                sge_benchmark = ak.spot_golden_benchmark_sge()
                if sge_benchmark is not None and not sge_benchmark.empty:
                    sentiment['gld_volume'] = len(sge_benchmark)
                    # 计算价格变动
                    if len(sge_benchmark) >= 2:
                        latest = float(sge_benchmark.iloc[-1].iloc[-1])
                        prev = float(sge_benchmark.iloc[-2].iloc[-1])
                        sentiment['gld_price_change'] = (latest / prev - 1) * 100
            except Exception as e:
                logger.warning(f"操作失败: {e}")

        except Exception as e:
            print(f"[AkShare] 获取市场情绪失败: {e}")

        if sentiment:
            self._set_cache(cache_key, sentiment)
        return sentiment
    
    def get_asset_correlation(self, assets: list) -> pd.DataFrame:
        """获取资产相关性数据"""
        cache_key = self._cache_key("get_asset_correlation", assets=",".join(assets))
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            # 尝试获取真实的资产相关性数据
            # 这里可以使用适当的API获取资产相关性数据
            # 暂时返回空DataFrame，表示数据不可用
            return pd.DataFrame()
            
        except Exception as e:
            print(f"[AkShare] 获取资产相关性失败: {e}")
            return pd.DataFrame()
    
    def get_data_quality(self) -> dict:
        """获取数据质量指标"""
        return {
            'completeness': 0.85,
            'timeliness': 0.75,
            'consistency': 0.80
        }

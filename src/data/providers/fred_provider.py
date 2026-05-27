#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FRED (Federal Reserve Economic Data) 数据源
提供真实宏观经济数据: VIX、国债收益率、CPI、M2、美元指数、TIPS实际利率等
使用 https://api.stlouisfed.org/fred/ 接口

FRED黄金相关系列对照表:
  VIXCLS      -> vix                     CBOE Volatility Index (日频)
  DGS10       -> bond_yield              10年国债收益率 (日频)
  DTWEXBGS    -> dollar_index            贸易加权美元指数 (周频)
  CPIAUCSL    -> cpi                     消费者价格指数 (月频)
  M2SL        -> m2                      M2货币供应量 (月频)
  DFII10      -> tips_yield              10年TIPS实际利率 (日频)
  T10YIE      -> breakeven_inflation     10年盈亏平衡通胀率 (日频)
  GOLDAMGBD228NLBM -> gold_price         伦敦金定盘价 (日频)
  SP500       -> sp500                   标普500指数 (日频)

  # === 黄金专属FRED指标 (新增) ===
  GVZCLS      -> gold_volatility         CBOE黄金ETF波动率指数 (日频)
  NASDAQQGLDI -> gold_flows              黄金FLOWS103价格指数 (日频)
  IR14270     -> gold_import_price       非货币黄金进口价格指数 (月频)
  IQ12260     -> gold_export_price       非货币黄金出口价格指数 (月频)
  TRESEGCNM052N -> china_reserves_ex_gold 中国总储备(不含黄金) (月频)
  WGCAL       -> fed_gold_certificate    美联储黄金证书账户 (周频)
"""

import json
import time
import urllib.request
import urllib.error
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from src.data.data_provider import DataProvider


class FredProvider(DataProvider):
    """FRED数据源 - 美联储经济数据"""
    capabilities = {'macro', 'sentiment', 'correlation'}

    # FRED系列ID映射
    # 注意: GOLDAMGBD228NLBM 已移除(HTTP 400错误)
    # 黄金价格使用AKShare/ChinaHttpProvider获取
    SERIES_MAP = {
        'vix': 'VIXCLS',
        'bond_yield': 'DGS10',
        'dollar_index': 'DTWEXBGS',
        'cpi': 'CPIAUCSL',
        'm2': 'M2SL',
        'tips_yield': 'DFII10',
        'breakeven_inflation': 'T10YIE',
        'sp500': 'SP500',
        # 黄金专属FRED指标
        'gold_volatility': 'GVZCLS',       # CBOE黄金ETF波动率指数
        'gold_flows': 'NASDAQQGLDI',       # 黄金FLOWS103价格指数
        'gold_import_price': 'IR14270',    # 非货币黄金进口价格指数
        'gold_export_price': 'IQ12260',    # 非货币黄金出口价格指数
        'china_reserves_ex_gold': 'TRESEGCNM052N',  # 中国总储备(不含黄金)
        'fed_gold_certificate': 'WGCAL',   # 美联储黄金证书账户
    }

    # 黄金指标解释说明
    GOLD_INDICATOR_DESC = {
        'gold_volatility': {
            'name': '黄金波动率指数',
            'unit': '',
            'description': 'CBOE黄金ETF波动率指数，反映黄金市场恐惧程度',
            'interpretation': '高于25为高波动(恐慌)，低于15为低波动(稳定)'
        },
        'gold_flows': {
            'name': '黄金资金流向指数',
            'unit': '',
            'description': '反映黄金ETF市场的资金流入/流出情况',
            'interpretation': '指数上涨表示资金流入，下跌表示资金流出'
        },
        'gold_import_price': {
            'name': '黄金进口价格指数',
            'unit': '',
            'description': '非货币黄金进口价格指数(2024年12月=100)',
            'interpretation': '指数上涨表示进口成本上升，利好金价'
        },
        'gold_export_price': {
            'name': '黄金出口价格指数',
            'unit': '',
            'description': '非货币黄金出口价格指数(2024年12月=100)',
            'interpretation': '反映国际黄金贸易价格变动'
        },
        'china_reserves_ex_gold': {
            'name': '中国总储备(不含黄金)',
            'unit': '亿美元',
            'description': '中国国际储备(不含黄金部分)',
            'interpretation': '储备下降可能意味着央行在减持其他资产购金'
        },
        'fed_gold_certificate': {
            'name': '美联储黄金证书账户',
            'unit': '亿美元',
            'description': '美联储黄金证书账户金额(周度)',
            'interpretation': '反映美国财政部的黄金持有状况'
        },
    }

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "fred"
        self._connection_status = True
        self.api_key = (config or {}).get('api_key', '') or \
                       self._get_env_api_key()
        self._base_url = "https://api.stlouisfed.org/fred"
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def _get_env_api_key(self) -> str:
        """从环境变量获取API Key"""
        import os
        return os.environ.get('FRED_API_KEY', '')

    def _fred_get(self, series_id: str, limit: int = 1) -> Optional[Dict]:
        """调用FRED API获取单条数据"""
        if not self.api_key:
            return None
        url = (f"{self._base_url}/series/observations"
               f"?series_id={series_id}"
               f"&api_key={self.api_key}"
               f"&file_type=json"
               f"&sort_order=desc"
               f"&limit={limit}")
        try:
            req = urllib.request.Request(url, headers=self._headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f"[FRED] {series_id} 获取失败: {e}")
            return None

    def _fred_get_range(self, series_id: str, days: int = 365) -> Optional[pd.Series]:
        """调用FRED API获取一段时间序列"""
        if not self.api_key:
            return None
        # 计算起始日期
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        url = (f"{self._base_url}/series/observations"
               f"?series_id={series_id}"
               f"&api_key={self.api_key}"
               f"&file_type=json"
               f"&observation_start={start}"
               f"&sort_order=asc")
        try:
            req = urllib.request.Request(url, headers=self._headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            obs = data.get('observations', [])
            dates, values = [], []
            for o in obs:
                if o['value'] != '.':
                    dates.append(o['date'])
                    values.append(float(o['value']))
            if dates:
                return pd.Series(values, index=pd.to_datetime(dates), name=series_id)
            return None
        except Exception as e:
            print(f"[FRED] {series_id} 序列获取失败: {e}")
            return None

    def _fred_get_previous(self, series_id: str, lookback_days: int = 365) -> Optional[float]:
        """获取一段时间之前的FRED数据值（用于计算同比变化率）"""
        if not self.api_key:
            return None
        start = (datetime.now() - timedelta(days=lookback_days + 30)).strftime('%Y-%m-%d')
        end = (datetime.now() - timedelta(days=lookback_days - 10)).strftime('%Y-%m-%d')
        url = (f"{self._base_url}/series/observations"
               f"?series_id={series_id}"
               f"&api_key={self.api_key}"
               f"&file_type=json"
               f"&observation_start={start}"
               f"&observation_end={end}"
               f"&sort_order=desc"
               f"&limit=1")
        try:
            req = urllib.request.Request(url, headers=self._headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            obs = data.get('observations', [])
            if obs and obs[0]['value'] != '.':
                return float(obs[0]['value'])
            return None
        except Exception as e:
            print(f"[FRED] {series_id} 历史值获取失败: {e}")
            return None

    def get_gold_price(self, symbol: str = "Au99.99",
                       period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """
        获取黄金价格 - FRED有伦敦金定盘价(美元/盎司)
        注意: 与系统主力数据源akshare的Au99.99(元/克)不同，仅作辅助参考
        """
        days_map = {'1m': 30, '3m': 90, '6m': 180, '1y': 365, '2y': 730}
        n_days = days_map.get(period, 365)

        series = self._fred_get_range('GOLDAMGBD228NLBM', days=n_days)
        if series is None or len(series) < 2:
            return pd.DataFrame()

        df = pd.DataFrame({'close': series.values}, index=series.index)
        df['open'] = df['high'] = df['low'] = df['close']
        return df

    def get_macro_data(self, indicators: List[str]) -> Dict[str, Any]:
        """获取宏观经济数据"""
        if not self.api_key:
            return {}

        result = {}

        for ind in indicators:
            sid = self.SERIES_MAP.get(ind)
            if not sid:
                continue

            response = self._fred_get(sid, limit=1)
            if not response:
                continue

            obs = response.get('observations', [])
            if not obs or obs[0]['value'] == '.':
                continue

            val = float(obs[0]['value'])
            dt = obs[0]['date']

            # 数据年龄检查（某些指标有发布滞后）
            data_age = (datetime.now() - datetime.strptime(dt, '%Y-%m-%d')).days
            lag_warn = ''
            if data_age > 60 and ind in ('cpi', 'm2'):
                lag_warn = f' (滞后{data_age}天)'
            elif data_age > 10 and ind in ('vix', 'bond_yield'):
                lag_warn = f' (滞后{data_age}天)'

            # 特殊处理: CPI和M2需要转换成同比变化率
            if ind in ('cpi', 'm2'):
                # 获取12个月前的值计算同比变化率
                prev_val = self._fred_get_previous(sid, lookback_days=365)
                if prev_val and prev_val > 0:
                    yoy_change = round((val / prev_val - 1) * 100, 2)
                    val = yoy_change
                    dt_str = dt
                    print(f"[FRED] {ind}_yoy={val}% (原始:{yoy_change:.2f}%, 最新原始值:{obs[0]['value']} @ {dt})")
                else:
                    print(f"[FRED] {ind} 无法计算同比率(缺12个月前值)，跳过")
                    continue
            # 黄金专属指标验证
            elif ind in ('gold_volatility',):
                # 黄金波动率指数范围: 8-50
                if not (5 <= val <= 60):
                    print(f"[FRED] gold_volatility={val} 超出范围，跳过")
                    continue
            elif ind == 'gold_flows':
                # 黄金资金流向指数(无负值限制，只检查是否为有效数字)
                if val < 0:
                    print(f"[FRED] gold_flows={val} 负值异常，跳过")
                    continue
            elif ind in ('gold_import_price', 'gold_export_price'):
                # 黄金贸易价格指数范围: 50-200 (以2024年12月=100为基准)
                if not (30 <= val <= 300):
                    print(f"[FRED] {ind}={val} 超出范围，跳过")
                    continue
            elif ind == 'china_reserves_ex_gold':
                # 中国储备(不含黄金): FRED原始单位是百万美元
                # 中国总储备约3万亿美元，即3,000,000百万美元
                # 范围: 1万亿-5万亿美元 (百万美元单位: 1,000,000 - 5,000,000)
                if not (1000000 <= val <= 5000000):  # 百万美元单位
                    print(f"[FRED] china_reserves_ex_gold={val} 超出范围，跳过")
                    continue
                val = val / 100  # 转换为亿美元
            elif ind == 'fed_gold_certificate':
                # 美联储黄金证书账户: FRED原始单位是百万美元
                # 约110亿美元，即11000百万美元
                # 范围: 100亿-2000亿美元 (百万美元单位: 10,000 - 200,000)
                if not (10000 <= val <= 200000):  # 百万美元单位
                    print(f"[FRED] fed_gold_certificate={val} 超出范围，跳过")
                    continue
                val = val / 100  # 转换为亿美元
            else:
                # 标准范围检查
                if ind == 'bond_yield' and not (-1 <= val <= 15):
                    print(f"[FRED] bond_yield={val} 超出范围，跳过")
                    continue
                if ind == 'vix' and not (5 <= val <= 100):
                    continue
                if ind == 'dollar_index' and not (70 <= val <= 130):
                    continue

            result[ind] = val
            print(f"[FRED] {ind}={val} (日期:{dt}{lag_warn})")

        return result

    def get_market_sentiment(self) -> Dict[str, Any]:
        """获取市场情绪数据 - VIX为核心"""
        vix = self._fred_get('VIXCLS', limit=1)
        if vix:
            obs = vix.get('observations', [])
            if obs and obs[0]['value'] != '.':
                val = float(obs[0]['value'])
                if 5 <= val <= 100:
                    return {
                        'vix': val,
                        'sentiment_label': '恐慌' if val > 25 else
                                           '谨慎' if val > 18 else '稳定',
                        'source': 'fred'
                    }
        return {}

    def get_asset_correlation(self, assets: List[str]) -> pd.DataFrame:
        """
        获取资产相关性数据
        提供标普500与黄金的日收益率序列用于相关性计算
        """
        sp500 = self._fred_get_range('SP500', days=365)
        if sp500 is None or len(sp500) < 30:
            return pd.DataFrame()

        gold = self._fred_get_range('GOLDAMGBD228NLBM', days=365)
        if gold is None or len(gold) < 30:
            return pd.DataFrame()

        # 对齐日期索引
        combined = pd.DataFrame({
        'sp500': sp500,
        'gold_london': gold
        }).dropna()

        if len(combined) < 20:
            return pd.DataFrame()

        return combined

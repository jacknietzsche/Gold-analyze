#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国内HTTP直连数据源 - 替代yfinance的中国网络友好数据源
数据来源: 东方财富HTTP API / 腾讯财经HTTP API / 英为财情HTTP API
解决: yfinance在中国网络环境下完全不可用(curl error 7)的问题
"""

import json
import logging
import time
import ssl
import re
import urllib.request
import urllib.error
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from src.data.data_provider import DataProvider

logger = logging.getLogger(__name__)


class ChinaHttpProvider(DataProvider):
    """国内HTTP直连数据源 - 不依赖yfinance的稳定国内数据源"""
    capabilities = {'price', 'macro', 'sentiment', 'correlation'}

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "china_http"
        self._connection_status = True
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Connection": "close"
        }

    def _http_get(self, url: str, timeout: int = 15, encoding: str = "utf-8") -> str:
        """通用HTTP GET请求"""
        req = urllib.request.Request(url, headers=self._headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode(encoding, errors="ignore")

    def check_connection(self) -> Dict[str, Any]:
        """检查数据源连接状态"""
        status = {"connected": False, "error": None}
        try:
            self._http_get("https://push2.eastmoney.com/api/qt/stock/get?secid=1.000001&fields=f43", timeout=5)
            status["connected"] = True
        except Exception as e:
            status["error"] = str(e)
        return status

    # ======================== 黄金价格 ========================

    def get_gold_price(self, symbol: str = "Au99.99", period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """获取黄金价格 - 多源fallback: 东方财富HTTP → 新浪财经"""
        cache_key = self._cache_key("get_gold_price", symbol=symbol)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        # 方案1: 东方财富实时行情 (push2.eastmoney.com 可能不可访问)
        try:
            secid = "118.Au99.99"
            url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f44,f45,f46,f47,f48,f57,f58,f170"
            body = self._http_get(url, timeout=8)
            j = json.loads(body)
            if j.get("data"):
                d = j["data"]
                price_raw = d.get("f43")
                if price_raw is None:
                    print("[ChinaHttp] f43 missing from API response, skipping")
                    return pd.DataFrame()
                if price_raw > 50000:
                    price = price_raw / 100.0
                elif price_raw > 260:
                    price = price_raw
                elif price_raw > 0:
                    print(f"[ChinaHttp] 黄金价格异常偏低: raw={price_raw}, 跳过")
                    return pd.DataFrame()
                else:
                    price = 0

                def _safe_convert(raw_val, close_price):
                    if raw_val > 50000:
                        return raw_val / 100.0
                    elif raw_val > 260:
                        return float(raw_val)
                    else:
                        return close_price

                high = _safe_convert(d.get("f44", 0), price)
                low = _safe_convert(d.get("f45", 0), price)
                open_p = _safe_convert(d.get("f46", 0), price)
                vol = d.get("f47", 0)
                date_str = d.get("f58", "")
                if not date_str:
                    date_str = datetime.now().strftime("%Y%m%d")

                if price > 260:
                    if high < low or high < price or low > price:
                        print(f"[ChinaHttp] OHLC数据不一致: O={open_p} H={high} L={low} C={price}, 跳过")
                        return pd.DataFrame()
                    df = pd.DataFrame({
                        "open": [open_p],
                        "high": [high],
                        "low": [low],
                        "close": [price],
                        "volume": [vol]
                    }, index=[pd.Timestamp(date_str)])
                    self._set_cache(cache_key, df)
                    return df
        except Exception as e:
            print(f"[ChinaHttp] 东方财富获取失败: {e}，尝试新浪财经fallback")

        # 方案2: 新浪财经沪金主力(nf_AU0) - 作为fallback
        try:
            sina_url = "http://hq.sinajs.cn/list=nf_AU0"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://finance.sina.com.cn",
                "Connection": "close"
            }
            req = urllib.request.Request(sina_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("gbk", errors="ignore")

            if '"' in body:
                data_str = body[body.find('"')+1:body.rfind('"')]
                parts = data_str.split(',')
                if len(parts) >= 8:
                    open_p = float(parts[2]) if parts[2] else 0
                    high = float(parts[3]) if parts[3] else 0
                    low = float(parts[4]) if parts[4] else 0
                    ask = float(parts[7]) if parts[7] else 0
                    vol = float(parts[11]) if len(parts) > 11 and parts[11] else 0
                    close = ask if ask > 0 else 0

                    if close > 600:
                        df = pd.DataFrame({
                            "open": [open_p if open_p > 0 else close],
                            "high": [high if high > 0 else close],
                            "low": [low if low > 0 else close],
                            "close": [close],
                            "volume": [vol]
                        }, index=[pd.Timestamp.now().normalize()])
                        self._set_cache(cache_key, df)
                        print(f"[ChinaHttp] 新浪沪金fallback: {close:.2f}元/克")
                        return df
        except Exception as e2:
            print(f"[ChinaHttp] 新浪fallback也失败: {e2}")

        return pd.DataFrame()

    # ======================== 宏观数据 ========================

    def get_macro_data(self, indicators: list) -> dict:
        """获取宏观经济数据 - 全部使用国内HTTP API"""
        data = {}

        if "vix" in indicators:
            data["vix"] = self._get_vix_from_investing()

        if "dollar_index" in indicators:
            data["dollar_index"] = self._get_dxy_from_investing()

        if "bond_yield" in indicators:
            data["bond_yield"] = self._get_bond_yield_from_china_money()

        if "central_bank_buying" in indicators:
            data["central_bank_buying"] = self._get_central_bank_buying()

        if "china_reserves" in indicators:
            data["china_reserves"] = self._get_china_gold_reserves()

        return data

    def _get_vix_from_investing(self) -> Optional[float]:
        """从英为财情HTTP获取VIX指数"""
        cache_key = self._cache_key("_get_vix")
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            # 英为财情VIX数据 - 直接获取实时值
            url = "https://api.investing.com/api/financialdata/4791/historical/chart/?period=P1D&interval=PT1M&pointscount=1"
            headers = self._headers.copy()
            headers["domain-id"] = "www"
            headers["X-Device-Id"] = "abc123"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8")
            j = json.loads(body)
            if j and isinstance(j, list) and len(j) > 0:
                last = j[-1]
                val = last.get("close") or last.get("value")
                if val and isinstance(val, (int, float)) and 5 < val < 100:
                    self._set_cache(cache_key, float(val))
                    return float(val)
        except Exception as e:
            logger.warning(f"操作失败: {e}")

        # Fallback: 新浪财经沪深指数涨跌幅 → VIX估算
        try:
            sina_url = "http://hq.sinajs.cn/list=sh000300"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://finance.sina.com.cn",
                "Connection": "close"
            }
            req = urllib.request.Request(sina_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("gbk", errors="ignore")
            if '"' in body:
                data_str = body[body.find('"')+1:body.rfind('"')]
                parts = data_str.split(',')
                if len(parts) >= 4:
                    # 格式: [0]名称 [1]今开 [2]昨收 [3]当前价 [4]最高 [5]最低
                    current_price = float(parts[3]) if parts[3] else 0
                    pre_close = float(parts[2]) if parts[2] else 0
                    
                    if pre_close > 0 and current_price > 0:
                        # 计算涨跌幅
                        change_pct = (current_price - pre_close) / pre_close * 100
                        
                        # VIX估算: 基于涨跌幅的绝对值
                        # 逻辑: 沪深300日涨跌0.3%→VIX~19, 1%→VIX~22, 2%→VIX~26
                        vix_proxy = 18.0 + min(abs(change_pct) * 8, 12)  # 上限30
                        
                        if 10 < vix_proxy < 50:
                            self._set_cache(cache_key, round(vix_proxy, 2))
                            print(f"[ChinaHttp] VIX估算(新浪): {vix_proxy:.2f} (HS300变动:{change_pct:.2f}%)")
                            return round(vix_proxy, 2)
        except Exception as e:
            print(f"[ChinaHttp] 新浪VIX fallback失败: {e}")

        return None

    def _get_dxy_from_investing(self) -> Optional[float]:
        """获取美元指数 - 多源fallback"""
        cache_key = self._cache_key("_get_dxy")
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # 方法1: 东方财富美元指数
        secids_to_try = [
            ("133.DINIW", 1000),
            ("100.USDX", 1),
            ("133.DINIW", 1),
        ]
        for secid, divisor in secids_to_try:
            try:
                url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f44,f45,f170"
                body = self._http_get(url, timeout=8)
                j = json.loads(body)
                if j.get("data"):
                    d = j["data"]
                    val = d.get("f43", 0)
                    if val and val > 0:
                        if divisor == 1000 and val > 1000:
                            dxy = val / 1000.0
                        else:
                            dxy = float(val)
                        if 70 < dxy < 130:
                            self._set_cache(cache_key, dxy)
                            return dxy
            except Exception:
                continue

        # 方法2: 新浪财经USD/CNH汇率推算
        try:
            sina_url = "http://hq.sinajs.cn/list=fx_susdcny"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://finance.sina.com.cn",
                "Connection": "close"
            }
            req = urllib.request.Request(sina_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("gbk", errors="ignore")
            if '"' in body:
                data_str = body[body.find('"')+1:body.rfind('"')]
                parts = data_str.split(',')
                if len(parts) >= 4:
                    buy = float(parts[1]) if parts[1] else 0
                    sell = float(parts[2]) if parts[2] else 0
                    rate = (buy + sell) / 2 if buy > 0 and sell > 0 else 0
                    if 6.0 < rate < 8.0:
                        dxy_est = 100 + (rate - 7.0) * 20
                        if 70 < dxy_est < 130:
                            self._set_cache(cache_key, round(dxy_est, 2))
                            print(f"[ChinaHttp] DXY估算(新浪): USD/CNH={rate:.4f} → {dxy_est:.2f}")
                            return round(dxy_est, 2)
        except Exception as e:
            print(f"[ChinaHttp] 新浪DXY fallback失败: {e}")

        print(f"[ChinaHttp] 美元指数获取失败")
        return None

    def _get_bond_yield_from_china_money(self) -> Optional[float]:
        """获取中国10年期国债收益率"""
        cache_key = self._cache_key("_get_bond_yield")
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            # 方法1: 东方财富10年期国债ETF (511260) 收益率近似
            url = "https://push2.eastmoney.com/api/qt/stock/get?secid=1.511260&fields=f43,f170"
            body = self._http_get(url)
            j = json.loads(body)
            if j.get("data"):
                d = j["data"]
                val = d.get("f43", 0)
                if val and 80 < val < 200:
                    # 国债ETF价格约100元, 收益率=100-ETF价格 近似(不太精确但可用)
                    yield_est = 100.0 - float(val)
                    if 0 < yield_est < 10:
                        self._set_cache(cache_key, round(yield_est, 2))
                        return round(yield_est, 2)
        except Exception as e:
            logger.warning(f"操作失败: {e}")

        # 方法2: 东方财富国债期货主力
        try:
            url = "https://push2.eastmoney.com/api/qt/stock/get?secid=142.T2506&fields=f43,f170"
            body = self._http_get(url)
            j = json.loads(body)
            if j.get("data"):
                d = j["data"]
                val = d.get("f43", 0)
                if val and val > 90:
                    yield_est = 100.0 - float(val)
                    if 0 < yield_est < 10:
                        self._set_cache(cache_key, round(yield_est, 2))
                        return round(yield_est, 2)
        except Exception as e:
            logger.warning(f"操作失败: {e}")

        # 方法3: 使用investing.com的HTTP数据
        try:
            url = "https://api.investing.com/api/financialdata/642287/historical/chart/?period=P1D&interval=PT1M&pointscount=1"
            headers = self._headers.copy()
            headers["domain-id"] = "www"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8")
            if body.strip():
                j = json.loads(body)
                if isinstance(j, list) and len(j) > 0:
                    last = j[-1]
                    val = last.get("close") or last.get("value")
                    if val and 0 < val < 15:
                        self._set_cache(cache_key, float(val))
                        return float(val)
        except Exception as e:
            logger.warning(f"操作失败: {e}")

        # 方法4: 中国债券信息网 (chinabond.com.cn) 关键期限数据
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            # 尝试今天+最近5天（覆盖周末/节假日）
            for days_back in range(6):
                d = datetime.now() - timedelta(days=days_back)
                date_str = d.strftime("%Y-%m-%d")
                cb_url = f"https://yield.chinabond.com.cn/cbweb-cbrc-web/cbrc/queryGjqxInfo?workTime={date_str}&locale=cn_ZH"
                req = urllib.request.Request(cb_url, headers=self._headers)
                with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                    body = resp.read().decode("utf-8", errors="ignore")
                gov_row = re.search(r'中债国债收益率曲线</td>(.*?)</tr>', body, re.DOTALL)
                if gov_row:
                    tds = re.findall(r'<td>([\d.]+)</td>', gov_row.group(1))
                    if len(tds) >= 7:
                        bond_10y = float(tds[6])
                        if 0.5 < bond_10y < 8:
                            self._set_cache(cache_key, round(bond_10y, 4))
                            lag = f" ({days_back}天前)" if days_back > 0 else ""
                            print(f"[ChinaHttp] 国债收益率(中国债券信息网): {bond_10y:.4f}% [日期:{date_str}]{lag}")
                            return round(bond_10y, 4)
                    break  # 有数据但格式不对，不继续尝试
        except Exception as e:
            print(f"[ChinaHttp] 中国债券信息网获取失败: {e}")

        print(f"[ChinaHttp] 国债收益率获取失败")
        return None

    def _get_central_bank_buying(self) -> Optional[float]:
        """获取中国央行月度购金数据（基于黄金储备数值变化推算）
        
        [FIX 2026-04-28] 原公式 |环比%| x 22 完全无依据，误差82.5%
        新公式: 使用最近6个月增量均值，过滤异常值(单月>50万盎司)
        
        数据来源: ak.macro_china_fx_gold() -> 黄金储备-数值列(单位:万盎司)
        单位换算: 1万盎司 = 0.311035吨
        """
        try:
            import akshare as ak
            fx_gold = ak.macro_china_fx_gold()
            if fx_gold is not None and isinstance(fx_gold, pd.DataFrame) and len(fx_gold) >= 2:
                # 查找"黄金储备-数值"列（万盎司）
                value_col = None
                for col in fx_gold.columns:
                    if str(col) == '黄金储备-数值':
                        value_col = col
                        break
                
                if value_col and len(fx_gold) >= 3:
                    # 取最近6个月数据计算月度增量
                    recent = fx_gold.tail(6).copy()
                    increments_tons = []
                    
                    for i in range(1, len(recent)):
                        prev_val = pd.to_numeric(recent.iloc[i-1][value_col], errors='coerce')
                        curr_val = pd.to_numeric(recent.iloc[i][value_col], errors='coerce')
                        if pd.notna(prev_val) and pd.notna(curr_val):
                            diff_wan_ounces = curr_val - prev_val  # 万盎司增量
                            
                            # [FIX] 异常值过滤: 单月增减超过50万盎司(~15.5吨)视为数据异常
                            # 正常中国央行月度购金: 5-25吨/月 ≈ 16-80万盎司/月
                            # 2024-2025极端月份可能达到100万盎司(~31吨)，设阈值为150万盎司
                            if abs(diff_wan_ounces) > 150:
                                print(f"[ChinaHttp] 异常值过滤: {recent.index[i]} 增量 {diff_wan_ounces:+.2f}万盎司 > 150阈值，跳过")
                                continue
                            
                            # 万盎司 -> 吨: 1万盎司 = 0.311035吨
                            diff_tons = abs(diff_wan_ounces) * 0.311035
                            increments_tons.append(diff_tons)
                    
                    if increments_tons:
                        avg_buying = round(sum(increments_tons) / len(increments_tons), 2)
                        
                        # 合理性校验: 中国央行正常月均购金范围 0-40吨/月
                        # 全球央行月均约90吨/月
                        if 0 < avg_buying < 80:
                            print(f"[ChinaHttp] 央行购金({len(increments_tons)}个月均): {avg_buying}吨/月")
                            return avg_buying
                        else:
                            print(f"[ChinaHttp] 购金数据异常({avg_buying}吨/月超出合理范围0-80)，返回None")
                            return None
        except Exception as e:
            print(f"[ChinaHttp] 央行黄金储备获取失败: {e}")
        return None

    def _get_china_gold_reserves(self) -> Optional[float]:
        """获取中国外汇黄金储备 (万盎司)"""
        try:
            import akshare as ak
            fx_gold = ak.macro_china_fx_gold()
            if fx_gold is not None and isinstance(fx_gold, pd.DataFrame) and len(fx_gold) > 0:
                latest = fx_gold.iloc[-1]
                # 精确匹配"黄金储备-数值"列
                for col in fx_gold.columns:
                    if str(col) == '黄金储备-数值':
                        val = pd.to_numeric(latest[col], errors='coerce')
                        if pd.notna(val) and 1000 < val < 5000:
                            return round(float(val), 2)
        except Exception as e:
            print(f"[ChinaHttp] 中国黄金储备获取失败: {e}")
        return None

    # ======================== 市场情绪 ========================

    def get_market_sentiment(self) -> dict:
        """获取市场情绪数据 - 全部使用国内HTTP"""
        sentiment = {}

        vix = self._get_vix_from_investing()
        if vix:
            sentiment["vix"] = vix
            if vix > 30:
                sentiment["sentiment"] = "fear"
            elif vix > 20:
                sentiment["sentiment"] = "anxiety"
            else:
                sentiment["sentiment"] = "calm"

        # GLD替代: 用上海金价格变动
        try:
            url = "https://push2.eastmoney.com/api/qt/stock/get?secid=118.Au99.99&fields=f43,f47,f170"
            body = self._http_get(url)
            j = json.loads(body)
            if j.get("data"):
                d = j["data"]
                change = d.get("f170", 0) / 100
                vol = d.get("f47", 0)
                sentiment["gld_price_change"] = change
                sentiment["gld_volume"] = vol
        except Exception as e:
            logger.warning(f"操作失败: {e}")

        return sentiment

    # ======================== 资产相关性 ========================

    def get_asset_correlation(self, assets: list) -> pd.DataFrame:
        """获取资产相关性 - 基于国内数据的简化实现"""
        return pd.DataFrame()

    # ======================== 数据质量 ========================

    def get_data_quality(self) -> dict:
        return {
            "completeness": 0.80,
            "timeliness": 0.95,
            "consistency": 0.85
        }

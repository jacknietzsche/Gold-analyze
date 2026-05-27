#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新浪财经数据源 - 提供黄金、汇率、VIX、美股指数等数据
数据来源: 新浪财经HTTP API (http://hq.sinajs.cn)
已验证接口: COMEX黄金(hf_GC)、沪金主力(nf_AU0)、黄金ETF(sh518880)、USD/CNH(fx_susdcny)、道琼斯/纳斯达克
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


class SinaFinanceProvider(DataProvider):
    """新浪财经数据源 - 国内直连，不依赖东方财富push2域名"""
    capabilities = {'price', 'sentiment'}

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "sina"
        self._connection_status = True
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://finance.sina.com.cn",
            "Connection": "close"
        }

    def _http_get(self, url: str, timeout: int = 15, encoding: str = "gbk") -> str:
        """通用HTTP GET请求"""
        req = urllib.request.Request(url, headers=self._headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode(encoding, errors="ignore")

    def _parse_sina_response(self, body: str) -> str:
        """从新浪HTTP响应中提取引号内的数据部分"""
        if '"' in body:
            data_start = body.find('"') + 1
            data_end = body.rfind('"')
            if data_start > 0 and data_end > data_start:
                return body[data_start:data_end]
        return ""

    def check_connection(self) -> Dict[str, Any]:
        """检查数据源连接状态"""
        status = {"connected": False, "error": None}
        try:
            # 测试新浪财经API - 使用可靠的代码
            url = "http://hq.sinajs.cn/list=sh518880"
            body = self._http_get(url, timeout=5)
            if "518880" in body:
                status["connected"] = True
            else:
                status["error"] = "响应内容异常"
        except Exception as e:
            status["error"] = str(e)
        return status

    # ======================== 黄金价格 ========================

    def get_gold_price(self, symbol: str = "Au99.99", period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """
        获取黄金价格 - 多源尝试:
        1. 沪金主力合约(nf_AU0) - 上海期货交易所，单位元/克
        2. 黄金ETF华安(sh518880) - 跟踪Au99.99，价格约9.8元/份
        3. COMEX黄金(hf_GC) - 纽约黄金，单位美元/盎司
        """
        cache_key = self._cache_key("get_gold_price", symbol=symbol)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # 方案1: 沪金主力合约 (最准确，元/克)
        df = self._get_shfe_gold()
        if df is not None and not df.empty:
            self._set_cache(cache_key, df)
            return df

        # 方案2: 黄金ETF (元/份，需要转换为元/克)
        df = self._get_gold_etf_price()
        if df is not None and not df.empty:
            self._set_cache(cache_key, df)
            return df

        # 方案3: COMEX黄金 (美元/盎司，需要转换)
        df = self._get_comex_gold()
        if df is not None and not df.empty:
            self._set_cache(cache_key, df)
            return df

        return pd.DataFrame()

    def _get_shfe_gold(self) -> Optional[pd.DataFrame]:
        """获取沪金主力合约价格 (nf_AU0) - 元/克"""
        try:
            url = "http://hq.sinajs.cn/list=nf_AU0"
            body = self._http_get(url)
            data_str = self._parse_sina_response(body)
            if not data_str:
                return None

            parts = data_str.split(',')
            # 格式: 名称,昨收盘,开盘,最高,最低,?,昨结算,买价,卖价,?,?,?,成交量,持仓量,...
            if len(parts) >= 8:
                name = parts[0]
                open_p = float(parts[2]) if parts[2] else 0
                high = float(parts[3]) if parts[3] else 0
                low = float(parts[4]) if parts[4] else 0
                settle = float(parts[5]) if parts[5] and parts[5] != '0.000' else 0
                bid = float(parts[6]) if parts[6] else 0
                ask = float(parts[7]) if parts[7] else 0
                vol = float(parts[11]) if len(parts) > 11 and parts[11] else 0

                # 取中间价作为close
                close = ask if ask > 0 else (bid if bid > 0 else 0)

                # 沪金主力合约价格通常在600-1500元/克范围
                if close > 600:
                    df = pd.DataFrame({
                        "open": [open_p if open_p > 0 else close],
                        "high": [high if high > 0 else close],
                        "low": [low if low > 0 else close],
                        "close": [close],
                        "volume": [vol]
                    }, index=[pd.Timestamp.now().normalize()])
                    print(f"[Sina] 沪金主力价格: {close:.2f}元/克")
                    return df
                else:
                    print(f"[Sina] 沪金价格异常偏低: {close}")
        except Exception as e:
            print(f"[Sina] 沪金获取失败: {e}")
        return None

    def _get_gold_etf_price(self) -> Optional[pd.DataFrame]:
        """获取黄金ETF华安(518880)价格，转换为Au99.99参考价(元/克)"""
        try:
            url = "http://hq.sinajs.cn/list=sh518880"
            body = self._http_get(url)
            data_str = self._parse_sina_response(body)
            if not data_str:
                return None

            parts = data_str.split(',')
            # 格式: 名称,开盘,昨收,最新,最高,最低,买1,卖1,成交量,成交额,...
            if len(parts) >= 10:
                name = parts[0]
                open_p = float(parts[1]) if parts[1] else 0
                pre_close = float(parts[2]) if parts[2] else 0
                price = float(parts[3]) if parts[3] else 0
                high = float(parts[4]) if parts[4] else 0
                low = float(parts[5]) if parts[5] else 0
                vol = float(parts[8]) if parts[8] else 0

                if price > 0:
                    # 黄金ETF 1份 ≈ 0.01克黄金
                    # 价格约9.8元/份 → 约980元/克 (但2026年金价已涨)
                    # 用ETF价格 * 100 作为粗略估算 (金价约1000元/克时，ETF约10元)
                    gold_price = price * 100  # 粗略转换

                    if 600 < gold_price < 2500:
                        df = pd.DataFrame({
                            "open": [open_p * 100],
                            "high": [high * 100],
                            "low": [low * 100],
                            "close": [gold_price],
                            "volume": [vol]
                        }, index=[pd.Timestamp.now().normalize()])
                        print(f"[Sina] 黄金ETF价格: {price:.3f}元/份 → 黄金参考价: {gold_price:.0f}元/克")
                        return df
        except Exception as e:
            print(f"[Sina] 黄金ETF获取失败: {e}")
        return None

    def _get_comex_gold(self) -> Optional[pd.DataFrame]:
        """获取COMEX黄金期货价格(美元/盎司)"""
        try:
            url = "http://hq.sinajs.cn/list=hf_GC"
            body = self._http_get(url)
            data_str = self._parse_sina_response(body)
            if not data_str:
                return None

            parts = data_str.split(',')
            # 格式: 最新价,,开盘,昨收,最高,最低,时间,买价,卖价,?,?,?,日期,名称,...
            if len(parts) >= 6:
                price = float(parts[0]) if parts[0] else 0
                open_p = float(parts[2]) if parts[2] else price
                high = float(parts[4]) if parts[4] else price
                low = float(parts[5]) if parts[5] else price

                if price > 0 and 1000 < price < 10000:
                    df = pd.DataFrame({
                        "open": [open_p],
                        "high": [high],
                        "low": [low],
                        "close": [price],
                        "volume": [0]
                    }, index=[pd.Timestamp.now().normalize()])
                    print(f"[Sina] COMEX黄金: ${price:.2f}/盎司")
                    return df
        except Exception as e:
            print(f"[Sina] COMEX黄金获取失败: {e}")
        return None

    # ======================== 宏观数据 ========================

    def get_macro_data(self, indicators: List[str]) -> dict:
        """获取宏观经济数据"""
        data = {}

        if "dollar_index" in indicators or "vix" in indicators:
            # 通过USD/CNH汇率推算美元指数
            dxy = self._get_dxy_from_usdcnh()
            if dxy:
                data["dollar_index"] = dxy

        return data

    def _get_dxy_from_usdcnh(self) -> Optional[float]:
        """通过USD/CNH汇率推算美元指数"""
        cache_key = self._cache_key("_get_dxy_from_usdcnh")
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            url = "http://hq.sinajs.cn/list=fx_susdcny"
            body = self._http_get(url)
            data_str = self._parse_sina_response(body)
            if not data_str:
                return None

            parts = data_str.split(',')
            # 格式: 时间,买入价,卖出价,最高,成交量,昨收,开盘,最低,中间价,...
            if len(parts) >= 4:
                buy = float(parts[1]) if parts[1] else 0
                sell = float(parts[2]) if parts[2] else 0
                rate = (buy + sell) / 2 if buy > 0 and sell > 0 else 0

                if 6.0 < rate < 8.0:
                    # DXY ~ 100 + (USDCNY - 7.0) * 20 粗略估算
                    dxy_est = 100 + (rate - 7.0) * 20
                    if 70 < dxy_est < 130:
                        self._set_cache(cache_key, round(dxy_est, 2))
                        print(f"[Sina] USD/CNH={rate:.4f} → DXY估算: {dxy_est:.2f}")
                        return round(dxy_est, 2)
        except Exception as e:
            print(f"[Sina] USD/CNH获取失败: {e}")
        return None

    def get_market_sentiment(self) -> Dict[str, Any]:
        """获取市场情绪数据 - 从新浪财经获取道琼斯/纳斯达克/沪深300"""
        sentiment = {}

        # 获取道琼斯
        try:
            url = "http://hq.sinajs.cn/list=int_dji"
            body = self._http_get(url)
            data_str = self._parse_sina_response(body)
            if data_str:
                parts = data_str.split(',')
                if len(parts) >= 4:
                    dji_price = float(parts[1]) if parts[1] else None
                    dji_change = float(parts[2]) if parts[2] else None
                    dji_pct = float(parts[3]) if parts[3] else None
                    if dji_price:
                        sentiment["dow_jones"] = dji_price
                        sentiment["dow_change_pct"] = dji_pct
        except Exception as e:
            print(f"[Sina] 道琼斯获取失败: {e}")

        # 获取纳斯达克
        try:
            url = "http://hq.sinajs.cn/list=int_nasdaq"
            body = self._http_get(url)
            data_str = self._parse_sina_response(body)
            if data_str:
                parts = data_str.split(',')
                if len(parts) >= 4:
                    nasdaq_price = float(parts[1]) if parts[1] else None
                    nasdaq_pct = float(parts[3]) if parts[3] else None
                    if nasdaq_price:
                        sentiment["nasdaq"] = nasdaq_price
                        sentiment["nasdaq_change_pct"] = nasdaq_pct
        except Exception as e:
            print(f"[Sina] 纳斯达克获取失败: {e}")

        # 获取上证指数
        try:
            url = "http://hq.sinajs.cn/list=sh000001"
            body = self._http_get(url)
            data_str = self._parse_sina_response(body)
            if data_str:
                parts = data_str.split(',')
                if len(parts) >= 4:
                    sse_price = float(parts[1]) if parts[1] else None
                    sse_pct = float(parts[3]) if parts[3] else None
                    if sse_price:
                        sentiment["sse_index"] = sse_price
                        sentiment["sse_change_pct"] = sse_pct
        except Exception as e:
            print(f"[Sina] 上证指数获取失败: {e}")

        # 综合市场情绪
        changes = [v for k, v in sentiment.items() if 'change_pct' in k and v is not None]
        if changes:
            avg_change = sum(changes) / len(changes)
            if avg_change > 1.0:
                sentiment["market_sentiment"] = "bullish"
            elif avg_change < -1.0:
                sentiment["market_sentiment"] = "bearish"
            else:
                sentiment["market_sentiment"] = "neutral"

        return sentiment

    def get_asset_correlation(self, assets: list) -> pd.DataFrame:
        """获取资产相关性数据 - 新浪财经不支持历史数据，返回空DataFrame"""
        return pd.DataFrame()


if __name__ == "__main__":
    provider = SinaFinanceProvider()

    print("=" * 60)
    print("新浪财经数据源测试")
    print("=" * 60)

    conn_status = provider.check_connection()
    print(f"\n连接状态: {conn_status}")

    # 测试黄金价格
    print("\n获取黄金价格...")
    gold_data = provider.get_gold_price("Au99.99")
    if not gold_data.empty:
        print(f"成功: {gold_data.to_dict()}")
    else:
        print("失败")

    # 测试宏观数据
    print("\n获取宏观数据...")
    macro = provider.get_macro_data(["dollar_index", "vix"])
    print(f"宏观数据: {macro}")

    # 测试市场情绪
    print("\n获取市场情绪...")
    sentiment = provider.get_market_sentiment()
    print(f"市场情绪: {sentiment}")

    print("\n" + "=" * 60)
    print("测试完成")

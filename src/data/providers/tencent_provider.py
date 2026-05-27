#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯财经数据源 - 提供股票、ETF、指数等实时行情
数据来源: 腾讯财经HTTP API (http://qt.gtimg.cn / http://web.ifzq.gtimg.cn)
已验证: http://qt.gtimg.cn 可正常访问
"""

import json
import time
import urllib.request
import urllib.error
import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from src.data.data_provider import DataProvider


class TencentFinanceProvider(DataProvider):
    """腾讯财经数据源 - 国内直连"""
    capabilities = {'price', 'sentiment'}

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "tencent"
        self._connection_status = True
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://gu.qq.com",
            "Connection": "close"
        }

    def _http_get(self, url: str, timeout: int = 15, encoding: str = "gbk") -> str:
        """通用HTTP GET请求"""
        req = urllib.request.Request(url, headers=self._headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode(encoding, errors="ignore")

    def _parse_qt_response(self, body: str) -> List[str]:
        """解析腾讯财经qt.gtimg.cn响应
        格式: v_SYMBOL="field1~field2~field3~...";
        """
        match = re.search(r'="([^"]*)"', body)
        if match:
            return match.group(1).split('~')
        return []

    def check_connection(self) -> Dict[str, Any]:
        """检查数据源连接状态"""
        status = {"connected": False, "error": None}
        try:
            url = "http://qt.gtimg.cn/q=sh518880"
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
        获取黄金价格 - 通过黄金ETF估算
        腾讯财经提供实时股票/ETF行情
        """
        cache_key = self._cache_key("get_gold_price", symbol=symbol)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # 方案1: 黄金ETF华安(518880) → 估算Au99.99
        df = self._get_gold_etf()
        if df is not None and not df.empty:
            self._set_cache(cache_key, df)
            return df

        # 方案2: 黄金ETF国泰(518800)
        df = self._get_gold_etf("sh518800")
        if df is not None and not df.empty:
            self._set_cache(cache_key, df)
            return df

        return pd.DataFrame()

    def _get_gold_etf(self, code: str = "sh518880") -> Optional[pd.DataFrame]:
        """获取黄金ETF价格并转换为Au99.99参考价"""
        try:
            url = f"http://qt.gtimg.cn/q={code}"
            body = self._http_get(url)
            parts = self._parse_qt_response(body)

            if len(parts) < 35:
                return None

            # 腾讯财经字段
            name = parts[1] if len(parts) > 1 else ""
            price = float(parts[3]) if parts[3] else 0
            pre_close = float(parts[4]) if parts[4] else 0
            open_p = float(parts[5]) if parts[5] else 0
            vol = float(parts[6]) if parts[6] else 0
            high = float(parts[33]) if len(parts) > 33 and parts[33] else price
            low = float(parts[34]) if len(parts) > 34 and parts[34] else price

            if price > 0:
                # 黄金ETF 1份 ≈ 0.01克黄金
                # 精确转换: ETF价格 / 0.01 = 元/克
                gold_price = price / 0.01  # 更准确的转换

                if 600 < gold_price < 2500:
                    df = pd.DataFrame({
                        "open": [open_p / 0.01],
                        "high": [high / 0.01],
                        "low": [low / 0.01],
                        "close": [gold_price],
                        "volume": [vol]
                    }, index=[pd.Timestamp.now().normalize()])
                    print(f"[Tencent] 黄金ETF({code}): {price:.3f}元/份 → 黄金参考价: {gold_price:.0f}元/克")
                    return df
                else:
                    print(f"[Tencent] 黄金ETF价格异常: {gold_price}")
        except Exception as e:
            print(f"[Tencent] 黄金ETF获取失败: {e}")
        return None

    # ======================== 宏观数据 ========================

    def get_macro_data(self, indicators: List[str]) -> dict:
        """获取宏观经济数据 - 腾讯财经提供股票行情，暂无宏观指标"""
        return {}

    def get_market_sentiment(self) -> Dict[str, Any]:
        """获取市场情绪数据 - 从腾讯财经获取沪深300/上证指数"""
        sentiment = {}

        # 获取上证指数
        try:
            url = "http://qt.gtimg.cn/q=sh000001"
            body = self._http_get(url)
            parts = self._parse_qt_response(body)

            if len(parts) >= 35:
                sse_price = float(parts[3]) if parts[3] else None
                sse_pct_str = parts[32] if len(parts) > 32 else ""
                sse_pct = float(sse_pct_str) if sse_pct_str else None

                if sse_price:
                    sentiment["sse_index"] = sse_price
                    sentiment["sse_change_pct"] = sse_pct
                    print(f"[Tencent] 上证指数: {sse_price} ({sse_pct}%)")
        except Exception as e:
            print(f"[Tencent] 上证指数获取失败: {e}")

        # 获取深证成指
        try:
            url = "http://qt.gtimg.cn/q=sz399001"
            body = self._http_get(url)
            parts = self._parse_qt_response(body)

            if len(parts) >= 35:
                szse_price = float(parts[3]) if parts[3] else None
                szse_pct_str = parts[32] if len(parts) > 32 else ""
                szse_pct = float(szse_pct_str) if szse_pct_str else None

                if szse_price:
                    sentiment["szse_index"] = szse_price
                    sentiment["szse_change_pct"] = szse_pct
                    print(f"[Tencent] 深证成指: {szse_price} ({szse_pct}%)")
        except Exception as e:
            print(f"[Tencent] 深证成指获取失败: {e}")

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
        """获取资产相关性数据 - 腾讯财经不支持历史数据，返回空DataFrame"""
        return pd.DataFrame()


if __name__ == "__main__":
    provider = TencentFinanceProvider()

    print("=" * 60)
    print("腾讯财经数据源测试")
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

    # 测试市场情绪
    print("\n获取市场情绪...")
    sentiment = provider.get_market_sentiment()
    print(f"市场情绪: {sentiment}")

    print("\n" + "=" * 60)
    print("测试完成")

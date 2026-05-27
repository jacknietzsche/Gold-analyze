#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FRED API 客户端 — 从 V6 报告提取的纯 HTTP 逻辑
无外部依赖（仅 stdlib），可独立使用。
"""

import json
import os
import urllib.request
import ssl as _ssl
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def _get_api_key() -> str:
    """获取 FRED API Key（环境变量 → config）"""
    key = os.environ.get('FRED_API_KEY', '')
    if key:
        return key
    try:
        from src.config.gold_config import get_config
        return get_config().data.api_keys.get('fred', '')
    except Exception:
        return ''


def fetch_fred_data(series_id: str, limit: int = 1,
                    api_key: str = '') -> Optional[Dict]:
    """直接调用 FRED API 获取最新观测值"""
    if not api_key:
        api_key = _get_api_key()
    if not api_key:
        return None

    url = (f"https://api.stlouisfed.org/fred/series/observations"
           f"?series_id={series_id}&api_key={api_key}"
           f"&file_type=json&sort_order=desc&limit={limit}")
    try:
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        logger.warning(f"FRED fetch failed for {series_id}: {e}")
        return None


def fetch_fred_series(series_id: str, days: int = 365,
                      api_key: str = '') -> Optional[pd.Series]:
    """获取 FRED 时间序列（返回 pd.Series）"""
    if not api_key:
        api_key = _get_api_key()
    if not api_key:
        return None

    start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    url = (f"https://api.stlouisfed.org/fred/series/observations"
           f"?series_id={series_id}&api_key={api_key}"
           f"&file_type=json&observation_start={start}&sort_order=asc")
    try:
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
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
        logger.warning(f"FRED series fetch failed for {series_id}: {e}")
        return None


def fetch_latest_value(series_id: str, api_key: str = '') -> Optional[float]:
    """获取 FRED 最新单值（便捷函数）"""
    data = fetch_fred_data(series_id, limit=1, api_key=api_key)
    if data and 'observations' in data:
        obs = data['observations']
        if obs and obs[0].get('value') != '.':
            return float(obs[0]['value'])
    return None

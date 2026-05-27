#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
类型化数据契约 — 替代无类型 dict 传递
所有 DataService → Report 层的数据流通过这些 dataclass 定义。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import pandas as pd


@dataclass
class GoldPriceData:
    """黄金价格数据"""
    ohlc: pd.DataFrame = field(default_factory=pd.DataFrame)   # 含 open/high/low/close/volume
    price_series: Optional[pd.Series] = None                   # close 序列
    symbol: str = "Au99.99"
    source: str = ""
    rows: int = 0


@dataclass
class MacroData:
    """宏观经济数据"""
    bond_yield: Optional[float] = None
    tips_yield: Optional[float] = None
    vix: Optional[float] = None
    dollar_index: Optional[float] = None
    cpi: Optional[float] = None
    m2: Optional[float] = None
    central_bank_buying: Optional[float] = None
    china_reserves: Optional[float] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SentimentData:
    """市场情绪数据"""
    vix: Optional[float] = None
    sentiment: str = "calm"            # fear / anxiety / calm
    gld_volume: Optional[int] = None
    gld_price_change: Optional[float] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkData:
    """基准数据（上海金基准价等）"""
    benchmark_price: Optional[float] = None
    benchmark_change_pct: Optional[float] = None
    source: str = ""


@dataclass
class AllMarketData:
    """完整市场数据容器 — DataService.get_all_data 返回值"""
    gold: GoldPriceData = field(default_factory=GoldPriceData)
    macro: MacroData = field(default_factory=MacroData)
    sentiment: SentimentData = field(default_factory=SentimentData)
    benchmark: BenchmarkData = field(default_factory=BenchmarkData)
    returns: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    correlation: pd.DataFrame = field(default_factory=pd.DataFrame)
    data_quality: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

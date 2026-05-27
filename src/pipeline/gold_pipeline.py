#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金量化报告 Pipeline — 顶层编排器
协调 Data → Analysis → Report 三层。
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def run_pipeline(report_version: str = "v6", use_llm: bool = True,
                 llm_type: Optional[str] = None, api_key: Optional[str] = None,
                 auto_open: bool = True) -> str:
    """运行完整 Pipeline: 数据获取 → 分析 → 报告生成

    Args:
        report_version: "v5" 或 "v6"
        use_llm: 是否使用 LLM 分析
        llm_type: LLM 类型 (siliconflow/chatanywhere/openai/cherry/openrouter)
        api_key: API Key
        auto_open: 是否自动打开报告

    Returns:
        生成的报告文件路径
    """
    if report_version == "v6":
        from src.report.gold_report_generator_v6 import GoldReportGeneratorV6 as ReportClass
    else:
        from src.report.gold_report_generator_v5 import GoldReportGeneratorV5 as ReportClass

    report = ReportClass(llm_type=llm_type, use_llm=use_llm, api_key=api_key)
    report.run(auto_open=auto_open)

    filepath = getattr(report, 'report_filepath', None)
    if filepath:
        logger.info(f"报告生成完成: {filepath}")
    return filepath or ""

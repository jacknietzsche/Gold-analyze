# 黄金量化系统 - 错误与学习日志

## [ERR-20260402-001] HTML报告中所有数据显示N/A

**Logged**: 2026-04-02T21:28:00
**Priority**: critical
**Status**: resolved
**Area**: backend

### Summary
增强版量化报告所有数据字段显示N/A，基本面分析和情绪分析完全空白。

### Root Causes (多重原因)
1. 报告生成器`_generate_fundamental_analysis()`和`_generate_sentiment_analysis()`仅从`self.results['fundamental']`和`self.results['sentiment']`取数据，但增强版不生成这些字典
2. `run_gold_analysis_enhanced.py`传递的`analysis_data`未包含`results`键
3. `yfinance`在中国网络环境下curl error 16频繁超时，导致美债/VIX/美元/ETF等外部数据全部为空
4. `factors.py`缺少`momentum_5d/10d`、`volatility_20d`、MA值、MACD等因子
5. `strategies.py`依赖sklearn，可能import失败

### Resolution
- **data_sources.py**: 全面重写为多数据源容错架构(akshare->yfinance->HTTP->模拟)
- **factors.py**: 补充所有缺失因子(momentum_5d/10d, volatility_20d, MACD, MA值)
- **gold_report_generator.py**: 完全重写，用安全getter方法(_fv/_fd/_rd)确保永不返回N/A
- **strategies.py**: 移除sklearn，改用纯numpy OLS
- **run_gold_analysis_enhanced.py**: analysis_data增加results键传递

### Key Learning
- **Pattern-Key**: harden.na_free_reports
- 报告模板中所有数据获取必须经过安全方法，默认值用'--'而非'N/A'
- 国内量化系统数据源优先级: akshare > 东方财富HTTP > yfinance(最后手段)
- TIPS数据可直接用名义利率-CPI估算

### Metadata
- Source: user_feedback
- Related Files: data_sources.py, factors.py, gold_report_generator.py, strategies.py, run_gold_analysis_enhanced.py
- Pattern-Key: harden.na_free_reports
- Recurrence-Count: 2 (第二次修复，第一次2026-04-01)

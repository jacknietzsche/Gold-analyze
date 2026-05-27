# 学习记录

## [LRN-20260427-001] html_escape

**Logged**: 2026-04-27T20:30:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
AI生成的Markdown内容在转换为HTML时，由于先执行了全局`replace('&','&amp;')`，导致内容中已有的`<br>`、`</p>`等HTML标签被转义为`&lt;br&gt;`、`&lt;/p&gt;`，在页面上直接显示为文本而非渲染为标签。

### Details
原代码：
```python
html = md_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
```
当LLM返回的内容已经包含`<br>`、`<p>`等HTML标签时，上述代码会将它们转义，导致浏览器显示原始文本`&lt;br&gt;`。

### Suggested Action
修复方案：在转义前识别并保留已有的HTML标签，或改进_markdown_to_html方法以正确处理混合内容。

### Resolution
- **Resolved**: 2026-04-27T20:30:00+08:00
- **修复方案**: 在`_markdown_to_html()`中，先恢复已转义的HTML标签，再处理Markdown格式。对于已经是HTML格式的输入，直接返回而不包裹`<p>`标签。
- **相关文件**: `src/report/gold_report_generator_v6.py`

### Metadata
- Source: user_feedback
- Related Files: src/report/gold_report_generator_v6.py
- Tags: html, markdown, escaping
- Pattern-Key: harden.html_escape_order

---

## [LRN-20260427-002] dynamic_data

**Logged**: 2026-04-27T20:30:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
AI fallback内容中的情景分析价格（如1150元、950元）和配置比例是硬编码的，不随真实金价变化，导致报告数据失真。

### Details
`_get_fallback_content()`中的`scenario_analysis`主题使用了固定价格区间：
- 乐观：1150元
- 中性：980-1100元
- 悲观：950元

这些价格与当前真实金价（如1048元）脱节。

### Suggested Action
所有价格目标应基于当前真实价格动态计算：
```python
bull_target = round(price * (1 + bull_pct), 0)
base_low = round(price * (1 + base_pct - 0.03), 0)
```

### Resolution
- **Resolved**: 2026-04-27T20:30:00+08:00
- **修复方案**: 
  1. `scenario_analysis`: 基于`price`动态计算目标价（bull_target/base_low/bear_target）
  2. `investment_strategy`: 基于`vol_pct`动态计算止损比例，引用真实MA20/high_60d
  3. `risk_warning`: 基于真实`dd`/`var95`计算风险等级，动态止损建议
  4. `portfolio_allocation`: 基于`hp`（历史分位）动态调整配置比例
- **相关文件**: `src/report/gold_report_generator_v6.py`

### Metadata
- Source: user_feedback
- Related Files: src/report/gold_report_generator_v6.py
- Tags: data_integrity, hardcoded, dynamic
- Pattern-Key: harden.no_hardcoded_prices

---

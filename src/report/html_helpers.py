#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML 辅助工具函数 — 颜色/标签/Markdown转换
纯函数，无状态。
"""

import re


def safe_float(val, default=0):
    """安全转换为浮点数"""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def trend_word(value):
    """趋势文字描述"""
    if value > 10: return '强势大涨'
    if value > 5: return '趋势性上涨'
    if value > 2: return '震荡上行'
    if value > 0: return '小幅上涨'
    if value > -2: return '小幅下跌'
    if value > -5: return '震荡下行'
    if value > -10: return '明显回调'
    return '大幅下跌'


def gram_outlook_text(score):
    """GRAM 评分展望文本"""
    if score >= 6.5: return '四大驱动因子多数利好，金价具备持续上涨动能'
    if score >= 5.5: return '利好因素占主导，但需关注边际变化'
    if score >= 4.5: return '多空因素交织，建议观望或轻仓操作'
    if score >= 3.5: return '利空因素偏多，注意风险控制'
    return '多重利空压制，建议规避'


def rsi_color(v):
    if v >= 70: return '#c0392b'
    if v <= 30: return '#27ae60'
    return '#d4af37'


def rsi_bg(v):
    if v >= 70: return '#fdecea'
    if v <= 30: return '#eafaf1'
    return '#fef9e7'


def rsi_label(v):
    if v >= 80: return '严重超买'
    if v >= 70: return '超买区'
    if v >= 50: return '中性偏强'
    if v >= 30: return '中性偏弱'
    if v >= 20: return '超卖区'
    return '严重超卖'


def hist_zone_label(p):
    if p >= 80: return '历史高位'
    if p >= 60: return '偏高区域'
    if p >= 40: return '中位区域'
    if p >= 20: return '偏低区域'
    return '历史低位'


def kdj_color(jv):
    if jv >= 100: return '#c0392b'
    if jv <= 0: return '#27ae60'
    return '#d4af37'


def kdj_bg(jv):
    if jv >= 100: return '#fdecea'
    if jv <= 0: return '#eafaf1'
    return '#fef9e7'


def markdown_to_html(md_text):
    """将Markdown文本转换为HTML(轻量级解析器，无外部依赖)"""
    if not md_text:
        return ''

    html = md_text

    # 代码块
    html = re.sub(r'```(\w*)\n(.*?)```', r'<pre><code class="\1">\2</code></pre>', html, flags=re.DOTALL)
    # 行内代码
    html = re.sub(r'`([^`]+)`', r'<code style="background:#f4f4f4;padding:2px 6px;border-radius:3px;font-size:0.9em;">\1</code>', html)
    # 标题
    html = re.sub(r'^### (.+)$', r'<h4 style="color:#2c3e50;margin:14px 0 8px;font-size:15px;border-bottom:1px solid #eee;padding-bottom:4px;">\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h3 style="color:#1a1a2e;margin:18px 0 10px;font-size:16px;">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h2 style="color:#d4af37;margin:20px 0 10px;font-size:18px;">\1</h2>', html, flags=re.MULTILINE)
    # 加粗 / 斜体
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#1a1a2e;">\1</strong>', html)
    html = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', html)
    # 无序列表
    html = re.sub(r'^\- (.+)$', r'<li style="margin:3px 0;">\1</li>', html, flags=re.MULTILINE)
    # 换行
    html = html.replace('\n', '<br>\n')

    return html

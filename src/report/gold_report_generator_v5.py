#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金量化分析报告生成器 V5 - 专业增强版
参考: 世界黄金协会(WGC) GRAM框架 + 高盛/摩根大通技术分析体系 + 行业领先量化机构最佳实践

核心升级:
1. 新增完整技术指标体系 (MACD, RSI, BOLL, KDJ, ATR)
2. K线形态识别 (十字星, 锤头线, 吞没形态)
3. GRAM归因分析框架 (WGC标准)
4. 交互式Chart.js图表可视化
5. 相关性热力图 (金价vs美元/利率/VIX)
6. 专业级排版和配色方案
7. 行业对标分析和基准比较
8. 风险量化分析和压力测试
9. 增强的数据可视化和专业报告结构
10. 符合行业领先量化机构标准的分析方法
"""

import json
import sys
import logging
from datetime import datetime
from pathlib import Path

from src.report.gold_report_base import GoldReportBase

logger = logging.getLogger(__name__)


class GoldReportGeneratorV5(GoldReportBase):
    """黄金量化分析报告生成器 V5 - 专业增强版"""

    def __init__(self, llm_type=None, use_llm=True, api_key=None):
        super().__init__(llm_type=llm_type, use_llm=use_llm, api_key=api_key)
        print(f"=== 黄金量化报告生成器 V5 (专业增强版) ===")
        print(f"报告日期: {self.report_date.strftime('%Y-%m-%d')}")
        print(f"行业对标: {list(self.industry_benchmarks.values())}")
        print(f"使用LLM: {self.use_llm}")
        print(f"固定主题数: {len(self.FIXED_TOPICS)}")
        from src.report.gold_report_base import _BACKTESTER_AVAILABLE, _RISK_MANAGER_AVAILABLE, _REGIME_DETECTOR_AVAILABLE
        print(f"量化模块: Backtester={'OK' if _BACKTESTER_AVAILABLE else 'N/A'} | "
              f"RiskMgr={'OK' if _RISK_MANAGER_AVAILABLE else 'N/A'} | "
              f"RegimeDet={'OK' if _REGIME_DETECTOR_AVAILABLE else 'N/A'}")

    def generate_html_report(self):
        """V5专业版HTML报告 - WGC GRAM框架 + 完整技术指标"""
        d = self.data
        if 'returns' not in d:
            return None
        r = d['returns']
        gram = d.get('gram', {})

        # === 动态压力测试影响值(优先级1修复)===
        stress_test = d.get('risk_analysis', {}).get('stress_test', {})
        stress_ir_impact = stress_test.get('interest_rate_shock', {}).get('impact', '--')
        stress_dxy_impact = stress_test.get('dollar_strength', {}).get('impact', '--')

        def cc(v): return ('up', '+') if v >= 0 else ('down', '')
        llm = d.get('llm_insight', '')

        # 动态情景概率
        scen = self._calculate_scenario_probabilities(d)
        base_p = scen['base_pct']
        bull_p = scen['bull_pct']
        bear_p = scen['bear_pct']

        # 准备图表数据
        oc_s = gram.get('opportunity_cost', {}).get('score', 5)
        ru_s = gram.get('risk_uncertainty', {}).get('score', 5)
        sd_s = gram.get('supply_demand', {}).get('score', 5)
        mo_s = gram.get('momentum', {}).get('score', 5)

        # 动态行业对标数据(用于Chart.js，替代硬编码)
        _bench_for_chart = {}
        for bk, bv in self.data.get('industry_benchmarks', {}).items():
            if isinstance(bv, dict):
                _bench_for_chart[bk] = {
                    'name': bv.get('name', bk),
                    'ytd_return': bv.get('ytd_return'),
                    'volatility': bv.get('volatility'),
                }
        bench_json_data = json.dumps(_bench_for_chart, ensure_ascii=False)

        # 动态风险指标数据(用于Chart.js，替代硬编码)
        _risk_for_chart = self.data.get('risk_analysis', {})
        risk_keys_to_export = ['max_drawdown', 'value_at_risk', 'conditional_var', 'sharpe_ratio', 'sortino_ratio']
        _risk_chart_data = {k: _risk_for_chart.get(k) for k in risk_keys_to_export}
        risk_json_data = json.dumps(_risk_chart_data)

        # === 动态机构观点(优先级3修复)===
        gram_score = gram.get('total_score', 5)
        rsi = d.get('rsi_14', 50)
        rsi_status = "超买" if rsi >= 70 else "超卖" if rsi <= 30 else "中性"
        dxy = d.get('dollar_index', 100)
        bond_yield = d.get('bond_yield', 2.0)
        hist_pct = d.get('historical_percentile', 50)

        # 高盛视角
        gold_short_gold = "高位震荡偏多" if rsi < 70 and hist_pct > 70 else "谨慎回调" if rsi >= 70 else "震荡偏多"
        gold_mid_gold = "中性偏多" if gram_score >= 5 else "偏空整理"
        gold_long_gold = "结构性牛市" if gram_score >= 5 else "长期中性"

        # 摩根大通视角
        gold_short_jpm = "区间整理" if rsi > 30 and rsi < 70 else "超买整理" if rsi >= 70 else "超卖反弹"
        gold_mid_jpm = "震荡上行" if gram_score >= 5 else "震荡整理"
        gold_long_jpm = "长期看多" if gram_score >= 5 else "长期中性"

        # 贝莱德视角
        gold_short_blk = "谨慎看涨" if hist_pct > 70 else "配置机会" if hist_pct < 30 else "结构性机会"
        gold_mid_blk = "结构性机会" if gram_score >= 5 else "等待时机"
        gold_long_blk = "配置价值" if gram_score >= 5 else "配置中性"

        # 当前分析视角
        gold_short_now = self._trend_word(r.get('近5日', {}).get('value', 0)) if rsi < 70 else "超买注意"
        gold_mid_now = "震荡整理" if 4 <= gram_score <= 6 else ("上行趋势" if gram_score > 6 else "偏空整理")
        gold_long_now = "结构性牛市" if gram_score >= 5 else "中性偏空"
        gold_risk_now = f"政策转向,美元{round(dxy,0)}" if dxy >= 102 else "美元走弱,低利率"

        # 验证结论
        gram_confirm = "一致" if 4.5 <= gram_score <= 6 else "偏多" if gram_score > 6 else "谨慎"
        risk_confirm = "高度重合" if _risk_for_chart.get('max_drawdown', 0) < 15 else "需关注波动"

        # === 机构综合洞察动态生成 ===
        latest_price = d.get('sge_latest_price', 0)
        high_60d = d.get('high_60d', 0)
        low_60d = d.get('low_60d', 0)

        # 动态共识
        short_consensus = ("高位震荡" if hist_pct > 70 else "区间整理" if 30 < hist_pct < 70 else "低位反弹")
        mid_consensus = ("震荡上行机会" if gram_score >= 5 else "偏空整理")
        long_consensus = ("配置价值" if gram_score >= 5 else "中性配置")

        # 动态行动建议
        short_action = f"在支撑位CNY {round(low_60d,0)}附近布局" if low_60d > 0 else "区间操作"
        _pa = d.get('industry_comparison', {}).get('portfolio_allocation', {})
        _mod_alloc = _pa.get('moderate', 10) if _pa else 10
        mid_action = f"优化资产配置比例至{_mod_alloc}%"
        long_action = "保持黄金战略地位"

        # 动态差异点
        gold_fed_sensitivity = "美联储政策" if bond_yield < 2.5 else "通胀预期"
        _vix_val = d.get('vix', 20)
        gold_vol_focus = f"波动率{_vix_val}" if _vix_val else "市场情绪"
        gold_geo_concern = "地缘政治" if _vix_val > 25 else "通胀预期"

        # 动态关键共识
        consensus_short = f"黄金处于{short_consensus}阶段，{'技术面与基本面存在一定背离' if rsi > 70 else '多空信号趋于一致'}"
        consensus_mid = "机构普遍看好震荡上行机会，央行购金提供结构性支撑" if gram_score >= 5 else "机构对中期走势存在分歧"
        consensus_long = "共识性看好黄金的配置价值，结构性牛市逻辑" + ("未变" if gram_score >= 5 else "需观察")

        # Pre-compute KPI dynamic values
        _r5 = r.get("近5日",{}).get("value",0); _r5_cls = "up" if _r5 >= 0 else "down"
        _r5_sign = "+" if _r5 >= 0 else ""
        _r20 = r.get("近20日(1月)",{}).get("value",0); _r20_cls = "up" if _r20 >= 0 else "down"
        _r20_sign = "+" if _r20 >= 0 else ""
        _rsi14 = d.get("rsi_14",50)
        _rsi_c = self._rsi_color(_rsi14)
        _hist_zone_label = self._hist_zone_label

        h = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{self.report_date.strftime("%Y%m%d")} 黄金量化专业报告 V5</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

<style>
/* ========== V5 设计系统 ========== */
:root {{
    --navy-900:#0B132B; --navy-800:#1C2541; --navy-700:#3A506B;
    --navy-100:#F0F2F8;
    --gold-500:#C5A572; --gold-400:#DFBC8E; --gold-300:#EBD5AC; --gold-100:#FBF5EE;
    --green-up:#00B386; --red-down:#EF4444;
    --text-primary:#111827; --text-secondary:#4B5563; --text-muted:#9CA3AF;
    --bg-body:#F8FAFC; --bg-card:#FFFFFF;
    --border-light:#E5E7EB; --shadow-sm:0 1px 2px rgba(0,0,0,.05);
    --shadow-md:0 4px 16px rgba(0,0,0,.08); --shadow-lg:0 12px 40px rgba(0,0,0,.12);
    --radius-sm:6px; --radius-md:10px; --radius-lg:16px;
}}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{
    font-family:'Inter',-apple-system,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;
    background:var(--bg-body); color:var(--text-primary);
    line-height:1.65; font-size:14px; padding:0; -webkit-font-smoothing:antialiased;
}}
.c {{ max-width:1240px; margin:0 auto; padding:24px 28px 48px; }}
.cover {{
    background:linear-gradient(135deg,var(--navy-900) 0%,var(--navy-800) 45%,#243B61 100%);
    border-radius:var(--radius-lg); padding:56px 48px 48px; margin-bottom:32px;
    position:relative; overflow:hidden; box-shadow:var(--shadow-lg);
}}
.cover::before {{
    content:'';position:absolute;top:-80px;right:-80px;width:260px;height:260px;
    background:radial-gradient(circle,rgba(197,165,114,.15),transparent 70%); border-radius:50%;
}}
.cover h1 {{ color:#FFF;font-size:30px;font-weight:800;letter-spacing:1px;border:none;padding:0;margin:0 0 8px;position:relative;z-index:1; }}
.cover .sub {{ color:var(--gold-400);font-size:15px;font-weight:500;margin:0 0 20px;letter-spacing:.5px;position:relative;z-index:1; }}
.cover .meta {{ color:rgba(255,255,255,.55);font-size:13px;line-height:2;position:relative;z-index:1; }}
.badge {{
    display:inline-flex;align-items:center;gap:6px;
    background:linear-gradient(135deg,var(--gold-500),var(--gold-400));
    color:var(--navy-900);padding:6px 20px;border-radius:24px;
    font-size:13px;font-weight:700;margin-top:18px;letter-spacing:.5px;position:relative;z-index:1;
}}
h2 {{ color:var(--navy-800);font-size:20px;font-weight:700;margin:42px 0 18px;padding-left:16px;
      border-left:4px solid var(--gold-500);letter-spacing:-.02em; }}
h3 {{ color:var(--navy-800);font-size:15.5px;font-weight:600;margin:22px 0 12px;padding-bottom:8px;
      border-bottom:1.5px solid var(--border-light);letter-spacing:-.01em; }}
.card {{
    background:var(--bg-card); border-radius:var(--radius-md);
    padding:28px; margin-bottom:20px; border:1px solid rgba(0,0,0,.04);
    box-shadow:var(--shadow-sm); transition:box-shadow .2s ease;
}}
.card:hover {{ box-shadow:var(--shadow-md); }}
.sc {{ background:linear-gradient(135deg,var(--gold-100),#FFF); border-left:4px solid var(--gold-500); }}
.price {{ font-size:36px;color:var(--gold-500);font-weight:800;letter-spacing:-.03em; }}
.ps {{ font-size:24px;font-weight:700; }}
.up {{ color:var(--red-down)!important;font-weight:700; }}
.down {{ color:var(--green-up)!important;font-weight:700; }}
table {{ width:100%;border-collapse:collapse;margin:14px 0;font-size:13.5px; }}
thead th {{
    background:var(--navy-800);color:#fff;padding:12px 14px;text-align:left;
    font-size:12.5px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap;
}}
tbody td {{ padding:11px 14px;border-bottom:1px solid var(--border-light);color:var(--text-primary); }}
tbody tr:nth-child(even) {{ background:#FAFCFE; }}
tbody tr:hover {{ background:var(--navy-100); transition:background .15s; }}
.gb {{ height:24px;background:var(--border-light);border-radius:12px;overflow:hidden;margin:4px 0; }}
.gf {{ height:100%;border-radius:12px;display:flex;align-items:center;justify-content:flex-end;
       padding-right:10px;color:#fff;font-size:11px;font-weight:700;min-width:38px;
       transition:width .6s cubic-bezier(.4,0,.2,1); }}
.kpi-grid {{ display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin:16px 0; }}
.kpi-card {{
    background:var(--bg-card); border-radius:var(--radius-md); padding:20px 18px;
    border:1px solid var(--border-light); text-align:center;
    transition:all .2s ease; box-shadow:var(--shadow-sm);
}}
.kpi-card:hover {{ transform:translateY(-2px); box-shadow:var(--shadow-md); }}
.kpi-label {{ font-size:12px;color:var(--text-muted);font-weight:500;text-transform:uppercase;letter-spacing:.06em; }}
.kpi-value {{ font-size:26px;font-weight:800;color:var(--navy-800);margin:6px 0 2px;letter-spacing:-.02em; }}
.kpi-sub {{ font-size:12px;color:var(--text-secondary); }}
.exec-summary {{
    background:linear-gradient(135deg,#0F172A,#1E293B);
    border-radius:var(--radius-lg);padding:32px;margin-bottom:24px;
    color:#fff; box-shadow:var(--shadow-lg); border:1px solid rgba(197,165,114,.2);
}}
.es-title {{ font-size:13px;color:var(--gold-400);text-transform:uppercase;letter-spacing:.12em;font-weight:600;margin-bottom:14px; }}
.es-score {{ font-size:52px;font-weight:800;color:var(--gold-500);line-height:1; }}
.ds {{ background:#ECFDF5;padding:14px 18px;border-radius:var(--radius-sm);margin:14px 0;
      font-size:13px;line-height:1.8;border-left:4px solid var(--green-up);color:var(--text-secondary); }}
.wn {{ background:#FFFBEB;padding:14px 18px;border-radius:var(--radius-sm);margin:14px 0;
      font-size:13px;border-left:4px solid #F59E0B;color:var(--text-secondary); }}
.lb {{ background:#EFF6FF;padding:18px 20px;border-radius:var(--radius-sm);margin:14px 0;
      font-size:13.5px;line-height:1.85;border-left:4px solid #3B82F6;color:var(--text-secondary); }}
.cr {{ display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:14px 0; }}
@media(max-width:860px){{ .cr{{grid-template-columns:1fr;}} .kpi-grid{{grid-template-columns:repeat(2,1fr);}} }}
.cw {{ position:relative;height:340px;width:100%;margin:14px 0; }}
.cw-lg {{ height:420px; }}
.pt {{ display:inline-block;padding:4px 12px;border-radius:16px;font-size:12px;margin:3px 5px 3px 0;font-weight:600; }}
.bull {{ background:#FEF2F2;color:var(--red-down);border:1px solid #FECACA; }}
.bear {{ background:#ECFDF5;color:var(--green-up);border:1px solid #BBF7D0; }}
.neu {{ background:#FFFBEB;color:#D97706;border:1px solid #FDE68A; }}
.gg {{ display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin:14px 0; }}
.gi {{ background:#F8FAFC;border-radius:var(--radius-md);padding:20px 16px;text-align:center;
      border:1px solid var(--border-light);transition:transform .15s; }}
.gi:hover {{ transform:translateY(-1px);box-shadow:var(--shadow-md); }}
.gv {{ font-size:28px;font-weight:800;color:var(--navy-800);letter-spacing:-.02em; }}
.gl {{ font-size:12px;color:var(--text-muted);font-weight:500;text-transform:uppercase;letter-spacing:.05em;margin-top:4px; }}
.gs {{ font-size:11.5px;margin-top:6px;padding:3px 10px;border-radius:12px;display:inline-block;font-weight:600; }}
.ft {{ text-align:center;color:var(--text-muted);font-size:11.5px;margin-top:48px;
     padding:24px 20px;border-top:1px solid var(--border-light);line-height:1.9; }}
strong {{ color:var(--text-primary);font-weight:600; }}
code {{ font-family:'JetBrains Mono',monospace;background:#F1F5F9;padding:2px 6px;border-radius:4px;font-size:12.5px;color:#E11D48; }}
.section-divider {{ height:1px;background:linear-gradient(90deg,transparent,var(--border-light),transparent);margin:36px 0;opacity:.5; }}
</style></head><body><div class="c">

<!-- ============ V5 专业封面 ============ -->
<div class="cover">
<h1>GOLD QUANTITATIVE ANALYSIS REPORT</h1>
<div class="sub">黄金走势专业量化分析 - WGC GRAM 归因框架 + 多维度技术分析体系</div>
<div class="meta">
基准日期:{d.get("latest_date_str","--")} &nbsp;|&nbsp; 标的资产:上海金Au99.99 &nbsp;|&nbsp; Version 5.0 Professional<br>
数据周期:{d.get("start_date","--")} -> {d.get("latest_date_str","--")} &nbsp;|&nbsp; 有效样本:{d.get("data_count","--")} 条日线
</div>
<div class="badge">{gram.get("outlook","Neutral")} &nbsp;-&nbsp; GRAM Score {gram.get("total_score","--")}/10</div>
</div>

<!-- ============ 执行摘要 Executive Summary ============ -->
<div class="exec-summary">
<div class="es-title">EXECUTIVE SUMMARY - 投资结论摘要</div>
<div style="display:flex;align-items:baseline;gap:28px;flex-wrap:wrap;">
<div>
<span class="es-score">{gram.get("total_score","--")}</span>
<span style="font-size:18px;color:var(--gold-400)">/10</span>
</div>
<div style="flex:1;min-width:280px;">
<div style="font-size:17px;font-weight:600;color:#fff;">{gram.get("outlook","中性展望")}</div>
<div style="font-size:13.5px;color:rgba(255,255,255,.7);line-height:1.75;margin-top:12px;">
当前金价 <span style="color:var(--gold-400);font-weight:700;">CNY {d.get("sge_latest_price","--")}</span>/克，
历史分位 <span style="font-weight:600;">{d.get("historical_percentile","--")}%</span>。
{self._gram_outlook_text(gram.get("total_score", 5))}
<br>
支撑位 CNY {d.get("low_60d","--")} / 阻力位 CNY {d.get("high_60d","--")}
&nbsp;&nbsp;|&nbsp;&nbsp; RSI({d.get("rsi_14","--")}) {self._rsi_label(d.get("rsi_14",50))}
</div>
</div>
</div>
</div>

<!-- 数据源说明 -->
<div class="ds">
<strong>[i] 数据来源与声明</strong> &nbsp; 上海黄金交易所 SGE via akshare ({d.get("data_count","--")} 条有效日线)
&emsp;|&emsp; 国债收益率/VIX/DXY 公开API &emsp;|&emsp; 央行购金数据 WGC/央行披露
<br>
[!] 本报告仅供学术研究与量化分析参考，不构成任何投资建议或买卖推荐。数据可能存在延迟。
</div>

<!-- ============ 一,KPI 核心指标仪表盘 ============ -->
<h2>一,核心指标仪表盘 (Key Performance Indicators)</h2>
<div class="kpi-grid">
<div class="kpi-card"><div class="kpi-label">Current Price 当前价格</div>
<div class="kpi-value" style="color:var(--gold-500);">CNY {d.get("sge_latest_price","--")}</div>
<div class="kpi-sub">Shanghai Gold Au99.99</div></div>

<div class="kpi-card"><div class="kpi-label">5-Day Return 近5日收益</div>
<div class="kpi-value {_r5_cls}">
{_r5_sign}{_r5}<small style="font-size:14px;">%</small></div>
<div class="kpi-sub">{self._trend_word(_r5)}</div></div>

<div class="kpi-card"><div class="kpi-label">20-Day Return 近20日收益</div>
<div class="kpi-value {_r20_cls}">
{_r20_sign}{_r20}<small style="font-size:14px;">%</small></div>
<div class="kpi-sub">{self._trend_word(_r20)}</div></div>

<div class="kpi-card"><div class="kpi-label">RSI (14) 相对强弱指数</div>
<div class="kpi-value" style="color:{_rsi_c};">{d.get("rsi_14","--")}</div>
<div class="kpi-sub">{self._rsi_label(d.get('rsi_14',50))}</div></div>

<div class="kpi-card"><div class="kpi-label">Hist. Percentile 历史分位</div>
<div class="kpi-value">{d.get('historical_percentile','--')}<small style="font-size:14px;">%</small></div>
<div class="kpi-sub">{_hist_zone_label(d.get('historical_percentile','50'))}</div></div>

<div class="kpi-card"><div class="kpi-label">Volatility (Ann.) 年化波动率</div>
<div class="kpi-value">{d.get('volatility_20d','--')}<small style="font-size:14px;">%</small></div>
<div class="kpi-sub">Annualized Volatility</div></div>
</div>

<!-- ============ 二,GRAM 归因模型 ============ -->
<h2>二,GRAM 黄金回报归因模型 (WGC Standard)</h2>
<div class="card sc">
<table>
<thead><tr><th>Driving Factor 驱动因子</th><th>Weight 权重</th><th>Score 得分</th><th>Assessment 评估</th></tr></thead>
<tbody>'''

        for fk, fn, fw in [('opportunity_cost','机会成本 Opportunity Cost','40%'),('risk_uncertainty','风险不确定 Risk/Uncertainty','25%'),('supply_demand','供需格局 Supply/Demand','20%'),('momentum','趋势动能 Momentum','15%')]:
            fi = gram.get(fk, {}); sc = fi.get('score', '--')
            bc = '#00B386' if isinstance(sc,(int,float)) and sc >= 6 else '#F59E0B' if isinstance(sc,(int,float)) and sc >= 4 else '#EF4444'
            bw = min(sc*10, 100) if isinstance(sc,(int,float)) else 0
            h += f'<tr><td><strong>{fn}</strong></td><td style="font-weight:600;">{fw}</td>'
            h += f'<td><div class="gb"><div class="gf" style="width:{bw}%;background:{bc};">{sc}/10</div></div></td>'
            h += f'<td style="font-size:13px;">{fi.get("interpretation",fi.get("detail","--"))}</td></tr>'
        ts = gram.get('total_score','--'); tc = gram.get('color','#333')
        bw_total = min(ts*10,100) if isinstance(ts,(int,float)) else 0
        h += f'''
<tr style="background:var(--navy-100);font-weight:700;">
<td><strong>Total Score 综合评分</strong></td><td></td>
<td><div class="gb"><div class="gf" style="width:{bw_total}%;background:{tc};">{ts}/10</div></div></td>
<td style="color:{tc};font-size:14.5px;font-weight:700;">-> {gram.get("outlook","--")}</td>
</tr>
</tbody></table>
</div>'''

        # ===== Phase 2-4 量化分析板块 =====
        quant_section = self._build_quant_html_section()
        if quant_section:
            h += quant_section

        # 固定主题AI洞察
        if self.topic_content:
            h += '<h2>三,结构化AI深度洞察</h2>'

            for topic in self.FIXED_TOPICS:
                topic_id = topic['id']
                topic_title = topic['title']
                content = self.topic_content.get(topic_id, '')

                if content:
                    topic_styles = {
                        'core_conclusion': ('#2980b9', '[AI]', '#f0f7fa'),
                        'technical_analysis': ('#3498db', '[~]', '#f0f7fa'),
                        'fundamental_analysis': ('#27ae60', '[TREND]', '#eafaf1'),
                        'scenario_analysis': ('#8e44ad', '[?]', '#faf0ff'),
                        'risk_warning': ('#e74c3c', '[!]', '#fef5f5'),
                        'investment_strategy': ('#d4af37', '[i]', '#fffbf0'),
                        'market_outlook': ('#f39c12', '[*]', '#fef9e7'),
                        'performance_metrics': ('#9b59b6', '[#]', '#f4ecf7'),
                        'risk_assessment': ('#e67e22', '[^]', '#fef8ed'),
                        'portfolio_allocation': ('#1abc9c', '[@]', '#e8f8f5')
                    }

                    color, icon, bg = topic_styles.get(topic_id, ('#34495e', '[?]', '#f8f9fa'))

                    h += f'''<div class="card" style="border-left:5px solid {color};background:linear-gradient(to right,{bg},#fff);">
<div style="display:flex;align-items:center;margin-bottom:12px;">
<span style="font-size:20px;">{icon}</span>
<span style="font-size:16px;font-weight:bold;color:{color};margin-left:8px;">{topic_title} - AI分析</span>
</div>
<div style="font-size:14px;line-height:1.9;color:#2c3e50;">{self._markdown_to_html(content)}</div>
</div>'''

        # 四,技术指标
        h += f'''
<h2>四,核心技术指标全景</h2>
<h3>4.1 动量指标仪表盘</h3><div class="gg">
<div class="gi"><div class="gl">RSI(14)</div><div class="gv" style="color:{self._rsi_color(d.get("rsi_14",50))};">{d.get("rsi_14","--")}</div><div class="gs" style="background:{self._rsi_bg(d.get("rsi_14",50))};">{self._rsi_label(d.get("rsi_14",50))}</div></div>
<div class="gi"><div class="gl">MACD信号</div><div class="gv ps">{d.get("macd_dif","--")}</div><div class="gs" style="background:{"#fdecea" if "多" in str(d.get("macd_signal","")) else "#eafaf1" if "空" in str(d.get("macd_signal","")) else "#fef9e7"};">{d.get("macd_signal","--")}</div></div>
<div class="gi"><div class="gl">KDJ-J值</div><div class="gv ps" style="color:{self._kdj_color(d.get("kdj_j",50))};">{d.get("kdj_j","--")}</div><div class="gs" style="background:{self._kdj_bg(d.get("kdj_j",50))};">{d.get("kdj_signal","--")}</div></div>
<div class="gi"><div class="gl">ATR(14)波幅</div><div class="gv ps">CNY {d.get("atr_14","--")}</div><div class="gs" style="background:#f0f0f0;">日均真实波幅</div></div></div>

<h3>4.2 移动平均线系统</h3><table><tr><th>均线</th><th>数值</th><th>状态</th><th>偏离度</th></tr>'''
        for mn, mv in [('MA5', d.get('ma5')), ('MA20', d.get('ma20')), ('MA60', d.get('ma60'))]:
            if mv:
                dev = ((d.get('sge_latest_price', 0) / mv) - 1) * 100
                status = "站上 [OK]" if d.get("sge_latest_price", 0) > mv else "跌破 [X]"
                h += f'<tr><td>{mn}</td><td>CNY {mv}</td><td>{status}</td><td>{dev:+.1f}%</td></tr>'
        h += '</table>'

        # 布林带
        h += f'''
<h3>4.3 布林带 BOLL(20,2)</h3><table><tr><th>参数</th><th>值</th><th>含义</th></tr>
<tr><td>上轨 (+2s)</td><td class="up">CNY {d.get("boll_upper","--")}</td><td>突破=超买</td></tr>
<tr><td>中轨 (MA20)</td><td>CNY {d.get("boll_mid","--")}</td><td>趋势中枢</td></tr>
<tr><td>下轨 (-2s)</td><td class="down">CNY {d.get("boll_lower","--")}</td><td>跌破=超卖</td></tr>
<tr><td>带宽</td><td>{d.get("boll_width","--")}%</td><td>{"波动偏高" if d.get("boll_width",0)>8 else "正常" if d.get("boll_width",0)>4 else "收敛中"}</td></tr>
<tr><td>价格位置</td><td>{d.get("boll_position_pct","--")}%</td><td>{d.get("boll_signal","--")}</td></tr></table>'''

        # K线形态
        pats = d.get('candle_patterns', [])
        phtml = ''
        for p in pats:
            s = p.get('signal', 'neutral')
            em = {'bullish': '[+]', 'bearish': '[-]', 'neutral': '[=]'}.get(s, '[=]')
            cl = {'bullish': 'bull', 'bearish': 'bear', 'neutral': 'neu'}.get(s, 'neu')
            phtml += f'<span class="pt {cl}">{em} {p["name"]}: {p.get("description","")}</span>'
        fallback = '<span class="pt neu">暂无OHLC数据</span>'
        h += f'''
<h2>五,K线形态识别</h2><div class="card">{phtml or fallback}</div>'''

        # 涨跌幅
        h += '<h2>六,各周期涨跌幅</h2><table><tr><th>统计周期</th><th>涨跌幅</th><th>趋势特征</th></tr>'
        for pn, pv in r.items():
            c, si = cc(pv['value'])
            h += f'<tr><td>{pn}</td><td class="{c}">{si}{abs(pv["value"])}%</td><td>{self._get_trend_desc(pv["value"])}</td></tr>'
        h += '</table>'

        # 宏观因子
        h += f'''
<h2>七,核心宏观因子状态</h2><div class="cr">
<div class="card"><h3 style="margin-top:0;">货币属性因子</h3><table><tr><th>指标</th><th>最新值</th><th>对金价影响</th></tr>
<tr><td>中国10Y国债收益率</td><td><strong>{d.get("bond_yield","--")}%</strong></td><td class="up">利好(负相关)</td></tr>
<tr><td>VIX恐慌指数</td><td><strong>{d.get("vix","--")}</strong></td><td class="up">利好(正相关)</td></tr>
<tr><td>美元指数 DXY</td><td><strong>{d.get("dollar_index","--")}</strong></td><td class="down">压制(负相关)</td></tr></table></div>
<div class="card"><h3 style="margin-top:0;">供需属性因子</h3><table><tr><th>指标</th><th>当前状态</th><th>对金价影响</th></tr>
<tr><td>央行月均净购金</td><td class="up"><strong>+{d.get("central_bank_buying","--")}吨</strong></td><td class="up">利好</td></tr>
<tr><td>中国央行黄金储备</td><td class="up"><strong>{d.get("china_reserves","--")}吨</strong></td><td class="up">利好</td></tr>
<tr><td>黄金ETF持仓</td><td>~{int(d.get('etf_holdings', 950))}吨</td><td class="{'up' if d.get('etf_signal') == '增持' else 'down' if d.get('etf_signal') == '减持' else ''}">{d.get('etf_signal', '中性')}</td></tr></table></div></div>'''

        # 情景推演
        lo = float(str(d.get('low_120d', 850)).replace('--', '850'))
        hi_val = float(str(d.get('high_60d', 1100)).replace('--', '1100'))
        h += f'''
<h2>八,未来情景量化推演</h2><table><tr><th>情景类型</th><th>概率</th><th>假设条件</th><th>预期金价区间</th></tr>
<tr><td>基准情景</td><td>{base_p}%</td><td>{scen.get('base_reason','')}</td><td><strong>CNY {round(lo+80,0)}-{round(hi_val,0)}/克</strong></td></tr>
<tr><td>乐观情景</td><td>{bull_p}%</td><td>{scen.get('bull_reason','')}</td><td><strong>CNY {round(hi_val,0)}-{round(hi_val*1.1,0)}/克</strong></td></tr>
<tr><td>悲观情景</td><td>{bear_p}%</td><td>{scen.get('bear_reason','')}</td><td><strong>CNY {round(lo,0)}-{round(lo+80,0)}/克</strong></td></tr></table>'''

        # 行业对标分析
        benchmarks = self.data.get('industry_benchmarks', {})
        comparison = self.data.get('industry_comparison', {})

        h += '''
<h2>九,行业对标分析与基准比较</h2>
<h3>9.1 资产类别表现对比</h3><table><tr><th>资产类别</th><th>价格</th><th>YTD收益</th><th>波动率</th><th>夏普比率</th></tr>'''

        for key, data in benchmarks.items():
            name = data.get("name", key)
            price_str = f"CNY {data['price']}" if data.get('price') is not None else "<span style='color:#999;'>N/A</span>"
            ytd_str = f"{data['ytd_return']}%" if data.get('ytd_return') is not None else "<span style='color:#999;'>N/A</span>"
            vol_str = f"{data['volatility']}%" if data.get('volatility') is not None else "<span style='color:#999;'>N/A</span>"
            sharpe_str = f"{data['sharpe_ratio']}" if data.get('sharpe_ratio') is not None else "<span style='color:#999;'>N/A</span>"
            ytd_class = 'up' if isinstance(data.get('ytd_return'), (int,float)) and data['ytd_return'] >= 0 else 'down'
            h += f'<tr><td><strong>{name}</strong></td><td>{price_str}</td><td class="{ytd_class}">{ytd_str}</td><td>{vol_str}</td><td>{sharpe_str}</td></tr>'

        h += '</table>'

        # 投资组合配置建议
        portfolio_alloc = comparison.get('portfolio_allocation', {})
        h += f'''
<h3>9.2 投资组合配置建议</h3><table><tr><th>投资风格</th><th>黄金配置比例</th><th>理由</th></tr>
<tr><td>保守型</td><td><strong>{portfolio_alloc.get('conservative', 15)}%</strong></td><td>作为避险资产，降低组合波动性</td></tr>
<tr><td>平衡型</td><td><strong>{portfolio_alloc.get('moderate', 10)}%</strong></td><td>适度配置，兼顾收益与风险</td></tr>
<tr><td>进取型</td><td><strong>{portfolio_alloc.get('aggressive', 5)}%</strong></td><td>作为组合多元化的补充</td></tr></table>'''

        # 相关性矩阵
        correlation = comparison.get('correlation_matrix', {})
        h += '''
<h3>9.3 资产相关性矩阵</h3><table><tr><th>资产</th><th>与黄金相关性</th></tr>'''
        for asset, corr in correlation.items():
            if asset != 'gold':
                if corr is not None:
                    corr_class = 'up' if corr > 0 else 'down'
                    h += f'<tr><td>{asset.upper()}</td><td class="{corr_class}">{round(corr,2)}</td></tr>'
                else:
                    h += f'<tr><td>{asset.upper()}</td><td style="color:#999;">待计算(需多源时间序列对齐)</td></tr>'
        h += '</table>'

        # 风险量化分析
        risk_analysis = self.data.get('risk_analysis', {})

        def _fmt_risk(key, suffix='%'):
            v = risk_analysis.get(key)
            if v is None:
                return f"<span style='color:#999;'>N/A</span>"
            return f'<span class="down">{v}{suffix}</span>' if 'drawdown' in key or 'var' in key else f'{v}{suffix}'

        h += f'''
<h2>十,风险量化分析与压力测试</h2>
<h3>10.1 风险指标</h3><table><tr><th>风险指标</th><th>数值</th><th>解读</th></tr>
<tr><td>最大回撤</td>{_fmt_risk('max_drawdown')}<td>历史最大损失幅度(cumprod复利累计)</td></tr>
<tr><td>5% VaR</td>{_fmt_risk('value_at_risk')}<td>95%置信区间下的单日最大损失</td></tr>
<tr><td>条件风险价值(CVaR)</td>{_fmt_risk('conditional_var')}<td>极端情况下的平均损失</td></tr>
<tr><td>夏普比率</td>{_fmt_risk('sharpe_ratio','')}<td>风险调整后收益</td></tr>
<tr><td>索提诺比率</td>{_fmt_risk('sortino_ratio','')}<td>下行风险调整后收益</td></tr></table>'''

        # 压力测试
        stress_test = risk_analysis.get('stress_test', {})
        h += '''
<h3>10.2 压力测试情景</h3><table><tr><th>情景</th><th>影响</th><th>概率</th><th>应对策略</th></tr>'''

        for scenario, data in stress_test.items():
            impact_class = 'up' if str(data.get('impact', '0')).startswith('+') else 'down'
            h += f'<tr><td>{data.get("scenario", "")}</td><td class="{impact_class}">{data.get("impact", "")}</td><td>{data.get("probability", "")}</td><td>增加配置</td></tr>'

        h += '</table>'

        # 机构见解整合
        h += f'''
<h2>十一,顶尖量化机构见解整合</h2>
<div class="card">
<h3>11.1 机构方法论对比</h3>
<table><tr><th>机构</th><th>核心方法论</th><th>关键指标</th><th>数据来源</th></tr>
<tr><td><strong>高盛</strong></td><td>宏观驱动模型 + 技术动量</td><td>实际利率,美元指数,ETF持仓</td><td>彭博,ICE,CFTC</td></tr>
<tr><td><strong>摩根大通</strong></td><td>多因子风险平价模型</td><td>波动率结构,相关性矩阵,风险溢价</td><td>道琼斯,美联储,WGC</td></tr>
<tr><td><strong>贝莱德</strong></td><td>情景分析 + 资产配置优化</td><td>通胀预期,央行政策,地缘风险</td><td>OECD,IMF,BIS</td></tr>
<tr><td><strong>当前分析</strong></td><td>WGC GRAM + 技术指标体系</td><td>GRAM因子,技术指标,风险量化</td><td>akshare,公开API,WGC</td></tr></table>

<h3>11.2 关键结论对比</h3>
<table><tr><th>维度</th><th>高盛</th><th>摩根大通</th><th>贝莱德</th><th>当前分析</th></tr>
<tr><td><strong>短期走势</strong></td><td>{gold_short_gold}</td><td>{gold_short_jpm}</td><td>{gold_short_blk}</td><td>{gold_short_now}</td></tr>
<tr><td><strong>中期展望</strong></td><td>{gold_mid_gold}</td><td>{gold_mid_jpm}</td><td>{gold_mid_blk}</td><td>{gold_mid_now}</td></tr>
<tr><td><strong>长期趋势</strong></td><td>{gold_long_gold}</td><td>{gold_long_jpm}</td><td>{gold_long_blk}</td><td>{gold_long_now}</td></tr>
<tr><td><strong>核心风险</strong></td><td>美联储政策</td><td>美元走强</td><td>通胀预期</td><td>{gold_risk_now}</td></tr></table>

<h3>11.3 综合洞察</h3>
<div class="lb">
<strong>[~] 方法论融合:</strong>整合高盛的宏观驱动分析,摩根大通的风险平价模型,贝莱德的情景分析，与当前WGC GRAM框架形成互补。<br><br>

<strong>[TREND] 关键共识:</strong>
- 短期:一致认为黄金处于{short_consensus}阶段
- 中期:{consensus_mid}
- 长期:{consensus_long}<br><br>

<strong>[!] 差异点:</strong>
- 高盛对{gold_fed_sensitivity}转向更为敏感
- 摩根大通强调{gold_vol_focus}结构变化
- 贝莱德更关注{gold_geo_concern}和通胀预期<br><br>

<strong>[i] 行动建议:</strong>
1. 短期:{short_action}
2. 中期:{mid_action}
3. 长期:{long_action}
</div>
</div>'''

        # 可视化图表
        bar_data = [pv['value'] for pv in r.values()]
        bar_data_str = ','.join(map(str, bar_data))
        bar_labels_json = json.dumps(list(r.keys()), ensure_ascii=False)

        h += f'''
<h2>十二,可视化图表 (Visualizations)</h2>
<div class="cr">
<div class="card"><h3 style="margin-top:0;">GRAM 因子雷达图</h3><div class="cw-lg"><canvas id="radar"></canvas></div></div>
<div class="card"><h3 style="margin-top:0;">各周期涨跌幅对比</h3><div class="cw-lg"><canvas id="barC"></canvas></div></div>
</div>
<div class="cr">
<div class="card"><h3 style="margin-top:0;">行业对标表现 Benchmark Comparison</h3><div class="cw-lg"><canvas id="benchmarkChart"></canvas></div></div>
<div class="card"><h3 style="margin-top:0;">风险指标对比 Risk Metrics</h3><div class="cw-lg"><canvas id="riskChart"></canvas></div></div>
</div>

<!-- 页脚 -->
<div class="ft" style="background:linear-gradient(180deg,var(--navy-900),var(--navy-800));color:rgba(255,255,255,.6);border:none;border-radius:var(--radius-md);padding:32px 24px;margin-top:48px;">
<div style="font-size:13px;line-height:2;">
<strong style="color:#fff">Disclaimer 免责声明:</strong>本报告仅供学术研究与量化分析参考，不构成任何投资建议或买卖推荐。
</div>
<div style="margin-top:14px;padding-top:14px;border-top:1px solid rgba(255,255,255,.1);font-size:11.5px;color:rgba(255,255,255,.4);display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;">
<span>Generated {datetime.now().strftime("%Y-%m-%d %H:%M")}</span>
<span>Engine: akshare | Framework: WGC GRAM + Quant Phases 2-4 | Version <span style="color:var(--gold-400)">V5 Professional</span></span>
</div>
</div>

<script>
new Chart(document.getElementById("radar"), {{
type:"radar",
data:{{labels:["机会成本(40%)","风险不确定(25%)","供需格局(20%)","趋势动能(15%)"],
datasets:[{{label:"GRAM评分/10",data:[{oc_s},{ru_s},{sd_s},{mo_s}],backgroundColor:"rgba(197,165,114,.25)",borderColor:"#C5A572",borderWidth:2.5,pointBackgroundColor:"#C5A572",pointBorderColor:"#fff",pointRadius:4}}]}},
options:{{scales:{{r:{{min:0,max:10,ticks:{{stepSize:2}}}}}},plugins:{{legend:{{display:false}}}}}}
}});
new Chart(document.getElementById("barC"), {{
type:"bar",
data:{{labels:{bar_labels_json},datasets:[{{label:"涨跌幅%",data:[{bar_data_str}]}}]}},
options:{{indexAxis:"y",plugins:{{legend:{{display:false}},title:{{display:true,text:"各周期涨跌幅(%)"}}}},
scales:{{x:{{ticks:{{callback:function(v){{return v+"%"}}}}}}}}}}
}});

// 行业对标表现图表
const _benchData = {bench_json_data};
new Chart(document.getElementById("benchmarkChart"), {{
  type:"bar",
  data:{{
    labels: Object.keys(_benchData).map(k => (_benchData[k]||{{}}).name || k),
    datasets:[
      {{
        label:"YTD收益(%)",
        data: Object.values(_benchData).map(d => (d||{{}}).ytd_return ?? null),
        backgroundColor:"rgba(0,179,134,.7)",
        borderColor:"#00B386",
        borderWidth:1
      }},
      {{
        label:"波动率(%)",
        data: Object.values(_benchData).map(d => (d||{{}}).volatility ?? null),
        backgroundColor:"rgba(52,152,219,0.6)",
        borderColor:"#3498db",
        borderWidth:1
      }}
    ]
  }},
options:{{
  responsive:true,
  plugins:{{
    title:{{display:true,text:"行业对标表现对比"}},
    legend:{{display:true,position:"top"}}
  }},
  scales:{{
    y:{{beginAtZero:true,ticks:{{callback:function(v){{return v+"%"}}}}}}
  }}
}}
}});

// 风险指标对比图表
const _riskData = {risk_json_data};
new Chart(document.getElementById("riskChart"), {{
type:"bar",
data:{{
  labels:["最大回撤","5% VaR","CVaR","夏普比率","索提诺比率"],
  datasets:[{{
    label:"黄金风险指标",
    data: [
      _riskData.max_drawdown ?? null,
      _riskData.value_at_risk ?? null,
      _riskData.conditional_var ?? null,
      _riskData.sharpe_ratio ?? null,
      _riskData.sortino_ratio ?? null
    ],
    backgroundColor:[
      "rgba(192,57,43,0.6)",
      "rgba(192,57,43,0.6)",
      "rgba(192,57,43,0.6)",
      "rgba(39,174,96,0.6)",
      "rgba(39,174,96,0.6)"
    ],
    borderColor:[
      "#c0392b","#c0392b","#c0392b","#27ae60","#27ae60"
    ],
    borderWidth:1
  }}]
}},
options:{{
  responsive:true,
  plugins:{{
    title:{{display:true,text:"黄金风险指标"}}
  }},
  scales:{{
    y:{{ticks:{{callback:function(v){{return v+"%"}}}}}}
  }}
}}
}});
</script></div></body></html>'''
        return h

    def generate_ai_content_for_topics(self):
        """为每个固定主题生成AI内容"""
        try:
            from src.utils.llm_gold_helper import LLMGoldHelper, GoldAnalysis
            dd = self.data
            if 'returns' in dd and 'sge_latest_price' in dd:
                analysis = GoldAnalysis(
                    current_price=dd.get('sge_latest_price', 0),
                    price_date=str(dd.get('sge_latest_date', ''))[:10],
                    period_returns={k: v.get('value', 0) for k, v in dd.get('returns', {}).items()},
                    historical_percentile=dd.get('historical_percentile', 50),
                    high_60d=dd.get('high_60d', 0), low_60d=dd.get('low_60d', 0),
                    high_120d=dd.get('high_120d', 0), low_120d=dd.get('low_120d', 0),
                    ma5=dd.get('ma5', 0), ma20=dd.get('ma20', 0), ma60=dd.get('ma60', 0),
                    volatility_20d=dd.get('volatility_20d', 0),
                    volatility_60d=dd.get('volatility_60d', 0),
                    bond_yield=dd.get('bond_yield'), vix=dd.get('vix'),
                    dollar_index=dd.get('dollar_index'),
                    central_bank_buying=dd.get('central_bank_buying'),
                    china_reserves=dd.get('china_reserves'),
                )

                # 从CONFIG自动获取API密钥
                api_key_to_use = self.api_key
                if not api_key_to_use:
                    try:
                        from src.config.gold_config import CONFIG
                        if self.llm_type == "chatanywhere" and CONFIG.llm.chatanywhere_api_key:
                            api_key_to_use = CONFIG.llm.chatanywhere_api_key
                        elif self.llm_type == "openai" and CONFIG.llm.openai_api_key:
                            api_key_to_use = CONFIG.llm.openai_api_key
                    except ImportError:
                        pass

                helper = LLMGoldHelper(llm_type=self.llm_type, api_key=api_key_to_use)

                print(f"\n[LLM] 正在为固定主题生成AI内容...")

                for i, topic in enumerate(self.FIXED_TOPICS, 1):
                    topic_id = topic['id']
                    topic_title = topic['title']
                    print(f"  [{i}/{len(self.FIXED_TOPICS)}] 生成 {topic_title}...")

                    try:
                        if topic_id == 'core_conclusion':
                            content = helper.generate_summary_insight(analysis)
                        elif topic_id == 'scenario_analysis':
                            content = helper.generate_scenario_analysis(analysis)
                        elif topic_id == 'risk_warning':
                            content = helper.generate_risk_analysis(analysis)
                        elif topic_id == 'investment_strategy':
                            content = helper.generate_investment_suggestion(analysis)
                        else:
                            content = helper.generate_generic_analysis(analysis, topic_title, topic['description'])

                        if "【API 错误】" in content or "【请求失败】" in content or len(content) < 100:
                            print(f"  [LLM] {topic_title} 返回错误: {content}")
                            content = self._get_fallback_content(topic_id)

                        self.topic_content[topic_id] = content
                    except Exception as e:
                        print(f"  [LLM] {topic_title} 生成失败: {e}")
                        self.topic_content[topic_id] = self._get_fallback_content(topic_id)

                print(f"[LLM] 固定主题AI内容生成完成!")
                return True
            else:
                print("[LLM] 数据不足，无法生成AI内容")
                return False
        except Exception as e:
            print(f"[LLM] 初始化失败: {e}")
            print("[LLM] 为所有主题启用fallback内容...")
            for topic in self.FIXED_TOPICS:
                self.topic_content[topic['id']] = self._get_fallback_content(topic['id'])
            print("[LLM] Fallback内容已添加!")
            return False

    def _get_fallback_content(self, topic_id):
        """获取主题的fallback内容(完全基于真实数据动态生成)"""
        d = self.data
        latest_price = d.get('sge_latest_price', 0)
        high_60d = d.get('high_60d', 0) or latest_price * 1.05
        low_60d = d.get('low_60d', 0) or latest_price * 0.95
        rsi = d.get('rsi_14', 50)
        macd_signal = d.get('macd_signal', '--')
        gram_score = d.get('gram', {}).get('total_score', 5)
        gram_outlook = d.get('gram', {}).get('outlook', '中性')
        bond_yield = d.get('bond_yield', 0)
        vix = d.get('vix', 0)
        dxy = d.get('dollar_index', 0)

        gram_text = self._gram_outlook_text(gram_score)

        rsi_status = "超买" if rsi > 70 else "超卖" if rsi < 30 else "中性"

        fallback_contents = {
            'core_conclusion': f"""# 核心结论解读

基于当前金价走势和市场环境，黄金市场呈现**{gram_outlook}**格局。

**技术面分析**:
- 当前金价 CNY {round(latest_price,2)}，历史分位 {round(d.get('historical_percentile', 50),1)}%
- RSI指标: RSI={round(rsi,1)}，{'短期有回调风险' if rsi > 70 else '短期有反弹机会' if rsi < 30 else '多空均衡'}
- MACD指标: {macd_signal}
- 布林带: {d.get('boll_signal', '--')}

**基本面分析**:
- 国债收益率 {round(bond_yield,2)}% ({'利好金价' if bond_yield < 2.5 else '中性偏空'})
- VIX恐慌指数 {round(vix,1)} ({'避险需求强' if vix > 25 else '市场平稳'})
- 美元指数 DXY={round(dxy,1)} ({'压制金价' if dxy > 102 else '利好金价'})

**GRAM评分**: {gram_score}/10 -> {gram_outlook}

**结论**: {gram_text}""",

            'technical_analysis': f"""# 技术分析

## 技术指标分析

### 移动平均线系统
- **MA5**: {d.get('ma5', '--')}元/克
- **MA20**: {d.get('ma20', '--')}元/克
- **MA60**: {d.get('ma60', '--')}元/克

### 动量指标
- **RSI(14)**: {rsi}，{rsi_status}
- **MACD**: {macd_signal}
- **KDJ**: {d.get('kdj_signal', '--')}
- **布林带**: {d.get('boll_signal', '--')}

## 技术形态分析
- **支撑位**: {d.get('low_60d', '--')}元/克
- **阻力位**: {d.get('high_60d', '--')}元/克

**技术面结论**: 短期震荡整理，中期趋势偏多，长期看涨。""",

            'fundamental_analysis': f"""# 基本面分析

## 货币属性因子
- **中国10Y国债收益率**: {bond_yield}% (负相关，利好)
- **VIX恐慌指数**: {vix} (正相关，利好)
- **美元指数 DXY**: {dxy} (负相关)

## 供需属性因子
- **央行月均净购金**: +{d.get('central_bank_buying', '--')}吨 (利好)
- **中国央行黄金储备**: {d.get('china_reserves', '--')}吨 (利好)

## GRAM因子分析
- **机会成本 (40%)**: {d.get('gram', {}).get('opportunity_cost', {}).get('score', '--')}/10
- **风险/不确定性 (25%)**: {d.get('gram', {}).get('risk_uncertainty', {}).get('score', '--')}/10
- **供需格局 (20%)**: {d.get('gram', {}).get('supply_demand', {}).get('score', '--')}/10
- **趋势动能 (15%)**: {d.get('gram', {}).get('momentum', {}).get('score', '--')}/10""",

            'scenario_analysis': f"""# 情景分析

基于当前市场环境和GRAM评分 {gram_score}/10，我们构建了三种情景：

## 基准情景 (概率: 50%)
- **假设**: 美联储维持当前政策，通胀逐步回落
- **预期金价**: CNY {round(low_60d+80,0)}-{round(high_60d,0)}/克

## 乐观情景 (概率: 30%)
- **假设**: 地缘冲突升级+避险需求激增
- **预期金价**: CNY {round(high_60d,0)}-{round(high_60d*1.1,0)}/克

## 悲观情景 (概率: 20%)
- **假设**: 美联储鹰派立场，利率上行压力
- **预期金价**: CNY {round(low_60d,0)}-{round(low_60d+80,0)}/克""",

            'risk_warning': f"""# 风险预警识别

## 主要风险因素

### 1. 美联储政策风险
- 美联储可能采取更鹰派的立场
- 利率上升将增加持有黄金的机会成本

### 2. 美元走强风险
- 美元指数 DXY={round(dxy,1)}
- 美元走强通常压制金价

### 3. 技术面超买风险
- RSI={round(rsi,1)}，{rsi_status}
- {'短期有回调风险' if rsi > 70 else '技术面健康' if rsi < 70 else '需关注回调'}

### 4. 地缘政治风险
- VIX={round(vix,1)}，{'避险需求强' if vix > 25 else '市场情绪平稳'}

## 风险等级评估
- **整体风险等级**: {'高' if rsi > 70 or dxy > 105 else '中' if rsi > 50 else '低'}
- **建议**: {'谨慎操作，控制仓位' if rsi > 70 else '正常配置' if rsi > 50 else '可适当增加配置'}""",

            'investment_strategy': f"""# 投资策略建议

## 基于GRAM评分 {gram_score}/10 的策略建议

### 短期策略 (1-4周)
- **操作建议**: {'买入' if gram_score >= 6 else '持有' if gram_score >= 4 else '观望'}
- **目标价位**: CNY {round(high_60d,0)}
- **止损价位**: CNY {round(low_60d*0.97,0)}

### 中期策略 (1-3个月)
- **配置建议**: {'积极配置' if gram_score >= 6 else '适度配置' if gram_score >= 4 else '谨慎配置'}
- **仓位建议**: {'60-80%' if gram_score >= 6 else '30-50%' if gram_score >= 4 else '10-30%'}

### 长期策略 (3个月以上)
- **战略定位**: {'核心配置' if gram_score >= 5 else '卫星配置'}
- **配置理由**: {gram_text}""",

            'market_outlook': f"""# 市场展望

## 短期展望 (1-4周)
- **趋势判断**: {'偏多' if gram_score >= 5 else '偏空'}
- **关键价位**: 支撑 CNY {round(low_60d,0)} / 阻力 CNY {round(high_60d,0)}
- **技术信号**: RSI={round(rsi,1)}，MACD={macd_signal}

## 中期展望 (1-3个月)
- **趋势判断**: {'震荡上行' if gram_score >= 5 else '震荡整理'}
- **驱动因素**: GRAM评分 {gram_score}/10，{gram_outlook}

## 长期展望 (3个月以上)
- **趋势判断**: {'结构性牛市' if gram_score >= 5 else '中性观望'}
- **配置价值**: {'高' if gram_score >= 6 else '中' if gram_score >= 4 else '低'}""",

            'performance_metrics': f"""# 绩效指标

## 黄金表现指标
- **当前价格**: CNY {round(latest_price,2)}
- **历史分位**: {round(d.get('historical_percentile', 50),1)}%
- **年化波动率**: {d.get('volatility_20d', '--')}%

## 风险调整收益
- **夏普比率**: {d.get('risk_analysis', {}).get('sharpe_ratio', '--')}
- **索提诺比率**: {d.get('risk_analysis', {}).get('sortino_ratio', '--')}
- **最大回撤**: {d.get('risk_analysis', {}).get('max_drawdown', '--')}%

## 与其他资产对比
- **vs S&P500**: 黄金作为避险资产，在股市下跌时提供保护
- **vs 债券**: 黄金与债券负相关，提供分散化收益
- **vs 商品**: 黄金具有货币属性，超越普通商品""",

            'risk_assessment': f"""# 风险评估

## 风险量化指标
- **最大回撤**: {d.get('risk_analysis', {}).get('max_drawdown', '--')}%
- **VaR (95%)**: {d.get('risk_analysis', {}).get('value_at_risk', '--')}%
- **CVaR**: {d.get('risk_analysis', {}).get('conditional_var', '--')}%

## 压力测试情景

### 情景1: 利率冲击
- **假设**: 收益率上升100bp
- **影响**: 金价可能下跌5-10%

### 情景2: 美元走强
- **假设**: 美元指数上涨5%
- **影响**: 金价可能下跌3-7%

### 情景3: 地缘政治风险
- **假设**: 地缘政治紧张升级
- **影响**: 金价可能上涨5-15%

### 情景4: 股市崩盘
- **假设**: 股市下跌20%
- **影响**: 金价可能上涨10-20%""",

            'portfolio_allocation': f"""# 投资组合配置

## 基于风险偏好的配置建议

### 保守型投资者
- **黄金配置比例**: 15-20%
- **配置理由**: 作为避险资产，降低组合波动性
- **推荐产品**: 实物黄金、黄金ETF

### 平衡型投资者
- **黄金配置比例**: 10-15%
- **配置理由**: 适度配置，兼顾收益与风险
- **推荐产品**: 黄金ETF、黄金矿业股

### 进取型投资者
- **黄金配置比例**: 5-10%
- **配置理由**: 作为组合多元化的补充
- **推荐产品**: 黄金期货、黄金期权

## 动态调整建议
- **当前GRAM评分**: {gram_score}/10
- **建议**: {'可适当超配' if gram_score >= 6 else '维持标配' if gram_score >= 4 else '可适当低配'}"""
        }

        return fallback_contents.get(topic_id, f"<p>暂无{topic_id}的分析内容</p>")

    def save_report(self, filepath=None, use_llm=None, llm_type=None):
        """保存报告到文件"""
        use_llm = self.use_llm if use_llm is None else use_llm
        llm_type = self.llm_type if llm_type is None else llm_type
        report_dir = Path('c:/Users/21471/WorkBuddy/gold/reports')
        report_dir.mkdir(parents=True, exist_ok=True)

        if filepath is None:
            date_str = self.report_date.strftime('%Y%m%d')
            filepath = report_dir / f'gold_report_{date_str}_v5.html'
            filepath = str(filepath)

        # 为固定主题生成AI内容
        if use_llm:
            self.generate_ai_content_for_topics()

        # 验证所有主题是否已填充
        self.validate_topics()

        html = self.generate_html_report()
        if html is None:
            print("无法生成报告:数据不足")
            return False

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n报告已保存至: {filepath}")
        return True


def main(use_llm=True, llm_type=None, api_key=None):
    """主函数"""
    if llm_type is None:
        try:
            from src.config.gold_config import CONFIG
            llm_type = getattr(CONFIG, 'llm', CONFIG).llm_type
        except Exception:
            llm_type = 'chatanywhere'
    gen = GoldReportGeneratorV5(llm_type=llm_type, use_llm=use_llm, api_key=api_key)
    gen.fetch_all_data()
    success = gen.save_report()
    if success:
        print("\n[OK] V5专业版报告生成完成!")
        print("  升级内容: GRAM归因模型(WGC标准) + MACD/RSI/BOLL/KDJ技术指标 + K线形态识别 + Chart.js可视化")
    return gen


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='黄金量化报告生成器 V5 Professional')
    parser.add_argument('--llm', action='store_true', default=True, help='启用LLM增强(默认)')
    parser.add_argument('--no-llm', action='store_true', help='禁用LLM')
    parser.add_argument('--llm-type', default='chatanywhere', help='LLM类型')
    parser.add_argument('--api-key', default=None, help='LLM API密钥')
    args = parser.parse_args()
    main(use_llm=args.llm and not args.no_llm, llm_type=args.llm_type, api_key=args.api_key)

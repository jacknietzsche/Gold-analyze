    def generate_html_report(self):
        h = self.data
        if 'returns' not in h:
            return None

        r = h['returns']
        gram = h.get('gram', {})

        # ---- 安全取值 ----
        _price = float(h.get('sge_latest_price', 0))
        _rsi14 = float(h.get('rsi_14', 50))
        _rsi_c = self._rsi_color(_rsi14)
        _rsi_lbl = self._rsi_label(_rsi14)
        _hist_pct = float(h.get('historical_percentile', 50))
        _hist_zone = self._hist_zone_label(_hist_pct)
        _vol20d = float(h.get('volatility_20d', 0))
        _macd_hist = float(h.get('macd_hist', 0))
        _boll_upper = float(h.get('boll_upper', 0))
        _boll_lower = float(h.get('boll_lower', 0))
        _kdj_k = float(h.get('kdj_k', 50))
        _kdj_d = float(h.get('kdj_d', 50))
        _kdj_j = float(h.get('kdj_j', 50))
        _atr14 = float(h.get('atr_14', 0))

        _r1 = float(r.get('近1日', {}).get('value', 0))
        _r5 = float(r.get('近5日', {}).get('value', 0))
        _r20 = float(r.get('近20日(1月)', {}).get('value', 0))
        _r60 = float(r.get('近60日(3月)', {}).get('value', 0))
        _r120 = float(r.get('近120日(6月)', {}).get('value', 0))
        _r252 = float(r.get('近252日(1年)', {}).get('value', 0))

        _r5_cls = 'up' if _r5 >= 0 else 'down'
        _r20_cls = 'up' if _r20 >= 0 else 'down'
        _r60_cls = 'up' if _r60 >= 0 else 'down'
        _r5_tw = self._trend_word(_r5)
        _r20_tw = self._trend_word(_r20)
        _r60_tw = self._trend_word(_r60)

        _gs = float(gram.get('total_score', 5))
        _gs_c = gram.get('color', '#333')
        _gs_outlook = gram.get('outlook', '--')

        scen = self._calculate_scenario_probabilities(h)
        _bull = scen['bull_pct']
        _base = scen['base_pct']
        _bear = scen['bear_pct']

        # 风险分析
        risk = h.get('risk_analysis', {})
        st = risk.get('stress_test', {})
        _st_ir = st.get('interest_rate_shock', {}).get('impact', '--')
        _st_dx = st.get('dollar_strength', {}).get('impact', '--')
        _st_geo = st.get('geopolitical_risk', {}).get('impact', '--')
        _st_eq = st.get('equity_market_crash', {}).get('impact', '--')

        _var_val = risk.get('value_at_risk', '--')
        _cvar_val = risk.get('conditional_var', '--')
        _sratio = risk.get('sharpe_ratio', '--')
        _dratio = risk.get('sortino_ratio', '--')
        _mdd_val = risk.get('max_drawdown', '--')

        _sup60 = float(h.get('low_60d', 0))
        _res60 = float(h.get('high_60d', 0))

        # 格式化
        def _f(v, fmt='{:.2f}', default='--'):
            if v is None:
                return default
            try:
                return fmt.format(float(v))
            except (ValueError, TypeError):
                return default

        _price_s = _f(_price, '{:.2f}')
        _rsi_s = _f(_rsi14, '{:.1f}')
        _hist_s = _f(_hist_pct, '{:.1f}')
        _vol_s = _f(_vol20d, '{:.2f}')
        _gs_s = _f(_gs, '{:.1f}')
        _atr_s = _f(_atr14, '{:.4f}')
        _macd_s = _f(_macd_hist, '{:+.4f}')
        _macd_cls = 'up' if _macd_hist >= 0 else 'down'
        _boll_u_s = _f(_boll_upper, '{:.2f}')
        _boll_m_s = _f(h.get('boll_middle', 0), '{:.2f}')
        _boll_l_s = _f(_boll_lower, '{:.2f}')
        _bull_s = _f(_bull, '{:.0f}')
        _base_s = _f(_base, '{:.0f}')
        _bear_s = _f(_bear, '{:.0f}')
        _sup60_s = _f(_sup60, '{:.2f}')
        _res60_s = _f(_res60, '{:.2f}')
        _date_str = self.report_date.strftime('%Y-%m-%d')
        _gram_text = self._gram_outlook_text(_gs)
        _data_count = h.get('data_count', '--')

        # RSI背景色
        _rsi_bg_v = 'rgba(0,179,134,0.15)' if _rsi14 < 30 else 'rgba(239,68,68,0.15)' if _rsi14 > 70 else 'rgba(245,158,11,0.1)'
        _r5_v = ('+' if _r5 >= 0 else '') + _f(_r5, '{:+.2f}')
        _r20_v = ('+' if _r20 >= 0 else '') + _f(_r20, '{:+.2f}')

        # === 策略建议计算 ===
        # 综合评分 -> 操作建议
        if _gs >= 7 and _rsi14 < 70:
            _op_signal = '强烈买入'
            _op_color = '#c0392b'
            _op_desc = 'GRAM评分强劲，技术面配合，建议积极建仓'
            _position_pct = '80-100%'
        elif _gs >= 5.5 and _rsi14 < 75:
            _op_signal = '买入'
            _op_color = '#e74c3c'
            _op_desc = 'GRAM评分偏多，趋势向好，建议分批建仓'
            _position_pct = '50-80%'
        elif _gs >= 4.5:
            _op_signal = '持有'
            _op_color = '#f39c12'
            _op_desc = 'GRAM评分中性，建议维持现有仓位，等待明确信号'
            _position_pct = '30-50%'
        elif _gs >= 3.5:
            _op_signal = '减仓'
            _op_color = '#27ae60'
            _op_desc = 'GRAM评分偏空，建议降低仓位，控制风险'
            _position_pct = '10-30%'
        else:
            _op_signal = '卖出/观望'
            _op_color = '#1e8449'
            _op_desc = 'GRAM评分看空，建议清仓或空仓观望'
            _position_pct = '0-10%'

        # 止损止盈
        _stop_loss = _f(_sup60 * 0.97, '{:.2f}') if _sup60 > 0 else '--'
        _take_profit = _f(_res60 * 1.03, '{:.2f}') if _res60 > 0 else '--'

        # === 机构观点（中文）===
        if _rsi14 < 70 and _hist_pct > 70:
            _gs_short = '高位震荡偏多'
        elif _rsi14 >= 70:
            _gs_short = '超买 cautious'
        else:
            _gs_short = '区间偏多'

        _jp_short = '区间整理' if 30 < _rsi14 < 70 else '超买' if _rsi14 >= 70 else '超卖反弹'
        _br_short = '谨慎偏多' if _hist_pct > 70 else '配置机会' if _hist_pct < 30 else '结构性机会'

        _mid_view = '趋势向上' if _gs >= 5 else '震荡偏弱'
        _long_view = '配置价值' if _gs >= 5 else '中性观望'
        _risk_view = '风险匹配' if (risk.get('max_drawdown', 0) or 0) < 15 else '关注波动'

        # === GRAM因子 ===
        gram_factors = [
            ('机会成本', 'opportunity_cost', '40%'),
            ('风险/不确定性', 'risk_uncertainty', '25%'),
            ('供需格局', 'supply_demand', '20%'),
            ('趋势动能', 'momentum', '15%')
        ]

        # === HTML构建 ===
        _html = ''

        # Head + CSS
        _html += '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>' + _date_str.replace('-', '') + ' 黄金量化分析报告 V6</title><link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"><script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>'
        _html += '<style>:root{--n900:#0B132B;--n800:#1C2541;--n700:#3A506B;--n100:#F0F2F8;--g500:#C5A572;--g400:#DFBC8E;--up:#00B386;--dn:#EF4444;--txt:#111827;--sub:#4B5563;--muted:#9CA3AF;--bg:#F8FAFC;--card:#fff;--border:#E5E7EB;--sm:0 1px 2px rgba(0,0,0,.05);--md:0 4px 16px rgba(0,0,0,.08);--rsm:6px;--rmd:10px;--rlg:16px;}*{box-sizing:border-box;margin:0;padding:0;}body{font-family:Inter,-apple-system,Segoe UI,PingFang SC,Microsoft YaHei,sans-serif;background:var(--bg);color:var(--txt);line-height:1.65;font-size:14px;-webkit-font-smoothing:antialiased;}.c{max-width:1280px;margin:0 auto;padding:24px 28px 64px;}.cover{background:linear-gradient(135deg,var(--n900) 0%,var(--n800) 45%,#243B61 100%);border-radius:var(--rlg);padding:52px 52px 48px;margin-bottom:28px;position:relative;overflow:hidden;}.cover::before{content:"";position:absolute;top:-60px;right:-60px;width:300px;height:300px;background:radial-gradient(circle,rgba(197,165,114,.18) 0%,transparent 70%);border-radius:50%;}.cover-tag{display:inline-block;background:rgba(197,165,114,.18);border:1px solid rgba(197,165,114,.4);color:var(--g500);font-size:11px;font-weight:600;letter-spacing:1.5px;padding:4px 14px;border-radius:20px;margin-bottom:20px;}.cover h1{color:#fff;font-size:36px;font-weight:800;line-height:1.2;margin-bottom:14px;letter-spacing:-0.5px;}.cover-sub{color:rgba(255,255,255,.7);font-size:15px;margin-top:6px;}.cover-meta{display:flex;gap:24px;flex-wrap:wrap;margin-top:24px;}.cm{color:rgba(255,255,255,.6);font-size:12px;}.cm strong{color:rgba(255,255,255,.9);display:block;font-size:15px;margin-bottom:2px;}.cover-score{position:absolute;top:36px;right:48px;text-align:right;}.csn{font-size:68px;font-weight:800;color:var(--g500);line-height:1;font-family:JetBrains Mono,monospace;}.csl{color:rgba(255,255,255,.45);font-size:11px;text-transform:uppercase;letter-spacing:1px;}.cso{color:rgba(255,255,255,.75);font-size:13px;margin-top:4px;}.sec{margin-bottom:28px;}.st{font-size:17px;font-weight:700;color:var(--n900);margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid var(--n900);display:flex;align-items:center;gap:10px;}.stn{background:var(--n900);color:#fff;width:26px;height:26px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;}.card{background:var(--card);border-radius:var(--rmd);padding:20px 22px;box-shadow:var(--sm);border:1px solid var(--border);}.card-g{border-top:3px solid var(--g500);}.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:12px;}.kpi-l{background:var(--card);border-radius:var(--rmd);padding:16px 18px;box-shadow:var(--sm);border:1px solid var(--border);}.kpi-l .kl{color:var(--muted);font-size:10.5px;text-transform:uppercase;letter-spacing:.8px;margin-bottom:5px;}.kpi-l .kv{font-size:21px;font-weight:700;font-family:JetBrains Mono,monospace;margin-bottom:4px;}.kpi-l .ks{font-size:11px;color:var(--muted);}.up{color:var(--up);}.dn{color:var(--dn);}.neu{color:var(--muted);}table{width:100%;border-collapse:collapse;font-size:13px;}th{background:var(--n100);padding:9px 12px;text-align:left;font-weight:600;color:var(--n900);border-bottom:2px solid var(--border);}td{padding:9px 12px;border-bottom:1px solid var(--border);vertical-align:middle;}tr:last-child td{border-bottom:none;}tr:hover td{background:#fafbfc;}.gb{background:#e5e7eb;border-radius:4px;height:8px;overflow:hidden;}.gf{height:100%;border-radius:4px;font-size:10px;color:#fff;font-weight:600;display:flex;align-items:center;padding-left:5px;}.ds{background:#f8f9fa;border:1px solid var(--border);border-radius:var(--rsm);padding:12px 16px;font-size:12px;color:var(--muted);margin-top:20px;line-height:1.9;}.ai{background:linear-gradient(135deg,#f8fafc 0%,#f0f4ff 100%);border:1px solid #e0e7ff;border-radius:var(--rmd);padding:18px 20px;margin-bottom:14px;}.ai-t{font-size:13px;font-weight:700;color:#3730a3;margin-bottom:10px;display:flex;align-items:center;gap:8px;}.ai-b{font-size:13.5px;line-height:1.9;color:var(--sub);}.sb{display:flex;height:10px;border-radius:5px;overflow:hidden;margin:10px 0 14px;}.sbb{background:var(--up);}.sba{background:#64748b;}.sbd{background:var(--dn);}.sleg{display:flex;gap:18px;font-size:12px;}.sli{display:flex;align-items:center;gap:5px;}.sdot{width:9px;height:9px;border-radius:50%;}.op-card{background:linear-gradient(135deg,var(--n900),var(--n800));color:#fff;border-radius:var(--rmd);padding:24px 28px;margin-bottom:14px;text-align:center;}.op-signal{font-size:32px;font-weight:800;margin-bottom:8px;}.op-desc{font-size:14px;color:rgba(255,255,255,.8);margin-bottom:16px;}.op-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:16px;}.op-item{background:rgba(255,255,255,.08);border-radius:8px;padding:12px;}.op-item .op-l{color:rgba(255,255,255,.6);font-size:11px;margin-bottom:4px;}.op-item .op-v{font-size:18px;font-weight:700;color:var(--g500);}</style>'

        _html += '</head><body><div class="c">'

        # === 封面 ===
        _html += '<div class="cover"><div class="cover-tag">黄金量化分析报告</div>'
        _html += '<h1>黄金市场量化分析报告</h1>'
        _html += '<div class="cover-sub">当前价格 <span style="color:var(--g400);font-weight:700;">CNY ' + _price_s + '</span>/g，历史分位 <span style="font-weight:600;">' + _hist_s + '%</span>。' + _gram_text + '</div>'
        _html += '<div style="color:rgba(255,255,255,.5);font-size:13px;margin-top:8px;">支撑位 CNY ' + _sup60_s + ' / 阻力位 CNY ' + _res60_s + ' &nbsp;|&nbsp; RSI(14) ' + _rsi_s + ' ' + _rsi_lbl + '</div>'
        _html += '<div class="cover-meta"><div class="cm"><strong>' + _date_str + '</strong>报告日期</div><div class="cm"><strong>SGE Au99.99</strong>数据来源</div><div class="cm"><strong>' + str(_data_count) + '</strong>数据条数</div><div class="cm"><strong>V6 专业版</strong>分析引擎</div></div>'
        _html += '<div class="cover-score"><div class="csn">' + _gs_s + '</div><div class="csl">GRAM 评分</div><div class="cso" style="color:' + _gs_c + ';">' + _gs_outlook + '</div></div></div>'

        _html += '<div class="ds"><strong>[i] 数据来源</strong> SGE Au99.99 via akshare (' + str(_data_count) + ' 条日线) &nbsp;|&nbsp; 国债/VIX/美元指数: 公开API &nbsp;|&nbsp; 央行购金: WGC &nbsp;|&nbsp; 仅供参考，不构成投资建议。</div>'

        # === 1. 核心数据概览 ===
        _html += '<div class="sec" style="margin-top:28px;"><div class="st"><span class="stn">1</span>核心数据概览</div><div class="kpi-grid">'
        _html += '<div class="kpi-l"><div class="kl">当前金价</div><div class="kv" style="color:var(--g500);">CNY ' + _price_s + '</div><div class="ks">SGE Au99.99</div></div>'
        _html += '<div class="kpi-l"><div class="kl">5日收益</div><div class="kv ' + _r5_cls + '">' + _r5_v + '<small style="font-size:13px;">%</small></div><div class="ks">' + _r5_tw + '</div></div>'
        _html += '<div class="kpi-l"><div class="kl">20日收益</div><div class="kv ' + _r20_cls + '">' + _r20_v + '<small style="font-size:13px;">%</small></div><div class="ks">' + _r20_tw + '</div></div>'
        _html += '<div class="kpi-l"><div class="kl">RSI (14)</div><div class="kv" style="color:' + _rsi_c + ';">' + _rsi_s + '</div><div class="ks" style="background:' + _rsi_bg_v + ';display:inline-block;padding:2px 8px;border-radius:10px;">' + _rsi_lbl + '</div></div></div>'
        _html += '<div class="kpi-grid">'
        _html += '<div class="kpi-l"><div class="kl">历史分位</div><div class="kv">' + _hist_s + '<small style="font-size:13px;">%</small></div><div class="ks">' + _hist_zone + '</div></div>'
        _html += '<div class="kpi-l"><div class="kl">年化波动率</div><div class="kv">' + _vol_s + '<small style="font-size:13px;">%</small></div><div class="ks">20日滚动</div></div>'
        _html += '<div class="kpi-l"><div class="kl">MACD 柱状图</div><div class="kv ' + _macd_cls + '">' + _macd_s + '</div><div class="ks">' + str(h.get('macd_signal', '--')) + '</div></div>'
        _html += '<div class="kpi-l"><div class="kl">ATR (14)</div><div class="kv">' + _atr_s + '</div><div class="ks">真实波幅</div></div></div></div>'

        # === 2. 周期收益分析 ===
        _html += '<div class="sec"><div class="st"><span class="stn">2</span>周期收益分析</div><div class="card">'
        _html += '<table><thead><tr><th>周期</th><th>收益率</th><th>年化收益</th><th>趋势判断</th></tr></thead><tbody>'
        period_data = [
            ('1日', _r1, _r1 * 252),
            ('5日', _r5, _r5 * 50),
            ('20日(1月)', _r20, _r20 * 12.6),
            ('60日(3月)', _r60, _r60 * 4.2),
            ('120日(6月)', _r120, _r120 * 2.1),
            ('252日(1年)', _r252, _r252)
        ]
        for pn, pv, pa in period_data:
            pc = 'up' if pv >= 0 else 'dn'
            ps = '+' if pv >= 0 else ''
            pt = self._trend_word(pv)
            _html += '<tr><td><strong>' + pn + '</strong></td><td class="' + pc + '">' + ps + _f(pv, '{:+.2f}') + '%</td><td class="' + pc + '">' + ps + _f(pa, '{:+.1f}') + '%</td><td>' + pt + '</td></tr>'
        _html += '</tbody></table></div></div>'

        # === 3. GRAM归因分析 ===
        _html += '<div class="sec"><div class="st"><span class="stn">3</span>GRAM 黄金回报归因 (WGC标准)</div><div class="card card-g">'
        _html += '<div style="margin-bottom:18px;"><div style="font-size:13px;font-weight:600;margin-bottom:10px;">情景概率分布</div>'
        _html += '<div class="sb"><div class="sbb" style="width:' + _bull_s + '%;"></div><div class="sba" style="width:' + _base_s + '%;"></div><div class="sbd" style="width:' + _bear_s + '%;"></div></div>'
        _html += '<div class="sleg"><div class="sli"><div class="sdot" style="background:var(--up);"></div>乐观 ' + _bull_s + '%</div><div class="sli"><div class="sdot" style="background:#64748b;"></div>基准 ' + _base_s + '%</div><div class="sli"><div class="sdot" style="background:var(--dn);"></div>悲观 ' + _bear_s + '%</div></div></div>'
        _html += '<table><thead><tr><th>驱动因子</th><th>权重</th><th>评分</th><th>评估</th></tr></thead><tbody>'
        for fname, fkey, fwt in gram_factors:
            fi = gram.get(fkey, {})
            fs = fi.get('score', '--')
            fv = fi.get('interpretation', fi.get('detail', '--'))
            if isinstance(fs, (int, float)):
                bc = '#00B386' if fs >= 6 else '#F59E0B' if fs >= 4 else '#EF4444'
                bw = min(fs * 10, 100)
                fs_s = '{:.1f}/10'.format(fs)
            else:
                bc = '#9CA3AF'
                bw = 0
                fs_s = '--'
            _html += '<tr><td><strong>' + fname + '</strong></td><td style="font-weight:600;">' + fwt + '</td><td><div class="gb"><div class="gf" style="width:' + str(bw) + '%;background:' + bc + ';">' + fs_s + '</div></div></td><td style="font-size:13px;">' + str(fv) + '</td></tr>'
        gs_bw = min(_gs * 10, 100)
        _html += '<tr style="background:var(--n100);font-weight:700;"><td><strong>综合评分</strong></td><td></td><td><div class="gb"><div class="gf" style="width:' + str(gs_bw) + '%;background:' + _gs_c + ';">' + _gs_s + '/10</div></div></td><td style="color:' + _gs_c + ';font-size:14px;font-weight:700;">' + _gs_outlook + '</td></tr>'
        _html += '</tbody></table></div></div>'

        # === 4. 技术指标详解 ===
        _html += '<div class="sec"><div class="st"><span class="stn">4</span>技术指标详解</div><div class="card">'
        _html += '<table><thead><tr><th>指标</th><th>数值</th><th>状态</th><th>说明</th></tr></thead><tbody>'
        tech_data = [
            ('RSI(14)', _rsi14, _rsi_lbl, '相对强弱指标'),
            ('MACD', h.get('macd', 0), '多头' if h.get('macd', 0) > 0 else '空头', 'MACD 12/26/9'),
            ('MACD 信号', h.get('macd_signal', '--'), '--', 'MACD信号线'),
            ('MACD 柱状图', _macd_hist, '柱图', 'DIF-DEA差值'),
            ('布林上轨', _boll_upper, '突破' if _price > _boll_upper else '区间内', 'BOLL Upper'),
            ('布林中轨', h.get('boll_middle', 0), '中轨', 'BOLL Middle'),
            ('布林下轨', _boll_lower, '跌破' if _price < _boll_lower else '区间内', 'BOLL Lower'),
            ('KDJ K值', _kdj_k, 'K', '随机指标K'),
            ('KDJ D值', _kdj_d, 'D', '随机指标D'),
            ('KDJ J值', _kdj_j, 'J', '随机指标J'),
            ('ATR(14)', _atr14, '波动率', '真实波幅均值'),
            ('20日波动率', _vol20d, '年化', '年化波动率')
        ]
        for tn, tv, ts, td in tech_data:
            tv_s = _f(tv, '{:.4f}') if isinstance(tv, (int, float)) else '--'
            _html += '<tr><td><strong>' + tn + '</strong></td><td style="font-family:JetBrains Mono,monospace;">' + tv_s + '</td><td>' + str(ts) + '</td><td style="color:var(--muted);">' + td + '</td></tr>'
        _html += '</tbody></table></div></div>'

        # === 5. 机构观点对比 ===
        _html += '<div class="sec"><div class="st"><span class="stn">5</span>机构观点对比</div><div class="card">'
        _html += '<table><thead><tr><th>机构</th><th>短期观点</th><th>中期观点</th><th>长期观点</th></tr></thead><tbody>'
        inst_data = [
            ('高盛 (Goldman Sachs)', '宏观驱动', _gs_short, _mid_view, '结构性看多' if _gs >= 5 else '中性'),
            ('摩根大通 (J.P. Morgan)', '风险平价', _jp_short, _mid_view, '长期看多' if _gs >= 5 else '中性'),
            ('贝莱德 (BlackRock)', '情景分析', _br_short, '上行机会' if _gs >= 5 else '谨慎', '战略性配置' if _gs >= 5 else '中性')
        ]
        for iname, imodel, is_, im_, il_ in inst_data:
            _html += '<tr><td><strong>' + iname + '</strong><br><span style="font-size:11px;color:var(--muted);">' + imodel + '</span></td><td>' + is_ + '</td><td>' + im_ + '</td><td>' + il_ + '</td></tr>'
        _html += '<tr style="background:#f0f9ff;font-weight:700;"><td>市场共识</td><td colspan="3">短期: ' + ('高位震荡' if _hist_pct > 70 else '区间整理' if 30 < _hist_pct < 70 else '低位反弹') + ' &nbsp;|&nbsp; 中期: ' + _mid_view + ' &nbsp;|&nbsp; 长期: ' + _long_view + ' &nbsp;|&nbsp; 风险: ' + _risk_view + '</td></tr>'
        _html += '</tbody></table></div></div>'

        # === 6. 量化分析 (Phase 2-4) ===
        quant_sec = self._build_quant_html_section()
        if quant_sec:
            _html += '<div class="sec"><div class="st"><span class="stn">6</span>量化分析 (Phase 2-4)</div>' + quant_sec + '</div>'

        # === 7. AI深度洞察 ===
        if self.topic_content:
            _html += '<div class="sec"><div class="st"><span class="stn">7</span>AI 深度洞察 (DeepSeek V3)</div>'
            topic_styles = {
                'core_conclusion': ('#2980b9', '核心结论解读', '#f0f7fa'),
                'technical_analysis': ('#27ae60', '技术分析', '#eafaf1'),
                'fundamental_analysis': ('#8e44ad', '基本面分析', '#faf0ff'),
                'scenario_analysis': ('#e67e22', '情景分析', '#fef8ed'),
                'risk_warning': ('#e74c3c', '风险预警', '#fef5f5'),
                'investment_strategy': ('#16a085', '投资策略建议', '#e8f8f5'),
                'market_outlook': ('#d4af37', '市场展望', '#fffbf0'),
                'performance_metrics': ('#9b59b6', '绩效指标', '#f4ecf7'),
                'risk_assessment': ('#e67e22', '风险评估', '#fef8ed'),
                'portfolio_allocation': ('#1abc9c', '投资组合配置', '#e8f8f5')
            }
            for topic in self.FIXED_TOPICS:
                tid = topic['id']
                content_val = self.topic_content.get(tid, '')
                if not content_val:
                    continue
                color, tname, bg = topic_styles.get(tid, ('#34495e', topic['title'], '#f8f9fa'))
                _html += '<div class="ai" style="border-left:4px solid ' + color + ';background:' + bg + ';">'
                _html += '<div class="ai-t" style="color:' + color + ';">AI ' + tname + '<span style="margin-left:auto;font-size:11px;color:#999;">DeepSeek-V3</span></div>'
                _html += '<div class="ai-b">' + self._markdown_to_html(content_val) + '</div></div>'
            _html += '</div>'

        # === 8. 近期走势分析 ===
        recent = h.get('recent_trend', {})
        if recent.get('signals'):
            _html += '<div class="sec"><div class="st"><span class="stn">8</span>近期走势分析</div><div class="card">'
            _ts = recent.get('status', '震荡')
            _tc = recent.get('color', '#f39c12')
            _ta = recent.get('advice', '观望')
            _tsp = recent.get('support', 0)
            _trp = recent.get('resistance', 0)
            _html += '<p style="font-size:16px;margin-bottom:14px;"><strong>【趋势判断】</strong>短期走势: <span style="color:' + _tc + ';font-weight:bold;font-size:20px;">' + _ts + '</span></p>'
            _html += '<div style="background:#f8f9fa;padding:12px 16px;border-radius:8px;margin-bottom:16px;"><strong>【操作建议】</strong> ' + _ta + '</div>'
            _html += '<table><tr><th>项目</th><th>数值</th><th>备注</th></tr>'
            _html += '<tr><td><strong>当前价格</strong></td><td style="color:var(--g500);font-weight:bold;">CNY ' + _price_s + '</td><td>最新收盘价</td></tr>'
            _html += '<tr><td><strong>支撑位</strong></td><td class="dn">CNY ' + _f(_tsp, '{:.2f}') + '</td><td>60日低点</td></tr>'
            _html += '<tr><td><strong>阻力位</strong></td><td class="up">CNY ' + _f(_trp, '{:.2f}') + '</td><td>60日高点</td></tr>'
            _html += '</table>'
            _html += '<div style="margin-top:14px;"><strong style="font-size:14px;">技术信号</strong></div>'
            for sig in recent.get('signals', []):
                sl = sig.get('level', 'neutral')
                sc = '#00B386' if sl == 'bullish' else '#EF4444' if sl == 'bearish' else '#9CA3AF'
                _html += '<div style="display:flex;align-items:center;gap:12px;padding:7px 0;border-bottom:1px solid var(--border);"><span style="width:8px;height:8px;border-radius:50%;background:' + sc + ';flex-shrink:0;"></span><span style="font-size:12px;font-weight:600;">' + sig.get('type', '') + '</span><span style="font-size:13px;color:' + sc + ';">' + sig.get('signal', '') + '</span></div>'
            _html += '</div></div>'

        # === 9. 量化策略建议 (新增) ===
        _html += '<div class="sec"><div class="st"><span class="stn">9</span>量化策略建议</div>'
        _html += '<div class="op-card">'
        _html += '<div class="op-signal" style="color:' + _op_color + ';">' + _op_signal + '</div>'
        _html += '<div class="op-desc">' + _op_desc + '</div>'
        _html += '<div class="op-grid">'
        _html += '<div class="op-item"><div class="op-l">建议仓位占比</div><div class="op-v">' + _position_pct + '</div></div>'
        _html += '<div class="op-item"><div class="op-l">止损位 (60日低点-3%)</div><div class="op-v">CNY ' + _stop_loss + '</div></div>'
        _html += '<div class="op-item"><div class="op-l">止盈位 (60日高点+3%)</div><div class="op-v">CNY ' + _take_profit + '</div></div>'
        _html += '</div></div>'
        _html += '<div class="card">'
        _html += '<table><thead><tr><th>策略维度</th><th>判断</th><th>依据</th></tr></thead><tbody>'
        # 策略依据
        gram_reason = gram.get('outlook', '中性')
        rsi_reason = 'RSI=' + _rsi_s + ('，超买注意回调' if _rsi14 > 70 else '，超卖关注反弹' if _rsi14 < 30 else '，正常区间')
        hist_reason = '历史分位' + _hist_s + '% (' + _hist_zone + ')'
        _html += '<tr><td><strong>GRAM综合评分</strong></td><td style="color:' + _gs_c + ';font-weight:700;">' + _gs_outlook + '</td><td>' + gram_reason + '</td></tr>'
        _html += '<tr><td><strong>技术形态</strong></td><td>' + _rsi_lbl + '</td><td>' + rsi_reason + '</td></tr>'
        _html += '<tr><td><strong>估值分位</strong></td><td>' + _hist_zone + '</td><td>' + hist_reason + '</td></tr>'
        _html += '<tr><td><strong>均线信号</strong></td><td>' + str(h.get('ma_signal', '--')) + '</td><td>MA5/MA20/MA60综合分析</td></tr>'
        _html += '<tr><td><strong>MACD信号</strong></td><td>' + str(h.get('macd_signal', '--')) + '</td><td>MACD DIF/DEA/柱状图</td></tr>'
        _html += '<tr><td><strong>KDJ信号</strong></td><td>' + str(h.get('kdj_signal', '--')) + '</td><td>KDJ K/D/J值</td></tr>'
        _html += '</tbody></table>'
        _html += '<div style="margin-top:14px;padding:13px 15px;background:#fffbf0;border-radius:8px;border:1px solid #fde68a;font-size:13px;color:#92400e;line-height:1.8;">'
        _html += '<strong>策略说明：</strong>以上建议基于GRAM评分体系（' + _gs_s + '/10）、技术指标（RSI=' + _rsi_s + '、MACD=' + str(h.get('macd_signal', '--')) + '）及历史分位（' + _hist_s + '%）综合计算。投资有风险，入市需谨慎。建议根据个人风险偏好调整仓位。</div>'
        _html += '</div></div>'

        # === 10. 风险量化指标 ===
        _html += '<div class="sec"><div class="st"><span class="stn">10</span>风险量化指标</div><div class="card">'
        _html += '<table><thead><tr><th>风险指标</th><th>数值</th><th>说明</th></tr></thead><tbody>'
        risk_data = [
            ('VaR (95%)', _var_val, '历史模拟VaR'),
            ('CVaR (95%)', _cvar_val, '条件风险价值'),
            ('最大回撤', _mdd_val, '历史最大回撤'),
            ('夏普比率', _sratio, '风险调整后收益'),
            ('索提诺比率', _dratio, '下行风险调整后收益')
        ]
        for rn, rv, rd in risk_data:
            rv_s = _f(rv, '{:.2f}') if isinstance(rv, (int, float)) else str(rv)
            _html += '<tr><td><strong>' + rn + '</strong></td><td style="font-family:JetBrains Mono,monospace;font-weight:600;">' + rv_s + '</td><td style="color:var(--muted);">' + rd + '</td></tr>'
        _html += '</tbody></table>'

        st_has_data = any(isinstance(v, (int, float)) for v in [_st_ir, _st_dx, _st_geo, _st_eq])
        if st_has_data:
            _html += '<div style="margin-top:18px;"><div style="font-size:14px;font-weight:700;margin-bottom:10px;">压力测试</div><table><thead><tr><th>压力情景</th><th>预估影响</th><th>概率</th></tr></thead><tbody>'
            st_items = [
                ('利率上升50bp', _st_ir, st.get('interest_rate_shock', {}).get('probability', '中等')),
                ('美元指数上涨5%', _st_dx, st.get('dollar_strength', {}).get('probability', '低')),
                ('地缘冲突升级', _st_geo, st.get('geopolitical_risk', {}).get('probability', '低')),
                ('股市下跌20%', _st_eq, st.get('equity_market_crash', {}).get('probability', '低'))
            ]
            for sn, sv, sp in st_items:
                sv_s = _f(sv, '{:.2f}%') if isinstance(sv, (int, float)) else str(sv)
                _html += '<tr><td>' + sn + '</td><td class="dn">' + sv_s + '</td><td>' + str(sp) + '</td></tr>'
            _html += '</tbody></table></div>'
        _html += '</div></div>'

        # === 11. 资产配置建议 ===
        # 动态配置比例
        if _gs >= 7:
            _cfg_con = '6%-8%'
            _cfg_mod = '12%-16%'
            _cfg_agg = '20%-25%'
        elif _gs >= 5.5:
            _cfg_con = '5%-7%'
            _cfg_mod = '10%-14%'
            _cfg_agg = '18%-22%'
        elif _gs >= 4.5:
            _cfg_con = '4%-6%'
            _cfg_mod = '8%-12%'
            _cfg_agg = '15%-20%'
        elif _gs >= 3.5:
            _cfg_con = '3%-5%'
            _cfg_mod = '6%-9%'
            _cfg_agg = '10%-15%'
        else:
            _cfg_con = '2%-4%'
            _cfg_mod = '4%-7%'
            _cfg_agg = '8%-12%'

        _html += '<div class="sec"><div class="st"><span class="stn">11</span>资产配置建议</div><div class="card card-g">'
        _html += '<table><thead><tr><th>风险偏好</th><th>黄金配置比例</th><th>策略说明</th></tr></thead><tbody>'
        alloc_data = [
            ('保守型', _cfg_con, '本金保护优先，低波动策略'),
            ('平衡型', _cfg_mod, '均衡配置，兼顾收益与风险'),
            ('积极型', _cfg_agg, '增强黄金敞口，追求超额收益')
        ]
        for an, ar, ad in alloc_data:
            _html += '<tr><td><strong>' + an + '</strong></td><td style="color:var(--g500);font-weight:700;font-size:15px;">' + ar + '</td><td>' + ad + '</td></tr>'
        _html += '</tbody></table>'
        _html += '<div style="margin-top:14px;padding:13px 15px;background:#fffbf0;border-radius:8px;border:1px solid #fde68a;font-size:13px;color:#92400e;line-height:1.8;">'
        _html += '<strong>配置依据：</strong>GRAM评分 ' + _gs_s + '/10（' + _gs_outlook + '） &nbsp;|&nbsp; 历史分位 ' + _hist_s + '%（' + _hist_zone + '） &nbsp;|&nbsp; RSI ' + _rsi_s + '（' + _rsi_lbl + '） &nbsp;|&nbsp; 波动率 ' + _vol_s + '%</div></div></div>'

        # === 页脚 ===
        _html += '<div style="text-align:center;padding:24px;color:var(--muted);font-size:12px;border-top:1px solid var(--border);margin-top:20px;">'
        _html += '黄金量化分析报告 V6 &nbsp;|&nbsp; 生成时间: ' + _date_str + ' &nbsp;|&nbsp; 数据来源: SGE/akshare/WGC &nbsp;|&nbsp; 仅供参考，不构成投资建议'
        _html += '</div>'
        _html += '</div></body></html>'
        return _html

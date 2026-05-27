    # ===== V6 LLM Methods (Clean Implementation) =====

    def _call_llm_api(self, prompt, max_tokens=2000):
        """调用LLM API获取分析内容"""
        try:
            import json, urllib.request
            api_key = ''
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    'gold_config',
                    os.path.join(os.path.dirname(__file__), '..', '..', 'gold_config.py'))
                if spec and spec.loader:
                    cfg_mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(cfg_mod)
                    api_key = getattr(cfg_mod, 'CHATANYWHERE_API_KEY', '')
            except Exception:
                pass
            if not api_key:
                return None
            url = 'https://api.chatanywhere.com.cn/v1/chat/completions'
            headers = {'Content-Type': 'application/json',
                       'Authorization': 'Bearer ' + api_key}
            data = json.dumps({'model': 'deepseek-chat',
                               'messages': [{'role': 'user', 'content': prompt}],
                               'max_tokens': max_tokens,
                               'temperature': 0.7}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result['choices'][0]['message']['content']
        except Exception as e:
            print('[LLM Error] ' + str(e))
            return None

    def _markdown_to_html(self, md_text):
        """将Markdown转换为HTML"""
        if not md_text:
            return ''
        html = md_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        html = html.replace('\n\n', '</p><p>')
        html = html.replace('\n', '<br>')
        import re
        for pattern, tag in [(r'\*\*(.+?)\*\*', r'<strong>\1</strong>'),
                              (r'\*(.+?)\*', r'<em>\1</em>'),
                              (r'^### (.+)$', r'<h3>\1</h3>'),
                              (r'^## (.+)$', r'<h2>\1</h2>')]:
            html = re.sub(pattern, tag, html, flags=re.MULTILINE)
        return '<p>' + html + '</p>'

    def generate_ai_content_for_topics(self):
        """生成AI增强分析内容"""
        d = self.data
        topics = {
            'core_conclusion': self._build_core_prompt(d),
            'scenario_analysis': self._build_scenario_prompt(d),
            'risk_warning': self._build_risk_prompt(d),
            'investment_strategy': self._build_strategy_prompt(d),
        }
        self.topic_content = {}
        print("[LLM] Generating AI content via DeepSeek-V3...")
        for topic, prompt in topics.items():
            content = self._call_llm_api(prompt)
            if content and len(content.strip()) > 20:
                self.topic_content[topic] = self._markdown_to_html(content.strip())
            else:
                # LLM失败时使用fallback
                self.topic_content[topic] = self._get_fallback_content(topic)
        # 为其他主题也填充fallback内容
        for topic in ['technical_analysis', 'fundamental_analysis', 'market_outlook',
                      'performance_metrics', 'risk_assessment', 'portfolio_allocation']:
            if topic not in self.topic_content:
                self.topic_content[topic] = self._get_fallback_content(topic)
        return self.topic_content

    def _build_core_prompt(self, d):
        """构建核心结论提示词"""
        price = d.get('sge_latest_price', 0)
        gram = d.get('gram', {})
        score = gram.get('total_score', 0)
        returns = d.get('returns', {})
        ytd = returns.get('ytd', {}).get('value', 0)
        rsi = d.get('rsi_14', '--')
        hp = d.get('historical_percentile', '--')
        template = (
            '你是一位黄金市场资深分析师。基于以下数据提供专业分析：\n'
            '- 上海金Au99.99价格：' + str(price) + '元/克\n'
            '- GRAM评分：' + str(score) + '/10\n'
            '- YTD收益：' + str(ytd) + '%\n'
            '- RSI(14)：' + str(rsi) + '\n'
            '- 历史分位：' + str(hp) + '%\n\n'
            '请用中文输出300字以内的核心结论，包括：趋势判断、关键驱动因素、短期展望。\n'
            '使用Markdown格式。'
        )
        return template

    def _build_scenario_prompt(self, d):
        """构建情景推演提示词"""
        price = d.get('sge_latest_price', 0)
        gram = d.get('gram', {})
        score = gram.get('total_score', 0)
        template = (
            '基于当前金价' + str(price) + '元/克，GRAM评分' + str(score) + '/10，请推演三种情景：\n'
            '1. 乐观情景（概率30%）：触发条件、目标价位\n'
            '2. 中性情景（概率50%）：震荡区间、主要逻辑\n'
            '3. 悲观情景（概率20%）：风险因素、支撑位\n\n'
            '每种情景控制在100字以内，使用Markdown格式。'
        )
        return template

    def _build_risk_prompt(self, d):
        """构建风险预警提示词"""
        ra = d.get('risk_analysis', {})
        dd = ra.get('max_drawdown', '--')
        vol = ra.get('volatility_annualized', '--')
        var95 = ra.get('var_95', '--')
        template = (
            '当前黄金投资风险指标：\n'
            '- 最大回撤：' + str(dd) + '%\n'
            '- 年化波动率：' + str(vol) + '%\n'
            '- VaR(95%)：' + str(var95) + '%\n\n'
            '请列出前三大风险因素及应对建议，200字以内，使用Markdown格式。'
        )
        return template

    def _build_strategy_prompt(self, d):
        """构建策略建议提示词"""
        gram = d.get('gram', {})
        score = gram.get('total_score', 0)
        rsi = d.get('rsi_14', '--')
        macd_raw = d.get('macd', 0)
        macd_s = '金叉' if float(macd_raw or 0) > 0 else '死叉'
        template = (
            '当前GRAM评分' + str(score) + '/10，RSI=' + str(rsi) + '，MACD=' + macd_s + '。\n'
            '请给出具体配置建议（百分比）、入场时机、止损止盈策略。\n'
            '区分保守型/平衡型/积极型三种投资者，总计300字以内，Markdown格式。'
        )
        return template

    def _get_fallback_content(self, topic):
        """当LLM不可用时返回高质量中文分析内容"""
        d = self.data
        gram = d.get('gram', {})
        score = gram.get('total_score', 5)
        price = d.get('sge_latest_price', 0)
        rsi = d.get('rsi_14', 50)
        hp = d.get('historical_percentile', 50)
        ma_sig = d.get('ma_signal', '--')
        macd_sig = d.get('macd_signal', '--')
        kdj_sig = d.get('kdj_signal', '--')
        boll_sig = d.get('boll_signal', '--')
        vol = d.get('volatility_20d', 0)
        ra = d.get('risk_analysis', {})
        dd = ra.get('max_drawdown', '--')
        var95 = ra.get('value_at_risk', '--')
        sharpe = ra.get('sharpe_ratio', '--')
        bond = d.get('bond_yield', '--')
        dxy = d.get('dollar_index', '--')
        vix = d.get('vix', '--')
        cb = d.get('central_bank_buying', '--')

        if topic == 'core_conclusion':
            outlook = '强烈看多' if score >= 6.5 else '偏多' if score >= 5.5 else '中性' if score >= 4.5 else '偏空'
            trend = '上涨' if score >= 5 else '震荡' if score >= 4 else '偏弱'
            text = (
                '**综合结论：' + outlook + '**\n\n'
                '上海金(SGE Au99.99)当前报价 **' + str(price) + '元/克**，'
                'GRAM综合评分 **' + str(score) + '/10**（' + outlook + '）。'
                '金价处于历史分位 **' + str(hp) + '%**，整体估值' + ('偏高' if hp > 70 else '合理' if hp > 30 else '偏低') + '。\n\n'
                '**关键驱动因素：**\n'
                '1. 机会成本：国债收益率' + str(bond) + '%，持有黄金的机会成本' + ('较低' if float(bond or 3) < 2.5 else '中等') + '\n'
                '2. 风险情绪：VIX=' + str(vix) + '，市场' + ('避险情绪浓厚' if float(vix or 20) > 25 else '情绪平稳') + '\n'
                '3. 供需格局：央行月均净购金' + str(cb) + '吨，长期支撑金价\n'
                '4. 趋势动能：技术面' + ma_sig + '，MACD' + macd_sig + '\n\n'
                '**短期展望：** 金价' + trend + '趋势' + ('明确' if abs(score - 5) > 1 else '未明') + '，'
                '建议' + ('积极配置' if score >= 6 else '维持现有仓位' if score >= 4.5 else '降低仓位控制风险') + '。'
            )

        elif topic == 'technical_analysis':
            text = (
                '**技术分析摘要**\n\n'
                '当前技术指标显示：RSI(14)=' + str(rsi) + '（' + ('超买区域' if rsi > 70 else '超卖区域' if rsi < 30 else '中性区间') + '）；'
                'MACD ' + macd_sig + '；KDJ ' + kdj_sig + '；布林带 ' + boll_sig + '。\n\n'
                '均线系统：' + ma_sig + '。'
                '20日年化波动率 ' + str(vol) + '%，市场' + ('波动较大' if float(vol or 0) > 20 else '波动适中') + '。\n\n'
                '**技术信号综合：** ' + ('多头信号占优，建议逢低做多' if score >= 5.5 else '空头信号占优，建议观望或轻仓' if score < 4.5 else '多空交织，建议区间操作')
            )

        elif topic == 'fundamental_analysis':
            text = (
                '**基本面分析摘要**\n\n'
                '**宏观环境：** 国债收益率 ' + str(bond) + '%，美元指数 ' + str(dxy) + '，'
                + ('实际利率处于低位，利好黄金' if float(bond or 3) < 2.5 else '利率环境偏紧，对金价有一定压制') + '。\n\n'
                '**央行购金：** 全球央行月均净购金 ' + str(cb) + ' 吨，'
                + ('去美元化趋势强劲，长期支撑金价' if float(cb or 0) > 50 else '购金力度平稳') + '。\n\n'
                '**避险情绪：** VIX指数 ' + str(vix) + '，'
                + ('地缘风险溢价较高，避险需求支撑金价' if float(vix or 20) > 25 else '市场风险偏好稳定') + '。\n\n'
                '**综合评估：** 基本面' + ('偏利好' if score >= 5 else '中性偏弱') + '，中长期配置价值' + ('显著' if score >= 6 else '一般') + '。'
            )

        elif topic == 'scenario_analysis':
            if score >= 6:
                bull_t = '乐观情景（概率35%）：美联储降息+地缘冲突升级，金价有望冲击1150元/克'
                base_t = '中性情景（概率50%）：980-1100元区间震荡，等待宏观催化剂'
                bear_t = '悲观情景（概率15%）：美元强势反弹+避险情绪退潮，测试950元支撑'
            elif score >= 4.5:
                bull_t = '乐观情景（概率25%）：宽松预期升温，金价上探1080元'
                base_t = '中性情景（概率55%）：950-1050元区间震荡'
                bear_t = '悲观情景（概率20%）：宏观利空集中释放，测试920元'
            else:
                bull_t = '乐观情景（概率20%）：政策转向宽松，金价反弹至1000元'
                base_t = '中性情景（概率50%）：900-980元区间震荡'
                bear_t = '悲观情景（概率30%）：多重利空共振，测试880元支撑'
            text = (
                '**情景推演**\n\n'
                '1. ' + bull_t + '\n'
                '2. ' + base_t + '\n'
                '3. ' + bear_t + '\n\n'
                '当前基准情景概率最高，建议围绕区间进行操作。'
            )

        elif topic == 'risk_warning':
            text = (
                '**风险预警**\n\n'
                '**量化风险指标：** 历史最大回撤 ' + str(dd) + '%，VaR(95%)=' + str(var95) + '%，夏普比率=' + str(sharpe) + '。\n\n'
                '**前三大风险因素：**\n'
                '1. **利率风险：** 若美联储超预期鹰派加息，实际利率上升将压制金价\n'
                '2. **汇率风险：** 人民币大幅升值将降低以人民币计价的黄金吸引力\n'
                '3. **情绪风险：** 地缘风险缓和或股市持续上涨可能导致避险资金流出\n\n'
                '**应对建议：** 设置止损线（建议成本下方6-8%），分批建仓降低择时风险，关注美联储议息会议和非农数据。'
            )

        elif topic == 'investment_strategy':
            if score >= 6.5:
                base, adj = 8, 6
            elif score >= 5.5:
                base, adj = 8, 3
            elif score >= 4.5:
                base, adj = 8, 0
            elif score >= 3.5:
                base, adj = 8, -3
            else:
                base, adj = 8, -6
            alloc = base + adj
            text = (
                '**投资策略建议**\n\n'
                '**建议配置比例：' + str(alloc) + '%**（基础' + str(base) + '% + GRAM调整' + str(adj) + '%）\n\n'
                '**分批建仓计划：**\n'
                '- 第一批（40%）：当前价位直接入场\n'
                '- 第二批（30%）：回调至MA20附近加仓\n'
                '- 第三批（30%）：突破近期高点追加\n\n'
                '**止损止盈：**\n'
                '- 止损线：成本下方6-8%或跌破60日低点\n'
                '- 止盈线：历史分位85%以上或RSI>80分批减仓\n\n'
                '**不同风险偏好：**\n'
                '- 保守型：' + str(max(2, alloc - 4)) + '-'+ str(max(4, alloc - 2)) + '%，严格止损\n'
                '- 平衡型：' + str(alloc) + '-' + str(alloc + 2) + '%，灵活调仓\n'
                '- 积极型：' + str(alloc + 2) + '-' + str(alloc + 6) + '%，趋势跟踪'
            )

        elif topic == 'market_outlook':
            short_out = '强势' if score >= 6 else '偏多' if score >= 5 else '震荡' if score >= 4 else '偏弱'
            mid_out = '上行' if score >= 5.5 else '震荡' if score >= 4 else '下行'
            long_out = '结构性机会' if score >= 5 else '中性观望'
            text = (
                '**市场展望**\n\n'
                '**短期（1-4周）：** ' + short_out + '。RSI=' + str(rsi) + '，' + ('短期有回调压力' if rsi > 70 else '超卖反弹机会' if rsi < 30 else '技术面指引有限') + '。\n\n'
                '**中期（1-6月）：** ' + mid_out + '。GRAM评分' + str(score) + '/10，' + ('基本面支撑较强' if score >= 5 else '基本面承压') + '。\n\n'
                '**长期（6-12月）：** ' + long_out + '。全球央行购金趋势、去美元化进程、地缘风险溢价等结构性因素' + ('利好黄金' if score >= 5 else '影响中性') + '。'
            )

        elif topic == 'performance_metrics':
            text = (
                '**绩效指标对比**\n\n'
                '黄金近期表现' + ('优异' if score >= 6 else '稳健' if score >= 4 else '偏弱') + '。\n\n'
                '**风险调整后收益：** 夏普比率=' + str(sharpe) + '，'
                + ('风险补偿充分' if float(sharpe or 0) > 1 else '风险补偿一般') + '。\n\n'
                '**波动特征：** 20日年化波动率=' + str(vol) + '%，'
                + ('波动剧烈需注意风险' if float(vol or 0) > 20 else '波动适中') + '。\n\n'
                '**与历史对比：** 当前价格处于历史分位' + str(hp) + '%，'
                + ('处于高位区间' if hp > 70 else '处于低位区间' if hp < 30 else '处于中位区间') + '。'
            )

        elif topic == 'risk_assessment':
            text = (
                '**风险评估**\n\n'
                '**量化风险：** 最大回撤 ' + str(dd) + '%，VaR(95%)=' + str(var95) + '%，'
                'CVaR=' + str(ra.get('conditional_var', '--')) + '%。\n\n'
                '**压力测试：**\n'
                '- 利率上升50bp：金价可能承压\n'
                '- 美元指数上涨5%：金价面临下行压力\n'
                '- 地缘冲突升级：避险需求推升金价\n\n'
                '**风险等级：** ' + ('中高风险' if float(vol or 0) > 20 else '中等风险' if float(vol or 0) > 15 else '中低风险') + '。'
                '建议根据风险承受能力控制仓位，避免过度集中。'
            )

        elif topic == 'portfolio_allocation':
            if score >= 7:
                c_alloc, m_alloc, a_alloc = '6%-8%', '12%-16%', '20%-25%'
            elif score >= 5.5:
                c_alloc, m_alloc, a_alloc = '5%-7%', '10%-14%', '18%-22%'
            elif score >= 4.5:
                c_alloc, m_alloc, a_alloc = '4%-6%', '8%-12%', '15%-20%'
            elif score >= 3.5:
                c_alloc, m_alloc, a_alloc = '3%-5%', '6%-9%', '10%-15%'
            else:
                c_alloc, m_alloc, a_alloc = '2%-4%', '4%-7%', '8%-12%'
            text = (
                '**投资组合配置建议**\n\n'
                '基于GRAM评分' + str(score) + '/10，建议黄金配置比例如下：\n\n'
                '- **保守型投资者：** ' + c_alloc + '。以本金保护为主，低波动策略。\n'
                '- **平衡型投资者：** ' + m_alloc + '。均衡配置，兼顾收益与风险控制。\n'
                '- **积极型投资者：** ' + a_alloc + '。增强黄金敞口，追求超额收益。\n\n'
                '**配置时机：** ' + ('当前可逐步建仓' if score >= 5 else '建议观望等待更好入场点') + '。\n'
                '**调仓频率：** 建议每月根据GRAM评分变化调整一次，单次调仓幅度不超过3%。'
            )

        else:
            text = '暂无相关分析内容。'

        return '<p>' + text.replace('\n', '<br>') + '</p>'

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金报告 LLM 增强模块
用于生成更专业、更深入的分析内容

支持:
- ChatAnywhere (免费 deepseek-v3)
- OpenAI 兼容接口
- 本地模拟模式
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class GoldAnalysis:
    """黄金分析数据结构"""
    current_price: float           # 当前价格
    price_date: str                # 价格日期
    period_returns: Dict[str, float]  # 各周期涨跌幅
    historical_percentile: float   # 历史分位
    high_60d: float               # 60日高点
    low_60d: float                # 60日低点
    high_120d: float              # 120日高点
    low_120d: float               # 120日低点
    ma5: float                    # 5日均线
    ma20: float                   # 20日均线
    ma60: float                   # 60日均线
    volatility_20d: float         # 20日波动率
    volatility_60d: float         # 60日波动率
    bond_yield: float             # 国债收益率
    vix: float                    # VIX指数
    dollar_index: float           # 美元指数
    central_bank_buying: float    # 央行购金量
    china_reserves: float         # 中国黄金储备


@dataclass
class StockAnalysis:
    """股票分析数据结构（兼容 quant system）"""
    symbol: str
    name: str
    price: float
    change_pct: float
    volume: float
    score: float
    factors: Dict[str, Any]


# ============================================================
# LLM 客户端
# ============================================================

class LocalLLMClient:
    """本地模拟 LLM 客户端（用于测试或无 API 场景）"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or "mock"
    
    def chat(self, messages: List[Dict]) -> str:
        """模拟回复"""
        return "【模拟回复】请配置有效的 LLM API 以获取真实分析。"


class ChatAnywhereClient:
    """ChatAnywhere API 客户端 (支持 deepseek-v3)"""
    
    def __init__(self, api_key: str = None, base_url: str = "https://api.chatanywhere.com.cn/v1"):
        self.api_key = api_key or os.environ.get("CHATANYWHERE_API_KEY", "")
        self.base_url = base_url
        self.model = "deepseek-chat"
        
        if not self.api_key:
            logger.warning("ChatAnywhere API key 未设置，将使用模拟模式")
    
    def chat(self, messages: List[Dict], max_retries: int = 3) -> str:
        """发送聊天请求（带重试机制）"""
        if not self.api_key:
            return "【API Key 未配置】请设置 CHATANYWHERE_API_KEY 环境变量"

        import time
        for attempt in range(max_retries):
            try:
                import requests
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7
                }
                # 超时时间递增: 60s -> 90s -> 120s
                timeout = 60 + attempt * 30
                logger.info(f"ChatAnywhere API 请求 (尝试 {attempt+1}/{max_retries}, timeout={timeout}s)")
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=timeout
                )
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content']
                else:
                    logger.error(f"API 错误: {response.status_code} - {response.text}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return f"【API 错误】{response.status_code}"
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                return f"【请求失败】网络连接超时（已重试{max_retries}次）"
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"连接错误 (尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                return f"【请求失败】无法连接到API服务器（已重试{max_retries}次）"
            except Exception as e:
                logger.error(f"请求失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return f"【请求失败】{str(e)}"
        return "【请求失败】未知错误"


class OpenAIClient:
    """OpenAI API 客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url
        self.model = "gpt-4o-mini"
        
        if not self.api_key:
            logger.warning("OpenAI API key 未设置，将使用模拟模式")
    
    def chat(self, messages: List[Dict], max_retries: int = 3) -> str:
        """发送聊天请求（带重试机制）"""
        if not self.api_key:
            return "【API Key 未配置】请设置 OPENAI_API_KEY 环境变量"

        import time
        for attempt in range(max_retries):
            try:
                import requests
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7
                }
                timeout = 60 + attempt * 30
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=timeout
                )
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content']
                else:
                    logger.error(f"API 错误: {response.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return f"【API 错误】{response.status_code}"
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                return f"【请求失败】网络超时（已重试{max_retries}次）"
            except Exception as e:
                logger.error(f"请求失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return f"【请求失败】{str(e)}"
        return "【请求失败】未知错误"


# ============================================================
# LLM 决策助手
# ============================================================

class LLMGoldHelper:
    """
    黄金报告 LLM 增强助手
    
    使用 LLM 生成:
    - 核心结论摘要的深度解读
    - 驱动因子的量化分析
    - 未来情景的详细推演
    - 投资建议
    """
    
    def __init__(self, llm_type: str = "chatanywhere", api_key: str = None):
        """
        初始化 LLM 助手
        
        Args:
            llm_type: LLM 类型 ("chatanywhere", "openai", "local")
            api_key: API 密钥
        """
        self.llm_type = llm_type
        self._client = None
        
        # 自动从CONFIG获取API密钥
        if api_key is None:
            try:
                from src.config.gold_config import CONFIG
                if llm_type == "chatanywhere" and CONFIG.llm.chatanywhere_api_key:
                    api_key = CONFIG.llm.chatanywhere_api_key
                elif llm_type == "openai" and CONFIG.llm.openai_api_key:
                    api_key = CONFIG.llm.openai_api_key
            except ImportError:
                pass
        
        self._init_client(api_key)
    
    def _init_client(self, api_key: str = None):
        """初始化 LLM 客户端"""
        if self.llm_type == "chatanywhere":
            self._client = ChatAnywhereClient(api_key)
        elif self.llm_type == "openai":
            self._client = OpenAIClient(api_key)
        else:
            self._client = LocalLLMClient(api_key)
        
        logger.info(f"LLM 助手初始化完成 (type={self.llm_type})")
    
    def generate_summary_insight(self, analysis: GoldAnalysis) -> str:
        """
        生成核心结论摘要的深度解读
        
        Args:
            analysis: 黄金分析数据
            
        Returns:
            深度解读文本（Markdown格式）
        """
        prompt = f"""你是一位顶尖的贵金属量化分析师，服务于对冲基金。请基于以下数据，生成专业的黄金核心结论摘要解读。

【当前市场数据】
- 上海金 Au99.99 价格: ¥{analysis.current_price}/克 ({analysis.price_date})
- 历史分位: {analysis.historical_percentile:.1f}%
- 近期涨跌: 
  * 近5日: {analysis.period_returns.get('近5日', 'N/A')}
  * 近20日: {analysis.period_returns.get('近20日(1月)', analysis.period_returns.get('近20日', 'N/A'))}
  * 近60日: {analysis.period_returns.get('近60日(3月)', analysis.period_returns.get('近60日', 'N/A'))}
  * 近120日: {analysis.period_returns.get('近120日(6月)', analysis.period_returns.get('近120日', 'N/A'))}
  * 近252日: {analysis.period_returns.get('近252日(1年)', analysis.period_returns.get('近252日', 'N/A'))}

【技术指标】
- 20日波动率: {analysis.volatility_20d:.2f}%
- 60日波动率: {analysis.volatility_60d:.2f}%
- MA5: ¥{analysis.ma5:.2f}, MA20: ¥{analysis.ma20:.2f}, MA60: ¥{analysis.ma60:.2f}
- 60日高低: ¥{analysis.low_60d:.2f} - ¥{analysis.high_60d:.2f}

【核心驱动因子】
- 中国10年国债收益率: {analysis.bond_yield}%
- VIX恐慌指数: {analysis.vix}
- 美元指数: {analysis.dollar_index}
- 全球央行月度购金: {analysis.central_bank_buying}吨
- 中国黄金储备: {analysis.china_reserves}吨

**请使用Markdown格式输出**，包含以下章节：

### 📊 周期阶段判断
当前金价处于什么周期阶段（底部/上行/顶部/下行），量化依据是什么。

### ⚖️ 核心支撑与压制
列出2-3个最关键的支撑因素和2-3个最关键的压制因素，附量化数据。

### 📈 短中长期趋势
- **短期(1-5日)**：趋势判断+关键价位
- **中期(1-3月)**：趋势判断+核心逻辑
- **长期(6-12月)**：趋势判断+结构性因素

### 💎 一句话结论
用一句话总结当前金价的核心判断。

要求：专业、量化、无废话。所有判断必须有数据支撑。"""

        messages = [{"role": "user", "content": prompt}]
        return self._client.chat(messages)
    
    def generate_scenario_analysis(self, analysis: GoldAnalysis) -> str:
        """
        生成情景分析
        
        Args:
            analysis: 黄金分析数据
            
        Returns:
            情景分析文本（Markdown格式）
        """
        prompt = f"""你是一位顶尖的贵金属量化分析师。请为黄金未来走势生成详细的情景推演。

【当前状态】
- 价格: ¥{analysis.current_price}/克 ({analysis.price_date})
- 历史分位: {analysis.historical_percentile:.1f}%
- 60日区间: ¥{analysis.low_60d:.2f} - ¥{analysis.high_60d:.2f}
- 120日区间: ¥{analysis.low_120d:.2f} - ¥{analysis.high_120d:.2f}
- 10年国债收益率: {analysis.bond_yield}%
- 美元指数: {analysis.dollar_index}
- VIX: {analysis.vix}
- 央行购金: {analysis.central_bank_buying}吨/月

**请使用Markdown格式输出**，包含以下章节：

### 🟢 乐观情景（概率约25%）
- **触发条件**：具体哪些事件需要发生
- **核心变量变化**：利率/美元/VIX等如何变动
- **预期金价区间**：¥xxx - ¥xxx/克
- **走势描述**：1-2句话

### 🟡 基准情景（概率约55%）
- **触发条件**：
- **核心变量变化**：
- **预期金价区间**：¥xxx - ¥xxx/克
- **走势描述**：

### 🔴 悲观情景（概率约20%）
- **触发条件**：
- **核心变量变化**：
- **预期金价区间**：¥xxx - ¥xxx/克
- **走势描述**：

### 🎯 最可能情景判断
你判断最可能发生的情景及量化理由（2-3句话）。

要求：所有价格区间必须有具体数字，所有概率判断必须有逻辑依据。"""

        messages = [{"role": "user", "content": prompt}]
        return self._client.chat(messages)
    
    def generate_risk_analysis(self, analysis: GoldAnalysis) -> str:
        """
        生成风险分析
        
        Args:
            analysis: 黄金分析数据
            
        Returns:
            风险分析文本（Markdown格式）
        """
        prompt = f"""你是一位专业的风险管理专家，专注贵金属市场。请分析黄金投资的核心风险。

【当前市场状态】
- 价格: ¥{analysis.current_price}/克 ({analysis.price_date})
- 历史分位: {analysis.historical_percentile:.1f}%
- 20日波动率: {analysis.volatility_20d:.2f}%
- 60日波动率: {analysis.volatility_60d:.2f}%
- 国债收益率: {analysis.bond_yield}%
- 美元指数: {analysis.dollar_index}
- VIX: {analysis.vix}
- 央行购金: {analysis.central_bank_buying}吨/月

**请使用Markdown格式输出**，包含以下章节：

### ⚠️ 核心风险一：[风险名称]
- **触发条件**：具体量化条件
- **潜在影响**：价格变动幅度预估
- **监控阈值**：什么指标到什么数值时需要警惕
- **应对策略**：具体操作建议

### ⚠️ 核心风险二：[风险名称]
- **触发条件**：
- **潜在影响**：
- **监控阈值**：
- **应对策略**：

### 🛡️ 风险防控建议
2-3条具体的、可执行的风控建议。

要求：简洁量化，每个风险必须给出具体数值阈值，不要泛泛而谈。"""

        messages = [{"role": "user", "content": prompt}]
        return self._client.chat(messages)
    
    def generate_investment_suggestion(self, analysis: GoldAnalysis) -> str:
        """
        生成投资建议
        
        Args:
            analysis: 黄金分析数据
            
        Returns:
            投资建议文本（Markdown格式）
        """
        prompt = f"""你是一位专业的黄金投资顾问，服务于高净值客户。请基于以下数据给出黄金投资建议。

【当前状态】
- 价格: ¥{analysis.current_price}/克 ({analysis.price_date})
- 历史分位: {analysis.historical_percentile:.1f}%
- 近期表现: 
  * 近5日: {analysis.period_returns.get('近5日', 'N/A')}%
  * 近60日: {analysis.period_returns.get('近60日(3月)', analysis.period_returns.get('近60日', 'N/A'))}%
  * 近252日: {analysis.period_returns.get('近252日(1年)', analysis.period_returns.get('近252日', 'N/A'))}%

【技术位置】
- MA5: ¥{analysis.ma5:.2f} (当前价格{'高于' if analysis.current_price > analysis.ma5 else '低于'})
- MA20: ¥{analysis.ma20:.2f} (当前价格{'高于' if analysis.current_price > analysis.ma20 else '低于'})
- MA60: ¥{analysis.ma60:.2f} (当前价格{'高于' if analysis.current_price > analysis.ma60 else '低于'})
- 60日区间: ¥{analysis.low_60d:.2f} - ¥{analysis.high_60d:.2f}

【核心驱动】
- 国债收益率: {analysis.bond_yield}%
- 美元指数: {analysis.dollar_index}
- 央行购金: {analysis.central_bank_buying}吨/月
- VIX: {analysis.vix}

**请使用Markdown格式输出**，包含以下章节：

### 🎯 市场判断
当前市场状态（多头/空头/震荡），判断依据。

### 📍 入场策略
- **建议入场价位**：¥xxx/克（具体数字）
- **入场时机**：什么条件下可以入场
- **分批建仓建议**：如何分批

### 🛡️ 止损止盈
- **止损位**：¥xxx/克（跌破此价止损）
- **第一止盈位**：¥xxx/克
- **第二止盈位**：¥xxx/克

### 📊 仓位建议
- **保守型**：配置比例%
- **平衡型**：配置比例%
- **进取型**：配置比例%

### ⏰ 持有周期
建议的持有时间及调仓条件。

要求：所有价格和比例必须是具体数字，不要含糊表述。"""

        messages = [{"role": "user", "content": prompt}]
        return self._client.chat(messages)
    
    def generate_generic_analysis(self, analysis: GoldAnalysis, topic_title: str, topic_description: str) -> str:
        """
        生成通用分析内容
        
        Args:
            analysis: 黄金分析数据
            topic_title: 主题标题
            topic_description: 主题描述
            
        Returns:
            分析文本（Markdown格式）
        """
        prompt = f"""你是一位顶尖的贵金属量化分析师。请基于以下数据，为'{topic_title}'生成专业的分析内容。

【当前市场数据】
- 上海金 Au99.99 价格: ¥{analysis.current_price}/克 ({analysis.price_date})
- 历史分位: {analysis.historical_percentile:.1f}%
- 近期涨跌: 
  * 近5日: {analysis.period_returns.get('近5日', 'N/A')}
  * 近20日: {analysis.period_returns.get('近20日(1月)', analysis.period_returns.get('近20日', 'N/A'))}
  * 近60日: {analysis.period_returns.get('近60日(3月)', analysis.period_returns.get('近60日', 'N/A'))}
  * 近120日: {analysis.period_returns.get('近120日(6月)', analysis.period_returns.get('近120日', 'N/A'))}
  * 近252日: {analysis.period_returns.get('近252日(1年)', analysis.period_returns.get('近252日', 'N/A'))}

【技术指标】
- 20日波动率: {analysis.volatility_20d:.2f}%
- 60日波动率: {analysis.volatility_60d:.2f}%
- MA5: ¥{analysis.ma5:.2f}, MA20: ¥{analysis.ma20:.2f}, MA60: ¥{analysis.ma60:.2f}
- 60日高低: ¥{analysis.low_60d:.2f} - ¥{analysis.high_60d:.2f}
- 120日高低: ¥{analysis.low_120d:.2f} - ¥{analysis.high_120d:.2f}

【核心驱动因子】
- 中国10年国债收益率: {analysis.bond_yield}%
- VIX恐慌指数: {analysis.vix}
- 美元指数: {analysis.dollar_index}
- 全球央行月度购金: {analysis.central_bank_buying}吨
- 中国黄金储备: {analysis.china_reserves}吨

**请使用Markdown格式输出**，基于以下主题生成详细分析：

主题：{topic_title}
描述：{topic_description}

要求：
1. 专业、量化、无废话
2. 所有判断必须有数据支撑
3. 结构清晰，层次分明
4. 包含具体的数值和分析逻辑
5. 提供有价值的见解和结论"""

        messages = [{"role": "user", "content": prompt}]
        return self._client.chat(messages)


# ============================================================
# 兼容接口 (与 quant system 保持一致)
# ============================================================

class LLMDecisionHelper:
    """兼容 quant system 的接口"""
    
    def __init__(self, llm_type: str = "chatanywhere", api_key: str = None):
        if llm_type == "local":
            self._helper = LLMGoldHelper("local", api_key)
        else:
            self._helper = LLMGoldHelper(llm_type, api_key)
    
    def generate_stock_reasons(self, analysis: StockAnalysis) -> List[str]:
        """生成选股理由（兼容接口）"""
        prompt = f"""分析股票 {analysis.symbol} {analysis.name}:
价格: {analysis.price}, 涨跌幅: {analysis.change_pct}%, 成交量: {analysis.volume}
评分: {analysis.score}, 因子: {analysis.factors}

请给出 3-5 条简短的选股理由。"""
        
        messages = [{"role": "user", "content": prompt}]
        result = self._helper._client.chat(messages)
        # 解析结果为列表
        reasons = [r.strip() for r in result.split('\n') if r.strip() and len(r.strip()) > 10]
        return reasons[:5]


# ============================================================
# 模块信息（直接运行时展示）
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("LLM Gold Helper - LLM增强分析模块")
    print("=" * 60)
    print("\n[模块功能]")
    print("  1. 核心摘要解读 (generate_summary_insight)")
    print("     - 基于GRAM评分和技术指标生成核心结论")
    print("  2. 情景分析 (generate_scenario_analysis)")
    print("     - 基准/乐观/悲观三情景推演")
    print("  3. 风险分析 (generate_risk_analysis)")
    print("     - 压力测试、VaR、回撤风险")
    print("  4. 投资建议 (generate_investment_suggestion)")
    print("     - 仓位建议、操作时机、品种选择")
    print("\n[使用方式]")
    print("  生产环境通过报告生成器自动调用:")
    print("    from src.utils.llm_gold_helper import LLMGoldHelper")
    print("    helper = LLMGoldHelper('chatanywhere')  # 或 'local'")
    print("    insight = helper.generate_summary_insight(analysis_data)")
    print("\n[注意]")
    print("  本模块不包含任何模拟/随机数据，所有输入须为真实分析结果。")
    print("=" * 60)
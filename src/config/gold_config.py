#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金量化分析系统配置
与quant system的配置体系保持一致
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional

# 加载 .env 文件 (如果存在)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv 未安装时静默跳过

# ============================================================
# 项目路径
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent
GOLD_REPORT_DIR = PROJECT_ROOT / "gold_reports"
DATA_CACHE_DIR = PROJECT_ROOT / ".data_cache"

# ============================================================
# LLM配置 (与quant system保持一致)
# ============================================================
@dataclass
class LLMConfig:
    """LLM配置 - 支持多个API提供商"""
    llm_type: str = "openrouter"           # siliconflow / chatanywhere / openai / cherry / openrouter
    
    # SiliconFlow API (优先)
    siliconflow_api_key: Optional[str] = os.environ.get("SILICONFLOW_API_KEY")
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    siliconflow_model: str = "deepseek-ai/DeepSeek-R1"  # 可切换多个模型
    
    # ChatAnywhere API (fallback)
    chatanywhere_api_key: Optional[str] = None  # 环境变量: CHATANYWHERE_API_KEY
    chatanywhere_base_url: str = "https://api.chatanywhere.com.cn/v1"
    chatanywhere_model: str = "deepseek-chat"
    
    # OpenAI API (fallback)
    openai_api_key: Optional[str] = None       # 环境变量: OPENAI_API_KEY
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    
    # Cherry API (fallback)
    cherry_api_key: Optional[str] = None         # 环境变量: CHERRY_API_KEY
    cherry_base_url: str = "https://open.cherryin.net/v1"
    cherry_model: str = "deepseek/deepseek-v3.2"
    
    # OpenRouter API (已测试成功，免费模型)
    openrouter_api_key: Optional[str] = os.environ.get("OPENROUTER_API_KEY")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "baidu/cobuddy:free"  # 已测试成功

    temperature: float = 0.7
    timeout: int = 60  # 免费模型响应较慢，增加超时

# ============================================================
# 数据源配置
# ============================================================
@dataclass
class DataSourceConfig:
    """黄金数据源配置"""
    primary_source: str = "akshare"

    source_priority: Dict[str, List[str]] = field(default_factory=lambda: {
        'price': ['akshare', 'china_http', 'yinhe', 'goldapi', 'yahoo'],
        'historical': ['akshare', 'china_http', 'yahoo', 'yinhe', 'goldapi'],
        'macro': ['fred', 'akshare', 'china_http', 'openbb', 'yahoo', 'yinhe'],
        'sentiment': ['fred', 'akshare', 'china_http', 'yahoo', 'yinhe', 'openbb']
    })
    
    # API配置
    api_keys: Dict[str, str] = field(default_factory=lambda: {
        'fred': os.environ.get("FRED_API_KEY", ""),  # FRED API Key
    })
    
    # 缓存配置
    cache_enabled: bool = True
    cache_hours: int = 24                      # 缓存有效期（小时）
    cache_dir: str = str(DATA_CACHE_DIR)
    
    # 数据拉取
    default_days: int = 365 * 5                # 默认拉取5年数据
    min_data_rows: int = 60                    # 最少有效数据行数
    
    # 基准黄金
    benchmark_symbol: str = "Au99.99"          # 上海金标准合约
    
    # 数据质量配置
    min_data_quality: float = 0.8              # 最低数据质量要求
    max_retry_attempts: int = 3                # 最大重试次数

# ============================================================
# 数据质量配置
# ============================================================
@dataclass
class DataQualityConfig:
    """数据质量配置"""
    # 数据完整性阈值
    completeness_threshold: float = 0.95
    
    # 数据时效性阈值（分钟）
    timeliness_threshold: int = 15
    
    # 数据一致性阈值
    consistency_threshold: float = 0.9
    
    # 异常值检测配置
    outlier_detection: bool = True
    outlier_threshold: float = 3.0              # 标准差倍数

# ============================================================
# 报告生成配置
# ============================================================
@dataclass
class ReportConfig:
    """报告生成配置"""
    # 颜色标准（中国股市标准）
    price_up_color: str = "#c0392b"            # 红色（上涨）
    price_down_color: str = "#27ae60"          # 绿色（下跌）
    
    # 报告设置
    include_llm_analysis: bool = True          # 是否包含LLM分析
    save_to_folder: bool = True               # 是否保存到文件夹
    auto_open_report: bool = True              # 是否自动打开报告
    
    # 图表设置
    chart_width: int = 800
    chart_height: int = 400
    show_trend_lines: bool = True

# ============================================================
# 技术分析配置
# ============================================================
@dataclass
class TechnicalConfig:
    """技术分析配置"""
    # 移动平均线
    ma_periods: List[int] = field(default_factory=lambda: [5, 20, 60])
    
    # 波动率计算
    volatility_periods: List[int] = field(default_factory=lambda: [20, 60])
    annual_trading_days: int = 252
    
    # 历史分位计算
    min_history_days: int = 30
    
    # 周期涨跌幅
    return_periods: Dict[str, int] = field(default_factory=lambda: {
        '近1日': 2,
        '近5日': 6,
        '近20日(1月)': 21,
        '近60日(3月)': 61,
        '近120日(6月)': 121,
        '近252日(1年)': 253
    })

# ============================================================
# 全局配置实例
# ============================================================
class GoldConfig:
    """全局配置管理器"""
    
    def __init__(self):
        self.llm = LLMConfig()
        self.data = DataSourceConfig()
        self.report = ReportConfig()
        self.technical = TechnicalConfig()
        self.quality = DataQualityConfig()
        
        # 从环境变量更新（可覆盖默认密钥）
        self.update_from_env()
        
        # 确保目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        GOLD_REPORT_DIR.mkdir(parents=True, exist_ok=True)
        DATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    def update_from_env(self):
        """从环境变量更新配置"""
        import os
        
        # LLM API Keys
        if os.environ.get("CHATANYWHERE_API_KEY"):
            self.llm.chatanywhere_api_key = os.environ.get("CHATANYWHERE_API_KEY")
        
        if os.environ.get("OPENAI_API_KEY"):
            self.llm.openai_api_key = os.environ.get("OPENAI_API_KEY")
        
        if os.environ.get("CHERRY_API_KEY"):
            self.llm.cherry_api_key = os.environ.get("CHERRY_API_KEY")
        
        # OpenRouter API Key
        if os.environ.get("OPENROUTER_API_KEY"):
            self.llm.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
        
        # 数据源API Keys
        if os.environ.get("YINHEDATA_API_KEY"):
            self.data.api_keys['yinhe'] = os.environ.get("YINHEDATA_API_KEY")
        
        if os.environ.get("GOLDAPI_API_KEY"):
            self.data.api_keys['goldapi'] = os.environ.get("GOLDAPI_API_KEY")
        
        # FRED (美联储经济数据)
        if os.environ.get("FRED_API_KEY"):
            self.data.api_keys['fred'] = os.environ.get("FRED_API_KEY")
        
        # 数据源配置
        if os.environ.get("GOLD_CACHE_HOURS"):
            self.data.cache_hours = int(os.environ.get("GOLD_CACHE_HOURS"))
        
        if os.environ.get("GOLD_PRIMARY_SOURCE"):
            self.data.primary_source = os.environ.get("GOLD_PRIMARY_SOURCE")
        
        # 报告配置
        if os.environ.get("GOLD_NO_LLM"):
            self.report.include_llm_analysis = False


# 全局配置实例 (懒加载)
_CONFIG: Optional[GoldConfig] = None


def get_config() -> GoldConfig:
    """获取全局配置单例 (懒加载)"""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = GoldConfig()
    return _CONFIG


def __getattr__(name):
    """模块级向后兼容: from src.config.gold_config import CONFIG 仍然可用"""
    if name == 'CONFIG':
        return get_config()
    raise AttributeError(f"module 'src.config.gold_config' has no attribute '{name}'")
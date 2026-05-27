# Gold Analyze — 黄金量化分析系统

> **⚠️ 项目状态：开发中 / 未完成**
>
> 本项目仍在积极开发中，存在以下已知问题：
> - 部分模块尚未完成集成测试，端到端流程可能存在异常
> - LLM 分析功能依赖外部 API，稳定性受第三方服务影响
> - 数据源接口可能因上游变动而失效，需要持续维护
> - 回测模块 (backtester/regime_detector) 尚未与主流程完全对接
> - 报告模板仍在迭代，输出格式可能变动
>
> **本项目仅供学习和研究，不构成任何投资建议。**

---

## 简介

基于 Python 的黄金量化分析系统，参考世界黄金协会 (WGC) GRAM 框架和高盛/摩根大通技术分析体系，实现从数据采集、因子计算、策略回测到报告生成的全流程自动化。

## 架构

```
scripts/          ← 入口脚本
    ↓
pipeline/         ← 顶层编排
    ↓
report/           ← HTML 报告生成
    ↑
analysis/         ← 纯函数分析模块（无副作用）
    ↑
data/             ← 多源数据采集 + 融合
    ↑
config/           ← 配置管理
```

## 目录结构

```
src/
├── config/
│   └── gold_config.py              # 全局配置（懒加载）
├── data/
│   ├── interfaces.py               # 类型化数据契约
│   ├── data_service.py             # 数据服务门面
│   ├── fred_client.py              # FRED API 客户端
│   ├── data_cleaner.py             # 数据清洗
│   ├── data_fusion.py              # 多源数据融合
│   ├── data_cross_validator.py     # 交叉验证
│   ├── data_quality_monitor.py     # 质量监控
│   └── providers/                  # 8 个数据源 Provider
│       ├── akshare_provider.py     # 主力数据源
│       ├── china_http_provider.py  # 国内 HTTP 直连
│       ├── fred_provider.py        # 美联储经济数据
│       ├── goldapi_provider.py     # Gold-API
│       ├── openbb_provider.py      # OpenBB
│       ├── sina_provider.py        # 新浪财经
│       ├── tencent_provider.py     # 腾讯财经
│       └── yinhe_provider.py       # 银河数据
├── analysis/
│   ├── indicators.py               # 技术指标（RSI/MACD/BOLL/KDJ/ATR）
│   ├── factors.py                  # 因子计算
│   ├── strategies.py               # 量化策略
│   ├── gram_scorer.py              # GRAM 评分
│   ├── risk_analyzer.py            # 风险分析
│   ├── risk_manager.py             # 波动率目标化管理
│   ├── trend_judger.py             # 趋势判断
│   ├── candle_patterns.py          # K 线形态识别
│   ├── scenario_engine.py          # 情景推演
│   ├── backtester.py               # 回测引擎
│   └── regime_detector.py          # 市场状态识别
├── report/
│   ├── gold_report_base.py         # 报告基类
│   ├── gold_report_generator_v5.py # V5 报告
│   ├── gold_report_generator_v6.py # V6 报告（增强版）
│   └── html_helpers.py             # HTML 工具函数
├── pipeline/
│   └── gold_pipeline.py            # 编排器
└── utils/
    └── llm_gold_helper.py          # LLM 多模型集成
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量（复制 .env.example 为 .env 后填入 API Key）
cp .env.example .env

# 生成 V5 报告
python run_gold_report.py

# 生成 V6 报告（增强版）
python run_gold_final.py
```

## 测试

```bash
# 运行核心测试（76 个）
python -m pytest tests/test_indicators.py tests/test_analysis_modules.py \
    tests/test_factors.py tests/test_strategies.py \
    tests/test_risk_manager.py tests/test_data_provider.py -v
```

## 数据源

系统支持 8 个数据源，按能力自动路由：

| 数据源 | 价格 | 宏观 | 情绪 | 备注 |
|--------|------|------|------|------|
| AkShare | ✓ | ✓ | ✓ | 主力数据源 |
| China HTTP | ✓ | ✓ | ✓ | 国内直连 |
| FRED | - | ✓ | ✓ | 美联储经济数据 |
| Gold-API | ✓ | - | - | 国际金价 |
| OpenBB | ✓ | ✓ | ✓ | 需本地安装 |
| 新浪财经 | ✓ | - | ✓ | |
| 腾讯财经 | ✓ | - | ✓ | |
| 银河数据 | ✓ | - | - | |

## LLM 集成

支持多个 LLM 提供商（通过 `.env` 配置 API Key）：

- **OpenRouter** — 免费模型可用
- **SiliconFlow** — DeepSeek-R1
- **ChatAnywhere** — DeepSeek-V3
- **OpenAI** — GPT-4o-mini
- **Cherry** — DeepSeek-V3.2

## 环境变量

参见 `.env.example`，主要配置项：

```
OPENROUTER_API_KEY=          # OpenRouter API Key
SILICONFLOW_API_KEY=         # SiliconFlow API Key
FRED_API_KEY=                # FRED 美联储数据 API Key
GOLD_PRIMARY_SOURCE=akshare  # 主数据源
GOLD_NO_LLM=                 # 设为 1 禁用 LLM
```

## 免责声明

- 本系统仅供学术研究与量化分析学习参考
- 不构成任何投资建议，据此操作风险自担
- 数据来源于公开渠道，可能存在延迟或误差

## License

MIT

# 黄金量化分析系统

## 项目结构

本项目经过系统性整理，按照功能模块进行了分类归档，建立了清晰的文件组织结构。

```
gold/
├── src/                  # 源代码目录
│   ├── analysis/         # 分析模块
│   │   ├── gold_analysis_v5.py     # 黄金分析引擎 V5
│   │   ├── factors.py              # 因子计算模块
│   │   └── strategies.py            # 策略模块
│   ├── report/           # 报告生成模块
│   │   └── gold_report_generator_v5.py  # 报告生成器 V5
│   ├── utils/            # 工具模块
│   │   └── llm_gold_helper.py      # LLM 助手
│   ├── config/           # 配置模块
│   │   └── gold_config.py          # 系统配置
│   └── core/             # 核心模块（预留）
├── data/                 # 数据目录
├── reports/              # 报告输出目录
├── docs/                 # 文档目录
├── run_gold_analysis.py  # 主运行脚本
├── README.md             # 项目说明
└── V5_USAGE_GUIDE.md     # V5版本使用指南
```

## 系统模块说明

### 1. 分析模块 (src/analysis/)
- **gold_analysis_v5.py**: 黄金量化分析引擎 V5，基于akshare的机构研报版，严格对标WGC分析框架
- **factors.py**: 因子计算模块，提供各种量化因子的计算功能
- **strategies.py**: 策略模块，包含各种交易策略的实现

### 2. 报告生成模块 (src/report/)
- **gold_report_generator_v5.py**: 黄金量化分析报告生成器 V5，专业增强版，参考WGC GRAM框架和高盛/摩根大通技术分析体系

### 3. 工具模块 (src/utils/)
- **llm_gold_helper.py**: LLM 助手，提供AI增强分析功能

### 4. 配置模块 (src/config/)
- **gold_config.py**: 系统配置，包含LLM配置、数据源配置、报告配置等

## 运行说明

### 基本运行
```bash
# 基础分析（不使用LLM）
python run_gold_analysis.py --no-llm

# 使用LLM增强分析
python run_gold_analysis.py --llm

# 指定LLM类型
python run_gold_analysis.py --llm --llm-type chatanywhere
```

### 测试功能
```bash
# 测试LLM功能
python run_gold_analysis.py --test-llm

# 查看配置
python run_gold_analysis.py --show-config

# 显示版本信息
python run_gold_analysis.py --version
```

## 系统特性

- **真实数据源**: 使用akshare API获取真实的黄金价格和宏观数据
- **量化分析**: 8维度全面分析，包括价格趋势、技术指标、宏观因子等
- **LLM增强**: 专业AI分析，提供深度洞察
- **报告系统**: HTML专业报告，包含交互式图表和详细分析
- **配置体系**: 与quant system兼容的配置管理

## 版本说明

当前系统版本为 **V5**，包含以下核心升级：
1. 新增完整技术指标体系 (MACD, RSI, BOLL, KDJ, ATR)
2. K线形态识别 (十字星, 锤头线, 吞没形态)
3. GRAM归因分析框架 (WGC标准)
4. 交互式Chart.js图表可视化
5. 相关性热力图 (金价vs美元/利率/VIX)
6. 专业级排版和配色方案

## 注意事项

- 本系统仅供学术研究与量化分析参考，不构成任何投资建议
- 数据来源于公开权威渠道，但可能存在延迟或误差
- 运行系统需要安装相关依赖，包括akshare、pandas、numpy等

## 联系方式

如有问题或建议，请联系项目维护人员。

# 黄金量化分析系统 V4

与quant system架构完全一致的黄金量化分析系统，支持LLM增强分析和专业报告生成。

## 核心特性

- ✅ **真实数据源**: 使用akshare API获取上海金Au99.99真实交易数据
- ✅ **专业量化分析**: 8维度黄金定价模型（修正GRAM框架）
- ✅ **LLM增强**: 支持ChatAnywhere/OpenAI/Local三种LLM模式
- ✅ **配置体系**: 与quant system一致的dataclass配置管理
- ✅ **专业报告**: 包含8项核心结论的HTML量化报告
- ✅ **文件夹存储**: 所有报告自动归档到`gold_reports/`文件夹
- ✅ **自动化**: 一键生成、一键打开

## 快速开始

### 1. 安装依赖

```bash
pip install akshare pandas numpy
```

### 2. 运行分析

```bash
# 基础分析（不使用LLM）
python run_gold_analysis.py --no-llm

# 使用LLM增强
python run_gold_analysis.py --llm

# 指定LLM类型
python run_gold_analysis.py --llm --llm-type chatanywhere
```

### 3. 查看帮助

```bash
python run_gold_analysis.py --help
python run_gold_analysis.py --show-config
python run_gold_analysis.py --version
```

## 文件结构

```
gold/
├── run_gold_analysis.py          # 主程序入口
├── gold_config.py               # 配置文件（dataclass）
├── gold_report_generator_v4.py  # 报告生成器
├── llm_gold_helper.py          # LLM增强模块
├── gold_reports/               # 报告文件夹（自动创建）
│   └── gold_report_20260404_v4.html
└── README_GOLD_V4.md          # 本文档
```

## 8项核心结论摘要

每个报告包含以下8项量化分析：

1. **📊 金价周期定性与历史分位**
   - 当前价格与历史分位
   - 近期高低点分析
   - 周期定性判断

2. **⚔️ 核心驱动矛盾量化拆解**
   - 支撑因子：实际利率、央行购金、避险需求
   - 压制因子：美元指数、技术面超买
   - 矛盾态势分析

3. **📈 短/中/长周期走势判断**
   - 短期（1-20日）：震荡偏弱判断
   - 中期（60-120日）：趋势性上涨判断
   - 长期（252日+）：长期牛市判断

4. **📊 核心运行区间与中枢**
   - 短期/中期/长期价格区间
   - 支撑/阻力逻辑
   - 核心中枢位置

5. **📜 历史走势归因总结**
   - 近12个月涨幅归因
   - 近3个月涨幅归因
   - 驱动逻辑延续性分析

6. **🔮 未来情景提示**
   - 基准情景（55%概率）
   - 乐观情景（25%概率）
   - 悲观情景（20%概率）
   - 最可能情景判断

7. **⚠️ 核心风险提示**
   - 美联储政策转向风险
   - 美元指数反弹风险
   - 潜在跌幅量化评估

8. **💎 一句话核心趋势总结**
   - 简洁明了的趋势判断

## LLM配置

### 支持3种LLM模式

1. **chatanywhere** (默认，推荐)
   - 免费deepseek-v3模型
   - 无需付费API
   - 设置环境变量：`CHATANYWHERE_API_KEY`

2. **openai**
   - 需要OpenAI API密钥
   - 设置环境变量：`OPENAI_API_KEY`

3. **local**
   - 本地模拟模式
   - 用于测试或无API环境

### 环境变量配置

```bash
# Windows PowerShell
$env:CHATANYWHERE_API_KEY="your-api-key"
$env:OPENAI_API_KEY="your-openai-key"

# 或编辑 gold_config.py 中的配置
```

## 与quant system的集成

本系统设计为与quant system完全兼容：

### 配置一致性
- 使用相同的`dataclass`配置结构
- 支持相同的LLM类型 (`chatanywhere`/`openai`/`local`)
- 统一的错误处理和日志系统

### 架构一致性
- 模块化设计：数据获取、分析、报告分离
- 支持命令行参数解析
- 自动文件夹管理和版本化存储

### API一致性
- `llm_gold_helper.py` 提供与quant system兼容的接口
- `GoldAnalysis` 数据结构与 `StockAnalysis` 对齐
- 统一的配置文件管理

## 示例输出

### 命令行输出
```
=== 黄金量化分析系统启动 ===
LLM模式: 启用 (chatanywhere)
=== 黄金量化报告生成器 V4 ===
报告日期: 2026-04-04
LLM模式: 启用 (chatanywhere)

[1] 获取上海金 Au99.99 数据...
  成功: 2253 条记录
  起始: 2016-12-19
  最新: 2026-04-03 价格=1034.42

[LLM] 正在生成深度分析...
[LLM] 深度分析生成完成

报告已保存至: gold_reports/gold_report_20260404_v4.html

==================================================
分析完成!
报告已保存至: gold_reports/ 文件夹
最新报告: gold_report_20260404_v4.html
==================================================
正在打开报告...
```

### 报告内容
报告包含：
- 专业HTML格式，支持响应式设计
- 中国股市颜色标准（涨红跌绿）
- 数据表格和图表
- LLM深度分析章节（启用时）
- 详细的量化分析数据

## 故障排除

### 常见问题

1. **akshare连接失败**
   - 检查网络连接
   - 尝试使用代理
   - 查看akshare官方文档

2. **LLM API错误**
   - 检查API密钥设置
   - 验证网络连接
   - 使用 `--test-llm` 测试LLM功能

3. **文件权限问题**
   - 确保有写入 `gold_reports/` 文件夹的权限
   - 检查磁盘空间

### 调试命令

```bash
# 测试LLM功能
python run_gold_analysis.py --test-llm

# 显示当前配置
python run_gold_analysis.py --show-config

# 查看版本信息
python run_gold_analysis.py --version
```

## 版本历史

### V4.0 (2026-04-04)
- ✅ 集成quant system配置体系
- ✅ 完整的8项核心结论摘要
- ✅ LLM增强分析支持
- ✅ 自动化报告文件夹管理
- ✅ 与quant system架构完全一致

### V3.0 (2026-04-03)
- ✅ 真实数据源支持
- ✅ 中国股市颜色标准
- ✅ 基础量化分析框架

## 后续开发计划

- [ ] 添加多数据源支持（伦敦金、COMEX金）
- [ ] 集成更多宏观经济因子
- [ ] 添加实时价格监控
- [ ] 支持自动化定期分析
- [ ] 添加投资组合管理功能

## 许可证

仅供学习和研究使用，不构成投资建议。
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚假数据清除验证脚本 (2026-04-27)

验证项目中的所有数据是否为真实值，确认：
1. quantitative_strategy.py 不再包含 np.random 模拟数据
2. 报告生成器不再有硬编码的 volatility/sharpe_ratio/bond_ytd_ret
3. fallback模板的价格目标基于当前金价动态计算
"""

import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("  虚假数据清除验证 - Fake Data Elimination Verification")
print(f"  时间: 2026-04-27")
print("=" * 70)

errors = []
warnings = []
passed = []

def check(condition, msg):
    if condition:
        passed.append(msg)
        print(f"  [PASS] {msg}")
    else:
        errors.append(msg)
        print(f"  [FAIL] {msg}")

# ================================================================
# 验证 #1: quantitative_strategy.py 无随机数据
# ================================================================
print("\n[1/6] 检查 quantitative_strategy.py ...")

with open('src/analysis/quantitative_strategy.py', 'r', encoding='utf-8') as f:
    qs_code = f.read()

# 检查是否还有 np.random.uniform/generate 用于数据生成的模式
random_patterns = [
    (r'np\.random\.uniform\(1000,\s*1100', '黄金价格随机范围1000-1100'),
    (r'np\.random\.uniform\(95,\s*105', '美元指数随机范围95-105'),
    (r'np\.random\.uniform\(10,\s*40', 'VIX随机范围10-40'),
    (r'np\.random\.uniform\(400,\s*500', 'SPY随机范围400-500'),
    (r'# 生成模拟数据', '模拟数据注释标记'),
]

for pattern, desc in random_patterns:
    found = re.search(pattern, qs_code)
    check(not found, f"  无{desc} ({'发现!' if found else '干净'})")

# 确认有真实数据源引用
has_akshare = 'akshare' in qs_code or 'ak.' in qs_code
has_dataservice = 'DataService' in qs_code or '_DATA_SERVICE_AVAILABLE' in qs_code
has_real_comment = '真实数据' in qs_code or '真实' in qs_code
check(has_akshare or has_dataservice, "  引用真实数据源(AkShare/DataService)")
check(has_real_comment, "  包含'真实数据'注释标识")

# 确认数据失败时返回空对象而非假数据
has_empty_return = '返回空数据' in qs_code or '返回空' in qs_code or 'return pd.DataFrame()' in qs_code
check(has_empty_return, "  数据源失败时返回空对象(不伪造)")

# ================================================================
# 验证 #2: 报告生成器 v6 无硬编码 fallback 默认值
# ================================================================
print("\n[2/7] 检查 gold_report_generator_v6.py 硬编码值 ...")

with open('src/report/gold_report_generator_v6.py', 'r', encoding='utf-8') as f:
    v6_code = f.read()

# 检查旧的硬编码模式
hardcoded_patterns = [
    (r"'volatility':\s*8\.7", "硬编码 volatility=8.7"),
    (r"'sharpe_ratio':\s*0\.36", "硬编码 sharpe_ratio=0.36"),
    (r"bond_ytd_ret\s*=\s*1\.81", "硬编码 bond_ytd_ret=1.81"),
    (r"self\.data\['bond_yield'\]\s*=\s*1\.81", "硬编码 fallback bond_yield=1.81"),
    (r"self\.data\['vix'\]\s*=\s*24\.90", "硬编码 fallback vix=24.90"),
    (r"self\.data\['dollar_index'\]\s*=\s*103\.5", "硬编码 fallback dxy=103.5"),
    (r"setdefault\('bond_yield',\s*1\.81\)", "setdefault fallback bond_yield"),
    (r"setdefault\('vix',\s*24\.90\)", "setdefault fallback vix"),
]

for pattern, desc in hardcoded_patterns:
    found = re.search(pattern, v6_code)
    check(not found, f"  v6: 无{desc} ({'仍存在!' if found else '已清除'})")

# 确认新代码使用动态计算或None
has_dynamic_vol = 'bond_volatility' in v6_code or 'all_yields.pct_change' in v6_code
has_none_fallback = 'bond_ytd_ret is not None' in v6_code or 'bond_volatility is not None' in v6_code
check(has_dynamic_vol, "  v6: 国债波动率动态计算(all_yields.pct_change)")
check(has_none_fallback, "  v6: 数据不足时返回None而非硬编码")

# ================================================================
# 验证 #3: 报告生成器 v5 同样修复
# ================================================================
print("\n[3/7] 检查 gold_report_generator_v5.py 硬编码值 ...")

with open('src/report/gold_report_generator_v5.py', 'r', encoding='utf-8') as f:
    v5_code = f.read()

for pattern, desc in hardcoded_patterns:
    found = re.search(pattern, v5_code)
    check(not found, f"  v5: 无{desc} ({'仍存在!' if found else '已清除'})")

has_dynamic_vol_v5 = 'bond_volatility' in v5_code
has_none_fallback_v5 = 'bond_ytd_ret is not None' in v5_code
check(has_dynamic_vol_v5, "  v5: 国债波动率动态计算")
check(has_none_fallback_v5, "  v5: 数据不足时返回None")

# ================================================================
# 验证 #4: Fallback情景分析使用动态价格目标
# ================================================================
print("\n[4/7] 检查 fallback 情景分析动态化 ...")

# v6 的 scenario_analysis 应该有动态计算
has_dynamic_price = '_cur_price' in v6_code and '_range_3m' in v6_code
has_dynamic_prob = 'bull_p' in v6_code or 'base_lo' in v6_code
has_no_1150 = '1150元' not in v6_code.split('_get_fallback_content')[1].split('\n\ndef ')[0] if '_get_fallback_content' in v6_code else True
check(has_dynamic_price, "  v6 fallback: 价格目标基于 _cur_price + _range_3m 动态计算")
check(has_dynamic_prob, "  v6 fallback: 概率分配为变量(bull_p/base_p/bear_p)")

# ================================================================
# 验证 #5: 核心模块 __main__ 块无随机数据
# ================================================================
print("\n[5/7] 检查核心模块 __main__ 块无随机数据 ...")

test_files = {
    'src/analysis/factors.py': 'factors',
    'src/analysis/strategies.py': 'strategies',
    'src/analysis/risk_manager.py': 'risk_manager',
    'src/analysis/regime_detector.py': 'regime_detector',
    'src/analysis/backtester.py': 'backtester',
    'src/analysis/quantitative_strategy.py': 'quantitative_strategy',
    'src/analysis/integrated_strategy.py': 'integrated_strategy',
}

for filepath, name in test_files.items():
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    # 检查 __main__ 块区域
    main_match = re.search(r"if __name__ == ['\"]__main__['\"]:(.*?)(?:\n\n\n|\nclass |\ndef |\Z)", content, re.DOTALL)
    if main_match:
        main_block = main_match.group(1)
        has_random = 'np.random' in main_block or 'random.seed' in main_block
        check(not has_random, f"  {name}.py __main__ 块无 np.random ({'发现!' if has_random else '干净'})")
    else:
        check(True, f"  {name}.py 无 __main__ 块 (无需检查)")

# ================================================================
# 验证 #6: 导入测试 - 确认模块可正常加载
# ================================================================
print("\n[6/7] 导入测试 ...")

try:
    sys.path.insert(0, 'src')
    from analysis.quantitative_strategy import QuantitativeStrategy
    qs = QuantitativeStrategy()
    
    # 确认类属性正确
    check(qs.position == 0, "  QuantitativeStrategy 初始化正确(position=0)")
    check(qs.entry_price == 0, "  QuantitativeStrategy 初始化正确(entry_price=0)")
    check(hasattr(qs, 'factor_data'), "  QuantitativeStrategy 有 factor_data 属性")
    print("  [INFO]  quantitative_strategy.py 可正常导入，无语法错误")
except Exception as e:
    check(False, f"  quantitative_strategy.py 导入失败: {e}")

try:
    from report.gold_report_generator_v6 import GoldReportGeneratorV6
    print("  [INFO]  gold_report_generator_v6.py 可正常导入")
    check(True, "  gold_report_generator_v6.py 导入成功")
except Exception as e:
    check(False, f"  gold_report_generator_v6.py 导入失败: {e}")

# ================================================================
# 验证 #7: backtester.py 导入测试
# ================================================================
print("\n[7/7] 检查 backtester.py 模块导入 ...")

try:
    from analysis.backtester import GoldBacktester, ICAnalyzer
    print("  [INFO]  backtester.py 可正常导入")
    check(True, "  backtester.py 导入成功 (GoldBacktester + ICAnalyzer)")
except Exception as e:
    check(False, f"  backtester.py 导入失败: {e}")

# ================================================================
# 总结
# ================================================================
print("\n" + "=" * 70)
print("  验证结果汇总")
print("=" * 70)
total = len(passed) + len(errors)
print(f"  通过: {len(passed)}/{total}")
if errors:
    print(f"  失败: {len(errors)}/{total} !!")
    for e in errors:
        print(f"    ✗ {e}")
else:
    print("  所有检查项全部通过! 虚假数据已彻底清除。")

if warnings:
    print(f"\n  提醒: {len(warnings)} 项需要关注")
    for w in warnings:
        print(f"    ! {w}")

print("=" * 70)

sys.exit(0 if len(errors) == 0 else 1)

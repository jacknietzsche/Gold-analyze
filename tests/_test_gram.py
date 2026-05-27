#!/usr/bin/env python3
"""测试GRAM评分系统的数据获取和计算逻辑"""
import sys
sys.path.insert(0, 'src')

from report.gold_report_generator_v6 import GoldReportGeneratorV6

print("=" * 60)
print("GRAM评分系统检查")
print("=" * 60)

# 创建生成器（不使用LLM）
g = GoldReportGeneratorV6(use_llm=False)

# 获取数据
print("\n[1] 获取宏观数据...")
g.fetch_all_data()

# 检查数据
print("\n[2] 数据获取检查:")
print(f"  国债收益率: {g.data.get('bond_yield')}%")
print(f"  VIX: {g.data.get('vix')}")
print(f"  美元指数: {g.data.get('dollar_index')}")
print(f"  央行购金: {g.data.get('central_bank_buying')}吨/月")
print(f"  中国储备: {g.data.get('china_reserves')}吨")

# 检查数据是否真实
print("\n[3] 数据真实性验证:")
bond = g.data.get('bond_yield')
vix = g.data.get('vix')
dxy = g.data.get('dollar_index')
cb = g.data.get('central_bank_buying')

print(f"  国债收益率: {'真实' if bond != 1.81 else '默认值'} ({bond}%)")
print(f"  VIX: {'真实' if vix != 24.90 else '默认值'} ({vix})")
print(f"  美元指数: {'真实' if dxy != 103.5 else '默认值'} ({dxy})")
print(f"  央行购金: {'真实' if cb != 45 else '默认值'} ({cb}吨/月)")

# 计算GRAM评分
print("\n[4] 计算GRAM评分...")
g.calculate_gram_factors()
gram = g.data.get('gram', {})

print(f"\n[5] GRAM评分结果:")
print(f"  总分: {gram.get('total_score')}/10")
print(f"  展望: {gram.get('outlook')}")
print(f"  颜色: {gram.get('color')}")

print(f"\n[6] 各因子评分:")
oc = gram.get('opportunity_cost', {})
ru = gram.get('risk_uncertainty', {})
sd = gram.get('supply_demand', {})
mom = gram.get('momentum', {})

print(f"  机会成本 (40%): {oc.get('score')}/10")
print(f"    - 利率评分: {oc.get('rate_score')}")
print(f"    - 美元评分: {oc.get('dxy_score')}")
print(f"    - 国债收益率: {oc.get('bond_yield')}%")
print(f"    - 美元指数: {oc.get('dollar_index')}")
print(f"  风险不确定性 (25%): {ru.get('score')}/10")
print(f"    - VIX: {ru.get('vix')}")
print(f"  供需格局 (20%): {sd.get('score')}/10")
print(f"    - 央行购金: {sd.get('central_bank_buying')}吨/月")
print(f"  趋势动能 (15%): {mom.get('score')}/10")
print(f"    - 1日收益: {mom.get('r1d')}%")
print(f"    - 5日收益: {mom.get('r5d')}%")
print(f"    - 20日收益: {mom.get('r20d')}%")
print(f"    - 平均动量: {mom.get('avg_momentum')}%")

# 计算验证
print(f"\n[7] 评分计算验证:")
oc_score = oc.get('score', 0)
ru_score = ru.get('score', 0)
sd_score = sd.get('score', 0)
mom_score = mom.get('score', 0)
expected = oc_score * 0.40 + ru_score * 0.25 + sd_score * 0.20 + mom_score * 0.15
print(f"  期望总分: {round(expected, 1)}")
print(f"  实际总分: {gram.get('total_score')}")
print(f"  计算正确: {abs(expected - gram.get('total_score', 0)) < 0.1}")

print("\n" + "=" * 60)
print("检查完成")
print("=" * 60)

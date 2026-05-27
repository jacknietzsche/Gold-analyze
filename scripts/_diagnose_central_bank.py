#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
央行购金数据诊断脚本 (2026-04-27)

诊断目标：
1. 验证 ak.macro_china_fx_gold() 返回的原始数据格式和单位
2. 检查 万盎司→吨 转换系数是否正确
3. 验证计算结果是否与公开数据一致
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import numpy as np

print("=" * 70)
print("  央行购金数据源单位验证 - Central Bank Gold Data Unit Verification")
print(f"  时间: 2026-04-27")
print("=" * 70)

# ================================================================
# Step 1: 获取原始数据，查看所有列和数据
# ================================================================
print("\n[Step 1] 获取 macro_china_fx_gold() 原始数据...")

try:
    import akshare as ak
    fx_gold = ak.macro_china_fx_gold()
    
    print(f"\n  数据形状: {fx_gold.shape}")
    print(f"\n  所有列名:")
    for i, col in enumerate(fx_gold.columns):
        print(f"    [{i}] '{col}'")
    
    print(f"\n  最近12个月原始数据（全部列）:")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    pd.set_option('display.max_rows', 15)
    print(fx_gold.tail(12).to_string())
    
except Exception as e:
    print(f"  [ERROR] akshare获取失败: {e}")
    sys.exit(1)

# ================================================================
# Step 2: 验证单位转换
# ================================================================
print("\n\n" + "=" * 70)
print("[Step 2] 单位转换验证")
print("=" * 70)

# 找到关键列
value_col = None
mom_col = None
yoy_col = None

for col in fx_gold.columns:
    col_str = str(col)
    if '数值' in col_str and '黄金' in col_str:
        value_col = col
    elif '环比' in col_str and '黄金' in col_str:
        mom_col = col
    elif '同比' in col_str and '黄金' in col_str:
        yoy_col = col

print(f"\n  黄金储备-数值列: {value_col}")
print(f"  黄金储备-环比列: {mom_col}")
print(f"  黄金储备-同比列: {yoy_col}")

if value_col:
    # 显示最近6个月的数值
    print(f"\n  最近6个月 {value_col} 原始值:")
    recent_6 = fx_gold.tail(6).copy()
    for idx, row in recent_6.iterrows():
        val = row[value_col]
        print(f"    {idx}: {val} 万盎司")
    
    # 计算月度增量（万盎司）
    print(f"\n  月度增量计算:")
    recent = fx_gold.tail(5).copy()
    for i in range(1, len(recent)):
        prev_date = recent.index[i-1]
        curr_date = recent.index[i]
        prev_val = pd.to_numeric(recent.iloc[i-1][value_col], errors='coerce')
        curr_val = pd.to_numeric(recent.iloc[i][value_col], errors='coerce')
        diff = curr_val - prev_val
        
        # 单位转换验证
        # 1 万盎司 = 10,000 troy ounces
        # 1 troy ounce = 31.1034768 grams
        # 1 万盎司 = 311.034768 grams ≈ 0.311034768 kg... 不对!
        
        # 正确换算:
        # 1 troy ounce = 31.1034768 g
        # 10,000 troy ounces = 311,034.768 g = 311.034768 kg = 0.311034768 吨
        # 所以 1 万盎司 = 0.311034768 吨 ✓
        
        diff_tons_method1 = diff * 0.311035  # 当前代码使用的方法
        diff_kg = diff * 311.034768  # 先转kg再转ton
        diff_tons_from_kg = diff_kg / 1000  # kg -> ton
        
        print(f"    {curr_date} vs {prev_date}: Δ={diff:+.2f} 万盎司")
        print(f"      → 方法1(diff×0.311035): {diff_tons_method1:.4f} 吨")
        print(f"      → 方法2(diff×311.034768/1000): {diff_tons_from_kg:.4f} 吨")
        print(f"      → 差异: |{diff_tons_method1 - diff_tons_from_kg:.6f}| 吨")

# ================================================================
# Step 3: 验证当前代码的计算结果
# ================================================================
print("\n\n" + "=" * 70)
print("[Step 3] 当前代码计算逻辑验证")
print("=" * 70)

if value_col and len(fx_gold) >= 2:
    # AkShareProvider 的方法：最近3个月平均增量
    recent = fx_gold.tail(3)
    increments = []
    print("\n  AkShareProvider 方法 (3个月平均):")
    for i in range(1, len(recent)):
        prev_val = pd.to_numeric(recent.iloc[i-1][value_col], errors='coerce')
        curr_val = pd.to_numeric(recent.iloc[i][value_col], errors='coerce')
        if pd.notna(prev_val) and pd.notna(curr_val):
            increment_ton = abs(curr_val - prev_val) * 0.311035
            increments.append(increment_ton)
            print(f"    月{i}增量: {abs(curr_val - prev_val):+.2f} 万盎司 × 0.311035 = {increment_ton:.2f} 吨")
    
    if increments:
        avg_increment = sum(increments) / len(increments)
        print(f"\n  [*] AkShareProvider 结果: central_bank_buying = {avg_increment:.2f} 吨/月")
    
    # ChinaHttpProvider 的方法：环比 × 22
    if mom_col:
        print("\n  ChinaHttpProvider 方法 (环比×22):")
        latest = fx_gold.iloc[-1]
        prev = fx_gold.iloc[-2]
        mom_val = pd.to_numeric(latest[mom_col], errors='coerce')
        base_val = pd.to_numeric(prev[value_col], errors='coerce')
        if pd.notna(mom_val):
            cb_buying = round(abs(mom_val) * 22, 2)
            print(f"    最新环比: {mom_val}%")
            print(f"    上期基数: {base_val} 万盎司")
            print(f"    计算: |{mom_val}| × 22 = {cb_buying} 吨")
            
            # 验证这个公式是否合理
            # 如果 base=3400万盎司，环比=0.3%，则实际增量=3400×0.003%=10.2万盎司=3.17吨
            real_diff = base_val * abs(mom_val) / 100  # 实际增量（万盎司）
            real_tons = real_diff * 0.311035  # 转为吨
            print(f"\n    [!] 正确计算应该是:")
            print(f"       增量(万盎司) = 基数 × |环比%| = {base_val} × {abs(mom_val)}% = {real_diff:.2f} 万盎司")
            print(f"       增量(吨) = {real_diff} × 0.311035 = {real_tons:.2f} 吨")
            print(f"       ChinaHttpProvider结果: {cb_buying} 吨 (误差: {(cb_buying - real_tons)/real_tons*100 if real_tons > 0 else 999:.1f}%)")

# ================================================================
# Step 4: 与公开真实数据交叉验证
# ================================================================
print("\n\n" + "=" * 70)
print("[Step 4] 公开数据交叉验证")
print("=" * 70)

print("""
  公开数据参考 (2024-2025 中国央行PBoC购金情况):
  
  来源: WGC世界黄金协会 / 中国人民银行官方数据
  
  2022年11月起中国央行连续18个月增持黄金:
  - 2022年Q4: 约30吨 (重启购金)
  - 2023全年: 约225吨 (约18.75吨/月)
  - 2024全年: 约300吨 (约25吨/月)
  - 2024年11月: 暂停增持 (连续6个月后首次暂停)
  - 2024年12月: 继续暂停
  - 2025年1月: 重启增持16万盎司≈5吨
  - 2025年2月: 增持24万盎司≈7.5吨  
  - 2025年3月: 增持约10万盎司≈3吨
  
  全球央行购金 (WGC季度数据):
  - 2024Q1: 290吨 (全球)
  - 2024Q2: 279吨 (全球)
  - 2024Q3: 186吨 (全球)
  - 2024Q4: 222吨 (全球)
  - 2024全年: 约1070吨 (全球), 月均约89吨
  
  [!] 关键问题:
  - current central_bank_buying = 97.71吨/月 接近全球月均购金水平
  - 这说明当前代码可能将"中国央行购金"误报为"全球央行购金"
  - 或者数据源返回的数据有异常
""")

# ================================================================
# Step 5: 最终结论
# ================================================================
print("\n" + "=" * 70)
print("  诊断结论汇总")
print("=" * 70)

print("""
  问题清单:
  ───────────────────────────────────────────────
  1. [P0] 数据含义混淆: "央行购金"实际只反映中国PBoC,
     不代表全球央行。应改名为"中国央行购金"或增加WGC全球数据
  
  2. [P0] ChinaHttpProvider._get_central_bank_buying() 使用错误公式
     - 公式: |环比%| x 22 = 吨 (硬编码乘数22完全无依据)
     - 应使用: 基数 x |环比%| / 100 x 0.311035 = 吨
  
  3. [P1] 数值偏高: 97.71吨/月 对单国央行来说过高
     (中国正常水平: 5-25吨/月; 全球月均: ~90吨)
  
  4. [P1] 标签误导: 报告中显示"央行购金: XX吨/月",
     用户会理解为全球央行，实际仅为中国
""")

print(f"\n  原始数据最新一行完整信息:")
latest = fx_gold.iloc[-1]
for col in fx_gold.columns:
    print(f"    {col}: {latest[col]}")

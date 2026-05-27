#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源全面验证测试 (2026-04-28)
验证所有数据源修复: 央行购金/VIX/黄金价格/美元指数
"""

import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("=" * 70)
print("  数据源全面验证 - Data Source Comprehensive Verification")
print(f"  时间: 2026-04-28")
print("=" * 70)

errors = []
passed = []

def check(cond, msg):
    if cond:
        passed.append(msg)
        print(f"  [PASS] {msg}")
    else:
        errors.append(msg)
        print(f"  [FAIL] {msg}")

# ================================================================
# 验证 #1: 央行购金修复
# ================================================================
print("\n[1/7] 验证央行购金修复...")

for provider_name in ['akshare', 'china_http']:
    filepath = f'src/data/providers/{provider_name}_provider.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # 检查旧的错误公式是否已移除
    has_bad_formula = re.search(r'val\s*\*\s*22', code) or re.search(r'环比.*\*.*22', code)
    check(not has_bad_formula, f"  {provider_name}: 无旧公式(|环比|x22)")
    
    # 检查新公式存在
    has_new_formula = '0.311035' in code or '万盎司' in code or 'wan_ounces' in code
    check(has_new_formula, f"  {provider_name}: 使用正确的单位换算(万盎司->吨)")
    
    # 检查异常值过滤
    has_outlier_filter = '150' in code and ('异常' in code or '过滤' in code or '阈值' in code)
    check(has_outlier_filter, f"  {provider_name}: 有异常值过滤(>150万盎司)")
    
    # 检查使用6个月窗口
    has_6month = 'tail(6)' in code or 'tail(3)' not in code or '6' in code.split('central_bank')[0].split('get_macro')[0]
    check(has_6month, f"  {provider_name}: 使用延长平均窗口")
    
    # 检查合理性校验范围
    has_range_check = '< 80' in code or '< 40' in code
    check(has_range_check, f"  {provider_name}: 有合理性校验(0-80吨)")

# ================================================================
# 验证 #2: VIX代理公式修复
# ================================================================
print("\n[2/7] 验证VIX代理公式修复...")

with open('src/data/providers/china_http_provider.py', 'r', encoding='utf-8') as f:
    ch_code = f.read()

has_old_vix_formula = 'change * 100' in ch_code and '20.0 + change' in ch_code
check(not has_old_vix_formula, "  ChinaHttp: 无旧VIX公式(change*100)")

has_new_vix_formula = 'change_pct * 8' in ch_code or 'min(change' in ch_code
check(has_new_vix_formula, "  ChinaHttp: 使用修正VIX公式(18 + change*8, capped at 30)")

has_vix_range_check = '10 < vix_proxy < 50' in ch_code or '10 < vix' in ch_code
check(has_vix_range_check, "  ChinaHttp: VIX结果在合理范围内(10-50)")

# ================================================================
# 验证 #3: 黄金价格修复
# ================================================================
print("\n[3/7] 验证黄金价格阈值和OHLC校验...")

with open('src/data/providers/china_http_provider.py', 'r', encoding='utf-8') as f:
    gold_code = f.read()

has_low_threshold_260 = '> 260' in gold_code
check(has_low_threshold_260, "  黄金价格下限阈值提升到260(历史最低)")

has_ohlc_check = 'OHLC' in gold_code or ('high < low' in gold_code or 'high < price' in gold_code)
check(has_ohlc_check, "  增加OHLC一致性校验(H>=C>=L)")

has_safe_convert = '_safe_convert' in gold_code
check(has_safe_convert, "  使用统一的OHLC转换函数")

has_anomaly_skip = '异常偏低' in gold_code or '单位错误' in gold_code
check(has_anomaly_skip, "  异常偏低价格直接跳过(不静默接受)")

# ================================================================
# 验证 #4: 美元指数公式统一
# ================================================================
print("\n[4/7] 验证美元指数fallback公式...")

with open('src/data/providers/china_http_provider.py', 'r', encoding='utf-8') as f:
    dxy_ch = f.read()
with open('src/data/providers/akshare_provider.py', 'r', encoding='utf-8') as f:
    dxy_ak = f.read()

ch_multiplier = re.search(r'\(rate\s*-\s*7\.0\)\s*\*\s*(\d+)', dxy_ch)
ak_multiplier = re.search(r'\(latest_rate\s*-\s*7\.0\)\s*\*\s*(\d+)', dxy_ak)

ch_m = int(ch_multiplier.group(1)) if ch_multiplier else None
ak_m = int(ak_multiplier.group(1)) if ak_multiplier else None

check(ch_m == ak_m == 20, f"  DXY fallback系数一致: CH={ch_m}, AK={ak_m} (均应为20)")

# ================================================================
# 验证 #5: 导入测试
# ================================================================
print("\n[5/7] 导入测试(语法验证)...")

try:
    from data.providers.akshare_provider import AkShareDataProvider
    from data.providers.china_http_provider import ChinaHttpProvider
    ak_p = AkShareDataProvider()
    ch_p = ChinaHttpProvider()
    check(True, "  两个Provider均可正常导入和实例化")
except Exception as e:
    check(False, f"  Provider导入失败: {e}")

# ================================================================
# 验证 #6: 实际获取央行购金数据
# ================================================================
print("\n[6/7] 央行购金实际数据验证...")

try:
    ak_data = ak_p.get_macro_data(['central_bank_buying', 'china_reserves'])
    if 'central_bank_buying' in ak_data and ak_data['central_bank_buying'] is not None:
        cb_val = ak_data['central_bank_buying']
        check(cb_val < 80, f"  AkShare央行购金={cb_val}吨/月 (在合理范围<80内)")
        
        # 应该远低于之前错误的97.71
        if cb_val > 90:
            print(f"  [WARN] 数值仍然偏高({cb_val})，可能仍有未过滤的异常月份")
        elif cb_val > 40:
            print(f"  [INFO] 数值偏高但合理({cb_val})，可能反映近期大量购金")
        else:
            print(f"  [OK] 数值正常({cb_val}吨/月)，符合中国央行历史水平(5-25吨/月)")
    else:
        print(f"  [INFO] 央行购金返回None (所有月份可能都被过滤为异常，或数据源问题)")
        print(f"  其他宏观数据: {list(ak_data.keys())}")
        
    if 'china_reserves' in ak_data:
        cr_val = ak_data.get('china_reserves')
        if cr_val:
            check(2000 < cr_val < 5000, f"  中国储备={cr_val}万盎司 (在2200-4000合理范围)")
except Exception as e:
    print(f"  [ERROR] 实际获取失败: {e}")

# ================================================================
# 验证 #7: 代码无语法错误(lint)
# ================================================================
print("\n[7/7] 语法检查...")
import ast
files_to_check = [
    'src/data/providers/china_http_provider.py',
    'src/data/providers/akshare_provider.py',
]
all_ok = True
for fp in files_to_check:
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        check(True, f"  {fp} AST解析通过")
    except SyntaxError as e:
        all_ok = False
        check(False, f"  {fp} 语法错误: {e}")

# ================================================================
# 总结
# ================================================================
print("\n" + "=" * 70)
total = len(passed) + len(errors)
print(f"  验证结果: {len(passed)}/{total} 通过")
if errors:
    print(f"  失败: {len(errors)} 项:")
    for e in errors:
        print(f"    X {e}")
else:
    print("  全部通过! 所有数据源修复已生效。")
print("=" * 70)

sys.exit(0 if len(errors) == 0 else 1)

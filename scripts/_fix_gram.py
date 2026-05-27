#!/usr/bin/env python3
"""修复gold_report_generator_v6.py中的语法错误和重复代码"""
import re

file_path = r"c:\Users\21471\WorkBuddy\gold\src\report\gold_report_generator_v6.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复1：第1415行语法错误 - 字典项之间缺少逗号
# 查找: 'r1d': r1d, 'r5d': r5d, 'r20d': r20d,
# 替换为: 'r1d': r1d, 'r5d': r5d, 'r20d': r20d,
old_pattern1 = "'r1d': r1d, 'r5d': r5d, 'r20d': r20d,"
new_pattern1 = "'r1d': r1d, 'r5d': r5d, 'r20d': r20d,"
if old_pattern1 in content:
    content = content.replace(old_pattern1, new_pattern1)
    print("[FIX] 修复了第1415行的语法错误")
else:
    print("[CHECK] 第1415行语法正确，无需修复")

# 修复2：删除第1162-1167行的重复代码
# 查找从 trend_signals.append({"type": "动量" 开始的多行重复代码
old_pattern2 = '''            trend_signals.append({"type": "动量", "signal": "明显下跌", "level": "bearish", "desc": f"近5日下跌{abs(r5d),1}%，短期承压"})
            trend_signals.append({'type': '动量', 'signal': '明显下跌', 'level': 'bearish', 'desc': f'近5日下跌{abs(r5d),1}%，短期承压'})
            trend_score -= 2
            trend_signals.append({"type": "动量", "signal": "小幅回调", "level": "neutral", "desc": f"近5日下跌{abs(r5d),1}%，正常调整"})
            trend_signals.append({"type": "动量", "signal": "小幅回调", "level": "neutral", "desc": f"近5日下跌{abs(r5d),1}%，正常调整"})
            trend_signals.append({'type': '动量', 'signal': '小幅回调', 'level': 'neutral', 'desc': f'近5日下跌{abs(r5d),1}%，正常调整'})'''

new_pattern2 = '''        else:
            if r5d > -3:
                trend_signals.append({'type': '动量', 'signal': '小幅回调', 'level': 'neutral', 'desc': f'近5日下跌{abs(r5d):.1f}%，正常调整'})
                trend_score -= 0.5
            else:
                trend_signals.append({'type': '动量', 'signal': '明显下跌', 'level': 'bearish', 'desc': f'近5日下跌{abs(r5d):.1f}%，短期承压'})
                trend_score -= 2'''

if old_pattern2 in content:
    content = content.replace(old_pattern2, new_pattern2)
    print("[FIX] 删除了重复代码，添加了正确的else分支逻辑")
else:
    print("[CHECK] 未找到重复代码，可能已修复")
    # 尝试查找并修复格式错误 {abs(r5d),1}
    content = content.replace('{abs(r5d),1}', '{abs(r5d):.1f}')
    print("[FIX] 修复了格式错误 {abs(r5d),1} -> {abs(r5d):.1f}")

# 写入修复后的内容
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n[OK] 文件修复完成")
print(f"请手动检查文件: {file_path}")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全测试 gold_report_generator_v6 的 LLM 集成
使用 subprocess 隔离运行，避免静默崩溃影响主进程
"""
import subprocess
import sys
import os
import json

print("=" * 60)
print("安全测试 GoldReportGeneratorV6 LLM 集成")
print("=" * 60)

# 测试脚本内容（将被 subprocess 执行）
test_script = r"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(r'__file__'), 'src'))

print("[Test] 阶段1: 导入模块...")
try:
    from report.gold_report_generator_v6 import GoldReportGeneratorV6
    print("[Test] ✅ 模块导入成功")
except Exception as e:
    print(f"[Test] ❌ 导入失败: {e}")
    sys.exit(1)

print("\n[Test] 阶段2: 创建报告生成器 (llm_type=openrouter)...")
try:
    gen = GoldReportGeneratorV6(llm_type='openrouter', use_llm=True)
    print("[Test] ✅ 生成器创建成功")
except Exception as e:
    print(f"[Test] ❌ 创建失败: {e}")
    sys.exit(1)

print("\n[Test] 阶段3: 测试 _call_llm_api 方法...")
try:
    prompt = "请用50个字介绍黄金投资的基本原则。"
    result = gen._call_llm_api(prompt, max_tokens=100)
    if result and len(result.strip()) > 10:
        print(f"[Test] ✅ LLM调用成功！返回 {len(result)} 字符")
        print(f"[Test] 内容预览: {result[:80]}...")
        sys.exit(0)
    else:
        print(f"[Test] ⚠️  LLM返回为空或太短: {result}")
        sys.exit(1)
except Exception as e:
    print(f"[Test] ❌ 调用失败: {type(e).__name__}: {e}")
    sys.exit(1)
"""

# 将测试脚本写入临时文件
test_file = r"C:\Users\21471\WorkBuddy\gold\_test_llm_subprocess.py"
with open(test_file, 'w', encoding='utf-8') as f:
    f.write(test_script)

print(f"\n📝 测试脚本已写入: {test_file}")
print(f"\n🚀 启动子进程测试（超时120秒）...\n")
print("-" * 60)

try:
    result = subprocess.run(
        [sys.executable, test_file],
        cwd=r"C:\Users\21471\WorkBuddy\gold",
        capture_output=True,
        text=True,
        timeout=120,
        encoding='utf-8'
    )
    
    print(result.stdout)
    
    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("🎉 LLM 集成测试通过！")
        print("=" * 60)
        
        # 现在测试完整报告生成（也用子进程）
        print("\n是否继续测试完整报告生成? (y/n)")
        # 自动执行
        print("\n🚀 启动完整报告生成测试...")
        # 这里可以调用 run_gold_report.py
        
    else:
        print("\n" + "=" * 60)
        print("❌ 测试失败")
        print("=" * 60)
        if result.stderr:
            print(f"错误输出:\n{result.stderr}")
        
except subprocess.TimeoutExpired:
    print("\n❌ 子进程超时（120秒）")
    print("可能原因: LLM API 调用超时或静默崩溃")
    
except Exception as e:
    print(f"\n❌ 子进程执行失败: {e}")

# 清理临时文件
try:
    if os.path.exists(test_file):
        os.remove(test_file)
        print(f"\n🗑️  临时测试文件已清理: {test_file}")
except:
    pass

print("\n测试完成。")

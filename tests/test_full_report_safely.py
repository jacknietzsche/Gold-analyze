#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整报告生成测试 - 使用子进程隔离
"""
import subprocess
import sys
import os

print("=" * 60)
print("完整黄金量化报告生成测试（含LLM增强）")
print("=" * 60)

test_script = r"""
import sys
import os
sys.path.insert(0, os.path.dirname(r'__file__'))

print("[Test] 开始完整报告生成...")
print("[Test] llm_type=openrouter, use_llm=True\n")

try:
    from src.report.gold_report_generator_v6 import main
    result = main(use_llm=True, llm_type="openrouter")
    
    if result:
        print("\n[Test] ✅ 报告生成成功！")
        print(f"[Test] 返回对象类型: {type(result)}")
        
        # 检查是否有LLM内容
        if hasattr(result, 'topic_content'):
            tc = result.topic_content
            llm_topics = [k for k in tc if tc[k] and 'LLM' not in str(tc[k])[:50]]
            print(f"[Test] LLM生成主题数: {len([k for k in tc if tc[k]])}/{len(tc)}")
        
        sys.exit(0)
    else:
        print("\n[Test] ⚠️ 报告生成返回None")
        sys.exit(1)
        
except Exception as e:
    print(f"\n[Test] ❌ 报告生成失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""

test_file = r"C:\Users\21471\WorkBuddy\gold\_test_full_report.py"
with open(test_file, 'w', encoding='utf-8') as f:
    f.write(test_script)

print(f"📝 测试脚本已写入: {test_file}")
print(f"\n🚀 启动子进程（超时300秒）...\n")
print("-" * 60)

try:
    result = subprocess.run(
        [sys.executable, test_file],
        cwd=r"C:\Users\21471\WorkBuddy\gold",
        capture_output=True,
        text=True,
        timeout=300,
        encoding='utf-8'
    )
    
    # 打印输出
    if result.stdout:
        print(result.stdout)
    
    print("-" * 60)
    
    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("🎉 完整报告生成测试通过！")
        print("=" * 60)
        
        # 查找生成的报告文件
        import glob
        reports = glob.glob(r"C:\Users\21471\WorkBuddy\gold\reports\gold_report_*.html")
        if reports:
            latest = max(reports, key=os.path.getmtime)
            print(f"\n📄 最新报告: {os.path.basename(latest)}")
            print(f"   路径: {latest}")
            print(f"\n💡 可以在浏览器中打开查看完整LLM分析结果")
        
    else:
        print("\n" + "=" * 60)
        print("❌ 报告生成失败")
        print("=" * 60)
        if result.stderr:
            print(f"\n错误输出:\n{result.stderr[:2000]}")
        
except subprocess.TimeoutExpired:
    print("\n❌ 子进程超时（300秒）")
    print("可能原因: LLM API 调用超时或报告生成过程卡住")
    
except Exception as e:
    print(f"\n❌ 子进程执行失败: {e}")

# 清理
try:
    if os.path.exists(test_file):
        os.remove(test_file)
        print(f"\n🗑️  临时文件已清理")
except:
    pass

print("\n测试完成。")
